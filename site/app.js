// Copy buttons, the before/after viewer, the theme switch, scroll-in, the install picker,
// the chapter progress bar, the capability filter with its example requests, and the
// figure viewer. The hero editor lives in editor.js. The page reads completely without
// either file; they only add behaviour. Words come from words.<language>.js.

const motion = matchMedia("(prefers-reduced-motion: no-preference)");
const words = globalThis.ChemWords || null;
const fmt = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => o[k]);

async function copyText(text, btn, done) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    return false;
  }
  const label = btn.textContent;
  btn.dataset.done = "";
  btn.textContent = done;
  setTimeout(() => { btn.textContent = label; delete btn.dataset.done; }, 1600);
  return true;
}

document.querySelectorAll("[data-copy]").forEach((btn) => {
  const label = btn.textContent;
  btn.addEventListener("click", async () => {
    const text = document.querySelector(btn.dataset.copy).textContent;
    try {
      await navigator.clipboard.writeText(text);
      btn.dataset.done = "";
      btn.textContent = btn.dataset.doneLabel || "Copied";
      setTimeout(() => { btn.textContent = label; delete btn.dataset.done; }, 1600);
    } catch {
      const range = document.createRange();
      range.selectNodeContents(document.querySelector(btn.dataset.copy));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
    }
  });
});

// Before / after: the first time a viewer scrolls into sight the divider swings out and back,
// so it is clear it moves. Touching it stops the hint.
function sweep(input, set) {
  const keys = [[0, 50], [450, 22], [1100, 78], [1600, 50]];
  let begun = null, stopped = false;
  const stop = () => { stopped = true; };
  input.addEventListener("pointerdown", stop, { once: true });
  input.addEventListener("keydown", stop, { once: true });
  const tick = (now) => {
    if (stopped) return;
    if (begun === null) begun = now;
    const t = now - begun;
    const k = keys.findIndex(([at]) => at > t);
    if (k === -1) { input.value = 50; set(); return; }
    const [t0, v0] = keys[k - 1], [t1, v1] = keys[k];
    const u = (t - t0) / (t1 - t0), ease = u * u * (3 - 2 * u);
    input.value = v0 + (v1 - v0) * ease;
    set();
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

const hints = "IntersectionObserver" in window && new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    hints.unobserve(e.target);
    if (motion.matches) sweep(e.target.querySelector("input"), e.target.set);
  });
}, { threshold: 0.6 });

document.querySelectorAll(".compare").forEach((box) => {
  const input = box.querySelector("input");
  const set = () => box.style.setProperty("--cut", input.value + "%");
  input.addEventListener("input", set);
  set();
  box.set = set;
  if (hints) hints.observe(box);
});

// Tabs: arrow keys move between tabs, as the ARIA tabs pattern expects.
document.querySelectorAll(".tabs[role=tablist]").forEach((list) => {
  const tabs = [...list.querySelectorAll("[role=tab]")];
  const select = (tab) => {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (e) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!step) return;
      const next = tabs[(i + step + tabs.length) % tabs.length];
      select(next);
      next.focus();
    });
  });
});

// Theme: follows the system until the button is used; the choice is kept in this browser.
const themeBtn = document.querySelector(".theme");
if (themeBtn) {
  const root = document.documentElement;
  const system = matchMedia("(prefers-color-scheme: dark)");
  const mode = () => root.dataset.theme || (system.matches ? "dark" : "light");
  const paint = () => {
    themeBtn.dataset.mode = mode();
    themeBtn.setAttribute("aria-pressed", mode() === "dark");
  };
  themeBtn.addEventListener("click", () => {
    root.dataset.theme = mode() === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch { /* private mode: the choice just isn't kept */ }
    paint();
  });
  system.addEventListener("change", paint);
  themeBtn.hidden = false;
  paint();
}

// The reaction arrows in "How it works" draw as they scroll into view.
const steps = document.querySelectorAll(".step");
document.documentElement.classList.add("reveal");
if ("IntersectionObserver" in window) {
  const seen = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      seen.unobserve(e.target);
    });
  }, { threshold: 0.35 });
  steps.forEach((s) => seen.observe(s));
} else {
  steps.forEach((s) => s.classList.add("in"));
}

// "Run it": replay the four steps as a terminal session. Each arrow draws, its command panel
// opens, the command types itself out and the output follows. Without motion everything
// simply opens at once.
const runBtn = document.querySelector("[data-run]");
if (runBtn && words) {
  const label = runBtn.querySelector("span");
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const panels = [...document.querySelectorAll(".step")].map((step) => {
    const code = step.querySelector(".cmd code");
    return { step, box: step.querySelector(".cmd"), code, html: code.innerHTML };
  });
  async function type(code, html) {
    // Commands (the .run spans) type character by character; output lines appear whole.
    const tpl = document.createElement("template");
    tpl.innerHTML = html;
    code.textContent = "";
    for (const node of [...tpl.content.childNodes]) {
      if (node.nodeType === 1 && node.classList.contains("run")) {
        const span = node.cloneNode(false);
        code.append(span);
        for (const ch of node.textContent) { span.textContent += ch; await wait(ch === " " ? 8 : 22); }
        await wait(260);
      } else {
        code.append(node.cloneNode(true));
        await wait(60);
      }
    }
  }
  runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    label.textContent = words.running;
    document.querySelector("#how .scheme").dataset.running = "";
    panels.forEach((p) => { p.box.open = false; p.step.classList.remove("in", "live"); p.code.innerHTML = p.html; });
    for (const p of panels) {
      p.step.classList.add("in", "live");
      p.box.open = true;
      if (motion.matches) {
        p.step.scrollIntoView({ block: "nearest", behavior: "smooth" });
        await wait(500);
        await type(p.code, p.html);
        await wait(350);
      }
      p.step.classList.remove("live");
    }
    delete document.querySelector("#how .scheme").dataset.running;
    document.querySelector(".cpd.end").classList.add("flash");
    setTimeout(() => document.querySelector(".cpd.end").classList.remove("flash"), 1400);
    label.textContent = words.rerun;
    runBtn.disabled = false;
  });
  runBtn.hidden = false;
}

// Install picker: rewrite the commands for the chosen agent and system. Each agent
// option carries its installer flag as its value and its Skill folder in data-dir.
const picker = document.querySelector(".choose");
if (picker) {
  const fill = (name, value) =>
    document.querySelectorAll(`[data-var="${name}"]`).forEach((el) => { el.textContent = value; });
  const update = () => {
    const agent = picker.querySelector("[name=agent]:checked");
    const windows = picker.querySelector("[name=os]:checked").value === "windows";
    fill("python", windows ? "python" : "python3");
    fill("agent", agent.value);
    fill("home", "$HOME/" + agent.dataset.dir);
  };
  const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
  const os = /mac/i.test(platform) ? "macos" : /linux|x11/i.test(platform) ? "linux" : /win/i.test(platform) ? "windows" : null;
  if (os) picker.querySelector(`[name=os][value=${os}]`).checked = true;
  picker.addEventListener("change", update);
  picker.hidden = false;
  update();
}

// Jumps inside a page: a short glide instead of a long roll past every figure. A far jump
// hops to one screen away first. The wheel, a touch or a key takes the page back at once.
function glide(target) {
  const offset = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
  const goal = () => Math.max(0, target.getBoundingClientRect().top + scrollY - offset);
  if (!motion.matches) { scrollTo(0, goal()); return; }
  const gap = goal() - scrollY;
  if (Math.abs(gap) > innerHeight * 2) scrollTo(0, goal() - Math.sign(gap) * innerHeight);
  const from = scrollY, start = performance.now();
  let frame = 0;
  const stop = () => {
    cancelAnimationFrame(frame);
    for (const type of ["wheel", "touchstart", "keydown"]) removeEventListener(type, stop);
  };
  const step = (now) => {
    const t = Math.max(0, Math.min(1, (now - start) / 360));
    scrollTo(0, from + (goal() - from) * (1 - (1 - t) ** 3));
    if (t < 1) frame = requestAnimationFrame(step); else stop();
  };
  for (const type of ["wheel", "touchstart", "keydown"]) addEventListener(type, stop, { passive: true });
  frame = requestAnimationFrame(step);
}

document.addEventListener("click", (e) => {
  const link = e.target.closest('a[href^="#"]:not(.skip)');
  if (!link || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const target = document.getElementById(link.hash.slice(1));
  if (!target) return;
  e.preventDefault();
  history.pushState(null, "", link.hash);
  target.tabIndex = -1;
  target.focus({ preventScroll: true });
  glide(target);
});

// Reading progress: a segment per chapter along the header, filled as the page is read, and
// the chapter in view lit in the navigation. The segments are for the mouse; keyboards and
// screen readers have the navigation, so the bar stays out of both.
const progress = document.querySelector(".top .progress");
if (progress) {
  const chapters = [document.querySelector(".hero"), ...document.querySelectorAll("main section[id]")].map((el) => {
    const id = el.id || "main";
    const link = Object.assign(document.createElement("a"), { href: `#${id}`, tabIndex: -1, innerHTML: "<i><i></i></i>" });
    link.dataset.label = el.querySelector("h2")?.textContent.trim() || words?.progressTop || "";
    progress.append(link);
    return { el, link, fill: link.querySelector("i i"), nav: document.querySelector(`.nav a[href="#${id}"]`), top: 0, height: 1, shown: -1 };
  });
  let queued = false, lit = null;
  const paint = () => {
    queued = false;
    const room = document.documentElement.scrollHeight - innerHeight;
    const read = room > 0 ? Math.min(1, scrollY / room) : 0;
    // This line runs from the window's top to its bottom over the page, so the bar starts empty and ends full
    const line = scrollY + innerHeight * read;
    for (const c of chapters) {
      const part = Math.round(Math.max(0, Math.min(1, (line - c.top) / c.height)) * 1000) / 1000;
      if (part !== c.shown) { c.shown = part; c.fill.style.transform = `scaleX(${part})`; }
    }
    const here = read > 0.995 ? chapters.at(-1) : chapters.filter((c) => c.top <= scrollY + innerHeight * 0.35).at(-1);
    if (here !== lit) {
      lit?.nav?.removeAttribute("aria-current");
      here?.nav?.setAttribute("aria-current", "true");
      lit = here;
    }
  };
  const measure = () => {
    for (const c of chapters) {
      const box = c.el.getBoundingClientRect();
      c.top = box.top + scrollY;
      c.height = box.height;
      c.link.style.flexGrow = box.height;
    }
    paint();
  };
  addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(paint); } }, { passive: true });
  addEventListener("resize", measure);
  new ResizeObserver(measure).observe(document.body);
  measure();
}

// The drawing grid lights up under the pointer, except on the canvases, where the preview needs
// the attention. Mouse only, and only if motion is welcome.
if (motion.matches && matchMedia("(hover: hover) and (pointer: fine)").matches) {
  const glow = Object.assign(document.createElement("div"), { className: "grid-glow" });
  glow.setAttribute("aria-hidden", "true");
  document.body.append(glow);
  let x = 0, y = 0, queued = false, idle = 0;
  const paint = () => {
    queued = false;
    glow.style.transform = `translate(${x}px, ${y}px)`;
    // The dots stay still on the page while the window onto them moves
    glow.style.backgroundPosition = `${-x % 14}px ${-y % 14}px`;
  };
  addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    clearTimeout(idle);
    if (e.target.closest?.(".doc-canvas")) { delete glow.dataset.on; return; }
    x = e.clientX - 180;
    y = e.clientY - 180;
    glow.dataset.on = "";
    idle = setTimeout(() => { delete glow.dataset.on; }, 1000);
    if (!queued) { queued = true; requestAnimationFrame(paint); }
  }, { passive: true });
}

// FAQ: search as you type, open or close everything, and a link to each answer.
const faq = document.querySelector(".faq");
if (faq && words) {
  const L = words.faq;
  const tools = document.querySelector(".faq-tools");
  const input = tools.querySelector("input");
  const total = tools.querySelector(".faq-count");
  const all = tools.querySelector("[data-faq-all]");
  const empty = document.querySelector(".faq-empty");
  const items = [...faq.querySelectorAll("details")];
  let before = null;

  const paintAll = () => {
    const shown = items.filter((d) => !d.hidden);
    all.textContent = shown.length && shown.every((d) => d.open) ? L.collapse : L.expand;
    all.hidden = !shown.length;
  };
  const unmark = () => faq.querySelectorAll("mark").forEach((m) => {
    const parent = m.parentNode;
    m.replaceWith(m.textContent);
    parent.normalize();
  });
  const mark = (item, pattern) => {
    const walker = document.createTreeWalker(item, NodeFilter.SHOW_TEXT);
    const texts = [];
    while (walker.nextNode()) texts.push(walker.currentNode);
    for (const text of texts) {
      const parts = text.data.split(pattern);
      if (parts.length < 2) continue;
      const found = document.createDocumentFragment();
      parts.forEach((part, i) => { if (part) found.append(i % 2 ? Object.assign(document.createElement("mark"), { textContent: part }) : part); });
      text.replaceWith(found);
    }
  };
  input.addEventListener("input", () => {
    const terms = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    unmark();
    if (!terms.length) {
      items.forEach((d, i) => { d.hidden = false; if (before) d.open = before[i]; });
      before = null;
      total.textContent = "";
      empty.hidden = true;
      paintAll();
      return;
    }
    before ||= items.map((d) => d.open);
    const pattern = new RegExp(`(${terms.map((t) => t.replace(/[.*+?^\${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
    let hits = 0;
    for (const d of items) {
      const hay = d.textContent.toLowerCase();
      d.hidden = !terms.every((t) => hay.includes(t));
      if (d.hidden) continue;
      hits++;
      d.open = true;
      mark(d, pattern);
    }
    total.textContent = fmt(L.count, { n: hits });
    empty.hidden = hits > 0;
    paintAll();
  });
  all.addEventListener("click", () => {
    const open = all.textContent === L.expand;
    items.forEach((d) => { if (!d.hidden) d.open = open; });
  });
  faq.addEventListener("toggle", paintAll, true);

  for (const d of items) {
    const row = Object.assign(document.createElement("div"), { className: "qa" });
    d.replaceWith(row);
    const link = Object.assign(document.createElement("button"), { type: "button", className: "faq-link", title: L.link });
    link.setAttribute("aria-label", L.link);
    link.innerHTML = `<svg class="chain" viewBox="0 0 16 16" aria-hidden="true"><path d="M6.8 9.2a2.6 2.6 0 0 0 3.7 0l2-2a2.6 2.6 0 0 0-3.7-3.7l-.8.8M9.2 6.8a2.6 2.6 0 0 0-3.7 0l-2 2a2.6 2.6 0 0 0 3.7 3.7l.8-.8"/></svg><svg class="tick" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 4.8"/></svg>`;
    link.addEventListener("click", async () => {
      await navigator.clipboard.writeText(new URL(`#${d.id}`, location.href).href);
      link.dataset.done = "";
      setTimeout(() => { delete link.dataset.done; }, 1500);
    });
    row.append(d, link);
  }

  const openLinked = () => {
    const linked = items.find((d) => `#${d.id}` === location.hash);
    if (linked) linked.open = true;
  };
  addEventListener("hashchange", openLinked);
  openLinked();
  tools.hidden = false;
  paintAll();
}

// Capabilities: filter the list by kind, and copy any example request.
const filters = document.querySelector(".filters");
if (filters && words) {
  const items = [...document.querySelectorAll(".caps > [data-kind]")];
  filters.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-filter]");
    if (!chip) return;
    const kind = chip.dataset.filter;
    filters.querySelectorAll("[data-filter]").forEach((b) => b.setAttribute("aria-pressed", b === chip));
    items.forEach((item, k) => {
      const show = kind === "all" || item.dataset.kind === kind;
      item.hidden = !show;
      if (show && motion.matches) {
        item.classList.remove("pop");
        void item.offsetWidth;
        item.style.setProperty("--k", k);
        item.classList.add("pop");
      }
    });
  });
  filters.hidden = false;
  document.querySelectorAll(".try").forEach((box) => {
    const ask = box.querySelector(".ask");
    const btn = Object.assign(document.createElement("button"), { type: "button", className: "btn sm", textContent: words.copyAsk });
    btn.addEventListener("click", () => copyText(ask.textContent, btn, words.copiedAsk));
    ask.after(btn);
  });
}

// Figure viewer: every gallery plate opens full screen, where it can be zoomed (wheel,
// double-click, pinch or the buttons), panned by dragging and paged with the arrow keys.
const shots = [...document.querySelectorAll("img[data-zoom]")];
if (shots.length && words && typeof HTMLDialogElement === "function") {
  const L = words.lightbox;
  const icon = (d) => `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="${d}"/></svg>`;
  const box = document.createElement("dialog");
  box.className = "lightbox";
  box.innerHTML = `
    <div class="lb-stage"><img alt="" draggable="false"></div>
    <div class="lb-bar">
      <p class="lb-cap"></p>
      <span class="lb-count"></span>
      <div class="lb-tools">
        <button type="button" data-lb="prev" aria-label="${L.prev}" title="${L.prev} (←)">${icon("M12.5 4.5L7 10l5.5 5.5")}</button>
        <button type="button" data-lb="next" aria-label="${L.next}" title="${L.next} (→)">${icon("M7.5 4.5L13 10l-5.5 5.5")}</button>
        <button type="button" data-lb="out" aria-label="${L.zoomOut}" title="${L.zoomOut} (−)">${icon("M5 10h10")}</button>
        <button type="button" data-lb="fit" aria-label="${L.fit}" title="${L.fit} (0)">${icon("M4 8V4h4M16 8V4h-4M4 12v4h4M16 12v4h-4")}</button>
        <button type="button" data-lb="in" aria-label="${L.zoomIn}" title="${L.zoomIn} (+)">${icon("M5 10h10M10 5v10")}</button>
        <button type="button" data-lb="close" aria-label="${L.close}" title="${L.close} (Esc)">${icon("M5 5l10 10M15 5L5 15")}</button>
      </div>
    </div>
    <p class="lb-hint">${L.hint}</p>`;
  document.body.append(box);
  const stage = box.querySelector(".lb-stage"), img = stage.querySelector("img");
  const cap = box.querySelector(".lb-cap"), count = box.querySelector(".lb-count");
  let at = 0, s = 1, x = 0, y = 0, opener = null;
  const pointers = new Map();
  let pan = null, pinch = null;

  const apply = () => {
    img.style.transform = `translate(${x}px, ${y}px) scale(${s})`;
    if (s > 1.01) box.dataset.zoomed = ""; else delete box.dataset.zoomed;
  };
  // Zoom to `to` keeping the image point under (px, py), measured from the stage centre, still.
  const zoom = (to, px = 0, py = 0) => {
    const next = Math.min(6, Math.max(1, to));
    x = px - ((px - x) * next) / s;
    y = py - ((py - y) * next) / s;
    s = next;
    if (s === 1) { x = 0; y = 0; }
    apply();
  };
  const local = (e) => {
    const r = stage.getBoundingClientRect();
    return [e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2];
  };
  const show = (k) => {
    at = (k + shots.length) % shots.length;
    const shot = shots[at];
    img.src = shot.currentSrc || shot.src;
    img.alt = shot.alt;
    const caption = shot.closest("figure").querySelector("figcaption");
    cap.innerHTML = caption ? caption.innerHTML : "";
    count.textContent = fmt(L.count, { n: at + 1, total: shots.length });
    s = 1; x = 0; y = 0;
    apply();
  };

  shots.forEach((shot, k) => {
    const target = shot.closest(".plate") || shot;
    target.classList.add("zoomable");
    target.tabIndex = 0;
    target.setAttribute("role", "button");
    target.setAttribute("aria-label", fmt(L.open, { alt: shot.alt }));
    const open = () => { opener = target; show(k); box.showModal(); };
    target.addEventListener("click", open);
    target.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
  });

  box.addEventListener("close", () => { if (opener) opener.focus(); });
  box.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lb]");
    if (btn) {
      const act = btn.dataset.lb;
      if (act === "close") box.close();
      else if (act === "prev") show(at - 1);
      else if (act === "next") show(at + 1);
      else if (act === "in") zoom(s * 1.6);
      else if (act === "out") zoom(s / 1.6);
      else if (act === "fit") zoom(1);
      return;
    }
    // A click on the dark surround closes, as long as it was not the end of a drag.
    if ((e.target === box || e.target === stage) && !box.dataset.dragged) box.close();
  });
  box.addEventListener("keydown", (e) => {
    const act = { ArrowLeft: () => show(at - 1), ArrowRight: () => show(at + 1), "+": () => zoom(s * 1.6), "=": () => zoom(s * 1.6), "-": () => zoom(s / 1.6), "0": () => zoom(1) }[e.key];
    if (act) { e.preventDefault(); act(); }
  });
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoom(s * Math.exp(-e.deltaY * (e.deltaMode ? 0.05 : 0.0018)), ...local(e));
  }, { passive: false });
  stage.addEventListener("dblclick", (e) => zoom(s > 1.01 ? 1 : 2.5, ...local(e)));

  stage.addEventListener("pointerdown", (e) => {
    pointers.set(e.pointerId, local(e));
    stage.setPointerCapture(e.pointerId);
    delete box.dataset.dragged;
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), s };
      pan = null;
    } else if (s > 1.01) {
      pan = { px: e.clientX, py: e.clientY, x, y };
    }
  });
  stage.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, local(e));
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      zoom((pinch.s * Math.hypot(a[0] - b[0], a[1] - b[1])) / pinch.d, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
      box.dataset.dragged = "";
    } else if (pan) {
      x = pan.x + e.clientX - pan.px;
      y = pan.y + e.clientY - pan.py;
      if (Math.abs(e.clientX - pan.px) + Math.abs(e.clientY - pan.py) > 4) box.dataset.dragged = "";
      apply();
    }
  });
  const lift = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) pan = null;
  };
  stage.addEventListener("pointerup", lift);
  stage.addEventListener("pointercancel", lift);
}
