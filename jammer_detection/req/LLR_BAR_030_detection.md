# LLR_BAR_030 — Barrage Detection Task (Three-Pillar + Fused CFAR)

## Level : LOW LEVEL
## Parent HLR : HLR_BAR_001
## Depends on : LLR_BAR_010, LLR_BAR_020

## Files to Generate
- src/detection/BarrageDetector.h
- src/detection/BarrageDetector.cpp
- tests/test_barrage_detector.cpp

---

## 1. Purpose
Fuse the six front-end features through three complementary "pillars" and a CFAR
threshold to declare a barrage jammer (Task 1), reaching −13 dB JNR with < 5 ms
latency. Also produce the parameter estimates consumed by suppression.

---

## 2. Three Pillars (source §3)

### Pillar A — SNN (temporal statistics)
- Tracks running `Ĉ42(t)` step-down at onset.
- Tracks firing rate of all cyclic-frequency populations: a **uniform** rate
  drop across all α_k is the barrage fingerprint (spot jammers drop only in-band
  cycles).
- Tracks Rician K-factor step-down.
- Emits the onset event/time `t̂_on`.

### Pillar B — CNN (time-frequency / spatial)
- Operates on the cyclic-coherence map and log-polar WVD.
- Detects global cyclic-coherence collapse, Rényi-entropy elevation, inward AR
  pole drift, SFM → 1 (absence of geometric features is the feature).

### Pillar C — Temporal Matching Pursuit (persistence)
- Propagates the `D_JS` trajectory across windows; confirms a sustained
  elevated plateau (broadband sustained interference), rejecting multipath
  fading (spike-then-return-to-baseline).

---

## 3. Fusion and CFAR Decision
```
Λ_BN = w1·Λcyc + w2·|C̃42| ... (inverted so barrage increases Λ_BN)
     + w3·H_TF + w4·(1/r̄_poles)
decision = (Λ_BN > η_CFAR) ? H1_BARRAGE : H0_NO_JAMMER
```
- Weights `w_k` are learned (multi-task); at runtime they are fixed parameters.
- CFAR maintains constant `P_FA` regardless of noise power (the jammer inflates
  power; the test must not).
- The contributing terms move monotonically with JNR (source §3 summary table):

| Feature | H0 value | H1 trend | Min JNR | Latency |
|---------|----------|----------|---------|---------|
| Cyclic coherence | > 0 | → 0 monotone | −10 dB | 5 ms |
| Normalised kurtosis | 2.0 (BPSK) | ↓ (1+JNR)⁻² | −3 dB | 10 ms |
| TF Rényi entropy | low | ↑ uniform | −8 dB | 5 ms |
| D_JS plateau | ≈ 0 | ↑ persistent | −12 dB | 20 ms |
| AR pole radius | ≈ 1 | ↓ inward | −6 dB | 2 ms |
| Composite Λ_BN | nominal | elevated | −13 dB | < 5 ms |

---

## 4. Parameter Estimation (feeds Suppression, source §4.1)
- `σ̂²_J` : from the cumulant dilution ratio.
- `B̂_J`  : from the SFM flatness extent.
- `t̂_on` : SNN onset spike event.
These populate `DetectionResult` (LLR_BAR_010) together with the front-end's
reference PSD and the signal cyclic support.

---

## 5. Interface
```cpp
class BarrageDetector {
public:
    void configure(const float* fusionWeights, uint32_t nWeights,
                   float cfarThreshold);
    /// Consume one window's features; emit decision + estimates.
    DetStatus update(const FeatureVector& f, uint64_t tick, DetectionResult& out);
    void reset();
};
```

---

## 6. Constraints
- No allocation in `update()`; fixed weight/threshold storage.
- Fixed-point or float per target; the fusion is a small dot product.
- CFAR threshold parameterised, not hardcoded.
- Decision must be power-normalised and carrier-phase invariant (SO(2)).

---

## 7. Test Requirements
| Test ID | Input | Expected |
|---------|-------|----------|
| T001 | H0 features | decision = H0, Λ_BN < η |
| T002 | H1 features at −13 dB JNR | decision = H1 |
| T003 | uniform vs in-band cyclic drop | barrage flagged, spot-jam not |
| T004 | fading transient (F6 spike only) | no false alarm |
| T005 | estimates | σ̂²_J, B̂_J, t̂_on populated and plausible |
| T006 | CFAR | P_FA approx constant as noise power scales |
