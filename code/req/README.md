# Requirements — System Specification

This folder contains all system requirements organized in three levels.

---

## Structure

```
req/
├── master/        ← start here — defines generation order and global rules
│   └── MASTER.md
├── hlr/           ← High Level Requirements (what the system must do)
│   └── HLR_001_system.md
└── llr/           ← Low Level Requirements (how each unit is implemented)
    ├── LLR_IOM_001_gpio.md
    ├── LLR_IRQ_001_vectors.md
    ├── LLR_ITF_001_itask.md
    ├── LLR_ITF_002_idriver.md
    ├── LLR_ITF_003_isensor.md
    ├── LLR_ITF_004_ievent.md
    ├── LLR_DRV_001_uart.md
    ├── LLR_DRV_002_spi.md
    ├── LLR_DRV_003_i2c.md
    ├── LLR_SCH_001_freertos_config.md
    ├── LLR_TSK_001_task_base.md
    ├── LLR_TSK_002_task_communication.md
    ├── LLR_TSK_003_task_sensor.md
    └── LLR_TSK_004_task_heartbeat.md
```

---

## Two levels of requirements

**HLR — High Level Requirements**
Describe *what* the system must do from a functional perspective.
Technology-agnostic. Each HLR links to one or more LLRs.

**LLR — Low Level Requirements**
Describe *how* each unit is implemented. They are the direct input
to Claude Code and contain interface definitions, constraints,
and test requirements — but no implementation code.

---

## LLR naming convention

| Prefix | Domain              | Example                    |
|--------|---------------------|----------------------------|
| IOM    | IO mapping          | LLR\_IOM\_001\_gpio        |
| IRQ    | Interrupt vectors   | LLR\_IRQ\_001\_vectors     |
| ITF    | Interfaces          | LLR\_ITF\_001\_itask       |
| DRV    | Drivers             | LLR\_DRV\_001\_uart        |
| SCH    | Scheduling          | LLR\_SCH\_001\_freertos    |
| TSK    | Tasks               | LLR\_TSK\_001\_task\_base  |

---

## Generation order

Always follow the order in `master/MASTER.md`:

```
1. IOM  →  2. IRQ  →  3. ITF  →  4. DRV  →  5. SCH  →  6. TSK
```

Dependencies flow downward — never generate a file before its
dependencies exist.
