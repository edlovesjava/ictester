#include <avr/io.h>
#include <avr/interrupt.h>
#include "config.h"
#include "hal.h"
#include "uart.h"
#include "cmd.h"
#include "ui.h"

#ifdef HAVE_PANEL                                 /* OLED + button boards */
#include <util/delay.h>
#include "ssd1306.h"

static const uint8_t pin_opts[] = {14, 16, 20, 24};

static void button(void)
{
    if (PINB & (1 << BTN_BIT)) return;
    _delay_ms(30);
    if (PINB & (1 << BTN_BIT)) return;
    uint16_t t = 0;
    while (!(PINB & (1 << BTN_BIT)) && t < 2000) { _delay_ms(10); t += 10; }
    if (t >= 700) {                               /* long press: next package size */
        uint8_t i = 0;
        while (pin_opts[i] != default_pins) i++;
        default_pins = pin_opts[(i + 1) & 3];
        ui_ready(default_pins);
    } else {
        cmd_identify(default_pins);               /* also reports on serial */
    }
    while (!(PINB & (1 << BTN_BIT))) ;
    _delay_ms(30);
}
#endif

int main(void)
{
    hal_status = hal_init();
    uart_init();
    sei();
#ifdef HAVE_PANEL
    oled_init();
#endif
    ui_ready(default_pins);
    printf_P(PSTR("{\"ready\":true,\"fw\":\"" FW_VERSION "\",\"mcp23008\":%s,\"ina219\":%s}\n"),
             (hal_status & 1) ? "true" : "false", (hal_status & 2) ? "true" : "false");
    for (;;) {
        char *l = uart_getline();
        if (l) cmd_exec(l);
#ifdef HAVE_PANEL
        button();
#endif
    }
}
