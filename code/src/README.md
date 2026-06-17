# STM32 FreeRTOS — Event-driven system

Code generated from the requirements in [`code/req/`](../req/) (MASTER + HLR + LLR),
in the generation order enforced by [MASTER.md](../req/master/MASTER.md).

## Principle: dispatch via virtual method, no switch/case

A task receives an `IEvent` on its queue and runs the associated code through a
**virtual method**: `IEvent::execute(task)` calls `onInit`/`onStart`/`onStop`
(double-dispatch / visitor). The event type is **never** resolved with a
`switch/case` or an `if/else` chain.

```
event queue ──► TaskBase::run() ──► event->execute(*this)
                                         ├─ InitEvent  → task.onInit()
                                         ├─ StartEvent → task.onStart()
                                         └─ StopEvent  → task.onStop()
```

## Layout

| Folder / file | LLR | Role |
|---|---|---|
| `interfaces/ITask.h` | LLR_ITF_001 | Task interface (virtual handlers) |
| `interfaces/IDriver.h` | LLR_ITF_002 | Driver interface |
| `interfaces/ISensor.h` | LLR_ITF_003 | Sensor interface |
| `interfaces/IEvent.h` / `.cpp` | LLR_ITF_004 | Events + double-dispatch |
| `config/io_mapping.h` | LLR_IOM_001 | GPIO mapping |
| `config/stm32f4xx_it.h` / `.cpp` | LLR_IRQ_001 | Interrupt vectors |
| `config/FreeRTOSConfig.h`, `scheduler.h` / `.cpp` | LLR_SCH_001 | Config + scheduler |
| `drivers/UartDriver.*`, `SpiDriver.*`, `I2cDriver.*` | LLR_DRV_001..003 | HAL drivers |
| `tasks/TaskBase.h` / `.cpp` | LLR_TSK_001 | Event loop + dispatch |
| `tasks/TaskCommunication.*` | LLR_TSK_002 | Event-driven UART task |
| `tasks/TaskSensor.*` | LLR_TSK_003 | Event-driven sensor task (ISensor) |
| `tasks/TaskHeartbeat.*` | LLR_TSK_004 | Event-driven heartbeat LED task |
| `main.cpp` | — | Entry point (init + scheduler) |

## Build

- **STM32F4 target**: `config/`, `drivers/`, `tasks/`, `main.cpp` depend on the
  STM32 HAL (`stm32f4xx_hal.h`) and a FreeRTOS port — build with the embedded
  toolchain (arm-none-eabi-g++), with CubeMX/BSP providing `huart1`, etc.
- **Host (tests)**: compiled and tested on a PC thanks to shims in `test/shim/`
  that emulate the missing dependencies:
  - `FreeRTOS.h` / `queue.h` / `task.h` → queue + tasks (for `TaskBase`)
  - `semphr.h` → mutexes (for the drivers)
  - `stm32f4xx_hal.h` → HAL **with a controllable mock** `g_hal` (inject
    `HAL_OK`/`HAL_TIMEOUT`/`HAL_ERROR`, call counters, GPIO state).

## Tests

```sh
cd ../test
make        # build (C++17) and run the 4 suites (83 checks)
```
- `run_tests`: event dispatch (interfaces + IEvent), pure.
- `run_tests_taskbase`: TaskBase queue + dispatch loop (FreeRTOS shim).
- `run_tests_sensor`: TaskSensor with a mock ISensor.
- `run_tests_drivers`: UART/SPI/I2C via the HAL shim (status mapping, SPI CS
  deassertion, I2C bus recovery).

## Known gaps (to track)

- `TaskSensor` (LLR_TSK_003) is **defined and tested** but **not instantiated**
  in the scheduler: it requires a concrete `ISensor` implementation (e.g. an I2C
  sensor driver), which does not yet have an LLR.
- `stm32f4xx_it.cpp` expects `hspi1` / `htim2` from the BSP/CubeMX (HAL handles).
