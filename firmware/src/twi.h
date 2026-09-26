#pragma once
#include <stdint.h>
void    twi_init(void);
uint8_t twi_write(uint8_t addr, const uint8_t *buf, uint8_t n);              /* 1 = ok */
uint8_t twi_write_P(uint8_t addr, uint8_t ctrl, const uint8_t *buf_P, uint16_t n);
uint8_t twi_read_reg(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t n);
uint8_t twi_probe(uint8_t addr);
/* streaming (used by the OLED driver) */
uint8_t twi_begin(uint8_t addr);
uint8_t twi_put(uint8_t b);
void    twi_end(void);
