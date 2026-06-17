#pragma once

/**
 * @file FreeRTOSConfig.h
 * @brief LLR_SCH_001 — FreeRTOS configuration (STM32F4).
 */

#define configUSE_PREEMPTION                    1
#define configTICK_RATE_HZ                      ((TickType_t)1000)
#define configMAX_PRIORITIES                    7
#define configMINIMAL_STACK_SIZE                ((uint16_t)128)
#define configTOTAL_HEAP_SIZE                   ((size_t)32768)
#define configUSE_TIMERS                        1
#define configTIMER_TASK_PRIORITY               (configMAX_PRIORITIES - 1)
#define configTIMER_QUEUE_LENGTH                10
#define configTIMER_TASK_STACK_DEPTH            configMINIMAL_STACK_SIZE
#define configUSE_MUTEXES                       1
#define configUSE_COUNTING_SEMAPHORES           1
#define configSUPPORT_STATIC_ALLOCATION         1
#define configSUPPORT_DYNAMIC_ALLOCATION        1
#define configUSE_16_BIT_TICKS                  0
#define configUSE_IDLE_HOOK                     0
#define configUSE_TICK_HOOK                     0

/* Interrupt priorities (Cortex-M4 / NVIC). */
#define configPRIO_BITS                         4
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY 15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5
#define configMAX_SYSCALL_INTERRUPT_PRIORITY \
    (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

/* Optional FreeRTOS APIs used. */
#define INCLUDE_vTaskDelete                     1
#define INCLUDE_vTaskDelayUntil                 1
#define INCLUDE_vTaskDelay                      1
#define INCLUDE_uxTaskGetStackHighWaterMark     1

/* Mapping of kernel handlers to CMSIS vectors. */
#define vPortSVCHandler     SVC_Handler
#define xPortPendSVHandler  PendSV_Handler
#define xPortSysTickHandler SysTick_Handler
