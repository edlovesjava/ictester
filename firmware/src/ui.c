/* OLED front panel. 21 x 8 characters. */
#include <stdio.h>
#include <avr/pgmspace.h>
#include "ui.h"
#include "ssd1306.h"
#include "hal.h"
#include "cmd.h"

static char buf[22];

static void fmt_icc(int16_t icc)
{
    if (icc == ICC_NONE) snprintf_P(buf, sizeof buf, PSTR("ICC  --"));
    else { if (icc < 0) icc = 0; snprintf_P(buf, sizeof buf, PSTR("ICC %d.%d MA"), icc / 10, icc % 10); }
    oled_line(7, buf);
}

static void header(uint8_t pins)
{
    snprintf_P(buf, sizeof buf, PSTR("IC TESTER       %uP"), pins);
    oled_line(0, buf);
}

void ui_ready(uint8_t pins)
{
    oled_clear();
    header(pins);
    oled_line(2, "READY");
    oled_line(4, "SHORT PRESS: ID");
    oled_line(5, "LONG PRESS: PINS");
}

void ui_busy(const char *name_P, uint8_t pins)
{
    hal_led(1);
    header(pins);
    snprintf_P(buf, sizeof buf, PSTR("%S..."), name_P);
    oled_line(2, buf);
    for (uint8_t r = 3; r < 8; r++) oled_line(r, "");
}

void ui_test_result(uint8_t idx, const result_t *r)
{
    chip_t ch; tester_chip(idx, &ch);
    hal_led(0);
    snprintf_P(buf, sizeof buf, PSTR("%S %S"), ch.name, r->pass ? PSTR("PASS") : r->tripped ? PSTR("TRIP!") : PSTR("FAIL"));
    oled_line(2, buf);
    snprintf_P(buf, sizeof buf, PSTR("%S"), ch.desc);
    oled_line(3, buf);
    if (!r->pass && !r->tripped) {
        snprintf_P(buf, sizeof buf, PSTR("VEC %u PIN %u"), r->fail_vec, r->fail_pin);
        oled_line(5, buf);
        snprintf_P(buf, sizeof buf, PSTR("WANT %c GOT %c"), r->expected, r->got);
        oled_line(6, buf);
    }
    if (r->tripped) oled_line(5, "OVERCURRENT: REVERSED?");
    fmt_icc(r->icc);
}

void ui_id_result(uint8_t pins, uint8_t n, const uint8_t *first)
{
    hal_led(0);
    header(pins);
    if (!n) { oled_line(2, "NO MATCH"); oled_line(3, "CHECK PINS/ORIENT."); return; }
    snprintf_P(buf, sizeof buf, PSTR("%u MATCH%S"), n, n > 1 ? PSTR("ES") : PSTR(""));
    oled_line(2, buf);
    for (uint8_t i = 0; i < n && i < 4; i++) {
        chip_t ch; tester_chip(first[i], &ch);
        snprintf_P(buf, sizeof buf, PSTR("%S"), ch.name);
        oled_line(3 + i, buf);
    }
}
