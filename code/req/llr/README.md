# LLR — Low Level Requirements

Low Level Requirements describe **how** each unit of the system is
implemented. They are the direct input to Claude Code. Each LLR
produces one or more source files.

---

## Files

### IO and interrupts

| File                    | Generated files                          |
|-------------------------|------------------------------------------|
| `LLR_IOM_001_gpio`      | `src/config/io_mapping.h`               |
| `LLR_IRQ_001_vectors`   | `src/config/stm32f4xx_it.h/.cpp`        |

### Interfaces (abstract, header-only)

| File                    | Generated files                          |
|-------------------------|------------------------------------------|
| `LLR_ITF_001_itask`     | `src/interfaces/ITask.h`                |
| `LLR_ITF_002_idriver`   | `src/interfaces/IDriver.h`              |
| `LLR_ITF_003_isensor`   | `src/interfaces/ISensor.h`              |
| `LLR_ITF_004_ievent`    | `src/interfaces/IEvent.h`               |

### Drivers

| File                    | Generated files                          |
|-------------------------|------------------------------------------|
| `LLR_DRV_001_uart`      | `src/drivers/UartDriver.h/.cpp`         |
| `LLR_DRV_002_spi`       | `src/drivers/SpiDriver.h/.cpp`          |
| `LLR_DRV_003_i2c`       | `src/drivers/I2cDriver.h/.cpp`          |

### Scheduling

| File                    | Generated files                          |
|-------------------------|------------------------------------------|
| `LLR_SCH_001_freertos_config` | `src/config/FreeRTOSConfig.h`<br>`src/config/scheduler.h/.cpp` |

### Tasks

| File                    | Generated files                          |
|-------------------------|------------------------------------------|
| `LLR_TSK_001_task_base`          | `src/tasks/TaskBase.h/.cpp`   |
| `LLR_TSK_002_task_communication` | `src/tasks/TaskComm.h/.cpp`   |
| `LLR_TSK_003_task_sensor`        | `src/tasks/TaskSensor.h/.cpp` |
| `LLR_TSK_004_task_heartbeat`     | `src/tasks/TaskHB.h/.cpp`     |

---

## LLR structure

Every LLR contains these sections — no implementation code:

```
1. Purpose
2. Interface specification   ← inputs, outputs, types
3. Behavioral specification  ← what it must do, not how
4. Constraints               ← no malloc, no float, thread-safe…
5. Test requirements         ← input → expected output tables
```

---

## Event dispatch — no switch/case

Tasks receive messages via event objects. Each event dispatches
itself to the correct virtual method on the task. No switch/case
or enum comparison is permitted anywhere in the generated source.

Adding a new message type = creating a new Event class only.
No existing code is modified.

---

## Generate a single LLR

```bash
# Regenerate one driver without touching anything else
claude "Read code/req/llr/LLR_DRV_001_uart.md
and regenerate src/drivers/UartDriver.h and UartDriver.cpp only."
```
