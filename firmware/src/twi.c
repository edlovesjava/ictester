/* Polled TWI master, 400 kHz, with timeouts so a missing/miswired breadboard
 * device cannot hang the tester. */
#include <avr/io.h>
#include <avr/pgmspace.h>
#include "config.h"
#include "twi.h"

#define ST (TWSR & 0xF8)

static uint8_t wait(void)
{
    uint16_t t = 0;
    while (!(TWCR & (1 << TWINT))) if (++t == 0) return 0;
    return 1;
}

void twi_init(void)
{
    TWSR = 0;                                   /* prescaler 1 */
    TWBR = (uint8_t)((F_CPU / 400000UL - 16) / 2);  /* 12 @ 16 MHz */
    TWCR = (1 << TWEN);
}

static uint8_t start(uint8_t sla)
{
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
    if (!wait() || (ST != 0x08 && ST != 0x10)) return 0;
    TWDR = sla;
    TWCR = (1 << TWINT) | (1 << TWEN);
    if (!wait()) return 0;
    return ST == 0x18 || ST == 0x40;           /* SLA+W ack / SLA+R ack */
}

uint8_t twi_put(uint8_t b)
{
    TWDR = b;
    TWCR = (1 << TWINT) | (1 << TWEN);
    return wait() && ST == 0x28;
}

void twi_end(void)
{
    uint16_t t = 0;
    TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
    while ((TWCR & (1 << TWSTO)) && ++t) ;
}

uint8_t twi_begin(uint8_t addr) { if (start(addr << 1)) return 1; twi_end(); return 0; }

uint8_t twi_probe(uint8_t addr) { uint8_t ok = start(addr << 1); twi_end(); return ok; }

uint8_t twi_write(uint8_t addr, const uint8_t *buf, uint8_t n)
{
    uint8_t ok = start(addr << 1);
    while (ok && n--) ok = twi_put(*buf++);
    twi_end();
    return ok;
}

uint8_t twi_write_P(uint8_t addr, uint8_t ctrl, const uint8_t *p, uint16_t n)
{
    uint8_t ok = start(addr << 1) && twi_put(ctrl);
    while (ok && n--) ok = twi_put(pgm_read_byte(p++));
    twi_end();
    return ok;
}

uint8_t twi_read_reg(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t n)
{
    if (!start(addr << 1) || !twi_put(reg)) { twi_end(); return 0; }
    if (!start((addr << 1) | 1)) { twi_end(); return 0; }
    while (n--) {
        TWCR = (1 << TWINT) | (1 << TWEN) | (n ? (1 << TWEA) : 0);
        if (!wait()) { twi_end(); return 0; }
        *buf++ = TWDR;
    }
    twi_end();
    return 1;
}
