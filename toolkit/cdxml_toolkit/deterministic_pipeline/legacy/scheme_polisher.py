#!/usr/bin/env python3
"""
scheme_polisher.py — Polish a CDXML reaction scheme for presentation.

Takes a CDXML reaction scheme (typically from eln_cdx_cleanup.py) and:
  1. Classifies reagents as atom-contributing or non-contributing
     (using reactant_heuristic.py)
  2. Replaces non-contributing reagent structures with text abbreviations
     (e.g. Cs₂CO₃ structure → "Cs2CO3" text, n-BuLi → "n-BuLi")
  3. Promotes atom-contributing text labels to drawn structures
     (e.g. "Morpholine" → morpholine structure via ChemScript name resolution)
  4. Aligns atom-contributing reagents to match product orientation:
     a. Finds atom correspondence via RDKit substructure match or MCS
     b. Maps RDKit (MOL) atom indices to CDXML node indices by coordinate
        matching (handles ChemScript atom reordering on export)
     c. Computes optimal rigid rotation via Kabsch algorithm on matched
        CDXML coordinates (3× heteroatom weighting for symmetric rings)
     d. Applies rotation in-place around reagent centroid
  5. Reformats text labels (subscripts for numbers, italic for prefixes)
  6. Deduplicates identical reagents/conditions (e.g. duplicate "THF")
  7. Optionally merges all condition text into a single centered block
     below the arrow (--merge-conditions)
  8. Compacts above/below-arrow objects toward the arrow
  9. Optionally runs ChemDraw COM "Clean Up Reaction" for final spacing

Post-processing modes (default: compact + ChemDraw cleanup):
  --no-chemdraw-cleanup   Compact only, skip ChemDraw COM pass
  --no-compact            Skip compaction and ChemDraw COM (raw polished output)

Usage:
    python scheme_polisher.py -i scheme.cdxml [-o polished.cdxml] [-v]
    python scheme_polisher.py -i scheme.cdxml --merge-conditions -v
    python scheme_polisher.py -i scheme.cdxml --no-chemdraw-cleanup
    python scheme_polisher.py -i scheme.cdxml --no-compact

Dependencies:
    - reactant_heuristic.py (reagent classification)
    - chemscript_bridge.py  (text→structure promotion, MOL export)
    - rdkit                 (MCS, substructure matching)
    - reagent_abbreviations.json (curated name→display mapping)
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from typing import Dict, List, Optional, Set, Tuple
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Shared reagent database
# ---------------------------------------------------------------------------

from ...resolve.reagent_db import get_reagent_db


# ---------------------------------------------------------------------------
# Text formatting: subscripts + italic prefixes (from text_formatting.py)
# ---------------------------------------------------------------------------

from ...text_formatting import (
    build_formatted_s_xml as _build_formatted_s_xml,  # Re-exported for eln_enrichment.py backward compat
    needs_subscript as _needs_subscript,
    split_italic_prefix as _split_italic_prefix,
    SUBSCRIPT_RE as _SUBSCRIPT_RE,
    ITALIC_PREFIXES as _ITALIC_PREFIXES,
)

# Keep the old name as an alias used by _build_replacement_text_element
_build_subscripted_s_xml = _build_formatted_s_xml


# ---------------------------------------------------------------------------
# CDXML Helpers
# ---------------------------------------------------------------------------

def _get_text_content(el: ET.Element) -> str:
    """Extract concatenated text from all <s> children of a <t> element.
    Joins without spaces — chemical formulae like Cs2CO3 are split across
    multiple <s> elements (Cs + 2 + CO + 3) and must not get spaces."""
    parts = []
    for s in el.iter("s"):
        if s.text:
            parts.append(s.text)
    return "".join(parts).strip()


def _get_fm_molecule_type(el: ET.Element) -> Optional[int]:
    """Read the Findmolecule MOLECULE TYPE objecttag.
    Values: 0=molecule, 1=solvent, 2=condition text, 3=product."""
    for ot in el.iter("objecttag"):
        if ot.get("Name") == "FM MOLECULE TYPE":
            try:
                return int(ot.get("Value", ""))
            except ValueError:
                return None
    return None


def _fragment_bbox_center(frag: ET.Element) -> Tuple[float, float]:
    """Compute the center of a fragment's bounding box from node positions.

    Delegates to cdxml_utils.fragment_centroid(); falls back to (500, 250).
    """
    from ...cdxml_utils import fragment_centroid
    result = fragment_centroid(frag)
    if result is not None:
        return result
    return 500.0, 250.0  # fallback center


def _element_to_xml_string(el: ET.Element) -> str:
    """Serialize an element to a raw XML string."""
    return ET.tostring(el, encoding="unicode")


# ---------------------------------------------------------------------------
# Alignment imports (from alignment.py)
# ---------------------------------------------------------------------------
# All alignment primitives + high-level orchestrators live in alignment.py.
# We import the public names here and keep private aliases so any internal
# callers that used the old names still work.

from ...layout.alignment import (
    sp_fragment_to_cdxml,
    filtered_atom_nodes,
    compute_rigid_rotation_2d,
    rotate_fragment_in_place,
    make_abbrev_dummy_copy,
    kabsch_align_fragment_to_product,
    kabsch_align_to_product,
)

# Backward-compatible private aliases
_sp_fragment_to_cdxml = sp_fragment_to_cdxml
_filtered_atom_nodes = filtered_atom_nodes
_compute_rigid_rotation = compute_rigid_rotation_2d
_rotate_fragment_in_place = rotate_fragment_in_place
_make_abbrev_dummy_copy = make_abbrev_dummy_copy
_align_reagent_to_product = kabsch_align_fragment_to_product


# ---------------------------------------------------------------------------
# Display name resolution for non-contributing fragments
# ---------------------------------------------------------------------------

def _resolve_display_name(
    smiles: Optional[str],
    name: Optional[str],
    role: Optional[str],
) -> Optional[str]:
    """Determine the text abbreviation to display for a non-contributing reagent.

    Resolution chain:
      1a. Reagent DB display_name (via canonical SMILES — exact match)
      1b. Reagent DB display_name (via stereo-agnostic SMILES match)
      2a. Reagent DB display_name (via exact name/alias)
      2b. Reagent DB display_name (via Levenshtein on name — catches typos
          and abbreviation variants like EDC.HCl, nBuLi, i-Pr2NEt)
      3.  The reagent name itself (if available)
      4.  None (keep structure as-is)
    """
    db = get_reagent_db()

    # 1a. Look up display name by SMILES (exact canonical match)
    if smiles:
        display = db.display_for_smiles(smiles)
        if display:
            return display

    # 1b. Stereo-agnostic SMILES match (e.g. OPSIN omits E/Z on DEAD)
    if smiles:
        display = _match_smiles_no_stereo(smiles, db)
        if display:
            return display

    # 2a. Look up display name by name/alias (exact)
    if name:
        display = db.display_for_name(name)
        if display:
            return display

    # 2b. Levenshtein fuzzy match on name
    if name:
        display = _match_name_levenshtein(name, db)
        if display:
            return display

    # 3. Use the name as-is
    if name:
        return name

    return None


# Levenshtein similarity threshold for name matching (0.0 - 1.0).
# 0.80 catches "EDC.HCl"→"edc" (0.86), "nBuLi"→"n-buli" (0.80),
# "DIEA"→"dipea" (0.80) while rejecting spurious matches.
_LEVENSHTEIN_THRESHOLD = 0.80


def _levenshtein_distance(s: str, t: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s) < len(t):
        return _levenshtein_distance(t, s)
    if not t:
        return len(s)
    prev = list(range(len(t) + 1))
    for i, sc in enumerate(s):
        curr = [i + 1]
        for j, tc in enumerate(t):
            cost = 0 if sc == tc else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _match_name_levenshtein(
    name: str, db: 'ReagentDB', threshold: float = _LEVENSHTEIN_THRESHOLD,
) -> Optional[str]:
    """Find the best DB entry for *name* via Levenshtein similarity.

    Returns the display name if similarity >= threshold, else None.
    """
    query = name.strip().lower()
    # Also try stripping common suffixes/prefixes that don't affect identity
    # e.g. "EDC.HCl" → "edc", "Pd(OAc)2·xH2O" → "pd(oac)2"
    candidates = [query]
    for sep in ['.', '\u00b7', '\u2022', ' ']:
        if sep in query:
            candidates.append(query.split(sep)[0])

    all_keys = sorted(db._by_name.keys())
    best_score = 0.0
    best_key = None

    for candidate in candidates:
        if not candidate:
            continue
        for key in all_keys:
            dist = _levenshtein_distance(candidate, key)
            max_len = max(len(candidate), len(key))
            if max_len == 0:
                continue
            similarity = 1.0 - dist / max_len
            if similarity > best_score:
                best_score = similarity
                best_key = key

    if best_score >= threshold and best_key:
        display = db.display_for_name(best_key)
        if display:
            print(f"    Levenshtein: '{name}' -> '{best_key}' "
                  f"(similarity={best_score:.2f})", file=sys.stderr)
            return display
    return None


def _match_smiles_no_stereo(smiles: str, db: 'ReagentDB') -> Optional[str]:
    """Match SMILES against DB after stripping stereochemistry.

    Catches cases like DEAD where the input SMILES has no E/Z
    but the DB entry has explicit /N=N/ stereo.
    """
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        Chem.RemoveStereochemistry(mol)
        flat_smi = Chem.MolToSmiles(mol)

        # Compare against all DB SMILES (also stripped)
        for smi_key, entry in db._by_smiles.items():
            mol2 = Chem.MolFromSmiles(smi_key)
            if mol2 is None:
                continue
            Chem.RemoveStereochemistry(mol2)
            flat2 = Chem.MolToSmiles(mol2)
            if flat_smi == flat2:
                return entry.get("display")
    except ImportError:
        pass
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Build replacement <t> element for a non-contributing fragment
# ---------------------------------------------------------------------------

def _build_replacement_text_element(
    display_name: str,
    element_id: str,
    cx: float,
    cy: float,
    z_value: str,
) -> ET.Element:
    """Build a <t> element to replace a non-contributing fragment.

    The text is positioned at (cx, cy) which was the center of the original
    fragment's bounding box. Subscript formatting is applied for chemical
    formulae.
    """
    # Estimate bounding box
    char_w = len(display_name) * 5.8
    ascender = 8.0
    descender = 3.0

    # <t> p="x baseline_y" — baseline is at cy + partial ascender offset
    baseline_y = cy + 3.5  # shift down slightly from center to align baseline
    bx1 = cx - char_w / 2.0
    by1 = baseline_y - ascender
    bx2 = cx + char_w / 2.0
    by2 = baseline_y + descender

    s_xml = _build_subscripted_s_xml(display_name)

    # Build XML string and parse it
    t_xml = (
        f'<t id="{element_id}" '
        f'p="{cx:.2f} {baseline_y:.2f}" '
        f'BoundingBox="{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}" '
        f'Z="{z_value}" '
        f'InterpretChemically="no" '
        f'LineHeight="auto">'
        f'{s_xml}'
        f'</t>'
    )

    return ET.fromstring(t_xml)


# ---------------------------------------------------------------------------
# Resolve reagent name to CDXML fragment (for text → structure promotion)
# ---------------------------------------------------------------------------

def _resolve_name_to_fragment(
    name: str,
    smiles: Optional[str],
    cs_bridge,
    verbose: bool = False,
) -> Optional[Tuple[str, float, float, float, float]]:
    """Resolve a reagent name (or SMILES) to a CDXML fragment.

    Resolution chain:
      1. ChemScript name_to_cdxml
      2. If SMILES available: ChemScript smiles_to_cdxml
      3. PubChem name → SMILES → ChemScript smiles_to_cdxml

    Returns (frag_xml, xmin, ymin, xmax, ymax) or None.
    """
    from ...image.reaction_from_image import (
        _extract_fragment_from_cdxml, _measure_fragment_xml,
    )

    def log(msg: str):
        if verbose:
            print(f"[scheme_polisher] {msg}", file=sys.stderr)

    # Resolve canonical display name from reagent DB
    canonical = get_reagent_db().resolve_display(name)

    # 1. ChemScript name resolution
    try:
        cdxml_str = cs_bridge.name_to_cdxml(canonical)
        result = _extract_fragment_from_cdxml(cdxml_str)
        if result is not None:
            log(f"    '{canonical}' → ChemScript name OK")
            return result
    except Exception as exc:
        log(f"    '{canonical}' → ChemScript name failed: {exc}")

    # 2. Direct SMILES if available
    if smiles:
        try:
            cdxml_str = cs_bridge.smiles_to_cdxml(smiles)
            result = _extract_fragment_from_cdxml(cdxml_str)
            if result is not None:
                log(f"    '{canonical}' → ChemScript SMILES OK")
                return result
        except Exception as exc:
            log(f"    '{canonical}' → ChemScript SMILES failed: {exc}")

    # 3. PubChem name → SMILES → ChemScript
    try:
        from ...resolve.cas_resolver import resolve_name_to_smiles
        pub_smiles = resolve_name_to_smiles(canonical)
        if pub_smiles:
            log(f"    '{canonical}' → PubChem SMILES: {pub_smiles[:60]}")
            cdxml_str = cs_bridge.smiles_to_cdxml(pub_smiles)
            result = _extract_fragment_from_cdxml(cdxml_str)
            if result is not None:
                log(f"    '{canonical}' → PubChem+ChemScript OK")
                return result
    except Exception as exc:
        log(f"    '{canonical}' → PubChem fallback failed: {exc}")

    return None


# ---------------------------------------------------------------------------
# Core polishing logic
# ---------------------------------------------------------------------------

def polish_scheme(
    cdxml_path: str,
    output_path: str,
    verbose: bool = False,
    merge_conditions: bool = False,
    skip_alignment: bool = False,
    use_rxnmapper: bool = False,
) -> Dict:
    """Polish a CDXML reaction scheme in-place.

    If merge_conditions=True, all text labels above the arrow are merged
    into a single centered multi-line text block, and likewise below.

    If skip_alignment=True, Step 4d (Kabsch orientation alignment) is
    skipped.  Useful when the caller will run its own alignment
    afterwards (e.g. scheme_polisher_v2's RDKit MCS alignment).

    use_rxnmapper is deprecated and ignored.  Classification now uses
    Schneider FP scoring (context-aware, no ML dependency).

    Returns a dict describing changes made.
    """
    def log(msg: str):
        if verbose:
            print(f"[scheme_polisher] {msg}", file=sys.stderr)

    # --- Step 1: Run reactant_heuristic classification ---
    log("Running reactant_heuristic classification...")
    from ...perception.reactant_heuristic import classify_from_cdxml

    classification = classify_from_cdxml(cdxml_path,
                                          use_rxnmapper=use_rxnmapper)
    reagents = classification["reagents"]

    log(f"Classified {len(reagents)} reagent(s):")
    for r in reagents:
        log(f"  id={r['source_id']} type={r['source_type']} "
            f"class={r['classification']} "
            f"role={r.get('role', '-')} name={r.get('name', '-')}")

    # --- Step 2: Parse CDXML ---
    tree = ET.parse(cdxml_path)
    root = tree.getroot()
    page = root.find("page")
    if page is None:
        raise SystemExit("ERROR: no <page> element in CDXML")

    # Build id → element map and id → parent map
    id_to_el: Dict[str, ET.Element] = {}
    id_to_parent: Dict[str, ET.Element] = {}
    for parent in page:
        eid = parent.get("id", "")
        if eid:
            id_to_el[eid] = parent
            id_to_parent[eid] = page

    # --- Step 3: Parse <step> metadata ---
    scheme = page.find("scheme")
    step = scheme.find("step") if scheme is not None else None
    if step is None:
        raise SystemExit("ERROR: no <scheme><step> found in CDXML")

    reactant_ids = set(step.get("ReactionStepReactants", "").split())
    product_ids = set(step.get("ReactionStepProducts", "").split())
    above_ids = step.get("ReactionStepObjectsAboveArrow", "").split()
    below_ids = step.get("ReactionStepObjectsBelowArrow", "").split()

    # --- Step 4: Process non-contributing fragments → replace with text ---
    replacements = []   # (old_id, display_name)
    ids_to_remove = []  # fragment IDs to remove from page

    for r in reagents:
        if r["classification"] != "non_contributing":
            continue
        if r["source_type"] != "fragment":
            continue

        src_id = r["source_id"]
        el = id_to_el.get(src_id)
        if el is None or el.tag != "fragment":
            continue

        # Skip products (shouldn't happen but be safe)
        if src_id in product_ids:
            continue

        # Determine display name
        display_name = _resolve_display_name(
            r.get("smiles"), r.get("name"), r.get("role")
        )
        if display_name is None:
            log(f"  WARNING: no display name for fragment {src_id}, keeping structure")
            continue

        log(f"  Replacing fragment {src_id} with text '{display_name}'")

        # Get position from fragment center
        cx, cy = _fragment_bbox_center(el)
        z_value = el.get("Z", "1")

        # Build replacement text element (same ID to preserve step refs)
        new_t = _build_replacement_text_element(
            display_name, src_id, cx, cy, z_value
        )

        # Replace in page: remove old fragment, insert new text
        page.remove(el)
        # Insert before the scheme element to keep document order sensible
        scheme_idx = list(page).index(scheme) if scheme in page else len(list(page))
        page.insert(scheme_idx, new_t)

        replacements.append((src_id, display_name))

    # Move replaced IDs from ReactionStepReactants → above-arrow so they
    # are treated as conditions text (and eligible for merge-conditions).
    if replacements and step is not None:
        replaced_ids = {r[0] for r in replacements}
        # Remove from reactants
        current_reactants = step.get("ReactionStepReactants", "").split()
        new_reactants = [rid for rid in current_reactants
                         if rid not in replaced_ids]
        step.set("ReactionStepReactants", " ".join(new_reactants))
        # Add to above-arrow
        current_above = step.get("ReactionStepObjectsAboveArrow", "").split()
        current_above = [a for a in current_above if a]  # filter empty
        for rid, _ in replacements:
            if rid not in current_above:
                current_above.append(rid)
        step.set("ReactionStepObjectsAboveArrow", " ".join(current_above))
        # Update local tracking sets
        reactant_ids -= replaced_ids
        above_ids = current_above

    log(f"Replaced {len(replacements)} non-contributing fragment(s) with text")

    # --- Lazy-init ChemScript bridge (shared by Step 4b and 4d) ---
    cs_bridge = None

    def _ensure_cs_bridge():
        nonlocal cs_bridge
        if cs_bridge is None:
            from ...chemdraw.chemscript_bridge import ChemScriptBridge
            cs_bridge = ChemScriptBridge()
        return cs_bridge

    # --- Step 4b: Promote atom-contributing text labels to structures ---
    promotions = []  # (old_id, name)

    for r in reagents:
        if r["classification"] != "atom_contributing":
            continue
        if r["source_type"] != "text":
            continue

        src_id = r["source_id"]
        el = id_to_el.get(src_id)
        if el is None or el.tag != "t":
            continue

        name = r.get("name", "")
        if not name:
            continue

        log(f"  Promoting text '{name}' (id={src_id}) to structure...")

        # Lazy-init ChemScript bridge
        try:
            _ensure_cs_bridge()
        except Exception as exc:
            log(f"  WARNING: ChemScript unavailable ({exc}), "
                f"cannot promote text to structures")
            break

        # Resolve name → CDXML fragment
        frag_info = _resolve_name_to_fragment(name, r.get("smiles"), cs_bridge,
                                              verbose)
        if frag_info is None:
            log(f"  WARNING: could not resolve '{name}' to structure, keeping text")
            continue

        frag_xml, xmin, ymin, xmax, ymax = frag_info

        # Position the new fragment at the old text element's location
        from ...image.reaction_from_image import _translate_fragment_xml
        bb = el.get("BoundingBox", "")
        if bb:
            vals = [float(v) for v in bb.split()]
            tcx = (vals[0] + vals[2]) / 2.0
            tcy = (vals[1] + vals[3]) / 2.0
        else:
            p = el.get("p", "")
            if p:
                pp = p.split()
                tcx, tcy = float(pp[0]), float(pp[1])
            else:
                tcx, tcy = 500.0, 250.0

        frag_cx = (xmin + xmax) / 2.0
        frag_cy = (ymin + ymax) / 2.0
        dx = tcx - frag_cx
        dy = tcy - frag_cy
        translated = _translate_fragment_xml(frag_xml, dx, dy)

        # Parse the translated fragment XML and assign the old element's ID
        new_frag = ET.fromstring(translated)
        new_frag.set("id", src_id)

        # Replace in page
        page.remove(el)
        scheme_idx = list(page).index(scheme) if scheme in page else len(list(page))
        page.insert(scheme_idx, new_frag)

        # Update id_to_el
        id_to_el[src_id] = new_frag

        promotions.append((src_id, name))
        log(f"  Promoted '{name}' to structure (id={src_id})")

    log(f"Promoted {len(promotions)} text label(s) to structures")

    # --- Step 4d: Align atom-contributing reagents to product orientation ---
    alignments = []  # list of aligned fragment IDs

    if skip_alignment:
        log("Step 4d: Skipped (skip_alignment=True)")
    else:
        # Rebuild id_to_el after promotions
        id_to_el.clear()
        for el in page:
            eid = el.get("id", "")
            if eid:
                id_to_el[eid] = el

        # Collect atom-contributing fragment IDs (excluding product)
        contributing_frag_ids = set()
        for r in reagents:
            if r["classification"] != "atom_contributing":
                continue
            src_id = r["source_id"]
            el = id_to_el.get(src_id)
            if el is not None and el.tag == "fragment":
                if src_id not in product_ids:
                    contributing_frag_ids.add(src_id)

        if contributing_frag_ids:
            log(f"Step 4d: Aligning {len(contributing_frag_ids)} atom-contributing "
                f"fragment(s) to product orientation...")
            aligned_ids = kabsch_align_to_product(
                root, cs_bridge=cs_bridge, verbose=verbose,
                frag_ids=contributing_frag_ids)
            alignments = [(fid, "aligned") for fid in aligned_ids]
        else:
            log("Step 4d: No atom-contributing fragments to align")

    # Close ChemScript bridge (shared by 4b and 4d)
    if cs_bridge is not None:
        try:
            cs_bridge.close()
        except Exception:
            pass

    log(f"Aligned {len(alignments)} fragment(s) to product orientation")

    # --- Step 4c: Reformat existing text labels (subscripts + italic) ---
    # Rebuild id_to_el before reformatting
    id_to_el.clear()
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    above_ids_reformat = step.get("ReactionStepObjectsAboveArrow", "").split()
    below_ids_reformat = step.get("ReactionStepObjectsBelowArrow", "").split()
    all_condition_ids = set(above_ids_reformat) | set(below_ids_reformat)
    # Skip IDs that were just created in step 4 (already correctly formatted)
    newly_created_ids = {r[0] for r in replacements}
    reformatted = []

    for eid in all_condition_ids:
        if eid in newly_created_ids:
            continue
        el = id_to_el.get(eid)
        if el is None or el.tag != "t":
            continue

        # Get current plain text
        old_text = _get_text_content(el)
        if not old_text:
            continue

        # Look up canonical display form from reagent DB
        canonical = get_reagent_db().resolve_display(old_text)

        # Build new formatted <s> elements
        new_s_xml = _build_formatted_s_xml(canonical)

        # Check if reformatting would actually change anything
        old_s_xml = "".join(ET.tostring(s, encoding="unicode") for s in el.findall("s"))
        if old_s_xml == new_s_xml:
            continue

        # Remove old <s> children, keep objecttags and other children
        old_children = list(el)
        for child in old_children:
            if child.tag == "s":
                el.remove(child)

        # Parse the new <s> elements and insert at the front
        # Wrap in a dummy element for parsing
        wrapper = ET.fromstring(f"<dummy>{new_s_xml}</dummy>")
        insert_pos = 0
        for new_s in wrapper:
            el.insert(insert_pos, new_s)
            insert_pos += 1

        reformatted.append((eid, old_text, canonical))
        log(f"  Reformatted text id={eid}: '{old_text}' → '{canonical}' "
            f"(subscript/italic)")

    log(f"Reformatted {len(reformatted)} text label(s)")

    # --- Step 5: Deduplicate text elements ---
    # Rebuild id_to_el after replacements
    id_to_el.clear()
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    # Collect all text content for above/below arrow elements
    def _normalize_text(text: str) -> str:
        return text.strip().lower()

    above_ids = step.get("ReactionStepObjectsAboveArrow", "").split()
    below_ids = step.get("ReactionStepObjectsBelowArrow", "").split()

    dedup_removed = []

    for position_name, id_list_attr in [
        ("above", "ReactionStepObjectsAboveArrow"),
        ("below", "ReactionStepObjectsBelowArrow"),
    ]:
        id_list = step.get(id_list_attr, "").split()
        seen_texts: Dict[str, str] = {}  # normalized_text → first_id
        new_id_list = []
        for eid in id_list:
            el = id_to_el.get(eid)
            if el is None:
                continue

            # Only deduplicate text elements
            if el.tag == "t":
                text = _get_text_content(el)
                norm = _normalize_text(text)
                if norm in seen_texts:
                    # Duplicate — remove element and skip ID
                    log(f"  Dedup: removing duplicate '{text}' (id={eid}) "
                        f"from {position_name} (keeping id={seen_texts[norm]})")
                    page.remove(el)
                    dedup_removed.append((eid, text, position_name))
                    continue
                seen_texts[norm] = eid

            new_id_list.append(eid)

        step.set(id_list_attr, " ".join(new_id_list))

    log(f"Removed {len(dedup_removed)} duplicate(s)")

    # --- Step 6: Merge all text labels into one centered block (optional) ---
    merged_conditions = False
    merged_text_id = None

    if merge_conditions:
        # Rebuild id_to_el
        id_to_el.clear()
        for el in page:
            eid = el.get("id", "")
            if eid:
                id_to_el[eid] = el

        # Find arrow midpoint for rough centering
        arrow_cx, arrow_cy = 500.0, 250.0  # fallback
        arrow_id = step.get("ReactionStepArrows", "").split()
        for aid in arrow_id:
            a_el = id_to_el.get(aid)
            if a_el is None:
                # Try the superseding arrow (graphic → arrow pattern)
                for child in page:
                    if child.tag == "arrow":
                        a_el = child
                        break
                if a_el is None:
                    for child in page:
                        if child.tag == "graphic" and child.get("id") == aid:
                            sup_id = child.get("SupersededBy", "")
                            if sup_id:
                                a_el = id_to_el.get(sup_id)
                            break
            if a_el is not None:
                head = a_el.get("Head3D", "")
                tail = a_el.get("Tail3D", "")
                if head and tail:
                    hx, hy = float(head.split()[0]), float(head.split()[1])
                    tx, ty = float(tail.split()[0]), float(tail.split()[1])
                    arrow_cx = (hx + tx) / 2.0
                    arrow_cy = (hy + ty) / 2.0
                else:
                    bb = a_el.get("BoundingBox", "")
                    if bb:
                        vals = [float(v) for v in bb.split()]
                        arrow_cx = (vals[0] + vals[2]) / 2.0
                        arrow_cy = (vals[1] + vals[3]) / 2.0
                break

        # Collect ALL text labels from above + below into one ordered list
        all_text_ids = []
        all_text_lines = []
        non_text_above = []
        non_text_below = []

        for position_name, id_list_attr in [
            ("above", "ReactionStepObjectsAboveArrow"),
            ("below", "ReactionStepObjectsBelowArrow"),
        ]:
            id_list = step.get(id_list_attr, "").split()
            for eid in id_list:
                el = id_to_el.get(eid)
                if el is None:
                    continue
                if el.tag == "t":
                    text = _get_text_content(el)
                    if text:
                        all_text_ids.append(eid)
                        all_text_lines.append(text)
                else:
                    if position_name == "above":
                        non_text_above.append(eid)
                    else:
                        non_text_below.append(eid)

        if len(all_text_ids) >= 2:
            log(f"  Merging {len(all_text_ids)} text labels into one block: "
                f"{all_text_lines}")

            # Build merged <s> content with \n between lines
            s_parts = []
            for i, text in enumerate(all_text_lines):
                if i > 0:
                    s_parts.append(
                        '<s font="3" size="10" color="0" face="96">\n</s>'
                    )
                canonical = get_reagent_db().resolve_display(text)
                s_parts.append(_build_formatted_s_xml(canonical))
            s_xml = "".join(s_parts)

            # Keep the first text element, remove all others
            keep_id = all_text_ids[0]
            keep_el = id_to_el[keep_id]
            keep_z = keep_el.get("Z", "1")

            for eid in all_text_ids[1:]:
                el = id_to_el.get(eid)
                if el is not None:
                    page.remove(el)

            # Position just below arrow — ChemDraw cleanup will refine
            line_height = 12.5
            n_lines = len(all_text_lines)
            max_text_len = max(len(t) for t in all_text_lines)
            total_w = max_text_len * 5.8
            total_h = n_lines * line_height

            mcx = arrow_cx
            by1 = arrow_cy + 4.0  # just below arrow
            by2 = by1 + total_h
            bx1 = mcx - total_w / 2.0
            bx2 = mcx + total_w / 2.0
            first_baseline_y = by1 + 10.0  # first line baseline

            # Rebuild the kept element
            for child in list(keep_el):
                keep_el.remove(child)

            keep_el.set("p", f"{mcx:.2f} {first_baseline_y:.2f}")
            keep_el.set("BoundingBox",
                         f"{bx1:.2f} {by1:.2f} {bx2:.2f} {by2:.2f}")
            keep_el.set("Z", keep_z)
            keep_el.set("InterpretChemically", "no")
            keep_el.set("LineHeight", "auto")
            keep_el.set("CaptionJustification", "Center")
            keep_el.set("Justification", "Center")

            # Parse and insert new <s> children
            wrapper = ET.fromstring(f"<dummy>{s_xml}</dummy>")
            for child in wrapper:
                keep_el.append(child)

            # Update step refs: merged text block goes above arrow
            # (ChemDraw Clean Up Reaction expects objects in above/below)
            step.set("ReactionStepObjectsAboveArrow",
                      " ".join(non_text_above + [keep_id]))
            step.set("ReactionStepObjectsBelowArrow",
                      " ".join(non_text_below))

            merged_conditions = True
            merged_text_id = keep_id
            log(f"  Merged into single text block (id={keep_id})")

    # --- Step 7: Write output CDXML ---
    tree.write(output_path, xml_declaration=True, encoding="UTF-8")

    # Post-process: fix XML declaration and DOCTYPE
    _fixup_cdxml_output(output_path)

    log(f"Written polished scheme to {output_path}")

    return {
        "replacements": replacements,
        "promotions": promotions,
        "alignments": alignments,
        "reformatted": reformatted,
        "dedup_removed": dedup_removed,
        "merged_conditions": merged_conditions,
        "merged_text_id": merged_text_id,
        "total_reagents": len(reagents),
        "product_smiles": classification.get("product_smiles"),
        "classification": classification,
    }


def _fixup_cdxml_output(path: str):
    """Fix up the CDXML output from ElementTree.

    ElementTree's write() doesn't include DOCTYPE and may mangle some
    attributes. This does a minimal fix-up pass.
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure proper XML declaration
    if not content.startswith("<?xml"):
        content = '<?xml version="1.0" encoding="UTF-8" ?>\n' + content

    # Add DOCTYPE if missing
    if "<!DOCTYPE CDXML" not in content:
        content = content.replace(
            "<CDXML",
            '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n<CDXML',
            1,
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# ChemDraw COM cleanup pass
# ---------------------------------------------------------------------------

def _find_arrow_center(page: ET.Element, step: ET.Element,
                       id_to_el: Dict[str, ET.Element],
                       ) -> Tuple[float, float]:
    """Find the arrow midpoint from step metadata."""
    arrow_cx, arrow_cy = 500.0, 250.0
    arrow_ids = step.get("ReactionStepArrows", "").split()
    for aid in arrow_ids:
        a_el = id_to_el.get(aid)
        if a_el is None:
            for child in page:
                if child.tag == "graphic" and child.get("id") == aid:
                    sup_id = child.get("SupersededBy", "")
                    if sup_id:
                        a_el = id_to_el.get(sup_id)
                    break
        if a_el is not None:
            head = a_el.get("Head3D", "")
            tail = a_el.get("Tail3D", "")
            if head and tail:
                hx, hy = float(head.split()[0]), float(head.split()[1])
                tx, ty = float(tail.split()[0]), float(tail.split()[1])
                arrow_cx = (hx + tx) / 2.0
                arrow_cy = (hy + ty) / 2.0
            else:
                bb = a_el.get("BoundingBox", "")
                if bb:
                    vals = [float(v) for v in bb.split()]
                    arrow_cx = (vals[0] + vals[2]) / 2.0
                    arrow_cy = (vals[1] + vals[3]) / 2.0
            break
    return arrow_cx, arrow_cy


def _compact_toward_arrow(cdxml_path: str, verbose: bool = False):
    """Move above/below-arrow objects closer to the arrow line.

    ChemDraw's "Clean Up Reaction" only recognises reaction components
    that are reasonably close together.  After merging conditions into
    one large text block the vertical spread can exceed this threshold.
    This helper nudges every above-arrow element downward and every
    below-arrow element upward so that all objects sit within a tight
    band around the arrow y-coordinate.
    """
    def log(msg: str):
        if verbose:
            print(f"[scheme_polisher] {msg}", file=sys.stderr)

    tree = ET.parse(cdxml_path)
    root = tree.getroot()
    page = root.find("page")
    scheme = page.find("scheme") if page is not None else None
    step = scheme.find("step") if scheme is not None else None
    if step is None:
        return

    id_to_el: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    arrow_cx, arrow_cy = _find_arrow_center(page, step, id_to_el)
    log(f"  Compacting: arrow center = ({arrow_cx:.1f}, {arrow_cy:.1f})")

    # Target: above-arrow objects sit with their bottom edge at arrow_cy - 5
    # Target: below-arrow objects sit with their top edge at arrow_cy + 5
    GAP = 5.0

    for attr, direction in [
        ("ReactionStepObjectsAboveArrow", "above"),
        ("ReactionStepObjectsBelowArrow", "below"),
    ]:
        ids = step.get(attr, "").split()
        for eid in ids:
            el = id_to_el.get(eid)
            if el is None:
                continue

            # Compute current bounding box center-y
            if el.tag == "fragment":
                _, cy = _fragment_bbox_center(el)
            elif el.tag == "t":
                bb = el.get("BoundingBox", "")
                if bb:
                    vals = [float(v) for v in bb.split()]
                    cy = (vals[1] + vals[3]) / 2.0
                else:
                    continue
            else:
                continue

            # How far to shift toward the arrow (y-axis points down)
            if direction == "above":
                target_cy = arrow_cy - GAP - 15  # keep a small gap above
                dy = target_cy - cy
                # dy > 0 means object is above target → move down toward arrow
                # dy < 0 means object is already below target → skip
                if dy <= 0:
                    continue
            else:
                target_cy = arrow_cy + GAP + 15
                dy = target_cy - cy
                # dy < 0 means object is below target → move up toward arrow
                # dy > 0 means object is already above target → skip
                if dy >= 0:
                    continue

            log(f"  Compacting {el.tag} id={eid} {direction}: "
                f"dy={dy:+.1f}")
            _shift_element_y(el, dy)

    tree.write(cdxml_path, xml_declaration=True, encoding="UTF-8")
    _fixup_cdxml_output(cdxml_path)


def _shift_element_y(el: ET.Element, dy: float):
    """Shift an element (fragment or text) vertically by dy points."""
    if el.tag == "fragment":
        # Shift all node positions
        for n in el.iter("n"):
            p = n.get("p")
            if p:
                parts = p.split()
                if len(parts) >= 2:
                    new_y = float(parts[1]) + dy
                    n.set("p", f"{parts[0]} {new_y:.2f}")
        # Shift nested text label positions
        for t in el.iter("t"):
            p = t.get("p")
            if p:
                parts = p.split()
                if len(parts) >= 2:
                    new_y = float(parts[1]) + dy
                    t.set("p", f"{parts[0]} {new_y:.2f}")
            bb = t.get("BoundingBox")
            if bb:
                vals = [float(v) for v in bb.split()]
                if len(vals) >= 4:
                    vals[1] += dy
                    vals[3] += dy
                    t.set("BoundingBox",
                          " ".join(f"{v:.2f}" for v in vals))
        # Shift fragment BoundingBox
        bb = el.get("BoundingBox")
        if bb:
            vals = [float(v) for v in bb.split()]
            if len(vals) >= 4:
                vals[1] += dy
                vals[3] += dy
                el.set("BoundingBox",
                       " ".join(f"{v:.2f}" for v in vals))

    elif el.tag == "t":
        p = el.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                new_y = float(parts[1]) + dy
                el.set("p", f"{parts[0]} {new_y:.2f}")
        bb = el.get("BoundingBox")
        if bb:
            vals = [float(v) for v in bb.split()]
            if len(vals) >= 4:
                vals[1] += dy
                vals[3] += dy
                el.set("BoundingBox",
                       " ".join(f"{v:.2f}" for v in vals))


def _chemdraw_cleanup_reaction(cdxml_path: str, output_path: str,
                                verbose: bool = False):
    """Run ChemDraw COM "Clean Up Reaction" on the CDXML file.

    Reuses the same COM automation pattern as eln_cdx_cleanup.py.
    Expects the file to already be compacted (see _compact_toward_arrow).
    """
    import win32com.client

    def log(msg: str):
        if verbose:
            print(f"[scheme_polisher] {msg}", file=sys.stderr)

    log("Running ChemDraw COM cleanup...")

    # Import COM helpers from eln_cdx_cleanup
    from .eln_cdx_cleanup import (
        _get_chemdraw, _chemdraw_open,
        _restore_chemdraw_window,
    )

    cdApp, launched = _get_chemdraw()
    doc = _chemdraw_open(cdApp, os.path.abspath(cdxml_path))

    # Select all, then Clean Up Reaction (Structure menu → item 7)
    # Run 3 times — arrow lengths and spacing may not fully converge
    # on the first pass.
    for i in range(3):
        doc.Objects.Select()
        time.sleep(1)
        cdApp.MenuBars(1).Menus(5).MenuItems(7).Execute()
        time.sleep(1)

    # Save to output
    doc.SaveAs(os.path.abspath(output_path))
    time.sleep(0.5)
    doc.Close(False)

    if launched:
        _restore_chemdraw_window()
        cdApp.Quit()

    log(f"ChemDraw cleanup saved to {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Polish a CDXML reaction scheme: replace non-contributing "
            "reagent structures with text abbreviations, deduplicate, "
            "and optionally run ChemDraw Clean Up Reaction."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="Input CDXML file",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output CDXML file (default: <input_stem>-polished.cdxml)",
    )
    parser.add_argument(
        "--no-chemdraw-cleanup", action="store_true",
        help="Skip the ChemDraw COM 'Clean Up Reaction' pass (still compacts)",
    )
    parser.add_argument(
        "--no-compact", action="store_true",
        help="Skip the compaction step (implies --no-chemdraw-cleanup)",
    )
    parser.add_argument(
        "--merge-conditions", action="store_true",
        help=(
            "Merge all text labels above/below the arrow into a single "
            "centered multi-line text block"
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print progress to stderr",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output result as JSON to stdout",
    )

    args = parser.parse_args(argv)

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        return 1

    # Default output path
    if args.output is None:
        stem = os.path.splitext(input_path)[0]
        output_path = stem + "-polished.cdxml"
    else:
        output_path = os.path.abspath(args.output)

    # --no-compact implies --no-chemdraw-cleanup
    do_compact = not args.no_compact
    do_chemdraw = not args.no_chemdraw_cleanup and not args.no_compact

    if not do_compact and not do_chemdraw:
        # No post-processing — write directly to output
        result = polish_scheme(input_path, output_path,
                               verbose=args.verbose,
                               merge_conditions=args.merge_conditions)
    elif do_compact and not do_chemdraw:
        # Compact only — write to output, then compact in-place
        result = polish_scheme(input_path, output_path,
                               verbose=args.verbose,
                               merge_conditions=args.merge_conditions)
        _compact_toward_arrow(output_path, args.verbose)
    else:
        # Compact + ChemDraw cleanup — write to temp, compact, cleanup
        tmpdir = tempfile.mkdtemp(prefix="scheme_polish_")
        tmp_path = os.path.join(tmpdir, "pre_cleanup.cdxml")
        try:
            result = polish_scheme(input_path, tmp_path,
                                   verbose=args.verbose,
                                   merge_conditions=args.merge_conditions)
            _compact_toward_arrow(tmp_path, args.verbose)
            _chemdraw_cleanup_reaction(tmp_path, output_path,
                                        verbose=args.verbose)
        finally:
            import shutil
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    # --- Report ---
    n_replaced = len(result["replacements"])
    n_promoted = len(result["promotions"])
    n_aligned = len(result.get("alignments", []))
    n_reformatted = len(result["reformatted"])
    n_deduped = len(result["dedup_removed"])
    parts = [
        f"{n_replaced} structure(s) → text",
        f"{n_promoted} text → structure",
        f"{n_aligned} fragment(s) aligned to product",
        f"{n_reformatted} text reformatted",
        f"{n_deduped} duplicate(s) removed",
    ]
    if result.get("merged_conditions"):
        parts.append("conditions merged into single block")
    print(f"Polished: {', '.join(parts)}", file=sys.stderr)
    print(f"Output: {output_path}", file=sys.stderr)

    if args.json:
        # Determine mode
        if not do_compact and not do_chemdraw:
            mode = "raw"
        elif do_compact and not do_chemdraw:
            mode = "compact"
        else:
            mode = "chemdraw"

        steps_applied = []
        if n_replaced:
            steps_applied.append(f"{n_replaced} structure(s) replaced with text")
        if n_promoted:
            steps_applied.append(f"{n_promoted} text promoted to structure")
        if n_aligned:
            steps_applied.append(f"{n_aligned} fragment(s) aligned to product")
        if n_reformatted:
            steps_applied.append(f"{n_reformatted} text reformatted")
        if n_deduped:
            steps_applied.append(f"{n_deduped} duplicate(s) removed")
        if result.get("merged_conditions"):
            steps_applied.append("conditions merged")
        if do_compact:
            steps_applied.append("compacted toward arrow")
        if do_chemdraw:
            steps_applied.append("ChemDraw COM cleanup")

        warnings = []
        json_result = {
            "input": str(input_path),
            "output": str(output_path),
            "mode": mode,
            "steps_applied": steps_applied,
            "warnings": warnings,
        }
        print(json.dumps(json_result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
