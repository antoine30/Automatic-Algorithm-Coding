# 06 — Single-Thread Event-Driven Architecture

[← 05](05-everything-is-an-event.md) | [Next: Request/Response →](07-request-response.md)

---

## The Ideal: One Thread, Zero Mutexes

All FSMs run in **one single thread**. There is no concurrent access to application state. No mutex is needed by construction.

```c
void main_fsm_thread(void *arg) {
    FsmEvent_t ev;
    while (true) {
        // 1. Drain urgent queue first (non-blocking)
        while (queue_recv(&g_urgent, &ev, NO_WAIT) == OK) {
            fsm_piezo_process(&ctx_piezo, &ev);
            fsm_power_process(&ctx_power, &ev);
            fsm_comm_process (&ctx_comm,  &ev);
        }
        // 2. One normal event, then back to check urgent
        if (queue_recv(&g_normal, &ev, 10) == OK) {
            fsm_piezo_process(&ctx_piezo, &ev);
            fsm_power_process(&ctx_power, &ev);
            fsm_comm_process (&ctx_comm,  &ev);
        }
        watchdog_kick();
    }
}
```

What was in separate threads becomes **cases in a switch**. Sequential, deterministic, mutex-free.

## Event Sources

```
Timer 1ms  ──→ EVT_PLL_TICK ─────┐
Timer 100ms──→ EVT_MONITOR ──────┤
IRQ FPGA   ──→ EVT_FAULT ────────┤──→ QUEUE ──→ SINGLE THREAD FSM
UART/CAN   ──→ EVT_CMD_* ────────┤
Auto-event ──→ EVT_IIR_STEP ─────┘

THREAD FSM:
  ┌─────────────────────────────────────────┐
  │  while(true) {                          │
  │    drain urgent queue;                  │
  │    process one normal event;            │
  │    watchdog_kick();                     │
  │  }                                      │
  └─────────────────────────────────────────┘
  ↓ only place that touches hardware
  ↓ zero mutexes, zero race conditions
```

## What We Gain

| Multi-thread | Single-thread event-driven |
|-------------|---------------------------|
| Mutex on every shared resource | Zero mutexes |
| Priority inversion possible | Impossible by construction |
| Deadlock possible | Impossible by construction |
| State scattered across N threads | State centralized in ctx |
| Watchdog hard to guarantee | Single kick point per iteration |

---

*[← 05](05-everything-is-an-event.md) | [Next: Request/Response →](07-request-response.md)*
