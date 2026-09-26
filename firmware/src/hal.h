/* Hardware abstraction: ZIF-40 positions, DUT power, supply current.
 * The chip is always inserted top-justified (pin 1 in ZIF 1). */
#pragma once
#include <stdint.h>

#define ZIF_VCC 40                 /* always chip pin N for standard pinouts */
enum { PM_HIZ, PM_PULLUP, PM_LOW, PM_HIGH };

#define ICC_NONE (-32768)          /* returned when the INA219 is absent */

uint8_t hal_init(void);            /* returns bitmask: 1=MCP23008 ok, 2=INA219 ok */
void    hal_pin(uint8_t zif, uint8_t mode);
uint8_t hal_read(uint8_t zif);
void    hal_all_hiz(void);
void    hal_gnd(uint8_t zif);      /* 0 = all off, else 7/8/10/12 */
void    hal_vcc(uint8_t on);
int16_t hal_icc(void);             /* 0.1 mA units */
int16_t hal_vbus_mv(void);
void    hal_delay_us(uint16_t us);
void    hal_delay_ms(uint16_t ms);
void    hal_led(uint8_t on);
