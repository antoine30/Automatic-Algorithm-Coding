# MASTER — STM32 FreeRTOS System

## Global Rules
- Language : C++17
- Target   : STM32F4
- OS       : FreeRTOS
- No malloc / new / delete
- No exceptions
- Fixed-width types : uint8_t, uint16_t, uint32_t
- Doxygen comments mandatory on all public methods

## Architecture Rule (MANDATORY)
- Tasks are EVENT-DRIVEN : a task receives an IEvent on its queue and executes
  the associated code through a VIRTUAL method (IEvent::execute → onInit/onStart/
  onStop). The event type is NEVER resolved with a switch/case or if/else chain.

## Code Generation Order (MANDATORY)
1. LLR/06_io_mapping/     ← GPIO pin mapping
2. LLR/05_interrupts/     ← interrupt vectors
3. LLR/03_interfaces/     ← abstract interfaces (ITask, IDriver, ISensor, IEvent)
4. LLR/04_drivers/        ← drivers (depend on interfaces)
5. LLR/01_scheduling/     ← FreeRTOS configuration
6. LLR/02_tasks/          ← tasks (depend on drivers + IEvent)

## Traceability Matrix
| HLR       | LLR           | Generated Files                     |
|-----------|---------------|-------------------------------------|
| HLR_001   | LLR_IOM_001   | src/config/io_mapping.h             |
| HLR_001   | LLR_IRQ_001   | src/config/stm32f4xx_it.h/.cpp      |
| HLR_001   | LLR_ITF_001   | src/interfaces/ITask.h              |
| HLR_001   | LLR_ITF_002   | src/interfaces/IDriver.h            |
| HLR_001   | LLR_ITF_003   | src/interfaces/ISensor.h            |
| HLR_001   | LLR_ITF_004   | src/interfaces/IEvent.h             |
| HLR_001   | LLR_DRV_001   | src/drivers/UartDriver.h/.cpp       |
| HLR_001   | LLR_DRV_002   | src/drivers/SpiDriver.h/.cpp        |
| HLR_001   | LLR_DRV_003   | src/drivers/I2cDriver.h/.cpp        |
| HLR_001   | LLR_SCH_001   | src/config/FreeRTOSConfig.h         |
| HLR_001   | LLR_TSK_001   | src/tasks/TaskBase.h/.cpp           |
| HLR_001   | LLR_TSK_002   | src/tasks/TaskCommunication.h/.cpp  |
| HLR_001   | LLR_TSK_003   | src/tasks/TaskSensor.h/.cpp         |
| HLR_001   | LLR_TSK_004   | src/tasks/TaskHeartbeat.h/.cpp      |

## Claude Code Instructions
```
Read requirements/MASTER.md first.
Generate code in the order defined above.
Respect all constraints defined in each LLR.
Do not generate a file if its LLR dependencies are not yet generated.
```
