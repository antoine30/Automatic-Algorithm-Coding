/**
 * @file TaskCommunication.cpp
 * @brief LLR_TSK_002 — Communication task implementation.
 */

#include "tasks/TaskCommunication.h"

// The concrete driver exposes read(buf,len,timeout); we cast from IDriver.
#include "drivers/UartDriver.h"

uint8_t TaskCommunication::s_rxBuffer[256] = {0};

namespace
{
constexpr uint32_t kReadTimeoutMs = 1000; ///< UART read timeout (1 s).
constexpr UBaseType_t kPriority = 3;
constexpr uint32_t kStackWords = 512;
} // namespace

TaskCommunication::TaskCommunication(IDriver &uartDriver)
    : TaskBase("TaskComm", kStackWords, kPriority), m_uart(uartDriver),
      m_rxCount(0), m_running(false)
{
}

const char *TaskCommunication::getName() const
{
    return "TaskComm";
}

TaskStatus TaskCommunication::onInit()
{
    // Initialize the driver and check the connection.
    if (m_uart.init() != DriverStatus::OK)
    {
        return TaskStatus::ERROR;
    }
    if (!m_uart.isReady())
    {
        return TaskStatus::NOT_INITIALIZED;
    }
    m_running = false;
    m_rxCount = 0;
    return TaskStatus::OK;
}

TaskStatus TaskCommunication::onStart()
{
    if (!m_uart.isReady())
    {
        return TaskStatus::NOT_INITIALIZED; // START before INIT.
    }
    m_running = true;

    // Read with a 1000 ms timeout (the UART driver exposes read()).
    auto *uart = static_cast<UartDriver *>(&m_uart);
    DriverStatus st = uart->read(s_rxBuffer, sizeof(s_rxBuffer), kReadTimeoutMs);

    if (st == DriverStatus::TIMEOUT)
    {
        // A timeout does not stop the task: log and continue.
        return TaskStatus::OK;
    }
    if (st == DriverStatus::ERROR)
    {
        // Error: reset the driver then continue.
        m_uart.reset();
        return TaskStatus::OK;
    }

    // Data received: process it.
    ++m_rxCount;
    if (processMessage(s_rxBuffer, sizeof(s_rxBuffer)) != TaskStatus::OK)
    {
        // Invalid message: ignore it (log + discard).
        return TaskStatus::OK;
    }
    return TaskStatus::OK;
}

TaskStatus TaskCommunication::onStop()
{
    if (!m_uart.isReady())
    {
        return TaskStatus::NOT_INITIALIZED;
    }
    m_running = false;
    // Flush the software buffer and log the shutdown.
    for (size_t i = 0; i < sizeof(s_rxBuffer); ++i)
    {
        s_rxBuffer[i] = 0;
    }
    return TaskStatus::OK;
}

TaskStatus TaskCommunication::processMessage(const uint8_t *buf, size_t len)
{
    if (buf == nullptr || len == 0)
    {
        return TaskStatus::ERROR;
    }
    // TODO project: decode the application frame and emit the response.
    return TaskStatus::OK;
}
