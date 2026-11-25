#include <stdlib.h>

#include "core.h"
#include "elif.h"
#include "stats.h"

#define EXPORT(name) __attribute__((export_name(name)))

static char input[ELIF_MAXLEN];

EXPORT("elif_input")
char *elif_input(void)
{
    return input;
}

EXPORT("elif_capacity")
int elif_capacity(void)
{
    return ELIF_MAXLEN;
}

EXPORT("elif_seed")
void elif_seed(unsigned seed)
{
    srand(seed);
}

EXPORT("elif_respond")
const char *elif_respond(const char *in)
{
    if (elif_is_bye(in)) {
        elif_ticks = 0;
        return "Goodbye! I'll be here, in the elifs, forever. (You can keep typing. I'm a web page. I can't actually leave.)";
    }
    return elif_expand(elif_reply(in), 1);
}

EXPORT("elif_branches")
unsigned elif_branches(void)
{
    return (unsigned)elif_ticks;
}

EXPORT("elif_params")
const char *elif_params(void)
{
    return ELIF_PARAMS_STR;
}

EXPORT("elif_lines")
const char *elif_lines(void)
{
    return ELIF_LINES_STR;
}
