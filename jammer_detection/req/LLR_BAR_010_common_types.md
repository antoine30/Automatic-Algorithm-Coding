# LLR_BAR_010 — Common Types and Detection Result

## Level : LOW LEVEL
## Parent HLR : HLR_BAR_001
## Depends on : (none — root types)

## Files to Generate
- src/common/jammer_types.h

---

## 1. Purpose
Shared status codes and the typed hand-off between the Detection and Suppression
tasks. This is the only coupling point between the two tasks (HLR_BAR_001_06).

---

## 2. Enumerations
```cpp
enum class DetStatus : int32_t {
    OK = 0, BAD_ARGUMENT = 1, NOT_READY = 2
};

/// Hypothesis decision per analysis window.
enum class Hypothesis : uint8_t { H0_NO_JAMMER = 0, H1_BARRAGE = 1 };

/// Suppression filter selected by the mode policy (§4 of the source doc).
enum class SuppressionMode : uint8_t {
    NONE = 0,           ///< pass-through (no jammer)
    WIENER_MMSE = 1,    ///< §4.2  low latency
    FRESH_CYCLIC = 2,   ///< §4.3  cyclic Wiener, ~zero distortion
    SPECTRAL_SUB = 3    ///< §4.4  adaptive spectral subtraction
};
```

---

## 3. DetectionResult (contract Detection → Suppression)
```cpp
struct DetectionResult {
    Hypothesis decision;       ///< H1 when Λ_BN > η_CFAR
    float      lambdaBN;       ///< fused composite statistic
    float      jnrEstimateDb;  ///< JNR from cumulant dilution ratio
    float      sigma2J;        ///< σ̂²_J  estimated jammer power
    float      bandwidthJ;     ///< B̂_J   estimated jammer bandwidth (Hz)
    uint64_t   onsetTick;      ///< t̂_on  onset time (SNN spike event)
    const float* refPsd;       ///< Ŝ⁰_s(f) jammer-free reference PSD (pre-onset)
    const float* cyclicSupport;///< A_s    signal cyclic frequencies (for FRESH)
    uint32_t   refPsdLen;      ///< length of refPsd
    uint32_t   cyclicSupportLen;
};
```

---

## 4. Constraints
- Header-only; fixed-width underlying types.
- `DetectionResult` carries pointers to caller-owned static buffers (no copy,
  no allocation).
- No dependency beyond `<cstdint>`.

---

## 5. Test Requirements
| Test ID | Check |
|---------|-------|
| T001 | enum underlying types are fixed width; OK == 0 |
| T002 | DetectionResult is trivially copyable (POD hand-off) |
