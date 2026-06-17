# Requirements-Driven Code Generation Strategy

## Overview

This project uses a structured, requirements-driven approach to generate clean,
maintainable C++ code for STM32 / FreeRTOS embedded systems using Claude Code.

The core idea is simple: **describe what the system must do before writing a single
line of code**. Requirements are split into two levels — high level and low level —
and stored as versioned Markdown files. Claude Code reads these files and generates
the corresponding C++ source, headers, and tests in a controlled, traceable order.

---

## Why Requirements-Driven Generation?

Traditional AI-assisted coding tends to produce large, monolithic outputs that are
hard to review, modify, or extend. This strategy solves that by:

- Breaking the system into small, independently described units
- Making every design decision explicit and reviewable before generation
- Enabling partial regeneration (fix one driver, one task, one interface)
- Providing a living document that stays in sync with the codebase
- Making it easy to onboard new contributors — the requirements explain the system

---

## Repository Structure

```
requirements/
├── MASTER.md                        ← entry point, global rules, generation order
├── HLR/                             ← High Level Requirements
│   └── HLR_001_system.md
└── LLR/                             ← Low Level Requirements
    ├── 01_scheduling/
    │   └── LLR_SCH_001_freertos_config.md
    ├── 02_tasks/
    │   ├── LLR_TSK_001_task_base.md
    │   └── LLR_TSK_002_task_communication.md
    ├── 03_interfaces/
    │   ├── LLR_ITF_001_itask.md
    │   ├── LLR_ITF_002_idriver.md
    │   ├── LLR_ITF_003_isensor.md
    │   └── LLR_ITF_004_ievent.md
    ├── 04_drivers/
    │   ├── LLR_DRV_001_uart.md
    │   ├── LLR_DRV_002_spi.md
    │   └── LLR_DRV_003_i2c.md
    ├── 05_events/
    │   ├── LLR_EVT_001_concrete_events.md
    │   └── LLR_EVT_002_event_pool.md
    └── 06_io_mapping/
        └── LLR_IOM_001_gpio.md

src/                                 ← generated C++ source (do not edit manually)
├── config/
├── interfaces/
├── events/
├── drivers/
├── tasks/
└── tests/
```

---

## Two Levels of Requirements

### High Level Requirements (HLR)

HLRs describe **what** the system must do from a functional perspective.
They are technology-agnostic and focus on system behavior, not implementation.

Example: *"The system shall detect and recover from communication errors."*

Each HLR links to one or more LLRs that implement it.

### Low Level Requirements (LLR)

LLRs describe **how** each unit is implemented. They are the direct input
to Claude Code and contain:

- Files to generate (`.h`, `.cpp`)
- Class and method signatures
- Constraints (no malloc, thread-safety, error handling)
- Dependencies on other LLRs
- Step-by-step instructions for Claude

Example: *"Generate UartDriver.h implementing IDriver. Use HAL_UART_Receive_IT.
Static buffer of 256 bytes. Thread-safe via FreeRTOS mutex."*

---

## LLR Naming Convention

| Prefix  | Domain              | Example                        |
|---------|---------------------|--------------------------------|
| IOM     | IO Mapping          | LLR_IOM_001_gpio.md            |
| IRQ     | Interrupt Vectors   | LLR_IRQ_001_vectors.md         |
| ITF     | Interfaces          | LLR_ITF_001_itask.md           |
| EVT     | Events              | LLR_EVT_001_concrete_events.md |
| DRV     | Drivers             | LLR_DRV_001_uart.md            |
| SCH     | Scheduling          | LLR_SCH_001_freertos_config.md |
| TSK     | Tasks               | LLR_TSK_001_task_base.md       |

---

## Architecture Principles

### Event-Based Task Dispatch (no switch/case)

Tasks receive messages (INIT, START, STOP) as event objects.
Each event dispatches itself to the correct virtual method on the task —
there is **no switch/case or enum comparison anywhere** in the codebase.

```
Queue receives IEvent*
      │
      ▼
event->dispatch(*this)         ← polymorphic — NO switch/case
      │
      ├─ InitEvent::dispatch()  → task.onInit(event)
      ├─ StartEvent::dispatch() → task.onStart(event)
      └─ StopEvent::dispatch()  → task.onStop(event)
```

Adding a new message type requires only a new Event class — no existing
code is modified. This is the Open/Closed Principle applied to embedded C++.

### Static Memory Only

No dynamic allocation after system initialization. All buffers, event pools,
and task stacks are allocated at compile time. This is enforced by a global
rule in `MASTER.md` and verified by static_assert at build time.

### Dependency Injection

Drivers are injected into tasks by reference at construction time.
Tasks depend on interfaces (IDriver, ISensor), not concrete implementations.
This makes unit testing straightforward with mock objects.

---

## Code Generation Workflow

### Generate Everything from Scratch

```bash
claude "Read requirements/MASTER.md and generate all code in the mandatory order."
```

### Regenerate a Single Unit

```bash
# Fix a driver
claude "Read requirements/LLR/04_drivers/LLR_DRV_001_uart.md
and regenerate src/drivers/UartDriver.h and UartDriver.cpp only."

# Add a new task
claude "Read requirements/LLR/02_tasks/LLR_TSK_002_task_communication.md
and generate the files listed under 'Files to Generate'."
```

### Fix a Bug

Create a bug report in `requirements/backlog/bugs/BUG_001_description.md`,
then:

```bash
claude "Read requirements/backlog/bugs/BUG_001_description.md
and apply the fix to the files listed under 'Files Concerned'."
```

### Add a Feature

Create a feature spec in `requirements/backlog/features/FEAT_001_description.md`,
then:

```bash
claude "Read requirements/backlog/features/FEAT_001_description.md
and implement the feature without modifying unrelated files."
```

---

## Global Constraints (enforced in MASTER.md)

| Rule                          | Enforcement                        |
|-------------------------------|------------------------------------|
| No malloc / new / delete      | static_assert on pool sizes        |
| No exceptions                 | compiler flag `-fno-exceptions`    |
| No switch/case on event type  | `grep -r "switch" src/` must be empty |
| Fixed-width types only        | Doxygen lint + code review         |
| Doxygen on all public methods | CI documentation build             |
| Thread-safe drivers           | FreeRTOS mutex in every driver     |

---

## Adding a New Message Type

1. Create `src/events/PauseEvent.h` inheriting `IEvent`
2. Implement `dispatch()` to call `task.onPause(*this)`
3. Add `onPause(const PauseEvent&) = 0` to `ITask`
4. Implement `onPause()` in each concrete task
5. Update the corresponding LLR to document the change

No existing dispatch code is modified. ✓

---

## Traceability

Every generated file traces back to an LLR, and every LLR traces back to an HLR.
The traceability matrix in `MASTER.md` is the single source of truth.

| HLR     | LLR           | Generated File                     |
|---------|---------------|------------------------------------|
| HLR_001 | LLR_IOM_001   | src/config/io_mapping.h            |
| HLR_001 | LLR_IRQ_001   | src/config/stm32f4xx_it.h/.cpp     |
| HLR_001 | LLR_ITF_001   | src/interfaces/ITask.h             |
| HLR_001 | LLR_ITF_004   | src/interfaces/IEvent.h            |
| HLR_001 | LLR_EVT_001   | src/events/Init/Start/StopEvent.h  |
| HLR_001 | LLR_DRV_001   | src/drivers/UartDriver.h/.cpp      |
| HLR_001 | LLR_TSK_001   | src/tasks/TaskBase.h/.cpp          |

---

## Target Platform

| Parameter     | Value              |
|---------------|--------------------|
| MCU           | STM32F4            |
| OS            | FreeRTOS           |
| Language      | C++17              |
| Compiler      | GCC ARM            |
| Tick rate     | 1000 Hz            |
| Heap size     | 32768 bytes        |

---

## Contributing

To add or modify a feature:

1. Update or create the relevant LLR file in `requirements/LLR/`
2. Update the traceability matrix in `MASTER.md`
3. Run Claude Code with the updated LLR
4. Review the generated diff — never edit `src/` manually
5. Commit both the updated `.md` and the generated `.cpp`/`.h`

The `.md` files are the source of truth. The `src/` files are their output.
