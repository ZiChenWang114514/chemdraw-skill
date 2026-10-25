// The structure editor in the hero window: five small molecules you can bond, rename,
// grow, move and erase, with the Analysis caption and the agent's readback line
// recomputed from what is on the canvas.
//
// MOLS was laid out with RDKit and kept as plain coordinates; docs/website.md says how to
// regenerate it. All words come from the page (#i18n), so one script serves both languages.
// The page reads completely without this file.

(() => {
  const MOLS = {
    "aspirin": {"smiles":"CC(=O)Oc1ccccc1C(=O)O","formula":"C9H8O4","atoms":[["C",40.0,123.7],["C",88.4,151.8],["O",88.4,207.8],["O",137.0,123.8],["C",185.4,152.0],["C",185.3,208.0],["C",233.8,236.1],["C",282.3,208.2],["C",282.4,152.2],["C",234.0,124.1],["C",234.1,68.1],["O",185.6,40.1],["O",282.6,40.1]],"bonds":[[0,1,1],[1,2,2],[1,3,1],[3,4,1],[4,5,2],[5,6,1],[6,7,2],[7,8,1],[8,9,2],[9,10,1],[10,11,2],[10,12,1],[9,4,1]]},
    "paracetamol": {"smiles":"CC(=O)Nc1ccc(O)cc1","formula":"C8H9NO2","atoms":[["C",48.0,137.7],["C",87.6,127.1],["O",98.2,87.5],["N",116.6,156.1],["C",156.2,145.5],["C",185.2,174.5],["C",224.8,163.9],["C",235.4,124.3],["O",275.0,113.7],["C",206.4,95.3],["C",166.8,105.9]],"bonds":[[0,1,1],[1,2,2],[1,3,1],[3,4,1],[4,5,1],[5,6,2],[6,7,1],[7,8,1],[7,9,2],[9,10,1],[10,4,2]]},
    "caffeine": {"smiles":"Cn1c(=O)c2c(ncn2C)n(C)c1=O","formula":"C8H10N4O2","atoms":[["C",66.7,168.0],["N",92.6,135.7],["C",81.7,95.8],["N",116.3,73.2],["C",148.5,99.0],["C",133.9,137.7],["C",160.1,169.7],["O",145.4,208.3],["N",200.8,163.0],["C",227.0,195.0],["C",215.5,124.3],["O",256.3,117.7],["N",189.3,92.3],["C",203.9,53.7]],"bonds":[[0,1,1],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[5,6,1],[6,7,2],[6,8,1],[8,9,1],[8,10,1],[10,11,2],[10,12,1],[12,13,1],[5,1,1],[12,4,1]]},
    "ibuprofen": {"smiles":"CC(C)Cc1ccc(C(C)C(=O)O)cc1","formula":"C13H18O2","atoms":[["C",48.0,125.4],["C",80.4,123.4],["C",94.9,94.3],["C",98.4,150.5],["C",130.8,148.5],["C",148.7,175.6],["C",181.2,173.6],["C",195.7,144.5],["C",177.7,117.5],["C",145.3,119.4],["C",228.1,142.6],["C",246.0,169.6],["C",242.6,113.5],["O",224.6,86.4],["O",275.0,111.5]],"bonds":[[0,1,1],[1,2,1],[1,3,1],[3,4,1],[4,5,1],[5,6,2],[6,7,1],[7,8,2],[8,9,1],[7,10,1],[10,11,1],[10,12,1],[12,13,2],[12,14,1],[9,4,2]]},
    "vanillin": {"smiles":"COc1cc(C=O)ccc1O","formula":"C8H8O3","atoms":[["C",268.3,159.1],["O",230.5,175.9],["C",197.1,151.6],["C",159.3,168.3],["C",125.9,144.0],["C",88.1,160.8],["O",54.7,136.5],["C",130.3,102.9],["C",168.0,86.1],["C",201.5,110.5],["O",239.2,93.7]],"bonds":[[0,1,1],[1,2,1],[2,3,1],[3,4,2],[4,5,1],[5,6,2],[4,7,1],[7,8,2],[8,9,1],[9,10,1],[9,2,2]]},
  };

  const W = 323, H = 262;
  const EL = {
    C: { v: 4, mass: 12.011, exact: 12, w: 13.7 },
    N: { v: 3, mass: 14.007, exact: 14.003074, w: 13.7 },
    O: { v: 2, mass: 15.999, exact: 15.9949146, w: 14.8 },
    S: { v: 2, mass: 32.06, exact: 31.9720707, w: 12.7 },
    F: { v: 1, mass: 18.998, exact: 18.9984032, w: 11.6 },
    Cl: { v: 1, mass: 35.45, exact: 34.9688527, w: 17.9 },
    Br: { v: 1, mass: 79.904, exact: 78.9183376, w: 19.3 },
  };
  const HYDROGEN = { mass: 1.008, exact: 1.00782503 };
  const CYCLE = ["C", "N", "O", "S", "F", "Cl", "Br"];

  const fmt = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => o[k]);
  const f1 = (n) => n.toFixed(1);

  function load(name) {
    const m = MOLS[name];
    return {
      atoms: m.atoms.map(([s, x, y]) => ({ s, x, y })),
      bonds: m.bonds.map(([a, b, o]) => ({ a, b, o })),
    };
  }

  // Bond orders per atom, implicit hydrogens, the Hill formula, masses and any atom over its valence.
  function analyse(g) {
    const used = g.atoms.map(() => 0);
    g.bonds.forEach((b) => { used[b.a] += b.o; used[b.b] += b.o; });
    const hyd = g.atoms.map((a, i) => Math.max(0, EL[a.s].v - used[i]));
    const over = g.atoms.map((a, i) => used[i] > EL[a.s].v);
    const count = {};
    let mass = 0, exact = 0;
    g.atoms.forEach((a, i) => {
      count[a.s] = (count[a.s] || 0) + 1;
      count.H = (count.H || 0) + hyd[i];
      mass += EL[a.s].mass + hyd[i] * HYDROGEN.mass;
      exact += EL[a.s].exact + hyd[i] * HYDROGEN.exact;
    });
    const symbols = Object.keys(count).filter((s) => count[s] > 0);
    const rest = symbols.filter((s) => s !== "C" && s !== "H").sort();
    const order = count.C ? ["C", "H", ...rest] : symbols.sort();
    const parts = order.filter((s) => count[s] > 0).map((s) => [s, count[s]]);
    return {
      used, hyd, over, mass, exact,
      text: parts.map(([s, n]) => s + (n > 1 ? n : "")).join(""),
      html: parts.map(([s, n]) => s + (n > 1 ? `<sub>${n}</sub>` : "")).join(""),
    };
  }

  if (typeof module !== "undefined") module.exports = { MOLS, analyse, load };

  const doc = typeof document !== "undefined" && document.querySelector(".doc");
  const svg = doc && doc.querySelector(".mol");
  const i18n = doc && document.getElementById("i18n");
  if (!svg || !i18n) return;
  const T = JSON.parse(i18n.textContent);

  const canvas = doc.querySelector(".doc-canvas");
  const palette = doc.querySelector(".palette");
  const tabs = [...doc.querySelectorAll("[data-mol]")];
  const status = doc.querySelector(".status");
  const undoBtn = doc.querySelector("[data-undo]");
  const resetBtn = doc.querySelector(".reset");
  const replayBtn = doc.querySelector(".replay");
  const motion = matchMedia("(prefers-reduced-motion: no-preference)");
  const point = svg.createSVGPoint();

  const states = {};
  let name = tabs[0].dataset.mol;
  let tool = "bond";
  let st;
  let drag = null;

  const stateOf = (n) => {
    if (!states[n]) {
      const g = load(n);
      states[n] = { name: n, g, original: JSON.stringify(g), undo: [] };
    }
    return states[n];
  };

  // ---- geometry -------------------------------------------------------------------

  const bondLength = (g) => {
    if (!g.bonds.length) return 52;
    const sum = g.bonds.reduce((t, b) => t + Math.hypot(g.atoms[b.a].x - g.atoms[b.b].x, g.atoms[b.a].y - g.atoms[b.b].y), 0);
    return sum / g.bonds.length;
  };
  const neighbours = (g) => {
    const n = g.atoms.map(() => []);
    g.bonds.forEach((b) => { n[b.a].push(b.b); n[b.b].push(b.a); });
    return n;
  };
  const inside = (p, pad = 12) => p.x >= pad && p.x <= W - pad && p.y >= pad && p.y <= H - pad;

  // The direction a new bond from atom i should take: the middle of the widest gap between
  // its bonds, or, for a chain end, a zig-zag turn away from the rest of the molecule.
  function freeAngle(g, i) {
    const a = g.atoms[i];
    const around = neighbours(g)[i].map((j) => Math.atan2(g.atoms[j].y - a.y, g.atoms[j].x - a.x)).sort((p, q) => p - q);
    if (!around.length) return -Math.PI / 6;
    if (around.length === 1) {
      const cx = g.atoms.reduce((t, p) => t + p.x, 0) / g.atoms.length;
      const cy = g.atoms.reduce((t, p) => t + p.y, 0) / g.atoms.length;
      const turns = [around[0] + (2 * Math.PI) / 3, around[0] - (2 * Math.PI) / 3];
      const far = (t) => Math.hypot(a.x + Math.cos(t) - cx, a.y + Math.sin(t) - cy);
      return far(turns[0]) >= far(turns[1]) ? turns[0] : turns[1];
    }
    let best = 0, from = around[0];
    around.forEach((t, k) => {
      const next = k + 1 < around.length ? around[k + 1] : around[0] + 2 * Math.PI;
      if (next - t > best) { best = next - t; from = t; }
    });
    return from + best / 2;
  }

  // Try the preferred direction first, then swing either side until the new atoms fit the canvas.
  function place(g, i, build) {
    const base = freeAngle(g, i);
    for (const k of [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6]) {
      const atoms = build(base + (k * Math.PI) / 12);
      if (atoms.every((p) => inside(p))) return atoms;
    }
    return null;
  }

  // ---- drawing --------------------------------------------------------------------

  const trim = (atom) => Math.max(9.5, EL[atom.s].w / 2 + 3);

  // The side of a double bond its second line goes on: toward the other bonds when they all lie
  // on one side (a ring), centred otherwise.
  function doubleSide(g, nb, b, ux, uy) {
    const nx = -uy, ny = ux;
    let pos = 0, neg = 0;
    [[b.a, b.b], [b.b, b.a]].forEach(([from, skip]) => {
      nb[from].forEach((j) => {
        if (j === skip) return;
        const d = (g.atoms[j].x - g.atoms[from].x) * nx + (g.atoms[j].y - g.atoms[from].y) * ny;
        if (d > 1) pos++; else if (d < -1) neg++;
      });
    });
    return pos && !neg ? 1 : neg && !pos ? -1 : 0;
  }

  function bondPath(g, nb, labelled, b) {
    const A = g.atoms[b.a], B = g.atoms[b.b];
    const len = Math.hypot(B.x - A.x, B.y - A.y) || 1;
    const ux = (B.x - A.x) / len, uy = (B.y - A.y) / len, nx = -uy, ny = ux;
    const ta = labelled[b.a] ? trim(A) : 0, tb = labelled[b.b] ? trim(B) : 0;
    const line = (off, ea = 0, eb = 0) => {
      const s = Math.max(ta, ea), e = len - Math.max(tb, eb);
      if (e - s < 2) return "";
      return `M${f1(A.x + ux * s + nx * off)} ${f1(A.y + uy * s + ny * off)}L${f1(A.x + ux * e + nx * off)} ${f1(A.y + uy * e + ny * off)}`;
    };
    if (b.o === 1) return line(0);
    if (b.o === 3) return line(0) + line(5) + line(-5);
    const side = doubleSide(g, nb, b, ux, uy);
    return side ? line(0) + line(side * 8, 9, 9) : line(4) + line(-4);
  }

  function label(g, nb, info, i, delay) {
    const a = g.atoms[i];
    const y = a.y + 6.8;
    const bad = info.over[i] ? " over" : "";
    let out = `<text class="a el-${a.s}${bad}" style="--i:${delay}" x="${f1(a.x)}" y="${f1(y)}" text-anchor="middle">${a.s}</text>`;
    const h = info.hyd[i];
    if (h > 0) {
      // Put the hydrogens on the side away from the bonds, as ChemDraw does: OH, but H2N.
      const lean = nb[i].reduce((t, j) => t + Math.sign(g.atoms[j].x - a.x), 0);
      const left = lean > 0;
      const x = left ? a.x - EL[a.s].w / 2 - 0.5 : a.x + EL[a.s].w / 2 + 0.5;
      out += `<text class="a el-${a.s}${bad}" style="--i:${delay}" x="${f1(x)}" y="${f1(y)}" text-anchor="${left ? "end" : "start"}">H${h > 1 ? `<tspan dy="4" font-size="13">${h}</tspan>` : ""}</text>`;
    }
    return out;
  }

  // ChemDraw's selection box: dashed outline with eight handles around what is drawn.
  function selection(g) {
    if (!g.atoms.length) return "";
    const xs = g.atoms.map((p) => p.x), ys = g.atoms.map((p) => p.y);
    const x0 = Math.max(4, Math.min(...xs) - 16), x1 = Math.min(W - 4, Math.max(...xs) + 16);
    const y0 = Math.max(4, Math.min(...ys) - 16), y1 = Math.min(H - 4, Math.max(...ys) + 16);
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
    const handles = [[x0, y0], [mx, y0], [x1, y0], [x0, my], [x1, my], [x0, y1], [mx, y1], [x1, y1]]
      .map(([x, y]) => `<rect class="handle" x="${f1(x - 4)}" y="${f1(y - 4)}" width="8" height="8"/>`).join("");
    return `<g class="selg" aria-hidden="true"><rect class="sel" x="${f1(x0)}" y="${f1(y0)}" width="${f1(x1 - x0)}" height="${f1(y1 - y0)}"/>${handles}</g>`;
  }

  function draw(g, info) {
    const nb = neighbours(g);
    const labelled = g.atoms.map((a, i) => a.s !== "C" || !nb[i].length);
    const spread = (k) => Math.round((k * 12) / Math.max(g.bonds.length - 1, 12));
    const first = g.atoms.map(() => null);
    g.bonds.forEach((b, k) => { [b.a, b.b].forEach((i) => { if (first[i] === null || spread(k) < first[i]) first[i] = spread(k); }); });

    const bonds = g.bonds.map((b, k) => `<path class="b" style="--i:${spread(k)}" d="${bondPath(g, nb, labelled, b)}"/>`).join("");
    const labels = g.atoms.map((a, i) => (labelled[i] ? label(g, nb, info, i, first[i] || 0) : "")).join("");
    const flags = g.atoms.map((a, i) => (info.over[i] ? `<circle class="warn" cx="${f1(a.x)}" cy="${f1(a.y)}" r="12"/>` : "")).join("");
    const hitBonds = g.bonds.map((b, k) => `<path data-bond="${k}" d="M${f1(g.atoms[b.a].x)} ${f1(g.atoms[b.a].y)}L${f1(g.atoms[b.b].x)} ${f1(g.atoms[b.b].y)}"/>`).join("");
    const hitAtoms = g.atoms.map((a, i) => `<circle data-atom="${i}" cx="${f1(a.x)}" cy="${f1(a.y)}" r="13"/>`).join("");
    svg.innerHTML = bonds + labels + flags + selection(g) + `<g class="hit">${hitBonds}${hitAtoms}</g>`;
  }

  // ---- page updates ---------------------------------------------------------------

  const setText = (sel, html) => { const el = doc.querySelector(sel); if (el) el.innerHTML = html; };

  function describe() {
    const info = analyse(st.g);
    const original = analyse(JSON.parse(st.original));
    return { info, original };
  }

  function refreshLog(info, original) {
    const display = T.names[st.name];
    setText("[data-log=ask]", fmt(T.ask, { name: display }));
    setText("[data-log=resolve]", `${st.name} → ${MOLS[st.name].smiles}`);
    setText("[data-log=build]", fmt(T.build, { name: st.name }));
    if (!st.g.atoms.length) {
      setText("[data-log=readback]", `${T.empty} <span class="no">✗</span>`);
    } else if (info.text === original.text) {
      setText("[data-log=readback]", `${info.html} ${T.matches} <span class="ok">✓</span>`);
    } else {
      setText("[data-log=readback]", `${info.html} ${fmt(T.differs, { input: original.html })} <span class="no">✗</span>`);
    }
  }

  function update(message) {
    const { info, original } = describe();
    draw(st.g, info);
    const empty = !st.g.atoms.length;
    setText("[data-a=formula]", empty ? "—" : info.html);
    setText("[data-a=exact]", empty ? "—" : info.exact.toFixed(2));
    setText("[data-a=mw]", empty ? "—" : info.mass.toFixed(2));
    refreshLog(info, original);

    const dirty = JSON.stringify(st.g) !== st.original;
    const tab = tabs.find((t) => t.dataset.mol === st.name);
    if (dirty) tab.dataset.edited = ""; else delete tab.dataset.edited;
    resetBtn.hidden = !dirty;
    undoBtn.disabled = !st.undo.length;
    svg.setAttribute("aria-label", fmt(T.aria, { name: T.names[st.name], formula: empty ? "—" : info.text }));

    const badAtom = info.over.indexOf(true);
    if (badAtom >= 0) {
      const a = st.g.atoms[badAtom];
      status.textContent = fmt(T.valence, { sym: a.s, n: info.used[badAtom], v: EL[a.s].v });
      status.dataset.state = "warn";
    } else {
      status.textContent = message || T.hint[tool];
      delete status.dataset.state;
    }
  }

  // The draw-in sequence plays once on load and again on a tab switch or Replay. The first
  // edit ends it, so redrawing the canvas does not restart the animation.
  function play() {
    doc.classList.remove("play");
    void doc.offsetWidth;
    doc.classList.add("play");
  }
  const stopPlay = () => doc.classList.remove("play");

  function change(message, mutate) {
    stopPlay();
    st.undo.push(JSON.stringify(st.g));
    if (st.undo.length > 40) st.undo.shift();
    mutate(st.g);
    update(message);
  }

  // ---- tools ----------------------------------------------------------------------

  function setTool(next) {
    tool = next;
    doc.dataset.tool = next;
    palette.querySelectorAll("[data-tool]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.tool === next));
    update();
  }

  function remove(g, atom) {
    g.atoms.splice(atom, 1);
    g.bonds = g.bonds.filter((b) => b.a !== atom && b.b !== atom).map((b) => ({
      a: b.a > atom ? b.a - 1 : b.a, b: b.b > atom ? b.b - 1 : b.b, o: b.o,
    }));
  }

  function onClick(e) {
    if (tool === "move") return;
    const atomEl = e.target.closest("[data-atom]");
    const bondEl = e.target.closest("[data-bond]");
    const g = st.g;
    if (atomEl) {
      const i = +atomEl.dataset.atom;
      if (tool === "bond") {
        const L = bondLength(g);
        const spot = place(g, i, (t) => [{ x: g.atoms[i].x + L * Math.cos(t), y: g.atoms[i].y + L * Math.sin(t) }]);
        if (!spot) return update(T.noRoom);
        change(T.grow, (d) => { d.atoms.push({ s: "C", x: spot[0].x, y: spot[0].y }); d.bonds.push({ a: i, b: d.atoms.length - 1, o: 1 }); });
      } else if (tool === "atom") {
        const at = CYCLE.indexOf(g.atoms[i].s);
        const next = CYCLE[(at + (e.shiftKey ? CYCLE.length - 1 : 1)) % CYCLE.length];
        change(fmt(T.element, { sym: next }), (d) => { d.atoms[i].s = next; });
      } else if (tool === "ring") {
        const L = bondLength(g);
        const spot = place(g, i, (t) => {
          const centre = { x: g.atoms[i].x + 2 * L * Math.cos(t), y: g.atoms[i].y + 2 * L * Math.sin(t) };
          return Array.from({ length: 6 }, (_, k) => ({ x: centre.x + L * Math.cos(t + Math.PI + (k * Math.PI) / 3), y: centre.y + L * Math.sin(t + Math.PI + (k * Math.PI) / 3) }));
        });
        if (!spot) return update(T.noRoom);
        change(T.ring, (d) => {
          const base = d.atoms.length;
          spot.forEach((p) => d.atoms.push({ s: "C", x: p.x, y: p.y }));
          d.bonds.push({ a: i, b: base, o: 1 });
          for (let k = 0; k < 6; k++) d.bonds.push({ a: base + k, b: base + ((k + 1) % 6), o: k % 2 ? 1 : 2 });
        });
      } else if (tool === "erase") {
        change(T.erased, (d) => remove(d, i));
      }
    } else if (bondEl) {
      const k = +bondEl.dataset.bond;
      if (tool === "bond") {
        const order = (g.bonds[k].o % 3) + 1;
        change(fmt(T.setBond, { order: T.order[order - 1] }), (d) => { d.bonds[k].o = order; });
      } else if (tool === "erase") {
        change(T.erased, (d) => d.bonds.splice(k, 1));
      }
    }
  }

  function toSvg(e) {
    point.x = e.clientX;
    point.y = e.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  }

  svg.addEventListener("click", onClick);
  svg.addEventListener("pointerdown", (e) => {
    if (tool !== "move") return;
    const hit = e.target.closest("[data-atom]");
    if (!hit) return;
    drag = { i: +hit.dataset.atom, moved: false };
    svg.setPointerCapture(e.pointerId);
    doc.classList.add("dragging");
    e.preventDefault();
  });
  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const p = toSvg(e);
    if (!drag.moved) {
      stopPlay();
      st.undo.push(JSON.stringify(st.g));
      drag.moved = true;
    }
    const atom = st.g.atoms[drag.i];
    atom.x = Math.min(W - 10, Math.max(10, p.x));
    atom.y = Math.min(H - 10, Math.max(10, p.y));
    update();
  });
  const endDrag = () => {
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
    if (!st.undo.length) return;
    st.g = JSON.parse(st.undo.pop());
    stopPlay();
    update(T.undone);
  }
  undoBtn.addEventListener("click", undo);
  resetBtn.addEventListener("click", () => {
    stopPlay();
    st.undo.push(JSON.stringify(st.g));
    st.g = JSON.parse(st.original);
    update(T.reset);
  });

  // Single-letter shortcuts while focus is inside the window, as in ChemDraw's own palette.
  const keys = { v: "move", b: "bond", a: "atom", r: "ring", e: "erase" };
  doc.addEventListener("keydown", (e) => {
    if (e.target.matches("[role=tab]")) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); undo(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const next = keys[e.key.toLowerCase()];
    if (next) setTool(next);
  });

  // ---- documents ------------------------------------------------------------------

  function open(next, animate) {
    name = next;
    st = stateOf(next);
    drag = null;
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
  tabs[0].closest("[role=tablist]").hidden = false;
  doc.querySelector(".fname").hidden = true;
  open(name, false);
  setTool("bond");
  play();
})();
