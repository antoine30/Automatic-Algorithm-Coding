# LLR_BAR_040 — Signal Recovery Task (Mode-Selected Filtering)

## Level : LOW LEVEL
## Parent HLR : HLR_BAR_001
## Depends on : LLR_BAR_010, LLR_BAR_030

## Files to Generate
- src/suppression/SignalRecovery.h
- src/suppression/SignalRecovery.cpp
- tests/test_signal_recovery.cpp

---

## 1. Purpose
When a barrage jammer is declared (Task 2), recover the useful signal using a
selectable filter, driven by the `DetectionResult`. Implements the source
document's detection-to-filtering pipeline (§4).

---

## 2. Mode Selection
A policy picks the filter from `DetectionResult` and the latency budget:

| Mode | Residual JNR | Distortion | Latency | When to use |
|------|--------------|-----------|---------|-------------|
| WIENER_MMSE | −10log₁₀(1+JNR/SNR) | mild (H_W<1) | < 1 ms | default; clean reference PSD available |
| FRESH_CYCLIC | → −∞ (theoretic) | none | 10–100 ms | cyclic support A_s known/stable; latency-tolerant |
| SPECTRAL_SUB | ~ −15 dB | mild artefacts | < 5 ms | no clean reference / fastest adaptation |
| NONE | input | none | 0 | H0 (pass-through) |

Policy: prefer FRESH when `A_s` known and latency allows; else Wiener when a
pre-onset `Ŝ⁰_s` reference exists; else spectral subtraction.

---

## 3. Filters

### A — Wiener / MMSE (§4.2)
```
Ŝ(f) = H_W(f) · Y(f),   H_W(f) = S⁰_s(f) / (S⁰_s(f) + σ̂²_J/B̂_J + σ²_n) ∈ [0,1]
```
- `S⁰_s(f)` from the jammer-free reference window before `t̂_on`.
- `H_W → 1` where signal dominates, `→ 0` where noise+jammer dominate.

### B — FRESH cyclic Wiener (§4.3)
```
ŝ(t) = Σ_{α∈A_s} ∫ H^α(f) S_y^α(f) e^{j2π(f+α)t} df
```
- Exploits disjoint cyclic supports: barrage has zero cyclic spectrum, so the
  signal is recovered from its cyclic features; separation → perfect as T → ∞.

### C — Adaptive spectral subtraction (§4.4, runtime)
```
Ŝ⁰_J(f,t) = λ·Ŝ⁰_J(f,t−1) + (1−λ)·|Y(f,t)|²·1[Λ>η]
ŝ(t)      = F⁻¹[ max(|Y(f,t)|² − β·Ŝ⁰_J(f,t), ε)^{1/2} · e^{j∠Y(f,t)} ]
```
- Oversubtraction factor `β ∈ [1.2, 2.0]` suppresses musical-noise artefacts.

---

## 4. Interface
```cpp
class SignalRecovery {
public:
    void configure(float lambdaSmoothing, float beta, float noiseFloorSigma2);
    /// Select a mode from the detection result and filter the live buffer
    /// in place (or into out). Returns the mode applied.
    SuppressionMode process(const DetectionResult& det,
                            const float* yI, const float* yQ,
                            float* sI, float* sQ, uint32_t len);
    void reset();
};
```

---

## 5. Constraints
- No allocation after init; static FFT scratch and PSD buffers (size ≤ N_max).
- When `det.decision == H0`, output equals input exactly (pass-through).
- `β`, `λ`, and `σ²_n` are configuration parameters, not hardcoded.
- FRESH requires a valid `cyclicSupport`; if absent, fall back per the policy.

---

## 6. Test Requirements
| Test ID | Input | Expected |
|---------|-------|----------|
| T001 | H0 result | pass-through, output == input |
| T002 | Wiener mode, known S⁰_s | output SINR improved; H_W∈[0,1] |
| T003 | FRESH mode, signal+barrage | jammer rejected, signal preserved |
| T004 | spectral-sub mode | ~−15 dB residual, bounded artefacts (β sweep) |
| T005 | mode selection | policy picks expected mode per available inputs |
