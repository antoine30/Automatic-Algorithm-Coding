# HLR_BAR_001 — Barrage Detection & Suppression System

## Level : HIGH LEVEL

## Description
On a single receive antenna, detect the presence of a barrage noise jammer
(wideband circularly-symmetric Gaussian interference) at low JNR, and recover
the useful signal once a jammer is declared. The jammer is "geometrically
transparent": it raises the noise floor but leaves no coherent imprint in the
cyclostationary, higher-order-cumulant, time-frequency, AR-pole, or
information-geometry spaces.

## Requirements
- HLR_BAR_001_01 : The system shall continuously compute, per analysis window,
  the six signature features that separate a structured signal from Gaussian
  barrage noise (cyclostationarity, HOS cumulants, amplitude PDF, time-frequency
  flatness, AR-pole geometry, information-geometry persistence).
- HLR_BAR_001_02 : The system shall declare a barrage jammer active when a fused,
  CFAR-thresholded statistic exceeds its threshold, down to −13 dB JNR.
- HLR_BAR_001_03 : Detection shall use normalised (scale-invariant) statistics so
  that detectability does not depend on the jammer's power calibration.
- HLR_BAR_001_04 : On detection, the system shall estimate jammer power σ̂²_J,
  bandwidth B̂_J, and onset time t̂_on, and expose them to the suppression task.
- HLR_BAR_001_05 : The system shall recover the useful signal using a selectable
  filter (Wiener MMSE, FRESH cyclic Wiener, or adaptive spectral subtraction).
- HLR_BAR_001_06 : Detection and suppression shall be separate tasks coupled only
  through a typed result; suppression shall not recompute detection statistics.
- HLR_BAR_001_07 : No dynamic memory allocation shall occur after initialization.

## Validation Criteria
- Composite detector P_D high at −13 dB JNR with CFAR-constant P_FA; latency < 5 ms.
- Sustained-plateau information-geometry test rejects multipath fading
  (spike-then-baseline) as a false alarm.
- After suppression, output SINR is improved per §4.5 of the source document.

## Associated LLRs
- req/LLR_BAR_010_common_types.md
- req/LLR_BAR_020_frontend_features.md
- req/LLR_BAR_030_detection.md
- req/LLR_BAR_040_suppression.md
