/**
 * @file stm32f4xx_it.cpp
 * @brief LLR_IRQ_001 — Implémentation des gestionnaires d'interruption.
 *
 * Chaque handler diffère le travail vers une tâche (pattern FromISR) puis
 * appelle portYIELD_FROM_ISR pour basculer immédiatement si une tâche de plus
 * haute priorité a été réveillée.
 */

#include "stm32f4xx_it.h"

#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"

#include "stm32f4xx_hal.h"

#include "interfaces/IEvent.h"
#include "tasks/TaskCommunication.h"

// Instances externes définies par le scheduler (cf. scheduler.cpp).
extern UART_HandleTypeDef huart1;
extern TaskCommunication g_taskCommunication;

extern "C" void USART1_IRQHandler(void)
{
    // Acquitte l'IT HAL puis signale à la tâche qu'une donnée est disponible.
    HAL_UART_IRQHandler(&huart1);

    BaseType_t higherPriorityTaskWoken = pdFALSE;
    // On poste l'événement START : la tâche lira et traitera la donnée reçue.
    g_taskCommunication.postEventFromISR(events::kStart, &higherPriorityTaskWoken);
    portYIELD_FROM_ISR(higherPriorityTaskWoken);
}

extern "C" void SPI1_IRQHandler(void)
{
    // Transfert SPI terminé : on laisse HAL gérer le callback de complétion.
    extern SPI_HandleTypeDef hspi1;
    HAL_SPI_IRQHandler(&hspi1);

    BaseType_t higherPriorityTaskWoken = pdFALSE;
    portYIELD_FROM_ISR(higherPriorityTaskWoken);
}

extern "C" void TIM2_IRQHandler(void)
{
    // Tick système applicatif.
    extern TIM_HandleTypeDef htim2;
    HAL_TIM_IRQHandler(&htim2);
}

extern "C" void EXTI15_10_IRQHandler(void)
{
    // Appui bouton utilisateur (PC13) : on demande un arrêt du process.
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_13);

    BaseType_t higherPriorityTaskWoken = pdFALSE;
    g_taskCommunication.postEventFromISR(events::kStop, &higherPriorityTaskWoken);
    portYIELD_FROM_ISR(higherPriorityTaskWoken);
}
