#pragma once

/**
 * @file I2cDriver.h
 * @brief LLR_DRV_003 — I2C driver (implements IDriver).
 *
 * Master reads/writes to addressed slaves.
 * Thread-safe via a FreeRTOS mutex. Bus recovery on repeated errors.
 */

#include <cstddef>
#include <cstdint>

#include "FreeRTOS.h"
#include "semphr.h"

#include "stm32f4xx_hal.h"

#include "interfaces/IDriver.h"

class I2cDriver : public IDriver
{
public:
    explicit I2cDriver(I2C_HandleTypeDef *hi2c);

    DriverStatus init() override;
    DriverStatus reset() override;
    bool isReady() const override;
    const char *getName() const override;

    /// Write to @p devAddr (8-bit address, already shifted).
    DriverStatus write(uint8_t devAddr, const uint8_t *buf, size_t len,
                       uint32_t timeout_ms);

    /// Read from @p devAddr (8-bit address, already shifted).
    DriverStatus read(uint8_t devAddr, uint8_t *buf, size_t len,
                      uint32_t timeout_ms);

private:
    I2C_HandleTypeDef *m_hi2c;
    bool m_initialized;
    uint8_t m_consecutiveErrors;         ///< Counter for bus recovery.
    SemaphoreHandle_t m_mutex;
    StaticSemaphore_t m_mutexBuffer;

    /// Converts a HAL status to DriverStatus and manages the error counter.
    DriverStatus mapStatus(HAL_StatusTypeDef hal);
};
