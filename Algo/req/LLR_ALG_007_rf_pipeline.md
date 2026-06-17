# LLR_ALG_007 — RF Processing Pipeline Assembly

## Level : LOW LEVEL
## Parent HLR : HRR_003
## Version : 4.0
## Depends on : LLR_ALG_000, LLR_ALG_001, LLR_ALG_002, LLR_ALG_003, LLR_ALG_004

## Files to Generate
- src/algorithms/RfPipeline.h
- src/algorithms/RfPipeline.cpp
- tests/test_rf_pipeline.cpp

---

## 1. Purpose

Assembles all processing stages into a single callable pipeline.
Defines format at every stage boundary and buffer handoff.

---

## 2. Pipeline Format Trace

This is the master format trace. Every stage boundary is explicit.

| Boundary               | Type          | FP format    | Shift applied | Saturate   |
|------------------------|---------------|--------------|---------------|------------|
| ADC output             | int12         | Q0.11        | —             | —          |
| DMA buffer (left-align)| int16         | Q1.15        | << 4 (HW)    | —          |
| After promote          | int32         | Q4.27        | << 12         | no         |
| After Bessel I channel | int32         | Q4.27        | >> 27 (internal)| yes/32   |
| After Bessel Q channel | int32         | Q4.27        | >> 27 (internal)| yes/32   |
| After CORDIC atan2     | int32         | Q4.27        | none          | yes/32     |
| After phase unwrap     | int32         | Q4.27        | none          | yes/32     |
| Pipeline output        | int32         | Q4.27        | —             | —          |

---

## 3. Operation Groups — FP IN / Operation / FP OUT

### Group 0 — Promote and de-interleave (per buffer)

| Step | FP IN              | Operation                    | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------------|--------------|-------|----------|
| 0.1  | int16 Q1.15 (IQ)  | read dma[2n] → I sample     | int16 Q1.15  | none  | no       |
| 0.2  | int16 Q1.15       | << 12 (= frac − adc_frac)   | int32 Q4.27  | << 12 | no       |
| 0.3  | int16 Q1.15 (IQ)  | read dma[2n+1] → Q sample   | int16 Q1.15  | none  | no       |
| 0.4  | int16 Q1.15       | << 12                        | int32 Q4.27  | << 12 | no       |

Output: iBuf[] int32 Q4.27, qBuf[] int32 Q4.27

---

### Group 1 — Bessel spur removal (per sample, per biquad)

References LLR_ALG_002 Groups 2, 3, 4.

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------|--------------|-------|----------|
| 1.1  | int32 Q4.27 (I)   | biquad MAC (Groups 2,3,4)| int32 Q4.27| >> 27 | yes/32   |
| 1.2  | int32 Q4.27 (Q)   | biquad MAC (Groups 2,3,4)| int32 Q4.27| >> 27 | yes/32   |

Both I and Q channels processed independently.
Output: iBuf[] int32 Q4.27, qBuf[] int32 Q4.27 (in-place)

---

### Group 2 — Phase computation (per sample)

References LLR_ALG_003 Groups 3, 4, 5.

| Step | FP IN                         | Operation              | FP OUT       | Shift | Saturate |
|------|-------------------------------|------------------------|--------------|-------|----------|
| 2.1  | int32 Q4.27 (I), int32 Q4.27 (Q)| gain comp (Group 5)| int32 Q4.27  | >> 27 | yes/32   |
| 2.2  | int32 Q4.27 (I, Q)           | CORDIC 27 iter (Group 3)| int32 Q4.27 | >> i  | no/iter  |
| 2.3  | int32 Q4.27 (z after 27 iter)| final saturate (Group 4)| int32 Q4.27 | none  | yes/32   |

Output: phaseBuf[] int32 Q4.27

---

### Group 3 — Phase unwrapping (per sample)

References LLR_ALG_004 Groups 1, 2, 3, 4.

| Step | FP IN              | Operation              | FP OUT       | Shift | Saturate |
|------|--------------------|------------------------|--------------|-------|----------|
| 3.1  | int32 Q4.27        | delta (Group 1)        | int32 Q4.27  | none  | yes/32   |
| 3.2  | int32 Q4.27        | wrap (Group 2)         | int32 Q4.27  | none  | yes/32   |
| 3.3  | int32 Q4.27        | accumulate (Group 3)   | int64 Q4.27  | none  | no       |
| 3.4  | int64 Q4.27        | write output (Group 3) | int32 Q4.27  | none  | yes/32   |

Output: phaseOut[] int32 Q4.27

---

## 4. Static Buffer Specification

| Buffer   | Type          | FP format | Size         | Owner      |
|----------|---------------|-----------|--------------|------------|
| iBuf     | int32_t array | Q4.27     | MAX_BUF_SIZE | RfPipeline |
| qBuf     | int32_t array | Q4.27     | MAX_BUF_SIZE | RfPipeline |
| phaseBuf | int32_t array | Q4.27     | MAX_BUF_SIZE | RfPipeline |

---

## 5. Interface Specification

### 5.1 process()

| Parameter  | Type          | FP IN/OUT    | Description                   |
|------------|---------------|--------------|-------------------------------|
| dmaBuffer  | int16_t array | Q1.15 IQ     | DMA input, length = 2 × len  |
| phaseOut   | int32_t array | Q4.27        | unwrapped phase output        |
| len        | size_t        | —            | number of IQ pairs            |
| return     | TaskStatus    | —            | OK or first failing stage     |

### 5.2 reset()

| Stage reset        | State cleared                    | FP format cleared |
|--------------------|----------------------------------|-------------------|
| BesselSpurRemoval  | w₁ = 0, w₂ = 0 per biquad      | int64 Q8.54 → 0  |
| PhaseUnwrapper     | prev_phase = 0, accumulator = 0  | int32/int64 Q4.27 → 0 |

---

## 6. Initialization Sequence

| Step | Action                                   | FP IN  | FP OUT       |
|------|------------------------------------------|--------|--------------|
| 1    | Verify frac + int + 1 == 32             | —      | assert       |
| 2    | Compute CORDIC table (LLR_ALG_003 G1)   | float  | int32 Q4.27  |
| 3    | Compute CORDIC_COMP (LLR_ALG_003 G2)    | float  | int32 Q4.27  |
| 4    | Design Bessel coeffs (LLR_ALG_002 G1)   | float  | int32 Q4.27  |
| 5    | Verify cascade gain < 8.0               | float  | assert       |
| 6    | Verify promote shift = frac − adc_frac  | —      | assert       |

Float permitted in steps 1–6 (initialization only).

---

## 7. Timing Budget

| Stage   | Group         | Dominant FP op     | Cycles/sample | Shift cost |
|---------|---------------|--------------------|---------------|------------|
| Promote | Group 0       | << 12              | ~2            | 1 shift    |
| Bessel  | Groups 1–4    | int64 MAC >> 27    | ~15           | 1 shift    |
| CORDIC  | Groups 2–4    | 27× (>> i + add)  | ~30           | 27 shifts  |
| Unwrap  | Groups 1–3    | sub + add          | ~5            | 0 shifts   |
| **Total**| —            | —                  | **~52**       | **29 shifts/sample** |

At 168 MHz, 256 samples: ~80 µs → margin > 10× vs 1 ms target.

---

## 8. Test Requirements

| Test ID | FP IN        | Groups exercised  | Expected FP OUT          |
|---------|--------------|-------------------|--------------------------|
| T001    | int16 Q1.15  | 0,1,2,3           | int32 Q4.27 clean phase  |
| T002    | int16 Q1.15  | 0,1 (spur)        | spur > 40 dB attenuated  |
| T003    | int16 Q1.15  | all               | no jump > π in output    |
| T004    | int16 Q1.15  | all, 2 buffers    | same as 1 full buffer    |
| T005    | any          | reset then proc.  | output starts from 0     |
| T006    | format trace | all boundaries    | see §2 format trace      |
