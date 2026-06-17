#pragma once

/**
 * @file semphr.h (SHIM)
 * @brief FreeRTOS semaphore/mutex stub — host tests only.
 *
 * Mutexes are simulated: take/give always succeed. Enough to exercise the
 * driver logic (critical sections) on a PC.
 */

#include "FreeRTOS.h"

typedef void *SemaphoreHandle_t;

/// Dummy static storage for a mutex.
typedef struct
{
    int dummy;
} StaticSemaphore_t;

inline SemaphoreHandle_t xSemaphoreCreateMutexStatic(StaticSemaphore_t *buffer)
{
    return reinterpret_cast<SemaphoreHandle_t>(buffer); // non-null handle.
}

inline BaseType_t xSemaphoreTake(SemaphoreHandle_t, TickType_t) { return pdTRUE; }
inline BaseType_t xSemaphoreGive(SemaphoreHandle_t) { return pdTRUE; }
