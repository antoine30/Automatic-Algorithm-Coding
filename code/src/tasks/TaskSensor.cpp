/**
 * @file TaskSensor.cpp
 * @brief LLR_TSK_003 — Implémentation de la tâche capteur.
 */

#include "tasks/TaskSensor.h"

uint8_t TaskSensor::s_sample[32] = {0};

namespace
{
constexpr UBaseType_t kPriority = 2;
constexpr uint32_t kStackWords = 256;
} // namespace

TaskSensor::TaskSensor(ISensor &sensor)
    : TaskBase("TaskSensor", kStackWords, kPriority), m_sensor(sensor),
      m_sampleCount(0), m_running(false)
{
}

const char *TaskSensor::getName() const
{
    return "TaskSensor";
}

TaskStatus TaskSensor::onInit()
{
    if (m_sensor.init() != DriverStatus::OK)
    {
        return TaskStatus::ERROR;
    }
    if (m_sensor.calibrate() != DriverStatus::OK)
    {
        return TaskStatus::ERROR;
    }
    if (!m_sensor.isCalibrated())
    {
        return TaskStatus::NOT_INITIALIZED;
    }
    m_running = false;
    m_sampleCount = 0;
    return TaskStatus::OK;
}

TaskStatus TaskSensor::onStart()
{
    if (!m_sensor.isReady() || !m_sensor.isCalibrated())
    {
        return TaskStatus::NOT_INITIALIZED; // START avant INIT/calibration.
    }
    m_running = true;

    DriverStatus st = m_sensor.read(s_sample, sizeof(s_sample));
    if (st == DriverStatus::TIMEOUT)
    {
        // Timeout : on log et on continue (la tâche ne s'arrête pas).
        return TaskStatus::OK;
    }
    if (st != DriverStatus::OK)
    {
        return TaskStatus::ERROR;
    }

    ++m_sampleCount;
    return TaskStatus::OK;
}

TaskStatus TaskSensor::onStop()
{
    m_running = false;
    return TaskStatus::OK;
}
