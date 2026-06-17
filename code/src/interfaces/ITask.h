#pragma once

/**
 * @file ITask.h
 * @brief LLR_ITF_001 — Abstract interface for FreeRTOS tasks (event-driven).
 *
 * A task is event-driven: it receives IEvent objects (see LLR_ITF_004) and
 * each event runs the associated code by calling one of the virtual handlers
 * below. The event type is never resolved by a switch/case: it is
 * IEvent::execute() that selects the handler (double-dispatch).
 */

#include <cstdint>

/// Return code for task processing.
enum class TaskStatus : uint8_t
{
    OK = 0,
    ERROR = 1,
    TIMEOUT = 2,
    NOT_INITIALIZED = 3,
    BUSY = 4
};

/**
 * @brief Fully abstract interface that every FreeRTOS task must implement.
 *
 * Handlers are called via IEvent::execute() (double-dispatch). No member
 * data, no implementation: pure interface.
 */
class ITask
{
public:
    virtual ~ITask() = default;

    /// Executed on the INIT event.
    virtual TaskStatus onInit() = 0;

    /// Executed on the START event (starts / runs the process).
    virtual TaskStatus onStart() = 0;

    /// Executed on the STOP event.
    virtual TaskStatus onStop() = 0;

    /// @return the task name (for logging).
    virtual const char *getName() const = 0;
};
