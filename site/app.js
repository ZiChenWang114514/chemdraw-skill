// Copy buttons, the before/after viewer, the hero replay and the install picker.
// The page reads completely without this file; it only adds behaviour.

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

document.querySelectorAll(".compare").forEach((box) => {
  const input = box.querySelector("input");
  const set = () => box.style.setProperty("--cut", input.value + "%");
  input.addEventListener("input", set);
  set();
});

// Tabs: arrow keys move between tabs, as the ARIA tabs pattern expects.
document.querySelectorAll("[role=tablist]").forEach((list) => {
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

// The hero drawing plays once on load; the replay button restarts it.
const doc = document.querySelector(".doc");
const replay = document.querySelector(".replay");
if (doc) {
  doc.classList.add("play");
  if (replay && matchMedia("(prefers-reduced-motion: no-preference)").matches) {
    replay.hidden = false;
    replay.addEventListener("click", () => {
      doc.classList.remove("play");
      void doc.offsetWidth;
      doc.classList.add("play");
    });
  }
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
