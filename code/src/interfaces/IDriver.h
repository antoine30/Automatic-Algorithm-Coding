#pragma once

/**
 * @file IDriver.h
 * @brief LLR_ITF_002 — Interface abstraite commune à tous les drivers.
 */

#include <cstdint>

/// Code de retour des opérations driver.
enum class DriverStatus : uint8_t
{
    OK = 0,
    ERROR = 1,
    BUSY = 2,
    NOT_INITIALIZED = 3,
    TIMEOUT = 4
};

/**
 * @brief Interface 100% abstraite que tout driver périphérique doit implémenter.
 */
class IDriver
{
public:
    virtual ~IDriver() = default;

    virtual DriverStatus init() = 0;       ///< Initialise le périphérique.
    virtual DriverStatus reset() = 0;      ///< Remet dans l'état initial.
    virtual bool isReady() const = 0;      ///< @return true si prêt.
    virtual const char *getName() const = 0; ///< @return le nom du driver.
};
