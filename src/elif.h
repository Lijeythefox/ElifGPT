#ifndef ELIF_H
#define ELIF_H

#include <string.h>
#include <stddef.h>

extern const char *const RESP[];
extern unsigned long elif_ticks;
int has_word(const char *m, const char *w);

#define IS(s) (++elif_ticks, strcmp(m, (s)) == 0)
#define EQ(s) (++elif_ticks, strcmp(e, (s)) == 0)
#define HAS(s) (++elif_ticks, has_word(m, (s)))
#define R(i) (RESP[i])

#endif
