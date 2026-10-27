/* Exercise the actual firmware line assembler with stdin/stdout as UART I/O. */
#define main fixture_main
#include "main.c"
#undef main

int main(void)
{
    return fixture_main();
}
