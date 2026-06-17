#pragma once

/**
 * @file ISensor.h
 * @brief LLR_ITF_003 — Abstract interface for sensors (extends IDriver).
 */

#include <cstddef>
#include <cstdint>

#include "IDriver.h"

/**
 * @brief Fully abstract interface for sensors: reading + calibration.
 */
class ISensor : public IDriver
{
public:
    virtual ~ISensor() = default;

    /// Reads the sensor data into @p buf (size @p len).
    virtual DriverStatus read(uint8_t *buf, size_t len) = 0;

    /// Starts the calibration procedure.
    virtual DriverStatus calibrate() = 0;

    /// @return true if the sensor is calibrated.
    virtual bool isCalibrated() const = 0;
};
