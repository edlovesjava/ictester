#include <avr/pgmspace.h>
#include "config.h"
#include "twi.h"
#include "ssd1306.h"
#include "font5x7.h"

static uint8_t present;

static const uint8_t init_seq[] PROGMEM = {
    0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0x8D, 0x14,
    0x20, 0x00,             /* horizontal addressing */
    0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40,
    0xA4, 0xA6, 0xAF
};

static void window(uint8_t row, uint8_t col)
{
    uint8_t c[] = {0x00, 0x21, (uint8_t)(col * 6), 127, 0x22, row, row};
    twi_write(I2C_OLED, c, sizeof c);
}

uint8_t oled_init(void)
{
    present = twi_write_P(I2C_OLED, 0x00, init_seq, sizeof init_seq);
    if (present) oled_clear();
    return present;
}

static void glyph(char ch)
{
    if (ch >= 'a' && ch <= 'z') ch -= 32;
    if (ch < 0x20 || ch > 0x5F) ch = '?';
    const uint8_t *g = font5x7[ch - 0x20];
    for (uint8_t i = 0; i < 5; i++) twi_put(pgm_read_byte(g + i));
    twi_put(0);
}

void oled_clear(void)
{
    if (!present) return;
    for (uint8_t r = 0; r < 8; r++) {
        window(r, 0);
        if (!twi_begin(I2C_OLED)) return;
        twi_put(0x40);
        for (uint8_t i = 0; i < 128; i++) twi_put(0);
        twi_end();
    }
}

static void text(uint8_t row, uint8_t col, const char *s, uint8_t pgm, uint8_t pad)
{
    if (!present) return;
    window(row, col);
    if (!twi_begin(I2C_OLED)) return;
    twi_put(0x40);
    uint8_t n = col;
    for (;; s++) {
        char c = pgm ? (char)pgm_read_byte(s) : *s;
        if (!c || n >= 21) break;
        glyph(c); n++;
    }
    if (pad) { while (n < 21) { glyph(' '); n++; } twi_put(0); twi_put(0); }
    twi_end();
}

void oled_text(uint8_t row, uint8_t col, const char *s)     { text(row, col, s, 0, 0); }
void oled_text_P(uint8_t row, uint8_t col, const char *s)   { text(row, col, s, 1, 0); }
void oled_line(uint8_t row, const char *s)                  { text(row, 0, s, 0, 1); }
