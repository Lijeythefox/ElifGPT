# ElifGPT

A chatbot made entirely of `if` / `else if` statements. No neural network, no machine learning, no lookup tables: every answer is a hardcoded branch in a very, very long chain of C.

- **CLI version:** about 10,000,000 lines of C, about 5,000,000 branches, a ~950 MB executable.
- **Web version:** about 1,000,000 lines of the same C, compiled to a ~30 MB WebAssembly module.

## How it works

`gen.py` writes the C source. It crosses templates ("do you like X", "how do i Y", "capital of Z", math, primes, Roman numerals, unit conversions...) with big vocab lists, adds "hey / so / yo ... bro / lol / pls" variants of each phrasing, and writes every combination out as its own `else if (strcmp(...) == 0)` branch.

| Path | What it is |
| --- | --- |
| `gen.py` | Generates the C source into `gen/` (CLI) or `gen_web/` (web) |
| `build_elifgpt.py` | The original Python version; `gen.py` reuses its topics and greetings |
| `src/core.c` | Shared logic: normalize input, knock-knock and name memory, run the brains, fallbacks |
| `src/main.c` | The terminal chat loop |
| `src/web.c` | WebAssembly exports for the browser |
| `build.py` | Compiles the CLI with Zig |
| `build_web.py` | Compiles the web version to `docs/elifgpt.wasm` |
| `docs/` | The static site (`index.html`, `style.css`, `app.js`, `elifgpt.wasm`) |

## Requirements

- Python 3.10+
- Zig, installed through pip:

  ```
  py -m pip install ziglang
  ```

## Build the CLI (10M lines)

```
py gen.py
py build.py
.\elifgpt.exe
```

Generating takes a couple of minutes, compiling about 5 minutes on 12 cores, and the build output takes about 5 GB of disk. For a quick ~300k-line test build, use `py gen.py --small`.

## Build the web version (1M lines)

```
py gen.py --web
py build_web.py
```

This writes `docs/elifgpt.wasm`, using `zig cc -target wasm32-wasi -O2`. To try it locally:

```
py -m http.server -d docs
```

Then open http://localhost:8000.

The page has no build step: `docs/index.html`, `docs/style.css` and `docs/app.js` are plain files. `app.js` loads the wasm with a tiny WASI shim (only `clock_time_get` is imported), writes your message into wasm memory, and calls `elif_respond()`. Time and date replies are filled in by JavaScript so they use your local time zone. The "checked N branches" line under each reply is a real counter, incremented by every `if` the C code evaluates.

## Publish on GitHub Pages

1. Commit `docs/` (including `docs/elifgpt.wasm`, which is about 30 MB and under GitHub's 100 MB file limit) and push to GitHub.
2. In the repository, go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
4. Pick your branch (for example `main`) and the **`/docs`** folder, then click **Save**.
5. After a minute or two the site is live at https://lijeythefox.github.io/ElifGPT/.

## Release the 10M-line version

The footer's "Download the full 10M-line version" link points to `/releases/latest`. To fill it, build the CLI and attach `elifgpt.exe` to a GitHub Release. It's about 950 MB, under GitHub's 2 GB limit for a release asset, but too big to commit to the repo itself.
