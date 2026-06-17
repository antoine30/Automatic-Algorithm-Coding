#pragma once

/**
 * @file FreeRTOS.h (SHIM)
 * @brief Stub FreeRTOS minimal — UNIQUEMENT pour les tests hôte.
 *
 * NE FAIT PAS PARTIE DU FIRMWARE. Fournit juste les types et macros utilisés
 * par TaskBase afin de pouvoir tester la boucle de dispatch sur PC.
 */

#include <cstddef>
#include <cstdint>

typedef long BaseType_t;
typedef unsigned long UBaseType_t;
typedef uint32_t TickType_t;
typedef uint32_t StackType_t;

#define pdTRUE ((BaseType_t)1)
#define pdFALSE ((BaseType_t)0)
#define pdPASS pdTRUE
#define pdFAIL pdFALSE

#define portMAX_DELAY ((TickType_t)0xFFFFFFFFU)
#define tskIDLE_PRIORITY ((UBaseType_t)0)
#define configMINIMAL_STACK_SIZE ((uint16_t)128)
#define configTOTAL_HEAP_SIZE ((size_t)32768)

#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
