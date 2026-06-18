# Barrage Noise Jammer — Single-Antenna Detection (Source Specification)

> Faithful Markdown transcription of the source system specification
> *Barrage Noise Jammer — Wideband Gaussian Noise Flooding*, A. Damon, 2026
> (Single-Antenna Jamming Detection Series — Electronic Warfare). The original
> was delivered as a PDF; this transcription preserves the technical content,
> equations, and tables used to derive the requirements in `../req/`.

- **Threat level:** HIGH — ubiquitous, most common jammer
- **Scope:** single receive antenna
- **Framework:** SNN + CNN + Temporal MP
- **Author:** Antoine DAMON — Antoine.Damon@laposte.net — 2026

---

## Abstract
The barrage noise jammer floods the receiver with wideband Gaussian-like noise,
raising the effective noise floor across the entire operating band. It is the
simplest, most common jammer — yet the most geometrically detectable: it is
provably incapable of replicating, simultaneously, the cyclostationary
structure, the non-Gaussian cumulants, and the structured time-frequency (TF)
geometry of any digital waveform. Detection is shown down to −10 dB JNR (−13 dB
composite).

**Geometric transparency.** A jammer is *geometrically transparent* when it
leaves no coherent imprint in the statistical spaces used to characterise
legitimate waveforms. Barrage noise occupies bandwidth and raises the floor, yet
is invisible in the cyclostationary domain, the higher-order cumulant manifold,
and the information-geometric sense — an intrinsic property of the Gaussian
distribution that no physical transmitter can circumvent.

---

## 1. Signal Model
```
y(t) = h(t)·s(t) + j_BN(t) + n(t)
j_BN(t) ~ CN(0, σ²_J),   S⁰_J(f) ≈ σ²_J / B_J  for all f in [fc − B_J/2, fc + B_J/2]
```
Key properties of `j_BN`:
- Circularly-symmetric Gaussian: C42^j = 0, C63^j = 0
- No periodicity: R_j^α(τ) = 0 ∀ α ≠ 0 (not cyclostationary)
- Maximum entropy for given power: H(j) = log(πe σ²_J)
- Power spectral density: flat over B_J

Effective noise floor and SINR:
```
σ²_eff = σ²_n + σ²_J
SINR = σ²_s / (σ²_n + σ²_J) = SNR / (1 + JNR)  →  SNR/JNR → 0   (JNR ≫ 1)
```

---

## 2. Separation via 7 Signature Components

Where the signal `s(t)` is structured, the barrage maps to the *trivial point*:

| Mathematical space | Signal s(t) | Barrage j_BN(t) |
|--------------------|-------------|-----------------|
| Cyclostationary domain | S_s^α(f) ≠ 0 at α ∈ A_s | S_j^α(f) = 0 ∀ α ≠ 0 |
| Cumulant manifold | C42^s ≠ 0, C63^s ≠ 0 | C42^j = 0, C63^j = 0 |
| Time-frequency plane | structured (ridges, carriers, hops) | uniform white surface |
| Information geometry | low entropy, structured covariance | maximum entropy log(πeσ²_J) |
| AR pole geometry | poles near unit circle | poles collapse inward |

### 2.1 Cyclostationarity (definitive separator)
Cyclic autocorrelation `R_s^α(τ)` is non-zero at discrete cyclic frequencies
α = k/T0 for a cyclostationary signal; barrage is strictly stationary so
`R_j^α(τ) = 0 ∀ α ≠ 0`. Adding barrage dilutes but does not destroy cyclic
features: `S_y^α(f) = S_s^α(f)` (unchanged), `S_y^0(f) = S_s^0(f) + σ²_J/B_J`.
Cyclic coherence collapse:
```
|γ_y^α(f)|² = |S_s^α(f)|² / (S_s^0(f) + σ²_J/B_J)²  → 0   as JNR → ∞
```
The collapse is **uniform across all** cyclic frequencies — the barrage
fingerprint (CW/chirp/DRFM are themselves cyclostationary). Detector:
`Λcyc = (1/|A_s|) Σ_{α∈A_s} ∫ |γ_y^α(f)|² df  ≷ ξ_th`.

### 2.2 Higher-order cumulants (Gaussianisation)
Gaussian noise has all cumulants of order ≥ 3 identically zero. Cumulants are
additive over independent variables, so `C42^y = C42^s` (unnormalised,
unchanged), but the **normalised** cumulant divides by total variance:
```
C̃42^y = C42^y / (Var[y])² = C̃42^s / (1 + JNR)²
C̃63^y = C̃63^s / (1 + JNR)³
```
The pair `(C̃42, C̃63)` traces a straight line to the Gaussian point (0,0); the
direction is modulation-specific. Detector: `Λkurt = |C̃42^y| ≷ κ_th`.

Dilution rates by modulation:

| Modulation | |C̃42^s| | |C̃63^s| | Min detectable JNR | CFAR threshold |
|------------|---------|---------|--------------------|----------------|
| BPSK | 2.0 | 16.0 | −3 dB | κ = 1.0 |
| QPSK | 1.0 | 4.0 | 0 dB | κ = 0.5 |
| 16QAM | 0.68 | 0.62 | +3 dB | κ = 0.34 |
| OFDM | 0 | 0 | N/A (use cyclic test) | — |

### 2.3 Analytic-signal amplitude PDF
Instantaneous amplitude transitions Rice/Nakagami → Rayleigh under barrage;
Rician K-factor K = ν_s²/(2σ²_eff) → 0. Tracked via moment ratio
`K̂ ≈ M̂10² / (2(M̂20 − M̂10²))`; a step-down at onset is a barrage cue.

### 2.4 Wigner-Ville distribution (spectral flatness)
`W_y = W_s + W_j`, with `W_j ≈ (σ²_J/B_J)·Π_{B_J}(f − fc)` a uniform flat
background → TF Rényi entropy `Hα(W_y)` rises monotonically with JNR; spectral
flatness measure (SFM) → 1.

### 2.5 AR pole geometry (inward pole drift)
Adding broadband noise raises the prediction-error floor; Burg poles drift
toward the origin: mean radius `r̄ = (1/p)Σ|z_k|` decreases monotonically;
reflection coefficients `k_m` → 0 (white process).

### 2.6 Information geometry (sustained maximum-entropy)
Jensen-Shannon divergence between consecutive windows `D_JS(p_t‖p_{t−1})`: small
under H0; a spike at onset then a **sustained elevated plateau** under barrage
(vs fading's spike-then-baseline). Temporal MP propagates this trajectory.

### Why detectable below −10 dB JNR
Normalised statistics measure *shape*, not scale. For BPSK `C̃42^s = 2.0`; at
JNR = −10 dB (0.1 linear), `C̃42^y = 2.0/(1.1)² ≈ 1.65` — a 17.5 % drop, well
above threshold for N > 10³ samples. Cyclic coherence collapses even more
sensitively (down to −13 dB combined across α ∈ A_s).

---

## 3. Three-Pillar Composite Detector
- **SNN tracks:** running Ĉ42(t) step-down; firing rate of all cyclic-frequency
  populations (uniform drop across all α_k — distinguishes barrage from spot
  jamming); Rician K-factor step-down.
- **CNN extracts:** cyclic coherence map |γ_y^α(f)| (global collapse); TF Rényi
  entropy elevation; average AR pole radius (inward drift); SFM → 1.
- **Temporal MP aggregates:** sustained D_JS plateau (rules out fading).

Fused CFAR decision:
```
Λ_BN = w1·Λcyc + w2·|C̃42| + w3·H_TF + w4·r̄_poles⁻¹   ≷  η_CFAR
```
Weights `w_k` learned by an equivariant fusion head (multi-task training).

**Performance summary:**

| Feature | H0 value | H1 trend | Min JNR | Latency |
|---------|----------|----------|---------|---------|
| Cyclic coherence \|γ^α\|² | > 0 (modulation) | → 0 monotone | −10 dB | 5 ms |
| Normalised kurtosis \|C̃42\| | 2.0 (BPSK) | ↓ (1+JNR)⁻² | −3 dB | 10 ms |
| TF Rényi entropy Hα | low (structured) | ↑ uniform | −8 dB | 5 ms |
| D_JS sustained plateau | ≈ 0 | ↑ persistent | −12 dB | 20 ms |
| AR pole radius r̄ | near 1 | ↓ inward | −6 dB | 2 ms |
| Composite Λ_BN | nominal | elevated | **−13 dB** | **< 5 ms** |

---

## 4. Detection-to-Filtering Pipeline (recovering the useful signal)

**Step 1 — Detection decision.** Once `Λ_BN > η_CFAR`, declare the jammer active
and expose: σ̂²_J (from cumulant dilution ratio), B̂_J (from SFM flatness extent),
t̂_on (SNN onset spike).

**Step 2 — Wiener / MMSE estimator.**
```
Ŝ(f) = H_W(f)·Y(f),   H_W(f) = S⁰_s(f) / (S⁰_s(f) + σ̂²_J/B̂_J + σ²_n) ∈ [0,1]
```
`S⁰_s(f)` estimated from a jammer-free reference window before t̂_on.

**Step 3 — Cyclostationary reconstruction (FRESH).** Since `S_y^α(f) = S_s^α(f)
∀ α ≠ 0`:
```
ŝ(t) = Σ_{α∈A_s} ∫ H^α(f) S_y^α(f) e^{j2π(f+α)t} df
```
Separation → perfect as T → ∞ (disjoint cyclic supports).

**Step 4 — Adaptive spectral subtraction (runtime).**
```
Ŝ⁰_J(f,t) = λ·Ŝ⁰_J(f,t−1) + (1−λ)·|Y(f,t)|²·1[Λ>η]
ŝ(t) = F⁻¹[ max(|Y(f,t)|² − Ŝ⁰_J(f,t), ε)^{1/2} · e^{j∠Y(f,t)} ]
```
Oversubtraction `β ∈ [1.2, 2.0]` suppresses musical-noise artefacts.

**Step 5 — Performance after filtering:**

| Method | Residual JNR | Signal distortion | Latency |
|--------|--------------|-------------------|---------|
| No filtering | JNR_in | none | 0 |
| Wiener filter | −10log₁₀(1+JNR/SNR) | mild (H_W < 1) | < 1 ms |
| FRESH filter | → −∞ (theoretic) | none | 10–100 ms |
| Spectral subtraction | −15 dB improvement | mild artefacts | < 5 ms |
