# LLR_DRV_003 — I2C Driver

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_ITF_002, LLR_IOM_001

## Files to Generate
- src/drivers/I2cDriver.h
- src/drivers/I2cDriver.cpp

## Description
I2C driver implementing IDriver.
Handles master read/write to addressed slave devices.

## Class Definition
```cpp
class I2cDriver : public IDriver {
public:
    explicit I2cDriver(I2C_HandleTypeDef* hi2c);

    DriverStatus init()          override;
    DriverStatus reset()         override;
    bool         isReady() const override;
    const char*  getName() const override;

    DriverStatus write(uint8_t devAddr, const uint8_t* buf,
                       size_t len, uint32_t timeout_ms);
    DriverStatus read (uint8_t devAddr, uint8_t* buf,
                       size_t len, uint32_t timeout_ms);

private:
    I2C_HandleTypeDef* m_hi2c;
    bool               m_initialized;
};
```

## Constraints
- Use HAL_I2C_Master_Transmit / HAL_I2C_Master_Receive
- Device address passed as 8-bit (already shifted)
- Thread-safe via FreeRTOS mutex
- HAL_TIMEOUT → return DriverStatus::TIMEOUT
- HAL_ERROR   → return DriverStatus::ERROR
- Bus recovery (reset) on consecutive errors

## Instructions for Claude
1. Generate I2cDriver.h with the class definition above
2. Generate I2cDriver.cpp with full implementation
3. Add bus recovery logic in reset() method
4. Add Doxygen comment on each public method
5. Generate tests/test_i2c_driver.cpp with mock HAL
