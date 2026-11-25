(() => {
  "use strict";

  const WASM_URL = "elifgpt.wasm";
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

  const $ = (id) => document.getElementById(id);
  const body = document.body;
  const log = $("log");
  const input = $("input");
  const send = $("send");
  const form = $("composer");
  const ghost = $("ghost");
  const ghostText = $("ghost-text");
  const chips = $("chips");
  const loading = $("loading");
  const bar = $("bar");
  const barFill = $("bar-fill");
  const loadingText = $("loading-text");
  const dock = $("dock");

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)");
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  let elif = null;
  let memory = null;
  let busy = false;
  let suggestion = 0;

  function syncDockHeight() {
    document.documentElement.style.setProperty("--dock-h", `${dock.offsetHeight}px`);
  }
  new ResizeObserver(syncDockHeight).observe(dock);
  syncDockHeight();

  function wasiImports() {
    const wasi = {
      clock_time_get(_id, _precision, ptr) {
        new DataView(memory.buffer).setBigUint64(ptr, BigInt(Date.now()) * 1000000n, true);
        return 0;
      },
      random_get(ptr, len) {
        crypto.getRandomValues(new Uint8Array(memory.buffer, ptr, len));
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

  function readCString(ptr) {
    const view = new Uint8Array(memory.buffer);
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

  function ask(text) {
    const cap = elif.elif_capacity() - 1;
    let bytes = encoder.encode(text);
    if (bytes.length > cap) bytes = bytes.subarray(0, cap);
    const ptr = elif.elif_input();
    const view = new Uint8Array(memory.buffer);
    view.set(bytes, ptr);
    view[ptr + bytes.length] = 0;
    const t0 = performance.now();
    const out = elif.elif_respond(ptr);
    const ms = performance.now() - t0;
    return { text: expandHostReply(readCString(out)), branches: elif.elif_branches(), ms };
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

  function addUser(text) {
    const el = document.createElement("div");
    el.className = "msg msg-user";
    el.textContent = text;
    log.append(el);
  }

  function addThinking() {
    const el = document.createElement("div");
    el.className = "msg msg-bot thinking";
    el.setAttribute("aria-label", "ElifGPT is thinking");
    el.innerHTML =
      '<svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">' +
      '<g class="stem" fill="none" stroke="currentColor" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M16 28.5V18"/><path d="M16 18c0-5-7.5-4.5-7.5-10"/><path d="M16 18V8"/><path d="M16 18c0-5 7.5-4.5 7.5-10"/></g>' +
      '<g fill="currentColor"><circle class="node" cx="8.5" cy="5.6" r="2.7"/><circle class="node" cx="16" cy="4.8" r="2.7"/>' +
      '<circle class="node" cx="23.5" cy="5.6" r="2.7"/></g></svg>' +
      '<span>thinking<span class="dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span></span>';
    log.append(el);
    return el;
  }

  function fillReply(el, reply) {
    el.className = "msg msg-bot";
    el.removeAttribute("aria-label");
    el.textContent = reply.text;
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    const n = reply.branches.toLocaleString("en-US");
    const t = formatMs(reply.ms);
    if (reply.branches === 0) {
      meta.textContent = `answered from memory, no branches needed (${t})`;
    } else {
      const count = document.createElement("b");
      count.textContent = n;
      meta.append("checked ", count, ` branch${reply.branches === 1 ? "" : "es"} in ${t}`);
    }
    el.append(meta);
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const nextFrame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

  async function submit(text) {
    text = text.trim();
    if (!text || busy || !elif) return;
    busy = true;
    body.classList.remove("is-empty");
    addUser(text);
    input.value = "";
    autosize();
    updateControls();
    const thinking = addThinking();
    scrollToEnd();
    const started = performance.now();
    await nextFrame();
    let reply;
    try {
      reply = ask(text);
    } catch (err) {
      console.error(err);
      reply = { text: "Something broke inside my elifs. Refresh the page and try again.", branches: 0, ms: 0 };
    }
    const wait = 400 + Math.random() * 500 - (performance.now() - started);
    if (wait > 0) await sleep(wait);
    fillReply(thinking, reply);
    scrollToEnd();
    busy = false;
    updateControls();
  }

  function autosize() {
    input.style.height = "24px";
    const max = 24 * MAX_LINES;
    const h = Math.min(input.scrollHeight - 12, max);
    input.style.height = `${Math.max(24, h)}px`;
    input.style.overflowY = input.scrollHeight - 12 > max ? "auto" : "hidden";
  }

  function updateControls() {
    const empty = input.value.length === 0;
    send.disabled = !elif || busy || input.value.trim().length === 0;
    ghost.classList.toggle("is-hidden", !empty || !elif);
  }

  function showSuggestion(i) {
    ghostText.textContent = EXAMPLES[i];
  }

  function cycleSuggestion() {
    if (!elif) return;
    if (input.value.length > 0) return;
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

  input.addEventListener("input", () => {
    autosize();
    updateControls();
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      submit(input.value);
    } else if (e.key === "Tab" && !e.shiftKey && input.value.length === 0 && elif) {
      e.preventDefault();
      input.value = EXAMPLES[suggestion];
      input.setSelectionRange(input.value.length, input.value.length);
      autosize();
      updateControls();
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submit(input.value);
    input.focus();
  });

  async function boot() {
    showSuggestion(0);
    ghost.classList.add("is-hidden");
    try {
      const bytes = await fetchWithProgress(WASM_URL, (p) => {
        if (p < 0) {
          bar.classList.add("is-indeterminate");
        } else {
          barFill.style.width = `${Math.round(p * 100)}%`;
        }
      });
      bar.classList.remove("is-indeterminate");
      barFill.style.width = "100%";
      const { instance } = await WebAssembly.instantiate(bytes, wasiImports());
      elif = instance.exports;
      memory = elif.memory;
      if (elif._initialize) elif._initialize();
      elif.elif_seed((Math.random() * 0xffffffff) >>> 0);
    } catch (err) {
      console.error(err);
      loading.classList.add("is-error");
      bar.hidden = true;
      loadingText.textContent = "Couldn't load the elifs. Refresh the page to try again.";
      return;
    }
    loading.hidden = true;
    chips.hidden = false;
    input.disabled = false;
    updateControls();
    setInterval(cycleSuggestion, CYCLE_MS);
    if (canHover.matches) input.focus();
  }

  renderChips();
  boot();
})();
