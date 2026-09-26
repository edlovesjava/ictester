#pragma once
#include <stdint.h>
extern uint8_t default_pins;
extern uint8_t hal_status;
void cmd_exec(char *line);
void cmd_identify(uint8_t pins);
