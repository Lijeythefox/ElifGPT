import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import ziglang

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
GEN = os.path.join(ROOT, "gen")
OBJ = os.path.join(ROOT, "build")
ZIG = os.path.join(os.path.dirname(ziglang.__file__), "zig.exe" if os.name == "nt" else "zig")
JOBS = int(os.environ.get("JOBS", os.cpu_count() or 4))
EXE = os.environ.get("ELIF_EXE") or os.path.join(ROOT, "elifgpt.exe" if os.name == "nt" else "elifgpt")


def compile_one(job):
    src, obj = job
    deps = [src, os.path.join(SRC, "elif.h"), os.path.join(SRC, "core.h")]
    if src.endswith(("main.c", "core.c")):
        deps.append(os.path.join(GEN, "stats.h"))
    if os.path.exists(obj) and os.path.getmtime(obj) > max(os.path.getmtime(d) for d in deps):
        return src, 0.0, None
    t = time.time()
    cmd = [ZIG, "cc", "-O0", "-w", "-std=gnu11", "-I", SRC, "-I", GEN, "-c", src, "-o", obj]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return src, time.time() - t, (p.stderr if p.returncode else None)


def main():
    os.makedirs(OBJ, exist_ok=True)
    os.environ.setdefault("ZIG_LOCAL_CACHE_DIR", os.path.join(OBJ, "zig-cache"))
    sources = [os.path.join(SRC, "main.c"), os.path.join(SRC, "core.c")] + sorted(os.path.join(GEN, f) for f in os.listdir(GEN) if f.endswith(".c"))
    jobs = [(s, os.path.join(OBJ, os.path.splitext(os.path.basename(s))[0] + ".o")) for s in sources]
    print(f"compiling {len(jobs)} files with {JOBS} jobs using {ZIG}")
    start = time.time()
    failed = []
    with ThreadPoolExecutor(JOBS) as pool:
        for i, (src, dt, err) in enumerate(pool.map(compile_one, jobs), 1):
            if err:
                failed.append((src, err))
                print(f"\nFAILED {src}\n{err[:2000]}")
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} compiled ({time.time() - start:.0f}s)", end="\r")
    print()
    if failed:
        sys.exit(f"{len(failed)} file(s) failed to compile")
    objs = [os.path.basename(o) for _, o in jobs]
    rsp = os.path.join(OBJ, "link.rsp")
    with open(rsp, "w", encoding="ascii") as f:
        f.write("\n".join(objs) + "\n")
    print("linking...")
    t = time.time()
    p = subprocess.run([ZIG, "cc", "-O0", "-o", EXE, "@link.rsp"], cwd=OBJ, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"link failed:\n{p.stderr[:4000]}")
    size = os.path.getsize(EXE) / (1024 * 1024)
    print(f"linked {EXE} ({size:,.1f} MB) in {time.time() - t:.0f}s; total {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
