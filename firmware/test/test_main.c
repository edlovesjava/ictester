#include <stdio.h>
#include <string.h>
#include "../src/tester.h"
#include "../src/cmd.h"
#include "../src/ui.h"
#include "sim.h"

/* UI stubs */
void ui_ready(uint8_t p) { (void)p; }
void ui_busy(const char *n, uint8_t p) { (void)n; (void)p; }
void ui_test_result(uint8_t i, const result_t *r) { (void)i; (void)r; }
void ui_id_result(uint8_t p, uint8_t n, const uint8_t *f) { (void)p; (void)n; (void)f; }

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

/* ---------- simulated chips ---------- */
static const int8_t *L;
static int8_t in(uint8_t p) { return L[p]; }

/* 7400 */
static int8_t lv7400[25];
static void u7400(const int8_t *lv, const int8_t *pv) { (void)pv; memcpy(lv7400, lv, 25); }
static int8_t nand(int8_t a, int8_t b) { return (a == 1 && b == 1) ? 0 : 1; }
static int8_t d7400(uint8_t p)
{
    L = lv7400;
    switch (p) { case 3: return nand(in(1), in(2)); case 6: return nand(in(4), in(5));
                 case 8: return nand(in(9), in(10)); case 11: return nand(in(12), in(13)); }
    return -1;
}
static const sim_chip_t s7400 = {"7400", 14, 0, u7400, d7400};

/* 7474 */
static int8_t q1, q2;
static void r7474(void) { q1 = 1; q2 = 0; }       /* arbitrary power-up state */
static void u7474(const int8_t *v, const int8_t *pv)
{
    if (v[1] == 0) q1 = 0; else if (v[4] == 0) q1 = 1; else if (pv[3] == 0 && v[3] == 1) q1 = v[2];
    if (v[13] == 0) q2 = 0; else if (v[10] == 0) q2 = 1; else if (pv[11] == 0 && v[11] == 1) q2 = v[12];
}
static int8_t d7474(uint8_t p)
{
    switch (p) { case 5: return q1; case 6: return !q1; case 9: return q2; case 8: return !q2; }
    return -1;
}
static const sim_chip_t s7474 = {"7474", 14, r7474, u7474, d7474};

/* 4040: CLK 10 (falling), RST 11 */
static unsigned cnt4040;
static void r4040(void) { cnt4040 = 1234; }
static void u4040(const int8_t *v, const int8_t *pv)
{
    if (v[11] == 1) cnt4040 = 0;
    else if (pv[10] == 1 && v[10] == 0) cnt4040 = (cnt4040 + 1) & 0xFFF;
}
static int8_t d4040(uint8_t p)
{
    static const int8_t tap[17] = {0, 12, 6, 5, 7, 4, 3, 2, 0, 1, 0, 0, 9, 8, 10, 11, 0};
    if (p >= 17 || !tap[p]) return -1;
    return (int8_t)((cnt4040 >> (tap[p] - 1)) & 1);
}
static const sim_chip_t s4040 = {"4040", 16, r4040, u4040, d4040};

/* 74193 */
static int q193;
static void r193(void) { q193 = 7; }
static void u193(const int8_t *v, const int8_t *pv)
{
    if (v[14] == 1) { q193 = 0; return; }
    if (v[11] == 0) { q193 = (v[15] == 1) | (v[1] == 1) << 1 | (v[10] == 1) << 2 | (v[9] == 1) << 3; return; }
    if (pv[5] == 0 && v[5] == 1 && v[4] == 1) q193 = (q193 + 1) & 15;
    if (pv[4] == 0 && v[4] == 1 && v[5] == 1) q193 = (q193 - 1) & 15;
    L = v;
}
static int8_t lv193[25];
static void u193w(const int8_t *v, const int8_t *pv) { u193(v, pv); memcpy(lv193, v, 25); }
static int8_t d193(uint8_t p)
{
    switch (p) {
    case 3: return q193 & 1; case 2: return q193 >> 1 & 1; case 6: return q193 >> 2 & 1; case 7: return q193 >> 3 & 1;
    case 12: return (q193 == 15 && lv193[5] == 0) ? 0 : 1;
    case 13: return (q193 == 0 && lv193[4] == 0) ? 0 : 1;
    }
    return -1;
}
static const sim_chip_t s193 = {"74193", 16, r193, u193w, d193};

/* ---------- helpers ---------- */
static int nmatch; static char matches[256];
static void cb(uint8_t idx, const result_t *r, void *c)
{
    (void)r; (void)c;
    chip_t ch; tester_chip(idx, &ch);
    strcat(matches, ch.name); strcat(matches, " ");
    nmatch++;
}
static void identify(uint8_t pins) { nmatch = 0; matches[0] = 0; tester_identify(pins, cb, 0); }

static int run(const char *part, result_t *r)
{
    int idx = tester_find(part);
    if (idx < 0) return -1;
    tester_run((uint8_t)idx, r);
    return idx;
}

int main(void)
{
    result_t r;
    const sim_chip_t *own[] = {&s7400, &s7474, &s4040, &s193};

    for (unsigned i = 0; i < sizeof own / sizeof *own; i++) {
        sim_insert(own[i]);
        CHECK(run(own[i]->name, &r) >= 0 && r.pass, "%s own test: vec %u pin %u want %c got %c",
              own[i]->name, r.fail_vec, r.fail_pin, r.expected, r.got);
        identify(own[i]->pins);
        CHECK(nmatch == 1 && strncmp(matches, own[i]->name, strlen(own[i]->name)) == 0,
              "%s ID gave [%s]", own[i]->name, matches);
        printf("sim %-6s own test %s, ID -> [%s]\n", own[i]->name, r.pass ? "PASS" : "FAIL", matches);
    }

    /* faults */
    sim_insert(&s7400); sim_stuck_pin = 11; sim_stuck_val = 1;
    run("7400", &r);
    CHECK(!r.pass && r.fail_pin == 11, "stuck-at on 7400 pin 11 not caught");
    sim_insert(&s4040); sim_stuck_pin = 1; sim_stuck_val = 0;         /* Q12 stuck low */
    run("4040", &r);
    CHECK(!r.pass && r.fail_pin == 1, "4040 Q12 stuck-low not caught (needs >2048 clocks)");
    sim_insert(0);
    identify(14);
    CHECK(nmatch == 0, "empty socket matched [%s]", matches);
    sim_insert(&s7400); sim_icc = 2000;
    run("7400", &r);
    CHECK(r.tripped && !r.pass, "over-current not tripped");
    sim_icc = 42;

    /* part-number normalisation */
    struct { const char *in, *want; } pn[] = {
        {"SN74LS00N", "7400"}, {"74hc00", "7400"}, {"74LS03", "7400"}, {"CD4011BE", "4011"},
        {"4093", "4011"}, {"74HC4040", "4040"}, {"MC14013B", "4013"}, {"74LS161A", "74161"},
        {"74F163", "74161"}, {"DM7485N", "7485"}, {"HEF4066BP", "4066"}, {"74HCT595", "74595"},
    };
    for (unsigned i = 0; i < sizeof pn / sizeof *pn; i++) {
        int idx = tester_find(pn[i].in);
        chip_t ch; if (idx >= 0) tester_chip((uint8_t)idx, &ch);
        CHECK(idx >= 0 && !strcmp(ch.name, pn[i].want), "find(%s) -> %s", pn[i].in, idx >= 0 ? ch.name : "none");
    }
    CHECK(tester_find("74LS999") < 0, "bogus part found");

    /* a board that only takes 14-pin chips must refuse bigger packages
     * without ever powering the socket */
    sim_insert(&s7400); sim_max_pins = 14;
    {
        const char *refuse[] = {"ID 16", "TEST 4040", "VEC 0000000G0000000V", "PINS 16"};
        for (unsigned i = 0; i < sizeof refuse / sizeof *refuse; i++) {
            char line[64]; strcpy(line, refuse[i]);
            unsigned before = sim_power_ups;
            printf("> %s  (14-pin board)\n< ", refuse[i]); fflush(stdout);
            cmd_exec(line);
            CHECK(sim_power_ups == before, "'%s' powered the socket on a 14-pin board", refuse[i]);
        }
        CHECK(default_pins == 14, "PINS 16 accepted on a 14-pin board");
        char ok[] = "TEST 7400";
        unsigned before = sim_power_ups;
        printf("> %s  (14-pin board)\n< ", ok); fflush(stdout);
        cmd_exec(ok);
        CHECK(sim_power_ups > before, "TEST 7400 refused on a 14-pin board");
    }
    sim_max_pins = 24;

    /* the serial API, as the host sees it */
    puts("\n--- API transcript (sim 7400 inserted) ---");
    sim_insert(&s7400);
    const char *cmds[] = {"INFO", "TEST 74LS00", "TEST 7402", "ID 14", "VEC 00h00hGH00H00V",
                          "VEC 11H11HGH11H11V", "OFF", "PINS 16", "LIMIT 80", "BOGUS", "LIST 20"};
    for (unsigned i = 0; i < sizeof cmds / sizeof *cmds; i++) {
        char line[64]; strcpy(line, cmds[i]);
        printf("> %s\n< ", cmds[i]); fflush(stdout);
        cmd_exec(line);
    }

    printf("\n%s (%d failure%s)\n", fails ? "TESTS FAILED" : "ALL TESTS PASSED", fails, fails == 1 ? "" : "s");
    return fails != 0;
}
