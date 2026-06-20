# 16 — YAML and Security Analysis

[← 15](15-yaml-requirements.md) | [Next: Generating YAML →](17-generating-yaml.md)

---

## The Incorrect Conclusion

Section 15 showed that YAML formalizes behavioral requirements. One might conclude YAML is at the heart of security analysis. **This is wrong — and dangerous.**

The YAML is a **specification artifact**. System security rests on four independent layers. YAML is only a partial input to the first.

## The Four Security Layers

| Layer | Question | Tools | YAML role |
|-------|----------|-------|-----------|
| **1 — Spec completeness** | Is the specification complete and consistent? | YAML verification, SPIN | **Direct input** |
| **2 — FMEA** | What failures are possible and what are their effects? | FMEA, HAZOP, FTA | Generates new requirements |
| **3 — Code security** | Is the code correct, free of UB and race conditions? | Polyspace, MISRA C, MC/DC | Not involved |
| **4 — Defense in depth** | Does the system remain safe if one component fails? | Redundant architecture, HW protections | Not involved |

## What YAML Guarantees

- Specification is complete — every (state, event) pair has a rule
- Specification is consistent — no contradictory transitions
- Traceability established — every transition points to a REQ
- Timing constraints specified
- Every transition has an associated test

## What YAML Does NOT Guarantee

```c
// YAML says: guard "voltage_mv > 120000"
// Code says:
uint16_t voltage_mv = fpga_read(ADC_VOLTAGE);
//  ^^^^^^^ uint16 — max value = 65535
//          NEVER > 120000
//          the guard is always false — protection NEVER fires

if (voltage_mv > 120000) {   // ← always false
    power_cut();             // ← never executed
}
// YAML is formally correct. Code is dangerous.
// Static analysis detects this. YAML does not.
```

## FMEA Excerpt

| Component | Failure mode | System effect | Criticality | Required mitigation |
|-----------|-------------|--------------|-------------|---------------------|
| FPGA ADC | Stuck at 0 | voltage_mv = 0, guard always false, voltage rises undetected | CRITICAL | ADC watchdog: no new value in 10ms → FAULT |
| power_cut() | SW deadlock | FPGA not cut, voltage continues rising | CRITICAL | Independent HW protection in FPGA (<1µs) |
| Event queue | Queue full, EVT_FAULT lost | RUN→FAULT transition not triggered | CRITICAL | Dedicated urgent queue, non-blocking |

## The Golden Rule

```
YAML → formalizes WHAT the system must do
FMEA → determines WHAT CAN FAIL
Static analysis → verifies THE CODE IS CORRECT
Defense in depth → ensures THE SYSTEM STAYS SAFE even if one level fails

These four questions are independent. All are necessary.
```

---

*[← 15](15-yaml-requirements.md) | [Next: Generating YAML →](17-generating-yaml.md)*
