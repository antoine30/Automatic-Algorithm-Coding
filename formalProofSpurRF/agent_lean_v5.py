"""
Agent de vérification formelle v5 : Claude + Qwen + Lean 4

Principe :
  1. Claude lit un fichier de requirements et écrit la SPÉCIFICATION FORMELLE :
     la signature d'une fonction Lean et les énoncés de théorèmes qu'elle doit satisfaire.
     Vous validez (ou corrigez) cette spec : c'est le point de confiance du système.
  2. Qwen (local) écrit l'implémentation et les preuves.
  3. Lean 4 compile le tout. Les erreurs sont renvoyées au LLM, et on reboucle.
  4. Après QWEN_ROUNDS échecs, Claude prend la relève pour l'implémentation et les preuves.
  5. Succès = Lean compile sans erreur, sans 'sorry', sans axiome ajouté.

Contrôles de la spec avant la boucle de preuve :
  - La spec est compilée avec des 'sorry' pour détecter les énoncés mal formés (corrigés par Claude)
  - Une relecture critique signale propriétés manquantes et implémentations dégénérées possibles

Garde-fous contre la triche :
  - Les énoncés des théorèmes sont réinsérés par le script, jamais écrits par le LLM
  - Interdits : sorry, admit, axiom, native_decide, unsafe, implemented_by, opaque
  - Chaque théorème est suivi de '#print axioms' et le résultat est contrôlé

Prérequis :
  pip install anthropic requests
  Lean 4 installé (via elan) et un projet Lake avec Mathlib (dossier lean_project par défaut,
  ou variable d'environnement LEAN_PROJECT_DIR) : "lake env lean --version" doit fonctionner dedans
  Ollama avec qwen2.5-coder:7b, et ANTHROPIC_API_KEY définie

Utilisation :
  python agent_lean_v5.py requirements.txt

Avertissement : une preuve garantit que le code respecte la spec, pas que la spec
est la bonne. Relisez toujours la spec avant de lancer la boucle de preuve.
"""

import os
import re
import sys
import json
import hashlib
import signal
import subprocess
import textwrap
import time
import requests
from anthropic import Anthropic

AGENT_VERSION = "2026-10-15.5"   # les trois scripts agent_*.py doivent porter le même numéro

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
QWEN_MODEL = "qwen2.5-coder:7b"
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")   # ex. $env:CLAUDE_MODEL = "claude-opus-5-5" pour des preuves plus difficiles
MAX_ROUNDS = int(os.environ.get("MAX_ROUNDS", "12"))  # nombre total de tentatives
QWEN_ROUNDS = int(os.environ.get("QWEN_ROUNDS", "0"))  # tentatives confiées à Qwen avant Claude (0 : Claude seul, plus fiable pour Lean)
QWEN_TIMEOUT = 300     # secondes avant d'abandonner Qwen pour cette tentative
QWEN_MAX_TOKENS = 1500 # plafond de génération : évite les sorties sans fin
QWEN_NUM_CTX = 8192    # fenêtre de contexte (le défaut d'Ollama tronque silencieusement les longs prompts)
LEAN_IMPORT = os.environ.get("LEAN_IMPORT", "")  # ligne d'import en tête des fichiers : vide = Lean de base (rapide, par défaut) ; $env:LEAN_IMPORT = "import Mathlib" pour Mathlib
LIBRARY_SRC = ""     # code Lean déjà prouvé (autres modules), inséré avant l'implémentation
FORCE = False        # True : ignore tout ce qui est déjà validé et refait chaque étape
REFERENCE_DIR = None    # dossier de solutions de référence (<module>.lean), déjà vérifiées par Lean : repli après REFERENCE_AFTER échecs
REFERENCE_AFTER = int(os.environ.get("REFERENCE_AFTER", "3"))   # nombre de tentatives de Claude avant de tenter la solution de référence
LAST_RUN = {}        # trace de la dernière exécution de prove_requirements (pour les rapports)
LEAN_TIMEOUT = 300   # secondes, valeur de repli ; voir lean_timeout()
def _is_lake_project(path: str) -> bool:
    return bool(path) and os.path.isdir(path) and any(
        os.path.isfile(os.path.join(path, n)) for n in ("lakefile.toml", "lakefile.lean"))


def _find_project_dir() -> str:
    """Trouve le projet Lake (avec Mathlib) : variable LEAN_PROJECT_DIR, sinon un dossier
    'lean_project' cherché à côté du script, dans le dossier courant, et dans leurs parents
    (jusqu'à 4 niveaux). Toujours renvoyé en chemin absolu."""
    base = os.path.dirname(os.path.abspath(__file__))
    env = os.environ.get("LEAN_PROJECT_DIR")
    candidates = [env] if env else []
    for start in (base, os.getcwd()):
        d = os.path.abspath(start)
        for _ in range(5):
            candidates += [os.path.join(d, "lean_project"), d]
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    for c in candidates:
        if _is_lake_project(c):
            return os.path.abspath(c)
    return os.path.abspath(env or os.path.join(base, "lean_project"))


LEAN_PROJECT_DIR = _find_project_dir()  # projet Lake contenant Mathlib


def ensure_lean_project():
    """Arrête le programme avec un message clair si le projet Lake est introuvable."""
    if not _is_lake_project(LEAN_PROJECT_DIR):
        print(f"⚠️  Projet Lake introuvable : {LEAN_PROJECT_DIR}")
        print("    Il doit contenir lakefile.toml. Placez 'lean_project' à côté du script, ou indiquez son chemin :")
        print('    PowerShell : $env:LEAN_PROJECT_DIR = "C:\\chemin\\vers\\lean_project"')
        sys.exit(1)
OUTPUT_DIR = "lean_out"
FORBIDDEN = ["sorry", "admit", "axiom", "native_decide", "unsafe", "implemented_by", "opaque"]

# Le client Anthropic lit aussi ANTHROPIC_AUTH_TOKEN (envoyé EN PLUS de la clé) et ANTHROPIC_BASE_URL (adresse du serveur). Des valeurs
# résiduelles d'autres outils (Claude Code, proxys) provoquent des erreurs 401 même avec une clé active : cet agent les ignore.
ENV_NOTES = []
if os.environ.pop("ANTHROPIC_AUTH_TOKEN", None):
    ENV_NOTES.append("la variable ANTHROPIC_AUTH_TOKEN est définie dans votre session : elle est IGNORÉE par cet agent (elle s'ajoute à la clé et peut causer une 401)")
BASE_URL = os.environ.get("AGENT_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
_other_base = os.environ.get("ANTHROPIC_BASE_URL")
if _other_base and _other_base.rstrip("/") != BASE_URL.rstrip("/"):
    ENV_NOTES.append(f"la variable ANTHROPIC_BASE_URL vaut {_other_base} : elle est IGNORÉE (l'agent utilise {BASE_URL} ; "
                     "pour passer par un proxy, définissez AGENT_ANTHROPIC_BASE_URL)")
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), base_url=BASE_URL)


# ---------- Appels aux LLM ----------

def ask_qwen(prompt: str):
    """Retourne la réponse de Qwen, ou None si Ollama est trop lent ou injoignable."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": QWEN_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": QWEN_MAX_TOKENS, "num_ctx": QWEN_NUM_CTX, "temperature": 0.2},
            },
            timeout=QWEN_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Qwen n'a pas répondu ({type(e).__name__}).")
        return None


USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0}   # consommation cumulée de cette exécution
CALL_LOG = []                                                  # un enregistrement par appel à Claude (étape, tokens, durée, résultat)
CURRENT = {"module": "", "stage": ""}                          # module et étape en cours, pour étiqueter les appels
TOKEN_BUDGET = int(os.environ.get("TOKEN_BUDGET", "0") or 0)   # 0 = illimité ; sinon l'agent s'arrête proprement au-delà (tokens entrée + sortie)
DEFAULT_PRICES = {"claude-opus-5-5": (4.0, 20.0)}              # USD par million de tokens (entrée, sortie), indicatif : à vérifier sur la page de tarifs
LAST_STOP = {"reason": None}                                   # motif d'arrêt de la dernière réponse ("max_tokens" = réponse tronquée)

CREDIT_HELP = """
⛔ Le solde de crédits de l'API Anthropic est insuffisant. L'agent s'arrête proprement : rien n'est perdu.
   1. Ajoutez des crédits : console.anthropic.com, rubrique « Plans & Billing ».
   2. Relancez avec --resume : les modules déjà validés sont sautés.
   (Les crédits de l'API sont distincts d'un abonnement Claude.ai.)"""
LIMIT_HELP = """
⛔ La limite d'usage de l'API fixée sur votre compte est atteinte{date}. L'agent s'arrête proprement : rien n'est perdu.
   Cette limite est un plafond de dépense que vous (ou l'administrateur) avez réglé dans la console, ce n'est pas un solde vide.
   1. Relevez-la : console.anthropic.com, rubrique « Settings », puis « Limits » (ou les limites de l'espace de travail de votre clé).
   2. Ou attendez la date indiquée.
   Puis relancez : les modules déjà validés sont réutilisés sans appel à Claude."""
DIRECT_TEST_HELP = """   Test direct de la clé, sans passer par l'agent (PowerShell) :
       $h = @{ "x-api-key" = $env:ANTHROPIC_API_KEY; "anthropic-version" = "2023-06-01"; "content-type" = "application/json" }
       $b = '{"model":"claude-sonnet-4-6","max_tokens":5,"messages":[{"role":"user","content":"OK"}]}'
       try { (Invoke-RestMethod -Uri https://api.anthropic.com/v1/messages -Method Post -Headers $h -Body $b).content[0].text } catch { $_.ErrorDetails.Message }
   Si ce test répond du texte, la clé est bonne et le problème est dans l'environnement de l'agent ; sinon, le message d'erreur dit pourquoi."""
AUTH_HELP = """
⛔ Clé API refusée (erreur 401). Causes fréquentes :
   - la clé a été révoquée (vous en avez peut-être révoqué une pour sécurité) alors qu'une ANCIENNE valeur reste mémorisée par Windows
     (commande setx) : la session la reprend au redémarrage ;
   - la clé est incomplète, entre guillemets doubles imbriqués, ou contient un espace ou un saut de ligne ;
   - c'est la clé d'un autre compte ou d'un autre espace de travail.
   Solution : créez une NOUVELLE clé (console.anthropic.com, rubrique API Keys), puis dans PowerShell :
       $env:ANTHROPIC_API_KEY = "la-nouvelle-cle"                                   (pour cette fenêtre)
       setx ANTHROPIC_API_KEY "la-nouvelle-cle"                                     (pour les prochaines fenêtres)
   Ne collez jamais la clé dans une conversation. Vérifiez la longueur sans l'afficher : $env:ANTHROPIC_API_KEY.Length (environ 100)."""


def set_stage(label: str):
    CURRENT["stage"] = label


def note_outcome(text: str):
    """Associe un résultat (Lean a accepté ou rejeté, motif...) au dernier appel à Claude."""
    if CALL_LOG:
        CALL_LOG[-1]["resultat"] = text[:160]


def _prices():
    try:
        pin, pout = float(os.environ["PRICE_IN_PER_M"]), float(os.environ["PRICE_OUT_PER_M"])
        return pin, pout, "tarif saisi par vous"
    except (KeyError, ValueError):
        if CLAUDE_MODEL in DEFAULT_PRICES:
            pin, pout = DEFAULT_PRICES[CLAUDE_MODEL]
            return pin, pout, "tarif indicatif à vérifier sur la page de tarifs d'Anthropic"
    return None


def write_call_journal(name: str):
    """Affiche un bilan par étape (appels, tokens, coût estimé) et écrit lean_out/<name>_journal_appels.json."""
    rows = [c for c in CALL_LOG if c["module"] == name]
    if not rows:
        return
    by_stage = {}
    for c in rows:
        key = c["stage"].split(" ")[0]
        d = by_stage.setdefault(key, {"appels": 0, "in": 0, "out": 0})
        d["appels"] += 1
        d["in"] += c["input_tokens"]
        d["out"] += c["output_tokens"]
    fmt = lambda n: f"{n:,}".replace(",", " ")
    tin, tout = sum(c["input_tokens"] for c in rows), sum(c["output_tokens"] for c in rows)
    print(f"\n📊 BILAN DES APPELS À CLAUDE : module {name}, modèle {CLAUDE_MODEL}")
    for k, d in by_stage.items():
        print(f"   {k:10s} {d['appels']:3d} appels   {fmt(d['in']):>10s} tokens en entrée   {fmt(d['out']):>9s} tokens en sortie")
    print(f"   {'TOTAL':10s} {len(rows):3d} appels   {fmt(tin):>10s} tokens en entrée   {fmt(tout):>9s} tokens en sortie")
    pr = _prices()
    cost = None
    if pr:
        cost = tin / 1e6 * pr[0] + tout / 1e6 * pr[1]
        print(f"   Coût estimé : {cost:.2f} USD ({pr[0]:g} $/M en entrée, {pr[1]:g} $/M en sortie ; {pr[2]})")
    else:
        print("   Coût : définissez PRICE_IN_PER_M et PRICE_OUT_PER_M (USD par million de tokens) pour l'estimer.")
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, f"{name}_journal_appels.json"), "w", encoding="utf-8") as f:
            json.dump({"module": name, "model": CLAUDE_MODEL, "appels": rows, "total_input_tokens": tin, "total_output_tokens": tout,
                       "cout_estime_usd": cost}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _redact(text: str) -> str:
    return re.sub(r"sk-ant-[A-Za-z0-9_\-]+", "sk-ant-…", str(text))


def key_report() -> str:
    """Décrit la clé API de la session SANS l'afficher : longueur, début standard, caractères indésirables."""
    k = os.environ.get("ANTHROPIC_API_KEY", "")
    if not k:
        return "   Diagnostic : la variable ANTHROPIC_API_KEY est VIDE dans cette fenêtre PowerShell."
    problems = []
    if not k.startswith("sk-ant-"):
        problems.append("ne commence pas par « sk-ant- »")
    if re.search(r"\s", k):
        problems.append("contient un espace ou un saut de ligne")
    if '"' in k or "'" in k:
        problems.append("contient des guillemets")
    if len(k) < 90:
        problems.append("semble trop courte (une clé fait environ 100 caractères)")
    head = k[:7] if k.startswith("sk-ant-") else k[:2] + "…"
    forme = ("PROBLÈMES : " + " ; ".join(problems)) if problems else \
        "aucune anomalie de forme : la clé est donc probablement RÉVOQUÉE, supprimée, ou d'un autre compte"
    fin = f", fin « …{k[-4:]} »" if len(k) >= 12 else ""
    notes = "".join(f"   ⚠️  {n}.\n" for n in ENV_NOTES)
    return (notes + f"   Diagnostic de votre clé : longueur {len(k)}, début « {head} »{fin} ; {forme}.\n"
            "   Pour savoir de QUELLE clé il s'agit : sur console.anthropic.com, rubrique API Keys, la liste montre pour chaque clé ses derniers\n"
            "   caractères et son état. Si la fin ci-dessus n'y figure pas, ou figure comme révoquée, vous utilisez une ANCIENNE clé.")


def check_api(model=None):
    """Vérifie la clé, le crédit et un modèle avec une requête minimale AVANT un long travail. S'arrête avec un message clair en cas de problème."""
    if client is None:
        return
    model = model or CLAUDE_MODEL
    try:
        client.messages.create(model=model, max_tokens=5, messages=[{"role": "user", "content": "Réponds OK."}])
        print(f"🔑 API Anthropic joignable, clé acceptée, modèle {model}.")
    except Exception as e:
        status, msg, name = getattr(e, "status_code", None), str(e), type(e).__name__
        if "credit balance is too low" in msg:
            print(CREDIT_HELP)
            sys.exit(2)
        if "usage limits" in msg:
            m = re.search(r"regain access on ([^.']+?)(?:\.|'|$)", msg)
            print(LIMIT_HELP.format(date=f" (accès rétabli le {m.group(1).strip()})" if m else ""))
            sys.exit(2)
        if status in (401, 403) or name in ("AuthenticationError", "PermissionDeniedError"):
            print(AUTH_HELP)
            print(key_report())
            print(f"   Réponse brute de l'API (expurgée) : {_redact(msg)[:400]}")
            print(DIRECT_TEST_HELP)
            sys.exit(2)
        if status == 404 or "not_found" in msg:
            print(f"\n⛔ Le modèle « {model} » est inconnu ou non autorisé pour votre compte. Vérifiez $env:CLAUDE_MODEL ou la clé \"model\" de "
                  "projet_pm.json (par exemple claude-opus-5-5 ou claude-sonnet-5-5), ou retirez-la pour utiliser le modèle par défaut.")
            sys.exit(2)
        print(f"⚠️  Vérification de l'API non concluante ({name}) : le travail continue, les erreurs éventuelles seront traitées en cours de route.")


def usage_summary() -> str:
    fmt = lambda n: f"{n:,}".replace(",", " ")
    return (f"{USAGE['calls']} appels à Claude ; {fmt(USAGE['input_tokens'])} tokens en entrée, "
            f"{fmt(USAGE['output_tokens'])} tokens en sortie")


def ask_claude(prompt: str, max_tokens: int = 4000) -> str:
    """Appelle Claude. Réessaie (attente croissante) en cas d'erreur transitoire (limite de débit, surcharge, réseau) ;
    s'arrête avec un message clair si le solde est insuffisant ou la clé refusée."""
    for attempt in range(1, 7):
        try:
            t0 = time.monotonic()
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:  # les classes d'erreur d'anthropic sont reconnues par leur nom et leur code HTTP
            status, msg, name = getattr(e, "status_code", None), str(e), type(e).__name__
            if "credit balance is too low" in msg:
                print(CREDIT_HELP)
                sys.exit(2)
            if "usage limits" in msg:
                m = re.search(r"regain access on ([^.']+?)(?:\.|'|$)", msg)
                print(LIMIT_HELP.format(date=f" (accès rétabli le {m.group(1).strip()})" if m else ""))
                sys.exit(2)
            if status in (401, 403) or name in ("AuthenticationError", "PermissionDeniedError"):
                print(AUTH_HELP)
                print(key_report())
                sys.exit(2)
            if status == 404 or "not_found" in msg:
                print(f"\n⛔ Le modèle « {CLAUDE_MODEL} » est inconnu ou non autorisé pour votre compte. Vérifiez $env:CLAUDE_MODEL ou la clé \"model\" de projet_pm.json.")
                sys.exit(2)
            transient = status in (408, 409, 429, 500, 502, 503, 504, 529) or name in (
                "APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError", "OverloadedError")
            if transient and attempt < 6:
                wait = min(90, 4 * 2 ** (attempt - 1))
                print(f"⏳ API momentanément indisponible ({name}) : nouvelle tentative dans {wait} s ({attempt}/5).")
                time.sleep(wait)
                continue
            raise
        USAGE["calls"] += 1
        LAST_STOP["reason"] = getattr(response, "stop_reason", None)
        u = getattr(response, "usage", None)
        t_in, t_out = getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0
        USAGE["input_tokens"] += t_in
        USAGE["output_tokens"] += t_out
        CALL_LOG.append({"module": CURRENT["module"], "stage": CURRENT["stage"] or "autre", "model": CLAUDE_MODEL, "input_tokens": t_in,
                         "output_tokens": t_out, "stop": LAST_STOP["reason"], "secondes": round(time.monotonic() - t0, 1), "resultat": ""})
        if TOKEN_BUDGET and USAGE["input_tokens"] + USAGE["output_tokens"] > TOKEN_BUDGET:
            print(f"\n⛔ Plafond de tokens atteint ({TOKEN_BUDGET:,} fixés par TOKEN_BUDGET) : arrêt volontaire pour limiter le coût.".replace(",", " "))
            write_call_journal(CURRENT["module"])
            sys.exit(3)
        return "".join(b.text for b in response.content if b.type == "text")


def parse_json(reply: str) -> dict:
    """Extrait un objet JSON d'une réponse, même entourée de texte ou d'un bloc ```json ... ```."""
    text = reply.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("aucun objet JSON dans la réponse")
        text = text[start:end + 1]
    return json.loads(text)


def ask_json(prompt: str, retries: int = 3, max_tokens: int = 4000) -> dict:
    """Interroge Claude et renvoie un objet JSON ; redemande (jusqu'à `retries` fois) si la réponse n'est pas un JSON valide."""
    last = None
    for _ in range(retries):
        reply = ask_claude(prompt, max_tokens=max_tokens)
        try:
            return parse_json(reply)
        except ValueError as e:  # json.JSONDecodeError en est un cas particulier
            last = e
            prompt += ("\n\nTa réponse précédente n'était pas un JSON valide. Réponds UNIQUEMENT avec l'objet JSON complet, "
                       "sans aucun texte avant ou après.")
    raise ValueError(f"réponse JSON invalide après {retries} essais ({last})")


# ---------- Étape 1 : spécification formelle ----------

IMPOSED_BEGIN = "=== SPEC LEAN IMPOSÉE ==="
IMPOSED_END = "=== FIN SPEC ==="


def imposed_spec(requirements: str):
    """Si les requirements contiennent un bloc « SPEC LEAN IMPOSÉE », retourne la spec (signature + énoncés) qu'il décrit.
    Une spec relue et fixée par un humain est plus fiable qu'une spec regénérée par le modèle à chaque lancement."""
    if IMPOSED_BEGIN not in requirements or IMPOSED_END not in requirements:
        return None
    body = requirements.split(IMPOSED_BEGIN, 1)[1].split(IMPOSED_END, 1)[0]
    blocks, cur = [], []
    for line in body.splitlines():
        if re.match(r"^(def|theorem)\s", line) and cur:
            blocks.append("\n".join(cur).strip())
            cur = []
        if line.strip() or cur:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur).strip())
    sigs = [b for b in blocks if b.startswith("def ")]
    thms = [b for b in blocks if b.startswith("theorem ")]
    if len(sigs) != 1 or not thms or any(":=" in b.split("\n")[0] and b.startswith("def ") for b in sigs):
        raise ValueError("bloc SPEC LEAN IMPOSÉE invalide : une ligne 'def ...' (signature sans corps) et des 'theorem ...' sont attendus")
    return {"signature": sigs[0], "theorems": [{"name": b.split()[1], "statement": b} for b in thms]}


def write_spec(requirements: str) -> dict:
    set_stage("spec")
    fixed = imposed_spec(requirements)
    if fixed is not None:
        print("📌 Spécification Lean imposée par les requirements (non regénérée par le modèle).")
        return fixed
    prompt = f"""Voici des requirements en langage naturel :

{requirements}

{_library_block()}Traduis-les en spécification formelle {_dialect()} (ne mets pas d'import).
Réponds UNIQUEMENT avec un JSON de la forme :
{{
  "signature": "def nomFonction (arg : Type) : TypeRetour",
  "theorems": [
    {{"name": "nom_theoreme", "statement": "theorem nom_theoreme (args) : proposition"}}
  ]
}}
Règles :
- Formalise UNIQUEMENT les propriétés listées sous « Propriétés à prouver » (6 théorèmes au maximum). Ignore les propriétés
  marquées « souhaitable » ou « optionnelle » : elles sont volontairement exclues de cette version.
- La signature n'inclut PAS le corps (pas de ':=').
- Les énoncés n'incluent PAS ':= by' ni de preuve.
- Les énoncés doivent capturer la correction COMPLÈTE de la fonction, pas seulement des propriétés triviales.
- Utilise des types standard (Nat, Int, List, tuples ; avec Mathlib : ℚ, ℝ, Finset...) selon le besoin.
- Dans les énoncés, évite `let (a, b, c) := ... ; ...` (filtrage de motifs, qui complique les preuves) : utilise les projections
  (.1, .2.1, .2.2) ou des variables nommées. Si les requirements donnent une FORMULE exacte, ajoute un théorème qui l'énonce
  entièrement (égalité entre la sortie et l'expression écrite en toutes lettres) : c'est ce qui garantit la fidélité de l'implémentation.
Aucun texte avant ou après le JSON.
"""
    return ask_json(prompt)


def _dialect() -> str:
    """Version de Lean visée, selon LEAN_IMPORT : avec Mathlib (par défaut) ou Lean de base sans Mathlib (LEAN_IMPORT vide)."""
    if LEAN_IMPORT:
        return "Lean 4 avec Mathlib"
    return "Lean 4 de BASE, sans Mathlib (rien n'est importé : n'utilise ni lemmes ni tactiques de Mathlib comme linarith, nlinarith, positivity, norm_num, ring)"


def _tactics() -> str:
    if LEAN_IMPORT:
        return "simp, omega, induction, cases, rfl, decide, intro, constructor, exact, ring, linarith, nlinarith, positivity, norm_num, field_simp"
    return ("simp, omega, decide, decide +kernel, rfl, induction, cases, rcases, obtain, intro, constructor, exact, apply, rw, unfold, split, "
            "generalize, by_cases, show")


def _library_block() -> str:
    if not LIBRARY_SRC:
        return ""
    return ("Définitions et théorèmes DÉJÀ disponibles (modules prouvés, à utiliser tels quels, sans les redéfinir) :\n"
            f"```lean\n{LIBRARY_SRC}\n```\n\n")


def check_spec_compiles(spec: dict) -> str:
    """Compile la spec avec des 'sorry' pour détecter les énoncés mal typés ou mal formés.
    Retourne le texte des erreurs Lean, ou une chaîne vide si la spec est bien formée."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    parts = [LEAN_IMPORT, "", LIBRARY_SRC, "", f"noncomputable {spec['signature']} := sorry", ""]
    for t in spec["theorems"]:
        parts.append(f"{t['statement']} := by\n  sorry\n")
    path = os.path.join(OUTPUT_DIR, "_spec_check.lean")
    source = "\n".join(parts)
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    output = run_lean(path)["output"]
    return annotate_errors(source, output) if ": error" in output else ""


def fix_spec(requirements: str, spec: dict, errors: str) -> dict:
    set_stage("spec")
    prompt = f"""Cette spécification formelle ({_dialect()}) ne compile pas.

Requirements d'origine :
{requirements}

Spec actuelle (JSON) :
{json.dumps(spec, ensure_ascii=False, indent=2)}

Erreurs Lean :
{errors[:2000]}

Corrige la spec (signature et énoncés) sans en affaiblir le sens. Réponds UNIQUEMENT avec le même format JSON, sans texte autour.
"""
    return ask_json(prompt)


def audit_spec(requirements: str, spec: dict, brief: bool = False) -> str:
    set_stage("audit")
    """Relecture critique de la spec par Claude : une aide pour l'humain, pas une garantie."""
    statements = "\n".join(f"- {t['statement']}" for t in spec["theorems"])
    prompt = f"""Tu es un relecteur critique de spécifications formelles Lean 4.

Requirements d'origine :
{requirements}

Signature : {spec['signature']}
Théorèmes :
{statements}

Cherche les failles de cette spec :
1. Propriétés des requirements NON couvertes par les théorèmes.
2. Implémentations triviales ou dégénérées qui satisferaient quand même tous les théorèmes
   (par exemple renvoyer une liste vide ou une constante).
3. Hypothèses vacueuses ou contradictoires, cas limites mal traités (liste vide, zéro,
   soustraction ou division sur les entiers naturels).
4. Ambiguïtés des requirements que l'humain devrait trancher.

Réponds en français, par une liste courte et concrète. Si la spec te semble solide, dis-le en une
phrase : n'invente pas de défaut.
"""
    if brief:
        prompt += """
CONSIGNE SUPPLÉMENTAIRE : cette spécification a déjà été relue et fixée par un humain, et les requirements documentent ses choix de
conception. Signale UNIQUEMENT un défaut réel et bloquant : énoncé faux, vacueux ou incohérent avec les requirements, ou propriété importante
absente. 5 lignes au maximum, sans titres. Ne répète ni les choix de conception documentés, ni les risques de preuve, ni les remarques
de forme. S'il n'y a rien de bloquant, réponds exactement : RAS.
"""
    return ask_claude(prompt, max_tokens=700 if brief else 1500)


def validate_spec_with_user(spec: dict, spec_path: str, audit: str = "") -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    print("\n=== SPÉCIFICATION FORMELLE PROPOSÉE ===")
    print(spec["signature"])
    for t in spec["theorems"]:
        print(f"\n  {t['statement']}")
    print(f"\n(Fichier éditable : {spec_path})")
    if audit:
        print("\n=== AUDIT AUTOMATIQUE DE LA SPEC (aide à la relecture, pas une garantie) ===")
        print(audit)

    while True:
        answer = input("\nValider cette spec ? [o]ui / [e]diter le fichier puis recharger / [n]on et quitter : ").strip().lower()
        if answer == "o":
            return spec
        if answer == "e":
            input(f"Modifiez {spec_path}, enregistrez, puis appuyez sur Entrée...")
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
            print(spec["signature"])
            for t in spec["theorems"]:
                print(f"  {t['statement']}")
            spec_errors = check_spec_compiles(spec)
            if spec_errors:
                print("⚠️  La spec modifiée ne compile pas :")
                print(spec_errors[:800])
            else:
                print("✔️  La spec modifiée compile.")
            continue
        if answer == "n":
            return None


# ---------- Étape 2 : implémentation et preuves ----------

def build_attempt_prompt(spec: dict, previous: str, errors: str, prover: str, stagnating: bool = False,
                         requirements: str = "", bad_names=()) -> str:
    req_block = ""
    if requirements:
        req_block = ("Description fonctionnelle COMPLÈTE : c'est la RÉFÉRENCE. L'implémentation doit reproduire exactement ces formules "
                     "(constantes, arrondis, cas limites). Les théorèmes n'en expriment qu'une partie : une implémentation triviale ou "
                     "dégénérée qui les satisfait (par exemple une sortie toujours égale à 0) est INTERDITE. Si fidélité et preuve "
                     "s'opposent, la fidélité prime.\n```\n" + requirements + "\n```\n\n")
    statements = "\n".join(f"{i}. {t['statement']}" for i, t in enumerate(spec["theorems"], 1))
    feedback = ""
    if previous:
        feedback = f"""
Ta tentative précédente :
```lean
{previous}
```
Retour de vérification (erreurs Lean, ou motif de rejet avant compilation) :
```
{errors}
```
Corrige l'implémentation et/ou les preuves en tenant compte de ces erreurs.
"""
        if bad_names:
            feedback += ("\nNOMS DÉJÀ REJETÉS PAR LEAN (inexistants dans cette version, ou mal employés) : "
                         + ", ".join(f"`{n}`" for n in sorted(bad_names))
                         + ".\nNE LES RÉUTILISE PLUS. Démontre le résultat autrement (omega, simp, cases, induction, decide), "
                           "ou avec un lemme dont tu es certain qu'il existe.\n")
        if stagnating:
            feedback += ("\nATTENTION : ta tentative précédente a produit exactement les mêmes erreurs que la précédente. "
                         "Ne répète pas la même approche : change de stratégie (autre structure de preuve, autres lemmes auxiliaires, "
                         "autre définition de la fonction).\n")
    return f"""Tu écris du code {_dialect()} avec preuves (ne mets pas d'import).

{req_block}{_library_block()}Signature imposée de la fonction :
{spec['signature']}

Théorèmes à prouver (énoncés FIGÉS, tu n'écris que les preuves) :
{statements}
{feedback}
Tactiques utiles : {_tactics()}.
Interdit : sorry, admit, axiom, native_decide, unsafe, opaque.
La fonction doit être totale (terminaison évidente pour Lean).

Réponds EXACTEMENT dans ce format, sans rien d'autre :
### IMPL
(la fonction demandée, plus d'éventuelles fonctions auxiliaires `def`)
### LEMMAS
(lemmes auxiliaires COMPLETS avec leur preuve, par exemple `theorem aux ... := by ...` ; laisse vide si inutile)
### PROOF 1
(tactiques de la preuve du théorème 1, SANS le mot 'by' ni l'énoncé ; indentation cohérente)
### PROOF 2
(...)

Règles de syntaxe :
- N'utilise pas la notation `~` : écris `List.Perm a b`. Pas de `open` : préfixe les noms de bibliothèque (List., Nat., ...).
- Les noms des théorèmes imposés sont réservés : ne les redéclare pas. Tes lemmes auxiliaires doivent avoir d'autres noms.
- Les noms de lemmes de Mathlib changent selon les versions : n'utilise que des noms dont tu es certain ; sinon démontre le résultat toi-même
  (omega, simp, nlinarith, induction). Les utilitaires usuels (clamp, etc.) n'existent pas toujours : définis-les.
- « No goals to be solved » signifie qu'une tactique est en trop après la fermeture du but : supprime-la.
- Les numéros de ligne des erreurs sont ceux du fichier assemblé ; le code concerné est recopié sous les erreurs.
- Une preuve difficile demande presque toujours des lemmes auxiliaires : mets-les dans ### LEMMAS plutôt que des `have` imbriqués.
"""


def _drop_placeholder(text: str, proof: bool = False) -> str:
    """Retire une consigne du format de réponse recopiée par erreur (ligne entièrement entre parenthèses)."""
    lines = text.split("\n")
    i = next((k for k, l in enumerate(lines) if l.strip()), None)
    if i is not None:
        l = lines[i].strip()
        if l.startswith("(") and l.endswith(")") and " " in l and len(l) > 15 and (not proof or re.search(r"tactiques|preuve", l)):
            del lines[i]
    return "\n".join(lines).strip("\n")


def _clean_block(text: str) -> str:
    """Retire les balises ``` et les lignes vides de bord, puis normalise l'indentation commune.
    Ne jamais faire un .strip() brut : il détruit l'indentation de la première ligne et
    produit des blocs de tactiques mal alignés (erreur Lean 'unexpected token ... expected command')."""
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return textwrap.dedent("\n".join(lines)).strip("\n").rstrip()


def diagnose_reply(reply: str, n_theorems: int) -> str:
    """Dit pourquoi une réponse de preuve est inutilisable (et le redit à Claude, qui sinon répète la même erreur)."""
    if LAST_STOP.get("reason") == "max_tokens":
        return ("Ta réponse a été COUPÉE (limite de longueur atteinte) avant la fin. Écris uniquement le code demandé : aucun commentaire, "
                "aucune explication, aucun raisonnement ; garde les définitions et les preuves aussi courtes que possible. N'énumère jamais "
                "les 257 cases de la table à la main (disjonction + rcases) : prouve les faits sur la table par « decide +kernel » écrit "
                "directement sur l'énoncé « ∀ i, i < 257 → ... ».")
    if "### IMPL" not in reply:
        return "La section « ### IMPL » est absente. Commence ta réponse par la ligne ### IMPL, suivie du code."
    for i in range(1, n_theorems + 1):
        if f"### PROOF {i}" not in reply:
            return (f"La section « ### PROOF {i} » est absente : il faut {n_theorems} sections de preuve, numérotées de 1 à {n_theorems}, "
                    "dans l'ordre des théorèmes, chacune sur sa propre ligne « ### PROOF n ».")
    return "Format de réponse invalide : respecte exactement ### IMPL, ### LEMMAS puis ### PROOF 1, ### PROOF 2, ..."


def parse_attempt(reply: str, n_theorems: int):
    """Retourne (impl, lemmas, proofs), ou (None, None, None) si le format est invalide."""
    impl_match = re.search(r"### IMPL[ \t]*\n(.*?)(?=### LEMMAS|### PROOF|\Z)", reply, re.DOTALL)
    if not impl_match:
        return None, None, None
    impl = _drop_placeholder(_clean_block(impl_match.group(1)))
    lem_match = re.search(r"### LEMMAS[ \t]*\n(.*?)(?=### PROOF|\Z)", reply, re.DOTALL)
    lemmas = _drop_placeholder(_clean_block(lem_match.group(1))) if lem_match else ""
    proofs = []
    for i in range(1, n_theorems + 1):
        m = re.search(rf"### PROOF {i}[ \t]*\n(.*?)(?=### PROOF|\Z)", reply, re.DOTALL)
        if not m:
            return None, None, None
        proofs.append(_drop_placeholder(_clean_block(m.group(1)), proof=True))
    return impl, lemmas, proofs


def find_redeclared(spec: dict, text: str):
    """Détecte un théorème imposé redéclaré par le LLM (erreur 'has already been declared')."""
    for t in spec["theorems"]:
        if re.search(rf"\b(?:theorem|lemma)\s+{re.escape(t['name'])}\b", text):
            return t["name"]
    return None


def _strip_comments(text: str) -> str:
    """Retire les commentaires Lean (/- ... -/ et -- ...) avant de chercher des mots interdits."""
    text = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", text)


def signature_name(signature: str):
    """Extrait le nom de la fonction imposée depuis la signature."""
    m = re.match(r"\s*(?:noncomputable\s+)?def\s+([^\s(:]+)", signature)
    return m.group(1) if m else None


def check_forbidden(text: str):
    text = _strip_comments(text)
    for word in FORBIDDEN:
        if re.search(rf"\b{word}\b", text):
            return word
    return None


def assemble(spec: dict, impl: str, lemmas: str, proofs: list) -> str:
    parts = [LEAN_IMPORT, "", LIBRARY_SRC, "", impl, ""]
    if lemmas:
        parts += [lemmas, ""]
    for t, proof in zip(spec["theorems"], proofs):
        indented = "\n".join("  " + line for line in proof.splitlines())
        parts.append(f"{t['statement']} := by\n{indented}\n")
    for t in spec["theorems"]:
        parts.append(f"#print axioms {t['name']}")
    return "\n".join(parts)


# ---------- Étape 3 : vérification par Lean ----------

def lean_timeout() -> int:
    """Délai maximal d'une compilation Lean : variable LEAN_TIMEOUT, sinon 120 s en Lean de base et 300 s avec Mathlib (premier chargement lent)."""
    env = os.environ.get("LEAN_TIMEOUT")
    return int(env) if env else (300 if LEAN_IMPORT else 120)


def file_timeout(path: str) -> int:
    """Délai pour compiler CE fichier : un fichier qui importe Mathlib charge la bibliothèque (plusieurs minutes à froid sur certains disques)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(2000)
    except OSError:
        return lean_timeout()
    return max(lean_timeout(), 900) if re.search(r"^\s*import\s+Mathlib", head, re.MULTILINE) else lean_timeout()


def _kill_tree(p):
    """Tue le processus ET ses enfants. Sous Windows, 'lake' lance 'lean.exe' comme enfant : tuer seulement 'lake' laisserait Lean tourner
    en arrière-plan, saturer le processeur et faire dépasser le délai aux tentatives suivantes."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        p.kill()


def run_with_timeout(cmd, cwd=None, timeout=120):
    """Exécute une commande avec un délai ; au dépassement, tue toute l'arborescence. Retourne (code, stdout, stderr, dépassé)."""
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", cwd=cwd, **kw)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err, False
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        return None, out or "", err or "", True


_SLOW_WARNED = [False]


def lean_mode_banner() -> str:
    if LEAN_IMPORT:
        return (f"🔧 Lean avec « {LEAN_IMPORT} » : chaque compilation charge la bibliothèque, ce qui est LENT (délai {lean_timeout()} s). "
                "Ce projet n'en a pas besoin : mettez \"lean_import\": \"\" dans projet_pm.json et ne définissez pas LEAN_IMPORT.")
    return f"🔧 Lean de base, sans Mathlib (rapide ; délai {lean_timeout()} s par compilation)."


def run_lean(path: str, timeout=None) -> dict:
    t_start = time.monotonic()
    try:
        code, out, err, timed_out = run_with_timeout(["lake", "env", "lean", os.path.abspath(path)], cwd=LEAN_PROJECT_DIR,
                                                    timeout=timeout or file_timeout(path))
    except (FileNotFoundError, NotADirectoryError):
        print("⚠️  Commande 'lake' ou dossier de projet introuvable. Installez Lean via elan, "
              f"créez le projet Mathlib ({LEAN_PROJECT_DIR}) et rouvrez PowerShell.")
        sys.exit(1)
    if timed_out:
        return {"ok": False, "output": "Timeout Lean : preuve ou calcul trop long."}
    duree = time.monotonic() - t_start
    if duree > 60 and not _SLOW_WARNED[0]:
        _SLOW_WARNED[0] = True
        print(f"⏱️  Une compilation Lean a pris {duree:.0f} s. " + ("Cause probable : « " + LEAN_IMPORT + " » est chargé à chaque compilation." if LEAN_IMPORT
              else "Fermez les processus lean.exe restés ouverts et les applications lourdes."))
    output = (out + "\n" + err).strip()
    has_error = code != 0 or "error" in output.lower()
    has_sorry = "sorry" in output.lower()  # warning 'declaration uses sorry' ou sorryAx
    return {"ok": not has_error and not has_sorry, "output": output}


def locate_slow(spec: dict, impl: str, lemmas: str, proofs: list, per_timeout: int = 45) -> list:
    """Après un dépassement de délai, cherche QUELLE partie est lente : une compilation par théorème, les autres preuves étant remplacées
    par 'sorry' (fichier de diagnostic uniquement). Retourne les noms des parties lentes."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "_timeout_probe.lean")

    def slow(variant_proofs) -> bool:
        with open(path, "w", encoding="utf-8") as f:
            f.write(assemble(spec, impl, lemmas, variant_proofs))
        return "Timeout" in run_lean(path, timeout=per_timeout)["output"]

    if slow(["sorry"] * len(proofs)):
        return ["l'implémentation ou les lemmes auxiliaires (avant tout théorème)"]
    found = []
    for k, t in enumerate(spec["theorems"]):
        variant = ["sorry"] * len(proofs)
        variant[k] = proofs[k]
        if slow(variant):
            found.append(t["name"])
        if len(found) >= 3:
            break
    return found


def timeout_message(slow_parts: list) -> str:
    where = ("Parties lentes identifiées : " + ", ".join(slow_parts) + ". ") if slow_parts else ""
    return (f"Délai dépassé ({lean_timeout()} s) : Lean n'a pas terminé. {where}Causes fréquentes : `decide` ou `decide +kernel` sur un terme trop gros ou "
            "contenant Nat.sqrt ; `simp` ou `omega` qui bouclent sur de grands nombres ; énumération de très nombreux cas. Remplace ces tactiques "
            "par un raisonnement symbolique : lemmes, `generalize` des termes lourds, omega sur des variables. N'évalue jamais Nat.sqrt sur de "
            "grands littéraux, et n'énumère jamais les 257 cases de la table à la main.")


# ---------- Boucle principale ----------

def run_pipeline(requirements_path: str):
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = f.read().strip()
    return prove_requirements(requirements, "Verified")


_ERR_RE = re.compile(r"^(?P<file>[^\n]*?\.lean):(?P<line>\d+):(?P<col>\d+): (?P<kind>error|warning)", re.MULTILINE)


def annotate_errors(source: str, output: str, max_items: int = 8) -> str:
    """Ajoute à la sortie de Lean le code des lignes en erreur. Les numéros de ligne désignent le fichier assemblé,
    que le LLM n'a jamais sous les yeux tel quel : sans ce rappel, il corrige souvent la mauvaise ligne."""
    lines = source.splitlines()
    seen, notes = set(), []
    for m in _ERR_RE.finditer(output):
        if m.group("kind") != "error":
            continue
        ln, col = int(m.group("line")), int(m.group("col"))
        if (ln, col) in seen or not (1 <= ln <= len(lines)):
            continue
        seen.add((ln, col))
        ctx = [f"{k:4d}{'>' if k == ln else ' '}| {lines[k - 1]}" for k in range(max(1, ln - 1), min(len(lines), ln + 1) + 1)]
        notes.append(f"Erreur en ligne {ln}, colonne {col} :\n" + "\n".join(ctx))
        if len(notes) >= max_items:
            break
    if not notes:
        return output
    return output + "\n\nCODE CONCERNÉ PAR LES ERREURS (numéros de ligne du fichier compilé) :\n" + "\n\n".join(notes)


_BAD_NAME_RES = [re.compile(r"Unknown (?:constant|identifier) `([^`]+)`"), re.compile(r"Function expected at\s+([^\s()]+)")]


def rejected_names(output: str) -> set:
    """Noms de lemmes que Lean a rejetés (inexistants, ou employés comme des fonctions alors qu'ils n'en sont pas)."""
    names = set()
    for rx in _BAD_NAME_RES:
        for m in rx.finditer(output):
            n = m.group(1).strip("`.,;:")
            if n and "." in n or (n and n[0].isalpha() and "_" in n):  # noms de lemmes, pas de variables locales
                names.add(n)
    return names


_ERROR_TIPS = [
    (r"must not contain free variables",
     "`decide +kernel` ne doit PAS suivre un `intro` : écris `theorem T : ∀ i, i < 257 → ... := by decide +kernel`, directement sur l'énoncé complet (ou ajoute `+revert`)."),
    (r"maximum recursion depth",
     "Ne fais pas `simp`, `norm_num` ni `omega` sur une grosse liste de littéraux (comme TBL) : prouve ces faits par `decide +kernel`, ou fais précéder le lemme de `set_option maxRecDepth 100000 in`."),
    (r"Timeout Lean|Délai dépassé", "Lean a dépassé le délai : évite decide/simp/omega sur de gros termes (Nat.sqrt, grands littéraux, listes de 257 valeurs) ; raisonne par lemmes."),
    (r"unknown tactic", "Une tactique de ton code n'existe pas en Lean de base (set, nlinarith, linarith, positivity, norm_num, ring, interval_cases, use, lift, tauto, aesop, "
                        "field_simp : elles viennent de Mathlib). Disponibles : omega, simp, decide, cases, rcases, obtain, induction, constructor, exact, apply, rw, unfold, split, "
                        "generalize, push_cast, norm_cast, exact_mod_cast."),
    (r"Unknown identifier `(pow_succ|pow_zero|sq_nonneg|mul_nonneg|mul_self_nonneg|le_trans|abs_le|le_min|min_le_left|Monoid\.npow)",
     "Ce lemme est un nom de Mathlib : il n'existe pas en Lean de base. N'essaie pas de démontrer des faits sur les carrés (a^2 >= 0, a^2 = a*a) ni sur Int.toNat : "
     "les théorèmes n'en ont pas besoin. Utilise omega, ou la version à préfixe Int./Nat. si elle existe."),
    (r"No goals to be solved", "Une tactique est en trop après la fermeture du but : supprime la ligne signalée."),
    (r"Eq\.symm \(Nat\.div_add_mod|Nat\.div_add_mod|Nat\.mod_add_div",
     "Pour les faits sur `/` et `%` par une constante littérale, utilise `omega` : il les comprend directement, sans lemme Nat.div_add_mod."),
    (r"omega could not prove",
     "omega ne traite que l'arithmétique linéaire, avec `/` et `%` par des littéraux : généralise les produits non linéaires (`generalize`) et fournis leurs bornes comme hypothèses."),
    (r"expected 'by' or 'from'", "Dans un `have`, écris `have h : énoncé := by ...` : le signe `=` ne peut pas suivre directement `have h`."),
    (r"Application type mismatch", "Un argument n'a pas le type attendu : regarde le type « expected » dans le message, et remplace l'argument (ou utilise `omega`)."),
]


# Tactiques ABSENTES de Lean 4 de base (testées sur Lean 4.35) : elles viennent de Mathlib. push_cast, norm_cast, exact_mod_cast, obtain,
# rcases, omega, decide, generalize, simp existent bien.
MATHLIB_ONLY_TACTICS = ("set", "nlinarith", "linarith", "positivity", "norm_num", "ring", "interval_cases", "use", "lift", "tauto", "aesop", "field_simp")
_TACTIC_FIXES = {"set": "remplace `set x := e with h` par `generalize h : e = x` (ou `obtain ⟨x, h⟩ : ∃ x, x = e := ⟨e, rfl⟩`)",
                 "nlinarith": "génère le produit à la main (Int.mul_nonneg, Int.mul_le_mul_of_nonneg_left) puis omega",
                 "linarith": "utilise omega", "positivity": "utilise Int.natCast_nonneg ou Int.mul_nonneg", "norm_num": "utilise omega, simp ou decide",
                 "ring": "utilise omega, ou Int.mul_comm / Int.add_comm", "interval_cases": "utilise omega, ou decide +kernel sur l'énoncé ∀",
                 "use": "écris `exact ⟨valeur, preuve⟩`", "lift": "utilise Int.toNat_of_nonneg", "tauto": "utilise constructor, cases et omega",
                 "aesop": "utilise simp, cases et omega", "field_simp": "inutile sur des entiers : utilise omega"}


def mathlib_only_tactics(source: str) -> dict:
    """Retrouve, dans le code Lean, les tactiques qui n'existent pas en Lean de base : {nom: [numéros de ligne]}."""
    found = {}
    rx = re.compile(r"(?<![\w.'])(" + "|".join(MATHLIB_ONLY_TACTICS) + r")(?![\w'])")
    for n, line in enumerate(source.splitlines(), 1):
        code = re.sub(r"--.*$", "", line)
        for m in rx.finditer(code):
            found.setdefault(m.group(1), []).append(n)
    return found


def error_tips(output: str, source: str = "", max_items: int = 5) -> str:
    """Conseils ciblés pour les erreurs Lean fréquentes (le modèle les répète sinon, tentative après tentative)."""
    tips = []
    if not LEAN_IMPORT and "unknown tactic" in output and source:    # le plus utile : NOMMER la tactique fautive et donner son remplacement
        for name, lines in mathlib_only_tactics(source).items():
            tips.append(f"La tactique `{name}` n'existe PAS en Lean de base (lignes {', '.join(map(str, lines[:6]))} du fichier compilé) : {_TACTIC_FIXES[name]}.")
    tips += [tip for rx, tip in _ERROR_TIPS if re.search(rx, output)]
    return ("\n\nCONSEILS POUR CES ERREURS :\n- " + "\n- ".join(tips[:max_items])) if tips else ""


def _try_reference(spec: dict, name: str, requirements: str) -> bool:
    """Adopte la solution de référence <REFERENCE_DIR>/<name>.lean si Lean l'accepte pour CETTE spec (tous les énoncés présents, aucun sorry,
    aucune erreur). C'est une preuve fournie d'avance, pas produite par Claude : le journal et le rapport l'indiquent."""
    if not REFERENCE_DIR:
        return False
    path = os.path.join(REFERENCE_DIR, f"{name}.lean")
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    missing = [t["name"] for t in spec["theorems"] if t["statement"] not in source]
    if missing:
        print(f"📚 Solution de référence {path} ignorée : elle ne contient pas les énoncés de la spec courante ({', '.join(missing)}).")
        return False
    if check_forbidden(source):
        return False
    lean_path = os.path.join(OUTPUT_DIR, f"{name}.lean")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(lean_path, "w", encoding="utf-8") as f:
        f.write(source)
    result = run_lean(lean_path)
    if not result["ok"]:
        print(f"📚 Solution de référence {path} rejetée par Lean : {result['output'][:300]}")
        return False
    LAST_RUN.update(ok=True, rounds=0, provers=["référence (fournie)"], spec=spec,
                    axioms=[l for l in result["output"].splitlines() if "depends on axioms" in l])
    _save_run_info(name)
    print(f"📚 Solution de référence adoptée ({path}) : vérifiée par Lean sur la spec courante, aucune tentative supplémentaire de Claude.")
    return True


def _save_run_info(name: str):
    """Écrit lean_out/<name>_proof.json : trace de la preuve, utilisée par les rapports."""
    try:
        with open(os.path.join(OUTPUT_DIR, f"{name}_proof.json"), "w", encoding="utf-8") as f:
            json.dump(LAST_RUN, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_stored(requirements: str, name: str):
    """Teste si la preuve stockée de <name> est réutilisable. Retourne (True, "") après revérification par Lean, sinon (False, raison)."""
    pj = os.path.join(OUTPUT_DIR, f"{name}_proof.json")
    lean_path = os.path.join(OUTPUT_DIR, f"{name}.lean")
    spec_path = os.path.join(OUTPUT_DIR, f"{name}_spec.json")
    if not all(os.path.isfile(x) for x in (pj, lean_path, spec_path)):
        return False, "aucun résultat stocké"
    try:
        with open(pj, "r", encoding="utf-8") as f:
            stored = json.load(f)
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        with open(lean_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, ValueError):
        return False, "fichiers stockés illisibles"
    if not stored.get("ok"):
        return False, "la dernière exécution n'a pas abouti (preuve non validée)"
    ctx = stored.get("context_key")
    if ctx is None:        # résultat produit par une version antérieure : acceptable seulement hors bibliothèque (le fichier est revérifié par Lean)
        if LIBRARY_SRC:
            return False, "contexte inconnu avec une bibliothèque"
    elif ctx != _sha(LEAN_IMPORT + "\x00" + LIBRARY_SRC):
        return False, "le contexte a changé (ligne d'import Lean ou bibliothèque des modules)"
    fixed = imposed_spec(requirements)
    if fixed is not None:
        if fixed != spec:
            return False, "la spec imposée des requirements a changé"
    elif stored.get("req_key") != _sha(requirements):
        return False, "les requirements ont changé"
    missing = [t["name"] for t in spec.get("theorems", []) if t["statement"] not in source]
    if missing:
        return False, f"le fichier Lean stocké ne contient pas les énoncés : {', '.join(missing)}"
    result = run_lean(lean_path)
    if not result["ok"]:
        why = "Lean a dépassé le délai de vérification" if "Timeout Lean" in result["output"] else "Lean rejette le fichier stocké"
        return False, why + (" (machine surchargée ? fermez les 'lean.exe' restés ouverts)" if "délai" in why else "")
    LAST_RUN.clear()
    LAST_RUN.update(stored)
    print(f"♻️  Module {name} : preuve déjà validée (spec inchangée), revérifiée par Lean : réutilisée, aucun appel à Claude.")
    return True, ""


_START_RE = re.compile(r"^(@\[|/--|/-|--|private\s|protected\s|noncomputable\s|partial\s|unsafe\s|def\s|theorem\s|lemma\s|abbrev\s|instance\s|"
                       r"structure\s|inductive\s|class\s|example\s|#|set_option\s|open\s|namespace\s|section\b|end\b|variable\s|import\s)")


def _toplevel_blocks(text: str) -> list:
    blocks, cur = [], []
    for line in text.splitlines():
        if _START_RE.match(line) and cur and not all(l.strip().startswith(("--", "/-", "@[")) or not l.strip() for l in cur):
            blocks.append("\n".join(cur).rstrip())
            cur = []
        cur.append(line)
    if cur:
        blocks.append("\n".join(cur).rstrip())
    return blocks


def _recover_from_vectors(name: str, spec: dict, requirements: str) -> bool:
    """Reconstruit la preuve validée à partir du fichier de vecteurs : mbd_out/<name>/Model_vectors.lean commence par le code du modèle
    prouvé, suivi du programme de vecteurs. Utile quand lean_out/<name>.lean a été écrasé par une régénération qui a échoué."""
    mbd = "mbd_out" if name == "Model" else os.path.join("mbd_out", name)
    vpath = os.path.join(mbd, "Model_vectors.lean")
    if not os.path.isfile(vpath) or not spec.get("theorems"):
        print(f"   (récupération de {name} impossible : pas de fichier {vpath})")
        return False
    with open(vpath, "r", encoding="utf-8") as f:
        blocks = _toplevel_blocks(f.read())
    last = spec["theorems"][-1]["name"]
    idx = next((i for i, b in enumerate(blocks) if re.match(rf"theorem\s+{re.escape(last)}\b", b.lstrip())), None)
    if idx is None:
        print(f"   (récupération de {name} impossible : le théorème {last} est introuvable dans {vpath} : il a été prouvé pour une spec différente)")
        return False
    source = "\n\n".join(blocks[:idx + 1]).rstrip() + "\n\n" + "\n".join(f"#print axioms {t['name']}" for t in spec["theorems"]) + "\n"
    missing = [t["name"] for t in spec["theorems"] if t["statement"] not in source]
    if missing:
        print(f"   (récupération de {name} impossible : les énoncés de la spec actuelle diffèrent de ceux de la preuve stockée : {', '.join(missing)})")
        return False
    lean_path = os.path.join(OUTPUT_DIR, f"{name}.lean")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    uses_mathlib = bool(re.search(r"^\s*import\s+Mathlib", source, re.MULTILINE))
    core_source = re.sub(r"^\s*import\s+\S+[ \t]*\n", "", source, flags=re.MULTILINE)
    if uses_mathlib and not LEAN_IMPORT:
        # mode de base : la preuve a-t-elle vraiment besoin de Mathlib ? On essaie d'abord SANS l'import (compilation en quelques secondes).
        with open(lean_path, "w", encoding="utf-8") as f:
            f.write(core_source)
        if run_lean(lean_path)["ok"]:
            source, uses_mathlib = core_source, False
            print(f"   (la preuve de {name} n'a pas besoin de Mathlib : import retiré, compilation rapide)")
    with open(lean_path, "w", encoding="utf-8") as f:
        f.write(source)
    result = run_lean(lean_path, timeout=max(lean_timeout(), 900) if uses_mathlib else None)   # un fichier qui importe Mathlib peut être très lent
    if not result["ok"]:
        raison = "délai dépassé" if "Timeout Lean" in result["output"] else "Lean rejette le fichier reconstruit"
        print(f"   (récupération de {name} impossible : {raison}" + (" ; le fichier importe Mathlib, très lent sur cette machine" if uses_mathlib else "")
              + f". Début de la sortie : {result['output'][:200]!r})")
        return False
    run = dict(name=name, ok=True, rounds=0, provers=["récupérée depuis les vecteurs (déjà validée)"], spec=spec, requirements=requirements,
               axioms=[l for l in result["output"].splitlines() if "depends on axioms" in l],
               context_key=_sha(LEAN_IMPORT + "\x00" + LIBRARY_SRC), req_key=_sha(requirements))
    with open(os.path.join(OUTPUT_DIR, f"{name}_spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUTPUT_DIR, f"{name}_proof.json"), "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=2)
    print(f"🛟 Module {name} : preuve validée récupérée depuis mbd_out (elle avait été écrasée), revérifiée par Lean.")
    return True


def _try_reuse_proof(requirements: str, name: str) -> bool:
    """Réutilise une preuve déjà validée, sans appel à Claude, après revérification locale par Lean. Dit toujours pourquoi elle ne l'est pas."""
    if FORCE:
        return False
    ok, why = _check_stored(requirements, name)
    if ok:
        return True
    fixed = imposed_spec(requirements)
    if fixed is not None and _recover_from_vectors(name, fixed, requirements):
        ok2, why2 = _check_stored(requirements, name)
        if ok2:
            return True
        why = why2
    if why != "aucun résultat stocké":
        print(f"ℹ️  Module {name} : résultat stocké non réutilisé ({why}) : la preuve sera regénérée.")
    return False


_BACKUP_SUFFIXES = (".lean", "_spec.json", "_proof.json")


def _backup_valid(name: str):
    """Garde en mémoire la preuve actuellement validée, pour la restaurer si une régénération échoue."""
    try:
        with open(os.path.join(OUTPUT_DIR, f"{name}_proof.json"), "r", encoding="utf-8") as f:
            if not json.load(f).get("ok"):
                return None
        return {suf: open(os.path.join(OUTPUT_DIR, f"{name}{suf}"), "r", encoding="utf-8").read() for suf in _BACKUP_SUFFIXES}
    except (OSError, ValueError):
        return None


def _restore_valid(name: str, backup: dict):
    for suf, content in backup.items():
        with open(os.path.join(OUTPUT_DIR, f"{name}{suf}"), "w", encoding="utf-8") as f:
            f.write(content)


def prove_requirements(requirements: str, name: str = "Verified", library_src=None) -> bool:
    """Formalise des requirements, fait valider la spec, puis lance la boucle de preuve. Si une preuve validée existait et que la nouvelle
    tentative échoue (ou est interrompue), l'ancienne preuve est restaurée : un échec ne détruit jamais un résultat valide."""
    global LIBRARY_SRC
    if library_src is not None:
        LIBRARY_SRC = library_src
    backup = _backup_valid(name)
    ok = False
    try:
        ok = _prove_requirements(requirements, name)
        return ok
    finally:
        if not ok and backup:
            _restore_valid(name, backup)
            print(f"🛟 Module {name} : la preuve précédemment validée a été restaurée (la nouvelle tentative n'a pas abouti).")


def _prove_requirements(requirements: str, name: str) -> bool:
    """Formalise des requirements (texte), fait valider la spec, puis lance la boucle de preuve.
    Écrit lean_out/<name>.lean. Retourne True si Lean a validé tous les théorèmes."""
    ensure_lean_project()
    if _try_reuse_proof(requirements, name):
        return True
    LAST_RUN.clear()
    LAST_RUN.update(name=name, ok=False, rounds=0, provers=[], axioms=[], requirements=requirements,
                    context_key=_sha(LEAN_IMPORT + "\x00" + LIBRARY_SRC), req_key=_sha(requirements))
    print("🧠 Claude écrit la spécification formelle...")
    spec = write_spec(requirements)

    spec_errors = check_spec_compiles(spec)  # contrôle 1 : la spec est-elle bien formée pour Lean ?
    for _ in range(3):
        if not spec_errors:
            break
        print("⚠️  La spec ne compile pas, correction demandée à Claude. Erreur Lean :")
        print(spec_errors[:600])
        try:
            spec = fix_spec(requirements, spec, spec_errors)
        except ValueError as e:
            print(f"⚠️  Correction automatique impossible ({e}). Vous pourrez corriger la spec vous-même (option e).")
            break
        spec_errors = check_spec_compiles(spec)

    print("🔍 Audit critique de la spec...")  # contrôle 2 : la spec dit-elle assez ?
    audit = audit_spec(requirements, spec, brief=imposed_spec(requirements) is not None)
    if spec_errors:
        audit = ("⚠️  ATTENTION : cette spec ne compile toujours pas. Éditez-la (option e) avant de valider.\n"
                 + spec_errors[:800] + "\n\n" + audit)
    spec = validate_spec_with_user(spec, os.path.join(OUTPUT_DIR, f"{name}_spec.json"), audit)
    if spec is None:
        print("Module ignoré (spec refusée).")
        return False

    lean_path = os.path.join(OUTPUT_DIR, f"{name}.lean")
    previous, errors, prev_errors = "", "", None
    bad_names = set()
    attempt_tokens = 8000   # longueur maximale d'une réponse de preuve ; doublée si une réponse est tronquée

    reference_tried = False
    for round_no in range(1, MAX_ROUNDS + 1):
        if REFERENCE_DIR and not reference_tried and round_no == REFERENCE_AFTER + 1:
            reference_tried = True
            if _try_reference(spec, name, requirements):
                return True
        prover = "qwen" if (round_no <= QWEN_ROUNDS and not LIBRARY_SRC) else "claude"
        print(f"\n--- Tentative {round_no}/{MAX_ROUNDS} (prouveur : {prover}) ---")

        set_stage(f"preuve {round_no}/{MAX_ROUNDS}")
        prompt = build_attempt_prompt(spec, previous, errors, prover, stagnating=bool(errors) and errors == prev_errors,
                                      requirements=requirements, bad_names=bad_names)
        if prover == "qwen":
            reply = ask_qwen(prompt)
            if reply is None:
                print("↪️  Qwen indisponible : cette tentative est confiée à Claude.")
                prover = "claude"
        if prover == "claude":
            reply = ask_claude(prompt, max_tokens=attempt_tokens)

        LAST_RUN["rounds"] = round_no
        LAST_RUN["provers"].append(prover)
        previous = reply          # ce que le LLM verra comme "tentative précédente"
        prev_errors = errors      # pour détecter une stagnation
        impl, lemmas, proofs = parse_attempt(reply, len(spec["theorems"]))
        if impl is None:
            errors = diagnose_reply(reply, len(spec["theorems"]))
            print(f"⚠️  Réponse inutilisable : {errors}")
            note_outcome("réponse inutilisable : " + errors)
            try:   # on garde la réponse brute pour comprendre ce qui s'est passé
                with open(os.path.join(OUTPUT_DIR, f"{name}_reponse_invalide.txt"), "w", encoding="utf-8") as fbad:
                    fbad.write(reply)
            except OSError:
                pass
            if LAST_STOP.get("reason") == "max_tokens":
                attempt_tokens = min(16000, attempt_tokens * 2)
            continue

        everything = impl + "\n" + lemmas + "\n" + "\n".join(proofs)
        banned = check_forbidden(everything)
        if banned:
            errors = f"Mot interdit utilisé : '{banned}'. Écris une vraie preuve."
            print(f"🚫 Triche détectée ('{banned}'), tentative rejetée.")
            note_outcome(f"rejetée avant Lean : mot interdit '{banned}'")
            continue

        clash = find_redeclared(spec, everything)
        if clash:
            errors = f"Tu as redéclaré le théorème imposé '{clash}' : ne mets que sa preuve dans ### PROOF, et donne d'autres noms à tes lemmes."
            print(f"🚫 Théorème imposé redéclaré ('{clash}'), tentative rejetée.")
            note_outcome(f"rejetée avant Lean : théorème '{clash}' redéclaré")
            continue

        fn_name = signature_name(spec["signature"])
        if fn_name and not re.search(rf"\bdef\s+{re.escape(fn_name)}\b", impl):
            errors = (f"Tu dois définir la fonction `{fn_name}` dans ### IMPL avec `def {fn_name}` "
                      f"(type attendu : {spec['signature']}). Tu peux la définir par filtrage de motifs "
                      f"et ajouter des fonctions auxiliaires.")
            print(f"🚫 Fonction `{fn_name}` non définie, tentative rejetée.")
            note_outcome(f"rejetée avant Lean : fonction {fn_name} non définie")
            continue

        source = assemble(spec, impl, lemmas, proofs)
        with open(lean_path, "w", encoding="utf-8") as f:
            f.write(source)

        result = run_lean(lean_path)
        if "Timeout Lean" in result["output"]:
            print(f"⏱️  Délai de {lean_timeout()} s dépassé : recherche de la partie lente...")
            slow_parts = locate_slow(spec, impl, lemmas, proofs)
            print("   Parties lentes :", ", ".join(slow_parts) or "non identifiées")
            result["output"] += "\n" + timeout_message(slow_parts)
        previous, errors = source, annotate_errors(source, result["output"]) + error_tips(result["output"], source)
        bad_names |= rejected_names(result["output"])

        if result["ok"]:
            LAST_RUN.update(ok=True, spec=spec, axioms=[l for l in result["output"].splitlines() if "depends on axioms" in l])
            _save_run_info(name)
            note_outcome("PREUVE ACCEPTÉE par Lean")
            print(f"\n✅ PREUVE RÉUSSIE : Lean a vérifié tous les théorèmes ({lean_path})")
            print(result["output"])
            return True

        first_err = next((l.split(": ", 2)[-1] for l in result["output"].splitlines() if ": error" in l),
                         "délai dépassé" if "Timeout Lean" in result["output"] else "erreur")
        n_err = sum(1 for l in result["output"].splitlines() if ": error" in l)
        note_outcome(f"Lean : {n_err} erreur(s), première : {first_err}")
        print("❌ Lean a rejeté la tentative :")
        print(result["output"][:800])

    LAST_RUN.update(spec=spec)
    _save_run_info(name)
    print(f"\n⚠️  Pas de convergence après {MAX_ROUNDS} tentatives. Dernière version : {lean_path}")
    return False


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Variable ANTHROPIC_API_KEY non définie.")
        sys.exit(1)
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        print("Usage : python agent_lean_v5.py requirements.txt")
        sys.exit(1)
    run_pipeline(sys.argv[1])
