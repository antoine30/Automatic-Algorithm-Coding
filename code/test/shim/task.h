#pragma once

/**
 * @file task.h (SHIM)
 * @brief FreeRTOS task stub — host tests only.
 *
 * xTaskCreate does NOT launch the task function: the tests drive the dispatch
 * manually via TaskBase::processNextEvent().
 */

#include "FreeRTOS.h"

typedef void *TaskHandle_t;
typedef void (*TaskFunction_t)(void *);

inline BaseType_t xTaskCreate(TaskFunction_t fn, const char *name, uint16_t stack,
                              void *param, UBaseType_t prio, TaskHandle_t *handle)
{
    (void)fn;
    (void)name;
    (void)stack;
    (void)param;
    (void)prio;
    if (handle != nullptr)
    {
        *handle = reinterpret_cast<TaskHandle_t>(1); // non-null handle.
    }
    return pdPASS;
}

inline void vTaskDelete(TaskHandle_t) {}
inline void vTaskStartScheduler() {}
inline void vTaskDelay(TickType_t) {}
inline void vTaskDelayUntil(TickType_t *, TickType_t) {}
