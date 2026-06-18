# MASTER — Barrage Noise Jammer Detection & Suppression

Source specification: `spec/barrage_noise_spec.md` (*Barrage Noise Jammer —
Single-Antenna Detection*, A. Damon, 2026). Architecture:
`spec/barrage_architecture.md`.

## Global Rules
- Language : C++17
- Target   : single receive antenna, real-time DSP (RTOS, fixed-point friendly)
- No malloc / new / delete after initialization (static buffers, fixed `K_max`)
- No exceptions
- Fixed-width types : uint8_t, uint16_t, uint32_t, int32_t, int64_t
- Doxygen comments mandatory on all public methods
- Two cooperating tasks: **Detection** (always-on) and **Suppression**
  (activated on detection), coupled only through the typed `DetectionResult`.

## System Decomposition
The system answers two questions from the source document:
- **Detection**: has the signal's geometric structure been diluted toward the
  Gaussian / maximum-entropy "trivial point"?
- **Suppression**: the barrage has no cyclic structure, so recover the signal
  from its cyclic support / spectral shape.

## Code Generation Order (MANDATORY)
1. LLR_BAR_010  — common types & status (`DetectionResult`, enums)
2. LLR_BAR_020  — shared front-end: windowing + 6 signature feature extractors
3. LLR_BAR_030  — Detection task (SNN/CNN/Temporal-MP pillars + fused CFAR)
4. LLR_BAR_040  — Suppression task (Wiener / FRESH / spectral subtraction)

A module is not generated until its LLR dependencies are generated.

## Traceability Matrix
| HLR         | LLR          | Generated Files                              | Doc ref |
|-------------|--------------|----------------------------------------------|---------|
| HLR_BAR_001 | LLR_BAR_010  | src/common/jammer_types.h                    | §4.1    |
| HLR_BAR_001 | LLR_BAR_020  | src/frontend/FeatureFrontEnd.h/.cpp          | §2      |
| HLR_BAR_001 | LLR_BAR_030  | src/detection/BarrageDetector.h/.cpp         | §3      |
| HLR_BAR_001 | LLR_BAR_040  | src/suppression/SignalRecovery.h/.cpp        | §4      |

## Key Quantitative Targets (from the source document)
| Quantity                         | Value           | Source |
|----------------------------------|-----------------|--------|
| Composite detection floor        | −13 dB JNR      | §3 table |
| Composite detection latency      | < 5 ms          | §3 table |
| Normalised cumulant law          | C̃42^y = C̃42^s/(1+JNR)² | §2.2 |
| Max simultaneous notch/spurs n/a | barrage = broadband | §1 |
| Wiener residual JNR              | −10log₁₀(1+JNR/SNR) | §4.5 |
| Spectral-subtraction improvement | ~ −15 dB         | §4.5 |
| Oversubtraction factor β         | [1.2, 2.0]      | §4.4 |
