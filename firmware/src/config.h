#pragma once
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#define FW_VERSION      "1.0"
#define UART_BAUD       115200UL

/* I2C 7-bit addresses */
#define I2C_OLED        0x3C
#define I2C_INA219      0x40
#define I2C_MCP23008    0x20

/* INA219 with its 0.1 ohm shunt: 10 uV LSB / 0.1 ohm = 0.1 mA per count */
#define TRIP_DEFAULT    1200   /* 0.1 mA units -> 120.0 mA */

/* Test timing (4000B parts at 5 V need hundreds of ns; be generous) */
#define SETTLE_US       20
#define PULSE_US        5

/* Front panel (spare port B pins; PB5-7 left free for ISP) */
#define BTN_BIT         3      /* PB3 to GND, internal pull-up */
#define LED_BIT         4      /* PB4 -> 1k -> LED -> GND */
