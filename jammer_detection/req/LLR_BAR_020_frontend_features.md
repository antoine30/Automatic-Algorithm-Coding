# LLR_BAR_020 — Shared Feature Front-End (6 Signature Components)

## Level : LOW LEVEL
## Parent HLR : HLR_BAR_001
## Depends on : LLR_BAR_010

## Files to Generate
- src/frontend/FeatureFrontEnd.h
- src/frontend/FeatureFrontEnd.cpp
- tests/test_feature_frontend.cpp

---

## 1. Purpose
Per analysis window, extract the six signature features that distinguish a
structured signal from circularly-symmetric Gaussian barrage noise (source §2).
Each feature is a *contrast* statistic that moves toward the Gaussian /
maximum-entropy "trivial point" under barrage. Also maintain a jammer-free
reference PSD for the suppression task.

---

## 2. Windowing
| Property            | Specification                          |
|---------------------|----------------------------------------|
| Input               | complex IQ samples (analytic signal)   |
| Window length N     | configurable, ≤ 1024, power of two     |
| Overlap             | configurable (default 50%)             |
| Reference PSD       | rolling estimate of last pre-onset window (Ŝ⁰_s) |

---

## 3. Feature Extractors (one operation group each)

### F1 — Cyclic coherence (the definitive separator, §2.1)
- Compute the spectral correlation `S_y^α(f)` / cyclic coherence
  `|γ_y^α(f)|² = |S_y^α(f)|² / (S_y^0(f+α/2) S_y^0(f−α/2))`.
- Output `Λcyc = (1/|A_s|) Σ_{α∈A_s} ∫ |γ_y^α(f)|² df`.
- H0: > 0 at signal cyclic frequencies; H1: → 0, uniform collapse over all α.

### F2 — Higher-order cumulants (§2.2)
- Normalised fourth-order cumulant `C̃42 = C42 / (Var[y])²`, and `C̃63`.
- H0: `|C̃42|` = 2.0 (BPSK), 1.0 (QPSK), 0.68 (16QAM); H1: `C̃42^y = C̃42^s/(1+JNR)²` → 0.
- Joint `(C̃42, C̃63)` trajectory toward (0,0) along a modulation-specific line.

### F3 — Analytic-signal amplitude PDF (§2.3)
- Rician K-factor estimate `K̂ = M̂10² / (2(M̂20 − M̂10²))` from amplitude moments.
- H0: Rician (K>0); H1: → Rayleigh (K → 0).

### F4 — Wigner-Ville flatness (§2.4)
- TF Rényi entropy `Hα(W_y)` and spectral flatness measure (SFM).
- H0: low entropy / structured ridges; H1: entropy ↑, SFM → 1 (flat surface).

### F5 — AR pole geometry (§2.5)
- Burg AR model order p; mean pole radius `r̄ = (1/p) Σ_k |z_k|`; reflection
  coefficients `k_m`.
- H0: poles near unit circle (`r̄` → 1); H1: poles drift inward (`r̄` ↓), `k_m` → 0.

### F6 — Information geometry persistence (§2.6)
- Jensen-Shannon divergence between consecutive window PDFs
  `D_JS(p_t ‖ p_{t−1})`.
- H0: small/stationary; H1 onset: spike; H1 sustained: elevated **plateau**
  (distinguishes barrage from fading's spike-then-baseline).

---

## 4. Interface
```cpp
struct FeatureVector {
    float lambdaCyc;     // F1
    float cTilde42;      // F2
    float cTilde63;      // F2
    float kFactor;       // F3
    float renyiEntropy;  // F4
    float spectralFlatness; // F4 (→ 1 under barrage)
    float poleRadius;    // F5
    float dJsPlateau;    // F6 (sustained level)
};

class FeatureFrontEnd {
public:
    void  configure(uint32_t windowLen, const float* cyclicSupport, uint32_t nAlpha);
    DetStatus process(const float* iBuf, const float* qBuf, uint32_t len,
                      FeatureVector& out);
    const float* referencePsd(uint32_t& lenOut) const; // Ŝ⁰_s
    void  reset();
};
```

---

## 5. Constraints
- Float permitted (front-end analysis runs once per window, not a tight ADC loop).
- Static buffers sized by the max window length; no allocation in `process()`.
- Estimators referenced to normalised quantities where the source mandates
  scale-invariance (F2, F1 coherence).

---

## 6. Test Requirements
| Test ID | Input | Expected |
|---------|-------|----------|
| T001 | structured signal (e.g. BPSK), no jammer | `|C̃42|`≈2.0, K>0, SFM<1, `Λcyc`>0 |
| T002 | + barrage at high JNR | C̃42→0, K→0, SFM→1, `Λcyc`→0 |
| T003 | normalised cumulant law | C̃42^y ≈ C̃42^s/(1+JNR)² within tolerance |
| T004 | fading vs barrage | F6 plateau only for sustained barrage |
| T005 | reference PSD | pre-onset window captured for suppression |
