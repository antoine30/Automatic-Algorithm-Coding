/**
 * @file stm32f4xx_it.cpp
 * @brief LLR_IRQ_001 — Interrupt handler implementation.
 *
 * Each handler defers the work to a task (FromISR pattern) then calls
 * portYIELD_FROM_ISR to switch immediately if a higher-priority task has been
 * woken.
 */

#include "stm32f4xx_it.h"

#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"

#include "stm32f4xx_hal.h"

#include "interfaces/IEvent.h"
#include "tasks/TaskCommunication.h"

// External instances defined by the scheduler (see scheduler.cpp).
extern UART_HandleTypeDef huart1;
extern TaskCommunication g_taskCommunication;

extern "C" void USART1_IRQHandler(void)
{
    // Acknowledge the HAL interrupt then signal the task that data is available.
    HAL_UART_IRQHandler(&huart1);

    BaseType_t higherPriorityTaskWoken = pdFALSE;
    // Post the START event: the task will read and process the received data.
    g_taskCommunication.postEventFromISR(events::kStart, &higherPriorityTaskWoken);
    portYIELD_FROM_ISR(higherPriorityTaskWoken);
}

extern "C" void SPI1_IRQHandler(void)
{
    // SPI transfer complete: let HAL handle the completion callback.
    extern SPI_HandleTypeDef hspi1;
    HAL_SPI_IRQHandler(&hspi1);

    BaseType_t higherPriorityTaskWoken = pdFALSE;
    portYIELD_FROM_ISR(higherPriorityTaskWoken);
}

extern "C" void TIM2_IRQHandler(void)
{
    // Application system tick.
    extern TIM_HandleTypeDef htim2;
    HAL_TIM_IRQHandler(&htim2);
}

extern "C" void EXTI15_10_IRQHandler(void)
{
    // User button press (PC13): request a process stop.
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_13);

    BaseType_t higherPriorityTaskWoken = pdFALSE;
    g_taskCommunication.postEventFromISR(events::kStop, &higherPriorityTaskWoken);
    portYIELD_FROM_ISR(higherPriorityTaskWoken);
}
