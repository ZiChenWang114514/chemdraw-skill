// Plays the built site in headless Chrome with trusted input over the DevTools protocol: no
// window opens and nothing is installed. Run by tests/test_site.py with SITE_BROWSER=1.
// usage: node tests/site_smoke.mjs http://127.0.0.1:8642/chemdraw-skill/
// CHROME names the browser when it is not in the usual place.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const base = process.argv[2];
const host = new URL(base).host;
const browser = process.env.CHROME || (process.platform === "darwin"
  ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "google-chrome");
const folder = mkdtempSync(join(tmpdir(), "site-smoke-"));
const port = 9400 + Math.floor(Math.random() * 500);
const chrome = spawn(browser, [
  "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${join(folder, "profile")}`,
  "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
  // A Linux runner has no mouse, so without this the hover-only features stay off. Touch emulation still overrides it.
  "--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4",
  ...(process.env.CI ? ["--no-sandbox"] : []), "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const failures = [];
const problems = [];
const passed = [];
const check = (name, ok, detail = "") => {
  if (ok) passed.push(name);
  else failures.push(`${name}${detail === "" ? "" : `: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`}`);
};

async function connect() {
  for (let i = 0; i < 100; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = pages.find((t) => t.type === "page");
      if (page) {
        const ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((ready, fail) => { ws.addEventListener("open", ready); ws.addEventListener("error", fail); });
        return ws;
      }
    } catch {}
    await sleep(100);
  }
  throw new Error(`Chrome did not start from ${browser}`);
}

const ws = await connect();
let nextId = 0;
const waiting = new Map();
ws.addEventListener("message", ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); }
  if (msg.method === "Runtime.exceptionThrown") problems.push(`exception: ${msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text}`);
  if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") problems.push(`console.error: ${msg.params.args.map((a) => a.value ?? a.description).join(" ")}`);
  if (msg.method === "Network.requestWillBeSent") {
    const url = new URL(msg.params.request.url);
    if (/^https?:$/.test(url.protocol) && url.host !== host) problems.push(`left the site: ${url.href}`);
  }
  if (msg.method === "Network.responseReceived" && msg.params.response.status >= 400) problems.push(`${msg.params.response.status}: ${msg.params.response.url}`);
});
const send = (method, params = {}) => new Promise((done, fail) => {
  const id = ++nextId;
  waiting.set(id, (msg) => (msg.error ? fail(new Error(`${method}: ${msg.error.message}`)) : done(msg.result)));
  ws.send(JSON.stringify({ id, method, params }));
});

const run = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true, userGesture: true });
  if (r.exceptionDetails) throw new Error(`${expression}\n${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
  return r.result.value;
};
const until = async (expression, ms = 3000) => {
  for (const end = Date.now() + ms; Date.now() < end; await sleep(25)) if (await run(expression)) return true;
  return false;
};
const open = async (path) => {
  await send("Page.navigate", { url: "about:blank" });
  await send("Page.navigate", { url: base + path });
  await until(`document.readyState === "complete"`);
  await sleep(120);
};
// The route change runs on the next frame, inside the view transition when there is one
const hash = async (route) => {
  await run(`location.hash = ${JSON.stringify(route)}`);
  await run(`new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))`);
  await until(`!document.documentElement.dataset.slide`);
};
const count = (selector) => run(`document.querySelectorAll(${JSON.stringify(selector)}).length`);
const store = async () => JSON.parse(await run(`localStorage.getItem("chemdraw-skill-lab")`) || "null");

const where = (selector) => run(`(() => {
  const el = document.querySelector(${JSON.stringify(selector)});
  if (!el) return null;
  el.scrollIntoView({ block: "nearest", behavior: "instant" });
  const r = el.getBoundingClientRect();
  return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
})()`);
const mouse = (type, { x, y }, extra = {}) => send("Input.dispatchMouseEvent", { type, x, y, ...extra });
const move = (at) => mouse("mouseMoved", at);
const clickAt = async (at) => {
  await move(at);
  await mouse("mousePressed", at, { button: "left", clickCount: 1, buttons: 1 });
  await mouse("mouseReleased", at, { button: "left", clickCount: 1 });
};
const click = async (selector) => {
  const at = await where(selector);
  if (!at) throw new Error(`nothing to click: ${selector}`);
  await clickAt(at);
};
const KEYS = { Enter: 13, Backspace: 8, " ": 32, Tab: 9, ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40 };
const press = async (key, modifiers = 0) => {
  const vk = KEYS[key] ?? key.toUpperCase().charCodeAt(0);
  const params = { key, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers, code: key.length === 1 ? `Key${key.toUpperCase()}` : key };
  await send("Input.dispatchKeyEvent", { type: "keyDown", ...params, ...(key === "Enter" ? { text: "\r" } : key.length === 1 ? { text: key } : {}) });
  await send("Input.dispatchKeyEvent", { type: "keyUp", ...params });
};
const touch = (type, points) => send("Input.dispatchTouchEvent", { type, touchPoints: points });

// The editor's own words for a move: tools, hover hotkeys and clicks, as a visitor would do it.
const canvas = ".doc .mol";
const atom = (i) => `${canvas} .hit [data-atom="${i}"]`;
const bond = (i) => `${canvas} .hit [data-bond="${i}"]`;
const tool = (name) => click(`.doc [data-tool="${name}"]`);
const ELEMENT_KEY = { C: "c", N: "n", O: "o", S: "s", F: "f", Cl: "l" };
async function playMove([name, i, value]) {
  if (name === "erase") { await tool("erase"); await click(atom(i)); }
  else if (name === "grow") { await tool("bond"); await click(atom(i)); }
  else if (name === "element") { await tool("bond"); await move(await where(atom(i))); await press(ELEMENT_KEY[value]); }
  else if (name === "order") {
    await tool("bond");
    await move(await where(bond(i)));
    await press(String(value));
  }
}

async function main() {
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Emulation.setFocusEmulationEnabled", { enabled: true });
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send("Browser.grantPermissions", { origin: new URL(base).origin, permissions: ["clipboardReadWrite", "clipboardSanitizedWrite"] });
  await send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: folder });

  // Reading progress: one segment per chapter, and the header follows along
  await open("");
  const shift = () => run(`new Promise((done) => {
    let total = 0;
    new PerformanceObserver((list) => { for (const e of list.getEntries()) if (!e.hadRecentInput) total += e.value; }).observe({ type: "layout-shift", buffered: true });
    setTimeout(() => done(total), 200);
  })`);
  check("the hero does not jump as the editor loads", (await shift()) < 0.005, await shift());
  const chapters = await run(`document.querySelectorAll("main section[id]").length + 1`);
  check("one progress segment per chapter", (await count(".progress a")) === chapters);
  const fills = () => run(`[...document.querySelectorAll(".progress a i i")].map((i) => new DOMMatrix(getComputedStyle(i).transform).a)`);
  check("nothing read at the top", (await fills()).every((f) => f < 0.05), await fills());
  await run(`scrollTo({ top: document.documentElement.scrollHeight, behavior: "instant" })`);
  await sleep(120);
  check("everything read at the bottom", (await fills()).every((f) => f > 0.99), await fills());
  check("the last chapter is lit in the header", await run(`document.querySelector('.nav a[href="#faq"]').getAttribute("aria-current") === "true"`));
  await run(`scrollTo({ top: 0, behavior: "instant" })`);
  await sleep(120);
  check("no chapter is lit at the top", (await count(`.nav [aria-current]`)) === 0);
  const segment = await run(`(() => { const r = document.querySelector(".progress a[href='#start']").getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()`);
  await move(segment);
  await sleep(200);
  check("a hovered segment thickens", await run(`new DOMMatrix(getComputedStyle(document.querySelector(".progress a[href='#start'] > i")).transform).d > 1.5`));
  check("a hovered segment names its chapter", await run(`document.querySelector(".progress a[href='#start']").dataset.label === document.querySelector("#start h2").textContent.trim()`));
  await clickAt(segment);
  check("a segment jumps to its chapter", await until(`Math.abs(document.querySelector("#start").getBoundingClientRect().top - 72) < 3`, 2500));
  await run(`scrollTo({ top: 0, behavior: "instant" })`);

  // Jumps inside the page: short, cancellable and recorded in the address
  const faqTop = `Math.abs(document.querySelector("#faq").getBoundingClientRect().top - 72)`;
  await click('.nav a[href="#faq"]');
  check("a link glides to its chapter", await until(`${faqTop} < 3`, 1500), await run(faqTop));
  check("a glide updates the address", await run(`location.hash === "#faq"`));
  await run(`scrollTo({ top: 0, behavior: "instant" }); history.replaceState(null, "", location.pathname)`);
  await click('.nav a[href="#faq"]');
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: 640, y: 450, deltaX: 0, deltaY: -160 });
  await sleep(600);
  check("the wheel stops a glide", (await run(faqTop)) > 40, await run(faqTop));
  await run(`scrollTo({ top: 0, behavior: "instant" }); history.replaceState(null, "", location.pathname)`);

  // Switching Lab modes keeps the window steady and hands focus to the new view
  await open("lab/#daily");
  const steadyHeight = await run(`document.querySelector(".lab-body").offsetHeight`);
  await hash("#hunt");
  check("the hunts show no formula difference", await run(`!document.querySelector("[data-delta]")?.checkVisibility()`));
  await sleep(320);
  check("a short view keeps the window's height", (await run(`document.querySelector(".lab-body").offsetHeight`)) >= steadyHeight - 90);
  check("the tab mark sits under the open tab", await run(`Math.abs(document.querySelector(".tab-mark").getBoundingClientRect().left - document.querySelector('.modes [aria-current]').getBoundingClientRect().left) < 2`));
  check("focus moves into the new view", await until(`!!document.activeElement.closest("[data-view=hunt]")`, 800));
  check("the mode is announced", await run(`document.querySelector(".lab-status").textContent.includes(document.querySelector('.modes [aria-current]').textContent)`));
  check("the slide cleans up", await until(`!document.documentElement.dataset.slide`, 800));
  await hash("#daily");
  await sleep(320);

  // The FAQ: search, nothing found, open everything, deep links, and no script at all
  await open("");
  const type = async (text) => {
    await click(".faq-search input");
    await run(`document.querySelector(".faq-search input").select()`);
    if (text) await send("Input.insertText", { text }); else await press("Backspace");
    await sleep(60);
  };
  const shownQuestions = () => count(".faq details:not([hidden])");
  await type("SDS");
  check("search keeps only matching questions", (await shownQuestions()) === 1, await shownQuestions());
  check("search marks what it found", (await count(".faq mark")) > 0);
  check("a found question is open", await run(`document.querySelector(".faq details:not([hidden])").open`));
  check("search says how many", /1/.test(await run(`document.querySelector(".faq-count").textContent`)));
  await type("zzzz");
  check("an empty search offers a way forward", await run(`!document.querySelector(".faq-empty").hidden && !!document.querySelector(".faq-empty a")`));
  await type("");
  check("clearing the search restores the list", (await shownQuestions()) === 8 && (await count(".faq details[open]")) === 1 && (await count(".faq mark")) === 0);
  await click("[data-faq-all]");
  check("expand all opens every answer", (await count(".faq details[open]")) === 8);
  await sleep(320);
  await click("[data-faq-all]");
  check("expand all closes them again", (await count(".faq details[open]")) === 0);
  await sleep(320);
  await run(`document.querySelector("#faq-safety summary").scrollIntoView({ block: "center", behavior: "instant" })`);
  await click("#faq-safety ~ .faq-link");
  check("each question copies its own link", await until(`navigator.clipboard.readText().then((t) => t.endsWith("#faq-safety"))`), await run(`navigator.clipboard.readText()`));
  await open("#faq-safety");
  check("a deep link opens its answer", await run(`document.querySelector("#faq-safety").open`));
  await send("Emulation.setScriptExecutionDisabled", { value: true });
  await open("");
  check("without scripts the FAQ still reads", (await count(".faq details .lead")) === 8 && await run(`getComputedStyle(document.querySelector(".faq-tools")).display === "none"`));
  await send("Emulation.setScriptExecutionDisabled", { value: false });

  // The pointer: each tool shows its own cursor, and a preview is exactly what the click does
  await open("lab/#free");
  await run(`document.querySelector('[data-act="free-load"][data-id="aspirin"]').click()`);
  await sleep(60);
  const graphNow = () => run(`JSON.stringify([...document.querySelectorAll("${canvas} .hit [data-atom]")].length + ":" + [...document.querySelectorAll("${canvas} .hit [data-bond]")].length)`);
  const cursorOver = (selector) => run(`getComputedStyle(document.querySelector(${JSON.stringify(selector)})).cursor`);
  for (const [name, target, previewed] of [
    ["bond", atom(0), `${canvas} .preview`], ["atom", atom(0), `${canvas} .preview`], ["ring", atom(3), `${canvas} .preview`], ["erase", atom(0), `${canvas} .preview.drop`],
  ]) {
    await tool(name);
    check(`${name} has its own cursor`, (await cursorOver(target)).includes(`cursors/${name}.svg`), await cursorOver(target));
    await move(await where(target));
    await sleep(60);
    check(`${name} previews its move`, (await count(previewed)) === 1, await count(previewed));
    const before = await graphNow();
    await click(target);
    await sleep(40);
    check(`${name} click changes the drawing`, (await graphNow()) !== before || name === "atom");
    await press("z", process.platform === "darwin" ? 4 : 2);
    await sleep(40);
  }
  await tool("ring");
  await move(await where(atom(0)));
  await sleep(60);
  check("a move with no room shows not-allowed", (await cursorOver(atom(0))) === "not-allowed" && (await count(`${canvas} .preview`)) === 0, await cursorOver(atom(0)));
  await tool("move");
  await move(await where(atom(0)));
  await sleep(60);
  check("move has no preview", (await count(`${canvas} .preview`)) === 0);
  check("move still grabs", (await cursorOver(`${canvas} .hit [data-atom="0"]`)) === "grab");
  await tool("bond");
  await move(await where(atom(0)));
  await sleep(220);
  check("resting on an atom names it", await run(`!document.querySelector(".atom-tip").hidden && /\\d\\s*\\/\\s*\\d/.test(document.querySelector(".atom-tip").textContent)`), await run(`document.querySelector(".atom-tip").textContent`));
  await move({ x: 2, y: 2 });
  await sleep(60);
  check("leaving the canvas clears the preview", (await count(`${canvas} .preview`)) === 0 && await run(`document.querySelector(".atom-tip").hidden`));
  await hash("#hunt");
  await click('[data-act="hunt-start"]');
  await sleep(40);
  await move(await where(".hunt-canvas [data-atom]"));
  await sleep(220);
  check("the hunt gives nothing away", (await count(".preview")) === 0 && await run(`document.querySelector(".atom-tip").hidden`));

  await open("");
  await move({ x: 300, y: 820 });
  await sleep(60);
  await move({ x: 310, y: 826 });
  await sleep(60);
  check("the grid lights under the pointer", await run(`document.querySelector(".grid-glow")?.dataset.on === ""`));
  await move(await where(atom(0)));
  await sleep(60);
  check("the grid stands down over the canvas", await run(`document.querySelector(".grid-glow").dataset.on === undefined`));

  // The toolbar names each tool and its key, on hover and on keyboard focus
  await open("lab/#free");
  const tipOf = (selector) => run(`(() => { const b = document.querySelector(${JSON.stringify(selector)}), t = getComputedStyle(b, "::after"); return [t.content, +t.opacity]; })()`);
  const ringTool = '.doc [data-tool="ring"]';
  await move(await where(ringTool));
  await sleep(320);
  const hovered = await tipOf(ringTool);
  check("a tool shows its name and key on hover", hovered[0].includes("(R)") && hovered[1] === 1, hovered);
  await move(await where(canvas));
  await run(`document.querySelector('.doc [data-tool="atom"]').focus()`);
  await press("Tab");
  await sleep(320);
  check("a tool shows its tip on keyboard focus", await run(`(() => { const t = getComputedStyle(document.activeElement, "::after"); return document.activeElement.matches("[data-tip]") && +t.opacity === 1; })()`));

  // The shortcut list opens with ?, and from the toolbar, and never takes the focus
  await move(await where(canvas));
  const listOpen = () => run(`!document.querySelector(".keys-panel").hidden`);
  check("the shortcut list starts closed", !(await listOpen()));
  const focused = await run(`document.activeElement === document.body ? "body" : document.activeElement.tagName`);
  await press("?");
  check("? opens the shortcut list", await listOpen());
  check("the list leaves the focus alone", (await run(`document.activeElement === document.body ? "body" : document.activeElement.tagName`)) === focused);
  check("the list names the element keys", /\bL\b/.test(await run(`document.querySelector(".keys-panel").textContent`)));
  await press("Escape");
  check("Escape closes the shortcut list", !(await listOpen()));
  await click("[data-help]");
  check("the toolbar opens the shortcut list", (await listOpen()) && await run(`document.querySelector("[data-help]").getAttribute("aria-expanded") === "true"`));
  await click("[data-help]");
  check("the toolbar closes it again", !(await listOpen()));
  await open("#faq");
  await run(`document.querySelector(".faq-tools input").focus()`);
  await press("?");
  check("? in a text field is only a character", !(await listOpen()) && (await run(`document.querySelector(".faq-tools input").value`)) === "?");

  // Home: the editor and the daily molecule in the hero
  await open("");
  check("home draws aspirin", (await count(`${canvas} .hit [data-atom]`)) === 13);
  await tool("erase");
  await click(atom(0));
  check("erase with a real click", (await count(`${canvas} .hit [data-atom]`)) === 12);
  await press("z", process.platform === "darwin" ? 4 : 2);
  check("undo with the keyboard", (await count(`${canvas} .hit [data-atom]`)) === 13);
  await press("z", (process.platform === "darwin" ? 4 : 2) | 8);
  check("redo with the keyboard", (await count(`${canvas} .hit [data-atom]`)) === 12);
  const daily = await run(`(() => { const d = Chem.dailyPick(Chem.localDate()); return { id: d.id, solve: d.solve }; })()`);
  await click("[data-challenge-open]");
  check("daily strip opens at home", await run(`!document.querySelector(".challenge").hidden`));
  for (const m of daily.solve) await playMove(m);
  check("daily solved at home", await until(`Chem.parseStore(localStorage.getItem("chemdraw-skill-lab")).daily.streak === 1`), await store());
  check("button shows the streak", await run(`/1/.test(document.querySelector("[data-challenge-open]").dataset.count)`));
  await open("");
  check("home remembers the streak", /1/.test(await run(`document.querySelector("[data-daily]").textContent`)));

  // Every level, played through the interface, reaches three stars
  await open("lab/");
  const levels = await run(`Chem.CHALLENGES.map((c) => ({ id: c.id, solve: c.solve }))`);
  for (const level of levels) {
    await hash(`#level-${level.id}`);
    for (const m of level.solve) await playMove(m);
    const won = await until(`!!document.querySelector(".mission .result")`, 1500);
    check(`level ${level.id}`, won && (await store())?.levels?.[level.id]?.stars === 3, { won, saved: (await store())?.levels?.[level.id] });
    if (level === levels[0]) {
      check("a win hands the focus to the next level", await run(`document.activeElement === document.querySelector(".mission .acts .primary")`));
      check("the rings fill one after another", (await run(`[...document.querySelectorAll(".result .rings path.on")].map((p) => getComputedStyle(p).animationDelay).join()`)) === "0s,0.12s,0.24s");
    }
    if (level === levels.at(-1)) {
      check("the badge toast links to the badges", (await run(`document.querySelector(".toast[data-on] a")?.getAttribute("href")`)) === "#dex");
      await click(".toast a");
      check("a new badge is highlighted", await until(`document.querySelectorAll(".badges .fresh").length > 0`, 1000));
      await sleep(500);
      check("the page goes to the new badge", await run(`(() => { const r = document.querySelector(".badges .fresh").getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })()`));
      await hash("#levels");
      await hash("#dex");
      check("the highlight is shown once", (await count(".badges .fresh")) === 0);
    }
  }
  check("twenty levels saved", Object.keys((await store()).levels).length === 20);
  const earned = (await store()).badges;
  check("level badges earned", ["first", "perfect", "xanthines", "complete"].every((b) => earned.includes(b)), earned);

  // Progress survives a reload and fills the route and the collection
  await open("lab/#levels");
  check("route shows solved levels", (await count(".node.solved")) === 20, await count(".node.solved"));
  check("each chapter counts its solved levels", await run(`[...document.querySelectorAll(".chapter")].every((c) => { const n = c.querySelectorAll(".node").length; return c.querySelector("h2 .count").textContent === n + " / " + n; })`));
  const arrowInk = (k) => run(`getComputedStyle(document.querySelectorAll(".rxn-row .rxn-arrow path")[${k}]).stroke`);
  const restInk = await arrowInk(0);
  await move(await where(".rxn-row .parent"));
  await sleep(220);
  check("a parent lights its arrow", (await arrowInk(0)) !== restInk, await arrowInk(0));
  check("only its own arrow", (await arrowInk(2)) === restInk, await arrowInk(2));
  await move({ x: 2, y: 2 });
  check("the Lab has no reading bar", (await count(".top .progress")) === 0);
  check("every chapter's stars are full", await run(`[...document.querySelectorAll(".progress.stars i i")].every((i) => new DOMMatrix(getComputedStyle(i).transform).a === 1)`));
  check("the star bar says its value", await run(`document.querySelector(".progress.stars").getAttribute("aria-valuenow") === "60"`));
  check("stars counted", (await run(`document.querySelector("[data-stat=stars]").textContent`)).startsWith("60"));
  await hash("#dex");
  check("collection unlocked", (await count(".dex > li:not(.locked)")) === 20);

  // A level by keyboard alone: the arrows walk the cursor, Enter acts
  await open("lab/");
  await run(`localStorage.removeItem("chemdraw-skill-lab")`);
  await open("lab/#level-salicylic");
  await run(`document.querySelector('.doc [data-tool="erase"]').focus()`);
  await press("Enter");
  for (let i = 0; i < 12 && !(await run(`document.activeElement === document.querySelector(${JSON.stringify(canvas)})`)); i++) await press("Tab");
  check("canvas takes keyboard focus", await run(`document.activeElement === document.querySelector(${JSON.stringify(canvas)})`));
  const cursorAt = () => run(`(() => { const c = document.querySelector("${canvas} .cursor"); return c ? [+c.getAttribute("cx"), +c.getAttribute("cy")] : null; })()`);
  check("focus shows a cursor", !!(await cursorAt()));
  const moves = levels.find((l) => l.id === "salicylic").solve.length;
  const delta = () => run(`document.querySelector("[data-delta]").textContent`);
  const deltaAtStart = await delta();
  check("the mission shows what the formula still needs", deltaAtStart === await run(`Chem.formulaDelta(Chem.load("aspirin"), Chem.targetOf(Chem.CHALLENGES.find((c) => c.id === "salicylic"))).map((d) => (d.n > 0 ? "+" : "\u2212") + Math.abs(d.n) + " " + d.s).join("\u3001")`), deltaAtStart);
  for (let n = 0; n < moves; n++) {
    const target = await run(`(() => { const c = document.querySelector(${JSON.stringify(atom(0))}); return [+c.getAttribute("cx"), +c.getAttribute("cy")]; })()`);
    for (let step = 0; step < 24; step++) {
      const at = await cursorAt();
      if (!at || Math.hypot(at[0] - target[0], at[1] - target[1]) < 1) break;
      const dx = target[0] - at[0], dy = target[1] - at[1];
      const order = Math.abs(dx) > Math.abs(dy)
        ? [dx > 0 ? "ArrowRight" : "ArrowLeft", dy > 0 ? "ArrowDown" : "ArrowUp"]
        : [dy > 0 ? "ArrowDown" : "ArrowUp", dx > 0 ? "ArrowRight" : "ArrowLeft"];
      await press(order[step % 3 === 2 ? 1 : 0]);
    }
    await press("Enter");
    await sleep(30);
    if (n === 0) check("the difference follows the drawing", (await run(`document.querySelector("[data-delta]")?.textContent ?? ""`)) !== deltaAtStart);
  }
  check("level solved by keyboard", await until(`!!document.querySelector(".mission .result")`, 1000), await count(`${canvas} .hit [data-atom]`));

  // Bond drag and a touch tap
  await hash("#free");
  await run(`document.querySelector('[data-act="free-load"][data-id="aspirin"]').click()`);
  await sleep(60);
  await tool("bond");
  const bonds = await count(`${canvas} .hit [data-bond]`);
  const pair = [0, 5];
  if (pair) {
    const from = await where(atom(pair[0])), to = await where(atom(pair[1]));
    await move(from);
    await mouse("mousePressed", from, { button: "left", clickCount: 1, buttons: 1 });
    for (let t = 0.2; t <= 1; t += 0.2) await mouse("mouseMoved", { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t }, { button: "left", buttons: 1 });
    await mouse("mouseReleased", to, { button: "left", clickCount: 1 });
    check("drag joins two atoms", (await count(`${canvas} .hit [data-bond]`)) === bonds + 1);
  } else check("drag joins two atoms", false, "no pair");

  await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 2 });
  check("a finger gets no hover features", await run(`!matchMedia("(hover: hover) and (pointer: fine)").matches`));
  await run(`document.querySelector('[data-act="free-load"][data-id="aspirin"]').click()`);
  await sleep(60);
  await tool("erase");
  const tap = await where(atom(0));
  await touch("touchStart", [tap]);
  await touch("touchEnd", []);
  check("touch tap edits the drawing", await until(`document.querySelectorAll(${JSON.stringify(`${canvas} .hit [data-atom]`)}).length === 12`, 1500));
  await run(`document.querySelector('[data-act="free-load"][data-id="aspirin"]').click()`);
  await sleep(60);
  await tool("bond");
  const before = await count(`${canvas} .hit [data-bond]`);
  const a = await where(atom(0)), b = await where(atom(5));
  await touch("touchStart", [a]);
  for (let t = 0.25; t <= 1; t += 0.25) await touch("touchMove", [{ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }]);
  await touch("touchEnd", []);
  await sleep(120);
  check("touch drag draws a bond", (await count(`${canvas} .hit [data-bond]`)) === before + 1, { before, after: await count(`${canvas} .hit [data-bond]`) });
  await send("Emulation.setTouchEmulationEnabled", { enabled: false });

  // Clipboard, the real download and the share link
  await open("lab/#free");
  check("nothing to export on a blank sheet", await run(`document.querySelector('[data-export="smiles"]').disabled`));
  await click('[data-act="free-load"][data-id="aspirin"]');
  await sleep(60);
  await click('[data-export="smiles"]');
  const copied = await until(`navigator.clipboard.readText().then((t) => t.length > 0)`);
  check("SMILES reaches the clipboard", copied);
  const smilesButton = '[data-export="smiles"]';
  check("a copy shows the tick", await run(`document.querySelector('${smilesButton}').hasAttribute("data-done")`));
  check("the tick keeps the button's size", await run(`document.querySelector('${smilesButton}').offsetWidth === ${await run(`document.querySelector('${smilesButton}').offsetWidth`)}`));
  await sleep(1600);
  check("the tick goes away", !(await run(`document.querySelector('${smilesButton}').hasAttribute("data-done")`)));
  await click('[data-export="link"]');
  await sleep(80);
  const link = await run(`navigator.clipboard.readText()`);
  check("share link copied", link.includes("#s="), link);
  await click('[data-export="cdxml"]');
  check("file really downloads", await (async () => {
    for (let i = 0; i < 60; i++) {
      const file = readdirSync(folder).find((f) => f.endsWith(".cdxml"));
      if (file && readFileSync(join(folder, file), "utf8").includes("<CDXML")) return true;
      await sleep(50);
    }
    return false;
  })(), readdirSync(folder));
  check("export badge earned", (await store()).badges.includes("export"), (await store()).badges);
  await hash(link.slice(link.indexOf("#")));
  check("share link draws the structure", (await count(`${canvas} .hit [data-atom]`)) === 13);
  const evil = await run(`btoa(JSON.stringify({ a: [['<img src=x onerror="window.pwned=1">', 10, 10]], b: [] })).replace(/\\+/g, "-").replace(/\\//g, "_").replace(/=+$/, "")`);
  await hash(`#s=${evil}`);
  await sleep(60);
  check("a forged link is refused", !(await run(`window.pwned === 1 || !!document.querySelector("img[src=x]")`)));

  // Spot the error: a miss costs a life, the right spot moves on, eight rounds earn the badge
  await open("lab/#hunt");
  await run(`Math.random = () => 0.25`);
  const rounds = await run(`Chem.makeHunt(Math.floor(0.25 * 2 ** 32)).map((r) => r.hot)`);
  await click("[data-act=hunt-start]");
  for (const [n, hot] of rounds.entries()) {
    await click(`.hunt-canvas .hit ${hot.atoms.length ? `[data-atom="${hot.atoms[0]}"]` : `[data-bond="${hot.bonds[0]}"]`}`);
    if (n < rounds.length - 1) {
      check(`hunt round ${n + 1}`, await until(`!document.querySelector("[data-act=hunt-next]").hidden`, 800));
      await click("[data-act=hunt-next]");
    }
  }
  check("hunt finished clean", await until(`Chem.parseStore(localStorage.getItem("chemdraw-skill-lab")).badges.includes("readback")`, 1000), await store());

  // Isomers from a blank canvas: ethanol, then dimethyl ether
  await open("lab/#isomers-C2H6O");
  const middle = await where(canvas);
  const draw = async (oxygen) => {
    await tool("bond");
    await clickAt(middle);
    await click(atom(0));
    await click(atom(1));
    await move(await where(atom(oxygen)));
    await press("o");
    await sleep(40);
  };
  await draw(2);
  check("first isomer found", (await count(".slots li:not(.empty)")) === 1, await count(".slots li:not(.empty)"));
  await click("[data-act=iso-clear]");
  await draw(1);
  check("isomer set finished", await until(`Chem.parseStore(localStorage.getItem("chemdraw-skill-lab")).isomers.C2H6O?.length === 2`, 800), await store());

  // Reset asks twice; broken and refused storage do not stop the page
  await open("lab/#dex");
  await click("[data-act=reset]");
  check("reset waits for a second click", (await store()) !== null && (await store()).badges.length > 0);
  await click("[data-act=reset]");
  check("reset clears progress", !(((await store())?.badges || []).length));
  await run(`localStorage.setItem("chemdraw-skill-lab", "{broken")`);
  await open("lab/#levels");
  check("corrupt progress is ignored", (await count(".node")) === 20);
  const script = await send("Page.addScriptToEvaluateOnNewDocument", { source: `Object.defineProperty(window, "localStorage", { get() { throw new DOMException("denied", "SecurityError"); } });` });
  await open("lab/#level-salicylic");
  for (const m of levels.find((l) => l.id === "salicylic").solve) await playMove(m);
  check("level plays with storage refused", await until(`!!document.querySelector(".mission .result")`, 1000));
  await send("Page.removeScriptToEvaluateOnNewDocument", script);

  // Viewer gestures on the gallery
  await open("");
  await click("img[data-zoom]");
  check("viewer opens", await until(`document.querySelector("dialog.lightbox").open`));
  const scale = () => run(`document.querySelector(".lb-stage img").style.transform`);
  const start = await scale();
  const stage = { x: 640, y: 380 };
  await send("Input.dispatchMouseEvent", { type: "mouseWheel", ...stage, deltaX: 0, deltaY: -300 });
  check("wheel zooms", await until(`document.querySelector(".lb-stage img").style.transform !== ${JSON.stringify(start)}`, 800));
  await click('[data-lb="fit"]');
  await sleep(60);
  await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 2 });
  const fitted = await scale();
  await touch("touchStart", [{ x: 600, y: 380, id: 0 }, { x: 680, y: 380, id: 1 }]);
  for (let d = 60; d <= 240; d += 60) await touch("touchMove", [{ x: 600 - d, y: 380, id: 0 }, { x: 680 + d, y: 380, id: 1 }]);
  await touch("touchEnd", []);
  check("pinch zooms", await until(`document.querySelector(".lb-stage img").style.transform !== ${JSON.stringify(fitted)}`, 800), { fitted, now: await scale() });
  await send("Emulation.setTouchEmulationEnabled", { enabled: false });

  // Every page at phone width, both languages and colour schemes, and with motion off
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  for (const scheme of ["light", "dark"]) {
    await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: scheme }, { name: "prefers-reduced-motion", value: "reduce" }] });
    for (const page of ["", "en/", "lab/", "en/lab/"]) {
      for (const route of page.includes("lab") ? ["#daily", "#levels", "#hunt", "#isomers", "#dex", "#free"] : [""]) {
        await open(page + route);
        const wide = await run(`document.documentElement.scrollWidth`);
        check(`${page || "home"}${route} fits 390 px (${scheme})`, wide <= 390, wide);
      }
    }
  }
  await open("");
  check("no glow without motion", (await count(".grid-glow")) === 0);
  await run(`document.querySelector('a[href="#faq"]').click()`);
  check("jumps are immediate without motion", await run(`Math.abs(document.querySelector("#faq").getBoundingClientRect().top - 72) < 3`));
  await open("lab/#daily");
  await hash("#hunt");
  check("modes swap without a transition", await run(`!document.documentElement.dataset.slide && !document.querySelector("[data-view=hunt]").hidden`));
  await open("");
  check("no replay without motion", await run(`!document.querySelector(".replay") || document.querySelector(".replay").hidden || getComputedStyle(document.querySelector(".replay")).display === "none"`));

  check("no errors, failed requests or requests off the site", problems.length === 0, problems.slice(0, 12));
}

try {
  await main();
} catch (e) {
  failures.push(`stopped: ${e.stack || e}`);
}
ws.close();
chrome.kill();
await sleep(150);
try { rmSync(folder, { recursive: true, force: true }); } catch {}
console.log(`${passed.length} checks passed`);
if (failures.length) {
  console.log(failures.map((f) => `FAIL ${f}`).join("\n"));
  process.exit(1);
}
process.exit(0);
