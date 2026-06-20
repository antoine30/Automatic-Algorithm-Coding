# 01 — What is an FSM?

[← README](../README.md) | [Next: EFSM →](02-efsm-complete-description.md)

---

## Definition

A **Finite State Machine (FSM)** is a mathematical model that describes a system through a finite set of **states**, with exactly one state active at any time, and **rules** (transitions) that determine how the system moves between states in response to **events**.

Formally, an FSM is a quintuple **(S, E, T, s₀, F)**:

| Symbol | Name | Description | Piezo example |
|--------|------|-------------|---------------|
| **S** | States | Finite set of discrete situations | OFF, INIT, SCAN, LOCK, RUN, PAUSE, COOLDOWN, FAULT |
| **E** | Events | Stimuli that can cause transitions | CMD_START, FPGA_READY, ADC_OVERVOLTAGE, TIMEOUT |
| **T** | Transitions | Rules: T(state, event) → state' + action | T(OFF, CMD_START) = INIT |
| **s₀** | Initial state | Starting state | OFF |
| **F** | Final states | Optional — rarely used in embedded | Not used (FSM runs forever) |

---

## The Concrete Intuition

The simplest FSM is a light switch: two states (ON, OFF), one event (PRESS), two transitions.

```
OFF --[PRESS]--> ON
ON  --[PRESS]--> OFF
```

That's it. At any moment the switch is in exactly one state. An event arrives, a rule applies, we move.

```c
// The simplest possible FSM
typedef enum { OFF, ON } State_t;

State_t fsm_switch(State_t state, Event_t ev) {
    switch (state) {
    case OFF: if (ev == PRESS) return ON;   break;
    case ON:  if (ev == PRESS) return OFF;  break;
    }
    return state;  // unhandled event: stay
}
```

The function is **deterministic**: for a given state and event, there is exactly one outcome. No ambiguity, no undefined behavior.

---

## FSM vs Ordinary Code

The fundamental difference is how state is managed.

### Ordinary code — implicit state

```c
bool initialized = false;
bool running     = false;
bool freq_locked = false;
bool fault       = false;

void process(void) {
    if (initialized) {
        if (running) {
            if (freq_locked) { /* do something */ }
        }
    }
}
// 2⁴ = 16 possible combinations
// Some are incoherent: running=true AND initialized=false
// Nobody knows which "state" the system is really in
```

### FSM — explicit state

```c
typedef enum {
    STATE_OFF,
    STATE_INIT,
    STATE_LOCK,
    STATE_RUN,
    STATE_FAULT,
} State_t;

State_t state = STATE_OFF;  // always coherent, always visible
```

With an explicit state variable:
- The system's situation is **always unambiguous**
- **Impossible** to be in STATE_RUN without having been through STATE_INIT
- All transitions are **auditable** — you can list them in a table
- The state can be **logged, displayed, tested**

---

## Moore vs Mealy

Two fundamental FSM models:

| Model | Output depends on | When action occurs | Typical use |
|-------|------------------|--------------------|-------------|
| **Moore** | State only | On state entry (or permanently during state) | STATE_RUN → FPGA powered continuously |
| **Mealy** | State AND event | On the transition | RUN + CMD_STOP → triggers ramp-down |

In practice, embedded systems mix both: the **state** determines permanent behavior (Moore), **transitions** trigger one-shot actions (Mealy).

```c
// Moore: action tied to the state
void on_entry_run(Ctx_t *ctx) {
    fpga_write(CTRL, CTRL_ENABLE);   // entry action
}
void on_exit_run(Ctx_t *ctx) {
    fpga_write(CTRL, 0);             // exit action
}

// Mealy: action tied to the transition
case STATE_RUN:
    if (ev.type == CMD_STOP) {
        ramp_start(&ctx->ramp, 0, 100);  // Mealy action on event
        set_state(ctx, STATE_COOLDOWN);
    }
    break;
```

---

## Why FSMs Are Suited to Embedded Real-Time

- **Physical systems are naturally discrete.** A motor is running or stopped. A protection is armed or not. An FSM faithfully models this reality.
- **Exhaustive and verifiable behavior.** All (state, event) pairs can be listed in a table and checked — including unexpected cases.
- **Perfect traceability.** At any instant you know exactly where you are.
- **Certifiability.** You can prove no path from STATE_OFF to STATE_RUN bypasses STATE_INIT. ISO 26262, DO-178C, and IEC 61508 explicitly recommend FSMs for critical systems.
- **Determinism.** For a given state and event, there is exactly one rule — no ambiguity.

---

*[← README](../README.md) | [Next: EFSM →](02-efsm-complete-description.md)*
