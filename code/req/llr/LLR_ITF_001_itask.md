# LLR_ITF_001 — ITask Interface

## Level : LOW LEVEL
## Parent HLR : HLR_001

## Files to Generate
- src/interfaces/ITask.h

## Description
Pure abstract interface that all FreeRTOS tasks must implement.
A task is **event-driven** : it receives `IEvent` objects (see LLR_ITF_004) on a
queue, and each event executes the associated code by calling one of the virtual
handlers below. The event type is therefore never inspected with a switch/case —
the polymorphic `IEvent::execute()` selects the handler.

## Interface Definition
```cpp
class ITask {
public:
    virtual ~ITask() = default;

    // --- Event handlers (called via IEvent::execute(), double-dispatch) ---
    virtual TaskStatus onInit()  = 0;   ///< Executed on the INIT event
    virtual TaskStatus onStart() = 0;   ///< Executed on the START event (run process)
    virtual TaskStatus onStop()  = 0;   ///< Executed on the STOP event

    virtual const char* getName() const = 0; ///< Returns task name for logging
};
```

## TaskStatus Enum
```cpp
enum class TaskStatus : uint8_t {
    OK              = 0,
    ERROR           = 1,
    TIMEOUT         = 2,
    NOT_INITIALIZED = 3,
    BUSY            = 4
};
```

## Event-Driven Model
```
event queue ──► TaskBase loop ──► event.execute(task)
                                        │  (virtual, no switch)
                                        ├─ InitEvent  → task.onInit()
                                        ├─ StartEvent → task.onStart()
                                        └─ StopEvent  → task.onStop()
```
The FreeRTOS receive loop itself lives in TaskBase (LLR_TSK_001), not here.

## Constraints
- 100% abstract class — no attributes, no implementation
- Virtual destructor mandatory
- All methods must be pure virtual (= 0)
- Header-only file (no .cpp)
- The dispatch on event type is done by virtual methods only — **no switch/case**

## Instructions for Claude
1. Generate ITask.h with the interface and TaskStatus enum
2. Add include guards (#pragma once)
3. Add Doxygen comment on each method
4. Do not add any attributes or non-virtual methods
5. Forward-declare nothing here; IEvent (LLR_ITF_004) depends on this header
