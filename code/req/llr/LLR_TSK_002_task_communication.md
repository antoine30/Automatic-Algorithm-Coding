# LLR_TSK_002 — TaskCommunication

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_TSK_001, LLR_DRV_001, LLR_ITF_004

## Files to Generate
- src/tasks/TaskCommunication.h
- src/tasks/TaskCommunication.cpp

## Description
Event-driven FreeRTOS task responsible for UART communication.
It reacts to the INIT / START / STOP events through virtual handlers (no switch).
Incoming UART data is signalled by posting a START event (or a dedicated data
event) from the UART RX interrupt; the handler then reads and processes it.

## Class Definition
```cpp
class TaskCommunication : public TaskBase {
public:
    explicit TaskCommunication(IDriver& uartDriver);

    // Event handlers — invoked by IEvent::execute() (double-dispatch, no switch)
    TaskStatus onInit()  override; ///< INIT  : init UART, verify connection
    TaskStatus onStart() override; ///< START : read UART + processMessage()
    TaskStatus onStop()  override; ///< STOP  : flush buffer, log shutdown
    const char* getName() const override;

private:
    IDriver&       m_uart;
    static uint8_t s_rxBuffer[256]; ///< Static buffer — no malloc
    uint32_t       m_rxCount;
    bool           m_running;

    TaskStatus processMessage(const uint8_t* buf, size_t len);
};
```

## Behavior
- onInit()  : initialize UART driver, verify connection, set m_running = false
- onStart() : set m_running = true, read UART (1000ms timeout), call processMessage()
- onStop()  : set m_running = false, flush buffer, log shutdown

## Constraints
- Stack  : 512 words
- Priority : 3
- Timeout of 1000ms on every UART read
- TIMEOUT error must not stop the task — log and continue
- Static RX buffer — no dynamic allocation
- React to events only through the virtual handlers — **no switch/case**

## Error Handling
| Error                 | Action                        |
|-----------------------|-------------------------------|
| DriverStatus::TIMEOUT | Log + return OK (continue)    |
| DriverStatus::ERROR   | Log + reset driver + return OK |
| processMessage fail   | Log + discard message         |
| Event before onInit() | Return NOT_INITIALIZED        |

## Instructions for Claude
1. Generate TaskCommunication.h with the class definition above
2. Generate TaskCommunication.cpp with full implementation of the 3 handlers
3. Inject IDriver by reference (dependency injection)
4. Handlers are invoked via IEvent::execute() — do NOT add a switch on event id
5. Add Doxygen comment on each method
6. Generate tests/test_task_communication.cpp with a mock IDriver, posting
   InitEvent/StartEvent/StopEvent and checking each handler runs
