#pragma once

/**
 * @file UartDriver.h
 * @brief LLR_DRV_001 — Driver UART (implémente IDriver).
 *
 * Réception pilotée par interruption, émission bloquante avec timeout.
 * Thread-safe via un mutex FreeRTOS. Buffer RX statique (aucune allocation).
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
    /// @param huart Handle HAL de l'UART à piloter.
    explicit UartDriver(UART_HandleTypeDef *huart);

    DriverStatus init() override;
    DriverStatus reset() override;
    bool isReady() const override;
    const char *getName() const override;

    /// Lecture (timeout en ms). @return OK / TIMEOUT / ERROR.
    DriverStatus read(uint8_t *buf, size_t len, uint32_t timeout_ms);

    /// Écriture bloquante. @return OK / TIMEOUT / ERROR.
    DriverStatus write(const uint8_t *buf, size_t len);

private:
    UART_HandleTypeDef *m_huart;
    bool m_initialized;
    SemaphoreHandle_t m_mutex;            ///< Mutex de protection d'accès.
    StaticSemaphore_t m_mutexBuffer;      ///< Stockage statique du mutex.
    static uint8_t s_rxBuffer[256];       ///< Buffer RX statique — no malloc.
};
