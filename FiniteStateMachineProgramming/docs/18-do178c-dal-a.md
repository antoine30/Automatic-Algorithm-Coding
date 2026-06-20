# 18 — DO-178C DAL-A Certification Chain

[← 17](17-generating-yaml.md) | [Next: WCET →](19-wcet-discipline.md)

---

## What is DO-178C?

DO-178C (Software Considerations in Airborne Systems) is the reference standard for avionics software. It defines five criticality levels DAL-A through DAL-E.

| Level | Effect of failure | Example | Max probability |
|-------|-----------------|---------|-----------------|
| **DAL-A** | CATASTROPHIC — loss of aircraft | Primary flight control, FADEC | < 10⁻⁹/flight hour |
| **DAL-B** | HAZARDOUS — serious crew injury | Navigation, autopilot | < 10⁻⁷/flight hour |
| **DAL-C** | MAJOR — significant safety margin reduction | Secondary cockpit display | < 10⁻⁵/flight hour |
| **DAL-D** | MINOR — passenger discomfort | Cabin lighting | < 10⁻³/flight hour |
| **DAL-E** | NO EFFECT on safety | Ground maintenance software | Unconstrained |

> **DO-178C does not certify the software — it certifies the PROCESS that produced the software.**

## The 8-Phase Chain

```
Phase 1 : PLANNING        → PSAC, SDP, SVP, SCMP, SQAP
Phase 2 : REQUIREMENTS    → HLR (SRS), LLR (SDD = YAML)
Phase 3 : DESIGN          → Architecture, partitioning, WCET analysis
Phase 4 : CODE            → MISRA C, annotated C with @req
Phase 5 : VERIFICATION    → Static analysis, formal proof, code review
Phase 6 : TESTING         → Unit tests, MC/DC 100% coverage
Phase 7 : TOOL QUAL.      → DO-330 TQL-1 to TQL-5
Phase 8 : DER REVIEW      → Independent approval, SAS
```

## MC/DC — Why It Matters

DAL-A requires **MC/DC** (Modified Condition/Decision Coverage) — the most demanding test criterion. Every elementary condition must be shown to independently influence the decision outcome.

```c
// Guard: (voltage_mv > vmax) AND (temp_c > tmax)
// MC/DC requires N+1 = 3 tests:
//
// TC   voltage > vmax   temp > tmax   Decision   Isolated effect
// ──   ──────────────   ───────────   ────────   ──────────────
// TC1  FALSE            FALSE         FALSE      (baseline)
// TC2  TRUE             FALSE         FALSE      voltage alone does NOT trigger
// TC3  FALSE            TRUE          FALSE      temp alone does NOT trigger
// TC4  TRUE             TRUE          TRUE       BOTH required → verified
```

## YAML Position in DO-178C

The YAML FSM is the **LLR (Low Level Requirements)** document — phase 2 output. Each transition = one LLR. Each LLR must have:
- Traceability to one or more HLR (`derives` field)
- A corresponding test case (`test` field)
- A code reference (`@req` annotation in C)

```yaml
- id:      LLR-042-001
  from:    RUN
  event:   EVT_ADC_READY
  guard:   voltage_mv > vmax_threshold
  action:  power_cut()
  to:      FAULT
  timing:  { max_latency_ms: 1 }
  derives: HLR-FSM-042         # upward traceability
  test:    TC-042-001           # test traceability
  review:  approved             # DER review status
```

---

*[← 17](17-generating-yaml.md) | [Next: WCET →](19-wcet-discipline.md)*
