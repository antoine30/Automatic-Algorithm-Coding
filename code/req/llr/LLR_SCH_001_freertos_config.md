# LLR_SCH_001 — FreeRTOS Scheduling Configuration

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_TSK_001, LLR_TSK_002

## Files to Generate
- src/config/FreeRTOSConfig.h
- src/config/scheduler.h
- src/config/scheduler.cpp

## Task Registry
| Task                | Priority | Stack (words) | Period   | Core Affinity |
|---------------------|----------|---------------|----------|---------------|
| TaskCommunication   | 3        | 512           | 10 ms    | Any           |
| TaskSensor          | 2        | 256           | 50 ms    | Any           |
| TaskHeartbeat       | 1        | 128           | 500 ms   | Any           |

## FreeRTOS Configuration
- configTICK_RATE_HZ            : 1000
- configMAX_PRIORITIES          : 7
- configTOTAL_HEAP_SIZE         : 32768
- configUSE_PREEMPTION          : 1
- configUSE_TIMERS              : 1
- configUSE_MUTEXES             : 1
- configUSE_COUNTING_SEMAPHORES : 1
- configMAX_SYSCALL_INTERRUPT_PRIORITY : 5

## Scheduler Class
```cpp
class Scheduler {
public:
    static Scheduler& getInstance();
    void init();    ///< Instantiate all tasks
    void start();   ///< Call vTaskStartScheduler()

private:
    Scheduler() = default;
    TaskCommunication m_taskComm;
    TaskSensor        m_taskSensor;
    TaskHeartbeat     m_taskHeartbeat;
};
```

## Constraints
- Verify total stack usage < configTOTAL_HEAP_SIZE at compile time (static_assert)
- Use vTaskDelayUntil for strict periodicity
- Singleton pattern for Scheduler
- Tasks instantiated as static members (no heap)

## Instructions for Claude
1. Generate FreeRTOSConfig.h with all values above
2. Generate scheduler.h/.cpp with Scheduler singleton
3. Add static_assert to verify stack totals
4. Add Doxygen comment on each method
