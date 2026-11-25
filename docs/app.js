(() => {
  "use strict";

  const LITE_URL = "elifgpt.wasm";
  const FULL_MANIFEST = "full/manifest.json";
  const EXAMPLES = [
    "is 99991 prime?",
    "what's 287 x 143",
    "who is socrates",
    "how do i exit vim",
    "pizza or tacos",
    "capital of mongolia",
    "1999 in roman numerals",
    "100 km to miles",
    "knock knock",
    "do you like capybaras",
    "how many parameters do you have",
    "tell me a joke",
  ];
  const CHIPS = ["is 99991 prime?", "pizza or tacos", "who is socrates", "how do i exit vim"];
  const CYCLE_MS = 3000;
  const MAX_LINES = 5;
  const LOGO_SVG =
    '<svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">' +
    '<g class="stem" fill="none" stroke="currentColor" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M16 28.5V18"/><path d="M16 18c0-5-7.5-4.5-7.5-10"/><path d="M16 18V8"/><path d="M16 18c0-5 7.5-4.5 7.5-10"/></g>' +
    '<g fill="currentColor"><circle class="node" cx="8.5" cy="5.6" r="2.7"/><circle class="node" cx="16" cy="4.8" r="2.7"/>' +
    '<circle class="node" cx="23.5" cy="5.6" r="2.7"/></g></svg>';

  const $ = (id) => document.getElementById(id);
  const body = document.body;
  const input = $("input");
  const send = $("send");
  const form = $("composer");
  const ghost = $("ghost");
  const ghostText = $("ghost-text");
  const chips = $("chips");
  const dock = $("dock");
  const tabs = [...document.querySelectorAll(".tab")];
  const gate = $("gate");
  const gateAck = $("gate-ack");
  const gateLoad = $("gate-load");

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)");
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const engines = {
    lite: { key: "lite", state: "idle", exports: null, memory: null, log: $("log-lite"), busy: false },
    full: { key: "full", state: "idle", exports: null, memory: null, log: $("log-full"), busy: false },
  };
  let active = engines.lite;
  let suggestion = 0;
  let manifest = null;

  function syncDockHeight() {
    document.documentElement.style.setProperty("--dock-h", `${dock.offsetHeight}px`);
  }
  new ResizeObserver(syncDockHeight).observe(dock);
  syncDockHeight();

  function wasiImports(engine) {
    const wasi = {
      clock_time_get(_id, _precision, ptr) {
        new DataView(engine.memory.buffer).setBigUint64(ptr, BigInt(Date.now()) * 1000000n, true);
        return 0;
      },
      random_get(ptr, len) {
        crypto.getRandomValues(new Uint8Array(engine.memory.buffer, ptr, len));
        return 0;
      },
      proc_exit(code) {
        throw new Error(`wasm exited with code ${code}`);
      },
    };
    return {
      wasi_snapshot_preview1: new Proxy(wasi, {
        get: (target, name) => target[name] || (() => 52),
      }),
    };
  }

  async function fetchWithProgress(url, onProgress) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const total = Number(res.headers.get("content-length")) || 0;
    if (!res.body || !total) {
      onProgress(-1);
      return new Uint8Array(await res.arrayBuffer());
    }
    const reader = res.body.getReader();
    const chunks = [];
    let received = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      received += value.length;
      onProgress(Math.min(received / total, 1));
    }
    const bytes = new Uint8Array(received);
    let offset = 0;
    for (const c of chunks) {
      bytes.set(c, offset);
      offset += c.length;
    }
    return bytes;
  }

  function partsStream(parts, total, onProgress) {
    let index = 0;
    let reader = null;
    let loaded = 0;
    return new ReadableStream({
      async pull(controller) {
        for (;;) {
          if (!reader) {
            if (index >= parts.length) {
              controller.close();
              return;
            }
            const res = await fetch(`full/${parts[index++].file}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            reader = res.body.getReader();
          }
          const { done, value } = await reader.read();
          if (done) {
            reader = null;
            continue;
          }
          loaded += value.length;
          onProgress(loaded, total);
          controller.enqueue(value);
          return;
        }
      },
    });
  }

  async function start(engine, module) {
    const instance = await WebAssembly.instantiate(module, wasiImports(engine));
    engine.exports = instance.exports;
    engine.memory = instance.exports.memory;
    if (engine.exports._initialize) engine.exports._initialize();
    engine.exports.elif_seed((Math.random() * 0xffffffff) >>> 0);
    engine.state = "ready";
  }

  async function loadLite() {
    const engine = engines.lite;
    const bar = $("bar");
    const fill = $("bar-fill");
    engine.state = "loading";
    try {
      const bytes = await fetchWithProgress(LITE_URL, (p) => {
        if (p < 0) bar.classList.add("is-indeterminate");
        else fill.style.width = `${Math.round(p * 100)}%`;
      });
      bar.classList.remove("is-indeterminate");
      fill.style.width = "100%";
      await start(engine, await WebAssembly.compile(bytes));
    } catch (err) {
      console.error(err);
      engine.state = "error";
      $("loading").classList.add("is-error");
      bar.hidden = true;
      $("loading-text").textContent = "Couldn't load the elifs. Refresh the page to try again.";
    }
    render();
  }

  async function getManifest() {
    if (manifest) return manifest;
    const res = await fetch(FULL_MANIFEST);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    manifest = await res.json();
    $("gate-size").textContent = Math.round(manifest.total / (1024 * 1024)).toLocaleString("en-US");
    $("gate-lines").textContent = manifest.lines;
    return manifest;
  }

  async function loadFull() {
    const engine = engines.full;
    if (engine.state === "loading" || engine.state === "ready") return;
    engine.state = "loading";
    const fill = $("full-bar-fill");
    const bar = $("full-bar");
    const text = $("full-loading-text");
    $("gate-progress").hidden = false;
    gateLoad.disabled = true;
    gateAck.disabled = true;
    render();
    const mb = (n) => (n / (1024 * 1024)).toFixed(0);
    try {
      const m = await getManifest();
      text.textContent = `downloading 0 of ${mb(m.total)} MB...`;
      const stream = partsStream(m.parts, m.total, (loaded, total) => {
        fill.style.width = `${Math.round((loaded / total) * 100)}%`;
        text.textContent = loaded < total
          ? `downloading ${mb(loaded)} of ${mb(total)} MB...`
          : `compiling ${m.lines} lines of elif. This is the heavy part...`;
      });
      let module;
      if (WebAssembly.compileStreaming) {
        module = await WebAssembly.compileStreaming(new Response(stream, { headers: { "Content-Type": "application/wasm" } }));
      } else {
        module = await WebAssembly.compile(await new Response(stream).arrayBuffer());
      }
      text.textContent = "starting up...";
      bar.classList.add("is-indeterminate");
      await start(engine, module);
    } catch (err) {
      console.error(err);
      engine.state = "error";
      bar.hidden = true;
      text.textContent = "The 10M version didn't load. Your browser may have run out of memory. Reload the page to try again, or use Lite.";
      $("gate-progress").classList.add("is-error");
    }
    render();
    if (active === engine && engine.state === "ready" && canHover.matches) input.focus();
  }

  function readCString(engine, ptr) {
    const view = new Uint8Array(engine.memory.buffer);
    let end = ptr;
    while (view[end] !== 0) end++;
    return decoder.decode(view.subarray(ptr, end));
  }

  function expandHostReply(text) {
    if (text.charCodeAt(0) !== 1) return text;
    const now = new Date();
    const code = text.slice(1);
    if (code === "TIME") {
      const t = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
      return `It's ${t}. I didn't hardcode that one, I cheated and asked the computer.`;
    }
    if (code === "DATE") {
      const d = now.toLocaleDateString([], { weekday: "long", year: "numeric", month: "long", day: "numeric" });
      return `It's ${d}. Look at me, being useful for once.`;
    }
    return `My dynamic branch '${code}' broke. Even my elifs have bugs.`;
  }

  function ask(engine, text) {
    const x = engine.exports;
    const cap = x.elif_capacity() - 1;
    let bytes = encoder.encode(text);
    if (bytes.length > cap) bytes = bytes.subarray(0, cap);
    const ptr = x.elif_input();
    const view = new Uint8Array(engine.memory.buffer);
    view.set(bytes, ptr);
    view[ptr + bytes.length] = 0;
    const t0 = performance.now();
    const out = x.elif_respond(ptr);
    const ms = performance.now() - t0;
    return { text: expandHostReply(readCString(engine, out)), branches: x.elif_branches(), ms };
  }

  function formatMs(ms) {
    if (ms < 0.1) return "under 0.1 ms";
    if (ms < 1) return `${ms.toFixed(1)} ms`;
    if (ms < 10) return `${ms.toFixed(1)} ms`;
    return `${Math.round(ms)} ms`;
  }

  function scrollToEnd() {
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: reducedMotion.matches ? "auto" : "smooth" });
  }

  function addUser(log, text) {
    const el = document.createElement("div");
    el.className = "msg msg-user";
    el.textContent = text;
    log.append(el);
  }

  function addThinking(log) {
    const el = document.createElement("div");
    el.className = "msg msg-bot thinking";
    el.setAttribute("aria-label", "ElifGPT is thinking");
    el.innerHTML = `${LOGO_SVG}<span>thinking<span class="dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span></span>`;
    log.append(el);
    return el;
  }

  function fillReply(el, reply) {
    el.className = "msg msg-bot";
    el.removeAttribute("aria-label");
    el.textContent = reply.text;
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    const t = formatMs(reply.ms);
    if (reply.branches === 0) {
      meta.textContent = `answered from memory, no branches needed (${t})`;
    } else {
      const count = document.createElement("b");
      count.textContent = reply.branches.toLocaleString("en-US");
      meta.append("checked ", count, ` branch${reply.branches === 1 ? "" : "es"} in ${t}`);
    }
    el.append(meta);
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const nextFrame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

  async function submit(text) {
    const engine = active;
    text = text.trim();
    if (!text || engine.busy || engine.state !== "ready") return;
    engine.busy = true;
    addUser(engine.log, text);
    input.value = "";
    autosize();
    render();
    const thinking = addThinking(engine.log);
    scrollToEnd();
    const started = performance.now();
    await nextFrame();
    let reply;
    try {
      reply = ask(engine, text);
    } catch (err) {
      console.error(err);
      reply = { text: "Something broke inside my elifs. Refresh the page and try again.", branches: 0, ms: 0 };
    }
    const wait = 400 + Math.random() * 500 - (performance.now() - started);
    if (wait > 0) await sleep(wait);
    fillReply(thinking, reply);
    engine.busy = false;
    render();
    if (active === engine) scrollToEnd();
  }

  function autosize() {
    input.style.height = "24px";
    const max = 24 * MAX_LINES;
    const h = Math.min(input.scrollHeight - 12, max);
    input.style.height = `${Math.max(24, h)}px`;
    input.style.overflowY = input.scrollHeight - 12 > max ? "auto" : "hidden";
  }

  function render() {
    const ready = active.state === "ready";
    const empty = active.log.childElementCount === 0;
    body.classList.toggle("is-empty", empty);
    body.dataset.engine = active.key;
    for (const t of tabs) {
      const on = t.dataset.engine === active.key;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    }
    engines.lite.log.hidden = active !== engines.lite;
    engines.full.log.hidden = active !== engines.full;
    $("loading").hidden = !(active === engines.lite && engines.lite.state !== "ready");
    gate.hidden = !(active === engines.full && engines.full.state !== "ready");
    chips.hidden = !(ready && empty);
    input.disabled = !ready;
    input.setAttribute(
      "aria-label",
      ready ? `Message ElifGPT ${active === engines.full ? "Full" : "Lite"}` : "Message ElifGPT (not loaded yet)",
    );
    send.disabled = !ready || active.busy || input.value.trim().length === 0;
    ghost.classList.toggle("is-hidden", input.value.length > 0 || !ready);
  }

  function setActive(key, focusTab) {
    active = engines[key];
    if (key === "full" && engines.full.state === "idle") getManifest().catch(() => {});
    render();
    if (focusTab) tabs.find((t) => t.dataset.engine === key).focus();
  }

  function showSuggestion(i) {
    ghostText.textContent = EXAMPLES[i];
  }

  function cycleSuggestion() {
    if (active.state !== "ready" || input.value.length > 0) return;
    const next = (suggestion + 1) % EXAMPLES.length;
    if (reducedMotion.matches) {
      suggestion = next;
      showSuggestion(suggestion);
      return;
    }
    ghost.classList.add("is-fading");
    setTimeout(() => {
      suggestion = next;
      showSuggestion(suggestion);
      ghost.classList.remove("is-fading");
    }, 300);
  }

  function renderChips() {
    for (const text of CHIPS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = text;
      b.addEventListener("click", () => submit(text));
      chips.append(b);
    }
  }

  for (const t of tabs) {
    t.addEventListener("click", () => setActive(t.dataset.engine, false));
    t.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        const i = tabs.indexOf(t);
        const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        setActive(next.dataset.engine, true);
      }
    });
  }

  gateAck.addEventListener("change", () => {
    gateLoad.disabled = !gateAck.checked || engines.full.state === "loading";
  });
  gateLoad.addEventListener("click", () => {
    if (gateAck.checked) loadFull();
  });

  input.addEventListener("input", () => {
    autosize();
    render();
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      submit(input.value);
    } else if (e.key === "Tab" && !e.shiftKey && input.value.length === 0 && active.state === "ready") {
      e.preventDefault();
      input.value = EXAMPLES[suggestion];
      input.setSelectionRange(input.value.length, input.value.length);
      autosize();
      render();
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submit(input.value);
    input.focus();
  });

  renderChips();
  showSuggestion(0);
  render();
  setInterval(cycleSuggestion, CYCLE_MS);
  loadLite().then(() => {
    if (active === engines.lite && engines.lite.state === "ready" && canHover.matches) input.focus();
  });
})();
