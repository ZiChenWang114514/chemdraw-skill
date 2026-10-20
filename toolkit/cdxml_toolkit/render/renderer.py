"""
renderer.py — Render a SchemeDescriptor to a CDXML document.

Supports:
  - linear: single step (substrates → products)
  - sequential: multi-step in a single row
  - wrap: repeat — multi-row L→R with repeated structures
  - wrap: serpentine — zigzag layout (L→R, R→L, L→R, ...) with vertical arrows

Uses RDKit for SMILES → 2D coords (no ChemDraw COM dependency).
Uses cdxml_builder infrastructure for fragment/arrow/text XML generation.
Uses reaction_cleanup-style layout logic for positioning.
"""

from __future__ import annotations

import json
import math
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

from ..constants import (
    ACS_BOND_LENGTH,
    ACS_BOND_LENGTH_STR,
    ACS_BOND_SPACING,
    ACS_BOLD_WIDTH,
    ACS_CAPTION_FACE,
    ACS_CAPTION_SIZE,
    ACS_CHAIN_ANGLE_STR,
    ACS_HASH_SPACING,
    ACS_LABEL_FACE,
    ACS_LABEL_FONT,
    ACS_LABEL_SIZE,
    ACS_LINE_WIDTH,
    ACS_MARGIN_WIDTH,
    CDXML_FOOTER,
    CDXML_HEADER,
    LAYOUT_ABOVE_GAP,
    LAYOUT_BELOW_GAP,
    LAYOUT_FRAG_GAP_BONDS,
    LAYOUT_INTER_GAP_BONDS,
)
from ..text_formatting import build_formatted_s_xml

from .schema import (
    ArrowContent,
    RunArrowEntry,
    SchemeDescriptor,
    SectionDescriptor,
    StepDescriptor,
    StepRunArrows,
    StructureRef,
)


# ---------------------------------------------------------------------------
# Text metrics for Arial 10pt Bold in ChemDraw
# (measured via bbox investigation: 135 fragments, 237 texts, 83 arrows)
# ---------------------------------------------------------------------------

_CHAR_WIDTH = 4.7       # average character width (proportional Arial)
_LINE_ADVANCE = 11.5    # line-to-line distance (ChemDraw ~1.15× multiplier)
_CAP_HEIGHT = 9.1       # baseline to top of uppercase letters
_DESCENT = 2.0          # baseline to bottom of descenders

# Fragment bbox padding beyond atom center positions (half of measured excess)
_FRAG_PAD_W = 3.3       # ±3.3 pt per side (6.6 pt total width excess)
_FRAG_PAD_H = 1.45      # ±1.45 pt per side (2.9 pt total height excess)


# ---------------------------------------------------------------------------
# Multi-row constants
# ---------------------------------------------------------------------------

# Vertical gap between bottom of row N (including run arrows) and top of row N+1.
# ~55 pts matches real Report-scheme-extr-2 inter-row spacing.
ROW_GAP = 55.0


# ---------------------------------------------------------------------------
# Source JSON loader (reaction_parser output)
# ---------------------------------------------------------------------------

def _load_source_json(path: str) -> Dict[str, Dict]:
    """
    Load reaction_parser JSON, build species lookup by ID and by role.

    Returns a dict mapping keys to species dicts. Keys include:
      - species ID ("sp_0", "sp_1", ...)
      - "SM" / "DP" shortcuts
      - lowercase species name
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    lookup: Dict[str, Dict] = {}
    for sp in data.get("species", []):
        sp_id = sp.get("id", "")
        if sp_id:
            lookup[sp_id] = sp
        if sp.get("is_sm"):
            lookup["SM"] = sp
        if sp.get("is_dp"):
            lookup["DP"] = sp
        # Register by lowercase name for flexible matching
        name = sp.get("name", "")
        if name:
            lookup[name.lower()] = sp
        # Register by CSV name too
        csv_name = sp.get("csv_name", "")
        if csv_name:
            lookup[csv_name.lower()] = sp
    return lookup


# ---------------------------------------------------------------------------
# ID generator (same pattern as cdxml_builder)
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
# Resolved structure: SMILES → atoms/bonds in CDXML points
# ---------------------------------------------------------------------------

@dataclass
class ResolvedFragment:
    """A structure that has been resolved to atom/bond data + XML."""
    ref: StructureRef
    atoms: List[Dict]
    bonds: List[Dict]
    xml: str = ""                # <fragment> XML string
    frag_id: int = 0             # XML element ID
    # Bounding box (CDXML points): min_x, min_y, max_x, max_y
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    # Current center position
    cx: float = 0
    cy: float = 0


@dataclass
class ResolvedStep:
    """A step with all structures resolved and laid out."""
    descriptor: StepDescriptor
    substrates: List[ResolvedFragment]
    products: List[ResolvedFragment]
    above_structures: List[ResolvedFragment]
    above_text: List[str]
    below_text: List[str]
    below_structures: List[ResolvedFragment]
    # Arrow geometry (set during layout)
    arrow_tail_x: float = 0
    arrow_tail_y: float = 0
    arrow_head_x: float = 0
    arrow_head_y: float = 0


# ---------------------------------------------------------------------------
# SMILES → atom/bond dicts (using structure_from_image + normalize)
# ---------------------------------------------------------------------------

def _smiles_to_fragment_data(
    smiles: str,
    center_x: float = 200.0,
    center_y: float = 300.0,
) -> Optional[Tuple[List[Dict], List[Dict]]]:
    """
    Convert SMILES to atom/bond dicts in CDXML point coordinates.

    Returns (atoms, bonds) or None on failure.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        raise RuntimeError("RDKit is required for SMILES→structure conversion")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    AllChem.Compute2DCoords(mol)

    # Kekulize for explicit single/double bonds.
    # Use a copy because clearAromaticFlags=True corrupts the mol on failure.
    mol_kek = Chem.RWMol(mol)
    try:
        Chem.Kekulize(mol_kek, clearAromaticFlags=True)
        mol = mol_kek
    except Exception:
        # Kekulization failed — use original mol with aromatic bonds.
        # _rdkit_mol_to_atom_bond_dicts handles AROMATIC → order 2 fallback.
        pass

    # Extract atom/bond dicts
    from ..image.structure_from_image import _rdkit_mol_to_atom_bond_dicts
    atoms, bonds = _rdkit_mol_to_atom_bond_dicts(mol)

    # Normalize to CDXML coordinate space (scale + flip y + center)
    from ..image.structure_from_image import normalize_for_cdxml
    atoms, bonds = normalize_for_cdxml(atoms, bonds, center_x, center_y)

    return atoms, bonds


def _align_mol_to_reference(
    target_mol,
    ref_mol,
    center_x: float = 200.0,
    center_y: float = 300.0,
) -> Optional[Tuple[List[Dict], List[Dict]]]:
    """
    Align target_mol's 2D layout to ref_mol using MCS, then extract
    atom/bond dicts in CDXML coordinates.

    Uses RDKit's GenerateDepictionMatching2DStructure to orient the target
    so its shared scaffold matches the reference orientation.

    Returns (atoms, bonds) or None if alignment fails or MCS is too small.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, rdFMCS
    except ImportError:
        return None

    if target_mol is None or ref_mol is None:
        return None

    # Find MCS between target and reference
    try:
        mcs_result = rdFMCS.FindMCS(
            [target_mol, ref_mol],
            timeout=5,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
        )
    except Exception:
        return None

    if mcs_result.numAtoms < 3:
        return None  # MCS too small for meaningful alignment

    # Build the MCS query mol
    mcs_mol = Chem.MolFromSmarts(mcs_result.smartsString)
    if mcs_mol is None:
        return None

    # Get substructure matches
    ref_match = ref_mol.GetSubstructMatch(mcs_mol)
    target_match = target_mol.GetSubstructMatch(mcs_mol)

    if not ref_match or not target_match:
        return None

    # Build atom map: (ref_idx, target_idx) for MCS atoms
    atom_map = list(zip(ref_match, target_match))

    # Ensure reference has 2D coordinates
    if ref_mol.GetNumConformers() == 0:
        AllChem.Compute2DCoords(ref_mol)

    # Generate aligned 2D coordinates for target
    try:
        AllChem.Compute2DCoords(target_mol)
        AllChem.GenerateDepictionMatching2DStructure(
            target_mol, ref_mol, atomMap=atom_map
        )
    except Exception:
        # Alignment failed — fall back to standard coords
        AllChem.Compute2DCoords(target_mol)

    # Kekulize for explicit bonds
    mol_kek = Chem.RWMol(target_mol)
    try:
        Chem.Kekulize(mol_kek, clearAromaticFlags=True)
        target_mol = mol_kek
    except Exception:
        pass

    # Extract atom/bond dicts
    from ..image.structure_from_image import _rdkit_mol_to_atom_bond_dicts
    atoms, bonds = _rdkit_mol_to_atom_bond_dicts(target_mol)

    # Normalize to CDXML coordinate space
    from ..image.structure_from_image import normalize_for_cdxml
    atoms, bonds = normalize_for_cdxml(atoms, bonds, center_x, center_y)

    return atoms, bonds


# ---------------------------------------------------------------------------
# Fragment XML builder (adapted from cdxml_builder._build_fragment)
# ---------------------------------------------------------------------------

# Element number lookup
ELEMENT_NUMBERS = {
    "H":  1,  "He": 2,  "Li": 3,  "Be": 4,  "B":  5,  "C":  6,  "N":  7,
    "O":  8,  "F":  9,  "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14,
    "P":  15, "S":  16, "Cl": 17, "Ar": 18, "K":  19, "Ca": 20, "Ti": 22,
    "V":  23, "Cr": 24, "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28, "Cu": 29,
    "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34, "Br": 35, "Kr": 36,
    "Rb": 37, "Sr": 38, "Zr": 40, "Mo": 42, "Ru": 44, "Rh": 45, "Pd": 46,
    "Ag": 47, "Cd": 48, "In": 49, "Sn": 50, "Sb": 51, "Te": 52, "I":  53,
    "Xe": 54, "Cs": 55, "Ba": 56, "La": 57, "Ce": 58, "Pr": 59, "Nd": 60,
    "W":  74, "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80,
    "Tl": 81, "Pb": 82, "Bi": 83,
}

# Bond stereo
BOND_STEREO_ATTR = {
    1: "WedgeBegin",
    4: "Wavy",
    6: "WedgedHashBegin",
}


from contextvars import ContextVar

_fragment_receipts = ContextVar('fragment_receipts', default=None)


def _build_fragment(
    atoms: List[Dict],
    bonds: List[Dict],
    ids: _IDGen,
) -> Tuple[str, Dict[int, int], int]:
    """
    Build a <fragment> XML string from atom/bond dicts.

    Returns (xml_string, atom_id_map, fragment_xml_id).
    """
    atom_id_map: Dict[int, int] = {}
    frag_id = ids.next()

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

    for a in atoms:
        atom_xml_id = ids.next()
        atom_id_map[a["index"]] = atom_xml_id
        ax, ay = a["x"], a["y"]
        z = ids.next()

        sym = a.get("symbol", "C")
        elem_num = a.get('atomic_number', ELEMENT_NUMBERS.get(sym, 6))
        nh = a.get("num_hydrogens")
        charge = a.get("charge", 0)
        isotope = a.get("isotope")

        attrs = [
            f'id="{atom_xml_id}"',
            f'p="{ax:.2f} {ay:.2f}"',
            f'Z="{z}"',
        ]

        is_carbon = (sym == "C" and not charge and not isotope)
        is_variable = elem_num == 0
        if is_variable:
            # Element=0 is accepted by some parsers but cannot be opened by
            # ChemDraw. Use its native generic substituent node instead.
            if charge or isotope:
                raise ValueError('Charged or isotopically labelled variable atoms are unsupported')
            attrs.extend(['NodeType="GenericNickname"', 'GenericNickname="R"'])
        elif not is_carbon:
            attrs.append(f'Element="{elem_num}"')
            if nh is not None:
                attrs.append(f'NumHydrogens="{nh}"')
            if isotope:
                attrs.append(f'Isotope="{isotope}"')
            attrs.append('NeedsClean="yes"')
            if charge:
                attrs.append(f'Charge="{charge}"')

        if a.get('enhanced_stereo_type'):
            attrs.append(f'EnhancedStereoType="{a["enhanced_stereo_type"]}"')
            attrs.append(f'EnhancedStereoGroupNum="{a["enhanced_stereo_group"]}"')

        if is_carbon:
            lines.append(f'<n {" ".join(attrs)}/>')
        else:
            # Heteroatom needs a text label
            lines.append(f'<n {" ".join(attrs)}>')
            lx = ax - 3.25
            ly = ay + 3.52
            label_w = max(len(sym) * 5.5, 6.0)
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
            # Use isotope-specific symbol for display (e.g. D for deuterium)
            if is_variable:
                display_text = "R"
            elif sym == "H" and isotope == 2:
                display_text = "D"
            elif sym == "H" and isotope == 3:
                display_text = "T"
            else:
                display_text = sym
                if nh is not None and nh > 0:
                    display_text += "H" if nh == 1 else f"H{nh}"
            if isotope and not (sym == 'H' and isotope in (2, 3)):
                lines.append(
                    f'<s font="{ACS_LABEL_FONT}" size="{ACS_LABEL_SIZE}" '
                    f'color="0" face="64">{int(isotope)}</s>'
                )
            lines.append(
                f'<s font="{ACS_LABEL_FONT}" size="{ACS_LABEL_SIZE}" '
                f'color="0" face="{ACS_LABEL_FACE}">{xml_escape(display_text)}</s>'
            )
            if charge:
                charge_text = (str(abs(charge)) if abs(charge) > 1 else '') + ('+' if charge > 0 else '-')
                lines.append(
                    f'<s font="{ACS_LABEL_FONT}" size="{ACS_LABEL_SIZE}" '
                    f'color="0" face="64">{charge_text}</s>'
                )
            lines.append('</t>')
            lines.append('</n>')

    # Bonds
    for b in bonds:
        bid = ids.next()
        z = ids.next()
        a1 = atom_id_map.get(b["atom1"], 0)
        a2 = atom_id_map.get(b["atom2"], 0)
        order = b.get("order", 1)

        attrs = [
            f'id="{bid}"',
            f'Z="{z}"',
            f'B="{a1}"',
            f'E="{a2}"',
        ]
        if order == 2:
            attrs.append('Order="2"')
        elif order == 3:
            attrs.append('Order="3"')

        cfg = b.get("cfg", 0)
        if cfg in BOND_STEREO_ATTR:
            attrs.append(f'Display="{BOND_STEREO_ATTR[cfg]}"')

        dp = b.get("double_pos")
        if dp:
            attrs.append(f'DoublePosition="{dp}"')

        lines.append(f'<b {" ".join(attrs)}/>')

    lines.append('</fragment>')
    fragment_xml = "\n".join(lines)
    source_cx = atoms[0].get('_source_cxsmiles') if atoms else None
    if source_cx:
        from ..chemistry_semantics import validate_fragment
        receipt = validate_fragment(source_cx, fragment_xml)
        collector = _fragment_receipts.get()
        if collector is not None:
            collector.append({'fragment_id': frag_id, **receipt})
    return fragment_xml, atom_id_map, frag_id


# ---------------------------------------------------------------------------
# Text builder
# ---------------------------------------------------------------------------

def _build_text_element(
    text_lines: List[str],
    x: float,
    y: float,
    ids: _IDGen,
    justification: str = "Center",
    use_formatting: bool = True,
    font_size: Optional[float] = None,
) -> Tuple[str, int]:
    """
    Build a standalone <t> element for condition text.

    Parameters
    ----------
    font_size : float, optional
        Override font size (default: ACS_CAPTION_SIZE, typically 10pt).

    Returns (xml_string, text_xml_id).
    """
    size = float(font_size if font_size is not None else ACS_CAPTION_SIZE)
    scale = size / float(ACS_CAPTION_SIZE)
    char_w = _CHAR_WIDTH * scale
    cap_h = _CAP_HEIGHT * scale
    descent = _DESCENT * scale
    line_adv = _LINE_ADVANCE * scale

    tid = ids.next()
    z = ids.next()

    max_chars = max((len(ln) for ln in text_lines), default=1)
    n = len(text_lines)
    w = max_chars * char_w

    bx1 = x - w / 2.0
    by1 = y - cap_h
    bx2 = x + w / 2.0
    by2 = y + max(0, n - 1) * line_adv + descent

    parts = [
        f'<t id="{tid}" p="{x:.2f} {y:.2f}" '
        f'BoundingBox="{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}" '
        f'Z="{z}" '
        f'CaptionJustification="{justification}" '
        f'Justification="{justification}" '
        f'LineHeight="auto">'
    ]

    if use_formatting:
        # Use chemistry-aware text formatting for each line.
        # ChemDraw requires \n INSIDE <s> text content for line breaks —
        # newlines between XML elements are treated as whitespace.
        formatted_runs = []
        for i, line in enumerate(text_lines):
            run = build_formatted_s_xml(
                line,
                font=ACS_LABEL_FONT,
                size=size,
                color="0",
            )
            if i < len(text_lines) - 1:
                # Inject \n before the closing </s> of this line's last run
                # so ChemDraw renders a line break
                last_close = run.rfind("</s>")
                if last_close >= 0:
                    run = run[:last_close] + "\n" + run[last_close:]
            formatted_runs.append(run)
        parts.append("".join(formatted_runs))
    else:
        text = "\n".join(xml_escape(ln) for ln in text_lines)
        parts.append(
            f'<s font="{ACS_LABEL_FONT}" size="{size}" '
            f'color="0" face="{ACS_CAPTION_FACE}">{text}</s>'
        )

    parts.append("</t>")
    return "\n".join(parts), tid


def _build_label_element(
    label: str,
    x: float,
    y: float,
    ids: _IDGen,
) -> Tuple[str, int]:
    """Build a compound number label (e.g. "1", "2") centered below a structure."""
    return _build_text_element(
        [label], x, y, ids, justification="Center", use_formatting=False,
    )


# ---------------------------------------------------------------------------
# Arrow builder
# ---------------------------------------------------------------------------

def _build_arrow(
    tail_x: float,
    tail_y: float,
    head_x: float,
    head_y: float,
    ids: _IDGen,
    dashed: bool = False,
    nogo: bool = False,
) -> Tuple[str, int]:
    """Build an <arrow> element. Returns (xml_string, arrow_xml_id).

    Parameters
    ----------
    nogo : bool
        If True, adds ``NoGo="Cross"`` — ChemDraw's native failed-arrow
        rendering (bold X through the arrow shaft).
    """
    aid = ids.next()
    z = ids.next()

    bx1 = min(tail_x, head_x)
    by1 = min(tail_y, head_y) - 4.0
    bx2 = max(tail_x, head_x)
    by2 = max(tail_y, head_y) + 4.0

    cx3 = (tail_x + head_x) / 2.0
    cy3 = tail_y + 100.0

    attrs = [
        f'id="{aid}"',
        f'BoundingBox="{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}"',
        f'Z="{z}"',
        f'FillType="None"',
        f'ArrowheadHead="Full"',
        f'ArrowheadType="Solid"',
        f'HeadSize="1000"',
        f'ArrowheadCenterSize="875"',
        f'ArrowheadWidth="250"',
        f'Head3D="{head_x:.2f} {head_y:.2f} 0"',
        f'Tail3D="{tail_x:.2f} {tail_y:.2f} 0"',
        f'LineWidth="{ACS_LINE_WIDTH}"',
    ]

    if dashed:
        attrs.append('LineType="Dashed"')
    if nogo:
        attrs.append('NoGo="Cross"')

    xml = f'<arrow {" ".join(attrs)}/>'
    return xml, aid


def _build_failed_x(
    cx: float,
    cy: float,
    ids: _IDGen,
) -> str:
    """Build a bold 'X' text element centered on an arrow midpoint.

    .. deprecated::
        Use ``NoGo="Cross"`` on the ``<arrow>`` element instead.
        This function is kept for backwards compatibility.
    """
    tid = ids.next()
    z = ids.next()
    # Position slightly above arrow line so X sits centered on it
    py = cy + 3.5  # baseline offset — text anchor is at baseline
    return (
        f'<t id="{tid}" p="{cx:.2f} {py:.2f}" Z="{z}" '
        f'Justification="Center" InterpretChemically="no" '
        f'CaptionJustification="Center">\n'
        f'<s font="{ACS_LABEL_FONT}" size="12" color="0" face="1">X</s>\n'
        f'</t>'
    )


def _is_letter_condition(text_lines: List[str]) -> bool:
    """Check if below-arrow text is a letter condition like 'a' or 'b,c'."""
    if len(text_lines) != 1:
        return False
    import re
    return bool(re.match(r'^[a-z](,\s*[a-z])*$', text_lines[0].strip()))


def _build_letter_label(
    letter: str,
    cx: float,
    y: float,
    ids: _IDGen,
) -> Tuple[str, int]:
    """Build a small letter label centered above an arrow."""
    tid = ids.next()
    z = ids.next()
    # Position slightly above arrow line
    py = y - 6.0
    xml = (
        f'<t id="{tid}" p="{cx:.2f} {py:.2f}" Z="{z}" '
        f'Justification="Center" InterpretChemically="no" '
        f'CaptionJustification="Center">\n'
        f'<s font="{ACS_LABEL_FONT}" size="8" color="0" face="1">'
        f'{xml_escape(letter)}</s>\n'
        f'</t>'
    )
    return xml, tid


def _build_condition_key(
    condition_key: Dict[str, str],
    left_x: float,
    top_y: float,
    ids: _IDGen,
) -> Tuple[str, float]:
    """Build the condition key block below the scheme.

    Returns (xml_string, bottom_y).
    """
    xml_parts: List[str] = []
    y = top_y
    for letter in sorted(condition_key.keys()):
        text = condition_key[letter]
        tid = ids.next()
        z = ids.next()
        # Format: "(a) conditions text" — letter in italic, rest in regular
        # Use build_formatted_s_xml for chemistry-aware subscript formatting
        letter_run = (
            f'<s font="{ACS_LABEL_FONT}" size="{ACS_CAPTION_SIZE}" '
            f'color="0" face="2">({xml_escape(letter)})</s>'
        )
        text_run = build_formatted_s_xml(
            f" {text}",
            font=ACS_LABEL_FONT,
            size=ACS_CAPTION_SIZE,
            color="0",
        )
        xml_parts.append(
            f'<t id="{tid}" p="{left_x:.2f} {y:.2f}" Z="{z}" '
            f'InterpretChemically="no">\n'
            f'{letter_run}{text_run}\n'
            f'</t>'
        )
        y += 14.0  # line spacing
    return "\n".join(xml_parts), y


def _build_vertical_arrow(
    x: float,
    top_y: float,
    bottom_y: float,
    ids: _IDGen,
    condition_lines: Optional[List[str]] = None,
    condition_side: str = "right",
    dashed: bool = False,
    nogo: bool = False,
) -> Tuple[str, int]:
    """
    Build a vertical down arrow with optional condition text beside it.

    Parameters
    ----------
    x : float
        Horizontal position of the arrow.
    top_y : float
        Y coordinate of the arrow tail (top, in CDXML y-down coords).
    bottom_y : float
        Y coordinate of the arrow head (bottom).
    condition_lines : list of str, optional
        Condition text lines placed beside the arrow.
    condition_side : "right" or "left"
        Which side of the arrow to place condition text.
    nogo : bool
        If True, adds ``NoGo="Cross"`` for failed arrow.

    Returns (xml_string, arrow_xml_id).
    """
    arrow_xml, aid = _build_arrow(x, top_y, x, bottom_y, ids, dashed=dashed, nogo=nogo)

    if not condition_lines:
        return arrow_xml, aid

    # Place condition text beside the arrow
    mid_y = (top_y + bottom_y) / 2.0
    text_offset = 12.0  # horizontal gap from arrow shaft
    if condition_side == "right":
        text_x = x + text_offset
        justification = "Left"
    else:
        text_x = x - text_offset
        justification = "Right"

    # p.y is the first line baseline. To vertically center the visual
    # text block on the arrow midpoint:
    #   visual_top = p.y - _CAP_HEIGHT
    #   visual_bottom = p.y + (n-1)*_LINE_ADVANCE + _DESCENT
    #   visual_center = visual_top + text_h/2 = mid_y
    #   → p.y = mid_y - text_h/2 + _CAP_HEIGHT
    text_h = _estimate_text_height(condition_lines)
    text_y = mid_y - text_h / 2.0 + _CAP_HEIGHT

    txt_xml, _ = _build_text_element(
        condition_lines, text_x, text_y, ids, justification=justification,
    )

    return arrow_xml + "\n" + txt_xml, aid


def _build_run_arrow(
    tail_x: float,
    head_x: float,
    y: float,
    input_label: str,
    output_label: str,
    ids: _IDGen,
) -> Tuple[str, List[int]]:
    """
    Build a simple run arrow with input/output labels.

    Returns (xml_string, [element_ids]).
    """
    parts = []
    all_ids = []

    # Arrow
    arrow_xml, arrow_id = _build_arrow(tail_x, y, head_x, y, ids)
    parts.append(arrow_xml)
    all_ids.append(arrow_id)

    # Input label (left of arrow) — center text vertically on arrow.
    # p.y is baseline; visual center = p.y - (_CAP_HEIGHT - _DESCENT)/2
    # To center on arrow at y: p.y = y + (_CAP_HEIGHT - _DESCENT)/2
    label_baseline_y = y + (_CAP_HEIGHT - _DESCENT) / 2.0
    inp_xml, inp_id = _build_text_element(
        [input_label], tail_x - 5.0, label_baseline_y, ids,
        justification="Right", use_formatting=False,
    )
    parts.append(inp_xml)
    all_ids.append(inp_id)

    # Output label (right of arrow) — center text vertically on arrow
    if output_label:
        out_xml, out_id = _build_text_element(
            [output_label], head_x + 5.0, label_baseline_y, ids,
            justification="Left", use_formatting=False,
        )
        parts.append(out_xml)
        all_ids.append(out_id)

    return "\n".join(parts), all_ids


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _fragment_bbox(atoms: List[Dict]) -> Tuple[float, float, float, float]:
    """Compute (min_x, min_y, max_x, max_y) from atom positions.

    Includes padding for bond lines and heteroatom labels that extend
    beyond atom center positions (measured: +6.6pt width, +2.9pt height).
    """
    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    return (
        min(xs) - _FRAG_PAD_W,
        min(ys) - _FRAG_PAD_H,
        max(xs) + _FRAG_PAD_W,
        max(ys) + _FRAG_PAD_H,
    )


def _bbox_width(bbox: Tuple[float, float, float, float]) -> float:
    return bbox[2] - bbox[0]


def _bbox_height(bbox: Tuple[float, float, float, float]) -> float:
    return bbox[3] - bbox[1]


def _bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _shift_atoms(atoms: List[Dict], dx: float, dy: float) -> None:
    """Translate all atoms in place."""
    for a in atoms:
        a["x"] += dx
        a["y"] += dy


def _estimate_text_width(lines: List[str]) -> float:
    """Estimate text block width in CDXML points."""
    if not lines:
        return 0
    return max(len(ln) for ln in lines) * _CHAR_WIDTH


def _estimate_text_height(lines: List[str]) -> float:
    """Estimate visual text block height (cap-height + line advances + descent)."""
    n = len(lines)
    if n == 0:
        return 0.0
    return _CAP_HEIGHT + max(0, n - 1) * _LINE_ADVANCE + _DESCENT


# ---------------------------------------------------------------------------
# Structure resolver
# ---------------------------------------------------------------------------

def _resolve_structure(
    ref: StructureRef,
    center_x: float = 200.0,
    center_y: float = 300.0,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> ResolvedFragment:
    """
    Resolve a StructureRef to atoms/bonds in CDXML coordinates.

    Resolution order (three tiers):
      1. Source JSON — species ID or shorthand lookup
      2. Declared SMILES — from StructureRef.smiles
      3. Name resolution — reagent_db → PubChem cascade

    Parameters
    ----------
    reference_mol : RDKit Mol, optional
        When provided, the structure is aligned to this reference via MCS.
        This orients shared scaffolds to match the reference (product) layout.
    """
    smiles = ref.smiles
    label = ref.label

    # Tier 1: Source JSON lookup (by ref.id)
    if source_data and not smiles:
        # Try exact id, then lowercase
        sp = source_data.get(ref.id) or source_data.get(ref.id.lower())
        if sp:
            smiles = sp.get("smiles")
            # JSON label overrides ref label when ref has none
            if label is None and sp.get("label"):
                label = sp["label"]

    # Tier 2: Declared SMILES
    if smiles:
        # Try MCS alignment to reference if available
        if reference_mol is not None:
            try:
                from rdkit import Chem
                target_mol = Chem.MolFromSmiles(smiles)
                if target_mol is not None:
                    aligned = _align_mol_to_reference(
                        target_mol, reference_mol, center_x, center_y,
                    )
                    if aligned is not None:
                        atoms, bonds = aligned
                        bbox = _fragment_bbox(atoms)
                        cx, cy = _bbox_center(bbox)
                        resolved_ref = StructureRef(
                            id=ref.id, smiles=smiles, name=ref.name, file=ref.file,
                            cdxml_id=ref.cdxml_id, label=label,
                        )
                        return ResolvedFragment(
                            ref=resolved_ref, atoms=atoms, bonds=bonds,
                            bbox=bbox, cx=cx, cy=cy,
                        )
            except Exception:
                pass  # Fall through to standard coords

        result = _smiles_to_fragment_data(smiles, center_x, center_y)
        if result is None:
            raise ValueError(f"Failed to generate 2D coords for '{ref.id}' (SMILES: {smiles})")
        atoms, bonds = result
        bbox = _fragment_bbox(atoms)
        cx, cy = _bbox_center(bbox)
        resolved_ref = StructureRef(
            id=ref.id, smiles=smiles, name=ref.name, file=ref.file,
            cdxml_id=ref.cdxml_id, label=label,
        )
        return ResolvedFragment(
            ref=resolved_ref, atoms=atoms, bonds=bonds, bbox=bbox, cx=cx, cy=cy,
        )

    # Tier 3: Name resolution (reagent_db cascade)
    name = ref.name
    # If source_data had a species with a name, use it for resolution
    if not name and source_data:
        sp = source_data.get(ref.id) or source_data.get(ref.id.lower())
        if sp:
            name = sp.get("name")

    if name:
        try:
            from ..reagent_db import get_reagent_db
            db = get_reagent_db()
            entry = db.entry_for_name(name.lower())
            if entry and entry.get("smiles"):
                smi = entry["smiles"]
                if isinstance(smi, list):
                    smi = smi[0]
                ref_copy = StructureRef(
                    id=ref.id, smiles=smi, label=label,
                )
                return _resolve_structure(
                    ref_copy, center_x, center_y,
                    reference_mol=reference_mol,
                )
        except Exception:
            pass
        raise ValueError(
            f"Cannot resolve structure '{ref.id}' by name '{name}'. "
            f"Provide a SMILES string instead."
        )

    if ref.file:
        raise NotImplementedError(
            f"File-based structure loading not yet implemented for '{ref.id}'"
        )

    # Tier 4: Try the ID itself as a compound name in reagent_db
    try:
        from ..reagent_db import get_reagent_db
        db = get_reagent_db()
        entry = db.entry_for_name(ref.id.lower())
        if entry and entry.get("smiles"):
            smi = entry["smiles"]
            if isinstance(smi, list):
                smi = smi[0]
            ref_copy = StructureRef(
                id=ref.id, smiles=smi, label=label,
            )
            return _resolve_structure(
                ref_copy, center_x, center_y,
                reference_mol=reference_mol,
            )
    except ImportError:
        pass

    raise ValueError(
        f"Structure '{ref.id}' has no smiles, name, or file — cannot resolve. "
        f"Provide explicit smiles: or name: in the structures block."
    )


# ---------------------------------------------------------------------------
# Layout engine: linear (single step)
# ---------------------------------------------------------------------------

def _layout_linear(
    scheme: SchemeDescriptor,
    ids: _IDGen,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float]:
    """
    Layout a single-step scheme: substrates → products.

    Returns (inner_xml, lowest_y).
    """
    xml, lowest_y, _, _ = _layout_steps_row(scheme, scheme.steps, ids, start_x=100.0,
                                            arrow_y=300.0, source_data=source_data,
                                            reference_mol=reference_mol)
    return xml, lowest_y


# ---------------------------------------------------------------------------
# Layout engine: sequential (multi-step, with wrap:repeat support)
# ---------------------------------------------------------------------------

def _split_into_rows(
    steps: List[StepDescriptor],
    steps_per_row: Optional[int],
) -> List[List[StepDescriptor]]:
    """Split steps into row groups for wrap:repeat."""
    if steps_per_row is None or steps_per_row >= len(steps):
        return [steps]
    rows = []
    for i in range(0, len(steps), steps_per_row):
        rows.append(steps[i:i + steps_per_row])
    return rows


def _split_serpentine_rows(
    steps: List[StepDescriptor],
    steps_per_row: int,
) -> Tuple[List[List[StepDescriptor]], List[Optional[StepDescriptor]]]:
    """
    Split steps into horizontal rows + transition steps for serpentine layout.

    Returns (rows, transitions) where:
      - rows[i] = list of steps rendered horizontally in row i
      - transitions[i] = the step between row i and row i+1 (rendered as
        a vertical arrow), or None if row i is the last row.
    """
    rows: List[List[StepDescriptor]] = []
    transitions: List[Optional[StepDescriptor]] = []
    i = 0
    while i < len(steps):
        row = steps[i:i + steps_per_row]
        rows.append(row)
        i += steps_per_row
        if i < len(steps):
            # The next step becomes the vertical transition arrow
            transitions.append(steps[i])
            i += 1
        else:
            transitions.append(None)
    return rows, transitions


def _layout_sequential(
    scheme: SchemeDescriptor,
    ids: _IDGen,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float]:
    """
    Layout a multi-step sequential scheme.

    Supports wrap:repeat (multi-row L->R with repeated structures),
    wrap:serpentine (zigzag with vertical arrows between rows), and
    single-row (no wrapping).

    Returns (inner_xml, lowest_y).
    """
    wrap = scheme.wrap
    steps_per_row = scheme.steps_per_row

    # Single row: no wrapping needed
    if (wrap not in ("repeat", "serpentine")
            or steps_per_row is None
            or steps_per_row >= len(scheme.steps)):
        xml, lowest_y, _, _ = _layout_steps_row(
            scheme, scheme.steps, ids, start_x=80.0, arrow_y=300.0,
            source_data=source_data, reference_mol=reference_mol)
        return xml, lowest_y

    if wrap == "serpentine":
        return _layout_serpentine(scheme, ids, source_data=source_data,
                                  reference_mol=reference_mol)

    # --- Multi-row wrap:repeat ---
    rows = _split_into_rows(scheme.steps, steps_per_row)

    # Assign run arrows to rows with step numbers adjusted to be 1-indexed
    # within each row.  Step N (1-indexed overall) -> row (N-1)//spr,
    # adjusted step = N - row_idx * spr.
    row_run_arrows: Dict[int, List[StepRunArrows]] = {}
    for sra in scheme.run_arrows:
        row_idx = (sra.step - 1) // steps_per_row
        adjusted_step = sra.step - row_idx * steps_per_row
        row_run_arrows.setdefault(row_idx, []).append(
            StepRunArrows(step=adjusted_step, runs=sra.runs))

    xml_parts: List[str] = []
    arrow_y = 300.0
    lowest_y = arrow_y

    for row_idx, row_steps in enumerate(rows):
        row_ra = row_run_arrows.get(row_idx, [])

        row_xml, lowest_y, _, _ = _layout_steps_row(
            scheme, row_steps, ids,
            start_x=80.0, arrow_y=arrow_y,
            source_data=source_data,
            run_arrows=row_ra,
            reference_mol=reference_mol,
        )
        xml_parts.append(row_xml)

        # Next row starts below this row's lowest point
        arrow_y = lowest_y + ROW_GAP

    return "\n".join(xml_parts), lowest_y


def _layout_serpentine(
    scheme: SchemeDescriptor,
    ids: _IDGen,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float]:
    """
    Layout a serpentine (zigzag) multi-row scheme.

    Row 1 flows L→R, vertical down arrow at right edge, Row 2 flows R→L,
    vertical down arrow at left edge, Row 3 flows L→R, etc.

    Transition steps between rows are rendered as vertical arrows with
    their conditions placed beside the arrow.

    Returns (inner_xml, lowest_y).
    """
    steps_per_row = scheme.steps_per_row
    left_margin = 80.0

    rows, transitions = _split_serpentine_rows(scheme.steps, steps_per_row)

    bond_len = ACS_BOND_LENGTH
    frag_gap = bond_len * LAYOUT_FRAG_GAP_BONDS
    inter_gap = bond_len * LAYOUT_INTER_GAP_BONDS

    xml_parts: List[str] = []
    arrow_y = 300.0
    right_edge = 0.0  # will be set from first row's width
    last_product_frag_id: Optional[int] = None
    last_product_cursor_x: Optional[float] = None  # cursor pos after pre-placed substrate

    def _get_ref(sid: str) -> StructureRef:
        if sid in scheme.structures:
            return scheme.structures[sid]
        return StructureRef(id=sid)

    for row_idx, row_steps in enumerate(rows):
        direction = "ltr" if row_idx % 2 == 0 else "rtl"

        if direction == "ltr":
            start_x = left_margin
        else:
            start_x = right_edge

        # For rows after the first, the first substrate was placed by
        # the transition step's product. Pass skip_first_substrate_id
        # so _layout_steps_row doesn't redraw it.
        skip_id = last_product_frag_id if row_idx > 0 else None
        skip_cursor = last_product_cursor_x if row_idx > 0 else None

        row_xml, lowest_y, row_edge, row_info = _layout_steps_row(
            scheme, row_steps, ids,
            start_x=start_x, arrow_y=arrow_y,
            source_data=source_data,
            direction=direction,
            skip_first_substrate_id=skip_id,
            skip_first_substrate_cursor_x=skip_cursor,
            reference_mol=reference_mol,
        )
        xml_parts.append(row_xml)

        # After row 1, record the right edge for RTL alignment
        if row_idx == 0:
            right_edge = row_edge

        # --- Transition: vertical arrow + product of transition step ---
        transition = transitions[row_idx]
        if transition is not None:
            # Vertical arrow position: below the CENTER of the last product
            # in the current row (not at the row edge).
            if direction == "ltr":
                vert_x = row_info["last_product_cx"]
            else:
                vert_x = row_info["last_product_cx"]

            # Vertical arrow geometry:
            # - tail starts BELOW the last product (below its compound label)
            # - head ends with enough room for the next row's product
            last_prod_bottom = row_info["last_product_bottom"]
            vert_top_y = last_prod_bottom + 8.0  # below the last product + label
            vert_bottom_y = vert_top_y + ROW_GAP  # adequate vertical span

            # Condition text from the transition step
            cond_lines: List[str] = []
            if transition.below_arrow and transition.below_arrow.text:
                cond_lines = transition.below_arrow.text[:]
            if transition.above_arrow and transition.above_arrow.text:
                cond_lines = transition.above_arrow.text + cond_lines
            if transition.yield_:
                cond_lines.append(transition.yield_)

            # Condition text placement: right side for right-edge arrows,
            # left side for left-edge arrows
            if direction == "ltr":
                cond_side = "right"
            else:
                cond_side = "left"

            vert_xml, _ = _build_vertical_arrow(
                vert_x, vert_top_y, vert_bottom_y, ids,
                condition_lines=cond_lines if cond_lines else None,
                condition_side=cond_side,
            )
            xml_parts.append(vert_xml)

            # Place the transition step's product below the vertical
            # arrow. This becomes the first substrate of the next row.
            prod_ref = _get_ref(transition.products[0])
            prod_frag = _resolve_structure(
                prod_ref,
                center_x=vert_x,
                center_y=vert_bottom_y + 25.0,
                source_data=source_data,
                reference_mol=reference_mol,
            )
            # Shift so product top is below arrowhead with clearance
            prod_h = _bbox_height(prod_frag.bbox)
            target_cy = vert_bottom_y + frag_gap * 1.0 + prod_h / 2.0
            dx = vert_x - prod_frag.cx
            dy = target_cy - prod_frag.cy
            _shift_atoms(prod_frag.atoms, dx, dy)
            prod_frag.bbox = _fragment_bbox(prod_frag.atoms)
            prod_frag.cx, prod_frag.cy = _bbox_center(prod_frag.bbox)

            frag_xml, _, frag_id = _build_fragment(
                prod_frag.atoms, prod_frag.bonds, ids,
            )
            xml_parts.append(frag_xml)

            # Compound label
            if prod_frag.ref.label:
                lbl_xml, _ = _build_label_element(
                    prod_frag.ref.label, prod_frag.cx,
                    prod_frag.bbox[3] + 14.0, ids,
                )
                xml_parts.append(lbl_xml)

            last_product_frag_id = frag_id

            # Compute cursor position for the next row's first step
            # (after the pre-placed substrate).
            # Next row direction is opposite of current.
            next_direction = "rtl" if direction == "ltr" else "ltr"
            if next_direction == "rtl":
                # RTL: cursor is at the LEFT edge of the substrate
                last_product_cursor_x = prod_frag.bbox[0] - inter_gap
            else:
                # LTR: cursor is at the RIGHT edge of the substrate
                last_product_cursor_x = prod_frag.bbox[2] + inter_gap

            # Next row's arrow_y = below the transition product
            arrow_y = prod_frag.cy
        else:
            last_product_frag_id = None
            last_product_cursor_x = None

    return "\n".join(xml_parts), lowest_y


# ---------------------------------------------------------------------------
# Layout engine: divergent (one SM → multiple products via vertical branching)
# ---------------------------------------------------------------------------

# Gap between the bottom of one branch and the top of the next.
_DIVERGENT_BRANCH_GAP = 2.5 * ACS_BOND_LENGTH


def _layout_divergent(
    scheme: SchemeDescriptor,
    ids: _IDGen,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float]:
    """
    Layout a divergent scheme: one SM gives multiple products.

    Detects the shared substrate (appears in multiple steps) and renders it
    once on the left, with the first step going horizontally and subsequent
    steps branching downward with vertical arrows.

    Returns (inner_xml, lowest_y).
    """
    steps = scheme.steps
    if not steps:
        return "", 300.0

    # --- Identify shared substrate ---
    # Count how many steps each substrate ID appears in
    from collections import Counter
    sub_counts: Counter = Counter()
    for step in steps:
        for sid in step.substrates:
            sub_counts[sid] += 1

    # The shared substrate is the one appearing in the most steps
    shared_id = sub_counts.most_common(1)[0][0] if sub_counts else None

    # If no substrate appears more than once, just stack steps vertically
    if shared_id is None or sub_counts[shared_id] < 2:
        # Fall back to stacking as independent rows
        return _layout_divergent_stacked(scheme, ids, source_data,
                                        reference_mol=reference_mol)

    # Separate steps: those sharing the substrate vs others
    shared_steps = [s for s in steps if shared_id in s.substrates]
    other_steps = [s for s in steps if shared_id not in s.substrates]

    # --- Resolve shared substrate once ---
    def _get_ref(sid: str) -> StructureRef:
        if sid in scheme.structures:
            return scheme.structures[sid]
        return StructureRef(id=sid)

    bond_len = ACS_BOND_LENGTH
    frag_gap = bond_len * LAYOUT_FRAG_GAP_BONDS
    inter_gap = bond_len * LAYOUT_INTER_GAP_BONDS
    min_arrow_len = 5.0 * bond_len

    start_x = 100.0
    arrow_y = 300.0

    sm_ref = _get_ref(shared_id)
    sm_frag = _resolve_structure(sm_ref, center_x=200.0, center_y=arrow_y,
                                 source_data=source_data,
                                 reference_mol=reference_mol)
    # Position SM at start
    sm_w = _bbox_width(sm_frag.bbox)
    cx_target = start_x + sm_w / 2.0
    dx = cx_target - sm_frag.cx
    dy = arrow_y - sm_frag.cy
    _shift_atoms(sm_frag.atoms, dx, dy)
    sm_frag.bbox = _fragment_bbox(sm_frag.atoms)
    sm_frag.cx, sm_frag.cy = _bbox_center(sm_frag.bbox)

    xml_parts: List[str] = []
    all_frag_ids: List[int] = []
    step_metadata: List[Dict] = []

    # Build SM fragment
    sm_xml, _, sm_frag_id = _build_fragment(sm_frag.atoms, sm_frag.bonds, ids)
    xml_parts.append(sm_xml)
    all_frag_ids.append(sm_frag_id)

    # SM label
    if sm_frag.ref.label:
        lbl_xml, _ = _build_label_element(
            sm_frag.ref.label, sm_frag.cx, sm_frag.bbox[3] + 14.0, ids)
        xml_parts.append(lbl_xml)

    sm_right_x = sm_frag.bbox[2]
    lowest_y = arrow_y + 60.0

    # --- First step: horizontal (same Y as SM) ---
    first_step = shared_steps[0]
    branch_y = arrow_y

    for branch_idx, step in enumerate(shared_steps):
        step_meta: Dict[str, Any] = {
            "reactant_ids": [sm_frag_id],
            "product_ids": [],
            "arrow_id": 0,
            "above_ids": [],
            "below_ids": [],
        }

        if branch_idx == 0:
            # Horizontal arrow from SM
            arrow_tail_x = sm_right_x + frag_gap * 0.3

            # Compute arrow length from content
            below_text = list(step.below_arrow.text) if step.below_arrow else []
            above_text = list(step.above_arrow.text) if step.above_arrow else []
            if step.yield_:
                below_text.append(step.yield_)
            content_w = max(
                _estimate_text_width(below_text),
                _estimate_text_width(above_text),
                0,
            )
            arrow_len = max(content_w + 10.0, min_arrow_len)
            arrow_head_x = arrow_tail_x + arrow_len
            arrow_mid_x = (arrow_tail_x + arrow_head_x) / 2.0

            dashed = (step.arrow_style == "dashed")
            failed = (step.arrow_style == "failed")
            arrow_xml, arrow_id = _build_arrow(
                arrow_tail_x, branch_y, arrow_head_x, branch_y, ids,
                dashed=dashed, nogo=failed)
            xml_parts.append(arrow_xml)
            step_meta["arrow_id"] = arrow_id

            # Above-arrow text (p.y = baseline of first line)
            # Position so visual bottom sits LAYOUT_BELOW_GAP above arrow
            # (same gap as below-arrow content for symmetry)
            if above_text:
                n_abt = len(above_text)
                text_below_baseline = max(0, n_abt - 1) * _LINE_ADVANCE + _DESCENT
                text_y = branch_y - LAYOUT_BELOW_GAP - text_below_baseline
                txt_xml, txt_id = _build_text_element(
                    above_text, arrow_mid_x, text_y, ids,
                    use_formatting=False,
                )
                xml_parts.append(txt_xml)
                step_meta["above_ids"].append(txt_id)

            # Below-arrow text (p.y = baseline; visual top = p.y - _CAP_HEIGHT)
            if below_text:
                text_y = branch_y + LAYOUT_BELOW_GAP + _CAP_HEIGHT
                txt_xml, txt_id = _build_text_element(below_text, arrow_mid_x, text_y, ids)
                xml_parts.append(txt_xml)
                step_meta["below_ids"].append(txt_id)
                n_blt = len(below_text)
                lowest_y = max(
                    lowest_y,
                    text_y + max(0, n_blt - 1) * _LINE_ADVANCE + _DESCENT,
                )

            # Products
            cursor_x = arrow_head_x + frag_gap * 1.0
            for prod_sid in step.products:
                prod_ref = _get_ref(prod_sid)
                prod_frag = _resolve_structure(prod_ref, source_data=source_data,
                                               reference_mol=reference_mol)
                pw = _bbox_width(prod_frag.bbox)
                pcx = cursor_x + pw / 2.0
                ddx = pcx - prod_frag.cx
                ddy = branch_y - prod_frag.cy
                _shift_atoms(prod_frag.atoms, ddx, ddy)
                prod_frag.bbox = _fragment_bbox(prod_frag.atoms)
                prod_frag.cx, prod_frag.cy = _bbox_center(prod_frag.bbox)

                pfrag_xml, _, pfrag_id = _build_fragment(
                    prod_frag.atoms, prod_frag.bonds, ids)
                xml_parts.append(pfrag_xml)
                step_meta["product_ids"].append(pfrag_id)
                all_frag_ids.append(pfrag_id)

                if prod_frag.ref.label:
                    lbl_xml, _ = _build_label_element(
                        prod_frag.ref.label, prod_frag.cx,
                        prod_frag.bbox[3] + 14.0, ids)
                    xml_parts.append(lbl_xml)

                cursor_x = prod_frag.bbox[2] + inter_gap

            # Track lowest for below-text of this horizontal step
            lowest_y = max(lowest_y, branch_y + 60.0)

        else:
            # Vertical branch downward from SM
            # Vertical arrow starts below the previous branch's content
            vert_top_y = lowest_y + 8.0

            # Condition text
            cond_lines: List[str] = []
            if step.above_arrow and step.above_arrow.text:
                cond_lines.extend(step.above_arrow.text)
            if step.below_arrow and step.below_arrow.text:
                cond_lines.extend(step.below_arrow.text)
            if step.yield_:
                cond_lines.append(step.yield_)

            # Compute vertical arrow length: enough for condition text + product
            prod_ref = _get_ref(step.products[0])
            prod_frag = _resolve_structure(prod_ref, source_data=source_data,
                                           reference_mol=reference_mol)
            prod_h = _bbox_height(prod_frag.bbox)

            cond_text_h = _estimate_text_height(cond_lines) if cond_lines else 0
            vert_len = max(cond_text_h + 20.0, prod_h + 30.0, 3.0 * bond_len)
            vert_bottom_y = vert_top_y + vert_len

            dashed = (step.arrow_style == "dashed")
            failed = (step.arrow_style == "failed")

            vert_xml, vert_aid = _build_vertical_arrow(
                sm_frag.cx, vert_top_y, vert_bottom_y, ids,
                condition_lines=cond_lines if cond_lines else None,
                condition_side="right",
                dashed=dashed,
                nogo=failed,
            )
            xml_parts.append(vert_xml)
            step_meta["arrow_id"] = vert_aid

            # Product below the vertical arrow, centered on SM's x.
            prod_w = _bbox_width(prod_frag.bbox)
            prod_y = vert_bottom_y + frag_gap * 1.0 + prod_h / 2.0
            prod_target_cx = sm_frag.cx
            ddx = prod_target_cx - prod_frag.cx
            ddy = prod_y - prod_frag.cy
            _shift_atoms(prod_frag.atoms, ddx, ddy)
            prod_frag.bbox = _fragment_bbox(prod_frag.atoms)
            prod_frag.cx, prod_frag.cy = _bbox_center(prod_frag.bbox)

            pfrag_xml, _, pfrag_id = _build_fragment(
                prod_frag.atoms, prod_frag.bonds, ids)
            xml_parts.append(pfrag_xml)
            step_meta["product_ids"].append(pfrag_id)
            all_frag_ids.append(pfrag_id)

            if prod_frag.ref.label:
                lbl_xml, _ = _build_label_element(
                    prod_frag.ref.label, prod_frag.cx,
                    prod_frag.bbox[3] + 14.0, ids)
                xml_parts.append(lbl_xml)

            lowest_y = prod_frag.bbox[3] + 20.0

        step_metadata.append(step_meta)

    # --- Build <scheme> ---
    scheme_id = ids.next()
    scheme_parts = [f'<scheme id="{scheme_id}">']
    for meta in step_metadata:
        step_id = ids.next()
        attrs = [f'id="{step_id}"']
        if meta["reactant_ids"]:
            attrs.append(f'ReactionStepReactants="{" ".join(str(x) for x in meta["reactant_ids"])}"')
        if meta["product_ids"]:
            attrs.append(f'ReactionStepProducts="{" ".join(str(x) for x in meta["product_ids"])}"')
        attrs.append(f'ReactionStepArrows="{meta["arrow_id"]}"')
        if meta["above_ids"]:
            attrs.append(f'ReactionStepObjectsAboveArrow="{" ".join(str(x) for x in meta["above_ids"])}"')
        if meta["below_ids"]:
            attrs.append(f'ReactionStepObjectsBelowArrow="{" ".join(str(x) for x in meta["below_ids"])}"')
        scheme_parts.append(f'<step {" ".join(attrs)}/>')
    scheme_parts.append('</scheme>')
    xml_parts.append("\n".join(scheme_parts))

    return "\n".join(xml_parts), lowest_y


def _layout_divergent_stacked(
    scheme: SchemeDescriptor,
    ids: _IDGen,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float]:
    """Fallback: stack divergent steps vertically when no shared substrate."""
    xml_parts: List[str] = []
    arrow_y = 300.0
    lowest_y = arrow_y

    for step in scheme.steps:
        sub_scheme = SchemeDescriptor(
            structures=scheme.structures,
            steps=[step],
            layout="linear",
        )
        row_xml, row_lowest = _layout_linear(sub_scheme, ids, source_data=source_data,
                                             reference_mol=reference_mol)
        xml_parts.append(row_xml)
        lowest_y = row_lowest
        arrow_y = row_lowest + _DIVERGENT_BRANCH_GAP

    return "\n".join(xml_parts), lowest_y


# ---------------------------------------------------------------------------
# Layout engine: stacked-rows (multiple independent sub-schemes)
# ---------------------------------------------------------------------------

SECTION_GAP = 5.5 * ACS_BOND_LENGTH  # ~79.2 pt between sections (more clearance)
SECTION_LABEL_X = 40.0               # left margin for section labels


def _layout_stacked_rows(
    scheme: SchemeDescriptor,
    ids: _IDGen,
    source_data: Optional[Dict[str, Dict]] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float]:
    """
    Layout multiple independent sub-schemes stacked vertically.

    Each section is rendered as its own row (linear or sequential).
    Section labels like "(i)", "(ii)" are placed at the left margin.

    Returns (inner_xml, lowest_y).
    """
    sections = scheme.sections
    if not sections:
        # Fall back to linear if no sections defined
        return _layout_linear(scheme, ids, source_data=source_data,
                              reference_mol=reference_mol)

    # --- Partition run_arrows by section ---
    # Global step numbers are 1-indexed across all sections.  Build a map
    # from global step number → (section_index, local_step_number).
    global_step = 1
    sec_run_arrows: Dict[int, List[StepRunArrows]] = {}
    for sec_idx, sec in enumerate(sections):
        for local_step in range(1, len(sec.steps) + 1):
            # Map this global step to this section
            for sra in scheme.run_arrows:
                if sra.step == global_step:
                    sec_run_arrows.setdefault(sec_idx, []).append(
                        StepRunArrows(step=local_step, runs=sra.runs))
            global_step += 1

    xml_parts: List[str] = []
    arrow_y = 300.0
    lowest_y = arrow_y
    # Content starts to the right of section labels
    content_start_x = 100.0

    for sec_idx, sec in enumerate(sections):
        # --- Section label ---
        if sec.label:
            # Place label at the left margin, vertically centered on arrow_y
            # Baseline is below center, so use arrow_y + small offset
            label_xml, _ = _build_text_element(
                [sec.label], SECTION_LABEL_X, arrow_y + 4.0, ids,
                justification="Left", use_formatting=False,
            )
            xml_parts.append(label_xml)

        # --- Per-section reference product for alignment ---
        # Each section is an independent reaction, so align structures
        # within each section to that section's own product.
        sec_ref_mol = _product_mol_for_steps(
            sec.steps, scheme.structures, source_data,
        )
        if sec_ref_mol is None:
            sec_ref_mol = reference_mol  # fallback to global

        # --- Run arrows for this section ---
        section_ra = sec_run_arrows.get(sec_idx, [])

        # --- Render this section's steps ---
        # Create a temporary sub-scheme sharing the structure definitions
        sub_scheme = SchemeDescriptor(
            structures=scheme.structures,
            steps=sec.steps,
            layout=sec.layout or "linear",
        )

        row_xml, row_lowest, _, _ = _layout_steps_row(
            sub_scheme, sec.steps, ids,
            start_x=content_start_x, arrow_y=arrow_y,
            source_data=source_data,
            run_arrows=section_ra,
            reference_mol=sec_ref_mol,
        )

        xml_parts.append(row_xml)
        lowest_y = row_lowest

        # Move to next section
        arrow_y = lowest_y + SECTION_GAP

    return "\n".join(xml_parts), lowest_y


# ---------------------------------------------------------------------------
# Core row layout: positions steps in a single row (LTR or RTL)
# ---------------------------------------------------------------------------

def _layout_steps_row(
    scheme: SchemeDescriptor,
    steps: List[StepDescriptor],
    ids: _IDGen,
    start_x: float = 100.0,
    arrow_y: float = 300.0,
    source_data: Optional[Dict[str, Dict]] = None,
    run_arrows: Optional[List[StepRunArrows]] = None,
    direction: str = "ltr",
    skip_first_substrate_id: Optional[int] = None,
    skip_first_substrate_cursor_x: Optional[float] = None,
    reference_mol: Optional[Any] = None,
) -> Tuple[str, float, float, Dict]:
    """
    Layout multiple steps in a single row.

    Parameters
    ----------
    run_arrows : optional
        Run arrows for this row (step numbers are 1-indexed within this row).
        If None, uses scheme.run_arrows with original step numbers.
    direction : str
        "ltr" for left-to-right (default), "rtl" for right-to-left.
        For RTL, start_x is the RIGHT edge; cursor moves leftward.
        Arrows point left, substrates on right, products on left.
    skip_first_substrate_id : optional int
        If set, the first step's substrate is already placed (e.g. by a
        vertical arrow in serpentine mode). This frag_id is used in the
        scheme metadata but the structure is not drawn or positioned.
    skip_first_substrate_cursor_x : optional float
        When skip_first_substrate_id is set, the cursor position after the
        pre-placed substrate. For LTR this is the substrate's right_x + gap;
        for RTL this is the substrate's left_x - gap.

    Returns (xml_string, lowest_y, row_edge_x, row_info) where:
        lowest_y = bottom extent of this row including run arrows
        row_edge_x = rightmost x for LTR, leftmost x for RTL
        row_info = dict with extra metadata:
            "last_product_cx" : float — center x of the last product placed
            "last_product_bottom" : float — bottom y extent of last product + label
            "first_substrate_cx" : float — center x of the first substrate
    """
    is_rtl = (direction == "rtl")
    bond_len = ACS_BOND_LENGTH
    frag_gap = bond_len * LAYOUT_FRAG_GAP_BONDS    # gap between fragment and arrow
    inter_gap = bond_len * LAYOUT_INTER_GAP_BONDS   # gap between adjacent fragments

    # --- Phase 1: Resolve all structures ---
    def _get_ref(sid: str) -> StructureRef:
        """Get StructureRef from declared structures or create a bare one for source lookup."""
        if sid in scheme.structures:
            return scheme.structures[sid]
        # Not declared — create a bare ref (will be resolved via source_data)
        return StructureRef(id=sid)

    resolved_steps: List[ResolvedStep] = []
    for step in steps:
        subs = [_resolve_structure(_get_ref(sid), source_data=source_data,
                                   reference_mol=reference_mol)
                for sid in step.substrates]
        prods = [_resolve_structure(_get_ref(pid), source_data=source_data,
                                    reference_mol=reference_mol)
                 for pid in step.products]

        above_structs = []
        above_text = []
        below_text = []
        below_structs = []

        if step.above_arrow:
            for sid in step.above_arrow.structures:
                above_structs.append(
                    _resolve_structure(_get_ref(sid), source_data=source_data,
                                      reference_mol=reference_mol))
            above_text = step.above_arrow.text[:]
        if step.below_arrow:
            for sid in step.below_arrow.structures:
                below_structs.append(
                    _resolve_structure(_get_ref(sid), source_data=source_data,
                                      reference_mol=reference_mol))
            below_text = step.below_arrow.text[:]

        # Add yield to below-arrow text if present
        if step.yield_:
            below_text.append(step.yield_)

        resolved_steps.append(ResolvedStep(
            descriptor=step,
            substrates=subs,
            products=prods,
            above_structures=above_structs,
            above_text=above_text,
            below_text=below_text,
            below_structures=below_structs,
        ))

    # --- Phase 2: Compute arrow lengths from content ---
    min_arrow_len = 5.0 * bond_len
    use_letter_conditions = bool(scheme.condition_key)

    for rs in resolved_steps:
        # Check if this step uses letter conditions
        is_letter = (use_letter_conditions
                     and _is_letter_condition(rs.below_text))
        rs._is_letter_cond = is_letter

        # Width of above-arrow content
        above_width = 0.0
        for af in rs.above_structures:
            above_width += _bbox_width(af.bbox) + inter_gap
        above_text_w = _estimate_text_width(rs.above_text)
        above_width = max(above_width, above_text_w)

        # Width of below-arrow content (skip if using letter label)
        below_width = 0.0
        if not is_letter:
            for bf in rs.below_structures:
                below_width += _bbox_width(bf.bbox) + inter_gap
            below_text_w = _estimate_text_width(rs.below_text)
            below_width = max(below_width, below_text_w)

        content_width = max(above_width, below_width)
        rs._arrow_len = max(content_width + 10.0, min_arrow_len)

    # --- Phase 3: Position everything ---
    # For LTR: cursor_x = left edge of next element, moves right.
    # For RTL: cursor_x = right edge of next element, moves left.
    cursor_x = start_x

    xml_parts: List[str] = []
    all_frag_ids: List[int] = []
    step_metadata: List[Dict] = []  # for <scheme><step> elements

    # Track extra info for serpentine/multi-row callers
    _last_product_cx: float = start_x
    _last_product_bottom: float = arrow_y
    _first_substrate_cx: float = start_x

    for step_idx, rs in enumerate(resolved_steps):
        step_meta: Dict[str, Any] = {
            "reactant_ids": [],
            "product_ids": [],
            "arrow_id": 0,
            "above_ids": [],
            "below_ids": [],
        }

        # -- Substrates --
        # Skip if: (a) pre-placed by vertical arrow (serpentine), or
        # (b) shared intermediate from the previous step's product.
        skip_substrate = False
        if step_idx == 0 and skip_first_substrate_id is not None:
            skip_substrate = True
            step_meta["reactant_ids"].append(skip_first_substrate_id)
            if skip_first_substrate_cursor_x is not None:
                cursor_x = skip_first_substrate_cursor_x
        elif step_idx > 0:
            prev_products = resolved_steps[step_idx - 1].descriptor.products
            curr_substrates = rs.descriptor.substrates
            if (len(curr_substrates) == 1 and len(prev_products) >= 1
                    and curr_substrates[0] == prev_products[-1]):
                skip_substrate = True
                # Use the previous step's product fragment ID
                prev_meta = step_metadata[step_idx - 1]
                if prev_meta["product_ids"]:
                    step_meta["reactant_ids"].append(prev_meta["product_ids"][-1])

        if not skip_substrate:
            for i, sub in enumerate(rs.substrates):
                if i:
                    plus_x = cursor_x + inter_gap / 2 if is_rtl else cursor_x - inter_gap / 2
                    plus_xml, _ = _build_text_element(['+'], plus_x, arrow_y + 3.5, ids)
                    xml_parts.append(plus_xml)
                bbox = sub.bbox
                w = _bbox_width(bbox)
                # Shift to position
                if is_rtl:
                    cx_target = cursor_x - w / 2.0
                else:
                    cx_target = cursor_x + w / 2.0
                cy_target = arrow_y
                dx = cx_target - sub.cx
                dy = cy_target - sub.cy
                _shift_atoms(sub.atoms, dx, dy)
                sub.bbox = _fragment_bbox(sub.atoms)
                sub.cx, sub.cy = _bbox_center(sub.bbox)

                frag_xml, _, frag_id = _build_fragment(sub.atoms, sub.bonds, ids)
                sub.xml = frag_xml
                sub.frag_id = frag_id
                xml_parts.append(frag_xml)
                step_meta["reactant_ids"].append(frag_id)
                all_frag_ids.append(frag_id)

                # Track first substrate center
                if step_idx == 0 and i == 0:
                    _first_substrate_cx = sub.cx

                # Compound label below structure
                if sub.ref.label:
                    label_x = sub.cx
                    label_y = sub.bbox[3] + 14.0  # below structure
                    lbl_xml, lbl_id = _build_label_element(
                        sub.ref.label, label_x, label_y, ids,
                    )
                    xml_parts.append(lbl_xml)

                if is_rtl:
                    cursor_x = sub.bbox[0] - inter_gap
                else:
                    cursor_x = sub.bbox[2] + inter_gap

        # -- Arrow --
        if is_rtl:
            # RTL: tail on right (near substrate), head on left (near product)
            arrow_tail_x = cursor_x - frag_gap * 0.3
            arrow_head_x = arrow_tail_x - rs._arrow_len
        else:
            arrow_tail_x = cursor_x + frag_gap * 0.3
            arrow_head_x = arrow_tail_x + rs._arrow_len
        arrow_mid_x = (arrow_tail_x + arrow_head_x) / 2.0

        dashed = (rs.descriptor.arrow_style == "dashed")
        failed = (rs.descriptor.arrow_style == "failed")
        arrow_xml, arrow_id = _build_arrow(
            arrow_tail_x, arrow_y, arrow_head_x, arrow_y, ids,
            dashed=dashed, nogo=failed,
        )
        xml_parts.append(arrow_xml)
        step_meta["arrow_id"] = arrow_id

        rs.arrow_tail_x = arrow_tail_x
        rs.arrow_tail_y = arrow_y
        rs.arrow_head_x = arrow_head_x
        rs.arrow_head_y = arrow_y

        # -- Above-arrow content --
        # Structures above arrow
        above_cursor_x = arrow_mid_x
        if rs.above_structures:
            total_above_w = sum(_bbox_width(af.bbox) for af in rs.above_structures)
            total_above_w += inter_gap * max(0, len(rs.above_structures) - 1)
            above_cursor_x = arrow_mid_x - total_above_w / 2.0

            # If there's text below above-arrow structures (e.g. "(1.2 eq)"),
            # push structures higher to make room for the text between
            # structure bottom and arrow.
            # Gap layout: struct -(4pt)- text -(2pt)- arrow
            above_text_height = 0.0
            if rs.above_text:
                n_abt = len(rs.above_text)
                # Visual text height + struct-to-text gap (4pt)
                above_text_height = (
                    _CAP_HEIGHT + max(0, n_abt - 1) * _LINE_ADVANCE + _DESCENT + 4.0
                )

            for af in rs.above_structures:
                af_w = _bbox_width(af.bbox)
                af_h = _bbox_height(af.bbox)
                label_height = 20.0 if af.ref.label else 0.0
                # Position above the arrow, with extra room for text below structure
                target_cx = above_cursor_x + af_w / 2.0
                if rs.above_text:
                    # text sits LAYOUT_BELOW_GAP above arrow; struct sits above text
                    target_cy = arrow_y - LAYOUT_BELOW_GAP - above_text_height - label_height - af_h / 2.0
                else:
                    # no text: struct sits LAYOUT_ABOVE_GAP above arrow
                    target_cy = arrow_y - LAYOUT_ABOVE_GAP - label_height - af_h / 2.0
                dx = target_cx - af.cx
                dy = target_cy - af.cy
                _shift_atoms(af.atoms, dx, dy)
                af.bbox = _fragment_bbox(af.atoms)
                af.cx, af.cy = _bbox_center(af.bbox)

                frag_xml, _, frag_id = _build_fragment(af.atoms, af.bonds, ids)
                af.xml = frag_xml
                af.frag_id = frag_id
                xml_parts.append(frag_xml)
                step_meta["above_ids"].append(frag_id)
                all_frag_ids.append(frag_id)

                # Label for above-arrow structure
                if af.ref.label:
                    lbl_xml, _ = _build_label_element(
                        af.ref.label, af.cx, af.bbox[3] + 14.0, ids,
                    )
                    xml_parts.append(lbl_xml)

                above_cursor_x += af_w + inter_gap

        # Above-arrow text (equiv text for above structures, or condition text)
        # p.y is the BASELINE of the first line.
        # Position so that the visual bottom (last baseline + descent) sits
        # LAYOUT_BELOW_GAP above the arrow (same gap as below-arrow content).
        if rs.above_text:
            n_abt = len(rs.above_text)
            # Distance from first baseline to visual bottom
            text_below_baseline = max(0, n_abt - 1) * _LINE_ADVANCE + _DESCENT
            text_y = arrow_y - LAYOUT_BELOW_GAP - text_below_baseline
            if rs.above_structures:
                # Text sits between above-arrow structures and the arrow.
                # Structures were already pushed higher to make room.
                pass  # text_y is already correct
            txt_xml, txt_id = _build_text_element(
                rs.above_text, arrow_mid_x, text_y, ids,
                use_formatting=False,
            )
            xml_parts.append(txt_xml)
            step_meta["above_ids"].append(txt_id)

        # -- Below-arrow content --
        # p.y is the BASELINE of the first line.
        # Visual top = p.y - _CAP_HEIGHT, so set p.y so that
        # (p.y - _CAP_HEIGHT) = arrow_y + LAYOUT_BELOW_GAP.
        below_y = arrow_y + LAYOUT_BELOW_GAP + _CAP_HEIGHT

        # Below-arrow structures first
        if rs.below_structures:
            below_struct_y = arrow_y + LAYOUT_BELOW_GAP
            total_below_w = sum(_bbox_width(bf.bbox) for bf in rs.below_structures)
            total_below_w += inter_gap * max(0, len(rs.below_structures) - 1)
            below_cursor_x = arrow_mid_x - total_below_w / 2.0

            for bf in rs.below_structures:
                bf_w = _bbox_width(bf.bbox)
                bf_h = _bbox_height(bf.bbox)
                target_cx = below_cursor_x + bf_w / 2.0
                target_cy = below_struct_y + bf_h / 2.0 + 4.0
                dx = target_cx - bf.cx
                dy = target_cy - bf.cy
                _shift_atoms(bf.atoms, dx, dy)
                bf.bbox = _fragment_bbox(bf.atoms)
                bf.cx, bf.cy = _bbox_center(bf.bbox)

                frag_xml, _, frag_id = _build_fragment(bf.atoms, bf.bonds, ids)
                bf.xml = frag_xml
                bf.frag_id = frag_id
                xml_parts.append(frag_xml)
                step_meta["below_ids"].append(frag_id)
                all_frag_ids.append(frag_id)

                if bf.ref.label:
                    lbl_xml, _ = _build_label_element(
                        bf.ref.label, bf.cx, bf.bbox[3] + 14.0, ids,
                    )
                    xml_parts.append(lbl_xml)

                below_cursor_x += bf_w + inter_gap

            # Adjust text Y to be below the structures
            below_y = max(bf.bbox[3] for bf in rs.below_structures) + 14.0

        # Below-arrow text (or letter label for condition key mode)
        if rs.below_text:
            if rs._is_letter_cond:
                # Letter condition: render small italic label above arrow
                letter_text = rs.below_text[0].strip()
                lbl_xml, lbl_id = _build_letter_label(
                    letter_text, arrow_mid_x, arrow_y, ids,
                )
                xml_parts.append(lbl_xml)
                step_meta["above_ids"].append(lbl_id)
            else:
                txt_xml, txt_id = _build_text_element(
                    rs.below_text, arrow_mid_x, below_y, ids,
                )
                xml_parts.append(txt_xml)
                step_meta["below_ids"].append(txt_id)

        if is_rtl:
            cursor_x = arrow_head_x - frag_gap * 1.0
        else:
            cursor_x = arrow_head_x + frag_gap * 1.0

        # -- Products --
        for i, prod in enumerate(rs.products):
            if i:
                plus_x = cursor_x + inter_gap / 2 if is_rtl else cursor_x - inter_gap / 2
                plus_xml, _ = _build_text_element(['+'], plus_x, arrow_y + 3.5, ids)
                xml_parts.append(plus_xml)
            bbox = prod.bbox
            w = _bbox_width(bbox)
            if is_rtl:
                cx_target = cursor_x - w / 2.0
            else:
                cx_target = cursor_x + w / 2.0
            cy_target = arrow_y
            dx = cx_target - prod.cx
            dy = cy_target - prod.cy
            _shift_atoms(prod.atoms, dx, dy)
            prod.bbox = _fragment_bbox(prod.atoms)
            prod.cx, prod.cy = _bbox_center(prod.bbox)

            frag_xml, _, frag_id = _build_fragment(prod.atoms, prod.bonds, ids)
            prod.xml = frag_xml
            prod.frag_id = frag_id
            xml_parts.append(frag_xml)
            step_meta["product_ids"].append(frag_id)
            all_frag_ids.append(frag_id)

            prod_bottom = prod.bbox[3]
            if prod.ref.label:
                lbl_xml, _ = _build_label_element(
                    prod.ref.label, prod.cx, prod.bbox[3] + 14.0, ids,
                )
                xml_parts.append(lbl_xml)
                prod_bottom = prod.bbox[3] + 14.0 + 6.0  # label baseline + descent

            # Track last product info for serpentine callers
            _last_product_cx = prod.cx
            _last_product_bottom = prod_bottom

            if is_rtl:
                cursor_x = prod.bbox[0] - inter_gap
            else:
                cursor_x = prod.bbox[2] + inter_gap

        step_metadata.append(step_meta)

    # --- Phase 4: Build <scheme> with <step> elements ---
    scheme_id = ids.next()
    scheme_parts = [f'<scheme id="{scheme_id}">']
    for meta in step_metadata:
        step_id = ids.next()
        attrs = [f'id="{step_id}"']
        if meta["reactant_ids"]:
            attrs.append(f'ReactionStepReactants="{" ".join(str(x) for x in meta["reactant_ids"])}"')
        if meta["product_ids"]:
            attrs.append(f'ReactionStepProducts="{" ".join(str(x) for x in meta["product_ids"])}"')
        attrs.append(f'ReactionStepArrows="{meta["arrow_id"]}"')
        if meta["above_ids"]:
            attrs.append(f'ReactionStepObjectsAboveArrow="{" ".join(str(x) for x in meta["above_ids"])}"')
        if meta["below_ids"]:
            attrs.append(f'ReactionStepObjectsBelowArrow="{" ".join(str(x) for x in meta["below_ids"])}"')
        scheme_parts.append(f'<step {" ".join(attrs)}/>')
    scheme_parts.append('</scheme>')
    xml_parts.append("\n".join(scheme_parts))

    # --- Phase 5: Run arrows ---
    # Compute lowest_y from row content (always needed for return value)
    lowest_y = arrow_y + 60.0  # baseline estimate
    for rs in resolved_steps:
        if rs.below_text:
            n_blt = len(rs.below_text)
            # below_y baseline + distance to visual bottom + margin
            below_vis_bottom = (
                arrow_y + LAYOUT_BELOW_GAP + _CAP_HEIGHT  # first baseline
                + max(0, n_blt - 1) * _LINE_ADVANCE + _DESCENT  # to visual bottom
                + 4.0  # margin
            )
            lowest_y = max(lowest_y, below_vis_bottom)
        for bf in rs.below_structures:
            lowest_y = max(lowest_y, bf.bbox[3] + 20.0)

    # Determine which run arrows to render
    effective_run_arrows = run_arrows if run_arrows is not None else scheme.run_arrows

    if effective_run_arrows:
        run_y = lowest_y + 6.0  # tighter gap between conditions text and run arrows

        for sra in effective_run_arrows:
            step_idx = sra.step - 1  # 0-indexed
            if step_idx < 0 or step_idx >= len(resolved_steps):
                continue
            rs = resolved_steps[step_idx]

            # Run arrow matches the reaction arrow exactly (same tail/head X),
            # just translated vertically below the scheme content.
            run_tail_x = rs.arrow_tail_x
            run_head_x = rs.arrow_head_x

            for run_entry in sra.runs:
                if run_entry.note:
                    # Text centered above this specific run arrow
                    note_y = run_y - 1.0
                    note_xml, _ = _build_text_element(
                        [run_entry.note],
                        (run_tail_x + run_head_x) / 2.0,
                        note_y, ids,
                        justification="Center",
                        use_formatting=False,
                    )
                    xml_parts.append(note_xml)
                    run_y += 10.0  # space for note text
                run_xml, _ = _build_run_arrow(
                    run_tail_x, run_head_x,
                    run_y,
                    run_entry.input_label,
                    run_entry.output_label,
                    ids,
                )
                xml_parts.append(run_xml)
                run_y += 18.0  # stack multiple runs

        lowest_y = run_y

    # Compute row edge (rightmost for LTR, leftmost for RTL)
    row_edge_x = cursor_x

    row_info = {
        "last_product_cx": _last_product_cx,
        "last_product_bottom": _last_product_bottom,
        "first_substrate_cx": _first_substrate_cx,
    }
    return "\n".join(xml_parts), lowest_y, row_edge_x, row_info


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

def _format_header(bbox: str) -> str:
    """Format the full CDXML header with ACS style."""
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


_PAGE_OPEN = (
    '<page id="{page_id}" BoundingBox="0 0 1620 2160" '
    'HeaderPosition="36" FooterPosition="36" '
    'PrintTrimMarks="yes" HeightPages="3" WidthPages="3">'
)
_PAGE_CLOSE = "</page>"


def _product_mol_for_steps(
    steps: List[StepDescriptor],
    structures: Dict[str, StructureRef],
    source_data: Optional[Dict[str, Dict]] = None,
    pick: str = "last",
) -> Optional[Any]:
    """
    Build an RDKit Mol with 2D coords for the product of given steps.

    Parameters
    ----------
    steps : list of StepDescriptor
    structures : dict mapping structure IDs to StructureRef
    source_data : optional reaction_parser JSON species lookup
    pick : "last" (default) = last step's last product;
           "first" = first step's first product (for divergent).

    Returns an RDKit Mol with 2D conformer, or None.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return None

    pid: Optional[str] = None
    if pick == "first":
        if steps and steps[0].products:
            pid = steps[0].products[0]
    else:
        if steps and steps[-1].products:
            pid = steps[-1].products[-1]

    if pid is None:
        return None

    product_smiles: Optional[str] = None
    ref = structures.get(pid)
    if ref and ref.smiles:
        product_smiles = ref.smiles
    elif source_data:
        sp = source_data.get(pid) or source_data.get(pid.lower())
        if sp:
            product_smiles = sp.get("smiles")

    if not product_smiles:
        return None

    mol = Chem.MolFromSmiles(product_smiles)
    if mol is None:
        return None

    AllChem.Compute2DCoords(mol)
    return mol


def _identify_product_mol(
    scheme: SchemeDescriptor,
    source_data: Optional[Dict[str, Dict]] = None,
) -> Optional[Any]:
    """
    Identify the main product and create an RDKit Mol with 2D coords.

    This mol serves as the reference for MCS alignment of all other
    structures in the scheme — shared scaffolds are oriented to match
    the product's layout, producing visually consistent schemes.

    Reference product selection:
      - linear / sequential: product of the LAST step
      - divergent: product of the FIRST (horizontal) step
      - stacked-rows: product of the first section's last step

    Returns an RDKit Mol with 2D conformer, or None if RDKit is
    unavailable or no product SMILES can be resolved.
    """
    if scheme.layout == "divergent":
        return _product_mol_for_steps(
            scheme.steps, scheme.structures, source_data, pick="first",
        )
    elif scheme.layout == "stacked-rows":
        if scheme.sections:
            return _product_mol_for_steps(
                scheme.sections[0].steps, scheme.structures, source_data,
            )
        return None
    else:
        # linear / sequential — last step's last product
        return _product_mol_for_steps(
            scheme.steps, scheme.structures, source_data,
        )


def _render_impl(scheme: SchemeDescriptor, yaml_dir: Optional[str] = None) -> str:
    """
    Render a SchemeDescriptor to a CDXML document string.

    Parameters
    ----------
    scheme : SchemeDescriptor
        Parsed scheme from YAML.
    yaml_dir : str, optional
        Directory of the YAML file (for resolving relative source paths).

    Returns
    -------
    str
        Complete CDXML document.
    """
    ids = _IDGen(1000)

    # Load source JSON if specified
    source_data = None
    if scheme.source:
        source_path = scheme.source
        if not os.path.isabs(source_path) and yaml_dir:
            source_path = os.path.join(yaml_dir, source_path)
        source_data = _load_source_json(source_path)

    # --- Identify product reference Mol for alignment ---
    # The product of the last step is the reference for MCS alignment.
    # All other structures are aligned to match its scaffold orientation.
    ref_mol = _identify_product_mol(scheme, source_data)

    # Choose layout
    if scheme.layout == "linear":
        inner_xml, lowest_y = _layout_linear(scheme, ids, source_data=source_data,
                                              reference_mol=ref_mol)
    elif scheme.layout == "sequential":
        inner_xml, lowest_y = _layout_sequential(scheme, ids, source_data=source_data,
                                                  reference_mol=ref_mol)
    elif scheme.layout == "divergent":
        inner_xml, lowest_y = _layout_divergent(scheme, ids, source_data=source_data,
                                                 reference_mol=ref_mol)
    elif scheme.layout == "stacked-rows":
        inner_xml, lowest_y = _layout_stacked_rows(scheme, ids, source_data=source_data,
                                                    reference_mol=ref_mol)
    else:
        raise NotImplementedError(
            f"Layout '{scheme.layout}' is not yet implemented. "
            f"Supported: linear, sequential, divergent, stacked-rows"
        )

    # Condition key block below the scheme
    if scheme.condition_key:
        key_y = lowest_y + 20.0
        key_xml, _ = _build_condition_key(
            scheme.condition_key, 80.0, key_y, ids,
        )
        inner_xml += "\n" + key_xml

    # Wrap in document
    page_id = ids.next()

    # Use a generous bounding box
    bbox = "0 0 1620 2160"

    doc_parts = [
        _format_header(bbox),
        _PAGE_OPEN.format(page_id=page_id),
        inner_xml,
        _PAGE_CLOSE,
        CDXML_FOOTER,
    ]
    return "\n".join(doc_parts)


class _ValidatedCDXML(str):
    pass


def render(scheme: SchemeDescriptor, yaml_dir: Optional[str] = None) -> str:
    """Render a scheme and retain per-fragment output-derived validation receipts."""
    receipts = []
    token = _fragment_receipts.set(receipts)
    try:
        result = _ValidatedCDXML(_render_impl(scheme, yaml_dir))
        from xml.etree import ElementTree as ET
        root = ET.fromstring(result)
        fragment_ids = {node.get('id') for node in root.iter('fragment')}
        validated_ids = {str(receipt['fragment_id']) for receipt in receipts}
        result.chemistry_validation = {
            'status': 'preserved' if fragment_ids and fragment_ids == validated_ids else 'unverified',
            'method': 'final_coordinate_fragment_roundtrips', 'fragments': receipts}
        return result
    finally:
        _fragment_receipts.reset(token)


def render_to_file(
    scheme: SchemeDescriptor,
    output_path: str,
    yaml_dir: Optional[str] = None,
) -> None:
    """Render and write to a file."""
    cdxml = render(scheme, yaml_dir=yaml_dir)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cdxml)
