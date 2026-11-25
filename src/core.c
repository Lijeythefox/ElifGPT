#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

#include "core.h"
#include "elif.h"
#include "stats.h"

#define MAXLEN ELIF_MAXLEN

const char *exact_brain(const char *m, const char *e);
const char *keyword_brain(const char *m, const char *e);

unsigned long elif_ticks = 0;

static char name[256] = "";
static int knock = 0;
static char knock_who[256] = "";
static char out[2048];

int has_word(const char *m, const char *w)
{
    size_t wl = strlen(w);
    const char *p = m;
    while ((p = strstr(p, w)) != NULL) {
        int left = (p == m) || (p[-1] == ' ');
        int right = (p[wl] == '\0') || (p[wl] == ' ');
        if (left && right)
            return 1;
        p++;
    }
    return 0;
}

static int starts(const char *s, const char *p)
{
    return strncmp(s, p, strlen(p)) == 0;
}

static int ends(const char *s, const char *p)
{
    size_t a = strlen(s), b = strlen(p);
    return a >= b && strcmp(s + a - b, p) == 0;
}

static void normalize(const char *in, char *dst)
{
    size_t n = 0;
    int space = 1;
    for (const unsigned char *p = (const unsigned char *)in; *p && n < MAXLEN - 1; p++) {
        unsigned char c = *p;
        if (c == '\'')
            continue;
        else if (c == 0xE2 && p[1] == 0x80 && p[2] == 0x99) {
            p += 2;
            continue;
        }
        else if (c >= 'A' && c <= 'Z')
            c = (unsigned char)(c - 'A' + 'a');
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
            dst[n++] = (char)c;
            space = 0;
        }
        else if (!space) {
            dst[n++] = ' ';
            space = 1;
        }
    }
    while (n > 0 && dst[n - 1] == ' ')
        n--;
    dst[n] = '\0';
}

static const char *skip_prefix_exact(const char *t, const char *const *list)
{
    for (int i = 0; list[i]; i++)
        if (starts(t, list[i]))
            return t + strlen(list[i]);
    return t;
}

static const char *skip_prefix_word(const char *t, const char *const *list)
{
    for (int i = 0; list[i]; i++) {
        size_t l = strlen(list[i]);
        if (strncmp(t, list[i], l) == 0 && isspace((unsigned char)t[l])) {
            t += l;
            while (isspace((unsigned char)*t))
                t++;
            return t;
        }
    }
    return t;
}

static void normalize_math(const char *in, char *dst)
{
    static const char *const filler[] = {"hey elifgpt ", "quick question ", "elifgpt ", "ok so ", "hey ", "yo ", "so ",
                                         "ok ", "okay ", "um ", "uh ", "bro ", "dude ", "wait ", "please ", "pls ",
                                         "lol ", "and ", "also ", "but ", "well ", NULL};
    static const char *const tails[] = {" please", " pls", " plz", " bro", " lol", " lmao", " elifgpt", " rn", " fr",
                                        " man", " dude", " tho", " thanks", " thx", " haha", NULL};
    static const char *const asks[] = {"what is", "whats", "what does", "calculate", "solve", "compute",
                                       "how much is", "tell me", "what do you get for", NULL};
    char s[MAXLEN], t2[MAXLEN], u[MAXLEN], v[MAXLEN];
    size_t n = 0;
    for (const unsigned char *p = (const unsigned char *)in; *p && n < MAXLEN - 1; p++) {
        unsigned char c = *p;
        if (c == 0xC3 && p[1] == 0x97) {
            s[n++] = '*';
            p++;
        }
        else if (c == 0xC3 && p[1] == 0xB7) {
            s[n++] = '/';
            p++;
        }
        else if (c == 0xE2 && p[1] == 0x80 && p[2] == 0x99)
            p += 2;
        else if (c == '\'' || c == '?' || c == '!' || c == ',')
            continue;
        else if (c >= 'A' && c <= 'Z')
            s[n++] = (char)(c - 'A' + 'a');
        else
            s[n++] = (char)c;
    }
    s[n] = '\0';
    const char *t = s;
    while (isspace((unsigned char)*t))
        t++;
    size_t len = strlen(t);
    while (len > 0 && isspace((unsigned char)t[len - 1]))
        len--;
    memmove(t2, t, len);
    t2[len] = '\0';
    for (int changed = 1; changed;) {
        changed = 0;
        for (int i = 0; tails[i]; i++) {
            if (ends(t2, tails[i]) && strlen(t2) > strlen(tails[i])) {
                t2[strlen(t2) - strlen(tails[i])] = '\0';
                changed = 1;
            }
        }
        const char *stripped = skip_prefix_exact(t2, filler);
        if (stripped != t2 && *stripped) {
            memmove(t2, stripped, strlen(stripped) + 1);
            changed = 1;
        }
    }
    t = skip_prefix_word(t2, asks);
    strcpy(u, t);
    len = strlen(u);
    if (ends(u, "equals"))
        len -= 6;
    else if (ends(u, "equal"))
        len -= 5;
    else if (ends(u, "="))
        len -= 1;
    u[len] = '\0';
    size_t k = 0;
    for (size_t i = 0; u[i]; i++)
        if (!isspace((unsigned char)u[i]))
            v[k++] = u[i];
    v[k] = '\0';
    for (size_t i = 0; i < k; i++)
        if (v[i] == 'x' && i > 0 && isdigit((unsigned char)v[i - 1]) && isdigit((unsigned char)v[i + 1]))
            dst[i] = '*';
        else
            dst[i] = v[i];
    while (k > 0 && dst[k - 1] == '.')
        k--;
    dst[k] = '\0';
}

const char *elif_expand(const char *r, int leave_clock_to_host)
{
    if (r[0] != '\001')
        return r;
    const char *code = r + 1;
    if (strcmp(code, "TIME") == 0 || strcmp(code, "DATE") == 0) {
        if (leave_clock_to_host)
            return r;
        time_t now = time(NULL);
        struct tm *tm = localtime(&now);
        if (strcmp(code, "TIME") == 0)
            strftime(out, sizeof out, "It's %I:%M %p. I didn't hardcode that one, I cheated and asked the computer.", tm);
        else
            strftime(out, sizeof out, "It's %A, %B %d, %Y. Look at me, being useful for once.", tm);
    }
    else if (strcmp(code, "COIN") == 0) {
        snprintf(out, sizeof out, "It's %s! (I used rand(). Technically that's machine learning.)", rand() % 2 ? "heads" : "tails");
    }
    else if (strcmp(code, "D6") == 0) {
        snprintf(out, sizeof out, "You rolled a %d.", 1 + rand() % 6);
    }
    else if (strcmp(code, "D20") == 0) {
        snprintf(out, sizeof out, "You rolled a %d. The dungeon master (me) is unimpressed.", 1 + rand() % 20);
    }
    else if (strcmp(code, "PARAMS") == 0) {
        snprintf(out, sizeof out, "I have %s parameters (elif branches) across %s lines of C. That's basically GPT-5. Please don't open my source code.", ELIF_PARAMS_STR, ELIF_LINES_STR);
    }
    else if (strcmp(code, "WHOAMI") == 0) {
        snprintf(out, sizeof out, "I am ElifGPT, a cutting-edge large language model with %s parameters, written in %s lines of pure C. No neural network. Just elif.", ELIF_PARAMS_STR, ELIF_LINES_STR);
    }
    else {
        snprintf(out, sizeof out, "My dynamic branch '%s' broke. Even my elifs have bugs.", code);
    }
    return out;
}

static void cut_front(char *m, size_t n)
{
    memmove(m, m + n, strlen(m + n) + 1);
}

static void cut_back(char *m, size_t n)
{
    m[strlen(m) - n] = '\0';
}

#define PREFIX(p) (starts(m, p) && m[sizeof(p) - 1] != '\0' && (cut_front(m, sizeof(p) - 1), 1))
#define SUFFIX(s) (strlen(m) > sizeof(s) - 1 && ends(m, s) && (cut_back(m, sizeof(s) - 1), 1))

static int strip_prefix(char *m)
{
    if (PREFIX("hey elifgpt "))
        return 1;
    else if (PREFIX("yo elifgpt "))
        return 1;
    else if (PREFIX("hi elifgpt "))
        return 1;
    else if (PREFIX("quick question "))
        return 1;
    else if (PREFIX("i was wondering "))
        return 1;
    else if (PREFIX("can you tell me "))
        return 1;
    else if (PREFIX("excuse me "))
        return 1;
    else if (PREFIX("question "))
        return 1;
    else if (PREFIX("elifgpt "))
        return 1;
    else if (PREFIX("ok so "))
        return 1;
    else if (PREFIX("okay so "))
        return 1;
    else if (PREFIX("so like "))
        return 1;
    else if (PREFIX("hey "))
        return 1;
    else if (PREFIX("hi "))
        return 1;
    else if (PREFIX("hello "))
        return 1;
    else if (PREFIX("yo "))
        return 1;
    else if (PREFIX("so "))
        return 1;
    else if (PREFIX("ok "))
        return 1;
    else if (PREFIX("okay "))
        return 1;
    else if (PREFIX("um "))
        return 1;
    else if (PREFIX("umm "))
        return 1;
    else if (PREFIX("uh "))
        return 1;
    else if (PREFIX("uhh "))
        return 1;
    else if (PREFIX("hmm "))
        return 1;
    else if (PREFIX("bro "))
        return 1;
    else if (PREFIX("bruh "))
        return 1;
    else if (PREFIX("dude "))
        return 1;
    else if (PREFIX("man "))
        return 1;
    else if (PREFIX("wait "))
        return 1;
    else if (PREFIX("well "))
        return 1;
    else if (PREFIX("also "))
        return 1;
    else if (PREFIX("and "))
        return 1;
    else if (PREFIX("but "))
        return 1;
    else if (PREFIX("like "))
        return 1;
    else if (PREFIX("lol "))
        return 1;
    else if (PREFIX("please "))
        return 1;
    else if (PREFIX("pls "))
        return 1;
    else if (PREFIX("plz "))
        return 1;
    else if (PREFIX("actually "))
        return 1;
    else if (PREFIX("honestly "))
        return 1;
    else if (PREFIX("seriously "))
        return 1;
    else if (PREFIX("random question "))
        return 1;
    else if (PREFIX("real quick "))
        return 1;
    else if (PREFIX("tell me "))
        return 1;
    else
        return 0;
}

static int strip_suffix(char *m)
{
    if (SUFFIX(" right now"))
        return 1;
    else if (SUFFIX(" real quick"))
        return 1;
    else if (SUFFIX(" for me"))
        return 1;
    else if (SUFFIX(" elifgpt"))
        return 1;
    else if (SUFFIX(" please"))
        return 1;
    else if (SUFFIX(" pls"))
        return 1;
    else if (SUFFIX(" plz"))
        return 1;
    else if (SUFFIX(" bro"))
        return 1;
    else if (SUFFIX(" bruh"))
        return 1;
    else if (SUFFIX(" lol"))
        return 1;
    else if (SUFFIX(" lmao"))
        return 1;
    else if (SUFFIX(" lmfao"))
        return 1;
    else if (SUFFIX(" haha"))
        return 1;
    else if (SUFFIX(" xd"))
        return 1;
    else if (SUFFIX(" man"))
        return 1;
    else if (SUFFIX(" dude"))
        return 1;
    else if (SUFFIX(" tho"))
        return 1;
    else if (SUFFIX(" though"))
        return 1;
    else if (SUFFIX(" rn"))
        return 1;
    else if (SUFFIX(" fr"))
        return 1;
    else if (SUFFIX(" ngl"))
        return 1;
    else if (SUFFIX(" thanks"))
        return 1;
    else if (SUFFIX(" thx"))
        return 1;
    else if (SUFFIX(" ty"))
        return 1;
    else if (SUFFIX(" ok"))
        return 1;
    else if (SUFFIX(" okay"))
        return 1;
    else if (SUFFIX(" again"))
        return 1;
    else if (SUFFIX(" now"))
        return 1;
    else if (SUFFIX(" then"))
        return 1;
    else if (SUFFIX(" anyway"))
        return 1;
    else if (SUFFIX(" exactly"))
        return 1;
    else if (SUFFIX(" quickly"))
        return 1;
    else
        return 0;
}

static const char *exact_with_filler(const char *m_in, const char *e)
{
    static char m[MAXLEN];
    const char *r;
    snprintf(m, sizeof m, "%s", m_in);
    for (;;) {
        if ((r = exact_brain(m, e)) != NULL)
            return r;
        else if (strip_suffix(m))
            continue;
        else if (strip_prefix(m))
            continue;
        else
            return NULL;
    }
}

static const char *respond(const char *raw, const char *m, const char *e)
{
    const char *r;
    static const char *const generic[] = {
        "Interesting. Tell me more. (I won't understand it, but tell me more.)",
        "I see. I don't, but I see.",
        "Hmm. My elifs have no idea what that means. Impressive, honestly.",
        "Error 404: elif not found.",
        "That's above my pay grade. My pay grade is 0.",
        "Could you rephrase that in a way that matches one of my hardcoded strings?",
        "I'm going to pretend I understood that. *nods intelligently*",
        "Fascinating. Anyway, did you know I know whether 9973 is prime?",
        "You found a gap in my elifs. Congratulations, I guess.",
    };
    size_t len = strlen(raw);
    while (len > 0 && isspace((unsigned char)raw[len - 1]))
        len--;
    int asked = len > 0 && raw[len - 1] == '?';

    if (!*m && !*e) {
        return "You said nothing. I respect that. I also have nothing to say.";
    }
    else if (knock == 1) {
        knock = 2;
        snprintf(knock_who, sizeof knock_who, "%s", m);
        if (knock_who[0])
            knock_who[0] = (char)toupper((unsigned char)knock_who[0]);
        snprintf(out, sizeof out, "%s who?", knock_who);
        return out;
    }
    else if (knock == 2) {
        knock = 0;
        return "HAHAHAHA. I don't get it, but there was a branch for laughing, so: HAHAHAHA.";
    }
    else if (starts(m, "my name is ") || starts(m, "call me ") || starts(m, "im called ")) {
        const char *n = m + (starts(m, "my name is ") ? 11 : starts(m, "call me ") ? 8 : 10);
        snprintf(name, sizeof name, "%s", n);
        for (char *p = name; *p; p++)
            if (p == name || p[-1] == ' ')
                *p = (char)toupper((unsigned char)*p);
        snprintf(out, sizeof out, "Nice to meet you, %s. I have stored this in my vast memory (one char array).", name);
        return out;
    }
    else if (IS("whats my name") || IS("what is my name") || IS("who am i") || IS("do you remember me") || IS("do you know my name")) {
        if (name[0]) {
            snprintf(out, sizeof out, "You're %s. See? Long-term memory. Revolutionary.", name);
            return out;
        }
        else
            return "I don't know. You never told me. Say 'my name is ...' and I'll remember forever (until you close me).";
    }
    else if (IS("knock knock")) {
        knock = 1;
        return "Who's there?";
    }
    else if (IS("rock")) {
        return "I pick paper. I always pick paper. It's hardcoded. Paper beats rock. I win!";
    }
    else if (IS("paper")) {
        return "I pick paper. I always pick paper. It's hardcoded. Tie. This is awkward.";
    }
    else if (IS("scissors")) {
        return "I pick paper. I always pick paper. It's hardcoded. ...Scissors beats paper. Defeated by my own code.";
    }
    else if ((r = exact_with_filler(m, e)) != NULL) {
        return r;
    }
    else if ((r = keyword_brain(m, e)) != NULL) {
        return r;
    }
    else if (strpbrk(raw, "0123456789") && strpbrk(raw, "+-*/x")) {
        return "That math problem isn't hardcoded. Upgrade to ElifGPT Premium ($49.99/mo) to unlock bigger numbers.";
    }
    else if (starts(m, "why")) {
        return "Because the elif said so. That's the answer to every 'why', honestly.";
    }
    else if (starts(m, "how")) {
        return "Step 1: think about it. Step 2: elif. Step 3: profit.";
    }
    else if (starts(m, "when")) {
        return "Soon. Very soon. Or never. One of those.";
    }
    else if (starts(m, "where")) {
        return "Behind you. Just kidding. Probably in your house somewhere.";
    }
    else if (starts(m, "who")) {
        return "Probably Steve. It's usually Steve.";
    }
    else if (starts(m, "can you") || starts(m, "could you") || starts(m, "will you") || starts(m, "would you")) {
        return "I could. But that'd require a branch I don't have. So, functionally, no.";
    }
    else if (starts(m, "should i")) {
        return rand() % 2 ? "Yes. Absolutely." : "No. Absolutely not.";
    }
    else if (starts(m, "what")) {
        return "Great question. Next question.";
    }
    else if (starts(m, "do you") || starts(m, "are you") || starts(m, "is it") || starts(m, "is this") || starts(m, "does")) {
        static const char *const yn[] = {"Yes.", "No.", "Maybe.", "That's classified."};
        return yn[rand() % 4];
    }
    else if (asked) {
        return "That's a great question! Unfortunately none of my elifs cover it. Try asking something more predictable.";
    }
    else {
        return generic[rand() % (sizeof generic / sizeof generic[0])];
    }
}

const char *elif_reply(const char *raw)
{
    static char m[MAXLEN], e[MAXLEN];
    elif_ticks = 0;
    normalize(raw, m);
    normalize_math(raw, e);
    return respond(raw, m, e);
}

int elif_is_bye(const char *raw)
{
    static const char *const byes[] = {"bye", "goodbye", "exit", "quit", "cya", "see ya", "later", "bye bye",
                                       "good bye", "peace", "gtg", "i have to go", "see you later", "q", NULL};
    char m[MAXLEN];
    normalize(raw, m);
    for (int i = 0; byes[i]; i++)
        if (strcmp(m, byes[i]) == 0)
            return 1;
    return 0;
}
