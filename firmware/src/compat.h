/* Lets the platform-independent parts (tester, cmd, chip DB) build on a PC for tests. */
#pragma once
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#else
#define PROGMEM
#define PSTR(s) (s)
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define memcpy_P memcpy
#define strcmp_P strcmp
#define strlen_P strlen
#define printf_P printf
#endif
