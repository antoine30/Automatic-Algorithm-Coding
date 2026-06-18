# Jammer Detection — Barrage Noise (Single Antenna)

Detect and suppress a **barrage noise jammer** (wideband, circularly-symmetric
Gaussian interference) on a single receive antenna, then recover the useful
signal. This folder holds the **specification** (`spec/`) and the **derived
requirements** (`req/`); implementation is generated from the requirements.

## What a barrage jammer is (and why it is detectable)

A barrage jammer floods the band with Gaussian noise, raising the effective
noise floor (`σ²_eff = σ²_n + σ²_J`) and driving `SINR = SNR/(1+JNR) → 0`. It is
the most common jammer — and the most **geometrically transparent**: it leaves
no coherent imprint in the spaces that characterise real waveforms. It maps to
the *trivial point* everywhere:

| Analysis space | Structured signal | Barrage noise |
|----------------|-------------------|---------------|
| Cyclostationary | cyclic lines at α ∈ A_s | zero (α ≠ 0) |
| HOS cumulants | C̃42, C̃63 ≠ 0 | 0 |
| Time-frequency | ridges / carriers | flat surface |
| Information geometry | low entropy | maximum entropy |
| AR poles | near unit circle | drift inward |

Because detection uses **normalised** (shape, not power) statistics, the jammer
cannot hide by calibrating its power: e.g. `C̃42^y = C̃42^s/(1+JNR)²`. The
composite detector works down to **−13 dB JNR** with **< 5 ms** latency.

## The two tasks

1. **Detection** (always-on). A shared front-end computes six signature features
   per window; three pillars (SNN, CNN, Temporal-MP) feed a fused, CFAR-thresholded
   statistic `Λ_BN`. On H1 it also estimates `σ̂²_J`, `B̂_J`, `t̂_on`.
2. **Suppression** (activated on detection). A mode policy selects a filter —
   Wiener/MMSE, FRESH cyclic Wiener, or adaptive spectral subtraction — to
   recover the signal, using the detection estimates and a jammer-free reference.

The two tasks are decoupled and communicate only through a typed
`DetectionResult` (see `req/LLR_BAR_010`).

```
IQ ─► [front-end: F1..F6] ─► [Detection: SNN|CNN|MP → CFAR] ─DetectionResult─► [Suppression: Wiener|FRESH|SpecSub] ─► ŝ(t)
```

## Folder layout

```
jammer_detection/
├── README.md                         ← this file
├── spec/                             ← the specification (adjacent to req/)
│   ├── barrage_noise_spec.md         ← source spec (transcribed): signal model,
│   │                                   7 signature components, 3-pillar detector,
│   │                                   detection-to-filtering pipeline
│   └── barrage_architecture.md       ← proposed two-task software architecture
└── req/                              ← requirements derived from the spec
    ├── MASTER.md                     ← rules, generation order, traceability
    ├── HLR_BAR_001_system.md         ← high-level system requirements
    ├── LLR_BAR_010_common_types.md   ← DetectionResult contract + enums
    ├── LLR_BAR_020_frontend_features.md ← windowing + 6 feature extractors
    ├── LLR_BAR_030_detection.md      ← Task 1: pillars + fused CFAR
    └── LLR_BAR_040_suppression.md    ← Task 2: Wiener / FRESH / spectral sub
```

## How to read it

- Start with [`spec/barrage_noise_spec.md`](spec/barrage_noise_spec.md) for the
  theory (the *why*), then [`spec/barrage_architecture.md`](spec/barrage_architecture.md)
  for the software design (the *how*).
- The [`req/`](req/) folder turns the spec into verifiable Low-Level Requirements,
  one module per LLR, each with an interface, constraints, and **Test
  Requirements**. Generation order and traceability are in
  [`req/MASTER.md`](req/MASTER.md).

## Key targets (from the spec)

| Quantity | Value |
|----------|-------|
| Composite detection floor | −13 dB JNR |
| Composite detection latency | < 5 ms |
| Normalised cumulant dilution | C̃42^y = C̃42^s/(1+JNR)² |
| Wiener residual JNR | −10·log₁₀(1+JNR/SNR) |
| Spectral-subtraction improvement | ~ −15 dB |
| Oversubtraction factor β | 1.2 – 2.0 |

## Conventions

C++17, single receive antenna, real-time DSP. No dynamic allocation after init
(static buffers, fixed `K_max`), no exceptions, fixed-width integer types,
Doxygen on public methods — consistent with the sibling `code/` (event-driven
RTOS) and `Algo/` (Q4.27 fixed-point) projects in this repository.

## Status

Specification and requirements complete. Implementation (`src/`, `test/`) not yet
generated — it would follow the `req/MASTER.md` order: types → front-end →
detection → suppression, with host-compilable unit tests per LLR.
