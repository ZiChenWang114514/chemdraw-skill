#!/usr/bin/env python3
"""
scheme_merger.py -- Merge multiple ELN-enriched reaction schemes.

Auto-detects relationships between input schemes:
  Parallel:   Same reaction at different scales -> one scheme, stacked run arrows.
  Sequential: Step 1 product = step 2 starting material -> multi-step linear scheme.
  Unrelated:  No chemical relationship -> placed adjacent (side by side).

Input: ELN-enriched CDXMLs from scheme_polisher_v2.py (via run_pipeline.py).

Usage:
    python scheme_merger.py s1.cdxml s2.cdxml s3.cdxml s4.cdxml  # auto-detect
    python scheme_merger.py --mode parallel s1.cdxml s2.cdxml      # explicit mode
    python scheme_merger.py --mode sequential s1.cdxml s2.cdxml
    python scheme_merger.py s1.cdxml s2.cdxml --no-equiv
    python scheme_merger.py s1.cdxml s2.cdxml --equiv-range
    python scheme_merger.py s1.cdxml s2.cdxml --ref-cdxml ref.cdxml
    python scheme_merger.py s1.cdxml s2.cdxml --no-adjacent  # error on unrelated
"""

import argparse
import copy
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..cdxml_utils import (
    fragment_bbox,
    fragment_bbox_with_label_extension,
    fragment_bottom_has_hanging_label,
    parse_cdxml,
    write_cdxml,
    recompute_text_bbox,
)
from ..rdkit_utils import frag_to_smiles, frag_to_mw
from ..constants import (
    ACS_BOND_LENGTH,
    LAYOUT_ABOVE_GAP,
    LAYOUT_BELOW_GAP,
    LAYOUT_HANGING_LABEL_GAP,
    LAYOUT_FRAG_GAP_BONDS,
    LAYOUT_INTER_GAP_BONDS,
    MW_MATCH_TOLERANCE,
)


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class RunArrowData:
    """Data extracted from one run arrow (mass/yield for one run)."""
    sm_mass_text: str       # e.g. "50.0 mg"
    yield_text: str         # e.g. "62.6 mg, 77 %"
    source_file: str = ""   # filename stem for identification


@dataclass
class EquivInfo:
    """Equiv value for one reagent in one scheme."""
    reagent_name: str
    equiv_value: float


@dataclass
class ParsedScheme:
    """A parsed ELN-enriched CDXML scheme with all metadata extracted."""
    path: str
    tree: ET.ElementTree
    root: ET.Element
    page: ET.Element
    scheme_el: ET.Element
    step: ET.Element

    # Element maps
    id_map: Dict[str, ET.Element] = field(default_factory=dict)

    # Fragments and their roles (from step metadata)
    reactant_ids: List[str] = field(default_factory=list)
    product_ids: List[str] = field(default_factory=list)
    above_arrow_ids: List[str] = field(default_factory=list)
    below_arrow_ids: List[str] = field(default_factory=list)
    arrow_ids: List[str] = field(default_factory=list)

    # Classified elements
    fragments: Dict[str, ET.Element] = field(default_factory=dict)
    fragment_smiles: Dict[str, str] = field(default_factory=dict)

    # Arrows
    main_arrow: Optional[ET.Element] = None
    main_arrow_id: str = ""
    main_graphic: Optional[ET.Element] = None
    run_arrows: List[ET.Element] = field(default_factory=list)
    run_graphics: List[ET.Element] = field(default_factory=list)

    # Arrow geometry
    arrow_tail_x: float = 0.0
    arrow_head_x: float = 0.0
    arrow_y: float = 0.0

    # Run arrow data
    run_arrow_data: List[RunArrowData] = field(default_factory=list)

    # Text elements associated with run arrows (to remove during merge)
    run_arrow_text_ids: List[str] = field(default_factory=list)

    # Equiv values parsed from conditions text
    equiv_values: List[EquivInfo] = field(default_factory=list)

    def get_reactant_smiles_set(self) -> set:
        """Set of canonical SMILES for reactant fragments."""
        result = set()
        for rid in self.reactant_ids:
            s = self.fragment_smiles.get(rid, "")
            if s:
                result.add(s)
        return result

    def get_product_smiles_set(self) -> set:
        """Set of canonical SMILES for product fragments."""
        result = set()
        for pid in self.product_ids:
            s = self.fragment_smiles.get(pid, "")
            if s:
                result.add(s)
        return result


# ============================================================================
# Parsing helpers
# ============================================================================

def _get_text_content(t_elem: ET.Element) -> str:
    """Extract concatenated text from all <s> children of a <t> element."""
    parts = []
    for s in t_elem.iter("s"):
        if s.text:
            parts.append(s.text)
    return "".join(parts).strip()


def _get_max_id(root: ET.Element) -> int:
    """Find the maximum id attribute value in the entire document."""
    max_id = 0
    for el in root.iter():
        eid = el.get("id", "")
        if eid:
            try:
                max_id = max(max_id, int(eid))
            except ValueError:
                pass
    return max_id


def _get_max_z(root: ET.Element) -> int:
    """Find the maximum Z attribute value in the entire document."""
    max_z = 0
    for el in root.iter():
        z = el.get("Z", "")
        if z:
            try:
                max_z = max(max_z, int(z))
            except ValueError:
                pass
    return max_z


def _get_arrow_coords(arrow_el: ET.Element) -> Tuple[float, float, float]:
    """Extract (tail_x, head_x, y) from an <arrow> or <graphic> element."""
    if arrow_el.tag == "arrow":
        head3d = arrow_el.get("Head3D", "")
        tail3d = arrow_el.get("Tail3D", "")
        if head3d and tail3d:
            hp = head3d.split()
            tp = tail3d.split()
            head_x = float(hp[0])
            tail_x = float(tp[0])
            y = float(hp[1])
        else:
            bb = arrow_el.get("BoundingBox", "").split()
            tail_x = float(bb[0])
            head_x = float(bb[2])
            y = (float(bb[1]) + float(bb[3])) / 2.0
    else:  # graphic
        bb = arrow_el.get("BoundingBox", "").split()
        head_x = float(bb[0])
        tail_x = float(bb[2])
        y = float(bb[1])

    if tail_x > head_x:
        tail_x, head_x = head_x, tail_x
    return tail_x, head_x, y


def _fragment_centroid_y(page: ET.Element, frag_ids: List[str],
                         id_map: Dict[str, ET.Element]) -> float:
    """Average y-centroid of the specified fragments."""
    ys = []
    for fid in frag_ids:
        el = id_map.get(fid)
        if el is not None and el.tag == "fragment":
            bb = fragment_bbox(el)
            if bb:
                ys.append((bb[1] + bb[3]) / 2.0)
    return sum(ys) / len(ys) if ys else 0.0


def _build_page_id_map(page: ET.Element) -> Dict[str, ET.Element]:
    """Build id->element map for direct children of page."""
    id_map = {}
    for el in page:
        eid = el.get("id")
        if eid:
            id_map[eid] = el
    return id_map


def parse_scheme(path: str, log=None) -> ParsedScheme:
    """Parse an ELN-enriched CDXML scheme file."""
    if log is None:
        log = lambda msg: None

    tree = parse_cdxml(path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        raise ValueError(f"No <page> found in {path}")

    scheme_el = page.find(".//scheme")
    if scheme_el is None:
        raise ValueError(f"No <scheme> found in {path}")

    step = scheme_el.find("step")
    if step is None:
        raise ValueError(f"No <step> found in {path}")

    ps = ParsedScheme(
        path=path, tree=tree, root=root, page=page,
        scheme_el=scheme_el, step=step,
    )

    # Build ID map (direct children of page)
    ps.id_map = _build_page_id_map(page)

    # Parse step metadata
    ps.reactant_ids = step.get("ReactionStepReactants", "").split()
    ps.product_ids = step.get("ReactionStepProducts", "").split()
    ps.above_arrow_ids = step.get("ReactionStepObjectsAboveArrow", "").split()
    ps.below_arrow_ids = step.get("ReactionStepObjectsBelowArrow", "").split()
    ps.arrow_ids = step.get("ReactionStepArrows", "").split()

    # Collect all fragment IDs and compute SMILES
    for el in page:
        if el.tag == "fragment":
            fid = el.get("id", "")
            ps.fragments[fid] = el
            try:
                smiles = frag_to_smiles(el)
                ps.fragment_smiles[fid] = smiles
            except Exception:
                ps.fragment_smiles[fid] = ""

    # Identify all arrows on the page
    all_arrows = []
    all_graphics = {}  # arrow_id -> graphic element (via SupersededBy)
    for el in page:
        if el.tag == "arrow":
            all_arrows.append(el)
        elif el.tag == "graphic" and el.get("SupersededBy"):
            all_graphics[el.get("SupersededBy")] = el

    # Distinguish main arrow from run arrows by proximity to fragment centroids
    all_frag_ids = list(ps.reactant_ids) + list(ps.product_ids)
    frag_cy = _fragment_centroid_y(page, all_frag_ids, ps.id_map)

    if all_arrows:
        # Sort arrows by distance to fragment centroid y
        arrows_with_dist = []
        for a in all_arrows:
            _, _, ay = _get_arrow_coords(a)
            arrows_with_dist.append((abs(ay - frag_cy), ay, a))
        arrows_with_dist.sort(key=lambda x: x[0])

        ps.main_arrow = arrows_with_dist[0][2]
        ps.main_arrow_id = ps.main_arrow.get("id", "")
        ps.main_graphic = all_graphics.get(ps.main_arrow_id)

        # Get main arrow coordinates
        ps.arrow_tail_x, ps.arrow_head_x, ps.arrow_y = _get_arrow_coords(ps.main_arrow)

        # Run arrows: everything below the main arrow
        for _, ay, a in arrows_with_dist[1:]:
            if ay > ps.arrow_y + 5.0:
                ps.run_arrows.append(a)
                aid = a.get("id", "")
                if aid in all_graphics:
                    ps.run_graphics.append(all_graphics[aid])

        # Sort run arrows by y position
        ps.run_arrows.sort(
            key=lambda a: float(a.get("Head3D", "0 0 0").split()[1])
        )

    # Extract run arrow data (text near each run arrow)
    for ra in ps.run_arrows:
        ra_tail_x, ra_head_x, ra_y = _get_arrow_coords(ra)
        sm_text = ""
        yield_text = ""
        for el in page:
            if el.tag != "t":
                continue
            p = el.get("p", "")
            if not p:
                continue
            parts = p.split()
            tx, ty = float(parts[0]), float(parts[1])
            if abs(ty - (ra_y + 2.25)) < 6.0:
                text = _get_text_content(el)
                # SM text is right-justified, near arrow tail
                if tx < (ra_tail_x + ra_head_x) / 2.0:
                    sm_text = text
                    ps.run_arrow_text_ids.append(el.get("id", ""))
                else:
                    yield_text = text
                    ps.run_arrow_text_ids.append(el.get("id", ""))

        ps.run_arrow_data.append(RunArrowData(
            sm_mass_text=sm_text,
            yield_text=yield_text,
            source_file=os.path.splitext(os.path.basename(path))[0],
        ))

    # Extract equiv values from conditions text
    _extract_equiv_values(ps)

    log(f"Parsed {os.path.basename(path)}: "
        f"{len(ps.fragments)} fragments, "
        f"{len(ps.run_arrows)} run arrow(s), "
        f"main arrow at y={ps.arrow_y:.1f}")
    return ps


def _extract_equiv_values(ps: ParsedScheme):
    """Parse equiv values from conditions text and equiv labels."""
    # Pattern: "ReagentName (X eq.)" or standalone "(X eq.)"
    equiv_re = re.compile(r'\((\d+\.?\d*)\s*eq\.\)')

    for el in ps.page:
        if el.tag != "t":
            continue
        text = _get_text_content(el)
        if not text:
            continue

        # Multi-line conditions text: "PPh3 (1.6 eq.)\nDEAD (1.55 eq.)\nTHF"
        for line in text.split("\n"):
            line = line.strip()
            m = equiv_re.search(line)
            if m:
                equiv_val = float(m.group(1))
                # Reagent name is everything before the parentheses
                name = line[:m.start()].strip()
                if not name:
                    name = line  # standalone equiv label
                ps.equiv_values.append(EquivInfo(
                    reagent_name=name,
                    equiv_value=equiv_val,
                ))


# ============================================================================
# Element creation helpers (patterns from eln_enrichment.py)
# ============================================================================

def _create_text_element(elem_id: int, z_order: int,
                         x: float, y: float,
                         text: str, justify: str = "Left") -> ET.Element:
    """Create a standalone <t> element with plain text content."""
    t = ET.Element("t")
    t.set("id", str(elem_id))
    t.set("p", f"{x:.2f} {y:.2f}")
    t.set("Z", str(z_order))
    t.set("Warning",
          "Chemical Interpretation is not possible for this label")
    t.set("LineHeight", "auto")

    if justify == "Center":
        t.set("CaptionJustification", "Center")
        t.set("Justification", "Center")
    elif justify == "Right":
        t.set("CaptionJustification", "Right")
        t.set("Justification", "Right")

    s = ET.SubElement(t, "s")
    s.set("font", "3")
    s.set("size", "10")
    s.set("color", "0")
    s.text = text

    # BoundingBox
    char_w = 5.8
    line_h = 12.0
    w = len(text) * char_w
    if justify == "Center":
        x1, x2 = x - w / 2.0, x + w / 2.0
    elif justify == "Right":
        x1, x2 = x - w, x
    else:
        x1, x2 = x, x + w
    y1 = y - line_h + 3.0
    y2 = y + 3.0
    t.set("BoundingBox", f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}")
    return t


def _create_arrow(elem_id: int, z_order: int,
                  tail_x: float, head_x: float,
                  y: float) -> ET.Element:
    """Create an <arrow> element."""
    arrow = ET.Element("arrow")
    arrow.set("id", str(elem_id))
    bb_top = y - 1.64
    bb_bot = y + 1.52
    arrow.set("BoundingBox",
              f"{tail_x:.2f} {bb_top:.2f} {head_x:.2f} {bb_bot:.2f}")
    arrow.set("Z", str(z_order))
    arrow.set("FillType", "None")
    arrow.set("ArrowheadHead", "Full")
    arrow.set("ArrowheadType", "Solid")
    arrow.set("HeadSize", "1000")
    arrow.set("ArrowheadCenterSize", "875")
    arrow.set("ArrowheadWidth", "250")
    arrow.set("Head3D", f"{head_x:.2f} {y:.2f} 0")
    arrow.set("Tail3D", f"{tail_x:.2f} {y:.2f} 0")
    # Center3D / axis ends (cosmetic)
    cx_3d = (tail_x + head_x) / 2.0 + 290.0
    cy_3d = y + 129.0
    half_len = (head_x - tail_x) / 2.0
    arrow.set("Center3D", f"{cx_3d:.2f} {cy_3d:.2f} 0")
    arrow.set("MajorAxisEnd3D",
              f"{cx_3d + half_len:.2f} {cy_3d:.2f} 0")
    arrow.set("MinorAxisEnd3D",
              f"{cx_3d:.2f} {cy_3d + half_len:.2f} 0")
    return arrow


def _create_graphic(elem_id: int, z_order: int,
                    superseded_by: int,
                    tail_x: float, head_x: float,
                    y: float) -> ET.Element:
    """Create a <graphic> element (old-style arrow ref)."""
    g = ET.Element("graphic")
    g.set("id", str(elem_id))
    g.set("SupersededBy", str(superseded_by))
    g.set("BoundingBox",
          f"{head_x:.2f} {y:.2f} {tail_x:.2f} {y:.2f}")
    g.set("Z", str(z_order))
    g.set("GraphicType", "Line")
    g.set("ArrowType", "FullHead")
    g.set("HeadSize", "1000")
    return g


# ============================================================================
# Geometry helpers
# ============================================================================

def _fragment_main_component_bbox(frag: ET.Element) -> Optional[Tuple[float, float, float, float]]:
    """Get atom-only bbox of the largest connected component in a fragment.

    For salt products (e.g. amine + HCl), the counterion atoms may be far
    from the main structure, inflating the bbox. This returns the bbox of
    only the largest connected component by atom count.

    Falls back to regular fragment_bbox if there's only one component.
    """
    # Collect atoms with positions
    atoms = {}  # id -> (x, y)
    for n in frag:
        if n.tag != "n":
            continue
        nid = n.get("id", "")
        p = n.get("p", "")
        if nid and p:
            parts = p.split()
            if len(parts) >= 2:
                atoms[nid] = (float(parts[0]), float(parts[1]))

    if len(atoms) < 2:
        return fragment_bbox(frag)

    # Build adjacency from bonds
    adj: Dict[str, List[str]] = {aid: [] for aid in atoms}
    for b in frag:
        if b.tag != "b":
            continue
        b_id = b.get("B", "")
        e_id = b.get("E", "")
        if b_id in adj and e_id in adj:
            adj[b_id].append(e_id)
            adj[e_id].append(b_id)

    # Find connected components via BFS
    visited = set()
    components = []
    for start in atoms:
        if start in visited:
            continue
        comp = []
        queue = [start]
        visited.add(start)
        while queue:
            node = queue.pop(0)
            comp.append(node)
            for nb in adj.get(node, []):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        components.append(comp)

    if len(components) <= 1:
        return fragment_bbox(frag)

    # Use the largest component
    largest = max(components, key=len)
    xs = [atoms[aid][0] for aid in largest]
    ys = [atoms[aid][1] for aid in largest]
    return (min(xs), min(ys), max(xs), max(ys))


def _get_element_bbox(el: ET.Element) -> Optional[Tuple[float, float, float, float]]:
    """Get bounding box for any element."""
    if el.tag == "fragment":
        return fragment_bbox_with_label_extension(el)
    elif el.tag == "t":
        bb = el.get("BoundingBox", "")
        if bb:
            vals = [float(v) for v in bb.split()]
            if len(vals) >= 4:
                return (vals[0], vals[1], vals[2], vals[3])
        p = el.get("p", "")
        if p:
            parts = [float(v) for v in p.split()]
            text = _get_text_content(el)
            w = len(text) * 5.8
            return (parts[0] - w / 2, parts[1] - 12.0,
                    parts[0] + w / 2, parts[1])
    elif el.tag in ("arrow", "graphic"):
        bb = el.get("BoundingBox", "")
        if bb:
            vals = [float(v) for v in bb.split()]
            if len(vals) >= 4:
                return (vals[0], vals[1], vals[2], vals[3])
    return None


def _content_bottom(page: ET.Element, exclude_ids: set = None) -> float:
    """Find the bottom y coordinate of all visible content on the page."""
    if exclude_ids is None:
        exclude_ids = set()
    bottom = 0.0
    for el in page:
        eid = el.get("id", "")
        if eid in exclude_ids:
            continue
        if el.tag in ("scheme",):
            continue
        bb = _get_element_bbox(el)
        if bb and bb[3] > bottom:
            bottom = bb[3]
    return bottom


def _shift_element(el: ET.Element, dx: float, dy: float):
    """Translate an element (fragment or text) by (dx, dy)."""
    if el.tag == "fragment":
        for n in el.iter("n"):
            p = n.get("p")
            if p:
                parts = p.split()
                if len(parts) >= 2:
                    nx = float(parts[0]) + dx
                    ny = float(parts[1]) + dy
                    n.set("p", f"{nx:.2f} {ny:.2f}")
        for t in el.iter("t"):
            _shift_text_el(t, dx, dy)
        _shift_bbox_attr(el, dx, dy)
        for inner in el.iter("fragment"):
            if inner is not el:
                _shift_bbox_attr(inner, dx, dy)
    elif el.tag == "t":
        _shift_text_el(el, dx, dy)


def _shift_text_el(t: ET.Element, dx: float, dy: float):
    """Shift a <t> element's p and BoundingBox."""
    p = t.get("p")
    if p:
        parts = p.split()
        if len(parts) >= 2:
            t.set("p", f"{float(parts[0]) + dx:.2f} {float(parts[1]) + dy:.2f}")
    _shift_bbox_attr(t, dx, dy)


def _shift_bbox_attr(el: ET.Element, dx: float, dy: float):
    """Shift BoundingBox attribute by (dx, dy)."""
    bb = el.get("BoundingBox")
    if bb:
        vals = [float(v) for v in bb.split()]
        if len(vals) >= 4:
            vals[0] += dx
            vals[1] += dy
            vals[2] += dx
            vals[3] += dy
            el.set("BoundingBox", " ".join(f"{v:.2f}" for v in vals))


def _move_element_to(el: ET.Element, target_cx: float, target_cy: float):
    """Move element so its center is at (target_cx, target_cy)."""
    bb = _get_element_bbox(el)
    if bb is None:
        return
    cx = (bb[0] + bb[2]) / 2.0
    cy = (bb[1] + bb[3]) / 2.0
    _shift_element(el, target_cx - cx, target_cy - cy)


def _update_document_bbox(root: ET.Element, page: ET.Element):
    """Update root CDXML BoundingBox to encompass all content."""
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for el in page:
        bb = _get_element_bbox(el)
        if bb is None:
            continue
        min_x = min(min_x, bb[0])
        min_y = min(min_y, bb[1])
        max_x = max(max_x, bb[2])
        max_y = max(max_y, bb[3])
    if min_x < float('inf'):
        root.set("BoundingBox",
                 f"{min_x:.2f} {min_y:.2f} {max_x:.2f} {max_y:.2f}")


# ============================================================================
# Fragment comparison
# ============================================================================

def _smiles_match(s1: str, s2: str) -> bool:
    """Check if two SMILES represent the same molecule."""
    if not s1 or not s2:
        return False
    return s1 == s2


def _fragments_same_molecule(frag1: ET.Element, frag2: ET.Element,
                             smiles1: str = "", smiles2: str = "") -> bool:
    """Check if two fragments represent the same molecule.

    Primary: canonical SMILES comparison.
    Fallback: MW comparison within MW_MATCH_TOLERANCE (for fragments
    with abbreviation groups that produce '*' in SMILES).
    """
    # Try SMILES first
    if not smiles1:
        try:
            smiles1 = frag_to_smiles(frag1)
        except Exception:
            smiles1 = ""
    if not smiles2:
        try:
            smiles2 = frag_to_smiles(frag2)
        except Exception:
            smiles2 = ""

    if smiles1 and smiles2 and "*" not in smiles1 and "*" not in smiles2:
        return _smiles_match(smiles1, smiles2)

    # Fallback: MW comparison
    try:
        mw1 = frag_to_mw(frag1)
        mw2 = frag_to_mw(frag2)
        if mw1 is not None and mw2 is not None:
            return abs(mw1 - mw2) < MW_MATCH_TOLERANCE
    except Exception:
        pass

    return False


def _products_match(ps_a: ParsedScheme, ps_b: ParsedScheme) -> bool:
    """Check if two schemes have the same set of product molecules."""
    prod_a = ps_a.get_product_smiles_set()
    prod_b = ps_b.get_product_smiles_set()

    # Fast path: identical SMILES sets (no abbreviation groups)
    if prod_a and prod_b and prod_a == prod_b:
        return True

    # Fragment-level comparison with MW fallback
    frags_a = [(pid, ps_a.fragments.get(pid)) for pid in ps_a.product_ids
               if ps_a.fragments.get(pid) is not None]
    frags_b = [(pid, ps_b.fragments.get(pid)) for pid in ps_b.product_ids
               if ps_b.fragments.get(pid) is not None]

    if len(frags_a) != len(frags_b):
        return False

    # Try to match each product in A to one in B
    used = set()
    for aid, afrag in frags_a:
        asmiles = ps_a.fragment_smiles.get(aid, "")
        matched = False
        for j, (bid, bfrag) in enumerate(frags_b):
            if j in used:
                continue
            bsmiles = ps_b.fragment_smiles.get(bid, "")
            if _fragments_same_molecule(afrag, bfrag, asmiles, bsmiles):
                used.add(j)
                matched = True
                break
        if not matched:
            return False
    return True


def _any_reactant_matches(ps_a: ParsedScheme, ps_b: ParsedScheme) -> bool:
    """Check if at least one reactant fragment matches between two schemes."""
    for aid in ps_a.reactant_ids:
        afrag = ps_a.fragments.get(aid)
        if afrag is None:
            continue
        asmiles = ps_a.fragment_smiles.get(aid, "")
        for bid in ps_b.reactant_ids:
            bfrag = ps_b.fragments.get(bid)
            if bfrag is None:
                continue
            bsmiles = ps_b.fragment_smiles.get(bid, "")
            if _fragments_same_molecule(afrag, bfrag, asmiles, bsmiles):
                return True
    return False


def _product_matches_reactant(ps_a: ParsedScheme, ps_b: ParsedScheme) -> bool:
    """Check if any product of A matches any reactant of B."""
    for pid in ps_a.product_ids:
        pfrag = ps_a.fragments.get(pid)
        if pfrag is None:
            continue
        psmiles = ps_a.fragment_smiles.get(pid, "")
        for rid in ps_b.reactant_ids:
            rfrag = ps_b.fragments.get(rid)
            if rfrag is None:
                continue
            rsmiles = ps_b.fragment_smiles.get(rid, "")
            if _fragments_same_molecule(pfrag, rfrag, psmiles, rsmiles):
                return True
    return False


# ============================================================================
# Auto-detection: classify pairs and plan merges
# ============================================================================

def classify_pair(ps_a: ParsedScheme, ps_b: ParsedScheme) -> str:
    """Classify the relationship between two parsed schemes.

    Returns:
        "parallel"       - Same reaction (same products, shared reactant)
        "sequential_ab"  - A's product is B's starting material
        "sequential_ba"  - B's product is A's starting material
        "unrelated"      - No chemical relationship
    """
    # Check parallel first: same products AND at least one shared reactant
    if _products_match(ps_a, ps_b) and _any_reactant_matches(ps_a, ps_b):
        return "parallel"

    # Check sequential: product of one matches reactant of the other
    if _product_matches_reactant(ps_a, ps_b):
        return "sequential_ab"
    if _product_matches_reactant(ps_b, ps_a):
        return "sequential_ba"

    return "unrelated"


@dataclass
class MergePlan:
    """Result of auto-detection: how to merge N schemes."""
    parallel_groups: List[List[int]] = field(default_factory=list)
    """Groups of scheme indices that are the same reaction."""
    sequential_chain: List[int] = field(default_factory=list)
    """Indices into parallel_groups, in reaction order."""
    unrelated_groups: List[int] = field(default_factory=list)
    """Indices into parallel_groups with no sequential link."""

    def describe(self) -> str:
        """Human-readable summary of the merge plan."""
        parts = []
        if self.sequential_chain:
            chain_desc = []
            for gi in self.sequential_chain:
                grp = self.parallel_groups[gi]
                if len(grp) > 1:
                    chain_desc.append(f"[{'+'.join(str(g) for g in grp)}]")
                else:
                    chain_desc.append(str(grp[0]))
            parts.append(f"Sequential chain: {' -> '.join(chain_desc)}")
        elif len(self.parallel_groups) == 1 and len(self.parallel_groups[0]) > 1:
            grp = self.parallel_groups[0]
            parts.append(f"Parallel merge: {'+'.join(str(g) for g in grp)}")
        if self.unrelated_groups:
            for gi in self.unrelated_groups:
                grp = self.parallel_groups[gi]
                parts.append(f"Adjacent (unrelated): "
                             f"{'+'.join(str(g) for g in grp)}")
        return "; ".join(parts) if parts else "Single scheme"


def auto_detect(schemes: List[ParsedScheme], log=None) -> MergePlan:
    """Analyze N schemes and determine merge strategy.

    Algorithm:
    1. Classify all pairs (parallel, sequential, unrelated).
    2. Union-Find to cluster parallel schemes.
    3. Build DAG of sequential links between clusters.
    4. Topological sort for reaction order.
    5. Remaining clusters are unrelated.
    """
    if log is None:
        log = lambda msg: None

    n = len(schemes)
    if n == 1:
        return MergePlan(parallel_groups=[[0]], sequential_chain=[0])

    # --- Step 1: Classify all pairs ---
    classifications = {}
    for i in range(n):
        for j in range(i + 1, n):
            c = classify_pair(schemes[i], schemes[j])
            classifications[(i, j)] = c
            log(f"  {os.path.basename(schemes[i].path)} vs "
                f"{os.path.basename(schemes[j].path)}: {c}")

    # --- Step 2: Union-Find for parallel clusters ---
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for (i, j), c in classifications.items():
        if c == "parallel":
            union(i, j)

    # Build groups
    groups_map = {}
    for i in range(n):
        root = find(i)
        groups_map.setdefault(root, []).append(i)
    groups = list(groups_map.values())

    # Index each scheme to its group
    scheme_to_group = {}
    for gi, grp in enumerate(groups):
        for si in grp:
            scheme_to_group[si] = gi

    # --- Step 3: Build DAG of sequential links between groups ---
    # For each sequential pair, determine which group feeds into which
    seq_edges = set()  # (from_group, to_group)
    for (i, j), c in classifications.items():
        gi, gj = scheme_to_group[i], scheme_to_group[j]
        if gi == gj:
            continue  # same parallel group
        if c == "sequential_ab":
            seq_edges.add((gi, gj))
        elif c == "sequential_ba":
            seq_edges.add((gj, gi))

    # --- Step 4: Topological sort for sequential chain ---
    if seq_edges:
        # Build adjacency and in-degree
        ng = len(groups)
        adj = {i: [] for i in range(ng)}
        in_deg = {i: 0 for i in range(ng)}
        for (a, b) in seq_edges:
            adj[a].append(b)
            in_deg[b] += 1

        # Kahn's algorithm
        queue = [i for i in range(ng) if in_deg[i] == 0]
        topo_order = []
        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            for nb in adj[node]:
                in_deg[nb] -= 1
                if in_deg[nb] == 0:
                    queue.append(nb)

        if len(topo_order) != ng:
            log("WARNING: Cycle detected in sequential links — "
                "falling back to input order")
            topo_order = list(range(ng))

        # Split into connected (in the sequential DAG) and unrelated
        connected = set()
        for a, b in seq_edges:
            connected.add(a)
            connected.add(b)

        chain = [gi for gi in topo_order if gi in connected]
        unrelated = [gi for gi in topo_order if gi not in connected]
    else:
        # No sequential links — everything is either one parallel group
        # or multiple unrelated groups
        chain = []
        unrelated = list(range(len(groups)))
        # If there's only one group, it's parallel (not unrelated)
        if len(groups) == 1:
            chain = [0]
            unrelated = []

    plan = MergePlan(
        parallel_groups=groups,
        sequential_chain=chain,
        unrelated_groups=unrelated,
    )
    log(f"  Merge plan: {plan.describe()}")
    return plan


def execute_merge_plan(schemes: List[ParsedScheme], plan: MergePlan, *,
                       equiv_mode: str = "default",
                       ref_cdxml: str = None,
                       allow_adjacent: bool = True,
                       log=None) -> ET.ElementTree:
    """Execute a merge plan: parallel within groups, sequential between.

    Args:
        schemes: All parsed schemes.
        plan: Auto-detected merge plan.
        equiv_mode: Equiv handling for parallel merges.
        ref_cdxml: Reference CDXML for sequential alignment.
        allow_adjacent: If False, raise ValueError for unrelated reactions.
        log: Logging callback.
    """
    if log is None:
        log = lambda msg: None

    # Check for unrelated groups
    if plan.unrelated_groups and not plan.sequential_chain:
        # All groups are unrelated (no sequential chain)
        if not allow_adjacent and len(plan.parallel_groups) > 1:
            raise ValueError(
                "Input schemes have no chemical relationship (not parallel, "
                "not sequential). Use --adjacent to place them side by side."
            )

    if plan.unrelated_groups and plan.sequential_chain and not allow_adjacent:
        raise ValueError(
            "Some input schemes are unrelated to the sequential chain. "
            "Use --adjacent to place them side by side."
        )

    # --- Phase 1: Parallel merge within each group ---
    group_trees = []  # one tree per group (parallel-merged or single)
    group_schemes = []  # re-parsed schemes for sequential merge

    for gi, grp in enumerate(plan.parallel_groups):
        if len(grp) == 1:
            # Single scheme — use as-is
            s = schemes[grp[0]]
            group_trees.append(copy.deepcopy(s.tree))
            log(f"Group {gi}: single scheme "
                f"({os.path.basename(s.path)})")
        else:
            # Parallel merge
            grp_schemes = [schemes[si] for si in grp]
            names = [os.path.basename(schemes[si].path) for si in grp]
            log(f"Group {gi}: parallel merge of {', '.join(names)}")
            merged = parallel_merge(grp_schemes, equiv_mode=equiv_mode,
                                    log=log)
            group_trees.append(merged)

    # --- Phase 2: Sequential merge across groups in chain order ---
    if len(plan.sequential_chain) > 1:
        # Re-parse the parallel-merged trees for sequential merge
        chain_schemes = []
        for gi in plan.sequential_chain:
            tree = group_trees[gi]
            # Write to temp file and re-parse
            fd, tmp_path = tempfile.mkstemp(suffix=".cdxml")
            try:
                write_cdxml(tree, tmp_path)
                os.close(fd)
                ps = parse_scheme(tmp_path, log=log)
                chain_schemes.append(ps)
            except Exception as e:
                log(f"WARNING: Failed to re-parse group {gi}: {e}")
                os.close(fd)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        if len(chain_schemes) >= 2:
            log(f"Sequential merge: {len(chain_schemes)} steps")
            result_tree = sequential_merge(
                chain_schemes, ref_cdxml=ref_cdxml, log=log)
        else:
            result_tree = group_trees[plan.sequential_chain[0]]

    elif len(plan.sequential_chain) == 1:
        result_tree = group_trees[plan.sequential_chain[0]]
    elif plan.unrelated_groups:
        # All groups are unrelated — use the first one as starting point
        result_tree = group_trees[plan.unrelated_groups[0]]
    else:
        result_tree = group_trees[0]

    # --- Phase 3: Adjacent placement for unrelated groups ---
    if plan.unrelated_groups and plan.sequential_chain:
        # Have both a sequential chain result and unrelated groups
        trees_to_place = [result_tree]
        for gi in plan.unrelated_groups:
            trees_to_place.append(group_trees[gi])
        if len(trees_to_place) > 1:
            result_tree = adjacent_place(trees_to_place, log=log)
    elif not plan.sequential_chain and len(plan.unrelated_groups) > 1:
        # All groups are unrelated — place adjacent
        trees_to_place = [group_trees[gi] for gi in plan.unrelated_groups]
        result_tree = adjacent_place(trees_to_place, log=log)

    return result_tree


def adjacent_place(trees: List[ET.ElementTree], *,
                   log=None) -> ET.ElementTree:
    """Place multiple independent schemes side by side on one page.

    Each tree keeps its own fragments, arrows, run arrows, and scheme/step
    structure. They are arranged horizontally with a generous gap.

    Args:
        trees: List of CDXML ElementTrees to place adjacent.
        log: Logging callback.

    Returns:
        Combined ElementTree with all schemes side by side.
    """
    if log is None:
        log = lambda msg: None

    if len(trees) == 1:
        return trees[0]

    log(f"Adjacent placement: {len(trees)} schemes side by side")

    # Use first tree as base
    result_tree = copy.deepcopy(trees[0])
    result_root = result_tree.getroot()
    result_page = result_root.find(".//page")

    # Find the right edge of existing content
    _, _, right_edge, _ = _page_bbox(result_page)

    gap = ACS_BOND_LENGTH * 3.0  # generous horizontal gap

    for tree_idx, extra_tree in enumerate(trees[1:], 2):
        extra_root = extra_tree.getroot()
        extra_page = extra_root.find(".//page")
        if extra_page is None:
            continue

        # Get bbox of content to add
        ex_left, ex_top, ex_right, ex_bottom = _page_bbox(extra_page)
        if ex_left >= float('inf'):
            continue

        # Compute horizontal shift to place after existing content
        dx = (right_edge + gap) - ex_left

        # Remap IDs to avoid conflicts with existing content
        next_id = _get_max_id(result_root) + 1
        next_z = _get_max_z(result_root) + 1
        old_to_new = {}

        # Copy elements from extra_page to result_page
        for el in list(extra_page):
            el_copy = copy.deepcopy(el)
            # Remap IDs
            _remap_element_ids(el_copy, old_to_new, next_id, next_z)
            next_id = max(next_id,
                         _get_max_id_in_element(el_copy) + 1)
            next_z = max(next_z,
                         _get_max_z_in_element(el_copy) + 1)
            # Shift horizontally
            _shift_element(el_copy, dx, 0)
            result_page.append(el_copy)

        # Update right edge for next placement
        right_edge = right_edge + gap + (ex_right - ex_left)
        log(f"  Placed scheme {tree_idx} at x offset {dx:.1f}")

    _update_document_bbox(result_root, result_page)
    return result_tree


def _page_bbox(page: ET.Element) -> Tuple[float, float, float, float]:
    """Get bounding box of all content on a page."""
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for el in page:
        bb = _get_element_bbox(el)
        if bb is None:
            continue
        min_x = min(min_x, bb[0])
        min_y = min(min_y, bb[1])
        max_x = max(max_x, bb[2])
        max_y = max(max_y, bb[3])
    return min_x, min_y, max_x, max_y


# ============================================================================
# Parallel merge
# ============================================================================

RUN_ARROW_SPACING = 16.0  # vertical gap between stacked run arrows (pts)
RUN_ARROW_GAP = 20.0      # gap from content bottom to first run arrow (pts)

def parallel_merge(schemes: List[ParsedScheme], *,
                   equiv_mode: str = "default",
                   strict: bool = True,
                   log=None) -> ET.ElementTree:
    """Merge schemes for the same reaction into one with stacked run arrows.

    Args:
        schemes: Parsed schemes (same reaction, different scales).
        equiv_mode: "default" (keep scheme 1), "no-equiv", "equiv-range".
        strict: If True, reject when products don't match (default).
        log: Logging callback.

    Returns:
        Merged ElementTree.

    Raises:
        ValueError: If strict=True and schemes don't represent the same reaction.
    """
    if log is None:
        log = lambda msg: None

    base = schemes[0]
    log(f"Parallel merge: {len(schemes)} schemes, "
        f"base = {os.path.basename(base.path)}")

    # Validate: all schemes must have the same products
    for i, s in enumerate(schemes[1:], 2):
        if not _products_match(base, s):
            msg = (f"Scheme {i} ({os.path.basename(s.path)}) has different "
                   f"products from scheme 1 ({os.path.basename(base.path)}) "
                   f"— these are not the same reaction")
            if strict:
                raise ValueError(msg)
            log(f"WARNING: {msg}")

        if not _any_reactant_matches(base, s):
            msg = (f"Scheme {i} ({os.path.basename(s.path)}) has no shared "
                   f"reactants with scheme 1 — reagent drawn vs text?")
            log(f"WARNING: {msg}")

    # Deep copy base scheme
    merged_tree = copy.deepcopy(base.tree)
    merged_root = merged_tree.getroot()
    merged_page = merged_root.find(".//page")

    # Identify and remove existing run arrows + their text from the copy
    run_arrow_ids = set()
    run_graphic_ids = set()
    run_text_ids = set()

    # Re-parse the copy to find its arrows
    copy_id_map = _build_page_id_map(merged_page)
    copy_arrows = [el for el in merged_page if el.tag == "arrow"]
    copy_graphics = {}
    for el in merged_page:
        if el.tag == "graphic" and el.get("SupersededBy"):
            copy_graphics[el.get("SupersededBy")] = el

    # Find the main arrow (closest to fragment centroids)
    all_frag_ids = list(base.reactant_ids) + list(base.product_ids)
    frag_cy = _fragment_centroid_y(merged_page, all_frag_ids, copy_id_map)

    main_arrow_el = None
    main_arrow_y = None
    for a in copy_arrows:
        _, _, ay = _get_arrow_coords(a)
        if main_arrow_el is None or abs(ay - frag_cy) < abs(main_arrow_y - frag_cy):
            main_arrow_el = a
            main_arrow_y = ay

    # Everything below main arrow = run arrows to remove
    elements_to_remove = []
    for a in copy_arrows:
        if a is main_arrow_el:
            continue
        _, _, ay = _get_arrow_coords(a)
        if ay > main_arrow_y + 5.0:
            run_arrow_ids.add(a.get("id", ""))
            elements_to_remove.append(a)
            # Also remove corresponding graphic
            aid = a.get("id", "")
            if aid in copy_graphics:
                elements_to_remove.append(copy_graphics[aid])
                run_graphic_ids.add(copy_graphics[aid].get("id", ""))

    # Find run arrow text (near removed arrows)
    for a in list(run_arrow_ids):
        a_el = copy_id_map.get(a)
        if a_el is None:
            continue
        _, _, ra_y = _get_arrow_coords(a_el)
        for el in merged_page:
            if el.tag != "t":
                continue
            p = el.get("p", "")
            if not p:
                continue
            ty = float(p.split()[1])
            if abs(ty - (ra_y + 2.25)) < 6.0:
                elements_to_remove.append(el)
                run_text_ids.add(el.get("id", ""))

    # Remove elements
    for el in elements_to_remove:
        try:
            merged_page.remove(el)
        except ValueError:
            pass  # already removed

    # Also remove graphic for main arrow's superseding graphic if step
    # references a run arrow (clean up stale step metadata)
    # Update step to reference the main arrow's graphic
    merged_scheme = merged_page.find(".//scheme")
    merged_step = merged_scheme.find("step") if merged_scheme is not None else None

    # Handle equivalents
    if equiv_mode == "no-equiv":
        _remove_equiv_labels(merged_page, log)
    elif equiv_mode == "equiv-range":
        _apply_equiv_range(merged_page, schemes, log)

    # Collect all run arrow data from all schemes
    all_run_data = []
    for s in schemes:
        if s.run_arrow_data:
            all_run_data.extend(s.run_arrow_data)
        else:
            # Scheme has no run arrow (no ELN enrichment) — skip
            log(f"  {os.path.basename(s.path)}: no run arrow data")

    if not all_run_data:
        log("WARNING: No run arrow data found in any scheme")
        _update_document_bbox(merged_root, merged_page)
        return merged_tree

    # Get main arrow coordinates from the merged copy
    main_tail_x, main_head_x, _ = _get_arrow_coords(main_arrow_el)

    # Find content bottom (excluding removed elements)
    exclude_ids = run_arrow_ids | run_graphic_ids | run_text_ids
    bottom = _content_bottom(merged_page, exclude_ids)

    # Create stacked run arrows
    next_id = _get_max_id(merged_root) + 1
    next_z = _get_max_z(merged_root) + 1
    run_arrow_y = bottom + RUN_ARROW_GAP

    last_arrow_graphic_id = None

    for i, rad in enumerate(all_run_data):
        if i > 0:
            run_arrow_y += RUN_ARROW_SPACING

        # Create graphic (old-style ref)
        graphic_id = next_id
        next_id += 1
        arrow_id = next_id
        next_id += 1

        graphic = _create_graphic(
            graphic_id, next_z, arrow_id,
            main_tail_x, main_head_x, run_arrow_y,
        )
        next_z += 1
        merged_page.append(graphic)

        arrow = _create_arrow(
            arrow_id, next_z,
            main_tail_x, main_head_x, run_arrow_y,
        )
        next_z += 1
        merged_page.append(arrow)

        last_arrow_graphic_id = graphic_id

        # SM mass text (left of arrow, right-justified)
        text_y = run_arrow_y + 2.25
        if rad.sm_mass_text:
            sm_label = _create_text_element(
                next_id, next_z,
                main_tail_x - 4.0, text_y,
                rad.sm_mass_text, justify="Right",
            )
            next_id += 1
            next_z += 1
            merged_page.append(sm_label)

        # Yield text (right of arrow, left-justified)
        if rad.yield_text:
            yield_label = _create_text_element(
                next_id, next_z,
                main_head_x + 4.0, text_y,
                rad.yield_text, justify="Left",
            )
            next_id += 1
            next_z += 1
            merged_page.append(yield_label)

        log(f"  Run arrow {i+1}: '{rad.sm_mass_text}' -> '{rad.yield_text}' "
            f"at y={run_arrow_y:.1f}")

    # Update step to reference the bottom-most graphic
    # (matching reference file pattern)
    if merged_step is not None and last_arrow_graphic_id is not None:
        merged_step.set("ReactionStepArrows", str(last_arrow_graphic_id))

    _update_document_bbox(merged_root, merged_page)
    return merged_tree


def _remove_equiv_labels(page: ET.Element, log):
    """Remove all standalone equiv labels like '(1.6 eq.)'."""
    equiv_re = re.compile(r'^\s*\(\d+\.?\d*\s*eq\.\)\s*$')
    to_remove = []
    for el in page:
        if el.tag != "t":
            continue
        text = _get_text_content(el)
        if equiv_re.match(text):
            to_remove.append(el)
            log(f"  Removing equiv label: '{text}'")

    for el in to_remove:
        page.remove(el)

    # Also remove equiv suffixes from conditions text
    for el in page:
        if el.tag != "t":
            continue
        _strip_equiv_from_conditions(el)


def _strip_equiv_from_conditions(t_elem: ET.Element):
    """Remove ' (X eq.)' suffixes from conditions text <s> elements."""
    equiv_suffix = re.compile(r'\s*\(\d+\.?\d*\s*eq\.\)')
    for s in t_elem.iter("s"):
        if s.text:
            new_text = equiv_suffix.sub("", s.text)
            if new_text != s.text:
                s.text = new_text


def _apply_equiv_range(page: ET.Element, schemes: List[ParsedScheme], log):
    """Replace equiv values with ranges when they differ across schemes."""
    # Collect equiv values per reagent name
    reagent_equivs: Dict[str, List[float]] = {}
    for s in schemes:
        for ei in s.equiv_values:
            name = ei.reagent_name.lower()
            if name not in reagent_equivs:
                reagent_equivs[name] = []
            reagent_equivs[name].append(ei.equiv_value)

    if not reagent_equivs:
        return

    # Build replacement map: old equiv text -> new equiv text
    equiv_re = re.compile(r'\((\d+\.?\d*)\s*eq\.\)')

    for el in page:
        if el.tag != "t":
            continue
        text = _get_text_content(el)
        if not text:
            continue

        # Check if this is a standalone equiv label
        standalone_m = re.match(r'^\s*\((\d+\.?\d*)\s*eq\.\)\s*$', text)
        if standalone_m:
            val = float(standalone_m.group(1))
            # Find which reagent this belongs to by matching value
            for name, vals in reagent_equivs.items():
                if val in vals:
                    min_v, max_v = min(vals), max(vals)
                    if min_v != max_v:
                        new_text = f"({min_v:.2g} - {max_v:.2g} eq.)"
                        log(f"  Equiv range: '{text}' -> '{new_text}'")
                        for s in el.iter("s"):
                            s.text = new_text
                        recompute_text_bbox(el)
                    break
            continue

        # Multi-line conditions: replace inline equiv values
        for s in el.iter("s"):
            if s.text:
                def _replace_equiv(m):
                    val = float(m.group(1))
                    for name, vals in reagent_equivs.items():
                        if val in vals:
                            min_v, max_v = min(vals), max(vals)
                            if min_v != max_v:
                                return f"({min_v:.2g} - {max_v:.2g} eq.)"
                    return m.group(0)
                s.text = equiv_re.sub(_replace_equiv, s.text)


# ============================================================================
# Sequential merge
# ============================================================================

def sequential_merge(schemes: List[ParsedScheme], *,
                     ref_cdxml: str = None,
                     log=None) -> ET.ElementTree:
    """Merge schemes where step N product = step N+1 starting material.

    Creates a multi-step linear scheme.

    Args:
        schemes: Parsed schemes in reaction order.
        ref_cdxml: Reference CDXML for final product alignment.
        log: Logging callback.

    Returns:
        Merged ElementTree.
    """
    if log is None:
        log = lambda msg: None

    log(f"Sequential merge: {len(schemes)} steps")

    # Validate sequential linkage
    links = []  # (product_frag_id_in_step_i, reactant_frag_id_in_step_i+1)
    for i in range(len(schemes) - 1):
        s_cur = schemes[i]
        s_next = schemes[i + 1]
        found = False
        for pid in s_cur.product_ids:
            pfrag = s_cur.fragments.get(pid)
            psmiles = s_cur.fragment_smiles.get(pid, "")
            if pfrag is None:
                continue
            for rid in s_next.reactant_ids:
                rfrag = s_next.fragments.get(rid)
                rsmiles = s_next.fragment_smiles.get(rid, "")
                if rfrag is None:
                    continue
                if _fragments_same_molecule(pfrag, rfrag, psmiles, rsmiles):
                    links.append((pid, rid))
                    log(f"  Step {i+1} product {pid} matches "
                        f"step {i+2} reactant {rid}")
                    found = True
                    break
            if found:
                break
        if not found:
            log(f"WARNING: No product/reactant match between "
                f"step {i+1} and step {i+2}")
            links.append(("", ""))

    # --- Alignment cascade (backwards from final product) ---
    _alignment_cascade(schemes, links, ref_cdxml, log)

    # --- Assemble the merged CDXML ---
    # Use first scheme's root as template for document settings
    base_root = schemes[0].root
    merged_root = ET.Element("CDXML")
    for attr_name in base_root.keys():
        merged_root.set(attr_name, base_root.get(attr_name))

    # Copy colortable and fonttable
    for child_tag in ("colortable", "fonttable"):
        src = base_root.find(child_tag)
        if src is not None:
            merged_root.append(copy.deepcopy(src))

    # Create page
    base_page = schemes[0].page
    merged_page = ET.SubElement(merged_root, "page")
    for attr_name in base_page.keys():
        merged_page.set(attr_name, base_page.get(attr_name))

    # --- ID remapping and element collection ---
    next_id = 1
    next_z = 1

    # For each step, collect the elements we need and remap their IDs
    step_data = []  # list of dicts per step

    for step_idx, s in enumerate(schemes):
        sd = {
            "elements": [],       # (element, role) tuples to add to page
            "reactant_ids": [],   # remapped IDs
            "product_ids": [],    # remapped IDs
            "above_ids": [],      # remapped IDs
            "below_ids": [],      # remapped IDs
            "arrow_id": "",       # remapped main arrow ID
            "graphic_id": "",     # remapped main graphic ID
            "other_ids": [],      # remapped IDs of elements with no step role
            "skip_reactant_ids": set(),  # IDs to skip (shared intermediate)
            "orig_arrow_cx": 0.0, # original arrow center for delta computation
        }

        # Record original arrow center for computing layout deltas
        if s.main_arrow is not None:
            sd["orig_arrow_cx"] = (s.arrow_tail_x + s.arrow_head_x) / 2.0

        # If this is not the first step, the shared intermediate (which is
        # step N-1's product) is already in the merged page. Skip the
        # duplicate reactant.
        if step_idx > 0 and links[step_idx - 1][1]:
            sd["skip_reactant_ids"].add(links[step_idx - 1][1])

        # Deep copy all page elements and remap IDs
        old_to_new = {}

        # Collect elements from this scheme's page
        for el in s.page:
            if el.tag in ("scheme",):
                continue  # will rebuild scheme/step

            eid = el.get("id", "")

            # Skip elements belonging to run arrows (we'll rebuild them)
            if eid in {a.get("id", "") for a in s.run_arrows}:
                continue
            if eid in {g.get("id", "") for g in s.run_graphics}:
                continue
            if eid in set(s.run_arrow_text_ids):
                continue

            # Skip the duplicate reactant
            if eid in sd["skip_reactant_ids"]:
                continue

            # Skip standalone equiv labels — these are redundant in multi-step
            # schemes because the conditions text already contains equiv info
            # (e.g. "PPh₃ (1.6 eq.)"). ELN enrichment adds these as separate
            # text elements next to fragments, but they cause overlap when
            # the layout rearranges positions.
            if el.tag == "t":
                text = _get_text_content(el)
                if re.match(r'^\s*\(\d+\.?\d*\s*eq\.\)\s*$', text):
                    log(f"  Skipping standalone equiv label: '{text}'")
                    continue

            el_copy = copy.deepcopy(el)

            # Remap all IDs in this element subtree
            _remap_element_ids(el_copy, old_to_new, next_id, next_z)
            next_id = max(next_id, _get_max_id_in_element(el_copy) + 1)
            next_z = max(next_z, _get_max_z_in_element(el_copy) + 1)

            # Determine role
            role = "other"
            if eid in s.reactant_ids:
                role = "reactant"
            elif eid in s.product_ids:
                role = "product"
            elif eid in s.above_arrow_ids:
                role = "above"
            elif eid in s.below_arrow_ids:
                role = "below"
            elif el.tag == "arrow" and eid == s.main_arrow_id:
                role = "main_arrow"
            elif el.tag == "graphic" and s.main_arrow is not None and \
                    el.get("SupersededBy") == s.main_arrow_id:
                role = "main_graphic"

            sd["elements"].append((el_copy, role, eid))

        # FIX 1: After all elements collected, fix cross-references with
        # the complete old_to_new mapping. When _remap_element_ids processes
        # elements individually, a graphic's SupersededBy might reference an
        # arrow that hasn't been assigned a new ID yet. Now old_to_new is
        # complete for this step, so we fix any stale references.
        for el_copy, role, old_id in sd["elements"]:
            for node in el_copy.iter():
                for attr in ("SupersededBy",):
                    ref = node.get(attr)
                    if ref and ref in old_to_new:
                        node.set(attr, old_to_new[ref])

        # Build remapped ID lists
        for el_copy, role, old_id in sd["elements"]:
            new_id = el_copy.get("id", "")
            if role == "reactant":
                sd["reactant_ids"].append(new_id)
            elif role == "product":
                sd["product_ids"].append(new_id)
            elif role == "above":
                sd["above_ids"].append(new_id)
            elif role == "below":
                sd["below_ids"].append(new_id)
            elif role == "main_arrow":
                sd["arrow_id"] = new_id
            elif role == "main_graphic":
                sd["graphic_id"] = new_id
            elif role == "other":
                sd["other_ids"].append(new_id)

        # If shared intermediate was skipped, use the previous step's product ID
        if step_idx > 0 and links[step_idx - 1][1]:
            prev_sd = step_data[step_idx - 1]
            # The intermediate is the product of the previous step
            if prev_sd["product_ids"]:
                intermediate_id = prev_sd["product_ids"][0]
                sd["reactant_ids"].insert(0, intermediate_id)

        step_data.append(sd)

    # --- Horizontal layout ---
    bond_len = ACS_BOND_LENGTH
    frag_gap = bond_len * LAYOUT_FRAG_GAP_BONDS
    inter_gap = bond_len * LAYOUT_INTER_GAP_BONDS

    # Add all elements to the merged page first
    all_elements = {}  # id -> element
    for sd in step_data:
        for el_copy, role, old_id in sd["elements"]:
            merged_page.append(el_copy)
            new_id = el_copy.get("id", "")
            all_elements[new_id] = el_copy

    # Now lay out step by step, left to right
    cursor_x = 100.0  # starting x position
    arrow_y = None  # will be set from first step's reactant centroids

    # Compute a common arrow_y from all reactant fragments
    all_reactant_bbs = []
    for sd in step_data:
        for rid in sd["reactant_ids"]:
            el = all_elements.get(rid)
            if el is not None and el.tag == "fragment":
                bb = fragment_bbox(el)
                if bb:
                    all_reactant_bbs.append(bb)
    if all_reactant_bbs:
        arrow_y = sum((bb[1] + bb[3]) / 2.0 for bb in all_reactant_bbs) / len(all_reactant_bbs)
    else:
        arrow_y = 200.0  # fallback

    placed_ids = set()  # track already-placed fragment IDs (for shared intermediates)

    for step_idx, sd in enumerate(step_data):
        # Place reactants (skip shared intermediate if already placed)
        for rid in sd["reactant_ids"]:
            if rid in placed_ids:
                # Already placed as previous step's product — account for its width
                el = all_elements.get(rid)
                if el is not None:
                    bb = _get_element_bbox(el)
                    if bb:
                        cursor_x = bb[2] + frag_gap  # right edge + gap
                continue

            el = all_elements.get(rid)
            if el is None or el.tag != "fragment":
                continue
            # Use atom-only bbox for centering (avoids salt/counterion inflation)
            bb_atoms = fragment_bbox(el)
            bb_full = _get_element_bbox(el)
            bb = bb_atoms if bb_atoms else bb_full
            if bb is None:
                continue
            w = bb[2] - bb[0]
            cy = (bb[1] + bb[3]) / 2.0
            dx = (cursor_x + w / 2.0) - (bb[0] + bb[2]) / 2.0
            dy = arrow_y - cy
            _shift_element(el, dx, dy)
            placed_ids.add(rid)
            full_w = (bb_full[2] - bb_full[0]) if bb_full else w
            cursor_x += max(w, full_w) + inter_gap

        # Replace last inter_gap with frag_gap before arrow
        if sd["reactant_ids"]:
            cursor_x = cursor_x - inter_gap + frag_gap

        # Compute arrow length from above/below content
        above_els = [all_elements.get(i) for i in sd["above_ids"]
                     if all_elements.get(i) is not None]
        below_els = [all_elements.get(i) for i in sd["below_ids"]
                     if all_elements.get(i) is not None]
        min_arrow = bond_len * 5.0
        max_w = 0.0
        for el in above_els + below_els:
            if el is not None:
                bb = _get_element_bbox(el)
                if bb:
                    w = bb[2] - bb[0]
                    if w > max_w:
                        max_w = w
        arrow_len = max(min_arrow, max_w + 10.0)

        # Place arrow
        tail_x = cursor_x
        head_x = cursor_x + arrow_len
        arrow_cx = (tail_x + head_x) / 2.0

        arrow_el = all_elements.get(sd["arrow_id"])
        if arrow_el is not None:
            arrow_el.set("Tail3D", f"{tail_x:.2f} {arrow_y:.2f} 0")
            arrow_el.set("Head3D", f"{head_x:.2f} {arrow_y:.2f} 0")
            bb_top = arrow_y - 1.64
            bb_bot = arrow_y + 1.52
            arrow_el.set("BoundingBox",
                         f"{tail_x:.2f} {bb_top:.2f} {head_x:.2f} {bb_bot:.2f}")
            # Center3D etc.
            cx_3d = arrow_cx + 280.0
            cy_3d = arrow_y + 130.0
            half_len = arrow_len / 2.0
            arrow_el.set("Center3D", f"{cx_3d:.2f} {cy_3d:.2f} 0")
            arrow_el.set("MajorAxisEnd3D",
                         f"{cx_3d + half_len:.2f} {cy_3d:.2f} 0")
            arrow_el.set("MinorAxisEnd3D",
                         f"{cx_3d:.2f} {cy_3d + half_len:.2f} 0")

        # Update graphic
        graphic_el = all_elements.get(sd["graphic_id"])
        if graphic_el is not None:
            graphic_el.set("BoundingBox",
                           f"{head_x:.2f} {arrow_y:.2f} "
                           f"{tail_x:.2f} {arrow_y:.2f}")

        # Stack above/below arrow objects
        for el in above_els:
            if el is None:
                continue
            if el.tag == "t":
                # Text goes below arrow
                pass  # handled in below stacking
            else:
                bb = _get_element_bbox(el)
                if bb is None:
                    continue
                h = bb[3] - bb[1]
                if el.tag == "fragment" and fragment_bottom_has_hanging_label(el):
                    gap = LAYOUT_HANGING_LABEL_GAP
                else:
                    gap = LAYOUT_ABOVE_GAP
                target_bottom = arrow_y - gap
                target_cy = target_bottom - h / 2.0
                _move_element_to(el, arrow_cx, target_cy)

        # Below arrow: collect all text (from above + below lists)
        above_texts = [all_elements.get(i) for i in sd["above_ids"]
                       if all_elements.get(i) is not None
                       and all_elements[i].tag == "t"]
        below_texts = [all_elements.get(i) for i in sd["below_ids"]
                       if all_elements.get(i) is not None
                       and all_elements[i].tag == "t"]
        all_below_text = above_texts + below_texts

        BASELINE_OFFSET = 10.0
        TEXT_ELEMENT_GAP = 2.0  # gap between consecutive text elements
        y_cursor = arrow_y + LAYOUT_BELOW_GAP + BASELINE_OFFSET
        for el in all_below_text:
            if el is None:
                continue
            el.set("p", f"{arrow_cx:.2f} {y_cursor:.2f}")
            el.set("CaptionJustification", "Center")
            el.set("Justification", "Center")
            recompute_text_bbox(el)
            # Advance cursor past this element's full height
            bb_str = el.get("BoundingBox", "")
            if bb_str:
                bb_vals = [float(v) for v in bb_str.split()]
                if len(bb_vals) >= 4:
                    y_cursor = bb_vals[3] + TEXT_ELEMENT_GAP
                else:
                    y_cursor += 13.0
            else:
                y_cursor += 13.0

        cursor_x = head_x + frag_gap

        # Place products — use main-component bbox for centering to handle
        # salt products (e.g. amine + HCl where counterion is far from main)
        for pid in sd["product_ids"]:
            if pid in placed_ids:
                continue
            el = all_elements.get(pid)
            if el is None or el.tag != "fragment":
                continue
            # Use main-component bbox for centering (ignores distant counterions)
            bb_main = _fragment_main_component_bbox(el)
            bb_full = _get_element_bbox(el)
            bb = bb_main if bb_main else bb_full
            if bb is None:
                continue
            w = bb[2] - bb[0]
            cy = (bb[1] + bb[3]) / 2.0
            # Move using main-component center
            dx = (cursor_x + w / 2.0) - (bb[0] + bb[2]) / 2.0
            dy = arrow_y - cy
            _shift_element(el, dx, dy)
            placed_ids.add(pid)
            # Use full bbox width for cursor advance (accounts for labels)
            full_w = (bb_full[2] - bb_full[0]) if bb_full else w
            cursor_x += max(w, full_w) + inter_gap

        # After products, replace inter_gap with frag_gap for next step
        cursor_x = cursor_x - inter_gap + frag_gap

        # FIX 2: Shift "other" elements (standalone equiv labels etc.)
        # by the same horizontal delta as the step's arrow moved.
        new_arrow_cx = arrow_cx  # arrow_cx was set above during arrow placement
        orig_cx = sd["orig_arrow_cx"]
        if orig_cx and sd["other_ids"]:
            delta_x = new_arrow_cx - orig_cx
            for oid in sd["other_ids"]:
                oel = all_elements.get(oid)
                if oel is not None:
                    _shift_element(oel, delta_x, 0.0)

    # --- Create multi-step <scheme> ---
    scheme_el = ET.SubElement(merged_page, "scheme")
    scheme_el.set("id", str(next_id))
    next_id += 1

    for sd in step_data:
        step_el = ET.SubElement(scheme_el, "step")
        step_el.set("id", str(next_id))
        next_id += 1
        step_el.set("ReactionStepReactants",
                     " ".join(sd["reactant_ids"]))
        step_el.set("ReactionStepProducts",
                     " ".join(sd["product_ids"]))
        if sd["graphic_id"]:
            step_el.set("ReactionStepArrows", sd["graphic_id"])
        elif sd["arrow_id"]:
            step_el.set("ReactionStepArrows", sd["arrow_id"])
        step_el.set("ReactionStepObjectsAboveArrow",
                     " ".join(sd["above_ids"]))
        step_el.set("ReactionStepObjectsBelowArrow",
                     " ".join(sd["below_ids"]))

    # --- Add run arrows per step ---
    for step_idx, (sd, s) in enumerate(zip(step_data, schemes)):
        if not s.run_arrow_data:
            continue

        arrow_el = all_elements.get(sd["arrow_id"])
        if arrow_el is None:
            continue
        step_tail_x, step_head_x, step_y = _get_arrow_coords(arrow_el)

        # Find content bottom for this step's column
        bottom = step_y
        for eid in (sd["above_ids"] + sd["below_ids"] +
                    sd["reactant_ids"] + sd["product_ids"]):
            el = all_elements.get(eid)
            if el is not None:
                bb = _get_element_bbox(el)
                if bb and bb[3] > bottom:
                    bottom = bb[3]

        run_y = bottom + RUN_ARROW_GAP
        for i, rad in enumerate(s.run_arrow_data):
            if i > 0:
                run_y += RUN_ARROW_SPACING

            g_id = next_id
            next_id += 1
            a_id = next_id
            next_id += 1

            graphic = _create_graphic(
                g_id, next_z, a_id,
                step_tail_x, step_head_x, run_y,
            )
            next_z += 1
            merged_page.append(graphic)

            arrow = _create_arrow(
                a_id, next_z,
                step_tail_x, step_head_x, run_y,
            )
            next_z += 1
            merged_page.append(arrow)

            text_y = run_y + 2.25
            if rad.sm_mass_text:
                merged_page.append(_create_text_element(
                    next_id, next_z,
                    step_tail_x - 4.0, text_y,
                    rad.sm_mass_text, justify="Right",
                ))
                next_id += 1
                next_z += 1

            if rad.yield_text:
                merged_page.append(_create_text_element(
                    next_id, next_z,
                    step_head_x + 4.0, text_y,
                    rad.yield_text, justify="Left",
                ))
                next_id += 1
                next_z += 1

    # Increase page width if needed
    merged_page.set("WidthPages", "4")

    _update_document_bbox(merged_root, merged_page)

    merged_tree = ET.ElementTree(merged_root)
    return merged_tree


def _remap_element_ids(el: ET.Element, old_to_new: Dict[str, str],
                       start_id: int, start_z: int):
    """Remap all id/Z attributes and cross-references in an element subtree.

    Populates old_to_new mapping as a side effect.
    """
    # Phase 1: assign new IDs
    counter = [start_id, start_z]
    for node in el.iter():
        old_id = node.get("id")
        if old_id and old_id not in old_to_new:
            new_id = str(counter[0])
            old_to_new[old_id] = new_id
            counter[0] += 1

    # Phase 2: apply mapping
    for node in el.iter():
        # Remap id
        old_id = node.get("id")
        if old_id and old_id in old_to_new:
            node.set("id", old_to_new[old_id])

        # Remap Z (just increment to avoid conflicts)
        z = node.get("Z")
        if z:
            node.set("Z", str(counter[1]))
            counter[1] += 1

        # Remap bond references
        for attr in ("B", "E"):
            ref = node.get(attr)
            if ref and ref in old_to_new:
                node.set(attr, old_to_new[ref])

        # Remap SupersededBy
        sup = node.get("SupersededBy")
        if sup and sup in old_to_new:
            node.set("SupersededBy", old_to_new[sup])

        # Remap BondCircularOrdering
        bco = node.get("BondCircularOrdering")
        if bco:
            parts = bco.split()
            new_parts = [old_to_new.get(p, p) for p in parts]
            node.set("BondCircularOrdering", " ".join(new_parts))


def _get_max_id_in_element(el: ET.Element) -> int:
    """Get max id in an element subtree."""
    max_id = 0
    for node in el.iter():
        eid = node.get("id", "")
        if eid:
            try:
                max_id = max(max_id, int(eid))
            except ValueError:
                pass
    return max_id


def _get_max_z_in_element(el: ET.Element) -> int:
    """Get max Z in an element subtree."""
    max_z = 0
    for node in el.iter():
        z = node.get("Z", "")
        if z:
            try:
                max_z = max(max_z, int(z))
            except ValueError:
                pass
    return max_z


# ============================================================================
# Alignment cascade for sequential merge
# ============================================================================

def _alignment_cascade(schemes: List[ParsedScheme],
                       links: List[Tuple[str, str]],
                       ref_cdxml: str, log):
    """Align all structures backwards from the final product.

    Modifies scheme trees in-place.
    """
    try:
        from .alignment import (
            align_product_to_reference,
            rdkit_align_to_product,
        )
        has_alignment = True
    except ImportError:
        has_alignment = False
        log("WARNING: alignment module not available — skipping alignment")
        return

    # Process backwards from last step
    for step_idx in range(len(schemes) - 1, -1, -1):
        s = schemes[step_idx]
        root = s.root

        if step_idx == len(schemes) - 1 and ref_cdxml:
            # Last step: align product to external reference
            log(f"  Step {step_idx+1}: aligning product to reference {ref_cdxml}")
            try:
                align_product_to_reference(root, ref_cdxml, verbose=False)
            except Exception as e:
                log(f"  WARNING: align_product_to_reference failed: {e}")

        elif step_idx < len(schemes) - 1:
            # Earlier step: align this step's product to the already-aligned
            # version of the same molecule from the next step's reactant side.
            next_s = schemes[step_idx + 1]
            link_product_id, link_reactant_id = links[step_idx]

            if link_reactant_id and link_reactant_id in next_s.fragments:
                # Write the aligned reactant from next step to a temp CDXML
                aligned_frag = next_s.fragments[link_reactant_id]
                try:
                    ref_path = _write_temp_fragment_cdxml(aligned_frag, s.root)
                    log(f"  Step {step_idx+1}: aligning product to "
                        f"step {step_idx+2}'s aligned reactant")
                    align_product_to_reference(root, ref_path, verbose=False)
                    os.unlink(ref_path)
                except Exception as e:
                    log(f"  WARNING: cross-step alignment failed: {e}")

        # Align all structures within this step to the product
        log(f"  Step {step_idx+1}: aligning reactants/reagents to product")
        try:
            rdkit_align_to_product(root, verbose=False)
        except Exception as e:
            log(f"  WARNING: within-step alignment failed: {e}")


def _write_temp_fragment_cdxml(frag: ET.Element,
                               source_root: ET.Element) -> str:
    """Write a single fragment to a temporary CDXML file for use as alignment ref."""
    from ..constants import CDXML_MINIMAL_HEADER, CDXML_FOOTER

    frag_copy = copy.deepcopy(frag)
    # Wrap in minimal CDXML
    content = CDXML_MINIMAL_HEADER
    content += ET.tostring(frag_copy, encoding="unicode")
    content += CDXML_FOOTER

    fd, path = tempfile.mkstemp(suffix=".cdxml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Merge ELN-enriched reaction schemes (auto-detects mode).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("inputs", nargs="+", metavar="CDXML",
                        help="Input CDXML files (2 or more)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output CDXML path "
                             "(default: auto-generated from input names)")

    # Mode: auto-detect by default, explicit override available
    parser.add_argument("--mode", choices=["auto", "parallel", "sequential"],
                        default="auto",
                        help="Merge mode (default: auto-detect)")
    # Backward-compat aliases (deprecated)
    parser.add_argument("--parallel", action="store_true",
                        help=argparse.SUPPRESS)  # deprecated
    parser.add_argument("--sequential", action="store_true",
                        help=argparse.SUPPRESS)  # deprecated

    # Parallel options
    parser.add_argument("--no-equiv", action="store_true",
                        help="Remove all equivalents labels")
    parser.add_argument("--equiv-range", action="store_true",
                        help="Show equiv range when values differ")

    # Sequential options
    parser.add_argument("--ref-cdxml", default=None,
                        help="Reference CDXML for final product alignment")

    # Unrelated handling
    parser.add_argument("--adjacent", action="store_true", default=True,
                        help="Place unrelated reactions side by side (default)")
    parser.add_argument("--no-adjacent", action="store_true",
                        help="Error if any reactions are unrelated")

    # Common
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print progress to stderr")
    parser.add_argument("--render", action="store_true",
                        help="Render output to PNG via cdxml_to_image.py")

    args = parser.parse_args()

    # Handle deprecated flags
    mode = args.mode
    if args.parallel:
        print("WARNING: --parallel is deprecated, use --mode parallel",
              file=sys.stderr)
        mode = "parallel"
    elif args.sequential:
        print("WARNING: --sequential is deprecated, use --mode sequential",
              file=sys.stderr)
        mode = "sequential"

    if len(args.inputs) < 2:
        parser.error("Need at least 2 input files")

    for path in args.inputs:
        if not os.path.isfile(path):
            parser.error(f"File not found: {path}")

    log = (lambda msg: print(msg, file=sys.stderr)) if args.verbose else (lambda msg: None)

    # Parse all input schemes
    schemes = []
    for path in args.inputs:
        try:
            ps = parse_scheme(path, log=log)
            schemes.append(ps)
        except Exception as e:
            print(f"ERROR: Failed to parse {path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Determine equiv mode
    equiv_mode = "default"
    if args.no_equiv:
        equiv_mode = "no-equiv"
    elif args.equiv_range:
        equiv_mode = "equiv-range"

    allow_adjacent = not args.no_adjacent

    # Merge
    try:
        if mode == "auto":
            plan = auto_detect(schemes, log=log)
            log(f"Detected: {plan.describe()}")
            merged_tree = execute_merge_plan(
                schemes, plan,
                equiv_mode=equiv_mode,
                ref_cdxml=args.ref_cdxml,
                allow_adjacent=allow_adjacent,
                log=log,
            )
        elif mode == "parallel":
            merged_tree = parallel_merge(
                schemes, equiv_mode=equiv_mode, strict=True, log=log)
        elif mode == "sequential":
            merged_tree = sequential_merge(
                schemes, ref_cdxml=args.ref_cdxml, log=log)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        out_path = args.output
    else:
        # Auto-generate from input names
        stems = []
        for p in args.inputs:
            stem = os.path.splitext(os.path.basename(p))[0]
            # Strip common suffixes like "-scheme"
            stem = re.sub(r'-scheme$', '', stem)
            stems.append(stem)
        # Find common prefix
        prefix = os.path.commonprefix(stems)
        if prefix and prefix[-1] == '-':
            prefix = prefix[:-1]
        if prefix:
            # Use prefix + unique suffixes
            suffixes = []
            for s in stems:
                suffix = s[len(prefix):].lstrip('-')
                if suffix:
                    suffixes.append(suffix)
            if suffixes:
                out_name = f"{prefix}-{'+'.join(suffixes)}-merged.cdxml"
            else:
                out_name = f"{prefix}-merged.cdxml"
        else:
            out_name = f"{stems[0]}-merged.cdxml"
        out_dir = os.path.dirname(args.inputs[0])
        out_path = os.path.join(out_dir, out_name)

    # Write output
    write_cdxml(merged_tree, out_path)
    log(f"Written: {out_path}")
    print(out_path)

    # Optional render
    if args.render:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        render_script = os.path.join(script_dir, "cdxml_to_image.py")
        if os.path.isfile(render_script):
            subprocess.run(
                [sys.executable, render_script, out_path],
                capture_output=True, text=True,
            )
            log(f"Rendered: {os.path.splitext(out_path)[0]}.png")


if __name__ == "__main__":
    main()
