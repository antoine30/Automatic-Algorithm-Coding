# LLR_DRV_001 — UART Driver

## Level : LOW LEVEL
## Parent HLR : HLR_001
## Depends on : LLR_ITF_002, LLR_IOM_001

## Files to Generate
- src/drivers/UartDriver.h
- src/drivers/UartDriver.cpp

## Description
UART driver implementing IDriver.
Handles interrupt-driven receive and blocking transmit.

## Class Definition
```cpp
class UartDriver : public IDriver {
public:
    explicit UartDriver(UART_HandleTypeDef* huart);

    DriverStatus init()                                              override;
    DriverStatus reset()                                             override;
    bool         isReady()                               const       override;
    const char*  getName()                               const       override;

    DriverStatus read (uint8_t* buf, size_t len, uint32_t timeout_ms);
    DriverStatus write(const uint8_t* buf, size_t len);

private:
    UART_HandleTypeDef* m_huart;
    bool                m_initialized;
    static uint8_t      s_rxBuffer[256]; ///< Static RX buffer — no malloc
};
```

## Constraints
- Static RX buffer of 256 bytes — no dynamic allocation
- Use HAL_UART_Receive_IT for reception
- Use HAL_UART_Transmit for transmission (blocking with timeout)
- Thread-safe via FreeRTOS mutex (osMutexId_t)
- HAL_TIMEOUT  → return DriverStatus::TIMEOUT
- HAL_ERROR    → return DriverStatus::ERROR
- Log errors via debug UART if available

## Instructions for Claude
1. Generate UartDriver.h with the class definition above
2. Generate UartDriver.cpp with full implementation
3. Add Doxygen comment on each public method
4. Implement mutex acquire/release around read and write
5. Generate tests/test_uart_driver.cpp with mock HAL
