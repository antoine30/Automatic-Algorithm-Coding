/**
 * @file SpiDriver.cpp
 * @brief LLR_DRV_002 — SPI driver implementation.
 */

#include "drivers/SpiDriver.h"

SpiDriver::SpiDriver(SPI_HandleTypeDef *hspi, GPIO_TypeDef *csPort, uint16_t csPin)
    : m_hspi(hspi), m_csPort(csPort), m_csPin(csPin), m_initialized(false),
      m_mutex(nullptr), m_mutexBuffer{}
{
}

DriverStatus SpiDriver::init()
{
    if (m_hspi == nullptr || m_csPort == nullptr)
    {
        return DriverStatus::ERROR;
    }
    if (m_mutex == nullptr)
    {
        m_mutex = xSemaphoreCreateMutexStatic(&m_mutexBuffer);
        if (m_mutex == nullptr)
        {
            return DriverStatus::ERROR;
        }
    }
    // CS deasserted when idle.
    HAL_GPIO_WritePin(m_csPort, m_csPin, GPIO_PIN_SET);
    m_initialized = true;
    return DriverStatus::OK;
}

DriverStatus SpiDriver::reset()
{
    if (m_hspi == nullptr)
    {
        return DriverStatus::ERROR;
    }
    HAL_SPI_Abort(m_hspi);
    m_initialized = false;
    return init();
}

bool SpiDriver::isReady() const
{
    return m_initialized && m_hspi != nullptr;
}

const char *SpiDriver::getName() const
{
    return "SPI1";
}

DriverStatus SpiDriver::transfer(const uint8_t *txBuf, uint8_t *rxBuf, size_t len,
                                 uint32_t timeout_ms)
{
    if (!isReady())
    {
        return DriverStatus::NOT_INITIALIZED;
    }
    if (txBuf == nullptr || rxBuf == nullptr || len == 0)
    {
        return DriverStatus::ERROR;
    }

    if (xSemaphoreTake(m_mutex, pdMS_TO_TICKS(timeout_ms)) != pdTRUE)
    {
        return DriverStatus::TIMEOUT;
    }

    DriverStatus result = DriverStatus::OK;
    {
        // CsGuard guarantees the CS is deasserted even on error (RAII).
        CsGuard cs(m_csPort, m_csPin);
        HAL_StatusTypeDef hal = HAL_SPI_TransmitReceive(
            m_hspi, const_cast<uint8_t *>(txBuf), rxBuf,
            static_cast<uint16_t>(len), timeout_ms);

        if (hal == HAL_TIMEOUT)
        {
            result = DriverStatus::TIMEOUT;
        }
        else if (hal != HAL_OK)
        {
            result = DriverStatus::ERROR;
        }
    } // CS deasserted here.

    xSemaphoreGive(m_mutex);
    return result;
}
