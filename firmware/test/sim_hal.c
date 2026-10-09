/* Simulated socket: a behavioural chip model wired to the ZIF exactly as the
 * real HAL is. Written independently of tools/chips.py so the host test
 * cross-checks the generator's assumptions (pin order, edges, pull-ups). */
#include <stdio.h>
#include <string.h>
#include "../src/hal.h"
#include "../src/tester.h"
#include "sim.h"

static uint8_t mode[41];
static uint8_t vcc_on, gnd_zif;
static int8_t lv[MAXPINS + 1], prv[MAXPINS + 1];
static const sim_chip_t *dut;
int16_t sim_icc = 42;                 /* 4.2 mA */
int8_t  sim_stuck_pin = 0, sim_stuck_val = 0;
uint8_t sim_max_pins = 24;
unsigned sim_power_ups;

static uint8_t powered(void) { return dut && vcc_on && gnd_zif == dut->pins / 2; }

static int8_t pin_of_zif(uint8_t z)
{
    if (!dut) return -1;
    for (uint8_t p = 1; p <= dut->pins; p++) if (zif_of(p, dut->pins) == z) return (int8_t)p;
    return -1;
}

static void settle(void)
{
    if (!powered()) return;
    for (uint8_t p = 1; p <= dut->pins; p++) {
        uint8_t m = mode[zif_of(p, dut->pins)];
        lv[p] = m == PM_LOW ? 0 : m == PM_HIGH ? 1 : m == PM_PULLUP ? 1 : -1;
    }
    dut->update(lv, prv);
    memcpy(prv, lv, sizeof lv);
}

void sim_insert(const sim_chip_t *c)
{
    dut = c;
    memset(prv, -1, sizeof prv);
    if (c && c->reset) c->reset();
    sim_stuck_pin = 0;
}

uint8_t hal_init(void) { return 3; }
void hal_pin(uint8_t z, uint8_t m) { mode[z] = m; settle(); }
void hal_all_hiz(void) { for (int z = 0; z < 41; z++) mode[z] = PM_HIZ; settle(); }
void hal_gnd(uint8_t z) { gnd_zif = z; settle(); }
void hal_vcc(uint8_t on) { if (on) sim_power_ups++; vcc_on = on; if (!on) memset(prv, -1, sizeof prv); settle(); }
int16_t hal_icc(void) { return powered() ? sim_icc : 0; }
int16_t hal_vbus_mv(void) { return vcc_on ? 4950 : 0; }
void hal_delay_us(uint16_t us) { (void)us; }
void hal_delay_ms(uint16_t ms) { (void)ms; }
void hal_led(uint8_t on) { (void)on; }
uint8_t hal_max_pins(void) { return sim_max_pins; }

uint8_t hal_read(uint8_t z)
{
    uint8_t m = mode[z];
    if (m == PM_LOW) return 0;
    if (m == PM_HIGH) return 1;
    int8_t p = pin_of_zif(z);
    if (p > 0 && powered()) {
        if (p == sim_stuck_pin) return (uint8_t)sim_stuck_val;
        int8_t d = dut->drive((uint8_t)p);
        if (d >= 0) return (uint8_t)d;
    }
    return m == PM_PULLUP ? 1 : 0;
}
