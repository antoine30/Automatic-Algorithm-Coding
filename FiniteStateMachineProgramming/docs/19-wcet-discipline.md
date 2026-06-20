# 19 — Real-Time FSM Programming: WCET Discipline

[← 18](18-do178c-dal-a.md) | [Next: C++ →](20-cpp-smart-pointers.md)

---

## Real-Time ≠ Fast

**Real-time means deterministic.** A system can be slow and real-time. A system can be fast and not real-time.

Real-time = you can **prove** that an action will occur within a bounded delay, in ALL cases, including the worst case.

```
NOT real-time — even if fast on average:
  Web system: p50 = 2ms, p99 = 200ms, p999 = 500ms
  Cannot prove every response arrives in < 10ms

REAL-TIME — deterministic:
  RT FSM: min = 10µs, max = 12µs, WCET = 12µs
  CAN PROVE every action occurs in < 1ms
```

## The End-to-End Latency Model

```
Latency = IRQ latency + ISR WCET + scheduler latency + FSM transition WCET

         ├── Fixed by hardware ──┤  ├────── Controlled by you ──────────┤
         ~260ns + ~100ns           + ~2µs   +     <300ns
         = ~3µs total  <<  1ms deadline  ✓
```

## The 8 Rules

### R1 — No blocking calls
```c
// FORBIDDEN
case STATE_INIT:
    k_msleep(50);          // blocks 50ms
    k_sem_take(&s, K_FOREVER);  // blocks unknown duration
    break;

// CORRECT
case STATE_INIT:
    timer_start(&ctx->tmr, 50);
    set_state(STATE_WAIT);
    break;
```

### R2 — No dynamic allocation
```c
// FORBIDDEN
float *buf = malloc(1024 * sizeof(float));  // unbounded WCET

// CORRECT
static float g_scan_buf[1024];  // allocated once at startup
```

### R3 — Bounded loops
```c
// FORBIDDEN
for (int i = 0; i < ev.data.n; i++) { ... }  // n unknown

// CORRECT
#define CHUNK 8
uint16_t n = MIN(ev.data.n, CHUNK);
for (int i = 0; i < n; i++) { ... }
if (ctx->offset < total) post(EVT_CONTINUE);
```

### R4 — No recursion
MISRA C 2012 Rule 17.2 — functions shall not be called recursively.

### R5 — Documented WCET for every call
```c
// WCET table — measured on target with GPIO + oscilloscope
// fpga_write()      :  2 cycles  =  20ns
// queue_send()      : 10 cycles  = 100ns
// pll_update()      : 50 cycles  = 500ns
// enter_fault()     : 20 cycles  = 200ns

// FORBIDDEN without documented WCET:
printf("freq=%.2f
", ctx->freq);   // unknown WCET (UART, formatting)
log_to_flash(ctx);                   // unknown WCET (flash I/O)
```

### R6 — Delegate long actions
```c
case STATE_RUN:
    if (ev.type == EVT_FAULT) {
        fpga_write(CTRL, RESET);        // 2 cycles — critical, inline
        set_state(STATE_FAULT);
        // Delegate long actions — non-blocking
        queue_send(&g_diag_queue, &req, NO_WAIT);  // thread prio 8
    }
    break;
```

### R7 — Minimal ISR
```c
void fpga_fault_isr(void) {
    FPGA_REG(IRQ_STATUS) = FPGA_REG(IRQ_STATUS);  // clear IRQ
    FsmEvent_t ev = { .type = EVT_FAULT };
    queue_send_from_isr(&g_urgent_queue, &ev);
    // NOTHING ELSE — exit in < 10 instructions
}
```

### R8 — No hidden paths
```c
// FORBIDDEN — behavior depends on hidden global
case STATE_RUN:
    if (g_calibration_mode) { calibrate(); }  // hidden path
    else                     { pll_update(); }

// CORRECT — state makes path explicit
case STATE_CALIBRATION:
    if (ev.type == EVT_ADC) calibrate(ctx, &ev); break;
case STATE_RUN:
    if (ev.type == EVT_ADC) pll_update(ctx, &ev); break;
```

## On-Target Verification

```c
#define WCET_PROBE_SET()  GPIO_SET(GPIOA, PIN_WCET)
#define WCET_PROBE_CLR()  GPIO_CLR(GPIOA, PIN_WCET)

void fsm_run_state(Ctx_t *ctx, const FsmEvent_t *ev) {
    WCET_PROBE_SET();
    // ... transitions ...
    WCET_PROBE_CLR();
    // Oscilloscope: measure longest pulse over 10⁶ iterations = WCET
}
// Accept if: WCET_measured < deadline - IRQ_latency - ISR_WCET - scheduler_latency
```

---

*[← 18](18-do178c-dal-a.md) | [Next: C++ →](20-cpp-smart-pointers.md)*
