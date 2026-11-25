import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import ziglang

FULL = "--full" in sys.argv
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
GEN = os.path.join(ROOT, "gen" if FULL else "gen_web")
OBJ = os.path.join(ROOT, "build_web_full" if FULL else "build_web")
DOCS = os.path.join(ROOT, "docs")
FULL_DIR = os.path.join(DOCS, "full")
WASM = os.path.join(OBJ, "elifgpt-10m.wasm") if FULL else os.path.join(DOCS, "elifgpt.wasm")
PART_SIZE = 45 * 1024 * 1024
ZIG = os.path.join(os.path.dirname(ziglang.__file__), "zig.exe" if os.name == "nt" else "zig")
JOBS = int(os.environ.get("JOBS", os.cpu_count() or 4))
FLAGS = ["-target", "wasm32-wasi", "-O2", "-g0", "-w", "-std=gnu11"]


def compile_one(job):
    src, obj = job
    deps = [src, os.path.join(SRC, "elif.h"), os.path.join(SRC, "core.h"), os.path.join(GEN, "stats.h")]
    if os.path.exists(obj) and os.path.getmtime(obj) > max(os.path.getmtime(d) for d in deps):
        return src, None
    cmd = [ZIG, "cc", *FLAGS, "-I", SRC, "-I", GEN, "-c", src, "-o", obj]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return src, (p.stderr if p.returncode else None)


def split_full():
    os.makedirs(FULL_DIR, exist_ok=True)
    for f in os.listdir(FULL_DIR):
        if f.startswith("elifgpt-10m.part") or f == "manifest.json":
            os.remove(os.path.join(FULL_DIR, f))
    with open(os.path.join(GEN, "stats.h"), encoding="ascii") as f:
        stats = f.read()
    lines = re.search(r'ELIF_LINES_STR "([^"]+)"', stats).group(1)
    params = re.search(r'ELIF_PARAMS_STR "([^"]+)"', stats).group(1)
    parts = []
    with open(WASM, "rb") as src:
        i = 0
        while True:
            chunk = src.read(PART_SIZE)
            if not chunk:
                break
            name = f"elifgpt-10m.part{i:02d}"
            with open(os.path.join(FULL_DIR, name), "wb") as out:
                out.write(chunk)
            parts.append({"file": name, "size": len(chunk)})
            i += 1
    manifest = {"total": sum(p["size"] for p in parts), "lines": lines, "branches": params, "parts": parts}
    with open(os.path.join(FULL_DIR, "manifest.json"), "w", encoding="ascii") as f:
        json.dump(manifest, f, indent=2)
    print(f"split into {len(parts)} parts of up to {PART_SIZE // (1024 * 1024)} MB in {FULL_DIR}")


def main():
    if not os.path.exists(os.path.join(GEN, "stats.h")):
        sys.exit(f"{os.path.basename(GEN)}/ is missing. Run: py gen.py{'' if FULL else ' --web'}")
    os.makedirs(OBJ, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    os.environ.setdefault("ZIG_LOCAL_CACHE_DIR", os.path.join(OBJ, "zig-cache"))
    sources = [os.path.join(SRC, "web.c"), os.path.join(SRC, "core.c")]
    sources += sorted(os.path.join(GEN, f) for f in os.listdir(GEN) if f.endswith(".c"))
    jobs = [(s, os.path.join(OBJ, os.path.splitext(os.path.basename(s))[0] + ".o")) for s in sources]
    print(f"compiling {len(jobs)} files to wasm32-wasi with {JOBS} jobs")
    start = time.time()
    failed = []
    with ThreadPoolExecutor(JOBS) as pool:
        for i, (src, err) in enumerate(pool.map(compile_one, jobs), 1):
            if err:
                failed.append(src)
                print(f"\nFAILED {src}\n{err[:2000]}")
            print(f"  {i}/{len(jobs)} compiled ({time.time() - start:.0f}s)", end="\r")
    print()
    if failed:
        sys.exit(f"{len(failed)} file(s) failed to compile")
    with open(os.path.join(OBJ, "link.rsp"), "w", encoding="ascii") as f:
        f.write("\n".join(os.path.basename(o) for _, o in jobs) + "\n")
    print("linking...")
    cmd = [ZIG, "cc", *FLAGS, "-mexec-model=reactor", "-Wl,--strip-all", "-o", WASM, "@link.rsp"]
    p = subprocess.run(cmd, cwd=OBJ, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"link failed:\n{p.stderr[:4000]}")
    print(f"wrote {WASM} ({os.path.getsize(WASM) / (1024 * 1024):,.1f} MB) in {time.time() - start:.0f}s")
    if FULL:
        split_full()


if __name__ == "__main__":
    main()
