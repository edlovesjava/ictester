/* Test engine -- platform independent (talks to hal.h only). */
#include <ctype.h>
#include "tester.h"
#include "hal.h"
#include "config.h"

int16_t trip_limit = TRIP_DEFAULT;
static uint8_t powered;                 /* pin count while DUT is powered */

/* Chip pins 1..N/2 run down the left column (ZIF 1..N/2); pins N/2+1..N run up
 * the right column so that pin N always lands on ZIF 40. */
uint8_t zif_of(uint8_t p, uint8_t n)
{
    return (p <= n / 2) ? p : (uint8_t)(40 - (n - p));
}

void tester_chip(uint8_t idx, chip_t *out) { memcpy_P(out, &chip_db[idx], sizeof(chip_t)); }

uint8_t tester_powered_pins(void) { return powered; }

/* CMOS rule: never drive a pin of an unpowered chip. Everything is Hi-Z until
 * ground and VCC are up, and goes Hi-Z again before power is removed. */
int8_t tester_power_up(uint8_t n)
{
    if (powered == n) return 0;
    tester_power_down();
    hal_all_hiz();
    hal_gnd(n / 2);
    hal_delay_us(200);
    hal_vcc(1);
    hal_delay_ms(2);                    /* >= 2 INA219 conversions (532 us each) */
    int16_t i = hal_icc();
    if (i != ICC_NONE && i > trip_limit) {
        tester_power_down();
        return -1;
    }
    powered = n;
    return 0;
}

void tester_power_down(void)
{
    hal_all_hiz();
    hal_vcc(0);
    hal_delay_ms(1);
    hal_gnd(0);
    powered = 0;
}

/* Apply one vector. Pins are changed one at a time in chip-pin order (the
 * database generator models exactly this), then clock pins are pulsed
 * 0->1->0 `rep` times. Returns 0 on match, else the 1-based pin that failed.
 * `actual` receives what was observed (drive pins echo their drive char). */
uint8_t tester_apply(const char *v, uint8_t n, uint8_t rep, char *actual)
{
    uint8_t p, clk = 0, bad = 0;
    for (p = 1; p <= n; p++) {
        uint8_t z = zif_of(p, n);
        switch (v[p - 1]) {
        case '0': hal_pin(z, PM_LOW);  break;
        case '1': hal_pin(z, PM_HIGH); break;
        case 'C': hal_pin(z, PM_LOW); clk = 1; break;
        case 'L': case 'H': case 'X': hal_pin(z, PM_PULLUP); break;
        case 'G': hal_pin(z, PM_HIZ); break;   /* low-side switch owns it */
        default: break;                         /* 'V': switched rail, no GPIO */
        }
    }
    hal_delay_us(SETTLE_US);
    if (clk) {
        while (rep--) {
            for (p = 1; p <= n; p++) if (v[p - 1] == 'C') hal_pin(zif_of(p, n), PM_HIGH);
            hal_delay_us(PULSE_US);
            for (p = 1; p <= n; p++) if (v[p - 1] == 'C') hal_pin(zif_of(p, n), PM_LOW);
            hal_delay_us(PULSE_US);
        }
        hal_delay_us(SETTLE_US);
    }
    for (p = 1; p <= n; p++) {
        char c = v[p - 1];
        if (c == 'L' || c == 'H' || c == 'X') {
            char got = hal_read(zif_of(p, n)) ? 'H' : 'L';
            if (actual) actual[p - 1] = got;
            if (c != 'X' && got != c && !bad) bad = p;
        } else if (actual) {
            actual[p - 1] = c;
        }
    }
    if (actual) actual[n] = 0;
    return bad;
}

void tester_run(uint8_t idx, result_t *r)
{
    chip_t ch;
    char v[MAXPINS + 1], act[MAXPINS + 1];
    tester_chip(idx, &ch);
    memset(r, 0, sizeof *r);
    r->nvec = ch.nvec;
    r->icc = ICC_NONE;
    if (tester_power_up(ch.pins)) { r->tripped = 1; return; }

    const uint8_t *p = ch.vecs;
    for (uint16_t i = 0; i < ch.nvec; i++) {
        uint8_t rep = pgm_read_byte(p++);
        for (uint8_t k = 0; k < ch.pins; k++) v[k] = (char)pgm_read_byte(p++);
        uint8_t m = tester_apply(v, ch.pins, rep, act);
        if (m) {
            r->fail_vec = i; r->fail_pin = m;
            r->expected = v[m - 1]; r->got = act[m - 1];
            goto done;
        }
        if ((i & 7) == 7) {
            int16_t icc = hal_icc();
            if (icc != ICC_NONE && icc > trip_limit) { r->tripped = 1; r->fail_vec = i; goto done; }
        }
    }
    r->pass = 1;
    r->icc = hal_icc();
done:
    tester_power_down();
}

/* ---- part-number normalisation: SN74LS00N -> 7400, CD4011BE -> 4011,
 *      74HC4040 -> 4040, MC14011B -> 4011 */
static void normalise(const char *in, char *out, uint8_t max)
{
    char d[8]; uint8_t nd = 0;
    const char *s = in;
    while (*s && !isdigit((unsigned char)*s)) s++;          /* SN, CD, MC, HEF, DM ... */
    uint8_t is74 = (s[0] == '7' && s[1] == '4');
    if (is74) {
        s += 2;
        while (*s && isalpha((unsigned char)*s)) s++;         /* LS, HC, HCT, ALS, F ... */
    }
    while (*s && isdigit((unsigned char)*s) && nd < sizeof d - 1) d[nd++] = *s++;
    d[nd] = 0;
    if (!is74 && nd == 5 && d[0] == '1' && d[1] == '4') {    /* Motorola MC14xxx */
        memmove(d, d + 1, nd--);
    }
    if (is74 && nd < 4) snprintf(out, max, "74%s", d);
    else snprintf(out, max, "%s", d);
}

static uint8_t alias_has(const char *aliases_P, const char *want)
{
    char tok[12]; uint8_t t = 0;
    for (;;) {
        char c = (char)pgm_read_byte(aliases_P++);
        if (c == ' ' || c == 0) {
            tok[t] = 0;
            if (t && strcmp(tok, want) == 0) return 1;
            t = 0;
            if (!c) return 0;
        } else if (t < sizeof tok - 1) {
            tok[t++] = c;
        }
    }
}

int16_t tester_find(const char *part)
{
    char up[16], norm[12];
    uint8_t i;
    for (i = 0; part[i] && i < sizeof up - 1; i++) up[i] = (char)toupper((unsigned char)part[i]);
    up[i] = 0;
    normalise(up, norm, sizeof norm);
    for (i = 0; i < chip_db_count; i++) {
        chip_t ch; tester_chip(i, &ch);
        if (strcmp_P(norm, ch.name) == 0) return i;
    }
    for (i = 0; i < chip_db_count; i++) {
        chip_t ch; tester_chip(i, &ch);
        if (alias_has(ch.aliases, norm)) return i;
    }
    return -1;
}

uint8_t tester_identify(uint8_t npins, match_cb cb, void *ctx)
{
    uint8_t tried = 0;
    for (uint8_t i = 0; i < chip_db_count; i++) {
        chip_t ch; tester_chip(i, &ch);
        if (ch.pins != npins) continue;
        result_t r;
        tester_run(i, &r);
        tried++;
        if (r.pass) cb(i, &r, ctx);
    }
    return tried;
}
