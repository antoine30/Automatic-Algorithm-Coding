/**
 * @file test_drivers.cpp
 * @brief Host tests for the UART/SPI/I2C drivers via the HAL shim (test/shim).
 *
 * Verifies: HAL status mapping -> DriverStatus, guard against use before init,
 * systematic CS deassertion on SPI (RAII), and I2C bus recovery after
 * consecutive errors.
 */

#include "stm32f4xx_hal.h" // shim + g_hal mock

#include "drivers/I2cDriver.h"
#include "drivers/SpiDriver.h"
#include "drivers/UartDriver.h"

#include <cstdio>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do                                                                         \
    {                                                                          \
        ++g_checks;                                                            \
        if (!(cond))                                                           \
        {                                                                      \
            ++g_failures;                                                      \
            std::printf("  [FAIL] %s:%d  %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                      \
    } while (0)

// --- UART ------------------------------------------------------------------
static void test_uart()
{
    g_hal.reset();
    UART_HandleTypeDef huart{};
    UartDriver uart(&huart);

    // null init -> ERROR.
    UartDriver bad(nullptr);
    CHECK(bad.init() == DriverStatus::ERROR);

    // Read before init -> NOT_INITIALIZED.
    uint8_t buf[8] = {0};
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::NOT_INITIALIZED);

    // init OK.
    CHECK(uart.init() == DriverStatus::OK);
    CHECK(uart.isReady());
    CHECK(g_hal.uartReceiveItCalls == 1);

    // Read OK: buffer filled by the mock.
    g_hal.rxFillByte = 0x5A;
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::OK);
    CHECK(buf[0] == 0x5A);

    // Injected timeout / error.
    g_hal.uartReceiveStatus = HAL_TIMEOUT;
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::TIMEOUT);
    g_hal.uartReceiveStatus = HAL_ERROR;
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::ERROR);

    // Write OK then error.
    const uint8_t msg[3] = {1, 2, 3};
    g_hal.uartTransmitStatus = HAL_OK;
    CHECK(uart.write(msg, sizeof(msg)) == DriverStatus::OK);
    g_hal.uartTransmitStatus = HAL_ERROR;
    CHECK(uart.write(msg, sizeof(msg)) == DriverStatus::ERROR);

    // reset -> abort + re-init.
    CHECK(uart.reset() == DriverStatus::OK);
    CHECK(g_hal.uartAbortCalls == 1);
}

// --- SPI -------------------------------------------------------------------
static void test_spi()
{
    g_hal.reset();
    SPI_HandleTypeDef hspi{};
    GPIO_TypeDef csPort{};
    SpiDriver spi(&hspi, &csPort, GPIO_PIN_6);

    uint8_t tx[4] = {1, 2, 3, 4};
    uint8_t rx[4] = {0};

    // Transfer before init -> NOT_INITIALIZED.
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::NOT_INITIALIZED);

    // init: CS set to idle (high).
    CHECK(spi.init() == DriverStatus::OK);
    CHECK(g_hal.lastGpioState == GPIO_PIN_SET);

    // Transfer OK: CS deasserted again afterwards (RAII).
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::OK);
    CHECK(g_hal.spiTransferCalls == 1);
    CHECK(g_hal.lastGpioState == GPIO_PIN_SET); // CS deasserted.

    // Transfer in error: CS MUST still be deasserted.
    g_hal.spiTransferStatus = HAL_ERROR;
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::ERROR);
    CHECK(g_hal.lastGpioState == GPIO_PIN_SET); // guaranteed by CsGuard.

    // Injected timeout.
    g_hal.spiTransferStatus = HAL_TIMEOUT;
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::TIMEOUT);
}

// --- I2C -------------------------------------------------------------------
static void test_i2c()
{
    g_hal.reset();
    I2C_HandleTypeDef hi2c{};
    I2cDriver i2c(&hi2c);

    uint8_t buf[4] = {0};

    // Before init.
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::NOT_INITIALIZED);

    CHECK(i2c.init() == DriverStatus::OK);
    CHECK(i2c.isReady());

    // Write / read OK.
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::OK);
    CHECK(i2c.read(0x50, buf, sizeof(buf), 100) == DriverStatus::OK);

    // Timeout.
    g_hal.i2cTxStatus = HAL_TIMEOUT;
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::TIMEOUT);

    // Bus recovery: 3 consecutive errors -> reset (DeInit + Init).
    g_hal.i2cTxStatus = HAL_ERROR;
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::ERROR);
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::ERROR);
    CHECK(g_hal.i2cDeInitCalls == 0); // not yet.
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::ERROR);
    CHECK(g_hal.i2cDeInitCalls == 1); // recovery triggered on the 3rd failure.
    CHECK(g_hal.i2cInitCalls == 1);
}

int main()
{
    std::printf("Running driver unit tests (with HAL shim)...\n");

    test_uart();
    test_spi();
    test_i2c();

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
