// The structure editor: a document you can bond, rename, grow, move, erase and clean up, with
// the Analysis caption and the agent's readback line recomputed from what is on the canvas. What
// is drawn can be copied as SMILES, saved as an ACS Document 1996 CDXML file that opens in
// ChemDraw, or turned into a link. ChemEditor.mount serves the hero and the Lab; at the end of
// this file the hero is mounted with today's daily molecule. The chemistry itself is in chem.js
// and all words come from words.<language>.js. The home page reads completely without this file.

(() => {
  const { MOLS, W, H, EL, fmt, load, analyse, bondLength, remove, inside, toSmiles, toCdxml, cleanUp, drawMarkup,
    graphKey, targetOf, stars, localDate, dailyNumber, dailyPick, nextStreak, dailyShare, encodeDrawing, decodeDrawing, emptyStore, parseStore,
    record, earned, STORE_KEY, applyTool, previewMarkup } = globalThis.Chem;

  // Progress in this browser, or only in this page when storage is refused.
  function openStore() {
    let data;
    try { data = parseStore(localStorage.getItem(STORE_KEY)); } catch { data = emptyStore(); }
    return {
      data,
      save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(this.data)); } catch { /* not kept */ } },
      clear() { this.data = emptyStore(); try { localStorage.removeItem(STORE_KEY); } catch { /* nothing kept */ } },
    };
  }

  // Note a solved daily molecule: the level, the day and the streak. Returns the stars.
  function solveDaily(store, c, date, moves, hinted) {
    record(store, c.id, { moves, hinted });
    const today = stars(moves, c.solve.length, hinted);
    const old = store.daily.solved[date];
    if (!old || today > old.stars) store.daily.solved[date] = { stars: today, moves };
    store.daily = nextStreak(store.daily, date);
    return today;
  }

  // A shower of atom labels and rings from the middle of a canvas.
  function burst(canvas) {
    if (!matchMedia("(prefers-reduced-motion: no-preference)").matches) return;
    const bits = ["C", "N", "O", "H", "S", "⬡", "⬡", "✓"];
    for (let k = 0; k < 26; k++) {
      const el = document.createElement("span");
      el.className = "confetti";
      el.textContent = bits[k % bits.length];
      const angle = (k / 26) * Math.PI * 2 + Math.random() * 0.4;
      const reach = 70 + Math.random() * 110;
      el.style.setProperty("--dx", `${Math.cos(angle) * reach}px`);
      el.style.setProperty("--dy", `${Math.sin(angle) * reach - 40}px`);
      el.style.setProperty("--r", `${(Math.random() - 0.5) * 540}deg`);
      el.style.setProperty("--d", `${Math.random() * 120}ms`);
      el.dataset.el = el.textContent;
      canvas.append(el);
      setTimeout(() => el.remove(), 1600);
    }
  }

  function mount(doc, T, options = {}) {
    const svg = doc.querySelector(".mol");
    const canvas = doc.querySelector(".doc-canvas");
    const palette = doc.querySelector(".palette");
    const tabs = [...doc.querySelectorAll("[data-mol]")];
    const status = doc.querySelector(".status");
    const undoBtn = doc.querySelector("[data-undo]");
    const resetBtn = doc.querySelector(".reset");
    const replayBtn = doc.querySelector(".replay");
    const cleanBtn = doc.querySelector('[data-tool-action="clean"]');
    const exportBar = doc.querySelector(".export");
    const fname = doc.querySelector(".fname");
    const motion = matchMedia("(prefers-reduced-motion: no-preference)");
    const fine = matchMedia("(hover: hover) and (pointer: fine)");
    const canvasBox = doc.querySelector(".doc-canvas");
    const tip = Object.assign(document.createElement("div"), { className: "atom-tip", hidden: true });
    tip.setAttribute("aria-hidden", "true");
    canvasBox.append(tip);
    const point = svg.createSVGPoint();
    const NS = "http://www.w3.org/2000/svg";

    const states = {};
    const listeners = { change: [], win: [], export: [] };
    const emit = (kind, value) => listeners[kind].forEach((fn) => fn(value));
    let tool = "bond";
    let st;
    let drag = null, link = null, ghost = null, swallowClick = false;
    let aim = null, byKeyboard = false, tipped = false;
    let spot = null, tipTimer = 0, previewQueued = false;
    let quest = null;
    let tween = 0;

    const fresh = (name, g, title) => ({ name, title, g, original: JSON.stringify(g), undo: [], redo: [] });
    const stateOf = (n) => {
      if (!states[n]) states[n] = fresh(n, load(n), T.names[n]);
      return states[n];
    };

    // ---- page updates -------------------------------------------------------------

    const setText = (sel, html) => { const el = doc.querySelector(sel); if (el) el.innerHTML = html; };

    function refreshLog(info) {
      const original = analyse(JSON.parse(st.original));
      const known = MOLS[st.name];
      setText("[data-log=ask]", fmt(T.ask, { name: st.title }).replace(/([\u4e00-\u9fff])([A-Z])/g, "$1 $2").replace(/([A-Za-z0-9])([\u4e00-\u9fff])/g, "$1 $2"));
      setText("[data-log=resolve]", known ? `${st.name} → ${known.smiles}` : st.title);
      setText("[data-log=build]", fmt(T.build, { name: st.name }));
      if (!st.g.atoms.length) {
        setText("[data-log=readback]", `${T.empty} <span class="no">✗</span>`);
      } else if (quest && quest.doc === st) {
        // In a challenge the readback is checked against the target structure instead.
        const hit = quest.solved(st.g, info);
        setText("[data-log=readback]", hit ? `${info.html} ${T.challenge.matches} <span class="ok">✓</span>` : `${info.html} → ${fmt(T.challenge.aim, { formula: quest.formula })}`);
      } else if (info.text === original.text) {
        setText("[data-log=readback]", `${info.html} ${T.matches} <span class="ok">✓</span>`);
      } else {
        setText("[data-log=readback]", `${info.html} ${fmt(T.differs, { input: original.html })} <span class="no">✗</span>`);
      }
    }

    function paintCursor() {
      svg.querySelector(".cursor")?.remove();
      if (!byKeyboard || !aim) return;
      const g = st.g;
      const at = aim.atom !== undefined ? g.atoms[aim.atom]
        : g.bonds[aim.bond] ? { x: (g.atoms[g.bonds[aim.bond].a].x + g.atoms[g.bonds[aim.bond].b].x) / 2, y: (g.atoms[g.bonds[aim.bond].a].y + g.atoms[g.bonds[aim.bond].b].y) / 2 } : null;
      if (!at) return;
      const ring = document.createElementNS(NS, "circle");
      ring.setAttribute("class", "cursor");
      ring.setAttribute("cx", at.x);
      ring.setAttribute("cy", at.y);
      ring.setAttribute("r", aim.atom !== undefined ? 14 : 10);
      svg.append(ring);
    }

    function update(message) {
      const info = analyse(st.g);
      svg.innerHTML = drawMarkup(st.g);
      paintCursor();
      paintPreview();
      hideTip();
      const empty = !st.g.atoms.length;
      setText("[data-a=formula]", empty ? "—" : info.html);
      setText("[data-a=exact]", empty ? "—" : info.exact.toFixed(2));
      setText("[data-a=mw]", empty ? "—" : info.mass.toFixed(2));
      refreshLog(info);

      const dirty = JSON.stringify(st.g) !== st.original;
      const tab = tabs.find((t) => t.dataset.mol === st.name);
      if (tab) { if (dirty) tab.dataset.edited = ""; else delete tab.dataset.edited; }
      resetBtn.hidden = !dirty;
      undoBtn.disabled = !st.undo.length;
      cleanBtn.disabled = st.g.atoms.length < 2;
      exportBar.querySelectorAll("[data-export]").forEach((b) => { b.disabled = empty; });
      svg.setAttribute("aria-label", fmt(T.aria, { name: st.title, formula: empty ? "—" : info.text }));
      if (fname) fname.textContent = `${st.name}.cdxml`;

      const badAtom = info.over.indexOf(true);
      if (badAtom >= 0) {
        const a = st.g.atoms[badAtom];
        status.textContent = fmt(T.valence, { sym: a.s, n: info.used[badAtom], v: EL[a.s].v });
        status.dataset.state = "warn";
      } else {
        status.textContent = message || T.hint[tool];
        delete status.dataset.state;
      }

      if (quest && !quest.won && quest.doc === st && quest.solved(st.g, info)) {
        quest.won = true;
        emit("win", { moves: quest.moves });
      }
      emit("change", st.g);
    }

    // The draw-in sequence plays once on load and again on a tab switch or Replay. The first
    // edit ends it, so redrawing the canvas does not restart the animation.
    function play() {
      doc.classList.remove("play");
      void doc.offsetWidth;
      doc.classList.add("play");
    }
    const stopPlay = () => doc.classList.remove("play");

    // Keep the current drawing for undo. Only a chemical edit counts as a move in a challenge;
    // moving atoms and Clean Up leave the structure as it was.
    function keep(counted) {
      st.undo.push({ g: JSON.stringify(st.g), counted });
      if (st.undo.length > 40) st.undo.shift();
      st.redo = [];
    }
    function change(message, mutate, counted = true) {
      stopPlay();
      cancelAnimationFrame(tween);
      keep(counted);
      if (quest && counted) quest.moves++;
      mutate(st.g);
      update(message);
    }

    // ---- tools --------------------------------------------------------------------

    function setTool(next) {
      tool = next;
      doc.dataset.tool = next;
      palette.querySelectorAll("[data-tool]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.tool === next));
      update();
    }

    // What the current tool does at a target. chem.js decides; the preview shows the same plan.
    function act(target, back) {
      const plan = applyTool(st.g, tool, target, back);
      if (!plan) return;
      if (!plan.g) return update(T[plan.say]);
      if (plan.drop) aim = null;
      const say = plan.say === "element" ? fmt(T.element, { sym: plan.sym })
        : plan.say === "setBond" ? fmt(T.setBond, { order: T.order[plan.order - 1] }) : T[plan.say];
      change(say, (d) => { d.atoms = plan.g.atoms; d.bonds = plan.g.bonds; });
    }

    // Under the pointer: the move a click would make, and what the atom or bond is. On a device
    // with a mouse only; a finger has nothing to hover with.
    function paintPreview() {
      svg.querySelector(".preview")?.remove();
      const target = aim || spot;
      const plan = target && !drag && !link && fine.matches ? applyTool(st.g, tool, target) : null;
      doc.toggleAttribute("data-blocked", !!plan && !plan.g);
      if (plan?.g) svg.insertAdjacentHTML("beforeend", previewMarkup(st.g, plan));
    }
    function hideTip() {
      clearTimeout(tipTimer);
      tip.hidden = true;
    }
    function showTip(e) {
      hideTip();
      if (!aim || byKeyboard || !fine.matches) return;
      const box = canvasBox.getBoundingClientRect();
      const x = e.clientX - box.left, y = e.clientY - box.top;
      tipTimer = setTimeout(() => {
        const g = st.g, info = analyse(g);
        if (aim?.atom !== undefined && g.atoms[aim.atom]) {
          const i = aim.atom, s = g.atoms[i].s;
          tip.textContent = fmt(T.tip.atom, { name: T.elements[s], h: info.hyd[i], used: info.used[i], max: EL[s].v });
        } else if (aim?.bond !== undefined && g.bonds[aim.bond]) {
          const b = g.bonds[aim.bond];
          tip.textContent = fmt(T.tip.bond, { pair: `${g.atoms[b.a].s}${"-=≡"[b.o - 1]}${g.atoms[b.b].s}`, order: T.order[b.o - 1] });
        } else return;
        tip.hidden = false;
        // Beside the pointer, or across it when that would run off the canvas
        const left = x + 16 + tip.offsetWidth > box.width ? x - 12 - tip.offsetWidth : x + 16;
        const top = y + 20 + tip.offsetHeight > box.height ? y - 12 - tip.offsetHeight : y + 20;
        tip.style.transform = `translate(${Math.max(4, left)}px, ${Math.max(4, top)}px)`;
      }, 120);
    }

    function toSvg(e) {
      point.x = e.clientX;
      point.y = e.clientY;
      return point.matrixTransform(svg.getScreenCTM().inverse());
    }

    svg.addEventListener("click", (e) => {
      if (swallowClick) { swallowClick = false; return; }
      if (tool === "move") return;
      const atomEl = e.target.closest("[data-atom]"), bondEl = e.target.closest("[data-bond]");
      if (atomEl) act({ atom: +atomEl.dataset.atom }, e.shiftKey);
      else if (bondEl) act({ bond: +bondEl.dataset.bond });
      else act(toSvg(e));
    });

    // Dragging from an atom with the bond tool draws a bond, as in ChemDraw: to another atom it
    // joins them, to empty space it adds a carbon one bond length away at the nearest 30°.
    function linkEnd(p) {
      const g = st.g, from = g.atoms[link.from];
      let join = null, best = 20;
      g.atoms.forEach((a, i) => {
        const d = Math.hypot(a.x - p.x, a.y - p.y);
        if (i !== link.from && d < best) { best = d; join = i; }
      });
      if (join !== null) return { atom: join, x: g.atoms[join].x, y: g.atoms[join].y };
      const L = bondLength(g), turn = Math.round(Math.atan2(p.y - from.y, p.x - from.x) / (Math.PI / 6)) * (Math.PI / 6);
      return { x: from.x + L * Math.cos(turn), y: from.y + L * Math.sin(turn) };
    }
    const dropGhost = () => { ghost?.remove(); ghost = null; };

    svg.addEventListener("pointerdown", (e) => {
      // A drag ends with a click only if its atom is still drawn, so never carry this over.
      swallowClick = false;
      const hit = e.target.closest("[data-atom]");
      if (!hit) return;
      if (tool === "move") {
        drag = { i: +hit.dataset.atom, moved: false };
        svg.setPointerCapture(e.pointerId);
        doc.classList.add("dragging");
        e.preventDefault();
      } else if (tool === "bond") {
        link = { from: +hit.dataset.atom, id: e.pointerId, moved: false };
      }
    });
    // A finger on an atom draws a bond; anywhere else on the canvas it scrolls the page. Browsers
    // ignore touch-action on shapes inside an SVG, so the scroll is stopped here instead.
    svg.addEventListener("touchmove", (e) => { if (link) e.preventDefault(); }, { passive: false });
    svg.addEventListener("pointermove", (e) => {
      if (link && e.pointerId === link.id) {
        const p = toSvg(e), a = st.g.atoms[link.from];
        if (!link.moved) {
          if (Math.hypot(p.x - a.x, p.y - a.y) < 16) return;
          link.moved = true;
          svg.setPointerCapture(e.pointerId);
          ghost = document.createElementNS(NS, "line");
          ghost.setAttribute("class", "ghost");
          ghost.setAttribute("x1", a.x);
          ghost.setAttribute("y1", a.y);
          svg.append(ghost);
        }
        const end = linkEnd(p);
        ghost.setAttribute("x2", end.x);
        ghost.setAttribute("y2", end.y);
        return;
      }
      if (!drag) {
        spot = aim || e.pointerType !== "mouse" ? null : toSvg(e);
        if (!previewQueued) {
          previewQueued = true;
          requestAnimationFrame(() => { previewQueued = false; paintPreview(); });
        }
        return;
      }
      const p = toSvg(e);
      if (!drag.moved) {
        stopPlay();
        keep(false);
        drag.moved = true;
      }
      const atom = st.g.atoms[drag.i];
      atom.x = Math.min(W - 10, Math.max(10, p.x));
      atom.y = Math.min(H - 10, Math.max(10, p.y));
      update();
    });
    function endLink(e) {
      if (!link) return;
      const { from, moved } = link;
      dropGhost();
      if (moved && e.type === "pointerup") {
        swallowClick = true;
        const end = linkEnd(toSvg(e));
        link = null;
        if (end.atom !== undefined) {
          const pair = (b) => (b.a === from && b.b === end.atom) || (b.b === from && b.a === end.atom);
          if (st.g.bonds.some(pair)) update(T.alreadyBonded);
          else change(T.bonded, (d) => { d.bonds.push({ a: from, b: end.atom, o: 1 }); });
        } else if (inside(end, 8)) {
          change(T.grow, (d) => { d.atoms.push({ s: "C", x: end.x, y: end.y }); d.bonds.push({ a: from, b: d.atoms.length - 1, o: 1 }); });
        } else {
          update(T.noRoom);
        }
      }
      link = null;
    }
    const endDrag = (e) => {
      endLink(e);
      if (!drag) return;
      const moved = drag.moved;
      drag = null;
      doc.classList.remove("dragging");
      if (moved) update(T.moved);
    };
    svg.addEventListener("pointerup", endDrag);
    svg.addEventListener("pointercancel", endDrag);

    palette.querySelectorAll("[data-tool]").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));

    function undo() {
      const last = st.undo.pop();
      if (!last) return;
      st.redo.push({ g: JSON.stringify(st.g), counted: last.counted });
      st.g = JSON.parse(last.g);
      if (quest && quest.doc === st && last.counted) quest.moves = Math.max(0, quest.moves - 1);
      aim = null;
      stopPlay();
      update(T.undone);
    }
    function redo() {
      const next = st.redo.pop();
      if (!next) return;
      st.undo.push({ g: JSON.stringify(st.g), counted: next.counted });
      st.g = JSON.parse(next.g);
      if (quest && quest.doc === st && next.counted) quest.moves++;
      aim = null;
      stopPlay();
      update(T.redone);
    }
    undoBtn.addEventListener("click", undo);
    function reset() {
      stopPlay();
      if (quest && quest.doc === st) {
        // Starting a challenge over clears its count, so it clears the way back to it too.
        quest.moves = 0;
        st.undo = [];
        st.redo = [];
      } else {
        keep(false);
      }
      st.g = JSON.parse(st.original);
      aim = null;
      update(T.reset);
    }
    resetBtn.addEventListener("click", reset);

    // Single-letter shortcuts while focus is inside the window, as in ChemDraw's own palette.
    const keys = { v: "move", b: "bond", a: "atom", r: "ring", e: "erase" };
    doc.addEventListener("keydown", (e) => {
      if (e.target.matches("[role=tab]")) return;
      const letter = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && letter === "z") { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && letter === "k") { e.preventDefault(); clean(); return; }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const next = keys[letter];
      if (next) setTool(next);
    });

    // ? lists the keys beside the drawing, without taking the focus or stopping the work.
    const helpBtn = Object.assign(document.createElement("button"), { type: "button" });
    helpBtn.dataset.help = "";
    helpBtn.dataset.tip = `${T.shortcuts.title} (?)`;
    helpBtn.setAttribute("aria-label", T.shortcuts.title);
    helpBtn.setAttribute("aria-expanded", "false");
    helpBtn.innerHTML = '<svg viewBox="0 0 20 20" aria-hidden="true"><text x="6" y="15">?</text></svg>';
    palette.querySelector("[data-undo]").before(helpBtn);
    const keysPanel = Object.assign(document.createElement("div"), { className: "keys-panel", hidden: true });
    keysPanel.setAttribute("role", "region");
    keysPanel.setAttribute("aria-label", T.shortcuts.title);
    keysPanel.innerHTML = `<h3>${T.shortcuts.title}</h3><dl>${T.shortcuts.rows.map(([keys, what]) =>
      `<div><dt>${keys.split(" ").map((k) => `<kbd>${k}</kbd>`).join("")}</dt><dd>${what}</dd></div>`).join("")}</dl>`;
    canvasBox.append(keysPanel);
    function toggleKeys(on = keysPanel.hidden) {
      keysPanel.hidden = !on;
      helpBtn.setAttribute("aria-expanded", on);
    }
    helpBtn.addEventListener("click", () => toggleKeys());
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !keysPanel.hidden) return toggleKeys(false);
      if (e.key !== "?" || e.ctrlKey || e.metaKey || e.altKey || (e.target instanceof Element && e.target.closest("input, textarea, select, [contenteditable]"))) return;
      if (doc.contains(document.activeElement) || doc.matches(":hover")) { e.preventDefault(); toggleKeys(); }
    });

    // ChemDraw's hotkeys: with the pointer or the keyboard cursor on an atom, type an element (L
    // is Cl); on a bond, type 1, 2 or 3 for its order. Delete removes what is under it.
    const ELEMENT_KEYS = { c: "C", n: "N", o: "O", s: "S", f: "F", l: "Cl" };
    svg.addEventListener("pointerover", (e) => {
      if (byKeyboard) return;
      const atomEl = e.target.closest("[data-atom]"), bondEl = e.target.closest("[data-bond]");
      aim = atomEl ? { atom: +atomEl.dataset.atom } : bondEl ? { bond: +bondEl.dataset.bond } : null;
      // The first time the pointer rests on the drawing, say that these keys exist.
      if (aim && !tipped && tool !== "move" && !status.dataset.state) { tipped = true; status.textContent = T.keys; }
      if (aim) spot = null;
      paintPreview();
      showTip(e);
    });
    svg.addEventListener("pointerleave", () => {
      if (!byKeyboard) aim = null;
      spot = null;
      paintPreview();
      hideTip();
    });
    document.addEventListener("keydown", (e) => {
      if (!aim || drag || e.ctrlKey || e.metaKey || e.altKey || (e.target instanceof Element && e.target.closest("input, textarea, select, [contenteditable]"))) return;
      const key = e.key.toLowerCase();
      if (aim.atom !== undefined && aim.atom < st.g.atoms.length) {
        const i = aim.atom, sym = ELEMENT_KEYS[key];
        if (sym && st.g.atoms[i].s !== sym) { e.preventDefault(); change(fmt(T.element, { sym }), (d) => { d.atoms[i].s = sym; }); }
        else if (key === "delete" || key === "backspace") { e.preventDefault(); aim = null; change(T.erased, (d) => remove(d, i)); pickFirst(); }
      } else if (aim.bond !== undefined && aim.bond < st.g.bonds.length) {
        const k = aim.bond, order = { 1: 1, 2: 2, 3: 3 }[key];
        if (order && st.g.bonds[k].o !== order) { e.preventDefault(); change(fmt(T.setBond, { order: T.order[order - 1] }), (d) => { d.bonds[k].o = order; }); }
        else if (key === "delete" || key === "backspace") { e.preventDefault(); aim = null; change(T.erased, (d) => d.bonds.splice(k, 1)); pickFirst(); }
      }
    });

    // The keyboard cursor: focus the canvas, walk between atoms and bonds with the arrow keys,
    // and Enter does what a click would. Shift with an arrow nudges the atom.
    const spots = () => [
      ...st.g.atoms.map((a, i) => ({ to: { atom: i }, x: a.x, y: a.y })),
      ...st.g.bonds.map((b, k) => ({ to: { bond: k }, x: (st.g.atoms[b.a].x + st.g.atoms[b.b].x) / 2, y: (st.g.atoms[b.a].y + st.g.atoms[b.b].y) / 2 })),
    ];
    function announce() {
      paintCursor();
      if (!aim) return;
      if (aim.atom !== undefined) {
        const info = analyse(st.g), i = aim.atom;
        status.textContent = fmt(T.cursorAtom, { sym: st.g.atoms[i].s, n: info.used[i] });
      } else {
        status.textContent = fmt(T.cursorBond, { order: T.order[st.g.bonds[aim.bond].o - 1] });
      }
    }
    function pickFirst() {
      if (!byKeyboard) return;
      aim = st.g.atoms.length ? { atom: 0 } : null;
      announce();
    }
    function walk(dx, dy) {
      const list = spots();
      if (!list.length) return;
      const here = list.find((s) => s.to.atom === aim?.atom && s.to.bond === aim?.bond);
      if (!here) { aim = list[0].to; return announce(); }
      let best = null, score = Infinity;
      list.forEach((s) => {
        if (s === here) return;
        const px = s.x - here.x, py = s.y - here.y, d = Math.hypot(px, py), along = (px * dx + py * dy) / (d || 1);
        if (along < 0.4) return;
        const cost = d * (2 - along);
        if (cost < score) { score = cost; best = s; }
      });
      if (best) { aim = best.to; announce(); }
    }
    svg.tabIndex = 0;
    svg.addEventListener("focus", () => {
      if (!svg.matches(":focus-visible")) return;
      byKeyboard = true;
      pickFirst();
    });
    svg.addEventListener("blur", () => {
      if (!byKeyboard) return;
      byKeyboard = false;
      aim = null;
      paintCursor();
    });
    svg.addEventListener("keydown", (e) => {
      const step = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] }[e.key];
      if (step) {
        e.preventDefault();
        byKeyboard = true;
        if (e.shiftKey && aim?.atom !== undefined) {
          const i = aim.atom;
          change(T.moved, (d) => {
            d.atoms[i].x = Math.min(W - 10, Math.max(10, d.atoms[i].x + step[0] * 6));
            d.atoms[i].y = Math.min(H - 10, Math.max(10, d.atoms[i].y + step[1] * 6));
          }, false);
        } else {
          walk(...step);
        }
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        byKeyboard = true;
        if (!st.g.atoms.length) act({ x: W / 2, y: H / 2 });
        else if (aim?.atom !== undefined) act({ atom: aim.atom }, e.shiftKey);
        else if (aim?.bond !== undefined) act({ bond: aim.bond });
        else return pickFirst();
        if (!aim) pickFirst(); else paintCursor();
      }
    });

    // Clean Up: the atoms glide to their cleaned positions, then the drawing is redrawn once
    // more so labels and double bonds settle on the right side.
    function clean() {
      if (st.g.atoms.length < 2) return;
      const to = cleanUp(st.g, bondLength(JSON.parse(st.original).bonds.length ? JSON.parse(st.original) : st.g));
      const from = st.g.atoms.map((a) => ({ x: a.x, y: a.y }));
      change(T.cleaned, () => {}, false);
      if (!motion.matches) {
        st.g.atoms.forEach((a, i) => { a.x = to[i].x; a.y = to[i].y; });
        return update(T.cleaned);
      }
      const begun = performance.now();
      const step = (now) => {
        const u = Math.min(1, (now - begun) / 420), ease = 1 - (1 - u) ** 3;
        st.g.atoms.forEach((a, i) => { a.x = from[i].x + (to[i].x - from[i].x) * ease; a.y = from[i].y + (to[i].y - from[i].y) * ease; });
        update(T.cleaned);
        if (u < 1) tween = requestAnimationFrame(step);
      };
      tween = requestAnimationFrame(step);
    }
    cleanBtn.addEventListener("click", clean);

    // Export: SMILES to the clipboard, the drawing as a CDXML file, or a link to it in the Lab.
    async function copy(text, done, shown, btn) {
      try {
        await navigator.clipboard.writeText(text);
        flashDone(btn);
        update(done);
      } catch {
        update(shown);
      }
    }
    function saveFile(g, base) {
      const url = URL.createObjectURL(new Blob([toCdxml(g)], { type: "chemical/x-cdxml" }));
      const a = Object.assign(document.createElement("a"), { href: url, download: `${base}.cdxml` });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      return a.download;
    }
    exportBar.querySelector('[data-export="smiles"]').addEventListener("click", (e) => {
      const smiles = toSmiles(st.g);
      if (smiles === null) return update(T.noSmiles);
      copy(smiles, fmt(T.copied, { smiles }), fmt(T.smiles, { smiles }), e.currentTarget);
    });
    exportBar.querySelector('[data-export="cdxml"]').addEventListener("click", () => {
      const dirty = JSON.stringify(st.g) !== st.original;
      update(fmt(T.download, { file: saveFile(st.g, `${st.name}${dirty ? "-edited" : ""}`) }));
      emit("export");
    });
    exportBar.querySelector('[data-export="link"]')?.addEventListener("click", (e) => {
      const code = encodeDrawing(st.g);
      if (!decodeDrawing(code)) return update(T.tooBig);
      const url = `${options.labUrl}#s=${code}`;
      copy(url, T.linkCopied, fmt(T.link, { url }), e.currentTarget);
    });

    // ---- documents ----------------------------------------------------------------

    function open(next, animate) {
      st = stateOf(next);
      drag = null;
      aim = null;
      tabs.forEach((t) => {
        const on = t.dataset.mol === next;
        t.setAttribute("aria-selected", on);
        t.tabIndex = on ? 0 : -1;
      });
      update();
      if (animate && motion.matches) play(); else stopPlay();
    }

    tabs.forEach((t, k) => {
      t.addEventListener("click", () => open(t.dataset.mol, true));
      t.addEventListener("keydown", (e) => {
        const to = { ArrowRight: k + 1, ArrowLeft: k - 1, Home: 0, End: tabs.length - 1 }[e.key];
        if (to === undefined) return;
        e.preventDefault();
        const target = tabs[(to + tabs.length) % tabs.length];
        open(target.dataset.mol, true);
        target.focus();
      });
    });

    if (replayBtn) {
      replayBtn.hidden = !motion.matches;
      replayBtn.addEventListener("click", play);
    }

    // A dot that snaps to the drawing grid under the pointer.
    const snap = canvas.querySelector(".snap");
    if (snap && matchMedia("(pointer: fine)").matches) {
      canvas.addEventListener("pointermove", (e) => {
        if (e.pointerType !== "mouse") return;
        const r = canvas.getBoundingClientRect();
        const x = Math.round((e.clientX - r.left - 7) / 14) * 14 + 7;
        const y = Math.round((e.clientY - r.top - 7) / 14) * 14 + 7;
        snap.style.transform = `translate(${x}px, ${y}px)`;
        snap.hidden = false;
      });
      canvas.addEventListener("pointerleave", () => { snap.hidden = true; });
    }

    doc.classList.add("live");
    palette.hidden = false;
    exportBar.hidden = false;
    st = stateOf("aspirin");
    setTool("bond");

    return {
      open,
      on(kind, fn) { listeners[kind].push(fn); },
      graph: () => st.g,
      play,
      saveFile,
      canvas,
      // A drawing of its own: a blank canvas, a shared structure or a challenge's start.
      show(g, name, title) {
        cancelAnimationFrame(tween);
        st = fresh(name, g, title);
        aim = null;
        update();
        stopPlay();
      },
      // Start again from a table molecule, with the check for this challenge attached.
      restart(mol) {
        const target = stateOf(mol);
        target.undo = [];
        target.redo = [];
        target.g = JSON.parse(target.original);
        open(mol, false);
      },
      // quest: { key, formula, won } on the document now open; null ends it.
      quest(next) {
        quest = next && { moves: 0, won: false, doc: st, solved: (g, info) => graphKey(g) === next.key && !info.over.some(Boolean), ...next };
        update();
        return quest;
      },
      status: update,
    };
  }

  globalThis.ChemEditor = { mount, openStore, solveDaily, burst };

  // ---- the hero -------------------------------------------------------------------

  const hero = document.querySelector(".hero .doc");
  const T = globalThis.ChemWords;
  if (!hero || !T) return;

  const labUrl = new URL("lab/", location.href.split("#")[0]).href;
  const editor = mount(hero, T, { labUrl });
  const strip = hero.querySelector(".challenge");
  const button = hero.querySelector("[data-challenge-open]");
  const store = openStore();
  const today = localDate();
  const c = dailyPick(today);
  const task = T.challenge.tasks[c.id];
  const D = T.daily;
  let quest = null, hinted = false;

  const paintButton = () => {
    if (store.data.daily.streak && store.data.daily.last) button.dataset.count = fmt(D.streak, { n: store.data.daily.streak });
  };
  function paintStrip(result) {
    const won = !!result;
    strip.dataset.state = won ? "won" : "";
    strip.innerHTML = `
      <div class="ch-head"><b>${fmt(D.title, { n: dailyNumber(today) })}</b>
        <button type="button" data-ch="close" aria-label="${T.challenge.close}" title="${T.challenge.close}">×</button></div>
      <p class="ch-task">${won ? `${fmt(T.challenge.done, { moves: result.moves })} ${task.fact}` : task.task}</p>
      <div class="ch-actions">${won
        ? `<button class="btn sm" type="button" data-ch="share">${D.share}</button><a href="${labUrl}">${D.lab}</a>`
        : `<button class="btn sm" type="button" data-ch="hint">${T.challenge.hint}</button>`}</div>
      <p class="ch-hint"${hinted && !won ? "" : " hidden"}>${task.hint}</p>`;
  }
  function start() {
    hinted = false;
    editor.restart(c.mol);
    const target = targetOf(c);
    quest = editor.quest({ key: graphKey(target), formula: analyse(target).html });
    strip.hidden = false;
    button.setAttribute("aria-expanded", "true");
    paintStrip(null);
  }
  function stop() {
    quest = null;
    editor.quest(null);
    strip.hidden = true;
    button.setAttribute("aria-expanded", "false");
    button.focus();
  }

  editor.on("win", ({ moves }) => {
    const got = solveDaily(store.data, c, today, moves, hinted);
    store.data.badges = earned(store.data);
    store.save();
    paintButton();
    paintStrip({ moves, stars: got });
    quest.result = { stars: got, moves };
    burst(editor.canvas);
  });
  editor.on("export", () => {
    store.data.exported = true;
    store.data.badges = earned(store.data);
    store.save();
  });

  button.addEventListener("click", () => (quest ? stop() : start()));
  strip.addEventListener("click", async (e) => {
    const act = e.target.closest("[data-ch]");
    if (!act) return;
    if (act.dataset.ch === "close") stop();
    else if (act.dataset.ch === "hint") { hinted = true; paintStrip(null); }
    else if (act.dataset.ch === "share") {
      const text = dailyShare(D, today, quest.result.stars, quest.result.moves, labUrl);
      try { await navigator.clipboard.writeText(text); editor.status(D.shared); } catch { editor.status(fmt(D.shareText, { text })); }
    }
  });

  // A streak is only live while the last solved day is today or yesterday.
  const probe = nextStreak(store.data.daily, today);
  const days = probe.streak > 1 || store.data.daily.last === today ? store.data.daily.streak : 0;
  const line = document.querySelector("[data-daily]");
  if (line) line.textContent = fmt(days ? D.lineStreak : D.line, { n: dailyNumber(today), mol: T.names[c.mol], days });

  button.hidden = false;
  if (days) paintButton();
  hero.querySelector("[data-mol]").closest("[role=tablist]").hidden = false;
  hero.querySelector(".fname").hidden = true;
  editor.open("aspirin", false);
  editor.play();
})();
