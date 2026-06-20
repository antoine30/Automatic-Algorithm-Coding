# FSM Rendez-vous — Event-Driven Architecture for Real-Time Embedded Systems

**Antoine DAMON** · Antoine.Damon@laposte.net

> A complete architectural framework for designing real-time embedded systems from system requirements — without mutexes, without blocking, and with provable timing guarantees.

---

## Why this repository?

Real-time embedded systems fail in predictable ways: race conditions from shared state, unbounded execution from dynamic allocation, deadlocks from blocking calls, and behavioral spaghetti from nested if/else chains.

This repository documents a **formal architectural approach** that eliminates these failure modes **by construction** — not by discipline. The approach is based on five formal elements that together completely describe any reactive system, and a set of rules that turn those elements into deterministic, certifiable code.

**The core insight:** every reactive system can be described by five formal elements. Mastering these five is sufficient to specify, implement, test, and certify embedded software — from a Cortex-M0 prototype to a DO-178C DAL-A avionics system.

---

## Table of Contents

### Part I — Foundations
- [01 — What is an FSM?](docs/01-what-is-a-fsm.md)
- [02 — Complete System Description: the EFSM](docs/02-efsm-complete-description.md)
- [03 — FSM Modeling Tools](docs/03-modeling-tools.md)

### Part II — Event-Driven Architecture Without Blocking
- [04 — The Blocking Problem](docs/04-blocking-problem.md)
- [05 — Everything is an Event](docs/05-everything-is-an-event.md)
- [06 — Single-Thread Event-Driven Architecture](docs/06-single-thread-architecture.md)
- [07 — Request/Response Asynchronous Synchronization](docs/07-request-response.md)
- [08 — Publish/Subscribe Event Bus](docs/08-publish-subscribe.md)
- [09 — N-FSM Rendezvous by Counter](docs/09-n-fsm-rendezvous.md)
- [10 — Dual-Priority Queue](docs/10-dual-priority-queue.md)
- [11 — Variable Sharing Without Mutexes](docs/11-variable-sharing.md)
- [12 — Intra-FSM Synchronization and Synthetic Events](docs/12-synthetic-events.md)
- [13 — The IF is a Hidden Transition](docs/13-if-is-a-transition.md)

### Part III — Specification, Documentation and Certification
- [14 — Document Hierarchy: ConOps, SRS, HLR, SDD](docs/14-document-hierarchy.md)
- [15 — YAML as Executable Requirements](docs/15-yaml-requirements.md)
- [16 — YAML and Security Analysis](docs/16-yaml-and-security.md)
- [17 — Generating YAML from SRS and SDD](docs/17-generating-yaml.md)
- [18 — DO-178C DAL-A Certification Chain](docs/18-do178c-dal-a.md)

### Part IV — Real-Time Implementation
- [19 — Real-Time FSM Programming: WCET Discipline](docs/19-wcet-discipline.md)
- [20 — FSM in Modern C++: Smart Pointers and RT](docs/20-cpp-smart-pointers.md)

### Part V — Emergent Properties and Conclusion
- [21 — Design Rules — Summary](docs/21-design-rules.md)
- [22 — Conclusion: Extensibility, Parallelism, Distribution](docs/22-conclusion.md)

---

## The Five Formal Elements

A real-time embedded system is **completely described** by exactly five elements. If one is missing, the description is incomplete and behavior is undefined somewhere.

### 1. States (S) — qualitative memory

A state is a **stable situation** of the system in which it waits for an event. **Only one state is active at any time** — the exclusivity property.

```
OFF → INIT → SCAN → LOCK → RUN ⇌ PAUSE → COOLDOWN → OFF
                               ↓
                             FAULT
```

States make **explicit** what ordinary code keeps implicit:

```c
// Ordinary code — state hidden in boolean combinations
bool initialized = false;
bool running     = false;
bool freq_locked = false;
bool fault       = false;
// 2⁴ = 16 possible combinations, some incoherent

// FSM — explicit state, always coherent
typedef enum { STATE_OFF, STATE_INIT, STATE_RUN, STATE_FAULT } State_t;
State_t state = STATE_OFF;  // unambiguous at all times
```

### 2. Events (E) — stimuli

An event is a **fact that occurs at a given instant**. It is passive — it does nothing by itself. It waits to be processed by the FSM from its current state.

```c
typedef enum {
    EVT_CMD_START,        // operator command
    EVT_FPGA_READY,       // hardware signal
    EVT_ADC_OVERVOLTAGE,  // measurement exceeding threshold
    EVT_PLL_TICK,         // 1ms periodic timer
    EVT_TIMEOUT,          // guard timer expiry
    EVT_CMD_STOP,
    EVT_CMD_RESET,
} EvtType_t;

typedef struct {
    EvtType_t type;
    union {
        uint32_t voltage_mv;   // value carried by the event
        float    freq_hz;
        uint8_t  fault_code;
    } data;
    uint32_t timestamp_ms;
} FsmEvent_t;
```

> **Key principle:** an event is a **value copy** passed through a thread-safe queue. Never a pointer into shared memory. This is what eliminates race conditions.

### 3. Transitions (T) — the rules

A transition is a **rule**: `T(state, event, guard) → destination_state + action`.

```
T(RUN, EVT_ADC_OVERVOLTAGE, voltage > 120V) → FAULT + power_cut()
T(RUN, EVT_CMD_STOP,        —             ) → COOLDOWN + ramp_down()
T(OFF, EVT_CMD_START,       —             ) → INIT + fpga_init()
```

- The **state** says where we are
- The **event** says what arrived
- The **guard** says whether the transition fires (condition on context)
- The **action** says what to do (short, non-blocking)
- The **destination** says where we go

**The same event produces different transitions depending on the current state:**

```c
// EVT_CMD_STOP in RUN   → COOLDOWN (controlled ramp-down)
// EVT_CMD_STOP in PAUSE → COOLDOWN (direct shutdown)
// EVT_CMD_STOP in INIT  → ignored (no rule defined)
```

### 4. Context (Ctx) — quantitative memory

The context is the **extended memory** of the FSM — continuous values, counters, coefficients. It is not a state (discrete) but a set of variables (continuous).

```c
typedef struct {
    // The pure FSM
    State_t  state;

    // Extended context (EFSM — Extended FSM)
    float    freq_hz;           // measured resonance frequency
    float    pll_integrator;    // PLL integrator state
    uint32_t voltage_mv;        // last ADC measurement
    uint8_t  fault_code;        // active fault code
    uint8_t  scan_idx;          // sweep progress counter
    uint32_t sync_flags;        // synchronization bitmask
} Ctx_t;
```

Guards use the context to create **quantitative conditions**:

```c
case EVT_ADC_READY:
    ctx->voltage_mv = ev.data.voltage_mv;
    if (ctx->voltage_mv > ctx->vmax_threshold) {  // guard on context
        enter_fault(ctx, FAULT_OVERVOLTAGE);
    }
    break;
```

### 5. Timing constraints (Θ) — the guarantees

```
PLL timer      : period 1ms    ±50µs   (firm RT)
Init timeout   : max 50ms              (guard)
Fault cutoff   : max 1ms               (hard RT)
ISR latency    : max 260ns             (hardware)
```

> **Without timing constraints, you describe logical behavior but not real-time guarantees.** A system can be functionally correct and not real-time.

---

## Why It's Deterministic

**Deterministic does not mean fast.** It means: you can **prove** that an action will occur within a bounded delay, in all cases, including the worst case.

### The three sources of non-determinism

```
Source 1 — Unbounded heap
  malloc() can take 0 to ∞ cycles depending on fragmentation
  → Forbidden in FSM transitions

Source 2 — Unbounded loops
  for (int i = 0; i < n_external; i++) { ... }
  n_external could be 1 or 100000
  → All loops must be bounded by a compile-time constant

Source 3 — Blocking
  k_sem_take(K_FOREVER) — waits indefinitely
  → Replace with: post(EVT) + WAIT state + guard timer
```

### The end-to-end timing guarantee chain

```
Critical event (overvoltage detected)
│
│  ~260ns : IRQ hardware latency (Cortex-R5, fixed by silicon)
▼
ISR: clear IRQ + post(EVT_FAULT) to urgent queue
│
│  ~100ns : ISR WCET (post and exit, ~10 instructions)
▼
Zephyr preempts current thread (priority 1 > all)
│
│  ~2µs : scheduler latency
▼
fsm_process(EVT_FAULT) — short transition
│
│  ~300ns : transition WCET (fpga_write + set_state, <30 instructions)
▼
fpga_write(CTRL, RESET) — physical action taken

TOTAL: ~3µs  <<  1ms deadline  ✓
```

Each term is **independently bounded** and **measurable on target** with a GPIO and oscilloscope.

| Term | Value | Bounded by |
|------|-------|-----------|
| IRQ hardware latency | ~260ns | Silicon — datasheet |
| ISR WCET | <100ns | Rule: post and exit |
| Scheduler latency | ~2µs | Priority 1 — preempts everything |
| Transition WCET | <300ns | 8 programming rules |
| **Total** | **<3µs** | **<< 1ms deadline** |

---

## Why It's Robust

Robustness comes from the **structural impossibility** of certain bug classes — not from better human discipline.

### Property 1 — Exhaustiveness

The transition table lists all `(state, event)` pairs. A tool can mechanically verify that no case is unhandled.

```python
def verify_completeness(fsm):
    gaps = []
    for state in fsm['states']:
        for event in fsm['events']:
            if not any(t['from']==state and t['event']==event
                       for t in fsm['transitions']):
                gaps.append((state, event))
    return gaps
# A gap = undefined behavior = potential production bug
```

### Property 2 — Exclusive ownership

```
Thread A (prio 1) → owns ctx_a → NEVER ctx_b
Thread B (prio 5) → owns ctx_b → NEVER ctx_a

Communication: value copies only, through thread-safe queues
```

**Consequence:** zero race conditions on application state by construction. No mutex on context — impossible to forget one.

### Property 3 — Guard on every WAIT state

```c
// Without guard — potential deadlock
case STATE_WAIT_FPGA:
    if (ev.type == EVT_FPGA_READY) {
        set_state(STATE_SCAN);
    }
    // What if EVT_FPGA_READY never arrives?
    // FSM stays in STATE_WAIT_FPGA forever.

// With guard — deadlock impossible
case STATE_WAIT_FPGA:
    if (ev.type == EVT_FPGA_READY) {
        timer_stop(&ctx->tmr_guard);
        set_state(STATE_SCAN);
    } else if (ev.type == EVT_TIMEOUT) {
        enter_fault(ctx, FAULT_FPGA_INIT);  // guaranteed exit
    }
    break;
```

> **Absolute rule:** every `WAIT_xxx` state must have a guard timer. A wait state without a timeout is a deadlock in disguise.

### Property 4 — Full traceability

Every transition is an LLR (Low Level Requirement). Every LLR has a test. The chain is mechanically verifiable:

```
SYS-042 → HLR-FSM-042 → LLR-042-001 → fsm_run_state() → TC-042-001
                                         (code)              (test)
```

---

## From Requirements to Code

### Document hierarchy

```
ConOps     "Operator presses START, system reaches operational state in < 2s"
   ↓
SRS        SYS-042 : voltage > 120V → cutoff < 1ms
           SYS-010 : operational state in < 2s after CMD_START
   ↓
HLR        HLR-FSM-042 : software monitors voltage continuously
           HLR-FSM-010 : software manages startup sequence
   ↓
SDD/LLR    LLR-042-001 : T(RUN, ADC_READY, voltage > 120000) → FAULT
  = YAML   LLR-010-001 : T(OFF, CMD_START) → INIT + fpga_init()
   ↓
CODE       case EVT_ADC_OVERVOLTAGE: enter_fault(ctx, FAULT_OVERVOLT);
   ↓
TEST       test_TC042_001_overvoltage_in_run()
```

### YAML as formal SDD

The YAML FSM **is** the SDD. Each transition = one LLR.

```yaml
transitions:
  - id:      LLR-042-001
    from:    RUN
    event:   EVT_ADC_READY
    guard:   voltage_mv > 120000        # SYS-042: "voltage > 120V"
    action:  power_cut()
    to:      FAULT
    timing:  { max_latency_ms: 1 }      # SYS-042: "< 1ms"
    req:     [SYS-042]
    test:    TC-042-001
    confidence: HIGH

  - id:      LLR-INIT-001
    from:    OFF
    event:   EVT_CMD_START
    action:  fpga_reset()
    to:      INIT
    timing:  { max_latency_ms: "[? budget not specified]" }
    req:     []
    confidence: MEDIUM
    question: "What timeout if FPGA_READY never arrives?"
```

---

## The 8 Real-Time Programming Rules

| # | Rule | Forbidden | Guaranteed Property |
|---|------|-----------|---------------------|
| R1 | No blocking calls | sleep, semaphore, blocking I/O | WCET bounded |
| R2 | No dynamic allocation | malloc, new, free | No compaction |
| R3 | Bounded loops | Loop on external N | WCET = CHUNK × WCET(body) |
| R4 | No recursion | Direct or indirect recursion | Stack bounded |
| R5 | Documented WCET | Functions without measured WCET | Total WCET = sum |
| R6 | Delegate long actions | Heavy processing inline | Budget respected |
| R7 | Minimal ISR | Computation in ISR | Latency = hardware only |
| R8 | No hidden paths | Global state influencing path | Static analysis exact |

---

## The Three Architectural Virtues

All three emerge from the same principle: **decoupling by message**.

### 1. Extensibility

```c
// Adding EVT_FREQ_OUT_BAND does not touch existing transitions
case STATE_RUN:
    switch (ev.type) {
    case EVT_ADC_OVERVOLTAGE: enter_fault(ctx, FAULT_VOLTAGE); break; // unchanged
    case EVT_CMD_STOP:        set_state(ctx, STATE_COOLDOWN);  break; // unchanged
    case EVT_FREQ_OUT_BAND:   set_state(ctx, STATE_RESCAN);    break; // new — zero risk
    }
```

### 2. Parallelism

```
Thread A (prio 1) → owns ctx_a exclusively → queue_a
Thread B (prio 5) → owns ctx_b exclusively → queue_b
         ↕ (only contact: thread-safe queues)
```

Zero mutex on application state. Zero risk of inversion of priority on context.

### 3. Distribution

```c
// FSM always calls the same interface
osal_queue_send(&g_target_queue, &ev, NO_WAIT);

// Only the OSAL changes per deployment:
// Mode 1: Zephyr k_msgq      → latency < 1µs   (same thread)
// Mode 2: AMP shared memory  → latency 10-100µs (dual-core)
// Mode 3: IPC mailbox R5+A53 → latency 50-500µs (heterogeneous)
// Mode 4: CAN FD / Ethernet  → latency < 10ms   (networked nodes)
```

---

## Repository Structure

```
.
├── README.md                         ← this file
├── docs/
│   ├── 01-what-is-a-fsm.md           ← Part I
│   ├── 02-efsm-complete-description.md
│   ├── 03-modeling-tools.md
│   ├── 04-blocking-problem.md        ← Part II
│   ├── 05-everything-is-an-event.md
│   ├── 06-single-thread-architecture.md
│   ├── 07-request-response.md
│   ├── 08-publish-subscribe.md
│   ├── 09-n-fsm-rendezvous.md
│   ├── 10-dual-priority-queue.md
│   ├── 11-variable-sharing.md
│   ├── 12-synthetic-events.md
│   ├── 13-if-is-a-transition.md
│   ├── 14-document-hierarchy.md      ← Part III
│   ├── 15-yaml-requirements.md
│   ├── 16-yaml-and-security.md
│   ├── 17-generating-yaml.md
│   ├── 18-do178c-dal-a.md
│   ├── 19-wcet-discipline.md         ← Part IV
│   ├── 20-cpp-smart-pointers.md
│   ├── 21-design-rules.md            ← Part V
│   └── 22-conclusion.md
├── fsm/
│   ├── fsm.yaml                      ← single source of truth (formal SDD)
│   ├── fsm_skeleton.c                ← generated C skeleton
│   ├── fsm_tests.c                   ← generated Unity tests
│   ├── fsm.puml                      ← generated PlantUML diagram
│   └── gaps.yaml                     ← detected specification gaps
├── osal/
│   ├── osal.h                        ← OSAL interface
│   └── osal_zephyr.c                 ← Zephyr implementation
└── tools/
    ├── yaml_to_c.py                  ← C code generation from YAML
    ├── yaml_verify.py                ← completeness verification
    └── req_matrix.py                 ← traceability matrix generator
```

---

## References

- **Miro Samek** — *Practical UML Statecharts in C/C++, 2nd Ed.* (Elsevier, 2008)
- **QP/C & QP/C++** — github.com/QuantumLeaps/qpc
- **PlantUML** — plantuml.com
- **Zephyr RTOS** — zephyrproject.org
- **MISRA C 2012** — misra.org.uk
- **DO-178C** — RTCA/DO-178C Software Considerations in Airborne Systems
- **IEC 61508** — Functional Safety of E/E/PE Safety-related Systems

---

*Antoine DAMON · Antoine.Damon@laposte.net*
