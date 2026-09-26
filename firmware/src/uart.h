#pragma once
#include <stdint.h>
void uart_init(void);          /* also binds stdout */
char *uart_getline(void);      /* non-blocking: returns a complete line or NULL */
