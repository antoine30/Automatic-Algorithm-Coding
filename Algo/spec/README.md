# Algo — RF Signal Processing Specifications

This folder contains the complete specification of the fixed-point
RF signal processing pipeline. It covers spur removal, phase computation,
and phase unwrapping for an IQ signal acquired by a 12-bit ADC.

---

## Contents

```
Algo/
├── FIXPOINT_TAXONOMY.md   ← fixed-point operation vocabulary (start here)
└── req/                   ← algorithm Low Level Requirements
    ├── LLR_ALG_000_arithmetic_target.md
    ├── LLR_ALG_002_bessel_spur_removal.md
    ├── LLR_ALG_003_phase_compute.md
    ├── LLR_ALG_004_phase_unwrapper.md
    └── LLR_ALG_007_rf_pipeline.md
```

---

## Start here

Read [`FIXPOINT_TAXONOMY.md`](FIXPOINT_TAXONOMY.md) first.
It defines the three operation families used in every LLR table:

| Family             | Operations                              |
|--------------------|-----------------------------------------|
| Arithmetic         | add, subtract, multiply, accumulate     |
| Format shaping     | shift right, shift left, round          |
| Saturation         | saturate (clamp to word size)           |

Every LLR operation table uses the pattern:

```
FP IN → arithmetic → format shaping → saturate → FP OUT
```

---

## Pipeline overview

```
ADC (int12, left-aligned)
        │ << 12  (LLR_ALG_000: frac_bits − adc_frac = 27 − 15)
        ▼
int32 Q4.27 IQ
        │ Bessel notch  (LLR_ALG_002)
        │ MAC → int64 Q8.54 → >> 27 → sat/32
        ▼
int32 Q4.27 IQ (filtered)
        │ CORDIC atan2  (LLR_ALG_003)
        │ 27 iterations → sat/32
        ▼
int32 Q4.27 phase [-π, +π]
        │ Phase unwrap  (LLR_ALG_004)
        │ sub → wrap → acc int64 → sat/32
        ▼
int32 Q4.27 unwrapped phase
```

---

## LLR reading order

| Order | File                            | Purpose                          |
|-------|---------------------------------|----------------------------------|
| 1     | LLR_ALG_000_arithmetic_target   | root — all parameters derive from here |
| 2     | LLR_ALG_002_bessel_spur_removal | Bessel biquad filter             |
| 3     | LLR_ALG_003_phase_compute       | CORDIC atan2                     |
| 4     | LLR_ALG_004_phase_unwrapper     | phase delta + accumulation       |
| 5     | LLR_ALG_007_rf_pipeline         | pipeline assembly                |

---

## Generate code

```bash
claude "Read Algo/req/ in the order defined in LLR_ALG_007_rf_pipeline.md
and generate all files listed under 'Files to Generate' in each LLR.
No float in any inner loop. No code in the LLRs — derive behavior from tables only."
```
