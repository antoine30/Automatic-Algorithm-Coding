#pragma once

/**
 * @file TaskSensor.h
 * @brief LLR_TSK_003 — Event-driven sensor task.
 *
 * Periodically reads a sensor (ISensor). Reacts to INIT/START/STOP events
 * via virtual handlers (no switch). The periodicity (50 ms) is provided by
 * a FreeRTOS software timer that posts a START event.
 */

#include <cstddef>
#include <cstdint>

#include "interfaces/ISensor.h"
#include "tasks/TaskBase.h"

class TaskSensor : public TaskBase
{
public:
    /// @param sensor Sensor injected by reference (dependency injection).
    explicit TaskSensor(ISensor &sensor);

    TaskStatus onInit() override;  ///< INIT  : init + sensor calibration.
    TaskStatus onStart() override; ///< START : acquire a sample.
    TaskStatus onStop() override;  ///< STOP  : switch to idle.
    const char *getName() const override;

    /// @return the number of acquired samples (useful for tests).
    uint32_t sampleCount() const { return m_sampleCount; }

private:
    ISensor &m_sensor;
    static uint8_t s_sample[32]; ///< Static sample buffer — no malloc.
    uint32_t m_sampleCount;
    bool m_running;
};
