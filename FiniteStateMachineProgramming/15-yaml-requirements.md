# 15 — YAML as Executable Requirements

[← 14](14-document-hierarchy.md) | [Next: Security →](16-yaml-and-security.md)

---

## The Fundamental Observation

A requirements document says:

```
REQ-042 : System shall enter FAULT state if voltage exceeds 120V during RUN.
REQ-043 : Cutoff time shall be less than 1ms.
REQ-044 : Only CMD_RESET allows exit from FAULT.
```

The YAML FSM says:

```yaml
- id:     LLR-042-001
  from:   RUN
  event:  EVT_ADC_READY
  guard:  voltage_mv > 120000
  action: power_cut()
  to:     FAULT
  timing: { max_latency_ms: 1 }
  req:    [REQ-042, REQ-043]

- id:     LLR-044-001
  from:   FAULT
  event:  EVT_CMD_RESET
  action: full_reset()
  to:     OFF
  req:    [REQ-044]
```

**Same semantic content. The YAML is executable, verifiable, and generative. The text is not.**

## Why Natural Language Requirements Fail

| Problem | Manifestation | Consequence |
|---------|--------------|-------------|
| **Ambiguity** | "120V" — peak? RMS? | Different implementations |
| **Fragmentation** | REQ-042 and REQ-043 describe one transition separately | No formal link |
| **Non-verifiability** | Cannot run a PDF | Verification is manual |
| **Drift** | Code evolves, requirement stays frozen | Documentation no longer reflects reality |

## Anatomy of a YAML Requirement

| YAML field | Question | Requirement dimension |
|-----------|----------|----------------------|
| `from / to` | In which context? | Scope / precondition |
| `event` | Trigger? | Stimulus |
| `guard` | Exact condition? | Acceptance criterion |
| `action` | What to do? | Response / behavior |
| `timing` | Within what delay? | Timing constraint |
| `safety` | Criticality level? | SIL/DAL level |
| `req` | Why? | Upstream traceability |
| `test` | How to verify? | Acceptance test |
| `rationale` | Justification? | Design rationale |

## Generalization: Every Behavioral Requirement is a Transition

```yaml
# Functional requirement:
# "If user presses STOP during operation, system shall stop cleanly in < 500ms"
- from: RUN  event: CMD_STOP  action: ramp_down()  to: COOLDOWN
  timing: { max_ms: 500 }

# Safety requirement:
# "Voltage shall never exceed 120V during operation"
- from: RUN  event: ADC_READY  guard: voltage_mv > 120000
  action: power_cut()  to: FAULT  timing: { max_ms: 1 }

# Availability requirement:
# "After a fault, system shall be able to restart"
- from: FAULT  event: CMD_RESET  action: full_reset()  to: OFF
```

The pattern is universal: **condition → behavior → constraints → traceability**.

---

*[← 14](14-document-hierarchy.md) | [Next: Security →](16-yaml-and-security.md)*
