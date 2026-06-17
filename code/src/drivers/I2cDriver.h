#pragma once

/**
 * @file I2cDriver.h
 * @brief LLR_DRV_003 — Driver I2C (implémente IDriver).
 *
 * Lectures/écritures maître vers des esclaves adressés.
 * Thread-safe via mutex FreeRTOS. Récupération de bus en cas d'erreurs répétées.
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

    /// Écriture vers @p devAddr (adresse 8 bits déjà décalée).
    DriverStatus write(uint8_t devAddr, const uint8_t *buf, size_t len,
                       uint32_t timeout_ms);

    /// Lecture depuis @p devAddr (adresse 8 bits déjà décalée).
    DriverStatus read(uint8_t devAddr, uint8_t *buf, size_t len,
                      uint32_t timeout_ms);

private:
    I2C_HandleTypeDef *m_hi2c;
    bool m_initialized;
    uint8_t m_consecutiveErrors;         ///< Compteur pour la récupération de bus.
    SemaphoreHandle_t m_mutex;
    StaticSemaphore_t m_mutexBuffer;

    /// Convertit un statut HAL en DriverStatus et gère le compteur d'erreurs.
    DriverStatus mapStatus(HAL_StatusTypeDef hal);
};
