/* Front-panel hooks (OLED on the AVR, no-ops on the host test build).
 * Strings passed as `name` are PROGMEM. */
#pragma once
#include <stdint.h>
#include "tester.h"
void ui_ready(uint8_t pins);
void ui_busy(const char *name_P, uint8_t pins);
void ui_test_result(uint8_t idx, const result_t *r);
void ui_id_result(uint8_t pins, uint8_t nmatch, const uint8_t *first);
