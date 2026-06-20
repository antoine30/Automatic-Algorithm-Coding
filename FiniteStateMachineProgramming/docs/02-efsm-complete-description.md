# 02 — Complete System Description: the EFSM

[← 01](01-what-is-a-fsm.md) | [Next: Tools →](03-modeling-tools.md)

---

## Can an FSM Fully Describe a Real-Time System?

Yes — but only if you extend the classic FSM definition with two additional dimensions: **time** and **data**. Without them, you describe logical behavior but not real-time guarantees.

## The Five-Element Model (EFSM)

A real-time embedded system is completely described by the quintuple **(S, E, T, Ctx, Θ)**:

| Element | Symbol | Role | Piezo example |
|---------|--------|------|---------------|
| Discrete states | **S** | Qualitative situations, exclusive | OFF, INIT, SCAN, LOCK, RUN, PAUSE, FAULT |
| Events | **E** | Stimuli — passive, they arrive | CMD_START, EVT_PLL_TICK, EVT_FAULT |
| Transitions + guards | **T** | Rules T(S,E,guard)→S'+action | T(RUN, ADC_READY, v>120V)→FAULT+cut() |
| Data context | **Ctx** | Extended memory — continuous values | freq, amp, voltage_mv, pll_integrator |
| Timing constraints | **Θ** | Periods, max delays, WCET, latencies | PLL:1ms, init timeout:50ms, ISR:<10µs |

## What Classic FSM Misses

### Missing: Time

A classic FSM knows a timeout can expire but not *when* it expires.

```yaml
# Classic FSM — timeless
INIT --[TIMEOUT]--> FAULT   # knows it can expire, not after how long

# Timed automaton (UPPAAL style)
INIT:
  invariant: x <= 50         # cannot stay more than 50ms
  transition: x >= 50 -> FAULT
```

### Missing: Data

A pure FSM only manipulates discrete states. Real systems manipulate continuous values.

```c
typedef struct {
    State_t  state;          // ← the pure FSM
    float    freq_hz;        // ┐
    float    amp;            // ├ the context — invisible to pure FSM
    uint32_t voltage_mv;     // │
    uint8_t  fault_code;     // ┘
} Ctx_t;
```

## Bug Taxonomy

Every embedded bug falls into exactly one of five categories:

| Category | Typical symptom | Example | Detection tool |
|----------|----------------|---------|----------------|
| **State bug** | System in incoherent state | FSM in RUN but FPGA not initialized | State invariants, SPIN |
| **Event bug** | Event lost, duplicated, wrong order | FPGA_READY lost — FSM stuck in INIT | Event logging, queue sizing |
| **Transition bug** | Wrong rule, bad guard, missing action | ramp_down() not called on CMD_STOP | Transition tests, YAML review |
| **Context bug** | Corrupted value, race, overflow | uint16 read as uint32 — guard never fires | Atomics, Valgrind, ASan |
| **Timing bug** | Timing constraint violated | ISR takes 500µs — watchdog expires | Oscilloscope, WCET analyzer |

> **When debugging:** first identify the category. A timing bug won't be fixed by reviewing transitions. A context bug won't be fixed by adding states.

---

*[← 01](01-what-is-a-fsm.md) | [Next: Tools →](03-modeling-tools.md)*
