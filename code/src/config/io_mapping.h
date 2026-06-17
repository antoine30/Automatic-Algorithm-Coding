#pragma once

/**
 * @file io_mapping.h
 * @brief LLR_IOM_001 — Cartographie des broches GPIO (STM32F4).
 *
 * Toutes les broches sont des constantes nommées (aucun nombre magique),
 * regroupées par périphérique. Code cible STM32F4 + HAL.
 */

#include "stm32f4xx_hal.h"

/// Association port + broche pour un signal.
struct PinConfig
{
    GPIO_TypeDef *port; ///< Port GPIO (GPIOA, GPIOB, ...).
    uint16_t pin;       ///< Masque de broche (GPIO_PIN_x).
};

// --- GPIO applicatifs ------------------------------------------------------
namespace io::gpio
{
/// LED d'état (heartbeat) — sortie.
inline const PinConfig kLedStatus{GPIOA, GPIO_PIN_5};
/// Bouton utilisateur (reset) — entrée.
inline const PinConfig kBtnUser{GPIOC, GPIO_PIN_13};
} // namespace io::gpio

// --- USART1 ----------------------------------------------------------------
namespace io::uart1
{
/// USART1 TX (fonction alternée).
inline const PinConfig kTx{GPIOA, GPIO_PIN_9};
/// USART1 RX (fonction alternée).
inline const PinConfig kRx{GPIOA, GPIO_PIN_10};
} // namespace io::uart1

// --- SPI1 ------------------------------------------------------------------
namespace io::spi1
{
/// SPI1 horloge (fonction alternée).
inline const PinConfig kSck{GPIOA, GPIO_PIN_5};
/// SPI1 MOSI (fonction alternée).
inline const PinConfig kMosi{GPIOA, GPIO_PIN_7};
/// SPI1 MISO (fonction alternée).
inline const PinConfig kMiso{GPIOA, GPIO_PIN_6};
/// SPI1 chip-select (sortie, géré manuellement).
inline const PinConfig kCs{GPIOB, GPIO_PIN_6};
} // namespace io::spi1

// --- I2C1 ------------------------------------------------------------------
namespace io::i2c1
{
/// I2C1 horloge (fonction alternée).
inline const PinConfig kScl{GPIOB, GPIO_PIN_8};
/// I2C1 données (fonction alternée).
inline const PinConfig kSda{GPIOB, GPIO_PIN_9};
} // namespace io::i2c1
