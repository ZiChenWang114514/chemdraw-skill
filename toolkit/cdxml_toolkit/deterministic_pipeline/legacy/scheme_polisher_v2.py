#!/usr/bin/env python3
"""
scheme_polisher_v2.py — Experimental COM-free scheme polishing pipeline.

Takes a CDX/CDXML reaction scheme and produces a presentation-ready CDXML
without any ChemDraw COM dependency (except CDX→CDXML conversion if needed,
which falls through to whatever backend cdx_converter.py has available).

Pipeline:
  1. Convert CDX → CDXML if needed (via cdx_converter.py)
  2. Normalize bond lengths per-fragment to ACS Document 1996 (14.40 pt)
  3. Apply ACS Document 1996 document-level settings
  4. Normalize caption/label fonts to Arial 10pt Bold
  5. Run scheme_polisher logic (reagent classification, structure↔text swaps,
     orientation alignment, subscript formatting, deduplication)
  6. Merge conditions into single centered text block (default on)
  7. Compact above/below-arrow objects toward arrow
  8. Run reaction_cleanup for final spatial layout

Defaults differ from scheme_polisher.py:
  - --merge-conditions is ON by default (use --no-merge-conditions to disable)
  - ChemDraw COM cleanup is NEVER used

Usage:
    python scheme_polisher_v2.py input.cdx [-o output.cdxml] [-v]
    python scheme_polisher_v2.py input.cdxml [-o output.cdxml] [-v]
    python scheme_polisher_v2.py input.cdx --no-merge-conditions
    python scheme_polisher_v2.py input.cdxml --approach compact -v
"""

import argparse
import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from ...constants import (
    ACS_BOND_LENGTH as TARGET_BOND_LENGTH,
    ACS_STYLE as ACS_SETTINGS,
    CDXML_MINIMAL_HEADER,
    CDXML_FOOTER,
)


# ---------------------------------------------------------------------------
# Bond length measurement and per-fragment normalization
# ---------------------------------------------------------------------------

def _measure_bond_lengths(frag: ET.Element) -> List[float]:
    """Measure all bond lengths in a fragment from node coordinates.

    Uses direct-child <n> and <b> elements only (not inner fragments
    of NodeType="Fragment" abbreviation groups).
    """
    # Build node id → (x, y) map from direct child <n> nodes
    node_map: Dict[str, Tuple[float, float]] = {}
    for n in frag.findall("n"):
        nid = n.get("id", "")
        p = n.get("p", "")
        if nid and p:
            parts = p.split()
            if len(parts) >= 2:
                node_map[nid] = (float(parts[0]), float(parts[1]))

    lengths = []
    for b in frag.findall("b"):
        b_id = b.get("B", "")
        e_id = b.get("E", "")
        if b_id in node_map and e_id in node_map:
            bx, by = node_map[b_id]
            ex, ey = node_map[e_id]
            d = math.sqrt((bx - ex) ** 2 + (by - ey) ** 2)
            if d > 0.1:
                lengths.append(d)

    return lengths


def _median(values: List[float]) -> float:
    """Compute median of a list of floats."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def _scale_fragment(frag: ET.Element, factor: float, cx: float, cy: float):
    """Scale all coordinates in a fragment around (cx, cy) by factor.

    Scales ALL descendant nodes and text elements (including those
    inside inner NodeType="Fragment" sub-structures), since all
    coordinates live in the same global space.
    """
    def scale_pt(x: float, y: float) -> Tuple[float, float]:
        return cx + (x - cx) * factor, cy + (y - cy) * factor

    def scale_bb(bb_str: str) -> str:
        vals = [float(v) for v in bb_str.split()]
        if len(vals) >= 4:
            x1, y1 = scale_pt(vals[0], vals[1])
            x2, y2 = scale_pt(vals[2], vals[3])
            return f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}"
        return bb_str

    # Scale all node positions (iter = all descendants)
    for n in frag.iter("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                nx, ny = scale_pt(float(parts[0]), float(parts[1]))
                n.set("p", f"{nx:.2f} {ny:.2f}")

    # Scale text label positions and bounding boxes
    for t in frag.iter("t"):
        p = t.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                nx, ny = scale_pt(float(parts[0]), float(parts[1]))
                t.set("p", f"{nx:.2f} {ny:.2f}")
        bb = t.get("BoundingBox")
        if bb:
            t.set("BoundingBox", scale_bb(bb))

    # Scale fragment-level BoundingBox
    bb = frag.get("BoundingBox")
    if bb:
        frag.set("BoundingBox", scale_bb(bb))

    # Scale inner fragment BoundingBoxes (abbreviation groups)
    for inner in frag.iter("fragment"):
        if inner is not frag:
            bb = inner.get("BoundingBox")
            if bb:
                inner.set("BoundingBox", scale_bb(bb))


def _fragment_centroid(frag: ET.Element) -> Tuple[float, float]:
    """Compute centroid from direct-child node positions."""
    xs, ys = [], []
    for n in frag.findall("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                xs.append(float(parts[0]))
                ys.append(float(parts[1]))
    if not xs:
        return 0.0, 0.0
    return sum(xs) / len(xs), sum(ys) / len(ys)


def normalize_bond_lengths(root: ET.Element, target: float = TARGET_BOND_LENGTH,
                           verbose: bool = False) -> int:
    """Normalize bond lengths in every fragment to the target length.

    Each fragment is scaled independently around its own centroid,
    so fragments at different scales (common in ELN exports) all
    converge to the same bond length.

    Returns the number of fragments scaled.
    """
    page = root.find("page")
    if page is None:
        return 0

    scaled_count = 0
    for frag in page.findall("fragment"):
        lengths = _measure_bond_lengths(frag)
        if not lengths:
            continue

        med = _median(lengths)
        if med < 1.0:
            continue

        factor = target / med
        if abs(factor - 1.0) < 0.02:
            if verbose:
                fid = frag.get("id", "?")
                print(f"  Fragment {fid}: median {med:.2f} pt, "
                      f"already at target ({factor:.3f}x)", file=sys.stderr)
            continue

        cx, cy = _fragment_centroid(frag)
        _scale_fragment(frag, factor, cx, cy)
        scaled_count += 1

        if verbose:
            fid = frag.get("id", "?")
            print(f"  Fragment {fid}: median {med:.2f} pt → "
                  f"scaled {factor:.3f}x around ({cx:.1f}, {cy:.1f})",
                  file=sys.stderr)

    return scaled_count


# ---------------------------------------------------------------------------
# ACS document settings + font normalization
# ---------------------------------------------------------------------------

def apply_acs_settings(root: ET.Element):
    """Apply ACS Document 1996 settings to the root CDXML element."""
    for attr, val in ACS_SETTINGS.items():
        root.set(attr, val)


def normalize_fonts(root: ET.Element, verbose: bool = False) -> int:
    """Set all caption text to Arial 10pt Bold (face=96).

    Only touches <t> elements that are direct children of <page>
    (i.e. captions/conditions, not atom labels inside fragments).
    Returns number of text elements modified.
    """
    page = root.find("page")
    if page is None:
        return 0

    count = 0
    for t_el in page.findall("t"):
        modified = False
        for s in t_el.findall("s"):
            changed = False
            if s.get("font") != "3":
                s.set("font", "3")
                changed = True
            if s.get("size") != "10":
                s.set("size", "10")
                changed = True
            # Don't override subscript (32) or italic (2) faces —
            # only set formula (96) if it's something else like bold (1)
            face = s.get("face", "")
            if face not in ("2", "32", "96"):
                s.set("face", "96")
                changed = True
            if changed:
                modified = True
        if modified:
            count += 1

    if verbose and count:
        print(f"  Normalized fonts on {count} text element(s)", file=sys.stderr)
    return count


def fix_narrow_text(root: ET.Element, verbose: bool = False) -> int:
    """Fix degenerate narrow text labels from Findmolecule ELN exports.

    ELN exports sometimes create text with per-character LineStarts (each
    character on its own line in a very narrow column, e.g. "Sodium Bicarbonate"
    rendered as a 1-character-wide column 18 lines tall).  This causes
    BoundingBox to extend very far vertically, breaking layout and
    run-arrow placement.

    Fix: remove LineStarts attribute and recalculate BoundingBox to
    approximate single-line width so downstream layout works correctly.

    Returns number of text elements fixed.
    """
    page = root.find("page")
    if page is None:
        return 0

    count = 0
    for t_el in page.findall("t"):
        ls = t_el.get("LineStarts")
        if not ls:
            continue

        # Get text content
        text = "".join((s.text or "") for s in t_el.findall("s"))
        if not text:
            continue

        line_starts = ls.strip().split()
        n_lines = len(line_starts)
        n_words = len(text.split())

        # Heuristic: if LineStarts has more entries than 2× words,
        # it's likely per-character wrapping from a narrow column
        if n_lines <= max(n_words * 2, 3):
            continue

        # Remove LineStarts to make it single-line
        del t_el.attrib["LineStarts"]

        # Recalculate BoundingBox based on text length
        # Arial 10pt Bold: ~6.0 pt per character average
        p = t_el.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                px, py = float(parts[0]), float(parts[1])
                est_width = len(text) * 6.0
                # BoundingBox: left top right bottom
                t_el.set("BoundingBox",
                          f"{px:.2f} {py - 11:.2f} "
                          f"{px + est_width:.2f} {py + 3:.2f}")

        count += 1
        if verbose:
            print(f"  Fixed narrow text: '{text}' "
                  f"({n_lines} LineStarts → single line)",
                  file=sys.stderr)

    return count


def resolve_orphan_reagent_text(root: ET.Element, verbose: bool = False) -> int:
    """Resolve orphan text labels to their reagent DB display names.

    ELN exports sometimes place reagent names as free-floating text
    elements that are NOT referenced in the ``<step>`` metadata (e.g.
    "Sodium Bicarbonate" placed next to the substrate).  The polisher
    only processes step-referenced elements, so these labels are never
    reformatted.

    This function:
    1. Finds text elements on the page that are NOT referenced in any step.
    2. Looks up each text in the reagent database.
    3. If found, renames the text to the DB display name (e.g.
       "Sodium Bicarbonate" → "NaHCO3").
    4. Adds the text to the nearest step's below-arrow references so
       the polisher will process it (reformatting, conditions merging).

    Returns number of text elements resolved.
    """
    from ...resolve.reagent_db import get_reagent_db

    page = root.find("page")
    if page is None:
        return 0

    db = get_reagent_db()

    # Collect all IDs referenced by any step
    step_ids: set = set()
    for scheme in page.findall("scheme"):
        for step in scheme.findall("step"):
            for attr in ("ReactionStepReactants", "ReactionStepProducts",
                         "ReactionStepArrows",
                         "ReactionStepObjectsAboveArrow",
                         "ReactionStepObjectsBelowArrow"):
                val = step.get(attr, "")
                for tok in val.split():
                    try:
                        step_ids.add(int(tok))
                    except ValueError:
                        pass

    # Find the first step (for adding below-arrow references)
    first_step = None
    for scheme in page.findall("scheme"):
        steps = scheme.findall("step")
        if steps:
            first_step = steps[0]
            break

    count = 0
    for t_el in page.findall("t"):
        tid_str = t_el.get("id")
        if tid_str is None:
            continue
        try:
            tid = int(tid_str)
        except ValueError:
            continue

        if tid in step_ids:
            continue  # Already referenced in a step — polisher handles it

        # Get text content
        text = "".join((s.text or "") for s in t_el.findall("s"))
        text = text.strip()
        if not text or len(text) < 2:
            continue

        # Try to resolve via reagent DB
        display = db.display_for_name(text.lower())
        if display is None:
            continue
        if display.lower() == text.lower():
            # Already the display form — still add to step but don't rename
            pass
        else:
            # Rename the text to the display form
            for s_el in t_el.findall("s"):
                s_el.text = display
            # Recalculate bounding box
            p = t_el.get("p")
            if p:
                parts = p.split()
                if len(parts) >= 2:
                    px, py = float(parts[0]), float(parts[1])
                    est_width = len(display) * 5.8
                    t_el.set("BoundingBox",
                             f"{px:.2f} {py - 9:.2f} "
                             f"{px + est_width:.2f} {py + 3:.2f}")
            if verbose:
                print(f"  Renamed orphan text: '{text}' → '{display}'",
                      file=sys.stderr)

        # Add to step below-arrow references
        if first_step is not None:
            below_str = first_step.get(
                "ReactionStepObjectsBelowArrow", "")
            if str(tid) not in below_str.split():
                first_step.set(
                    "ReactionStepObjectsBelowArrow",
                    f"{below_str} {tid}".strip())
                if verbose:
                    print(f"  Added '{display}' (id={tid}) to step "
                          f"below-arrow references",
                          file=sys.stderr)

        count += 1

    return count


# ---------------------------------------------------------------------------
# Alignment imports (from alignment.py)
# ---------------------------------------------------------------------------
# Geometry primitives + high-level alignment orchestrators live in
# alignment.py.  We import what's needed here and keep backward-
# compatible private aliases for internal callers.

from ...layout.alignment import (
    fragment_centroid as _fragment_centroid,
    get_visible_carbon_positions as _get_visible_carbon_positions,
    match_and_compute_rotation as _match_and_compute_rotation,
    rotate_fragment_in_place as _rotate_all_coords,
    rdkit_align_to_product,
    kabsch_align_to_product,
    align_product_to_reference,
    rxnmapper_align_to_product,
)


def _shift_element_coords(elem: ET.Element, dx: float, dy: float) -> None:
    """Shift all <n> and <t> coordinates within an element tree by (dx, dy).

    Updates node positions, text positions, and BoundingBox attributes
    on all descendants.
    """
    for n in elem.iter("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                n.set("p", f"{float(parts[0]) + dx:.2f} "
                           f"{float(parts[1]) + dy:.2f}")
    for t in elem.iter("t"):
        p = t.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                t.set("p", f"{float(parts[0]) + dx:.2f} "
                           f"{float(parts[1]) + dy:.2f}")
        bb = t.get("BoundingBox")
        if bb:
            vals = [float(v) for v in bb.split()]
            if len(vals) >= 4:
                t.set("BoundingBox",
                      f"{vals[0]+dx:.2f} {vals[1]+dy:.2f} "
                      f"{vals[2]+dx:.2f} {vals[3]+dy:.2f}")
    bb = elem.get("BoundingBox")
    if bb:
        vals = [float(v) for v in bb.split()]
        if len(vals) >= 4:
            elem.set("BoundingBox",
                      f"{vals[0]+dx:.2f} {vals[1]+dy:.2f} "
                      f"{vals[2]+dx:.2f} {vals[3]+dy:.2f}")


# Note: RDKit MCS alignment functions have been moved to alignment.py.
# rdkit_align_to_product and kabsch_align_to_product are imported above.


# ---------------------------------------------------------------------------
# ChemScript per-fragment structure cleanup
# ---------------------------------------------------------------------------

# Dummy element used to replace abbreviation nodes during cleanup.
# Iodine (53) is a safe choice: ChemScript treats it as a normal atom
# and won't add hydrogens.  In the rare case the molecule already has
# iodine, dummies are matched back by position proximity.
_ABBREV_DUMMY_ELEMENT = "53"


def _cleanup_fragments_chemscript(root: ET.Element,
                                   verbose: bool = False) -> int:
    """Clean up each fragment's geometry via ChemScript CleanupStructure.

    Extracts each <fragment> from the page into a standalone CDXML,
    runs ChemScript cleanup on it, then replaces the fragment in-place
    while preserving the original centroid position and element ID.

    **Abbreviation preservation:** Before cleanup, any abbreviation nodes
    (``NodeType="Fragment"``) are temporarily replaced with dummy atoms
    (Iodine) so ChemScript doesn't expand them.  After cleanup, the
    saved abbreviation nodes are restored at the cleaned positions.

    **Orientation preservation:** Kabsch alignment on visible carbon
    atom positions corrects arbitrary rotations introduced by cleanup.

    Returns the number of fragments cleaned.
    """
    page = root.find("page")
    if page is None:
        return 0

    # Lazy-init ChemScript bridge
    cs_bridge = None

    def _ensure_cs():
        nonlocal cs_bridge
        if cs_bridge is None:
            from ...chemdraw.chemscript_bridge import ChemScriptBridge
            cs_bridge = ChemScriptBridge()
        return cs_bridge

    cleaned_count = 0

    for frag in list(page.findall("fragment")):  # list() — we modify page
        frag_id = frag.get("id", "?")

        # Measure current centroid
        old_cx, old_cy = _fragment_centroid(frag)
        if old_cx == 0.0 and old_cy == 0.0:
            if verbose:
                print(f"  Fragment {frag_id}: no atom coords, skipping",
                      file=sys.stderr)
            continue

        # Save visible carbon positions for Kabsch orientation matching
        old_carbons = _get_visible_carbon_positions(frag)

        # Skip fragments with too few visible carbons — these are likely
        # inorganic salts (Cs2CO3=1C, NaH=0C) or very small molecules
        # that don't benefit from geometry cleanup.  ChemScript can also
        # alter their connectivity (e.g. strip counterions from salts).
        if len(old_carbons) < 3:
            if verbose:
                print(f"  Fragment {frag_id}: only {len(old_carbons)} "
                      f"visible carbon(s), skipping cleanup",
                      file=sys.stderr)
            continue

        # Preserve objecttag children (FM MOLECULE TYPE, etc.)
        saved_objecttags = []
        for ot in frag.findall("objecttag"):
            saved_objecttags.append(copy.deepcopy(ot))

        # --- Abbreviation preservation: swap with dummy atoms ---
        # Work on a deep copy so the original fragment is untouched
        # in case cleanup fails.
        work_frag = copy.deepcopy(frag)
        saved_abbrevs = []  # list of deep-copied abbreviation <n> elements

        for n in work_frag.findall("n"):
            if n.get("NodeType") != "Fragment":
                continue
            # Save deep copy of the full abbreviation node
            saved_abbrevs.append(copy.deepcopy(n))
            # Strip to dummy atom: remove inner fragment + label
            for child in list(n):
                n.remove(child)
            for attr in ("NodeType", "LabelDisplay", "NeedsClean",
                         "AS", "Warning"):
                if attr in n.attrib:
                    del n.attrib[attr]
            n.set("Element", _ABBREV_DUMMY_ELEMENT)
            n.set("NumHydrogens", "0")

        if saved_abbrevs and verbose:
            labels = []
            for sa in saved_abbrevs:
                t = sa.find("t")
                if t is not None:
                    labels.append("".join(
                        (s.text or "") for s in t.findall("s")))
            print(f"  Fragment {frag_id}: {len(saved_abbrevs)} abbreviation(s) "
                  f"swapped with dummies ({', '.join(labels)})",
                  file=sys.stderr)

        # Wrap the modified copy in minimal CDXML
        frag_xml = ET.tostring(work_frag, encoding="unicode")
        wrapper_cdxml = (
            f'{CDXML_MINIMAL_HEADER}\n'
            '<page id="1">\n'
            f'{frag_xml}\n'
            '</page>\n'
            f'{CDXML_FOOTER}'
        )

        tmp_in = tmp_out = None
        try:
            _ensure_cs()

            with tempfile.NamedTemporaryFile(
                suffix=".cdxml", mode="w", delete=False, encoding="utf-8"
            ) as f:
                f.write(wrapper_cdxml)
                tmp_in = f.name

            tmp_out = tmp_in.replace(".cdxml", "-clean.cdxml")
            cs_bridge.cleanup(tmp_in, output=tmp_out)

            # Parse cleaned output
            clean_tree = ET.parse(tmp_out)
            clean_root = clean_tree.getroot()
            clean_page = clean_root.find("page")
            if clean_page is None:
                continue
            clean_frag = clean_page.find("fragment")
            if clean_frag is None:
                continue

            # --- Preserve original orientation via Kabsch alignment ---
            # ChemScript cleanup can arbitrarily rotate the structure.
            # Use visible carbon positions (same count before/after since
            # abbreviations were replaced with dummies, not carbons).
            new_carbons = _get_visible_carbon_positions(clean_frag)

            if (len(old_carbons) >= 3
                    and len(new_carbons) == len(old_carbons)):
                cos_a, sin_a, angle_deg = _match_and_compute_rotation(
                    new_carbons, old_carbons)
                if abs(angle_deg) >= 1.0:
                    rot_cx, rot_cy = _fragment_centroid(clean_frag)
                    _rotate_all_coords(
                        clean_frag, cos_a, sin_a, rot_cx, rot_cy)
                    if verbose:
                        print(f"  Fragment {frag_id}: re-aligned "
                              f"{angle_deg:.1f}\u00b0 to original "
                              f"orientation", file=sys.stderr)
            elif verbose and old_carbons:
                print(f"  Fragment {frag_id}: Kabsch skipped "
                      f"(old={len(old_carbons)}, "
                      f"new={len(new_carbons)} visible carbons)",
                      file=sys.stderr)

            # Compute new centroid and shift to old position
            new_cx, new_cy = _fragment_centroid(clean_frag)
            if new_cx == 0.0 and new_cy == 0.0:
                continue

            dx = old_cx - new_cx
            dy = old_cy - new_cy

            # Shift all coordinates in the cleaned fragment
            _shift_element_coords(clean_frag, dx, dy)
            # Also shift inner fragment BoundingBoxes (not covered by
            # _shift_element_coords since it uses .iter on the element
            # itself, but inner <fragment> BB is on a non-n/non-t tag)
            for inner in clean_frag.iter("fragment"):
                if inner is not clean_frag:
                    ib = inner.get("BoundingBox")
                    if ib:
                        vals = [float(v) for v in ib.split()]
                        if len(vals) >= 4:
                            inner.set("BoundingBox",
                                      f"{vals[0]+dx:.2f} {vals[1]+dy:.2f} "
                                      f"{vals[2]+dx:.2f} {vals[3]+dy:.2f}")

            # --- Restore abbreviation nodes ---
            if saved_abbrevs:
                # Find dummy atoms in the cleaned fragment
                dummies = [n for n in clean_frag.findall("n")
                           if n.get("Element") == _ABBREV_DUMMY_ELEMENT]

                # Match dummies to saved abbreviations by position proximity
                used_saved = set()
                for dummy in dummies:
                    dp = dummy.get("p", "").split()
                    if len(dp) < 2:
                        continue
                    d_x, d_y = float(dp[0]), float(dp[1])

                    # Find closest saved abbreviation
                    best_si = -1
                    best_d2 = float("inf")
                    for si, saved in enumerate(saved_abbrevs):
                        if si in used_saved:
                            continue
                        sp = saved.get("p", "").split()
                        if len(sp) < 2:
                            continue
                        s_x, s_y = float(sp[0]), float(sp[1])
                        d2 = (d_x - s_x) ** 2 + (d_y - s_y) ** 2
                        if d2 < best_d2:
                            best_d2 = d2
                            best_si = si

                    if best_si < 0:
                        continue
                    used_saved.add(best_si)
                    saved_node = saved_abbrevs[best_si]

                    # Compute offset from old to new abbreviation position
                    old_sp = saved_node.get("p", "").split()
                    if len(old_sp) < 2:
                        continue
                    abbr_dx = d_x - float(old_sp[0])
                    abbr_dy = d_y - float(old_sp[1])

                    # Update abbreviation node position + ID
                    saved_node.set("p", dummy.get("p"))
                    saved_node.set("id", dummy.get("id"))

                    # Shift inner fragment coordinates by the same offset
                    inner_frag = saved_node.find("fragment")
                    if inner_frag is not None:
                        _shift_element_coords(inner_frag, abbr_dx, abbr_dy)

                    # Replace dummy with abbreviation in the fragment
                    children = list(clean_frag)
                    idx = children.index(dummy)
                    clean_frag.remove(dummy)
                    clean_frag.insert(idx, saved_node)

                    if verbose:
                        lbl = ""
                        t = saved_node.find("t")
                        if t is not None:
                            lbl = "".join(
                                (s.text or "") for s in t.findall("s"))
                        print(f"  Fragment {frag_id}: restored "
                              f"abbreviation '{lbl}' at "
                              f"({d_x:.1f}, {d_y:.1f})",
                              file=sys.stderr)

            # Preserve original fragment ID
            clean_frag.set("id", frag_id)

            # Restore objecttags (ChemScript strips custom metadata)
            for ot in saved_objecttags:
                clean_frag.append(ot)

            # Replace fragment in page
            page_children = list(page)
            frag_index = page_children.index(frag)
            page.remove(frag)
            page.insert(frag_index, clean_frag)

            cleaned_count += 1
            if verbose:
                print(f"  Fragment {frag_id}: cleaned "
                      f"(shift dx={dx:.1f}, dy={dy:.1f})",
                      file=sys.stderr)

        except Exception as exc:
            if verbose:
                print(f"  Fragment {frag_id}: cleanup failed: {exc}",
                      file=sys.stderr)
        finally:
            for tmp in (tmp_in, tmp_out):
                if tmp and os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass

    # Close ChemScript bridge
    if cs_bridge is not None:
        try:
            cs_bridge.close()
        except Exception:
            pass

    return cleaned_count


def _cleanup_fragments_rdkit(root: ET.Element,
                             verbose: bool = False) -> int:
    """Clean up each fragment's geometry via RDKit (fallback for ChemScript).

    Uses rdkit_utils.cleanup_fragment_rdkit() which does RDKit 2D layout
    + Kabsch orientation restoration.  Abbreviation groups are included
    as dummy atoms so their bonds get proper lengths too.

    Returns the number of fragments cleaned.
    """
    from ...rdkit_utils import cleanup_fragment_rdkit

    page = root.find("page")
    if page is None:
        return 0

    cleaned = 0
    for frag in page.findall("fragment"):
        try:
            if cleanup_fragment_rdkit(frag, verbose):
                cleaned += 1
        except Exception as e:
            if verbose:
                frag_id = frag.get("id", "?")
                print(f"    [warn] RDKit cleanup skipped fragment {frag_id}: {e}",
                      file=sys.stderr)
    return cleaned


# ---------------------------------------------------------------------------
# CDXML I/O helpers
# ---------------------------------------------------------------------------

def _parse_cdxml(path: str) -> ET.ElementTree:
    return ET.parse(path)


def _write_cdxml(tree: ET.ElementTree, path: str):
    """Write CDXML, re-inserting DOCTYPE."""
    tree.write(path, xml_declaration=True, encoding="UTF-8")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "<!DOCTYPE" not in content:
        content = content.replace(
            "?>",
            '?>\n<!DOCTYPE CDXML SYSTEM '
            '"http://www.cambridgesoft.com/xml/cdxml.dtd" >',
            1,
        )
    content = content.replace("ns0:", "").replace(":ns0", "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _convert_cdx_to_cdxml(cdx_path: str, verbose: bool = False) -> str:
    """Convert CDX to CDXML using cdx_converter.py.

    Returns path to the generated CDXML file.
    """
    cdxml_path = os.path.splitext(cdx_path)[0] + ".cdxml"
    cmd = [sys.executable, "-m", "cdxml_toolkit.cdx_converter",
           cdx_path, "-o", cdxml_path]
    if verbose:
        print(f"  Converting CDX → CDXML: {os.path.basename(cdx_path)}",
              file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"CDX conversion failed: {result.stderr.strip()}")
    if verbose:
        print(f"  {result.stdout.strip()}", file=sys.stderr)
    return cdxml_path


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    input_path: str,
    output_path: str,
    merge_conditions: bool = True,
    approach: str = "chemdraw_mimic",
    chemscript_cleanup: bool = True,
    align_mode: str = "rdkit",
    eln_csv: Optional[str] = None,
    ref_cdxml: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Run the full COM-free polishing pipeline.

    Parameters
    ----------
    input_path : str
        Path to input .cdx or .cdxml file.
    output_path : str
        Path for final output .cdxml file.
    merge_conditions : bool
        Merge all condition text into one centered block (default True).
    approach : str
        Layout approach for reaction_cleanup (default "chemdraw_mimic").
    chemscript_cleanup : bool
        Run ChemScript CleanupStructure on each fragment before bond
        normalization (fixes bond angles; default True). Cleaned
        structures are re-aligned to their original orientation via
        Kabsch alignment so the cleanup doesn't rotate the scheme.
    align_mode : str
        How to align reactant/reagent orientations to the product.
        "rdkit" (default): RDKit MCS + GenerateDepictionMatching2DStructure.
            Can rotate individual bonds, not just the whole molecule.
            Falls back to scheme_polisher's Kabsch if RDKit is unavailable.
        "rxnmapper": ML transformer atom mapping via RXNMapper.
            Understands reaction chemistry; falls back to MCS if unavailable.
        "kabsch": rigid-rotation Kabsch alignment via scheme_polisher
            (legacy mode — only rotates the entire fragment).
    eln_csv : str or None
        Path to Findmolecule ELN CSV file for enrichment (equivalents,
        run arrow with SM mass and product yield).
    ref_cdxml : str or None
        Path to a reference CDXML file containing known-good structures
        drawn with the desired orientation (e.g. from a group meeting
        slide).  The product is aligned to the best-matching reference
        structure via MCS, then reactants are aligned to the product.
    verbose : bool
        Print progress to stderr.

    Returns
    -------
    str
        Path to the output file.
    """
    def log(msg: str):
        if verbose:
            print(f"[v2] {msg}", file=sys.stderr)

    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    ext = os.path.splitext(input_path)[1].lower()

    # --- Step 1: CDX → CDXML conversion if needed ---
    if ext == ".cdx":
        cdxml_path = _convert_cdx_to_cdxml(input_path, verbose)
        owns_cdxml = False  # don't delete — user may want it
    elif ext == ".cdxml":
        cdxml_path = input_path
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    # --- Step 2: Parse CDXML and optionally run ChemScript cleanup ---
    tree = _parse_cdxml(cdxml_path)
    root = tree.getroot()

    if chemscript_cleanup:
        log("Step 0: Running fragment geometry cleanup...")
        cleanup_done = False
        # RDKit is the default cleanup path (works without ChemScript)
        try:
            n_cleaned = _cleanup_fragments_rdkit(root, verbose)
            if n_cleaned > 0:
                log(f"  Cleaned {n_cleaned} fragment(s) via RDKit")
                cleanup_done = True
            else:
                log(f"  RDKit cleanup returned 0 fragments, trying ChemScript...")
        except Exception as exc:
            log(f"  RDKit cleanup failed ({exc}), trying ChemScript...")
        # ChemScript fallback (if available and RDKit didn't clean anything)
        if not cleanup_done:
            try:
                n_cleaned = _cleanup_fragments_chemscript(root, verbose)
                if n_cleaned > 0:
                    log(f"  Cleaned {n_cleaned} fragment(s) via ChemScript")
                else:
                    log(f"  No fragments cleaned by either backend")
            except Exception as exc2:
                log(f"  ChemScript also unavailable ({exc2}), "
                    f"continuing without cleanup...")

    # --- Normalize bond lengths per-fragment ---
    log("Step 1: Normalizing bond lengths to ACS 14.40 pt...")
    n_scaled = normalize_bond_lengths(root, TARGET_BOND_LENGTH, verbose)
    log(f"  Scaled {n_scaled} fragment(s)")

    # --- Step 3: Apply ACS document settings ---
    log("Step 2: Applying ACS Document 1996 settings...")
    apply_acs_settings(root)

    # --- Step 3: Normalize fonts ---
    log("Step 3: Normalizing fonts to Arial 10pt...")
    normalize_fonts(root, verbose)

    # --- Step 3b: Fix narrow vertical text from ELN exports ---
    n_fixed_text = fix_narrow_text(root, verbose)
    if n_fixed_text:
        log(f"  Fixed {n_fixed_text} narrow text element(s)")

    # --- Step 3c: Resolve orphan reagent text labels ---
    n_resolved = resolve_orphan_reagent_text(root, verbose)
    if n_resolved:
        log(f"  Resolved {n_resolved} orphan reagent text label(s)")

    # --- Step 5: Write intermediate CDXML ---
    tmpdir = tempfile.mkdtemp(prefix="spv2_")
    normalized_path = os.path.join(tmpdir, "normalized.cdxml")
    _write_cdxml(tree, normalized_path)
    log(f"  Wrote normalized CDXML to temp")

    try:
        # --- Step 6: Run scheme_polisher logic ---
        # Always skip alignment inside polish_scheme — alignment is handled
        # as an explicit Step 4e below (either rdkit or kabsch).
        log("Step 4: Running scheme_polisher (classification + swaps + "
            "formatting, alignment deferred to Step 4e)...")
        from .scheme_polisher import polish_scheme, _compact_toward_arrow

        polished_path = os.path.join(tmpdir, "polished.cdxml")
        result = polish_scheme(
            normalized_path, polished_path,
            verbose=verbose,
            merge_conditions=merge_conditions,
            skip_alignment=True,
        )

        n_replaced = len(result["replacements"])
        n_promoted = len(result["promotions"])
        n_aligned = len(result.get("alignments", []))
        n_reformatted = len(result["reformatted"])
        n_deduped = len(result["dedup_removed"])
        log(f"  {n_replaced} structure->text, {n_promoted} text->structure, "
            f"{n_aligned} aligned (Kabsch), {n_reformatted} reformatted, "
            f"{n_deduped} deduped"
            + (", conditions merged" if result.get("merged_conditions") else ""))

        # --- Step 4d: Align product to reference orientation ---
        if ref_cdxml:
            log("Step 4d: Aligning product to reference structure...")
            polished_tree = _parse_cdxml(polished_path)
            polished_root = polished_tree.getroot()
            try:
                success = align_product_to_reference(
                    polished_root, ref_cdxml, verbose=verbose)
                if success:
                    _write_cdxml(polished_tree, polished_path)
                    log("  Product aligned to reference orientation")
                else:
                    log("  No matching reference found — product keeps "
                        "current orientation")
            except Exception as exc:
                log(f"  WARNING: Reference alignment failed ({exc})")

        # --- Step 4e: Alignment to product orientation ---
        if align_mode == "rdkit":
            log("Step 4e: RDKit MCS alignment to product orientation...")
            polished_tree = _parse_cdxml(polished_path)
            polished_root = polished_tree.getroot()
            try:
                n_rdkit_aligned = rdkit_align_to_product(
                    polished_root, verbose=verbose)
                if n_rdkit_aligned > 0:
                    _write_cdxml(polished_tree, polished_path)
                    log(f"  Aligned {n_rdkit_aligned} fragment(s) via "
                        f"RDKit MCS + GenerateDepictionMatching2DStructure")
                else:
                    log("  No fragments aligned via RDKit "
                        "(MCS too small or RDKit unavailable)")
            except Exception as exc:
                log(f"  WARNING: RDKit alignment failed ({exc}), "
                    f"falling back to Kabsch...")
                # Fall back to Kabsch if RDKit fails
                polished_tree = _parse_cdxml(polished_path)
                polished_root = polished_tree.getroot()
                try:
                    aligned_ids = kabsch_align_to_product(
                        polished_root, verbose=verbose)
                    if aligned_ids:
                        _write_cdxml(polished_tree, polished_path)
                        log(f"  Kabsch fallback aligned {len(aligned_ids)} "
                            f"fragment(s)")
                except Exception as exc2:
                    log(f"  WARNING: Kabsch fallback also failed ({exc2})")
        elif align_mode == "rxnmapper":
            log("Step 4e: RXNMapper alignment to product orientation...")
            polished_tree = _parse_cdxml(polished_path)
            polished_root = polished_tree.getroot()
            try:
                n_rxnm_aligned = rxnmapper_align_to_product(
                    polished_root, verbose=verbose)
                if n_rxnm_aligned > 0:
                    _write_cdxml(polished_tree, polished_path)
                    log(f"  Aligned {n_rxnm_aligned} fragment(s) via "
                        f"RXNMapper atom maps")
                else:
                    log("  No fragments aligned via RXNMapper")
            except Exception as exc:
                log(f"  WARNING: RXNMapper alignment failed ({exc}), "
                    f"falling back to RDKit MCS...")
                polished_tree = _parse_cdxml(polished_path)
                polished_root = polished_tree.getroot()
                try:
                    n_rdkit_aligned = rdkit_align_to_product(
                        polished_root, verbose=verbose)
                    if n_rdkit_aligned > 0:
                        _write_cdxml(polished_tree, polished_path)
                        log(f"  MCS fallback aligned {n_rdkit_aligned} "
                            f"fragment(s)")
                except Exception as exc2:
                    log(f"  WARNING: MCS fallback also failed ({exc2})")
        elif align_mode == "kabsch":
            log("Step 4e: Kabsch alignment to product orientation...")
            polished_tree = _parse_cdxml(polished_path)
            polished_root = polished_tree.getroot()
            try:
                aligned_ids = kabsch_align_to_product(
                    polished_root, verbose=verbose)
                if aligned_ids:
                    _write_cdxml(polished_tree, polished_path)
                    log(f"  Aligned {len(aligned_ids)} fragment(s) via Kabsch")
                else:
                    log("  No fragments aligned via Kabsch")
            except Exception as exc:
                log(f"  WARNING: Kabsch alignment failed ({exc})")

        # --- Step 4.5: Reposition non-substrate reactant above arrow ---
        if eln_csv:
            from .eln_enrichment import reposition_reactant_above_arrow

            polished_tree = _parse_cdxml(polished_path)
            polished_root = polished_tree.getroot()
            if reposition_reactant_above_arrow(
                    polished_root, eln_csv, verbose=verbose):
                _write_cdxml(polished_tree, polished_path)
                log("Step 4.5: Repositioned non-substrate reactant above arrow")

        # --- Step 5.5: Phase A — ELN enrichment (equiv into text, before layout) ---
        enrichment_data = None
        if eln_csv:
            log("Step 5.5: Phase A — Injecting equivalents into text...")
            from .eln_enrichment import match_csv_to_scheme, enrich_phase_a

            # Re-parse the polished CDXML to inject equivs
            polished_tree = _parse_cdxml(polished_path)
            polished_root = polished_tree.getroot()

            enrichment_data = match_csv_to_scheme(
                polished_root, eln_csv, verbose=verbose)
            log(f"  Matched {len(enrichment_data.matches)} CSV reagents "
                f"to scheme elements")

            merged_text_id = result.get("merged_text_id")
            enrich_phase_a(
                polished_root, enrichment_data,
                merged_text_id=str(merged_text_id) if merged_text_id else None,
                verbose=verbose,
            )

            # Write back
            _write_cdxml(polished_tree, polished_path)

        # --- Step 7: Compact toward arrow ---
        log("Step 5: Compacting objects toward arrow...")
        _compact_toward_arrow(polished_path, verbose)

        # --- Step 8: Run reaction_cleanup ---
        log(f"Step 6: Running reaction_cleanup (approach={approach})...")
        from ...layout.reaction_cleanup import run_cleanup

        run_cleanup(polished_path, output_path, approach=approach, verbose=verbose)
        log(f"  Final layout complete")

        # --- Step 7.5: Phase B — ELN enrichment (run arrow + eq labels, after layout) ---
        if eln_csv and enrichment_data:
            log("Step 7.5: Phase B — Adding run arrow + eq labels...")
            from .eln_enrichment import enrich_phase_b

            final_tree = _parse_cdxml(output_path)
            final_root = final_tree.getroot()

            enrich_phase_b(final_root, enrichment_data, verbose=verbose)

            _write_cdxml(final_tree, output_path)
            log(f"  Enrichment complete")

    finally:
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

    log(f"Output: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _classify_error(exc: Exception) -> str:
    """Map an exception to a machine-readable error code."""
    msg = str(exc).lower()
    name = type(exc).__name__

    if name == "FileNotFoundError" or "not found" in msg:
        return "file_not_found"
    if "parse" in msg or "xml" in msg.lower() or name == "ParseError":
        return "cdxml_parse_failed"
    if "rdkit" in msg or "smiles" in msg:
        return "smiles_parse_failed"
    if "chemscript" in msg:
        return "chemscript_error"
    if "alignment" in msg or "mcs" in msg:
        return "alignment_failed"
    if "enrichment" in msg or "csv" in msg:
        return "enrichment_failed"
    if "layout" in msg or "cleanup" in msg:
        return "layout_failed"
    if name in ("KeyError", "IndexError", "ValueError", "TypeError"):
        return "internal_error"
    return "pipeline_failed"


def main(argv: Optional[List[str]] = None) -> int:
    from ...layout.reaction_cleanup import APPROACHES

    parser = argparse.ArgumentParser(
        description=(
            "COM-free scheme polishing pipeline: normalize bond lengths, "
            "classify reagents, swap structures/text, align orientations, "
            "format subscripts, merge conditions, and clean up layout."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        help="Input .cdx or .cdxml file",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output CDXML file (default: <input_stem>-v2.cdxml)",
    )
    parser.add_argument(
        "--no-merge-conditions", action="store_true",
        help="Keep condition text as separate labels (default: merge into one block)",
    )
    parser.add_argument(
        "--approach", choices=list(APPROACHES.keys()),
        default="chemdraw_mimic",
        help="Layout approach for reaction_cleanup (default: chemdraw_mimic)",
    )
    parser.add_argument(
        "--no-chemscript-cleanup", action="store_true",
        help="Skip ChemScript CleanupStructure per fragment "
             "(default: cleanup is enabled to fix bond angles)",
    )
    parser.add_argument(
        "--align-mode", choices=["rdkit", "rxnmapper", "kabsch"],
        default="rdkit",
        help="Orientation alignment method (default: rdkit). "
             "'rdkit' uses MCS + GenerateDepictionMatching2DStructure "
             "(can rotate individual bonds for better alignment). "
             "'rxnmapper' uses ML transformer atom mapping to align "
             "reactants to product orientation (falls back to MCS). "
             "'kabsch' uses rigid-body rotation only (legacy backup).",
    )
    parser.add_argument(
        "--eln-csv", default=None,
        help="Findmolecule ELN CSV file for enrichment (adds equivalents, "
             "run arrow with SM mass and product yield)",
    )
    parser.add_argument(
        "--ref-cdxml", default=None,
        help="Reference CDXML file with known-good structure(s) for "
             "product orientation. The product is aligned to the best-"
             "matching reference via MCS, then reactants align to the "
             "product.",
    )
    parser.add_argument(
        "--render", action="store_true",
        help="Render output to PNG via cdxml_to_image.py",
    )
    parser.add_argument(
        "--json-errors", action="store_true",
        help="Output structured JSON error objects to stderr on failure "
             "(for agent orchestration)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print progress to stderr",
    )

    args = parser.parse_args(argv)

    def _emit_json_error(error_code: str, detail: str,
                         file: str = None) -> None:
        """Write a structured JSON error to stderr if --json-errors."""
        if not args.json_errors:
            return
        obj = {"error": error_code, "detail": detail}
        if file:
            obj["file"] = file
        print(json.dumps(obj), file=sys.stderr)

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        msg = f"file not found: {input_path}"
        _emit_json_error("file_not_found", msg, os.path.basename(input_path))
        if not args.json_errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    if args.output is None:
        stem = os.path.splitext(input_path)[0]
        output_path = stem + "-v2.cdxml"
    else:
        output_path = os.path.abspath(args.output)

    try:
        run_pipeline(
            input_path,
            output_path,
            merge_conditions=not args.no_merge_conditions,
            approach=args.approach,
            chemscript_cleanup=not args.no_chemscript_cleanup,
            align_mode=args.align_mode,
            eln_csv=args.eln_csv,
            ref_cdxml=args.ref_cdxml,
            verbose=args.verbose,
        )
    except Exception as e:
        error_type = type(e).__name__
        error_code = _classify_error(e)
        _emit_json_error(error_code, str(e),
                         os.path.basename(input_path))
        if not args.json_errors:
            print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    print(f"Output: {output_path}")

    if args.render:
        try:
            from ...chemdraw.cdxml_to_image import cdxml_to_image
            png_path = cdxml_to_image(output_path)
            print(f"Rendered: {png_path}")
        except Exception as e:
            _emit_json_error("render_failed", str(e),
                             os.path.basename(output_path))
            if not args.json_errors:
                print(f"Render failed: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
