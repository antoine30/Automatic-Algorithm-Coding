#pragma once

/**
 * @file SpiDriver.h
 * @brief LLR_DRV_002 — SPI driver (implements IDriver).
 *
 * Full-duplex transfers with manual chip-select management.
 * Thread-safe via a FreeRTOS mutex. The CS is always deasserted, even on error.
 */

#include <cstddef>
#include <cstdint>

#include "FreeRTOS.h"
#include "semphr.h"

#include "stm32f4xx_hal.h"

#include "interfaces/IDriver.h"

class SpiDriver : public IDriver
{
public:
    SpiDriver(SPI_HandleTypeDef *hspi, GPIO_TypeDef *csPort, uint16_t csPin);

    DriverStatus init() override;
    DriverStatus reset() override;
    bool isReady() const override;
    const char *getName() const override;

    /// Full-duplex transfer (timeout in ms). CS handled automatically.
    DriverStatus transfer(const uint8_t *txBuf, uint8_t *rxBuf, size_t len,
                          uint32_t timeout_ms);

private:
    /// RAII guard: asserts the CS on construction, deasserts it on destruction.
    class CsGuard
    {
    public:
        CsGuard(GPIO_TypeDef *port, uint16_t pin) : m_port(port), m_pin(pin)
        {
            HAL_GPIO_WritePin(m_port, m_pin, GPIO_PIN_RESET); // CS active (low).
        }
        ~CsGuard()
        {
            HAL_GPIO_WritePin(m_port, m_pin, GPIO_PIN_SET); // CS inactive (high).
        }
        CsGuard(const CsGuard &) = delete;
        CsGuard &operator=(const CsGuard &) = delete;

    private:
        GPIO_TypeDef *m_port;
        uint16_t m_pin;
    };

    SPI_HandleTypeDef *m_hspi;
    GPIO_TypeDef *m_csPort;
    uint16_t m_csPin;
    bool m_initialized;
    SemaphoreHandle_t m_mutex;
    StaticSemaphore_t m_mutexBuffer;
};
