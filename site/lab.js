// The Molecule Lab: the daily molecule, the route map of levels, Spot the error, the isomer
// hunt, the collection and the sketchpad. The hash in the address says which is open, so every
// one can be linked to. Rules and scoring are in chem.js, the canvas in editor.js, the words in
// words.<language>.js. Progress stays in this browser.

(() => {
  const root = document.querySelector(".lab");
  const T = globalThis.ChemWords;
  if (!root || !T || !globalThis.ChemEditor) return;
  const { MOLS, CHALLENGES, CHAPTERS, ISOMERS, BADGES, ROUNDS, fmt, load, analyse, neighbours, toSmiles, drawMarkup, thumb, graphKey, targetOf, record, stars,
    localDate, dailyNumber, dailyPick, dailyShare, encodeDrawing, decodeDrawing, earned, isomerKey, makeHunt, formulaDelta } = globalThis.Chem;
  const { mount, openStore, solveDaily, burst } = globalThis.ChemEditor;
  const L = T.lab, C = T.challenge, D = T.daily;

  const labUrl = location.href.split("#")[0];
  const store = openStore();
  const today = localDate();
  const editor = mount(root.querySelector(".doc"), T, { labUrl });
  const mission = root.querySelector(".mission");
  const views = [...root.querySelectorAll("[data-view]")];
  const modes = [...root.querySelectorAll("[data-mode]")];
  const toastEl = root.querySelector(".toast");
  const starBar = root.querySelector(".progress.stars");
  const tabs = root.querySelector(".modes");
  const tabMark = root.querySelector(".tab-mark");
  const status = root.querySelector(".lab-status");
  const labWindow = root.querySelector(".lab-window");
  const openTab = () => modes.find((m) => m.hasAttribute("aria-current"));
  // On a wide screen the side panel holds the task; below the canvas, on a phone, it is out of sight.
  const quest = Object.assign(document.createElement("p"), { className: "quest", hidden: true });
  root.querySelector(".board .doc-bar").after(quest);

  const blank = () => ({ atoms: [], bonds: [] });
  const nameOf = (id) => (MOLS[id] ? T.names[id] : C.tasks[id].name);
  const levelOf = (id) => CHALLENGES.find((c) => c.id === id);
  const subscript = (formula) => formula.replace(/\d+/g, "<sub>$&</sub>");

  // Three benzene rings, filled for each star earned: the one ornament of the Lab.
  const rings = (n) => {
    const ring = (on, x) => `<path class="${on ? "on" : ""}" transform="translate(${x} 0)" d="M8 1.2l5.9 3.4v6.8L8 14.8l-5.9-3.4V4.6z"/>`;
    return `<svg class="rings" viewBox="0 0 52 16" role="img" aria-label="${fmt(L.starsLabel, { n })}">${[0, 1, 2].map((k) => ring(k < n, k * 18)).join("")}</svg>`;
  };

  // ---- toasts, stats and badges -----------------------------------------------------

  let toastTimer = 0, newBadges = [];
  function toast(text, link) {
    clearTimeout(toastTimer);
    toastEl.textContent = text;
    if (link) toastEl.insertAdjacentHTML("beforeend", ` <a href="#dex">${link}</a>`);
    toastEl.dataset.on = "";
    toastTimer = setTimeout(() => { delete toastEl.dataset.on; }, link ? 7000 : 4200);
  }

  function paintStats() {
    const levels = Object.values(store.data.levels);
    const fill = (key, value) => { root.querySelector(`[data-stat=${key}]`).textContent = value; };
    fill("stars", `${levels.reduce((t, l) => t + l.stars, 0)} / ${CHALLENGES.length * 3}`);
    fill("streak", store.data.daily.streak);
    fill("compounds", `${levels.length} / ${CHALLENGES.length}`);
    fill("badges", `${store.data.badges.length} / ${BADGES.length}`);
    const won = levels.reduce((t, l) => t + l.stars, 0);
    starBar.setAttribute("aria-valuenow", won);
    starBar.setAttribute("aria-valuemax", CHALLENGES.length * 3);
    starBar.setAttribute("aria-label", L.stats.stars);
    starBar.innerHTML = CHAPTERS.map((chapter) => {
      const list = CHALLENGES.filter((c) => c.chapter === chapter);
      const got = list.reduce((t, c) => t + (store.data.levels[c.id]?.stars || 0), 0);
      return `<i style="flex-grow:${list.length}"><i style="transform:scaleX(${got / (list.length * 3)})"></i></i>`;
    }).join("");
  }

  function saveProgress() {
    const now = earned(store.data);
    const fresh = now.filter((b) => !store.data.badges.includes(b));
    store.data.badges = now;
    store.save();
    paintStats();
    if (!fresh.length) return;
    newBadges.push(...fresh);
    const said = fresh.map((b) => fmt(L.badgeUnlocked, { title: L.badges[b].title })).join(" ");
    if (location.hash === "#dex") {
      toast(said);
      paintDex();
    } else toast(said, L.badgeView);
  }

  async function copy(text, done, fallback, btn) {
    try {
      await navigator.clipboard.writeText(text);
      if (btn) flashDone(btn);
      toast(done);
    } catch {
      toast(fallback);
    }
  }

  // ---- views ------------------------------------------------------------------------

  let onChange = null, onWin = null;
  editor.on("change", (g) => { if (onChange) onChange(g); });
  editor.on("win", (result) => { if (onWin) onWin(result); });
  editor.on("export", () => { store.data.exported = true; saveProgress(); });

  function markTab() {
    const tab = openTab();
    if (!tab) return;
    tabMark.style.width = `${tab.offsetWidth}px`;
    tabMark.style.transform = `translateX(${tab.offsetLeft}px)`;
    if (tab.offsetLeft < tabs.scrollLeft || tab.offsetLeft + tab.offsetWidth > tabs.scrollLeft + tabs.clientWidth) tabs.scrollLeft = tab.offsetLeft - 8;
  }

  function view(name, mode) {
    quest.hidden = true;
    views.forEach((v) => { v.hidden = v.dataset.view !== name; });
    modes.forEach((m) => {
      if (m.dataset.mode === mode) m.setAttribute("aria-current", "page"); else m.removeAttribute("aria-current");
    });
    markTab();
    onChange = null;
    onWin = null;
    editor.quest(null);
  }

  // ---- challenges: the daily molecule and the levels --------------------------------

  const stillNeeded = (g, target) => formulaDelta(g, target).map((d) => `${d.n > 0 ? "+" : "\u2212"}${Math.abs(d.n)} ${d.s}`).join(L.deltaJoin) || L.deltaDone;

  function paintQuest(c, g, moves) {
    const left = stillNeeded(g, targetOf(c));
    quest.lastChild.textContent = `${L.moves} ${moves} / ${c.solve.length} \u00b7 ${left === L.deltaDone ? left : `${L.delta} ${left}`}`;
  }

  function missionFor(c, title, sub) {
    const task = C.tasks[c.id];
    const target = analyse(targetOf(c));
    quest.innerHTML = `${task.task}<span data-progress></span>`;
    quest.hidden = false;
    paintQuest(c, load(c.mol), 0);
    mission.innerHTML = `
      <h2>${title}</h2>
      ${sub ? `<p class="sub">${sub}</p>` : ""}
      <p class="task">${task.task}</p>
      <dl class="facts">
        <div><dt>${L.from}</dt><dd>${T.names[c.mol]}</dd></div>
        <div><dt>${L.target}</dt><dd>${target.html}</dd></div>
        <div><dt>${L.moves}</dt><dd data-moves>0</dd></div>
        <div><dt>${L.par}</dt><dd>${c.solve.length}</dd></div>
        <div class="delta"><dt>${L.delta}</dt><dd data-delta>${stillNeeded(load(c.mol), targetOf(c))}</dd></div>
      </dl>
      <div class="acts"><button type="button" class="btn sm" data-act="hint">${C.hint}</button><button type="button" class="btn sm" data-act="restart">${L.restart}</button></div>
      <p class="ch-hint" hidden>${task.hint}</p>
      <p class="sub">${L.starsHelp}</p>`;
  }

  function winPanel(c, moves, got, actions) {
    const task = C.tasks[c.id];
    quest.hidden = true;
    mission.innerHTML = `
      <h2>${task.name}</h2>
      <div class="result">${rings(got)}<p>${fmt(L.solvedIn, { moves })}</p></div>
      <p class="task">${task.fact}</p>
      <div class="acts">${actions}</div>`;
    mission.querySelector(".acts a, .acts button")?.focus({ preventScroll: true });
  }

  let current = null;
  function playChallenge(c, finish) {
    const target = targetOf(c);
    current = { c, hinted: false, finish };
    editor.restart(c.mol);
    current.quest = editor.quest({ key: graphKey(target), formula: analyse(target).html });
    onChange = (g) => {
      const el = mission.querySelector("[data-moves]");
      if (el) el.textContent = current.quest.moves;
      const delta = mission.querySelector("[data-delta]");
      if (delta) delta.textContent = stillNeeded(g, target);
      paintQuest(c, g, current.quest.moves);
    };
    onWin = ({ moves }) => {
      finish(moves);
      saveProgress();
      burst(editor.canvas);
      // Let the burst play on the canvas, then show the stars and the way on if they are out of sight
      setTimeout(() => {
        const panel = mission.getBoundingClientRect();
        if (!mission.closest("[hidden]") && (panel.top < 0 || panel.top > innerHeight / 2)) glide(mission);
      }, 900);
    };
  }

  function playLevel(c) {
    view("board", "levels");
    const chapter = L.chapters[c.chapter].title, k = CHALLENGES.indexOf(c);
    const sub = store.data.levels[c.id] ? rings(store.data.levels[c.id].stars) : "";
    playChallenge(c, (moves) => {
      record(store.data, c.id, { moves, hinted: current.hinted });
      const next = CHALLENGES.slice(k + 1).concat(CHALLENGES.slice(0, k)).find((x) => !store.data.levels[x.id]);
      const got = stars(moves, c.solve.length, current.hinted);
      winPanel(c, moves, got, `${next ? `<a class="btn sm primary" href="#level-${next.id}">${L.nextLevel}</a>` : ""}<a href="#levels">${L.backToRoute}</a><a href="#dex">${L.modes.dex}</a>`);
    });
    missionFor(c, `${fmt(C.title, { n: k + 1, total: CHALLENGES.length })}: ${chapter}`, sub);
    mission.insertAdjacentHTML("beforeend", `<p class="sub"><a href="#levels">${L.backToRoute}</a></p>`);
  }

  function playDaily() {
    view("board", "daily");
    const c = dailyPick(today), done = store.data.daily.solved[today];
    playChallenge(c, (moves) => {
      const got = solveDaily(store.data, c, today, moves, current.hinted);
      current.score = { got, moves };
      winPanel(c, moves, got, `<button type="button" class="btn sm primary" data-act="share">${D.share}</button><a href="#levels">${L.modes.levels}</a>`);
    });
    missionFor(c, fmt(D.title, { n: dailyNumber(today) }), done ? `${rings(done.stars)} ${D.solved}` : "");
    if (done) current.score = { got: done.stars, moves: done.moves };
  }

  // ---- route map --------------------------------------------------------------------

  const arrow = '<svg class="rxn-arrow" viewBox="0 0 56 14" aria-hidden="true"><path d="M1 7h46"/><path class="head" d="M55 7l-10-4.6 2.6 4.6-2.6 4.6z"/></svg>';

  function showRoute() {
    view("route", "levels");
    root.querySelector("[data-view=route]").innerHTML = CHAPTERS.map((chapter) => {
      const list = CHALLENGES.filter((c) => c.chapter === chapter);
      const parents = [...new Set(list.map((c) => c.mol))];
      const rows = parents.map((mol) => `
        <li class="rxn-row">
          <figure class="parent">${thumb(load(mol), T.names[mol])}<figcaption>${T.names[mol]}</figcaption></figure>
          ${arrow}
          <ul class="products">${list.filter((c) => c.mol === mol).map((c) => {
            const got = store.data.levels[c.id];
            const task = C.tasks[c.id];
            return `<li><a class="node${got ? " solved" : ""}" href="#level-${c.id}">
              <span class="frame">${got ? thumb(targetOf(c), task.name) : `<span class="open"><span>${analyse(targetOf(c)).html}</span></span>`}</span>
              <span class="label">${task.name}</span>${got ? rings(got.stars) : `<span class="sub">${L.unsolved}</span>`}</a></li>`;
          }).join("")}</ul>
        </li>`).join("");
      const solved = list.filter((c) => store.data.levels[c.id]).length;
      return `<section class="chapter"><h2>${L.chapters[chapter].title} <span class="count">${solved} / ${list.length}</span></h2><p>${L.chapters[chapter].text}</p><ol class="scheme-rows">${rows}</ol></section>`;
    }).join("");
  }

  // ---- spot the error ---------------------------------------------------------------

  const board = root.querySelector("[data-view=hunt]");
  let game = null;

  function drawnRound() {
    const round = game.rounds[game.at], g = round.shown;
    const info = analyse(g);
    const svg = board.querySelector(".hunt-canvas");
    let markup = drawMarkup(g, { flags: false, box: false });
    if (game.found) {
      const marks = round.hot.atoms.map((i) => `<circle class="found" cx="${g.atoms[i].x}" cy="${g.atoms[i].y}" r="15"/>`).join("");
      markup = marks + drawMarkup(g, { flags: false, box: false, hit: false });
    }
    svg.innerHTML = markup;
    svg.querySelectorAll("[data-atom]").forEach((el) => {
      const i = +el.dataset.atom;
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", `${fmt(L.huntAtom, { sym: g.atoms[i].s })}, ${neighbours(g)[i].length}, H${info.hyd[i]}`);
    });
    svg.querySelectorAll("[data-bond]").forEach((el) => {
      const b = g.bonds[+el.dataset.bond];
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", `${fmt(L.huntBond, { order: T.order[b.o - 1] })}, ${g.atoms[b.a].s}–${g.atoms[b.b].s}`);
    });
  }

  function paintRound(message) {
    const round = game.rounds[game.at];
    const name = nameOf(round.id), formula = analyse(round.truth);
    board.querySelector(".hunt-play").hidden = false;
    board.querySelector(".hunt-meta").innerHTML = `<b>${fmt(L.huntRound, { n: game.at + 1, total: ROUNDS })}</b><span>${fmt(L.huntLives, { n: game.lives })}</span>`;
    board.querySelector(".hunt-truth").innerHTML = `${thumb(round.truth, name)}<figcaption><b>${L.huntTruth}</b> ${name}, ${formula.html}</figcaption>`;
    board.querySelector(".hunt-caption").textContent = `${L.huntDrawn}${game.at >= 4 ? ` ${L.huntMirror}` : ""}`;
    board.querySelector(".hunt-say").textContent = message || "";
    const go = board.querySelector("[data-act=hunt-next]");
    go.hidden = !game.found;
    go.textContent = game.at + 1 < ROUNDS ? L.huntNext : L.huntAgain;
    drawnRound();
  }

  function endGame(text) {
    store.data.hunt.best = Math.max(store.data.hunt.best, game.cleared);
    saveProgress();
    const best = store.data.hunt.best;
    board.querySelector(".hunt-say").textContent = text || fmt(L.huntOver, { n: game.cleared, best });
    board.querySelector("[data-act=hunt-start]").textContent = L.huntAgain;
    board.querySelector("[data-act=hunt-start]").hidden = false;
    board.querySelector("[data-act=hunt-next]").hidden = true;
    board.querySelector(".hunt-best").textContent = fmt(L.huntBest, { n: best });
    game.over = true;
  }

  function huntPick(target) {
    if (!game || game.over || game.found) return;
    const atom = target.closest("[data-atom]"), bond = target.closest("[data-bond]");
    if (!atom && !bond) return;
    const round = game.rounds[game.at];
    const hit = atom ? round.hot.atoms.includes(+atom.dataset.atom) : round.hot.bonds.includes(+bond.dataset.bond);
    if (hit) {
      game.found = true;
      game.cleared++;
      paintRound(fmt(L.huntFound, { kind: L.huntKinds[round.kind] }));
      board.querySelector("[data-act=hunt-next]").focus();
      if (game.cleared === ROUNDS) {
        burst(board.querySelector(".hunt-drawn"));
        endGame(L.huntClear);
      }
    } else {
      game.lives--;
      if (game.lives > 0) return paintRound(L.huntMiss);
      game.found = true;
      paintRound(fmt(L.huntFound, { kind: L.huntKinds[round.kind] }));
      endGame();
    }
  }

  function huntStart() {
    game = { rounds: makeHunt(Math.floor(Math.random() * 2 ** 32)), at: 0, lives: 3, cleared: 0, found: false, over: false };
    board.querySelector("[data-act=hunt-start]").hidden = true;
    paintRound();
  }
  board.querySelector(".hunt-canvas").addEventListener("click", (e) => huntPick(e.target));
  board.querySelector(".hunt-canvas").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); huntPick(e.target); }
  });

  function showHunt() {
    view("hunt", "hunt");
    if (store.data.hunt.best) board.querySelector(".hunt-best").textContent = fmt(L.huntBest, { n: store.data.hunt.best });
  }

  // ---- isomer hunt ------------------------------------------------------------------

  function foundIsomers(formula) {
    return (store.data.isomers[formula] || []).map((code) => decodeDrawing(code)).filter(Boolean);
  }

  function paintIsomers(set) {
    const found = foundIsomers(set.formula);
    const slots = Array.from({ length: set.count }, (_, k) => (found[k] ? `<li>${thumb(found[k], set.formula)}</li>` : '<li class="empty"></li>')).join("");
    const chips = ISOMERS.map((s) => {
      const have = foundIsomers(s.formula).length;
      return `<a href="#isomers-${s.formula}"${s === set ? ' aria-current="true"' : ""}><b>${subscript(s.formula)}</b><span>${have}/${s.count}</span></a>`;
    }).join("");
    mission.innerHTML = `
      <h2>${L.modes.isomers}</h2>
      <p class="task">${L.isoIntro}</p>
      <p class="sub">${L.isoPick}</p>
      <div class="chips">${chips}</div>
      <p class="sub" data-iso-count>${found.length >= set.count ? L.isoDone : fmt(L.isoProgress, { n: found.length, total: set.count })}</p>
      <ol class="slots">${slots}</ol>
      <div class="acts"><button type="button" class="btn sm" data-act="iso-clear">${L.isoClear}</button></div>`;
  }

  function showIsomers(set) {
    view("board", "isomers");
    editor.show(blank(), set.formula, set.formula);
    let last = null;
    paintIsomers(set);
    onChange = (g) => {
      const key = isomerKey(g, set.formula);
      if (!key || key === last) { last = key; return; }
      last = key;
      const keys = foundIsomers(set.formula).map((x) => graphKey(x));
      if (keys.includes(key)) return editor.status(L.isoSeen);
      store.data.isomers[set.formula] = [...(store.data.isomers[set.formula] || []), encodeDrawing(g)];
      const done = keys.length + 1 >= set.count;
      saveProgress();
      paintIsomers(set);
      editor.status(done ? L.isoDone : L.isoFound);
      burst(editor.canvas);
    };
  }

  // ---- collection -------------------------------------------------------------------

  function showDex() {
    view("dex", "dex");
    paintDex();
  }

  function paintDex() {
    const plates = CHALLENGES.map((c) => {
      const got = store.data.levels[c.id], task = C.tasks[c.id];
      if (!got) return `<li class="locked"><a href="#level-${c.id}"><span class="frame"><span class="open"><span>${analyse(targetOf(c)).html}</span></span></span><b>${L.lockedName}</b></a></li>`;
      const smiles = toSmiles(targetOf(c));
      return `<li>
        <span class="frame">${thumb(targetOf(c), task.name)}</span>
        <h3>${task.name}</h3>${rings(got.stars)}
        <p>${task.fact}</p>
        <code>${smiles}</code>
        <div class="acts"><button type="button" class="btn sm" data-act="dex-save" data-id="${c.id}">${L.saveCdxml}</button><button type="button" class="btn sm" data-act="dex-ask" data-id="${c.id}">${L.copyAsk}</button><a href="#s=${encodeDrawing(targetOf(c))}">${L.openBoard}</a></div>
      </li>`;
    }).join("");
    const have = store.data.badges;
    const badges = BADGES.map((b) => `<li class="${have.includes(b) ? "on" : ""}${newBadges.includes(b) ? " fresh" : ""}"><b>${L.badges[b].title}</b><span>${L.badges[b].text}</span></li>`).join("");
    root.querySelector("[data-view=dex]").innerHTML = `
      <p class="intro">${L.dexIntro}</p>
      ${Object.keys(store.data.levels).length ? "" : `<p class="intro"><a href="#levels">${L.dexEmpty}</a></p>`}
      <ul class="dex">${plates}</ul>
      <h2>${L.badgesTitle}</h2>
      <ul class="badges">${badges}</ul>`;
    newBadges = [];
  }

  // ---- sketchpad and shared links ---------------------------------------------------

  function missionFree() {
    const chips = Object.keys(MOLS).map((m) => `<button type="button" class="btn sm" data-act="free-load" data-id="${m}">${T.names[m]}</button>`).join("");
    mission.innerHTML = `
      <h2>${L.modes.free}</h2>
      <p class="task">${L.freeIntro}</p>
      <p class="sub">${L.freeLoad}</p>
      <div class="chips"><button type="button" class="btn sm" data-act="free-blank">${L.freeBlank}</button>${chips}</div>`;
  }
  function showFree() {
    view("board", "free");
    missionFree();
    editor.show(blank(), "structure", T.drawing);
  }
  function openShared(code) {
    view("board", "free");
    missionFree();
    const g = decodeDrawing(code);
    editor.show(g || blank(), "structure", T.drawing);
    editor.status(g ? L.sharedLoaded : L.sharedBad);
  }

  // ---- routes and shared buttons ----------------------------------------------------

  function route() {
    const h = location.hash.slice(1);
    if (h.startsWith("s=")) return openShared(h.slice(2));
    if (h.startsWith("level-") && levelOf(h.slice(6))) return playLevel(levelOf(h.slice(6)));
    if (h.startsWith("isomers-")) {
      const set = ISOMERS.find((s) => s.formula === h.slice(8));
      if (set) return showIsomers(set);
    }
    const open = { levels: showRoute, hunt: showHunt, isomers: () => showIsomers(ISOMERS[0]), dex: showDex, free: showFree }[h];
    return (open || playDaily)();
  }

  // A new mode slides in from the side its tab is on, and focus goes with it. route() runs inside
  // the transition so both ends are captured; without one the swap is immediate.
  function settle(before) {
    const tab = openTab();
    if (tab === before) return;
    status.textContent = tab.textContent;
    const shown = views.find((v) => !v.hidden);
    const heading = shown.querySelector("h2, .intro");
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    const fresh = root.querySelector(".badges .fresh");
    if (fresh) glide(fresh);
    else if (labWindow.getBoundingClientRect().top < 0) glide(labWindow);
  }
  addEventListener("hashchange", () => {
    const before = openTab();
    if (!document.startViewTransition || !matchMedia("(prefers-reduced-motion: no-preference)").matches) {
      route();
      settle(before);
      return;
    }
    const clear = () => { delete document.documentElement.dataset.slide; };
    document.startViewTransition(() => {
      route();
      document.documentElement.dataset.slide = modes.indexOf(openTab()) < modes.indexOf(before) ? "back" : "next";
      settle(before);
    }).finished.then(clear, clear);
  });
  addEventListener("resize", markTab);

  root.addEventListener("click", (e) => {
    const act = e.target.closest("[data-act]");
    if (!act) return;
    const name = act.dataset.act, id = act.dataset.id;
    if (name === "hint") {
      current.hinted = true;
      mission.querySelector(".ch-hint").hidden = false;
    } else if (name === "restart") {
      route();
    } else if (name === "share") {
      const { got, moves } = current.score;
      const text = dailyShare(D, today, got, moves, `${labUrl}#daily`);
      if (navigator.share && matchMedia("(pointer: coarse)").matches) navigator.share({ text }).catch(() => {});
      else copy(text, D.shared, fmt(D.shareText, { text }), act);
    } else if (name === "hunt-start") {
      huntStart();
    } else if (name === "hunt-next") {
      if (game.at + 1 >= ROUNDS) return huntStart();
      game.at++;
      game.found = false;
      paintRound();
    } else if (name === "iso-clear") {
      editor.show(blank(), location.hash.slice(9) || ISOMERS[0].formula, location.hash.slice(9) || ISOMERS[0].formula);
    } else if (name === "dex-save") {
      toast(fmt(T.download, { file: editor.saveFile(targetOf(levelOf(id)), id) }));
      store.data.exported = true;
      saveProgress();
    } else if (name === "dex-ask") {
      const text = fmt(L.ask, { name: C.tasks[id].name });
      copy(text, T.copiedAsk, text, act);
    } else if (name === "free-load") {
      editor.show(load(id), id, T.names[id]);
    } else if (name === "free-blank") {
      editor.show(blank(), "structure", T.drawing);
    } else if (name === "reset") {
      if (act.dataset.armed === undefined) {
        act.dataset.armed = "";
        act.textContent = L.resetConfirm;
        setTimeout(() => { delete act.dataset.armed; act.textContent = L.reset; }, 5000);
      } else {
        store.clear();
        delete act.dataset.armed;
        act.textContent = L.reset;
        paintStats();
        route();
        toast(L.resetDone);
      }
    }
  });

  root.classList.add("ready");
  saveProgress();
  route();
  document.fonts.ready.then(() => { markTab(); tabs.dataset.ready = ""; });
})();
