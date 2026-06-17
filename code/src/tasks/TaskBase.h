#pragma once

/**
 * @file TaskBase.h
 * @brief LLR_TSK_001 — Abstract base class for FreeRTOS tasks.
 *
 * Manages the FreeRTOS lifecycle and an EVENT QUEUE. The task loop blocks on
 * the queue, receives an IEvent, and calls event.execute(*this) which routes
 * to the appropriate virtual handler (onInit/onStart/onStop).
 * NO switch/case on the event type: dispatch is polymorphic.
 */

#include <cstdint>

#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"

#include "interfaces/IEvent.h"
#include "interfaces/ITask.h"

class TaskBase : public ITask
{
public:
    TaskBase(const char *name, uint32_t stackSize, UBaseType_t priority,
             uint32_t queueLength = 8);
    virtual ~TaskBase();

    void start(); ///< Creates the event queue and starts the FreeRTOS task.
    void stop();  ///< Deletes the FreeRTOS task and the queue.

    /// Posts an event (task context). @return false if the queue is full.
    bool postEvent(const IEvent &event, TickType_t timeout = 0);

    /// Posts an event from an ISR.
    bool postEventFromISR(const IEvent &event, BaseType_t *higherPriorityTaskWoken);

protected:
    /// Receives an event (with @p timeout) and dispatches it via virtual
    /// method (event->execute). @return true if an event was processed.
    /// Extracted from the loop so it can be tested outside the scheduler.
    bool processNextEvent(TickType_t timeout);

    const char *m_name;
    uint32_t m_stackSize;
    UBaseType_t m_priority;
    uint32_t m_queueLength;
    TaskHandle_t m_handle;
    QueueHandle_t m_eventQueue; ///< Carries const IEvent* (no malloc).

private:
    static void taskEntry(void *param); ///< FreeRTOS entry point (static).
    void run();                         ///< Receive + dispatch loop.
};
