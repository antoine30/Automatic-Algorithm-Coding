# 09 — N-FSM Rendezvous by Counter

[← 08](08-publish-subscribe.md) | [Next: Priority Queue →](10-dual-priority-queue.md)

---

## The Problem

A supervisor FSM must wait for N independent subsystems to complete before proceeding. Classic approach (semaphore counting): blocking, non-deterministic.

## The Solution: Bitmask Counter

```c
// Supervisor: launch 3 subsystems in parallel
case STATE_MASTER_INIT:
    ctx->ready_flags = 0;
    timer_start(&ctx->tmr_global, 500);      // global guard
    bus_publish(&g_bus, &EVT_SUBSYS_START);  // launch all 3
    set_state(STATE_WAIT_ALL_READY);
    return;

// Wait for N confirmations — no blocking, no semaphore
case STATE_WAIT_ALL_READY:
    if (ev.type == EVT_SUBSYS_READY) {
        ctx->ready_flags |= ev.data.subsys_flag;

        if ((ctx->ready_flags & ALL_FLAGS) == ALL_FLAGS) {
            timer_stop(&ctx->tmr_global);
            set_state(STATE_RUN);            // all ready — start
        }
        // Otherwise: stay and wait for more
    } else if (ev.type == EVT_TIMEOUT) {
        // Diagnose: which subsystem didn't respond?
        uint8_t missing = ALL_FLAGS & ~ctx->ready_flags;
        enter_fault(ctx, fault_from_mask(missing));
    }
    return;
```

**Properties:**
- Order of arrival is **irrelevant** — verified after every event
- **Zero blocking** — the FSM processes other events between confirmations
- **Watchdog guaranteed** — no wait loop, normal iteration continues
- The `ready_flags` counter is private to the supervisor context — **zero mutex**

---

*[← 08](08-publish-subscribe.md) | [Next: Priority Queue →](10-dual-priority-queue.md)*
