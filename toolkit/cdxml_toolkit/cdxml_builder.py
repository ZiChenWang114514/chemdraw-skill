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
from typing import Any, Dict, List, Optional, Tuple
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
from .cdxml_utils import hydrogens_lead

# Element numbers for all 118 IUPAC elements
ELEMENT_NUMBERS: Dict[str, int] = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
    "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
    "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34,
    "Br": 35, "Kr": 36, "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42,
    "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49, "Sn": 50,
    "Sb": 51, "Te": 52, "I": 53, "Xe": 54, "Cs": 55, "Ba": 56, "La": 57, "Ce": 58,
    "Pr": 59, "Nd": 60, "Pm": 61, "Sm": 62, "Eu": 63, "Gd": 64, "Tb": 65, "Dy": 66,
    "Ho": 67, "Er": 68, "Tm": 69, "Yb": 70, "Lu": 71, "Hf": 72, "Ta": 73, "W": 74,
    "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80, "Tl": 81, "Pb": 82,
    "Bi": 83, "Po": 84, "At": 85, "Rn": 86, "Fr": 87, "Ra": 88, "Ac": 89, "Th": 90,
    "Pa": 91, "U": 92, "Np": 93, "Pu": 94, "Am": 95, "Cm": 96, "Bk": 97, "Cf": 98,
    "Es": 99, "Fm": 100, "Md": 101, "No": 102, "Lr": 103, "Rf": 104, "Db": 105,
    "Sg": 106, "Bh": 107, "Hs": 108, "Mt": 109, "Ds": 110, "Rg": 111, "Cn": 112,
    "Nh": 113, "Fl": 114, "Mc": 115, "Lv": 116, "Ts": 117, "Og": 118,
}
try:
    from rdkit import Chem as _Chem
    _pt = _Chem.GetPeriodicTable()
    for _z in range(1, 119):
        _sym = _pt.GetElementSymbol(_z)
        if _sym:
            ELEMENT_NUMBERS[_sym] = _z
except Exception:
    pass

_ELEMENT_NUMBERS = ELEMENT_NUMBERS


def element_number(symbol: str) -> int:
    """Atomic number for *symbol*; 0 only when the symbol is not an element."""
    if symbol in ELEMENT_NUMBERS:
        return ELEMENT_NUMBERS[symbol]
    try:
        from rdkit import Chem
        return Chem.GetPeriodicTable().GetAtomicNumber(symbol)
    except Exception:
        return 0


# Two-character element symbols (need special handling in label alignment)
WIDE_SYMBOLS = {"Br", "Cl", "Si", "Se", "Cs"}

# Bond order -> CDXML Order attribute (1 is default so we can omit it)
BOND_ORDER_ATTR: Dict[Any, Optional[str]] = {
    1: None,   # single -- omit Order attribute
    2: "2",
    3: "3",
    4: "1.5",  # aromatic rendered as 1.5 in ChemDraw
    9: "dative",
    "1": None,
    "2": "2",
    "3": "3",
    "1.5": "1.5",
    "dative": "dative",
    "DATIVE": "dative",
    "DATIVER": "dative",
    "DATIVEL": "dative",
    "DATIVEONE": "dative",
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
            el_num = element_number(sym)
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

        # Charge & Radical
        charge = a.get("charge", 0)
        rad = a.get("radical")
        rad_attr_val: Optional[str] = None
        if isinstance(rad, str) and rad in ("Doublet", "Triplet", "Singlet", "Diradical"):
            rad_attr_val = "Triplet" if rad == "Diradical" else rad
        else:
            n_rad = int(rad) if isinstance(rad, (int, float)) else int(a.get("num_radical_electrons", 0))
            if n_rad == 1:
                rad_attr_val = "Doublet"
            elif n_rad >= 2:
                rad_attr_val = "Triplet"

        if not is_carbon:
            el_num = element_number(sym)
            if el_num:
                attrs.append(f'Element="{el_num}"')
            nh = a.get("num_hydrogens", 0)
            attrs.append(f'NumHydrogens="{nh}"')
            attrs.append('NeedsClean="yes"')
            attrs.append('AS="N"')
        elif (charge or rad_attr_val or a.get("isotope")) and "num_hydrogens" in a:
            attrs.append(f'NumHydrogens="{a["num_hydrogens"]}"')

        if charge:
            attrs.append(f'Charge="{charge}"')
        if rad_attr_val:
            attrs.append(f'Radical="{rad_attr_val}"')
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
            # Carbon: no Element, no label
            lines.append(f'<n {" ".join(attrs)}/>')
        else:
            # Heteroatom: needs <t> child label
            # Label position: offset from atom centre
            lx = ax - 3.25
            ly = ay + 3.52
            bbox = _label_bbox(ax, ay, sym)

            # Build label text including hydrogens: "N" -> "NH", "O" -> "OH",
            # standalone binary hydrides: "H2O", "HCl", "H2S", "HF", "HBr", "HI"
            nh = a.get("num_hydrogens", 0)
            is_unbonded = not any(
                b.get("atom1") == a["index"] or b.get("atom2") == a["index"]
                for b in bonds
            )
            if not charge and is_unbonded and hydrogens_lead(sym, nh):
                label_text = ("H" if nh == 1 else f"H{nh}") + xml_escape(sym)
            elif nh == 1:
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

        order_str_upper = str(order).upper()
        if order_str_upper.endswith("DATIVEL"):
            a1_xml, a2_xml = a2_xml, a1_xml
            order_attr: Optional[str] = "dative"
        elif b.get("dative") or "DATIVE" in order_str_upper:
            order_attr = "dative"
        else:
            order_attr = BOND_ORDER_ATTR.get(order)

        attrs = [
            f'id="{bond_xml_id}"',
            f'Z="{z}"',
            f'B="{a1_xml}"',
            f'E="{a2_xml}"',
        ]

        if order_attr:
            attrs.append(f'Order="{order_attr}"')

        double_pos = b.get("double_pos", "")
        if double_pos:
            attrs.append(f'DoublePosition="{double_pos}"')

        if cfg and cfg in BOND_STEREO_ATTR:
            attrs.append(f'Display="{BOND_STEREO_ATTR[cfg]}"')
        elif order == 1 and not order_attr:
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
# Public API -- single molecule & RDKit Mol conversion
# ---------------------------------------------------------------------------

def mol_to_atom_bond_dicts(
    mol_or_smiles: Any,
    offset_index: int = 0,
    normalize: bool = True,
    center_x: float = 200.0,
    center_y: float = 300.0,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Convert an RDKit Mol or SMILES string into (atoms, bonds) dicts preserving
    dative/coordination bonds (Order="dative"), radicals (Radical="Doublet" / "Triplet"),
    and axial chirality / tetrahedral stereochemistry.
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from .chemistry_semantics import _elemental_metal, require_supported, semantic_key

    if isinstance(mol_or_smiles, str):
        mol = Chem.MolFromSmiles(mol_or_smiles)
    else:
        mol = Chem.Mol(mol_or_smiles) if mol_or_smiles is not None else None
    if mol is None:
        raise ValueError("Invalid chemical structure.")

    require_supported(mol, allow_radicals=True, allow_dative=True, allow_atropisomers=True)
    source_cx = semantic_key(mol)

    if mol.GetNumConformers() == 0:
        AllChem.Compute2DCoords(mol)

    mol_kek = Chem.RWMol(mol)
    try:
        Chem.Kekulize(mol_kek, clearAromaticFlags=True)
        mol = mol_kek.GetMol()
    except Exception:
        pass

    Chem.WedgeMolBonds(mol, mol.GetConformer())

    enhanced = {}
    group_names = {
        Chem.StereoGroupType.STEREO_AND: "And",
        Chem.StereoGroupType.STEREO_OR: "Or",
        Chem.StereoGroupType.STEREO_ABSOLUTE: "Absolute",
    }
    for group_num, group in enumerate(mol.GetStereoGroups(), 1):
        for atom in group.GetAtoms():
            enhanced[atom.GetIdx()] = (group_names[group.GetGroupType()], group_num)

    conf = mol.GetConformer()
    atoms: List[Dict] = []
    rdkit_to_local: Dict[int, int] = {}
    for i, atom in enumerate(mol.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        local_idx = i + 1 + offset_index
        rdkit_to_local[i] = local_idx
        sym = atom.GetSymbol()
        a: Dict[str, Any] = {
            "index": local_idx,
            "symbol": sym,
            "x": round(float(pos.x), 4),
            "y": round(float(pos.y), 4),
            "atomic_number": atom.GetAtomicNum(),
        }
        if atom.GetAtomicNum() == 0:
            a["is_generic"] = True
            a["generic_label"] = "R"
            a["node_type"] = "GenericNickname"
        charge = atom.GetFormalCharge()
        if charge != 0:
            a["charge"] = charge
        isotope = atom.GetIsotope()
        if isotope:
            a["isotope"] = isotope
        n_rad = atom.GetNumRadicalElectrons()
        if n_rad > 0 and not _elemental_metal(atom):
            a["num_radical_electrons"] = n_rad
            a["radical"] = "Doublet" if n_rad == 1 else "Triplet"
        nh = 0 if _elemental_metal(atom) else atom.GetTotalNumHs(includeNeighbors=False)
        if sym != "C" or charge or isotope or a.get("radical"):
            a["num_hydrogens"] = nh
        if i in enhanced:
            a["enhanced_stereo_type"], a["enhanced_stereo_group"] = enhanced[i]
        if i == 0:
            a["_source_cxsmiles"] = source_cx
        atoms.append(a)

    bonds: List[Dict] = []
    order_map = {
        Chem.BondType.SINGLE: 1,
        Chem.BondType.DOUBLE: 2,
        Chem.BondType.TRIPLE: 3,
        Chem.BondType.AROMATIC: 2,
    }
    dative_right = {
        Chem.BondType.DATIVE,
        Chem.BondType.DATIVER,
        Chem.BondType.DATIVEONE,
    }
    for bi, bond in enumerate(mol.GetBonds()):
        bt = bond.GetBondType()
        a1 = rdkit_to_local[bond.GetBeginAtomIdx()]
        a2 = rdkit_to_local[bond.GetEndAtomIdx()]
        if bt in dative_right:
            order: Any = "dative"
        elif bt == Chem.BondType.DATIVEL:
            order = "dative"
            a1, a2 = a2, a1
        else:
            order = order_map.get(bt, 1)

        cfg = 0
        bd = bond.GetBondDir()
        if bd == Chem.BondDir.BEGINWEDGE:
            cfg = 1
        elif bd == Chem.BondDir.BEGINDASH:
            cfg = 6
        elif bd in (Chem.BondDir.UNKNOWN, Chem.BondDir.EITHERDOUBLE):
            cfg = 4

        bond_dict: Dict[str, Any] = {
            "index": bi + 1 + offset_index,
            "order": order,
            "atom1": a1,
            "atom2": a2,
            "cfg": cfg,
        }
        bonds.append(bond_dict)

    if normalize and atoms:
        for a in atoms:
            a["y"] = -a["y"]
        xy = {a["index"]: (a["x"], a["y"]) for a in atoms}
        lengths = [
            math.hypot(xy[b["atom1"]][0] - xy[b["atom2"]][0], xy[b["atom1"]][1] - xy[b["atom2"]][1])
            for b in bonds
            if b["atom1"] in xy and b["atom2"] in xy
            and math.hypot(xy[b["atom1"]][0] - xy[b["atom2"]][0], xy[b["atom1"]][1] - xy[b["atom2"]][1]) > 1e-6
        ]
        avg_bl = sum(lengths) / len(lengths) if lengths else 1.5
        scale = float(ACS_BOND_LENGTH) / avg_bl if avg_bl > 1e-6 else float(ACS_BOND_LENGTH)
        for a in atoms:
            a["x"] *= scale
            a["y"] *= scale
        xs = [a["x"] for a in atoms]
        ys = [a["y"] for a in atoms]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        for a in atoms:
            a["x"] = round(a["x"] - cx + center_x, 3)
            a["y"] = round(a["y"] - cy + center_y, 3)

    return atoms, bonds


def mol_to_cdxml(mol_or_smiles: Any, start_id: int = 1000) -> str:
    """Build a complete CDXML document directly from an RDKit Mol or SMILES string."""
    atoms, bonds = mol_to_atom_bond_dicts(mol_or_smiles, normalize=True)
    return build_molecule_cdxml(atoms, bonds, start_id=start_id)


def build_molecule_cdxml(
    atoms: Any,
    bonds: Optional[List[Dict]] = None,
    start_id: int = 1000,
) -> str:
    """
    Build a CDXML document containing a single molecule fragment.

    Parameters
    ----------
    atoms : list of atom dicts (coordinates already in CDXML pts), or an RDKit Mol / SMILES string
    bonds : list of bond dicts (optional if *atoms* is an RDKit Mol, SMILES string, or dict)
    start_id : first XML element id to use

    Returns
    -------
    CDXML document as a string
    """
    if bonds is None:
        if isinstance(atoms, dict) and "atoms" in atoms:
            bonds = atoms.get("bonds", [])
            atoms = atoms["atoms"]
        else:
            atoms, bonds = mol_to_atom_bond_dicts(atoms, normalize=True)

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
