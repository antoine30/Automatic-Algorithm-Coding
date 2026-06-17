#pragma once

/**
 * @file UartDriver.h
 * @brief LLR_DRV_001 — UART driver (implements IDriver).
 *
 * Interrupt-driven reception, blocking transmission with timeout.
 * Thread-safe via a FreeRTOS mutex. Static RX buffer (no allocation).
 */

#include <cstddef>
#include <cstdint>

#include "FreeRTOS.h"
#include "semphr.h"

#include "stm32f4xx_hal.h"

#include "interfaces/IDriver.h"

class UartDriver : public IDriver
{
public:
    /// @param huart HAL handle of the UART to drive.
    explicit UartDriver(UART_HandleTypeDef *huart);

    DriverStatus init() override;
    DriverStatus reset() override;
    bool isReady() const override;
    const char *getName() const override;

    /// Read (timeout in ms). @return OK / TIMEOUT / ERROR.
    DriverStatus read(uint8_t *buf, size_t len, uint32_t timeout_ms);

    /// Blocking write. @return OK / TIMEOUT / ERROR.
    DriverStatus write(const uint8_t *buf, size_t len);

private:
    UART_HandleTypeDef *m_huart;
    bool m_initialized;
    SemaphoreHandle_t m_mutex;            ///< Access protection mutex.
    StaticSemaphore_t m_mutexBuffer;      ///< Static storage for the mutex.
    static uint8_t s_rxBuffer[256];       ///< Static RX buffer — no malloc.
};
