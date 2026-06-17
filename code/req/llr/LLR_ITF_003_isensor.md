# LLR_ITF_003 — ISensor Interface

## Level : LOW LEVEL
## Parent HLR : HLR_001

## Files to Generate
- src/interfaces/ISensor.h

## Description
Pure abstract interface for all sensor drivers.
Extends IDriver with read and calibration capabilities.

## Interface Definition
```cpp
class ISensor : public IDriver {
public:
    virtual ~ISensor() = default;
    virtual DriverStatus read(uint8_t* buf, size_t len)  = 0; ///< Read sensor data
    virtual DriverStatus calibrate()                     = 0; ///< Run calibration
    virtual bool         isCalibrated() const            = 0; ///< Calibration status
};
```

## Constraints
- Inherits from IDriver
- 100% abstract — no attributes, no implementation
- Virtual destructor mandatory
- Header-only file (no .cpp)

## Instructions for Claude
1. Generate ISensor.h inheriting from IDriver
2. Add include guards (#pragma once)
3. Include IDriver.h
4. Add Doxygen comment on each method
