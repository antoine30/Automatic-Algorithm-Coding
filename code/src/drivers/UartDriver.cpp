/**
 * @file UartDriver.cpp
 * @brief LLR_DRV_001 — UART driver implementation.
 */

#include "drivers/UartDriver.h"

uint8_t UartDriver::s_rxBuffer[256] = {0};

UartDriver::UartDriver(UART_HandleTypeDef *huart)
    : m_huart(huart), m_initialized(false), m_mutex(nullptr), m_mutexBuffer{}
{
}

DriverStatus UartDriver::init()
{
    if (m_huart == nullptr)
    {
        return DriverStatus::ERROR;
    }

    // Static creation of the mutex (no dynamic allocation).
    if (m_mutex == nullptr)
    {
        m_mutex = xSemaphoreCreateMutexStatic(&m_mutexBuffer);
        if (m_mutex == nullptr)
        {
            return DriverStatus::ERROR;
        }
    }

    // Arm interrupt-driven reception on the static buffer.
    if (HAL_UART_Receive_IT(m_huart, s_rxBuffer, sizeof(s_rxBuffer)) != HAL_OK)
    {
        return DriverStatus::ERROR;
    }

    m_initialized = true;
    return DriverStatus::OK;
}

DriverStatus UartDriver::reset()
{
    if (m_huart == nullptr)
    {
        return DriverStatus::ERROR;
    }
    HAL_UART_Abort(m_huart);
    m_initialized = false;
    return init();
}

bool UartDriver::isReady() const
{
    return m_initialized && m_huart != nullptr;
}

const char *UartDriver::getName() const
{
    return "UART1";
}

DriverStatus UartDriver::read(uint8_t *buf, size_t len, uint32_t timeout_ms)
{
    if (!isReady())
    {
        return DriverStatus::NOT_INITIALIZED;
    }
    if (buf == nullptr || len == 0)
    {
        return DriverStatus::ERROR;
    }

    // Critical section protected by the mutex.
    if (xSemaphoreTake(m_mutex, pdMS_TO_TICKS(timeout_ms)) != pdTRUE)
    {
        return DriverStatus::TIMEOUT;
    }

    HAL_StatusTypeDef hal = HAL_UART_Receive(m_huart, buf, static_cast<uint16_t>(len), timeout_ms);
    xSemaphoreGive(m_mutex);

    if (hal == HAL_TIMEOUT)
    {
        return DriverStatus::TIMEOUT;
    }
    if (hal != HAL_OK)
    {
        return DriverStatus::ERROR;
    }
    return DriverStatus::OK;
}

DriverStatus UartDriver::write(const uint8_t *buf, size_t len)
{
    if (!isReady())
    {
        return DriverStatus::NOT_INITIALIZED;
    }
    if (buf == nullptr || len == 0)
    {
        return DriverStatus::ERROR;
    }

    if (xSemaphoreTake(m_mutex, portMAX_DELAY) != pdTRUE)
    {
        return DriverStatus::TIMEOUT;
    }

    // Blocking transmission (HAL timeout set to 1000 ms).
    HAL_StatusTypeDef hal = HAL_UART_Transmit(
        m_huart, const_cast<uint8_t *>(buf), static_cast<uint16_t>(len), 1000);
    xSemaphoreGive(m_mutex);

    if (hal == HAL_TIMEOUT)
    {
        return DriverStatus::TIMEOUT;
    }
    if (hal != HAL_OK)
    {
        return DriverStatus::ERROR;
    }
    return DriverStatus::OK;
}
