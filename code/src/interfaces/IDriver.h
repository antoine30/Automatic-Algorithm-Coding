#pragma once

/**
 * @file IDriver.h
 * @brief LLR_ITF_002 — Abstract interface common to all drivers.
 */

#include <cstdint>

/// Return code for driver operations.
enum class DriverStatus : uint8_t
{
    OK = 0,
    ERROR = 1,
    BUSY = 2,
    NOT_INITIALIZED = 3,
    TIMEOUT = 4
};

/**
 * @brief Fully abstract interface that every peripheral driver must implement.
 */
class IDriver
{
public:
    virtual ~IDriver() = default;

    virtual DriverStatus init() = 0;       ///< Initializes the peripheral.
    virtual DriverStatus reset() = 0;      ///< Resets to the initial state.
    virtual bool isReady() const = 0;      ///< @return true if ready.
    virtual const char *getName() const = 0; ///< @return the driver name.
};
