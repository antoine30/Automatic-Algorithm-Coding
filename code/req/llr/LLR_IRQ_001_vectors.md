# LLR_IRQ_001 — Interrupt Vectors

## Level : LOW LEVEL
## Parent HLR : HLR_001

## Files to Generate
- src/config/stm32f4xx_it.h
- src/config/stm32f4xx_it.cpp

## Interrupt Vector Table
| Vector               | Priority | Trigger            | Usage                    |
|----------------------|----------|--------------------|--------------------------|
| USART1_IRQHandler    | 5        | RX not empty       | UART receive             |
| SPI1_IRQHandler      | 6        | Transfer complete  | SPI transfer done        |
| TIM2_IRQHandler      | 7        | Update event       | System tick              |
| EXTI15_10_IRQHandler | 10       | Falling edge PC13  | User button press        |

## FreeRTOS Constraints
- configMAX_SYSCALL_INTERRUPT_PRIORITY = 5
- Interrupts with priority >= 5 may call FreeRTOS FromISR APIs
- Interrupts with priority < 5 must NOT call any FreeRTOS API
- No long processing inside ISR handlers
- Use queues or task notifications to defer work to tasks

## ISR Pattern
```cpp
void USART1_IRQHandler(void) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    // notify task via xQueueSendFromISR or vTaskNotifyGiveFromISR
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

## Instructions for Claude
1. Generate stm32f4xx_it.h with all handler declarations
2. Generate stm32f4xx_it.cpp with each handler implementation
3. Each handler must use xHigherPriorityTaskWoken pattern
4. Each handler must call portYIELD_FROM_ISR at the end
5. Add Doxygen comment on each handler describing the trigger and action
