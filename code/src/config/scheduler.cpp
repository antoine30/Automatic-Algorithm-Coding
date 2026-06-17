/**
 * @file scheduler.cpp
 * @brief LLR_SCH_001 — Scheduler implementation.
 */

#include "config/scheduler.h"

#include "FreeRTOS.h"
#include "task.h"

#include "interfaces/IEvent.h"

// --- Hardware resources and tasks (static storage: no heap) ----------------
// huart1 is normally provided by the BSP/CubeMX; declared here for linking.
UART_HandleTypeDef huart1;

static UartDriver g_uartDriver(&huart1);

// Global referenced by the ISRs (see stm32f4xx_it.cpp).
TaskCommunication g_taskCommunication(g_uartDriver);
TaskHeartbeat g_taskHeartbeat;

// Static check: the sum of the stacks fits within the FreeRTOS heap.
// TaskCommunication 512 + TaskHeartbeat 128 = 640 words.
static_assert((512 + 128) * sizeof(StackType_t) < configTOTAL_HEAP_SIZE,
              "Task stacks exceed configTOTAL_HEAP_SIZE");

Scheduler &Scheduler::getInstance()
{
    static Scheduler instance; // Singleton (initialized on first request).
    return instance;
}

Scheduler::Scheduler() = default;

void Scheduler::init()
{
    // Create the queue + task, then send INIT and START to each task.
    g_taskCommunication.start();
    g_taskCommunication.postEvent(events::kInit, portMAX_DELAY);
    g_taskCommunication.postEvent(events::kStart, portMAX_DELAY);

    g_taskHeartbeat.start();
    g_taskHeartbeat.postEvent(events::kInit, portMAX_DELAY);
    g_taskHeartbeat.postEvent(events::kStart, portMAX_DELAY);
}

void Scheduler::start()
{
    vTaskStartScheduler(); // Does not return during normal operation.
}
