#pragma once
#include <stdint.h>
#include "chips_db.h"

#define MAXPINS 24

typedef struct {
    uint8_t  pass;
    uint8_t  tripped;        /* over-current: power cut */
    uint16_t nvec;
    uint16_t fail_vec;       /* 0-based */
    uint8_t  fail_pin;       /* chip pin, 1-based */
    char     expected, got;
    int16_t  icc;            /* 0.1 mA, measured at the end of a passing run */
} result_t;

extern int16_t trip_limit;   /* 0.1 mA */

uint8_t zif_of(uint8_t chip_pin, uint8_t npins);
int8_t  tester_power_up(uint8_t npins);   /* 0 ok, -1 over-current */
void    tester_power_down(void);
uint8_t tester_powered_pins(void);        /* 0 when off */
uint8_t tester_apply(const char *vec, uint8_t n, uint8_t rep, char *actual);
void    tester_run(uint8_t idx, result_t *r);
int16_t tester_find(const char *part);    /* accepts 74LS00, SN74HC00N, CD4011BE, MC14011... */
void    tester_chip(uint8_t idx, chip_t *out);
typedef void (*match_cb)(uint8_t idx, const result_t *r, void *ctx);
uint8_t tester_identify(uint8_t npins, match_cb cb, void *ctx);  /* returns #tried */
