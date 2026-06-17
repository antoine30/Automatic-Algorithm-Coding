/**
 * @file main.cpp
 * @brief Application entry point (STM32F4 + FreeRTOS).
 *
 * Initializes the HAL then delegates to the Scheduler: task creation, sending
 * of the initialization events, and startup of the scheduler.
 */

#include "stm32f4xx_hal.h"

#include "config/scheduler.h"

int main(void)
{
    // Hardware initialization (clocks, peripherals) — provided by the BSP.
    HAL_Init();

    Scheduler &scheduler = Scheduler::getInstance();
    scheduler.init();  // Creates the tasks and posts INIT/START.
    scheduler.start(); // Starts the scheduler (does not return).

    // Reached only if the scheduler failed to start.
    for (;;)
    {
    }
    return 0;
}
