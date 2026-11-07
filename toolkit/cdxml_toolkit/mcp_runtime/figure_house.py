"""Apply a house style's drawing conventions to a scheme drawn by ``draw_figure``.

The scheme is drawn at ACS geometry first; this module then edits the CDXML:
compound-number face and colour, where the yield goes, which groups become
abbreviation labels, substrate colours and the colour of bonds formed in a step.
The measurement preset is applied afterwards by ``figure_draw.styled``. Every
convention that is not applied is reported with the reason, never guessed.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from typing import Any

from rdkit import Chem
from rdkit.Chem import rdDepictor

from ..chemistry_semantics import read_fragments, semantic_key
from ..constants import ACS_LABEL_FACE, ACS_LABEL_FONT, ACS_LABEL_SIZE
from ..chemdraw.style_presets import style_preset
from ..publication.house_styles import (
    ABBREVIATIONS, APPLIED_FIGURE_CONVENTIONS, CONVENTION_KEYS, HouseStyle, group_name,
)
from ..render import renderer

_YIELD_VALUE = re.compile(r"\s*\(?\s*(\d+(?:\.\d+)?)\s*%?\s*(?:yield)?\s*\)?\s*", re.IGNORECASE)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def format_yield(text: str, template: str | None) -> str:
    """``template`` filled with the number of a yield such as "85%"; other text is kept."""
    match = _YIELD_VALUE.fullmatch(str(text))
    if not template or not match:
        return str(text)
    return template.replace("{value}", match.group(1))


def step_yield(step: Mapping, house: HouseStyle | None) -> str | None:
    """The yield text drawn under the arrow, or None when the house style moves it."""
    raw = step.get("yield")
    if raw in (None, ""):
        return None
    if house is None:
        return str(raw)
    if house.convention("yield_placement", "under_arrow") != "under_arrow":
        return None
    return format_yield(str(raw), house.convention("yield_format"))


def split_conditions(above: list[str], below: list[str], house: HouseStyle | None) -> tuple[list, list]:
    split = house.convention("conditions_split") if house else None
    if split == "all_above":
        return above + below, []
    if split == "all_below":
        return [], above + below
    return above, below


def final_products(brief: Mapping) -> list[str]:
    substrates = {s for step in brief["steps"] for s in _as_list(step.get("substrates"))}
    out: list[str] = []
    for step in brief["steps"]:
        for p in _as_list(step.get("products")):
            if p not in substrates and p not in out:
                out.append(p)
    return out


def add_highlight_fills(brief: dict, grounded: list[dict], house: HouseStyle | None) -> str | None:
    """Ask the ring_fills decoration for the largest ring of each final product."""
    color = house.convention("highlight_fill") if house else None
    if not color:
        return None
    smiles = {g["id"]: g["smiles"] for g in grounded}
    filled = 0
    for entry in brief["species"]:
        if not isinstance(entry, dict) or entry.get("id") not in final_products(brief) or entry.get("ring_fills"):
            continue
        mol = Chem.MolFromSmiles(smiles.get(str(entry["id"]), ""))
        rings = list(mol.GetRingInfo().AtomRings()) if mol is not None else []
        if rings:
            largest = max(range(len(rings)), key=lambda i: len(rings[i]))
            entry["ring_fills"] = [{"ring_index": largest, "color": color}]
            filled += 1
    return "highlight_fill" if filled else None


# --- document helpers ----------------------------------------------------------

class _Colors:
    """Colour-table indices, adding entries as needed (entry k is index k + 2)."""

    def __init__(self, root: ET.Element):
        self.table = root.find("colortable")
        if self.table is None:
            self.table = ET.Element("colortable")
            root.insert(0, self.table)

    def index(self, hex_color: str) -> str:
        text = hex_color.lstrip("#")
        rgb = tuple(round(int(text[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4))
        if rgb == (0.0, 0.0, 0.0):
            return "0"
        for k, entry in enumerate(self.table.findall("color")):
            if tuple(round(float(entry.get(c, "0")), 4) for c in "rgb") == rgb:
                return str(k + 2)
        ET.SubElement(self.table, "color", {c: f"{v:g}" for c, v in zip("rgb", rgb)})
        return str(len(self.table.findall("color")) + 1)


def _text_of(t: ET.Element) -> str:
    return "".join(s.text or "" for s in t.iter("s"))


def _point(el: ET.Element) -> tuple[float, float]:
    x, y = (el.get("p") or "0 0").split()[:2]
    return float(x), float(y)


def _species_fragments(root: ET.Element, cdxml: str, grounded: list[dict]):
    """(species id, fragment element, fragment mol) for every drawn species, in document order."""
    page = root.find("page")
    frag_els = {f.get("id", ""): f for f in page.iter("fragment")}
    key_to_ids: dict[str, list[str]] = {}
    for g in grounded:
        mol = Chem.MolFromSmiles(g["smiles"])
        if mol is not None:
            key_to_ids.setdefault(semantic_key(mol), []).append(g["id"])
    seen: dict[str, int] = {}
    out = []
    for frag_id, frag_mol in read_fragments(cdxml):
        el = frag_els.get(str(frag_id))
        ids = key_to_ids.get(semantic_key(frag_mol), []) if el is not None else []
        if not ids:
            continue
        key = semantic_key(frag_mol)
        n = seen.get(key, 0)
        seen[key] = n + 1
        out.append((ids[min(n, len(ids) - 1)], el, frag_mol))
    return out


def _atom_nodes(frag_el: ET.Element, frag_mol: Any, src_mol: Any) -> list[ET.Element] | None:
    """The drawn <n> of every atom of the species SMILES (by substructure match and position)."""
    nodes = [n for n in frag_el.findall("n") if n.get("NodeType") != "ExternalConnectionPoint"]
    if not nodes or frag_mol is None or src_mol is None or not frag_mol.GetNumConformers():
        return None
    match = frag_mol.GetSubstructMatch(src_mol)
    if len(match) != src_mol.GetNumAtoms():
        return None
    conf = frag_mol.GetConformer()
    out = []
    for idx in match:
        pos = conf.GetAtomPosition(idx)
        x, y = pos.x / 65536.0, -pos.y / 65536.0
        out.append(min(nodes, key=lambda n: (_point(n)[0] - x) ** 2 + (_point(n)[1] - y) ** 2))
    return out


def _bond_elements(frag_el: ET.Element) -> dict[frozenset, ET.Element]:
    return {frozenset((b.get("B"), b.get("E"))): b for b in frag_el.findall("b")}


def _frag_box(frag_el: ET.Element) -> tuple[float, float, float, float]:
    pts = [_point(n) for n in frag_el.findall("n")]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _label_of(page: ET.Element, frag_el: ET.Element, label: str | None) -> ET.Element | None:
    """The compound-number <t> drawn under a fragment."""
    if not label:
        return None
    x1, y1, x2, y2 = _frag_box(frag_el)
    atom_labels = {id(t) for f in page.iter("fragment") for t in f.iter("t")}
    candidates = [t for t in page.iter("t") if id(t) not in atom_labels and _text_of(t) == label
                  and x1 - 8 <= _point(t)[0] <= x2 + 8 and _point(t)[1] > y1]
    return min(candidates, key=lambda t: abs(_point(t)[1] - y2), default=None)


def _paint(el: ET.Element, index: str) -> None:
    el.set("color", index)
    for s in el.iter("s"):
        s.set("color", index)


# --- conventions ---------------------------------------------------------------

# Arial cap height as a fraction of the font size, to turn a measured bond/cap ratio into points.
_CAP_HEIGHT_EM = 0.716
_LABEL_SIZE_RANGE = (6.0, 14.0)
_ARROW_BONDS_RANGE = (3.0, 16.0)


def measured_arrow_bonds(house: HouseStyle | None) -> float | None:
    """The shortest arrow in bond lengths from the card's measurements, or None."""
    value = (house.measured or {}).get("arrow_length_over_bond_length") if house else None
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return min(max(float(value), _ARROW_BONDS_RANGE[0]), _ARROW_BONDS_RANGE[1])


def apply_measured_geometry(cdxml: Any, house: HouseStyle, slug: str) -> tuple[Any, list[str], list[str]]:
    """Line width, bold width and atom-label size from the card's ``measured`` ratios.

    The preset fixes the bond length; the ratios measured on the published figures then set
    the bond line width, the wedge width and the atom-label size relative to it.
    """
    measured = house.measured or {}
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    bond = float(root.get("BondLength") or style_preset(slug)["attributes"]["BondLength"])
    applied: list[str] = []
    skipped: list[str] = []

    def ratio(key: str) -> float | None:
        value = measured.get(key)
        return float(value) if isinstance(value, (int, float)) and value > 0 else None

    line = ratio("line_width_over_bond_length")
    if line:
        width = min(max(line * bond, 0.3), 3.0)
        old = root.get("LineWidth")
        root.set("LineWidth", f"{width:.3g}")
        for el in root.iter():
            if el is not root and "LineWidth" in el.attrib and el.get("LineWidth") == old:
                el.set("LineWidth", f"{width:.3g}")
        applied.append(f"measured.line_width={width:.3g} pt")
    bold = ratio("bold_width_over_bond_length")
    if bold:
        root.set("BoldWidth", f"{min(max(bold * bond, 0.8), 6.0):.3g}")
        applied.append(f"measured.bold_width={root.get('BoldWidth')} pt")
    cap = ratio("bond_length_over_cap_height")
    if cap:
        size = min(max(bond / cap / _CAP_HEIGHT_EM, _LABEL_SIZE_RANGE[0]), _LABEL_SIZE_RANGE[1])
        old_size = root.get("LabelSize")
        text_size = f"{size:.3g}"
        root.set("LabelSize", text_size)
        # Atom labels are the text inside nodes; compound numbers and conditions keep their size.
        for node in root.iter("n"):
            for run in node.iter("s"):
                if old_size is None or run.get("size") in (None, old_size):
                    run.set("size", text_size)
        applied.append(f"measured.atom_label_size={text_size} pt")
    if measured_arrow_bonds(house):
        applied.append(f"measured.arrow_length>={measured_arrow_bonds(house):.3g} bonds")
    if not applied:
        return cdxml, applied, skipped
    wrapped = renderer._ValidatedCDXML('<?xml version="1.0" encoding="UTF-8" ?>\n'
                                       + ET.tostring(root, encoding="unicode"))
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped, applied, skipped


# Curved-arrow width as a multiple of the preset's bond line width.
_ARROW_WEIGHTS = {"thin": 0.75, "bond": 1.0, "bold": 1.5}


def apply_figure_type_conventions(cdxml: Any, house: HouseStyle, figure_type: str,
                                  slug: str) -> tuple[Any, list[str], list[str]]:
    """Apply a card's ``figure_types`` section to a styled drawing; (cdxml, applied, skipped).

    Mechanisms take ``curved_arrow_color`` and ``curved_arrow_weight`` on their curved arrows;
    catalytic cycles take ``cycle_arrow_color`` on the cycle arrows. Every other convention of
    the section is guidance for whoever finishes the figure and is listed as skipped.
    """
    section = house.figure_types.get(figure_type) or {}
    conventions = {k: v for k, v in (section.get("conventions") or {}).items() if v is not None}
    if not section:
        return cdxml, [], [f"{house.slug} describes no {figure_type} figures; only its base preset was applied"]
    applied: list[str] = []
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    colors = _Colors(root)
    width = float(root.get("LineWidth") or style_preset(slug)["attributes"]["LineWidth"])
    if figure_type == "mechanism":
        curves = list(root.iter("curve"))
        color = conventions.get("curved_arrow_color")
        if color and curves:
            index = colors.index(color)
            for curve in curves:
                curve.set("color", index)
            applied.append(f"mechanism.curved_arrow_color={color}")
        weight = conventions.get("curved_arrow_weight")
        if weight in _ARROW_WEIGHTS and curves:
            for curve in curves:
                curve.set("LineWidth", f"{width * _ARROW_WEIGHTS[weight]:g}")
            applied.append(f"mechanism.curved_arrow_weight={weight}")
    elif figure_type == "catalytic_cycle":
        color = conventions.get("cycle_arrow_color")
        arrows = list(root.iter("arrow"))
        if color and arrows:
            index = colors.index(color)
            for arrow in arrows:
                arrow.set("color", index)
            applied.append(f"catalytic_cycle.cycle_arrow_color={color}")
    done = {entry.split("=", 1)[0].split(".", 1)[1] for entry in applied}
    tool_keys = set(APPLIED_FIGURE_CONVENTIONS.get(figure_type, ()))
    skipped = [f"{figure_type}.{key}={value}: guidance for finishing the figure, not drawn by the tool"
               for key, value in conventions.items() if key not in done and key not in tool_keys]
    skipped += [f"{figure_type}.{key}: nothing to apply it to in this drawing"
                for key in conventions if key in tool_keys and key not in done]
    if not applied:
        return cdxml, applied, skipped
    wrapped = renderer._ValidatedCDXML('<?xml version="1.0" encoding="UTF-8" ?>\n'
                                       + ET.tostring(root, encoding="unicode"))
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped, applied, skipped


def apply_house_conventions(cdxml: Any, brief: Mapping, grounded: list[dict],
                            house: HouseStyle) -> tuple[Any, list[str], list[str], list[str]]:
    """Edit the drawn scheme; returns (cdxml, applied, skipped reasons, warnings)."""
    applied: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []
    root = ET.fromstring(str(cdxml))
    page = root.find("page")
    colors = _Colors(root)
    labels = {g["id"]: (str(g["label"]) if g.get("label") else None) for g in grounded}
    smiles = {g["id"]: g["smiles"] for g in grounded}
    drawn = _species_fragments(root, str(cdxml), grounded)
    first: dict[str, tuple] = {}
    for sp_id, el, mol in drawn:
        first.setdefault(sp_id, (el, mol))
    used_ids = [int(v) for el in root.iter() for v in [el.get("id")] if v and v.isdigit()]
    ids = renderer._IDGen(max(used_ids, default=1000) + 1)

    # Compound numbers: face and colour.
    face = house.convention("compound_label_face")
    label_color = house.convention("compound_label_color")
    label_els = [(sp_id, _label_of(page, el, labels.get(sp_id))) for sp_id, el, _ in drawn]
    label_els = [(sp_id, t) for sp_id, t in label_els if t is not None]
    if face in ("bold", "plain"):
        for _, t in label_els:
            for s in t.iter("s"):
                s.set("face", "1" if face == "bold" else "0")
        applied.append(f"compound_label_face={face}")
    if label_color and label_color.upper() != "#000000":
        index = colors.index(label_color)
        for _, t in label_els:
            _paint(t, index)
        applied.append("compound_label_color")
    if house.convention("compound_label_italic_suffix"):
        skipped.append("compound_label_italic_suffix: not applied yet; labels keep one face")

    # Yield placement.
    placement = house.convention("yield_placement", "under_arrow")
    template = house.convention("yield_format")
    yields = [(n, step) for n, step in enumerate(brief["steps"], 1) if step.get("yield") not in (None, "")]
    if placement == "under_arrow":
        if yields and house.convention("yield_placement") == "under_arrow":
            applied.append("yield_placement=under_arrow")
        if yields and template:
            applied.append("yield_format")
    elif yields:
        label_by_id = dict(label_els)
        for number, step in yields:
            text = format_yield(str(step["yield"]), template)
            product = _as_list(step.get("products"))[0]
            if product not in first:
                warnings.append(f"Step {number}: the product is not drawn, so its yield {text} was not placed.")
                continue
            frag_el = first[product][0]
            label_t = label_by_id.get(product)
            if placement.startswith("after_product_label") and label_t is not None:
                if placement == "after_product_label_parenthesised":
                    suffix = " " + (text if text.startswith("(") else f"({text})")
                else:
                    suffix = house.convention("yield_separator", ", ") + text
                last = list(label_t.iter("s"))[-1]
                run = ET.SubElement(label_t, "s", dict(last.attrib))
                run.set("face", "0")
                run.text = suffix
                _resize_text_box(label_t)
                continue
            if label_t is not None:
                x, y = _point(label_t)
                y += renderer._LINE_ADVANCE
            else:
                x1, _, x2, y2 = _frag_box(frag_el)
                x, y = (x1 + x2) / 2.0, y2 + 14.0
                if placement.startswith("after_product_label"):
                    skipped.append(f"step {number}: the product has no label, so the yield is drawn under it")
            xml, _ = renderer._build_text_element([text], x, y, ids, use_formatting=False)
            new_t = ET.fromstring(xml)
            if label_t is not None:
                for s in new_t.iter("s"):
                    s.set("face", "0")
            page.append(new_t)
        applied.append(f"yield_placement={placement}")

    # Colours of substrates and of the bonds formed in each step.
    substrate_colors = house.convention("substrate_colors")
    if substrate_colors:
        made = set(final_products(brief)) | {p for st in brief["steps"] for p in _as_list(st.get("products"))}
        painted: set[str] = set()
        for step in brief["steps"]:
            for i, sp_id in enumerate(_as_list(step.get("substrates"))):
                if i >= len(substrate_colors) or sp_id in made or sp_id in painted or sp_id not in first:
                    continue
                index = colors.index(substrate_colors[i])
                frag_el = first[sp_id][0]
                for el in list(frag_el.findall("n")) + list(frag_el.findall("b")):
                    _paint(el, index)
                painted.add(sp_id)
        applied.append("substrate_colors")
    new_bond_color = house.convention("new_bond_color")
    if new_bond_color:
        coloured = _color_new_bonds(brief, smiles, first, colors.index(new_bond_color), warnings)
        if coloured:
            applied.append("new_bond_color")
        else:
            skipped.append("new_bond_color: no formed bond could be mapped; bonds left black")

    # Reagent text colour.
    reagent_color = house.convention("reagent_text_color")
    if reagent_color and reagent_color.upper() != "#000000":
        index = colors.index(reagent_color)
        texts = {t.get("id"): t for t in page.findall("t")}
        for step_el in root.iter("step"):
            for attr in ("ReactionStepObjectsAboveArrow", "ReactionStepObjectsBelowArrow"):
                for tid in (step_el.get(attr) or "").split():
                    if tid in texts:
                        _paint(texts[tid], index)
        applied.append("reagent_text_color")

    if house.convention("show_plus_sign") is False:
        for t in [t for t in page.findall("t") if _text_of(t).strip() == "+"]:
            page.remove(t)
        applied.append("show_plus_sign=false")
    elif house.convention("show_plus_sign") is True:
        applied.append("show_plus_sign=true")
    if reagent_color and reagent_color.upper() == "#000000":
        applied.append("reagent_text_color=#000000")
    layout = house.convention("substrate_layout")
    if layout and any(len(_as_list(st.get("substrates"))) > 1 for st in brief["steps"]):
        applied.append(f"substrate_layout={layout}")

    # abbreviate_groups is applied by apply_species_styling, after the brief's own colours.

    if house.convention("aromatic_rings") == "circle":
        skipped.append("aromatic_rings=circle: rings are drawn as Kekule structures")
    if house.convention("conditions_split") in ("all_above", "all_below"):
        applied.append(f"conditions_split={house.convention('conditions_split')}")
    if house.convention("conditions_split") == "reagents_above_solvent_below":
        skipped.append("conditions_split: the brief's above/below lines are kept as given")

    for key in CONVENTION_KEYS:
        if house.conventions.get(key) is None:
            skipped.append(f"{key}: not specified by the card")
    text = '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")
    wrapped = renderer._ValidatedCDXML(text)
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped, applied, skipped, warnings


SPECIES_STYLE_KEYS = ("color", "atom_colors", "bond_colors", "abbreviate")
FACE_BITS = {"bold": 1, "italic": 2}


def species_style_errors(entry: Mapping) -> list[str]:
    """Problems with a species' colour and abbreviation keys, for the brief check."""
    ident = entry.get("id")
    errors: list[str] = []

    def bad_color(value: Any) -> bool:
        return not (isinstance(value, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", value))

    if "color" in entry and bad_color(entry["color"]):
        errors.append(f"Species {ident}: color must be a hex colour like #D55E00.")
    for key, item_key in (("atom_colors", "atoms"), ("bond_colors", "bonds")):
        for item in _as_list(entry.get(key)):
            if not isinstance(item, Mapping) or bad_color(item.get("color")):
                errors.append(f"Species {ident}: every {key} entry needs a hex color.")
                continue
            members = item.get(item_key)
            if item_key == "atoms":
                ok = isinstance(members, list) and members and all(isinstance(i, int) for i in members)
            else:
                ok = isinstance(members, list) and members and all(
                    isinstance(p, list) and len(p) == 2 and all(isinstance(i, int) for i in p) for p in members)
            if not ok:
                shape = "atom indices" if item_key == "atoms" else "[i, j] pairs of atom indices"
                errors.append(f"Species {ident}: {key}.{item_key} must be a list of {shape} (SMILES order, from 0).")
    if "abbreviate" in entry:
        groups = entry["abbreviate"]
        if not isinstance(groups, list):
            errors.append(f"Species {ident}: abbreviate must be a list of group names, or [] for none.")
        else:
            bad = [g for g in groups if group_name(str(g)) not in ABBREVIATIONS]
            if bad:
                errors.append(f"Species {ident}: abbreviate names unknown groups {bad}; known: {', '.join(ABBREVIATIONS)}")
    return errors


def condition_line_errors(line: Any, where: str) -> list[str]:
    """A condition line is text, a run {text, color?, bold?, italic?} or a list of runs."""
    if isinstance(line, str):
        return []
    runs = line if isinstance(line, list) else [line]
    errors = []
    for run in runs:
        if not isinstance(run, Mapping) or not isinstance(run.get("text"), str) or not run["text"]:
            errors.append(f"{where}: a styled condition run needs a non-empty text.")
            continue
        unknown = sorted(set(run) - {"text", "color", "bold", "italic"})
        if unknown:
            errors.append(f"{where}: unknown keys {unknown} in a condition run.")
        color = run.get("color")
        if color is not None and not (isinstance(color, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", color)):
            errors.append(f"{where}: a condition run colour must be hex like #1F4E9E.")
    return errors


def condition_text(line: Any) -> str:
    """The plain text of a condition line."""
    if isinstance(line, str):
        return line
    runs = line if isinstance(line, list) else [line]
    return "".join(str(run.get("text", "")) for run in runs if isinstance(run, Mapping))


def _styled_runs(brief: Mapping) -> list[Mapping]:
    out = []
    for step in brief.get("steps") or []:
        for side in ("above", "below"):
            for line in _as_list(step.get(side)):
                if isinstance(line, str):
                    continue
                for run in (line if isinstance(line, list) else [line]):
                    if isinstance(run, Mapping) and (run.get("color") or run.get("bold") or run.get("italic")):
                        out.append(run)
    return out


def _style_text_span(t: ET.Element, run: Mapping, colors: "_Colors", done: set) -> bool:
    """Colour or set the face of the first not yet styled occurrence of ``run['text']`` in ``t``."""
    runs = list(t.findall("s"))
    text = "".join(s.text or "" for s in runs)
    # A long line may have been broken after a comma, so any whitespace matches any whitespace.
    pattern = r"\s+".join(re.escape(part) for part in str(run["text"]).split())
    for found in re.finditer(pattern, text):
        key = (id(t), found.start())
        if key in done:
            continue
        done.add(key)
        start, end = found.span()
        new_runs: list[ET.Element] = []
        pos = 0
        for s in runs:
            value = s.text or ""
            a, b = pos, pos + len(value)
            pos = b
            cuts = sorted({a, b, min(max(start, a), b), min(max(end, a), b)})
            for lo, hi in zip(cuts, cuts[1:]):
                piece = ET.Element("s", dict(s.attrib))
                piece.text = value[lo - a:hi - a]
                if start <= lo and hi <= end:
                    face = int(piece.get("face") or 0)
                    for name, bit in FACE_BITS.items():
                        if run.get(name):
                            face |= bit
                    piece.set("face", str(face))
                    if run.get("color"):
                        piece.set("color", colors.index(run["color"]))
                new_runs.append(piece)
        for s in runs:
            t.remove(s)
        for piece in new_runs:
            t.append(piece)
        return True
    return False


def apply_species_styling(cdxml: Any, brief: Mapping, grounded: list[dict],
                          house: HouseStyle | None = None) -> tuple[Any, list[str], list[str]]:
    """The brief's own colours, abbreviations and condition-text runs; returns (cdxml, applied, warnings).

    Runs after the house conventions so a colour the brief asks for wins over the card's.
    Abbreviations come last because they replace atoms that were painted: a species'
    ``abbreviate`` list replaces the card's ``abbreviate_groups`` for that species.
    """
    species = {str(sp.get("id")): sp for sp in brief.get("species") or [] if isinstance(sp, Mapping)}
    card_groups = list(house.convention("abbreviate_groups") or []) if house is not None else []
    styled_runs = _styled_runs(brief)
    wants_paint = any(any(k in sp for k in ("color", "atom_colors", "bond_colors")) for sp in species.values())
    wants_abbrev = bool(card_groups) or any("abbreviate" in sp for sp in species.values())
    if not (wants_paint or wants_abbrev or styled_runs):
        return cdxml, [], []
    applied: list[str] = []
    warnings: list[str] = []
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    page = root.find("page")
    colors = _Colors(root)
    smiles = {g["id"]: g["smiles"] for g in grounded}
    drawn = _species_fragments(root, str(cdxml), grounded) if (wants_paint or wants_abbrev) else []
    used_ids = [int(v) for el in root.iter() for v in [el.get("id")] if v and v.isdigit()]
    ids = renderer._IDGen(max(used_ids, default=1000) + 1)

    painted = 0
    for sp_id, frag_el, frag_mol in drawn:
        sp = species.get(sp_id) or {}
        if not any(k in sp for k in ("color", "atom_colors", "bond_colors")):
            continue
        if sp.get("color"):
            index = colors.index(sp["color"])
            for el in list(frag_el.findall("n")) + list(frag_el.findall("b")):
                _paint(el, index)
        if sp.get("atom_colors") or sp.get("bond_colors"):
            src = Chem.MolFromSmiles(smiles[sp_id])
            nodes = _atom_nodes(frag_el, frag_mol, src)
            if nodes is None:
                warnings.append(f"Species {sp_id}: the drawn structure could not be matched, so atom_colors "
                                "and bond_colors were not applied.")
            else:
                bonds = _bond_elements(frag_el)
                n_atoms = len(nodes)
                for item in sp.get("atom_colors") or []:
                    index = colors.index(item["color"])
                    atoms = [i for i in item["atoms"] if 0 <= i < n_atoms]
                    if len(atoms) < len(item["atoms"]):
                        warnings.append(f"Species {sp_id}: atom_colors names atoms outside 0..{n_atoms - 1}.")
                    for i in atoms:
                        _paint(nodes[i], index)
                    # A bond between two coloured atoms takes their colour, as in a highlighted fragment.
                    chosen = {nodes[i].get("id") for i in atoms}
                    for pair, b in bonds.items():
                        if pair <= chosen and len(pair) == 2:
                            _paint(b, index)
                for item in sp.get("bond_colors") or []:
                    index = colors.index(item["color"])
                    for i, j in item["bonds"]:
                        b = None
                        if 0 <= i < n_atoms and 0 <= j < n_atoms:
                            b = bonds.get(frozenset((nodes[i].get("id"), nodes[j].get("id"))))
                        if b is None:
                            warnings.append(f"Species {sp_id}: atoms {i} and {j} are not bonded.")
                            continue
                        _paint(b, index)
        painted += 1
    if painted:
        applied.append(f"species colours ({painted} structures)")

    if styled_runs:
        texts = list(page.findall("t"))
        done: set = set()
        missing = [run["text"] for run in styled_runs
                   if not any(_style_text_span(t, run, colors, done) for t in texts)]
        applied.append(f"condition text runs ({len(styled_runs) - len(missing)} styled)")
        for text in missing:
            warnings.append(f"The condition run {text!r} was not found in the drawn text, so it is unstyled.")

    if wants_abbrev:
        count = 0
        from_card = False
        for sp_id, frag_el, frag_mol in drawn:
            sp = species.get(sp_id) or {}
            groups = sp["abbreviate"] if "abbreviate" in sp else card_groups
            from_card = from_card or ("abbreviate" not in sp and bool(card_groups))
            if not groups:
                continue
            src = Chem.MolFromSmiles(smiles[sp_id])
            nodes = _atom_nodes(frag_el, frag_mol, src)
            if nodes is None:
                warnings.append(f"Species {sp_id}: the drawn structure could not be matched, so no group was abbreviated.")
                continue
            count += _abbreviate(frag_el, src, nodes, [str(g) for g in groups], ids)
        if from_card:
            applied.append(f"abbreviate_groups ({count} contracted)")
        else:
            applied.append(f"species abbreviations ({count} contracted)")

    text = '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")
    wrapped = renderer._ValidatedCDXML(text)
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped, applied, warnings


BOX_KEYS = {"color", "fill", "style", "rounded"}
BOX_STYLES = ("solid", "dashed")


def panel_errors(brief: Mapping) -> list[str]:
    """Problems with the title, panel label, captions and boxes of a brief."""
    errors: list[str] = []
    if "title" in brief and brief["title"] is not None:
        errors += condition_line_errors(brief["title"], "title")
    label = brief.get("panel_label")
    if label is not None and not (isinstance(label, str) and label.strip()):
        errors.append("panel_label must be a short text such as \"a\" or \"(b)\".")
    for sp in brief.get("species") or []:
        if not isinstance(sp, Mapping):
            continue
        ident = sp.get("id")
        if sp.get("caption") is not None:
            errors += condition_line_errors(sp["caption"], f"Species {ident} caption")
        box = sp.get("box")
        if box is None or box is False:
            continue
        if box is True:
            continue
        if not isinstance(box, Mapping):
            errors.append(f"Species {ident}: box must be true or an object {{color, fill, style, rounded}}.")
            continue
        unknown = sorted(set(box) - BOX_KEYS)
        if unknown:
            errors.append(f"Species {ident}: unknown box keys {unknown}.")
        for key in ("color", "fill"):
            value = box.get(key)
            if value is not None and not (isinstance(value, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", value)):
                errors.append(f"Species {ident}: box {key} must be a hex colour.")
        if box.get("style", "solid") not in BOX_STYLES:
            errors.append(f"Species {ident}: box style must be one of {list(BOX_STYLES)}.")
    return errors


def _new_ids(root: ET.Element):
    used = [int(v) for el in root.iter() for v in [el.get("id")] if v and v.isdigit()]
    return renderer._IDGen(max(used, default=1000) + 1)


def _wrap(root: ET.Element, cdxml: Any) -> Any:
    text = '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")
    wrapped = renderer._ValidatedCDXML(text)
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped


def _content_box(page: ET.Element) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for el in page.iter():
        box = el.get("BoundingBox")
        if box and el.tag in ("t", "graphic", "arrow"):
            x1, y1, x2, y2 = (float(v) for v in box.split()[:4])
            xs += [x1, x2]
            ys += [y1, y2]
        elif el.tag == "n" and el.get("p"):
            x, y = _point(el)
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _text_element(line: Any, x: float, y: float, ids, colors: "_Colors", justification: str = "Center",
                  bold_prefix: str | None = None) -> ET.Element:
    plain = condition_text(line)
    if bold_prefix:
        plain = f"{bold_prefix}  {plain}" if plain else bold_prefix
    xml, _ = renderer._build_text_element([plain], x, y, ids, justification=justification)
    t = ET.fromstring(xml)
    done: set = set()
    if bold_prefix:
        _style_text_span(t, {"text": bold_prefix, "bold": True}, colors, done)
    runs = line if isinstance(line, list) else [line]
    for run in runs:
        if isinstance(run, Mapping) and (run.get("color") or run.get("bold") or run.get("italic")):
            _style_text_span(t, run, colors, done)
    return t


def apply_captions_and_title(cdxml: Any, brief: Mapping, grounded: list[dict]) -> tuple[Any, list[str], list[str]]:
    """Captions under species, then the panel label and title above the whole figure."""
    species = {str(sp.get("id")): sp for sp in brief.get("species") or [] if isinstance(sp, Mapping)}
    captions = {i: sp["caption"] for i, sp in species.items() if sp.get("caption") not in (None, "", [])}
    title = brief.get("title")
    label = brief.get("panel_label")
    if not (captions or title or label):
        return cdxml, [], []
    applied: list[str] = []
    warnings: list[str] = []
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    page = root.find("page")
    colors = _Colors(root)
    ids = _new_ids(root)
    if captions:
        labels = {g["id"]: (str(g["label"]) if g.get("label") else None) for g in grounded}
        placed: set[str] = set()
        for sp_id, frag_el, _ in _species_fragments(root, str(cdxml), grounded):
            if sp_id not in captions or sp_id in placed:
                continue
            x1, y1, x2, y2 = _frag_box(frag_el)
            below = [t for t in page.findall("t") if x1 - 8 <= _point(t)[0] <= x2 + 8
                     and y2 < _point(t)[1] < y2 + 40 and t not in frag_el.iter("t")]
            y = max([_point(t)[1] for t in below], default=y2 + 2.0) + renderer._LINE_ADVANCE
            label_t = _label_of(page, frag_el, labels.get(sp_id))
            x = _point(label_t)[0] if label_t is not None else (x1 + x2) / 2.0
            page.append(_text_element(captions[sp_id], x, y, ids, colors))
            placed.add(sp_id)
        for sp_id in sorted(set(captions) - placed):
            warnings.append(f"Species {sp_id}: not drawn as a structure, so its caption was not placed.")
        if placed:
            applied.append(f"captions ({len(placed)})")
    if title or label:
        x1, y1, _, _ = _content_box(page)
        t = _text_element(title or "", x1, y1 - 14.0, ids, colors, justification="Left",
                          bold_prefix=str(label).strip() if label else None)
        page.append(t)
        applied.append("title" if title and not label else "panel label and title" if title else "panel label")
    return _wrap(root, cdxml), applied, warnings


def apply_species_boxes(cdxml: Any, brief: Mapping, grounded: list[dict]) -> tuple[Any, list[str]]:
    """A frame (solid, dashed or rounded) and/or a fill behind each species that asks for one."""
    species = {str(sp.get("id")): sp for sp in brief.get("species") or [] if isinstance(sp, Mapping)}
    boxed = {i: ({} if sp["box"] is True else sp["box"]) for i, sp in species.items() if sp.get("box")}
    if not boxed:
        return cdxml, []
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    page = root.find("page")
    colors = _Colors(root)
    ids = _new_ids(root)
    labels = {g["id"]: (str(g["label"]) if g.get("label") else None) for g in grounded}
    count = 0
    done: set[str] = set()
    for sp_id, frag_el, _ in _species_fragments(root, str(cdxml), grounded):
        if sp_id not in boxed or sp_id in done:
            continue
        done.add(sp_id)
        box = boxed[sp_id]
        x1, y1, x2, y2 = _frag_box(frag_el)
        x1, y1, x2, y2 = x1 - 6.0, y1 - 6.0, x2 + 6.0, y2 + 6.0
        for t in frag_el.iter("t"):
            if t.get("BoundingBox"):
                bx1, by1, bx2, by2 = (float(v) for v in t.get("BoundingBox").split()[:4])
                x1, y1, x2, y2 = min(x1, bx1 - 3), min(y1, by1 - 3), max(x2, bx2 + 3), max(y2, by2 + 3)
        label_t = _label_of(page, frag_el, labels.get(sp_id))
        if label_t is not None and label_t.get("BoundingBox"):
            bx1, by1, bx2, by2 = (float(v) for v in label_t.get("BoundingBox").split()[:4])
            x1, x2, y2 = min(x1, bx1 - 4), max(x2, bx2 + 4), max(y2, by2 + 4)
        bbox = f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}"
        if box.get("fill"):
            fill = ET.Element("graphic", {"id": str(ids.next()), "GraphicType": "Rectangle", "BoundingBox": bbox,
                                          "color": colors.index(box["fill"]), "FillType": "Solid", "Z": "1"})
            if box.get("rounded"):
                fill.set("RectangleType", "RoundEdge")
            page.insert(0, fill)
        if box.get("color") or not box.get("fill"):
            frame = ET.Element("graphic", {"id": str(ids.next()), "GraphicType": "Rectangle", "BoundingBox": bbox,
                                           "color": colors.index(box.get("color") or "#000000")})
            if box.get("rounded"):
                frame.set("RectangleType", "RoundEdge")
            if box.get("style") == "dashed":
                frame.set("LineType", "Dashed")
            page.append(frame)
        count += 1
    return _wrap(root, cdxml), [f"species boxes ({count})"] if count else []


def apply_scope_conventions(cdxml: Any, brief: Mapping, grounded: list[dict], house: HouseStyle | None,
                            slug: str) -> tuple[Any, list[str], list[str], list[str]]:
    """A scope page already in its preset: compound-number face and colour, the brief's species
    colours and abbreviations (the card's abbreviate_groups too), then the measured geometry."""
    applied: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []
    if house is not None:
        root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
        page = root.find("page")
        colors = _Colors(root)
        labels = {g["id"]: (str(g["label"]) if g.get("label") else None) for g in grounded}
        # A scope page keeps each structure, its number and its values in one <group>.
        group_of = {id(f): g for g in page.iter("group") for f in g.findall("fragment")}
        label_els = []
        for sp_id, el, _ in _species_fragments(root, str(cdxml), grounded):
            group = group_of.get(id(el))
            found = [t for t in group.findall("t") if _text_of(t) == labels.get(sp_id)] if group is not None else []
            label_t = found[0] if found else _label_of(page, el, labels.get(sp_id))
            if label_t is not None:
                label_els.append(label_t)
        face = house.convention("compound_label_face")
        if face in ("bold", "plain") and label_els:
            for t in label_els:
                for s in t.iter("s"):
                    s.set("face", "1" if face == "bold" else "0")
            applied.append(f"compound_label_face={face}")
        label_color = house.convention("compound_label_color")
        if label_color and label_color.upper() != "#000000" and label_els:
            index = colors.index(label_color)
            for t in label_els:
                _paint(t, index)
            applied.append("compound_label_color")
        cdxml = _wrap(root, cdxml)
        skipped.append("the reaction-scheme conventions (yield placement, arrows, conditions) apply to schemes only")
        section = (house.figure_types or {}).get("substrate_scope") or {}
        for key, value in (section.get("conventions") or {}).items():
            if value is not None:
                skipped.append(f"substrate_scope.{key}: guidance for finishing the panel, not drawn by the tool")
    cdxml, more, warned = apply_species_styling(cdxml, brief, grounded, house)
    applied += more
    warnings += warned
    # Abbreviation labels are made at ACS size; on a styled page they take the page's label size.
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    size = root.get("LabelSize")
    if size:
        for n in root.iter("n"):
            if n.get("NodeType") == "Fragment":
                for t in n.findall("t"):
                    for s in t.iter("s"):
                        s.set("size", size)
        cdxml = _wrap(root, cdxml)
    if house is not None:
        cdxml, more, _ = apply_measured_geometry(cdxml, house, slug)
        applied += [a for a in more if not a.startswith("measured.arrow_length")]
    return cdxml, applied, skipped, warnings


def _resize_text_box(t: ET.Element) -> None:
    x, y = _point(t)
    w = len(_text_of(t)) * renderer._CHAR_WIDTH
    box = (t.get("BoundingBox") or f"{x} {y} {x} {y}").split()
    t.set("BoundingBox", f"{x - w / 2:.2f} {box[1]} {x + w / 2:.2f} {box[3]}")


def _color_new_bonds(brief: Mapping, smiles: dict, first: dict, index: str, warnings: list[str]) -> int:
    from .report_tools import map_reaction_atoms

    coloured = 0
    for number, step in enumerate(brief["steps"], 1):
        subs = [smiles[s] for s in _as_list(step.get("substrates"))]
        prods = _as_list(step.get("products"))
        try:
            result = map_reaction_atoms(".".join(subs) + ">>" + ".".join(smiles[p] for p in prods),
                                        {"method": "mcs"})
        except Exception as exc:
            warnings.append(f"Step {number}: the atom mapping failed ({exc}); new bonds are left black.")
            continue
        if result.get("status") != "complete" or result.get("ambiguous"):
            warnings.append(f"Step {number}: the atom mapping is {result.get('status')}"
                            f"{' with ambiguous atoms' if result.get('ambiguous') else ''}; new bonds are left black.")
            continue
        by_map = {entry["map"]: entry["product"] for entry in result["map"] if entry.get("product")}
        for change in result.get("bond_changes", []):
            if change.get("type") != "formed":
                continue
            ends = []
            for atom in change["atoms"]:
                number_text = str(atom).split(":")[-1]
                ends.append(by_map.get(int(number_text)) if number_text.isdigit() else None)
            if None in ends or ends[0]["species"] != ends[1]["species"]:
                continue
            for pid in prods:
                if smiles[pid] != ends[0]["species"] or pid not in first:
                    continue
                frag_el, frag_mol = first[pid]
                nodes = _atom_nodes(frag_el, frag_mol, Chem.MolFromSmiles(smiles[pid]))
                if nodes is None:
                    warnings.append(f"Step {number}: product {pid} could not be matched; new bonds are left black.")
                    break
                key = frozenset((nodes[ends[0]["atom_index"]].get("id"), nodes[ends[1]["atom_index"]].get("id")))
                bond = _bond_elements(frag_el).get(key)
                if bond is not None:
                    bond.set("color", index)
                    coloured += 1
                break
    return coloured


def _abbreviate(frag_el: ET.Element, src: Any, nodes: list[ET.Element], groups: list[str], ids) -> int:
    used: set[int] = set()
    count = 0
    groups = list(dict.fromkeys(group_name(g) for g in groups))
    order = sorted(groups, key=lambda g: -Chem.MolFromSmarts(ABBREVIATIONS[g][0]).GetNumAtoms())
    for name in order:
        smarts, expansion, left_label, right_label = ABBREVIATIONS[name]
        for match in src.GetSubstructMatches(Chem.MolFromSmarts(smarts)):
            group = set(match)
            if group & used:
                continue
            external = [(a, nb.GetIdx()) for a in match for nb in src.GetAtomWithIdx(a).GetNeighbors()
                        if nb.GetIdx() not in group]
            if len(external) != 1 or external[0][0] != match[0]:
                continue
            used |= group
            _contract(frag_el, nodes, match, external[0][1], expansion,
                      left_label, right_label, ids)
            count += 1
    return count


def _contract(frag_el: ET.Element, nodes: list[ET.Element], match: tuple, outside: int,
              expansion: str, left_label: str, right_label: str, ids) -> None:
    head = nodes[match[0]]
    ax, ay = _point(head)
    nx, ny = _point(nodes[outside])
    group_ids = {nodes[i].get("id") for i in match}
    for b in list(frag_el.findall("b")):
        if b.get("B") in group_ids and b.get("E") in group_ids:
            frag_el.remove(b)
    for i in match[1:]:
        if nodes[i] in list(frag_el):
            frag_el.remove(nodes[i])
    color = head.get("color")
    for attr in ("Element", "NumHydrogens", "NeedsClean", "Charge", "Isotope", "Radical"):
        head.attrib.pop(attr, None)
    for child in list(head):
        head.remove(child)
    head.set("NodeType", "Fragment")
    head.append(ET.fromstring(_inner_fragment(expansion, (ax, ay), (nx, ny), ids)))
    rest_on_left = nx <= ax
    text = left_label if rest_on_left else right_label
    width = _label_width(text)
    # The attachment character (first for a right-flowing label, last for a
    # left-flowing one) is centred on the node. No LabelDisplay attribute is
    # written: with one, desktop ChemDraw re-anchors the label one bond
    # length towards the neighbour; without one it keeps this position but
    # spells a left-flowing label its own way (CO2Me rather than MeO2C),
    # which Clean Up in ChemDraw corrects.
    tx = ax - _char_width(text[0]) / 2 if rest_on_left else ax + _char_width(text[-1]) / 2 - width
    just = "Left" if rest_on_left else "Right"
    t = ET.SubElement(head, "t", {
        "id": str(ids.next()), "p": f"{tx:.2f} {ay + 3.52:.2f}",
        "BoundingBox": f"{tx:.2f} {ay - 7.52:.2f} {tx + width:.2f} {ay:.2f}",
        "LabelJustification": just, "LabelAlignment": just,
    })
    s = ET.SubElement(t, "s", {"font": ACS_LABEL_FONT, "size": str(ACS_LABEL_SIZE), "color": color or "0",
                               "face": ACS_LABEL_FACE})
    s.text = text


# Arial 10 pt advance widths (pt) for the characters abbreviations use.
_WIDE = {"M": 8.3, "W": 9.4, "O": 7.8, "C": 7.2, "N": 7.2, "B": 6.7, "S": 6.7, "T": 6.1, "P": 6.7, "H": 7.2,
         "A": 6.7, "E": 6.7, "F": 6.1, "Z": 6.1, "m": 8.3, "w": 7.2}


def _char_width(ch: str) -> float:
    if ch.isdigit():
        return 3.9  # subscript size
    if ch in _WIDE:
        return _WIDE[ch]
    return 6.7 if ch.isupper() else 5.6


def _label_width(text: str) -> float:
    return sum(_char_width(ch) for ch in text)


def _inner_fragment(expansion: str, at: tuple[float, float], outside: tuple[float, float], ids) -> str:
    """The abbreviation's expansion, its attachment atom at ``at`` and the connection point at ``outside``."""
    mol = Chem.MolFromSmiles("*" + expansion)
    Chem.Kekulize(mol, clearAromaticFlags=True)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    d0, a0 = conf.GetAtomPosition(0), conf.GetAtomPosition(1)
    # Similarity transform taking the dummy to ``outside`` and the attachment atom to ``at``.
    src_angle = math.atan2(a0.y - d0.y, a0.x - d0.x)
    dst_angle = math.atan2(-(at[1] - outside[1]), at[0] - outside[0])
    scale = math.hypot(at[0] - outside[0], at[1] - outside[1]) / max(math.hypot(a0.x - d0.x, a0.y - d0.y), 1e-6)
    rot = dst_angle - src_angle

    def place(i: int) -> tuple[float, float]:
        p = conf.GetAtomPosition(i)
        dx, dy = p.x - d0.x, p.y - d0.y
        rx = (dx * math.cos(rot) - dy * math.sin(rot)) * scale
        ry = (dx * math.sin(rot) + dy * math.cos(rot)) * scale
        return outside[0] + rx, outside[1] - ry

    node_ids = {a.GetIdx(): ids.next() for a in mol.GetAtoms()}
    parts = [f'<fragment id="{ids.next()}">']
    for atom in mol.GetAtoms():
        x, y = place(atom.GetIdx())
        if atom.GetIdx() == 0:
            parts.append(f'<n id="{node_ids[0]}" p="{x:.2f} {y:.2f}" NodeType="ExternalConnectionPoint"/>')
            continue
        extra = ""
        if atom.GetAtomicNum() != 6:
            extra += f' Element="{atom.GetAtomicNum()}" NumHydrogens="{atom.GetTotalNumHs()}"'
        if atom.GetFormalCharge():
            extra += f' Charge="{atom.GetFormalCharge()}"'
        parts.append(f'<n id="{node_ids[atom.GetIdx()]}" p="{x:.2f} {y:.2f}"{extra}/>')
    for bond in mol.GetBonds():
        order = {Chem.BondType.DOUBLE: ' Order="2"',
                 Chem.BondType.TRIPLE: ' Order="3"'}.get(bond.GetBondType(), "")
        parts.append(f'<b id="{ids.next()}" B="{node_ids[bond.GetBeginAtomIdx()]}" '
                     f'E="{node_ids[bond.GetEndAtomIdx()]}"{order}/>')
    parts.append("</fragment>")
    return "".join(parts)
