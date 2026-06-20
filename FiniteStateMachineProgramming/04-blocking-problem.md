# 04 — The Blocking Problem

[← 03](03-modeling-tools.md) | [Next: Events →](05-everything-is-an-event.md)

---

## The Naive Approach

When two threads must coordinate, the naive solution is to make one wait while the other works.

```c
// Thread A (piezo FSM) waits for Thread B (power FSM)
case STATE_INIT:
    power_supply_enable();
    k_sem_take(&power_ready_sem, K_FOREVER);  // ← BLOCKS
    fsm_set_state(STATE_SCAN);
```

This creates four critical problems:

| Problem | Manifestation | Consequence |
|---------|--------------|-------------|
| **Non-deterministic latency** | Thread A cannot serve other events while blocked | EVT_FAULT queued behind block goes unserved |
| **Watchdog risk** | Thread A stops kicking the watchdog during block | System reset if block lasts > watchdog period |
| **Priority inversion** | High-priority thread blocks on semaphore held by low-priority thread | System inverted |
| **Deadlock** | A waits for B, B waits for A | Both frozen forever, undetectable |

## The Solution: Everything Is an Event

Instead of blocking, FSM A posts a request, changes to a WAIT state, and continues processing other events. FSM B responds when ready by posting an event into A's queue.

```c
// Thread A — NON-BLOCKING
case STATE_INIT:
    post(fsm_b_queue, EVT_POWER_REQ);   // request sent
    timer_start(&ctx->tmr_guard, 200);  // guard: 200ms max
    set_state(STATE_WAIT_POWER);        // return immediately
    break;

case STATE_WAIT_POWER:
    if (ev.type == EVT_POWER_READY) {
        timer_stop(&ctx->tmr_guard);
        set_state(STATE_SCAN);
    } else if (ev.type == EVT_TIMEOUT) {
        enter_fault(ctx, FAULT_POWER_TIMEOUT);
    }
    // Other events (CMD_STOP etc.) still processed normally
    break;
```

The EVT_POWER_READY arrives from FSM B when it is done — in its own time, without blocking A.

---

*[← 03](03-modeling-tools.md) | [Next: Events →](05-everything-is-an-event.md)*
