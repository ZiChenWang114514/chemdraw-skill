// Copy buttons, the before/after viewer, the theme switch, scroll-in and the install picker.
// The hero editor lives in editor.js. The page reads completely without either file;
// they only add behaviour.

const motion = matchMedia("(prefers-reduced-motion: no-preference)");

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
