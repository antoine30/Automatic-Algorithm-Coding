# 13 — The IF is a Hidden Transition

[← 12](12-synthetic-events.md) | [Next: Documents →](14-document-hierarchy.md)

---

## The Core Assertion

Every `if` in the body of an FSM implicitly asks one of these questions:

| Question | What it should be |
|----------|-------------------|
| "Which state am I going to?" | A transition in the table |
| "Which event should I generate?" | A synthetic event in the queue |
| "Is this condition true?" | A guard on the transition |

An `if` making a behavioral decision in the FSM body is a **transition in disguise**.

## The Four Maturity Levels

| Level | IFs in FSM | Architecture |
|-------|-----------|--------------|
| 1 | N (nested) | All if/else — logic hidden |
| 2 | 3 | FSM with IFs in switch/case |
| 3 | 1 | Externalized guards, transition table |
| 4 | 0 | Flat switch/case — synthetic events |

## Level 2 → Level 4 Transformation

```c
// ✗ Level 2 — IFs nested in switch
case STATE_RUN:
    if (ev.type == EVT_ADC_READY) {
        if (ctx->voltage_mv > ctx->vmax) {       // ← decision IF
            if (ctx->temp_c > ctx->tmax) {        // ← nested IF
                enter_fault(ctx, FAULT_BOTH);
            } else {
                enter_fault(ctx, FAULT_VOLTAGE);
            }
        }
    }
    break;

// ✓ Level 4 — flat switch, zero decision IFs
// The ADC driver qualifies the event BEFORE posting
void adc_driver_process(uint32_t v_mv, uint8_t t_c) {
    EvtType_t type;
    if      (v_mv > VMAX && t_c > TMAX) type = EVT_ADC_FAULT_BOTH;
    else if (v_mv > VMAX)                type = EVT_ADC_OVERVOLTAGE;
    else if (t_c  > TMAX)                type = EVT_ADC_OVERTEMP;
    else                                 type = EVT_ADC_NOMINAL;
    post_event(type, v_mv, t_c);  // already qualified
}

// FSM sees only exclusive cases — zero IFs
case STATE_RUN:
    switch (ev.type) {
    case EVT_ADC_FAULT_BOTH:  enter_fault(ctx, FAULT_BOTH);    break;
    case EVT_ADC_OVERVOLTAGE: enter_fault(ctx, FAULT_VOLTAGE); break;
    case EVT_ADC_OVERTEMP:    enter_fault(ctx, FAULT_TEMP);    break;
    case EVT_ADC_NOMINAL:     pll_update(ctx, &ev);            break;
    case EVT_CMD_STOP:        set_state(ctx, STATE_COOLDOWN);  break;
    default:                                                    break;
    }
    break;
```

## Legitimate IFs That Remain

```c
// In the sensor/driver — legitimate: event qualification
void sensor_process(raw_t raw) {
    if (raw > THRESHOLD) post(EVT_ALARM, raw);
    else                 post(EVT_NOMINAL, raw);
}

// In a guard — legitimate: it is its definition
bool guard_overvolt(const Ctx_t *c) {
    return c->voltage_mv > c->vmax_threshold;
}

// In an action — legitimate if no state change
void action_pll(Ctx_t *c) {
    c->integ = CLAMP(c->integ + c->ki * err, -500.f, 500.f);
    // CLAMP contains an IF — but it's arithmetic, not behavior
}

// In the FSM body — NEVER
case STATE_RUN:
    if (ev.type == EVT_ADC) {
        if (ctx->v > ctx->vmax) { /* ← this should be a transition */ }
    }
```

> **Rule:** the `switch/case` is a list of facts: "when this event arrives in this state, do this." An `if` in the switch means a state or event is missing.

---

*[← 12](12-synthetic-events.md) | [Next: Documents →](14-document-hierarchy.md)*
