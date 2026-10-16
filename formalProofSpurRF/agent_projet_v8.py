"""
Agent de projet v8 : de la spécification à des rapports PDF complets.

Pour un projet décrit dans un fichier JSON (voir projet_pm.json), l'agent enchaîne :
  1. chaque module : spec formelle -> modèle Lean prouvé -> vecteurs -> code C -> validation (agent_mbd_v7.py)
  2. l'intégration : les modules prouvés forment une bibliothèque Lean, Claude écrit la fonction d'intégration et ses
     théorèmes, qui sont prouvés à leur tour ; puis vecteurs, C d'intégration (qui réutilise les C des modules), validation
  3. les tests système : le C d'intégration est exécuté sur des signaux synthétiques de grande taille, comparé au prototype
     Python indépendant (identité au bit près) et le niveau de raie résiduelle est mesuré
  4. les rapports PDF (agent_rapport.py) : spec système, stratégie Lean, valeurs attendues, C généré, rapport de test

Réutilisation (rien n'est refait inutilement) : à chaque lancement, une preuve déjà validée est revérifiée par Lean, les vecteurs sont
recalculés par Lean et recontrôlés par l'oracle, le C existant est recompilé et reconfronté aux vecteurs. Seul ce qui échoue ou a changé
est regénéré par Claude. Une spec imposée inchangée n'est pas revalidée à la main.

Utilisation :
  python agent_projet_v8.py projet_pm.json            # tout le projet (réutilise ce qui est valide)
  python agent_projet_v8.py projet_pm.json --redo cossin,correlate   # refait entièrement ces modules
  python agent_projet_v8.py projet_pm.json --force    # refait tout, en ignorant les résultats existants
  python agent_projet_v8.py projet_pm.json --use-references   # autorise les preuves de référence en repli (par défaut : Claude seul)
  python agent_projet_v8.py projet_pm.json --resume   # saute les modules déjà validés (result.json existant)
  python agent_projet_v8.py projet_pm.json --pdf-only # reconstruit seulement les PDF à partir des résultats existants

Les fichiers sont produits dans le dossier courant : lean_out/, mbd_out/<module>/, rapport/.
Prérequis : ceux de agent_mbd_v7.py, plus  pip install reportlab matplotlib numpy
"""

import argparse
import json
import os
import re
import subprocess
import sys

import agent_lean_v5 as v5
import agent_mbd_v7 as v7

AGENT_VERSION = "2026-10-15.5"   # les trois scripts agent_*.py doivent porter le même numéro


def check_versions():
    """Vérifie que agent_lean_v5.py, agent_mbd_v7.py et agent_projet_v8.py viennent du même lot : un mélange d'anciennes et de nouvelles
    versions produit des erreurs incompréhensibles. S'arrête avec la liste des fichiers à remplacer."""
    stale = [(name, getattr(mod, "AGENT_VERSION", "ancienne version, sans numéro"))
             for name, mod in (("agent_lean_v5.py", v5), ("agent_mbd_v7.py", v7)) if getattr(mod, "AGENT_VERSION", None) != AGENT_VERSION]
    if stale:
        print(f"\n⛔ Fichiers de versions différentes (agent_projet_v8.py est en {AGENT_VERSION}) :")
        for name, ver in stale:
            print(f"   - {name} : {ver} -> à remplacer par la dernière version livrée")
        print("   Remplacez-les, puis relancez. Rien n'a été modifié.")
        sys.exit(1)

REPORT_DIR = "rapport"


# ---------- Fusion des modules Lean en une bibliothèque ----------

_DECL_RE = re.compile(r"^(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable|partial|unsafe)\s+)*"
                      r"(def|theorem|lemma|abbrev|instance|structure|inductive|class)\s+([^\s(:\[{]+)")
_START_RE = re.compile(r"^(@\[|/--|/-|--|private\s|protected\s|noncomputable\s|partial\s|unsafe\s|def\s|theorem\s|lemma\s|"
                       r"abbrev\s|instance\s|structure\s|inductive\s|class\s|example\s|#|set_option\s|open\s|namespace\s|"
                       r"section\b|end\b|variable\s|import\s)")
_PREFIX_ONLY = re.compile(r"^(?:(?:/--.*?-/|@\[[^\]]*\])\s*)+$", re.DOTALL)


def _strip_comments(text: str) -> str:
    text = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", text)


def _norm(block: str) -> str:
    return re.sub(r"\s+", " ", _strip_comments(block)).strip()


def parse_blocks(src: str):
    """Découpe un fichier Lean en blocs de premier niveau (déclarations, avec leurs commentaires de doc)."""
    blocks, cur = [], []

    def flush():
        text = "\n".join(cur).strip("\n")
        if text.strip():
            blocks.append(text)
        cur.clear()

    for line in src.splitlines():
        if _START_RE.match(line) and not _PREFIX_ONLY.match("\n".join(cur).strip() or "x"):
            flush()
        cur.append(line)
    flush()
    return blocks


def _decl_name(block: str):
    body = _strip_comments(block).strip()
    body = re.sub(r"^(?:/--.*?-/\s*)+", "", body, flags=re.DOTALL)
    m = _DECL_RE.match(body)
    return m.group(2) if m else None


def _apply_rename(block: str, rename: dict) -> str:
    for old, new in rename.items():
        block = re.sub(rf"(?<![\w.'])" + re.escape(old) + r"(?![\w'])", new, block)
    return block


def merge_lean_modules(named_sources):
    """Fusionne plusieurs modules Lean en une bibliothèque : retire les imports et #print, supprime les définitions identiques
    en double, renomme (préfixe du module) les noms en conflit dont le contenu diffère. Retourne (texte, notes)."""
    seen, out, notes = {}, [], []
    for mod, src in named_sources:
        blocks = []
        for b in parse_blocks(src):
            first = _strip_comments(b).strip()
            if first.startswith(("import", "#print", "#eval", "#check", "example")) or not first:
                continue
            if first.startswith(("namespace", "section", "end")):
                raise ValueError(f"module {mod} : 'namespace'/'section' non pris en charge par la fusion")
            blocks.append(b)
        rename = {}
        for _ in range(6):  # itère jusqu'à stabilité (un renommage peut en entraîner d'autres)
            changed = False
            for b in blocks:
                name = _decl_name(b)
                if name and name not in rename and name in seen and seen[name] != _norm(_apply_rename(b, rename)):
                    rename[name] = f"{mod}_{name}"
                    changed = True
            if not changed:
                break
        for b in blocks:
            b2 = _apply_rename(b, rename)
            name2 = _decl_name(b2)
            if name2 and name2 in seen:
                if seen[name2] == _norm(b2):
                    continue
                raise ValueError(f"conflit de nom persistant pour '{name2}' (module {mod})")
            if name2:
                seen[name2] = _norm(b2)
            out.append(b2)
        if rename:
            notes.append(f"module {mod} : noms renommés pour éviter un conflit : {rename}")
    return "\n\n".join(out), notes


# ---------- Tests système ----------

SPECTRUM_LABELS = {
    "fr": dict(before="avant correction", after="après correction", x="indice de bin (la raie est à ±%d)", y="niveau (dBc)"),
    "en": dict(before="before correction", after="after correction", x="bin index (the spur is at ±%d)", y="level (dBc)"),
}


def render_spectrum(npz_path: str, png_path: str, lang: str):
    """Dessine le spectre avant/après correction à partir des données sauvegardées, avec les légendes dans la langue demandée."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = np.load(npz_path)
    n, cycles, lab = int(d["n"]), int(d["cycles"]), SPECTRUM_LABELS[lang]
    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    for key, col in (("before", "#b3261e"), ("after", "#1b7f3b")):
        ax.plot(np.arange(-n // 2, n // 2), d[key], label=lab[key], color=col, linewidth=0.8)
    ax.set_xlim(-6 * cycles, 6 * cycles)
    ax.set_ylim(-110, 5)
    ax.set_xlabel(lab["x"] % cycles)
    ax.set_ylabel(lab["y"])
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=160)
    plt.close(fig)
    return png_path


def _run_harness(exe: str, lines: list, timeout=600):
    r = subprocess.run([os.path.abspath(exe)], input="\n".join(lines) + "\n", capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"le harnais s'est terminé avec le code {r.returncode}")
    return [ln.split() for ln in r.stdout.splitlines() if ln.strip()]


def run_system_tests(cfg: dict, harness_exe: str, out_dir: str):
    """Exécute le C d'intégration sur des signaux synthétiques et le compare au prototype Python indépendant."""
    sc_cfg = cfg.get("system_tests")
    if not sc_cfg:
        return None
    try:
        import numpy as np
        import spur_pm_prototype as P
    except ImportError as e:
        print(f"⚠️  Tests système ignorés ({e}). Installez numpy et placez spur_pm_prototype.py à côté du script.")
        return None
    if not os.path.isfile(harness_exe):
        print("⚠️  Tests système ignorés : harnais d'intégration introuvable.")
        return None

    n, cycles, amp = sc_cfg.get("n", 4096), sc_cfg.get("cycles", 37), sc_cfg.get("amplitude", 24000)
    crit = sc_cfg.get("criterion_dbc", -75)
    P.N, P.M_CYC = n, cycles
    delta = (cycles * 2 ** 32) // n
    signals, lines, expected = [], [], []
    for k, sc in enumerate(sc_cfg["scenarios"], 1):
        re_, im_ = P.make_signal(sc["beta"], sc["phi"], amp, sc["snr_db"], seed=k)
        c = P.correlate(re_, im_, delta)
        bq, ur, ui = P.estimate(c)
        o_re, o_im = P.derot_block(re_, im_, delta, ur, ui, bq)
        signals.append((re_, im_, o_re, o_im, bq))
        expected.append([str(v) for v in [bq, ur, ui, n] + o_re + [n] + o_im])
        lines.append(" ".join(map(str, [n] + re_ + [n] + im_ + [delta])))
    print(f"\n=== Tests système : {len(lines)} scénarios, blocs de {n} échantillons ===")
    try:
        outputs = _run_harness(harness_exe, lines)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"❌ {e}")
        outputs = []

    scenarios, first = [], None
    for k, sc in enumerate(sc_cfg["scenarios"]):
        re_, im_, o_re, o_im, bq = signals[k]
        got = outputs[k] if k < len(outputs) else []
        bitexact = got == expected[k]
        c_re = [int(v) for v in got[4:4 + n]] if len(got) == len(expected[k]) else o_re
        c_im = [int(v) for v in got[5 + n:5 + 2 * n]] if len(got) == len(expected[k]) else o_im
        before, proto_after = P.spur_dbc(re_, im_), P.spur_dbc(o_re, o_im)
        after = P.spur_dbc(c_re, c_im) if len(got) == len(expected[k]) else float("nan")
        beta_est = int(got[0]) / 65536 if got else float("nan")
        passed = bool(bitexact and after <= crit)
        scenarios.append(dict(id=f"T-SYS-{k + 1}", beta=sc["beta"], phi=sc["phi"], snr_db=sc["snr_db"], beta_est=beta_est,
                              spur_before_dbc=before, spur_after_dbc=after, proto_after_dbc=proto_after,
                              bitexact=bitexact, passed=passed))
        print(f"  T-SYS-{k + 1}: beta={sc['beta']} estimé {beta_est:.4f} | {before:6.1f} -> {after:6.1f} dBc | "
              f"{'identique au prototype' if bitexact else 'DIFFÉRENT du prototype'} | {'OK' if passed else 'ÉCHEC'}")
        if first is None:
            first = (re_, im_, c_re, c_im)

    figure, figure_en = None, None
    try:
        re_, im_, c_re, c_im = first
        spectra = {}
        for key, (r, i) in (("before", (re_, im_)), ("after", (c_re, c_im))):
            x = np.fft.fft(np.array(r, float) + 1j * np.array(i, float))
            spectra[key] = 20 * np.log10(np.maximum(np.abs(np.fft.fftshift(x)), 1e-9) / abs(x[0]))
        os.makedirs(out_dir, exist_ok=True)
        npz = os.path.join(out_dir, "spectres.npz")           # les données restent disponibles pour regénérer la figure dans une autre langue
        np.savez(npz, before=spectra["before"], after=spectra["after"], n=n, cycles=cycles)
        figure = render_spectrum(npz, os.path.join(out_dir, "spectres.png"), "fr")
        figure_en = render_spectrum(npz, os.path.join(out_dir, "spectres_en.png"), "en")
    except Exception as e:  # la figure est facultative
        print(f"⚠️  Figure non générée ({e}).")
    return dict(n=n, cycles=cycles, criterion_dbc=crit, scenarios=scenarios, figure=figure, figure_en=figure_en,
                criterion_text=sc_cfg.get("criterion_text", f"raie résiduelle <= {crit} dBc"))


# ---------- Collecte des résultats ----------

def _read(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return default


def _load_module(name: str, role: str, library_src: str = ""):
    mbd = "mbd_out" if name == "Model" else os.path.join("mbd_out", name)
    res_path = os.path.join(mbd, "result.json")
    result = json.loads(_read(res_path, "{}") or "{}")
    lean_src = _read(os.path.join(v5.OUTPUT_DIR, f"{name}.lean"))
    if library_src:
        lean_src = lean_src.replace(library_src, "-- (bibliothèque : définitions et théorèmes des modules précédents)")
    spec = json.loads(_read(os.path.join(v5.OUTPUT_DIR, f"{name}_spec.json"), "{}") or "{}")
    return dict(name=name, role=role, result=result, lean_src=lean_src, spec=spec,
                c_model=_read(os.path.join(mbd, "model.c")), c_harness=_read(os.path.join(mbd, "harness.c")),
                vectors_in=_read(os.path.join(mbd, "vectors_in.txt")).splitlines(),
                vectors_expected=_read(os.path.join(mbd, "vectors_expected.txt")).splitlines())


def _mbd_dir(name):
    return "mbd_out" if name == "Model" else os.path.join("mbd_out", name)


def _module_done(name) -> bool:
    res = json.loads(_read(os.path.join(_mbd_dir(name), "result.json"), "{}") or "{}")
    return bool(res.get("ok"))


# ---------- Orchestration ----------

def _set_oracle(entry: dict):
    """Branche l'oracle indépendant du module (clé "oracle" : "fichier_python:fonction") sur l'agent."""
    spec = entry.get("oracle")
    v7.ORACLE = None
    if not spec:
        return
    try:
        import importlib
        mod, fn = spec.split(":")
        v7.ORACLE = getattr(importlib.import_module(mod), fn)
    except (ImportError, AttributeError, ValueError) as e:
        print(f"⚠️  Oracle {spec} indisponible ({e}) : les vecteurs ne seront pas contrôlés par un oracle.")



def _wipe_module(name: str):
    """Met de côté tout ce qui a été produit pour un module (pour le refaire entièrement). Rien n'est supprimé : l'ancien résultat est déplacé
    dans lean_out/_sauvegardes/<module>_<date>/ ; si la nouvelle preuve échoue, vous pouvez le remettre."""
    import datetime
    import glob
    import shutil
    dest = os.path.join(v5.OUTPUT_DIR, "_sauvegardes", f"{name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(dest, exist_ok=True)
    for f in glob.glob(os.path.join(v5.OUTPUT_DIR, f"{name}.*")) + glob.glob(os.path.join(v5.OUTPUT_DIR, f"{name}_*")):
        try:
            shutil.move(f, dest)
        except OSError:
            pass
    if os.path.isdir(_mbd_dir(name)):
        shutil.move(_mbd_dir(name), os.path.join(dest, "mbd_out"))
    print(f"🧹 Module {name} : mis de côté dans {dest} ; il sera refait entièrement.")


def _mathlib_modules(cfg) -> list:
    """Modules dont le fichier Lean validé commence par « import Mathlib » (prouvés en mode Mathlib)."""
    import re
    found = []
    for m in cfg["modules"]:
        try:
            with open(os.path.join(v5.OUTPUT_DIR, f"{m['name']}.lean"), "r", encoding="utf-8") as f:
                if re.search(r"^\s*import\s+Mathlib", f.read(2000), re.MULTILINE):
                    found.append(m["name"])
        except OSError:
            pass
    return found


def run_project(cfg_path: str, resume=False, pdf_only=False, no_pdf=False, force=False, redo=(), use_references=False, languages=None, author=None, email=None):
    cfg_dir = os.path.dirname(os.path.abspath(cfg_path))
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    def path(p):
        return p if os.path.isabs(p) else os.path.join(cfg_dir, p)

    v5.FORCE = bool(force)
    default_model = v5.CLAUDE_MODEL
    known = [m["name"] for m in cfg["modules"]] + ([cfg["integration"]["name"]] if cfg.get("integration") else [])
    for n in redo:
        if n not in known:
            print(f"⚠️  --redo : module inconnu '{n}' (modules : {', '.join(known)}).")
            return False
    v5.REFERENCE_DIR = None
    if cfg.get("references") and use_references:
        ref_dir = cfg["references"] if os.path.isabs(cfg["references"]) else os.path.join(cfg_dir, cfg["references"])
        if os.path.isdir(ref_dir):
            v5.REFERENCE_DIR = ref_dir
            print(f"📚 Solutions de référence disponibles : {ref_dir} (utilisées après {v5.REFERENCE_AFTER} échec(s) de Claude par module ; "
                  "REFERENCE_AFTER=0 pour les utiliser d'emblée).")
    if "lean_import" in cfg:      # "" = Lean de base sans Mathlib (plus rapide) ; "import Mathlib" sinon
        v5.LEAN_IMPORT = cfg["lean_import"]
    print(v5.lean_mode_banner())
    if not pdf_only:
        v5.ensure_lean_project()
        # on vérifie CHAQUE modèle utilisé par le projet : le modèle par défaut et ceux demandés par certains modules (clé "model")
        used = [default_model] + [m["model"] for m in cfg["modules"] if m.get("model")] + \
               ([cfg["integration"]["model"]] if cfg.get("integration") and cfg["integration"].get("model") else [])
        for mdl in dict.fromkeys(used):
            v5.check_api(mdl)
        for m in cfg["modules"]:
            if m.get("model"):
                print(f"   (le module {m['name']} utilisera {m['model']} ; les autres, {default_model})")
        for n in redo:          # SEULEMENT après les vérifications de départ : un plantage au démarrage ne met rien de côté
            _wipe_module(n)
    if not pdf_only and not v5.LEAN_IMPORT:
        stale = [n for n in _mathlib_modules(cfg) if n not in redo]
        if stale:
            print("\n⛔ Ces modules ont été prouvés avec Mathlib : " + ", ".join(stale) + ".\n"
                  "   Le projet tourne en Lean de base (rapide) : ils ne peuvent pas être fusionnés dans la bibliothèque d'intégration (symbole ℕ, lemmes\n"
                  "   et tactiques de Mathlib). Refaites-les en Lean de base ; l'ancien résultat est conservé dans lean_out\\_sauvegardes :\n"
                  f"       python agent_projet_v8.py {os.path.basename(cfg_path)} --redo {','.join(stale)}\n"
                  "   Les autres modules validés seront réutilisés sans aucun appel à Claude.")
            return False
    modules, integ = cfg["modules"], cfg.get("integration")

    if not pdf_only:
        for m in modules:
            if resume and _module_done(m["name"]):
                print(f"⏭️  Module {m['name']} déjà validé (--resume).")
                continue
            print(f"\n################ MODULE {m['name']} ################")
            v5.LIBRARY_SRC, v7.C_CONTEXT = "", ""
            v5.CLAUDE_MODEL = m.get("model") or default_model   # clé facultative "model" : un modèle plus capable pour un module difficile
            v7.configure(m["name"])
            _set_oracle(m)
            ok = v7.run_pipeline(path(m["req"]))
            print(f"📊 Consommation cumulée : {v5.usage_summary()}")
            if not ok:
                print(f"⛔ Le module {m['name']} n'est pas validé : arrêt du projet.")
                return False

    library_src, notes = merge_lean_modules(
        [(m["name"], _read(os.path.join(v5.OUTPUT_DIR, f"{m['name']}.lean"))) for m in modules])
    for n in notes:
        print("ℹ️ ", n)

    if integ and not pdf_only and not (resume and _module_done(integ["name"])):
        print(f"\n################ INTÉGRATION {integ['name']} ################")
        check = os.path.join("mbd_out", "_library_check.lean")
        os.makedirs(os.path.dirname(check), exist_ok=True)
        with open(check, "w", encoding="utf-8") as f:
            f.write((v5.LEAN_IMPORT + "\n\n" if v5.LEAN_IMPORT else "") + library_src + "\n")
        res = v5.run_lean(check)
        if "error" in res["output"].lower():
            print("⛔ La bibliothèque fusionnée ne compile pas :\n" + res["output"][:1500])
            return False
        v5.LIBRARY_SRC = library_src
        v5.CLAUDE_MODEL = integ.get("model") or default_model
        v5.QWEN_ROUNDS = 0  # le contexte (bibliothèque) est trop long pour le modèle local
        v7.C_CONTEXT = "\n\n".join(_read(os.path.join(_mbd_dir(m["name"]), "model.c")) for m in modules)
        v7.configure(integ["name"])
        _set_oracle(integ)
        if not v7.run_pipeline(path(integ["req"])):
            print("⛔ L'intégration n'est pas validée : arrêt du projet.")
            return False

    system_tests = None
    if integ:
        exe = os.path.join(_mbd_dir(integ["name"]), "harness.exe" if os.name == "nt" else "harness")
        system_tests = run_system_tests(cfg, exe, REPORT_DIR) if not pdf_only else _cached_system_tests(cfg)
        if system_tests:
            with open(os.path.join(REPORT_DIR, "tests_systeme.json"), "w", encoding="utf-8") as f:
                json.dump(system_tests, f, ensure_ascii=False, indent=2)

    if no_pdf:
        return True
    try:
        import agent_rapport
    except ImportError as e:
        print(f"⚠️  Rapports PDF non générés ({e}). Installez reportlab et matplotlib.")
        return True
    if getattr(agent_rapport, "AGENT_VERSION", None) != AGENT_VERSION:
        print(f"\n⛔ agent_rapport.py ({getattr(agent_rapport, 'AGENT_VERSION', 'ancienne version, sans numéro')}) et agent_projet_v8.py ({AGENT_VERSION}) "
              "sont de versions différentes : remplacez agent_rapport.py par la dernière version livrée. Les résultats des modules sont conservés.")
        return False

    rep = cfg.get("report") or {}
    languages = [x for x in (languages or rep.get("languages") or ["fr"])]
    author, email = author or rep.get("author"), email or rep.get("email")
    mods = [_load_module(m["name"], m.get("role", "")) for m in modules]
    data = dict(name=cfg["name"], title=cfg["title"], overview_text=_read(path(cfg["overview"])), modules=mods,
                integration=_load_module(integ["name"], integ.get("role", ""), library_src) if integ else None,
                system_tests=system_tests, toolchain=(mods[0]["result"].get("toolchain", {}) if mods else {}),
                generated_at=(mods[0]["result"].get("generated_at") if mods else None) or "")
    # textes du projet en anglais : ceux de la configuration ; les absents sont traduits par le modèle de langage
    en = {}
    if cfg.get("title_en"):
        en["title"] = cfg["title_en"]
    if cfg.get("overview_en"):
        en["overview_text"] = _read(path(cfg["overview_en"]))
    roles = {m["name"]: m["role_en"] for m in modules + ([integ] if integ else []) if m.get("role_en")}
    if roles:
        en["roles"] = roles
    if (cfg.get("system_tests") or {}).get("criterion_text_en"):
        en["criterion_text"] = cfg["system_tests"]["criterion_text_en"]
    data["i18n"] = {"en": en}
    st_ = data.get("system_tests")
    if "en" in languages and st_ and not st_.get("figure_en"):       # anciens résultats : figure anglaise regénérée depuis les données sauvegardées
        npz = os.path.join(REPORT_DIR, "spectres.npz")
        if os.path.isfile(npz):
            try:
                st_["figure_en"] = render_spectrum(npz, os.path.join(REPORT_DIR, "spectres_en.png"), "en")
            except Exception as e:
                print(f"⚠️  Figure anglaise non générée ({e}).")
    v5.CLAUDE_MODEL = default_model
    v5.CURRENT["module"], v5.CURRENT["stage"] = "rapport", "rapport"
    print(f"\n=== Génération des PDF (langues : {', '.join(languages)}" + (f" ; auteur : {author}" if author else "") + ") ===")
    paths = agent_rapport.build_reports(data, REPORT_DIR, lambda p: v5.ask_claude(p, max_tokens=6000),
                                        languages=languages, author=author, email=email)
    for p in paths:
        print("📄", p)
    print(f"📊 Consommation totale de cette exécution : {v5.usage_summary()}")
    return True


def _cached_system_tests(cfg):
    p = os.path.join(REPORT_DIR, "tests_systeme.json")
    return json.loads(_read(p, "null") or "null")


def recover_project(cfg_path: str):
    """Pour chaque module à spec imposée : tente de reconstruire la preuve validée depuis mbd_out/<module>/Model_vectors.lean (sans aucun appel à Claude)."""
    cfg_dir = os.path.dirname(os.path.abspath(cfg_path))
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "lean_import" in cfg:
        v5.LEAN_IMPORT = cfg["lean_import"]
    print(v5.lean_mode_banner())
    v5.ensure_lean_project()
    for m in cfg["modules"]:
        req = _read(m["req"] if os.path.isabs(m["req"]) else os.path.join(cfg_dir, m["req"]))
        spec = v5.imposed_spec(req)
        print(f"--- {m['name']}")
        if spec is None:
            print("   pas de spec imposée : rien à récupérer automatiquement")
            continue
        ok, why = v5._check_stored(req, m["name"])
        if ok:
            print("   déjà valide : rien à faire")
            continue
        print(f"   état actuel : {why}")
        if v5._recover_from_vectors(m["name"], spec, req):
            print("   ✅ preuve validée récupérée")
    return True


def _clean_cli(value: str, option: str, kind: str = "text"):
    """Valeur d'une option de ligne de commande, ou None si elle est vide ou ressemble à un exemple copié tel quel (« ... », « <nom> »...)."""
    v = (value or "").strip()
    if not v:
        return None
    if re.fullmatch(r"[\s.…<>_\-]*", v) or re.fullmatch(r"<.*>", v) or v.lower() in ("votre nom", "your name", "nom", "name", "email", "courriel"):
        print(f"⚠️  {option} « {v} » ressemble à un exemple recopié, pas à une vraie valeur : ignoré (la valeur du fichier de projet est utilisée).")
        return None
    if kind == "email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
        print(f"⚠️  {option} « {v} » n'est pas une adresse de courriel valide : ignoré (la valeur du fichier de projet est utilisée).")
        return None
    return v


def main(argv=None):
    check_versions()
    parser = argparse.ArgumentParser(description="Projet complet : modules, intégration, tests système, rapports PDF")
    parser.add_argument("config", nargs="?", help="fichier JSON du projet")
    parser.add_argument("--resume", action="store_true", help="saute les modules déjà validés")
    parser.add_argument("--pdf-only", action="store_true", help="reconstruit seulement les PDF")
    parser.add_argument("--no-pdf", action="store_true", help="ne génère pas les PDF")
    parser.add_argument("--use-references", action="store_true",
                        help="autorise les solutions de référence fournies (references_lean/) en repli après des échecs de Claude. Désactivé par défaut : Claude seul")
    parser.add_argument("--lang", default="", help="langues des rapports, séparées par des virgules : fr, en (défaut : celles du fichier de projet)")
    parser.add_argument("--author", default="", help="auteur indiqué sur les rapports (défaut : celui du fichier de projet)")
    parser.add_argument("--email", default="", help="courriel de l'auteur indiqué sur les rapports")
    parser.add_argument("--version", action="store_true", help="affiche le numéro de version des trois scripts")
    parser.add_argument("--recover", action="store_true",
                        help="tente de récupérer, depuis mbd_out, les preuves validées qui auraient été écrasées, puis s'arrête")
    parser.add_argument("--force", action="store_true", help="ignore tout ce qui est déjà validé et refait chaque étape")
    parser.add_argument("--redo", default="", help="modules à refaire entièrement, séparés par des virgules (ex. cossin,correlate)")
    args = parser.parse_args(argv)
    if args.version:
        try:
            import agent_rapport
            rap = getattr(agent_rapport, "AGENT_VERSION", "ancienne version")
        except ImportError:
            rap = "non installé (reportlab/matplotlib manquants)"
        print(f"agent_projet_v8.py {AGENT_VERSION} | agent_lean_v5.py {v5.AGENT_VERSION} | agent_mbd_v7.py {v7.AGENT_VERSION} | agent_rapport.py {rap}")
        return True
    if not args.config:
        parser.error("indiquez le fichier JSON du projet, par exemple : python agent_projet_v8.py projet_pm.json")
    bad = [x for x in (x.strip() for x in args.lang.split(",")) if x and x not in ("fr", "en")]
    if bad:
        parser.error(f"langue(s) inconnue(s) pour --lang : {', '.join(bad)} (disponibles : fr, en)")
    if not os.path.isfile(args.config):
        print(f"⚠️  Fichier introuvable : {args.config}")
        sys.exit(1)
    if args.recover:                      # la récupération n'utilise pas l'API : pas besoin de clé
        return recover_project(args.config)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Variable ANTHROPIC_API_KEY non définie.")
        sys.exit(1)
    return run_project(args.config, resume=args.resume, pdf_only=args.pdf_only, no_pdf=args.no_pdf, force=args.force, use_references=args.use_references,
                       redo=[x.strip() for x in args.redo.split(",") if x.strip()],
                       languages=[x.strip() for x in args.lang.split(",") if x.strip()] or None,
                       author=_clean_cli(args.author, "--author"), email=_clean_cli(args.email, "--email", "email"))


if __name__ == "__main__":
    main()
