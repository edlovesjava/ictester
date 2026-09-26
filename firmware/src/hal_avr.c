/* ATmega1284P hardware layer.
 *
 * ZIF-40 map (chip top-justified, pin 1 in ZIF 1). Every GPIO reaches its ZIF
 * contact through a 220 ohm series resistor.
 *
 *   ZIF  1..8   -> PA0..PA7        ZIF 39..34 -> PD7..PD2
 *   ZIF  9..12  -> PC2..PC5        ZIF 33,32  -> PC7, PC6
 *                                  ZIF 31..29 -> PB2..PB0
 *   ZIF 40      -> switched VCC rail (INA219 shunt), no GPIO
 *   ZIF 13..28  -> unused (chips are at most 24 pins)
 *
 * MCP23008 @0x20: GP0 = /VCC_EN (BC327 base via 1k), GP1..GP4 = 2N7000 gates
 * for ZIF 7, 8, 10, 12 (the GND pin of 14/16/20/24-pin packages).
 */
#include <avr/io.h>
#include <util/delay.h>
#include "config.h"
#include "hal.h"
#include "twi.h"

#define P(port, bit) (uint8_t)(((port) << 3) | (bit))
enum { A_, B_, C_, D_ };
#define NONE 0xFF

static const uint8_t zmap[41] = {
    NONE,
    P(A_,0), P(A_,1), P(A_,2), P(A_,3), P(A_,4), P(A_,5), P(A_,6), P(A_,7),   /* ZIF 1-8  */
    P(C_,2), P(C_,3), P(C_,4), P(C_,5),                                      /* ZIF 9-12 */
    NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE,                          /* 13-20    */
    NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE,                          /* 21-28    */
    P(B_,0), P(B_,1), P(B_,2), P(C_,6), P(C_,7),                             /* ZIF 29-33 */
    P(D_,2), P(D_,3), P(D_,4), P(D_,5), P(D_,6), P(D_,7),                    /* ZIF 34-39 */
    NONE                                                                     /* ZIF 40 VCC */
};

/* ATmega1284P: PINx/DDRx/PORTx for port k live at I/O 3k, 3k+1, 3k+2 */
#define R_PIN(k)  (*(volatile uint8_t *)(0x20 + 3 * (k)))
#define R_DDR(k)  (*(volatile uint8_t *)(0x21 + 3 * (k)))
#define R_PORT(k) (*(volatile uint8_t *)(0x22 + 3 * (k)))

static uint8_t mcp_olat = 0x01;       /* GP0 high = VCC off, grounds off */
static uint8_t have_ina;

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

static void mcp_write(uint8_t reg, uint8_t v) { uint8_t b[2] = {reg, v}; twi_write(I2C_MCP23008, b, 2); }

void hal_gnd(uint8_t zif)
{
    uint8_t g = 0;
    switch (zif) { case 7: g = 1 << 1; break; case 8: g = 1 << 2; break;
                   case 10: g = 1 << 3; break; case 12: g = 1 << 4; break; }
    mcp_olat = (uint8_t)((mcp_olat & 0x01) | g);
    mcp_write(0x0A, mcp_olat);              /* OLAT */
}

void hal_vcc(uint8_t on)
{
    mcp_olat = on ? (uint8_t)(mcp_olat & ~0x01) : (uint8_t)(mcp_olat | 0x01);
    mcp_write(0x0A, mcp_olat);
}

static int16_t ina_reg(uint8_t reg, uint8_t *ok)
{
    uint8_t b[2];
    *ok = twi_read_reg(I2C_INA219, reg, b, 2);
    return (int16_t)((b[0] << 8) | b[1]);
}

int16_t hal_icc(void)
{
    uint8_t ok;
    if (!have_ina) return ICC_NONE;
    int16_t v = ina_reg(0x01, &ok);         /* shunt voltage, 10 uV/LSB -> 0.1 mA/LSB at 0.1 ohm */
    return ok ? v : ICC_NONE;
}

int16_t hal_vbus_mv(void)
{
    uint8_t ok;
    if (!have_ina) return -1;
    uint16_t v = (uint16_t)ina_reg(0x02, &ok);
    return ok ? (int16_t)((v >> 3) * 4) : -1;   /* bits 15..3, 4 mV/LSB */
}

void hal_delay_us(uint16_t us) { while (us--) _delay_us(1); }
void hal_delay_ms(uint16_t ms) { while (ms--) _delay_ms(1); }
void hal_led(uint8_t on) { if (on) PORTB |= 1 << LED_BIT; else PORTB &= (uint8_t)~(1 << LED_BIT); }

uint8_t hal_init(void)
{
    uint8_t st = 0;
    hal_all_hiz();
    DDRB |= 1 << LED_BIT;
    PORTB |= 1 << BTN_BIT;                  /* button pull-up */
    twi_init();
    if (twi_probe(I2C_MCP23008)) {
        st |= 1;
        mcp_write(0x0A, mcp_olat);          /* latch first ...            */
        mcp_write(0x00, 0xE0);              /* ... then GP0-4 as outputs  */
    }
    if (twi_probe(I2C_INA219)) {
        /* BRNG=16V, PGA=/1 (+-40 mV = +-400 mA), 12-bit bus & shunt, continuous */
        uint8_t cfg[3] = {0x00, 0x01, 0x9F};
        twi_write(I2C_INA219, cfg, 3);
        have_ina = 1;
        st |= 2;
    }
    return st;
}
