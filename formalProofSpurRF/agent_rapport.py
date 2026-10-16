"""
Générateur de rapports PDF pour la chaîne Lean -> vecteurs -> C -> tests.

Produit trois PDF à partir des résultats d'un projet :
  spec_<projet>.pdf         1. spécification système   2. stratégie de vérification Lean (théorèmes, preuves)
                            3. valeurs attendues
  rapport_test_<projet>.pdf 4. code C généré           5. tests (unitaires, intégration, système, traçabilité)
  dossier_<projet>.pdf      l'ensemble, dans cet ordre

Deux textes sont rédigés par Claude à partir des artefacts réels : la spécification système (exigences
traçables) et le commentaire de la stratégie de preuve de chaque module. Tout le reste (énoncés des
théorèmes, code Lean, code C, vecteurs, résultats de tests) est repris tel quel des fichiers produits.

Prérequis : pip install reportlab matplotlib   (matplotlib fournit les polices Unicode DejaVu)
"""

import copy
import datetime
import html
import json
import os
import re

AGENT_VERSION = "2026-10-15.5"   # doit être identique à celui de agent_projet_v8.py

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ACCENT = colors.HexColor("#1f3a5f")
GREEN, RED, GREY = "#1b7f3b", "#b3261e", "#555555"
CODE_WIDTH = 100  # caractères par ligne dans les listings


# ---------- Polices et texte ----------

def _register_fonts() -> bool:
    try:
        import matplotlib
        d = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        for key, fname in {"Body": "DejaVuSans.ttf", "Body-Bold": "DejaVuSans-Bold.ttf",
                           "Body-Italic": "DejaVuSans-Oblique.ttf", "Mono": "DejaVuSansMono.ttf"}.items():
            pdfmetrics.registerFont(TTFont(key, os.path.join(d, fname)))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic",
                                      boldItalic="Body-Bold")
        return True
    except Exception:
        return False


UNICODE_OK = _register_fonts()
F_BODY, F_BOLD, F_MONO = ("Body", "Body-Bold", "Mono") if UNICODE_OK else ("Helvetica", "Helvetica-Bold", "Courier")

_ASCII = {"≤": "<=", "≥": ">=", "→": "->", "↔": "<->", "∀": "forall ", "∃": "exists ", "∈": " in ", "∧": " /\\ ",
          "∨": " \\/ ", "¬": "~", "ℕ": "Nat", "ℤ": "Int", "ℚ": "Rat", "ℝ": "Real", "×": "x", "·": ".", "⟨": "<",
          "⟩": ">", "β": "beta", "φ": "phi", "π": "pi", "α": "alpha", "θ": "theta", "Σ": "Sum", "∑": "Sum",
          "−": "-", "–": "-", "—": "-", "…": "...", "≈": "~", "≠": "!=", "≡": "==", "λ": "fun", "√": "sqrt",
          "⊢": "|-", "∣": "|", "‖": "|", "⁻": "-", "¹": "1", "²": "2", "³": "3", "’": "'", "“": '"', "”": '"'}


def _t(text) -> str:
    """Rend un texte affichable : conserve l'Unicode si la police DejaVu est disponible, sinon translittère."""
    text = str(text)
    if UNICODE_OK:
        return text
    for k, v in _ASCII.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def _esc(text) -> str:
    return html.escape(_t(text), quote=False).replace("\n", "<br/>")


def _style(name, **kw):
    base = dict(fontName=F_BODY, fontSize=9, leading=12.5, textColor=colors.black)
    base.update(kw)
    return ParagraphStyle(name, **base)


ST = {
    "title": _style("Title", fontName=F_BOLD, fontSize=22, leading=27, textColor=ACCENT, spaceAfter=10),
    "subtitle": _style("Subtitle", fontSize=12, leading=16, textColor=colors.HexColor(GREY), spaceAfter=6),
    "h1": _style("H1", fontName=F_BOLD, fontSize=14.5, leading=18, textColor=ACCENT, spaceBefore=14, spaceAfter=7),
    "h2": _style("H2", fontName=F_BOLD, fontSize=11.5, leading=15, textColor=ACCENT, spaceBefore=10, spaceAfter=4),
    "h3": _style("H3", fontName=F_BOLD, fontSize=9.5, leading=13, spaceBefore=6, spaceAfter=2),
    "body": _style("Body", spaceAfter=4),
    "small": _style("Small", fontSize=7.5, leading=10, textColor=colors.HexColor(GREY)),
    "cell": _style("Cell", fontSize=7.5, leading=9.5),
    "cellb": _style("CellB", fontName=F_BOLD, fontSize=7.5, leading=9.5, textColor=colors.white),
    "mono": ParagraphStyle("Mono", fontName=F_MONO, fontSize=6.8, leading=8.2, backColor=colors.HexColor("#f4f5f7"),
                           borderPadding=3, spaceBefore=3, spaceAfter=5),
    "toctitle": _style("TocTitle", fontName=F_BOLD, fontSize=14.5, leading=18, textColor=ACCENT, spaceAfter=8),
    "toc1": _style("TOC1", fontName=F_BOLD, fontSize=9.5, leading=12, leftIndent=0, spaceBefore=4),
    "toc2": _style("TOC2", fontSize=8.5, leading=10.5, leftIndent=14),
}


def P(text, style="body"):
    return Paragraph(_esc(text), ST[style])


def PM(markup, style="body"):
    """Paragraphe avec balises <b>, <i>, <font> (le texte inséré doit déjà être échappé)."""
    return Paragraph(markup, ST[style])


# ---------- Textes du rapport, en français et en anglais ----------
# Le français est repris tel quel du rapport d'origine ; l'anglais en est la traduction. Les textes propres au projet (titre, description
# de l'algorithme, rôles des modules, critère) viennent de la configuration ; sinon, ils sont traduits par le modèle de langage.

LANG = "fr"

STR = {
    "fr": {
        "footer.page": "Page {n}",
        "cover.project": "Projet", "cover.document": "Document", "cover.author": "Auteur", "cover.contact": "Contact",
        "cover.date": "Date de génération", "cover.lean": "Lean", "cover.ccomp": "Compilateur C",
        "cover.disclaimer": ("Document généré automatiquement par l'agent. Les textes de synthèse (spécification système, commentaires de "
                             "preuve) sont rédigés par un modèle de langage à partir des fichiers produits et doivent être relus ; les énoncés "
                             "des théorèmes, les preuves, les vecteurs, le code C et les résultats de tests sont repris tels quels."),
        "cover.toc": "Table des matières",
        "doc.spec": "Spécification et vérification formelle", "doc.test": "Rapport de test",
        "doc.full": "Dossier complet : spécification, vérification et tests",
        "file.spec": "spec_{name}.pdf", "file.test": "rapport_test_{name}.pdf", "file.full": "dossier_{name}.pdf",
        "fb.object": "(rédaction automatique indisponible : voir la description algorithmique en 1.7)",
        "fb.theorem": "Propriété formelle {t} établie par Lean (module {m}).",
        "fb.test": "Le code C est conforme aux valeurs attendues ({t}).",
        "s1.title": "1. Spécification système", "s1.1": "1.1 Objet", "s1.2": "1.2 Contexte", "s1.3": "1.3 Hypothèses", "s1.4": "1.4 Interfaces",
        "if.hdr": ["Nom", "Type", "Format", "Plage"], "s1.5": "1.5 Exigences",
        "req.hdr": ["Identifiant", "Exigence", "Méthode", "Vérifiée par"], "req.tbc": "(à compléter)",
        "s1.6": "1.6 Limites et hypothèses ouvertes", "s1.7": "1.7 Description algorithmique de référence",
        "s2.title": "2. Stratégie de vérification en Lean", "s2.1": "2.1 Principe",
        "s2.principle": ("Chaque module est décrit par une spécification formelle (une fonction et des théorèmes). Les énoncés des théorèmes sont "
                         "figés : le modèle de langage ne peut écrire que l'implémentation et les preuves, que Lean 4 accepte ou rejette. "
                         "Un module est retenu uniquement si Lean le compile sans erreur, sans « sorry » et sans axiome ajouté. Une fonction de "
                         "référence écrite et prouvée en Lean sert ensuite à calculer les valeurs attendues."),
        "s2.proves.hdr": ["Ce que Lean prouve", "Ce qui est validé par test ou simulation"],
        "s2.proves.a": ("Bornes des valeurs et absence de débordement ; symétries et identités ; longueurs des résultats ; cas limites "
                        "(entrées nulles, plafonds)."),
        "s2.proves.b": ("Précision numérique des fonctions (table de sinus), efficacité de l'algorithme (niveau de raie résiduel), "
                        "conformité du code C sur un ensemble fini de vecteurs."),
        "s2.2": "2.2 Architecture",
        "arch.hdr": ["Module", "Rôle", "Théorèmes", "Tentatives", "Axiomes", "Statut"], "arch.yes": "prouvé", "arch.no": "non prouvé",
        "arch.note": ("Axiomes : propext, Classical.choice et Quot.sound sont les axiomes standard de Lean ; « sorryAx » signalerait une "
                      "preuve incomplète et ferait rejeter le module."),
        "s2.module": "2.{i} Module {name}", "s2.spec": "Spécification formelle (fixée avant la preuve)",
        "s2.strategy": "Stratégie de preuve (commentaire généré à partir du code Lean)",
        "thm.hdr": ["Théorème", "En clair", "Stratégie de preuve"], "lem.hdr": ["Lemme auxiliaire", "Rôle"],
        "s2.axioms": "Axiomes (sortie de #print axioms)",
        "appA": "Annexe A. Code Lean complet des modules (définitions, lemmes et preuves)", "module": "Module {name}",
        "s3.title": "3. Valeurs attendues", "s3.1": "3.1 Méthode",
        "s3.method": ("Les valeurs attendues sont calculées par le modèle Lean prouvé : un programme Lean appelle les fonctions du module sur des "
                      "entrées choisies (trajectoires typiques, cas limites, saturations) et affiche, pour chaque cas, l'entrée puis la sortie. "
                      "Les valeurs ne sont pas écrites à la main. Une vérification contrôle que le programme appelle bien la fonction du module. "
                      "Format : entiers séparés par un espace ; une liste est codée par sa longueur suivie de ses éléments."),
        "s3.2": "3.2 Couverture par module", "cov.hdr": ["Module", "Cas", "Fichiers"], "cov.module": "Couverture du module {name}",
        "s3.3": "3.3 Extraits des vecteurs", "vec.hdr": ["n°", "Entrées", "Sortie attendue"],
        "vec.module": "Module {name} : {n} cas, extrait des 8 premiers", "tok.more": " … (+{n} valeurs)",
        "s3.4": "3.4 Scénarios système",
        "s3.scen": ("Signaux de test synthétiques : porteuse modulée en phase par une raie d'indice beta et de phase phi, bruit blanc, "
                    "bloc de {n} échantillons. Valeurs de référence : prototype Python indépendant, arithmétique entière identique."),
        "scen.hdr": ["Test", "beta", "phi (rad)", "SNR (dB)", "Raie avant (dBc)", "Raie attendue après (dBc)"],
        "s4.title": "4. Code C généré",
        "s4.intro": ("Le code C est produit à partir du modèle Lean prouvé, sans virgule flottante, avec des entiers 64 bits pour les calculs "
                     "intermédiaires. Chaque module comporte un fichier model.c (la fonction, sans entrées-sorties) et un harnais harness.c qui "
                     "lit les vecteurs d'entrée et affiche les sorties."),
        "c.hdr": ["Module", "Compilateur", "Tentatives de génération", "Fichiers"], "s4.module": "4.{i} Module {name} : model.c",
        "absent": "(absent)", "appB": "Annexe B. Harnais de test (harness.c)",
        "s5.title": "5. Tests", "s5.1": "5.1 Procédure",
        "s5.proc": ("Pour chaque module, le code C est compilé puis exécuté sur les vecteurs d'entrée ; sa sortie est comparée, ligne à ligne et "
                    "exactement, aux valeurs attendues calculées par Lean. Un test réussit si et seulement si aucune ligne ne diffère. Le code C "
                    "n'a jamais accès aux valeurs attendues. En cas d'écart, le code est corrigé puis retesté ; les vecteurs ne sont jamais modifiés."),
        "s5.2": "5.2 Tests unitaires et d'intégration", "unit.hdr": ["Identifiant", "Module", "Cas", "Écarts", "Résultat"],
        "pass": "réussi", "fail": "échec", "s5.3": "5.3 Tests système (blocs de {n} échantillons)",
        "s5.sys": ("Le code C d'intégration est exécuté sur des signaux synthétiques. Deux contrôles : (a) sorties identiques au bit près à "
                   "celles du prototype Python indépendant ; (b) niveau de la raie résiduelle (le plus élevé parmi les harmoniques ±1 à "
                   "±3) conforme au critère : {crit}."),
        "sys.hdr": ["Test", "beta réel", "beta estimé", "Avant (dBc)", "Après (dBc)", "= prototype", "Critère", "Résultat"],
        "yes": "oui", "no": "NON",
        "fig.caption": ("Spectre avant et après correction, premier scénario. Les raies à ±1, ±2 et ±3 fois la fréquence "
                        "de la raie parasite disparaissent."),
        "s5.4": "5.4 Traçabilité des exigences", "proved": "prouvé", "trace.hdr": ["Exigence", "Texte", "Références", "Statut"],
        "verified": "vérifiée", "notcovered": "non couverte", "failedornot": "échec ou non exécutée",
        "s5.5": "5.5 Verdict", "verdict": "Verdict global : {badge}", "compliant": "CONFORME", "noncompliant": "NON CONFORME",
        "s5.limits": ("Les tests couvrent un ensemble fini de cas : ils ne constituent pas une preuve d'équivalence entre le code C et le modèle "
                      "Lean pour toutes les entrées. Les preuves Lean portent sur le modèle ; le passage du modèle au C est validé par ces tests. "
                      "Le compilateur C, Lean et les outils de génération font partie de la base de confiance."),
    },
    "en": {
        "footer.page": "Page {n}",
        "cover.project": "Project", "cover.document": "Document", "cover.author": "Author", "cover.contact": "Contact",
        "cover.date": "Generated on", "cover.lean": "Lean", "cover.ccomp": "C compiler",
        "cover.disclaimer": ("Document generated automatically by the agent. The summary texts (system specification, proof commentaries) "
                             "are written by a language model from the produced files and must be reviewed; the theorem statements, the "
                             "proofs, the vectors, the C code and the test results are reproduced as is."),
        "cover.toc": "Table of contents",
        "doc.spec": "Specification and formal verification", "doc.test": "Test report",
        "doc.full": "Complete dossier: specification, verification and tests",
        "file.spec": "spec_{name}_en.pdf", "file.test": "test_report_{name}_en.pdf", "file.full": "full_report_{name}_en.pdf",
        "fb.object": "(automatic drafting unavailable: see the algorithm description in 1.7)",
        "fb.theorem": "Formal property {t} established by Lean (module {m}).",
        "fb.test": "The C code conforms to the expected values ({t}).",
        "s1.title": "1. System specification", "s1.1": "1.1 Purpose", "s1.2": "1.2 Context", "s1.3": "1.3 Assumptions", "s1.4": "1.4 Interfaces",
        "if.hdr": ["Name", "Type", "Format", "Range"], "s1.5": "1.5 Requirements",
        "req.hdr": ["Identifier", "Requirement", "Method", "Verified by"], "req.tbc": "(to be completed)",
        "s1.6": "1.6 Limits and open assumptions", "s1.7": "1.7 Reference algorithm description",
        "s2.title": "2. Verification strategy in Lean", "s2.1": "2.1 Principle",
        "s2.principle": ("Each module is described by a formal specification (one function and its theorems). The theorem statements are "
                         "frozen: the language model may only write the implementation and the proofs, which Lean 4 then accepts or rejects. "
                         "A module is retained only if Lean compiles it with no error, no “sorry” and no added axiom. A reference function "
                         "written and proved in Lean is then used to compute the expected values."),
        "s2.proves.hdr": ["What Lean proves", "What is validated by test or simulation"],
        "s2.proves.a": ("Value bounds and absence of overflow; symmetries and identities; result lengths; limit cases "
                        "(zero inputs, clamping)."),
        "s2.proves.b": ("Numerical accuracy of the functions (sine table), effectiveness of the algorithm (residual spur level), "
                        "conformity of the C code on a finite set of vectors."),
        "s2.2": "2.2 Architecture",
        "arch.hdr": ["Module", "Role", "Theorems", "Attempts", "Axioms", "Status"], "arch.yes": "proved", "arch.no": "not proved",
        "arch.note": ("Axioms: propext, Classical.choice and Quot.sound are the standard Lean axioms; “sorryAx” would indicate an "
                      "incomplete proof and cause the module to be rejected."),
        "s2.module": "2.{i} Module {name}", "s2.spec": "Formal specification (fixed before the proof)",
        "s2.strategy": "Proof strategy (commentary generated from the Lean code)",
        "thm.hdr": ["Theorem", "In plain words", "Proof strategy"], "lem.hdr": ["Auxiliary lemma", "Role"],
        "s2.axioms": "Axioms (output of #print axioms)",
        "appA": "Appendix A. Complete Lean code of the modules (definitions, lemmas and proofs)", "module": "Module {name}",
        "s3.title": "3. Expected values", "s3.1": "3.1 Method",
        "s3.method": ("The expected values are computed by the proved Lean model: a Lean program calls the module functions on chosen inputs "
                      "(typical trajectories, limit cases, saturations) and prints, for each case, the input and then the output. "
                      "The values are not written by hand. A check verifies that the program really calls the module function. "
                      "Format: integers separated by a space; a list is encoded as its length followed by its elements."),
        "s3.2": "3.2 Coverage per module", "cov.hdr": ["Module", "Cases", "Files"], "cov.module": "Coverage of module {name}",
        "s3.3": "3.3 Vector excerpts", "vec.hdr": ["No.", "Inputs", "Expected output"],
        "vec.module": "Module {name}: {n} cases, first 8 shown", "tok.more": " … (+{n} values)",
        "s3.4": "3.4 System scenarios",
        "s3.scen": ("Synthetic test signals: carrier phase-modulated by a spur of index beta and phase phi, white noise, "
                    "block of {n} samples. Reference values: independent Python prototype, identical integer arithmetic."),
        "scen.hdr": ["Test", "beta", "phi (rad)", "SNR (dB)", "Spur before (dBc)", "Expected spur after (dBc)"],
        "s4.title": "4. Generated C code",
        "s4.intro": ("The C code is produced from the proved Lean model, with no floating point and with 64-bit integers for intermediate "
                     "computations. Each module has a model.c file (the function, without input/output) and a harness.c test harness that "
                     "reads the input vectors and prints the outputs."),
        "c.hdr": ["Module", "Compiler", "Generation attempts", "Files"], "s4.module": "4.{i} Module {name}: model.c",
        "absent": "(missing)", "appB": "Appendix B. Test harness (harness.c)",
        "s5.title": "5. Tests", "s5.1": "5.1 Procedure",
        "s5.proc": ("For each module, the C code is compiled and then run on the input vectors; its output is compared, line by line and "
                    "exactly, with the expected values computed by Lean. A test passes if and only if no line differs. The C code never has "
                    "access to the expected values. In case of a mismatch, the code is corrected and retested; the vectors are never modified."),
        "s5.2": "5.2 Unit and integration tests", "unit.hdr": ["Identifier", "Module", "Cases", "Mismatches", "Result"],
        "pass": "passed", "fail": "failed", "s5.3": "5.3 System tests (blocks of {n} samples)",
        "s5.sys": ("The integration C code is run on synthetic signals. Two checks: (a) outputs bit-identical to those of the independent "
                   "Python prototype; (b) residual spur level (the highest among harmonics ±1 to ±3) meeting the criterion: {crit}."),
        "sys.hdr": ["Test", "actual beta", "estimated beta", "Before (dBc)", "After (dBc)", "= prototype", "Criterion", "Result"],
        "yes": "yes", "no": "NO",
        "fig.caption": ("Spectrum before and after correction, first scenario. The lines at ±1, ±2 and ±3 times the spur frequency "
                        "disappear."),
        "s5.4": "5.4 Requirements traceability", "proved": "proved", "trace.hdr": ["Requirement", "Text", "References", "Status"],
        "verified": "verified", "notcovered": "not covered", "failedornot": "failed or not run",
        "s5.5": "5.5 Verdict", "verdict": "Overall verdict: {badge}", "compliant": "COMPLIANT", "noncompliant": "NON-COMPLIANT",
        "s5.limits": ("The tests cover a finite set of cases: they do not constitute a proof of equivalence between the C code and the Lean "
                      "model for all inputs. The Lean proofs concern the model; the translation from the model to C is validated by these tests. "
                      "The C compiler, Lean and the generation tools are part of the trusted base."),
    },
}


def set_lang(lang: str):
    global LANG
    if lang not in STR:
        raise ValueError(f"langue inconnue : {lang} (disponibles : {', '.join(STR)})")
    LANG = lang


def T(key: str, **kw):
    """Texte du rapport dans la langue courante ; les gabarits {x} sont remplis avec kw. Les en-têtes de tableau sont des listes."""
    value = STR[LANG][key]
    return value.format(**kw) if (kw and isinstance(value, str)) else value


def badge(ok, yes="OK", no="ÉCHEC") -> str:
    return f'<font color="{GREEN if ok else RED}"><b>{_esc(yes if ok else no)}</b></font>'


def wrap_code(text: str, width: int = CODE_WIDTH) -> str:
    out = []
    for line in str(text).replace("\t", "    ").splitlines():
        line = _t(line)
        indent = len(line) - len(line.lstrip(" "))
        while len(line) > width:
            out.append(line[:width])
            line = " " * (indent + 4) + line[width:]
        out.append(line)
    return "\n".join(out)


def Code(text):
    return Preformatted(wrap_code(text), ST["mono"])


def table(rows, widths, header=True):
    data = []
    for i, row in enumerate(rows):
        style = "cellb" if (header and i == 0) else "cell"
        data.append([c if not isinstance(c, str) else Paragraph(_esc(c), ST[style]) for c in row])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    cmds = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8bec9")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
    t.setStyle(TableStyle(cmds))
    return t


def markup_cell(markup):
    return Paragraph(markup, ST["cell"])


# ---------- Document avec table des matières ----------

class Doc(BaseDocTemplate):
    def __init__(self, path, header_text, author=None, email=None, **kw):
        if author:
            kw["author"] = author           # métadonnée « auteur » du PDF
        super().__init__(path, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=2.0 * cm,
                         bottomMargin=1.8 * cm, **kw)
        self.header_text = _t(header_text)
        self.footer_author = _t(author + (f" - {email}" if email else "")) if author else ""
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=self._decorate)])

    def _decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setFont(F_BODY, 7.5)
        canvas.setFillColor(colors.HexColor(GREY))
        text, maxw = self.header_text, self.width - 2.2 * cm
        while pdfmetrics.stringWidth(text, F_BODY, 7.5) > maxw and len(text) > 10:
            text = text[:-2]
        canvas.drawString(self.leftMargin, A4[1] - 1.2 * cm, text if text == self.header_text else text.rstrip() + "…" if UNICODE_OK else text.rstrip() + "...")
        canvas.drawRightString(A4[0] - self.rightMargin, 1.0 * cm, T("footer.page", n=doc.page))
        if self.footer_author:
            canvas.drawString(self.leftMargin, 1.0 * cm, self.footer_author)
        canvas.setStrokeColor(colors.HexColor("#b8bec9"))
        canvas.line(self.leftMargin, A4[1] - 1.4 * cm, A4[0] - self.rightMargin, A4[1] - 1.4 * cm)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ("H1", "H2"):
            self.notify("TOCEntry", (0 if flowable.style.name == "H1" else 1, flowable.getPlainText(), self.page))


def _toc():
    toc = TableOfContents()
    toc.levelStyles = [ST["toc1"], ST["toc2"]]
    return toc


# ---------- Rédaction par Claude ----------

def _json_from(reply: str):
    text = reply.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("pas de JSON dans la réponse")
    return json.loads(text[start:end + 1])


def _ask_json(ask, prompt, retries=2):
    last = None
    for _ in range(retries):
        try:
            return _json_from(ask(prompt))
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    raise RuntimeError(f"Réponse JSON invalide après {retries} essais : {last}")


def valid_references(data) -> dict:
    """Références que la spec système peut citer : théorèmes Lean et identifiants de tests."""
    theorems, tests = {}, {}
    for m in data["modules"] + ([data["integration"]] if data.get("integration") else []):
        for t in (m.get("spec") or {}).get("theorems", []):
            theorems[t["name"]] = m["name"]
        tests[f"T-{m['name']}-VEC"] = m["name"]
    for s in (data.get("system_tests") or {}).get("scenarios", []):
        tests[s["id"]] = "système"
    return {"theorems": theorems, "tests": tests}


def generate_system_spec(ask, data) -> dict:
    refs = valid_references(data)
    mods = "\n".join(f"- {m['name']} : {m.get('role', '')}" for m in data["modules"])
    st = data.get("system_tests") or {}
    prompt_fr = f"""Tu rédiges la SPÉCIFICATION SYSTÈME d'un composant logiciel, pour un rapport technique.

Description du système et de l'algorithme :
{data['overview_text']}

Modules : 
{mods}
Fonction d'intégration : {data['integration']['name'] if data.get('integration') else '(aucune)'}
Critère de performance système : {st.get('criterion_text', '(non défini)')}

Références valides (tu ne dois citer QUE celles-ci dans le champ "references") :
- théorèmes Lean : {', '.join(refs['theorems']) or '(aucun)'}
- tests : {', '.join(refs['tests']) or '(aucun)'}

Réponds UNIQUEMENT avec un JSON de la forme :
{{"objet": "...", "contexte": "...", "hypotheses": ["..."],
  "interfaces": [{{"nom": "...", "type": "...", "format": "...", "plage": "..."}}],
  "exigences": [{{"id": "SYS-01", "texte": "exigence vérifiable, formulée au présent", "methode": "Lean" | "Test" | "Simulation",
                 "references": ["nom de théorème ou identifiant de test"]}}],
  "limites": ["..."]}}
Règles : 8 à 14 exigences ; chaque exigence a au moins une référence valide ; appuie-toi uniquement sur les informations données ;
n'invente aucune valeur numérique absente du texte ; français technique concis.
"""
    prompt_en = f"""You are writing the SYSTEM SPECIFICATION of a software component, for a technical report.

Description of the system and of the algorithm:
{data['overview_text']}

Modules:
{mods}
Integration function: {data['integration']['name'] if data.get('integration') else '(none)'}
System performance criterion: {st.get('criterion_text', '(not defined)')}

Valid references (you must cite ONLY these in the "references" field):
- Lean theorems: {', '.join(refs['theorems']) or '(none)'}
- tests: {', '.join(refs['tests']) or '(none)'}

Answer ONLY with a JSON object of the form:
{{"objet": "...", "contexte": "...", "hypotheses": ["..."],
  "interfaces": [{{"nom": "...", "type": "...", "format": "...", "plage": "..."}}],
  "exigences": [{{"id": "SYS-01", "texte": "verifiable requirement, written in the present tense", "methode": "Lean" | "Test" | "Simulation",
                 "references": ["theorem name or test identifier"]}}],
  "limites": ["..."]}}
The JSON keys must stay exactly as written (they are identifiers) and the values "Lean", "Test" and "Simulation" are kept as is; all other
values must be written in English.
Rules: 8 to 14 requirements; each requirement has at least one valid reference; rely only on the information given; do not invent any
numerical value absent from the text; concise technical English.
"""
    prompt = prompt_en if LANG == "en" else prompt_fr

    spec = _ask_json(ask, prompt)
    for e in spec.get("exigences", []):
        e["references"] = [r for r in e.get("references", []) if r in refs["theorems"] or r in refs["tests"]]
    return spec


def fallback_system_spec(data) -> dict:
    """Spécification minimale construite sans modèle de langage (si la rédaction automatique échoue)."""
    refs = valid_references(data)
    ex = [{"id": f"SYS-{i + 1:02d}", "texte": T("fb.theorem", t=t, m=m), "methode": "Lean",
           "references": [t]} for i, (t, m) in enumerate(refs["theorems"].items())]
    ex += [{"id": f"SYS-{len(ex) + i + 1:02d}", "texte": T("fb.test", t=t), "methode": "Test",
            "references": [t]} for i, t in enumerate(refs["tests"])]
    return {"objet": T("fb.object"), "contexte": "",
            "hypotheses": [], "interfaces": [], "exigences": ex, "limites": []}


def generate_proof_strategy(ask, module) -> dict:
    spec = module.get("spec") or {}
    theorems = "\n".join(f"- {t['name']} : {t['statement']}" for t in spec.get("theorems", []))
    prompt_fr = f"""Voici un module Lean 4 (définitions, lemmes, théorèmes avec preuves) déjà accepté par Lean.

```lean
{module['lean_src']}
```

Théorèmes de la spécification :
{theorems}

Rédige un commentaire pour un rapport de vérification. Décris UNIQUEMENT ce qui figure dans ce code, sans rien inventer.
Réponds UNIQUEMENT avec un JSON de la forme :
{{"resume": "2 à 4 phrases : ce que fait la fonction et comment la preuve est organisée",
  "theoremes": [{{"nom": "...", "en_clair": "ce que dit le théorème, en une phrase", "strategie": "technique de preuve : récurrence, analyse de cas, omega, simp... et lemmes utilisés"}}],
  "lemmes": [{{"nom": "...", "role": "..."}}]}}
Un élément par théorème de la spécification ; "lemmes" liste les lemmes auxiliaires du code (liste vide s'il n'y en a pas).
"""
    prompt_en = f"""Here is a Lean 4 module (definitions, lemmas, theorems with proofs) already accepted by Lean.

```lean
{module['lean_src']}
```

Theorems of the specification:
{theorems}

Write a commentary for a verification report. Describe ONLY what appears in this code, without inventing anything.
Answer ONLY with a JSON object of the form:
{{"resume": "2 to 4 sentences: what the function does and how the proof is organised",
  "theoremes": [{{"nom": "...", "en_clair": "what the theorem says, in one sentence", "strategie": "proof technique: induction, case analysis, omega, simp... and lemmas used"}}],
  "lemmes": [{{"nom": "...", "role": "..."}}]}}
One element per theorem of the specification; "lemmes" lists the auxiliary lemmas of the code (empty list if there are none).
The JSON keys must stay exactly as written; all values must be written in English.
"""
    prompt = prompt_en if LANG == "en" else prompt_fr

    return _ask_json(ask, prompt)


# ---------- Textes du projet dans la langue demandée ----------

def translate_texts(ask, texts: dict) -> dict:
    """Traduit (français -> anglais) les textes du projet que la configuration ne fournit pas en anglais. Un seul appel."""
    prompt = ("Translate the string values of the following JSON object from French into English. This is technical writing about "
              "signal processing and formal verification: keep all formulas, numbers, identifiers, symbols and line breaks exactly as they "
              "are, and translate only the words. Answer ONLY with the JSON object, with exactly the same keys and structure.\n\n"
              + json.dumps(texts, ensure_ascii=False, indent=1))
    return _ask_json(ask, prompt)


def localize(data: dict, lang: str, ask) -> dict:
    """Copie des données du rapport avec les textes du projet (titre, description, rôles, critère) dans la langue demandée."""
    d = copy.deepcopy(data)
    if lang == "fr":
        return d
    given = (data.get("i18n") or {}).get(lang, {})
    mods = d["modules"] + ([d["integration"]] if d.get("integration") else [])
    st = d.get("system_tests") or {}
    todo = {}
    if not given.get("title"):
        todo["title"] = d["title"]
    if not given.get("overview_text"):
        todo["overview_text"] = d["overview_text"]
    if st.get("criterion_text") and not given.get("criterion_text"):
        todo["criterion_text"] = st["criterion_text"]
    roles = {m["name"]: m.get("role", "") for m in mods if m.get("role") and m["name"] not in given.get("roles", {})}
    if roles:
        todo["roles"] = roles
    done = {}
    if todo:
        print(f"📝 [{lang}] Traduction des textes du projet absents de la configuration ({', '.join(todo)})...")
        try:
            done = translate_texts(ask, todo)
        except RuntimeError as e:
            print(f"⚠️  {e} : les textes du projet restent en français dans le rapport anglais.")
    d["title"] = given.get("title") or done.get("title") or d["title"]
    d["overview_text"] = given.get("overview_text") or done.get("overview_text") or d["overview_text"]
    if st:
        st["criterion_text"] = given.get("criterion_text") or done.get("criterion_text") or st.get("criterion_text", "")
        if st.get(f"figure_{lang}") and os.path.isfile(st[f"figure_{lang}"]):
            st["figure"] = st[f"figure_{lang}"]
    all_roles = {**(done.get("roles") or {}), **given.get("roles", {})}
    for m in mods:
        if all_roles.get(m["name"]):
            m["role"] = all_roles[m["name"]]
    return d


# ---------- Sections du rapport ----------

def _short_tokens(line, limit=12):
    toks = line.split()
    return " ".join(toks) if len(toks) <= limit else " ".join(toks[:limit]) + T("tok.more", n=len(toks) - limit)


def _module_status(m) -> bool:
    return bool(m.get("result", {}).get("ok"))


def cover(title, doc_type, data):
    gen = data.get("generated_at", datetime.datetime.now().isoformat(timespec="minutes"))
    tc = data.get("toolchain", {})
    rows = [[T("cover.project"), title], [T("cover.document"), doc_type]]
    if data.get("author"):
        rows.append([T("cover.author"), data["author"]])
    if data.get("email"):
        rows.append([T("cover.contact"), data["email"]])
    rows += [[T("cover.date"), gen], [T("cover.lean"), tc.get("lean", "?")], [T("cover.ccomp"), tc.get("c_compiler", "?")]]
    return [Spacer(1, 3 * cm), P(title, "title"), P(doc_type, "subtitle"), Spacer(1, 1 * cm),
            table(rows, [4.5, 12.5], header=False), Spacer(1, 1 * cm),
            P(T("cover.disclaimer"), "small"),
            PageBreak(), P(T("cover.toc"), "toctitle"), _toc(), PageBreak()]


def section_system(data, sysspec):
    s = [P(T("s1.title"), "h1"), P(T("s1.1"), "h2"), P(sysspec.get("objet", "")),
         P(T("s1.2"), "h2"), P(sysspec.get("contexte", ""))]
    if sysspec.get("hypotheses"):
        s.append(P(T("s1.3"), "h2"))
        s += [P("• " + h) for h in sysspec["hypotheses"]]
    if sysspec.get("interfaces"):
        s.append(P(T("s1.4"), "h2"))
        rows = [T("if.hdr")] + [[i.get("nom", ""), i.get("type", ""), i.get("format", ""),
                                 i.get("plage", "")] for i in sysspec["interfaces"]]
        s.append(table(rows, [3.2, 4.2, 4.8, 4.8]))
    s.append(P(T("s1.5"), "h2"))
    rows = [T("req.hdr")]
    for e in sysspec.get("exigences", []):
        rows.append([e.get("id", ""), e.get("texte", ""), e.get("methode", ""), ", ".join(e.get("references", [])) or T("req.tbc")])
    s.append(table(rows, [1.8, 8.2, 1.9, 5.1]))
    if sysspec.get("limites"):
        s.append(P(T("s1.6"), "h2"))
        s += [P("• " + h) for h in sysspec["limites"]]
    s.append(P(T("s1.7"), "h2"))
    s.append(P(data["overview_text"], "small"))
    return s


def section_lean(data, strategies):
    mods = data["modules"] + ([data["integration"]] if data.get("integration") else [])
    s = [PageBreak(), P(T("s2.title"), "h1"), P(T("s2.1"), "h2"),
         P(T("s2.principle")),
         table([T("s2.proves.hdr"), [T("s2.proves.a"), T("s2.proves.b")]], [8.5, 8.5]),
         P(T("s2.2"), "h2")]
    rows = [T("arch.hdr")]
    for m in mods:
        proof = m.get("result", {}).get("proof", {})
        rows.append([m["name"], m.get("role", ""), str(len((m.get("spec") or {}).get("theorems", []))),
                     f"{proof.get('rounds', '?')} ({', '.join(sorted(set(proof.get('provers', [])))) or '?'})",
                     ", ".join(sorted({a.split('[')[-1].rstrip(']') for a in proof.get("axioms", [])})) or "?",
                     markup_cell(badge(_module_status(m), T("arch.yes"), T("arch.no")))])
    s.append(table(rows, [2.6, 5.0, 1.8, 2.6, 3.6, 1.6]))
    s.append(P(T("arch.note"), "small"))
    for i, m in enumerate(mods, 1):
        spec, strat = m.get("spec") or {}, strategies.get(m["name"], {})
        s += [P(T("s2.module", i=i + 2, name=m["name"]), "h2"), P(m.get("role", ""))]
        s += [P(T("s2.spec"), "h3"),
              Code(spec.get("signature", "") + "\n\n" + "\n\n".join(t["statement"] for t in spec.get("theorems", [])))]
        if strat.get("resume"):
            s += [P(T("s2.strategy"), "h3"), P(strat["resume"])]
        rows = [T("thm.hdr")]
        by_name = {t.get("nom"): t for t in strat.get("theoremes", [])}
        for t in spec.get("theorems", []):
            c = by_name.get(t["name"], {})
            rows.append([t["name"], c.get("en_clair", ""), c.get("strategie", "")])
        s.append(table(rows, [4.2, 6.0, 6.8]))
        if strat.get("lemmes"):
            s.append(table([T("lem.hdr")] + [[l.get("nom", ""), l.get("role", "")] for l in strat["lemmes"]], [5.0, 12.0]))
        ax = m.get("result", {}).get("proof", {}).get("axioms", [])
        if ax:
            s += [P(T("s2.axioms"), "h3"), Code("\n".join(ax))]
    s += [PageBreak(), P(T("appA"), "h1")]
    for m in mods:
        s += [P(T("module", name=m["name"]), "h2"), Code(m["lean_src"])]
    return s


def section_expected(data):
    mods = data["modules"] + ([data["integration"]] if data.get("integration") else [])
    s = [PageBreak(), P(T("s3.title"), "h1"), P(T("s3.1"), "h2"),
         P(T("s3.method")),
         P(T("s3.2"), "h2")]
    rows = [T("cov.hdr")]
    for m in mods:
        r = m.get("result", {})
        rows.append([m["name"], str(r.get("n_cases", "?")), f"{r.get('mbd_dir', '')}/vectors_in.txt, vectors_expected.txt"])
    s.append(table(rows, [3.0, 1.8, 12.2]))
    for m in mods:
        cov = m.get("result", {}).get("coverage", "")
        if cov:
            s += [P(T("cov.module", name=m["name"]), "h3"), Code(cov)]
    s.append(P(T("s3.3"), "h2"))
    for m in mods:
        ins, outs = m.get("vectors_in", []), m.get("vectors_expected", [])
        if not ins:
            continue
        rows = [T("vec.hdr")]
        for k in range(min(8, len(ins))):
            rows.append([str(k), _short_tokens(ins[k]), _short_tokens(outs[k])])
        s += [P(T("vec.module", name=m["name"], n=len(ins)), "h3"), table(rows, [1.0, 8.0, 8.0])]
    st = data.get("system_tests") or {}
    if st.get("scenarios"):
        s += [P(T("s3.4"), "h2"),
              P(T("s3.scen", n=st.get("n", "?")))]
        rows = [T("scen.hdr")]
        for sc in st["scenarios"]:
            rows.append([sc["id"], f"{sc['beta']}", f"{sc['phi']}", f"{sc['snr_db']}",
                         f"{sc['spur_before_dbc']:.1f}", f"{sc['proto_after_dbc']:.1f}"])
        s.append(table(rows, [2.2, 2.0, 2.4, 2.2, 4.0, 4.2]))
    return s


def section_c(data):
    mods = data["modules"] + ([data["integration"]] if data.get("integration") else [])
    s = [P(T("s4.title"), "h1"),
         P(T("s4.intro"))]
    rows = [T("c.hdr")]
    for m in mods:
        r = m.get("result", {})
        rows.append([m["name"], r.get("compiler", "?"), str(r.get("target_rounds", "?")), f"{r.get('mbd_dir', '')}/model.c, harness.c"])
    s.append(table(rows, [2.8, 4.0, 3.2, 7.0]))
    for i, m in enumerate(mods, 1):
        s += [P(T("s4.module", i=i, name=m["name"]), "h2"), Code(m.get("c_model", T("absent")))]
    s += [PageBreak(), P(T("appB"), "h1")]
    for m in mods:
        s += [P(T("module", name=m["name"]), "h2"), Code(m.get("c_harness", T("absent")))]
    return s


def section_tests(data, sysspec):
    mods = data["modules"] + ([data["integration"]] if data.get("integration") else [])
    st = data.get("system_tests") or {}
    s = [PageBreak(), P(T("s5.title"), "h1"), P(T("s5.1"), "h2"),
         P(T("s5.proc")),
         P(T("s5.2"), "h2")]
    rows = [T("unit.hdr")]
    for m in mods:
        r = m.get("result", {})
        ok = r.get("n_mismatch") == 0
        rows.append([f"T-{m['name']}-VEC", m["name"], str(r.get("n_cases", "?")), str(r.get("n_mismatch", "?")),
                     markup_cell(badge(ok, T("pass"), T("fail")))])
    s.append(table(rows, [3.6, 3.6, 2.0, 2.0, 5.8]))
    if st.get("scenarios"):
        s += [P(T("s5.3", n=st.get("n", "?")), "h2"),
              P(T("s5.sys", crit=st.get("criterion_text", "")))]
        rows = [T("sys.hdr")]
        for sc in st["scenarios"]:
            rows.append([sc["id"], f"{sc['beta']}", f"{sc['beta_est']:.4f}", f"{sc['spur_before_dbc']:.1f}",
                         f"{sc['spur_after_dbc']:.1f}", T("yes") if sc["bitexact"] else T("no"),
                         f"<= {st.get('criterion_dbc')}", markup_cell(badge(sc["passed"], T("pass"), T("fail")))])
        s.append(table(rows, [1.7, 1.6, 2.0, 2.0, 2.0, 2.2, 2.0, 3.5]))
        if st.get("figure") and os.path.isfile(st["figure"]):
            img = Image(st["figure"], width=16.5 * cm, height=7.5 * cm)
            s += [Spacer(1, 6), img, P(T("fig.caption"), "small")]
    s.append(P(T("s5.4"), "h2"))
    refs = valid_references(data)
    status = {}
    for m in mods:
        r = m.get("result", {})
        for t in (m.get("spec") or {}).get("theorems", []):
            status[t["name"]] = (T("proved"), _module_status(m))
        status[f"T-{m['name']}-VEC"] = (T("pass") if r.get("n_mismatch") == 0 else T("fail"), r.get("n_mismatch") == 0)
    for sc in st.get("scenarios", []):
        status[sc["id"]] = (T("pass") if sc["passed"] else T("fail"), sc["passed"])
    rows = [T("trace.hdr")]
    for e in sysspec.get("exigences", []):
        rs = e.get("references", [])
        if rs and all(r in status and status[r][1] for r in rs):
            st_markup = badge(True, T("verified"))
        elif not rs:
            st_markup = badge(False, "", T("notcovered"))
        else:
            st_markup = badge(False, "", T("failedornot"))
        rows.append([e.get("id", ""), e.get("texte", ""), ", ".join(rs) or "-", markup_cell(st_markup)])
    s.append(table(rows, [1.7, 8.0, 4.8, 2.5]))
    all_ok = (all(_module_status(m) and m.get("result", {}).get("n_mismatch") == 0 for m in mods)
              and all(sc["passed"] for sc in st.get("scenarios", [])))
    s += [P(T("s5.5"), "h2"),
          PM(T("verdict", badge=badge(all_ok, T("compliant"), T("noncompliant")))),
          P(T("s5.limits"), "small")]
    return s


# ---------- Construction ----------

def build_reports(data: dict, out_dir: str, ask, languages=("fr",), author=None, email=None) -> list:
    """Construit les trois PDF dans chaque langue demandée ("fr", "en"). `ask(prompt) -> str` interroge le modèle de langage.
    `author` et `email` figurent sur la page de garde, en pied de page et dans les métadonnées du PDF."""
    os.makedirs(out_dir, exist_ok=True)
    import hashlib
    cache_path = os.path.join(out_dir, "llm_cache.json")
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            llm_cache = json.load(f)
    except (OSError, ValueError):
        llm_cache = {}
    raw_ask = ask

    def ask(prompt):            # un texte déjà rédigé pour exactement le même prompt n'est pas redemandé
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if key not in llm_cache:
            llm_cache[key] = raw_ask(prompt)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(llm_cache, f, ensure_ascii=False)
        return llm_cache[key]

    paths = []
    try:
        for lang in languages:
            set_lang(lang)
            d = localize(data, lang, ask)
            d["author"], d["email"] = author, email
            title = d["title"]
            print(f"📝 [{lang}] Rédaction de la spécification système...")
            try:
                sysspec = generate_system_spec(ask, d)
            except RuntimeError as e:
                print(f"⚠️  {e} : spécification système minimale utilisée.")
                sysspec = fallback_system_spec(d)
            strategies = {}
            for m in d["modules"] + ([d["integration"]] if d.get("integration") else []):
                print(f"📝 [{lang}] Commentaire de preuve : {m['name']}...")
                try:
                    strategies[m["name"]] = generate_proof_strategy(ask, m)
                except RuntimeError as e:
                    print(f"⚠️  {e}")
                    strategies[m["name"]] = {}

            def build(path, doc_type, parts, d=d, title=title):
                doc = Doc(path, f"{title} - {doc_type}", author=author, email=email, title=f"{title} - {doc_type}",
                          subject=doc_type, creator="Lean-C verification agent")
                story = cover(title, doc_type, d)
                for part in parts:
                    story += part()
                doc.multiBuild(story)
                return path

            name = re.sub(r"\W", "_", d.get("name", "projet"))
            spec_parts = [lambda: section_system(d, sysspec), lambda: section_lean(d, strategies), lambda: section_expected(d)]
            test_parts = [lambda: section_c(d), lambda: section_tests(d, sysspec)]
            paths += [build(os.path.join(out_dir, T("file.spec", name=name)), T("doc.spec"), spec_parts),
                      build(os.path.join(out_dir, T("file.test", name=name)), T("doc.test"), test_parts),
                      build(os.path.join(out_dir, T("file.full", name=name)), T("doc.full"), spec_parts + test_parts)]
    finally:
        set_lang("fr")
    return paths
