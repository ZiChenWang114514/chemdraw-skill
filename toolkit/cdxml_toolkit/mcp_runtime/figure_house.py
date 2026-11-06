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
from ..publication.house_styles import ABBREVIATIONS, CONVENTION_KEYS, HouseStyle, group_name
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
    frag_els = {f.get("id", ""): f for f in page.findall("fragment")}
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
    candidates = [t for t in page.findall("t") if _text_of(t) == label
                  and x1 - 8 <= _point(t)[0] <= x2 + 8 and _point(t)[1] > y1]
    return min(candidates, key=lambda t: abs(_point(t)[1] - y2), default=None)


def _paint(el: ET.Element, index: str) -> None:
    el.set("color", index)
    for s in el.iter("s"):
        s.set("color", index)


# --- conventions ---------------------------------------------------------------

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

    # Abbreviations last: they replace atoms that the colour steps may have painted.
    groups = house.convention("abbreviate_groups") or []
    if groups:
        count = 0
        for sp_id, frag_el, frag_mol in drawn:
            src = Chem.MolFromSmiles(smiles[sp_id])
            nodes = _atom_nodes(frag_el, frag_mol, src)
            if nodes is None:
                warnings.append(f"Species {sp_id}: the drawn structure could not be matched, so no group was abbreviated.")
                continue
            count += _abbreviate(frag_el, src, nodes, groups, ids)
        applied.append(f"abbreviate_groups ({count} contracted)")

    if house.convention("aromatic_rings") == "circle":
        skipped.append("aromatic_rings=circle: rings are drawn as Kekule structures")
    if house.convention("conditions_split") == "reagents_above_solvent_below":
        skipped.append("conditions_split: the brief's above/below lines are kept as given")

    for key in CONVENTION_KEYS:
        if house.conventions.get(key) is None:
            skipped.append(f"{key}: not specified by the card")
    text = '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")
    wrapped = renderer._ValidatedCDXML(text)
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped, applied, skipped, warnings


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
