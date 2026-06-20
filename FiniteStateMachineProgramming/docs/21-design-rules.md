# 21 — Design Rules — Summary

[← 20](20-cpp-smart-pointers.md) | [Next: Conclusion →](22-conclusion.md)

---

## The Decision Tree

```
Do I need to synchronize two FSMs or share data?
│
├── No → nothing to do (single-thread = sequential by construction)
│
├── FSM A waits for a result from FSM B
│   └── Async Request/Response
│       ├── A posts EVT_REQ and changes to WAIT_xxx state
│       ├── B processes and posts EVT_RESPONSE to A's queue
│       └── MANDATORY guard timer on every WAIT_xxx state
│
├── Multiple FSMs react to the same event
│   └── Publish/Subscribe bus
│       ├── Publisher: bus_publish() without knowing subscribers
│       └── Subscribers: bus_subscribe() at startup
│
├── Wait for N subsystems
│   └── Bitmask counter in context + global guard timer
│
├── Urgent event in a long queue
│   └── Two queues: urgent + normal, drain urgent first
│
└── Share a variable
    ├── 32-bit scalar (threshold, flag, counter)
    │   └── atomic_store / atomic_load
    ├── Struct (sensor state, config)
    │   ├── Embed in event (if point-in-time send)
    │   └── Double buffer + atomic index (if frequent reads)
    └── Mutex as last resort only
        └── Never from an ISR — never on critical path
```

## The 10 Fundamental Rules

| Rule | Principle | Consequence |
|------|-----------|-------------|
| **R1** — No blocking | FSM returns immediately after each event | Watchdog guaranteed, deterministic latency |
| **R2** — Everything is an event | Timers, ISRs, results: all post to queue | Zero concurrent access |
| **R3** — One thread owns hardware | Only the FSM thread calls fpga_write() | Zero mutex on peripherals |
| **R4** — Every WAIT has a guard | No wait state without explicit timeout | Deadlock impossible |
| **R5** — IF belongs to sensor or guard | switch/case is a list of facts, not decisions | Extensibility, independent testability |
| **R6** — Check condition after every event | Event arrival order is irrelevant | Correct synchronization |
| **R7** — Synthetic event for complex transitions | Transition cause is a traceable event | Logging, DO-178C, easier debug |
| **R8** — YAML is the SDD | Every YAML transition = one LLR = one test | Bidirectional traceability |
| **R9** — Each FSM owns its context | No other thread ever touches an FSM's context | Parallelism without mutexes |
| **R10** — Only transport changes, not the FSM | OSAL hides transport behind single interface | Portability: thread → AMP → network |

## Choosing the Architecture

| Constraint | Architecture |
|-----------|-------------|
| Single deadline, simple system | Single-thread, one queue |
| Multiple deadlines of different criticality | Single-thread, dual-priority queue |
| Hard RT < 10µs AND soft RT tasks | Two threads with exclusive context partitioning |
| Hard RT < 1µs | Bare metal ISR, FSM lives in interrupt vectors |
| Certifiable (DO-178C DAL-A) | QP/C or QP/C++, MISRA C, WCET toolchain |

---

*[← 20](20-cpp-smart-pointers.md) | [Next: Conclusion →](22-conclusion.md)*
