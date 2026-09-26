#pragma once
#include <stdint.h>
typedef struct {
    const char *name;
    uint8_t pins;
    void   (*reset)(void);
    void   (*update)(const int8_t *lv, const int8_t *prev);   /* indexed by chip pin */
    int8_t (*drive)(uint8_t pin);                             /* -1 = not an output */
} sim_chip_t;
void sim_insert(const sim_chip_t *c);
extern int16_t sim_icc;
extern int8_t sim_stuck_pin, sim_stuck_val;
