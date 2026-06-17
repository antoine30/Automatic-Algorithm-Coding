#pragma once

/**
 * @file SpiDriver.h
 * @brief LLR_DRV_002 — Driver SPI (implémente IDriver).
 *
 * Transferts full-duplex avec gestion manuelle du chip-select.
 * Thread-safe via mutex FreeRTOS. Le CS est toujours désactivé, même en erreur.
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

    /// Transfert full-duplex (timeout en ms). CS géré automatiquement.
    DriverStatus transfer(const uint8_t *txBuf, uint8_t *rxBuf, size_t len,
                          uint32_t timeout_ms);

private:
    /// Garde RAII : assert le CS à la construction, le désactive à la destruction.
    class CsGuard
    {
    public:
        CsGuard(GPIO_TypeDef *port, uint16_t pin) : m_port(port), m_pin(pin)
        {
            HAL_GPIO_WritePin(m_port, m_pin, GPIO_PIN_RESET); // CS actif (bas).
        }
        ~CsGuard()
        {
            HAL_GPIO_WritePin(m_port, m_pin, GPIO_PIN_SET); // CS inactif (haut).
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
