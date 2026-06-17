/**
 * @file TaskHeartbeat.cpp
 * @brief LLR_TSK_004 — Heartbeat task implementation.
 */

#include "tasks/TaskHeartbeat.h"

#include "config/io_mapping.h"
#include "stm32f4xx_hal.h"

namespace
{
constexpr UBaseType_t kPriority = 1;
constexpr uint32_t kStackWords = 128;
} // namespace

TaskHeartbeat::TaskHeartbeat()
    : TaskBase("TaskHeartbeat", kStackWords, kPriority), m_ledOn(false),
      m_toggleCount(0)
{
}

const char *TaskHeartbeat::getName() const
{
    return "TaskHeartbeat";
}

TaskStatus TaskHeartbeat::onInit()
{
    // Configure the LED pin as push-pull output and turn it off.
    GPIO_InitTypeDef init = {};
    init.Pin = io::gpio::kLedStatus.pin;
    init.Mode = GPIO_MODE_OUTPUT_PP;
    init.Pull = GPIO_NOPULL;
    init.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(io::gpio::kLedStatus.port, &init);

    HAL_GPIO_WritePin(io::gpio::kLedStatus.port, io::gpio::kLedStatus.pin,
                      GPIO_PIN_RESET);
    m_ledOn = false;
    m_toggleCount = 0;
    return TaskStatus::OK;
}

TaskStatus TaskHeartbeat::onStart()
{
    // Toggle the LED state on every period tick.
    HAL_GPIO_TogglePin(io::gpio::kLedStatus.port, io::gpio::kLedStatus.pin);
    m_ledOn = !m_ledOn;
    ++m_toggleCount;
    return TaskStatus::OK;
}

TaskStatus TaskHeartbeat::onStop()
{
    HAL_GPIO_WritePin(io::gpio::kLedStatus.port, io::gpio::kLedStatus.pin,
                      GPIO_PIN_RESET);
    m_ledOn = false;
    return TaskStatus::OK;
}
