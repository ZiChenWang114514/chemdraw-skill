// The chemistry behind the site's editor and games, with no page in it: the molecule table,
// analysis, SMILES and CDXML export, Clean Up, the skeletal drawing, the challenge list and the
// rules of each game. tests/test_site.py runs all of it in Node; browsers get it as
// globalThis.Chem. MOLS was laid out with RDKit and kept as plain coordinates; docs/website.md
// says how to regenerate it.

(() => {
  const MOLS = {
    "aspirin": {"smiles":"CC(=O)Oc1ccccc1C(=O)O","formula":"C9H8O4","atoms":[["C",40.0,123.7],["C",88.4,151.8],["O",88.4,207.8],["O",137.0,123.8],["C",185.4,152.0],["C",185.3,208.0],["C",233.8,236.1],["C",282.3,208.2],["C",282.4,152.2],["C",234.0,124.1],["C",234.1,68.1],["O",185.6,40.1],["O",282.6,40.1]],"bonds":[[0,1,1],[1,2,2],[1,3,1],[3,4,1],[4,5,2],[5,6,1],[6,7,2],[7,8,1],[8,9,2],[9,10,1],[10,11,2],[10,12,1],[9,4,1]]},
    "paracetamol": {"smiles":"CC(=O)Nc1ccc(O)cc1","formula":"C8H9NO2","atoms":[["C",48.0,137.7],["C",87.6,127.1],["O",98.2,87.5],["N",116.6,156.1],["C",156.2,145.5],["C",185.2,174.5],["C",224.8,163.9],["C",235.4,124.3],["O",275.0,113.7],["C",206.4,95.3],["C",166.8,105.9]],"bonds":[[0,1,1],[1,2,2],[1,3,1],[3,4,1],[4,5,1],[5,6,2],[6,7,1],[7,8,1],[7,9,2],[9,10,1],[10,4,2]]},
    "caffeine": {"smiles":"Cn1c(=O)c2c(ncn2C)n(C)c1=O","formula":"C8H10N4O2","atoms":[["C",66.7,168.0],["N",92.6,135.7],["C",81.7,95.8],["N",116.3,73.2],["C",148.5,99.0],["C",133.9,137.7],["C",160.1,169.7],["O",145.4,208.3],["N",200.8,163.0],["C",227.0,195.0],["C",215.5,124.3],["O",256.3,117.7],["N",189.3,92.3],["C",203.9,53.7]],"bonds":[[0,1,1],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[5,6,1],[6,7,2],[6,8,1],[8,9,1],[8,10,1],[10,11,2],[10,12,1],[12,13,1],[5,1,1],[12,4,1]]},
    "ibuprofen": {"smiles":"CC(C)Cc1ccc(C(C)C(=O)O)cc1","formula":"C13H18O2","atoms":[["C",48.0,125.4],["C",80.4,123.4],["C",94.9,94.3],["C",98.4,150.5],["C",130.8,148.5],["C",148.7,175.6],["C",181.2,173.6],["C",195.7,144.5],["C",177.7,117.5],["C",145.3,119.4],["C",228.1,142.6],["C",246.0,169.6],["C",242.6,113.5],["O",224.6,86.4],["O",275.0,111.5]],"bonds":[[0,1,1],[1,2,1],[1,3,1],[3,4,1],[4,5,1],[5,6,2],[6,7,1],[7,8,2],[8,9,1],[7,10,1],[10,11,1],[10,12,1],[12,13,2],[12,14,1],[9,4,2]]},
    "vanillin": {"smiles":"COc1cc(C=O)ccc1O","formula":"C8H8O3","atoms":[["C",268.3,159.1],["O",230.5,175.9],["C",197.1,151.6],["C",159.3,168.3],["C",125.9,144.0],["C",88.1,160.8],["O",54.7,136.5],["C",130.3,102.9],["C",168.0,86.1],["C",201.5,110.5],["O",239.2,93.7]],"bonds":[[0,1,1],[1,2,1],[2,3,1],[3,4,2],[4,5,1],[5,6,2],[4,7,1],[7,8,2],[8,9,1],[9,10,1],[9,2,2]]},
  };

  // Starting skeletons for the daily molecules that no level uses. Laid out like MOLS (CoordGen, principal
  // axis horizontal, bond length 62 shrunk to 40 so there is room to grow) but kept off the hero's tabs and
  // the Sketchpad's chips. docs/website.md says how to regenerate them.
  const STARTERS = {
    "benzene": {"smiles":"C1=CC=CC=C1","formula":"C6H6","atoms":[["C",161.5,171.0],["C",196.1,151.0],["C",196.1,111.0],["C",161.5,91.0],["C",126.9,111.0],["C",126.9,151.0]],"bonds":[[0,1,1],[1,2,2],[2,3,1],[3,4,2],[4,5,1],[5,0,2]]},
    "pyridine": {"smiles":"C1=CC=NC=C1","formula":"C5H5N","atoms":[["C",161.5,171.0],["C",126.9,151.0],["C",126.9,111.0],["N",161.5,91.0],["C",196.1,111.0],["C",196.1,151.0]],"bonds":[[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[5,0,1]]},
    "pyrimidine": {"smiles":"C1=CN=CN=C1","formula":"C4H4N2","atoms":[["C",161.5,171.0],["C",126.9,151.0],["N",126.9,111.0],["C",161.5,91.0],["N",196.1,111.0],["C",196.1,151.0]],"bonds":[[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[5,0,1]]},
    "imidazole": {"smiles":"C1=CN=CN1","formula":"C3H4N2","atoms":[["C",161.5,161.8],["C",129.1,138.3],["N",141.5,100.2],["C",181.5,100.2],["N",193.9,138.3]],"bonds":[[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,0,1]]},
    "indole": {"smiles":"C1=CC=C2C(=C1)C=CN2","formula":"C8H7N","atoms":[["C",96.1,111.0],["C",96.1,151.0],["C",130.7,171.0],["C",165.4,151.0],["C",165.4,111.0],["C",130.7,91.0],["C",203.4,98.6],["C",226.9,131.0],["N",203.4,163.4]],"bonds":[[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[4,6,1],[6,7,2],[7,8,1],[5,0,1],[8,3,1]]},
    "naphthalene": {"smiles":"C1=CC=C2C=CC=CC2=C1","formula":"C10H8","atoms":[["C",92.2,151.0],["C",92.2,111.0],["C",126.9,91.0],["C",161.5,111.0],["C",196.1,91.0],["C",230.8,111.0],["C",230.8,151.0],["C",196.1,171.0],["C",161.5,151.0],["C",126.9,171.0]],"bonds":[[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[5,6,1],[6,7,2],[7,8,1],[8,9,2],[9,0,1],[8,3,1]]},
    "cyclohexane": {"smiles":"C1CCCCC1","formula":"C6H12","atoms":[["C",161.5,171.0],["C",196.1,151.0],["C",196.1,111.0],["C",161.5,91.0],["C",126.9,111.0],["C",126.9,151.0]],"bonds":[[0,1,1],[1,2,1],[2,3,1],[3,4,1],[4,5,1],[5,0,1]]},
    "thiophene": {"smiles":"C1=CSC=C1","formula":"C4H4S","atoms":[["C",161.5,161.8],["C",129.1,138.3],["S",141.5,100.2],["C",181.5,100.2],["C",193.9,138.3]],"bonds":[[0,1,2],[1,2,1],[2,3,1],[3,4,2],[4,0,1]]},
    "furan": {"smiles":"C1=COC=C1","formula":"C4H4O","atoms":[["C",161.5,161.8],["C",129.1,138.3],["O",141.5,100.2],["C",181.5,100.2],["C",193.9,138.3]],"bonds":[[0,1,2],[1,2,1],[2,3,1],[3,4,2],[4,0,1]]},
    "purine": {"smiles":"C1=C2C(=NC=N1)N=CN2","formula":"C5H4N4","atoms":[["C",192.3,171.0],["C",157.6,151.0],["C",157.6,111.0],["N",192.3,91.0],["C",226.9,111.0],["N",226.9,151.0],["N",119.6,98.6],["C",96.1,131.0],["N",119.6,163.4]],"bonds":[[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[2,6,1],[6,7,2],[7,8,1],[5,0,1],[8,1,1]]},
    "aceticAcid": {"smiles":"CC(=O)O","formula":"C2H4O2","atoms":[["C",161.5,161.0],["C",161.5,121.0],["O",196.1,101.0],["O",126.9,101.0]],"bonds":[[0,1,1],[1,2,2],[1,3,1]]},
    "hexane": {"smiles":"CCCCCC","formula":"C6H14","atoms":[["C",248.5,136.6],["C",212.9,118.4],["C",179.3,140.1],["C",143.7,121.9],["C",110.1,143.6],["C",74.5,125.4]],"bonds":[[0,1,1],[1,2,1],[2,3,1],[3,4,1],[4,5,1]]},
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
  // What a person sees of an id such as aceticAcid: in a file name, or in the agent's log.
  const fileName = (id) => id.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

  function load(name) {
    const m = MOLS[name] || STARTERS[name];
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
      used, hyd, over, count, mass, exact,
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

  // ---- edits and geometry ----------------------------------------------------------

  function remove(g, atom) {
    g.atoms.splice(atom, 1);
    g.bonds = g.bonds.filter((b) => b.a !== atom && b.b !== atom).map((b) => ({
      a: b.a > atom ? b.a - 1 : b.a, b: b.b > atom ? b.b - 1 : b.b, o: b.o,
    }));
  }

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

  // Six points of a hexagon around a centre.
  const ringAt = (centre, L, turn) => Array.from({ length: 6 }, (_, k) => ({ x: centre.x + L * Math.cos(turn + (k * Math.PI) / 3), y: centre.y + L * Math.sin(turn + (k * Math.PI) / 3) }));
  function addRing(d, spot) {
    const base = d.atoms.length;
    spot.forEach((p) => d.atoms.push({ s: "C", x: p.x, y: p.y }));
    for (let k = 0; k < 6; k++) d.bonds.push({ a: base + k, b: base + ((k + 1) % 6), o: k % 2 ? 1 : 2 });
    return base;
  }
  // The four new atoms of a ring built on a bond, on whichever side has more room; null if neither fits.
  function fuseSpot(g, bond) {
    const A = g.atoms[bond.a], B = g.atoms[bond.b];
    const side = Math.hypot(B.x - A.x, B.y - A.y) || 1;
    const nx = (A.y - B.y) / side, ny = (B.x - A.x) / side;
    const reach = (side * Math.sqrt(3)) / 2;
    let best = null, room = side * 0.6;
    for (const sign of [1, -1]) {
      const c = { x: (A.x + B.x) / 2 + sign * nx * reach, y: (A.y + B.y) / 2 + sign * ny * reach };
      const from = Math.atan2(A.y - c.y, A.x - c.x);
      const step = Math.atan2(Math.sin(Math.atan2(B.y - c.y, B.x - c.x) - from), Math.cos(Math.atan2(B.y - c.y, B.x - c.x) - from));
      const spot = [1, 2, 3, 4].map((k) => ({ x: c.x + side * Math.cos(from - k * step), y: c.y + side * Math.sin(from - k * step) }));
      const clear = Math.min(...spot.flatMap((p) => g.atoms.map((q) => Math.hypot(p.x - q.x, p.y - q.y))));
      if (spot.every((p) => inside(p)) && clear > room) { best = spot; room = clear; }
    }
    return best;
  }

  // What a tool does to an atom, a bond or a point on the canvas. This is the one place a click's
  // result is decided, and the preview draws its answer, so the two cannot disagree. Returns null
  // when the tool does nothing there, and { say, g: null } when it is refused. g is left alone.
  function applyTool(g, tool, aim, back = false) {
    if (tool === "move") return null;
    const d = JSON.parse(JSON.stringify(g));
    const L = bondLength(g);
    const noRoom = { say: "noRoom", g: null };
    if (aim.atom !== undefined) {
      const i = aim.atom, a = g.atoms[i];
      if (!a) return null;
      if (tool === "bond") {
        const spot = place(g, i, (t) => [{ x: a.x + L * Math.cos(t), y: a.y + L * Math.sin(t) }]);
        if (!spot) return noRoom;
        d.atoms.push({ s: "C", x: spot[0].x, y: spot[0].y });
        d.bonds.push({ a: i, b: d.atoms.length - 1, o: 1 });
        return { say: "grow", g: d };
      }
      if (tool === "atom") {
        const sym = CYCLE[(CYCLE.indexOf(a.s) + (back ? CYCLE.length - 1 : 1)) % CYCLE.length];
        d.atoms[i].s = sym;
        return { say: "element", sym, g: d };
      }
      if (tool === "ring") {
        const spot = place(g, i, (t) => ringAt({ x: a.x + 2 * L * Math.cos(t), y: a.y + 2 * L * Math.sin(t) }, L, t + Math.PI));
        if (!spot) return noRoom;
        d.bonds.push({ a: i, b: addRing(d, spot), o: 1 });
        return { say: "ring", g: d };
      }
      const bonds = g.bonds.flatMap((b, k) => (b.a === i || b.b === i ? [k] : []));
      remove(d, i);
      return { say: "erased", g: d, drop: { atoms: [i], bonds } };
    }
    if (aim.bond !== undefined) {
      const bond = g.bonds[aim.bond];
      if (!bond) return null;
      if (tool === "bond") {
        const order = (bond.o % 3) + 1;
        d.bonds[aim.bond].o = order;
        return { say: "setBond", order, g: d };
      }
      if (tool === "ring") {
        const spot = fuseSpot(g, bond);
        if (!spot) return noRoom;
        const base = d.atoms.length;
        spot.forEach((p) => d.atoms.push({ s: "C", x: p.x, y: p.y }));
        [bond.a, base, base + 1, base + 2, base + 3, bond.b].forEach((at, k, chain) => { if (k < 5) d.bonds.push({ a: at, b: chain[k + 1], o: k % 2 ? 2 : 1 }); });
        return { say: "ring", g: d };
      }
      if (tool === "erase") {
        d.bonds.splice(aim.bond, 1);
        return { say: "erased", g: d, drop: { atoms: [], bonds: [aim.bond] } };
      }
      return null;
    }
    if (!inside(aim)) return null;
    if (tool === "bond" || tool === "atom") {
      d.atoms.push({ s: "C", x: aim.x, y: aim.y });
      return { say: "placed", g: d };
    }
    if (tool === "ring") {
      const spot = ringAt(aim, L, -Math.PI / 2);
      if (!spot.every((q) => inside(q))) return noRoom;
      addRing(d, spot);
      return { say: "ringPlaced", g: d };
    }
    return null;
  }

  // A plan from applyTool drawn over the canvas: what will appear, or what will go.
  function previewMarkup(before, plan) {
    const isLabelled = (g, nb) => g.atoms.map((a, i) => a.s !== "C" || !nb[i].length);
    if (plan.drop) {
      const nb = neighbours(before), labelled = isLabelled(before, nb);
      const lines = plan.drop.bonds.map((k) => `<path class="b" d="${bondPath(before, nb, labelled, before.bonds[k])}"/>`).join("");
      const dots = plan.drop.atoms.map((i) => `<circle cx="${f1(before.atoms[i].x)}" cy="${f1(before.atoms[i].y)}" r="12"/>`).join("");
      return `<g class="preview drop">${lines}${dots}</g>`;
    }
    const g = plan.g, nb = neighbours(g), info = analyse(g), labelled = isLabelled(g, nb);
    const lines = g.bonds.filter((b, k) => k >= before.bonds.length || b.o !== before.bonds[k].o).map((b) => `<path class="b" d="${bondPath(g, nb, labelled, b)}"/>`).join("");
    const atoms = g.atoms.map((a, i) => {
      if (i < before.atoms.length && a.s === before.atoms[i].s) return "";
      const mask = i < before.atoms.length ? `<circle class="mask" cx="${f1(a.x)}" cy="${f1(a.y)}" r="12"/>` : "";
      return mask + (labelled[i] ? label(g, nb, info, i, 0) : "");
    }).join("");
    return `<g class="preview">${lines}${atoms}</g>`;
  }

  // The structure as SVG markup, used for the editor's canvas and for every thumbnail. flags
  // circles over-valent atoms, selection adds ChemDraw's box, hit adds the invisible click targets.
  function drawMarkup(g, { flags = true, box = true, hit = true } = {}) {
    const info = analyse(g);
    const nb = neighbours(g);
    const labelled = g.atoms.map((a, i) => a.s !== "C" || !nb[i].length);
    const spread = (k) => Math.round((k * 12) / Math.max(g.bonds.length - 1, 12));
    const first = g.atoms.map(() => null);
    g.bonds.forEach((b, k) => { [b.a, b.b].forEach((i) => { if (first[i] === null || spread(k) < first[i]) first[i] = spread(k); }); });

    const bonds = g.bonds.map((b, k) => `<path class="b" style="--i:${spread(k)}" d="${bondPath(g, nb, labelled, b)}"/>`).join("");
    const labels = g.atoms.map((a, i) => (labelled[i] ? label(g, nb, info, i, first[i] || 0) : "")).join("");
    const warn = flags ? g.atoms.map((a, i) => (info.over[i] ? `<circle class="warn" cx="${f1(a.x)}" cy="${f1(a.y)}" r="12"/>` : "")).join("") : "";
    const hitBonds = g.bonds.map((b, k) => `<path data-bond="${k}" d="M${f1(g.atoms[b.a].x)} ${f1(g.atoms[b.a].y)}L${f1(g.atoms[b.b].x)} ${f1(g.atoms[b.b].y)}"/>`).join("");
    const hitAtoms = g.atoms.map((a, i) => `<circle data-atom="${i}" cx="${f1(a.x)}" cy="${f1(a.y)}" r="13"/>`).join("");
    return bonds + labels + warn + (box ? selection(g) : "") + (hit ? `<g class="hit">${hitBonds}${hitAtoms}</g>` : "");
  }

  // A small drawing of a structure, framed tightly around it.
  function thumb(g, label = "") {
    const xs = g.atoms.map((a) => a.x), ys = g.atoms.map((a) => a.y);
    // Framed by bond length, so that a small molecule is drawn at the same scale as a big one.
    const pad = 24, L = bondLength(g);
    const w = Math.max(Math.max(...xs) - Math.min(...xs) + 2 * pad, 6 * L), h = Math.max(Math.max(...ys) - Math.min(...ys) + 2 * pad, 5 * L);
    const x0 = (Math.min(...xs) + Math.max(...xs) - w) / 2, y0 = (Math.min(...ys) + Math.max(...ys) - h) / 2;
    return `<svg class="mol thumb" viewBox="${f1(x0)} ${f1(y0)} ${f1(w)} ${f1(h)}" role="img" aria-label="${label}">${drawMarkup(g, { flags: false, box: false, hit: false })}</svg>`;
  }

  // ---- challenges -----------------------------------------------------------------

  // Small edits that turn one of the five molecules into a named compound, in three chapters.
  // Each target is defined by the moves that reach it (tests/test_site.py checks the result
  // against the compound's published SMILES), and their number is the par for three stars. The
  // visitor may reach it any way they like.
  const CHALLENGES = [
    { id: "salicylic", chapter: "take", mol: "aspirin", solve: [["erase", 0], ["erase", 0], ["erase", 0]] },
    { id: "aminophenol", chapter: "take", mol: "paracetamol", solve: [["erase", 0], ["erase", 0], ["erase", 0]] },
    { id: "acetanilide", chapter: "take", mol: "paracetamol", solve: [["erase", 8]] },
    { id: "phenylAcetate", chapter: "take", mol: "aspirin", solve: [["erase", 10], ["erase", 10], ["erase", 10]] },
    { id: "theophylline", chapter: "take", mol: "caffeine", solve: [["erase", 0]] },
    { id: "theobromine", chapter: "take", mol: "caffeine", solve: [["erase", 9]] },
    { id: "paraxanthine", chapter: "take", mol: "caffeine", solve: [["erase", 13]] },
    { id: "xanthine", chapter: "take", mol: "caffeine", solve: [["erase", 13], ["erase", 9], ["erase", 0]] },
    { id: "ibufenac", chapter: "take", mol: "ibuprofen", solve: [["erase", 11]] },
    { id: "protocatechuic", chapter: "take", mol: "vanillin", solve: [["erase", 0]] },
    { id: "fluoroacetanilide", chapter: "swap", mol: "paracetamol", solve: [["element", 8, "F"]] },
    { id: "vanillylAlcohol", chapter: "swap", mol: "vanillin", solve: [["order", 5, 1]] },
    { id: "ibuprofenAmide", chapter: "swap", mol: "ibuprofen", solve: [["element", 14, "N"]] },
    { id: "isovanillin", chapter: "swap", mol: "vanillin", solve: [["erase", 0], ["grow", 9]] },
    { id: "wintergreen", chapter: "swap", mol: "aspirin", solve: [["erase", 0], ["erase", 0], ["erase", 0], ["grow", 9]] },
    { id: "ibuprofenMethyl", chapter: "add", mol: "ibuprofen", solve: [["grow", 14]] },
    { id: "vanillic", chapter: "add", mol: "vanillin", solve: [["grow", 5], ["element", 11, "O"]] },
    { id: "ethylVanillin", chapter: "add", mol: "vanillin", solve: [["grow", 0]] },
    { id: "veratraldehyde", chapter: "add", mol: "vanillin", solve: [["grow", 10]] },
    { id: "phenacetin", chapter: "add", mol: "paracetamol", solve: [["grow", 8], ["grow", 11]] },
  ];
  // Molecules that are only ever the daily one: no chapter, no star, nothing in the collection. Same moves as
  // a level; the tests check each against its published SMILES. Only ever append at the end.
  const DAILIES = [
    { id: "alanine", mol: "aceticAcid", solve: [["grow", 0], ["grow", 0], ["element", 5, "N"]] },
    { id: "threonine", mol: "aceticAcid", solve: [["grow", 0], ["grow", 4], ["grow", 4], ["grow", 0], ["element", 6, "O"], ["element", 7, "N"]] },
    { id: "methylimidazole", mol: "imidazole", solve: [["grow", 0]] },
    { id: "gaba", mol: "aceticAcid", solve: [["grow", 0], ["grow", 4], ["grow", 5], ["element", 6, "N"]] },
    { id: "glycine", mol: "aceticAcid", solve: [["grow", 0], ["element", 4, "N"]] },
    { id: "serine", mol: "aceticAcid", solve: [["grow", 0], ["grow", 4], ["grow", 0], ["element", 5, "O"], ["element", 6, "N"]] },
    { id: "methylMethacrylate", mol: "aceticAcid", solve: [["grow", 0], ["grow", 0], ["grow", 3], ["order", 4, 2]] },
    { id: "triazole", mol: "imidazole", solve: [["element", 0, "N"]] },
    { id: "cysteine", mol: "aceticAcid", solve: [["grow", 0], ["grow", 4], ["grow", 0], ["element", 5, "S"], ["element", 6, "N"]] },
    { id: "glycolicAcid", mol: "aceticAcid", solve: [["grow", 0], ["element", 4, "O"]] },
    { id: "diallylDisulfide", mol: "hexane", solve: [["element", 3, "S"], ["element", 4, "S"], ["grow", 5], ["grow", 6], ["order", 0, 2], ["order", 6, 2]] },
    { id: "lacticAcid", mol: "aceticAcid", solve: [["grow", 0], ["grow", 0], ["element", 5, "O"]] },
    { id: "methacrylicAcid", mol: "aceticAcid", solve: [["grow", 0], ["grow", 0], ["order", 4, 2]] },
    { id: "thymol", mol: "benzene", solve: [["grow", 0], ["grow", 3], ["grow", 7], ["grow", 7], ["grow", 2], ["element", 10, "O"]] },
    { id: "skatole", mol: "indole", solve: [["grow", 6]] },
    { id: "leafAldehyde", mol: "hexane", solve: [["grow", 5], ["order", 3, 2], ["element", 6, "O"], ["order", 5, 2]] },
    { id: "acrylicAcid", mol: "aceticAcid", solve: [["grow", 0], ["order", 3, 2]] },
    { id: "valine", mol: "aceticAcid", solve: [["grow", 0], ["grow", 4], ["grow", 4], ["grow", 0], ["element", 7, "N"]] },
    { id: "dimethylDisulfide", mol: "hexane", solve: [["erase", 1], ["erase", 0], ["element", 1, "S"], ["element", 2, "S"]] },
    { id: "benzimidazole", mol: "indole", solve: [["element", 6, "N"]] },
    { id: "isoamylAcetate", mol: "aceticAcid", solve: [["grow", 3], ["grow", 4], ["grow", 5], ["grow", 6], ["grow", 6]] },
    { id: "butyricAcid", mol: "aceticAcid", solve: [["grow", 0], ["grow", 4]] },
    { id: "carvacrol", mol: "benzene", solve: [["grow", 0], ["grow", 3], ["grow", 7], ["grow", 7], ["grow", 1], ["element", 10, "O"]] },
    { id: "vinylAcetate", mol: "aceticAcid", solve: [["grow", 3], ["grow", 4], ["order", 4, 2]] },
    { id: "dimethylacetamide", mol: "aceticAcid", solve: [["element", 3, "N"], ["grow", 3], ["grow", 3]] },
    { id: "cinnamylAlcohol", mol: "benzene", solve: [["grow", 2], ["grow", 6], ["grow", 7], ["grow", 8], ["element", 9, "O"], ["order", 7, 2]] },
    { id: "benzofuran", mol: "indole", solve: [["element", 8, "O"]] },
    { id: "heptanone", mol: "hexane", solve: [["grow", 5], ["grow", 5], ["element", 6, "O"], ["order", 5, 2]] },
    { id: "pyrazine", mol: "pyrimidine", solve: [["element", 4, "C"], ["element", 5, "N"]] },
    { id: "isoprene", mol: "hexane", solve: [["erase", 1], ["erase", 0], ["grow", 1], ["order", 2, 2], ["order", 3, 2]] },
    { id: "benzaldehyde", mol: "benzene", solve: [["grow", 3], ["grow", 6], ["element", 7, "O"], ["order", 7, 2]] },
    { id: "quinoline", mol: "naphthalene", solve: [["element", 4, "N"]] },
    { id: "acetophenone", mol: "benzene", solve: [["grow", 0], ["grow", 6], ["grow", 6], ["element", 8, "O"], ["order", 8, 2]] },
    { id: "chlorobenzene", mol: "benzene", solve: [["grow", 3], ["element", 6, "Cl"]] },
    { id: "nicotinamide", mol: "pyridine", solve: [["grow", 5], ["grow", 6], ["grow", 6], ["element", 7, "O"], ["element", 8, "N"], ["order", 7, 2]] },
    { id: "leafAlcohol", mol: "hexane", solve: [["grow", 5], ["order", 2, 2], ["element", 6, "O"]] },
    { id: "styrene", mol: "benzene", solve: [["grow", 0], ["grow", 6], ["order", 7, 2]] },
    { id: "niacin", mol: "pyridine", solve: [["grow", 5], ["grow", 6], ["grow", 6], ["element", 7, "O"], ["element", 8, "O"], ["order", 7, 2]] },
    { id: "isoquinoline", mol: "naphthalene", solve: [["element", 5, "N"]] },
    { id: "phenylethanol", mol: "benzene", solve: [["grow", 4], ["grow", 6], ["grow", 7], ["element", 8, "O"]] },
    { id: "pyrazole", mol: "imidazole", solve: [["element", 2, "C"], ["element", 3, "N"]] },
    { id: "tetramethylpyrazine", mol: "pyridine", solve: [["element", 0, "N"], ["grow", 2], ["grow", 4], ["grow", 5], ["grow", 1]] },
    { id: "hydroquinone", mol: "benzene", solve: [["grow", 5], ["grow", 2], ["element", 6, "O"], ["element", 7, "O"]] },
    { id: "cyclohexene", mol: "cyclohexane", solve: [["order", 3, 2]] },
    { id: "acetylpyridine", mol: "pyridine", solve: [["grow", 2], ["grow", 6], ["grow", 6], ["element", 8, "O"], ["order", 8, 2]] },
    { id: "benzothiazole", mol: "indole", solve: [["element", 6, "N"], ["element", 8, "S"]] },
    { id: "serotonin", mol: "indole", solve: [["grow", 0], ["grow", 6], ["grow", 10], ["grow", 11], ["element", 9, "O"], ["element", 12, "N"]] },
    { id: "benzylAlcohol", mol: "benzene", solve: [["grow", 3], ["grow", 6], ["element", 7, "O"]] },
    { id: "anisole", mol: "benzene", solve: [["grow", 0], ["grow", 6], ["element", 6, "O"]] },
    { id: "menthol", mol: "cyclohexane", solve: [["grow", 0], ["grow", 4], ["grow", 3], ["grow", 8], ["grow", 8], ["element", 7, "O"]] },
    { id: "tetrahydropyran", mol: "cyclohexane", solve: [["element", 3, "O"]] },
    { id: "catechol", mol: "benzene", solve: [["grow", 4], ["grow", 3], ["element", 6, "O"], ["element", 7, "O"]] },
    { id: "tetralin", mol: "naphthalene", solve: [["order", 4, 1], ["order", 6, 1]] },
    { id: "coumarin", mol: "naphthalene", solve: [["order", 4, 1], ["element", 4, "O"], ["grow", 5], ["element", 10, "O"], ["order", 11, 2]] },
    { id: "cymene", mol: "benzene", solve: [["grow", 0], ["grow", 3], ["grow", 7], ["grow", 7]] },
    { id: "thiazole", mol: "thiophene", solve: [["element", 4, "N"]] },
    { id: "hypoxanthine", mol: "caffeine", solve: [["erase", 13], ["erase", 11], ["erase", 9], ["erase", 0], ["order", 8, 2]] },
    { id: "naphthol2", mol: "naphthalene", solve: [["grow", 5], ["element", 10, "O"]] },
    { id: "limonene", mol: "cyclohexane", solve: [["grow", 0], ["grow", 3], ["grow", 7], ["grow", 7], ["order", 0, 2], ["order", 8, 2]] },
    { id: "dimethylpyrazine", mol: "pyridine", solve: [["element", 0, "N"], ["grow", 2], ["grow", 5]] },
    { id: "indoleCarbinol", mol: "indole", solve: [["grow", 6], ["grow", 9], ["element", 10, "O"]] },
    { id: "terpinene", mol: "cyclohexane", solve: [["grow", 0], ["grow", 3], ["grow", 7], ["grow", 7], ["order", 0, 2], ["order", 3, 2]] },
    { id: "pyrrole", mol: "furan", solve: [["element", 2, "N"]] },
    { id: "dmap", mol: "pyridine", solve: [["grow", 0], ["grow", 6], ["grow", 6], ["element", 6, "N"]] },
    { id: "naphthol1", mol: "naphthalene", solve: [["grow", 4], ["element", 10, "O"]] },
    { id: "isobutylbenzene", mol: "ibuprofen", solve: [["erase", 14], ["erase", 13], ["erase", 12], ["erase", 11], ["erase", 10]] },
    { id: "histamine", mol: "imidazole", solve: [["grow", 0], ["grow", 5], ["grow", 6], ["element", 7, "N"]] },
    { id: "vinylguaiacol", mol: "vanillin", solve: [["element", 6, "C"]] },
    { id: "acetovanillone", mol: "vanillin", solve: [["grow", 5]] },
    { id: "cyclohexanol", mol: "cyclohexane", solve: [["grow", 3], ["element", 6, "O"]] },
    { id: "furoicAcid", mol: "furan", solve: [["grow", 3], ["grow", 5], ["grow", 5], ["element", 6, "O"], ["element", 7, "O"], ["order", 6, 2]] },
    { id: "hydroxyquinoline", mol: "naphthalene", solve: [["element", 4, "N"], ["grow", 2], ["element", 10, "O"]] },
    { id: "furfurylAlcohol", mol: "furan", solve: [["grow", 3], ["grow", 5], ["element", 6, "O"]] },
    { id: "mercaptopurine", mol: "purine", solve: [["order", 0, 1], ["order", 2, 1], ["grow", 0], ["order", 1, 2], ["element", 9, "S"], ["order", 10, 2]] },
    { id: "morpholine", mol: "cyclohexane", solve: [["element", 2, "O"], ["element", 5, "N"]] },
    { id: "tryptophol", mol: "indole", solve: [["grow", 6], ["grow", 9], ["grow", 10], ["element", 11, "O"]] },
    { id: "piperazine", mol: "cyclohexane", solve: [["element", 2, "N"], ["element", 5, "N"]] },
    { id: "tetrahydrothiophene", mol: "thiophene", solve: [["order", 0, 1], ["order", 3, 1]] },
    { id: "menthane", mol: "cyclohexane", solve: [["grow", 0], ["grow", 3], ["grow", 7], ["grow", 7]] },
    { id: "dimethylfuran", mol: "furan", solve: [["grow", 1], ["grow", 3]] },
    { id: "thf", mol: "furan", solve: [["order", 0, 1], ["order", 3, 1]] },
    { id: "adenine", mol: "purine", solve: [["grow", 0], ["element", 9, "N"]] },
    { id: "guanine", mol: "caffeine", solve: [["erase", 13], ["erase", 9], ["erase", 0], ["order", 8, 1], ["element", 9, "N"], ["order", 9, 2]] },
    { id: "furfurylThiol", mol: "furan", solve: [["grow", 3], ["grow", 5], ["element", 6, "S"]] },
    { id: "cumene", mol: "benzene", solve: [["grow", 0], ["grow", 6], ["grow", 6]] },
    { id: "methylxanthine7", mol: "caffeine", solve: [["erase", 13], ["erase", 9]] },
    { id: "guaiacol", mol: "vanillin", solve: [["erase", 6], ["erase", 5]] },
    { id: "thiophenecarbaldehyde", mol: "thiophene", solve: [["grow", 3], ["grow", 5], ["element", 6, "O"], ["order", 6, 2]] },
    { id: "isoeugenol", mol: "vanillin", solve: [["element", 6, "C"], ["grow", 6]] },
    { id: "syringaldehyde", mol: "vanillin", solve: [["grow", 8], ["grow", 11], ["element", 11, "O"]] },
    { id: "furfural", mol: "furan", solve: [["grow", 3], ["grow", 5], ["element", 6, "O"], ["order", 6, 2]] },
    { id: "anisaldehyde", mol: "vanillin", solve: [["erase", 1], ["erase", 0], ["grow", 8]] },
    { id: "phenetidine", mol: "paracetamol", solve: [["erase", 2], ["element", 2, "O"], ["element", 7, "N"]] },
    { id: "diaminopurine", mol: "purine", solve: [["grow", 0], ["grow", 4], ["element", 9, "N"], ["element", 10, "N"]] },
    { id: "enprofylline", mol: "caffeine", solve: [["erase", 9], ["erase", 0], ["grow", 11], ["grow", 12]] },
    { id: "eugenol", mol: "vanillin", solve: [["order", 5, 1], ["element", 6, "C"], ["grow", 6], ["order", 11, 2]] },
    { id: "aniline", mol: "paracetamol", solve: [["erase", 8], ["erase", 2], ["erase", 1], ["erase", 0]] },
    { id: "salicylamide", mol: "aspirin", solve: [["erase", 2], ["erase", 1], ["erase", 0], ["element", 9, "N"]] },
    { id: "benzoicAcid", mol: "aspirin", solve: [["erase", 3], ["erase", 2], ["erase", 1], ["erase", 0]] },
    { id: "salicylaldehyde", mol: "aspirin", solve: [["erase", 12], ["erase", 2], ["erase", 1], ["erase", 0]] },
  ];
  const CHAPTERS = ["take", "swap", "add"];
  const XANTHINES = ["theophylline", "theobromine", "paraxanthine", "xanthine"];

  // Add a carbon on atom i, where the editor's bond tool would put it.
  function grow(g, i) {
    const L = bondLength(g);
    const spot = place(g, i, (t) => [{ x: g.atoms[i].x + L * Math.cos(t), y: g.atoms[i].y + L * Math.sin(t) }]);
    const base = freeAngle(g, i);
    const p = spot ? spot[0] : { x: g.atoms[i].x + L * Math.cos(base), y: g.atoms[i].y + L * Math.sin(base) };
    g.atoms.push({ s: "C", x: Math.min(W - 8, Math.max(8, p.x)), y: Math.min(H - 8, Math.max(8, p.y)) });
    g.bonds.push({ a: i, b: g.atoms.length - 1, o: 1 });
  }

  function applyMoves(g, moves) {
    moves.forEach(([move, i, value]) => {
      if (move === "erase") remove(g, i);
      else if (move === "element") g.atoms[i].s = value;
      else if (move === "order") g.bonds[i].o = value;
      else if (move === "grow") grow(g, i);
    });
    return g;
  }

  // Which bonds lie in a ring: a bond is in a ring when its ends stay connected without it.
  function ringBonds(g) {
    return g.bonds.map((b, k) => {
      const seen = new Set([b.a]), queue = [b.a];
      while (queue.length) {
        const i = queue.shift();
        g.bonds.forEach((c, m) => {
          if (m === k) return;
          const j = c.a === i ? c.b : c.b === i ? c.a : -1;
          if (j >= 0 && !seen.has(j)) { seen.add(j); queue.push(j); }
        });
      }
      return seen.has(b.b);
    });
  }

  // A fingerprint of the structure that ignores where atoms sit and which Kekule form a ring is
  // drawn in: each atom starts from its element, hydrogens, degree and any excess valence, and
  // one round per atom folds in its neighbours, with ring bonds marked as ring bonds rather than
  // single or double. An over-valent atom keeps its bond count, so it never matches a real target.
  function graphKey(g) {
    const info = analyse(g);
    const adj = g.atoms.map(() => []);
    const ring = ringBonds(g);
    g.bonds.forEach((b, k) => {
      const tag = ring[k] ? "r" : String(b.o);
      adj[b.a].push([b.b, tag]);
      adj[b.b].push([b.a, tag]);
    });
    const hash = (str) => {
      let h = 2166136261;
      for (let k = 0; k < str.length; k++) h = Math.imul(h ^ str.charCodeAt(k), 16777619);
      return (h >>> 0).toString(36);
    };
    let tags = g.atoms.map((a, i) => `${a.s}${info.hyd[i]}d${adj[i].length}${info.over[i] ? `!${info.used[i]}` : ""}`);
    for (let round = 0; round < Math.max(5, g.atoms.length); round++) {
      tags = tags.map((l, i) => hash(l + "(" + adj[i].map(([j, t]) => t + tags[j]).sort().join(",") + ")"));
    }
    return info.text + ":" + tags.sort().join(".");
  }
  const targetOf = (c) => applyMoves(load(c.mol), c.solve);
  const challengeKey = (c) => graphKey(targetOf(c));
  // What a drawing still needs to reach a target: one { s, n } per element that differs, Hill order.
  function formulaDelta(g, target) {
    const have = analyse(g).count, want = analyse(target).count;
    const all = [...new Set([...Object.keys(have), ...Object.keys(want)])];
    const order = all.includes("C") ? ["C", "H", ...all.filter((s) => s !== "C" && s !== "H").sort()] : all.sort();
    return order.map((s) => ({ s, n: (want[s] || 0) - (have[s] || 0) })).filter((d) => d.n);
  }
  const stars = (moves, par, hinted) => (hinted ? 1 : moves <= par ? 3 : 2);

  // ---- the daily compound ---------------------------------------------------------

  // Calendar days of the visitor's own time zone, handled as dates so no clock change can move
  // them. The stride is coprime with the list, so every compound comes up before any repeats.
  const FIRST_DAY = "2026-10-31";
  const dayNumber = (date) => Math.round(Date.parse(date + "T00:00:00Z") / 86400000);
  const localDate = (now = new Date()) => {
    const two = (n) => String(n).padStart(2, "0");
    return `${now.getFullYear()}-${two(now.getMonth() + 1)}-${two(now.getDate())}`;
  };
  const dailyNumber = (date) => dayNumber(date) - dayNumber(FIRST_DAY) + 1;
  // The daily picks from the twenty levels and then from the molecules that are only ever dailies,
  // so both lists may only grow at their ends.
  const DAILY_POOL = [...CHALLENGES, ...DAILIES];
  const isLevel = (id) => CHALLENGES.some((c) => c.id === id);
  const dailyPick = (date) => {
    const n = DAILY_POOL.length;
    return DAILY_POOL[(((dailyNumber(date) * 7) % n) + n) % n];
  };
  function nextStreak(daily, date) {
    if (daily.last === date) return { ...daily };
    const streak = daily.last && dayNumber(date) - dayNumber(daily.last) === 1 ? daily.streak + 1 : 1;
    return { ...daily, last: date, streak, best: Math.max(daily.best, streak) };
  }
  const dailyShare = (D, date, score, moves, url) =>
    `${fmt(D.shareTitle, { n: dailyNumber(date) })}\n${"⬢".repeat(score)}${"⬡".repeat(3 - score)} ${fmt(D.shareMoves, { moves })}\n${url}`;

  // ---- shared drawings ------------------------------------------------------------

  // A drawing in a link: atoms and bonds as JSON in base64url. A link can come from anyone and
  // its symbols reach innerHTML, so decoding accepts only exactly what the editor can draw.
  const MAX_ATOMS = 60, MAX_BONDS = 80, MAX_CODE = 4000;
  const toBase64 = (text) => btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const encodeDrawing = (g) => toBase64(JSON.stringify([
    g.atoms.map((a) => [a.s, Math.round(a.x * 10) / 10, Math.round(a.y * 10) / 10]),
    g.bonds.map((b) => [b.a, b.b, b.o]),
  ]));
  function decodeDrawing(code) {
    if (typeof code !== "string" || !code || code.length > MAX_CODE || !/^[\w-]+$/.test(code)) return null;
    let data;
    try { data = JSON.parse(atob(code.replace(/-/g, "+").replace(/_/g, "/"))); } catch { return null; }
    if (!Array.isArray(data) || data.length !== 2 || !Array.isArray(data[0]) || !Array.isArray(data[1])) return null;
    const [atoms, bonds] = data;
    if (!atoms.length || atoms.length > MAX_ATOMS || bonds.length > MAX_BONDS) return null;
    const number = (v, max) => typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= max;
    if (!atoms.every((a) => Array.isArray(a) && a.length === 3 && CYCLE.includes(a[0]) && number(a[1], W) && number(a[2], H))) return null;
    const pairs = new Set();
    for (const b of bonds) {
      if (!Array.isArray(b) || b.length !== 3) return null;
      const [p, q, o] = b;
      if (!Number.isInteger(p) || !Number.isInteger(q) || p === q || !atoms[p] || !atoms[q] || ![1, 2, 3].includes(o)) return null;
      const pair = p < q ? `${p},${q}` : `${q},${p}`;
      if (pairs.has(pair)) return null;
      pairs.add(pair);
    }
    return { atoms: atoms.map(([s, x, y]) => ({ s, x, y })), bonds: bonds.map(([a, b, o]) => ({ a, b, o })) };
  }

  // ---- saved progress -------------------------------------------------------------

  // Everything the games remember, kept in this browser only. Whatever is read back is checked
  // field by field, so damaged or old data costs at most that field.
  const STORE_KEY = "chemdraw-skill-lab";
  const STORE_VERSION = 1;
  const ROUNDS = 8;
  const emptyStore = () => ({ v: STORE_VERSION, levels: {}, daily: { last: "", streak: 0, best: 0, solved: {} }, hunt: { best: 0 }, isomers: {}, badges: [], exported: false });
  const plain = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
  const ISOMERS = [
    { formula: "C2H6O", count: 2 }, { formula: "C3H8O", count: 3 }, { formula: "C5H12", count: 3 },
    { formula: "C6H14", count: 5 }, { formula: "C4H10O", count: 7 }, { formula: "C4H8", count: 5 },
  ];
  const BADGES = ["first", "perfect", "xanthines", "complete", "readback", "isomers", "streak", "export"];

  function parseStore(text) {
    const store = emptyStore();
    let raw;
    try { raw = JSON.parse(text); } catch { return store; }
    if (!plain(raw) || raw.v !== STORE_VERSION) return store;
    const count = (v, max) => (Number.isInteger(v) && v >= 0 && v <= max ? v : 0);
    if (plain(raw.levels)) {
      CHALLENGES.forEach(({ id }) => {
        const l = raw.levels[id];
        if (plain(l) && [1, 2, 3].includes(l.stars)) store.levels[id] = { stars: l.stars, moves: count(l.moves, 9999) };
      });
    }
    if (plain(raw.daily)) {
      const day = /^\d{4}-\d{2}-\d{2}$/;
      if (typeof raw.daily.last === "string" && day.test(raw.daily.last)) store.daily.last = raw.daily.last;
      store.daily.streak = store.daily.last ? count(raw.daily.streak, 99999) : 0;
      store.daily.best = count(raw.daily.best, 99999);
      if (plain(raw.daily.solved)) {
        Object.entries(raw.daily.solved).forEach(([date, stored]) => {
          if (day.test(date) && plain(stored) && [1, 2, 3].includes(stored.stars)) store.daily.solved[date] = { stars: stored.stars, moves: count(stored.moves, 9999) };
        });
      }
    }
    if (plain(raw.hunt)) store.hunt.best = count(raw.hunt.best, ROUNDS);
    if (plain(raw.isomers)) {
      ISOMERS.forEach(({ formula, count: total }) => {
        const list = raw.isomers[formula];
        if (Array.isArray(list)) {
          const good = list.filter((code) => decodeDrawing(code)).slice(0, total);
          if (good.length) store.isomers[formula] = good;
        }
      });
    }
    if (Array.isArray(raw.badges)) store.badges = raw.badges.filter((b) => BADGES.includes(b));
    store.exported = raw.exported === true;
    return store;
  }

  // Note a solved level, keeping the best result; returns the stars of this attempt.
  function record(store, id, { moves, hinted }) {
    const c = CHALLENGES.find((x) => x.id === id);
    const got = stars(moves, c.solve.length, hinted);
    const old = store.levels[id];
    if (!old || got > old.stars || (got === old.stars && moves < old.moves)) store.levels[id] = { stars: got, moves };
    return got;
  }

  function earned(store) {
    const solved = (id) => !!store.levels[id];
    const rules = {
      first: () => CHALLENGES.some((c) => solved(c.id)),
      perfect: () => Object.values(store.levels).some((l) => l.stars === 3),
      xanthines: () => XANTHINES.every(solved),
      complete: () => CHALLENGES.every((c) => solved(c.id)),
      readback: () => store.hunt.best >= ROUNDS,
      isomers: () => ISOMERS.some(({ formula, count }) => (store.isomers[formula] || []).length >= count),
      streak: () => store.daily.best >= 7,
      export: () => store.exported,
    };
    return BADGES.filter((b) => rules[b]());
  }

  // ---- isomer hunt ----------------------------------------------------------------

  function connected(g) {
    if (!g.atoms.length) return false;
    const nb = neighbours(g), seen = new Set([0]), queue = [0];
    while (queue.length) nb[queue.shift()].forEach((j) => { if (!seen.has(j)) { seen.add(j); queue.push(j); } });
    return seen.size === g.atoms.length;
  }

  // The key of a drawing that counts as an isomer of the formula, or null if it does not:
  // one connected molecule, with the right formula and no atom over its valence.
  function isomerKey(g, formula) {
    const info = analyse(g);
    return connected(g) && info.text === formula && !info.over.some(Boolean) ? graphKey(g) : null;
  }

  // ---- readback hunt --------------------------------------------------------------

  // A round takes a real compound, keeps it as the truth, and draws it with one error of the
  // kind a checker has to catch. `hot` says which atoms and bonds count as finding that error.
  const SWAPS = { O: ["S", "N"], N: ["O"], F: ["Cl"], Cl: ["F"], S: ["O"], Br: ["Cl"] };
  function huntOptions(truth, kind) {
    const info = analyse(truth), nb = neighbours(truth), ring = ringBonds(truth);
    const atomInRing = truth.atoms.map((_, i) => truth.bonds.some((b, k) => ring[k] && (b.a === i || b.b === i)));
    const copy = () => JSON.parse(JSON.stringify(truth));
    const valid = (g) => !analyse(g).over.some(Boolean);
    const ends = (k) => [truth.bonds[k].a, truth.bonds[k].b];
    const out = [];
    if (kind === "element") {
      truth.atoms.forEach((a, i) => (SWAPS[a.s] || []).forEach((s) => {
        const g = copy();
        g.atoms[i].s = s;
        if (valid(g)) out.push({ shown: g, hot: { atoms: [i], bonds: [] } });
      }));
    } else if (kind === "ringN") {
      truth.atoms.forEach((a, i) => {
        if (a.s !== "C" || !atomInRing[i] || info.hyd[i] !== 1) return;
        const g = copy();
        g.atoms[i].s = "N";
        out.push({ shown: g, hot: { atoms: [i], bonds: [] } });
      });
    } else if (kind === "order") {
      truth.bonds.forEach((b, k) => {
        if (ring[k]) return;
        const next = b.o === 2 ? 1 : b.o === 1 && info.hyd[b.a] > 0 && info.hyd[b.b] > 0 ? 2 : 0;
        if (!next) return;
        const g = copy();
        g.bonds[k].o = next;
        out.push({ shown: g, hot: { atoms: ends(k), bonds: [k] } });
      });
    } else if (kind === "extra") {
      truth.atoms.forEach((a, i) => {
        if (a.s !== "C" || !atomInRing[i] || info.hyd[i] !== 1) return;
        const g = copy();
        grow(g, i);
        out.push({ shown: g, hot: { atoms: [i, g.atoms.length - 1], bonds: [g.bonds.length - 1] } });
      });
    } else if (kind === "missing") {
      truth.atoms.forEach((a, i) => {
        if (nb[i].length !== 1) return;
        const g = copy(), anchor = nb[i][0];
        remove(g, i);
        out.push({ shown: g, hot: { atoms: [anchor > i ? anchor - 1 : anchor], bonds: [] } });
      });
    } else if (kind === "valence") {
      truth.bonds.forEach((b, k) => {
        if (b.o !== 1 || (info.hyd[b.a] > 0 && info.hyd[b.b] > 0)) return;
        const g = copy();
        g.bonds[k].o = 2;
        if (!valid(g)) out.push({ shown: g, hot: { atoms: ends(k), bonds: [k] } });
      });
    }
    return out;
  }

  function makeHunt(seed) {
    // mulberry32: the same seed gives the same game.
    let state = seed >>> 0;
    const random = () => {
      state = (state + 0x6d2b79f5) >>> 0;
      let t = state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const shuffled = (list) => {
      const out = [...list];
      for (let k = out.length - 1; k > 0; k--) {
        const j = Math.floor(random() * (k + 1));
        [out[k], out[j]] = [out[j], out[k]];
      }
      return out;
    };
    const pool = shuffled([
      ...Object.keys(MOLS).map((id) => ({ id, truth: load(id) })),
      ...CHALLENGES.map((c) => ({ id: c.id, truth: targetOf(c) })),
    ]).slice(0, ROUNDS);
    const kinds = ["element", "ringN", "order", "extra", "missing", "valence"];
    let order = [];
    return pool.map(({ id, truth }, n) => {
      if (order.length < kinds.length) order = [...order, ...shuffled(kinds)];
      const at = order.findIndex((kind) => huntOptions(truth, kind).length);
      const kind = order.splice(at, 1)[0];
      const options = huntOptions(truth, kind);
      const { shown, hot } = options[Math.floor(random() * options.length)];
      // From the fifth round the drawing is mirrored, so it has to be read, not just compared.
      if (n >= 4) shown.atoms.forEach((a) => { a.x = W - a.x; });
      return { id, kind, truth, shown, hot };
    });
  }

  const api = {
    applyTool, previewMarkup, fileName, MOLS, STARTERS, W, H, EL, CYCLE, CHALLENGES, DAILIES, CHAPTERS, XANTHINES, ISOMERS, BADGES, ROUNDS, STORE_KEY,
    fmt, load, analyse, bondLength, neighbours, remove, inside, freeAngle, place, toSmiles, toCdxml, cleanUp, drawMarkup, thumb,
    applyMoves, graphKey, targetOf, challengeKey, formulaDelta, stars,
    localDate, dailyNumber, dailyPick, isLevel, nextStreak, dailyShare,
    encodeDrawing, decodeDrawing, emptyStore, parseStore, record, earned, isomerKey, makeHunt,
  };
  if (typeof module !== "undefined") module.exports = api;
  else globalThis.Chem = api;
})();
