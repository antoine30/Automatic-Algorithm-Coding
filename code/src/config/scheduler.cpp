/**
 * @file scheduler.cpp
 * @brief LLR_SCH_001 — Implémentation du scheduler.
 */

#include "config/scheduler.h"

#include "FreeRTOS.h"
#include "task.h"

#include "interfaces/IEvent.h"

// --- Ressources matérielles et tâches (stockage statique : aucun heap) -----
// huart1 est normalement fourni par le BSP/CubeMX ; déclaré ici pour le lien.
UART_HandleTypeDef huart1;

static UartDriver g_uartDriver(&huart1);

// Globale référencée par les ISR (cf. stm32f4xx_it.cpp).
TaskCommunication g_taskCommunication(g_uartDriver);
TaskHeartbeat g_taskHeartbeat;

// Vérification statique : la somme des piles tient dans le heap FreeRTOS.
// TaskCommunication 512 + TaskHeartbeat 128 = 640 mots.
static_assert((512 + 128) * sizeof(StackType_t) < configTOTAL_HEAP_SIZE,
              "Task stacks exceed configTOTAL_HEAP_SIZE");

Scheduler &Scheduler::getInstance()
{
    static Scheduler instance; // Singleton (initialisation à la première demande).
    return instance;
}

Scheduler::Scheduler() = default;

void Scheduler::init()
{
    // Crée la file + la tâche, puis envoie INIT et START à chaque tâche.
    g_taskCommunication.start();
    g_taskCommunication.postEvent(events::kInit, portMAX_DELAY);
    g_taskCommunication.postEvent(events::kStart, portMAX_DELAY);

    g_taskHeartbeat.start();
    g_taskHeartbeat.postEvent(events::kInit, portMAX_DELAY);
    g_taskHeartbeat.postEvent(events::kStart, portMAX_DELAY);
}

void Scheduler::start()
{
    vTaskStartScheduler(); // Ne retourne pas en fonctionnement normal.
}
