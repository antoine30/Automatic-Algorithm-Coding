#pragma once

/**
 * @file semphr.h (SHIM)
 * @brief Stub des sémaphores/mutex FreeRTOS — tests hôte uniquement.
 *
 * Les mutex sont simulés : prise/libération réussissent toujours. Suffisant
 * pour exercer la logique des drivers (sections critiques) sur PC.
 */

#include "FreeRTOS.h"

typedef void *SemaphoreHandle_t;

/// Stockage statique factice d'un mutex.
typedef struct
{
    int dummy;
} StaticSemaphore_t;

inline SemaphoreHandle_t xSemaphoreCreateMutexStatic(StaticSemaphore_t *buffer)
{
    return reinterpret_cast<SemaphoreHandle_t>(buffer); // handle non nul.
}

inline BaseType_t xSemaphoreTake(SemaphoreHandle_t, TickType_t) { return pdTRUE; }
inline BaseType_t xSemaphoreGive(SemaphoreHandle_t) { return pdTRUE; }
