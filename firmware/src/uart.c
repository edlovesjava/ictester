#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdio.h>
#include "config.h"
#include "uart.h"

#define RXSZ 64
static volatile uint8_t rxbuf[RXSZ], rxh, rxt;
static char line[96];
static uint8_t llen;

ISR(USART0_RX_vect)
{
    uint8_t c = UDR0, n = (uint8_t)((rxh + 1) % RXSZ);
    if (n != rxt) { rxbuf[rxh] = c; rxh = n; }
}

static int put(char c, FILE *f)
{
    (void)f;
    if (c == '\n') put('\r', f);
    while (!(UCSR0A & (1 << UDRE0))) ;
    UDR0 = (uint8_t)c;
    return 0;
}
static FILE out = FDEV_SETUP_STREAM(put, NULL, _FDEV_SETUP_WRITE);

void uart_init(void)
{
    /* U2X: UBRR = F_CPU/(8*baud) - 1 = 16.36 -> 16 -> 117 647 baud, +2.1 %
     * (the same error every 16 MHz Arduino runs at 115200) */
    UCSR0A = (1 << U2X0);
    UBRR0 = (uint16_t)((F_CPU + UART_BAUD * 4) / (8 * UART_BAUD) - 1);
    UCSR0B = (1 << RXEN0) | (1 << TXEN0) | (1 << RXCIE0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
    stdout = &out;
}

char *uart_getline(void)
{
    while (rxt != rxh) {
        char c = (char)rxbuf[rxt];
        rxt = (uint8_t)((rxt + 1) % RXSZ);
        if (c == '\r' || c == '\n') {
            if (!llen) continue;
            line[llen] = 0; llen = 0;
            return line;
        }
        if (llen < sizeof line - 1) line[llen++] = c;
    }
    return 0;
}
