#!/usr/bin/env python3
"""
alignment.py -- Shared alignment functions for reaction scheme polishing.

Provides two independent product-alignment strategies:

  * **Kabsch** -- rigid-body 2D rotation computed from matched atom
    coordinates (requires ChemScript for MOL export + RDKit for MCS).
  * **RDKit MCS** -- per-bond re-depiction via
    ``GenerateDepictionMatching2DStructure`` (RDKit only, no ChemScript).

Both are consumed by ``scheme_polisher.py`` and ``scheme_polisher_v2.py``.
All geometry primitives (centroid, rotation, coordinate helpers) live here
so there is exactly one copy of each.

Layers
------
1. Geometry primitives  (stdlib only -- no RDKit / ChemScript)
2. Kabsch alignment     (ChemScript + RDKit, lazy imports)
3. RDKit MCS alignment  (RDKit only, lazy imports)
"""

import argparse
import copy
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple

from ..constants import ACS_BOND_LENGTH, CDXML_MINIMAL_HEADER
from ..cdxml_utils import write_cdxml


# ============================================================================
# LAYER 1 -- Geometry primitives  (stdlib only)
# ============================================================================

# ---------------------------------------------------------------------------
# Fragment <-> CDXML wrapping
# ---------------------------------------------------------------------------

def sp_fragment_to_cdxml(frag: ET.Element) -> str:
    """Wrap a single <fragment> element in a minimal CDXML document.

    Used to pass individual fragments to ChemScript for MOL block export.
    """
    frag_xml = ET.tostring(frag, encoding="unicode")
    lines = [
        CDXML_MINIMAL_HEADER,
        '<page id="1">',
        frag_xml,
        '</page>',
        '</CDXML>',
    ]
    return "\n".join(lines)


def filtered_atom_nodes(frag: ET.Element) -> List[ET.Element]:
    """Return only real atom <n> nodes from a fragment, filtering out
    ExternalConnectionPoint, Fragment, and Unspecified pseudo-nodes."""
    return [n for n in frag.iter("n")
            if n.get("NodeType") not in
            ("ExternalConnectionPoint", "Fragment", "Unspecified")]


# ---------------------------------------------------------------------------
# Centroid / position helpers
# ---------------------------------------------------------------------------

def fragment_centroid(frag: ET.Element) -> Tuple[float, float]:
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


def get_visible_carbon_positions(frag: ET.Element) -> List[Tuple[float, float]]:
    """Extract positions of visible carbon atoms for Kabsch alignment.

    Only uses carbon atoms (no Element attribute = carbon by CDXML convention)
    that are direct children of the fragment and are regular atoms (no
    NodeType attribute).  This excludes:
      - Heteroatoms (N, O, S, halogens -- they have Element="7", "8", etc.)
      - Abbreviation group nodes (NodeType="Fragment")
      - External connection points (NodeType="ExternalConnectionPoint")
      - Atoms inside abbreviation inner fragments

    Carbon backbone positions are the most geometrically stable reference
    points for orientation matching, unaffected by label rendering or
    abbreviation expansion.
    """
    positions = []
    for n in frag.findall("n"):  # direct children only
        if n.get("NodeType"):
            continue
        if n.get("Element"):
            continue
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                positions.append((float(parts[0]), float(parts[1])))
    return positions


# ---------------------------------------------------------------------------
# Kabsch 2D rotation
# ---------------------------------------------------------------------------

def compute_rigid_rotation_2d(
    old_pts: List[Tuple[float, float]],
    new_pts: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """Compute the optimal 2D rotation from matched point pairs (Kabsch).

    Returns (cos_a, sin_a).  Only the rotation component is computed;
    translation is discarded because we want to keep fragments in place.
    """
    n = len(old_pts)
    if n < 2:
        return (1.0, 0.0)

    ocx = sum(p[0] for p in old_pts) / n
    ocy = sum(p[1] for p in old_pts) / n
    ncx = sum(p[0] for p in new_pts) / n
    ncy = sum(p[1] for p in new_pts) / n

    s_xx = s_yy = s_xy = s_yx = 0.0
    for (ox, oy), (nx, ny) in zip(old_pts, new_pts):
        dx_o, dy_o = ox - ocx, oy - ocy
        dx_n, dy_n = nx - ncx, ny - ncy
        s_xx += dx_o * dx_n
        s_yy += dy_o * dy_n
        s_xy += dx_o * dy_n
        s_yx += dy_o * dx_n

    angle = math.atan2(s_xy - s_yx, s_xx + s_yy)
    return (math.cos(angle), math.sin(angle))


def match_and_compute_rotation(
    src_positions: List[Tuple[float, float]],
    tgt_positions: List[Tuple[float, float]],
) -> Tuple[float, float, float]:
    """Match atoms by normalized nearest-neighbor and compute Kabsch rotation.

    Finds the 1:1 correspondence between two sets of positions for the
    same molecule (e.g. before/after ChemScript cleanup), then computes
    the optimal rotation from src -> tgt orientation.

    Returns (cos_a, sin_a, angle_degrees).
    """
    n = len(src_positions)
    if n < 3 or len(tgt_positions) != n:
        return (1.0, 0.0, 0.0)

    # Center and normalize both sets so nearest-neighbor works
    # across different coordinate scales
    def _center_norm(pts):
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        centered = [(x - cx, y - cy) for x, y in pts]
        scale = max(max(abs(x), abs(y)) for x, y in centered) or 1.0
        return [(x / scale, y / scale) for x, y in centered]

    src_n = _center_norm(src_positions)
    tgt_n = _center_norm(tgt_positions)

    # Greedy nearest-neighbor matching
    used = set()
    matched_src = []
    matched_tgt = []
    for si, (sx, sy) in enumerate(src_n):
        best_ti = -1
        best_d2 = float("inf")
        for ti, (tx, ty) in enumerate(tgt_n):
            if ti in used:
                continue
            d2 = (sx - tx) ** 2 + (sy - ty) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_ti = ti
        if best_ti >= 0:
            matched_src.append(src_positions[si])
            matched_tgt.append(tgt_positions[best_ti])
            used.add(best_ti)

    if len(matched_src) < 3:
        return (1.0, 0.0, 0.0)

    # Compute Kabsch rotation from src -> tgt
    cos_a, sin_a = compute_rigid_rotation_2d(matched_src, matched_tgt)
    angle_deg = math.degrees(math.atan2(sin_a, cos_a))
    return (cos_a, sin_a, angle_deg)


# ---------------------------------------------------------------------------
# In-place coordinate rotation
# ---------------------------------------------------------------------------

def rotate_fragment_in_place(
    frag: ET.Element,
    cos_a: float, sin_a: float,
    cx: float, cy: float,
) -> None:
    """Rotate all coordinates in a fragment around (cx, cy).

    Updates all descendant <n> positions, <t> label positions and
    BoundingBoxes, fragment-level BoundingBox, and inner-fragment
    BoundingBoxes (abbreviation groups) -- all in-place.
    """
    def rot(x: float, y: float) -> Tuple[float, float]:
        dx, dy = x - cx, y - cy
        return (cos_a * dx - sin_a * dy + cx,
                sin_a * dx + cos_a * dy + cy)

    def rotate_bb(bb_str: str) -> str:
        vals = [float(v) for v in bb_str.split()]
        if len(vals) < 4:
            return bb_str
        corners = [(vals[0], vals[1]), (vals[2], vals[1]),
                    (vals[0], vals[3]), (vals[2], vals[3])]
        rotated = [rot(x, y) for x, y in corners]
        return (f"{min(r[0] for r in rotated):.2f} "
                f"{min(r[1] for r in rotated):.2f} "
                f"{max(r[0] for r in rotated):.2f} "
                f"{max(r[1] for r in rotated):.2f}")

    # Rotate all node positions (all descendants)
    for n in frag.iter("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                nx, ny = rot(float(parts[0]), float(parts[1]))
                n.set("p", f"{nx:.2f} {ny:.2f}")

    # Rotate text labels
    for t in frag.iter("t"):
        p = t.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                nx, ny = rot(float(parts[0]), float(parts[1]))
                t.set("p", f"{nx:.2f} {ny:.2f}")
        bb = t.get("BoundingBox")
        if bb:
            t.set("BoundingBox", rotate_bb(bb))

    # Fragment-level BoundingBox
    fb = frag.get("BoundingBox")
    if fb:
        frag.set("BoundingBox", rotate_bb(fb))

    # Inner fragment BoundingBoxes (abbreviation groups)
    for inner in frag.iter("fragment"):
        if inner is not frag:
            ib = inner.get("BoundingBox")
            if ib:
                inner.set("BoundingBox", rotate_bb(ib))


# ---------------------------------------------------------------------------
# Abbreviation dummy copy
# ---------------------------------------------------------------------------

def make_abbrev_dummy_copy(frag: ET.Element) -> ET.Element:
    """Create a deep copy of a fragment with abbreviation nodes replaced by
    dummy atoms (Iodine, Element=53).

    This ensures that ChemScript MOL export and ``filtered_atom_nodes``
    see exactly the same atoms -- abbreviation inner fragments are stripped
    so their child atoms don't pollute the MOL-to-CDXML mapping.  The
    dummy atom preserves the abbreviation node's position.
    """
    work = copy.deepcopy(frag)
    for n in work.findall("n"):
        if n.get("NodeType") != "Fragment":
            continue
        # Strip inner fragment children + label
        for child in list(n):
            n.remove(child)
        for attr in ("NodeType", "LabelDisplay", "NeedsClean",
                     "AS", "Warning"):
            if attr in n.attrib:
                del n.attrib[attr]
        n.set("Element", "53")        # Iodine dummy
        n.set("NumHydrogens", "0")
    return work


# ---------------------------------------------------------------------------
# Coordinate translation
# ---------------------------------------------------------------------------

def translate_subtree(elem: ET.Element, dx: float, dy: float) -> None:
    """Recursively shift all p and BoundingBox attributes by (dx, dy)."""
    p = elem.get("p")
    if p:
        parts = p.split()
        if len(parts) >= 2:
            elem.set("p",
                      f"{float(parts[0])+dx:.2f} {float(parts[1])+dy:.2f}")

    bb = elem.get("BoundingBox")
    if bb:
        parts = bb.split()
        if len(parts) == 4:
            elem.set("BoundingBox",
                      f"{float(parts[0])+dx:.2f} {float(parts[1])+dy:.2f} "
                      f"{float(parts[2])+dx:.2f} {float(parts[3])+dy:.2f}")

    for child in elem:
        translate_subtree(child, dx, dy)


# ============================================================================
# LAYER 2 -- Kabsch product alignment  (ChemScript + RDKit, lazy imports)
# ============================================================================

def kabsch_align_fragment_to_product(
    reagent_frag: ET.Element,
    product_frag: ET.Element,
    cs_bridge,
    verbose: bool = False,
) -> bool:
    """Align a reagent fragment's orientation to match its substructure in
    the product using rigid-body Kabsch rotation.

    Strategy:
      1. Create work copies with abbreviations replaced by dummy atoms
         (Iodine) so that ChemScript MOL export and the CDXML atom list
         have identical atom counts and consistent coordinates.
      2. Export both work copies to MOL blocks (via ChemScript) for RDKit.
      3. Find the atom correspondence via substructure match or MCS.
      4. Use the matched atom indices to pair up CDXML coordinates
         (both already in the same y-down coordinate system).
      5. Compute the optimal rigid rotation via Kabsch.
      6. Apply the rotation in-place to the **original** reagent fragment
         (including abbreviation inner fragments).

    Returns True on success, False on failure.
    """
    def log(msg: str):
        if verbose:
            print(f"[alignment] {msg}", file=sys.stderr)

    try:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS
    except ImportError:
        log("    RDKit not available, skipping Kabsch alignment")
        return False

    label = f"frag {reagent_frag.get('id', '?')}"

    # --- Create work copies with abbreviations replaced by dummies ---
    reagent_work = make_abbrev_dummy_copy(reagent_frag)
    product_work = make_abbrev_dummy_copy(product_frag)

    # --- Get MOL blocks from ChemScript ---
    reagent_cdxml = sp_fragment_to_cdxml(reagent_work)
    product_cdxml = sp_fragment_to_cdxml(product_work)

    r_tmp = p_tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".cdxml", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(reagent_cdxml)
            r_tmp = f.name
        with tempfile.NamedTemporaryFile(
            suffix=".cdxml", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(product_cdxml)
            p_tmp = f.name

        try:
            r_mol_block = cs_bridge.write_data(r_tmp, "chemical/x-mdl-molfile")
            p_mol_block = cs_bridge.write_data(p_tmp, "chemical/x-mdl-molfile")
        except Exception as exc:
            log(f"    {label}: ChemScript MOL export failed: {exc}")
            return False
    finally:
        for tmp in (r_tmp, p_tmp):
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    # --- Parse in RDKit ---
    reagent_mol = Chem.MolFromMolBlock(r_mol_block, sanitize=False)
    if reagent_mol:
        try:
            Chem.SanitizeMol(reagent_mol)
        except Exception:
            Chem.SanitizeMol(
                reagent_mol,
                Chem.SanitizeFlags.SANITIZE_ALL
                ^ Chem.SanitizeFlags.SANITIZE_KEKULIZE,
            )
    product_mol = Chem.MolFromMolBlock(p_mol_block, sanitize=False)
    if product_mol:
        try:
            Chem.SanitizeMol(
                product_mol,
                Chem.SanitizeFlags.SANITIZE_ALL
                ^ Chem.SanitizeFlags.SANITIZE_KEKULIZE,
            )
        except Exception:
            pass

    if reagent_mol is None or product_mol is None:
        log(f"    {label}: RDKit couldn't parse MOL blocks")
        return False

    # --- Build MOL-to-CDXML index mapping ---
    # ChemScript may reorder atoms when exporting to MOL block, so
    # RDKit atom indices may not correspond to CDXML <n> iteration order.
    # We build the mapping by matching MOL block coordinates (y-up) to
    # CDXML node coordinates (y-down, in points) via nearest-neighbor.
    # Use work copies (abbreviations replaced with dummies) so that the
    # CDXML atom list matches the MOL block atom list exactly.
    r_real = filtered_atom_nodes(reagent_work)
    p_real = filtered_atom_nodes(product_work)

    def _build_mol_to_cdxml_map(mol, cdxml_nodes):
        """Map MOL block atom index -> CDXML filtered-node index by
        matching coordinates. MOL coords are in Angstroms (y-up),
        CDXML coords are in points (y-down). We normalise by
        centering both sets and matching by relative position."""
        n = mol.GetNumAtoms()
        if n != len(cdxml_nodes):
            return None

        # MOL positions (y-up)
        conf = mol.GetConformer()
        mol_pts = []
        for i in range(n):
            pos = conf.GetAtomPosition(i)
            mol_pts.append((pos.x, -pos.y))  # flip y to y-down

        # CDXML positions (already y-down)
        cdxml_pts = []
        for node in cdxml_nodes:
            p = node.get("p", "")
            if p:
                parts = p.split()
                cdxml_pts.append((float(parts[0]), float(parts[1])))
            else:
                cdxml_pts.append((0.0, 0.0))

        # Center and normalise both to unit scale so nearest-neighbour
        # works across the Angstrom (MOL) / point (CDXML) scale gap.
        def _center_and_normalise(pts):
            cx = sum(p[0] for p in pts) / n
            cy = sum(p[1] for p in pts) / n
            centred = [(x - cx, y - cy) for x, y in pts]
            scale = max(max(abs(x), abs(y)) for x, y in centred) or 1.0
            return [(x / scale, y / scale) for x, y in centred]

        mol_n = _center_and_normalise(mol_pts)
        cdxml_n = _center_and_normalise(cdxml_pts)

        # Greedy nearest-neighbour matching
        used = set()
        mapping = {}  # mol_idx -> cdxml_idx
        for mi, (mx, my) in enumerate(mol_n):
            best_ci = -1
            best_d2 = float("inf")
            for ci, (cx, cy) in enumerate(cdxml_n):
                if ci in used:
                    continue
                d2 = (mx - cx) ** 2 + (my - cy) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best_ci = ci
            if best_ci >= 0:
                mapping[mi] = best_ci
                used.add(best_ci)
        return mapping if len(mapping) == n else None

    r_mol_to_cdxml = _build_mol_to_cdxml_map(reagent_mol, r_real)
    p_mol_to_cdxml = _build_mol_to_cdxml_map(product_mol, p_real)

    if r_mol_to_cdxml is None or p_mol_to_cdxml is None:
        log(f"    {label}: couldn't build MOL-to-CDXML atom mapping")
        return False

    # --- Find atom correspondence via RDKit ---
    r_match = None  # reagent MOL indices in the match
    p_match = None  # product MOL indices in the match

    if product_mol.HasSubstructMatch(reagent_mol):
        p_match_tuple = product_mol.GetSubstructMatch(reagent_mol)
        r_match = tuple(range(reagent_mol.GetNumAtoms()))
        p_match = p_match_tuple
        log(f"    {label}: full substructure match ({len(r_match)} atoms)")
    else:
        log(f"    {label}: no full substructure match, trying MCS...")
        mcs = rdFMCS.FindMCS(
            [reagent_mol, product_mol],
            threshold=1.0,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            timeout=5,
        )
        if mcs.canceled or mcs.numAtoms < 3:
            log(f"    {label}: MCS too small ({mcs.numAtoms} atoms), skipping")
            return False

        mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
        if mcs_mol is None:
            log(f"    {label}: couldn't parse MCS SMARTS, skipping")
            return False

        r_match = reagent_mol.GetSubstructMatch(mcs_mol)
        p_match = product_mol.GetSubstructMatch(mcs_mol)
        if not r_match or not p_match:
            log(f"    {label}: MCS match failed, skipping")
            return False
        log(f"    {label}: using MCS ({mcs.numAtoms} atoms) for alignment")

    # --- Build matched coordinate pairs from CDXML (y-down) ---
    def _node_pos(nodes, idx):
        p = nodes[idx].get("p", "")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                return (float(parts[0]), float(parts[1]))
        return None

    reagent_pts = []
    product_pts = []
    for r_mol_idx, p_mol_idx in zip(r_match, p_match):
        # Translate MOL indices to CDXML indices
        r_cdxml_idx = r_mol_to_cdxml.get(r_mol_idx)
        p_cdxml_idx = p_mol_to_cdxml.get(p_mol_idx)
        if r_cdxml_idx is None or p_cdxml_idx is None:
            continue
        rp = _node_pos(r_real, r_cdxml_idx)
        pp = _node_pos(p_real, p_cdxml_idx)
        if rp and pp:
            # Weight heteroatoms (non-carbon) 3x so they dominate the
            # rotation for symmetric rings like morpholine, where the
            # 4 near-equivalent carbons can outvote 2 heteroatoms and
            # produce a wrong Kabsch solution.
            is_hetero = r_real[r_cdxml_idx].get("Element", "") not in ("", "C")
            copies = 3 if is_hetero else 1
            for _ in range(copies):
                reagent_pts.append(rp)
                product_pts.append(pp)

    if len(reagent_pts) < 3:
        log(f"    {label}: too few matched points ({len(reagent_pts)}), skipping")
        return False

    # --- Compute rotation via Kabsch ---
    cos_a, sin_a = compute_rigid_rotation_2d(reagent_pts, product_pts)
    angle_deg = math.degrees(math.atan2(sin_a, cos_a))

    if abs(angle_deg) < 5.0:
        log(f"    {label}: rotation {angle_deg:.1f} deg < 5 deg, already aligned")
        return False

    # --- Apply rotation around reagent centroid ---
    all_r_pts = []
    for n in r_real:
        rp = n.get("p", "")
        if rp:
            parts = rp.split()
            if len(parts) >= 2:
                all_r_pts.append((float(parts[0]), float(parts[1])))
    cx = sum(p[0] for p in all_r_pts) / len(all_r_pts)
    cy = sum(p[1] for p in all_r_pts) / len(all_r_pts)

    rotate_fragment_in_place(reagent_frag, cos_a, sin_a, cx, cy)
    log(f"    {label}: rotated {angle_deg:.1f} deg around "
        f"({cx:.1f}, {cy:.1f})")
    return True


def kabsch_align_to_product(
    root: ET.Element,
    cs_bridge=None,
    verbose: bool = False,
    frag_ids: Optional[Set[str]] = None,
) -> List[str]:
    """Align fragments to product orientation using Kabsch rigid rotation.

    Reads ``<scheme><step>`` metadata to identify the product.  For each
    eligible non-product fragment, computes a rigid 2D rotation via MCS
    + Kabsch and applies it in-place.

    Parameters
    ----------
    root : ET.Element
        Parsed CDXML root element (modified in-place).
    cs_bridge : ChemScriptBridge or None
        If supplied, reuses an already-open bridge (avoids spinning up a
        second subprocess).  If *None*, creates and closes its own.
    verbose : bool
        Print progress to stderr.
    frag_ids : set of str or None
        Restrict alignment to these fragment IDs.  If *None*, all
        non-product fragments in the step are eligible.

    Returns
    -------
    list of str
        IDs of fragments that were actually rotated.
    """
    def log(msg: str):
        if verbose:
            print(f"[alignment] {msg}", file=sys.stderr)

    page = root.find("page")
    if page is None:
        return []

    # Build fragment lookup
    id_to_el: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    # Parse <scheme><step> metadata
    steps = root.findall(".//step")
    if not steps:
        log("No reaction steps found, skipping Kabsch alignment")
        return []

    # Use first step
    step = steps[0]
    product_ids = set(step.get("ReactionStepProducts", "").split())
    reactant_ids = set(step.get("ReactionStepReactants", "").split())
    above_ids = set(step.get("ReactionStepObjectsAboveArrow", "").split())
    below_ids = set(step.get("ReactionStepObjectsBelowArrow", "").split())

    # Find the product fragment
    product_frag = None
    for pid in product_ids:
        el = id_to_el.get(pid)
        if el is not None and el.tag == "fragment":
            product_frag = el
            break

    if product_frag is None:
        log("No product fragment found, skipping Kabsch alignment")
        return []

    # Determine which fragments to align
    if frag_ids is not None:
        eligible = frag_ids - product_ids
    else:
        # All non-product fragments in the step
        all_step_ids = (reactant_ids | above_ids | below_ids) - product_ids
        eligible = {fid for fid in all_step_ids
                    if fid in id_to_el and id_to_el[fid].tag == "fragment"}

    if not eligible:
        log("No eligible fragments to align")
        return []

    log(f"Kabsch aligning {len(eligible)} fragment(s) to product...")

    # Ensure ChemScript bridge
    owns_bridge = cs_bridge is None
    if owns_bridge:
        try:
            from ..chemdraw.chemscript_bridge import ChemScriptBridge
            cs_bridge = ChemScriptBridge()
        except Exception as exc:
            log(f"WARNING: ChemScript unavailable ({exc}), "
                f"skipping Kabsch alignment")
            return []

    aligned = []
    try:
        for fid in sorted(eligible):
            frag_el = id_to_el.get(fid)
            if frag_el is None:
                continue
            try:
                success = kabsch_align_fragment_to_product(
                    frag_el, product_frag, cs_bridge, verbose)
                if success:
                    aligned.append(fid)
            except Exception as exc:
                log(f"  Fragment {fid}: alignment error: {exc}")
    finally:
        if owns_bridge and cs_bridge is not None:
            try:
                cs_bridge.close()
            except Exception:
                pass

    log(f"Kabsch aligned {len(aligned)} fragment(s)")
    return aligned


# ============================================================================
# LAYER 3 -- RDKit MCS alignment  (RDKit only, lazy imports)
# ============================================================================

_HAS_RDKIT: Optional[bool] = None  # lazy detection


def _check_rdkit() -> bool:
    """Check if RDKit is available. Caches result."""
    global _HAS_RDKIT
    if _HAS_RDKIT is None:
        try:
            from rdkit import Chem  # noqa: F401
            _HAS_RDKIT = True
        except ImportError:
            _HAS_RDKIT = False
    return _HAS_RDKIT


def _frag_to_mol(frag_elem: ET.Element):
    """Convert a CDXML <fragment> to an RDKit Mol with atom metadata.

    Returns (mol, atoms_data) where atoms_data is a list of dicts with
    keys: id, idx, x, y, elem, num_h, is_abbrev, xml.

    Abbreviation groups (NodeType="Fragment") become dummy atoms (element 0)
    so they participate in connectivity but not MCS element matching.

    Returns (None, None) if conversion fails.
    """
    from rdkit import Chem

    atoms: List[dict] = []
    id_map: Dict[int, int] = {}

    for n in frag_elem.findall("n"):
        nid = int(n.get("id"))
        if n.get("NodeType") == "ExternalConnectionPoint":
            continue

        px, py = [float(v) for v in n.get("p", "0 0").split()]
        elem = int(n.get("Element", "6"))
        num_h_attr = n.get("NumHydrogens")
        num_h = int(num_h_attr) if num_h_attr is not None else None
        is_abbrev = n.get("NodeType") == "Fragment"

        idx = len(atoms)
        id_map[nid] = idx
        atoms.append({
            "id": nid, "idx": idx,
            "x": px, "y": py,
            "elem": elem, "num_h": num_h,
            "is_abbrev": is_abbrev,
            "xml": n,
        })

    bonds = []
    for b in frag_elem.findall("b"):
        bi, ei = int(b.get("B")), int(b.get("E"))
        if bi in id_map and ei in id_map:
            bonds.append((id_map[bi], id_map[ei], int(b.get("Order", "1"))))

    em = Chem.RWMol()
    for a in atoms:
        ra = Chem.Atom(0 if a["is_abbrev"] else a["elem"])
        if a["num_h"] is not None:
            ra.SetNoImplicit(True)
            ra.SetNumExplicitHs(a["num_h"])
        em.AddAtom(ra)

    BT = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE,
          3: Chem.BondType.TRIPLE}
    for bi, ei, order in bonds:
        em.AddBond(bi, ei, BT.get(order, Chem.BondType.SINGLE))

    mol = em.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        try:
            Chem.SanitizeMol(
                mol,
                Chem.SanitizeFlags.SANITIZE_ALL
                ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES,
            )
        except Exception:
            pass

    return mol, atoms


_rdk_bl_cache: Optional[float] = None


def _rdkit_default_bond_length() -> float:
    """RDKit's default 2D depiction bond length (cached)."""
    global _rdk_bl_cache
    if _rdk_bl_cache is None:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        m = Chem.MolFromSmiles("CC")
        AllChem.Compute2DCoords(m)
        c = m.GetConformer()
        p0, p1 = c.GetAtomPosition(0), c.GetAtomPosition(1)
        _rdk_bl_cache = math.sqrt(
            (p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2)
    return _rdk_bl_cache


def _avg_bond_length_from_atoms(atoms_data: List[dict], mol) -> float:
    """Average bond length computed from CDXML atom coordinates."""
    total, count = 0.0, 0
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        dx = atoms_data[i]["x"] - atoms_data[j]["x"]
        dy = atoms_data[i]["y"] - atoms_data[j]["y"]
        total += math.sqrt(dx * dx + dy * dy)
        count += 1
    return total / count if count else ACS_BOND_LENGTH


def _set_cdxml_conformer(mol, atoms_data: List[dict], scale: float = 1.0):
    """Set conformer from CDXML coordinates (y-flipped, scaled to RDKit space).

    CDXML y-axis points down; RDKit y-axis points up. The scale factor
    converts from CDXML points (~14.40 pt bond length) to RDKit units
    (~1.5 unit bond length).
    """
    from rdkit import Chem
    from rdkit.Geometry import Point3D

    conf = Chem.Conformer(mol.GetNumAtoms())
    for a in atoms_data:
        conf.SetAtomPosition(
            a["idx"], Point3D(a["x"] * scale, -a["y"] * scale, 0.0))
    mol.RemoveAllConformers()
    mol.AddConformer(conf, assignId=True)


def _find_mcs_match(ref_mol, target_mol, timeout: int = 30):
    """Find MCS between ref and target molecules.

    Returns atom_map as list of (ref_idx, tgt_idx) tuples,
    or (None, 0) if MCS has fewer than 3 atoms.
    """
    from rdkit import Chem
    from rdkit.Chem import rdFMCS

    mcs = rdFMCS.FindMCS(
        [ref_mol, target_mol],
        timeout=timeout,
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareOrder,
        ringMatchesRingOnly=True,
        completeRingsOnly=True,
    )

    if mcs.numAtoms < 3:
        return None, 0

    core = Chem.MolFromSmarts(mcs.smartsString)
    if core is None:
        return None, 0

    ref_match = ref_mol.GetSubstructMatch(core)
    target_match = target_mol.GetSubstructMatch(core)
    if not ref_match or not target_match:
        return None, 0

    return list(zip(ref_match, target_match)), mcs.numAtoms


def _rdkit_align_and_write(
    frag_elem: ET.Element,
    ref_mol,
    tgt_mol,
    tgt_atoms: List[dict],
    atom_map: list,
    scale: float,
    original_center: Tuple[float, float],
) -> float:
    """Align target mol to reference using GenerateDepictionMatching2DStructure,
    then write aligned coordinates back to the CDXML fragment.

    Parameters
    ----------
    frag_elem : ET.Element
        The CDXML <fragment> element to update (modified in-place).
    ref_mol : RDKit Mol
        Reference molecule (product) with conformer set at RDKit scale.
    tgt_mol : RDKit Mol
        Target molecule (reactant/reagent) -- conformer will be generated.
    tgt_atoms : list of dict
        Atom metadata from _frag_to_mol (includes 'xml' references).
    atom_map : list of (ref_idx, tgt_idx) tuples
        MCS atom correspondence.
    scale : float
        CDXML-to-RDKit scale factor (rdk_bl / cdxml_bl).
    original_center : (float, float)
        Original fragment centroid in CDXML space (for center preservation).

    Returns
    -------
    float
        RMSD of MCS atoms after alignment (should be ~0).
    """
    from rdkit.Chem import rdDepictor

    # Align: generates new 2D depiction for tgt_mol with MCS atoms
    # constrained to match ref_mol's positions
    rdDepictor.GenerateDepictionMatching2DStructure(
        tgt_mol, ref_mol, atom_map)

    # Compute RMSD for validation
    rc = ref_mol.GetConformer()
    tc = tgt_mol.GetConformer()
    ss = sum(
        (rc.GetAtomPosition(ri).x - tc.GetAtomPosition(ti).x) ** 2 +
        (rc.GetAtomPosition(ri).y - tc.GetAtomPosition(ti).y) ** 2
        for ri, ti in atom_map)
    rmsd = math.sqrt(ss / len(atom_map)) if atom_map else 0.0

    # Convert aligned RDKit coords back to CDXML space
    conf = tgt_mol.GetConformer()
    inv = 1.0 / scale

    aligned = []
    for a in tgt_atoms:
        pos = conf.GetAtomPosition(a["idx"])
        aligned.append((pos.x * inv, -pos.y * inv))  # scale back + flip y

    # Translate to preserve original fragment center
    acx = sum(p[0] for p in aligned) / len(aligned)
    acy = sum(p[1] for p in aligned) / len(aligned)
    gdx = original_center[0] - acx
    gdy = original_center[1] - acy

    for i, a in enumerate(tgt_atoms):
        new_x = aligned[i][0] + gdx
        new_y = aligned[i][1] + gdy
        adx = new_x - a["x"]
        ady = new_y - a["y"]

        node = a["xml"]
        node.set("p", f"{new_x:.2f} {new_y:.2f}")

        # Shift all child elements (labels, inner fragments) by atom offset
        for child in node:
            translate_subtree(child, adx, ady)

    # Recompute fragment BoundingBox from atom positions
    xs, ys = [], []
    for n in frag_elem.findall("n"):
        if n.get("NodeType") == "ExternalConnectionPoint":
            continue
        p = n.get("p")
        if p:
            parts = p.split()
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
    if xs and ys:
        margin = 15.0
        frag_elem.set(
            "BoundingBox",
            f"{min(xs)-margin:.2f} {min(ys)-margin:.2f} "
            f"{max(xs)+margin:.2f} {max(ys)+margin:.2f}")

    return rmsd


def align_product_to_reference(
    root: ET.Element,
    ref_cdxml_path: str,
    verbose: bool = False,
    timeout: int = 30,
) -> bool:
    """Align the product fragment to the best-matching structure in a
    reference CDXML file.

    The reference file should contain one or more "known good" structures
    drawn with the desired orientation (e.g. from a group meeting slide).
    The product is matched to whichever reference structure has the largest
    MCS overlap, then aligned via GenerateDepictionMatching2DStructure.

    Call this BEFORE rdkit_align_to_product() so that reactant alignment
    uses the correctly-oriented product as its reference.

    Parameters
    ----------
    root : ET.Element
        Parsed CDXML root element (modified in-place).
    ref_cdxml_path : str
        Path to reference CDXML with known-good structure(s).
    verbose : bool
        Print progress to stderr.
    timeout : int
        MCS timeout in seconds per comparison (default 30).

    Returns
    -------
    bool
        True if the product was successfully aligned.
    """
    if not _check_rdkit():
        if verbose:
            print("[alignment] RDKit not available, skipping reference alignment",
                  file=sys.stderr)
        return False

    def log(msg):
        if verbose:
            print(f"[alignment] {msg}", file=sys.stderr)

    page = root.find("page")
    if page is None:
        return False

    # Build fragment lookup
    fragments = {}
    for f in page.findall("fragment"):
        fid = f.get("id")
        if fid:
            fragments[fid] = f

    # Find the product from reaction step metadata
    steps = root.findall(".//step")
    if not steps:
        log("No reaction steps found")
        return False

    step = steps[0]
    product_ids = step.get("ReactionStepProducts", "").split()
    prod_frag = None
    prod_id = None
    for pid in product_ids:
        if pid in fragments:
            prod_frag = fragments[pid]
            prod_id = pid
            break

    if prod_frag is None:
        log("No product fragment found")
        return False

    # Convert product to RDKit mol
    prod_result = _frag_to_mol(prod_frag)
    if prod_result is None or prod_result[0] is None:
        log("Product fragment conversion failed")
        return False
    prod_mol, prod_atoms = prod_result
    if prod_mol.GetNumAtoms() < 3:
        log("Product too small for reference alignment")
        return False

    # Parse reference CDXML file (sanitize control chars — Findmolecule
    # embeds binary "Molecule ID" values with \x01, \x12 etc. that are
    # illegal in XML)
    import re as _re
    with open(ref_cdxml_path, "r", encoding="utf-8", errors="replace") as _f:
        raw = _f.read()
    raw = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    ref_root = ET.fromstring(raw)
    ref_page = ref_root.find(".//page")
    if ref_page is None:
        log("No page in reference CDXML")
        return False

    # Extract reference fragments as RDKit mols
    ref_entries = []
    for rf in ref_page.findall("fragment"):
        rf_result = _frag_to_mol(rf)
        if rf_result is None or rf_result[0] is None:
            continue
        rf_mol, rf_atoms = rf_result
        if rf_mol.GetNumAtoms() < 3:
            continue
        ref_entries.append((rf, rf_mol, rf_atoms))

    if not ref_entries:
        log("No usable fragments in reference CDXML")
        return False

    log(f"Reference file: {len(ref_entries)} fragment(s)")

    # Find best-matching reference by MCS size
    best_ref = None
    best_map = None
    best_n_mcs = 0

    for rf_elem, rf_mol, rf_atoms in ref_entries:
        atom_map, n_mcs = _find_mcs_match(rf_mol, prod_mol, timeout)
        rf_id = rf_elem.get("id", "?")
        if atom_map is not None and n_mcs > best_n_mcs:
            best_n_mcs = n_mcs
            best_map = atom_map
            best_ref = (rf_elem, rf_mol, rf_atoms)
            log(f"  Ref fragment {rf_id}: MCS = {n_mcs} atoms (new best)")
        else:
            log(f"  Ref fragment {rf_id}: MCS = {n_mcs} atoms")

    if best_ref is None:
        log("No reference with MCS >= 3 atoms")
        return False

    rf_elem, rf_mol, rf_atoms = best_ref

    # Set reference conformer at RDKit scale (preserving its drawn orientation)
    rf_bl = _avg_bond_length_from_atoms(rf_atoms, rf_mol)
    rdk_bl = _rdkit_default_bond_length()
    rf_scale = rdk_bl / rf_bl
    _set_cdxml_conformer(rf_mol, rf_atoms, rf_scale)

    # Product centroid for center preservation
    n_prod = len(prod_atoms)
    original_center = (
        sum(a["x"] for a in prod_atoms) / n_prod,
        sum(a["y"] for a in prod_atoms) / n_prod,
    )

    # Scale for writeback: after alignment, coords are at RDKit scale
    # (bond lengths ~ rdk_bl). Convert to ACS standard (14.40 pt).
    write_scale = rdk_bl / ACS_BOND_LENGTH

    # Align product to reference and write back
    rmsd = _rdkit_align_and_write(
        prod_frag, rf_mol, prod_mol, prod_atoms,
        best_map, write_scale, original_center)

    rf_id = rf_elem.get("id", "?")
    log(f"Product {prod_id} aligned to reference fragment {rf_id} "
        f"(MCS {best_n_mcs} atoms, RMSD {rmsd:.4f})")
    return True


def rdkit_align_to_product(
    root: ET.Element,
    verbose: bool = False,
    timeout: int = 30,
) -> int:
    """Align all non-product fragments to the product's orientation.

    Uses RDKit MCS + GenerateDepictionMatching2DStructure to align each
    reactant/reagent fragment to match the product's drawn orientation.
    Reads <scheme>/<step> metadata to identify roles.

    Modifies CDXML coordinates in-place.

    Returns the number of fragments successfully aligned.
    """
    if not _check_rdkit():
        if verbose:
            print("[alignment] RDKit not available, skipping RDKit alignment",
                  file=sys.stderr)
        return 0

    page = root.find("page")
    if page is None:
        return 0

    # Build fragment lookup (id string -> element)
    fragments: Dict[str, ET.Element] = {}
    for f in page.findall("fragment"):
        fid = f.get("id")
        if fid:
            fragments[fid] = f

    # Parse reaction steps
    steps = []
    for s in root.findall(".//step"):
        def _ids(attr_name):
            return [x for x in s.get(attr_name, "").split() if x]
        steps.append({
            "reactants": _ids("ReactionStepReactants"),
            "products":  _ids("ReactionStepProducts"),
            "above":     _ids("ReactionStepObjectsAboveArrow"),
            "below":     _ids("ReactionStepObjectsBelowArrow"),
        })

    if not steps:
        if verbose:
            print("[alignment] No reaction steps found, skipping RDKit alignment",
                  file=sys.stderr)
        return 0

    aligned_count = 0

    for si, step in enumerate(steps):
        if not step["products"]:
            continue

        # Product = reference for this step
        prod_id = step["products"][0]
        if prod_id not in fragments:
            continue

        prod_mol, prod_atoms = _frag_to_mol(fragments[prod_id])
        if prod_mol is None or prod_mol.GetNumAtoms() < 2:
            continue

        # Compute scale: CDXML bond length -> RDKit bond length
        cdxml_bl = _avg_bond_length_from_atoms(prod_atoms, prod_mol)
        rdk_bl = _rdkit_default_bond_length()
        scale = rdk_bl / cdxml_bl

        # Set product conformer at RDKit scale (the reference orientation)
        _set_cdxml_conformer(prod_mol, prod_atoms, scale)

        if verbose:
            print(f"[alignment] Step {si+1}: product = fragment {prod_id} "
                  f"({prod_mol.GetNumAtoms()} atoms, "
                  f"bond length {cdxml_bl:.1f} pts)",
                  file=sys.stderr)

        # Collect all other fragment IDs in this step
        other_ids = []
        for fid in (step["reactants"] + step["above"] + step["below"]):
            if fid in fragments and fid != prod_id and fid not in other_ids:
                other_ids.append(fid)

        for fid in other_ids:
            frag_elem = fragments[fid]
            frag_mol, frag_atoms = _frag_to_mol(frag_elem)
            if frag_mol is None or frag_mol.GetNumAtoms() < 2:
                continue

            # Original centroid for center preservation
            n_atoms = len(frag_atoms)
            original_center = (
                sum(a["x"] for a in frag_atoms) / n_atoms,
                sum(a["y"] for a in frag_atoms) / n_atoms,
            )

            # Find MCS with product
            atom_map, n_mcs = _find_mcs_match(
                prod_mol, frag_mol, timeout)
            if atom_map is None:
                if verbose:
                    print(f"[alignment]   Fragment {fid}: MCS < 3 atoms, "
                          f"skipping RDKit alignment",
                          file=sys.stderr)
                continue

            # Align and write back
            rmsd = _rdkit_align_and_write(
                frag_elem, prod_mol, frag_mol, frag_atoms,
                atom_map, scale, original_center)

            aligned_count += 1
            if verbose:
                print(f"[alignment]   Fragment {fid}: aligned to product "
                      f"(MCS {n_mcs} atoms, RMSD {rmsd:.4f})",
                      file=sys.stderr)

    return aligned_count


# ============================================================================
# LAYER 4 -- RXNMapper-based alignment  (RDKit + rxn-experiments subprocess)
# ============================================================================

def rxnmapper_align_to_product(
    root: ET.Element,
    verbose: bool = False,
    timeout: int = 120,
) -> int:
    """Align non-product fragments using RXNMapper atom maps.

    Like rdkit_align_to_product(), but uses transformer-based atom mapping
    instead of RDKit MCS to find atom correspondence.  RXNMapper understands
    reaction chemistry, so the atom correspondence reflects actual bond
    formation/breaking rather than purely structural overlap.

    Falls back to MCS alignment for fragments where RXNMapper fails
    (e.g. if the fragment isn't in the mapped output).

    Modifies CDXML coordinates in-place.
    Returns the number of fragments successfully aligned.
    """
    if not _check_rdkit():
        if verbose:
            print("[alignment] RDKit not available, skipping RXNMapper alignment",
                  file=sys.stderr)
        return 0

    from rdkit import Chem

    def log(msg):
        if verbose:
            print(f"[alignment] {msg}", file=sys.stderr)

    page = root.find("page")
    if page is None:
        return 0

    # Build fragment lookup
    fragments: Dict[str, ET.Element] = {}
    for f in page.findall("fragment"):
        fid = f.get("id")
        if fid:
            fragments[fid] = f

    # Parse reaction steps
    steps = []
    for s in root.findall(".//step"):
        def _ids(attr_name):
            return [x for x in s.get(attr_name, "").split() if x]
        steps.append({
            "reactants": _ids("ReactionStepReactants"),
            "products":  _ids("ReactionStepProducts"),
            "above":     _ids("ReactionStepObjectsAboveArrow"),
            "below":     _ids("ReactionStepObjectsBelowArrow"),
        })

    if not steps:
        log("No reaction steps found")
        return 0

    aligned_count = 0

    for si, step in enumerate(steps):
        if not step["products"]:
            continue

        prod_id = step["products"][0]
        if prod_id not in fragments:
            continue

        prod_result = _frag_to_mol(fragments[prod_id])
        if prod_result is None:
            continue
        prod_mol, prod_atoms = prod_result
        if prod_mol is None or prod_mol.GetNumAtoms() < 2:
            continue

        # Compute scale
        cdxml_bl = _avg_bond_length_from_atoms(prod_atoms, prod_mol)
        rdk_bl = _rdkit_default_bond_length()
        scale = rdk_bl / cdxml_bl

        # Set product conformer at RDKit scale
        _set_cdxml_conformer(prod_mol, prod_atoms, scale)

        # Get product SMILES
        prod_smi = Chem.MolToSmiles(prod_mol)

        log(f"Step {si+1}: product = fragment {prod_id} "
            f"({prod_mol.GetNumAtoms()} atoms, SMILES={prod_smi[:50]})")

        # Collect all other fragment IDs in this step
        other_ids = []
        for fid in (step["reactants"] + step["above"] + step["below"]):
            if fid in fragments and fid != prod_id and fid not in other_ids:
                other_ids.append(fid)

        # Convert all fragments to mols + SMILES
        frag_data = {}  # fid -> (mol, atoms, smiles)
        for fid in other_ids:
            frag_result = _frag_to_mol(fragments[fid])
            if frag_result is None:
                continue
            frag_mol, frag_atoms = frag_result
            if frag_mol is None or frag_mol.GetNumAtoms() < 2:
                continue
            frag_smi = Chem.MolToSmiles(frag_mol)
            if not frag_smi or "*" in frag_smi:
                # Skip fragments with dummy atoms (abbreviation groups)
                log(f"  Fragment {fid}: SMILES has wildcards, skipping RXNMapper")
                continue
            frag_data[fid] = (frag_mol, frag_atoms, frag_smi)

        if not frag_data:
            continue

        # Build reaction SMILES: all_fragments >> product
        reactant_side = ".".join(d[2] for d in frag_data.values())
        rxn_smi = f"{reactant_side}>>{prod_smi}"

        log(f"  RXN SMILES: {rxn_smi[:100]}...")

        # Call RXNMapper
        try:
            from experiments.atom_mapping.rxn_atom_mapper import map_reaction
            map_result = map_reaction(rxn_smi, timeout=timeout)
        except ImportError:
            log("  rxn_atom_mapper not importable, falling back to MCS")
            return rdkit_align_to_product(root, verbose=verbose)
        except Exception as exc:
            log(f"  RXNMapper error: {exc}, falling back to MCS")
            return rdkit_align_to_product(root, verbose=verbose)

        if map_result is None:
            log("  RXNMapper returned no results, falling back to MCS")
            return rdkit_align_to_product(root, verbose=verbose)

        mapped_rxn = map_result["mapped_rxn"]
        confidence = map_result.get("confidence", 0)
        log(f"  RXNMapper confidence: {confidence:.4f}")

        # Parse mapped SMILES
        mapped_r_str, mapped_p_str = mapped_rxn.split(">>")
        mapped_reactants = mapped_r_str.split(".")
        mapped_products = mapped_p_str.split(".")

        # Parse mapped product
        mapped_prod_mol = Chem.MolFromSmiles(mapped_products[0])
        if mapped_prod_mol is None:
            log("  Could not parse mapped product SMILES")
            continue

        # Build map_number -> mapped_prod_atom_idx lookup
        prod_mapnum_to_mapped_idx = {}
        for atom in mapped_prod_mol.GetAtoms():
            mn = atom.GetAtomMapNum()
            if mn > 0:
                prod_mapnum_to_mapped_idx[mn] = atom.GetIdx()

        # Bridge: mapped product atoms -> CDXML product atoms via substructure match
        mapped_prod_clean = Chem.RWMol(mapped_prod_mol)
        for atom in mapped_prod_clean.GetAtoms():
            atom.SetAtomMapNum(0)
        try:
            Chem.SanitizeMol(mapped_prod_clean)
        except Exception:
            pass

        prod_match = prod_mol.GetSubstructMatch(mapped_prod_clean)
        if not prod_match:
            # Try reverse match
            prod_match_rev = Chem.Mol(mapped_prod_clean).GetSubstructMatch(prod_mol)
            if prod_match_rev:
                # Invert: mapped_idx -> prod_mol_idx
                prod_match = [0] * mapped_prod_clean.GetNumAtoms()
                for prod_idx, mapped_idx in enumerate(prod_match_rev):
                    if mapped_idx < len(prod_match):
                        prod_match[mapped_idx] = prod_idx
                prod_match = tuple(prod_match)
            else:
                log("  Product substructure match failed, falling back to MCS")
                return rdkit_align_to_product(root, verbose=verbose)

        # For each fragment, find its mapped correspondence and align
        for fid, (frag_mol, frag_atoms, frag_smi) in frag_data.items():
            frag_canon = Chem.MolToSmiles(
                Chem.MolFromSmiles(frag_smi))

            # Find this fragment in the mapped reactants
            # (RXNMapper reorders reactants!)
            mapped_frag_smi = None
            for mr_smi in mapped_reactants:
                mr_mol = Chem.MolFromSmiles(mr_smi)
                if mr_mol is None:
                    continue
                mr_clean = Chem.RWMol(mr_mol)
                for atom in mr_clean.GetAtoms():
                    atom.SetAtomMapNum(0)
                mr_canon = Chem.MolToSmiles(mr_clean)
                if mr_canon == frag_canon:
                    mapped_frag_smi = mr_smi
                    break

            if mapped_frag_smi is None:
                log(f"  Fragment {fid}: not found in mapped output, "
                    "falling back to MCS")
                # Per-fragment MCS fallback
                atom_map, n_mcs = _find_mcs_match(prod_mol, frag_mol, 30)
                if atom_map is None:
                    log(f"  Fragment {fid}: MCS also < 3 atoms, skipping")
                    continue
                n_atoms = len(frag_atoms)
                original_center = (
                    sum(a["x"] for a in frag_atoms) / n_atoms,
                    sum(a["y"] for a in frag_atoms) / n_atoms,
                )
                _rdkit_align_and_write(
                    fragments[fid], prod_mol, frag_mol, frag_atoms,
                    atom_map, scale, original_center)
                aligned_count += 1
                continue

            # Parse mapped fragment
            mapped_frag_mol = Chem.MolFromSmiles(mapped_frag_smi)
            if mapped_frag_mol is None:
                continue

            frag_mapnum_to_mapped_idx = {}
            for atom in mapped_frag_mol.GetAtoms():
                mn = atom.GetAtomMapNum()
                if mn > 0:
                    frag_mapnum_to_mapped_idx[mn] = atom.GetIdx()

            # Bridge: mapped fragment atoms -> CDXML fragment atoms
            mapped_frag_clean = Chem.RWMol(mapped_frag_mol)
            for atom in mapped_frag_clean.GetAtoms():
                atom.SetAtomMapNum(0)
            try:
                Chem.SanitizeMol(mapped_frag_clean)
            except Exception:
                pass

            frag_match = frag_mol.GetSubstructMatch(mapped_frag_clean)
            if not frag_match:
                frag_match_rev = Chem.Mol(mapped_frag_clean).GetSubstructMatch(
                    frag_mol)
                if frag_match_rev:
                    frag_match = [0] * mapped_frag_clean.GetNumAtoms()
                    for fi, mi in enumerate(frag_match_rev):
                        if mi < len(frag_match):
                            frag_match[mi] = fi
                    frag_match = tuple(frag_match)
                else:
                    log(f"  Fragment {fid}: substruct match failed, "
                        "falling back to MCS")
                    atom_map, n_mcs = _find_mcs_match(prod_mol, frag_mol, 30)
                    if atom_map is not None:
                        n_atoms = len(frag_atoms)
                        original_center = (
                            sum(a["x"] for a in frag_atoms) / n_atoms,
                            sum(a["y"] for a in frag_atoms) / n_atoms,
                        )
                        _rdkit_align_and_write(
                            fragments[fid], prod_mol, frag_mol, frag_atoms,
                            atom_map, scale, original_center)
                        aligned_count += 1
                    continue

            # Build atom_map: (prod_mol_idx, frag_mol_idx)
            atom_map = []
            shared_maps = (set(frag_mapnum_to_mapped_idx.keys()) &
                           set(prod_mapnum_to_mapped_idx.keys()))

            for mn in shared_maps:
                mapped_frag_idx = frag_mapnum_to_mapped_idx[mn]
                mapped_prod_idx = prod_mapnum_to_mapped_idx[mn]

                if (mapped_frag_idx < len(frag_match) and
                        mapped_prod_idx < len(prod_match)):
                    cdxml_frag_idx = frag_match[mapped_frag_idx]
                    cdxml_prod_idx = prod_match[mapped_prod_idx]
                    atom_map.append((cdxml_prod_idx, cdxml_frag_idx))

            if len(atom_map) < 3:
                log(f"  Fragment {fid}: only {len(atom_map)} shared maps, "
                    "falling back to MCS")
                mcs_map, n_mcs = _find_mcs_match(prod_mol, frag_mol, 30)
                if mcs_map is not None:
                    n_atoms = len(frag_atoms)
                    original_center = (
                        sum(a["x"] for a in frag_atoms) / n_atoms,
                        sum(a["y"] for a in frag_atoms) / n_atoms,
                    )
                    _rdkit_align_and_write(
                        fragments[fid], prod_mol, frag_mol, frag_atoms,
                        mcs_map, scale, original_center)
                    aligned_count += 1
                continue

            # Compute original centroid
            n_atoms = len(frag_atoms)
            original_center = (
                sum(a["x"] for a in frag_atoms) / n_atoms,
                sum(a["y"] for a in frag_atoms) / n_atoms,
            )

            # Align!
            rmsd = _rdkit_align_and_write(
                fragments[fid], prod_mol, frag_mol, frag_atoms,
                atom_map, scale, original_center)

            aligned_count += 1
            log(f"  Fragment {fid}: aligned to product "
                f"(RXNMapper {len(atom_map)} atom maps, RMSD {rmsd:.4f})")

    return aligned_count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Align reaction scheme fragments to the product orientation."""
    parser = argparse.ArgumentParser(
        description="Align CDXML reaction scheme fragments to match product orientation.",
    )
    parser.add_argument("input", help="Input CDXML file with a reaction scheme")
    parser.add_argument("-o", "--output", help="Output CDXML path (default: input-aligned.cdxml)")
    parser.add_argument("--ref", help="Reference CDXML for product orientation (optional)")
    parser.add_argument("--method", choices=["rdkit", "kabsch"], default="rdkit",
                        help="Alignment method (default: rdkit)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="MCS timeout in seconds (default: 30)")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    tree = ET.parse(args.input)
    root = tree.getroot()

    # Optional: align product to reference first
    if args.ref:
        if not os.path.isfile(args.ref):
            print(f"Error: reference file not found: {args.ref}", file=sys.stderr)
            return 1
        align_product_to_reference(root, args.ref, verbose=args.verbose,
                                   timeout=args.timeout)

    # Align fragments to product
    if args.method == "rdkit":
        count = rdkit_align_to_product(root, verbose=args.verbose,
                                       timeout=args.timeout)
    else:
        aligned = kabsch_align_to_product(root, verbose=args.verbose)
        count = len(aligned)

    base, ext = os.path.splitext(args.input)
    out_path = args.output or f"{base}-aligned{ext}"

    write_cdxml(tree, out_path)

    print(f"Aligned {count} fragment(s) -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
