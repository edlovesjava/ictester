#pragma once
#include "compat.h"

/* vecs: nvec records of [rep byte][pins chars] */
typedef struct {
    const char    *name;
    const char    *aliases;   /* space separated part numbers sharing these vectors */
    const char    *desc;
    const uint8_t *vecs;
    uint16_t       nvec;
    uint8_t        pins;
} chip_t;

extern const chip_t  chip_db[] PROGMEM;
extern const uint8_t chip_db_count;
