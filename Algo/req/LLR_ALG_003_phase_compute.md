# LLR_ALG_003 — Instantaneous Phase Computation (atan2 CORDIC)

## Level : LOW LEVEL
## Parent HLR : HLR_003
## Version : 4.0
## Depends on : LLR_ALG_002, LLR_ALG_006, LLR_ALG_000

## Files to Generate
- src/algorithms/PhaseCompute.h
- src/algorithms/PhaseCompute.cpp
- tests/test_phase_compute.cpp

---

## 1. Purpose

Computes the instantaneous phase from Q4.27 IQ samples using a
27-iteration CORDIC algorithm. No float in the inner loop.

---

## 2. Arithmetic Parameters (from LLR_ALG_000)

| Parameter          | Value   | Source                         |
|--------------------|---------|--------------------------------|
| Input format       | Q4.27   | LLR_ALG_000 §3.2               |
| Output format      | Q4.27   | LLR_ALG_000 §3.2               |
| CORDIC group       | Group G | LLR_ALG_000 §4                 |
| CORDIC iterations  | 27      | LLR_ALG_000 §3.2 (= frac_bits)|
| CORDIC precision   | 2⁻²⁷   | LLR_ALG_000 §3.2               |
| CORDIC gain K₂₇   | 1.6468  | LLR_ALG_000 §6                 |
| Saturation         | 32 bits | LLR_ALG_000 §3.2               |
| Float in inner loop| forbidden | LLR_ALG_000 §3.2             |

---

## 3. Mathematical Definition

```
phase[n] = atan2( Q[n], I[n] )    range: [-π, +π]
```

---

## 4. CORDIC Rotation Table (initialization only)

Each entry precomputed as: `angle[i] = round( atan(2⁻ⁱ) × 2²⁷ )`

| i  | atan(2⁻ⁱ) radians | Q4.27 integer  |
|----|-------------------|----------------|
| 0  | 0.785398 (π/4)   | computed once  |
| 1  | 0.463648          | computed once  |
| 2  | 0.244979          | computed once  |
| …  | …                 | …              |
| 26 | 2⁻²⁶ ≈ 1.5×10⁻⁸  | computed once  |

Table computed at init using float. Stored as int32 Q4.27.
Never recomputed in the processing loop.

---

## 5. Operation Groups — FP IN / Operation / FP OUT

### Group 1 — Angle table initialization (float, once at init)

| Step | FP IN  | Operation                    | FP OUT       | Shift | Saturate |
|------|--------|------------------------------|--------------|-------|----------|
| 1.1  | float  | atan(2⁻ⁱ) for i=0..26      | float        | none  | no       |
| 1.2  | float  | × 2²⁷                       | float        | none  | no       |
| 1.3  | float  | round to nearest integer     | int32 Q4.27  | none  | no       |

---

### Group 2 — CORDIC gain compensation (initialization only)

| Step | FP IN  | Operation                       | FP OUT       | Shift | Saturate |
|------|--------|---------------------------------|--------------|-------|----------|
| 2.1  | float  | 1 / K₂₇ (= 1/1.6468)          | float        | none  | no       |
| 2.2  | float  | × 2²⁷                          | float        | none  | no       |
| 2.3  | float  | round                           | int32 Q4.27  | none  | no       |

CORDIC_COMP stored as int32 Q4.27. Applied in Group 4.

---

### Group 3 — CORDIC iteration i (inner loop, 27 times)

One iteration of the CORDIC vectoring algorithm.
σᵢ = sign(y) determines rotation direction.

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate          |
|------|--------------------|------------------------|--------------|-------|-------------------|
| 3.1  | int32 Q4.27 (y)   | sign(y) → σᵢ = ±1     | int32        | none  | no                |
| 3.2  | int32 Q4.27 (y)   | y >> i                 | int32 Q4.27  | >> i  | no                |
| 3.3  | int32 Q4.27 (x)   | x ∓ (y >> i)           | int32 Q4.27  | none  | no (mid-iter)     |
| 3.4  | int32 Q4.27 (x)   | x >> i                 | int32 Q4.27  | >> i  | no                |
| 3.5  | int32 Q4.27 (y)   | y ± (x >> i)           | int32 Q4.27  | none  | no (mid-iter)     |
| 3.6  | int32 Q4.27 (z)   | z ∓ angle_table[i]     | int32 Q4.27  | none  | no (mid-iter)     |

No saturation between iterations — rounding errors accumulate
and are resolved once at the final step (Group 4).

---

### Group 4 — CORDIC final output (after 27 iterations)

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------|--------------|-------|----------|
| 4.1  | int32 Q4.27 (z)   | z = accumulated angle  | int32 Q4.27  | none  | yes / 32 |

z after 27 iterations = atan2(Q, I) in Q4.27, range [-π, +π].

---

### Group 5 — CORDIC gain compensation (per sample, after Group 4)

Applied to I and Q amplitudes (not to the phase angle z).
Method: multiply I and Q by CORDIC_COMP before CORDIC.

| Step | FP IN                           | Operation               | FP OUT       | Shift | Saturate |
|------|---------------------------------|-------------------------|--------------|-------|----------|
| 5.1  | int32 Q4.27 (I or Q)           | widen to int64          | int64 Q4.27  | none  | no       |
| 5.2  | int64 Q4.27 × int32 Q4.27 (COMP)| multiply               | int64 Q8.54  | none  | no       |
| 5.3  | int64 Q8.54                     | >> 27                   | int64 Q4.27  | >> 27 | no       |
| 5.4  | int64 Q4.27                     | saturate                | int32 Q4.27  | none  | yes / 32 |

---

## 6. Format Trace per Sample

| Stage          | FP IN        | Operation group | FP OUT       |
|----------------|--------------|-----------------|--------------|
| Input          | int32 Q4.27  | —               | int32 Q4.27  |
| Gain comp I    | int32 Q4.27  | Group 5         | int32 Q4.27  |
| Gain comp Q    | int32 Q4.27  | Group 5         | int32 Q4.27  |
| CORDIC iter 0  | int32 Q4.27  | Group 3 (i=0)   | int32 Q4.27  |
| CORDIC iter 1  | int32 Q4.27  | Group 3 (i=1)   | int32 Q4.27  |
| …              | …            | …               | …            |
| CORDIC iter 26 | int32 Q4.27  | Group 3 (i=26)  | int32 Q4.27  |
| Final output   | int32 Q4.27  | Group 4         | int32 Q4.27  |

---

## 7. Edge Cases

| Condition   | I       | Q       | FP IN        | Expected FP OUT     |
|-------------|---------|---------|--------------|---------------------|
| No signal   | 0       | 0       | int32 Q4.27  | 0 (no crash)        |
| Pure +I     | max     | 0       | int32 Q4.27  | 0                   |
| Pure +Q     | 0       | max     | int32 Q4.27  | HALF_PI_Q427        |
| Pure −I     | min     | 0       | int32 Q4.27  | ±PI_Q427            |

---

## 8. Constraints

- CORDIC iterations = frac_bits = 27 (LLR_ALG_000)
- No float in Groups 3, 4, 5
- No saturation between CORDIC iterations (Group 3)
- Saturation once after all 27 iterations (Group 4)
- Rotation table precomputed at init (Group 1), never in loop
- Gain compensation at init (Group 2) and per-sample (Group 5)

---

## 9. Test Requirements

| Test ID | FP IN        | Operation group | Expected FP OUT   | Tolerance |
|---------|--------------|-----------------|-------------------|-----------|
| T001    | int32 Q4.27  | Group 3×27 + 4  | 0 (pure I)        | ≤ 1 LSB   |
| T002    | int32 Q4.27  | Group 3×27 + 4  | HALF_PI_Q427      | ≤ 1 LSB   |
| T003    | int32 Q4.27  | Group 3×27 + 4  | ±PI_Q427          | ≤ 1 LSB   |
| T004    | float angle  | Group 1         | int32 Q4.27 table | < 1 LSB   |
| T005    | float K₂₇   | Group 2         | int32 Q4.27 COMP  | < 1 LSB   |
| T006    | int32 Q4.27  | Group 5         | compensated Q4.27 | < 1 LSB   |
