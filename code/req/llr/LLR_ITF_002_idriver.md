# LLR_ITF_002 — IDriver Interface

## Level : LOW LEVEL
## Parent HLR : HLR_001

## Files to Generate
- src/interfaces/IDriver.h

## Description
Pure abstract interface that all peripheral drivers must implement.
Defines driver lifecycle: init, reset, and readiness check.

## Interface Definition
```cpp
class IDriver {
public:
    virtual ~IDriver() = default;
    virtual DriverStatus init()          = 0; ///< Initialize the peripheral
    virtual DriverStatus reset()         = 0; ///< Reset to initial state
    virtual bool         isReady() const = 0; ///< Returns true if ready
    virtual const char*  getName() const = 0; ///< Returns driver name
};
```

## DriverStatus Enum
```cpp
enum class DriverStatus : uint8_t {
    OK              = 0,
    ERROR           = 1,
    BUSY            = 2,
    NOT_INITIALIZED = 3,
    TIMEOUT         = 4
};
```

## Constraints
- 100% abstract class — no attributes, no implementation
- Virtual destructor mandatory
- All methods must be pure virtual (= 0)
- Header-only file (no .cpp)

## Instructions for Claude
1. Generate IDriver.h with the interface and DriverStatus enum
2. Add include guards (#pragma once)
3. Add Doxygen comment on each method
4. Do not add any attributes or non-virtual methods
