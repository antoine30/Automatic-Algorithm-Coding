# 12 — Intra-FSM Synchronization and Synthetic Events

[← 11](11-variable-sharing.md) | [Next: IF →](13-if-is-a-transition.md)

---

## The Core Problem

When a synchronization waits for N events, the FSM code executes N times — once per contributing event received. The transition must fire on the **N-th pass** — the last event that completes the condition. The **order of arrival is non-deterministic**.

## The Bug: Order-Dependent Verification

```c
// Naive — order-dependent, can block forever
case STATE_WAIT_SYNC:
    if (ev.type == EVT_FPGA_READY) {
        ctx->flags |= FLAG_FPGA;
    }
    // Verification only on FPGA_READY
    // If order is TEMP→VOLTAGE→FPGA: OK
    // If order is FPGA→TEMP→VOLTAGE: FPGA arrives, check → no
    //   TEMP arrives → no verification!
    //   VOLTAGE arrives → no verification!
    //   → FSM stays in WAIT_SYNC forever
    if (ctx->flags == ALL) { set_state(STATE_RUN); }
    break;
```

## The Fix: Verify After Every Contributing Event

```c
case STATE_WAIT_SYNC:
    // Sensor: update context
    switch (ev.type) {
    case EVT_FPGA_READY:  ctx->sync_flags |= FLAG_FPGA; break;
    case EVT_TEMP_STABLE: ctx->sync_flags |= FLAG_TEMP; break;
    case EVT_VOLTAGE_OK:  ctx->sync_flags |= FLAG_VOLT; break;
    default: break;
    }
    // Verified AFTER EVERY event — order irrelevant
    if ((ctx->sync_flags & ALL) == ALL) {
        post(EVT_SYNC_COMPLETE);           // synthetic event
        set_state(STATE_SYNC_PENDING);
    }
    break;
```

## Why a Synthetic Event?

A **synthetic event** (EVT_SYNC_COMPLETE) rather than a direct `set_state(STATE_RUN)` provides:

1. **Traceability** — the transition cause is logged with timestamp and flags
2. **Queue ordering** — EVT_SYNC_COMPLETE is posted after any events already in queue; EVT_FAULT is handled first if present
3. **Clean entry actions** — `set_state(STATE_RUN)` called in a clean context, not mid-processing of EVT_VOLTAGE_OK

## The Three-Layer Pattern

```c
// Layer 1: SENSOR — updates context without deciding
static void sync_update(SyncCtx_t *s, const FsmEvent_t *ev) { ... }

// Layer 2: EVALUATOR — pure function, no side effects
static SyncResult_t sync_evaluate(const SyncCtx_t *s) {
    SyncResult_t r = { .complete = false };
    if (!(s->flags & FLAG_FPGA)) r.pending |= SYNC_WAIT_FPGA;
    if (!(s->flags & FLAG_TEMP)) r.pending |= SYNC_WAIT_TEMP;
    r.complete = (r.pending == 0);
    return r;
}

// Layer 3: FSM — orchestrates the two layers
case STATE_WAIT_SYNC:
    sync_update(&ctx->sync, &ev);
    SyncResult_t result = sync_evaluate(&ctx->sync);
    if (result.complete) {
        FsmEvent_t synth = { .type = EVT_SYNC_COMPLETE,
                             .data.elapsed_ms = elapsed };
        queue_send(&g_fsm_queue, &synth, NO_WAIT);
        set_state(STATE_SYNC_PENDING);
    }
    break;
```

Each layer is independently unit-testable.

---

*[← 11](11-variable-sharing.md) | [Next: IF →](13-if-is-a-transition.md)*
