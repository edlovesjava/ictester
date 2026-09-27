/* Front panel for boards without an OLED: the status LED is on while a test
 * or identify runs and off when the result is in. */
#include "ui.h"
#include "hal.h"

void ui_ready(uint8_t pins) { (void)pins; hal_led(0); }
void ui_busy(const char *name_P, uint8_t pins) { (void)name_P; (void)pins; hal_led(1); }
void ui_test_result(uint8_t idx, const result_t *r) { (void)idx; (void)r; hal_led(0); }
void ui_id_result(uint8_t pins, uint8_t nmatch, const uint8_t *first) { (void)pins; (void)nmatch; (void)first; hal_led(0); }
