# STM32 FreeRTOS — Système event-driven

Code généré à partir des requirements [`code/req/`](../req/) (MASTER + HLR + LLR),
dans l'ordre de génération imposé par [MASTER.md](../req/master/MASTER.md).

## Principe : dispatch par méthode virtuelle, sans switch/case

Une tâche reçoit un `IEvent` sur sa file et exécute le code associé via une
**méthode virtuelle** : `IEvent::execute(task)` appelle `onInit`/`onStart`/`onStop`
(double-dispatch / visiteur). Le type d'événement n'est **jamais** résolu par un
`switch/case` ni une chaîne `if/else`.

```
file d'événements ──► TaskBase::run() ──► event->execute(*this)
                                               ├─ InitEvent  → task.onInit()
                                               ├─ StartEvent → task.onStart()
                                               └─ StopEvent  → task.onStop()
```

## Arborescence

| Dossier / fichier | LLR | Rôle |
|---|---|---|
| `interfaces/ITask.h` | LLR_ITF_001 | Interface tâche (handlers virtuels) |
| `interfaces/IDriver.h` | LLR_ITF_002 | Interface driver |
| `interfaces/ISensor.h` | LLR_ITF_003 | Interface capteur |
| `interfaces/IEvent.h` / `.cpp` | LLR_ITF_004 | Événements + double-dispatch |
| `config/io_mapping.h` | LLR_IOM_001 | Mapping GPIO |
| `config/stm32f4xx_it.h` / `.cpp` | LLR_IRQ_001 | Vecteurs d'interruption |
| `config/FreeRTOSConfig.h`, `scheduler.h` / `.cpp` | LLR_SCH_001 | Config + ordonnanceur |
| `drivers/UartDriver.*`, `SpiDriver.*`, `I2cDriver.*` | LLR_DRV_001..003 | Drivers HAL |
| `tasks/TaskBase.h` / `.cpp` | LLR_TSK_001 | Boucle d'événements + dispatch |
| `tasks/TaskCommunication.*` | LLR_TSK_002 | Tâche UART event-driven |
| `tasks/TaskSensor.*` | LLR_TSK_003 | Tâche capteur (ISensor) event-driven |
| `tasks/TaskHeartbeat.*` | LLR_TSK_004 | Tâche LED heartbeat event-driven |
| `main.cpp` | — | Point d'entrée (init + scheduler) |

## Compilation

- **Cible STM32F4** : `config/`, `drivers/`, `tasks/`, `main.cpp` dépendent du
  HAL STM32 (`stm32f4xx_hal.h`) et d'un port FreeRTOS — à compiler avec la
  toolchain embarquée (arm-none-eabi-g++), CubeMX/BSP fournissant `huart1`, etc.
- **Hôte (tests)** : compilés et testés sur PC grâce à des shims dans
  `test/shim/` qui imitent les dépendances absentes :
  - `FreeRTOS.h` / `queue.h` / `task.h` → file + tâches (pour `TaskBase`)
  - `semphr.h` → mutex (pour les drivers)
  - `stm32f4xx_hal.h` → HAL **avec un mock contrôlable** `g_hal` (injection de
    `HAL_OK`/`HAL_TIMEOUT`/`HAL_ERROR`, compteurs d'appels, état des GPIO).

## Tests

```sh
cd ../test
make        # compile (C++17) et exécute les 4 suites (83 vérifications)
```
- `run_tests` : dispatch d'événements (interfaces + IEvent), pur.
- `run_tests_taskbase` : file + boucle de dispatch de TaskBase (shim FreeRTOS).
- `run_tests_sensor` : TaskSensor avec mock ISensor.
- `run_tests_drivers` : UART/SPI/I2C via le shim HAL (mapping de statuts,
  désactivation du CS en SPI, recovery de bus I2C).

## Écarts connus (à tracer)

- `TaskSensor` (LLR_TSK_003) est **définie et testée** mais **non instanciée**
  dans le scheduler : elle requiert une implémentation concrète d'`ISensor`
  (ex. driver capteur I2C), qui n'a pas encore de LLR.
- `stm32f4xx_it.cpp` attend `hspi1` / `htim2` du BSP/CubeMX (handles HAL).
