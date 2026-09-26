#pragma once
#include <stdint.h>
/* Text-only SSD1306 128x64 driver: 8 rows x 21 columns of 6x8 cells, no framebuffer. */
uint8_t oled_init(void);
void oled_clear(void);
void oled_text(uint8_t row, uint8_t col, const char *s);      /* RAM string, pads nothing */
void oled_text_P(uint8_t row, uint8_t col, const char *s_P);
void oled_line(uint8_t row, const char *s);                    /* whole row, blank-padded */
