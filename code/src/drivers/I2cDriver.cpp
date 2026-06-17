/**
 * @file I2cDriver.cpp
 * @brief LLR_DRV_003 — Implémentation du driver I2C.
 */

#include "drivers/I2cDriver.h"

namespace
{
/// Au-delà de ce nombre d'erreurs consécutives, on tente une récupération de bus.
constexpr uint8_t kMaxConsecutiveErrors = 3;
} // namespace

I2cDriver::I2cDriver(I2C_HandleTypeDef *hi2c)
    : m_hi2c(hi2c), m_initialized(false), m_consecutiveErrors(0), m_mutex(nullptr),
      m_mutexBuffer{}
{
}

DriverStatus I2cDriver::init()
{
    if (m_hi2c == nullptr)
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
    m_consecutiveErrors = 0;
    m_initialized = true;
    return DriverStatus::OK;
}

DriverStatus I2cDriver::reset()
{
    if (m_hi2c == nullptr)
    {
        return DriverStatus::ERROR;
    }
    // Récupération de bus : ré-initialisation complète du périphérique I2C.
    HAL_I2C_DeInit(m_hi2c);
    if (HAL_I2C_Init(m_hi2c) != HAL_OK)
    {
        m_initialized = false;
        return DriverStatus::ERROR;
    }
    m_consecutiveErrors = 0;
    m_initialized = true;
    return DriverStatus::OK;
}

bool I2cDriver::isReady() const
{
    return m_initialized && m_hi2c != nullptr;
}

const char *I2cDriver::getName() const
{
    return "I2C1";
}

DriverStatus I2cDriver::mapStatus(HAL_StatusTypeDef hal)
{
    if (hal == HAL_OK)
    {
        m_consecutiveErrors = 0;
        return DriverStatus::OK;
    }
    if (hal == HAL_TIMEOUT)
    {
        return DriverStatus::TIMEOUT;
    }

    // Erreur : on incrémente et on tente une récupération de bus si nécessaire.
    if (m_consecutiveErrors < kMaxConsecutiveErrors)
    {
        ++m_consecutiveErrors;
    }
    if (m_consecutiveErrors >= kMaxConsecutiveErrors)
    {
        reset(); // Récupération de bus.
    }
    return DriverStatus::ERROR;
}

DriverStatus I2cDriver::write(uint8_t devAddr, const uint8_t *buf, size_t len,
                              uint32_t timeout_ms)
{
    if (!isReady())
    {
        return DriverStatus::NOT_INITIALIZED;
    }
    if (buf == nullptr || len == 0)
    {
        return DriverStatus::ERROR;
    }

    if (xSemaphoreTake(m_mutex, pdMS_TO_TICKS(timeout_ms)) != pdTRUE)
    {
        return DriverStatus::TIMEOUT;
    }
    HAL_StatusTypeDef hal = HAL_I2C_Master_Transmit(
        m_hi2c, devAddr, const_cast<uint8_t *>(buf),
        static_cast<uint16_t>(len), timeout_ms);
    DriverStatus result = mapStatus(hal);
    xSemaphoreGive(m_mutex);
    return result;
}

DriverStatus I2cDriver::read(uint8_t devAddr, uint8_t *buf, size_t len,
                             uint32_t timeout_ms)
{
    if (!isReady())
    {
        return DriverStatus::NOT_INITIALIZED;
    }
    if (buf == nullptr || len == 0)
    {
        return DriverStatus::ERROR;
    }

    if (xSemaphoreTake(m_mutex, pdMS_TO_TICKS(timeout_ms)) != pdTRUE)
    {
        return DriverStatus::TIMEOUT;
    }
    HAL_StatusTypeDef hal = HAL_I2C_Master_Receive(
        m_hi2c, devAddr, buf, static_cast<uint16_t>(len), timeout_ms);
    DriverStatus result = mapStatus(hal);
    xSemaphoreGive(m_mutex);
    return result;
}
