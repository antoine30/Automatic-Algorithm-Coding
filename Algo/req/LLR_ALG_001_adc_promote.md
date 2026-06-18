# LLR_ALG_001 — ADC Promote and De-interleave

## Level : LOW LEVEL
## Parent HLR : HLR_003
## Version : 4.0
## Depends on : LLR_ALG_000

## Files to Generate
- src/algorithms/AdcPromote.h
- src/algorithms/AdcPromote.cpp
- tests/test_adc_promote.cpp

---

## 1. Purpose

First stage of the RF pipeline. Converts the interleaved, left-aligned ADC DMA
buffer (int16 Q1.15) into two separate int32 Q4.27 channels (I and Q) by a
format-promotion shift. No arithmetic meaning — pure format shaping (Group A).

---

## 2. Arithmetic Parameters (from LLR_ALG_000)

| Parameter        | Value | Source           |
|------------------|-------|------------------|
| Input format     | Q1.15 | ADC, left-aligned |
| Output format    | Q4.27 | LLR_ALG_000 §3.2 |
| Promote shift    | 12    | LLR_ALG_000 §3.2 (frac_bits − adc_frac_bits) |
| Operation group  | Group A | LLR_ALG_000 §4 |

---

## 3. Operation Group — FP IN / Operation / FP OUT

### Group 0 — Promote and de-interleave (per buffer)

| Step | FP IN              | Operation                  | FP OUT       | Shift | Saturate |
|------|--------------------|----------------------------|--------------|-------|----------|
| 0.1  | int16 Q1.15 (IQ)  | read dma[2n] → I sample   | int16 Q1.15  | none  | no       |
| 0.2  | int16 Q1.15       | << 12 (= frac − adc_frac) | int32 Q4.27  | << 12 | no       |
| 0.3  | int16 Q1.15 (IQ)  | read dma[2n+1] → Q sample | int16 Q1.15  | none  | no       |
| 0.4  | int16 Q1.15       | << 12                      | int32 Q4.27  | << 12 | no       |

Promotion never saturates: the input is always in range (PDF taxonomy "promote").

---

## 4. Interface Specification

| Parameter | Direction | Type          | FP        | Description                  |
|-----------|-----------|---------------|-----------|------------------------------|
| dmaBuffer | in        | int16_t array | Q1.15 IQ  | interleaved, length = 2×len |
| iBuffer   | out       | int32_t array | Q4.27     | I channel, len samples       |
| qBuffer   | out       | int32_t array | Q4.27     | Q channel, len samples       |
| len       | in        | size_t        | —         | number of IQ pairs           |

---

## 5. Constraints

- Shift amount derived from LLR_ALG_000 (PROMOTE_SHIFT), never hardcoded.
- No saturation (input always in range).
- No float.

---

## 6. Test Requirements

| Test ID | FP IN        | Expected FP OUT                         |
|---------|--------------|-----------------------------------------|
| T001    | int16 Q1.15  | int32 Q4.27 = sample << 12              |
| T002    | int16 max    | no overflow, exact left shift           |
| T003    | interleaved  | de-interleaved into separate I/Q arrays |
