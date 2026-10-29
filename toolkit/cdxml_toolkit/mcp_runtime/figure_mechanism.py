"""Reaction mechanisms for draw_figure: structures with the curved arrows the brief lists.

The brief names every species, the steps in the order they happen and, for
each step, the electron moves as (from atom or bond, to atom or bond). This
module places the structures, turns each move into a curved arrow from the
drawn 2D coordinates, checks that no arrow runs through another atom (one
automatic re-layout if one does), and reads the saved file back. It never
decides which electrons move: a brief without moves is refused, and a move
that looks wrong is drawn as given and reported.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdkit import Chem

from ..constants import (
    ACS_BOND_LENGTH,
    ACS_LINE_WIDTH,
    LAYOUT_BELOW_GAP,
    LAYOUT_FRAG_GAP_BONDS,
    LAYOUT_INTER_GAP_BONDS,
    LAYOUT_PLUS_GAP,
)
from ..render import renderer as R
from ..render.schema import StructureRef
from ..text_formatting import normalize_condition_text
from . import artifact_safety, figure_draw, figure_lint

MECH_KEYS = {"kind", "species", "steps", "max_width", "title", "style", "show_atom_numbers"}
SPECIES_KEYS = {"id", "smiles", "name", "label"}
STEP_KEYS = {"substrates", "products", "above", "below", "yield", "arrow", "moves"}
MOVE_KEYS = {"from", "to", "electrons"}
END_KEYS = {"species", "atom", "bond"}
MECH_ARROWS = ("solid", "reversible", "resonance")

X0 = 100.0                 # left edge of every row
FIRST_ROW_TOP = 120.0      # page y of the top of the first row
ROW_GAP = 18.0
TITLE_ROOM = 18.0
BULGE_MIN, BULGE_MAX = 9.0, 28.0
RELAYOUT_BULGE = 1.35
SAMPLES = 24
CARBON_REACH, LABEL_REACH = 3.5, 6.5   # how close a curve may pass an atom
CARBON_STANDOFF, LABEL_STANDOFF = 3.0, 7.0   # where an arrow starts or stops from an atom
HEIGHT_STEPS = (1.0, 1.4, 1.9, 2.5)   # arc heights tried, relative to the default
LABEL_OBSTACLE = 8.0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _end_errors(where: str, end: Any, ids: set[str]) -> list[str]:
    if not isinstance(end, dict):
        return [f"{where}: give the species and exactly one of atom or bond."]
    errors: list[str] = []
    extra = sorted(set(end) - END_KEYS)
    if extra:
        errors.append(f"{where}: unknown keys {extra}.")
    species = end.get("species")
    if species is None:
        errors.append(f"{where}: species is missing.")
    elif species not in ids:
        errors.append(f"{where}: species {species!r} is not in species.")
    given = [key for key in ("atom", "bond") if end.get(key) is not None]
    if len(given) != 1:
        errors.append(f"{where}: give exactly one of atom or bond.")
    elif given[0] == "atom" and not (_is_int(end["atom"]) and end["atom"] >= 0):
        errors.append(f"{where}: atom must be a whole number from 0.")
    elif given[0] == "bond":
        bond = end["bond"]
        if not (isinstance(bond, (list, tuple)) and len(bond) == 2 and all(_is_int(i) and i >= 0 for i in bond)
                and bond[0] != bond[1]):
            errors.append(f"{where}: bond must be two different atom numbers, such as [1, 2].")
    return errors


def _validate(brief: dict) -> list[str]:
    errors: list[str] = []
    unknown = sorted(set(brief) - MECH_KEYS)
    if unknown:
        errors.append(f"Unknown brief keys: {unknown}")
    if brief.get("style", "acs1996") != "acs1996":
        errors.append("style: only 'acs1996' is available.")
    width = brief.get("max_width")
    if width is not None and not (isinstance(width, (int, float)) and not isinstance(width, bool) and width > 0):
        errors.append("max_width must be a positive number of points.")
    if brief.get("show_atom_numbers") is not None and not isinstance(brief["show_atom_numbers"], bool):
        errors.append("show_atom_numbers must be true or false.")
    if brief.get("title") is not None and not isinstance(brief["title"], str):
        errors.append("title must be text.")

    species = brief.get("species")
    ids: set[str] = set()
    if not isinstance(species, list) or not species:
        errors.append("species: list every structure that is drawn, each with an id and a smiles or a name.")
        species = []
    for entry in species:
        if not isinstance(entry, dict) or not str(entry.get("id") or "").strip():
            errors.append("Every species needs an id.")
            continue
        ident = str(entry["id"])
        if ident in ids:
            errors.append(f"Species {ident}: duplicate id.")
        ids.add(ident)
        extra = sorted(set(entry) - SPECIES_KEYS)
        if extra:
            errors.append(f"Species {ident}: unknown keys {extra}.")
        if not entry.get("smiles") and not entry.get("name"):
            errors.append(f"Species {ident} needs a smiles or a name.")

    steps = brief.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps: give at least one step with substrates, products and moves.")
        steps = []
    produced: dict[str, int] = {}
    for number, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            errors.append(f"Step {number} must be an object.")
            continue
        extra = sorted(set(step) - STEP_KEYS)
        if extra:
            errors.append(f"Step {number}: unknown keys {extra}.")
        members: dict[str, list] = {}
        for side in ("substrates", "products"):
            members[side] = _as_ids(step.get(side))
            if not members[side]:
                errors.append(f"Step {number} needs {side}.")
            for member in members[side]:
                if member not in ids:
                    errors.append(f"Step {number} names {member!r} in {side}, which is not in species.")
        for product in members["products"]:
            if product in produced:
                errors.append(f"Species {product} is produced by step {produced[product]} and step {number}; "
                              "draw a second copy under another id if both are meant.")
            produced.setdefault(product, number)
        if step.get("arrow", "solid") not in MECH_ARROWS:
            errors.append(f"Step {number}: arrow must be one of {list(MECH_ARROWS)}.")
        moves = step.get("moves")
        if not isinstance(moves, list) or not moves:
            errors.append(f"Step {number} needs moves: list each electron move as from and to "
                          "(an atom number or a bond). A mechanism is never inferred.")
            continue
        for index, move in enumerate(moves, 1):
            errors += _move_errors(number, index, move, members["substrates"], ids)
    return errors


def _as_ids(value: Any) -> list[str]:
    return [str(i) for i in figure_draw._as_list(value)]


def _move_errors(number: int, index: int, move: Any, substrates: list[str], ids: set[str]) -> list[str]:
    where = f"Step {number} move {index}"
    if not isinstance(move, dict):
        return [f"{where} must be an object with from and to."]
    errors: list[str] = []
    extra = sorted(set(move) - MOVE_KEYS)
    if extra:
        errors.append(f"{where}: unknown keys {extra}.")
    if move.get("electrons", 2) not in (1, 2) or isinstance(move.get("electrons"), bool):
        errors.append(f"{where}: electrons must be 1 or 2.")
    for side in ("from", "to"):
        errors += _end_errors(f"{where} {side}", move.get(side), ids)
        end = move.get(side)
        if isinstance(end, dict) and end.get("species") in ids and end["species"] not in substrates:
            errors.append(f"{where} {side}: species {end['species']!r} is not one of the step's substrates; "
                          "electrons move within the species that react.")
    if not errors and _end_key(move["from"]) == _end_key(move["to"]):
        errors.append(f"{where}: the arrow starts and ends on the same atom or bond.")
    return errors


def _end_key(end: dict) -> tuple:
    if end.get("atom") is not None:
        return (end["species"], "atom", end["atom"])
    return (end["species"], "bond", tuple(sorted(end["bond"])))


def _index_errors(brief: dict, mols: dict[str, Any]) -> list[str]:
    """Atom and bond numbers must exist in the grounded structures."""
    errors: list[str] = []
    for number, step in enumerate(brief["steps"], 1):
        for index, move in enumerate(step["moves"], 1):
            for side in ("from", "to"):
                end = move[side]
                mol = mols[end["species"]]
                where = f"Step {number} move {index} {side}"
                if end.get("atom") is not None:
                    if end["atom"] >= mol.GetNumAtoms():
                        errors.append(f"{where}: atom {end['atom']} does not exist in {end['species']} "
                                      f"({mol.GetNumAtoms()} atoms, numbered from 0).")
                else:
                    i, j = end["bond"]
                    if max(i, j) >= mol.GetNumAtoms() or mol.GetBondBetweenAtoms(i, j) is None:
                        errors.append(f"{where}: bond {[i, j]} does not exist in {end['species']}.")
    return errors


# ---------------------------------------------------------------------------
# Move checks (reported, never blocking)
# ---------------------------------------------------------------------------

def _describe(end: dict, mol) -> str:
    if end.get("atom") is not None:
        return f"{end['species']} atom {end['atom']} ({mol.GetAtomWithIdx(end['atom']).GetSymbol()})"
    i, j = end["bond"]
    return f"{end['species']} bond {i}-{j}"


def _lone_pairs(atom) -> int:
    outer = Chem.GetPeriodicTable().GetNOuterElecs(atom.GetAtomicNum())
    nonbonding = outer - atom.GetFormalCharge() - atom.GetTotalValence() - atom.GetNumRadicalElectrons()
    return max(nonbonding // 2, 0)


def _move_checks(move: dict, mol) -> list[str]:
    checks: list[str] = []
    source = move["from"]
    if source.get("atom") is None:
        return checks
    atom = mol.GetAtomWithIdx(source["atom"])
    name = _describe(source, mol)
    if move.get("electrons", 2) == 2:
        if atom.GetFormalCharge() >= 0 and _lone_pairs(atom) == 0:
            checks.append(f"{name} has no lone pair or negative charge to donate; "
                          "start the arrow on a bond or on an atom that has one.")
    elif atom.GetNumRadicalElectrons() == 0:
        checks.append(f"{name} has no unpaired electron for a one-electron arrow.")
    return checks


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

@dataclass
class _Inst:
    uid: int
    species: str
    frag: Any
    row: int = 0


@dataclass
class _Drawing:
    cdxml: Any
    lint_cdxml: Any
    rows: list
    curves: list
    atoms: list
    notes: list = field(default_factory=list)


def _reach(atom: dict) -> float:
    plain = atom.get("symbol", "C") == "C" and not atom.get("charge") and not atom.get("isotope")
    return CARBON_REACH if plain else LABEL_REACH


def _place(inst: _Inst, left: float, row: int) -> float:
    """Put the structure's left edge at ``left`` and its centre on the arrow line; return its right edge."""
    frag = inst.frag
    R._shift_atoms(frag.atoms, left + R._bbox_width(frag.bbox) / 2.0 - frag.cx, -frag.cy)
    frag.bbox = R._fragment_bbox(frag.atoms)
    frag.cx, frag.cy = R._bbox_center(frag.bbox)
    inst.row = row
    return frag.bbox[2]


def _text_lines(step: dict) -> tuple[list[str], list[str]]:
    above = [normalize_condition_text(str(t)) for t in figure_draw._as_list(step.get("above"))]
    below = [normalize_condition_text(str(t)) for t in figure_draw._as_list(step.get("below"))]
    if step.get("yield") not in (None, ""):
        below.append(str(step["yield"]))
    return above, below


def _arrange(brief: dict, grounded: list[dict], width: float, gap_scale: float):
    """Place every structure and step arrow in rows; returns (rows, per-step instances, notes)."""
    bond = ACS_BOND_LENGTH
    frag_gap = bond * LAYOUT_FRAG_GAP_BONDS * gap_scale
    inter_gap = max(bond * LAYOUT_INTER_GAP_BONDS, LAYOUT_PLUS_GAP) * gap_scale
    limit = X0 + width
    by_id = {g["id"]: g for g in grounded}
    insts: list[_Inst] = []
    notes: list[str] = []

    def new(species: str) -> _Inst:
        item = by_id[species]
        label = str(item["label"]) if item["label"] else None
        inst = _Inst(len(insts), species, R._resolve_structure(StructureRef(id=species, smiles=item["smiles"], label=label)))
        insts.append(inst)
        return inst

    def place_group(row_items: list, ids: list[str], cursor: float, row: int) -> tuple[list[_Inst], float]:
        placed: list[_Inst] = []
        for position, species in enumerate(ids):
            if position:
                row_items.append({"t": "plus", "x": cursor - inter_gap / 2.0})
            inst = new(species)
            cursor = _place(inst, cursor, row) + inter_gap
            row_items.append({"t": "frag", "inst": inst})
            placed.append(inst)
        return placed, cursor

    rows: list[list[dict]] = []
    step_insts: list[dict] = []
    drawn: set[str] = set()
    previous_products: list[str] = []
    last_product: _Inst | None = None

    for number, step in enumerate(brief["steps"], 1):
        substrates, products = _as_ids(step["substrates"]), _as_ids(step["products"])
        above, below = _text_lines(step)
        arrow_len = max(max(R._estimate_text_width(above), R._estimate_text_width(below)) + 10.0, 5.0 * bond)
        product_widths = []
        for species in products:
            probe = R._resolve_structure(StructureRef(id=species, smiles=by_id[species]["smiles"]))
            product_widths.append(R._bbox_width(probe.bbox))
        after_arrow = 0.3 * frag_gap + arrow_len + frag_gap + sum(product_widths) + inter_gap * (len(products) - 1)

        chained = number > 1 and substrates == previous_products and len(previous_products) == 1 and last_product
        sub_insts: list[_Inst]
        if chained:
            row_items = rows[-1]
            cursor = last_product.frag.bbox[2] + inter_gap
            if cursor + after_arrow > limit and any(i["t"] == "arrow" for i in row_items):
                rows.append([])
                row_items = rows[-1]
                sub_insts, cursor = place_group(row_items, substrates, X0, len(rows) - 1)
                notes.append(f"species {substrates[0]} is drawn again at the start of row {len(rows)} "
                             "because the route does not fit on one row.")
            else:
                sub_insts = [last_product]
        else:
            rows.append([])
            row_items = rows[-1]
            for species in substrates:
                if species in drawn:
                    notes.append(f"species {species} is drawn again in step {number} (row {len(rows)}) because "
                                 "that step has more than one substrate or does not directly follow the previous one.")
            sub_insts, cursor = place_group(row_items, substrates, X0, len(rows) - 1)
        drawn.update(substrates)

        tail = cursor + 0.3 * frag_gap
        head = tail + arrow_len
        row_items.append({"t": "arrow", "tail": tail, "head": head, "above": above, "below": below,
                          "style": step.get("arrow", "solid")})
        prod_insts, cursor = place_group(row_items, products, head + frag_gap, len(rows) - 1)
        drawn.update(products)
        step_insts.append({"subs": dict(zip(substrates, sub_insts)), "prods": dict(zip(products, prod_insts))})
        previous_products = products
        last_product = prod_insts[0] if len(prod_insts) == 1 else None
    return rows, step_insts, notes


def _row_extent(row: list[dict]) -> tuple[float, float]:
    top = bottom = 0.0
    for item in row:
        if item["t"] == "frag":
            frag = item["inst"].frag
            top = min(top, frag.bbox[1])
            bottom = max(bottom, frag.bbox[3] + (20.0 if frag.ref.label else 0.0))
        elif item["t"] == "arrow":
            if item["above"]:
                lines = len(item["above"])
                top = min(top, -LAYOUT_BELOW_GAP - ((lines - 1) * R._LINE_ADVANCE + R._DESCENT) - R._CAP_HEIGHT)
            if item["below"]:
                lines = len(item["below"])
                bottom = max(bottom, LAYOUT_BELOW_GAP + R._CAP_HEIGHT + (lines - 1) * R._LINE_ADVANCE + R._DESCENT)
    return top, bottom


# ---------------------------------------------------------------------------
# Curved arrows
# ---------------------------------------------------------------------------

def _anchor(inst: _Inst, end: dict) -> tuple[tuple[float, float], float, set]:
    """Page position, how far an arrow stays off the atom, and the atoms the endpoint belongs to."""
    by_index = dict(enumerate(inst.frag.atoms))  # the renderer numbers atoms from 1; moves count from 0
    if end.get("atom") is not None:
        atom = by_index[end["atom"]]
        return (atom["x"], atom["y"]), (LABEL_STANDOFF if _reach(atom) == LABEL_REACH else CARBON_STANDOFF),             {(inst.uid, end["atom"])}
    i, j = end["bond"]
    a, b = by_index[i], by_index[j]
    return ((a["x"] + b["x"]) / 2.0, (a["y"] + b["y"]) / 2.0), 0.0, {(inst.uid, i), (inst.uid, j)}


def _bezier(p0, p3, side: float, scale: float):
    dx, dy = p3[0] - p0[0], p3[1] - p0[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy * side, ux * side
    height = min(max(0.45 * length, BULGE_MIN), BULGE_MAX) * scale
    control = height / 0.75
    p1 = (p0[0] + 0.2 * dx + nx * control, p0[1] + 0.2 * dy + ny * control)
    p2 = (p3[0] - 0.2 * dx + nx * control, p3[1] - 0.2 * dy + ny * control)
    return [p0, p1, p2, p3]


def _unit(dx: float, dy: float) -> tuple[float, float]:
    length = math.hypot(dx, dy) or 1.0
    return dx / length, dy / length


def _shape(src, src_r: float, dst, dst_r: float, side: float, scale: float):
    """Bezier from ``src`` to ``dst`` that starts and stops ``*_r`` away from the atoms, on the arc's own side."""
    ux, uy = _unit(dst[0] - src[0], dst[1] - src[1])
    length = math.hypot(dst[0] - src[0], dst[1] - src[1])
    r_src, r_dst = min(src_r, 0.3 * length), min(dst_r, 0.3 * length)
    start, end = (src[0] + ux * r_src, src[1] + uy * r_src), (dst[0] - ux * r_dst, dst[1] - uy * r_dst)
    points = _bezier(start, end, side, scale)
    if src_r or dst_r:
        # land on the atom's edge from the side the arc arrives on, not along the straight chord
        if src_r:
            vx, vy = _unit(points[1][0] - src[0], points[1][1] - src[1])
            start = (src[0] + vx * src_r, src[1] + vy * src_r)
        if dst_r:
            wx, wy = _unit(dst[0] - points[2][0], dst[1] - points[2][1])
            end = (dst[0] - wx * dst_r, dst[1] - wy * dst_r)
        points = _bezier(start, end, side, scale)
    return points


def _sample(points, count: int = SAMPLES):
    out = []
    for step in range(count + 1):
        t = step / count
        u = 1 - t
        out.append((
            u ** 3 * points[0][0] + 3 * u * u * t * points[1][0] + 3 * u * t * t * points[2][0] + t ** 3 * points[3][0],
            u ** 3 * points[0][1] + 3 * u * u * t * points[1][1] + 3 * u * t * t * points[2][1] + t ** 3 * points[3][1],
        ))
    return out


def _hits(points, atoms: list[dict], skip: set) -> list[dict]:
    found: dict[Any, dict] = {}
    samples = _sample(points)[1:-1]
    for atom in atoms:
        if atom["key"] in skip:
            continue
        if any(math.hypot(x - atom["x"], y - atom["y"]) < atom["reach"] for x, y in samples):
            found[atom["key"]] = atom
    return list(found.values())


def _label_obstacles(row: list[dict]) -> list[dict]:
    """The compound numbers under the structures, so an arrow does not run through them."""
    found = []
    for item in row:
        if item["t"] == "frag" and item["inst"].frag.ref.label:
            frag = item["inst"].frag
            found.append({"key": ("label", item["inst"].uid), "label": f"the label {frag.ref.label}",
                          "x": (frag.bbox[0] + frag.bbox[2]) / 2.0, "y": frag.bbox[3] + 11.0,
                          "reach": LABEL_OBSTACLE})
    return found


def _row_curves(brief: dict, step_insts: list[dict], rows: list[list[dict]], bulge: float) -> dict[int, list[dict]]:
    """Curved arrows in row-local coordinates, keyed by row."""
    atoms_by_row: dict[int, list[dict]] = {}
    for row_index, row in enumerate(rows):
        atoms_by_row[row_index] = [
            {"key": (item["inst"].uid, number), "label": f"{item['inst'].species} atom {number}",
             "x": a["x"], "y": a["y"], "reach": _reach(a)}
            for item in row if item["t"] == "frag" for number, a in enumerate(item["inst"].frag.atoms)
        ] + _label_obstacles(row)
    curves: dict[int, list[dict]] = {i: [] for i in range(len(rows))}
    for number, step in enumerate(brief["steps"], 1):
        subs = step_insts[number - 1]["subs"]
        for index, move in enumerate(step["moves"], 1):
            src_inst, dst_inst = subs[move["from"]["species"]], subs[move["to"]["species"]]
            (sx, sy), src_r, src_keys = _anchor(src_inst, move["from"])
            (tx, ty), dst_r, dst_keys = _anchor(dst_inst, move["to"])
            row = src_inst.row
            skip = src_keys | dst_keys
            centre = None
            if src_inst is dst_inst:
                pts = src_inst.frag.atoms
                centre = (sum(a["x"] for a in pts) / len(pts), sum(a["y"] for a in pts) / len(pts))
            best = None
            for height, scale in enumerate(HEIGHT_STEPS):
                for side in (-1.0, 1.0):
                    points = _shape((sx, sy), src_r, (tx, ty), dst_r, side, scale * bulge)
                    hits = len(_hits(points, atoms_by_row[row], skip))
                    mid = _sample(points)[SAMPLES // 2]
                    if centre is not None:
                        preference = -math.hypot(mid[0] - centre[0], mid[1] - centre[1])  # outside the molecule
                    else:
                        preference = mid[1]  # higher on the page (smaller y) first
                    key = (hits, height, preference)
                    if best is None or key < best[0]:
                        best = (key, points)
            curves[row].append({"step": number, "move": index, "electrons": move.get("electrons", 2),
                                "pts": best[1], "skip": skip})
    return curves


def _crossings(curves: list[dict], atoms: list[dict]) -> list[dict]:
    """Atoms a curved arrow passes through (other than its own endpoints)."""
    found = []
    for curve in curves:
        for atom in _hits(curve["pts"], atoms, curve["skip"]):
            found.append({"step": curve["step"], "move": curve["move"], "with": atom["label"]})
    return found


def _curve_xml(curve: dict, ids) -> str:
    p = curve["pts"]
    flat = " ".join(f"{x:.2f} {y:.2f}" for x, y in (p[0], p[0], p[1], p[2], p[3], p[3]))
    samples = _sample(p)
    xs, ys = [s[0] for s in samples], [s[1] for s in samples]
    head = "HalfLeft" if curve["electrons"] == 1 else "Full"
    return (f'<curve id="{ids.next()}" BoundingBox="{min(xs):.2f} {min(ys):.2f} {max(xs):.2f} {max(ys):.2f}" '
            f'Z="{ids.next()}" CurvePoints="{flat}" FillType="None" LineWidth="{ACS_LINE_WIDTH}" '
            f'ArrowheadHead="{head}" ArrowheadType="Solid" HeadSize="1000" '
            f'ArrowheadCenterSize="875" ArrowheadWidth="250"/>')


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def _draw(brief: dict, grounded: list[dict], width: float, gap_scale: float, bulge: float,
          numbers: bool) -> _Drawing:
    rows, step_insts, notes = _arrange(brief, grounded, width, gap_scale)
    local_curves = _row_curves(brief, step_insts, rows, bulge)

    # Row-local layout -> page coordinates: stack the rows, leaving room for the loops.
    title = brief.get("title")
    cursor = FIRST_ROW_TOP + (TITLE_ROOM if title else 0.0)
    offsets: list[float] = []
    for row_index, row in enumerate(rows):
        top, bottom = _row_extent(row)
        for curve in local_curves[row_index]:
            ys = [y for _, y in _sample(curve["pts"])]
            top, bottom = min(top, min(ys)), max(bottom, max(ys))
        offset = cursor - top
        offsets.append(offset)
        cursor = offset + bottom + ROW_GAP
        for item in row:
            if item["t"] == "frag":
                R._shift_atoms(item["inst"].frag.atoms, 0.0, offset)
                item["inst"].frag.bbox = R._fragment_bbox(item["inst"].frag.atoms)
        for curve in local_curves[row_index]:
            curve["pts"] = [(x, y + offset) for x, y in curve["pts"]]

    curves = [c for row_index in range(len(rows)) for c in local_curves[row_index]]
    atoms = [
        {"key": (item["inst"].uid, number), "label": f"{item['inst'].species} atom {number}",
         "x": a["x"], "y": a["y"], "reach": _reach(a)}
        for row in rows for item in row if item["t"] == "frag" for number, a in enumerate(item["inst"].frag.atoms)
    ] + [o for row in rows for o in _label_obstacles(row)]

    def build(with_numbers: bool):
        def make(ids) -> str:
            parts: list[str] = []
            if title:
                xml, _ = R._build_text_element([str(title)], X0, FIRST_ROW_TOP - 4.0, ids, justification="Left",
                                               use_formatting=False)
                parts.append(xml)
            for row_index, row in enumerate(rows):
                y = offsets[row_index]
                for item in row:
                    if item["t"] == "frag":
                        frag = item["inst"].frag
                        xml, _, _ = R._build_fragment(frag.atoms, frag.bonds, ids)
                        parts.append(xml)
                        if frag.ref.label:
                            label, _ = R._build_label_element(frag.ref.label, frag.cx, frag.bbox[3] + 14.0, ids)
                            parts.append(label)
                    elif item["t"] == "plus":
                        xml, _ = R._build_text_element(["+"], item["x"], y + 3.5, ids)
                        parts.append(xml)
                    else:
                        parts += _arrow_xml(item, y, ids)
            if with_numbers:
                for row in rows:
                    for item in row:
                        if item["t"] == "frag":
                            for number, a in enumerate(item["inst"].frag.atoms):
                                xml, _ = R._build_text_element([str(number)], a["x"] + 4.0, a["y"] - 4.0, ids,
                                                               justification="Left", use_formatting=False,
                                                               font_size=7)
                                parts.append(xml)
            parts += [_curve_xml(c, ids) for c in curves]
            return "\n".join(parts)
        return make

    # Shifted atoms are final; recompute fragment centres used for labels.
    for row in rows:
        for item in row:
            if item["t"] == "frag":
                frag = item["inst"].frag
                frag.cx, frag.cy = R._bbox_center(frag.bbox)

    cdxml = R.render_with(build(numbers))
    clean = R.render_with(build(False)) if numbers else cdxml
    return _Drawing(cdxml=cdxml, lint_cdxml=clean, rows=rows, curves=curves, atoms=atoms, notes=notes)


def _arrow_xml(item: dict, y: float, ids) -> list[str]:
    parts: list[str] = []
    style = item["style"]
    xml, _ = R._build_arrow(item["tail"], y, item["head"], y, ids, kind=R._arrow_kind(style))
    parts.append(xml)
    middle = (item["tail"] + item["head"]) / 2.0
    if item["above"]:
        below_baseline = (len(item["above"]) - 1) * R._LINE_ADVANCE + R._DESCENT
        xml, _ = R._build_text_element(item["above"], middle, y - LAYOUT_BELOW_GAP - below_baseline, ids)
        parts.append(xml)
    if item["below"]:
        xml, _ = R._build_text_element(item["below"], middle, y + LAYOUT_BELOW_GAP + R._CAP_HEIGHT, ids)
        parts.append(xml)
    return parts


def _move_report(brief: dict, mols: dict[str, Any]) -> tuple[list[dict], list[str]]:
    report: list[dict] = []
    warnings: list[str] = []
    for number, step in enumerate(brief["steps"], 1):
        for index, move in enumerate(step["moves"], 1):
            checks = _move_checks(move, mols[move["from"]["species"]])
            report.append({
                "step": number, "move": index,
                "from": _describe(move["from"], mols[move["from"]["species"]]),
                "to": _describe(move["to"], mols[move["to"]["species"]]),
                "electrons": move.get("electrons", 2),
                "checks": checks,
            })
            warnings += [f"Step {number} move {index}: {text}" for text in checks]
    return report, warnings


def draw_mechanism(brief: dict, output_path: str | None, render: bool) -> dict:
    """Draw a mechanism; called by draw_figure for ``kind: mechanism``."""
    errors = _validate(brief)
    if errors:
        return figure_draw._failure(errors, kind="mechanism")
    grounded, errors = figure_draw._ground(brief["species"])
    if errors:
        return figure_draw._failure(errors, kind="mechanism")
    mols = {g["id"]: Chem.MolFromSmiles(g["smiles"]) for g in grounded}
    errors = _index_errors(brief, mols)
    if errors:
        return figure_draw._failure(errors, kind="mechanism")
    smiles = {g["id"]: g["smiles"] for g in grounded}

    balance, warnings = figure_draw._check_balance(brief, smiles)
    moves, move_warnings = _move_report(brief, mols)
    warnings += move_warnings
    notes: list[str] = []
    used = {i for step in brief["steps"] for side in ("substrates", "products") for i in _as_ids(step[side])}
    for item in grounded:
        if item["id"] not in used:
            notes.append(f"species {item['id']} is not used in any step, so it is not drawn.")
    numbers = bool(brief.get("show_atom_numbers"))
    if numbers:
        warnings.append("The atom numbers are drawn so the moves can be checked; "
                        "remove show_atom_numbers for the final figure.")

    budget = float(brief.get("max_width") or figure_draw.DEFAULT_MAX_WIDTH)
    width, gap_scale, bulge = budget, 1.0, 1.0
    try:
        drawing = _draw(brief, grounded, width, gap_scale, bulge, numbers)
        issues = figure_lint.lint_cdxml(drawing.lint_cdxml, max_width=budget)
        crossings = _crossings(drawing.curves, drawing.atoms)
        relayout = None
        if issues or crossings:
            first = {"issues": issues, "crossings": crossings}
            new_width, new_gap, changed = figure_draw._relayout(issues, width, gap_scale)
            if crossings:
                if new_gap == gap_scale:
                    new_gap = round(gap_scale * figure_draw.RELAYOUT_GAP_SCALE, 2)
                    changed.append(f"widened the gaps between structures by x{figure_draw.RELAYOUT_GAP_SCALE:g}")
                bulge = RELAYOUT_BULGE
                changed.append(f"raised the arrow loops by x{RELAYOUT_BULGE:g}")
            if changed:
                drawing = _draw(brief, grounded, new_width, new_gap, bulge, numbers)
                issues = figure_lint.lint_cdxml(drawing.lint_cdxml, max_width=budget)
                crossings = _crossings(drawing.curves, drawing.atoms)
                relayout = {"changed": changed, "first_issues": first["issues"],
                            "first_crossings": first["crossings"]}
    except Exception as exc:
        return figure_draw._failure([f"The layout failed: {exc}"], kind="mechanism", warnings=warnings)

    try:
        target = artifact_safety.resolve_destination(
            source=None, output_path=output_path, tag="figure", suffix=".cdxml")
        with artifact_safety.staging_file(target) as stage:
            stage.write_text(str(drawing.cdxml), encoding="utf-8", newline="")
            artifact_safety.publish_file(stage, target)
    except ValueError as exc:  # includes OutputExistsError
        return figure_draw._failure([str(exc)], kind="mechanism", warnings=warnings)

    notes += drawing.notes
    for issue in issues:
        warnings.append(f"Layout check: {issue['message']}")
    for crossing in crossings:
        warnings.append(f"Step {crossing['step']} move {crossing['move']}: the arrow passes through "
                        f"{crossing['with']}; move the species apart or reorder them.")
    readback = figure_draw._readback(target, grounded, used, getattr(drawing.cdxml, "chemistry_validation", None))
    if readback["status"] != "matched":
        warnings.append(f"The saved file does not match the brief: missing {readback['missing']}, "
                        f"{readback['unexpected']} unexpected structure(s).")
    if readback["fragment_roundtrip"] != "preserved":
        warnings.append(f"Per-structure round-trip is {readback['fragment_roundtrip']}: "
                        "a structure may have changed while drawing.")
    notes.append("The curved arrows are drawn exactly as listed in moves; the tool checks lone pairs and atom "
                 "balance but does not decide whether the mechanism is chemically right.")

    native: dict[str, Any]
    produced = [target]
    if not render:
        native = {"status": "not_run", "reason": "native rendering was not requested"}
        notes.append("The drawing has not been rendered natively; look at a render before treating it as final.")
    else:
        png = figure_draw._png_destination(target)
        try:
            figure_draw._render_png(str(target), str(png))
            native = {"status": "rendered", "png_path": str(png)}
            produced.append(png)
        except Exception as exc:
            native = {"status": "not_run", "reason": str(exc)}
            notes.append("Native rendering did not run, so the drawing is an unrendered draft.")

    species = []
    for g in grounded:
        entry = {k: g[k] for k in ("id", "label", "name", "smiles", "source")}
        entry["atoms"] = ", ".join(f"{a.GetIdx()} {a.GetSymbol()}" for a in mols[g["id"]].GetAtoms())
        species.append(entry)
    report = {
        "ok": True,
        "operation": "draw_figure",
        "kind": "mechanism",
        "output_path": str(target),
        "species": species,
        "steps": balance,
        "moves": moves,
        "arrows": {"count": len(drawing.curves), "crossings": crossings, "relayout": relayout},
        "lint": {"issues": issues, "relayout": relayout, "max_width": budget},
        "readback": readback,
        "native": native,
        "checks_passed": (not issues and not crossings and readback["status"] == "matched"
                          and readback["fragment_roundtrip"] == "preserved"),
        "notes": notes,
        "warnings": warnings,
    }
    return artifact_safety.with_artifacts(report, produced)


__all__ = ["MECH_KEYS", "draw_mechanism"]
