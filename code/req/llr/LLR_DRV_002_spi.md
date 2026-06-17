# LLR_DRV_002 — SPI Driver

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_ITF_002, LLR_IOM_001

## Files to Generate
- src/drivers/SpiDriver.h
- src/drivers/SpiDriver.cpp

## Description
SPI driver implementing IDriver.
Handles full-duplex transfers with manual chip select management.

## Class Definition
```cpp
class SpiDriver : public IDriver {
public:
    explicit SpiDriver(SPI_HandleTypeDef* hspi, GPIO_TypeDef* csPort, uint16_t csPin);

    DriverStatus init()          override;
    DriverStatus reset()         override;
    bool         isReady() const override;
    const char*  getName() const override;

    DriverStatus transfer(const uint8_t* txBuf, uint8_t* rxBuf,
                          size_t len, uint32_t timeout_ms);

private:
    SPI_HandleTypeDef* m_hspi;
    GPIO_TypeDef*      m_csPort;
    uint16_t           m_csPin;
    bool               m_initialized;
};
```

## Constraints
- Manual CS management (assert before transfer, deassert after)
- Use HAL_SPI_TransmitReceive for full-duplex
- Thread-safe via FreeRTOS mutex
- HAL_TIMEOUT → return DriverStatus::TIMEOUT
- HAL_ERROR   → return DriverStatus::ERROR
- CS must always be deasserted even on error

## Instructions for Claude
1. Generate SpiDriver.h with the class definition above
2. Generate SpiDriver.cpp with full implementation
3. CS assert/deassert must be in a RAII guard or try/finally pattern
4. Add Doxygen comment on each public method
5. Generate tests/test_spi_driver.cpp with mock HAL
