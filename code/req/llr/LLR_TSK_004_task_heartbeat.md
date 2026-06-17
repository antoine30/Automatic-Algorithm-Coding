# LLR_TSK_004 — TaskHeartbeat

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_TSK_001, LLR_IOM_001, LLR_ITF_004

## Files to Generate
- src/tasks/TaskHeartbeat.h
- src/tasks/TaskHeartbeat.cpp

## Description
Event-driven FreeRTOS task that blinks the status LED (LED_STATUS, GPIOA5).
Reacts to INIT / START / STOP through virtual handlers (no switch). Periodicity
(500 ms) is provided by a FreeRTOS software timer posting a START event.

## Class Definition
```cpp
class TaskHeartbeat : public TaskBase {
public:
    TaskHeartbeat();

    TaskStatus onInit()  override; ///< INIT  : configure LED GPIO, LED off
    TaskStatus onStart() override; ///< START : toggle LED
    TaskStatus onStop()  override; ///< STOP  : LED off
    const char* getName() const override;

    uint32_t toggleCount() const; ///< Number of toggles (tests)

private:
    bool     m_ledOn;
    uint32_t m_toggleCount;
};
```

## Behavior
- onInit()  : configure LED_STATUS as output, drive it low, m_ledOn = false
- onStart() : invert LED state (HAL_GPIO_TogglePin), ++m_toggleCount
- onStop()  : drive LED low, m_ledOn = false

## Constraints
- Stack : 128 words, Priority : 1, Period : 500 ms (software timer posts START)
- No dynamic allocation
- React via virtual handlers only — **no switch/case**
- Self-contained : depends only on io_mapping (no external driver)

## Instructions for Claude
1. Generate TaskHeartbeat.h with the class definition above
2. Generate TaskHeartbeat.cpp implementing the 3 handlers
3. Use io_mapping.h for the LED pin (no magic numbers)
4. Add Doxygen comment on each method
5. Generate tests/test_task_heartbeat.cpp
