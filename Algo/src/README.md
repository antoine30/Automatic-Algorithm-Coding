# RF Pipeline — Generated Fixed-Point Code

Generated from the requirements in [`Algo/req/`](../req/) and the Bessel system
specification [`Algo/spec/spur_removal_spec.pdf`](../spec/spur_removal_spec.pdf),
following the fixed-point taxonomy in [`Algo/README.md`](../README.md).

All arithmetic is **pure integer** (int32 / int64, Q4.27) — no floating point in
any inner loop, no hardware dependency. The code therefore compiles and is fully
unit-tested **on the host**.

## Files

| File | LLR | Role |
|------|-----|------|
| `config/arithmetic_target.h` | LLR_ALG_000 | Single source of truth: formats, shifts, constants, `saturate_i32`, `q427_mul` |
| `common/types.h` | LLR_ALG_006 | `TaskStatus` shared return type |
| `algorithms/AdcPromote.{h,cpp}` | LLR_ALG_001 | int16 Q1.15 → int32 Q4.27 promote + de-interleave |
| `algorithms/BesselSpurRemoval.{h,cpp}` | LLR_ALG_002 | Notch biquad cascade (DFII-T, int64 Q8.54) + DFT spur detection |
| `algorithms/PhaseCompute.{h,cpp}` | LLR_ALG_003 | 27-iteration CORDIC atan2 |
| `algorithms/PhaseUnwrapper.{h,cpp}` | LLR_ALG_004 | 2π unwrap, int64 cross-buffer accumulator |
| `algorithms/RfPipeline.{h,cpp}` | LLR_ALG_007 | promote → Bessel → CORDIC → unwrap assembly |

## Build & test

```sh
cd ../test
make        # builds and runs 6 suites (zero warnings)
```

Representative results:
- CORDIC angle error ≤ 5 LSB over the full circle (≈ 4e-8 rad).
- Notch attenuation > 140 dB on-frequency; spur auto-detection (DFT) finds the
  spur above the noise floor and designs the notch automatically.
- Unwrapper int64 accumulator verified monotone past INT32_MAX.
- SNR harness: phase RMS error tracks input SNR (≈5.7e-2 rad @20 dB,
  5.8e-4 rad @60 dB, 1.7e-8 rad noiseless — the fixed-point floor).
- Pipeline per-sample error bounded by ADC int16 quantization, not the algorithm.

## Spec deviations & notes (tracked)

1. **Radian constants derived, not copied.** LLR_ALG_000 §5 lists PI/TWOPI/
   HALF_PI hex values scaled by 2^29 (Q2.29), inconsistent with the mandated
   Q4.27 (§3.2) — they are 4× too large, and the "TWOPI overflows int32" note
   only holds at 2^29. Per the derivation-chain rule, the constants in
   `arithmetic_target.h` are derived as `round(value × 2^frac_bits)` in Q4.27
   (2π = 843,314,857 fits in int32). See the note in that header.
2. **Previously-missing LLRs now authored.** `LLR_ALG_001` (ADC promote) and
   `LLR_ALG_006` (common types) were referenced as dependencies but absent; they
   have been written in `req/` and implemented (`AdcPromote`, `common/types.h`).
3. **Spur detection** (PDF §4) is implemented in `BesselSpurRemoval::
   detectAndConfigure()`: a float DFT magnitude spectrum, median noise-floor
   estimate, and peak picking above floor + threshold (once per buffer, never in
   the inner loop). Detection assumes a real noise floor — a perfectly synthetic
   tone has none, so DFT round-off can masquerade as a peak; realistic inputs
   (and the test) include a noise floor.
