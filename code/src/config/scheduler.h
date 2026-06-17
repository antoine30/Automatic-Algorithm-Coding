#pragma once

/**
 * @file scheduler.h
 * @brief LLR_SCH_001 — Singleton managing the FreeRTOS tasks.
 *
 * NOTE: TaskCommunication (LLR_TSK_002) and TaskHeartbeat (LLR_TSK_004) are
 * instantiated. TaskSensor (LLR_TSK_003) is defined but NOT instantiated: it
 * requires a concrete ISensor implementation, which does not yet have an LLR.
 */

#include "drivers/UartDriver.h"
#include "tasks/TaskCommunication.h"
#include "tasks/TaskHeartbeat.h"

class Scheduler
{
public:
    /// @return the unique scheduler instance.
    static Scheduler &getInstance();

    /// Instantiates/starts the tasks and sends them the INIT event.
    void init();

    /// Starts the scheduler (does not return during normal operation).
    void start();

    Scheduler(const Scheduler &) = delete;
    Scheduler &operator=(const Scheduler &) = delete;

private:
    Scheduler();
};
