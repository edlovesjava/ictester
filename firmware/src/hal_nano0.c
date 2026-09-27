/* Stage 0 hardware layer: Arduino Nano (ATmega328P) wired straight to a
 * 14-pin chip on a breadboard.
 * Spec: docs/superpowers/specs/2026-09-26-stage0-nano-breadboard-design.md
 *
 * A 14-pin chip sits top-justified in the virtual ZIF-40 (tester.c zif_of):
 * pins 1-7 at ZIF 1-7, pins 8-14 at ZIF 34-40. Each signal pin reaches its
 * Nano pin through its own 220 ohm resistor.
 *
 *   ZIF 1..6   -> D2..D7  (PD2..PD7)     chip pins 1..6
 *   ZIF 7      -> GND wire, no GPIO       chip pin 7
 *   ZIF 34..38 -> D8..D12 (PB0..PB4)     chip pins 8..12
 *   ZIF 39     -> A1      (PC1)          chip pin 13
 *   ZIF 40     -> A0      (PC0) = VCC    chip pin 14, no resistor
 *
 * D13 (PB5) is the on-board LED, never a chip pin.
 * No INA219: supply current is unknown and the over-current trip is off.
 */
#include <avr/io.h>
#include <util/delay.h>
#include "hal.h"

#define P(port, bit) (uint8_t)(((port) << 3) | (bit))
enum { B_, C_, D_ };
#define NONE 0xFF

static const uint8_t zmap[41] = {
    NONE,
    P(D_,2), P(D_,3), P(D_,4), NONE, NONE, NONE, /* ZIF 1-6:  D2-D7 (task 3 adds 4-6) */
    NONE,                                         /* ZIF 7:    GND wire           */
    NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, /* ZIF 8-17  */
    NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, /* ZIF 18-27 */
    NONE, NONE, NONE, NONE, NONE, NONE,          /* ZIF 28-33: unused            */
    NONE, NONE, NONE, NONE, NONE,                /* ZIF 34-38: D8-D12 (task 3)   */
    NONE,                                         /* ZIF 39:   A1     (task 3)    */
    NONE                                          /* ZIF 40:   VCC, see hal_vcc   */
};

/* ATmega328P: PINx/DDRx/PORTx for B, C, D live at 0x23, 0x26, 0x29 (+1, +2) */
#define R_PIN(k)  (*(volatile uint8_t *)(0x23 + 3 * (k)))
#define R_DDR(k)  (*(volatile uint8_t *)(0x24 + 3 * (k)))
#define R_PORT(k) (*(volatile uint8_t *)(0x25 + 3 * (k)))

#define VCC_BIT PC0     /* A0 feeds chip pin 14 directly */
#define LED_BIT PB5     /* D13, on-board LED */

void hal_pin(uint8_t zif, uint8_t mode)
{
    uint8_t e = zmap[zif];
    if (e == NONE) return;
    uint8_t k = e >> 3, m = (uint8_t)(1 << (e & 7));
    switch (mode) {
    case PM_HIZ:    R_DDR(k) &= (uint8_t)~m; R_PORT(k) &= (uint8_t)~m; break;
    case PM_PULLUP: R_DDR(k) &= (uint8_t)~m; R_PORT(k) |= m; break;
    case PM_LOW:    R_PORT(k) &= (uint8_t)~m; R_DDR(k) |= m; break;
    case PM_HIGH:   R_PORT(k) |= m; R_DDR(k) |= m; break;
    }
}

uint8_t hal_read(uint8_t zif)
{
    uint8_t e = zmap[zif];
    if (e == NONE) return 0;
    return (R_PIN(e >> 3) >> (e & 7)) & 1;
}

void hal_all_hiz(void)
{
    for (uint8_t z = 1; z < 40; z++) hal_pin(z, PM_HIZ);
}

void hal_gnd(uint8_t zif) { (void)zif; }            /* GND is a wire */

void hal_vcc(uint8_t on)
{
    if (on) PORTC |= 1 << VCC_BIT; else PORTC &= (uint8_t)~(1 << VCC_BIT);
}

int16_t hal_icc(void) { return ICC_NONE; }
int16_t hal_vbus_mv(void) { return -1; }
void hal_delay_us(uint16_t us) { while (us--) _delay_us(1); }
void hal_delay_ms(uint16_t ms) { while (ms--) _delay_ms(1); }
void hal_led(uint8_t on) { if (on) PORTB |= 1 << LED_BIT; else PORTB &= (uint8_t)~(1 << LED_BIT); }

uint8_t hal_init(void)
{
    hal_all_hiz();
    PORTC &= (uint8_t)~(1 << VCC_BIT);                /* VCC off ...       */
    DDRC |= 1 << VCC_BIT;                             /* ... then drive it */
    DDRB |= 1 << LED_BIT;
    return 0;                                         /* no MCP23008, no INA219 */
}
