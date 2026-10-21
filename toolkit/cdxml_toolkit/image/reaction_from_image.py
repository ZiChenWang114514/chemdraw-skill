#!/usr/bin/env python3
"""
reaction_from_image.py — Build a full ChemDraw reaction scheme from a screenshot.

Takes a screenshot of a reaction scheme (e.g. from SciFinder, a paper, or a patent)
and produces a CDXML reaction scheme with proper arrow, conditions text, and
ACS Document 1996 styling.

Architecture
------------
This is an *orchestration* tool.  It does NOT try to auto-detect arrows or OCR
conditions text from the image — that is unreliable and unnecessary.  Instead,
an LLM (or user) looks at the screenshot and provides a small JSON descriptor
that tells the tool:

  1. Which detected structures are reactants vs products (by left-to-right index)
  2. What conditions text goes above / below the arrow

The tool then:
  a. Extracts molecular structures from the image via DECIMER
     (delegates to structure_from_image.py)
  b. Assigns them as reactants or products per the descriptor
  c. Lays out the molecules, arrow, and conditions text
  d. Builds a valid CDXML document via cdxml_builder.py
  e. Applies subscript formatting to chemical formulae in conditions

Usage
-----
Minimal (LLM provides JSON descriptor on stdin):
    python reaction_from_image.py --image scheme.png --descriptor desc.json -o scheme.cdxml

Descriptor JSON format:
    {
      "reactant_indices": [0, 1],
      "product_indices":  [2],
      "conditions_above": ["Pd2dba3", "BINAP"],
      "conditions_below": ["Dioxane", "24 h, reflux"]
    }

  - reactant_indices / product_indices refer to the left-to-right order of
    detected structures (0-indexed).  The tool extracts all structures first,
    then assigns roles based on these indices.
  - conditions_above / conditions_below are plain text strings.
  - If a condition string matches a known abbreviation (e.g. "Cs2CO3"),
    it is kept verbatim.  Unknown abbreviations are reproduced as-is
    (we never trust LLM-generated SMILES for reagents).

Abbreviation dictionary
-----------------------
A curated dictionary maps common reagent/ligand/catalyst abbreviations to
themselves (for subscript formatting) or to display names.  This is NOT
for structure resolution — it's only to decide whether a name is "known"
and how to display it.  If an abbreviation isn't in the dictionary, the
exact text from the descriptor is used verbatim.

The dictionary lives in ABBREVIATIONS below and can be extended over time.
"""

import argparse
import json
import math
import os
import re
import sys
from copy import deepcopy
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

# ---------------------------------------------------------------------------
# Shared reagent database
# ---------------------------------------------------------------------------

from ..resolve.reagent_db import get_reagent_db
from ..text_formatting import needs_subscript, build_formatted_s_xml
from ..constants import (
    ACS_BOND_LENGTH, EXPAND_SCALE_BOND,
    CDXML_HEADER, CDXML_FOOTER,
    ACS_LABEL_FONT, ACS_LABEL_SIZE, ACS_LABEL_FACE,
    ACS_CAPTION_SIZE, ACS_HASH_SPACING, ACS_MARGIN_WIDTH,
    ACS_LINE_WIDTH, ACS_BOLD_WIDTH, ACS_BOND_LENGTH_STR,
    ACS_BOND_SPACING, ACS_CHAIN_ANGLE_STR,
)


# ---------------------------------------------------------------------------
# Resolve abbreviation display text
# ---------------------------------------------------------------------------

def resolve_abbreviation(text: str) -> str:
    """Look up text in the reagent database.

    Returns the canonical display form if found, otherwise the original text
    verbatim (we never invent or transform unknown abbreviations).
    """
    return get_reagent_db().resolve_display(text)


# ---------------------------------------------------------------------------
# Condition classification: chemistry vs. non-chemistry text
# ---------------------------------------------------------------------------

def _is_non_chemistry_text(text: str) -> bool:
    """Return True if *text* is a non-chemistry condition string that should
    **always** be rendered as a text label (never expanded to a structure).

    Examples that return True:
        "24 h, reflux", "120 °C", "rt", "overnight", "10 mol%",
        "1.5 equiv", "N2", "Ar", "sealed tube"
    """
    t = text.strip()
    tl = t.lower()

    # Temperature patterns
    if re.search(r'-?\d+\s*°', t):
        return True
    if tl in ("rt", "room temperature", "room temp", "room temp."):
        return True

    # Time patterns
    if re.search(r'\d+\s*(h|hr|hrs|min|d|days?)\b', tl):
        return True
    if tl in ("overnight", "o/n", "on"):
        return True

    # Percentage / equivalents / concentration
    if re.search(r'\d+\s*(mol\s*)?%', tl):
        return True
    if re.search(r'[\d.]+\s*equiv', tl):
        return True
    if re.search(r'[\d.]+\s*M\b', t):           # case-sensitive M
        return True

    # Physical conditions (single keywords)
    _PHYS = {
        "reflux", "sealed tube", "microwave", "mw", "ultrasound",
        "sonication", "inert atmosphere", "dark", "hv", "light",
    }
    if tl in _PHYS:
        return True

    # Inert gas (very short abbreviations)
    if tl in ("n2", "ar", "argon", "nitrogen"):
        return True

    # Compound phrases with comma → likely mixed ("24 h, reflux")
    if "," in t:
        return True

    # "then ..." / step instructions
    if tl.startswith("then "):
        return True

    return False


# ---------------------------------------------------------------------------
# Expand conditions: resolve names to structures (ChemScript → PubChem)
# ---------------------------------------------------------------------------

def _extract_fragment_from_cdxml(cdxml_str: str) -> Optional[Tuple[str, float, float, float, float]]:
    """Parse a CDXML string and extract the first <fragment> element XML +
    its bounding box.  Returns (frag_xml, xmin, ymin, xmax, ymax) or None."""
    import xml.etree.ElementTree as ET

    if not cdxml_str or "<CDXML" not in cdxml_str:
        return None
    root = ET.fromstring(cdxml_str)
    page_el = root.find("page")
    if page_el is None:
        return None
    frag_el = page_el.find("fragment")
    if frag_el is None:
        return None

    frag_xml = ET.tostring(frag_el, encoding="unicode")
    xmin, ymin, xmax, ymax = _measure_fragment_xml(frag_xml)
    if xmin == xmax:
        return None
    return (frag_xml, xmin, ymin, xmax, ymax)


def _scale_fragment_xml(
    frag_xml: str,
    scale: float,
    xmin: float, ymin: float, xmax: float, ymax: float,
) -> Tuple[str, float, float, float, float]:
    """Scale a fragment's coordinates around its center by *scale* factor.

    Returns ``(scaled_xml, new_xmin, new_ymin, new_xmax, new_ymax)``.
    """
    cx = (xmin + xmax) / 2.0
    cy = (ymin + ymax) / 2.0

    def scale_p(m: "re.Match") -> str:
        x, y = float(m.group(1)), float(m.group(2))
        nx = cx + (x - cx) * scale
        ny = cy + (y - cy) * scale
        return f'p="{nx:.3f} {ny:.3f}"'

    def scale_bb(m: "re.Match") -> str:
        vals = [float(v) for v in m.group(1).split()]
        sv = [
            f"{cx + (vals[0] - cx) * scale:.3f}",
            f"{cy + (vals[1] - cy) * scale:.3f}",
            f"{cx + (vals[2] - cx) * scale:.3f}",
            f"{cy + (vals[3] - cy) * scale:.3f}",
        ]
        return f'BoundingBox="{" ".join(sv)}"'

    scaled = re.sub(r'\bp="([-\d.]+)\s+([-\d.]+)"', scale_p, frag_xml)
    scaled = re.sub(r'\bBoundingBox="((?:[-\d.]+ ?){4})"', scale_bb, scaled)
    new_xmin, new_ymin, new_xmax, new_ymax = _measure_fragment_xml(scaled)
    return scaled, new_xmin, new_ymin, new_xmax, new_ymax


def _resolve_condition_to_fragment(
    text: str,
    cs_bridge,
    verbose: bool = False,
) -> Optional[Tuple[str, float, float, float, float]]:
    """Attempt to resolve a single condition string to a CDXML fragment.

    Resolution chain:
      1. Skip if ``_is_non_chemistry_text(text)`` → always text.
      2. ChemScript ``name_to_cdxml(canonical_name)`` → extract fragment.
      3. PubChem name→SMILES → ChemScript ``smiles_to_cdxml(smiles)`` → extract fragment.
      4. Return ``None`` → caller renders text verbatim.

    If the resolved structure exceeds ``EXPAND_MAX_WIDTH``, it is scaled down
    so that conditions don't dominate the scheme.

    Returns (fragment_xml, xmin, ymin, xmax, ymax) or None.
    """
    def log(msg: str):
        if verbose:
            print(f"[expand] {msg}", file=sys.stderr)

    canonical = resolve_abbreviation(text)

    if _is_non_chemistry_text(canonical):
        log(f"  '{canonical}' → non-chemistry text, keeping as label")
        return None

    result = None

    # --- 1. ChemScript name resolution ---
    try:
        cdxml_str = cs_bridge.name_to_cdxml(canonical)
        result = _extract_fragment_from_cdxml(cdxml_str)
        if result is not None:
            log(f"  '{canonical}' → ChemScript name OK")
    except Exception as exc:
        log(f"  '{canonical}' → ChemScript name failed: {exc}")

    # --- 2. PubChem name → SMILES → ChemScript smiles_to_cdxml ---
    if result is None:
        try:
            from ..resolve.cas_resolver import resolve_name_to_smiles
            smiles = resolve_name_to_smiles(canonical)
            if smiles:
                log(f"  '{canonical}' → PubChem SMILES: {smiles[:60]}")
                cdxml_str = cs_bridge.smiles_to_cdxml(smiles)
                result = _extract_fragment_from_cdxml(cdxml_str)
                if result is not None:
                    log(f"  '{canonical}' → PubChem+ChemScript OK")
        except Exception as exc:
            log(f"  '{canonical}' → PubChem fallback failed: {exc}")

    if result is None:
        log(f"  '{canonical}' → unresolved, keeping as text label")
        return None

    # --- Scale down large structures ---
    frag_xml, xmin, ymin, xmax, ymax = result
    w = xmax - xmin
    if w > EXPAND_MAX_WIDTH:
        scale = EXPAND_MAX_WIDTH / w
        frag_xml, xmin, ymin, xmax, ymax = _scale_fragment_xml(
            frag_xml, scale, xmin, ymin, xmax, ymax
        )
        log(f"  '{canonical}' scaled to {scale:.2f}x (w={w:.1f} → {xmax - xmin:.1f})")

    return (frag_xml, xmin, ymin, xmax, ymax)


def _resolve_all_conditions(
    conditions: List[str],
    cs_bridge,
    verbose: bool = False,
) -> List[Tuple[str, Optional[Tuple[str, float, float, float, float]]]]:
    """Resolve a list of condition strings.  For each returns
    ``(display_text, fragment_info_or_None)``.
    """
    results: List[Tuple[str, Optional[Tuple[str, float, float, float, float]]]] = []
    for text in conditions:
        canonical = resolve_abbreviation(text)
        frag = _resolve_condition_to_fragment(text, cs_bridge, verbose)
        results.append((canonical, frag))
    return results


# ---------------------------------------------------------------------------
# Fragment ID reassignment (prevent collisions with reactant/product IDs)
# ---------------------------------------------------------------------------

def _reassign_fragment_ids(frag_xml: str, ids: "_IDGen") -> Tuple[str, int]:
    """Rewrite all element IDs in *frag_xml* using *ids* so they are unique
    within the overall CDXML document.

    Returns ``(new_xml, top_level_fragment_id)``.
    """
    import xml.etree.ElementTree as ET

    root = ET.fromstring(frag_xml)
    old_to_new: Dict[str, str] = {}

    # First pass: assign new IDs
    for el in root.iter():
        old_id = el.get("id")
        if old_id is not None:
            new_id = str(ids.next())
            old_to_new[old_id] = new_id

    # Second pass: rewrite id, B (bond begin), E (bond end), Z
    for el in root.iter():
        for attr in ("id", "B", "E", "SupersededBy"):
            val = el.get(attr)
            if val and val in old_to_new:
                el.set(attr, old_to_new[val])
        # Z attribute also needs a unique value
        if el.get("Z") is not None:
            el.set("Z", str(ids.next()))

    top_id = int(old_to_new.get(root.get("id", "0"), "0"))
    new_xml = ET.tostring(root, encoding="unicode")
    return new_xml, top_id


# ---------------------------------------------------------------------------
# Layout constants (ACS Document 1996)
# ---------------------------------------------------------------------------

INTER_MOL_GAP    = 18.0     # horizontal gap between molecules on same side
ARROW_MARGIN     = 20.0     # gap between molecules and arrow ends
ARROW_LENGTH     = 80.0     # default arrow shaft length
PAGE_LEFT        = 80.0     # left margin for first reactant
VERTICAL_CENTER  = 500.0    # y-coordinate for vertical centre of the scheme
CONDITIONS_GAP_ABOVE = 10.0 # clear gap between bottom of above-text and arrow shaft
CONDITIONS_GAP_BELOW = 10.0 # clear gap between arrow shaft and top of below-text
CONDITIONS_LINE_HEIGHT = 12.0  # line height for conditions text
CONDITIONS_DESCENDER  = 3.0   # extra space below baseline for descenders (g, p, y)

# Expanded conditions layout constants
EXPAND_STRUCTURE_GAP    = 10.0  # horizontal gap between adjacent condition structures
EXPAND_ABOVE_CLEARANCE  = 12.0  # clearance from arrow shaft to bottom of above-structures
EXPAND_BELOW_CLEARANCE  = 12.0  # clearance from arrow shaft to top of below-structures
EXPAND_MAX_WIDTH        = 80.0  # max width for a single condition structure before scaling


# ---------------------------------------------------------------------------
# CDXML header helper (uses shared template from constants.py)
# ---------------------------------------------------------------------------

def _format_cdxml_header(bbox: str) -> str:
    """Format CDXML_HEADER template with ACS Document 1996 style constants."""
    return CDXML_HEADER.format(
        bbox=bbox,
        label_font=ACS_LABEL_FONT,
        label_size=ACS_LABEL_SIZE,
        label_face=ACS_LABEL_FACE,
        caption_size=ACS_CAPTION_SIZE,
        hash_spacing=ACS_HASH_SPACING,
        margin_width=ACS_MARGIN_WIDTH,
        line_width=ACS_LINE_WIDTH,
        bold_width=ACS_BOLD_WIDTH,
        bond_length=ACS_BOND_LENGTH_STR,
        bond_spacing=ACS_BOND_SPACING,
        chain_angle=ACS_CHAIN_ANGLE_STR,
    )


# ---------------------------------------------------------------------------
# ID generator
# ---------------------------------------------------------------------------

class _IDGen:
    """Simple incrementing integer ID generator."""
    def __init__(self, start: int = 1000):
        self._n = start

    def next(self) -> int:
        v = self._n
        self._n += 1
        return v


# ---------------------------------------------------------------------------
# Molecule bounding box helpers
# ---------------------------------------------------------------------------

def _mol_extent(mol: Dict) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) of atoms."""
    xs = [a["x"] for a in mol["atoms"]]
    ys = [a["y"] for a in mol["atoms"]]
    return min(xs), min(ys), max(xs), max(ys)


def _translate_mol(mol: Dict, dx: float, dy: float) -> Dict:
    """Translate all atom coordinates by (dx, dy). Returns a new dict."""
    mol = deepcopy(mol)
    for a in mol["atoms"]:
        a["x"] += dx
        a["y"] += dy
    return mol


# ---------------------------------------------------------------------------
# Fragment (molecule) XML builder — adapted from cdxml_builder.py
# ---------------------------------------------------------------------------

# Element numbers for heteroatoms
ELEMENT_NUMBERS: Dict[str, int] = {
    "H":  1,  "B":  5,  "C":  6,  "N":  7,  "O":  8,
    "F":  9,  "Si": 14, "P":  15, "S":  16, "Cl": 17,
    "Se": 34, "Br": 35, "I":  53, "Cs": 55,
}

WIDE_SYMBOLS = {"Br", "Cl", "Si", "Se", "Cs"}

BOND_ORDER_ATTR: Dict[int, Optional[str]] = {
    1: None, 2: "2", 3: "3", 4: "1.5",
}

BOND_STEREO_ATTR: Dict[int, str] = {
    1: "WedgeBegin", 4: "WedgeBegin", 6: "WedgedHashBegin",
}


def _label_bbox(x: float, y: float, symbol: str) -> str:
    char_w = 7.0 if symbol in WIDE_SYMBOLS else 6.0
    lx = x - char_w / 2.0
    ty = y - 7.52
    by = y
    rx = lx + char_w
    return f"{lx:.2f} {ty:.2f} {rx:.2f} {by:.2f}"


def _build_fragment(
    atoms: List[Dict],
    bonds: List[Dict],
    ids: _IDGen,
) -> Tuple[str, int]:
    """Build a <fragment> XML string.  Returns (xml_string, fragment_id)."""
    frag_id = ids.next()
    atom_id_map: Dict[int, int] = {}

    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    bb = f"{min(xs):.2f} {min(ys):.2f} {max(xs):.2f} {max(ys):.2f}"

    lines = [f'<fragment id="{frag_id}" BoundingBox="{bb}" Z="{ids.next()}">']

    for a in atoms:
        aid = ids.next()
        atom_id_map[a["index"]] = aid
        sym = a.get("symbol", "C")
        ax, ay = a["x"], a["y"]
        z = ids.next()
        attrs = [f'id="{aid}"', f'p="{ax:.2f} {ay:.2f}"', f'Z="{z}"']

        is_carbon = (sym == "C")
        charge = a.get("charge", 0)

        if not is_carbon:
            el_num = ELEMENT_NUMBERS.get(sym, 0)
            if el_num:
                attrs.append(f'Element="{el_num}"')
            nh = a.get("num_hydrogens", 0)
            attrs.append(f'NumHydrogens="{nh}"')
            attrs.append('NeedsClean="yes"')
            attrs.append('AS="N"')

        if charge:
            attrs.append(f'Charge="{charge}"')

        cfg = a.get("cfg", 0)
        if cfg:
            attrs.append(f'Stereo="{cfg}"')

        if is_carbon and not charge:
            lines.append(f'<n {" ".join(attrs)}/>')
        else:
            lx = ax - 3.25
            ly = ay + 3.52
            bbox = _label_bbox(ax, ay, sym)
            label_text = xml_escape(sym)
            label_align = ""
            if sym in WIDE_SYMBOLS:
                label_align = ' LabelAlignment="Left"'
            lines.append(f'<n {" ".join(attrs)}>')
            lines.append(
                f'<t p="{lx:.2f} {ly:.2f}" BoundingBox="{bbox}" '
                f'LabelJustification="Left"{label_align}>'
            )
            lines.append(
                f'<s font="3" size="10" color="0" face="96">{label_text}</s>'
            )
            lines.append("</t>")
            lines.append("</n>")

    for b in bonds:
        bid = ids.next()
        z = ids.next()
        a1 = atom_id_map.get(b["atom1"], 0)
        a2 = atom_id_map.get(b["atom2"], 0)
        order = b.get("order", 1)
        cfg = b.get("cfg", 0)
        attrs = [f'id="{bid}"', f'Z="{z}"', f'B="{a1}"', f'E="{a2}"']

        order_attr = BOND_ORDER_ATTR.get(order)
        if order_attr:
            attrs.append(f'Order="{order_attr}"')

        double_pos = b.get("double_pos", "")
        if double_pos:
            attrs.append(f'DoublePosition="{double_pos}"')

        if cfg and cfg in BOND_STEREO_ATTR:
            attrs.append(f'Display="{BOND_STEREO_ATTR[cfg]}"')
        elif order == 1:
            attrs.append('BS="N"')

        lines.append(f'<b {" ".join(attrs)}/>')

    lines.append("</fragment>")
    return "\n".join(lines), frag_id


# ---------------------------------------------------------------------------
# Arrow XML builder
# ---------------------------------------------------------------------------

def _build_arrow(
    tail_x: float, tail_y: float,
    head_x: float, head_y: float,
    ids: _IDGen,
) -> Tuple[str, int]:
    """Build an <arrow> element. Returns (xml_string, arrow_id)."""
    aid = ids.next()
    z = ids.next()
    bx1 = min(tail_x, head_x)
    by1 = min(tail_y, head_y) - 4.0
    bx2 = max(tail_x, head_x)
    by2 = max(tail_y, head_y) + 4.0
    cx3 = (tail_x + head_x) / 2.0
    cy3 = tail_y + 100.0
    xml = (
        f'<arrow id="{aid}" '
        f'BoundingBox="{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}" '
        f'Z="{z}" '
        f'FillType="None" '
        f'ArrowheadHead="Full" '
        f'ArrowheadType="Solid" '
        f'HeadSize="1000" '
        f'ArrowheadCenterSize="875" '
        f'ArrowheadWidth="250" '
        f'Head3D="{head_x:.2f} {head_y:.2f} 0" '
        f'Tail3D="{tail_x:.2f} {tail_y:.2f} 0" '
        f'Center3D="{cx3:.2f} {cy3:.2f} 0" '
        f'MajorAxisEnd3D="{cx3 + 80:.2f} {cy3:.2f} 0" '
        f'MinorAxisEnd3D="{cx3:.2f} {cy3 + 80:.2f} 0"'
        f'/>'
    )
    return xml, aid


# ---------------------------------------------------------------------------
# Conditions text XML builder (with subscript support)
# ---------------------------------------------------------------------------

def _build_conditions_text(
    text_lines: List[str],
    x: float,
    baseline_y: float,
    ids: _IDGen,
) -> Tuple[str, int]:
    """Build a <t> element for conditions text above or below the arrow.

    Each entry in text_lines becomes one line.  Chemical formulae get
    subscript formatting (e.g. Pd2dba3 → Pd₂dba₃).

    Parameters
    ----------
    x          : horizontal centre of the text block
    baseline_y : y-coordinate for the baseline of the FIRST line
                 (CDXML <t> p="x y" uses first-line baseline)

    Returns (xml_string, text_element_id).
    """
    tid = ids.next()
    z = ids.next()

    # Estimate bounding box
    max_chars = max((len(ln) for ln in text_lines), default=1)
    n_lines = len(text_lines)
    w = max_chars * 5.8
    ascender = 8.0   # approximate ascender height above baseline
    descender = 3.0  # approximate descender depth below baseline

    bx1 = x - w / 2.0
    by1 = baseline_y - ascender
    bx2 = x + w / 2.0
    by2 = baseline_y + (n_lines - 1) * CONDITIONS_LINE_HEIGHT + descender

    # Build the <s> content.  We join lines with \n inside the <s>,
    # applying subscripts per-line where appropriate.  If ANY line
    # needs subscripts, we build per-line <s> elements; otherwise
    # we use a single <s> block.
    any_subscript = any(needs_subscript(ln) for ln in text_lines)

    if any_subscript:
        # Build each line as separate <s> element(s), with \n between lines
        s_parts = []
        for i, ln in enumerate(text_lines):
            if i > 0:
                # Newline between lines — plain text <s>
                s_parts.append(
                    '<s font="3" size="10" color="0" face="96">\n</s>'
                )
            s_parts.append(build_formatted_s_xml(ln))
        s_xml = "".join(s_parts)
    else:
        # Simple: all lines in one <s>
        text = "\n".join(xml_escape(ln) for ln in text_lines)
        s_xml = f'<s font="3" size="10" color="0" face="96">{text}</s>'

    xml = (
        f'<t id="{tid}" p="{x:.2f} {baseline_y:.2f}" '
        f'BoundingBox="{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}" '
        f'Z="{z}" '
        f'CaptionJustification="Center" '
        f'Justification="Center" '
        f'LineHeight="auto">'
        f'{s_xml}'
        f'</t>'
    )
    return xml, tid


# ---------------------------------------------------------------------------
# Layout expanded conditions (structures + text) above/below arrow
# ---------------------------------------------------------------------------

ExpandedItems = List[Tuple[str, Optional[Tuple[str, float, float, float, float]]]]


def _layout_expanded_conditions(
    resolved_items: "ExpandedItems",
    arrow_tail_x: float,
    arrow_head_x: float,
    arrow_y: float,
    position: str,           # "above" or "below"
    ids: "_IDGen",
    verbose: bool = False,
) -> Tuple[List[str], List[int]]:
    """Position resolved condition items (structures + text labels) above or
    below the arrow, arranged horizontally.

    Parameters
    ----------
    resolved_items : list of (display_text, fragment_info_or_None)
    arrow_tail_x, arrow_head_x : arrow horizontal extent
    arrow_y : arrow y-coordinate
    position : "above" or "below"
    ids : shared ID generator
    verbose : print debug info

    Returns
    -------
    (xml_strings, element_ids)
    """
    def log(msg: str):
        if verbose:
            print(f"[expand-layout] {msg}", file=sys.stderr)

    if not resolved_items:
        return [], []

    arrow_mid_x = (arrow_tail_x + arrow_head_x) / 2.0

    # --- Compute widths and heights for each item ---
    item_infos = []          # (width, height, is_structure)
    for display_text, frag_info in resolved_items:
        if frag_info is not None:
            _xml, xmin, ymin, xmax, ymax = frag_info
            w = xmax - xmin
            h = ymax - ymin
            item_infos.append((w, h, True))
        else:
            # Estimate text width
            w = max(len(display_text) * 5.8, 20.0)
            h = 12.0   # single-line text height
            item_infos.append((w, h, False))

    n = len(item_infos)
    total_width = sum(info[0] for info in item_infos) + (n - 1) * EXPAND_STRUCTURE_GAP
    max_height = max(info[1] for info in item_infos)

    # Starting x so the row is centered over the arrow midpoint
    start_x = arrow_mid_x - total_width / 2.0

    # --- Compute vertical anchor ---
    if position == "above":
        # Bottom edge of all items at arrow_y - clearance
        items_bottom_y = arrow_y - EXPAND_ABOVE_CLEARANCE
    else:
        # Top edge of all items at arrow_y + clearance
        items_top_y = arrow_y + EXPAND_BELOW_CLEARANCE

    # --- Place each item ---
    xml_parts: List[str] = []
    id_parts: List[int] = []
    cursor_x = start_x

    for i, (display_text, frag_info) in enumerate(resolved_items):
        w, h, is_struct = item_infos[i]

        if is_struct and frag_info is not None:
            frag_xml, xmin, ymin, xmax, ymax = frag_info
            frag_cx = (xmin + xmax) / 2.0
            frag_cy = (ymin + ymax) / 2.0
            target_cx = cursor_x + w / 2.0

            if position == "above":
                # Place so fragment's ymax = items_bottom_y
                target_cy = items_bottom_y - h / 2.0
            else:
                # Place so fragment's ymin = items_top_y
                target_cy = items_top_y + h / 2.0

            dx = target_cx - frag_cx
            dy = target_cy - frag_cy
            translated = _translate_fragment_xml(frag_xml, dx, dy)
            final_xml, frag_id = _reassign_fragment_ids(translated, ids)
            xml_parts.append(final_xml)
            id_parts.append(frag_id)
            log(f"  Structure '{display_text}' at cx={target_cx:.1f} cy={target_cy:.1f}")

        else:
            # Text label fallback
            text_cx = cursor_x + w / 2.0
            if position == "above":
                ascender = 8.0
                baseline_y = items_bottom_y - ascender
            else:
                ascender = 8.0
                baseline_y = items_top_y + ascender

            txt_xml, txt_id = _build_conditions_text(
                [display_text], text_cx, baseline_y, ids
            )
            xml_parts.append(txt_xml)
            id_parts.append(txt_id)
            log(f"  Text '{display_text}' at cx={text_cx:.1f} baseline={baseline_y:.1f}")

        cursor_x += w + EXPAND_STRUCTURE_GAP

    return xml_parts, id_parts


# ---------------------------------------------------------------------------
# Core: build reaction scheme CDXML
# ---------------------------------------------------------------------------

def build_reaction_scheme(
    structures: List[Dict],
    reactant_indices: List[int],
    product_indices: List[int],
    conditions_above: List[str],
    conditions_below: List[str],
    verbose: bool = False,
    expanded_above: Optional["ExpandedItems"] = None,
    expanded_below: Optional["ExpandedItems"] = None,
) -> str:
    """
    Assemble a CDXML reaction scheme from extracted structures + descriptor.

    Parameters
    ----------
    structures        : list of structure dicts from extract_structures_from_image
    reactant_indices  : which structures (by index) are reactants
    product_indices   : which structures (by index) are products
    conditions_above  : text lines for above the arrow
    conditions_below  : text lines for below the arrow
    verbose           : print layout info to stderr
    expanded_above    : pre-resolved expanded conditions for above (from --expand)
    expanded_below    : pre-resolved expanded conditions for below (from --expand)

    Returns
    -------
    CDXML document string
    """
    def log(msg: str):
        if verbose:
            print(f"[reaction_from_image] {msg}", file=sys.stderr)

    # Validate indices
    n = len(structures)
    for idx in reactant_indices + product_indices:
        if idx < 0 or idx >= n:
            raise ValueError(
                f"Structure index {idx} out of range (0–{n-1}). "
                f"Image yielded {n} structures."
            )

    # Separate reactant and product molecules
    reactant_mols = [structures[i] for i in reactant_indices]
    product_mols  = [structures[i] for i in product_indices]

    # Check that all molecules have atoms
    for side, mols, label in [
        (reactant_indices, reactant_mols, "reactant"),
        (product_indices, product_mols, "product"),
    ]:
        for idx, mol in zip(side, mols):
            if not mol.get("atoms"):
                raise ValueError(
                    f"Structure {idx} ({label}) has no atoms — DECIMER may have "
                    f"failed on this region. SMILES: {mol.get('smiles', '(none)')}"
                )

    # ------------------------------------------------------------------
    # Layout: position molecules left-to-right
    #
    #   [Reactant1] [gap] [Reactant2] [margin] →arrow→ [margin] [Product1]
    #
    # All molecules are centred vertically at VERTICAL_CENTER.
    # ------------------------------------------------------------------

    ids = _IDGen(1000)
    cursor_x = PAGE_LEFT   # running x position

    # Position reactants
    positioned_reactants: List[Dict] = []
    for mol in reactant_mols:
        x0, y0, x1, y1 = _mol_extent(mol)
        mol_w = x1 - x0
        mol_h = y1 - y0
        # Translate: left edge to cursor_x, vertical centre to VERTICAL_CENTER
        dx = cursor_x - x0
        dy = VERTICAL_CENTER - (y0 + y1) / 2.0
        positioned = _translate_mol(mol, dx, dy)
        positioned_reactants.append(positioned)
        cursor_x += mol_w + INTER_MOL_GAP
        log(f"Reactant placed at x=[{cursor_x - mol_w - INTER_MOL_GAP:.1f}, {cursor_x - INTER_MOL_GAP:.1f}]")

    # Arrow position
    arrow_tail_x = cursor_x - INTER_MOL_GAP + ARROW_MARGIN
    arrow_head_x = arrow_tail_x + ARROW_LENGTH
    arrow_y = VERTICAL_CENTER

    log(f"Arrow: tail={arrow_tail_x:.1f}, head={arrow_head_x:.1f}, y={arrow_y:.1f}")

    # Position products
    cursor_x = arrow_head_x + ARROW_MARGIN
    positioned_products: List[Dict] = []
    for mol in product_mols:
        x0, y0, x1, y1 = _mol_extent(mol)
        mol_w = x1 - x0
        dx = cursor_x - x0
        dy = VERTICAL_CENTER - (y0 + y1) / 2.0
        positioned = _translate_mol(mol, dx, dy)
        positioned_products.append(positioned)
        cursor_x += mol_w + INTER_MOL_GAP
        log(f"Product placed at x=[{cursor_x - mol_w - INTER_MOL_GAP:.1f}, {cursor_x - INTER_MOL_GAP:.1f}]")

    # Resolve abbreviations in conditions text
    resolved_above = [resolve_abbreviation(line) for line in conditions_above]
    resolved_below = [resolve_abbreviation(line) for line in conditions_below]

    log(f"Conditions above: {resolved_above}")
    log(f"Conditions below: {resolved_below}")

    # ------------------------------------------------------------------
    # Build XML elements
    # ------------------------------------------------------------------

    fragment_xmls: List[str] = []
    reactant_frag_ids: List[int] = []
    product_frag_ids: List[int] = []

    for mol in positioned_reactants:
        frag_xml, frag_id = _build_fragment(mol["atoms"], mol["bonds"], ids)
        fragment_xmls.append(frag_xml)
        reactant_frag_ids.append(frag_id)

    for mol in positioned_products:
        frag_xml, frag_id = _build_fragment(mol["atoms"], mol["bonds"], ids)
        fragment_xmls.append(frag_xml)
        product_frag_ids.append(frag_id)

    # Conditions: expanded structures or text labels
    above_xmls: List[str] = []
    below_xmls: List[str] = []
    above_ids: List[int] = []
    below_ids: List[int] = []

    arrow_mid_x = (arrow_tail_x + arrow_head_x) / 2.0

    if expanded_above is not None:
        # --expand mode: structures + text fallback
        ax, ai = _layout_expanded_conditions(
            expanded_above, arrow_tail_x, arrow_head_x, arrow_y,
            "above", ids, verbose,
        )
        above_xmls.extend(ax)
        above_ids.extend(ai)
    elif resolved_above:
        n_above = len(resolved_above)
        baseline_y = (arrow_y - CONDITIONS_GAP_ABOVE - CONDITIONS_DESCENDER
                      - (n_above - 1) * CONDITIONS_LINE_HEIGHT)
        txt_xml, txt_id = _build_conditions_text(
            resolved_above, arrow_mid_x, baseline_y, ids
        )
        above_xmls.append(txt_xml)
        above_ids.append(txt_id)

    if expanded_below is not None:
        bx, bi = _layout_expanded_conditions(
            expanded_below, arrow_tail_x, arrow_head_x, arrow_y,
            "below", ids, verbose,
        )
        below_xmls.extend(bx)
        below_ids.extend(bi)
    elif resolved_below:
        ascender = 8.0
        baseline_y = arrow_y + CONDITIONS_GAP_BELOW + ascender
        txt_xml, txt_id = _build_conditions_text(
            resolved_below, arrow_mid_x, baseline_y, ids
        )
        below_xmls.append(txt_xml)
        below_ids.append(txt_id)

    # Arrow
    arrow_xml, arrow_id = _build_arrow(
        arrow_tail_x, arrow_y, arrow_head_x, arrow_y, ids
    )

    # Scheme / step
    scheme_id = ids.next()
    step_id = ids.next()
    step_attrs = [
        f'id="{step_id}"',
        f'ReactionStepReactants="{" ".join(str(i) for i in reactant_frag_ids)}"',
        f'ReactionStepProducts="{" ".join(str(i) for i in product_frag_ids)}"',
        f'ReactionStepArrows="{arrow_id}"',
    ]
    if above_ids:
        step_attrs.append(
            f'ReactionStepObjectsAboveArrow="{" ".join(str(i) for i in above_ids)}"'
        )
    if below_ids:
        step_attrs.append(
            f'ReactionStepObjectsBelowArrow="{" ".join(str(i) for i in below_ids)}"'
        )

    scheme_xml = f'<scheme id="{scheme_id}"><step {" ".join(step_attrs)}/></scheme>'

    # ------------------------------------------------------------------
    # Compute overall bounding box
    # ------------------------------------------------------------------
    all_xs: List[float] = []
    all_ys: List[float] = []
    for mol in positioned_reactants + positioned_products:
        for a in mol["atoms"]:
            all_xs.append(a["x"])
            all_ys.append(a["y"])

    # Include expanded condition fragments in bounding box
    for frag_xml_str in above_xmls + below_xmls:
        if frag_xml_str.lstrip().startswith("<fragment"):
            fx0, fy0, fx1, fy1 = _measure_fragment_xml(frag_xml_str)
            if fx0 != fx1:
                all_xs.extend([fx0, fx1])
                all_ys.extend([fy0, fy1])

    margin = 20.0
    doc_bbox = (
        f"{min(all_xs) - margin:.2f} {min(all_ys) - margin:.2f} "
        f"{max(all_xs) + margin:.2f} {max(all_ys) + margin:.2f}"
    )

    # Page size — generous
    page_w = max(all_xs) + 100
    page_h = max(all_ys) + 100
    page_id = ids.next()

    # ------------------------------------------------------------------
    # Assemble document
    # ------------------------------------------------------------------
    parts = [
        _format_cdxml_header(doc_bbox),
        f'<page id="{page_id}" BoundingBox="0 0 {page_w:.0f} {page_h:.0f}" '
        f'HeaderPosition="36" FooterPosition="36" '
        f'PrintTrimMarks="yes" HeightPages="1" WidthPages="2">',
    ]
    parts.extend(fragment_xmls)
    parts.extend(above_xmls)
    parts.extend(below_xmls)
    parts.append(arrow_xml)
    parts.append(scheme_xml)
    parts.append("</page>")
    parts.append(CDXML_FOOTER)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Fragment XML translation helper (for ChemScript fragments)
# ---------------------------------------------------------------------------

def _translate_fragment_xml(frag_xml: str, dx: float, dy: float) -> str:
    """Shift all coordinate attributes in a fragment XML string by (dx, dy).

    Handles:  p="x y"  and  BoundingBox="x1 y1 x2 y2"
    """
    def shift_p(m: "re.Match") -> str:
        x, y = float(m.group(1)), float(m.group(2))
        return f'p="{x + dx:.3f} {y + dy:.3f}"'

    def shift_bb(m: "re.Match") -> str:
        vals = [float(v) for v in m.group(1).split()]
        shifted = [
            f"{vals[0] + dx:.3f}", f"{vals[1] + dy:.3f}",
            f"{vals[2] + dx:.3f}", f"{vals[3] + dy:.3f}",
        ]
        return f'BoundingBox="{" ".join(shifted)}"'

    frag_xml = re.sub(r'\bp="([-\d.]+)\s+([-\d.]+)"', shift_p, frag_xml)
    frag_xml = re.sub(r'\bBoundingBox="((?:[-\d.]+ ?){4})"', shift_bb, frag_xml)
    return frag_xml


def _measure_fragment_xml(frag_xml: str) -> Tuple[float, float, float, float]:
    """Measure (xmin, ymin, xmax, ymax) from all p="x y" attributes in fragment XML."""
    xs, ys = [], []
    for m in re.finditer(r'\bp="([-\d.]+)\s+([-\d.]+)"', frag_xml):
        xs.append(float(m.group(1)))
        ys.append(float(m.group(2)))
    if not xs:
        return (0, 0, 0, 0)
    return min(xs), min(ys), max(xs), max(ys)


def _best_smiles_component(smiles: str) -> str:
    """For a multi-component SMILES (dot-separated), return the largest
    drug-like component (most heavy atoms, filtering out pure alkyne chains)."""
    components = smiles.split(".")
    if len(components) <= 1:
        return smiles

    best = ""
    best_score = -1
    for comp in components:
        comp = comp.strip()
        if not comp:
            continue
        # Reject pure-alkyne chains
        if re.fullmatch(r'[C#]+', comp):
            continue
        # Score by number of heavy-atom characters
        score = sum(1 for c in comp if c.isalpha() and c.isupper())
        if score > best_score:
            best = comp
            best_score = score

    return best or smiles


# ---------------------------------------------------------------------------
# ChemScript cleanup: SMILES → ChemDraw-native fragment XML
# ---------------------------------------------------------------------------

def _open_chemscript_bridge(verbose: bool = False):
    """Import and open a ChemScriptBridge instance.  Caller must call .close()."""
    import importlib.util
    _dir = os.path.dirname(os.path.abspath(__file__))
    try:
        spec = importlib.util.spec_from_file_location(
            "chemscript_bridge", os.path.join(_dir, "chemscript_bridge.py")
        )
        csb_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(csb_mod)
    except Exception as exc:
        raise ImportError(
            f"Could not import chemscript_bridge.py: {exc}\n"
            "ChemDraw and chemscript_bridge are required."
        ) from exc
    if verbose:
        print("[reaction_from_image] Opening ChemScript bridge...",
              file=sys.stderr)
    return csb_mod.ChemScriptBridge()


def _chemscript_fragment_xmls(
    structures: List[Dict],
    verbose: bool = False,
) -> Dict[int, Tuple[str, float, float, float, float]]:
    """
    For each structure with a valid SMILES, produce a ChemScript-cleaned
    fragment XML string + its bounding box.

    Returns dict: structure_index → (fragment_xml, xmin, ymin, xmax, ymax)
    """
    import xml.etree.ElementTree as ET

    def log(msg: str):
        if verbose:
            print(f"[reaction_from_image] {msg}", file=sys.stderr)

    cs = _open_chemscript_bridge(verbose)

    result: Dict[int, Tuple[str, float, float, float, float]] = {}
    try:
        for i, entry in enumerate(structures):
            smiles = entry.get("smiles", "").strip()
            if not smiles:
                continue
            if "." in smiles:
                smiles = _best_smiles_component(smiles)

            log(f"  ChemScript [{i}]: {smiles[:60]}...")
            try:
                cdxml_str = cs.smiles_to_cdxml(smiles)
            except Exception as exc:
                log(f"  ChemScript failed for [{i}]: {exc}")
                continue

            if not cdxml_str or "<CDXML" not in cdxml_str:
                log(f"  ChemScript returned empty CDXML for [{i}]")
                continue

            # Parse and extract the first <fragment>
            root = ET.fromstring(cdxml_str)
            page_el = root.find("page")
            if page_el is None:
                continue
            frag_el = page_el.find("fragment")
            if frag_el is None:
                continue

            frag_xml = ET.tostring(frag_el, encoding="unicode")

            # Measure bounding box from atom positions
            xmin, ymin, xmax, ymax = _measure_fragment_xml(frag_xml)
            if xmin == xmax:
                continue

            result[i] = (frag_xml, xmin, ymin, xmax, ymax)
            log(f"  ChemScript [{i}]: OK, bbox w={xmax-xmin:.1f} h={ymax-ymin:.1f}")
    finally:
        cs.close()

    return result


# ---------------------------------------------------------------------------
# Build reaction scheme using ChemScript fragments
# ---------------------------------------------------------------------------

def build_reaction_scheme_chemscript(
    structures: List[Dict],
    cs_fragments: Dict[int, Tuple[str, float, float, float, float]],
    reactant_indices: List[int],
    product_indices: List[int],
    conditions_above: List[str],
    conditions_below: List[str],
    verbose: bool = False,
    expanded_above: Optional["ExpandedItems"] = None,
    expanded_below: Optional["ExpandedItems"] = None,
) -> str:
    """
    Assemble a CDXML reaction scheme using ChemScript-cleaned fragment XML.

    Same layout logic as build_reaction_scheme but uses native ChemDraw
    fragments instead of building from atom/bond dicts.
    """
    def log(msg: str):
        if verbose:
            print(f"[reaction_from_image] {msg}", file=sys.stderr)

    # Validate indices — must have ChemScript fragments for all
    for idx in reactant_indices + product_indices:
        if idx not in cs_fragments:
            raise ValueError(
                f"Structure {idx} has no ChemScript fragment — "
                f"cleanup may have failed for this structure."
            )

    ids = _IDGen(1000)
    cursor_x = PAGE_LEFT

    # ------------------------------------------------------------------
    # Layout: translate ChemScript fragments to final positions
    # ------------------------------------------------------------------

    reactant_frag_xmls: List[str] = []
    reactant_extents: List[Tuple[float, float, float, float]] = []

    for idx in reactant_indices:
        frag_xml, xmin, ymin, xmax, ymax = cs_fragments[idx]
        mol_w = xmax - xmin
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        target_cx = cursor_x + mol_w / 2.0
        target_cy = VERTICAL_CENTER
        dx = target_cx - cx
        dy = target_cy - cy
        translated = _translate_fragment_xml(frag_xml, dx, dy)

        # Re-measure to get actual final extent
        fx0, fy0, fx1, fy1 = _measure_fragment_xml(translated)
        reactant_frag_xmls.append(translated)
        reactant_extents.append((fx0, fy0, fx1, fy1))
        cursor_x += mol_w + INTER_MOL_GAP
        log(f"Reactant [{idx}] placed at x=[{cursor_x - mol_w - INTER_MOL_GAP:.1f}, {cursor_x - INTER_MOL_GAP:.1f}]")

    # Arrow
    arrow_tail_x = cursor_x - INTER_MOL_GAP + ARROW_MARGIN
    arrow_head_x = arrow_tail_x + ARROW_LENGTH
    arrow_y = VERTICAL_CENTER
    log(f"Arrow: tail={arrow_tail_x:.1f}, head={arrow_head_x:.1f}, y={arrow_y:.1f}")

    cursor_x = arrow_head_x + ARROW_MARGIN

    product_frag_xmls: List[str] = []
    product_extents: List[Tuple[float, float, float, float]] = []

    for idx in product_indices:
        frag_xml, xmin, ymin, xmax, ymax = cs_fragments[idx]
        mol_w = xmax - xmin
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        target_cx = cursor_x + mol_w / 2.0
        target_cy = VERTICAL_CENTER
        dx = target_cx - cx
        dy = target_cy - cy
        translated = _translate_fragment_xml(frag_xml, dx, dy)

        fx0, fy0, fx1, fy1 = _measure_fragment_xml(translated)
        product_frag_xmls.append(translated)
        product_extents.append((fx0, fy0, fx1, fy1))
        cursor_x += mol_w + INTER_MOL_GAP
        log(f"Product [{idx}] placed at x=[{cursor_x - mol_w - INTER_MOL_GAP:.1f}, {cursor_x - INTER_MOL_GAP:.1f}]")

    # Assign IDs to ChemScript fragments (need IDs for <scheme><step> references)
    # ChemScript fragments already have their own internal IDs; we need to extract
    # the top-level fragment id for the <step> element.
    reactant_frag_ids: List[str] = []
    for xml in reactant_frag_xmls:
        m = re.search(r'<fragment\s+id="(\d+)"', xml)
        if m:
            reactant_frag_ids.append(m.group(1))

    product_frag_ids: List[str] = []
    for xml in product_frag_xmls:
        m = re.search(r'<fragment\s+id="(\d+)"', xml)
        if m:
            product_frag_ids.append(m.group(1))

    # Resolve abbreviations
    resolved_above = [resolve_abbreviation(line) for line in conditions_above]
    resolved_below = [resolve_abbreviation(line) for line in conditions_below]
    log(f"Conditions above: {resolved_above}")
    log(f"Conditions below: {resolved_below}")

    # Conditions: expanded structures or text labels
    above_xmls: List[str] = []
    below_xmls: List[str] = []
    above_ids: List[int] = []
    below_ids: List[int] = []

    arrow_mid_x = (arrow_tail_x + arrow_head_x) / 2.0

    if expanded_above is not None:
        ax, ai = _layout_expanded_conditions(
            expanded_above, arrow_tail_x, arrow_head_x, arrow_y,
            "above", ids, verbose,
        )
        above_xmls.extend(ax)
        above_ids.extend(ai)
    elif resolved_above:
        n_above = len(resolved_above)
        baseline_y = (arrow_y - CONDITIONS_GAP_ABOVE - CONDITIONS_DESCENDER
                      - (n_above - 1) * CONDITIONS_LINE_HEIGHT)
        txt_xml, txt_id = _build_conditions_text(
            resolved_above, arrow_mid_x, baseline_y, ids
        )
        above_xmls.append(txt_xml)
        above_ids.append(txt_id)

    if expanded_below is not None:
        bx, bi = _layout_expanded_conditions(
            expanded_below, arrow_tail_x, arrow_head_x, arrow_y,
            "below", ids, verbose,
        )
        below_xmls.extend(bx)
        below_ids.extend(bi)
    elif resolved_below:
        ascender = 8.0
        baseline_y = arrow_y + CONDITIONS_GAP_BELOW + ascender
        txt_xml, txt_id = _build_conditions_text(
            resolved_below, arrow_mid_x, baseline_y, ids
        )
        below_xmls.append(txt_xml)
        below_ids.append(txt_id)

    # Arrow XML
    arrow_xml, arrow_id = _build_arrow(
        arrow_tail_x, arrow_y, arrow_head_x, arrow_y, ids
    )

    # Scheme / step
    scheme_id = ids.next()
    step_id = ids.next()
    step_attrs = [
        f'id="{step_id}"',
        f'ReactionStepReactants="{" ".join(reactant_frag_ids)}"',
        f'ReactionStepProducts="{" ".join(product_frag_ids)}"',
        f'ReactionStepArrows="{arrow_id}"',
    ]
    if above_ids:
        step_attrs.append(
            f'ReactionStepObjectsAboveArrow="{" ".join(str(i) for i in above_ids)}"'
        )
    if below_ids:
        step_attrs.append(
            f'ReactionStepObjectsBelowArrow="{" ".join(str(i) for i in below_ids)}"'
        )
    scheme_xml = f'<scheme id="{scheme_id}"><step {" ".join(step_attrs)}/></scheme>'

    # Bounding box
    all_extents = reactant_extents + product_extents
    all_x0 = min(e[0] for e in all_extents)
    all_y0 = min(e[1] for e in all_extents)
    all_x1 = max(e[2] for e in all_extents)
    all_y1 = max(e[3] for e in all_extents)

    # Include expanded condition fragments in bounding box
    for frag_xml_str in above_xmls + below_xmls:
        if frag_xml_str.lstrip().startswith("<fragment"):
            fx0, fy0, fx1, fy1 = _measure_fragment_xml(frag_xml_str)
            if fx0 != fx1:
                all_x0 = min(all_x0, fx0)
                all_y0 = min(all_y0, fy0)
                all_x1 = max(all_x1, fx1)
                all_y1 = max(all_y1, fy1)

    margin = 20.0
    doc_bbox = (
        f"{all_x0 - margin:.2f} {all_y0 - margin:.2f} "
        f"{all_x1 + margin:.2f} {all_y1 + margin:.2f}"
    )
    page_w = all_x1 + 100
    page_h = all_y1 + 100
    page_id = ids.next()

    # Assemble
    parts = [
        _format_cdxml_header(doc_bbox),
        f'<page id="{page_id}" BoundingBox="0 0 {page_w:.0f} {page_h:.0f}" '
        f'HeaderPosition="36" FooterPosition="36" '
        f'PrintTrimMarks="yes" HeightPages="1" WidthPages="2">',
    ]
    parts.extend(reactant_frag_xmls)
    parts.extend(product_frag_xmls)
    parts.extend(above_xmls)
    parts.extend(below_xmls)
    parts.append(arrow_xml)
    parts.append(scheme_xml)
    parts.append("</page>")
    parts.append(CDXML_FOOTER)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# High-level pipeline: image + descriptor → CDXML
# ---------------------------------------------------------------------------

def reaction_from_image(
    image_path: str,
    descriptor: Dict,
    page: int = 0,
    segment: bool = True,
    hand_drawn: bool = False,
    verbose: bool = False,
    merge_gap: Optional[int] = None,
    cleanup: bool = False,
    expand: bool = False,
) -> str:
    """
    Full pipeline: image + reaction descriptor → CDXML reaction scheme.

    Parameters
    ----------
    image_path : path to screenshot PNG/JPG/PDF
    descriptor : dict with reactant_indices, product_indices, conditions_above/below
    page       : PDF page number
    segment    : whether to segment the image
    hand_drawn : use hand-drawn DECIMER model
    verbose    : print progress
    merge_gap  : pixel gap for merging nearby boxes (None = adaptive)
    cleanup    : run ChemScript cleanup on structures (ChemDraw-native quality)
    expand     : expand conditions to molecular structures where possible

    Returns
    -------
    CDXML document string
    """
    # Import structure_from_image (sibling module)
    from . import structure_from_image as sfi

    # Step 1: Extract structures (DECIMER)
    if verbose:
        print(f"[reaction_from_image] Extracting structures from {image_path}...",
              file=sys.stderr)

    structures = sfi._extract_structures_raw(
        image_path,
        page=page,
        segment=segment,
        hand_drawn=hand_drawn,
        verbose=verbose,
        merge_gap=merge_gap,
    )

    if verbose:
        print(f"[reaction_from_image] Extracted {len(structures)} structure(s)",
              file=sys.stderr)
        for i, s in enumerate(structures):
            print(f"  [{i}] SMILES={s.get('smiles', '?')}, "
                  f"bbox={s.get('bbox', '?')}, "
                  f"atoms={len(s.get('atoms', []))}",
                  file=sys.stderr)

    reactant_indices = descriptor.get("reactant_indices", [])
    product_indices = descriptor.get("product_indices", [])
    conditions_above = descriptor.get("conditions_above", [])
    conditions_below = descriptor.get("conditions_below", [])

    # Step 2: Optionally expand conditions to structures
    expanded_above = None
    expanded_below = None
    if expand:
        cs_bridge = _open_chemscript_bridge(verbose)
        try:
            if verbose:
                print("[reaction_from_image] Resolving conditions to structures...",
                      file=sys.stderr)
            expanded_above = _resolve_all_conditions(
                conditions_above, cs_bridge, verbose
            )
            expanded_below = _resolve_all_conditions(
                conditions_below, cs_bridge, verbose
            )
        except Exception as exc:
            if verbose:
                print(f"[reaction_from_image] Expand failed: {exc}", file=sys.stderr)
        # Don't close bridge yet if cleanup also needs it

    # Step 3: Build reaction scheme
    if cleanup:
        # Use ChemScript for publication-quality structures
        if verbose:
            print("[reaction_from_image] Running ChemScript cleanup...",
                  file=sys.stderr)
        cs_fragments = _chemscript_fragment_xmls(structures, verbose=verbose)

        cdxml = build_reaction_scheme_chemscript(
            structures=structures,
            cs_fragments=cs_fragments,
            reactant_indices=reactant_indices,
            product_indices=product_indices,
            conditions_above=conditions_above,
            conditions_below=conditions_below,
            verbose=verbose,
            expanded_above=expanded_above,
            expanded_below=expanded_below,
        )
    else:
        # Use RDKit coordinates (faster, no ChemDraw dependency)
        cdxml = build_reaction_scheme(
            structures=structures,
            reactant_indices=reactant_indices,
            product_indices=product_indices,
            conditions_above=conditions_above,
            conditions_below=conditions_below,
            verbose=verbose,
            expanded_above=expanded_above,
            expanded_below=expanded_below,
        )

    return cdxml


# ---------------------------------------------------------------------------
# High-level pipeline: image + descriptor → JSON (ReactionDescriptor)
# ---------------------------------------------------------------------------

def reaction_from_image_to_json(
    image_path: str,
    descriptor: Dict,
    output_path: Optional[str] = None,
    page: int = 0,
    segment: bool = True,
    hand_drawn: bool = False,
    verbose: bool = False,
    merge_gap: Optional[int] = None,
    use_network: bool = True,
) -> "ReactionDescriptor":
    """
    Full pipeline: image + reaction descriptor → ReactionDescriptor JSON.

    Same extraction as :func:`reaction_from_image`, but returns a
    :class:`ReactionDescriptor` (the standard JSON source of truth) instead
    of a CDXML string.  The agent can then render a scheme downstream via
    the scheme DSL if needed.

    Parameters
    ----------
    image_path   : path to screenshot PNG/JPG/PDF
    descriptor   : dict with reactant_indices, product_indices, conditions_above/below
    output_path  : if given, write JSON to this path
    page         : PDF page number
    segment      : whether to segment the image
    hand_drawn   : use hand-drawn DECIMER model
    verbose      : print progress
    merge_gap    : pixel gap for merging nearby boxes (None = adaptive)
    use_network  : allow PubChem lookups for condition name resolution

    Returns
    -------
    ReactionDescriptor
    """
    from ..perception.reaction_parser import (
        ReactionDescriptor, SpeciesDescriptor,
        _resolve_text_label, _compute_all_masses,
    )
    from . import structure_from_image as sfi
    import datetime

    def _log(msg: str):
        if verbose:
            print(f"[reaction_from_image_to_json] {msg}", file=sys.stderr)

    # Step 1: Extract structures (DECIMER)
    _log(f"Extracting structures from {image_path}...")
    structures = sfi._extract_structures_raw(
        image_path,
        page=page,
        segment=segment,
        hand_drawn=hand_drawn,
        verbose=verbose,
        merge_gap=merge_gap,
    )
    _log(f"Extracted {len(structures)} structure(s)")

    reactant_indices = set(descriptor.get("reactant_indices", []))
    product_indices = set(descriptor.get("product_indices", []))
    conditions_above = descriptor.get("conditions_above", [])
    conditions_below = descriptor.get("conditions_below", [])

    db = get_reagent_db()
    species_list: List[SpeciesDescriptor] = []
    warnings: List[str] = []
    sp_idx = 0

    # Step 2: Build SpeciesDescriptor for each extracted structure
    for entry in structures:
        smiles = entry.get("smiles", "").strip()
        idx = entry.get("index", 0)

        if not smiles:
            warnings.append(f"Structure at index {idx}: DECIMER returned no SMILES")
            continue

        # Canonicalize SMILES
        canon_smiles = smiles
        try:
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                canon_smiles = Chem.MolToSmiles(mol)
        except ImportError:
            pass

        # Determine role from descriptor indices
        if idx in reactant_indices:
            role = "atom_contributing"
            is_sm = (idx == min(reactant_indices))  # first reactant = SM
        elif idx in product_indices:
            role = "product"
            is_sm = False
        else:
            role = "non_contributing"
            is_sm = False

        is_dp = (role == "product" and
                 (len(product_indices) == 1 or idx == min(product_indices)))

        # Try to get a display name from reagent DB (by SMILES)
        display = db.display_for_smiles(canon_smiles) if canon_smiles else None
        name = display or canon_smiles

        # Role detail from reagent DB (by SMILES)
        role_detail = db.role_for_smiles(canon_smiles) if canon_smiles else None

        # Build original_geometry from extracted atoms/bonds
        atoms = entry.get("atoms", [])
        bonds = entry.get("bonds", [])
        original_geometry = None
        if atoms:
            original_geometry = {
                "atoms": [
                    {k: v for k, v in a.items()
                     if k in ("index", "x", "y", "symbol", "num_hydrogens", "charge")}
                    for a in atoms
                ],
                "bonds": [
                    {k: v for k, v in b.items()
                     if k in ("index", "atom1", "atom2", "order", "cfg", "double_pos")}
                    for b in bonds
                ],
            }

        sp = SpeciesDescriptor(
            id=f"sp_{sp_idx}",
            smiles=canon_smiles,
            name=name,
            role=role,
            role_detail=role_detail,
            classification_method="image_descriptor",
            is_sm=is_sm,
            is_dp=is_dp,
            source="image",
            display_text=name,
            original_geometry=original_geometry,
        )
        species_list.append(sp)
        sp_idx += 1

    # Step 3: Resolve conditions text to species or condition strings
    condition_strings: List[str] = []
    all_conditions = conditions_above + conditions_below

    for cond_text in all_conditions:
        cond_text = cond_text.strip()
        if not cond_text:
            continue

        # Non-chemistry text goes straight to conditions
        if _is_non_chemistry_text(cond_text):
            condition_strings.append(cond_text)
            continue

        # Try to resolve to SMILES
        smi = _resolve_text_label(cond_text, use_network=use_network)
        if smi:
            # Get display name and role from reagent DB
            display = db.display_for_name(cond_text) or cond_text
            role_detail = db.role_for_name(cond_text)

            sp = SpeciesDescriptor(
                id=f"sp_{sp_idx}",
                smiles=smi,
                name=display,
                role="non_contributing",
                role_detail=role_detail,
                classification_method="name_resolution",
                source="text_label",
                display_text=display,
            )
            species_list.append(sp)
            sp_idx += 1
        else:
            # Could not resolve — store as condition text
            condition_strings.append(cond_text)

    # Step 4: Compute masses, formulas, adducts for all species
    _compute_all_masses(species_list)

    # Step 5: Build the reaction SMILES
    reaction_smiles = None
    try:
        reactant_smis = [sp.smiles for sp in species_list
                         if sp.role == "atom_contributing" and sp.smiles]
        product_smis = [sp.smiles for sp in species_list
                        if sp.role == "product" and sp.smiles]
        if reactant_smis and product_smis:
            reaction_smiles = (
                ".".join(reactant_smis) + ">>" + ".".join(product_smis)
            )
    except Exception:
        pass

    desc = ReactionDescriptor(
        version="1.3",
        experiment="",
        input_files={"image": os.path.abspath(image_path)},
        reaction_smiles=reaction_smiles,
        species=species_list,
        warnings=warnings,
        metadata={
            "parser_version": "reaction_from_image 1.0",
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "image",
        },
        conditions=condition_strings,
    )

    if output_path:
        desc.to_json(output_path)
        _log(f"Wrote {output_path}")

    return desc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _structures_json_to_descriptor(
    structures: List[Dict],
    descriptor: Dict,
    source_path: str,
    verbose: bool = False,
) -> "ReactionDescriptor":
    """Build a ReactionDescriptor from pre-extracted structures + descriptor.

    Used when --structures-json is combined with --format json in the CLI.
    """
    from ..perception.reaction_parser import (
        ReactionDescriptor, SpeciesDescriptor,
        _resolve_text_label, _compute_all_masses,
    )
    import datetime

    db = get_reagent_db()
    reactant_indices = set(descriptor.get("reactant_indices", []))
    product_indices = set(descriptor.get("product_indices", []))
    conditions_above = descriptor.get("conditions_above", [])
    conditions_below = descriptor.get("conditions_below", [])

    species_list: List[SpeciesDescriptor] = []
    warnings: List[str] = []
    sp_idx = 0

    for entry in structures:
        smiles = entry.get("smiles", "").strip()
        idx = entry.get("index", 0)
        if not smiles:
            warnings.append(f"Structure at index {idx}: no SMILES")
            continue

        canon_smiles = smiles
        try:
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                canon_smiles = Chem.MolToSmiles(mol)
        except ImportError:
            pass

        if idx in reactant_indices:
            role = "atom_contributing"
            is_sm = (idx == min(reactant_indices))
        elif idx in product_indices:
            role = "product"
            is_sm = False
        else:
            role = "non_contributing"
            is_sm = False

        is_dp = (role == "product" and
                 (len(product_indices) == 1 or idx == min(product_indices)))

        display = db.display_for_smiles(canon_smiles) if canon_smiles else None
        name = display or canon_smiles
        role_detail = db.role_for_smiles(canon_smiles) if canon_smiles else None

        atoms = entry.get("atoms", [])
        bonds = entry.get("bonds", [])
        original_geometry = None
        if atoms:
            original_geometry = {
                "atoms": [
                    {k: v for k, v in a.items()
                     if k in ("index", "x", "y", "symbol", "num_hydrogens", "charge")}
                    for a in atoms
                ],
                "bonds": [
                    {k: v for k, v in b.items()
                     if k in ("index", "atom1", "atom2", "order", "cfg", "double_pos")}
                    for b in bonds
                ],
            }

        sp = SpeciesDescriptor(
            id=f"sp_{sp_idx}",
            smiles=canon_smiles,
            name=name,
            role=role,
            role_detail=role_detail,
            classification_method="image_descriptor",
            is_sm=is_sm,
            is_dp=is_dp,
            source="image",
            display_text=name,
            original_geometry=original_geometry,
        )
        species_list.append(sp)
        sp_idx += 1

    condition_strings: List[str] = []
    for cond_text in conditions_above + conditions_below:
        cond_text = cond_text.strip()
        if not cond_text:
            continue
        if _is_non_chemistry_text(cond_text):
            condition_strings.append(cond_text)
            continue
        smi = _resolve_text_label(cond_text, use_network=True)
        if smi:
            display = db.display_for_name(cond_text) or cond_text
            role_detail_cond = db.role_for_name(cond_text)
            sp = SpeciesDescriptor(
                id=f"sp_{sp_idx}",
                smiles=smi,
                name=display,
                role="non_contributing",
                role_detail=role_detail_cond,
                classification_method="name_resolution",
                source="text_label",
                display_text=display,
            )
            species_list.append(sp)
            sp_idx += 1
        else:
            condition_strings.append(cond_text)

    _compute_all_masses(species_list)

    reaction_smiles = None
    try:
        r_smis = [sp.smiles for sp in species_list
                  if sp.role == "atom_contributing" and sp.smiles]
        p_smis = [sp.smiles for sp in species_list
                  if sp.role == "product" and sp.smiles]
        if r_smis and p_smis:
            reaction_smiles = ".".join(r_smis) + ">>" + ".".join(p_smis)
    except Exception:
        pass

    return ReactionDescriptor(
        version="1.3",
        experiment="",
        input_files={"structures_json": os.path.abspath(source_path)},
        reaction_smiles=reaction_smiles,
        species=species_list,
        warnings=warnings,
        metadata={
            "parser_version": "reaction_from_image 1.0",
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "image",
        },
        conditions=condition_strings,
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Build a ChemDraw reaction scheme (CDXML) from a screenshot image. "
            "Requires a JSON descriptor specifying which structures are reactants/products "
            "and what conditions text to include."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--image", "-i",
        default=None,
        help="Input image file (PNG/JPG/PDF). Required unless --structures-json is used.",
    )
    p.add_argument(
        "--descriptor", "-d",
        required=True,
        help="JSON descriptor file (or '-' for stdin)",
    )
    p.add_argument(
        "--output", "-o",
        default=None,
        help="Output CDXML file (default: <image_stem>_scheme.cdxml)",
    )
    p.add_argument(
        "--page",
        type=int,
        default=0,
        help="PDF page number, 0-indexed (default: 0)",
    )
    p.add_argument(
        "--no-segment",
        action="store_true",
        help="Don't segment — treat each region as one structure",
    )
    p.add_argument(
        "--hand-drawn",
        action="store_true",
        help="Use DECIMER hand-drawn model",
    )
    p.add_argument(
        "--gap",
        type=int,
        default=None,
        help="Merge gap in pixels for segmentation (default: adaptive)",
    )
    p.add_argument(
        "--cleanup",
        action="store_true",
        help="Run ChemScript cleanup on extracted structures",
    )
    p.add_argument(
        "--expand",
        action="store_true",
        help=(
            "Expand conditions to molecular structures where possible. "
            "Uses ChemScript name resolution and PubChem lookup. "
            "Falls back to text labels for unresolvable conditions."
        ),
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress to stderr",
    )
    p.add_argument(
        "--structures-json",
        default=None,
        help=(
            "Path to a pre-extracted structures JSON file "
            "(from structure_from_image.py). Skips DECIMER extraction."
        ),
    )
    p.add_argument(
        "--format",
        choices=["cdxml", "json"],
        default="cdxml",
        help=(
            "Output format (default: cdxml). 'json' produces a "
            "ReactionDescriptor JSON file (same format as cdxml-parse)."
        ),
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Validate: --image is required unless --structures-json is used
    if args.image is None and args.structures_json is None:
        parser.error("--image is required unless --structures-json is provided")

    # Load descriptor
    if args.descriptor == "-":
        descriptor = json.load(sys.stdin)
    else:
        with open(args.descriptor, encoding="utf-8") as f:
            descriptor = json.load(f)

    # Output path
    ext = ".json" if args.format == "json" else ".cdxml"
    if args.output is None:
        if args.image:
            stem = os.path.splitext(os.path.basename(args.image))[0]
        else:
            stem = os.path.splitext(os.path.basename(args.structures_json))[0]
        args.output = stem + ("_reaction" + ext if args.format == "json"
                              else "_scheme" + ext)

    # --- JSON output path: use reaction_from_image_to_json() ---
    if args.format == "json":
        if args.image:
            desc = reaction_from_image_to_json(
                image_path=args.image,
                descriptor=descriptor,
                output_path=args.output,
                page=args.page,
                segment=not args.no_segment,
                hand_drawn=args.hand_drawn,
                verbose=args.verbose,
                merge_gap=args.gap,
            )
        else:
            # --structures-json provided: build descriptor from pre-extracted
            from . import structure_from_image as sfi
            with open(args.structures_json, encoding="utf-8") as f:
                structures = json.load(f)
            # Synthesize an image path for metadata
            desc = _structures_json_to_descriptor(
                structures, descriptor, args.structures_json, args.verbose,
            )
            desc.to_json(args.output)

        print(f"Written reaction JSON to {args.output}", file=sys.stderr)
        return 0

    # --- CDXML output path (existing behaviour) ---
    if args.structures_json:
        with open(args.structures_json, encoding="utf-8") as f:
            structures = json.load(f)

        if args.verbose:
            print(f"[reaction_from_image] Loaded {len(structures)} structures "
                  f"from {args.structures_json}", file=sys.stderr)
            for i, s in enumerate(structures):
                print(f"  [{i}] SMILES={s.get('smiles', '?')}, "
                      f"atoms={len(s.get('atoms', []))}",
                      file=sys.stderr)

        reactant_indices = descriptor.get("reactant_indices", [])
        product_indices = descriptor.get("product_indices", [])
        conditions_above = descriptor.get("conditions_above", [])
        conditions_below = descriptor.get("conditions_below", [])

        # Resolve conditions to structures if --expand
        expanded_above = None
        expanded_below = None
        if args.expand:
            cs_bridge = _open_chemscript_bridge(args.verbose)
            try:
                if args.verbose:
                    print("[reaction_from_image] Resolving conditions to structures...",
                          file=sys.stderr)
                expanded_above = _resolve_all_conditions(
                    conditions_above, cs_bridge, args.verbose
                )
                expanded_below = _resolve_all_conditions(
                    conditions_below, cs_bridge, args.verbose
                )
            finally:
                cs_bridge.close()

        if args.cleanup:
            if args.verbose:
                print("[reaction_from_image] Running ChemScript cleanup...",
                      file=sys.stderr)
            cs_fragments = _chemscript_fragment_xmls(structures, verbose=args.verbose)
            cdxml = build_reaction_scheme_chemscript(
                structures=structures,
                cs_fragments=cs_fragments,
                reactant_indices=reactant_indices,
                product_indices=product_indices,
                conditions_above=conditions_above,
                conditions_below=conditions_below,
                verbose=args.verbose,
                expanded_above=expanded_above,
                expanded_below=expanded_below,
            )
        else:
            cdxml = build_reaction_scheme(
                structures=structures,
                reactant_indices=reactant_indices,
                product_indices=product_indices,
                conditions_above=conditions_above,
                conditions_below=conditions_below,
                verbose=args.verbose,
                expanded_above=expanded_above,
                expanded_below=expanded_below,
            )
    else:
        cdxml = reaction_from_image(
            image_path=args.image,
            descriptor=descriptor,
            page=args.page,
            segment=not args.no_segment,
            hand_drawn=args.hand_drawn,
            verbose=args.verbose,
            merge_gap=args.gap,
            cleanup=args.cleanup,
            expand=args.expand,
        )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(cdxml)

    print(f"Written reaction scheme to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
