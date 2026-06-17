#pragma once

/**
 * @file stm32f4xx_it.h
 * @brief LLR_IRQ_001 — Déclarations des gestionnaires d'interruption.
 *
 * Contraintes FreeRTOS :
 * - configMAX_SYSCALL_INTERRUPT_PRIORITY = 5
 * - Seules les IT de priorité >= 5 (valeur numérique) peuvent appeler les API
 *   FromISR de FreeRTOS.
 * - Aucun traitement long en ISR : on défère le travail aux tâches via files /
 *   notifications.
 */

#ifdef __cplusplus
extern "C"
{
#endif

/// USART1 : RX non vide → réveil de la tâche de communication. Priorité 5.
void USART1_IRQHandler(void);

/// SPI1 : transfert terminé → notification de fin de transfert. Priorité 6.
void SPI1_IRQHandler(void);

/// TIM2 : événement update → tick système. Priorité 7.
void TIM2_IRQHandler(void);

/// EXTI15_10 : front descendant PC13 → appui bouton utilisateur. Priorité 10.
void EXTI15_10_IRQHandler(void);

#ifdef __cplusplus
}
#endif
