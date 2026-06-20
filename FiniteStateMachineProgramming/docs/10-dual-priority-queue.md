# 10 — Dual-Priority Queue

[← 09](09-n-fsm-rendezvous.md) | [Next: Variable Sharing →](11-variable-sharing.md)

---

## The Problem

With a single queue, an EVT_FAULT posted by an ISR can sit behind 50 EVT_PLL_TICK events. It waits its turn instead of being processed immediately.

```
Single queue: [PLL_TICK][PLL_TICK][PLL_TICK][PLL_TICK][FAULT]
                                                           ↑
                   4 events processed before FAULT: 4×10µs = 40µs extra delay
```

## The Solution: Two Queues, Drained in Priority Order

```c
// Two queues by criticality
static OsalQueue_t g_urgent_q;   // small — EVT_FAULT, EVT_RESET
static OsalQueue_t g_normal_q;   // large — timers, commands

// FSM thread — urgent always drained first
void fsm_thread_entry(void *arg) {
    FsmEvent_t ev;
    while (true) {
        // 1. Drain entire urgent queue (non-blocking)
        while (queue_recv(&g_urgent_q, &ev, NO_WAIT) == OK)
            fsm_process(ctx, &ev);

        // 2. One normal event (blocking with timeout)
        if (queue_recv(&g_normal_q, &ev, 10) == OK)
            fsm_process(ctx, &ev);

        watchdog_kick();
    }
}

// Routing at emission
void fpga_fault_isr(void) {
    FsmEvent_t ev = { .type = EVT_FAULT };
    queue_send(&g_urgent_q, &ev, NO_WAIT);  // urgent queue
}

void pll_timer_cb(struct k_timer *t) {
    FsmEvent_t ev = { .type = EVT_PLL_TICK };
    queue_send(&g_normal_q, &ev, NO_WAIT);  // normal queue
}
```

EVT_FAULT now waits at most the WCET of the current normal transition — typically < 50µs.

---

*[← 09](09-n-fsm-rendezvous.md) | [Next: Variable Sharing →](11-variable-sharing.md)*
