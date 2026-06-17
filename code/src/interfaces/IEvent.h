#pragma once

/**
 * @file IEvent.h
 * @brief LLR_ITF_004 — Asynchronous event delivered to a task.
 *
 * Routing an event to its handling is done ONLY through a virtual method
 * (double-dispatch / visitor): IEvent::execute() calls the corresponding
 * handler of the task. No switch/case, no if/else chain on EventId. Adding an
 * event = adding a class, never editing a dispatch table.
 */

#include <cstdint>

#include "ITask.h"

/// Event identifiers (debug / log only — NOT for dispatch).
enum class EventId : uint8_t
{
    INIT = 0,  ///< Initializes the task.
    START = 1, ///< Starts / runs the process.
    STOP = 2   ///< Stops the process.
};

/**
 * @brief Abstract event. The concrete type chooses the handler to call.
 */
class IEvent
{
public:
    virtual ~IEvent() = default;

    /// @return the event identifier (debug/log, never for dispatch).
    virtual EventId id() const = 0;

    /// Double-dispatch: runs the associated code by calling the appropriate
    /// virtual handler of the task. No switch/case.
    virtual TaskStatus execute(ITask &task) const = 0;
};

/// INIT event → ITask::onInit().
class InitEvent final : public IEvent
{
public:
    EventId id() const override { return EventId::INIT; }
    TaskStatus execute(ITask &task) const override { return task.onInit(); }
};

/// START event → ITask::onStart().
class StartEvent final : public IEvent
{
public:
    EventId id() const override { return EventId::START; }
    TaskStatus execute(ITask &task) const override { return task.onStart(); }
};

/// STOP event → ITask::onStop().
class StopEvent final : public IEvent
{
public:
    EventId id() const override { return EventId::STOP; }
    TaskStatus execute(ITask &task) const override { return task.onStop(); }
};

/**
 * @brief Shared singleton instances (stateless events).
 *
 * Allows posting a const IEvent* into a FreeRTOS queue without dynamic
 * allocation.
 */
namespace events
{
extern const InitEvent kInit;
extern const StartEvent kStart;
extern const StopEvent kStop;
} // namespace events
