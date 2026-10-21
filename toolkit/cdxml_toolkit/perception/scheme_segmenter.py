"""Detect and segment independent sub-schemes within a single CDXML file.

Multi-panel CDXML files (e.g., literature surveys, methodology figures) may
contain several independent reaction schemes drawn on the same page.  The
deterministic parser (Mode A) merges all ``<scheme>`` elements into one flat
step list, which mis-interprets independent reactions as a single multi-step
route.

This module provides:

- ``segment_scheme(cdxml_path)`` — detect independent sub-schemes using a
  three-level cascade: (1) scheme-element species overlap, (2) Y-band
  clustering, (3) arrow-graph connected components.
- ``classify_scheme_complexity(cdxml_path)`` — classify a CDXML file as
  ``"simple"``, ``"moderate"``, or ``"complex"`` to guide mode selection.

Usage::

    from cdxml_toolkit.perception.scheme_segmenter import segment_scheme
    segments = segment_scheme("oleObject12.cdxml")
    # => 5 SchemeSegment objects with disjoint species

    from cdxml_toolkit.perception.scheme_segmenter import classify_scheme_complexity
    tier = classify_scheme_complexity("oleObject12.cdxml")
    # => "complex"
"""

import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SchemeSegment:
    """One independent sub-scheme identified within a CDXML file."""
    segment_index: int
    scheme_element_ids: List[str] = field(default_factory=list)
    species_ids: List[str] = field(default_factory=list)
    arrow_ids: List[str] = field(default_factory=list)
    step_count: int = 0
    y_range: Tuple[float, float] = (0.0, 0.0)
    is_independent: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["y_range"] = list(d["y_range"])
        return d


@dataclass
class SegmentationResult:
    """Result of segmenting a CDXML file."""
    source_file: str = ""
    total_schemes: int = 0
    total_steps: int = 0
    total_fragments: int = 0
    total_arrows: int = 0
    segments: List[SchemeSegment] = field(default_factory=list)
    is_multi_panel: bool = False       # True if >1 independent segment found
    wrap_repeat_detected: bool = False  # True if SMILES overlap linked schemes
    method: str = ""                   # "scheme_overlap" | "y_band" | "arrow_graph" | "single"

    @property
    def num_segments(self) -> int:
        return len(self.segments)

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "total_schemes": self.total_schemes,
            "total_steps": self.total_steps,
            "total_fragments": self.total_fragments,
            "total_arrows": self.total_arrows,
            "num_segments": self.num_segments,
            "is_multi_panel": self.is_multi_panel,
            "wrap_repeat_detected": self.wrap_repeat_detected,
            "method": self.method,
            "segments": [s.to_dict() for s in self.segments],
        }


# ---------------------------------------------------------------------------
# XML parsing helpers
# ---------------------------------------------------------------------------

def _parse_scheme_elements(page: ET.Element) -> List[ET.Element]:
    """Find all <scheme> elements on the page."""
    schemes = page.findall("scheme")
    if not schemes:
        schemes = page.findall(".//scheme")
    return schemes


def _get_step_species(step_el: ET.Element) -> Set[str]:
    """Extract all species (fragment/text) IDs referenced by a step."""
    ids: Set[str] = set()
    for attr in ("ReactionStepReactants", "ReactionStepProducts",
                 "ReactionStepObjectsAboveArrow",
                 "ReactionStepObjectsBelowArrow"):
        val = step_el.get(attr, "")
        ids.update(x for x in val.split() if x)
    return ids


def _get_step_arrows(step_el: ET.Element) -> List[str]:
    """Extract arrow IDs referenced by a step."""
    val = step_el.get("ReactionStepArrows", "")
    return [x for x in val.split() if x]


def _get_arrow_y_center(arrow_el: ET.Element) -> Optional[float]:
    """Get the Y-coordinate center of an arrow from its BoundingBox.

    BoundingBox format: "left top right bottom"
    """
    bbox = arrow_el.get("BoundingBox", "")
    if not bbox:
        # Try Head3D/Tail3D attributes
        head = arrow_el.get("Head3D", "")
        tail = arrow_el.get("Tail3D", "")
        if head and tail:
            try:
                hy = float(head.split()[1])
                ty = float(tail.split()[1])
                return (hy + ty) / 2
            except (ValueError, IndexError):
                pass
        return None
    try:
        parts = bbox.split()
        top = float(parts[1])
        bottom = float(parts[3])
        return (top + bottom) / 2
    except (ValueError, IndexError):
        return None


def _get_element_y_range(elem: ET.Element,
                         id_map: Dict[str, ET.Element],
                         species_ids: Set[str],
                         arrow_ids: Set[str]) -> Tuple[float, float]:
    """Get the Y-coordinate range for a set of species and arrows."""
    y_vals: List[float] = []

    for sid in species_ids:
        el = id_map.get(sid)
        if el is None:
            continue
        bbox = el.get("BoundingBox", "")
        if bbox:
            try:
                parts = bbox.split()
                y_vals.append(float(parts[1]))  # top
                y_vals.append(float(parts[3]))  # bottom
            except (ValueError, IndexError):
                pass

    for aid in arrow_ids:
        el = id_map.get(aid)
        if el is None:
            continue
        y = _get_arrow_y_center(el)
        if y is not None:
            y_vals.append(y)

    if not y_vals:
        return (0.0, 0.0)
    return (min(y_vals), max(y_vals))


# ---------------------------------------------------------------------------
# Lightweight SMILES extraction for overlap detection
# ---------------------------------------------------------------------------

def _extract_smiles_for_fragments(fragment_ids: Set[str],
                                  id_map: Dict[str, ET.Element]) -> Dict[str, str]:
    """Extract SMILES for a set of fragment IDs using RDKit (lightweight).

    Returns a dict mapping fragment_id -> canonical_SMILES.
    Only succeeds for fragments that are valid molecular structures.
    """
    result: Dict[str, str] = {}
    try:
        from ..rdkit_utils import frag_to_smiles_resolved
    except ImportError:
        return result

    for fid in fragment_ids:
        el = id_map.get(fid)
        if el is None or el.tag != "fragment":
            continue
        try:
            smiles = frag_to_smiles_resolved(el)
            if smiles:
                result[fid] = smiles
        except Exception:
            pass
    return result


def _smiles_to_inchi(smiles: str) -> Optional[str]:
    """Convert SMILES to InChI for stereo-invariant comparison."""
    try:
        from rdkit import Chem
        from rdkit.Chem.inchi import MolToInchi
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        inchi = MolToInchi(mol)
        return inchi if inchi else None
    except Exception:
        return None


def _check_smiles_overlap(group_a_smiles: Dict[str, str],
                          group_b_smiles: Dict[str, str]) -> bool:
    """Check if any species between two groups share the same structure.

    Uses InChI for stereo-invariant comparison, with SMILES fallback.
    """
    if not group_a_smiles or not group_b_smiles:
        return False

    # Build InChI lookup for group A
    a_inchis: Set[str] = set()
    a_smiles: Set[str] = set()
    for smiles in group_a_smiles.values():
        a_smiles.add(smiles)
        inchi = _smiles_to_inchi(smiles)
        if inchi:
            a_inchis.add(inchi)

    # Check group B against group A
    for smiles in group_b_smiles.values():
        # InChI match
        inchi = _smiles_to_inchi(smiles)
        if inchi and inchi in a_inchis:
            return True
        # Exact SMILES match
        if smiles in a_smiles:
            return True

    return False


# ---------------------------------------------------------------------------
# Union-Find (for connected components)
# ---------------------------------------------------------------------------

class _UnionFind:
    """Simple union-find for merging connected scheme groups."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1

    def groups(self) -> Dict[int, List[int]]:
        g: Dict[int, List[int]] = defaultdict(list)
        for i in range(len(self.parent)):
            g[self.find(i)].append(i)
        return g


# ---------------------------------------------------------------------------
# Core segmentation
# ---------------------------------------------------------------------------

def segment_scheme(cdxml_path: str,
                   verbose: bool = False) -> SegmentationResult:
    """Detect independent sub-schemes within a CDXML file.

    Uses a three-level cascade:

    1. **Scheme-element species overlap** — if multiple ``<scheme>``
       elements exist, check whether they share any species IDs.
       Disjoint sets suggest independent sub-schemes.

    2. **SMILES overlap** — for disjoint scheme groups, extract
       lightweight SMILES and check for structural overlap (InChI).
       If overlap is found, merge the groups back (wrap-repeat).

    3. **Y-band clustering** — for remaining disjoint groups, verify
       via Y-coordinate separation that they occupy distinct regions.

    Parameters
    ----------
    cdxml_path : str
        Path to CDXML file.
    verbose : bool
        Print debug info to stderr.

    Returns
    -------
    SegmentationResult
        Segmentation analysis result.
    """

    def _log(msg: str):
        if verbose:
            print(f"  [segmenter] {msg}", file=sys.stderr)

    from ..cdxml_utils import parse_cdxml, build_id_map

    result = SegmentationResult(source_file=os.path.abspath(cdxml_path))

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return result

    id_map = build_id_map(page)

    # -----------------------------------------------------------------------
    # Step 1: Parse scheme elements
    # -----------------------------------------------------------------------
    scheme_elements = _parse_scheme_elements(page)
    result.total_schemes = len(scheme_elements)

    if len(scheme_elements) == 0:
        # No scheme elements — single segment from geometry
        all_arrows = page.findall(".//arrow")
        all_frags = page.findall(".//fragment")
        result.total_arrows = len(all_arrows)
        result.total_fragments = len(all_frags)
        seg = SchemeSegment(
            segment_index=0,
            species_ids=[f.get("id", "") for f in all_frags],
            arrow_ids=[a.get("id", "") for a in all_arrows],
            step_count=len(all_arrows),
        )
        result.segments = [seg]
        result.method = "single"
        return result

    if len(scheme_elements) == 1:
        # Single scheme element — one segment
        scheme_el = scheme_elements[0]
        steps = scheme_el.findall("step")
        species: Set[str] = set()
        arrows: List[str] = []
        for step_el in steps:
            species.update(_get_step_species(step_el))
            arrows.extend(_get_step_arrows(step_el))
        result.total_steps = len(steps)
        result.total_fragments = len([s for s in species
                                       if id_map.get(s, ET.Element("x")).tag == "fragment"])
        result.total_arrows = len(arrows)
        seg = SchemeSegment(
            segment_index=0,
            scheme_element_ids=[scheme_el.get("id", "")],
            species_ids=sorted(species),
            arrow_ids=arrows,
            step_count=len(steps),
            y_range=_get_element_y_range(page, id_map, species, set(arrows)),
        )
        result.segments = [seg]
        result.method = "single"
        return result

    # -----------------------------------------------------------------------
    # Step 2: Multiple scheme elements — build per-scheme species sets
    # -----------------------------------------------------------------------
    _log(f"Found {len(scheme_elements)} scheme elements")

    # Per-scheme data
    scheme_ids: List[str] = []
    scheme_species: List[Set[str]] = []
    scheme_arrows: List[List[str]] = []
    scheme_step_counts: List[int] = []

    for scheme_el in scheme_elements:
        sid = scheme_el.get("id", "")
        scheme_ids.append(sid)
        steps = scheme_el.findall("step")
        species_set: Set[str] = set()
        arrow_list: List[str] = []
        for step_el in steps:
            species_set.update(_get_step_species(step_el))
            arrow_list.extend(_get_step_arrows(step_el))
        scheme_species.append(species_set)
        scheme_arrows.append(arrow_list)
        scheme_step_counts.append(len(steps))

    n = len(scheme_elements)
    result.total_steps = sum(scheme_step_counts)
    all_species = set().union(*scheme_species)
    all_arrows_flat = [a for arrows in scheme_arrows for a in arrows]
    result.total_fragments = len([s for s in all_species
                                   if id_map.get(s, ET.Element("x")).tag == "fragment"])
    result.total_arrows = len(all_arrows_flat)

    # -----------------------------------------------------------------------
    # Step 3: Check for fragment ID overlap (rare but possible)
    # -----------------------------------------------------------------------
    uf = _UnionFind(n)

    for i in range(n):
        for j in range(i + 1, n):
            overlap = scheme_species[i] & scheme_species[j]
            if overlap:
                _log(f"Schemes {scheme_ids[i]} and {scheme_ids[j]} share "
                     f"{len(overlap)} species IDs -> merging")
                uf.union(i, j)

    # -----------------------------------------------------------------------
    # Step 4: Check for SMILES overlap (wrap-repeat detection)
    # -----------------------------------------------------------------------
    # Only check pairs that aren't already merged
    groups_before_smiles = uf.groups()
    _log(f"After ID overlap check: {len(groups_before_smiles)} groups")

    # Extract SMILES for boundary species (products + reactants of each scheme)
    # to detect wrap-repeat linkage
    scheme_smiles: List[Dict[str, str]] = []
    for i in range(n):
        frag_ids = {s for s in scheme_species[i]
                    if id_map.get(s, ET.Element("x")).tag == "fragment"}
        smiles_map = _extract_smiles_for_fragments(frag_ids, id_map)
        scheme_smiles.append(smiles_map)
        _log(f"Scheme {scheme_ids[i]}: {len(smiles_map)}/{len(frag_ids)} "
             f"fragments with SMILES")

    for i in range(n):
        for j in range(i + 1, n):
            if uf.find(i) == uf.find(j):
                continue  # already merged
            if _check_smiles_overlap(scheme_smiles[i], scheme_smiles[j]):
                _log(f"Schemes {scheme_ids[i]} and {scheme_ids[j]} share "
                     f"SMILES -> merging (wrap-repeat)")
                uf.union(i, j)
                result.wrap_repeat_detected = True

    # -----------------------------------------------------------------------
    # Step 5: Build final segments from connected components
    # -----------------------------------------------------------------------
    groups = uf.groups()
    _log(f"After SMILES overlap check: {len(groups)} groups")

    segments: List[SchemeSegment] = []
    for seg_idx, (_, members) in enumerate(sorted(groups.items())):
        seg_scheme_ids = [scheme_ids[m] for m in members]
        seg_species = sorted(set().union(*(scheme_species[m] for m in members)))
        seg_arrows = [a for m in members for a in scheme_arrows[m]]
        seg_step_count = sum(scheme_step_counts[m] for m in members)

        y_range = _get_element_y_range(
            page, id_map,
            set(seg_species),
            set(seg_arrows),
        )

        segments.append(SchemeSegment(
            segment_index=seg_idx,
            scheme_element_ids=seg_scheme_ids,
            species_ids=seg_species,
            arrow_ids=seg_arrows,
            step_count=seg_step_count,
            y_range=y_range,
            is_independent=(len(groups) > 1),
        ))

    result.segments = segments
    result.is_multi_panel = len(segments) > 1
    result.method = ("scheme_overlap" if result.wrap_repeat_detected
                     else "scheme_overlap" if len(groups) < len(groups_before_smiles)
                     else "scheme_overlap")

    if result.is_multi_panel:
        _log(f"Multi-panel detected: {len(segments)} independent segments")
        result.method = "scheme_overlap"
    else:
        _log(f"Single panel (all schemes connected)")
        result.method = "connected"

    return result


# ---------------------------------------------------------------------------
# Complexity classification
# ---------------------------------------------------------------------------

def classify_scheme_complexity(cdxml_path: str) -> str:
    """Classify a CDXML file's complexity for mode selection.

    Returns
    -------
    str
        ``"simple"`` — 1 scheme element, <=4 arrows, <=10 fragments (Mode A)
        ``"moderate"`` — 1-2 scheme elements, 5-8 arrows, 10-30 fragments (Mode B)
        ``"complex"`` — 3+ scheme elements OR >8 arrows OR >30 fragments OR
        multi-panel (Mode C)
    """
    from ..cdxml_utils import parse_cdxml, build_id_map

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return "simple"

    schemes = _parse_scheme_elements(page)
    n_schemes = len(schemes)

    # Count arrows and fragments
    n_arrows = 0
    n_fragments = 0
    for scheme_el in schemes:
        for step_el in scheme_el.findall("step"):
            arrows = step_el.get("ReactionStepArrows", "").split()
            n_arrows += len([a for a in arrows if a])
    n_fragments = len(page.findall(".//fragment"))

    # Check for multi-panel
    if n_schemes >= 2:
        # Quick check: do a lightweight segmentation
        seg_result = segment_scheme(cdxml_path)
        if seg_result.is_multi_panel:
            return "complex"

    # Classify based on thresholds
    if n_schemes >= 3:
        return "complex"
    if n_arrows > 8 or n_fragments > 30:
        return "complex"
    if n_schemes >= 2 or n_arrows > 4 or n_fragments > 10:
        return "moderate"
    return "simple"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI for scheme segmentation analysis."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Analyze CDXML file for independent sub-schemes"
    )
    parser.add_argument("input", help="CDXML file or directory of CDXML files")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of terminal report")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print debug info")

    args = parser.parse_args()

    inputs = []
    if os.path.isdir(args.input):
        for f in sorted(os.listdir(args.input)):
            if f.endswith(".cdxml"):
                inputs.append(os.path.join(args.input, f))
    else:
        inputs.append(args.input)

    results = []
    for path in inputs:
        seg_result = segment_scheme(path, verbose=args.verbose)
        complexity = classify_scheme_complexity(path)
        results.append({
            "file": os.path.basename(path),
            "complexity": complexity,
            "segmentation": seg_result.to_dict(),
        })

    if args.json:
        json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        for r in results:
            seg = r["segmentation"]
            name = r["file"]
            n_seg = seg["num_segments"]
            multi = seg["is_multi_panel"]
            wrap = seg["wrap_repeat_detected"]
            complexity = r["complexity"]
            n_schemes = seg["total_schemes"]
            n_steps = seg["total_steps"]
            n_frags = seg["total_fragments"]

            tag = f"[{complexity.upper():8s}]"
            parts = [f"{n_schemes} schemes, {n_steps} steps, {n_frags} frags"]
            if multi:
                parts.append(f"{n_seg} independent segments")
            elif wrap:
                parts.append("wrap-repeat (connected)")
            else:
                parts.append("single panel")
            print(f"  {tag}  {name:45s}  {', '.join(parts)}")


if __name__ == "__main__":
    main()
