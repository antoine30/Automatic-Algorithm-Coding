# LLR_ALG_000 — Arithmetic Target Specification

## Level : LOW LEVEL
## Parent HLR : HLR_003
## Version : 4.0
## Depends on : (none — root arithmetic LLR)

## Files to Generate
- src/config/arithmetic_target.h

---

## 1. Purpose

Single source of truth for all fixed-point arithmetic parameters.
Every shift, iteration count, accumulator width, and saturation width
in every algorithm LLR is **derived** from the values defined here.

---

## 2. Signal Range Analysis

| Signal              | Mathematical range | Justification                    |
|---------------------|--------------------|----------------------------------|
| IQ amplitude        | [-1.0, +1.0]       | normalized ADC output            |
| Instantaneous phase | [-π, +π]           | atan2 output                     |
| Phase delta         | [-π, +π]           | bounded by wrap                  |
| Biquad coefficients | [-2.0, +2.0]       | Bessel notch design typical      |
| Cascade output      | [-8.0, +8.0]       | gain budget (§6.2)               |
| Unwrapped phase     | unbounded          | monotone accumulation → int64    |

Largest bounded value: cascade output ≈ 8.0 → requires 4 integer bits.

---

## 3. Arithmetic Target Definition

### 3.1 Primary parameters (chosen)

| Parameter     | Value | Justification                                   |
|---------------|-------|-------------------------------------------------|
| Word size      | 32    | CPU native register width                       |
| Sign bit       | 1     | two's complement, all signals are bipolar       |
| Integer bits   | 4     | covers max signal 8.0 with margin (2⁴ = 16)   |

### 3.2 Derived parameters

| Parameter          | Formula                          | Value |
|--------------------|----------------------------------|-------|
| Fractional bits    | word_size − sign_bit − int_bits  | 27    |
| Q format           | Q(int_bits).(frac_bits)          | Q4.27 |
| Resolution         | 2⁻²⁷                            | 7.45 × 10⁻⁹ |
| Max positive       | 2⁴ − 2⁻²⁷                       | ≈ +7.999 |
| Min negative       | −2⁴                              | −8.0 |
| Multiply shift     | = frac_bits                      | 27   |
| CORDIC iterations  | = frac_bits                      | 27   |
| Accumulator width  | = 2 × word_size                  | 64   |
| Saturation width   | = word_size                      | 32   |
| ADC frac bits      | adc_word − sign_bit (left-align) | 15   |
| Promotion shift    | frac_bits − adc_frac_bits        | 12   |

---

## 4. Operation Groups — FP IN / Operation / FP OUT

This is the normative table. All algorithm LLRs derive their
operation groups from these rows.

### Group A — Promote

| Step | FP IN        | Operation          | FP OUT       | Shift | Saturate |
|------|--------------|--------------------|--------------|-------|----------|
| A.1  | int16 Q1.15  | << 12 (= 27 − 15) | int32 Q4.27  | << 12 | no       |

### Group B — Multiply

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------|--------------|-------|----------|
| B.1  | int32 Q4.27 (×2)  | widen both to int64    | int64 Q4.27  | none  | no       |
| B.2  | int64 Q4.27 (×2)  | multiply               | int64 Q8.54  | none  | no       |
| B.3  | int64 Q8.54        | >> 27 (= frac_bits)    | int64 Q4.27  | >> 27 | no       |
| B.4  | int64 Q4.27        | saturate to word_size  | int32 Q4.27  | none  | yes / 32 |

### Group C — Multiply-Accumulate (MAC)

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------|--------------|-------|----------|
| C.1  | int32 Q4.27 (×2)  | widen both to int64    | int64 Q4.27  | none  | no       |
| C.2  | int64 Q4.27 (×2)  | multiply               | int64 Q8.54  | none  | no       |
| C.3  | int64 Q8.54        | add to accumulator     | int64 Q8.54  | none  | no       |
| C.4  | (repeat C.1–C.3 for each term)                                       |
| C.5  | int64 Q8.54        | >> 27 (= frac_bits)    | int64 Q4.27  | >> 27 | no       |
| C.6  | int64 Q4.27        | saturate to word_size  | int32 Q4.27  | none  | yes / 32 |

### Group D — Add / Subtract

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------|--------------|-------|----------|
| D.1  | int32 Q4.27 (×2)  | widen both to int64    | int64 Q4.27  | none  | no       |
| D.2  | int64 Q4.27 (×2)  | add or subtract        | int64 Q4.27  | none  | no       |
| D.3  | int64 Q4.27        | saturate to word_size  | int32 Q4.27  | none  | yes / 32 |

### Group E — Phase Accumulation (cross-buffer)

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate          |
|------|--------------------|------------------------|--------------|-------|-------------------|
| E.1  | int32 Q4.27        | widen to int64         | int64 Q4.27  | none  | no                |
| E.2  | int64 Q4.27 (×2)  | add to accumulator     | int64 Q4.27  | none  | no (int64 holds)  |
| E.3  | int64 Q4.27        | saturate on write only | int32 Q4.27  | none  | yes / 32          |

Note: accumulator itself is never saturated between samples.

### Group F — Phase Wrap

| Step | FP IN              | Operation                        | FP OUT       | Shift | Saturate |
|------|--------------------|----------------------------------|--------------|-------|----------|
| F.1  | int32 Q4.27        | compare with PI_Q427 (integer)   | bool         | none  | no       |
| F.2  | int32 Q4.27        | subtract TWOPI_Q427 if > +π     | int32 Q4.27  | none  | yes / 32 |
| F.3  | int32 Q4.27        | add TWOPI_Q427 if < −π          | int32 Q4.27  | none  | yes / 32 |

### Group G — CORDIC (per iteration i = 0..26)

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate           |
|------|--------------------|------------------------|--------------|-------|--------------------|
| G.1  | int32 Q4.27 (x,y) | x ∓ (y >> i)           | int32 Q4.27  | >> i  | no (mid-iter)      |
| G.2  | int32 Q4.27 (x,y) | y ± (x >> i)           | int32 Q4.27  | >> i  | no (mid-iter)      |
| G.3  | int32 Q4.27 (z)   | z ∓ angle_table[i]     | int32 Q4.27  | none  | no (mid-iter)      |
| G.4  | int32 Q4.27        | saturate after iter 26 | int32 Q4.27  | none  | yes / 32 (final)   |

Iterations: 27 (= frac_bits). No saturation between iterations.

---

## 5. Precomputed Constants

All derived from frac_bits = 27.

| Constant     | Formula          | Q4.27 hex    | Decimal value    |
|--------------|------------------|--------------|------------------|
| SCALE        | 2²⁷              | 0x08000000   | 134 217 728      |
| PI           | π × 2²⁷          | 0x6487ED51   | 1 686 629 713    |
| TWOPI        | 2π × 2²⁷         | 0xC90FDAA2   | (see note)       |
| HALF_PI      | (π/2) × 2²⁷      | 0x3243F6A9   | 843 314 857      |
| CORDIC_COMP  | (1/K₂₇) × 2²⁷   | 0x04D5B6A0   | K₂₇ ≈ 1.6468    |

Note: TWOPI overflows int32. Apply as two successive PI subtractions.

---

## 6. Overflow Budget

| Constraint                         | Value  | Derivation              |
|------------------------------------|--------|-------------------------|
| Q4.27 max value                    | 7.999  | 2⁴ − 2⁻²⁷             |
| Max cascade gain (theoretical)     | < 16.0 | 2^int_bits              |
| Max cascade gain (practical, 50%M) | < 8.0  | with safety margin      |
| CORDIC gain K₂₇                   | 1.6468 | ∏√(1+2⁻²ⁱ), i=0..26   |

---

## 7. Initialization Checks

| Check                               | Condition                         |
|-------------------------------------|-----------------------------------|
| Q format consistency                | frac_bits + int_bits + 1 == 32   |
| CORDIC iterations match frac_bits   | iterations == 27                  |
| Promotion shift correct             | shift == frac_bits − adc_frac    |
| Cascade gain within budget          | G_total < 8.0                    |
| Constants consistent                | PI / 2²⁷ ≈ 3.14159…             |
