# 22 — Conclusion: Extensibility, Parallelism, Distribution

[← 21](21-design-rules.md) | [↑ README](../README.md)

---

## The Single Underlying Principle

All the architectural properties documented in this repository — no blocking, no mutex, synthetic events, YAML traceability, WCET discipline, smart pointer discipline — emerge from a **single founding principle**:

> **Decoupling by message.**

The sender does not know the receiver. The receiver does not know the sender. They share nothing except the message format. This one constraint mechanically generates three architectural virtues.

---

## Virtue 1 — Extensibility

Adding a behavior means adding a `case` in a switch or an entry in the YAML table. Existing code is unchanged. Existing tests still pass. Regression is impossible by construction.

```c
// Adding EVT_FREQ_OUT_BAND does not touch existing transitions
case STATE_RUN:
    switch (ev.type) {
    case EVT_ADC_OVERVOLTAGE: enter_fault(ctx, FAULT_VOLTAGE); break; // unchanged
    case EVT_CMD_STOP:        set_state(ctx, STATE_COOLDOWN);  break; // unchanged
    case EVT_FREQ_OUT_BAND:   set_state(ctx, STATE_RESCAN);    break; // new — safe
    }
```

In DO-178C DAL-A terms: an extension does not invalidate existing certification tests.

---

## Virtue 2 — Parallelism

Each FSM owns its context exclusively. No other thread touches it. The only shared structure is the queue — designed to be thread-safe. **Zero mutex on application state** — not as an optimization but as an architectural property.

```
Core 0: FSM Piezo → ctx_piezo (exclusive) → queue_piezo
Core 1: FSM Power → ctx_power (exclusive) → queue_power
         ↕ (only contact: IPC/shared-memory queue)

Core 0 NEVER touches ctx_power.
Core 1 NEVER touches ctx_piezo.
```

This extends naturally to AMP dual-core (Cortex-R5 dual): each core runs its own FSM independently. The inter-core queue is a shared-memory FIFO or IPC mailbox — same OSAL interface, different transport.

---

## Virtue 3 — Distribution

The same FSM code runs in four radically different deployment configurations without modifying a single line of business logic. Only the OSAL changes.

```c
// The FSM always calls the same interface
osal_queue_send(&g_target_queue, &ev, NO_WAIT);

// Mode 1: Same thread (Zephyr k_msgq)   → < 1µs
// Mode 2: Dual-core AMP (shared memory)  → 10-100µs
// Mode 3: R5+A53 heterogeneous (IPC)     → 50-500µs
// Mode 4: Network nodes (CAN / Ethernet) → < 10ms
```

---

## The Actor Model — From Embedded to Distributed

What we have built is an implementation of the **Actor Model** (Hewitt, 1973), applied at the scale of a real-time microcontroller. The same abstraction applies at all scales:

| Scale | Actor | Message | Transport |
|-------|-------|---------|-----------|
| Function | Pure function | Argument / return value | Call stack |
| Thread | FSM in a thread | FsmEvent_t in k_msgq | Zephyr queue |
| Core | FSM on each core | FsmEvent_t in shared mem | AMP FIFO |
| Processor | FSM on R5 and A53 | FsmEvent_t via IPC | IPCC hardware |
| Network node | Independent ECU | CAN FD frame | Physical bus |
| Cloud service | Microservice | JSON / Protobuf | Kafka / RabbitMQ |

An event-driven embedded FSM on Cortex-R5/Zephyr is architecturally identical to a Kubernetes microservice. The difference is not the model — it is the latency and real-time constraints. Understanding one helps understand the other.

---

## In One Sentence

The event-driven FSM architecture is not one embedded technique among others. It is the application, at microcontroller scale, of a universal architectural principle: the most reliable and maintainable systems are those where components share nothing and communicate only by messages. From the Cortex-R5 ISR to the Kubernetes microservice, the model is the same. Only the transport changes.

---

*[← 21](21-design-rules.md) | [↑ README](../README.md)*

---

*Antoine DAMON · Antoine.Damon@laposte.net*
