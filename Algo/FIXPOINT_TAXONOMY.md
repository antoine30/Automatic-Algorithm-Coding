# Fixed-Point Operation Taxonomy

This document defines the standard vocabulary and decomposition rules
for describing fixed-point arithmetic in Low Level Requirements (LLRs).

Every operation group in every algorithm LLR must follow this taxonomy.
Each row in an LLR operation table corresponds to exactly one elementary
operation from one of the three families below. Arithmetic and format
shaping are never mixed on the same row.

---

## The Three Families

### 1. Arithmetic operations

Arithmetic operations produce a numerical result. They do not change
the Q format intentionally — though multiplication is an exception that
widens the format as a mathematical consequence, not as a shaping step.

| Operation   | Description                                      | FP IN           | FP OUT       |
|-------------|--------------------------------------------------|-----------------|--------------|
| add         | Widen both to int64, add                         | 2× int32 Q4.27  | int64 Q4.27  |
| subtract    | Widen both to int64, subtract                    | 2× int32 Q4.27  | int64 Q4.27  |
| multiply    | Widen both to int64, multiply                    | 2× int32 Q4.27  | int64 Q8.54  |
| accumulate  | Widen to int64, add to int64 accumulator         | int32 Q4.27     | int64 Q4.27  |

Key rules:
- Both operands of a multiply must be widened to int64 before the operation.
  Multiplying two int32 values directly is forbidden (silent overflow).
- The accumulator stays int64 for the full duration of accumulation.
  It is never truncated to int32 between terms.
- Add and subtract preserve the Q format (Q4.27 ± Q4.27 = Q4.27).
- Multiply widens the format (Q4.27 × Q4.27 = Q8.54) as a mathematical
  consequence. This is resolved by a shift in the format shaping step.

---

### 2. Format shaping operations

Format shaping operations reposition the binary point. They carry no
arithmetic meaning — they adjust the Q format to match the pipeline
target. There are three elementary shaping operations:

| Operation    | Description                                      | FP IN         | FP OUT        |
|--------------|--------------------------------------------------|---------------|---------------|
| shift right  | >> frac_bits — renormalizes after multiply       | int64 Q8.54   | int64 Q4.27   |
| shift left   | << N — promotes from a narrower format           | int16 Q1.15   | int32 Q4.27   |
| round        | Add 0.5 LSB before shift right — optional        | int64 Q8.54   | int64 Q8.54   |

Key rules:
- Shift right is always applied after multiply, never before.
  The shift amount equals frac_bits (27 for Q4.27), derived from
  LLR_ALG_000 — never hardcoded independently.
- Shift left (promote) is applied once per sample at pipeline entry.
  The shift amount is derived as: pipeline_frac_bits − adc_frac_bits.
  For Q4.27 and a 12-bit left-aligned ADC: 27 − 15 = 12.
- Round is optional. When used, it is inserted before the shift right:
  add (1 << (frac_bits − 1)) to the int64 value, then shift.
- Format shaping never stands alone — it always follows an arithmetic
  operation that produced the input format.

---

### 3. Saturation (clamp)

Saturation is always the last operation before storing a value to int32.
It is never applied in the middle of an accumulation, and never applied
to an int64 accumulator between samples.

| Operation | Description                                      | FP IN         | FP OUT       |
|-----------|--------------------------------------------------|---------------|--------------|
| saturate  | Clamp to word_size bits, store to int32          | int64 Q4.27   | int32 Q4.27  |

Key rules:
- Saturate is applied at every point where a value is stored to int32.
  No int32 store is permitted without a preceding saturate.
- Saturate is never applied to the int64 accumulator between terms
  in a MAC or phase accumulation. Only the final output is saturated.
- The saturation width (32 bits) is derived from word_size in LLR_ALG_000.
- The target-specific mechanism (hardware instruction or software clamp)
  is selected by the code generator based on the target in MASTER.md.

---

## Composite Groups

Some operations in the LLRs are composite — they are named sequences
of elementary operations from the three families above. Composites are
documented as ordered step tables, each step being one elementary
operation.

| Composite     | Elementary sequence                                        |
|---------------|------------------------------------------------------------|
| MAC           | multiply × N → accumulate × N → shift right → saturate    |
| phase wrap    | subtract → compare → add or subtract TWOPI → saturate      |
| promote       | shift left → (no saturate — input always in range)         |
| CORDIC iter   | shift right (× 2 per iter) → add → subtract → (no sat.)   |
| CORDIC final  | (after all iterations) → saturate                          |

Composite groups obey the same rule: each step is one elementary
operation, and format shaping and arithmetic are never on the same line.

---

## LLR Operation Table Format

Every operation group in an LLR must use this exact column structure:

```
| Step | FP IN        | Operation      | FP OUT       | Shift  | Saturate |
|------|-------------|----------------|--------------|--------|----------|
| N.1  | int32 Q4.27 | widen to int64 | int64 Q4.27  | none   | no       |
| N.2  | int64 Q4.27 | multiply       | int64 Q8.54  | none   | no       |
| N.3  | int64 Q8.54 | >> 27          | int64 Q4.27  | >> 27  | no       |
| N.4  | int64 Q4.27 | saturate       | int32 Q4.27  | none   | yes / 32 |
```

Column rules:

| Column    | Content                                                     |
|-----------|-------------------------------------------------------------|
| Step      | Group index dot step index: N.1, N.2, …                    |
| FP IN     | Full type and Q format of the input: `int32 Q4.27`         |
| Operation | One elementary operation name from this taxonomy           |
| FP OUT    | Full type and Q format of the output: `int64 Q8.54`        |
| Shift     | Shift amount if this step is a shift, otherwise `none`     |
| Saturate  | `yes / 32` if this step saturates, otherwise `no`         |

One elementary operation per row. Never combine arithmetic and shaping
on the same row. Never omit the FP IN or FP OUT columns.

---

## Derivation Chain

All format parameters are derived from LLR_ALG_000. No parameter is
defined independently in any algorithm LLR.

```
LLR_ALG_000 defines:
  word_size    = 32
  sign_bit     = 1
  int_bits     = 4       ← from signal range analysis
  frac_bits    = 27      ← 32 − 1 − 4

Derived in every algorithm LLR:
  shift right amount     = frac_bits         = 27
  CORDIC iterations      = frac_bits         = 27
  accumulator width      = 2 × word_size     = 64 bits
  saturation width       = word_size         = 32 bits
  promote shift (ADC)    = frac_bits − 15    = 12
```

Any change to word_size or int_bits in LLR_ALG_000 propagates
automatically to all derived parameters. No algorithm LLR needs
to be modified — only LLR_ALG_000 and the generated code change.

---

## Quick Reference

```
Arithmetic:    int32 Q4.27  →  [widen]  →  int64 Q4.27 or Q8.54
                                               ↓
Format shape:  int64 Q8.54  →  [>> 27]  →  int64 Q4.27
                                               ↓
Saturate:      int64 Q4.27  →  [clamp]  →  int32 Q4.27
```

This three-step pattern is the core of every fixed-point operation
in the pipeline. It repeats at every stage boundary, with the
accumulator step inserted between arithmetic and shaping for MAC loops.
