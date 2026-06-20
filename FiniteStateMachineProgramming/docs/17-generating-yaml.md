# 17 — Generating YAML from SRS and SDD

[← 16](16-yaml-and-security.md) | [Next: DO-178C →](18-do178c-dal-a.md)

---

## Claude Code Can Generate a Partial YAML

Given an SRS and SDD, Claude Code generates YAML with **gaps** marked `[?]` wherever the spec is insufficient or a design decision is required.

## The Three Information Categories

| Category | Source | Claude produces | Remaining work |
|----------|--------|----------------|----------------|
| **A — Direct extraction** | SRS with observable behavior, numeric values | Complete transition, `confidence: HIGH` | Technical validation, DER approval |
| **B — Guided inference** | SDD with implicit sequences | Partial transition with `[?]`, `confidence: MEDIUM` | Engineer fills `[?]` and validates |
| **C — Pure design** | Absent from documents — internal states, technical events | Empty stub with questions, `confidence: LOW` | Engineer designs and documents |

## Generated Output Structure

```yaml
# fsm_generated.yaml
metadata:
  source_srs:    spec_system_v2.1.pdf
  source_sdd:    software_design_v1.3.pdf
  completeness:  67%   # filled transitions / estimated total

transitions:
  # Category A — certain
  - id: LLR-042-001
    from: RUN    event: EVT_ADC_READY
    guard: voltage_mv > 120000
    action: power_cut()    to: FAULT
    timing: { max_latency_ms: 1 }
    req: [SYS-042]    confidence: HIGH

  # Category B — inferred
  - id: LLR-INIT-001
    from: OFF    event: EVT_CMD_START
    action: fpga_reset()    to: INIT
    timing: { max_latency_ms: "[? not specified]" }
    req: []    confidence: MEDIUM
    gap: "No SRS requirement covers this internal transition"

  # Category C — stub
  - id: LLR-044-001
    from: "[?]"    event: EVT_FREQ_CHECK
    guard: "[? out-of-band formula not defined in SDD ?]"
    action: "[?]"    to: "[?]"
    req: [SYS-044]    confidence: LOW
    gap: "SDD does not describe how SYS-044 is implemented"
```

```yaml
# gaps.yaml — structured gap list
critical:
  - id: GAP-001
    type: MISSING_TRANSITION
    description: "SYS-044 (frequency alarm): no LLR in SDD"
    question: "Does the system have an ALARM state distinct from FAULT?"
    action_owner: "System engineer + SW engineer"

  - id: GAP-002
    type: MISSING_GUARD
    description: "Timeout if FPGA_READY never arrives — not specified"
    question: "What timeout? Transition to which state?"
    risk: "Possible deadlock in STATE_INIT"
```

## What Claude Cannot Do Alone

| Decision | Why Claude cannot make it | What Claude does instead |
|----------|--------------------------|-------------------------|
| Internal state decomposition | Architecture depends on hardware and experience | Marks `[? number and names of states ?]` |
| Timing budget allocation | SYS-010 says "2s total" — distribution across sub-steps depends on hardware measurements | Marks `[? budget to allocate]` |
| Conflict resolution between documents | If SRS says 120V and SDD says 115V — Claude detects but doesn't know which is authoritative | Reports conflict with both values |

> **Gaps detected at specification cost 10-100x less than the same gaps discovered during integration or production.**

---

*[← 16](16-yaml-and-security.md) | [Next: DO-178C →](18-do178c-dal-a.md)*
