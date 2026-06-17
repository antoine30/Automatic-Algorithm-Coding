#pragma once

/**
 * @file stm32f4xx_it.h
 * @brief LLR_IRQ_001 — Interrupt handler declarations.
 *
 * FreeRTOS constraints:
 * - configMAX_SYSCALL_INTERRUPT_PRIORITY = 5
 * - Only interrupts with priority >= 5 (numeric value) may call FreeRTOS
 *   FromISR APIs.
 * - No long processing in an ISR: work is deferred to tasks via queues /
 *   notifications.
 */

#ifdef __cplusplus
extern "C"
{
#endif

/// USART1: RX not empty → wake the communication task. Priority 5.
void USART1_IRQHandler(void);

/// SPI1: transfer complete → transfer-complete notification. Priority 6.
void SPI1_IRQHandler(void);

/// TIM2: update event → system tick. Priority 7.
void TIM2_IRQHandler(void);

/// EXTI15_10: PC13 falling edge → user button press. Priority 10.
void EXTI15_10_IRQHandler(void);

#ifdef __cplusplus
}
#endif
