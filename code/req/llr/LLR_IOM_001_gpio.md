# LLR_IOM_001 — GPIO Mapping

## Level : LOW LEVEL
## Parent HLR : HLR_001

## Files to Generate
- src/config/io_mapping.h

## Pin Mapping
| Signal       | Port  | Pin | Direction | Function          |
|--------------|-------|-----|-----------|-------------------|
| LED_STATUS   | GPIOA | 5   | OUTPUT    | Heartbeat LED     |
| BTN_USER     | GPIOC | 13  | INPUT     | User reset button |
| UART1_TX     | GPIOA | 9   | AF        | USART1 TX         |
| UART1_RX     | GPIOA | 10  | AF        | USART1 RX         |
| SPI1_SCK     | GPIOA | 5   | AF        | SPI1 Clock        |
| SPI1_MOSI    | GPIOA | 7   | AF        | SPI1 MOSI         |
| SPI1_MISO    | GPIOA | 6   | AF        | SPI1 MISO         |
| SPI1_CS      | GPIOB | 6   | OUTPUT    | SPI1 Chip Select  |
| I2C1_SCL     | GPIOB | 8   | AF        | I2C1 Clock        |
| I2C1_SDA     | GPIOB | 9   | AF        | I2C1 Data         |

## Constraints
- Use constexpr for all pin definitions
- Group definitions by peripheral
- No magic numbers — all pins must be named constants

## Instructions for Claude
1. Generate io_mapping.h with constexpr for each pin (port + pin number)
2. Group by peripheral (UART, SPI, I2C, GPIO)
3. Add a Doxygen comment for each signal describing its role
4. Use STM32 HAL GPIO_PIN_x naming convention
