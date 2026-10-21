#!/usr/bin/env python3
"""
reaction_cleanup.py — Clean up a CDXML reaction scheme layout (pure Python).

Replaces ChemDraw COM "Clean Up Reaction" with algorithmic layout.
Offers multiple approaches that can be compared side-by-side.

Usage
-----
  python reaction_cleanup.py input.cdxml                          # default approach
  python reaction_cleanup.py input.cdxml -o out.cdxml             # explicit output
  python reaction_cleanup.py input.cdxml --approach bbox_center   # pick approach
  python reaction_cleanup.py input.cdxml --all                    # run all 6 approaches
  python reaction_cleanup.py input.cdxml --all --render           # run all + PNG

Approaches
----------
  1. bbox_center     — Bounding-box centroid alignment + uniform gaps
  2. arrow_driven    — Arrow length drives layout; molecules placed relative to arrow ends
  3. proportional    — Gap sizes proportional to molecule widths
  4. compact         — Minimal gaps; tight layout for slides/posters
  5. golden_ratio    — Arrow length and gaps use golden ratio proportions
  6. chemdraw_mimic  — Closest emulation of ChemDraw's own cleanup heuristics
"""

import argparse
import copy
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from ..constants import (
    ACS_BOND_LENGTH,
    LAYOUT_ABOVE_GAP,
    LAYOUT_BELOW_GAP,
    LAYOUT_FRAG_GAP_BONDS,
    LAYOUT_HANGING_LABEL_GAP,
    LAYOUT_INTER_FRAGMENT_GAP,
    LAYOUT_INTER_GAP_BONDS,
)
from ..cdxml_utils import (
    fragment_bbox,
    fragment_bottom_has_hanging_label,
    parse_cdxml,
    recompute_text_bbox,
    write_cdxml,
)

# Backward-compat alias (imported by eln_enrichment.py)
_recompute_text_bbox = recompute_text_bbox

# Below-arrow fragment padding (not in shared constants)
LAYOUT_BELOW_FRAG_PAD = 2.0


# ---------------------------------------------------------------------------
# CDXML geometry helpers
# ---------------------------------------------------------------------------


def _get_page(root: ET.Element) -> Optional[ET.Element]:
    return root.find("page")


def _build_id_map(page: ET.Element) -> Dict[str, ET.Element]:
    """Map element id → element for all direct children of page."""
    m: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            m[eid] = el
    return m


def _get_step(page: ET.Element) -> Optional[ET.Element]:
    """Find the first <step> inside a <scheme> on the page."""
    scheme = page.find("scheme")
    if scheme is None:
        return None
    return scheme.find("step")


def _get_arrow(page: ET.Element, step: ET.Element,
               id_map: Dict[str, ET.Element]) -> Optional[ET.Element]:
    """Resolve the arrow element from step metadata."""
    arrow_ids = step.get("ReactionStepArrows", "").split()
    for aid in arrow_ids:
        el = id_map.get(aid)
        if el is not None and el.tag == "arrow":
            return el
        # Check for graphic superseded by arrow
        if el is not None and el.tag == "graphic":
            sup_id = el.get("SupersededBy", "")
            if sup_id:
                arrow_el = id_map.get(sup_id)
                if arrow_el is not None:
                    return arrow_el
        # Also search all page children for graphic → arrow chain
        for child in page:
            if child.tag == "graphic" and child.get("id") == aid:
                sup_id = child.get("SupersededBy", "")
                if sup_id:
                    for child2 in page:
                        if child2.get("id") == sup_id:
                            return child2
    return None


def _arrow_endpoints(arrow: ET.Element) -> Tuple[float, float, float, float]:
    """Return (tail_x, tail_y, head_x, head_y) from arrow element."""
    from ..cdxml_utils import arrow_endpoints
    return arrow_endpoints(arrow)



# _fragment_bbox and _fragment_bottom_has_hanging_label are now in cdxml_utils


def _text_bbox(t_el: ET.Element) -> Tuple[float, float, float, float]:
    """Bounding box of a text element."""
    bb = t_el.get("BoundingBox", "")
    if bb:
        vals = [float(v) for v in bb.split()]
        if len(vals) >= 4:
            return vals[0], vals[1], vals[2], vals[3]
    p = t_el.get("p", "")
    if p:
        parts = [float(v) for v in p.split()]
        # Estimate text size
        text_content = "".join(s.text or "" for s in t_el.iter("s"))
        w = len(text_content) * 5.8
        h = 12.0 * max(1, text_content.count("\n") + 1)
        return parts[0] - w/2, parts[1] - h, parts[0] + w/2, parts[1]
    return 0, 0, 0, 0



# _recompute_text_bbox is now imported from cdxml_utils (alias at top of file)


def _estimate_text_width(t_el: ET.Element) -> float:
    """Estimate text width from content (5.8 pt/char for Arial 10pt).

    Uses the same character-width estimate as _recompute_text_bbox but
    without modifying the element.  Immune to stale BoundingBox values
    from upstream processing (e.g. ELN exports with non-ACS scaling).
    """
    text_content = "".join(s.text or "" for s in t_el.iter("s"))
    lines = text_content.split("\n") if "\n" in text_content else [text_content]
    max_line_len = max((len(l) for l in lines), default=0)
    return max_line_len * 5.8


def _element_bbox(el: ET.Element) -> Tuple[float, float, float, float]:
    """Bounding box for any element (fragment or text)."""
    if el.tag == "fragment":
        bb = fragment_bbox(el)
        return bb if bb is not None else (0, 0, 0, 0)
    elif el.tag == "t":
        return _text_bbox(el)
    bb = el.get("BoundingBox", "")
    if bb:
        vals = [float(v) for v in bb.split()]
        if len(vals) >= 4:
            return vals[0], vals[1], vals[2], vals[3]
    return 0, 0, 0, 0


def _bbox_center(bb: Tuple[float, float, float, float]) -> Tuple[float, float]:
    return (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0


def _bbox_width(bb: Tuple[float, float, float, float]) -> float:
    return bb[2] - bb[0]


def _bbox_height(bb: Tuple[float, float, float, float]) -> float:
    return bb[3] - bb[1]


# ---------------------------------------------------------------------------
# Element shifting / positioning
# ---------------------------------------------------------------------------

def _shift_element(el: ET.Element, dx: float, dy: float):
    """Translate an element (fragment or text) by (dx, dy).

    For fragments, shifts ALL descendant nodes and text elements
    (including those inside inner NodeType="Fragment" sub-structures).
    This is correct because all coordinates live in the same space.
    Also shifts BoundingBox attributes on all sub-elements.
    """
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
            _shift_text_element(t, dx, dy)
        # Shift BoundingBox on the fragment itself
        _shift_bbox_attr(el, dx, dy)
        # Also shift BoundingBox on any inner <fragment> elements
        for inner_frag in el.iter("fragment"):
            if inner_frag is not el:
                _shift_bbox_attr(inner_frag, dx, dy)

    elif el.tag == "t":
        _shift_text_element(el, dx, dy)


def _shift_text_element(t: ET.Element, dx: float, dy: float):
    """Shift a <t> element's position and bounding box."""
    p = t.get("p")
    if p:
        parts = p.split()
        if len(parts) >= 2:
            nx = float(parts[0]) + dx
            ny = float(parts[1]) + dy
            t.set("p", f"{nx:.2f} {ny:.2f}")
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


def _set_arrow(arrow: ET.Element, tail_x: float, tail_y: float,
               head_x: float, head_y: float):
    """Set arrow endpoints and update its bounding box."""
    arrow.set("Tail3D", f"{tail_x:.2f} {tail_y:.2f} 0")
    arrow.set("Head3D", f"{head_x:.2f} {head_y:.2f} 0")
    # Update Center3D and axis ends (elliptical arc geometry — ChemDraw internal)
    cx = (tail_x + head_x) / 2.0
    cy = (tail_y + head_y) / 2.0
    half_len = abs(head_x - tail_x) / 2.0
    arrow.set("Center3D", f"{cx + 280:.2f} {cy + 130:.2f} 0")
    arrow.set("MajorAxisEnd3D", f"{cx + 280 + half_len:.2f} {cy + 130:.2f} 0")
    arrow.set("MinorAxisEnd3D", f"{cx + 280:.2f} {cy + 130 + half_len:.2f} 0")
    # BoundingBox
    pad = 2.0
    bb_x1 = min(tail_x, head_x)
    bb_x2 = max(tail_x, head_x)
    arrow.set("BoundingBox",
              f"{bb_x1:.2f} {tail_y - pad:.2f} {bb_x2:.2f} {tail_y + pad:.2f}")
    # Also update the superseding graphic if present
    # (handled at page level in the caller)


def _update_graphic_for_arrow(page: ET.Element, arrow: ET.Element,
                              tail_x: float, head_x: float, arrow_y: float):
    """Update the <graphic> that the arrow supersedes."""
    arrow_id = arrow.get("id", "")
    for el in page:
        if el.tag == "graphic" and el.get("SupersededBy") == arrow_id:
            el.set("BoundingBox",
                   f"{head_x:.2f} {arrow_y:.2f} {tail_x:.2f} {arrow_y:.2f}")
            break


def _center_element_x(el: ET.Element, target_cx: float):
    """Move element so its horizontal center is at target_cx."""
    bb = _element_bbox(el)
    current_cx = (bb[0] + bb[2]) / 2.0
    dx = target_cx - current_cx
    _shift_element(el, dx, 0)


def _center_element_y(el: ET.Element, target_cy: float):
    """Move element so its vertical center is at target_cy."""
    bb = _element_bbox(el)
    current_cy = (bb[1] + bb[3]) / 2.0
    dy = target_cy - current_cy
    _shift_element(el, 0, dy)


def _move_element_to(el: ET.Element, target_cx: float, target_cy: float):
    """Move element so its center is at (target_cx, target_cy)."""
    bb = _element_bbox(el)
    cx = (bb[0] + bb[2]) / 2.0
    cy = (bb[1] + bb[3]) / 2.0
    _shift_element(el, target_cx - cx, target_cy - cy)


# ---------------------------------------------------------------------------
# Reaction parsing — extract roles from <step>
# ---------------------------------------------------------------------------

def _parse_reaction(page: ET.Element, step: ET.Element,
                    id_map: Dict[str, ET.Element]):
    """Extract reactants, products, above-arrow, below-arrow element lists."""
    def _resolve(attr):
        ids = step.get(attr, "").split()
        return [id_map[i] for i in ids if i in id_map]

    reactants = _resolve("ReactionStepReactants")
    products = _resolve("ReactionStepProducts")
    above = _resolve("ReactionStepObjectsAboveArrow")
    below = _resolve("ReactionStepObjectsBelowArrow")
    return reactants, products, above, below


# ---------------------------------------------------------------------------
# Approach 1: bbox_center — Bounding-box centroid alignment + uniform gaps
# ---------------------------------------------------------------------------

def approach_bbox_center(page, step, id_map, arrow, verbose=False):
    """
    Simple centroid-based layout:
    - All molecules vertically centered on arrow y
    - Uniform horizontal gaps between reactants, arrow, products
    - Above/below text centered over arrow
    """
    reactants, products, above, below = _parse_reaction(page, step, id_map)
    if not reactants or not products:
        return

    GAP = 15.0          # gap between elements and arrow (approach-specific)

    # Compute total width of reactant group and product group
    r_bboxes = [_element_bbox(r) for r in reactants]
    p_bboxes = [_element_bbox(p) for p in products]
    r_total_w = sum(_bbox_width(b) for b in r_bboxes) + GAP * max(0, len(reactants) - 1)
    p_total_w = sum(_bbox_width(b) for b in p_bboxes) + GAP * max(0, len(products) - 1)

    # Arrow length: at least as wide as the widest above/below object
    arrow_len = _compute_arrow_len_from_content(above, below)

    # Compute arrow y as average of all molecule centers
    all_bbs = r_bboxes + p_bboxes
    arrow_y = sum(_bbox_center(b)[1] for b in all_bbs) / len(all_bbs)

    # Layout: reactants | GAP | arrow | GAP | products
    # Find current centroid to place everything relative to it
    all_cx = sum(_bbox_center(b)[0] for b in all_bbs) / len(all_bbs)
    total_w = r_total_w + GAP + arrow_len + GAP + p_total_w
    start_x = all_cx - total_w / 2.0

    # Place reactants
    cursor_x = start_x
    for i, r in enumerate(reactants):
        bb = _element_bbox(r)
        w = _bbox_width(bb)
        _move_element_to(r, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + GAP

    # Place arrow
    tail_x = cursor_x
    head_x = cursor_x + arrow_len
    _set_arrow(arrow, tail_x, arrow_y, head_x, arrow_y)
    _update_graphic_for_arrow(page, arrow, tail_x, head_x, arrow_y)
    cursor_x = head_x + GAP

    # Place products
    for i, p in enumerate(products):
        bb = _element_bbox(p)
        w = _bbox_width(bb)
        _move_element_to(p, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + GAP

    # Center above-arrow objects
    arrow_cx = (tail_x + head_x) / 2.0
    _stack_above_below(above, below, arrow_cx, arrow_y,
                       LAYOUT_ABOVE_GAP, LAYOUT_BELOW_GAP)


# ---------------------------------------------------------------------------
# Approach 2: arrow_driven — Arrow length drives layout
# ---------------------------------------------------------------------------

def approach_arrow_driven(page, step, id_map, arrow, verbose=False):
    """
    Arrow-centric layout:
    - Arrow stays at a fixed reasonable length (70pt ≈ ~1 inch)
    - Reactants right-aligned to arrow tail with gap
    - Products left-aligned to arrow head with gap
    - Vertical centering on arrow midpoint
    """
    reactants, products, above, below = _parse_reaction(page, step, id_map)
    if not reactants or not products:
        return

    FRAG_GAP = 12.0      # gap between fragment edge and arrow tip (approach-specific)
    INTER_GAP = LAYOUT_INTER_FRAGMENT_GAP

    # Arrow length: at least as wide as widest above/below object, min 70pt
    ARROW_LEN = _compute_arrow_len_from_content(above, below, min_len=70.0)

    # Determine arrow y from the tallest molecule's vertical center
    all_bbs = [_element_bbox(r) for r in reactants] + [_element_bbox(p) for p in products]
    arrow_y = sum(_bbox_center(b)[1] for b in all_bbs) / len(all_bbs)

    # Place arrow centered on current midpoint
    all_cx = sum(_bbox_center(b)[0] for b in all_bbs) / len(all_bbs)
    tail_x = all_cx - ARROW_LEN / 2.0
    head_x = all_cx + ARROW_LEN / 2.0

    _set_arrow(arrow, tail_x, arrow_y, head_x, arrow_y)
    _update_graphic_for_arrow(page, arrow, tail_x, head_x, arrow_y)

    # Place reactants right-to-left from arrow tail
    cursor_x = tail_x - FRAG_GAP
    for r in reversed(reactants):
        bb = _element_bbox(r)
        w = _bbox_width(bb)
        _move_element_to(r, cursor_x - w / 2.0, arrow_y)
        cursor_x -= w + INTER_GAP

    # Place products left-to-right from arrow head
    cursor_x = head_x + FRAG_GAP
    for p in products:
        bb = _element_bbox(p)
        w = _bbox_width(bb)
        _move_element_to(p, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + INTER_GAP

    # Conditions
    arrow_cx = (tail_x + head_x) / 2.0
    _stack_above_below(above, below, arrow_cx, arrow_y,
                       LAYOUT_ABOVE_GAP, LAYOUT_BELOW_GAP)


# ---------------------------------------------------------------------------
# Approach 3: proportional — Gaps proportional to molecule widths
# ---------------------------------------------------------------------------

def approach_proportional(page, step, id_map, arrow, verbose=False):
    """
    Proportional spacing:
    - Arrow length = 0.6× the average molecule width
    - Gaps scale with molecule size
    - Looks balanced for both small and large molecules
    """
    reactants, products, above, below = _parse_reaction(page, step, id_map)
    if not reactants or not products:
        return

    r_bbs = [_element_bbox(r) for r in reactants]
    p_bbs = [_element_bbox(p) for p in products]

    avg_w = (sum(_bbox_width(b) for b in r_bbs + p_bbs) /
             len(r_bbs + p_bbs))

    content_len = _compute_arrow_len_from_content(above, below, min_len=45.0)
    ARROW_LEN = max(content_len, min(100.0, avg_w * 0.6))
    GAP_RATIO = 0.25  # gap = 25% of adjacent molecule width

    all_bbs = r_bbs + p_bbs
    arrow_y = sum(_bbox_center(b)[1] for b in all_bbs) / len(all_bbs)
    all_cx = sum(_bbox_center(b)[0] for b in all_bbs) / len(all_bbs)

    # Compute total width
    r_widths = [_bbox_width(b) for b in r_bbs]
    p_widths = [_bbox_width(b) for b in p_bbs]

    r_total = sum(r_widths) + sum(w * GAP_RATIO for w in r_widths[:-1]) if r_widths else 0
    p_total = sum(p_widths) + sum(w * GAP_RATIO for w in p_widths[:-1]) if p_widths else 0

    # Gap between last reactant and arrow tail
    r_arrow_gap = (r_widths[-1] * GAP_RATIO + 8.0) if r_widths else 12.0
    # Gap between arrow head and first product
    p_arrow_gap = (p_widths[0] * GAP_RATIO + 8.0) if p_widths else 12.0

    total_w = r_total + r_arrow_gap + ARROW_LEN + p_arrow_gap + p_total
    start_x = all_cx - total_w / 2.0

    # Place reactants
    cursor_x = start_x
    for i, r in enumerate(reactants):
        w = r_widths[i]
        _move_element_to(r, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + (w * GAP_RATIO if i < len(reactants) - 1 else 0)

    cursor_x += r_arrow_gap

    # Arrow
    tail_x = cursor_x
    head_x = cursor_x + ARROW_LEN
    _set_arrow(arrow, tail_x, arrow_y, head_x, arrow_y)
    _update_graphic_for_arrow(page, arrow, tail_x, head_x, arrow_y)
    cursor_x = head_x + p_arrow_gap

    # Products
    for i, p in enumerate(products):
        w = p_widths[i]
        _move_element_to(p, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + (w * GAP_RATIO if i < len(products) - 1 else 0)

    arrow_cx = (tail_x + head_x) / 2.0
    _stack_above_below(above, below, arrow_cx, arrow_y,
                       LAYOUT_ABOVE_GAP, LAYOUT_BELOW_GAP)


# ---------------------------------------------------------------------------
# Approach 4: compact — Minimal gaps for slides/posters
# ---------------------------------------------------------------------------

def approach_compact(page, step, id_map, arrow, verbose=False):
    """
    Compact layout for space-constrained output:
    - Minimal gaps (5pt)
    - Short arrow (45pt)
    - Tight vertical stacking
    """
    reactants, products, above, below = _parse_reaction(page, step, id_map)
    if not reactants or not products:
        return

    ARROW_LEN = _compute_arrow_len_from_content(above, below, min_len=45.0)
    GAP = 5.0
    ABOVE_GAP = 5.0  # approach-specific (tighter than standard)

    r_bbs = [_element_bbox(r) for r in reactants]
    p_bbs = [_element_bbox(p) for p in products]
    all_bbs = r_bbs + p_bbs

    arrow_y = sum(_bbox_center(b)[1] for b in all_bbs) / len(all_bbs)
    all_cx = sum(_bbox_center(b)[0] for b in all_bbs) / len(all_bbs)

    r_total = sum(_bbox_width(b) for b in r_bbs) + GAP * max(0, len(r_bbs) - 1)
    p_total = sum(_bbox_width(b) for b in p_bbs) + GAP * max(0, len(p_bbs) - 1)

    total_w = r_total + GAP + ARROW_LEN + GAP + p_total
    start_x = all_cx - total_w / 2.0

    cursor_x = start_x
    for i, r in enumerate(reactants):
        w = _bbox_width(r_bbs[i])
        _move_element_to(r, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + GAP

    tail_x = cursor_x
    head_x = cursor_x + ARROW_LEN
    _set_arrow(arrow, tail_x, arrow_y, head_x, arrow_y)
    _update_graphic_for_arrow(page, arrow, tail_x, head_x, arrow_y)
    cursor_x = head_x + GAP

    for i, p in enumerate(products):
        w = _bbox_width(p_bbs[i])
        _move_element_to(p, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + GAP

    arrow_cx = (tail_x + head_x) / 2.0
    _stack_above_below(above, below, arrow_cx, arrow_y,
                       ABOVE_GAP, LAYOUT_BELOW_GAP)


# ---------------------------------------------------------------------------
# Approach 5: golden_ratio — Arrow + gaps use golden ratio proportions
# ---------------------------------------------------------------------------

def approach_golden_ratio(page, step, id_map, arrow, verbose=False):
    """
    Golden ratio aesthetics:
    - Arrow length = φ × average molecule width
    - Gaps = average molecule width / φ
    - Pleasing visual proportions
    """
    PHI = 1.618

    reactants, products, above, below = _parse_reaction(page, step, id_map)
    if not reactants or not products:
        return

    r_bbs = [_element_bbox(r) for r in reactants]
    p_bbs = [_element_bbox(p) for p in products]
    all_bbs = r_bbs + p_bbs

    avg_w = sum(_bbox_width(b) for b in all_bbs) / len(all_bbs)
    content_len = _compute_arrow_len_from_content(above, below, min_len=50.0)
    ARROW_LEN = max(content_len, min(110.0, avg_w * PHI))
    GAP = max(LAYOUT_ABOVE_GAP, avg_w / PHI)

    arrow_y = sum(_bbox_center(b)[1] for b in all_bbs) / len(all_bbs)
    all_cx = sum(_bbox_center(b)[0] for b in all_bbs) / len(all_bbs)

    r_total = sum(_bbox_width(b) for b in r_bbs) + GAP * max(0, len(r_bbs) - 1)
    p_total = sum(_bbox_width(b) for b in p_bbs) + GAP * max(0, len(p_bbs) - 1)

    total_w = r_total + GAP + ARROW_LEN + GAP + p_total
    start_x = all_cx - total_w / 2.0

    cursor_x = start_x
    for i, r in enumerate(reactants):
        w = _bbox_width(r_bbs[i])
        _move_element_to(r, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + GAP

    tail_x = cursor_x
    head_x = cursor_x + ARROW_LEN
    _set_arrow(arrow, tail_x, arrow_y, head_x, arrow_y)
    _update_graphic_for_arrow(page, arrow, tail_x, head_x, arrow_y)
    cursor_x = head_x + GAP

    for i, p in enumerate(products):
        w = _bbox_width(p_bbs[i])
        _move_element_to(p, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + GAP

    arrow_cx = (tail_x + head_x) / 2.0
    _stack_above_below(above, below, arrow_cx, arrow_y,
                       LAYOUT_ABOVE_GAP, LAYOUT_BELOW_GAP)


# ---------------------------------------------------------------------------
# Approach 6: chemdraw_mimic — Closest emulation of ChemDraw heuristics
# ---------------------------------------------------------------------------

def approach_chemdraw_mimic(page, step, id_map, arrow, verbose=False):
    """
    Emulates ChemDraw's Clean Up Reaction behaviour:
    - Arrow length ≈ 1.5× bond length (BondLength from doc)
    - Molecules placed so nearest atom is ~1 bond length from arrow tip
    - Above-arrow objects stacked: structures first, then text
    - Below-arrow objects similarly stacked
    - Everything vertically centered on a common y-line
    - Separate above-arrow fragments from above-arrow text labels
    """
    reactants, products, above, below = _parse_reaction(page, step, id_map)
    if not reactants or not products:
        return

    # Read BondLength from document
    root = page
    while root.tag != "CDXML":
        # Walk up — but ET doesn't support parent. Use the global root instead.
        root = page
        break
    # ACS Document 1996 bond length
    bond_len = ACS_BOND_LENGTH

    content_len = _compute_arrow_len_from_content(above, below, min_len=bond_len * 5.0)
    ARROW_LEN = content_len
    FRAG_GAP = bond_len * LAYOUT_FRAG_GAP_BONDS
    INTER_GAP = bond_len * LAYOUT_INTER_GAP_BONDS

    r_bbs = [_element_bbox(r) for r in reactants]
    p_bbs = [_element_bbox(p) for p in products]
    all_bbs = r_bbs + p_bbs

    # Arrow y = vertical center of reactants (ChemDraw uses reactant center)
    arrow_y = sum(_bbox_center(b)[1] for b in r_bbs) / len(r_bbs)

    # Position arrow. Use mean x of all molecules as center.
    all_cx = sum(_bbox_center(b)[0] for b in all_bbs) / len(all_bbs)

    # Compute widths
    r_widths = [_bbox_width(b) for b in r_bbs]
    p_widths = [_bbox_width(b) for b in p_bbs]

    r_block_w = sum(r_widths) + INTER_GAP * max(0, len(r_widths) - 1)
    p_block_w = sum(p_widths) + INTER_GAP * max(0, len(p_widths) - 1)

    total_w = r_block_w + FRAG_GAP + ARROW_LEN + FRAG_GAP + p_block_w
    start_x = all_cx - total_w / 2.0

    # Place reactants
    cursor_x = start_x
    for i, r in enumerate(reactants):
        w = r_widths[i]
        _move_element_to(r, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + INTER_GAP
    cursor_x = cursor_x - INTER_GAP + FRAG_GAP  # replace last inter-gap with frag-gap

    # Arrow
    tail_x = cursor_x
    head_x = cursor_x + ARROW_LEN
    _set_arrow(arrow, tail_x, arrow_y, head_x, arrow_y)
    _update_graphic_for_arrow(page, arrow, tail_x, head_x, arrow_y)
    cursor_x = head_x + FRAG_GAP

    # Products
    for i, p in enumerate(products):
        w = p_widths[i]
        _move_element_to(p, cursor_x + w / 2.0, arrow_y)
        cursor_x += w + INTER_GAP

    # Conditions — use shared stacking (text closest to arrow, frags above/below)
    arrow_cx = (tail_x + head_x) / 2.0
    _stack_above_below(above, below, arrow_cx, arrow_y,
                       LAYOUT_ABOVE_GAP, LAYOUT_BELOW_GAP)


# ---------------------------------------------------------------------------
# Shared: stack above/below arrow
# ---------------------------------------------------------------------------

def _compute_arrow_len_from_content(above: List[ET.Element],
                                    below: List[ET.Element],
                                    min_len: float = 50.0) -> float:
    """Compute arrow length so it's at least as wide as the widest
    above- or below-arrow object.

    above/below are the raw element lists from the step metadata.
    Text from above is redirected below, so we check both groups.
    """
    above_frags = [e for e in above if e.tag != "t"]
    above_texts = [e for e in above if e.tag == "t"]
    below_texts = [e for e in below if e.tag == "t"]
    below_frags = [e for e in below if e.tag != "t"]

    all_above = above_frags
    all_below = above_texts + below_texts + below_frags

    max_w = 0.0
    for el in all_above + all_below:
        if el.tag == "t":
            # Use content-based width estimate instead of stored BoundingBox.
            # Stored BoundingBox may be stale (e.g. from ELN exports with
            # non-ACS scaling where bond normalization resized fragments but
            # left page-level text BoundingBoxes untouched).
            w = _estimate_text_width(el)
        else:
            bb = _element_bbox(el)
            w = _bbox_width(bb)
        if w > max_w:
            max_w = w

    # Arrow should be wider than the widest object, with some padding
    return max(min_len, max_w + 10.0)


def _stack_above_below(above: List[ET.Element], below: List[ET.Element],
                       arrow_cx: float, arrow_y: float,
                       above_gap: float, below_gap: float):
    """Place above/below-arrow objects with text always below the arrow.

    Text (<t>) elements — even if listed as "above arrow" in the step
    metadata — are always placed below the arrow line.  Only non-text
    elements (fragments / structures) go above.

    For above-arrow fragments, uses atom-only bounding boxes (no text
    labels) since ChemDraw's XML label BoundingBox values are unreliable.

    The above_gap parameter is the *base* gap (typically 8pt).  If the
    bottommost atom of a fragment is N or P with only 2 explicit bonds
    (i.e. it will have a vertically-stacked H label like NH or PH),
    the gap is increased to 16pt to avoid the hanging label clashing
    with the arrow.

    below_gap is the distance from the arrow y-line to the top edge
    of the highest below-arrow object (typically 4pt).
    """
    # Collect texts from both lists — they all go below
    above_texts = [e for e in above if e.tag == "t"]
    above_frags = [e for e in above if e.tag != "t"]
    below_texts = [e for e in below if e.tag == "t"]
    below_frags = [e for e in below if e.tag != "t"]

    # --- Above arrow: only non-text elements (fragments) ---
    # Use atom-only bbox; adjust gap for hanging labels (NH, PH)
    for el in above_frags:
        bb = _element_bbox(el)
        h = _bbox_height(bb)
        cx = (bb[0] + bb[2]) / 2.0
        cy = (bb[1] + bb[3]) / 2.0

        # Determine gap for this fragment
        if el.tag == "fragment" and fragment_bottom_has_hanging_label(el):
            gap = LAYOUT_HANGING_LABEL_GAP
        else:
            gap = above_gap

        # Place so bottom edge of atom-only bbox is at arrow_y - gap
        target_bottom = arrow_y - gap
        target_cy = target_bottom - h / 2.0
        _shift_element(el, arrow_cx - cx, target_cy - cy)

    # --- Below arrow: all text (from above + below lists), then fragments ---
    # Text elements use consistent baseline-to-baseline spacing (like
    # ChemDraw's multi-line text rendering).  This avoids dependence on
    # stale BoundingBox values from upstream processing.
    all_below_text = above_texts + below_texts
    BASELINE_OFFSET = 10.0   # baseline below top-of-text-line (cap height)
    TEXT_LINE_SPACING = 13.0  # baseline-to-baseline (Arial 10pt with leading)

    prev_baseline = None
    y_cursor = arrow_y + below_gap
    for el in all_below_text:
        if prev_baseline is None:
            baseline_y = y_cursor + BASELINE_OFFSET
        else:
            baseline_y = prev_baseline + TEXT_LINE_SPACING
        el.set("p", f"{arrow_cx:.2f} {baseline_y:.2f}")
        el.set("CaptionJustification", "Center")
        el.set("Justification", "Center")
        recompute_text_bbox(el)
        prev_baseline = baseline_y
        # Update y_cursor to bottom of this text element for any
        # subsequent non-text elements
        bb = _element_bbox(el)
        y_cursor = bb[3]

    # Non-text elements (fragments) below arrow, after all text
    for el in below_frags:
        bb = _element_bbox(el)
        h = _bbox_height(bb)
        _move_element_to(el, arrow_cx, y_cursor + LAYOUT_BELOW_FRAG_PAD + h / 2.0)
        y_cursor += LAYOUT_BELOW_FRAG_PAD + h


# ---------------------------------------------------------------------------
# Update document-level BoundingBox
# ---------------------------------------------------------------------------

def _update_doc_bbox(root: ET.Element):
    """Recompute the document-level BoundingBox from page contents."""
    page = root.find("page")
    if page is None:
        return
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for el in page:
        if el.tag in ("fragment", "t", "arrow", "graphic"):
            bb = _element_bbox(el)
            if bb != (0, 0, 0, 0):
                min_x = min(min_x, bb[0])
                min_y = min(min_y, bb[1])
                max_x = max(max_x, bb[2])
                max_y = max(max_y, bb[3])
    if min_x < float("inf"):
        root.set("BoundingBox",
                 f"{min_x:.2f} {min_y:.2f} {max_x:.2f} {max_y:.2f}")


# ---------------------------------------------------------------------------
# Approach registry
# ---------------------------------------------------------------------------

APPROACHES = {
    "bbox_center": approach_bbox_center,
    "arrow_driven": approach_arrow_driven,
    "proportional": approach_proportional,
    "compact": approach_compact,
    "golden_ratio": approach_golden_ratio,
    "chemdraw_mimic": approach_chemdraw_mimic,
}

APPROACH_DESCRIPTIONS = {
    "bbox_center":    "Bounding-box centroid alignment + uniform gaps",
    "arrow_driven":   "Arrow length drives layout; molecules placed relative to ends",
    "proportional":   "Gap sizes proportional to molecule widths",
    "compact":        "Minimal gaps; tight layout for slides/posters",
    "golden_ratio":   "Arrow + gaps use golden ratio proportions",
    "chemdraw_mimic": "Closest emulation of ChemDraw's cleanup heuristics",
}


def run_cleanup(input_path: str, output_path: str, approach: str = "chemdraw_mimic",
                verbose: bool = False) -> dict:
    """Run one cleanup approach on a CDXML file.

    Returns dict with keys: output, approach, num_reactants, num_products.
    """
    tree = parse_cdxml(input_path)
    root = tree.getroot()
    page = _get_page(root)
    if page is None:
        raise ValueError("No <page> found in CDXML")

    id_map = _build_id_map(page)
    step = _get_step(page)
    if step is None:
        raise ValueError("No <scheme>/<step> found — not a reaction CDXML")

    arrow = _get_arrow(page, step, id_map)
    if arrow is None:
        raise ValueError("No arrow element found in reaction")

    func = APPROACHES.get(approach)
    if func is None:
        raise ValueError(f"Unknown approach: {approach}. "
                         f"Choose from: {', '.join(APPROACHES)}")

    reactants, products, _, _ = _parse_reaction(page, step, id_map)
    num_reactants = len(reactants)
    num_products = len(products)

    func(page, step, id_map, arrow, verbose=verbose)
    _update_doc_bbox(root)
    write_cdxml(tree, output_path)
    return {
        "output": output_path,
        "approach": approach,
        "num_reactants": num_reactants,
        "num_products": num_products,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Clean up a CDXML reaction scheme layout (pure Python).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {k:18s} {v}" for k, v in APPROACH_DESCRIPTIONS.items()),
    )
    parser.add_argument("input", help="Input CDXML file with a reaction scheme")
    parser.add_argument("-o", "--output", help="Output CDXML path (default: input-cleaned.cdxml)")
    parser.add_argument("--approach", choices=list(APPROACHES.keys()),
                        default="chemdraw_mimic",
                        help="Layout approach (default: chemdraw_mimic)")
    parser.add_argument("--all", action="store_true",
                        help="Run all 6 approaches, producing one output each")
    parser.add_argument("--render", action="store_true",
                        help="Render each output to PNG via cdxml_to_image.py")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true",
                        help="Output result as JSON to stdout")

    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    base, ext = os.path.splitext(args.input)

    # When --json, redirect status prints to stderr
    _print = print
    if args.json:
        def _print(*a, **kw):
            kw.setdefault("file", sys.stderr)
            print(*a, **kw)

    if args.all:
        all_results = []
        for name in APPROACHES:
            out_path = f"{base}-cleanup-{name}{ext}"
            _print(f"[{name}] -> {out_path}")
            try:
                info = run_cleanup(args.input, out_path, approach=name, verbose=args.verbose)
                _print(f"  OK")
                all_results.append(info)
                if args.render:
                    _render(out_path)
            except Exception as e:
                _print(f"  FAILED: {e}", file=sys.stderr)
        if args.json:
            json_results = []
            for info in all_results:
                json_results.append({
                    "input": os.path.abspath(args.input),
                    "output": os.path.abspath(info["output"]),
                    "approach": info["approach"],
                    "num_reactants": info["num_reactants"],
                    "num_products": info["num_products"],
                })
            print(json.dumps(json_results, indent=2))
    else:
        out_path = args.output or f"{base}-cleaned{ext}"
        try:
            info = run_cleanup(args.input, out_path, approach=args.approach, verbose=args.verbose)
            if args.json:
                result = {
                    "input": os.path.abspath(args.input),
                    "output": os.path.abspath(out_path),
                    "approach": info["approach"],
                    "num_reactants": info["num_reactants"],
                    "num_products": info["num_products"],
                }
                print(json.dumps(result, indent=2))
            else:
                _print(f"Output: {out_path}")
            if args.render:
                _render(out_path)
        except Exception as e:
            _print(f"Error: {e}", file=sys.stderr)
            return 1

    return 0


def _render(cdxml_path: str):
    """Render a CDXML to PNG using cdxml_to_image.py."""
    try:
        from ..chemdraw.cdxml_to_image import cdxml_to_image
        png_path = cdxml_to_image(cdxml_path)
        print(f"  Rendered: {png_path}")
    except Exception as e:
        print(f"  Render failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
