#!/usr/bin/env python3
"""Rend les formules du README avec le vrai LaTeX, en images PNG transparentes (docs/eq/).

Pourquoi des images ? Le LaTeX écrit entre « $$ » dans un README n'est affiché que par certaines visionneuses (GitHub le fait, beaucoup d'éditeurs
et d'applications non). Une image s'affiche à l'identique partout. Chaque formule existe en deux versions : texte noir (thème clair) et texte
blanc (thème sombre de GitHub, choisi par la balise <picture>).

Les images sont déjà dans le dépôt : ce script n'est nécessaire que pour modifier une formule. Il demande pdflatex (avec amsmath et standalone)
et pdftocairo (poppler).

Usage :  python make_equations.py
"""

import os
import re
import subprocess
import tempfile

OUT_DIR = os.path.join("docs", "eq")
DISPLAY_SCALE = 1.35        # taille d'affichage des formules par rapport au texte courant

# nom : (source LaTeX en mode display, texte alternatif lisible sans rendu)
EQUATIONS = {
    "eq_model": (
        r"r[k] \;=\; C\,e^{\,j\beta\sin(2\pi D k+\varphi)} \;=\; C\sum_{n=-\infty}^{+\infty} J_n(\beta)\,e^{\,jn\,(2\pi D k+\varphi)}",
        "r[k] = C exp(j β sin(2π D k + φ)) = C Σ J_n(β) exp(j n (2π D k + φ))",
    ),
    "eq_corr": (
        r"c_n \;=\; \frac{1}{N}\sum_{k=0}^{N-1} r[k]\,e^{-jn\,2\pi D k} \;=\; C\,J_n(\beta)\,e^{\,jn\varphi}",
        "c_n = (1/N) Σ r[k] exp(-j n 2π D k) = C J_n(β) exp(j n φ)",
    ),
    "eq_bessel": (
        r"J_0(\beta)+J_2(\beta) \;=\; \frac{2}{\beta}\,J_1(\beta)",
        "J_0(β) + J_2(β) = (2/β) J_1(β)",
    ),
    "eq_beta": (
        r"\beta \;=\; \frac{2\,\lvert c_1\rvert}{\lvert c_0\rvert+\lvert c_2\rvert}",
        "β = 2 |c_1| / (|c_0| + |c_2|)",
    ),
    "eq_phase": (
        r"e^{\,j\varphi} \;=\; \frac{c_1\,\overline{c_0}}{\lvert c_1\,\overline{c_0}\rvert}",
        "exp(j φ) = c_1 conj(c_0) / |c_1 conj(c_0)|",
    ),
    "eq_derot": (
        r"r'[k] \;=\; r[k]\;e^{-j\beta\sin(2\pi D k+\varphi)} \;=\; C",
        "r'[k] = r[k] exp(-j β sin(2π D k + φ)) = C",
    ),
    "eq_q16": (
        r"\begin{aligned}"
        r"m_n &= \Big\lfloor \sqrt{\,\mathrm{Re}(c_n)^2+\mathrm{Im}(c_n)^2\,}\Big\rfloor \\[4pt]"
        r"\beta_{Q16} &= \begin{cases} 0 & \text{if } m_0+m_2=0,\\[2pt]"
        r"\min\!\Big(196608,\ \Big\lfloor \dfrac{131072\;m_1}{m_0+m_2} \Big\rfloor\Big) & \text{otherwise.} \end{cases}"
        r"\end{aligned}",
        "m_n = floor(sqrt(Re(c_n)^2 + Im(c_n)^2)); beta_Q16 = 0 if m_0 + m_2 = 0, otherwise min(196608, floor(131072 m_1 / (m_0 + m_2)))",
    ),
}

TEMPLATE = r"""\documentclass[12pt,border=5pt]{standalone}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\begin{document}
\color{%(color)s}$\displaystyle
%(body)s
$
\end{document}
"""


def render(name, body, color, out_png):
    with tempfile.TemporaryDirectory() as tmp:
        tex = os.path.join(tmp, f"{name}.tex")
        with open(tex, "w", encoding="utf-8") as f:
            f.write(TEMPLATE % dict(color=color, body=body))
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", tmp, tex],
                           capture_output=True, text=True, timeout=120)
        pdf = os.path.join(tmp, f"{name}.pdf")
        if r.returncode != 0 or not os.path.isfile(pdf):
            raise RuntimeError(f"pdflatex a échoué pour {name} :\n{r.stdout[-800:]}")
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        w_pt = float(re.search(r"Page size:\s+([\d.]+) x", info).group(1))
        subprocess.run(["pdftocairo", "-png", "-transp", "-r", "400", "-singlefile", pdf, out_png[:-4]], check=True)
        return w_pt


def snippet(name, alt, width_px, indent=""):
    """Balises HTML d'une formule centrée : version claire par défaut, version blanche pour le thème sombre."""
    return (f'{indent}<p align="center">\n'
            f'{indent}  <picture>\n'
            f'{indent}    <source media="(prefers-color-scheme: dark)" srcset="docs/eq/{name}_dark.png">\n'
            f'{indent}    <img src="docs/eq/{name}.png" alt="{alt}" width="{width_px}">\n'
            f'{indent}  </picture>\n'
            f'{indent}</p>')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    widths = {}
    for name, (body, alt) in EQUATIONS.items():
        w_pt = render(name, body, "black", os.path.join(OUT_DIR, f"{name}.png"))
        render(name, body, "white", os.path.join(OUT_DIR, f"{name}_dark.png"))
        widths[name] = round(w_pt * 96 / 72 * DISPLAY_SCALE)   # 12 pt de LaTeX = 16 px à l'écran ; les formules affichées sont agrandies pour la lisibilité
        print(f"{name:10s} {widths[name]:4d} px")
    with open(os.path.join(OUT_DIR, "snippets.html"), "w", encoding="utf-8") as f:
        for name, (body, alt) in EQUATIONS.items():
            f.write(f"<!-- {name} -->\n{snippet(name, alt, widths[name])}\n\n")
    print(f"images et docs/eq/snippets.html écrits dans {OUT_DIR}/")


if __name__ == "__main__":
    main()
