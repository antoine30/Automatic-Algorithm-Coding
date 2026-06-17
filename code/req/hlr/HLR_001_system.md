# HLR_001 — System Overview

## Level : HIGH LEVEL

## Description
The system must manage sensors, communication peripherals,
and real-time tasks on an STM32F4 microcontroller running FreeRTOS.

## Requirements
- HLR_001_01 : The system shall initialize all peripherals before starting tasks
- HLR_001_02 : The system shall detect and report communication errors
- HLR_001_03 : The system shall recover automatically from peripheral faults
- HLR_001_04 : All tasks shall respect their defined periods and priorities
- HLR_001_05 : No dynamic memory allocation shall occur after system init
- HLR_001_06 : Tasks shall be event-driven — each task receives events via a
  queue and executes the associated code through a virtual method (double
  dispatch). The event type shall NOT be resolved with a switch/case.

## Validation Criteria
- All tasks start within 500ms of power-on
- No data loss at nominal operating conditions
- Watchdog reset must not occur during normal operation

## Associated LLRs
- LLR/06_io_mapping/LLR_IOM_001_gpio.md
- LLR/05_interrupts/LLR_IRQ_001_vectors.md
- LLR/03_interfaces/LLR_ITF_001_itask.md
- LLR/03_interfaces/LLR_ITF_002_idriver.md
- LLR/03_interfaces/LLR_ITF_003_isensor.md
- LLR/03_interfaces/LLR_ITF_004_ievent.md
- LLR/04_drivers/LLR_DRV_001_uart.md
- LLR/04_drivers/LLR_DRV_002_spi.md
- LLR/04_drivers/LLR_DRV_003_i2c.md
- LLR/01_scheduling/LLR_SCH_001_freertos_config.md
- LLR/02_tasks/LLR_TSK_001_task_base.md
- LLR/02_tasks/LLR_TSK_002_task_communication.md
- LLR/02_tasks/LLR_TSK_003_task_sensor.md
- LLR/02_tasks/LLR_TSK_004_task_heartbeat.md
