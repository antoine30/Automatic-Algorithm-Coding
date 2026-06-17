# LLR_TSK_001 — TaskBase Class

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_ITF_001, LLR_ITF_004

## Files to Generate
- src/tasks/TaskBase.h
- src/tasks/TaskBase.cpp

## Description
Abstract base class for all FreeRTOS tasks.
Manages the FreeRTOS task lifecycle and an **event queue**. The task loop blocks
on the queue, receives an `IEvent`, and calls `event.execute(*this)` which routes
to the matching virtual handler (onInit/onStart/onStop). There is **no switch/case**
on the event type — dispatch is fully polymorphic.

## Class Definition
```cpp
class TaskBase : public ITask {
public:
    TaskBase(const char* name, uint32_t stackSize, UBaseType_t priority,
             uint32_t queueLength = 8);
    virtual ~TaskBase();

    void start(); ///< Create the event queue and start the FreeRTOS task
    void stop();  ///< Delete the FreeRTOS task and the queue

    /// Post an event to the task (from a task context). Returns false if full.
    bool postEvent(const IEvent& event, TickType_t timeout = 0);

    /// Post an event from an ISR context.
    bool postEventFromISR(const IEvent& event, BaseType_t* higherPriorityTaskWoken);

protected:
    /// Receive one event (blocking up to timeout) and dispatch it via
    /// event->execute(*this). Returns true if an event was processed.
    /// Extracted from run() so it can be unit-tested without the scheduler.
    bool processNextEvent(TickType_t timeout);

    const char*    m_name;
    uint32_t       m_stackSize;
    UBaseType_t    m_priority;
    uint32_t       m_queueLength;
    TaskHandle_t   m_handle;
    QueueHandle_t  m_eventQueue; ///< Carries const IEvent* (no dynamic alloc)

private:
    static void taskEntry(void* param); ///< FreeRTOS task entry point
    void run();                         ///< Event receive + dispatch loop
};
```

## Task Lifecycle
```
start()
  ├─ xQueueCreate(queueLength, sizeof(const IEvent*))
  └─ xTaskCreate(taskEntry)
       └─ taskEntry() → run()
            └─ for(;;)
                 ├─ xQueueReceive(&event, portMAX_DELAY)
                 └─ event->execute(*this)   ← virtual dispatch, NO switch
                       ├─ OK    → continue
                       └─ ERROR → log task name + status, continue
```

## Dispatch Rule (MANDATORY)
```cpp
// CORRECT — polymorphic, no switch:
const IEvent* ev = nullptr;
if (xQueueReceive(m_eventQueue, &ev, portMAX_DELAY) == pdTRUE && ev != nullptr) {
    TaskStatus st = ev->execute(*this); // calls onInit/onStart/onStop
    if (st != TaskStatus::OK) { /* log m_name + st */ }
}

// FORBIDDEN — never resolve the type like this:
// switch (ev->id()) { case EventId::INIT: onInit(); ... }
```

## Constraints
- taskEntry must be static (FreeRTOS requirement)
- Use reinterpret_cast<TaskBase*>(param) inside taskEntry
- The event queue stores pointers to shared event singletons — no malloc/new
- Log task name and error code on any handler returning != OK
- **No switch/case on event id** — dispatch only through IEvent::execute()

## Instructions for Claude
1. Generate TaskBase.h with the class definition above
2. Generate TaskBase.cpp with taskEntry + run() event loop
3. run() blocks on the queue and calls event->execute(*this) — no switch
4. start() creates the queue then the task; stop() deletes both
5. Add Doxygen comment on each public method
6. Generate tests/test_task_base.cpp (post InitEvent/StartEvent/StopEvent,
   verify the matching virtual handler is invoked, without any RTOS scheduler)
