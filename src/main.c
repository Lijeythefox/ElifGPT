#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#define nap(ms) Sleep(ms)
#else
#include <unistd.h>
#define nap(ms) usleep((ms) * 1000)
#endif

#include "core.h"
#include "stats.h"

int main(void)
{
    char raw[ELIF_MAXLEN];
    int interactive = 1;
#ifdef _WIN32
    DWORD mode;
    interactive = GetConsoleMode(GetStdHandle(STD_INPUT_HANDLE), &mode) != 0;
#else
    interactive = isatty(0);
#endif
    srand((unsigned)time(NULL));
    puts("============================================================");
    puts("  ElifGPT (C Edition)");
    printf("  Parameters: %s elif branches\n", ELIF_PARAMS_STR);
    printf("  Lines of C: %s\n", ELIF_LINES_STR);
    puts("  Neural networks: 0");
    puts("  Type 'bye' to leave.");
    puts("============================================================");
    for (;;) {
        printf("\nYou: ");
        fflush(stdout);
        if (!fgets(raw, sizeof raw, stdin)) {
            puts("\nElifGPT: Goodbye! (You can't just Ctrl+C an AI. That's rude.)");
            break;
        }
        raw[strcspn(raw, "\r\n")] = '\0';
        if (elif_is_bye(raw)) {
            puts("ElifGPT: Goodbye! I'll be here, in the elifs, forever.");
            break;
        }
        printf("thinking...\n");
        fflush(stdout);
        if (interactive)
            nap(300 + rand() % 600);
        printf("ElifGPT: %s\n", elif_expand(elif_reply(raw), 0));
    }
    return 0;
}
