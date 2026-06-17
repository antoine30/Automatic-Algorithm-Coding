# LLR_TSK_003 — TaskSensor

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_TSK_001, LLR_ITF_003, LLR_ITF_004

## Files to Generate
- src/tasks/TaskSensor.h
- src/tasks/TaskSensor.cpp

## Description
Event-driven FreeRTOS task that periodically reads a sensor (ISensor).
Reacts to INIT / START / STOP through virtual handlers (no switch). Periodicity
(50 ms) is provided by a FreeRTOS software timer posting a START event.

## Class Definition
```cpp
class TaskSensor : public TaskBase {
public:
    explicit TaskSensor(ISensor& sensor);

    TaskStatus onInit()  override; ///< INIT  : init sensor + calibrate
    TaskStatus onStart() override; ///< START : read one sample
    TaskStatus onStop()  override; ///< STOP  : mark idle
    const char* getName() const override;

    uint32_t sampleCount() const; ///< Number of samples acquired (tests)

private:
    ISensor&       m_sensor;
    static uint8_t s_sample[32]; ///< Static sample buffer — no malloc
    uint32_t       m_sampleCount;
    bool           m_running;
};
```

## Behavior
- onInit()  : m_sensor.init(); if OK m_sensor.calibrate(); verify isCalibrated()
- onStart() : if calibrated, m_sensor.read(s_sample, sizeof) → ++m_sampleCount
- onStop()  : m_running = false

## Constraints
- Stack : 256 words, Priority : 2, Period : 50 ms (software timer posts START)
- Static sample buffer — no dynamic allocation
- React via virtual handlers only — **no switch/case**
- TIMEOUT on read → log + continue (return OK)

## Instructions for Claude
1. Generate TaskSensor.h with the class definition above
2. Generate TaskSensor.cpp implementing the 3 handlers
3. Inject ISensor by reference (dependency injection)
4. Add Doxygen comment on each method
5. Generate tests/test_task_sensor.cpp with a mock ISensor
