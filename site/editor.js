// The structure editor in the hero window: five small molecules you can bond, rename,
// grow, move, erase and clean up, with the Analysis caption and the agent's readback line
// recomputed from what is on the canvas. What is drawn can be copied as SMILES or saved as
// an ACS Document 1996 CDXML file that opens in ChemDraw.
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

  // ---- export ---------------------------------------------------------------------

  // SMILES of what is drawn, in Kekule form: a depth-first walk writes branches in brackets
  // and closes a ring where it meets an atom it has already seen. Fragments are joined by ".".
  // null when an atom is over its valence, because SMILES would quietly give it a new one.
  function toSmiles(g) {
    if (analyse(g).over.some(Boolean)) return null;
    const adj = g.atoms.map(() => []);
    g.bonds.forEach((b, k) => { adj[b.a].push([b.b, k]); adj[b.b].push([b.a, k]); });
    const seen = g.atoms.map(() => false), tree = new Set(), rings = new Set();
    const walk = (i, from) => {
      seen[i] = true;
      adj[i].forEach(([j, k]) => {
        if (k === from || tree.has(k)) return;
        if (seen[j]) rings.add(k); else { tree.add(k); walk(j, k); }
      });
    };
    const mark = { 1: "", 2: "=", 3: "#" };
    const digit = (d) => (d < 10 ? String(d) : "%" + d);
    const open = new Map(), free = [], written = g.atoms.map(() => false);
    let next = 1;
    const write = (i) => {
      written[i] = true;
      let out = g.atoms[i].s;
      const closed = [];
      adj[i].forEach(([, k]) => {
        if (!rings.has(k)) return;
        if (open.has(k)) { out += digit(open.get(k)); closed.push(open.get(k)); open.delete(k); return; }
        free.sort((p, q) => p - q);
        const d = free.length ? free.shift() : next++;
        open.set(k, d);
        out += mark[g.bonds[k].o] + digit(d);
      });
      free.push(...closed);
      const kids = adj[i].filter(([j, k]) => tree.has(k) && !written[j]);
      kids.forEach(([j, k], n) => {
        const branch = mark[g.bonds[k].o] + write(j);
        out += n < kids.length - 1 ? `(${branch})` : branch;
      });
      return out;
    };
    const parts = [];
    g.atoms.forEach((_, i) => {
      if (seen[i]) return;
      walk(i, -1);
      parts.push(write(i));
    });
    return parts.join(".");
  }

  // An ACS Document 1996 CDXML file of the drawing, written the way cdxml_builder writes one:
  // 14.4 pt bonds, Arial 10 pt bold labels, heteroatoms with their hydrogens, and NeedsClean so
  // ChemDraw lays the labels out itself when it opens the file.
  const NUMBER = { C: 6, N: 7, O: 8, S: 16, F: 9, Cl: 17, Br: 35 };
  function toCdxml(g) {
    const info = analyse(g);
    const scale = 14.4 / bondLength(g);
    const xs = g.atoms.map((a) => a.x), ys = g.atoms.map((a) => a.y);
    const x0 = Math.min(...xs, 0), y0 = Math.min(...ys, 0);
    const at = (a) => [72 + (a.x - x0) * scale, 72 + (a.y - y0) * scale];
    const f2 = (n) => n.toFixed(2);
    const nodes = g.atoms.map((a, i) => {
      const [x, y] = at(a);
      const head = `<n id="${100 + i}" p="${f2(x)} ${f2(y)}"`;
      if (a.s === "C" && g.bonds.some((b) => b.a === i || b.b === i)) return `${head}/>`;
      const h = info.hyd[i];
      const text = a.s + (h ? "H" + (h > 1 ? h : "") : "");
      const element = a.s === "C" ? "" : ` Element="${NUMBER[a.s]}"`;
      return `${head}${element} NumHydrogens="${h}" NeedsClean="yes" AS="N"><t p="${f2(x - 3.25)} ${f2(y + 3.52)}" LabelJustification="Left"><s font="3" size="10" color="0" face="96">${text}</s></t></n>`;
    });
    const bonds = g.bonds.map((b, k) => `<b id="${1000 + k}" B="${100 + b.a}" E="${100 + b.b}"${b.o > 1 ? ` Order="${b.o}"` : ""}/>`);
    return [
      '<?xml version="1.0" encoding="UTF-8" ?>',
      '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >',
      '<CDXML CreationProgram="ChemDraw Skill website" BondLength="14.40" ChainAngle="120" LineWidth="0.60" BoldWidth="2" HashSpacing="2.50"' +
        ' MarginWidth="1.60" BondSpacing="18" LabelFont="3" LabelSize="10" LabelFace="96" CaptionFont="3" CaptionSize="10" CaptionFace="0"' +
        ' LabelJustification="Auto" CaptionJustification="Left" InterpretChemically="yes" color="0" bgcolor="1">',
      '<colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/></colortable>',
      '<fonttable><font id="3" charset="iso-8859-1" name="Arial"/></fonttable>',
      '<page id="1" HeightPages="1" WidthPages="1">',
      '<fragment id="2">', ...nodes, ...bonds, "</fragment>",
      "</page>",
      "</CDXML>",
      "",
    ].join("\n");
  }

  // ---- clean up -------------------------------------------------------------------

  // Clean Up Structure, as in ChemDraw's Structure menu. Every bond is pulled to length L and
  // every pair of atoms two bonds apart to the distance their angle should give (108° inside a
  // five-membered ring, 120° otherwise), and atoms that are not bonded keep their distance.
  // Returns new coordinates, centred on the canvas; the drawing itself is left alone.
  function cleanUp(g, L) {
    const p = g.atoms.map((a) => ({ x: a.x, y: a.y }));
    const nb = neighbours(g);
    const ringSize = (from, to, via) => {
      // The shortest path from one neighbour of `via` to another without passing through it, plus two.
      const depth = new Map([[from, 0]]), queue = [from];
      while (queue.length) {
        const i = queue.shift();
        if (i === to) return depth.get(i) + 2;
        if (depth.get(i) >= 5) continue;
        nb[i].forEach((j) => { if (j !== via && !depth.has(j)) { depth.set(j, depth.get(i) + 1); queue.push(j); } });
      }
      return 0;
    };
    const springs = g.bonds.map((b) => [b.a, b.b, L, 1]);
    const near = new Set(g.bonds.flatMap((b) => [b.a + "," + b.b, b.b + "," + b.a]));
    nb.forEach((list, j) => {
      list.forEach((i, m) => list.slice(m + 1).forEach((k) => {
        const size = ringSize(i, k, j);
        const angle = size >= 3 && size <= 5 ? Math.PI - (2 * Math.PI) / size : (2 * Math.PI) / 3;
        springs.push([i, k, 2 * L * Math.sin(angle / 2), 0.5]);
        near.add(i + "," + k).add(k + "," + i);
      }));
    });
    for (let round = 0; round < 400; round++) {
      springs.forEach(([i, k, length, stiff]) => {
        const dx = p[k].x - p[i].x, dy = p[k].y - p[i].y, d = Math.hypot(dx, dy) || 0.01;
        const push = ((d - length) / d) * 0.5 * stiff;
        p[i].x += dx * push; p[i].y += dy * push; p[k].x -= dx * push; p[k].y -= dy * push;
      });
      for (let i = 0; i < p.length; i++) {
        for (let k = i + 1; k < p.length; k++) {
          if (near.has(i + "," + k)) continue;
          const dx = p[k].x - p[i].x, dy = p[k].y - p[i].y, d = Math.hypot(dx, dy) || 0.01;
          if (d >= 1.5 * L) continue;
          const push = ((d - 1.5 * L) / d) * 0.1;
          p[i].x += dx * push; p[i].y += dy * push; p[k].x -= dx * push; p[k].y -= dy * push;
        }
      }
    }
    if (!p.length) return p;
    const xs = p.map((q) => q.x), ys = p.map((q) => q.y);
    const shrink = Math.min(1, (W - 40) / (Math.max(...xs) - Math.min(...xs) || 1), (H - 40) / (Math.max(...ys) - Math.min(...ys) || 1));
    const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
    return p.map((q) => ({ x: W / 2 + (q.x - cx) * shrink, y: H / 2 + (q.y - cy) * shrink }));
  }

  // ---- challenges -----------------------------------------------------------------

  function remove(g, atom) {
    g.atoms.splice(atom, 1);
    g.bonds = g.bonds.filter((b) => b.a !== atom && b.b !== atom).map((b) => ({
      a: b.a > atom ? b.a - 1 : b.a, b: b.b > atom ? b.b - 1 : b.b, o: b.o,
    }));
  }

  // Small edits that turn one of the five molecules into a named relative. Each target is
  // defined by the moves that reach it (tests/test_site.py checks the result against the
  // compound's published SMILES); the visitor may reach it any way they like.
  const CHALLENGES = [
    { id: "salicylic", mol: "aspirin", solve: [["erase", 0], ["erase", 0], ["erase", 0]] },
    { id: "aminophenol", mol: "paracetamol", solve: [["erase", 0], ["erase", 0], ["erase", 0]] },
    { id: "vanillic", mol: "vanillin", solve: [["grow", 5], ["element", 11, "O"]] },
    { id: "theophylline", mol: "caffeine", solve: [["erase", 0]] },
    { id: "ibuprofenMethyl", mol: "ibuprofen", solve: [["grow", 14]] },
    { id: "wintergreen", mol: "aspirin", solve: [["erase", 0], ["erase", 0], ["erase", 0], ["grow", 9]] },
  ];

  function applyMoves(g, moves) {
    moves.forEach(([move, i, value]) => {
      if (move === "erase") remove(g, i);
      else if (move === "element") g.atoms[i].s = value;
      else if (move === "grow") { g.atoms.push({ s: "C", x: g.atoms[i].x + 30, y: g.atoms[i].y }); g.bonds.push({ a: i, b: g.atoms.length - 1, o: 1 }); }
    });
    return g;
  }

  // A fingerprint of the structure that ignores where atoms sit and which Kekule form a ring is
  // drawn in: each atom starts from its element, hydrogens and degree, and five rounds fold in
  // its neighbours, with ring bonds marked as ring bonds rather than single or double.
  function graphKey(g) {
    const info = analyse(g);
    const adj = g.atoms.map(() => []);
    g.bonds.forEach((b, k) => {
      const seen = new Set([b.a]), queue = [b.a];
      while (queue.length) {
        const i = queue.shift();
        g.bonds.forEach((c, m) => {
          if (m === k) return;
          const j = c.a === i ? c.b : c.b === i ? c.a : -1;
          if (j >= 0 && !seen.has(j)) { seen.add(j); queue.push(j); }
        });
      }
      const tag = seen.has(b.b) ? "r" : String(b.o);
      adj[b.a].push([b.b, tag]);
      adj[b.b].push([b.a, tag]);
    });
    const hash = (str) => {
      let h = 2166136261;
      for (let k = 0; k < str.length; k++) h = Math.imul(h ^ str.charCodeAt(k), 16777619);
      return (h >>> 0).toString(36);
    };
    let label = g.atoms.map((a, i) => `${a.s}${info.hyd[i]}d${adj[i].length}`);
    for (let round = 0; round < 5; round++) {
      label = label.map((l, i) => hash(l + "(" + adj[i].map(([j, t]) => t + label[j]).sort().join(",") + ")"));
    }
    return info.text + ":" + label.sort().join(".");
  }
  const challengeKey = (c) => graphKey(applyMoves(load(c.mol), c.solve));

  if (typeof module !== "undefined") module.exports = { MOLS, CHALLENGES, analyse, load, bondLength, toSmiles, toCdxml, cleanUp, applyMoves, graphKey, challengeKey };

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
  const cleanBtn = doc.querySelector('[data-tool-action="clean"]');
  const exportBar = doc.querySelector(".export");
  const strip = doc.querySelector(".challenge");
  const challengeBtn = doc.querySelector("[data-challenge-open]");
  const motion = matchMedia("(prefers-reduced-motion: no-preference)");
  const point = svg.createSVGPoint();

  const states = {};
  let name = tabs[0].dataset.mol;
  let tool = "bond";
  let st;
  let drag = null;
  let hover = null, tipped = false;
  let quest = null;
  let tween = 0;

  const stateOf = (n) => {
    if (!states[n]) {
      const g = load(n);
      states[n] = { name: n, g, original: JSON.stringify(g), undo: [] };
    }
    return states[n];
  };

  // ---- geometry -------------------------------------------------------------------

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
    } else if (quest && st.name === quest.c.mol) {
      // In a challenge the readback is checked against the target structure instead.
      const hit = graphKey(st.g) === quest.key;
      setText("[data-log=readback]", hit ? `${info.html} ${T.challenge.matches} <span class="ok">✓</span>` : `${info.html} → ${fmt(T.challenge.aim, { formula: quest.formula })}`);
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
    cleanBtn.disabled = st.g.atoms.length < 2;
    exportBar.querySelectorAll("[data-export]").forEach((b) => { b.disabled = empty; });
    svg.setAttribute("aria-label", fmt(T.aria, { name: T.names[st.name], formula: empty ? "—" : info.text }));
    if (quest && !quest.won && st.name === quest.c.mol && graphKey(st.g) === quest.key) win();

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
    cancelAnimationFrame(tween);
    st.undo.push(JSON.stringify(st.g));
    if (st.undo.length > 40) st.undo.shift();
    if (quest) quest.moves++;
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
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "k") { e.preventDefault(); clean(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const next = keys[e.key.toLowerCase()];
    if (next) setTool(next);
  });

  // ChemDraw's hotkeys: with the pointer over an atom, type an element (L is Cl); over a bond,
  // type 1, 2 or 3 for its order. Delete removes whatever is under the pointer.
  const ELEMENT_KEYS = { c: "C", n: "N", o: "O", s: "S", f: "F", l: "Cl" };
  svg.addEventListener("pointerover", (e) => {
    const atomEl = e.target.closest("[data-atom]"), bondEl = e.target.closest("[data-bond]");
    hover = atomEl ? { atom: +atomEl.dataset.atom } : bondEl ? { bond: +bondEl.dataset.bond } : null;
    // The first time the pointer rests on the drawing, say that these keys exist.
    if (hover && !tipped && tool !== "move" && !status.dataset.state) { tipped = true; status.textContent = T.keys; }
  });
  svg.addEventListener("pointerleave", () => { hover = null; });
  document.addEventListener("keydown", (e) => {
    if (!hover || drag || e.ctrlKey || e.metaKey || e.altKey || (e.target instanceof Element && e.target.closest("input, textarea, select, [contenteditable]"))) return;
    const key = e.key.toLowerCase();
    if (hover.atom !== undefined && hover.atom < st.g.atoms.length) {
      const i = hover.atom, sym = ELEMENT_KEYS[key];
      if (sym && st.g.atoms[i].s !== sym) { e.preventDefault(); change(fmt(T.element, { sym }), (d) => { d.atoms[i].s = sym; }); }
      else if (key === "delete" || key === "backspace") { e.preventDefault(); hover = null; change(T.erased, (d) => remove(d, i)); }
    } else if (hover.bond !== undefined && hover.bond < st.g.bonds.length) {
      const k = hover.bond, order = { 1: 1, 2: 2, 3: 3 }[key];
      if (order && st.g.bonds[k].o !== order) { e.preventDefault(); change(fmt(T.setBond, { order: T.order[order - 1] }), (d) => { d.bonds[k].o = order; }); }
      else if (key === "delete" || key === "backspace") { e.preventDefault(); hover = null; change(T.erased, (d) => d.bonds.splice(k, 1)); }
    }
  });

  // Clean Up: the atoms glide to their cleaned positions, then the drawing is redrawn once more
  // so labels and double bonds settle on the right side.
  function clean() {
    if (st.g.atoms.length < 2) return;
    const to = cleanUp(st.g, bondLength(JSON.parse(st.original)));
    const from = st.g.atoms.map((a) => ({ x: a.x, y: a.y }));
    change(T.cleaned, () => {});
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

  // Export: SMILES to the clipboard, or the drawing as a CDXML file for ChemDraw.
  exportBar.querySelector('[data-export="smiles"]').addEventListener("click", async () => {
    const smiles = toSmiles(st.g);
    if (smiles === null) return update(T.noSmiles);
    try {
      await navigator.clipboard.writeText(smiles);
      update(fmt(T.copied, { smiles }));
    } catch {
      update(fmt(T.smiles, { smiles }));
    }
  });
  exportBar.querySelector('[data-export="cdxml"]').addEventListener("click", () => {
    const dirty = JSON.stringify(st.g) !== st.original;
    const url = URL.createObjectURL(new Blob([toCdxml(st.g)], { type: "chemical/x-cdxml" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${st.name}${dirty ? "-edited" : ""}.cdxml` });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    update(fmt(T.download, { file: a.download }));
  });

  // ---- challenge mode -------------------------------------------------------------

  // Six small edits, one at a time, checked by structure rather than by picture. Solved ones
  // are remembered in this browser.
  const C = T.challenge;
  const solvedKey = "chemdraw-skill-challenges";
  const solved = new Set((() => { try { return JSON.parse(localStorage.getItem(solvedKey)) || []; } catch { return []; } })());
  const keep = () => { try { localStorage.setItem(solvedKey, JSON.stringify([...solved])); } catch { /* not kept */ } };

  function paintStrip() {
    const k = CHALLENGES.indexOf(quest.c), task = C.tasks[quest.c.id];
    const dots = CHALLENGES.map((c, n) => `<i class="${solved.has(c.id) ? "got" : ""}${n === k ? " now" : ""}"></i>`).join("");
    const all = CHALLENGES.every((c) => solved.has(c.id));
    strip.dataset.state = quest.won ? "won" : "";
    strip.innerHTML = `
      <div class="ch-head"><b>${fmt(C.title, { n: k + 1, total: CHALLENGES.length })}</b>
        <span class="ch-dots" role="img" aria-label="${fmt(C.count, { done: solved.size, total: CHALLENGES.length })}">${dots}</span>
        <button type="button" data-ch="close" aria-label="${C.close}" title="${C.close}">×</button></div>
      <p class="ch-task">${quest.won ? fmt(C.done, { moves: quest.moves }) + (all ? " " + C.all : "") : task.task}</p>
      <div class="ch-actions">${quest.won ? "" : `<button type="button" data-ch="hint">${C.hint}</button>`}<button type="button" data-ch="skip">${quest.won ? C.next : C.skip}</button></div>
      <p class="ch-hint"${quest.hint && !quest.won ? "" : " hidden"}>${task.hint}</p>`;
  }

  function startChallenge(c) {
    quest = { c, key: challengeKey(c), formula: analyse(applyMoves(load(c.mol), c.solve)).html, moves: 0, won: false, hint: false };
    const target = stateOf(c.mol);
    target.undo = [];
    target.g = JSON.parse(target.original);
    strip.hidden = false;
    challengeBtn.setAttribute("aria-expanded", "true");
    open(c.mol, false);
    paintStrip();
  }
  const nextChallenge = () => {
    const from = quest ? CHALLENGES.indexOf(quest.c) + 1 : 0;
    const order = CHALLENGES.slice(from).concat(CHALLENGES.slice(0, from));
    startChallenge(order.find((c) => !solved.has(c.id)) || order[0]);
  };
  function stopChallenge() {
    quest = null;
    strip.hidden = true;
    update();
    challengeBtn.setAttribute("aria-expanded", "false");
    challengeBtn.focus();
  }

  function win() {
    quest.won = true;
    solved.add(quest.c.id);
    keep();
    challengeBtn.dataset.count = `${solved.size}/${CHALLENGES.length}`;
    paintStrip();
    burst();
  }

  // A shower of atom labels and rings from the middle of the canvas.
  function burst() {
    if (!motion.matches) return;
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

  challengeBtn.addEventListener("click", () => (quest ? stopChallenge() : nextChallenge()));
  strip.addEventListener("click", (e) => {
    const act = e.target.closest("[data-ch]");
    if (!act) return;
    if (act.dataset.ch === "close") stopChallenge();
    else if (act.dataset.ch === "skip") nextChallenge();
    else if (act.dataset.ch === "hint") { quest.hint = true; paintStrip(); }
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
  exportBar.hidden = false;
  challengeBtn.hidden = false;
  if (solved.size) challengeBtn.dataset.count = `${solved.size}/${CHALLENGES.length}`;
  tabs[0].closest("[role=tablist]").hidden = false;
  doc.querySelector(".fname").hidden = true;
  open(name, false);
  setTool("bond");
  play();
})();
