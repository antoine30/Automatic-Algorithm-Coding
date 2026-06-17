#pragma once

/**
 * @file ISensor.h
 * @brief LLR_ITF_003 — Interface abstraite des capteurs (étend IDriver).
 */

#include <cstddef>
#include <cstdint>

#include "IDriver.h"

/**
 * @brief Interface 100% abstraite pour les capteurs : lecture + calibration.
 */
class ISensor : public IDriver
{
public:
    virtual ~ISensor() = default;

    /// Lit les données du capteur dans @p buf (taille @p len).
    virtual DriverStatus read(uint8_t *buf, size_t len) = 0;

    /// Lance la procédure de calibration.
    virtual DriverStatus calibrate() = 0;

    /// @return true si le capteur est calibré.
    virtual bool isCalibrated() const = 0;
};
