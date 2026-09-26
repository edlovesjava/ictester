/* Line-oriented serial API. Every command answers with exactly one JSON line.
 *
 *   HELP                      list commands
 *   INFO                      firmware, sensors, current settings
 *   LIST [pins]               chip database
 *   TEST <part>               run one definition   (part: 7400, 74LS00, CD4011BE ...)
 *   ID [pins]                 try every definition with that pin count (default: PINS)
 *   PINS <14|16|20|24>        default package size for ID / front-panel button
 *   VEC <vector> [rep]        power up (if needed) and apply one raw vector; stays powered
 *   OFF                       power the socket down
 *   LIMIT <mA>                over-current trip threshold
 */
#include <stdlib.h>
#include <ctype.h>
#include "cmd.h"
#include "tester.h"
#include "hal.h"
#include "config.h"
#include "ui.h"

uint8_t default_pins = 14;
uint8_t hal_status;

static void p_icc(const char *key, int16_t icc)
{
    if (icc == ICC_NONE) { printf_P(PSTR(",\"%s\":null"), key); return; }
    if (icc < 0) icc = 0;
    printf_P(PSTR(",\"%s\":%d.%d"), key, icc / 10, icc % 10);
}

static void p_str_P(const char *s)          /* PROGMEM string, JSON-quoted */
{
    putchar('"');
    char c;
    while ((c = (char)pgm_read_byte(s++))) { if (c == '"' || c == '\\') putchar('\\'); putchar(c); }
    putchar('"');
}

static void err(const char *msg) { printf_P(PSTR("{\"error\":\"%s\"}\n"), msg); }

static uint8_t valid_pins(int n) { return n == 14 || n == 16 || n == 20 || n == 24; }

static void result_json(uint8_t idx, const result_t *r)
{
    chip_t ch; tester_chip(idx, &ch);
    printf_P(PSTR("{\"part\":")); p_str_P(ch.name);
    printf_P(PSTR(",\"pins\":%u,\"pass\":%s,\"vectors\":%u"), ch.pins, r->pass ? "true" : "false", r->nvec);
    if (r->tripped) printf_P(PSTR(",\"tripped\":true"));
    else if (!r->pass)
        printf_P(PSTR(",\"fail\":{\"vector\":%u,\"pin\":%u,\"expected\":\"%c\",\"got\":\"%c\"}"),
                 r->fail_vec, r->fail_pin, r->expected, r->got);
    p_icc("icc_mA", r->icc);
    printf_P(PSTR("}\n"));
}

typedef struct { uint8_t n; uint8_t first[4]; } idctx_t;

static void id_cb(uint8_t idx, const result_t *r, void *vctx)
{
    idctx_t *c = vctx;
    chip_t ch; tester_chip(idx, &ch);
    if (c->n) putchar(',');
    printf_P(PSTR("{\"part\":")); p_str_P(ch.name);
    printf_P(PSTR(",\"aliases\":")); p_str_P(ch.aliases);
    printf_P(PSTR(",\"desc\":")); p_str_P(ch.desc);
    p_icc("icc_mA", r->icc);
    putchar('}');
    if (c->n < 4) c->first[c->n] = idx;
    c->n++;
}

void cmd_identify(uint8_t pins)
{
    idctx_t c = {0};
    ui_busy(PSTR("IDENTIFY"), pins);
    printf_P(PSTR("{\"pins\":%u,\"matches\":["), pins);
    uint8_t tried = tester_identify(pins, id_cb, &c);
    printf_P(PSTR("],\"tried\":%u}\n"), tried);
    ui_id_result(pins, c.n, c.first);
}

static void cmd_test(const char *part)
{
    int16_t idx = tester_find(part);
    if (idx < 0) { err("unknown part"); return; }
    chip_t ch; tester_chip(idx, &ch);
    ui_busy(ch.name, ch.pins);
    result_t r;
    tester_run((uint8_t)idx, &r);
    result_json((uint8_t)idx, &r);
    ui_test_result((uint8_t)idx, &r);
}

static void cmd_vec(const char *v, int rep)
{
    uint8_t n = (uint8_t)strlen(v);
    char vv[MAXPINS + 1], act[MAXPINS + 1];
    if (!valid_pins(n)) { err("vector length must be 14/16/20/24"); return; }
    for (uint8_t i = 0; i < n; i++) {
        char c = (char)toupper((unsigned char)v[i]);
        if (!strchr("01CLHXGV", c)) { err("bad vector char"); return; }
        vv[i] = c;
    }
    vv[n] = 0;
    if (vv[n / 2 - 1] != 'G' || vv[n - 1] != 'V') { err("pin N/2 must be G and pin N must be V"); return; }
    if (rep < 1 || rep > 255) rep = 1;
    if (tester_power_up(n)) { printf_P(PSTR("{\"tripped\":true}\n")); return; }
    uint8_t bad = tester_apply(vv, n, (uint8_t)rep, act);
    printf_P(PSTR("{\"sent\":\"%s\",\"read\":\"%s\",\"match\":%s"), vv, act, bad ? "false" : "true");
    p_icc("icc_mA", hal_icc());
    printf_P(PSTR("}\n"));
}

static void cmd_list(int pins)
{
    printf_P(PSTR("{\"chips\":["));
    uint8_t first = 1;
    for (uint8_t i = 0; i < chip_db_count; i++) {
        chip_t ch; tester_chip(i, &ch);
        if (pins && ch.pins != pins) continue;
        if (!first) putchar(',');
        first = 0;
        printf_P(PSTR("{\"part\":")); p_str_P(ch.name);
        printf_P(PSTR(",\"pins\":%u,\"vectors\":%u,\"desc\":"), ch.pins, ch.nvec); p_str_P(ch.desc);
        printf_P(PSTR(",\"aliases\":")); p_str_P(ch.aliases);
        putchar('}');
    }
    printf_P(PSTR("]}\n"));
}

static void cmd_info(void)
{
    printf_P(PSTR("{\"fw\":\"" FW_VERSION "\",\"chips\":%u,\"pins\":%u,\"mcp23008\":%s,\"ina219\":%s,\"powered\":%u"),
             chip_db_count, default_pins, (hal_status & 1) ? "true" : "false",
             (hal_status & 2) ? "true" : "false", tester_powered_pins());
    p_icc("limit_mA", trip_limit);
    p_icc("icc_mA", hal_icc());
    int16_t mv = hal_vbus_mv();
    if (mv >= 0) printf_P(PSTR(",\"vbus_mV\":%d"), mv);
    printf_P(PSTR("}\n"));
}

void cmd_exec(char *line)
{
    char *argv[4]; uint8_t argc = 0;
    for (char *t = strtok(line, " \t\r\n"); t && argc < 4; t = strtok(NULL, " \t\r\n")) argv[argc++] = t;
    if (!argc) return;
    for (char *s = argv[0]; *s; s++) *s = (char)toupper((unsigned char)*s);
    const char *c = argv[0];

    if (!strcmp(c, "HELP"))
        printf_P(PSTR("{\"commands\":[\"INFO\",\"LIST [pins]\",\"TEST <part>\",\"ID [pins]\",\"PINS <n>\",\"VEC <vector> [rep]\",\"OFF\",\"LIMIT <mA>\"]}\n"));
    else if (!strcmp(c, "INFO")) cmd_info();
    else if (!strcmp(c, "LIST")) cmd_list(argc > 1 ? atoi(argv[1]) : 0);
    else if (!strcmp(c, "TEST")) { if (argc < 2) err("TEST <part>"); else cmd_test(argv[1]); }
    else if (!strcmp(c, "ID")) {
        int n = argc > 1 ? atoi(argv[1]) : default_pins;
        if (!valid_pins(n)) err("pins must be 14/16/20/24"); else cmd_identify((uint8_t)n);
    }
    else if (!strcmp(c, "PINS")) {
        int n = argc > 1 ? atoi(argv[1]) : 0;
        if (!valid_pins(n)) err("pins must be 14/16/20/24");
        else { default_pins = (uint8_t)n; ui_ready(default_pins); printf_P(PSTR("{\"pins\":%u}\n"), n); }
    }
    else if (!strcmp(c, "VEC")) { if (argc < 2) err("VEC <vector> [rep]"); else cmd_vec(argv[1], argc > 2 ? atoi(argv[2]) : 1); }
    else if (!strcmp(c, "OFF")) { tester_power_down(); printf_P(PSTR("{\"powered\":0}\n")); }
    else if (!strcmp(c, "LIMIT")) {
        int ma = argc > 1 ? atoi(argv[1]) : 0;
        if (ma < 5 || ma > 300) err("limit 5..300 mA");
        else { trip_limit = (int16_t)(ma * 10); printf_P(PSTR("{\"limit_mA\":%d}\n"), ma); }
    }
    else err("unknown command");
}
