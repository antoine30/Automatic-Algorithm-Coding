# Barrage Noise Jammer — Detection & Suppression Architecture

Derived from *Barrage Noise Jammer — Single-Antenna Detection* (A. Damon, 2026).
Two cooperating tasks: **Task 1 — Detection** and **Task 2 — Suppression**, sharing
a common feature front-end and a typed contract.

Key idea extracted from the document: barrage noise is **geometrically
transparent** — it maps to the *trivial point* in every analysis space (zero
cyclic spectrum, zero higher-order cumulants, maximum entropy, flat TF surface,
inward AR poles). Detection = "has the signal's structure been diluted toward
the trivial point?". Suppression = "the jammer has *no* cyclic structure, so the
signal can be recovered from its cyclic support."

---

## 0. Top-level dataflow

```
                IQ stream y(t) = h·s + j_BN + n
                          │
            ┌─────────────▼──────────────┐
            │  FRONT-END (shared)         │  windowing, analytic signal,
            │  feature extractors F1..F6  │  per-window features
            └─────────────┬──────────────┘
                          │ feature vector φ(t)
          ┌───────────────▼───────────────┐
TASK 1 →  │  DETECTION (3-pillar + CFAR)   │ → decision Λ_BN, ξ
          │  SNN ┆ CNN ┆ Temporal-MP        │   estimates {σ̂²_J, B̂_J, t̂_on}
          └───────────────┬───────────────┘
                          │  DetectionResult (contract)
          ┌───────────────▼───────────────┐
TASK 2 →  │  SUPPRESSION (mode-selected)   │ → ŝ(t) recovered signal
          │  Wiener ┆ FRESH ┆ Spec-Sub      │
          └────────────────────────────────┘
```

The two tasks run concurrently: detection is always-on; suppression activates
when `Λ_BN > η_CFAR` and consumes detection's parameter estimates.

---

## 1. Shared front-end — the 6 signature extractors

One module per signature component of the document (§2). Each consumes the
current window and emits a scalar/score; all are jammer-vs-signal *contrast*
measures that move toward the "trivial point" under barrage.

| ID | Module | Feature (H0 → H1 trend) | Source |
|----|--------|--------------------------|--------|
| F1 | `CyclicCoherence` | `Λcyc = mean_α ∫|γ_y^α(f)|² df` → 0 (uniform collapse over all α) | §2.1, §3 |
| F2 | `HosCumulants` | normalised `|C̃42|`, joint `(C̃42,C̃63)` trajectory → (0,0) | §2.2 |
| F3 | `AmplitudePdf` | Rician K-factor `K̂ = M̂10²/(2(M̂20−M̂10²))` → 0 (Rice→Rayleigh) | §2.3 |
| F4 | `WignerVille` | TF Rényi entropy `Hα(W_y)` ↑ ; spectral flatness SFM → 1 | §2.4 |
| F5 | `ArPoleGeometry` | mean pole radius `r̄ = (1/p)Σ|z_k|` ↓ (inward), reflection coeffs → 0 | §2.5 |
| F6 | `InfoGeometry` | Jensen–Shannon `D_JS(p_t‖p_{t−1})`: spike→**plateau** (vs fading: spike→baseline) | §2.6 |

Front-end also maintains a **jammer-free reference** `Ŝ⁰_s(f)` (rolling PSD of
the most recent pre-onset window) — required by Task 2.

---

## 2. Task 1 — Detection subsystem (three-pillar + fused CFAR)

Mirrors the document's "Optimal Composite Detector" (§3).

```
        φ(t)
   ┌─────┴───────────────────────────────────────┐
   ▼                    ▼                          ▼
┌───────────┐    ┌──────────────┐         ┌────────────────┐
│ SNN pillar│    │  CNN pillar  │         │ Temporal-MP    │
│ (temporal)│    │ (TF/spatial) │         │ (persistence)  │
├───────────┤    ├──────────────┤         ├────────────────┤
│ Ĉ42(t)    │    │ |γ^α(f)| map │         │ sustained D_JS │
│ step-down │    │ Hα(W_y) ↑    │         │ plateau (rules │
│ cyclic-pop│    │ r̄ inward     │         │ out fading)    │
│ rate drop │    │ SFM → 1      │         │                │
│ K̂ step    │    │              │         │                │
└─────┬─────┘    └──────┬───────┘         └───────┬────────┘
      └──────────┬──────┴──────────────────────────┘
                 ▼  fused, weights learned (multi-task)
     Λ_BN = w1·Λcyc + w2·|C̃42| + w3·H_TF + w4·r̄_poles⁻¹
                 ▼  CFAR threshold (constant P_FA)
        decision H1/H0  +  {σ̂²_J, B̂_J, t̂_on}
```

- **SNN** (neuromorphic, sub-Nyquist): tracks running statistics as spike
  trains — `Ĉ42(t)` step-down, *uniform* firing-rate drop across **all** cyclic
  populations `α_k` (this uniformity is the barrage fingerprint vs spot jamming),
  Rician `K̂` step-down.
- **CNN** (on log-polar WVD / coherence map): global cyclic-coherence collapse,
  Rényi-entropy elevation, inward AR-pole drift, SFM → 1.
- **Temporal-MP**: aggregates `D_JS` across windows; confirms a *sustained*
  elevated plateau (broadband sustained interference), rejecting multipath
  fading (spike-then-baseline).
- **Fusion + CFAR**: equivariant fusion head, learned weights `w_k`; CFAR keeps
  `P_FA` constant regardless of noise power. Composite reaches **−13 dB JNR**,
  latency **< 5 ms** (§3 summary table).

**Parameter estimation** (feeds Task 2, §4.1):
`σ̂²_J` from cumulant dilution ratio, `B̂_J` from SFM flatness extent, `t̂_on`
from the SNN onset spike event.

---

## 3. Detection→Suppression contract

The only coupling between the two tasks — a typed message emitted per decision:

```cpp
struct DetectionResult {
    bool      jammerActive;     // Λ_BN > η_CFAR
    float     lambdaBN;         // composite statistic
    float     jnrEstimateDb;    // from cumulant dilution
    float     sigma2J;          // σ̂²_J  estimated jammer power
    float     bandwidthJ;       // B̂_J   estimated jammer bandwidth
    uint64_t  onsetTick;        // t̂_on  jamming onset time
    const float* refPsd;        // Ŝ⁰_s(f) jammer-free reference (pre-onset)
    const float* cyclicSupport; // A_s    signal cyclic frequencies (for FRESH)
};
```

This keeps the tasks decoupled: detection never filters, suppression never
re-derives statistics.

---

## 4. Task 2 — Suppression subsystem (mode-selected filter chain)

Mirrors the document's "Detection-to-Filtering Pipeline" (§4). A **mode
selector** picks the filter per the latency / fidelity trade-off (§4.5):

```
DetectionResult ─► [Mode selector] ─► one of:

  (A) Wiener / MMSE      H_W(f) = S⁰_s / (S⁰_s + σ̂²_J/B̂_J + σ²_n)   §4.2
        low latency (<1 ms), mild distortion (H_W<1), needs Ŝ⁰_s reference.

  (B) FRESH (cyclic Wiener)  ŝ = Σ_{α∈A_s} ∫ H^α(f) S_y^α(f) e^{j2π(f+α)t} df  §4.3
        exploits disjoint cyclic supports; ~zero distortion, perfect as T→∞,
        higher latency (10–100 ms). Best when A_s is known/stable.

  (C) Adaptive spectral subtraction (runtime)                          §4.4
        Ŝ⁰_J(f,t) = λ Ŝ⁰_J(f,t−1) + (1−λ)|Y|²·1[Λ>η]
        ŝ = F⁻¹[ max(|Y|²−β Ŝ⁰_J, ε)^½ · e^{j∠Y} ],  β∈[1.2,2]
        short-window real-time, ~−15 dB, mild musical-noise (oversubtraction).
```

| Mode | Residual JNR | Distortion | Latency | When |
|------|--------------|-----------|---------|------|
| Wiener | `−10log₁₀(1+JNR/SNR)` | mild | < 1 ms | default, reference available |
| FRESH | → −∞ (theoretic) | none | 10–100 ms | stable `A_s`, latency-tolerant |
| Spec-sub | −15 dB | mild artefacts | < 5 ms | no clean reference / fast adapt |

Selector policy: prefer **FRESH** when `A_s` known and latency budget allows;
fall back to **Wiener** when a clean pre-onset `Ŝ⁰_s` exists; use **spectral
subtraction** otherwise / for fastest adaptation.

---

## 5. Module breakdown (LLR-ready)

| Module | Task | Responsibility |
|--------|------|----------------|
| `SignalWindower` | shared | framing, analytic signal, reference PSD buffer |
| `CyclicCoherence` (F1) | shared | CAF/SCF, `Λcyc` |
| `HosCumulants` (F2) | shared | normalised `C̃42/C̃63` |
| `AmplitudePdf` (F3) | shared | Rician K-factor tracker |
| `WignerVille` (F4) | shared | WVD, Rényi entropy, SFM |
| `ArPoleGeometry` (F5) | shared | Burg AR, pole radius, reflection coeffs |
| `InfoGeometry` (F6) | shared | `D_JS` trajectory |
| `SnnPillar` / `CnnPillar` / `TemporalMp` | T1 | three detection pillars |
| `FusionCfar` | T1 | weighted fusion + CFAR decision + estimates |
| `WienerFilter` / `FreshFilter` / `SpectralSubtractor` | T2 | three suppressors |
| `SuppressionSelector` | T2 | mode policy, applies chosen filter |
| `DetectionResult` | contract | typed hand-off T1 → T2 |

---

## 6. Concurrency & timing model (RTOS mapping)

Fits the event-driven, no-malloc, fixed-point conventions of this repo
(`code/` task model, `Algo/` Q4.27 arithmetic):

- **DetectionTask** (high priority): per-window, always-on. Budget ≈ the
  document's latencies (cyclic 5 ms, kurtosis 10 ms, MP 20 ms) → emits
  `DetectionResult` on an event queue.
- **SuppressionTask** (real-time priority): consumes `DetectionResult`; when
  active, filters the live buffer. Wiener/spec-sub meet <5 ms; FRESH runs on a
  larger window when its latency budget is acceptable.
- Static buffers only (ring buffer for reference PSD, fixed `A_s` table,
  `K_max`-style caps). No dynamic allocation in steady state.
- Event-driven hand-off reuses the `IEvent`/queue pattern already in `code/`:
  detection posts a `JammerStateEvent`, suppression's handler switches mode.

---

## 7. What the architecture exploits (rationale, from the doc)

- Detection works at very low JNR because it measures **normalised** (shape)
  statistics, not power: `C̃42^y = C̃42^s/(1+JNR)²` — a 17.5 % kurtosis drop at
  −10 dB JNR, well above threshold for N>10³ samples.
- The **uniform** collapse across *all* cyclic frequencies is unique to barrage
  (CW/chirp/DRFM are themselves cyclostationary) — this is the discriminating
  feature, carried by the SNN's all-population rate drop.
- Suppression is feasible because `S_y^α(f) = S_s^α(f) ∀α≠0`: the jammer adds
  nothing to the cyclic spectrum, so FRESH recovers `s` from its cyclic support.
