# 14 — Document Hierarchy: ConOps, SRS, HLR, SDD

[← 13](13-if-is-a-transition.md) | [Next: YAML →](15-yaml-requirements.md)

---

## The Document Chain

```
CUSTOMER NEED
(natural language, imprecise)
        │
        ▼
   ConOps / URD
(what the user wants to do)
        │
        ▼
    SRS / SRD
(what the SYSTEM must do)
        │
        ▼
    HLR / SW-SRS
(what the SOFTWARE must do)
        │
        ▼
    SDD / LLR          ← THE YAML FSM LIVES HERE
(how the software does it)
        │
        ▼
     SOURCE CODE
```

## Each Document Explained

### ConOps — Concept of Operations
Written by the customer or project manager. No technology, no architecture. The question: what does the operator want to do with the system?

> *"Operator presses START. System starts automatically and emits the acoustic signal within 2 seconds. In case of anomaly, a visual alarm lights up and the system stops itself."*

### SRS — System Requirements Specification
Written by the system engineer from the ConOps. Describes the complete system (hardware + software + interfaces) as a black box.

```
SYS-010 : System shall reach operational state in < 2s after CMD_START.
SYS-042 : System shall detect any voltage > 120V and cut output in < 1ms.
SYS-043 : After a fault, only CMD_RESET allows reinitialization.
```

The SRS does not say "there will be an FSM with a STATE_INIT."

### HLR — High Level Requirements (Software Requirements)
Written by the senior software engineer from the SRS. Describes what the **software** must do.

```
HLR-FSM-010 : Software shall manage a startup sequence from CMD_START
              to operational state in less than 2000ms. [derives SYS-010]

HLR-FSM-042 : Software shall monitor voltage continuously and trigger
              cutoff if voltage exceeds configured threshold in < 1ms.
              [derives SYS-042]
```

### SDD / LLR — Software Design Document
Written by the software engineer from the HLRs. The LLRs (Low Level Requirements) are directly implementable in code. **The YAML FSM is the SDD.**

```
LLR-042-001 : FSM transitions from STATE_RUN to STATE_FAULT when
              EVT_ADC_READY arrives and ctx->voltage_mv > ctx->vmax_threshold.
              Action: power_cut(). Max latency: 1ms. [derives HLR-FSM-042]
```

## The Common Confusion

**SRS can mean two things:**
- System Requirements Specification → system level
- Software Requirements Specification → HLR level (DO-178C usage)

Always specify: "system SRS" or "software SRS / HLR."

---

*[← 13](13-if-is-a-transition.md) | [Next: YAML →](15-yaml-requirements.md)*
