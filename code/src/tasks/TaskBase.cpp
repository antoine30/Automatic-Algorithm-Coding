/**
 * @file TaskBase.cpp
 * @brief LLR_TSK_001 — Event loop implementation.
 *
 * Dispatch on the event type is fully polymorphic
 * (event->execute(*this)): this file contains NO switch/case.
 */

#include "tasks/TaskBase.h"

TaskBase::TaskBase(const char *name, uint32_t stackSize, UBaseType_t priority,
                   uint32_t queueLength)
    : m_name(name), m_stackSize(stackSize), m_priority(priority),
      m_queueLength(queueLength), m_handle(nullptr), m_eventQueue(nullptr)
{
}

TaskBase::~TaskBase()
{
    stop();
}

void TaskBase::start()
{
    if (m_handle != nullptr || m_eventQueue != nullptr)
    {
        return; // Already started (idempotent).
    }

    // The queue carries pointers to singleton events.
    m_eventQueue = xQueueCreate(m_queueLength, sizeof(const IEvent *));
    if (m_eventQueue == nullptr)
    {
        return; // Allocation failed: task not started.
    }

    if (xTaskCreate(&TaskBase::taskEntry, m_name, m_stackSize, this, m_priority,
                    &m_handle) != pdPASS)
    {
        vQueueDelete(m_eventQueue);
        m_eventQueue = nullptr;
        m_handle = nullptr;
    }
}

void TaskBase::stop()
{
    if (m_handle != nullptr)
    {
        vTaskDelete(m_handle);
        m_handle = nullptr;
    }
    if (m_eventQueue != nullptr)
    {
        vQueueDelete(m_eventQueue);
        m_eventQueue = nullptr;
    }
}

bool TaskBase::postEvent(const IEvent &event, TickType_t timeout)
{
    if (m_eventQueue == nullptr)
    {
        return false;
    }
    const IEvent *ptr = &event;
    return xQueueSend(m_eventQueue, &ptr, timeout) == pdPASS;
}

bool TaskBase::postEventFromISR(const IEvent &event, BaseType_t *higherPriorityTaskWoken)
{
    if (m_eventQueue == nullptr)
    {
        return false;
    }
    const IEvent *ptr = &event;
    return xQueueSendFromISR(m_eventQueue, &ptr, higherPriorityTaskWoken) == pdPASS;
}

void TaskBase::taskEntry(void *param)
{
    auto *self = reinterpret_cast<TaskBase *>(param);
    self->run();
}

bool TaskBase::processNextEvent(TickType_t timeout)
{
    const IEvent *event = nullptr;

    if (xQueueReceive(m_eventQueue, &event, timeout) == pdTRUE && event != nullptr)
    {
        // Polymorphic dispatch: calls onInit/onStart/onStop. NO switch.
        TaskStatus status = event->execute(*this);
        if (status != TaskStatus::OK)
        {
            // Logging: task name + error code.
            // (hook the project's log channel here)
            (void)status;
        }
        return true;
    }
    return false;
}

void TaskBase::run()
{
    // Infinite loop: block on the queue and dispatch each received event.
    for (;;)
    {
        processNextEvent(portMAX_DELAY);
    }
}
