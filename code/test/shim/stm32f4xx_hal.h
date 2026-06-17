#pragma once

/**
 * @file stm32f4xx_hal.h (SHIM)
 * @brief Stub du HAL STM32F4 — tests hôte uniquement. NE FAIT PAS PARTIE DU FW.
 *
 * Fournit les types/fonctions HAL utilisés par les drivers, plus un MOCK
 * contrôlable (g_hal) permettant aux tests d'injecter des statuts de retour et
 * d'observer les appels (compteurs, données, état des broches GPIO).
 *
 * Utilisation dans un test :
 *   g_hal.reset();
 *   g_hal.uartReceiveStatus = HAL_TIMEOUT;   // injecte un timeout
 *   ... appeler le driver ...
 *   CHECK(g_hal.uartReceiveCalls == 1);      // observe
 */

#include <cstddef>
#include <cstdint>

// --- Types de base HAL -----------------------------------------------------
typedef enum
{
    HAL_OK = 0,
    HAL_ERROR = 1,
    HAL_BUSY = 2,
    HAL_TIMEOUT = 3
} HAL_StatusTypeDef;

typedef enum
{
    GPIO_PIN_RESET = 0,
    GPIO_PIN_SET = 1
} GPIO_PinState;

// Masques de broches (sous-ensemble suffisant).
#define GPIO_PIN_5 ((uint16_t)0x0020)
#define GPIO_PIN_6 ((uint16_t)0x0040)
#define GPIO_PIN_7 ((uint16_t)0x0080)
#define GPIO_PIN_9 ((uint16_t)0x0200)
#define GPIO_PIN_10 ((uint16_t)0x0400)
#define GPIO_PIN_13 ((uint16_t)0x2000)

// Modes GPIO (utilisés par TaskHeartbeat).
#define GPIO_MODE_OUTPUT_PP 0x01u
#define GPIO_NOPULL 0x00u
#define GPIO_SPEED_FREQ_LOW 0x00u

// Handles HAL (contenu sans importance pour les tests).
typedef struct { int instance; } UART_HandleTypeDef;
typedef struct { int instance; } SPI_HandleTypeDef;
typedef struct { int instance; } I2C_HandleTypeDef;
typedef struct { int instance; } TIM_HandleTypeDef;
typedef struct { int port; } GPIO_TypeDef;

typedef struct
{
    uint16_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
} GPIO_InitTypeDef;

// --- Mock contrôlable ------------------------------------------------------
struct HalMock
{
    // Statuts injectables.
    HAL_StatusTypeDef uartReceiveItStatus = HAL_OK;
    HAL_StatusTypeDef uartReceiveStatus = HAL_OK;
    HAL_StatusTypeDef uartTransmitStatus = HAL_OK;
    HAL_StatusTypeDef spiTransferStatus = HAL_OK;
    HAL_StatusTypeDef i2cInitStatus = HAL_OK;
    HAL_StatusTypeDef i2cTxStatus = HAL_OK;
    HAL_StatusTypeDef i2cRxStatus = HAL_OK;

    // Compteurs d'appels.
    int uartReceiveItCalls = 0;
    int uartReceiveCalls = 0;
    int uartTransmitCalls = 0;
    int uartAbortCalls = 0;
    int spiTransferCalls = 0;
    int spiAbortCalls = 0;
    int i2cDeInitCalls = 0;
    int i2cInitCalls = 0;
    int i2cTxCalls = 0;
    int i2cRxCalls = 0;
    int gpioWriteCalls = 0;
    int gpioToggleCalls = 0;

    // Observations.
    uint8_t rxFillByte = 0xAB;          ///< Octet utilisé pour remplir les lectures.
    GPIO_PinState lastGpioState = GPIO_PIN_RESET; ///< Dernier état écrit sur un GPIO.

    void reset() { *this = HalMock(); }
};

inline HalMock g_hal; // Instance unique (variable inline C++17).

// --- Fonctions HAL simulées ------------------------------------------------
inline void HAL_Init() {}

// UART
inline HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *, uint8_t *, uint16_t)
{
    ++g_hal.uartReceiveItCalls;
    return g_hal.uartReceiveItStatus;
}
inline HAL_StatusTypeDef HAL_UART_Abort(UART_HandleTypeDef *)
{
    ++g_hal.uartAbortCalls;
    return HAL_OK;
}
inline HAL_StatusTypeDef HAL_UART_Receive(UART_HandleTypeDef *, uint8_t *buf,
                                          uint16_t len, uint32_t)
{
    ++g_hal.uartReceiveCalls;
    if (g_hal.uartReceiveStatus == HAL_OK && buf != nullptr)
    {
        for (uint16_t i = 0; i < len; ++i)
        {
            buf[i] = g_hal.rxFillByte;
        }
    }
    return g_hal.uartReceiveStatus;
}
inline HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *, uint8_t *,
                                           uint16_t, uint32_t)
{
    ++g_hal.uartTransmitCalls;
    return g_hal.uartTransmitStatus;
}

// SPI
inline HAL_StatusTypeDef HAL_SPI_Abort(SPI_HandleTypeDef *)
{
    ++g_hal.spiAbortCalls;
    return HAL_OK;
}
inline HAL_StatusTypeDef HAL_SPI_TransmitReceive(SPI_HandleTypeDef *, uint8_t *,
                                                 uint8_t *rx, uint16_t len, uint32_t)
{
    ++g_hal.spiTransferCalls;
    if (g_hal.spiTransferStatus == HAL_OK && rx != nullptr)
    {
        for (uint16_t i = 0; i < len; ++i)
        {
            rx[i] = g_hal.rxFillByte;
        }
    }
    return g_hal.spiTransferStatus;
}

// I2C
inline HAL_StatusTypeDef HAL_I2C_DeInit(I2C_HandleTypeDef *)
{
    ++g_hal.i2cDeInitCalls;
    return HAL_OK;
}
inline HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *)
{
    ++g_hal.i2cInitCalls;
    return g_hal.i2cInitStatus;
}
inline HAL_StatusTypeDef HAL_I2C_Master_Transmit(I2C_HandleTypeDef *, uint16_t,
                                                 uint8_t *, uint16_t, uint32_t)
{
    ++g_hal.i2cTxCalls;
    return g_hal.i2cTxStatus;
}
inline HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *, uint16_t,
                                                uint8_t *buf, uint16_t len, uint32_t)
{
    ++g_hal.i2cRxCalls;
    if (g_hal.i2cRxStatus == HAL_OK && buf != nullptr)
    {
        for (uint16_t i = 0; i < len; ++i)
        {
            buf[i] = g_hal.rxFillByte;
        }
    }
    return g_hal.i2cRxStatus;
}

// GPIO
inline void HAL_GPIO_WritePin(GPIO_TypeDef *, uint16_t, GPIO_PinState state)
{
    ++g_hal.gpioWriteCalls;
    g_hal.lastGpioState = state;
}
inline void HAL_GPIO_TogglePin(GPIO_TypeDef *, uint16_t)
{
    ++g_hal.gpioToggleCalls;
    g_hal.lastGpioState =
        (g_hal.lastGpioState == GPIO_PIN_SET) ? GPIO_PIN_RESET : GPIO_PIN_SET;
}
inline void HAL_GPIO_Init(GPIO_TypeDef *, GPIO_InitTypeDef *) {}
