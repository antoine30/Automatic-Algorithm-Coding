# LLR_ALG_002 — Bessel Spur Removal

## Level : LOW LEVEL
## Parent HLR : HLR_003
## Version : 4.0
## Depends on : LLR_ALG_001, LLR_ALG_006, LLR_ALG_000

## Files to Generate
- src/algorithms/BesselSpurRemoval.h
- src/algorithms/BesselSpurRemoval.cpp
- tests/test_bessel_spur_removal.cpp

---

## 1. Purpose

Removes narrowband RF spurs from IQ samples using a cascade of
second-order Bessel notch biquad filters.

---

## 2. Arithmetic Parameters (from LLR_ALG_000)

| Parameter          | Value     | Source              |
|--------------------|-----------|---------------------|
| Input format       | Q4.27     | LLR_ALG_000 §3.2    |
| Output format      | Q4.27     | LLR_ALG_000 §3.2    |
| Coeff format       | Q4.27     | LLR_ALG_000 §3.2    |
| MAC group          | Group C   | LLR_ALG_000 §4      |
| Shift              | >> 27     | LLR_ALG_000 §3.2    |
| Accumulator        | int64     | LLR_ALG_000 §3.2    |
| Saturation         | 32 bits   | LLR_ALG_000 §3.2    |
| State type         | int64     | LLR_ALG_000 §4 (C.3)|

---

## 3. Filter Choice Rationale

| Filter    | Group delay    | Phase distortion | IQ suitability |
|-----------|----------------|-----------------|----------------|
| Butterworth | non-linear   | yes             | moderate       |
| Chebyshev | non-linear     | significant     | poor           |
| Bessel    | maximally flat | none            | ✓ best         |

---

## 4. Filter Structure

| Property               | Specification                     |
|------------------------|-----------------------------------|
| Topology               | Direct Form II Transposed         |
| Order per notch        | 2 (one biquad)                    |
| Coefficients per biquad| 5 : b₀, b₁, b₂, a₁, a₂         |
| Max simultaneous spurs | 4 (static bank)                   |
| Coefficient format     | Q4.27 (LLR_ALG_000 §3.2)        |
| State variable type    | int64 Q4.27 (see §5 group below) |

---

## 5. Operation Groups — FP IN / Operation / FP OUT

### Group 1 — Coefficient design (initialization only, float allowed)

| Step | FP IN    | Operation                        | FP OUT      | Shift | Saturate |
|------|----------|----------------------------------|-------------|-------|----------|
| 1.1  | float    | Bessel notch design (math)       | float       | none  | no       |
| 1.2  | float    | × 2²⁷ (= SCALE from ALG_000)   | float       | none  | no       |
| 1.3  | float    | round to nearest integer         | int32 Q4.27 | none  | no       |

This group runs once at initialization. Float is permitted here only.

---

### Group 2 — Biquad output y[n] (inner loop, per sample)

Implements: y[n] = b₀·x[n] + state_w1

| Step | FP IN                    | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------------|------------------------|--------------|-------|----------|
| 2.1  | int32 Q4.27 (b₀)        | widen to int64         | int64 Q4.27  | none  | no       |
| 2.2  | int32 Q4.27 (x[n])      | widen to int64         | int64 Q4.27  | none  | no       |
| 2.3  | int64 Q4.27 × int64 Q4.27| multiply              | int64 Q8.54  | none  | no       |
| 2.4  | int64 Q8.54 + int64 Q8.54 (state_w1)| add state | int64 Q8.54  | none  | no       |
| 2.5  | int64 Q8.54              | >> 27 (= frac_bits)    | int64 Q4.27  | >> 27 | no       |
| 2.6  | int64 Q4.27              | saturate to 32 bits    | int32 Q4.27  | none  | yes / 32 |

Output of step 2.6 = y[n] → input of next biquad or final output.

---

### Group 3 — State update w₁ (inner loop, per sample)

Implements: w₁ = b₁·x[n] − a₁·y[n] + state_w2

| Step | FP IN                      | Operation              | FP OUT       | Shift | Saturate |
|------|----------------------------|------------------------|--------------|-------|----------|
| 3.1  | int32 Q4.27 (b₁, x[n])    | widen + multiply       | int64 Q8.54  | none  | no       |
| 3.2  | int32 Q4.27 (a₁, y[n])    | widen + multiply       | int64 Q8.54  | none  | no       |
| 3.3  | int64 Q8.54 − int64 Q8.54 | subtract               | int64 Q8.54  | none  | no       |
| 3.4  | int64 Q8.54 + int64 Q8.54 (state_w2)| add state  | int64 Q8.54  | none  | no       |
| 3.5  | int64 Q8.54                | store as state_w1      | int64 Q8.54  | none  | no       |

State stored as int64 Q8.54 — not renormalized between samples.
Renormalization occurs in Group 2 step 2.5 when state is consumed.

---

### Group 4 — State update w₂ (inner loop, per sample)

Implements: w₂ = b₂·x[n] − a₂·y[n]

| Step | FP IN                      | Operation              | FP OUT       | Shift | Saturate |
|------|----------------------------|------------------------|--------------|-------|----------|
| 4.1  | int32 Q4.27 (b₂, x[n])    | widen + multiply       | int64 Q8.54  | none  | no       |
| 4.2  | int32 Q4.27 (a₂, y[n])    | widen + multiply       | int64 Q8.54  | none  | no       |
| 4.3  | int64 Q8.54 − int64 Q8.54 | subtract               | int64 Q8.54  | none  | no       |
| 4.4  | int64 Q8.54                | store as state_w2      | int64 Q8.54  | none  | no       |

---

### Group 5 — Cascade (N biquads)

| Step | FP IN          | Operation                           | FP OUT       |
|------|----------------|-------------------------------------|--------------|
| 5.1  | int32 Q4.27    | input to biquad k (Groups 2,3,4)   | int32 Q4.27  |
| 5.2  | int32 Q4.27    | output of biquad k = input of k+1  | int32 Q4.27  |

Format is preserved across cascade boundaries.
Each biquad saturates independently at Group 2 step 2.6.

---

## 6. Interface Specification

| Signal      | Type          | FP IN/OUT | Description              |
|-------------|---------------|-----------|--------------------------|
| iBuffer     | int32_t array | Q4.27     | I channel, N samples     |
| qBuffer     | int32_t array | Q4.27     | Q channel, N samples     |
| iBuffer out | int32_t array | Q4.27     | I filtered (in-place)    |
| qBuffer out | int32_t array | Q4.27     | Q filtered (in-place)    |
| return      | int32_t       | —         | spurs removed or < 0     |

---

## 7. Constraints

- No float in inner loop (Groups 2, 3, 4)
- State variables int64 Q8.54 — never truncated between samples
- Saturation only at Group 2 step 2.6
- Coefficient design (Group 1) at init only
- Cascade gain < 8.0 (LLR_ALG_000 §6)

---

## 8. Test Requirements

| Test ID | Description                          | FP IN        | Expected FP OUT   |
|---------|--------------------------------------|--------------|-------------------|
| T001    | Clean sine                           | int32 Q4.27  | ≈ input Q4.27     |
| T002    | Sine + spur at f₀                   | int32 Q4.27  | spur > 40 dB down |
| T003    | State after buffer 1                 | int64 Q8.54  | feeds buffer 2    |
| T004    | INT32_MAX input                      | int32 Q4.27  | no overflow out   |
| T005    | Coeff design output                  | float        | int32 Q4.27       |
