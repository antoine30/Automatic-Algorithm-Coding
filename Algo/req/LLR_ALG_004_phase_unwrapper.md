# LLR_ALG_004 — Phase Unwrapper

## Level : LOW LEVEL
## Parent HLR : HLR_003
## Version : 4.0
## Depends on : LLR_ALG_003, LLR_ALG_006, LLR_ALG_000

## Files to Generate
- src/algorithms/PhaseUnwrapper.h
- src/algorithms/PhaseUnwrapper.cpp
- tests/test_phase_unwrapper.cpp

---

## 1. Purpose

Removes 2π discontinuities from instantaneous phase. Maintains
cross-buffer int64 state for continuity between DMA callbacks.

---

## 2. Arithmetic Parameters (from LLR_ALG_000)

| Parameter          | Value   | Source                         |
|--------------------|---------|--------------------------------|
| Input format       | Q4.27   | LLR_ALG_000 §3.2               |
| Output format      | Q4.27   | LLR_ALG_000 §3.2               |
| Subtract group     | Group D | LLR_ALG_000 §4                 |
| Wrap group         | Group F | LLR_ALG_000 §4                 |
| Accumulate group   | Group E | LLR_ALG_000 §4                 |
| PI constant        | Q4.27   | LLR_ALG_000 §5                 |
| TWOPI constant     | Q4.27   | LLR_ALG_000 §5                 |
| Accumulator type   | int64   | LLR_ALG_000 §4 (Group E)       |
| Saturation         | 32 bits | LLR_ALG_000 §3.2               |

---

## 3. Mathematical Definition

Per sample n:
```
Δ[n] = phase[n] − phase[n−1]       (delta)
Δ[n] = wrap(Δ[n], −π, +π)          (remove 2π jumps)
Φ[n] = Φ[n−1] + Δ[n]               (accumulate)
```

---

## 4. Operation Groups — FP IN / Operation / FP OUT

### Group 1 — Phase delta (per sample)

Implements: Δ = phase[n] − prev_phase

| Step | FP IN                    | Operation            | FP OUT       | Shift | Saturate |
|------|--------------------------|----------------------|--------------|-------|----------|
| 1.1  | int32 Q4.27 (phase[n])  | widen to int64       | int64 Q4.27  | none  | no       |
| 1.2  | int32 Q4.27 (prev)      | widen to int64       | int64 Q4.27  | none  | no       |
| 1.3  | int64 Q4.27 − int64 Q4.27| subtract            | int64 Q4.27  | none  | no       |
| 1.4  | int64 Q4.27              | saturate to 32 bits  | int32 Q4.27  | none  | yes / 32 |

Format preserved: Q4.27 − Q4.27 = Q4.27. No shift needed.

---

### Group 2 — Phase wrap (per sample)

Implements: wrap(Δ, −π, +π) using Group F from LLR_ALG_000.

| Step | FP IN              | Operation                      | FP OUT       | Shift | Saturate |
|------|--------------------|--------------------------------|--------------|-------|----------|
| 2.1  | int32 Q4.27 (Δ)   | compare with PI_Q427 (integer) | bool         | none  | no       |
| 2.2  | int32 Q4.27 (Δ)   | subtract TWOPI_Q427 if > +π   | int32 Q4.27  | none  | yes / 32 |
| 2.3  | int32 Q4.27 (Δ)   | add TWOPI_Q427 if < −π        | int32 Q4.27  | none  | yes / 32 |

Comparison is direct integer comparison (no float, no shift).
Constants PI_Q427 and TWOPI_Q427 from LLR_ALG_000 §5.
Only one of steps 2.2 or 2.3 executes per sample.

---

### Group 3 — Phase accumulation (per sample, cross-buffer)

Implements: Φ[n] = Φ[n−1] + Δ[n], using Group E from LLR_ALG_000.

| Step | FP IN                    | Operation                   | FP OUT       | Shift | Saturate              |
|------|--------------------------|-----------------------------|--------------|-------|-----------------------|
| 3.1  | int32 Q4.27 (Δ)         | widen to int64              | int64 Q4.27  | none  | no                    |
| 3.2  | int64 Q4.27 + int64 Q4.27 (acc)| add to accumulator   | int64 Q4.27  | none  | no (int64 holds)      |
| 3.3  | int64 Q4.27              | saturate on output write    | int32 Q4.27  | none  | yes / 32              |

Accumulator stays int64 Q4.27 between samples and across buffers.
No shift because add of Q4.27 preserves Q4.27 format.
Saturation applied only at step 3.3 when writing to output buffer.

---

### Group 4 — State update (per sample)

| Step | FP IN              | Operation                | FP OUT       | Shift | Saturate |
|------|--------------------|--------------------------|--------------|-------|----------|
| 4.1  | int32 Q4.27 (phase[n])| store as prev_phase   | int32 Q4.27  | none  | no       |

---

### Group 5 — First sample initialization

Executed only when initialized = false (first sample after reset).

| Step | FP IN              | Operation                | FP OUT       | Shift | Saturate |
|------|--------------------|--------------------------|--------------|-------|----------|
| 5.1  | int32 Q4.27 (phase[0])| copy to accumulator  | int64 Q4.27  | none  | no       |
| 5.2  | int32 Q4.27 (phase[0])| copy to prev_phase   | int32 Q4.27  | none  | no       |
| 5.3  | int64 Q4.27 (acc)  | saturate → output[0]     | int32 Q4.27  | none  | yes / 32 |

---

## 5. Format Trace per Sample

| Stage            | FP IN        | Group   | FP OUT       | Shift | Saturate |
|------------------|--------------|---------|--------------|-------|----------|
| Phase input      | int32 Q4.27  | —       | int32 Q4.27  | —     | —        |
| Delta compute    | int32 Q4.27  | Group 1 | int32 Q4.27  | none  | yes/32   |
| Wrap             | int32 Q4.27  | Group 2 | int32 Q4.27  | none  | yes/32   |
| Accumulate       | int32 Q4.27  | Group 3 | int64 Q4.27  | none  | no       |
| Write output     | int64 Q4.27  | Group 3 | int32 Q4.27  | none  | yes/32   |
| Update prev      | int32 Q4.27  | Group 4 | int32 Q4.27  | none  | no       |

---

## 6. Cross-Buffer State

| Variable    | Type    | FP format | Initial | Persists |
|-------------|---------|-----------|---------|----------|
| prev_phase  | int32_t | Q4.27     | 0       | yes      |
| accumulator | int64_t | Q4.27     | 0       | yes      |
| initialized | bool    | —         | false   | yes      |

---

## 7. Constraints

- No float in any group
- No shift in any group (subtract and add preserve Q4.27)
- Accumulator int64 never truncated between samples
- Saturation at every int32 store
- TWOPI from LLR_ALG_000 §5 only

---

## 8. Test Requirements

| Test ID | FP IN        | Groups exercised   | Expected FP OUT          |
|---------|--------------|--------------------|--------------------------  |
| T001    | int32 Q4.27  | 1,2,3,4            | monotone rising output   |
| T002    | int32 Q4.27  | 1,2 (wrap +π)      | continuous, no jump       |
| T003    | int32 Q4.27  | 1,2 (wrap −π)      | continuous, no jump       |
| T004    | int32 Q4.27  | all, 2 buffers     | same as 1 buffer          |
| T005    | reset state  | Group 5            | output[0] = input[0]      |
| T006    | int32 Q4.27  | Group 3 only       | acc stays int64, no trunc |
