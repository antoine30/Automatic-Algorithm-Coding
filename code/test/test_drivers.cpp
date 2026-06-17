/**
 * @file test_drivers.cpp
 * @brief Tests hôte des drivers UART/SPI/I2C via le shim HAL (test/shim).
 *
 * Vérifie : mapping des statuts HAL → DriverStatus, garde anti-usage avant init,
 * désactivation systématique du CS en SPI (RAII), et recovery de bus I2C après
 * erreurs consécutives.
 */

#include "stm32f4xx_hal.h" // shim + mock g_hal

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

    // init nul → ERROR.
    UartDriver bad(nullptr);
    CHECK(bad.init() == DriverStatus::ERROR);

    // Lecture avant init → NOT_INITIALIZED.
    uint8_t buf[8] = {0};
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::NOT_INITIALIZED);

    // init OK.
    CHECK(uart.init() == DriverStatus::OK);
    CHECK(uart.isReady());
    CHECK(g_hal.uartReceiveItCalls == 1);

    // Lecture OK : buffer rempli par le mock.
    g_hal.rxFillByte = 0x5A;
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::OK);
    CHECK(buf[0] == 0x5A);

    // Timeout / erreur injectés.
    g_hal.uartReceiveStatus = HAL_TIMEOUT;
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::TIMEOUT);
    g_hal.uartReceiveStatus = HAL_ERROR;
    CHECK(uart.read(buf, sizeof(buf), 100) == DriverStatus::ERROR);

    // Écriture OK puis erreur.
    const uint8_t msg[3] = {1, 2, 3};
    g_hal.uartTransmitStatus = HAL_OK;
    CHECK(uart.write(msg, sizeof(msg)) == DriverStatus::OK);
    g_hal.uartTransmitStatus = HAL_ERROR;
    CHECK(uart.write(msg, sizeof(msg)) == DriverStatus::ERROR);

    // reset → abort + ré-init.
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

    // Transfert avant init → NOT_INITIALIZED.
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::NOT_INITIALIZED);

    // init : CS positionné au repos (haut).
    CHECK(spi.init() == DriverStatus::OK);
    CHECK(g_hal.lastGpioState == GPIO_PIN_SET);

    // Transfert OK : CS de nouveau désactivé après coup (RAII).
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::OK);
    CHECK(g_hal.spiTransferCalls == 1);
    CHECK(g_hal.lastGpioState == GPIO_PIN_SET); // CS désactivé.

    // Transfert en erreur : CS DOIT quand même être désactivé.
    g_hal.spiTransferStatus = HAL_ERROR;
    CHECK(spi.transfer(tx, rx, 4, 100) == DriverStatus::ERROR);
    CHECK(g_hal.lastGpioState == GPIO_PIN_SET); // garanti par CsGuard.

    // Timeout injecté.
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

    // Avant init.
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::NOT_INITIALIZED);

    CHECK(i2c.init() == DriverStatus::OK);
    CHECK(i2c.isReady());

    // Écriture / lecture OK.
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::OK);
    CHECK(i2c.read(0x50, buf, sizeof(buf), 100) == DriverStatus::OK);

    // Timeout.
    g_hal.i2cTxStatus = HAL_TIMEOUT;
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::TIMEOUT);

    // Recovery de bus : 3 erreurs consécutives → reset (DeInit + Init).
    g_hal.i2cTxStatus = HAL_ERROR;
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::ERROR);
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::ERROR);
    CHECK(g_hal.i2cDeInitCalls == 0); // pas encore.
    CHECK(i2c.write(0x50, buf, sizeof(buf), 100) == DriverStatus::ERROR);
    CHECK(g_hal.i2cDeInitCalls == 1); // recovery déclenchée au 3e échec.
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
