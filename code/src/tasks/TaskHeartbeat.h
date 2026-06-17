#pragma once

/**
 * @file TaskHeartbeat.h
 * @brief LLR_TSK_004 — Heartbeat task (status LED blinking), event-driven.
 *
 * Reacts to INIT/START/STOP events via virtual handlers (no switch).
 * The periodicity (500 ms) is provided by a FreeRTOS software timer that posts
 * a START event. Self-contained: depends only on io_mapping (no driver).
 */

#include <cstdint>

#include "tasks/TaskBase.h"

class TaskHeartbeat : public TaskBase
{
public:
    TaskHeartbeat();

    TaskStatus onInit() override;  ///< INIT  : configure the LED, turn it off.
    TaskStatus onStart() override; ///< START : toggle the LED state.
    TaskStatus onStop() override;  ///< STOP  : turn the LED off.
    const char *getName() const override;

    /// @return the number of LED toggles (useful for tests).
    uint32_t toggleCount() const { return m_toggleCount; }

private:
    bool m_ledOn;
    uint32_t m_toggleCount;
};
