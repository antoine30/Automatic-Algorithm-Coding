# 07 — Request/Response Asynchronous Synchronization

[← 06](06-single-thread-architecture.md) | [Next: Pub/Sub →](08-publish-subscribe.md)

---

## The Pattern

When FSM A needs a result produced by FSM B, it does not wait. It sends a request, changes to a WAIT state, and continues processing other events. When B is done, it posts the response into A's queue.

```
FSM A                           FSM B
─────                           ─────
post(EVT_POWER_REQ) ──────────→ receives, processes
changes to WAIT_POWER
... processes other events ...
receives EVT_POWER_READY ←───── posts when done
continues
```

## Implementation

```c
// FSM A — requester side
case STATE_INIT:
    FsmEvent_t req = { .type = EVT_POWER_REQ,
                       .requester_q = &fsm_a_queue };
    queue_send(&fsm_b_queue, &req, NO_WAIT);
    timer_start(&ctx->tmr_guard, 200);    // mandatory guard
    set_state(STATE_WAIT_POWER);
    return;  // IMMEDIATE RETURN

case STATE_WAIT_POWER:
    switch (ev.type) {
    case EVT_POWER_READY:
        timer_stop(&ctx->tmr_guard);
        set_state(STATE_SCAN);
        break;
    case EVT_TIMEOUT:
        enter_fault(ctx, FAULT_POWER_TIMEOUT);
        break;
    case EVT_CMD_STOP:          // still processed during wait
        timer_stop(&ctx->tmr_guard);
        set_state(STATE_COOLDOWN);
        break;
    default: break;
    }
    return;

// FSM B — responder side
case STATE_POWER_IDLE:
    if (ev.type == EVT_POWER_REQ) {
        ctx->requester_q = ev.requester_q;
        hw_power_enable();
        timer_start(&ctx->tmr_ramp, 50);
        set_state(STATE_POWER_RAMPING);
    }
    return;

case STATE_POWER_RAMPING:
    if (ev.type == EVT_TIMER) {
        FsmEvent_t rsp = { .type = EVT_POWER_READY };
        queue_send(ctx->requester_q, &rsp, NO_WAIT);
        set_state(STATE_POWER_ON);
    }
    return;
```

## N-FSM Synchronization by Counter

When a supervisor must wait for N independent subsystems:

```c
case STATE_WAIT_ALL_READY:
    if (ev.type == EVT_SUBSYS_READY) {
        ctx->ready_count++;
        if (ctx->ready_count >= N_SUBSYSTEMS) {
            set_state(STATE_RUN);
        }
        // Otherwise: stay, wait for more
    } else if (ev.type == EVT_TIMEOUT) {
        // Which subsystem didn't respond?
        enter_fault(ctx, FAULT_INIT_INCOMPLETE);
    }
    return;
```

---

*[← 06](06-single-thread-architecture.md) | [Next: Pub/Sub →](08-publish-subscribe.md)*
