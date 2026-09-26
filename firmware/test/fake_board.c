/* Runs the real command handler against a simulated 7400 over stdin/stdout,
 * so the Python client can be exercised through a pty. */
#include <stdio.h>
#include <string.h>
#include "../src/cmd.h"
#include "../src/ui.h"
#include "sim.h"
void ui_ready(uint8_t p) { (void)p; }
void ui_busy(const char *n, uint8_t p) { (void)n; (void)p; }
void ui_test_result(uint8_t i, const result_t *r) { (void)i; (void)r; }
void ui_id_result(uint8_t p, uint8_t n, const uint8_t *f) { (void)p; (void)n; (void)f; }
static int8_t lv[25];
static void u(const int8_t *v, const int8_t *pv) { (void)pv; memcpy(lv, v, 25); }
static int8_t nand(int a, int b) { return (lv[a] == 1 && lv[b] == 1) ? 0 : 1; }
static int8_t d(uint8_t p) { switch (p) { case 3: return nand(1,2); case 6: return nand(4,5); case 8: return nand(9,10); case 11: return nand(12,13);} return -1; }
static const sim_chip_t s = {"7400", 14, 0, u, d};
int main(void)
{
    char line[128];
    setvbuf(stdout, NULL, _IOLBF, 0);
    sim_insert(&s);
    printf("{\"ready\":true,\"fw\":\"sim\"}\n");
    while (fgets(line, sizeof line, stdin)) cmd_exec(line);
    return 0;
}
