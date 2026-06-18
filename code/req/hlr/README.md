# HLR — High Level Requirements

High Level Requirements describe **what** the system must do from a
functional perspective, without specifying how it is implemented.

---

## Files

| File                | Description                          |
|---------------------|--------------------------------------|
| `HLR_001_system.md` | Top-level system functional requirements |

---

## HLR structure

Each HLR contains:

- **Description** — functional purpose in plain language
- **Requirements** — numbered, testable statements (HLR\_xxx\_yy)
- **Validation criteria** — observable conditions that prove compliance
- **Associated LLRs** — which LLRs implement this HLR

---

## Traceability

Every LLR references its parent HLR. The traceability matrix
in [`../master/MASTER.md`](../master/MASTER.md) maps each HLR
to its LLRs and generated files.

---

## Writing HLRs

Good HLRs are:
- **Testable** — you can verify them without reading source code
- **Technology-neutral** — no mention of specific ICs or APIs
- **Complete** — cover normal operation, error cases, and timing

Bad HLRs contain implementation details, API names, or register values.
Those belong in LLRs.
