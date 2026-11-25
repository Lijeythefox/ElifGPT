#ifndef CORE_H
#define CORE_H

#define ELIF_MAXLEN 1024

const char *elif_reply(const char *raw);
const char *elif_expand(const char *r, int leave_clock_to_host);
int elif_is_bye(const char *raw);

#endif
