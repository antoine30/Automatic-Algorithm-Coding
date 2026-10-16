"""
Agent MBD v7 : modèle de référence Lean prouvé -> vecteurs de test -> code C cible -> validation

Étapes :
  1-3. Requirements -> spec formelle (validée par vous) -> modèle Lean + preuves.
       Réutilise agent_lean_v5.py (mêmes contrôles, même boucle LLM/Lean).
  4.   Vecteurs de test : Claude écrit un programme Lean qui APPELLE le modèle prouvé sur des
       entrées choisies (trajectoires, cas limites). Lean calcule les sorties attendues.
  5.   Code cible : Claude écrit model.c (la fonction) et harness.c (lecteur de vecteurs).
  6.   Validation : compilation, exécution sur les vecteurs, comparaison exacte aux sorties
       attendues. En cas d'écart, Claude corrige le C (jamais les vecteurs).

Ce qui est prouvé et ce qui ne l'est pas :
  - Prouvé par Lean : les propriétés du modèle (théorèmes de la spec validée).
  - Calculé par Lean : les valeurs attendues (exécution du modèle, pas preuve de chaque valeur).
  - Testé seulement : la conformité du code C, sur l'ensemble fini de vecteurs. Ce n'est pas une
    preuve d'équivalence pour toutes les entrées.

Fichiers produits dans mbd_out/ :
  Model_vectors.lean, vectors_in.txt, vectors_expected.txt, model.c, harness.c, report.txt

Prérequis : agent_lean_v5.py dans le même dossier, plus un compilateur C : gcc ou clang, sinon
  le script essaie leanc, le compilateur C livré avec Lean (via 'lake env leanc').

Utilisation :
  python agent_mbd_v7.py requirements_pi.txt
  python agent_mbd_v7.py requirements_pi.txt --skip-proof   # réutilise lean_out/Model.lean déjà prouvé
  python agent_mbd_v7.py requirements_pi.txt --vectors-only # s'arrête après les valeurs attendues (pas de C)
  python agent_mbd_v7.py req_module.txt --name mon_module   # un algorithme complexe, module par module :
                                                          # fichiers lean_out/mon_module.lean, mbd_out/mon_module/
  (--skip-proof et --vectors-only se combinent)
"""

import argparse
import datetime
import hashlib
import importlib.util
import os
import re
import sys
import json
import shutil
import subprocess
import tempfile

import agent_lean_v5 as v5

AGENT_VERSION = "2026-10-15.5"   # les trois scripts agent_*.py doivent porter le même numéro

# --- Configuration ---
MBD_DIR = "mbd_out"
MODEL_NAME = "Model"          # produit lean_out/Model.lean et lean_out/Model_spec.json
MAX_VECTOR_ROUNDS = 3
MAX_TARGET_ROUNDS = 4
MIN_CASES = 30
RUN_TIMEOUT = 60              # secondes pour l'exécution du harnais C
MAX_SHOWN_MISMATCHES = 3
C_CONTEXT = ""                # code C déjà validé (autres modules), à réutiliser dans le C d'intégration
ORACLE = None                 # fonction(liste d'entiers d'entrée) -> liste d'entiers de sortie : référence indépendante du modèle Lean
ORACLE_RETRIES = 1            # nouvelles preuves tentées si le modèle prouvé s'écarte de l'oracle
RUN_INFO = {}                 # trace de l'exécution, écrite dans result.json pour les rapports

INTERFACE_GUIDANCE = """
Contraintes d'interface (pour la génération ultérieure de vecteurs de test et de code C) :
- Le modèle est UNE fonction pure Lean dont les arguments et le résultat sont des Int (ou Nat),
  des tuples, ou des listes d'Int ou de Nat.
- Pour les listes, privilégie l'accès par `List.getD l i 0` et la construction par `List.range`
  et `List.map` : ces définitions sont bien plus faciles à prouver que la récursion sur les indices.
- L'état éventuel est passé explicitement en argument et renvoyé dans le résultat
  (pas de structure, pas de variable globale).
- Pour les divisions entières signées, utilise Int.tdiv (tronquée vers zéro, comme en C),
  pas l'opérateur / dont l'arrondi diffère pour les nombres négatifs.
- Virgule fixe : les entiers représentent des valeurs mises à l'échelle. Pas de Float.
"""

VECTOR_FORMAT = """Format des vecteurs (obligatoire) : pour chaque cas de test, le programme affiche
exactement DEUX lignes consécutives sur la sortie standard :
  IN  <entiers>      les arguments d'entrée, aplatis
  OUT <entiers>      le résultat, aplati
Aplatissement : un entier s'écrit tel quel (Bool : 0 ou 1) ; un tuple s'aplatit champ par champ,
dans l'ordre ; une liste s'écrit comme sa longueur suivie de ses éléments. Entiers séparés par
un espace. Exemple : IN 256 0 0 puis OUT 32 55 544."""


# ---------- Utilitaires ----------

def _drop_placeholder(text: str) -> str:
    """Retire une consigne du format de réponse recopiée par erreur (première ligne entièrement entre parenthèses, en colonne 0).
    Aucun code Lean ou C valide ne commence ainsi au niveau le plus haut."""
    lines = text.split("\n")
    i = next((k for k, l in enumerate(lines) if l.strip()), None)
    if i is not None and lines[i].startswith("(") and lines[i].rstrip().endswith(")") and " " in lines[i] and len(lines[i]) > 15:
        del lines[i]
    return "\n".join(lines).strip("\n")


def _section(reply: str, name: str, next_names=()) -> str:
    """Extrait le bloc '### NAME' d'une réponse, ou '' s'il est absent."""
    stop = "|".join(f"### {n}" for n in next_names) or r"\Z"
    m = re.search(rf"### {name}[ \t]*\n(.*?)(?={stop}|\Z)", reply, re.DOTALL)
    return _drop_placeholder(v5._clean_block(m.group(1))) if m else ""


def _strip_axiom_prints(src: str) -> str:
    return re.sub(r"^#print axioms.*$", "", src, flags=re.MULTILINE)


def _ints(text: str):
    return [int(tok) for tok in text.split()]


def _load_model():
    lean_path = os.path.join(v5.OUTPUT_DIR, f"{MODEL_NAME}.lean")
    spec_path = os.path.join(v5.OUTPUT_DIR, f"{MODEL_NAME}_spec.json")
    for p in (lean_path, spec_path):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Fichier introuvable : {p} (lancez d'abord sans --skip-proof)")
    with open(lean_path, "r", encoding="utf-8") as f:
        model_src = f.read()
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    return model_src, spec


# ---------- Étape 4 : vecteurs de test ----------

_VECTOR_TIPS = [
    (r"List Nat[\s\S]{0,120}List Int", "`List.range n` est une `List Nat`. Pour obtenir des entiers, ANNOTE le paramètre de la fonction : "
     "`(List.range 64).map (fun (k : Nat) => (k : Int) * 512 - 16384)`, ou utilise `Int.ofNat k`. Écrire `(k : Int)` sans annoter k ne suffit PAS "
     "(Lean en déduit que k est un Int et refuse la liste de Nat). Ne modifie pas autre chose : change exactement ces lignes."),
    (r"[Tt]ype mismatch", "Un type ne correspond pas : déclare le type des variables (`(x : Int)`), et convertis les Nat avec `Int.ofNat n`."),
    (r"[Uu]nknown (identifier|constant)", "Ce nom n'existe pas en Lean de base : limite-toi à List.map, List.range, List.foldl, List.zip, String, IO.println et aux fonctions du modèle."),
    (r"Timeout", "Le programme est trop long : réduis le nombre de cas et la taille des listes."),
]


def vector_error_tips(output: str) -> str:
    tips = [tip for rx, tip in _VECTOR_TIPS if re.search(rx, output)]
    return ("\n\nCONSEILS POUR CES ERREURS :\n- " + "\n- ".join(tips)) if tips else ""


def prompt_vectors(requirements, spec, model_src, previous, error):
    feedback = ""
    if previous:
        feedback = f"""
Ta tentative précédente :
```lean
{previous}
```
Retour du système :
```
{error[:3000]}
```
Corrige-la.
"""
    return f"""[TÂCHE: VECTEURS]
Voici un modèle de référence Lean, déjà PROUVÉ conforme à sa spécification.

Requirements d'origine :
{requirements}

Signature du modèle : {spec['signature']}

Code Lean du modèle (ne le modifie pas, il est déjà dans le fichier) :
```lean
{_strip_axiom_prints(model_src)}
```

Écris un programme Lean (`def main : IO Unit`) qui génère des vecteurs de test en APPELANT le modèle.
{VECTOR_FORMAT}

Exigences :
- Au moins {MIN_CASES} cas, déterministes (pas d'aléatoire, ou un générateur congruentiel à graine fixe).
- Couvre : trajectoires typiques (itérer le modèle en réinjectant l'état), valeur nulle, signes
  positifs et négatifs, saturations atteintes des deux côtés, valeurs juste avant/après un seuil.
- Les sorties OUT doivent être calculées par le modèle, jamais écrites en dur.
- Pas de ligne `import` ni de `open` global : ton code est AJOUTÉ à la fin du fichier du modèle.
- Pas de `sorry`.
- Piège fréquent : `List.range n` est une `List Nat`. Pour des entiers écris `(List.range 64).map (fun (k : Nat) => (k : Int) * 512 - 16384)`
  (annote k : Nat) ; les négatifs littéraux s'écrivent `(-5 : Int)`.
{feedback}
Réponds EXACTEMENT sous cette forme, sans rien d'autre. Écris directement le code Lean sous la ligne ### MAIN ;
ne recopie aucune consigne entre parenthèses :
### MAIN
(code Lean : éventuelles fonctions auxiliaires puis def main)
"""


def run_lean_program(path: str) -> dict:
    try:
        code, out, err, timed_out = v5.run_with_timeout(["lake", "env", "lean", "--run", os.path.abspath(path)],
                                                        cwd=v5.LEAN_PROJECT_DIR, timeout=v5.file_timeout(path))
    except (FileNotFoundError, NotADirectoryError):
        print(f"⚠️  'lake' ou dossier de projet introuvable ({v5.LEAN_PROJECT_DIR}).")
        sys.exit(1)
    if timed_out:
        return {"ok": False, "stdout": "", "stderr": "Timeout Lean."}
    return {"ok": code == 0, "stdout": out, "stderr": err}


def parse_cases(stdout: str):
    """Extrait les paires (entrées, sorties) des lignes IN/OUT. Lève ValueError si le format est faux."""
    cases, pending = [], None
    for raw in stdout.splitlines():
        line = raw.strip()
        if line.startswith("IN "):
            if pending is not None:
                raise ValueError("deux lignes IN consécutives sans OUT entre elles")
            pending = _ints(line[3:])
        elif line.startswith("OUT "):
            if pending is None:
                raise ValueError("ligne OUT sans IN avant elle")
            cases.append((pending, _ints(line[4:])))
            pending = None
    if pending is not None:
        raise ValueError("dernière ligne IN sans OUT")
    return cases


def coverage_report(cases) -> str:
    lines = [f"{len(cases)} cas de test."]
    for label, idx in (("entrée", 0), ("sortie", 1)):
        widths = {len(c[idx]) for c in cases}
        if len(widths) != 1:
            lines.append(f"  {label}s de longueur variable (listes) : pas de statistiques par colonne.")
            continue
        for j in range(widths.pop()):
            col = [c[idx][j] for c in cases]
            lines.append(f"  {label} {j} : min={min(col)}, max={max(col)}, valeurs distinctes={len(set(col))}")
            if idx == 1 and len(cases) >= 20 and len(set(col)) == 1:
                lines.append(f"  ⚠️  sortie {j} constante sur tous les cas : le modèle est peut-être dégénéré (à vérifier)")
    return "\n".join(lines)


class OracleMismatch(Exception):
    def __init__(self, n_bad, n_checked, examples):
        super().__init__(f"{n_bad} écart(s) sur {n_checked} cas contrôlés")
        self.n_bad, self.n_checked, self.examples = n_bad, n_checked, examples


def check_oracle(cases):
    """Compare les sorties calculées par le modèle Lean à l'oracle indépendant. Lève OracleMismatch en cas d'écart."""
    if ORACLE is None:
        return
    bad, checked, skipped = [], 0, 0
    for inp, out in cases:
        try:
            exp = [int(v) for v in ORACLE(list(inp))]
        except Exception:
            skipped += 1          # entrée hors du domaine de l'oracle (débordement, etc.) : cas ignoré
            continue
        checked += 1
        if exp != list(out):
            bad.append((inp, exp, out))
    print(f"🔎 Oracle indépendant : {checked} cas contrôlés, {len(bad)} écart(s)" + (f", {skipped} cas ignorés" if skipped else ""))
    if bad:
        ex = "\n".join(f"  entrées {_short(i)} -> attendu {_short(e)} (le modèle Lean donne {_short(o)})" for i, e, o in bad[:4])
        raise OracleMismatch(len(bad), checked, ex)


def _short(v, limit=14):
    v = list(v)
    return str(v) if len(v) <= limit else str(v[:limit])[:-1] + f", ... ({len(v)} valeurs)]"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def try_reuse_vectors(model_src):
    """Réutilise le programme de vecteurs déjà écrit pour CE modèle Lean (même contenu) : Lean le réexécute (gratuit, déterministe),
    puis l'oracle recontrôle les sorties. Aucun appel à Claude. Retourne les cas, ou None si rien n'est réutilisable."""
    if v5.FORCE:
        return None
    path = os.path.join(MBD_DIR, "Model_vectors.lean")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            stored = f.read()
    except OSError:
        return None
    # le fichier de vecteurs commence par le code du modèle : s'il est identique au modèle courant (à la ligne d'import près : une preuve
    # récupérée sans Mathlib a perdu sa ligne « import »), les vecteurs lui correspondent. On reconstruit alors le fichier avec le modèle courant.
    drop_imports = lambda t: re.sub(r"^\s*import\s+\S+[ \t]*\n", "", t, flags=re.MULTILINE)
    model_text = _strip_axiom_prints(model_src).rstrip()
    stored_n, model_n = drop_imports(stored).lstrip("\n"), drop_imports(model_text).strip("\n") + "\n\n"   # les lignes vides de tête ne comptent pas
    if not stored_n.startswith(model_n):
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write(model_text + "\n\n" + stored_n[len(model_n):])
    result = run_lean_program(path)
    if not result["ok"]:
        return None
    try:
        cases = parse_cases(result["stdout"])
    except ValueError:
        return None
    if len(cases) < MIN_CASES:
        return None
    check_oracle(cases)   # lève OracleMismatch si le modèle s'écarte de l'oracle
    print(f"♻️  Vecteurs réutilisés ({len(cases)} cas, recalculés par Lean et recontrôlés par l'oracle) : aucun appel à Claude.")
    RUN_INFO.update(vector_rounds=0, coverage=coverage_report(cases))
    return cases


def generate_vectors(requirements, spec, model_src):
    os.makedirs(MBD_DIR, exist_ok=True)
    fn_name = v5.signature_name(spec["signature"])
    path = os.path.join(MBD_DIR, "Model_vectors.lean")
    previous, error, last_main = "", "", ""

    for round_no in range(1, MAX_VECTOR_ROUNDS + 1):
        print(f"\n--- Vecteurs : tentative {round_no}/{MAX_VECTOR_ROUNDS} ---")
        v5.set_stage(f"vecteurs {round_no}")
        reply = v5.ask_claude(prompt_vectors(requirements, spec, model_src, previous, error), max_tokens=5000)
        main_code = _section(reply, "MAIN")
        previous = main_code or reply
        same_as_before = bool(last_main) and main_code.strip() == last_main.strip()
        last_main = main_code

        if "def main" not in main_code:
            error = "Format invalide : fournis un bloc '### MAIN' contenant 'def main : IO Unit'."
            print("⚠️  Réponse mal formatée.")
            continue
        if fn_name and not re.search(rf"\b{re.escape(fn_name)}\b", main_code):
            error = f"Le programme n'appelle jamais le modèle `{fn_name}` : les sorties ne seraient pas calculées par lui."
            print("🚫 Le modèle n'est pas appelé, tentative rejetée.")
            continue
        if v5.check_forbidden(main_code) or re.search(r"^\s*import\b", main_code, re.MULTILINE):
            error = "Mot interdit (sorry, axiom...) ou ligne 'import' présente."
            print("🚫 Contenu interdit, tentative rejetée.")
            continue

        with open(path, "w", encoding="utf-8") as f:
            f.write(_strip_axiom_prints(model_src).rstrip() + "\n\n" + main_code + "\n")

        result = run_lean_program(path)
        if not result["ok"]:
            error = (result["stdout"] + "\n" + result["stderr"]).strip()
            v5.note_outcome("Lean a rejeté le programme de vecteurs")
            print("❌ Lean a rejeté le programme :")
            print(error[:600])
            with open(path, "r", encoding="utf-8") as fsrc:
                error = v5.annotate_errors(fsrc.read(), error) + vector_error_tips(error)
            if same_as_before:
                error = ("ATTENTION : ton programme est IDENTIQUE à la tentative précédente et échoue donc à l'identique. Modifie-le réellement, "
                         "en suivant les conseils ci-dessous.\n") + error
            continue

        try:
            cases = parse_cases(result["stdout"])
        except ValueError as e:
            error = f"Sortie mal formée : {e}. Respecte le format IN/OUT."
            print(f"⚠️  {error}")
            continue
        if len(cases) < MIN_CASES:
            error = f"Seulement {len(cases)} cas : il en faut au moins {MIN_CASES}."
            print(f"⚠️  {error}")
            continue

        check_oracle(cases)
        with open(os.path.join(MBD_DIR, "cache.json"), "w", encoding="utf-8") as fc:
            json.dump({"model_hash": _sha(model_src)}, fc)
        v5.note_outcome(f"OK : {len(cases)} cas")
        print("✅ Vecteurs générés par le modèle Lean.")
        print(coverage_report(cases))
        RUN_INFO.update(vector_rounds=round_no, coverage=coverage_report(cases))
        return cases

    return None


def write_vectors(cases):
    with open(os.path.join(MBD_DIR, "vectors_in.txt"), "w", encoding="utf-8") as f:
        f.write("".join(" ".join(map(str, i)) + "\n" for i, _ in cases))
    with open(os.path.join(MBD_DIR, "vectors_expected.txt"), "w", encoding="utf-8") as f:
        f.write("".join(" ".join(map(str, o)) + "\n" for _, o in cases))


# ---------- Étape 5 : code C cible ----------

def prompt_target(requirements, spec, model_src, previous_c, error):
    feedback = ""
    if previous_c:
        feedback = f"""
Ta tentative précédente :
```c
{previous_c}
```
Retour de la validation :
```
{error[:3000]}
```
Corrige la LOGIQUE du code. N'écris jamais de cas particuliers pour des valeurs précises.
"""
    ctx = ("Code C déjà validé pour les modules (à réutiliser : copie les fonctions telles quelles, "
           "sans définitions en double) :\n```c\n" + C_CONTEXT + "\n```\n") if C_CONTEXT else ""
    return f"""[TÂCHE: CODE_C]
Traduis ce modèle de référence Lean (prouvé) en C.
{ctx}
Requirements : {requirements}

Signature Lean : {spec['signature']}

Modèle Lean :
```lean
{_strip_axiom_prints(model_src)}
```

Exigences :
- C99, sans flottants, sans dépendance hors bibliothèque standard. Utilise int64_t pour tous les
  entiers, sauf si les requirements imposent d'autres largeurs.
- Même arithmétique que le modèle : mêmes arrondis, mêmes saturations. La division `/` du C tronque
  vers zéro, comme Int.tdiv ; si le modèle utilise l'opérateur `/` ou `%` de Lean (division
  euclidienne), reproduis-la explicitement.
- `model.c` : UNIQUEMENT la ou les fonctions du modèle (pas de main, pas d'entrées-sorties).
- `harness.c` : doit contenir `#include "model.c"` et un `main` qui lit les entrées sur l'entrée
  standard, une ligne par cas, puis affiche pour chaque cas UNE ligne contenant le résultat.
  Il doit accepter des listes jusqu'à 65536 éléments (tableaux statiques assez grands ou allocation dynamique).
{VECTOR_FORMAT}
  Le harnais affiche seulement les entiers de sortie séparés par un espace (printf("%lld")),
  sans le préfixe OUT. Il lit les entrées en suivant ce même aplatissement.
{feedback}
Réponds EXACTEMENT sous cette forme, sans rien d'autre :
### MODEL_C
(code de model.c)
### HARNESS_C
(code de harness.c)
Écris directement le code C sous chaque ligne ###, sans recopier les consignes entre parenthèses.
"""


_CC_CACHE = {}


def _c_candidates():
    c = []
    for name in ("gcc", "clang", "cc"):
        if shutil.which(name):
            c.append(([name], None))
    if importlib.util.find_spec("ziglang"):
        c.append(([sys.executable, "-m", "ziglang", "cc"], None))
    if shutil.which("zig"):
        c.append((["zig", "cc"], None))
    if shutil.which("lake") and os.path.isdir(v5.LEAN_PROJECT_DIR):
        c.append((["lake", "env", "leanc"], v5.LEAN_PROJECT_DIR))
    return c


def _probe_c(cc, cwd) -> bool:
    """Un compilateur est retenu seulement s'il sait compiler un programme qui inclut stdio.h, stdint.h et stdlib.h."""
    d = tempfile.mkdtemp()
    src, exe = os.path.join(d, "p.c"), os.path.join(d, "p.exe" if os.name == "nt" else "p")
    with open(src, "w") as f:
        f.write("#include <stdio.h>\n#include <stdint.h>\n#include <stdlib.h>\nint main(void){printf(\"ok\");return 0;}\n")
    try:
        r = subprocess.run(cc + ["-o", exe, src], capture_output=True, text=True, cwd=cwd, timeout=180)
        return r.returncode == 0 and os.path.isfile(exe)
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


def find_c_compiler():
    """Premier compilateur C réellement utilisable : gcc, clang, cc, zig (pip install ziglang), puis leanc."""
    if "cc" not in _CC_CACHE:
        _CC_CACHE["cc"] = (None, None)
        for cc, cwd in _c_candidates():
            if _probe_c(cc, cwd):
                _CC_CACHE["cc"] = (cc, cwd)
                break
    return _CC_CACHE["cc"]


C_COMPILER_HELP = """⚠️  Aucun compilateur C utilisable n'a été trouvé (gcc, clang, zig et leanc ont été essayés : aucun ne compile
    un programme qui inclut stdio.h). Le compilateur leanc livré avec Lean n'inclut pas les en-têtes standard sous Windows.
    Solution la plus simple, sans droits administrateur :  pip install ziglang   puis relancez (--resume).
    Autres solutions : winget install BrechtSanders.WinLibs.POSIX.UCRT (gcc), MSYS2, ou Visual Studio Build Tools."""


_C_ERR_RE = re.compile(r"^(?P<file>[^\n]*?\.c):(?P<line>\d+):(?P<col>\d+): (?:fatal )?error", re.MULTILINE)


def annotate_c_errors(output: str, files: dict, max_items: int = 6) -> str:
    """Ajoute à la sortie du compilateur C les lignes fautives. files : {nom de fichier: texte}."""
    notes, seen = [], set()
    for m in _C_ERR_RE.finditer(output):
        name = os.path.basename(m.group("file").replace("\\", "/"))
        ln = int(m.group("line"))
        text = files.get(name)
        if text is None or (name, ln) in seen:
            continue
        seen.add((name, ln))
        lines = text.splitlines()
        if 1 <= ln <= len(lines):
            ctx = [f"{k:4d}{'>' if k == ln else ' '}| {lines[k - 1]}" for k in range(max(1, ln - 1), min(len(lines), ln + 1) + 1)]
            notes.append(f"{name}, ligne {ln} :\n" + "\n".join(ctx))
        if len(notes) >= max_items:
            break
    return output + ("\n\nCODE CONCERNÉ :\n" + "\n\n".join(notes) if notes else "")


def compile_c(harness_path: str, exe_path: str) -> dict:
    cc, cwd = find_c_compiler()
    if cc is None:
        print(C_COMPILER_HELP)
        sys.exit(1)
    cmd = cc + ["-O1", "-o", os.path.abspath(exe_path), os.path.abspath(harness_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    return {"ok": r.returncode == 0, "output": (r.stdout + "\n" + r.stderr).strip(), "cc": " ".join(cc)}


def compare(expected_cases, actual_stdout: str):
    """Compare les sorties du C aux valeurs attendues. Retourne (nb_écarts, résumé texte)."""
    actual = [line.split() for line in actual_stdout.splitlines() if line.strip()]
    mismatches = []
    if len(actual) != len(expected_cases):
        sample = "\n".join("  " + " ".join(l)[:100] for l in actual[:3])
        return len(expected_cases), (
            f"Le harnais a produit {len(actual)} lignes pour {len(expected_cases)} cas de test. Il doit afficher EXACTEMENT UNE ligne par cas, "
            "contenant uniquement les entiers de sortie séparés par un espace : pas d'écho des entrées, pas de préfixe (IN, OUT), "
            f"pas de ligne d'en-tête ni de ligne vide. Premières lignes produites :\n{sample}"
        )
    for k, ((inp, exp), got) in enumerate(zip(expected_cases, actual)):
        try:
            got_ints = [int(t) for t in got]
        except ValueError:
            got_ints = got
        if got_ints != exp:
            mismatches.append((k, inp, exp, got_ints))
    if not mismatches:
        return 0, "Aucun écart."
    shown = "\n".join(
        f"  cas {k}: entrées={inp} attendu={exp} obtenu={got}"
        for k, inp, exp, got in mismatches[:MAX_SHOWN_MISMATCHES]
    )
    return len(mismatches), f"{len(mismatches)} écart(s) sur {len(expected_cases)} cas. Premiers écarts :\n{shown}"


def try_existing_c(cases):
    """Essaie d'abord le model.c et le harness.c déjà présents : s'ils compilent et reproduisent TOUS les vecteurs courants, ils sont
    valides (la validation est refaite localement), sans appel à Claude. Retourne (True, résumé) ou None."""
    if v5.FORCE:
        return None
    mp, hp = os.path.join(MBD_DIR, "model.c"), os.path.join(MBD_DIR, "harness.c")
    if not (os.path.isfile(mp) and os.path.isfile(hp)):
        return None
    exe = os.path.join(MBD_DIR, "harness.exe" if os.name == "nt" else "harness")
    build = compile_c(hp, exe)
    if not build["ok"]:
        return None
    stdin_text = "".join(" ".join(map(str, i)) + "\n" for i, _ in cases)
    try:
        run = subprocess.run([os.path.abspath(exe)], input=stdin_text, capture_output=True, text=True, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    if run.returncode != 0:
        return None
    n_bad, summary = compare(cases, run.stdout)
    if n_bad:
        return None
    RUN_INFO.update(target_rounds=0, compiler=build.get("cc"), n_mismatch=0, test_summary=summary)
    print(f"♻️  Code C déjà présent : compilé et reconfronté aux vecteurs courants, conforme. Aucun appel à Claude.")
    return True, summary


def generate_and_validate_target(requirements, spec, model_src, cases):
    reused = try_existing_c(cases)
    if reused:
        return reused
    previous_c, error, last_c = "", "", ""
    exe = os.path.join(MBD_DIR, "harness.exe" if os.name == "nt" else "harness")
    stdin_text = "".join(" ".join(map(str, i)) + "\n" for i, _ in cases)

    for round_no in range(1, MAX_TARGET_ROUNDS + 1):
        print(f"\n--- Code C : tentative {round_no}/{MAX_TARGET_ROUNDS} ---")
        v5.set_stage(f"code {round_no}")
        reply = v5.ask_claude(prompt_target(requirements, spec, model_src, previous_c, error), max_tokens=5000)
        model_c = _section(reply, "MODEL_C", ("HARNESS_C",))
        harness_c = _section(reply, "HARNESS_C")
        previous_c = f"/* model.c */\n{model_c}\n\n/* harness.c */\n{harness_c}"
        same_c = bool(last_c) and previous_c.strip() == last_c.strip()
        last_c = previous_c

        if not model_c or not harness_c:
            error = "Format invalide : fournis les deux blocs '### MODEL_C' et '### HARNESS_C'."
            print("⚠️  Réponse mal formatée.")
            continue
        if '#include "model.c"' not in harness_c:
            error = 'harness.c doit contenir exactement #include "model.c".'
            print("⚠️  harness.c n'inclut pas model.c.")
            continue

        with open(os.path.join(MBD_DIR, "model.c"), "w", encoding="utf-8") as f:
            f.write(model_c + "\n")
        harness_path = os.path.join(MBD_DIR, "harness.c")
        with open(harness_path, "w", encoding="utf-8") as f:
            f.write(harness_c + "\n")

        build = compile_c(harness_path, exe)
        if not build["ok"]:
            error = "Erreur de compilation :\n" + annotate_c_errors(build["output"], {"model.c": model_c, "harness.c": harness_c})
            v5.note_outcome("compilation C échouée")
            print("❌ Compilation échouée :")
            print(build["output"][:600])
            continue

        try:
            run = subprocess.run([os.path.abspath(exe)], input=stdin_text, capture_output=True,
                                 text=True, timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            error = f"Le harnais n'a pas terminé en {RUN_TIMEOUT} s."
            print("❌ Timeout à l'exécution.")
            continue
        if run.returncode != 0:
            error = f"Le harnais s'est terminé avec le code {run.returncode}.\n{run.stderr[:500]}"
            print("❌ Plantage à l'exécution.")
            continue

        n_bad, summary = compare(cases, run.stdout)
        if same_c and n_bad:
            summary = "ATTENTION : ton code est IDENTIQUE à la tentative précédente et donne le même résultat. Change-le réellement.\n" + summary
        RUN_INFO.update(target_rounds=round_no, compiler=build.get("cc"), n_mismatch=n_bad, test_summary=summary)
        v5.note_outcome(("conforme sur tous les vecteurs" if n_bad == 0 else f"{n_bad} écart(s)"))
        print(("✅ " if n_bad == 0 else "❌ ") + summary)
        if n_bad == 0:
            return True, summary
        error = summary

    return False, error


# ---------- Orchestration ----------

def _tool_version(cmd, cwd=None) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=60)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def _write_result_json(requirements, cases, ok, summary):
    proof_path = os.path.join(v5.OUTPUT_DIR, f"{MODEL_NAME}_proof.json")
    proof = {}
    if os.path.isfile(proof_path):
        with open(proof_path, "r", encoding="utf-8") as f:
            proof = json.load(f)
    cc, cwd = find_c_compiler()
    info = dict(RUN_INFO)
    info.update(
        name=MODEL_NAME, ok=ok, final_summary=summary, requirements=requirements, n_cases=len(cases),
        generated_at=datetime.datetime.now().isoformat(timespec="seconds"),
        lean_file=os.path.join(v5.OUTPUT_DIR, f"{MODEL_NAME}.lean"), mbd_dir=MBD_DIR, proof=proof,
        toolchain={"lean": _tool_version(["lake", "env", "lean", "--version"], v5.LEAN_PROJECT_DIR),
                   "c_compiler": _tool_version(cc + ["--version"], cwd) if cc else "?"},
    )
    with open(os.path.join(MBD_DIR, "result.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


def run_pipeline(requirements_path: str, skip_proof: bool = False, vectors_only: bool = False):
    """Exécute toute la chaîne d'un module ; écrit à la fin le bilan des appels à Claude (tokens, coût estimé)."""
    try:
        return _run_pipeline(requirements_path, skip_proof, vectors_only)
    finally:
        v5.write_call_journal(MODEL_NAME)


def _run_pipeline(requirements_path: str, skip_proof: bool = False, vectors_only: bool = False):
    RUN_INFO.clear()
    v5.ensure_lean_project()
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = f.read().strip()

    extra, cases = "", None
    for attempt in range(1 + ORACLE_RETRIES):
        if not skip_proof:
            print("=== Étapes 1 à 3 : spec formelle et modèle Lean prouvé ===")
            saved_force = v5.FORCE
            v5.FORCE = saved_force or bool(extra)   # relance due à l'oracle : on ne réutilise surtout pas la preuve précédente
            try:
                ok = v5.prove_requirements(requirements + "\n" + INTERFACE_GUIDANCE + extra, name=MODEL_NAME)
            finally:
                v5.FORCE = saved_force
            if not ok:
                print("⚠️  Le modèle n'a pas pu être prouvé : arrêt avant la génération de vecteurs.")
                return False
        model_src, spec = _load_model()
        print("\n=== Étape 4 : vecteurs de test générés par le modèle Lean ===")
        try:
            cases = try_reuse_vectors(model_src) or generate_vectors(requirements, spec, model_src)
        except OracleMismatch as e:
            os.makedirs(MBD_DIR, exist_ok=True)
            with open(os.path.join(MBD_DIR, "oracle_mismatch.txt"), "w", encoding="utf-8") as f:
                f.write(f"{e}\n{e.examples}\n")
            print(f"⛔ Le modèle Lean prouvé s'écarte de l'oracle indépendant ({e}) : son implémentation n'est pas fidèle.\n{e.examples}")
            if skip_proof or attempt == ORACLE_RETRIES:
                return False
            print("↻ Nouvelle preuve, avec ces exemples de référence ajoutés à la description.")
            extra = ("\n\nEXEMPLES DE RÉFÉRENCE EXACTS (calculés par un oracle indépendant ; le modèle DOIT les reproduire ; "
                     "format aplati : une liste = sa longueur puis ses éléments) :\n" + e.examples)
            continue
        break
    if cases is None:
        print("⚠️  Pas de vecteurs valides après les tentatives.")
        return False
    write_vectors(cases)
    if vectors_only:
        print(f"\n✅ Valeurs attendues écrites dans {MBD_DIR}/vectors_expected.txt (entrées : {MBD_DIR}/vectors_in.txt).")
        return True

    print("\n=== Étapes 5 et 6 : code C cible et validation ===")
    ok, summary = generate_and_validate_target(requirements, spec, model_src, cases)

    report = os.path.join(MBD_DIR, "report.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"Modèle prouvé : {os.path.join(v5.OUTPUT_DIR, MODEL_NAME + '.lean')}\n")
        f.write(coverage_report(cases) + "\n\n")
        f.write(("CONFORME : " if ok else "NON CONFORME : ") + summary + "\n")
        f.write("Rappel : conformité vérifiée par test sur ces vecteurs, pas prouvée pour toutes les entrées.\n")
    _write_result_json(requirements, cases, ok, summary)

    print("\n=== BILAN ===")
    print(("✅ Code C conforme sur tous les vecteurs." if ok else "⚠️  Code C non conforme après les tentatives.")
          + f" Détails : {report}")
    return ok


def configure(name: str):
    """Choisit le module courant : fichiers lean_out/<name>.* et mbd_out/<name>/."""
    global MODEL_NAME, MBD_DIR
    MODEL_NAME = re.sub(r"\W", "_", name)
    v5.CURRENT["module"] = MODEL_NAME
    MBD_DIR = "mbd_out" if MODEL_NAME == "Model" else os.path.join("mbd_out", MODEL_NAME)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Modèle Lean prouvé -> vecteurs de test -> code C -> validation")
    parser.add_argument("requirements", help="fichier texte des requirements du module")
    parser.add_argument("--skip-proof", action="store_true", help="réutilise lean_out/<name>.lean déjà prouvé")
    parser.add_argument("--vectors-only", action="store_true", help="s'arrête après les valeurs attendues")
    parser.add_argument("--name", default="Model", help="nom du module (fichiers séparés par module)")
    args = parser.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Variable ANTHROPIC_API_KEY non définie.")
        sys.exit(1)
    if not os.path.isfile(args.requirements):
        print(f"⚠️  Fichier introuvable : {args.requirements}")
        sys.exit(1)

    if getattr(v5, "AGENT_VERSION", None) != AGENT_VERSION:
        print(f"⛔ agent_lean_v5.py ({getattr(v5, 'AGENT_VERSION', 'ancienne version')}) et agent_mbd_v7.py ({AGENT_VERSION}) sont de versions différentes : "
              "remplacez agent_lean_v5.py par la dernière version livrée.")
        sys.exit(1)
    configure(args.name)
    print(v5.lean_mode_banner())
    v5.check_api()
    return run_pipeline(args.requirements, skip_proof=args.skip_proof, vectors_only=args.vectors_only)


if __name__ == "__main__":
    main()
