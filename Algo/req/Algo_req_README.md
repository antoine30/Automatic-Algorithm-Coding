# Algorithm LLRs — Low Level Requirements

This folder contains the Low Level Requirements for the RF processing
pipeline. Each file specifies one algorithm stage with no implementation
code — only behavioral tables, mathematical equations, and fixed-point
operation groups.

---

## Files

| File                              | Stage | Depends on       |
|-----------------------------------|-------|------------------|
| `LLR_ALG_000_arithmetic_target`   | root  | —                |
| `LLR_ALG_002_bessel_spur_removal` | 1     | ALG_000, ALG_001 |
| `LLR_ALG_003_phase_compute`       | 2     | ALG_002, ALG_000 |
| `LLR_ALG_004_phase_unwrapper`     | 3     | ALG_003, ALG_000 |
| `LLR_ALG_007_rf_pipeline`         | all   | ALG_000 → ALG_004|

---

## LLR structure

Every LLR follows the same structure:

```
1. Purpose
2. Arithmetic parameters  ← all derived from LLR_ALG_000, never defined independently
3. Mathematical definition
4. Operation groups       ← FP IN / Operation / FP OUT tables
5. Interface specification
6. Constraints
7. Test requirements
```

---

## Fixed-point operation table format

Each row in an operation group table is one elementary operation:

```
| Step | FP IN        | Operation      | FP OUT       | Shift | Saturate |
|------|-------------|----------------|--------------|-------|----------|
| N.1  | int32 Q4.27 | widen to int64 | int64 Q4.27  | none  | no       |
| N.2  | int64 Q4.27 | multiply       | int64 Q8.54  | none  | no       |
| N.3  | int64 Q8.54 | >> 27          | int64 Q4.27  | >> 27 | no       |
| N.4  | int64 Q4.27 | saturate       | int32 Q4.27  | none  | yes/32   |
```

Arithmetic and format shaping are never on the same row.
See [`../FIXPOINT_TAXONOMY.md`](../FIXPOINT_TAXONOMY.md) for the full vocabulary.

---

## Derivation chain

All shift amounts, iteration counts, and accumulator widths trace
back to `LLR_ALG_000`:

```
word_size = 32  →  frac_bits = 27  →  shift = >> 27
                                    →  CORDIC iterations = 27
                                    →  accumulator = int64
                                    →  promote shift = 27 − 15 = 12
```
