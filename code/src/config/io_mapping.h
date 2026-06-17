#pragma once

/**
 * @file io_mapping.h
 * @brief LLR_IOM_001 — GPIO pin mapping (STM32F4).
 *
 * All pins are named constants (no magic numbers), grouped by peripheral.
 * Target code: STM32F4 + HAL.
 */

#include "stm32f4xx_hal.h"

/// Port + pin pairing for a signal.
struct PinConfig
{
    GPIO_TypeDef *port; ///< GPIO port (GPIOA, GPIOB, ...).
    uint16_t pin;       ///< Pin mask (GPIO_PIN_x).
};

// --- Application GPIO ------------------------------------------------------
namespace io::gpio
{
/// Status LED (heartbeat) — output.
inline const PinConfig kLedStatus{GPIOA, GPIO_PIN_5};
/// User button (reset) — input.
inline const PinConfig kBtnUser{GPIOC, GPIO_PIN_13};
} // namespace io::gpio

// --- USART1 ----------------------------------------------------------------
namespace io::uart1
{
/// USART1 TX (alternate function).
inline const PinConfig kTx{GPIOA, GPIO_PIN_9};
/// USART1 RX (alternate function).
inline const PinConfig kRx{GPIOA, GPIO_PIN_10};
} // namespace io::uart1

// --- SPI1 ------------------------------------------------------------------
namespace io::spi1
{
/// SPI1 clock (alternate function).
inline const PinConfig kSck{GPIOA, GPIO_PIN_5};
/// SPI1 MOSI (alternate function).
inline const PinConfig kMosi{GPIOA, GPIO_PIN_7};
/// SPI1 MISO (alternate function).
inline const PinConfig kMiso{GPIOA, GPIO_PIN_6};
/// SPI1 chip-select (output, managed manually).
inline const PinConfig kCs{GPIOB, GPIO_PIN_6};
} // namespace io::spi1

// --- I2C1 ------------------------------------------------------------------
namespace io::i2c1
{
/// I2C1 clock (alternate function).
inline const PinConfig kScl{GPIOB, GPIO_PIN_8};
/// I2C1 data (alternate function).
inline const PinConfig kSda{GPIOB, GPIO_PIN_9};
} // namespace io::i2c1
