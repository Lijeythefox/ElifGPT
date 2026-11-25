import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import ziglang

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
GEN = os.path.join(ROOT, "gen_web")
OBJ = os.path.join(ROOT, "build_web")
DOCS = os.path.join(ROOT, "docs")
WASM = os.path.join(DOCS, "elifgpt.wasm")
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


def main():
    if not os.path.exists(os.path.join(GEN, "stats.h")):
        sys.exit("gen_web/ is missing. Run: py gen.py --web")
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


if __name__ == "__main__":
    main()
