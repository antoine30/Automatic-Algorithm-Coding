#!/usr/bin/env python3
"""Génère les figures du README à partir du prototype de référence en virgule fixe (spur_pm_prototype.py).

  docs/spur_spectrum.png   spectre avant / après correction pour les quatre scénarios de projet_pm.json
  docs/spur_vs_beta.png    niveau de raie résiduel en fonction de l'indice de modulation beta (8 tirages de bruit par point)

Aucun appel à un modèle de langage, aucune compilation : seuls numpy et matplotlib sont nécessaires.
Usage :  python make_readme_figures.py [projet_pm.json]
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import spur_pm_prototype as P

RED, GREEN, GREY = "#b3261e", "#1b7f3b", "#6b7280"
OUT_DIR = "docs"


def run_block(beta, phi, amp, snr_db, seed, delta):
    """Un bloc complet : signal modulé -> corrélation -> estimation -> dérotation (arithmétique entière du prototype)."""
    re_, im_ = P.make_signal(beta, phi, amp, snr_db, seed=seed)
    bq, ur, ui = P.estimate(P.correlate(re_, im_, delta))
    o_re, o_im = P.derot_block(re_, im_, delta, ur, ui, bq)
    return re_, im_, o_re, o_im, bq


def spectrum_dbc(re_, im_):
    """Spectre normalisé à la porteuse (bin 0) : le niveau d'une raie se lit directement en dBc."""
    x = np.fft.fft(np.array(re_, float) + 1j * np.array(im_, float))
    return 20 * np.log10(np.maximum(np.abs(np.fft.fftshift(x)), 1e-9) / abs(x[0]))


def figure_spectra(cfg, path):
    n, cycles, amp, crit = cfg["n"], cfg["cycles"], cfg["amplitude"], cfg["criterion_dbc"]
    delta = (cycles * 2 ** 32) // n
    bins = np.arange(-n // 2, n // 2)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.2), sharex=True, sharey=True)
    for k, (ax, sc) in enumerate(zip(axes.flat, cfg["scenarios"]), 1):
        re_, im_, o_re, o_im, bq = run_block(sc["beta"], sc["phi"], amp, sc["snr_db"], k, delta)
        before, after = P.spur_dbc(re_, im_), P.spur_dbc(o_re, o_im)
        ax.plot(bins, spectrum_dbc(re_, im_), color=RED, lw=0.9, label="before correction")
        ax.plot(bins, spectrum_dbc(o_re, o_im), color=GREEN, lw=0.9, label="after correction")
        ax.axhline(crit, color=GREY, ls="--", lw=0.8)
        for h in (1, 2, 3):
            for sign in (-1, 1):
                ax.axvline(sign * h * cycles, color=GREY, lw=0.5, ls=":")
        ax.set_title(f"beta = {sc['beta']:g}  (estimated {bq / 65536:.4f})\nspur {before:+.1f} dBc  ->  {after:+.1f} dBc", fontsize=10.5)
        ax.set_xlim(-4 * cycles, 4 * cycles)
        ax.set_ylim(-125, 20)
        ax.grid(alpha=0.25)
        if k == 1:
            ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
            ax.text(-4 * cycles + 4, crit + 3, f"{crit:g} dBc criterion", fontsize=8, color=GREY)
    for ax in axes[1]:
        ax.set_xlabel(f"FFT bin (the spur is at +/-{cycles}, harmonics at +/-{2 * cycles} and +/-{3 * cycles})")
    for ax in axes[:, 0]:
        ax.set_ylabel("level relative to the carrier (dBc)")
    fig.suptitle(f"Phase-modulation spur removal: spectrum before / after  (N = {n}, SNR {cfg['scenarios'][0]['snr_db']} dB, "
                 "fixed point Q15/Q16)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=140)
    plt.close(fig)


def figure_vs_beta(cfg, path, draws=8):
    n, cycles, amp, crit = cfg["n"], cfg["cycles"], cfg["amplitude"], cfg["criterion_dbc"]
    delta = (cycles * 2 ** 32) // n
    betas = [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.2, 2.3]
    before, worst, median = [], [], []
    for beta in betas:
        afters = []
        for seed in range(1, draws + 1):
            re_, im_, o_re, o_im, _ = run_block(beta, 0.9, amp, 70, seed, delta)
            afters.append(P.spur_dbc(o_re, o_im))
            if seed == 1:
                before.append(P.spur_dbc(re_, im_))
        worst.append(max(afters))
        median.append(float(np.median(afters)))
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.plot(betas, before, "o-", color=RED, lw=1.4, ms=4, label="before correction")
    ax.plot(betas, worst, "o-", color=GREEN, lw=1.6, ms=4, label=f"after correction, worst of {draws} noise draws")
    ax.plot(betas, median, "-", color=GREEN, lw=0.9, alpha=0.6, label="after correction, median")
    ax.axhline(crit, color=GREY, ls="--", lw=0.9)
    ax.text(0.05, crit + 2.5, f"{crit:g} dBc criterion (0.02 <= beta <= 2)", fontsize=8.5, color=GREY)
    ax.axvline(2.405, color=GREY, ls=":", lw=0.9)
    ax.text(2.39, -112, "validity limit\n(first zero of J0)", fontsize=8, color=GREY, ha="right")
    ax.axvspan(0.02, 2.0, color=GREEN, alpha=0.05)
    ax.set_xlabel("modulation index beta")
    ax.set_ylabel("residual spur level (dBc)")
    ax.set_ylim(-118, 20)
    ax.set_xlim(0, 2.5)
    ax.grid(alpha=0.25)
    ax.legend(loc="center right", bbox_to_anchor=(0.995, 0.48), fontsize=8.5)
    ax.set_title("Residual spur versus modulation index (SNR 70 dB, N = %d)" % n, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return dict(zip(betas, zip(before, worst, median)))


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "projet_pm.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)["system_tests"]
    P.N, P.M_CYC = cfg["n"], cfg["cycles"]
    os.makedirs(OUT_DIR, exist_ok=True)
    figure_spectra(cfg, os.path.join(OUT_DIR, "spur_spectrum.png"))
    table = figure_vs_beta(cfg, os.path.join(OUT_DIR, "spur_vs_beta.png"))
    print("docs/spur_spectrum.png et docs/spur_vs_beta.png écrits.")
    print("beta : avant / pire cas après / médiane après (dBc)")
    for beta, (b, w, m) in table.items():
        print(f"  {beta:5g} : {b:7.1f} / {w:7.1f} / {m:7.1f}")


if __name__ == "__main__":
    main()
