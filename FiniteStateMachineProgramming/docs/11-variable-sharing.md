# 11 — Variable Sharing Without Mutexes

[← 10](10-dual-priority-queue.md) | [Next: Synthetic Events →](12-synthetic-events.md)

---

## The Problem

Even without semaphores, shared variables between threads cause race conditions. A `float` is not atomic. A struct never is.

```c
// Thread B writes a struct (3 writes)
ctx->freq   = 40000.0f;   // write 1
ctx->amp    = 0.85f;      // write 2
ctx->valid  = true;       // write 3  ← Thread A reads here between 2 and 3
                          //   sees freq+amp but valid=false
                          //   or worse: valid=true but amp half-written
```

## Solution 1 — Single Thread (the best solution)

If all FSMs run in the same thread, there is no concurrent access by construction.

## Solution 2 — Embed the Value in the Event

Instead of sharing a variable, Thread B embeds the value in the event. The reader never accesses Thread B's memory.

```c
// BAD: Thread A reads Thread B's variable
float freq = ctx_b->freq;   // concurrent access

// GOOD: Thread B sends the value in the event
FsmEvent_t ev = {
    .type       = EVT_PLL_RESULT,
    .pll_result = { .freq = 40012.5f, .amp = 0.85f }
};
queue_send(&fsm_a_queue, &ev, NO_WAIT);

// Thread A receives a complete, coherent copy
case EVT_PLL_RESULT:
    ctx->freq = event.pll_result.freq;   // coherent — it's a copy
    ctx->amp  = event.pll_result.amp;
    break;
```

## Solution 3 — Atomics for Scalars

```c
#include <stdatomic.h>
atomic_uint_fast32_t g_vmax_threshold;

// FSM: atomic write (non-blocking, memory order guaranteed)
atomic_store(&g_vmax_threshold, 120000);

// ISR: atomic read (non-blocking, coherent)
uint32_t vmax = atomic_load(&g_vmax_threshold);
```

Works for 32-bit scalars. **Not for structs.**

## Solution 4 — Double Buffer for Structs

```c
static SensorState_t  g_buf[2];
static atomic_int     g_write_idx = 0;

// Producer: writes to inactive buffer
void publish_state(float freq, uint32_t v) {
    int next = 1 - atomic_load(&g_write_idx);
    g_buf[next].freq_hz    = freq;    // complete write before swap
    g_buf[next].voltage_mv = v;
    atomic_store(&g_write_idx, next); // atomic swap
}

// Consumer: reads active buffer
void read_state(SensorState_t *out) {
    *out = g_buf[atomic_load(&g_write_idx)];  // coherent copy
}
```

The swap is atomic (one integer). The reader always sees a fully-written buffer.

---

*[← 10](10-dual-priority-queue.md) | [Next: Synthetic Events →](12-synthetic-events.md)*
