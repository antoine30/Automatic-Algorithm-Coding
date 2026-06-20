# 05 — Everything is an Event

[← 04](04-blocking-problem.md) | [Next: Architecture →](06-single-thread-architecture.md)

---

## The Fundamental Principle

**The FSM never does anything that takes time.** It launches a non-blocking action, changes state, and returns immediately. Time passes in timers and ISRs.

## Timers Post Events

```c
// BAD — timer callback accesses shared state
void pll_timer_cb(struct k_timer *t) {
    float err = compute_phase(ctx);   // shared access
    fpga_write(NCO_FREQ, f + err);    // FPGA access from timer ← race
}

// CORRECT — timer posts event and exits
void pll_timer_cb(struct k_timer *t) {
    FsmEvent_t ev = { .type = EVT_PLL_TICK };
    queue_send(&g_normal_queue, &ev, NO_WAIT);
}
```

## ISRs Post Events

```c
// BAD — long ISR
void fpga_fault_isr(void) {
    uint32_t v = fpga_read(ADC_VOLTAGE);    // slow
    if (v > VMAX) {
        fpga_write(CTRL, RESET);
        log_fault(FAULT_OV);                // even slower
    }
}

// CORRECT — minimal ISR
void fpga_fault_isr(void) {
    uint32_t st = FPGA_REG(IRQ_STATUS);
    FPGA_REG(IRQ_STATUS) = st;              // clear IRQ
    FsmEvent_t ev = { .type = EVT_FAULT, .data.status = st };
    queue_send_from_isr(&g_urgent_queue, &ev);
}
// ISR WCET: ~10 cycles = 100ns
```

## Decompose Long Processes into Sub-States

```c
// BAD — one monolithic state that blocks for 60ms
case STATE_INIT_FPGA:
    fpga_write(CTRL, RESET);
    k_msleep(10);             // BLOCKS 10ms
    fpga_write(CTRL, 0);
    k_msleep(50);             // BLOCKS 50ms
    set_state(STATE_SCAN);
    break;

// CORRECT — sub-states, each returns immediately
case STATE_INIT_ASSERT_RESET:
    fpga_write(CTRL, CTRL_RESET);
    timer_start(&ctx->tmr, 10);
    set_state(STATE_INIT_DEASSERT);
    return;  // immediate return

case STATE_INIT_DEASSERT:
    if (ev.type != EVT_TIMER) return;
    fpga_write(CTRL, 0);
    timer_start(&ctx->tmr, 50);
    set_state(STATE_INIT_WAIT_READY);
    return;

case STATE_INIT_WAIT_READY:
    if (ev.type == EVT_FPGA_READY) {
        set_state(STATE_SCAN);
    } else if (ev.type == EVT_TIMER) {
        enter_fault(ctx, FAULT_FPGA_INIT);
    }
    return;
```

The 60ms elapse in hardware — the thread runs freely throughout.

---

*[← 04](04-blocking-problem.md) | [Next: Architecture →](06-single-thread-architecture.md)*
