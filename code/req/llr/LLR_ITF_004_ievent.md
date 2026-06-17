# LLR_ITF_004 — IEvent Interface

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_ITF_001

## Files to Generate
- src/interfaces/IEvent.h

## Description
Pure abstract interface representing an asynchronous event delivered to a task.
A task receives an `IEvent` from its queue and executes the associated code
through a **virtual method** (double-dispatch / visitor pattern).

> MANDATORY : The event type MUST NOT be resolved with a `switch`/`case` or a
> chain of `if/else` on an enum. Routing is done by calling the polymorphic
> `IEvent::execute()`, which itself calls the matching virtual handler on the
> task. Adding a new event = adding a class, never editing a dispatch table.

## Event Identifiers
```cpp
enum class EventId : uint8_t {
    INIT  = 0,   ///< Initialize the task
    START = 1,   ///< Start / run the process
    STOP  = 2    ///< Stop the process
};
```

## Interface Definition
```cpp
class ITask; // forward declaration (see LLR_ITF_001)

/// Abstract event. The concrete type selects the handler to call (no switch).
class IEvent {
public:
    virtual ~IEvent() = default;

    /// @return the event identifier (debug / logging only — NOT for dispatch).
    virtual EventId id() const = 0;

    /// Double-dispatch : execute the code associated with this event by calling
    /// the corresponding virtual method on the task. No switch/case.
    virtual TaskStatus execute(ITask& task) const = 0;
};
```

## Concrete Events
```cpp
/// INIT event → ITask::onInit()
class InitEvent final : public IEvent {
public:
    EventId    id() const override { return EventId::INIT; }
    TaskStatus execute(ITask& task) const override { return task.onInit(); }
};

/// START event → ITask::onStart()
class StartEvent final : public IEvent {
public:
    EventId    id() const override { return EventId::START; }
    TaskStatus execute(ITask& task) const override { return task.onStart(); }
};

/// STOP event → ITask::onStop()
class StopEvent final : public IEvent {
public:
    EventId    id() const override { return EventId::STOP; }
    TaskStatus execute(ITask& task) const override { return task.onStop(); }
};
```

## Singleton Instances
Events are stateless : a single shared instance per type is provided so that a
`const IEvent*` can be posted into a FreeRTOS queue **without dynamic allocation**.
```cpp
namespace events {
    extern const InitEvent  kInit;
    extern const StartEvent kStart;
    extern const StopEvent  kStop;
}
```

## Constraints
- C++17, no malloc/new/delete, no exceptions
- Dispatch by virtual method only — **no switch/case, no if/else on EventId**
- Virtual destructor mandatory
- Events are stateless and shared as static singletons (no heap)
- `#pragma once` include guard
- Doxygen comment on every public method

## Instructions for Claude
1. Generate IEvent.h with the EventId enum, IEvent interface and the three
   concrete event classes
2. Declare the singleton instances in namespace `events` (define them in a small
   IEvent.cpp or inside TaskBase.cpp — keep them static, no heap)
3. Add Doxygen comment on each method
4. Do NOT use any switch/case to resolve the event type
