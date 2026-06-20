# 08 — Publish/Subscribe Event Bus

[← 07](07-request-response.md) | [Next: Rendezvous →](09-n-fsm-rendezvous.md)

---

## Why Pub/Sub

When multiple FSMs must react to the same event (e.g. EVT_FAULT must notify piezo FSM, power FSM, AND log manager), don't use cross-pointers between queues. Use a central bus: each FSM subscribes to the event types it cares about.

```
                  ┌──────────────┐
                  │  EVENT BUS   │
                  └──────┬───────┘
         ┌───────────────┼──────────────┐
         ↓               ↓              ↓
  ┌─────────────┐  ┌───────────┐  ┌───────────┐
  │  FSM PIEZO  │  │ FSM POWER │  │  FSM LOG  │
  │  queue_a    │  │ queue_b   │  │  queue_c  │
  └─────────────┘  └───────────┘  └───────────┘
```

## Implementation

```c
typedef struct {
    OsalQueue_t *subs[EVT_TYPE_MAX][MAX_SUBS];
    uint8_t      n_subs[EVT_TYPE_MAX];
} EventBus_t;

// Subscribe at startup
void bus_subscribe(EventBus_t *bus, EvtType_t type, OsalQueue_t *q) {
    uint8_t n = bus->n_subs[type];
    bus->subs[type][n] = q;
    bus->n_subs[type]++;
}

// Publish from anywhere — no knowledge of subscribers
void bus_publish(EventBus_t *bus, const FsmEvent_t *ev) {
    for (int i = 0; i < bus->n_subs[ev->type]; i++)
        queue_send(bus->subs[ev->type][i], ev, NO_WAIT);
}

// Initialization
bus_subscribe(&g_bus, EVT_FAULT, &fsm_piezo_queue);
bus_subscribe(&g_bus, EVT_FAULT, &fsm_power_queue);
bus_subscribe(&g_bus, EVT_FAULT, &fsm_log_queue);   // 3 subscribers

// Publishing — FSM Power doesn't know who will receive this
FsmEvent_t ev = { .type = EVT_FAULT };
bus_publish(&g_bus, &ev);  // all 3 queues receive it
```

The publisher has **zero knowledge** of subscribers. Zero coupling. Adding a new subscriber doesn't modify the publisher.

---

*[← 07](07-request-response.md) | [Next: Rendezvous →](09-n-fsm-rendezvous.md)*
