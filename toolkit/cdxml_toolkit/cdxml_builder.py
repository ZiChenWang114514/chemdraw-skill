#!/usr/bin/env python3
"""
cdxml_builder.py — Build valid ChemDraw 16 CDXML from structured atom/bond data.

Produces CDXML that opens correctly in ChemDraw 16 using ACS Document 1996 style:
  BondLength=14.40, ChainAngle=120, Arial 10 pt captions / 9 pt labels.

Modes
-----
Single molecule
    python cdxml_builder.py --input molecule.json --output molecule.cdxml

Reaction scheme
    python cdxml_builder.py --input reaction.json --mode reaction --output scheme.cdxml

Input JSON — single molecule
    {
      "atoms": [
        {"index": 1, "symbol": "C", "x": 150.0, "y": 300.0},
        {"index": 2, "symbol": "N", "x": 164.4, "y": 308.2, "num_hydrogens": 0},
        ...
      ],
      "bonds": [
        {"index": 1, "order": 1, "atom1": 1, "atom2": 2},
        {"index": 2, "order": 2, "atom1": 2, "atom2": 3},
        ...
      ]
    }

Input JSON — reaction
    {
      "reactants": [ <molecule>, ... ],
      "products":  [ <molecule>, ... ],
      "conditions": {
        "above": ["Pd2dba3 (5 mol%)", "BINAP (10 mol%)"],
        "below": ["Cs2CO3 (2 eq.)", "dioxane", "100 °C, 24 h"]
      }
    }

Coordinates must already be in CDXML points (run coord_normalizer.py first).

Atom dict keys
    index        int    atom number (1-based, must be unique)
    symbol       str    element symbol ("C", "N", "Br", …)
    x, y         float  position in CDXML points
    num_hydrogens int   explicit H count (omit or None for C to get implicit)
    cfg          int    stereo flag (1=wedge up, 6=wedge down, 4=either)
    charge       int    formal charge (0 = omit)

Bond dict keys
    index        int    bond number (1-based, must be unique)
    order        int    1=single, 2=double, 3=triple, 4=aromatic
    atom1, atom2 int    atom indices
    cfg          int    stereo: 1=up, 4=either, 6=down (wedge/dash)
    double_pos   str    "Right" | "Left" (for double bonds in rings)
"""

import argparse
import json
import math
import sys
from copy import deepcopy
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape


# ---------------------------------------------------------------------------
# Constants — ACS Document 1996 (from shared constants.py)
# ---------------------------------------------------------------------------

from .constants import (
    ACS_BOND_LENGTH_STR as ACS_BOND_LENGTH,
    ACS_CHAIN_ANGLE_STR as ACS_CHAIN_ANGLE,
    ACS_LABEL_FONT, ACS_LABEL_SIZE, ACS_LABEL_FACE,
    ACS_CAPTION_SIZE, ACS_CAPTION_FACE,
    ACS_LINE_WIDTH, ACS_BOLD_WIDTH, ACS_BOND_SPACING,
    ACS_HASH_SPACING, ACS_MARGIN_WIDTH,
    CDXML_HEADER as _CDXML_HEADER,
    CDXML_FOOTER as _CDXML_FOOTER,
)

# Element numbers for heteroatoms we care about
ELEMENT_NUMBERS: Dict[str, int] = {
    "H":  1,  "B":  5,  "C":  6,  "N":  7,  "O":  8,
    "F":  9,  "Si": 14, "P":  15, "S":  16, "Cl": 17,
    "Se": 34, "Br": 35, "I":  53, "Cs": 55,
}

# Two-character element symbols (need special handling in label alignment)
WIDE_SYMBOLS = {"Br", "Cl", "Si", "Se", "Cs"}

# Bond order → CDXML Order attribute (1 is default so we can omit it)
BOND_ORDER_ATTR: Dict[int, Optional[str]] = {
    1: None,   # single — omit Order attribute
    2: "2",
    3: "3",
    4: "1.5",  # aromatic rendered as 1.5 in ChemDraw
}

# Stereo bond config → ChemDraw BS / Display attribute
BOND_STEREO_ATTR: Dict[int, str] = {
    1: "WedgeBegin",   # solid wedge up
    4: "Wavy",   # unspecified configuration must not become a solid wedge
    6: "WedgedHashBegin",  # dashed wedge
}


# ---------------------------------------------------------------------------
# ID counter
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
# Label position helper
# ---------------------------------------------------------------------------

def _label_offset(symbol: str) -> Tuple[float, float]:
    """
    Return (dx, dy) offset from atom position to the top-left of the <t> label.
    Approximates ChemDraw's own offsets (3.25 pt horizontal, 3.5 pt vertical).
    """
    # ChemDraw positions labels slightly to the left and above the atom centre.
    # Wide symbols shift further left.
    char_w = 7.0 if symbol in WIDE_SYMBOLS else 3.5
    return -char_w + 0.75, -7.5   # dx, dy from atom p to label top-left


def _label_bbox(x: float, y: float, symbol: str) -> str:
    """Return BoundingBox string for a heteroatom label."""
    char_w = 7.0 if symbol in WIDE_SYMBOLS else 6.0
    # p is the bottom of the label in ChemDraw convention
    lx = x - char_w / 2.0
    ty = y - 7.52   # top
    by = y          # bottom ≈ atom y
    rx = lx + char_w
    return f"{lx:.2f} {ty:.2f} {rx:.2f} {by:.2f}"


# ---------------------------------------------------------------------------
# Inner fragment builder for abbreviation nodes
# ---------------------------------------------------------------------------

def _build_abbrev_inner_fragment(
    label_smiles: str,
    anchor_x: float,
    anchor_y: float,
    ids: _IDGen,
) -> str:
    """Build inner ``<fragment>`` XML for a ``NodeType="Fragment"`` abbreviation.

    Generates 2D coords from *label_smiles*, normalises to ACS bond length,
    positions near (*anchor_x*, *anchor_y*), and adds an
    ``ExternalConnectionPoint`` on the first atom (the attachment point).

    Returns the ``<fragment>...</fragment>`` XML string, or ``""`` on failure.
    """
    try:
        from .image.structure_from_image import smiles_to_coords
        from .coord_normalizer import normalize_coords
    except ImportError:
        return ""

    mol_data = smiles_to_coords(label_smiles, offset_index=0)
    if not mol_data or not mol_data.get("atoms"):
        return ""

    atoms, bonds = normalize_coords(
        mol_data["atoms"], mol_data["bonds"],
        center_x=anchor_x, center_y=anchor_y,
        flip_y=True,
    )
    if not atoms:
        return ""

    frag_id = ids.next()
    lines: List[str] = [f'<fragment id="{frag_id}">']

    inner_map: Dict[int, int] = {}
    for a in atoms:
        aid = ids.next()
        inner_map[a["index"]] = aid
        sym = a.get("symbol", "C")
        ax, ay = a["x"], a["y"]
        z = ids.next()
        attrs = [f'id="{aid}"', f'p="{ax:.2f} {ay:.2f}"', f'Z="{z}"']
        if sym != "C":
            el_num = ELEMENT_NUMBERS.get(sym, 0)
            if el_num:
                attrs.append(f'Element="{el_num}"')
            nh = a.get("num_hydrogens", 0)
            attrs.append(f'NumHydrogens="{nh}"')
            attrs.append('NeedsClean="yes"')
        lines.append(f'<n {" ".join(attrs)}/>')

    for b in bonds:
        bid = ids.next()
        z = ids.next()
        a1 = inner_map.get(b["atom1"], 0)
        a2 = inner_map.get(b["atom2"], 0)
        order = b.get("order", 1)
        attrs = [f'id="{bid}"', f'Z="{z}"', f'B="{a1}"', f'E="{a2}"']
        order_attr = BOND_ORDER_ATTR.get(order)
        if order_attr:
            attrs.append(f'Order="{order_attr}"')
        lines.append(f'<b {" ".join(attrs)}/>')

    # ExternalConnectionPoint — bonded to first atom (attachment point)
    ecp_id = ids.next()
    ecp_z = ids.next()
    first_atom = atoms[0]
    ecp_x = first_atom["x"] - 14.4
    ecp_y = first_atom["y"]
    first_inner_id = inner_map.get(first_atom["index"], 0)
    lines.append(
        f'<n id="{ecp_id}" NodeType="ExternalConnectionPoint" '
        f'p="{ecp_x:.2f} {ecp_y:.2f}" Z="{ecp_z}" '
        f'ExternalConnectionNum="1"/>'
    )
    ecp_bond_id = ids.next()
    ecp_bond_z = ids.next()
    lines.append(
        f'<b id="{ecp_bond_id}" Z="{ecp_bond_z}" '
        f'B="{ecp_id}" E="{first_inner_id}"/>'
    )

    lines.append('</fragment>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fragment (molecule) builder
# ---------------------------------------------------------------------------

def _build_fragment(
    atoms: List[Dict],
    bonds: List[Dict],
    ids: _IDGen,
    atom_id_map: Optional[Dict[int, int]] = None,  # out-param: atom index → xml id
) -> Tuple[str, Dict[int, int], int]:
    """
    Build a <fragment> XML string.

    Supports three atom types via optional dict keys:

    * **Normal atoms** — standard CDXML atoms (carbon or heteroatom with label).
    * **Abbreviation atoms** (``is_abbreviation=True``) — rendered as
      ``NodeType="Fragment"`` with an inner ``<fragment>`` and a text label.
      Requires ``abbrev_label``; ``abbrev_smiles`` used for inner fragment.
    * **Generic group atoms** (``is_generic=True``) — rendered as
      ``NodeType="GenericNickname"`` (or other *node_type*) with a text label.
      Requires ``generic_label``.

    Returns (xml_string, atom_id_map, fragment_xml_id).
    atom_id_map maps caller's atom index → the XML element id used.
    """
    if atom_id_map is None:
        atom_id_map = {}

    frag_id = ids.next()

    # Compute bounding box
    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    bb_x1, bb_y1 = min(xs), min(ys)
    bb_x2, bb_y2 = max(xs), max(ys)

    lines: List[str] = []
    lines.append(
        f'<fragment id="{frag_id}" '
        f'BoundingBox="{bb_x1:.2f} {bb_y1:.2f} {bb_x2:.2f} {bb_y2:.2f}" '
        f'Z="{ids.next()}">'
    )

    # Atoms
    for a in atoms:
        atom_xml_id = ids.next()
        atom_id_map[a["index"]] = atom_xml_id

        ax, ay = a["x"], a["y"]
        z = ids.next()

        # ---- Abbreviation group (NodeType="Fragment") ----
        if a.get("is_abbreviation"):
            label = a.get("abbrev_label", "?")
            label_smiles = a.get("abbrev_smiles")

            lines.append(
                f'<n id="{atom_xml_id}" NodeType="Fragment" '
                f'p="{ax:.2f} {ay:.2f}" Z="{z}" AS="N">'
            )

            # Inner fragment from SMILES (optional — ChemDraw needs it)
            if label_smiles:
                inner_xml = _build_abbrev_inner_fragment(
                    label_smiles, ax, ay, ids)
                if inner_xml:
                    lines.append(inner_xml)

            # Label text
            lx = ax - 3.25
            ly = ay + 3.52
            # Estimate bbox based on label length
            label_w = max(len(label) * 5.5, 6.0)
            lbx1 = ax - label_w / 2.0
            lby1 = ay - 7.52
            lbx2 = ax + label_w / 2.0
            lby2 = ay
            tid = ids.next()
            lines.append(
                f'<t id="{tid}" p="{lx:.2f} {ly:.2f}" '
                f'BoundingBox="{lbx1:.2f} {lby1:.2f} {lbx2:.2f} {lby2:.2f}" '
                f'LabelJustification="Left">'
            )
            lines.append(
                f'<s font="{ACS_LABEL_FONT}" size="{ACS_LABEL_SIZE}" '
                f'color="0" face="{ACS_LABEL_FACE}">'
                f'{xml_escape(label)}</s>'
            )
            lines.append('</t>')
            lines.append('</n>')
            continue

        # ---- Generic variable group (R, X, Ar, R1, …) ----
        if a.get("is_generic"):
            label = a.get("generic_label", "R")
            node_type = a.get("node_type", "GenericNickname")

            attrs = [
                f'id="{atom_xml_id}"',
                f'NodeType="{node_type}"',
                f'p="{ax:.2f} {ay:.2f}"',
                f'Z="{z}"',
                f'AS="N"',
            ]
            if node_type == "GenericNickname":
                attrs.append(f'GenericNickname="{xml_escape(label)}"')

            lines.append(f'<n {" ".join(attrs)}>')

            lx = ax - 3.25
            ly = ay + 3.52
            label_w = max(len(label) * 5.5, 6.0)
            lbx1 = ax - label_w / 2.0
            lby1 = ay - 7.52
            lbx2 = ax + label_w / 2.0
            lby2 = ay
            tid = ids.next()
            lines.append(
                f'<t id="{tid}" p="{lx:.2f} {ly:.2f}" '
                f'BoundingBox="{lbx1:.2f} {lby1:.2f} {lbx2:.2f} {lby2:.2f}" '
                f'LabelJustification="Left">'
            )
            lines.append(
                f'<s font="{ACS_LABEL_FONT}" size="{ACS_LABEL_SIZE}" '
                f'color="0" face="{ACS_LABEL_FACE}">'
                f'{xml_escape(label)}</s>'
            )
            lines.append('</t>')
            lines.append('</n>')
            continue

        # ---- Normal atom ----
        sym = a.get("symbol", "C")

        # Base attributes
        attrs = [f'id="{atom_xml_id}"', f'p="{ax:.2f} {ay:.2f}"', f'Z="{z}"']

        is_carbon = (sym == "C")

        # Charge
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
        if a.get('isotope'):
            attrs.append(f'Isotope="{a["isotope"]}"')
        if a.get('enhanced_stereo_type'):
            attrs.append(f'EnhancedStereoType="{a["enhanced_stereo_type"]}"')
            attrs.append(f'EnhancedStereoGroupNum="{a["enhanced_stereo_group"]}"')

        # Stereo cfg (atom)
        cfg = a.get("cfg", 0)
        if cfg:
            attrs.append(f'Stereo="{cfg}"')

        if is_carbon and not charge:
            # Carbon: no Element, no label, no NumHydrogens
            lines.append(f'<n {" ".join(attrs)}/>')
        else:
            # Heteroatom: needs <t> child label
            # Label position: offset from atom centre
            lx = ax - 3.25
            ly = ay + 3.52
            bbox = _label_bbox(ax, ay, sym)

            # Build label text including hydrogens: "N" → "NH", "O" → "OH"
            nh = a.get("num_hydrogens", 0)
            if nh == 1:
                label_text = xml_escape(sym) + "H"
            elif nh > 1:
                label_text = xml_escape(sym) + "H" + str(nh)
            else:
                label_text = xml_escape(sym)
            label_align = ""
            if sym in WIDE_SYMBOLS:
                label_align = ' LabelAlignment="Left"'

            lines.append(f'<n {" ".join(attrs)}>')
            lines.append(
                f'<t p="{lx:.2f} {ly:.2f}" BoundingBox="{bbox}" '
                f'LabelJustification="Left">'
            )
            lines.append(
                f'<s font="{ACS_LABEL_FONT}" size="{ACS_LABEL_SIZE}" '
                f'color="0" face="{ACS_LABEL_FACE}">{label_text}</s>'
            )
            lines.append("</t>")
            lines.append("</n>")

    # Bonds
    for b in bonds:
        bond_xml_id = ids.next()
        z = ids.next()
        a1_xml = atom_id_map.get(b["atom1"], 0)
        a2_xml = atom_id_map.get(b["atom2"], 0)
        order = b.get("order", 1)
        cfg = b.get("cfg", 0)

        attrs = [
            f'id="{bond_xml_id}"',
            f'Z="{z}"',
            f'B="{a1_xml}"',
            f'E="{a2_xml}"',
        ]

        order_attr = BOND_ORDER_ATTR.get(order)
        if order_attr:
            attrs.append(f'Order="{order_attr}"')

        double_pos = b.get("double_pos", "")
        if double_pos:
            attrs.append(f'DoublePosition="{double_pos}"')

        if cfg and cfg in BOND_STEREO_ATTR:
            attrs.append(f'Display="{BOND_STEREO_ATTR[cfg]}"')
        elif order == 1:
            # Default single bond gets BS="N" (normal, no stereo)
            attrs.append('BS="N"')

        lines.append(f'<b {" ".join(attrs)}/>')

    lines.append("</fragment>")
    fragment_xml = "\n".join(lines)
    source_cx = atoms[0].get('_source_cxsmiles') if atoms else None
    if source_cx:
        from .chemistry_semantics import validate_fragment
        validate_fragment(source_cx, fragment_xml)
    return fragment_xml, atom_id_map, frag_id


# ---------------------------------------------------------------------------
# Conditions text builder
# ---------------------------------------------------------------------------

def _build_conditions_text(
    lines: List[str],
    x: float,
    y: float,
    ids: _IDGen,
    justification: str = "Center",
) -> Tuple[str, int]:
    """
    Build a standalone <t> element for reaction conditions (above or below arrow).

    Returns (xml_string, text_xml_id).
    """
    tid = ids.next()
    z = ids.next()

    # Estimate bounding box: ~6 pt per char, 12 pt line height
    max_chars = max((len(ln) for ln in lines), default=1)
    w = max_chars * 5.8
    h = len(lines) * 12.0

    bx1 = x - w / 2.0
    by1 = y - h
    bx2 = x + w / 2.0
    by2 = y

    parts = [
        f'<t id="{tid}" p="{x:.2f} {y:.2f}" '
        f'BoundingBox="{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}" '
        f'Z="{z}" '
        f'CaptionJustification="{justification}" '
        f'Justification="{justification}" '
        f'LineHeight="auto">'
    ]
    text = "\n".join(xml_escape(ln) for ln in lines)
    parts.append(
        f'<s font="{ACS_LABEL_FONT}" size="{ACS_CAPTION_SIZE}" '
        f'color="0" face="{ACS_CAPTION_FACE}">{text}</s>'
    )
    parts.append("</t>")
    return "\n".join(parts), tid


# ---------------------------------------------------------------------------
# Arrow builder
# ---------------------------------------------------------------------------

def _build_arrow(
    tail_x: float, tail_y: float,
    head_x: float, head_y: float,
    ids: _IDGen,
) -> Tuple[str, int]:
    """
    Build an <arrow> element (full solid arrowhead, reaction style).
    Returns (xml_string, arrow_xml_id).
    """
    aid = ids.next()
    z = ids.next()

    # BoundingBox encloses the arrow shaft
    bx1 = min(tail_x, head_x)
    by1 = min(tail_y, head_y) - 4.0
    bx2 = max(tail_x, head_x)
    by2 = max(tail_y, head_y) + 4.0

    # Center3D / MajorAxisEnd3D / MinorAxisEnd3D — ChemDraw uses these for
    # internal geometry but they don't affect display in standard mode.
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
# Page templates
# ---------------------------------------------------------------------------

_PAGE_OPEN = (
    '<page id="{page_id}" BoundingBox="0 0 1620 2160" '
    'HeaderPosition="36" FooterPosition="36" '
    'PrintTrimMarks="yes" HeightPages="3" WidthPages="3">'
)
_PAGE_CLOSE = "</page>"


def _header(bbox: str) -> str:
    return _CDXML_HEADER.format(
        bbox=bbox,
        label_font=ACS_LABEL_FONT,
        label_size=ACS_LABEL_SIZE,
        label_face=ACS_LABEL_FACE,
        caption_size=ACS_CAPTION_SIZE,
        hash_spacing=ACS_HASH_SPACING,
        margin_width=ACS_MARGIN_WIDTH,
        line_width=ACS_LINE_WIDTH,
        bold_width=ACS_BOLD_WIDTH,
        bond_length=ACS_BOND_LENGTH,
        bond_spacing=ACS_BOND_SPACING,
        chain_angle=ACS_CHAIN_ANGLE,
    )


# ---------------------------------------------------------------------------
# Public API — single molecule
# ---------------------------------------------------------------------------

def build_molecule_cdxml(
    atoms: List[Dict],
    bonds: List[Dict],
    start_id: int = 1000,
) -> str:
    """
    Build a CDXML document containing a single molecule fragment.

    Parameters
    ----------
    atoms : list of atom dicts (coordinates already in CDXML pts)
    bonds : list of bond dicts
    start_id : first XML element id to use

    Returns
    -------
    CDXML document as a string
    """
    ids = _IDGen(start_id)

    atom_id_map: Dict[int, int] = {}
    frag_xml, atom_id_map, _ = _build_fragment(atoms, bonds, ids, atom_id_map)

    # Document bounding box
    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    bbox = f"{min(xs):.2f} {min(ys):.2f} {max(xs):.2f} {max(ys):.2f}"

    page_id = ids.next()

    lines = [
        _header(bbox),
        _PAGE_OPEN.format(page_id=page_id),
        frag_xml,
        _PAGE_CLOSE,
        _CDXML_FOOTER,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API — reaction scheme
# ---------------------------------------------------------------------------

def build_reaction_cdxml(
    reactants: List[Dict],
    products: List[Dict],
    conditions: Optional[Dict] = None,
    arrow_y: Optional[float] = None,
    arrow_tail_x: Optional[float] = None,
    arrow_head_x: Optional[float] = None,
    start_id: int = 1000,
) -> str:
    """
    Build a CDXML reaction scheme document.

    Each molecule in reactants/products is a dict::

        {
          "atoms": [...],
          "bonds": [...],
          # optional: "name", "role"
        }

    conditions is a dict::

        {
          "above": ["Pd2dba3 (5 mol%)", "BINAP (10 mol%)"],
          "below": ["Cs2CO3 (2 eq.)", "dioxane", "100 °C, 24 h"]
        }

    Arrow position is auto-calculated from molecule bounding boxes if not given.

    Parameters
    ----------
    reactants : list of molecule dicts
    products  : list of molecule dicts
    conditions: dict with optional "above" and "below" lists of strings
    arrow_y   : y-coordinate of arrow shaft (auto if None)
    arrow_tail_x, arrow_head_x : x-coords of arrow ends (auto if None)
    start_id  : first XML element id

    Returns
    -------
    CDXML document string
    """
    if conditions is None:
        conditions = {}

    ids = _IDGen(start_id)

    # ---- Build all fragment XMLs ----
    all_xml_parts: List[str] = []
    reactant_frag_ids: List[int] = []
    product_frag_ids:  List[int] = []

    # Collect all atom positions to determine arrow y and bounding box
    all_xs: List[float] = []
    all_ys: List[float] = []

    for mol in reactants:
        atom_id_map: Dict[int, int] = {}
        frag_xml, _, frag_id = _build_fragment(
            mol.get("atoms", []), mol.get("bonds", []), ids, atom_id_map
        )
        all_xml_parts.append(frag_xml)
        reactant_frag_ids.append(frag_id)
        for a in mol.get("atoms", []):
            all_xs.append(a["x"])
            all_ys.append(a["y"])

    for mol in products:
        atom_id_map = {}
        frag_xml, _, frag_id = _build_fragment(
            mol.get("atoms", []), mol.get("bonds", []), ids, atom_id_map
        )
        all_xml_parts.append(frag_xml)
        product_frag_ids.append(frag_id)
        for a in mol.get("atoms", []):
            all_xs.append(a["x"])
            all_ys.append(a["y"])

    if not all_xs:
        raise ValueError("No atoms found in reactants or products")

    # ---- Auto-calculate arrow position ----
    # Arrow y: vertical midpoint of all molecules
    mid_y = (min(all_ys) + max(all_ys)) / 2.0
    if arrow_y is None:
        arrow_y = mid_y

    # Arrow x: gap between right edge of last reactant and left edge of first product
    reactant_xs = []
    product_xs  = []
    for mol in reactants:
        reactant_xs.extend(a["x"] for a in mol.get("atoms", []))
    for mol in products:
        product_xs.extend(a["x"] for a in mol.get("atoms", []))

    reactant_right = max(reactant_xs) if reactant_xs else 100.0
    product_left   = min(product_xs)  if product_xs  else 300.0

    gap = product_left - reactant_right
    margin = max(10.0, gap * 0.15)

    if arrow_tail_x is None:
        arrow_tail_x = reactant_right + margin
    if arrow_head_x is None:
        arrow_head_x = product_left - margin

    # ---- Conditions text elements ----
    above_ids: List[int] = []
    below_ids: List[int] = []

    arrow_mid_x = (arrow_tail_x + arrow_head_x) / 2.0

    above_lines = conditions.get("above", [])
    below_lines = conditions.get("below", [])

    above_xml_parts: List[str] = []
    below_xml_parts: List[str] = []

    if above_lines:
        txt_xml, txt_id = _build_conditions_text(
            above_lines,
            x=arrow_mid_x,
            y=arrow_y - 8.0,   # above arrow shaft
            ids=ids,
        )
        above_xml_parts.append(txt_xml)
        above_ids.append(txt_id)

    if below_lines:
        txt_xml, txt_id = _build_conditions_text(
            below_lines,
            x=arrow_mid_x,
            y=arrow_y + 20.0,  # below arrow shaft
            ids=ids,
        )
        below_xml_parts.append(txt_xml)
        below_ids.append(txt_id)

    # ---- Arrow ----
    arrow_xml, arrow_id = _build_arrow(
        tail_x=arrow_tail_x,
        tail_y=arrow_y,
        head_x=arrow_head_x,
        head_y=arrow_y,
        ids=ids,
    )

    # ---- Scheme / step ----
    scheme_id = ids.next()
    step_id   = ids.next()

    reactant_str = " ".join(str(i) for i in reactant_frag_ids)
    product_str  = " ".join(str(i) for i in product_frag_ids)
    above_str    = " ".join(str(i) for i in above_ids)
    below_str    = " ".join(str(i) for i in below_ids)

    step_attrs = [
        f'id="{step_id}"',
        f'ReactionStepReactants="{reactant_str}"',
        f'ReactionStepProducts="{product_str}"',
        f'ReactionStepArrows="{arrow_id}"',
    ]
    if above_str:
        step_attrs.append(f'ReactionStepObjectsAboveArrow="{above_str}"')
    if below_str:
        step_attrs.append(f'ReactionStepObjectsBelowArrow="{below_str}"')

    scheme_xml = (
        f'<scheme id="{scheme_id}">'
        f'<step {" ".join(step_attrs)}/>'
        f'</scheme>'
    )

    # ---- Document bounding box ----
    extra_margin = 20.0
    doc_x1 = min(all_xs) - extra_margin
    doc_y1 = min(all_ys) - extra_margin
    doc_x2 = max(all_xs) + extra_margin
    doc_y2 = max(all_ys) + extra_margin
    doc_bbox = f"{doc_x1:.2f} {doc_y1:.2f} {doc_x2:.2f} {doc_y2:.2f}"

    page_id = ids.next()

    # ---- Assemble document ----
    sections = (
        [_header(doc_bbox)]
        + [_PAGE_OPEN.format(page_id=page_id)]
        + all_xml_parts
        + above_xml_parts
        + below_xml_parts
        + [arrow_xml]
        + [scheme_xml]
        + [_PAGE_CLOSE]
        + [_CDXML_FOOTER]
    )
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Helpers for loading from JSON
# ---------------------------------------------------------------------------

def _load_json(path: str) -> Dict:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build CDXML from structured atom/bond JSON (ACS Document 1996 style).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--input", "-i",
        default="-",
        help="Input JSON file (default: stdin)",
    )
    p.add_argument(
        "--output", "-o",
        default="-",
        help="Output CDXML file (default: stdout)",
    )
    p.add_argument(
        "--mode", "-m",
        choices=["molecule", "reaction"],
        default="molecule",
        help="Output mode: 'molecule' (single fragment) or 'reaction' (scheme with arrow)",
    )
    p.add_argument(
        "--start-id",
        type=int,
        default=1000,
        help="First XML element id to use (default: 1000)",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    data = _load_json(args.input)

    if args.mode == "molecule":
        atoms = data.get("atoms", [])
        bonds = data.get("bonds", [])
        if not atoms:
            print("ERROR: no atoms in input", file=sys.stderr)
            return 1
        cdxml = build_molecule_cdxml(atoms, bonds, start_id=args.start_id)

    else:  # reaction
        reactants  = data.get("reactants", [])
        products   = data.get("products",  [])
        conditions = data.get("conditions", {})
        if not reactants or not products:
            print("ERROR: reaction mode requires 'reactants' and 'products'", file=sys.stderr)
            return 1
        cdxml = build_reaction_cdxml(
            reactants, products, conditions,
            start_id=args.start_id,
        )

    if args.output == "-":
        print(cdxml)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(cdxml)
        print(f"Written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
