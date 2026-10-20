#!/usr/bin/env python3
"""
scheme_reader.py — Read CDXML reaction schemes into structured descriptions.

The semantic inverse of the DSL renderer: takes a CDXML file containing a
reaction scheme (single or multi-step) and produces a structured JSON with
a species registry, reaction graph, topology classification, and a natural
language narrative suitable for LLM consumption.

Two parsing strategies (tried in order):
  1. Step-attribute path — reads <scheme><step> attributes
     (ReactionStepReactants/Products/Above/Below).
  2. Geometry-based fallback — assigns roles by spatial position relative
     to arrows.

CLI:
    python -m cdxml_toolkit.scheme_reader scheme.cdxml -o description.json
    python -m cdxml_toolkit.scheme_reader scheme.cdxml --narrative-only

Python API:
    from cdxml_toolkit.perception.scheme_reader import read_scheme
    desc = read_scheme("scheme.cdxml")
    print(desc.narrative)
    desc.to_json("description.json")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_verbose = False


def _log(msg: str) -> None:
    if _verbose:
        print(f"  [scheme_reader] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SpeciesRecord:
    """One chemical entity identified in the scheme."""
    id: str = ""                          # "species_0", ...
    cdxml_element_id: str = ""            # CDXML element id
    element_type: str = ""                # "fragment" or "text"
    smiles: Optional[str] = None          # canonical SMILES (abbreviations resolved)
    smiles_raw: Optional[str] = None      # SMILES without abbreviation expansion
    name: Optional[str] = None            # display name / text label content
    formula: Optional[str] = None         # molecular formula
    mw: Optional[float] = None            # average molecular weight
    label: Optional[str] = None           # compound number ("1", "2a")
    iupac_name: Optional[str] = None      # IUPAC name (from ChemScript or PubChem)
    aligned_iupac: Optional[str] = None   # aligned IUPAC name (from aligned_namer)
    text_category: Optional[str] = None   # for text species: "chemical", "condition_ref",
                                          # "footnote", "yield", "compound_label",
                                          # "citation", "bioactivity"
    is_solvent: bool = False              # True if reagent_db role == "solvent"
    equiv_text: Optional[str] = None      # e.g. "1.2 eq", "5 mol%"

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items()
                if v is not None and v is not False}


@dataclass
class StepRecord:
    """One reaction step extracted from the scheme."""
    step_index: int = 0                             # 0-based
    reactant_ids: List[str] = field(default_factory=list)
    product_ids: List[str] = field(default_factory=list)
    reagent_ids: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    condition_text_raw: List[str] = field(default_factory=list)
    yield_text: Optional[str] = None
    arrow_style: str = "solid"                      # "solid", "dashed", "failed"
    arrow_cdxml_id: Optional[str] = None
    molecular_diff_text: Optional[str] = None       # e.g. "bromo → phenyl"

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items()
                if v is not None and v != [] and v != ""}


@dataclass
class ScopeEntry:
    """One entry in a substrate scope table."""
    entry_id: str = ""                    # "scope_0", "scope_1", ...
    species_id: str = ""                  # SpeciesRecord.id of the scope structure
    label: Optional[str] = None           # compound number ("5.70a")
    conditions_variant: Optional[str] = None  # "X = I" or "X = Br"
    yield_text: Optional[str] = None      # "39%"
    mass_text: Optional[str] = None       # "22 mg"
    notes: Optional[str] = None           # "Scale-up: 130 mg, 16%"

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SchemeDescription:
    """Complete structured description of a reaction scheme."""
    version: str = "1.0"
    source_file: str = ""
    topology: str = "linear"
    content_type: str = ""                # "synthesis", "sar_design", "biological_pathway",
                                          # "target_array", "literature_comparison",
                                          # "composite", "investigation", "unknown",
                                          # "substrate_scope"
    num_steps: int = 0
    species: Dict[str, SpeciesRecord] = field(default_factory=dict)
    steps: List[StepRecord] = field(default_factory=list)
    scope_entries: List[ScopeEntry] = field(default_factory=list)
    sub_schemes: List["SchemeDescription"] = field(default_factory=list)
    narrative: str = ""
    warnings: List[str] = field(default_factory=list)
    # --- Spatial assignment metadata (v1.1) ---
    layout_pattern: Optional[str] = None          # detected layout from spatial engine
    parse_method: str = ""                        # "geometry" or "step_attribute"
    assignment_confidences: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "version": self.version,
            "source_file": self.source_file,
            "topology": self.topology,
            "num_steps": self.num_steps,
            "species": {k: v.to_dict() for k, v in self.species.items()},
            "steps": [s.to_dict() for s in self.steps],
            "narrative": self.narrative,
            "warnings": self.warnings,
        }
        if self.content_type:
            d["content_type"] = self.content_type
        if self.scope_entries:
            d["scope_entries"] = [e.to_dict() for e in self.scope_entries]
        if self.sub_schemes:
            d["sub_schemes"] = [s.to_dict() for s in self.sub_schemes]
        if self.layout_pattern:
            d["layout_pattern"] = self.layout_pattern
        if self.parse_method:
            d["parse_method"] = self.parse_method
        if self.assignment_confidences:
            d["assignment_confidences"] = self.assignment_confidences
        return d

    def to_json(self, path: str, pretty: bool = True) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2 if pretty else None,
                      ensure_ascii=False)

    @classmethod
    def from_json(cls, path: str) -> "SchemeDescription":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_dict(cls, d: dict) -> "SchemeDescription":
        species = {}
        for k, v in d.get("species", {}).items():
            valid = {f for f in SpeciesRecord.__dataclass_fields__}
            species[k] = SpeciesRecord(**{f: v[f] for f in valid if f in v})
        steps = []
        for s in d.get("steps", []):
            valid = {f for f in StepRecord.__dataclass_fields__}
            steps.append(StepRecord(**{f: s[f] for f in valid if f in s}))
        scope_entries = []
        for se in d.get("scope_entries", []):
            valid = {f for f in ScopeEntry.__dataclass_fields__}
            scope_entries.append(
                ScopeEntry(**{f: se[f] for f in valid if f in se}))
        sub_schemes = [cls.from_dict(sd)
                       for sd in d.get("sub_schemes", [])]
        return cls(
            version=d.get("version", "1.0"),
            source_file=d.get("source_file", ""),
            topology=d.get("topology", "linear"),
            content_type=d.get("content_type", ""),
            num_steps=d.get("num_steps", 0),
            species=species,
            steps=steps,
            scope_entries=scope_entries,
            sub_schemes=sub_schemes,
            narrative=d.get("narrative", ""),
            warnings=d.get("warnings", []),
        )

    def to_scheme_descriptor(self) -> "SchemeDescriptor":
        """Convert to a DSL SchemeDescriptor for round-trip rendering."""
        from ..render.schema import (SchemeDescriptor, StepDescriptor,
                                 ArrowContent, StructureRef)

        structures = {}
        for sp_id, sp in self.species.items():
            if sp.smiles or sp.name:
                structures[sp_id] = StructureRef(
                    id=sp_id,
                    smiles=sp.smiles,
                    name=sp.name if not sp.smiles else None,
                    label=sp.label,
                )

        dsl_steps = []
        for step in self.steps:
            above = ArrowContent()
            below = ArrowContent()

            for rid in step.reagent_ids:
                sp = self.species.get(rid)
                if sp and sp.element_type == "fragment" and sp.smiles:
                    above.structures.append(rid)
                elif sp and sp.name:
                    below.text.append(sp.name)

            below.text.extend(step.conditions)

            sd = StepDescriptor(
                substrates=list(step.reactant_ids),
                products=list(step.product_ids),
                above_arrow=above if (above.structures or above.text) else None,
                below_arrow=below if below.text else None,
                yield_=step.yield_text,
                arrow_style=step.arrow_style,
            )
            dsl_steps.append(sd)

        layout_map = {
            "linear": "linear" if len(dsl_steps) <= 1 else "sequential",
            "divergent": "divergent",
            "convergent": "convergent",
            "parallel": "stacked-rows",
            "mixed": "sequential",
        }

        return SchemeDescriptor(
            structures=structures,
            steps=dsl_steps,
            layout=layout_map.get(self.topology, "sequential"),
        )


# ---------------------------------------------------------------------------
# Internal intermediate structure
# ---------------------------------------------------------------------------

@dataclass
class _RawStep:
    """Intermediate parsed step before species registry is built."""
    step_elem_id: str = ""
    reactant_elem_ids: List[str] = field(default_factory=list)
    product_elem_ids: List[str] = field(default_factory=list)
    above_arrow_ids: List[str] = field(default_factory=list)
    below_arrow_ids: List[str] = field(default_factory=list)
    arrow_elem_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _get_text_content(t_elem: ET.Element) -> str:
    """Extract plain text from a <t> element."""
    parts = []
    for s in t_elem.iter("s"):
        if s.text:
            parts.append(s.text)
    return "".join(parts).strip()


_YIELD_RE = re.compile(r"(\d+(?:\.\d+)?\s*%)")
_QUANT_RE = re.compile(r"\bquant\.?\b", re.IGNORECASE)
_LABEL_RE = re.compile(r"^[1-9]\d{0,2}[a-z]?$|^\([ivx]+\)$|^[a-z]$",
                        re.IGNORECASE)


def _extract_yield_from_text(text: str) -> Optional[str]:
    """Extract yield percentage from a text string."""
    m = _YIELD_RE.search(text)
    if m:
        return m.group(1)
    if _QUANT_RE.search(text):
        return "quant."
    return None


# ---------------------------------------------------------------------------
# Arrow helpers
# ---------------------------------------------------------------------------

def _arrow_endpoints(arrow: ET.Element) -> Tuple[float, float, float, float]:
    """Return (tail_x, tail_y, head_x, head_y) from an arrow element."""
    from ..cdxml_utils import arrow_endpoints
    return arrow_endpoints(arrow)


def _resolve_arrow(page: ET.Element, arrow_id: str,
                   id_map: Dict[str, ET.Element]) -> Optional[ET.Element]:
    """Resolve arrow element from ID, following SupersededBy chains."""
    el = id_map.get(arrow_id)
    if el is not None and el.tag == "arrow":
        return el
    if el is not None and el.tag == "graphic":
        sup_id = el.get("SupersededBy", "")
        if sup_id:
            arrow_el = id_map.get(sup_id)
            if arrow_el is not None:
                return arrow_el
    # Also search page children for graphic → arrow chain
    for child in page:
        if child.tag == "graphic" and child.get("id") == arrow_id:
            sup_id = child.get("SupersededBy", "")
            if sup_id:
                for child2 in page:
                    if child2.get("id") == sup_id:
                        return child2
    return None


def _detect_arrow_style(arrow: Optional[ET.Element]) -> str:
    """Detect arrow style from element attributes."""
    if arrow is None:
        return "solid"
    # NoGo="Cross" means failed reaction (X on arrow)
    if arrow.get("NoGo") == "Cross":
        return "failed"
    # Dashed arrow
    line_type = arrow.get("LineType", "")
    if line_type.lower() in ("dash", "dashed", "dot"):
        return "dashed"
    # Check ArrowheadType for dashed variant
    aht = arrow.get("ArrowheadType", "")
    if aht.lower() == "dashed":
        return "dashed"
    return "solid"


def _find_all_arrows(page: ET.Element) -> List[ET.Element]:
    """Find all reaction arrows on the page."""
    arrows = []
    seen_ids: Set[str] = set()
    for el in page:
        if el.tag == "arrow":
            eid = el.get("id", "")
            if eid not in seen_ids:
                arrows.append(el)
                seen_ids.add(eid)
    # Also check for graphic elements with arrow attributes
    for el in page:
        if el.tag == "graphic":
            if el.get("GraphicType") == "Line" and el.get("ArrowType"):
                eid = el.get("id", "")
                if eid not in seen_ids:
                    arrows.append(el)
                    seen_ids.add(eid)
    return arrows


# ---------------------------------------------------------------------------
# Step-attribute parsing (primary path)
# ---------------------------------------------------------------------------

def _parse_from_step_attributes(page: ET.Element,
                                id_map: Dict[str, ET.Element],
                                scheme_filter: Optional[Set[str]] = None,
                                ) -> List[_RawStep]:
    """Parse steps using <scheme><step> element attributes.

    Iterates ALL <scheme> elements on the page (there may be multiple
    for stacked-rows layouts).

    Parameters
    ----------
    scheme_filter : set of str, optional
        If provided, only process ``<scheme>`` elements whose ``id``
        is in this set.  Used by the segmenter to parse a single
        sub-scheme from a multi-panel file.
    """
    raw_steps: List[_RawStep] = []

    # Find all scheme elements (could be multiple for stacked sections)
    schemes = page.findall("scheme")
    if not schemes:
        # Also try deeper nesting
        schemes = page.findall(".//scheme")

    for scheme_el in schemes:
        if scheme_filter is not None:
            if scheme_el.get("id", "") not in scheme_filter:
                continue
        for step_el in scheme_el.findall("step"):
            step_id = step_el.get("id", "")

            reactant_ids = step_el.get("ReactionStepReactants", "").split()
            product_ids = step_el.get("ReactionStepProducts", "").split()
            above_ids = step_el.get("ReactionStepObjectsAboveArrow", "").split()
            below_ids = step_el.get("ReactionStepObjectsBelowArrow", "").split()
            arrow_ids = step_el.get("ReactionStepArrows", "").split()

            # Filter out empty strings from split
            reactant_ids = [x for x in reactant_ids if x]
            product_ids = [x for x in product_ids if x]
            above_ids = [x for x in above_ids if x]
            below_ids = [x for x in below_ids if x]
            arrow_ids = [x for x in arrow_ids if x]

            # Validate IDs exist in id_map
            for eid in reactant_ids + product_ids + above_ids + below_ids:
                if eid not in id_map:
                    _log(f"Warning: element id {eid} in step {step_id} "
                         f"not found in page")

            # Resolve arrow ID (take first if multiple)
            arrow_elem_id = arrow_ids[0] if arrow_ids else None

            raw_steps.append(_RawStep(
                step_elem_id=step_id,
                reactant_elem_ids=reactant_ids,
                product_elem_ids=product_ids,
                above_arrow_ids=above_ids,
                below_arrow_ids=below_ids,
                arrow_elem_id=arrow_elem_id,
            ))

    return raw_steps


# ---------------------------------------------------------------------------
# Orphan transition-arrow recovery (serpentine layouts)
# ---------------------------------------------------------------------------

def _recover_orphan_transition_steps(
    page: ET.Element,
    raw_steps: List[_RawStep],
    id_map: Dict[str, ET.Element],
) -> List[_RawStep]:
    """Recover reaction steps from orphan vertical arrows.

    In serpentine layouts the DSL renderer emits vertical transition arrows
    outside any ``<scheme><step>`` element.  The step-attribute parser
    therefore misses them, leaving disconnected row-groups that the topology
    detector wrongly classifies as "parallel".

    This function detects those orphan vertical arrows, spatially resolves
    their nearest reactant/product fragments, collects nearby condition text,
    and inserts synthetic ``_RawStep`` entries at the correct position in
    *raw_steps* so that the downstream species-registry and topology
    detector see a fully-connected chain.

    Parameters
    ----------
    page : ET.Element
        The ``<page>`` element of the parsed CDXML.
    raw_steps : list of _RawStep
        The steps already found by the step-attribute parser (mutated
        in-place via insertion).
    id_map : dict
        Element-id → element mapping for the page.

    Returns
    -------
    list of _RawStep
        The *raw_steps* list, possibly with additional entries inserted.
    """
    from ..cdxml_utils import arrow_endpoints as _ae, fragment_centroid

    if not raw_steps:
        return raw_steps

    # Collect arrow IDs already claimed by existing steps
    claimed_arrow_ids: Set[str] = set()
    for rs in raw_steps:
        if rs.arrow_elem_id:
            claimed_arrow_ids.add(rs.arrow_elem_id)

    # Collect element IDs already claimed (reactants/products/above/below)
    claimed_elem_ids: Set[str] = set()
    for rs in raw_steps:
        claimed_elem_ids.update(rs.reactant_elem_ids)
        claimed_elem_ids.update(rs.product_elem_ids)
        claimed_elem_ids.update(rs.above_arrow_ids)
        claimed_elem_ids.update(rs.below_arrow_ids)

    # Compute a length threshold from existing step arrows.
    # Serpentine transition arrows are comparable in size to the reaction
    # arrows; tiny annotation arrows (15-20 pt) should be ignored.
    import math
    step_arrow_lengths: List[float] = []
    for rs in raw_steps:
        if rs.arrow_elem_id:
            a_el = id_map.get(rs.arrow_elem_id)
            if a_el is not None:
                atx, aty, ahx, ahy = _ae(a_el)
                step_arrow_lengths.append(math.hypot(ahx - atx, ahy - aty))
    min_arrow_len = 30.0  # absolute floor
    if step_arrow_lengths:
        median_len = sorted(step_arrow_lengths)[len(step_arrow_lengths) // 2]
        # Require at least 40% of the median step-arrow length
        min_arrow_len = max(min_arrow_len, 0.4 * median_len)

    # Build set of element IDs that are products of existing steps
    # (the orphan arrow's reactant must be one of these to qualify)
    existing_product_eids: Set[str] = set()
    for rs in raw_steps:
        existing_product_eids.update(rs.product_elem_ids)

    # Find orphan arrows on the page
    orphan_arrows = []
    for el in page:
        if el.tag != "arrow":
            continue
        eid = el.get("id", "")
        if eid in claimed_arrow_ids:
            continue
        tx, ty, hx, hy = _ae(el)
        dx, dy = hx - tx, hy - ty
        # Only consider substantially vertical arrows (|dy| > |dx|)
        if abs(dy) <= abs(dx):
            continue
        # Must be long enough to be a real reaction arrow
        if math.hypot(dx, dy) < min_arrow_len:
            continue
        orphan_arrows.append({
            "element": el,
            "id": eid,
            "tail_x": tx, "tail_y": ty,
            "head_x": hx, "head_y": hy,
            "mid_x": (tx + hx) / 2, "mid_y": (ty + hy) / 2,
        })

    if not orphan_arrows:
        return raw_steps

    # Collect fragment centroids (exclude already-claimed where possible)
    frag_data = []
    for el in page:
        if el.tag == "fragment":
            c = fragment_centroid(el)
            if c:
                frag_data.append({
                    "id": el.get("id", ""),
                    "cx": c[0], "cy": c[1],
                })

    # Collect text element positions
    text_data = []
    for el in page:
        if el.tag == "t":
            tid = el.get("id", "")
            p = el.get("p")
            if p:
                parts = p.split()
                tcx, tcy = float(parts[0]), float(parts[1])
            else:
                bb = el.get("BoundingBox", "")
                if bb:
                    vals = [float(v) for v in bb.split()]
                    tcx = (vals[0] + vals[2]) / 2
                    tcy = (vals[1] + vals[3]) / 2
                else:
                    continue
            text_data.append({"id": tid, "cx": tcx, "cy": tcy})

    # Build product→step-index map to find the insertion point
    product_to_step_idx: Dict[str, int] = {}
    for i, rs in enumerate(raw_steps):
        for pid in rs.product_elem_ids:
            product_to_step_idx[pid] = i

    # Process each orphan vertical arrow
    new_entries: List[Tuple[int, _RawStep]] = []  # (insert_after_idx, step)

    for oa in orphan_arrows:
        # Find nearest fragment on the tail side (reactant)
        # CDXML y increases downward; vertical arrow goes from
        # tail (upper) to head (lower).
        best_reactant = None
        best_r_dist = float("inf")
        for fd in frag_data:
            # Reactant should be above/near the tail (cy <= tail_y + margin)
            if fd["cy"] > oa["mid_y"]:
                continue  # below midpoint — candidate for product, not reactant
            dist = ((fd["cx"] - oa["tail_x"])**2
                    + (fd["cy"] - oa["tail_y"])**2)**0.5
            if dist < best_r_dist:
                best_r_dist = dist
                best_reactant = fd

        # Find nearest fragment on the head side (product)
        best_product = None
        best_p_dist = float("inf")
        for fd in frag_data:
            # Product should be below/near the head (cy >= mid_y)
            if fd["cy"] < oa["mid_y"]:
                continue  # above midpoint — candidate for reactant
            dist = ((fd["cx"] - oa["head_x"])**2
                    + (fd["cy"] - oa["head_y"])**2)**0.5
            if dist < best_p_dist:
                best_p_dist = dist
                best_product = fd

        if best_reactant is None or best_product is None:
            continue  # can't resolve both ends

        # Sanity check: distances should be reasonable (< 5× arrow length)
        arrow_len = abs(oa["head_y"] - oa["tail_y"])
        if best_r_dist > 5 * arrow_len or best_p_dist > 5 * arrow_len:
            continue

        reactant_id = best_reactant["id"]
        product_id = best_product["id"]

        # The reactant fragment must be a product of an existing step —
        # this ensures we are bridging two rows of a serpentine layout
        # rather than picking up unrelated annotation arrows.
        if reactant_id not in existing_product_eids:
            continue

        # Find condition text elements near the arrow body
        # (between tail and head, or slightly to the side)
        condition_ids = []
        arrow_len_x2 = 2.0 * arrow_len
        for td in text_data:
            if td["id"] in claimed_elem_ids:
                continue
            # Must be reasonably close to the arrow midpoint
            dist = ((td["cx"] - oa["mid_x"])**2
                    + (td["cy"] - oa["mid_y"])**2)**0.5
            if dist > arrow_len_x2:
                continue
            # Skip compound labels that are close to reactant/product
            if best_reactant:
                r_dist = ((td["cx"] - best_reactant["cx"])**2
                          + (td["cy"] - best_reactant["cy"])**2)**0.5
                if r_dist < arrow_len * 0.6:
                    continue
            if best_product:
                p_dist = ((td["cx"] - best_product["cx"])**2
                          + (td["cy"] - best_product["cy"])**2)**0.5
                if p_dist < arrow_len * 0.6:
                    continue
            condition_ids.append(td["id"])

        # Build the synthetic _RawStep
        step = _RawStep(
            step_elem_id=oa["id"],
            reactant_elem_ids=[reactant_id],
            product_elem_ids=[product_id],
            above_arrow_ids=[],
            below_arrow_ids=condition_ids,
            arrow_elem_id=oa["id"],
        )

        # Determine insertion position: after the step whose product is
        # our reactant fragment
        insert_after = product_to_step_idx.get(reactant_id, len(raw_steps) - 1)
        new_entries.append((insert_after, step))

        _log(f"Recovered orphan transition step from arrow {oa['id']}: "
             f"reactant={reactant_id} -> product={product_id} "
             f"(conditions: {len(condition_ids)} text element(s))")

    # Insert new entries in reverse order to preserve indices
    new_entries.sort(key=lambda x: x[0], reverse=True)
    for insert_after, step in new_entries:
        raw_steps.insert(insert_after + 1, step)

    return raw_steps


# ---------------------------------------------------------------------------
# Geometry-based fallback
# ---------------------------------------------------------------------------

def _parse_from_geometry(page: ET.Element,
                         id_map: Dict[str, ET.Element],
                         ) -> List[_RawStep]:
    """Parse steps using spatial position relative to arrows.

    Fallback for CDXML files without <scheme><step> attributes.
    """
    from ..cdxml_utils import fragment_centroid

    arrows = _find_all_arrows(page)
    if not arrows:
        return []

    # Get arrow data sorted by tail x-position
    arrow_data = []
    for arrow in arrows:
        tx, ty, hx, hy = _arrow_endpoints(arrow)
        # Ensure tail is left of head for horizontal arrows
        if tx > hx:
            tx, ty, hx, hy = hx, hy, tx, ty
        arrow_data.append({
            "element": arrow,
            "id": arrow.get("id", ""),
            "tail_x": tx, "tail_y": ty,
            "head_x": hx, "head_y": hy,
            "mid_x": (tx + hx) / 2,
            "mid_y": (ty + hy) / 2,
        })
    arrow_data.sort(key=lambda a: a["tail_x"])

    # Collect all fragments and text elements on the page
    fragments = []
    texts = []
    for el in page:
        if el.tag == "fragment":
            centroid = fragment_centroid(el)
            if centroid:
                cx, cy = centroid
            else:
                cx, cy = 0.0, 0.0
            fragments.append({
                "element": el,
                "id": el.get("id", ""),
                "cx": cx, "cy": cy,
            })
        elif el.tag == "t":
            p = el.get("p")
            if p:
                parts = p.split()
                tx_coord, ty_coord = float(parts[0]), float(parts[1])
            else:
                bb = el.get("BoundingBox", "")
                if bb:
                    vals = [float(v) for v in bb.split()]
                    tx_coord = (vals[0] + vals[2]) / 2
                    ty_coord = (vals[1] + vals[3]) / 2
                else:
                    continue
            texts.append({
                "element": el,
                "id": el.get("id", ""),
                "cx": tx_coord, "cy": ty_coord,
            })

    # Build raw steps by assigning elements to their nearest arrow
    raw_steps: List[_RawStep] = []

    for arrow_idx, ad in enumerate(arrow_data):
        step = _RawStep(
            step_elem_id=ad["id"],
            arrow_elem_id=ad["id"],
        )

        # Determine the x-range boundaries for this arrow
        # Left boundary: either the start of the page or the previous arrow's head
        left_bound = arrow_data[arrow_idx - 1]["head_x"] if arrow_idx > 0 else -1e9
        # Right boundary: either the end of the page or the next arrow's tail
        right_bound = (arrow_data[arrow_idx + 1]["tail_x"]
                       if arrow_idx < len(arrow_data) - 1 else 1e9)

        for frag in fragments:
            cx = frag["cx"]
            fid = frag["id"]

            # Check if this fragment belongs to this arrow's zone
            if cx < ad["tail_x"] and cx >= left_bound:
                # Left of tail → reactant
                step.reactant_elem_ids.append(fid)
            elif cx > ad["head_x"] and cx <= right_bound:
                # Right of head → product
                step.product_elem_ids.append(fid)
            elif ad["tail_x"] <= cx <= ad["head_x"]:
                # Between tail and head → above/below based on y
                cy = frag["cy"]
                if cy < ad["mid_y"]:
                    step.above_arrow_ids.append(fid)
                else:
                    step.below_arrow_ids.append(fid)

        for txt in texts:
            tx_coord = txt["cx"]
            tid = txt["id"]

            # Only assign text within the arrow's x-span
            if ad["tail_x"] - 20 <= tx_coord <= ad["head_x"] + 20:
                ty_coord = txt["cy"]
                if ty_coord < ad["mid_y"]:
                    step.above_arrow_ids.append(tid)
                else:
                    step.below_arrow_ids.append(tid)

        raw_steps.append(step)

    # Handle shared intermediates: product of step i that overlaps with
    # reactant of step i+1
    for i in range(len(raw_steps) - 1):
        curr_products = set(raw_steps[i].product_elem_ids)
        next_reactants = set(raw_steps[i + 1].reactant_elem_ids)
        # If no reactants found for next step, check if current products
        # should be shared
        if not next_reactants:
            for pid in raw_steps[i].product_elem_ids:
                raw_steps[i + 1].reactant_elem_ids.append(pid)

    return raw_steps


# ---------------------------------------------------------------------------
# Spatial-engine bridge (geometry-first primary path)
# ---------------------------------------------------------------------------

def _parse_from_spatial_engine(
    page: ET.Element,
    id_map: Dict[str, ET.Element],
) -> Optional[List[_RawStep]]:
    """Parse steps using the spatial_assignment engine.

    Returns a list of _RawStep or None if no arrows found.
    Stores metadata (layout_pattern, confidences) on the function object
    as ``_parse_from_spatial_engine._last_meta`` for retrieval by the caller.
    """
    from .spatial_assignment import (
        build_arrow_vectors, classify_layout, assign_elements,
    )

    arrows = build_arrow_vectors(page)
    if not arrows:
        _parse_from_spatial_engine._last_meta = {}  # type: ignore[attr-defined]
        return None

    layout = classify_layout(arrows)
    steps, results = assign_elements(arrows, page, layout)

    # Convert spatial_assignment.RawStep -> scheme_reader._RawStep
    raw_steps: List[_RawStep] = []
    for sa_step in steps:
        raw = _RawStep(
            step_elem_id=sa_step.arrow_id,
            arrow_elem_id=sa_step.arrow_id,
        )
        raw.reactant_elem_ids = list(sa_step.reactant_ids)
        raw.product_elem_ids = list(sa_step.product_ids)
        raw.above_arrow_ids = list(sa_step.above_arrow_ids)
        raw.below_arrow_ids = list(sa_step.below_arrow_ids)
        raw_steps.append(raw)

    # Store metadata for caller
    confidences = {r.element_id: r.confidence for r in results}
    _parse_from_spatial_engine._last_meta = {  # type: ignore[attr-defined]
        "layout_pattern": layout.value,
        "confidences": confidences,
    }

    return raw_steps


# ---------------------------------------------------------------------------
# Name resolution helpers
# ---------------------------------------------------------------------------

def _name_from_smiles(smiles: str) -> Optional[str]:
    """Look up a display name for a SMILES string via reagent_db."""
    try:
        from ..resolve.reagent_db import get_reagent_db
        db = get_reagent_db()
        entry = db.entry_for_smiles(smiles)
        if entry:
            return entry.get("display") or entry.get("name")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Text classification patterns
# ---------------------------------------------------------------------------

# Condition reference letters: "a", "b, c", "d,e", "a, b, c, d"
_CONDITION_REF_RE = re.compile(
    r"^[a-z](\s*[,/]\s*[a-z])*$"
)

# Condition ref with "or": "a or b"
_CONDITION_REF_OR_RE = re.compile(
    r"^[a-z]\s+or\s+[a-z]$", re.IGNORECASE
)

# Footnote text: "(a) morpholine (1.2 eq), Pd2(dba)3 (5 mol%), ..."
# Requires letter enclosed in parens — the standard format for condition footnotes
# in reaction scheme literature.
_FOOTNOTE_RE = re.compile(
    r"^\(([a-z])\)\s+\S",
    re.IGNORECASE
)

# Pure yield text: "72%", "(85%)", "92% yield", "quant.", "(quant.)"
_YIELD_ONLY_RE = re.compile(
    r"^\(?\d+(?:\.\d+)?\s*%\s*(yield)?\)?$|"
    r"^\(?quant\.?\)?$",
    re.IGNORECASE
)

# Compound labels: "1", "2a", "15", "SM-1", "DP-2", "(iii)"
# Extends _LABEL_RE with prefix patterns (SM-, DP-, etc.)
_COMPOUND_LABEL_RE = re.compile(
    r"^[1-9]\d{0,2}[a-z]?$|"            # numeric: "1", "2a", "15b"
    r"^\([ivx]+\)$|"                      # roman: "(i)", "(iii)"
    r"^(SM|DP|P|CP|Int)-?\d+[a-z]?$",    # prefixed: "SM-1", "DP-2", "P1"
    re.IGNORECASE
)

# Literature citations: "Author et al. J. Org. Chem. 1994, 59, 1937"
_CITATION_RE = re.compile(
    r"[A-Z][a-z]+\s+et\s+al\.", re.IGNORECASE
)
_JOURNAL_RE = re.compile(
    r"(J\.\s*(Org|Med|Am)\.\s*Chem|Angew\.\s*Chem|Org\.\s*Lett|"
    r"Tetrahedron|Bioorg\.\s*Med|Chem\.\s*Commun|ChemMedChem|"
    r"Proc\.\s*Natl|Biochem\.\s*Biophys|Chem\.\s*Ber|"
    r"Org\.\s*Process\.\s*Res|Digital\s*Discovery|RSC|"
    r"JACS|ACS\s*Catal|Nat\.\s*Chem)",
    re.IGNORECASE
)

# Bioactivity data: "IC50 = 23nM", "EC50 (RPMI-8226) = 190nM", "Ki = 5 µM"
_BIOACTIVITY_RE = re.compile(
    r"(IC50|EC50|Ki|Kd|MIC|ED50|GI50|CC50)\s*[=(]",
    re.IGNORECASE
)


def _classify_text_species(text: str) -> str:
    """Classify a text element into a category.

    Returns one of: "condition_ref", "footnote", "yield",
    "compound_label", "citation", "bioactivity", "chemical" (default).
    """
    stripped = text.strip()

    # Condition reference letters (single or comma/slash-separated)
    if _CONDITION_REF_RE.match(stripped):
        return "condition_ref"
    if _CONDITION_REF_OR_RE.match(stripped):
        return "condition_ref"

    # Pure yield annotations (before footnote check — footnotes may end with %)
    if _YIELD_ONLY_RE.match(stripped):
        return "yield"

    # Compound labels — short numeric/prefixed identifiers
    if _COMPOUND_LABEL_RE.match(stripped):
        return "compound_label"

    # Footnote text: "(a) reagent, conditions..." or "(b) NBS, DMF..."
    # Must be long enough to contain actual conditions (not just "(a)")
    if len(stripped) > 5 and _FOOTNOTE_RE.match(stripped):
        return "footnote"

    # Literature citations
    if _CITATION_RE.search(stripped) or _JOURNAL_RE.search(stripped):
        return "citation"

    # Bioactivity annotations
    if _BIOACTIVITY_RE.search(stripped):
        return "bioactivity"

    return "chemical"


# Single-letter names that PubChem falsely resolves (d → deuterium, etc.)
_LETTER_SMILES_BLACKLIST = frozenset("abcdefghijklmnopqrstuvwxyz")


# ---------------------------------------------------------------------------
# Species registry building
# ---------------------------------------------------------------------------


def _extract_variable_labels(frag_el: ET.Element) -> List[str]:
    """Extract variable position labels from a fragment's child nodes.

    Looks for GenericNickname and Unspecified node types that carry
    text labels (R3, R4, Linker, etc.).
    """
    labels = []
    for node in frag_el.iter("n"):
        node_type = node.get("NodeType", "")
        if node_type in ("GenericNickname", "Unspecified"):
            # Get the text label
            t_el = node.find("t")
            if t_el is not None:
                text = _get_text_content(t_el)
                if text and text.strip():
                    labels.append(text.strip())
            elif node_type == "GenericNickname":
                # Fallback to GenericNickname attribute
                gn = node.get("GenericNickname", "")
                if gn:
                    labels.append(gn)
    return labels


def _build_static_species_registry(
    page: ET.Element,
    id_map: Dict[str, ET.Element],
    use_network: bool = True,
    use_chemscript: bool = False,
) -> Dict[str, SpeciesRecord]:
    """Enumerate all fragments on a page without requiring reaction steps.

    Used for non-reaction CDXMLs (target arrays, standalone structures)
    where no arrows are present.  Returns a species dict keyed by species
    ID, similar to the first return value of ``_build_species_registry``.
    """
    from ..rdkit_utils import frag_to_smiles_resolved, frag_to_smiles, frag_to_mw

    # Optional ChemScript
    _frag_to_smiles_cs = None
    _cs_bridge = None
    if use_chemscript:
        try:
            from ..rdkit_utils import frag_to_smiles_chemscript
            _frag_to_smiles_cs = frag_to_smiles_chemscript
        except ImportError:
            pass
        try:
            from ..chemdraw.chemscript_bridge import ChemScriptBridge
            _cs_bridge = ChemScriptBridge()
        except Exception:
            pass

    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        _has_rdkit = True
    except ImportError:
        _has_rdkit = False

    species_dict: Dict[str, SpeciesRecord] = {}
    species_counter = 0

    for el in page:
        if el.tag != "fragment":
            continue

        elem_id = el.get("id", "")
        sp_id = f"species_{species_counter}"
        species_counter += 1

        # SMILES extraction (same cascade as _build_species_registry)
        smiles_cs = None
        smiles_resolved = None
        smiles_raw = None
        if _frag_to_smiles_cs is not None:
            try:
                smiles_cs = _frag_to_smiles_cs(el)
            except Exception:
                pass
        try:
            smiles_resolved = frag_to_smiles_resolved(el)
        except Exception:
            pass
        try:
            smiles_raw = frag_to_smiles(el)
        except Exception:
            pass

        smiles = smiles_cs or smiles_resolved or smiles_raw

        # MW
        mw = None
        try:
            mw = frag_to_mw(el)
        except Exception:
            pass

        # Formula
        formula = None
        if smiles and _has_rdkit:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                formula = rdMolDescriptors.CalcMolFormula(mol)

        # Label
        label = _find_nearby_label(el, page, id_map)

        # Name from reagent_db
        name = None
        if smiles:
            name = _name_from_smiles(smiles)

        # IUPAC name
        iupac_name = None
        if _cs_bridge and smiles:
            try:
                iupac_name = _cs_bridge.get_name(smiles)
            except Exception:
                pass

        # Generic/variable group metadata
        var_labels = _extract_variable_labels(el)
        if var_labels:
            var_str = ", ".join(var_labels)
            if name:
                name = f"{name} (variable: {var_str})"
            else:
                name = f"scaffold (variable: {var_str})"

        record = SpeciesRecord(
            id=sp_id,
            cdxml_element_id=elem_id,
            element_type="fragment",
            smiles=smiles,
            smiles_raw=smiles_raw if smiles_raw != smiles else None,
            name=name,
            iupac_name=iupac_name,
            formula=formula,
            mw=round(mw, 2) if mw else None,
            label=label,
        )
        species_dict[sp_id] = record

    # Also collect standalone text elements on the page
    for el in page:
        if el.tag != "t":
            continue
        text_content = _get_text_content(el)
        if not text_content or not text_content.strip():
            continue
        # Skip trivially short or known non-chemical text
        stripped = text_content.strip()
        if len(stripped) < 2:
            continue

        sp_id = f"species_{species_counter}"
        species_counter += 1
        text_cat = _classify_text_species(stripped)

        record = SpeciesRecord(
            id=sp_id,
            cdxml_element_id=el.get("id", ""),
            element_type="text",
            name=text_content,
            text_category=text_cat,
        )
        species_dict[sp_id] = record

    return species_dict


def _build_species_registry(
    raw_steps: List[_RawStep],
    id_map: Dict[str, ET.Element],
    page: ET.Element,
    use_network: bool = True,
    use_chemscript: bool = False,
) -> Tuple[Dict[str, SpeciesRecord], Dict[str, List[str]]]:
    """Build species records for all referenced elements.

    Returns:
        (species_dict, elem_to_species_ids) where elem_to_species_ids maps
        CDXML element IDs to lists of species IDs (one-to-many for split
        text blocks).
    """
    from ..rdkit_utils import frag_to_smiles_resolved, frag_to_smiles, frag_to_mw

    # Optional ChemScript-based SMILES (best abbreviation resolution)
    _frag_to_smiles_cs = None
    _cs_bridge = None
    if use_chemscript:
        try:
            from ..rdkit_utils import frag_to_smiles_chemscript
            _frag_to_smiles_cs = frag_to_smiles_chemscript
            _log("ChemScript SMILES resolution enabled")
        except ImportError:
            _log("ChemScript not available, using RDKit resolution")
        # Also get ChemScript bridge for IUPAC name generation
        try:
            from ..chemdraw.chemscript_bridge import ChemScriptBridge
            _cs_bridge = ChemScriptBridge()
            _log("ChemScript IUPAC naming enabled")
        except Exception:
            pass

    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        _has_rdkit = True
    except ImportError:
        _has_rdkit = False

    # Collect all unique element IDs
    all_elem_ids: Set[str] = set()
    for step in raw_steps:
        all_elem_ids.update(step.reactant_elem_ids)
        all_elem_ids.update(step.product_elem_ids)
        all_elem_ids.update(step.above_arrow_ids)
        all_elem_ids.update(step.below_arrow_ids)

    species_dict: Dict[str, SpeciesRecord] = {}
    elem_to_species: Dict[str, List[str]] = {}
    species_counter = 0

    for elem_id in sorted(all_elem_ids):
        if elem_id in elem_to_species:
            continue  # already registered (shared intermediate)

        el = id_map.get(elem_id)
        if el is None:
            _log(f"Element {elem_id} not found in id_map, skipping")
            continue

        sp_id = f"species_{species_counter}"
        species_counter += 1

        if el.tag == "fragment":
            # Extract SMILES — try ChemScript first (best abbreviation
            # expansion), then superatom-table resolution, then raw.
            smiles_cs = None
            smiles_resolved = None
            smiles_raw = None
            if _frag_to_smiles_cs is not None:
                try:
                    smiles_cs = _frag_to_smiles_cs(el)
                except Exception as e:
                    _log(f"frag_to_smiles_chemscript failed for {elem_id}: {e}")
            try:
                smiles_resolved = frag_to_smiles_resolved(el)
            except Exception as e:
                _log(f"frag_to_smiles_resolved failed for {elem_id}: {e}")
            try:
                smiles_raw = frag_to_smiles(el)
            except Exception as e:
                _log(f"frag_to_smiles failed for {elem_id}: {e}")

            smiles = smiles_cs or smiles_resolved or smiles_raw

            # Compute MW
            mw = None
            try:
                mw = frag_to_mw(el)
            except Exception:
                pass

            # Compute formula from SMILES
            formula = None
            if smiles and _has_rdkit:
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    formula = rdMolDescriptors.CalcMolFormula(mol)

            # Detect compound label from nearby text
            label = _find_nearby_label(el, page, id_map)

            # Try to get a name from reagent_db by SMILES
            name = None
            if smiles:
                name = _name_from_smiles(smiles)

            # IUPAC name via ChemScript (when available)
            iupac_name = None
            if _cs_bridge and smiles:
                try:
                    iupac_name = _cs_bridge.get_name(smiles)
                except Exception:
                    pass  # ChemScript fails on some structures (charges, etc.)

            record = SpeciesRecord(
                id=sp_id,
                cdxml_element_id=elem_id,
                element_type="fragment",
                smiles=smiles,
                smiles_raw=smiles_raw if smiles_raw != smiles else None,
                name=name,
                iupac_name=iupac_name,
                formula=formula,
                mw=round(mw, 2) if mw else None,
                label=label,
            )

        elif el.tag == "t":
            text_content = _get_text_content(el)
            if not text_content:
                continue

            # Skip pure annotation text that isn't a chemical name:
            # - equiv annotations: "(1.2 eq)"
            # These are captured as step metadata, not species.
            stripped = text_content.strip()
            if re.match(r"^\(?\d+\.?\d*\s*eq\.?\)?$", stripped,
                        re.IGNORECASE):
                _log(f"Skipping equiv annotation: {stripped!r}")
                species_counter -= 1  # reclaim ID
                continue

            # Classify text species
            text_cat = _classify_text_species(stripped)
            _log(f"Text species {elem_id} classified as {text_cat}: "
                 f"{stripped[:60]!r}")

            if text_cat == "chemical":
                # Split multi-line text blocks into individual species.
                # Each chemical entity becomes its own SpeciesRecord;
                # condition tokens (temp, time, atmosphere) are skipped.
                from .reaction_parser import (
                    _resolve_text_label, _is_condition_token)
                from ..resolve.reagent_db import get_reagent_db
                _reagent_db = get_reagent_db()

                _equiv_re = re.compile(
                    r'\s*\((\d+\.?\d*\s*(?:eq\.?|equiv\.?|mol\s*%))\)'
                    r'\s*$', re.IGNORECASE)

                lines = [l.strip() for l in text_content.split("\n")
                         if l.strip()]
                split_records: List[SpeciesRecord] = []

                for line in lines:
                    # Extract equiv/mol% annotation
                    eq_match = _equiv_re.search(line)
                    line_equiv = eq_match.group(1) if eq_match else None
                    clean_line = _equiv_re.sub("", line).strip()
                    if not clean_line:
                        continue

                    # Sub-split on ", " (comma+space) or ";"
                    # Protects "1,4-dioxane" (no space after comma)
                    parts = re.split(r'\s*;\s*|,\s+', clean_line)

                    # Further split "/" mixtures into separate entities.
                    # e.g. "dioxane/H2O (3:1)" → ["dioxane", "H2O"]
                    # Strip trailing ratio annotations like "(3:1)" first.
                    expanded_parts: list = []
                    _ratio_re = re.compile(
                        r'\s*\(\d+:\d+\)\s*$')
                    for p in parts:
                        p_clean = _ratio_re.sub("", p).strip()
                        if "/" in p_clean:
                            expanded_parts.extend(
                                s.strip() for s in p_clean.split("/")
                                if s.strip())
                        else:
                            expanded_parts.append(p_clean)
                    parts = expanded_parts

                    for pi, part in enumerate(parts):
                        part = part.strip()
                        if not part:
                            continue
                        # Skip condition tokens
                        if _is_condition_token(part):
                            continue
                        # Skip yield annotations ("72%", "quant.")
                        if _YIELD_ONLY_RE.match(part):
                            continue
                        # Skip compound labels ("3a", "SM-1")
                        if _COMPOUND_LABEL_RE.match(part):
                            continue
                        # Skip single letters (false resolutions)
                        if part.lower() in _LETTER_SMILES_BLACKLIST:
                            continue

                        # Strip qualifier suffixes: "(cat.)", "(xs)",
                        # "(excess)", "(aq.)", "(anhyd.)" etc.
                        part = re.sub(
                            r'\s*\((cat\.?|xs|excess|anhyd\.?|'
                            r'aq\.?|anhydrous|catalytic|sat\.?|'
                            r'conc\.?|dil\.?)\)\s*$',
                            '', part, flags=re.IGNORECASE).strip()
                        if not part:
                            continue

                        # Skip reaction names / workup text that got
                        # through as "chemical".  Heuristic: if the
                        # token contains only Latin words (no digits,
                        # no chemical punctuation like parentheses or
                        # brackets), and it contains a known non-
                        # chemical keyword, skip it.
                        _lower = part.lower()
                        _NON_CHEM_KEYWORDS = {
                            "formylation", "coupling", "reaction",
                            "addition", "reduction", "oxidation",
                            "cyclization", "rearrangement", "workup",
                            "work-up", "quench", "extraction",
                        }
                        if any(kw in _lower for kw in _NON_CHEM_KEYWORDS):
                            continue
                        # Skip "then ..." workup prefixes
                        if _lower.startswith("then "):
                            continue

                        # Resolve SMILES
                        smi = None
                        try:
                            smi = _resolve_text_label(
                                part, use_network=use_network)
                        except Exception:
                            pass

                        # Compute MW / formula
                        mw_val = None
                        formula_val = None
                        if smi and _has_rdkit:
                            mol = Chem.MolFromSmiles(smi)
                            if mol:
                                formula_val = (
                                    rdMolDescriptors.CalcMolFormula(mol))
                                mw_val = round(Descriptors.MolWt(mol), 2)

                        # Detect solvent via reagent_db role
                        is_solvent = False
                        role = _reagent_db.role_for_name(part)
                        if role == "solvent":
                            is_solvent = True

                        cur_id = f"species_{species_counter}"
                        species_counter += 1
                        rec = SpeciesRecord(
                            id=cur_id,
                            cdxml_element_id=elem_id,
                            element_type="text",
                            smiles=smi,
                            name=part,
                            formula=formula_val,
                            mw=mw_val,
                            text_category="chemical",
                            is_solvent=is_solvent,
                            # Attach equiv only to first part of a line
                            equiv_text=line_equiv if pi == 0 else None,
                        )
                        split_records.append(rec)

                if split_records:
                    # Reclaim the pre-allocated sp_id; we use our own IDs
                    species_counter -= 1  # undo the +1 from line 937
                    # Re-number: the split_records already have correct IDs
                    # allocated above; just fix the counter
                    species_counter = int(
                        split_records[-1].id.split("_")[1]) + 1
                    for rec in split_records:
                        species_dict[rec.id] = rec
                        elem_to_species.setdefault(elem_id, []).append(
                            rec.id)
                    continue  # skip the generic record/assignment below
                else:
                    # No chemical tokens extracted — fall back to a single
                    # record with the raw text (e.g. pure condition block)
                    record = SpeciesRecord(
                        id=sp_id,
                        cdxml_element_id=elem_id,
                        element_type="text",
                        name=text_content,
                        text_category=text_cat,
                    )
            else:
                # Non-chemical text (condition_ref, citation, bioactivity)
                record = SpeciesRecord(
                    id=sp_id,
                    cdxml_element_id=elem_id,
                    element_type="text",
                    name=text_content,
                    text_category=text_cat,
                )

        else:
            # Unknown element type — skip but warn
            _log(f"Element {elem_id} has unexpected tag '{el.tag}', skipping")
            continue

        species_dict[sp_id] = record
        elem_to_species.setdefault(elem_id, []).append(sp_id)

    return species_dict, elem_to_species


def _find_nearby_label(frag: ET.Element, page: ET.Element,
                       id_map: Dict[str, ET.Element]) -> Optional[str]:
    """Find a compound label text element near the bottom of a fragment.

    Labels are typically short text elements ("1", "2a", "3") positioned
    directly below the fragment bounding box.
    """
    from ..cdxml_utils import fragment_bbox

    bbox = fragment_bbox(frag)
    if bbox is None:
        return None

    min_x, min_y, max_x, max_y = bbox
    frag_center_x = (min_x + max_x) / 2
    frag_width = max_x - min_x

    best_label = None
    best_dist = float("inf")

    for el in page:
        if el.tag != "t":
            continue
        p = el.get("p")
        if not p:
            continue
        parts = p.split()
        tx, ty = float(parts[0]), float(parts[1])

        # Label should be below the fragment (within ~25pt)
        if ty < max_y or ty > max_y + 25:
            continue
        # Label should be horizontally near the fragment center
        if abs(tx - frag_center_x) > frag_width / 2 + 15:
            continue

        text = _get_text_content(el)
        if text and _LABEL_RE.match(text):
            dist = abs(tx - frag_center_x) + abs(ty - max_y)
            if dist < best_dist:
                best_dist = dist
                best_label = text

    return best_label


# ---------------------------------------------------------------------------
# Step record building
# ---------------------------------------------------------------------------

def _build_step_records(
    raw_steps: List[_RawStep],
    elem_to_species: Dict[str, List[str]],
    species_dict: Dict[str, "SpeciesRecord"],
    id_map: Dict[str, ET.Element],
    page: ET.Element,
) -> List[StepRecord]:
    """Convert raw steps to StepRecords with species IDs and parsed text."""
    from .reaction_parser import (split_condition_text,
                                  extract_conditions_from_text)

    # Categories that should NOT be added to reagent_ids
    _NON_REAGENT_CATS = frozenset({
        "condition_ref", "yield", "compound_label",
        "footnote", "citation", "bioactivity",
    })

    def _is_reagent_species(sp_id: str) -> bool:
        """Return True if a species should be listed as a reagent."""
        sp = species_dict.get(sp_id)
        if sp is None:
            return True  # unknown → keep (shouldn't happen)
        if sp.element_type != "text":
            return True  # fragments are always reagents
        return sp.text_category not in _NON_REAGENT_CATS

    records: List[StepRecord] = []

    for idx, raw in enumerate(raw_steps):
        step = StepRecord(step_index=idx)

        # Map element IDs to species IDs
        for eid in raw.reactant_elem_ids:
            sp_ids = elem_to_species.get(eid, [])
            step.reactant_ids.extend(sp_ids)

        for eid in raw.product_elem_ids:
            sp_ids = elem_to_species.get(eid, [])
            step.product_ids.extend(sp_ids)

        # Process above/below arrow elements
        for eid in raw.above_arrow_ids:
            el = id_map.get(eid)
            if el is None:
                continue

            if el.tag == "fragment":
                sp_ids = elem_to_species.get(eid, [])
                step.reagent_ids.extend(sp_ids)
            elif el.tag == "t":
                text = _get_text_content(el)
                if not text:
                    continue
                # Text above arrow: only add chemical species as reagents
                sp_ids = elem_to_species.get(eid, [])
                reagent_sp_ids = [s for s in sp_ids if _is_reagent_species(s)]
                if reagent_sp_ids:
                    step.reagent_ids.extend(reagent_sp_ids)
                elif not sp_ids:
                    # No species at all → condition metadata
                    step.condition_text_raw.append(text)
                # For yield text above arrow, extract yield
                stripped = text.strip()
                if _YIELD_ONLY_RE.match(stripped):
                    y = _extract_yield_from_text(text)
                    if y and step.yield_text is None:
                        step.yield_text = y

        for eid in raw.below_arrow_ids:
            el = id_map.get(eid)
            if el is None:
                continue

            if el.tag == "fragment":
                sp_ids = elem_to_species.get(eid, [])
                step.reagent_ids.extend(sp_ids)
            elif el.tag == "t":
                text = _get_text_content(el)
                if not text:
                    continue

                step.condition_text_raw.append(text)

                # Extract yield from text
                y = _extract_yield_from_text(text)
                if y and step.yield_text is None:
                    step.yield_text = y

                # Split into conditions vs chemical names
                conds = extract_conditions_from_text(text)
                step.conditions.extend(conds)

                # Only add chemical text species as reagents
                sp_ids = elem_to_species.get(eid, [])
                reagent_sp_ids = [s for s in sp_ids if _is_reagent_species(s)]
                step.reagent_ids.extend(reagent_sp_ids)

        # Detect arrow style
        if raw.arrow_elem_id:
            arrow_el = _resolve_arrow(page, raw.arrow_elem_id, id_map)
            step.arrow_style = _detect_arrow_style(arrow_el)
            step.arrow_cdxml_id = raw.arrow_elem_id

        records.append(step)

    return records


# ---------------------------------------------------------------------------
# Footnote resolution
# ---------------------------------------------------------------------------

def _collect_footnotes(
    page: ET.Element,
    registered_elem_ids: Set[str],
) -> Dict[str, str]:
    """Scan page for footnote text elements and return {letter: conditions_text}.

    Footnotes are standalone text blocks like:
      "(a) morpholine (1.2 eq), Pd2(dba)3 (5 mol%), ..."
      "(b) NBS (1.1 eq), DMF, 0 C, 2 h, 95%"

    Only text elements NOT already registered as species are considered.
    """
    footnotes: Dict[str, str] = {}
    for el in page:
        if el.tag != "t":
            continue
        eid = el.get("id", "")
        if eid in registered_elem_ids:
            continue
        text = _get_text_content(el)
        if not text or len(text.strip()) <= 5:
            continue
        stripped = text.strip()
        m = _FOOTNOTE_RE.match(stripped)
        if m:
            letter = m.group(1).lower()
            # Extract the conditions part (everything after "(letter) ")
            cond_text = re.sub(r"^\([a-z]\)\s+", "", stripped,
                               count=1, flags=re.IGNORECASE)
            if cond_text:
                footnotes[letter] = cond_text
                _log(f"Footnote '{letter}': {cond_text[:60]!r}")
    return footnotes


def _resolve_footnote_conditions(
    steps: List[StepRecord],
    species_dict: Dict[str, "SpeciesRecord"],
    footnotes: Dict[str, str],
) -> None:
    """Enrich steps that use condition_ref letters with their footnote text.

    For each step, if its above/below arrow text includes condition_ref
    species (letters like "a", "b"), look up the corresponding footnote
    and populate the step's condition_text_raw, conditions, and yield_text.
    """
    if not footnotes:
        return

    from .reaction_parser import extract_conditions_from_text

    for step in steps:
        # Find condition_ref letters used by this step
        # (they were NOT added to reagent_ids, but we can find them
        # by checking species that share the step's arrow elements)
        ref_letters: List[str] = []
        for sp in species_dict.values():
            if sp.text_category != "condition_ref":
                continue
            # Check if this condition_ref letter is associated with
            # any element that belongs to this step's raw data.
            # Since we can't easily access raw step data here, instead
            # we look at all condition_ref species and match by
            # checking if their letter has a footnote.
            letters = [c.strip().lower() for c in sp.name.split(",")
                       if c.strip()]
            ref_letters.extend(letters)

        # For simplicity, resolve ALL footnotes for ALL steps that have
        # condition_ref species. The proper approach would track which
        # condition_ref belongs to which step, but that requires the
        # raw step data. Instead, we map letters to steps by position.
        # This works because steps and condition_refs are ordered.

    # Better approach: pair condition_ref species to steps via
    # elem_to_species mapping. Since we've already built steps,
    # we iterate steps and check for condition_ref species by
    # looking at which species are condition_ref and near which arrow.
    # For now, use a simpler heuristic: steps with no chemical reagents
    # and condition_ref species nearby get the footnote conditions.

    # Collect all condition_ref letters per step
    # We need to re-derive this from the species dict.
    # Strategy: condition_ref species have names like "a", "b, c".
    # Steps are ordered; condition_refs are ordered by position.
    # Match them by step index.
    all_cond_refs = sorted(
        [(sp.cdxml_element_id, sp.name.strip().lower())
         for sp in species_dict.values()
         if sp.text_category == "condition_ref"],
        key=lambda x: x[0]  # sort by element ID (roughly positional)
    )

    if not all_cond_refs:
        return

    # Map each step to its condition_ref letters
    # For schemes with N steps and N condition_ref letters, assign 1:1
    # For multi-letter refs like "a, b", split into individual letters
    ref_idx = 0
    for step in steps:
        if ref_idx >= len(all_cond_refs):
            break
        elem_id, ref_text = all_cond_refs[ref_idx]
        letters = [c.strip() for c in re.split(r"[,/\s]+", ref_text)
                   if c.strip() and len(c.strip()) == 1]
        ref_idx += 1

        for letter in letters:
            fn_text = footnotes.get(letter)
            if not fn_text:
                continue

            _log(f"Step {step.step_index}: resolving footnote "
                 f"'{letter}' → {fn_text[:60]!r}")

            step.condition_text_raw.append(f"({letter}) {fn_text}")

            # Extract yield
            y = _extract_yield_from_text(fn_text)
            if y and step.yield_text is None:
                step.yield_text = y

            # Extract conditions
            conds = extract_conditions_from_text(fn_text)
            step.conditions.extend(conds)


# ---------------------------------------------------------------------------
# Cross-scheme linkage (for wrap-repeat layouts)
# ---------------------------------------------------------------------------

def _smiles_to_inchi(smiles: str) -> Optional[str]:
    """Convert SMILES to InChI for stereo-invariant comparison.

    InChI normalises stereochemistry representation, so two SMILES
    that differ only in stereo assignment (common when ChemScript
    re-processes redrawn copies of the same intermediate) will still
    match by InChI.  Falls back to canonical SMILES if RDKit or InChI
    generation fails.
    """
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


def _link_repeated_species(steps: List[StepRecord],
                           species: Dict[str, SpeciesRecord]) -> None:
    """Link repeated structures across separate <scheme> elements.

    Wrap-repeat layouts re-draw intermediates with new element IDs.
    E.g., the product of step 2 (species_X, SMILES=AAA) appears as the
    reactant of step 3 (species_Y, SMILES=AAA) with a different ID.

    Uses InChI comparison (stereo-invariant) as the primary matcher,
    falling back to exact SMILES match.  This handles the case where
    ChemScript produces different stereo-specific SMILES for two
    drawings of the same intermediate.
    """
    # Build product species lookup keyed by InChI (primary) and SMILES (fallback)
    product_by_inchi: Dict[str, str] = {}   # InChI → species_id
    product_by_smiles: Dict[str, str] = {}  # SMILES → species_id
    for step in steps:
        for pid in step.product_ids:
            sp = species.get(pid)
            if sp and sp.smiles:
                product_by_smiles[sp.smiles] = pid
                inchi = _smiles_to_inchi(sp.smiles)
                if inchi:
                    product_by_inchi[inchi] = pid

    # Check each step's reactants for matches
    for step in steps:
        new_reactants = []
        for rid in step.reactant_ids:
            sp = species.get(rid)
            if sp and sp.smiles:
                # Try InChI match first (handles stereo differences)
                matched_id = None
                inchi = _smiles_to_inchi(sp.smiles)
                if inchi and inchi in product_by_inchi:
                    candidate = product_by_inchi[inchi]
                    if candidate != rid:
                        matched_id = candidate
                # Fallback to exact SMILES match
                if matched_id is None and sp.smiles in product_by_smiles:
                    candidate = product_by_smiles[sp.smiles]
                    if candidate != rid:
                        matched_id = candidate

                if matched_id:
                    _log(f"Linking repeated species: {rid} -> {matched_id} "
                         f"(SMILES: {sp.smiles[:40]})")
                    new_reactants.append(matched_id)
                    continue
            new_reactants.append(rid)
        step.reactant_ids = new_reactants


# ---------------------------------------------------------------------------
# Topology detection
# ---------------------------------------------------------------------------

def _detect_topology(steps: List[StepRecord]) -> str:
    """Classify scheme topology from the reaction graph.

    Returns one of: "linear", "divergent", "convergent", "parallel",
    "cycle", "mixed"
    """
    if len(steps) == 0:
        return "linear"
    if len(steps) == 1:
        return "linear"

    # Build graph: which species are reactants/products in which steps
    reactant_of: Dict[str, Set[int]] = defaultdict(set)
    product_of: Dict[str, Set[int]] = defaultdict(set)

    for i, step in enumerate(steps):
        for rid in step.reactant_ids:
            reactant_of[rid].add(i)
        for pid in step.product_ids:
            product_of[pid].add(i)

    # Check for sequential links: product of step i = reactant of step j
    sequential_links = 0
    for i in range(len(steps)):
        for j in range(i + 1, len(steps)):
            shared = set(steps[i].product_ids) & set(steps[j].reactant_ids)
            if shared:
                sequential_links += 1

    # Check divergent: same reactant in multiple steps with different products
    divergent = False
    for sp_id, step_indices in reactant_of.items():
        if len(step_indices) > 1:
            # Check that they produce different things
            product_sets = [frozenset(steps[i].product_ids)
                            for i in step_indices]
            if len(set(product_sets)) > 1:
                divergent = True
                break

    # Check convergent: one product step consumes species from multiple
    # different source steps
    convergent = False
    for sp_id, step_indices in product_of.items():
        if len(step_indices) > 1:
            convergent = True
            break

    # Check for disconnected components (parallel reactions)
    # Build adjacency: two steps are connected if they share any species
    adj: Dict[int, Set[int]] = defaultdict(set)
    for sp_id in set(list(reactant_of.keys()) + list(product_of.keys())):
        involved = reactant_of[sp_id] | product_of[sp_id]
        for si in involved:
            for sj in involved:
                if si != sj:
                    adj[si].add(sj)

    # Count connected components via BFS
    visited: Set[int] = set()
    components = 0
    for i in range(len(steps)):
        if i in visited:
            continue
        components += 1
        queue = [i]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

    # Check for cycles: product of step i = reactant of step j AND path
    # from j eventually leads back to i
    # Build directed graph: step i -> step j if product of i = reactant of j
    directed_adj: Dict[int, Set[int]] = defaultdict(set)
    for i in range(len(steps)):
        for j in range(len(steps)):
            if i == j:
                continue
            if set(steps[i].product_ids) & set(steps[j].reactant_ids):
                directed_adj[i].add(j)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = [WHITE] * len(steps)
    has_cycle = False

    def _dfs_cycle(u: int) -> bool:
        nonlocal has_cycle
        color[u] = GRAY
        for v in directed_adj.get(u, set()):
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and _dfs_cycle(v):
                return True
        color[u] = BLACK
        return False

    for i in range(len(steps)):
        if color[i] == WHITE and _dfs_cycle(i):
            has_cycle = True
            break

    if components > 1:
        if divergent or convergent or has_cycle:
            return "mixed"
        return "parallel"
    if has_cycle:
        if divergent or convergent:
            return "mixed"
        return "cycle"
    if divergent and convergent:
        return "mixed"
    if divergent:
        return "divergent"
    if convergent:
        return "convergent"
    if sequential_links > 0:
        return "linear"  # sequential chain
    return "parallel"  # no links found between steps


# ---------------------------------------------------------------------------
# Content type heuristic detection
# ---------------------------------------------------------------------------

def _detect_content_type(steps: List[StepRecord],
                         species: Dict[str, SpeciesRecord]) -> str:
    """Classify the scheme content type using heuristics.

    Returns one of: "synthesis", "sar_design", "biological_pathway",
    "target_array", "literature_comparison", "investigation", "unknown".
    """
    # No steps → static figure (target_array or standalone structure)
    if not steps:
        return "target_array"

    # Count text species by category
    cats = defaultdict(int)
    for sp in species.values():
        if sp.text_category:
            cats[sp.text_category] += 1

    n_citation = cats.get("citation", 0)
    n_bioactivity = cats.get("bioactivity", 0)
    n_condition_ref = cats.get("condition_ref", 0)
    n_chemical = cats.get("chemical", 0)
    n_text = sum(1 for sp in species.values() if sp.element_type == "text")
    n_frag = sum(1 for sp in species.values() if sp.element_type == "fragment")

    # Bioactivity-heavy → literature comparison (SAR data display)
    if n_bioactivity >= 3:
        return "literature_comparison"

    # Citation-heavy with few actual steps → literature comparison
    if n_citation >= 3 and len(steps) <= 2:
        return "literature_comparison"

    # Check for biological pathway markers (enzyme names in text)
    enzyme_pattern = re.compile(
        r"(ase\b|synthase|transferase|reductase|oxidase|kinase|"
        r"isomerase|mutase|ligase|lyase|dehydrogenase)",
        re.IGNORECASE
    )
    enzyme_count = sum(
        1 for sp in species.values()
        if sp.element_type == "text" and sp.name
        and enzyme_pattern.search(sp.name)
    )
    if enzyme_count >= 2:
        return "biological_pathway"

    # Many condition refs → likely synthetic scheme with footnoted conditions
    # (typical of thesis schemes)

    # Default: synthesis (the most common case)
    if len(steps) >= 1 and n_frag >= 2:
        return "synthesis"

    return "unknown"


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

def _species_display(sp: SpeciesRecord, include_smiles: bool = True) -> str:
    """Best available display string for a species.

    Priority: label > aligned_iupac > name > formula > SMILES.
    """
    parts = []
    if sp.label:
        parts.append(sp.label)
    elif sp.aligned_iupac:
        parts.append(sp.aligned_iupac)
    elif sp.name:
        # Use first line of name only (multi-line condition blocks)
        first_line = sp.name.split("\n")[0].strip()
        parts.append(first_line)
    elif sp.formula:
        parts.append(sp.formula)
    elif sp.smiles:
        parts.append(sp.smiles[:40])
    else:
        parts.append(sp.id)

    # When a label is used as primary, add the aligned name as qualifier
    if sp.label and sp.aligned_iupac:
        parts.append(f"({sp.aligned_iupac})")
    elif include_smiles and sp.smiles:
        # Fallback: add SMILES only if not already used as the main display
        display = parts[0]
        if display != sp.smiles and display != sp.smiles[:40]:
            parts.append(f"(SMILES: {sp.smiles})")

    return " ".join(parts)


def _generate_composite_narrative(
        sub_schemes: List["SchemeDescription"]) -> str:
    """Generate narrative for a composite (multi-panel) scheme."""
    parts = [f"Composite scheme with {len(sub_schemes)} independent "
             f"sub-schemes:"]
    parts.append("")
    for i, sub in enumerate(sub_schemes, 1):
        # Summarize each sub-scheme
        header = f"--- Sub-scheme {i} ---"
        parts.append(header)
        if sub.narrative:
            # Indent sub-narrative
            for line in sub.narrative.split("\n"):
                parts.append(f"  {line}")
        else:
            parts.append(f"  {sub.num_steps} step(s), "
                         f"{len(sub.species)} species, "
                         f"topology: {sub.topology}")
        parts.append("")
    return "\n".join(parts)


def _generate_narrative(desc: SchemeDescription) -> str:
    """Generate LLM-consumable natural language description."""
    parts = []

    # Opening line
    topo_label = {
        "linear": "linear",
        "divergent": "divergent",
        "convergent": "convergent",
        "parallel": "parallel (unrelated)",
        "mixed": "mixed-topology",
    }.get(desc.topology, desc.topology)

    # Content type label
    ct_label = {
        "synthesis": "reaction scheme",
        "sar_design": "SAR design diagram",
        "biological_pathway": "biological pathway",
        "target_array": "target structure",
        "literature_comparison": "literature comparison",
        "investigation": "mechanistic investigation",
    }.get(desc.content_type, "reaction scheme")

    if desc.num_steps == 1:
        parts.append(f"Single-step {ct_label}.")
    elif desc.num_steps == 0:
        parts.append(f"Static {ct_label} (no reaction steps).")
    else:
        parts.append(f"{desc.num_steps}-step {topo_label} {ct_label}.")

    # Per-step descriptions
    for step in desc.steps:
        step_num = step.step_index + 1
        line_parts = [f"\nStep {step_num}:"]

        # Reactants
        reactant_names = []
        for rid in step.reactant_ids:
            sp = desc.species.get(rid)
            if sp:
                reactant_names.append(_species_display(sp))
        if reactant_names:
            line_parts.append(" + ".join(reactant_names))

        # Reagents
        reagent_names = []
        for rid in step.reagent_ids:
            sp = desc.species.get(rid)
            if sp:
                reagent_names.append(
                    _species_display(sp, include_smiles=False))
        if reagent_names:
            line_parts.append(f"with {', '.join(reagent_names)}")

        # Arrow
        line_parts.append("->")

        # Products
        product_names = []
        for pid in step.product_ids:
            sp = desc.species.get(pid)
            if sp:
                product_names.append(_species_display(sp))
        if product_names:
            line_parts.append(" + ".join(product_names))

        # Conditions — combine parsed conditions with raw text fallback
        if step.conditions:
            line_parts.append(f"({', '.join(step.conditions)})")
        elif step.condition_text_raw:
            # No parsed conditions — use raw text, cleaned up
            cleaned = []
            for raw in step.condition_text_raw:
                for line in raw.split("\n"):
                    line = line.strip()
                    if line:
                        cleaned.append(line)
            if cleaned:
                line_parts.append(f"({'; '.join(cleaned)})")

        # Yield
        if step.yield_text:
            line_parts.append(f"[{step.yield_text}]")

        # Arrow style annotations
        if step.arrow_style == "failed":
            line_parts.append("[FAILED]")
        elif step.arrow_style == "dashed":
            line_parts.append("[tentative/planned]")

        # Molecular diff
        if step.molecular_diff_text:
            line_parts.append(f"[{step.molecular_diff_text}]")

        parts.append(" ".join(line_parts))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Substrate scope table detection
# ---------------------------------------------------------------------------

# Regex for scope table yield/result annotations
_SCOPE_YIELD_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
_SCOPE_MASS_RE = re.compile(r'(\d+(?:\.\d+)?)\s*mg')
_SCOPE_X_RE = re.compile(r'(?:X|R\d*)\s*=\s*(\w+)', re.IGNORECASE)
_SCOPE_LABEL_RE = re.compile(
    r'(\d+\.\d+[a-z](?:-[a-z])?(?:\')?)'  # e.g. "5.70a", "5.70k'", "4.1a-f"
    r'|'
    r'(\d+[a-z](?:\')?)'                    # e.g. "3a", "4b'"
)


def _parse_scope_annotation(text: str) -> Optional[dict]:
    """Parse a scope table text annotation into structured fields.

    Returns dict with keys: label, conditions_variant, yield_text,
    mass_text, notes.  Returns None if text doesn't look like a scope entry.
    """
    if not text or len(text) < 3:
        return None

    # Must contain at least one of: yield %, mass mg, X = halide
    has_yield = _SCOPE_YIELD_RE.search(text) is not None
    has_mass = _SCOPE_MASS_RE.search(text) is not None
    has_x = _SCOPE_X_RE.search(text) is not None
    has_label = _SCOPE_LABEL_RE.search(text) is not None

    if not (has_yield or has_mass or has_x or has_label):
        return None

    result = {}

    # Extract compound label
    m = _SCOPE_LABEL_RE.search(text)
    if m:
        result["label"] = m.group(1) or m.group(2)
    elif has_x:
        # Try numeric-only label (e.g. "4.22") when followed by X=/R= variant
        m_num = re.match(r'(\d+\.\d+)\s+', text)
        if m_num:
            result["label"] = m_num.group(1)

    # Extract conditions variant (X = I, R3 = F, etc.)
    # Capture all variable assignments in the line
    var_matches = _SCOPE_X_RE.findall(text)
    if var_matches:
        # Rebuild the full conditions string from all matches
        all_matches = list(_SCOPE_X_RE.finditer(text))
        result["conditions_variant"] = ", ".join(m.group(0) for m in all_matches)

    # Extract yield
    yields = _SCOPE_YIELD_RE.findall(text)
    if yields:
        result["yield_text"] = yields[0] + "%"

    # Extract mass
    masses = _SCOPE_MASS_RE.findall(text)
    if masses:
        result["mass_text"] = masses[0] + " mg"

    # Notes: special annotations like "Reaction failed", "Scale-up:", etc.
    notes_parts = []
    if re.search(r'\bfailed\b', text, re.IGNORECASE):
        notes_parts.append("Reaction failed")
    m = re.search(r'[Ss]cale-up[:\s]*(\d+\s*mg[,\s]*\d+\s*%)', text)
    if m:
        notes_parts.append(f"Scale-up: {m.group(1).strip()}")
    result["notes"] = "; ".join(notes_parts) if notes_parts else None

    return result


def _detect_scope_table(
    page: ET.Element,
    id_map: Dict[str, ET.Element],
    raw_steps: List,
    species_dict: Dict[str, SpeciesRecord],
    elem_to_species: Dict[str, List[str]],
    use_network: bool = True,
    use_chemscript: bool = False,
) -> Tuple[List[ScopeEntry], Dict[str, SpeciesRecord]]:
    """Detect substrate scope table entries from orphaned structures.

    Looks for:
    1. ``<bracketedgroup>`` elements with ``BracketedObjectIDs``
    2. Fragments/groups not claimed by any step
    3. Yield/result text annotations near orphaned fragments

    Returns (scope_entries, new_species) to be merged into the description.
    """
    from ..rdkit_utils import frag_to_smiles_resolved, frag_to_smiles, frag_to_mw

    # Build set of all element IDs claimed by steps
    claimed: Set[str] = set()
    for step in raw_steps:
        claimed.update(step.reactant_elem_ids)
        claimed.update(step.product_elem_ids)
        claimed.update(step.above_arrow_ids)
        claimed.update(step.below_arrow_ids)

    # Also include all elements already in species_dict
    for sp_id, sp in species_dict.items():
        claimed.add(sp.cdxml_element_id)

    # Check for bracketedgroup elements — these are the primary scope signal
    bracketed_groups = list(page.iter("bracketedgroup"))

    if not bracketed_groups:
        return [], {}

    _log(f"Found {len(bracketed_groups)} bracketedgroup element(s)")

    # Build parent map for looking up parent elements (standard ElementTree
    # does not track parent references)
    parent_map: Dict[ET.Element, ET.Element] = {}
    for parent in page.iter():
        for child in parent:
            parent_map[child] = parent

    # Collect all text elements on the page with their positions
    # We iterate over elements that contain <t> children and are NOT inside
    # a fragment (to skip text labels on atoms).
    text_elements = []
    # Find <t> elements that are direct children of page-level containers
    # (not inside <fragment> elements)
    fragment_ids: Set[str] = set()
    for frag in page.iter("fragment"):
        fragment_ids.add(id(frag))

    for t_el in page.iter("t"):
        # Check if this <t> is inside a fragment by walking parents
        in_fragment = False
        check = t_el
        while check in parent_map:
            p = parent_map[check]
            if p.tag == "fragment":
                in_fragment = True
                break
            check = p
        if in_fragment:
            continue

        text_content = _get_text_content(t_el)
        if not text_content:
            continue

        # Get bounding box from the <t> element itself or its parent
        bb = None
        t_parent = parent_map.get(t_el)
        for search_el in ([t_el, t_parent] if t_parent is not None
                          else [t_el]):
            if search_el is None:
                continue
            bb_str = search_el.get("BoundingBox", "")
            if bb_str:
                try:
                    vals = [float(v) for v in bb_str.split()]
                    bb = vals
                except (ValueError, IndexError):
                    pass
                break
            # Try position (p) attribute
            p = search_el.get("p", "")
            if p:
                try:
                    parts = p.split()
                    bb = [float(parts[0]), float(parts[1]),
                          float(parts[0]) + 50, float(parts[1]) + 10]
                except (ValueError, IndexError):
                    pass
                break

        if bb:
            t_el_id = t_el.get("id", "")
            t_parent_id = (t_parent.get("id", "")
                           if t_parent is not None else "")
            # Skip text elements already claimed by steps (conditions text)
            # Check both the <t> element ID and its parent's ID
            if (t_el_id and t_el_id in claimed) or \
               (t_parent_id and t_parent_id in claimed):
                continue
            # Use parent ID for display if available, else element ID
            el_id = t_parent_id if t_parent_id else t_el_id
            text_elements.append({
                "text": text_content,
                "id": el_id,
                "cx": (bb[0] + bb[2]) / 2,
                "cy": (bb[1] + bb[3]) / 2,
                "bb": bb,
            })

    # Parse scope annotations from text elements.
    # Strategy: first try parsing each text box as a single scope entry.
    # If a text box has multiple lines where EACH line has its own compound
    # label or X= variant, split into per-line entries (e.g. oleObject9:
    # "4.22 X = H\n4.26 X = Me" → 2 entries).  Otherwise treat the whole
    # text box as one entry (e.g. oleObject19: "5.70a\nX = I\n22 mg, 39%"
    # → 1 entry).
    scope_annotations = []
    for te in text_elements:
        full_text = te["text"]
        lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

        if len(lines) <= 1:
            # Single-line text: parse directly
            parsed = _parse_scope_annotation(full_text)
            if parsed:
                parsed["_text_id"] = te["id"]
                parsed["_cx"] = te["cx"]
                parsed["_cy"] = te["cy"]
                scope_annotations.append(parsed)
            continue

        # Multi-line: count how many lines have their own scope signal
        # (label, X=, yield, mass).  If multiple lines each have a label
        # or X= pattern, treat as per-line entries.
        line_parseds = []
        n_labels = 0
        n_x_variants = 0
        for ln in lines:
            p = _parse_scope_annotation(ln)
            line_parseds.append(p)
            if p:
                if p.get("label"):
                    n_labels += 1
                if p.get("conditions_variant"):
                    n_x_variants += 1

        # Split into per-line entries if multiple lines have labels or
        # multiple lines have X=/R= variants (table of variants)
        split_by_line = (n_labels >= 2 or n_x_variants >= 2)

        if split_by_line:
            for p in line_parseds:
                if p:
                    p["_text_id"] = te["id"]
                    p["_cx"] = te["cx"]
                    p["_cy"] = te["cy"]
                    scope_annotations.append(p)
        else:
            # Parse whole text box as one entry
            parsed = _parse_scope_annotation(full_text)
            if parsed:
                parsed["_text_id"] = te["id"]
                parsed["_cx"] = te["cx"]
                parsed["_cy"] = te["cy"]
                scope_annotations.append(parsed)

    if not scope_annotations:
        return [], {}

    _log(f"Found {len(scope_annotations)} scope annotation(s)")

    # Build scope entries directly from annotations (one per text box or
    # per line when split).  No spatial clustering needed since multi-line
    # handling already consolidates within each text element.
    scope_entries: List[ScopeEntry] = []
    new_species: Dict[str, SpeciesRecord] = {}

    for i, ann in enumerate(scope_annotations):
        entry = ScopeEntry(
            entry_id=f"scope_{i}",
            label=ann.get("label"),
            conditions_variant=ann.get("conditions_variant"),
            yield_text=ann.get("yield_text"),
            mass_text=ann.get("mass_text"),
            notes=ann.get("notes"),
        )
        scope_entries.append(entry)

    return scope_entries, new_species


# ---------------------------------------------------------------------------
# Aligned IUPAC naming enrichment
# ---------------------------------------------------------------------------

# Common heterocyclic ring names for parent normalization, ordered
# largest-first so that "benzimidazole" matches before "imidazole".
_KNOWN_RING_NAMES = [
    'benzimidazole', 'isoquinoline', 'quinazoline', 'naphthalene',
    'quinoline', 'carbazole', 'acridine',
    'morpholine', 'piperidine', 'piperazine', 'pyrimidine',
    'pyridine', 'thiophene', 'imidazole', 'thiazole', 'oxazole',
    'indole', 'furan', 'benzene',
]


def _find_preferred_parent(desc: "SchemeDescription") -> str:
    """Pre-scan all principal species to find the dominant naming parent.

    Decomposes each unique principal species (highest-MW per step) into
    its available naming parents, normalises each parent to a root ring
    name (e.g. "3-bromoquinoline" → "quinoline"), then picks the root
    ring that appears in the most compounds.

    Tiebreaker: prefer the ring present in the **final product**
    (last step's product).  In drug-discovery synthesis, the final product
    defines the target scaffold — transformations build *toward* that ring,
    while other ring substituents (morpholine, piperidine) are passengers.

    Returns the root ring name (e.g. "quinoline") or "" if none found.
    """
    try:
        from ..naming.name_decomposer import decompose_name
    except ImportError:
        return ""

    # Collect unique principal SMILES across all steps, preserving order
    principal_smiles: Dict[str, None] = {}  # ordered set
    for step in desc.steps:
        for role_ids in [step.reactant_ids, step.product_ids]:
            sps = [desc.species[sid] for sid in role_ids
                   if sid in desc.species and desc.species[sid].smiles]
            if sps:
                best = max(sps, key=lambda s: s.mw or 0)
                if best.smiles:
                    principal_smiles[best.smiles] = None

    if not principal_smiles:
        return ""

    # Find the final product SMILES (last step's principal product)
    final_product_smiles = ""
    if desc.steps:
        last_step = desc.steps[-1]
        prod_sps = [desc.species[sid] for sid in last_step.product_ids
                    if sid in desc.species and desc.species[sid].smiles]
        if prod_sps:
            final_product_smiles = max(prod_sps,
                                       key=lambda s: s.mw or 0).smiles or ""

    # Decompose each and collect all available parent names
    from collections import Counter
    ring_counts: Counter = Counter()
    final_prod_rings: set = set()  # rings in the final product

    for smi in principal_smiles:
        try:
            r = decompose_name(smi)
        except Exception:
            continue

        # Gather all parent strings for this compound
        parents: set = set()
        if r.canonical_parent:
            parents.add(r.canonical_parent.lower())
        for alt in r.alternatives:
            if alt.valid and alt.parent_name:
                parents.add(alt.parent_name.lower())
        # Also check the name itself for ring stems (handles cases
        # where the ring appears in complex parent names like
        # "4-(4-phenylquinolin-2-yl)morpholine")
        all_names = [r.canonical_name.lower()]
        all_names.extend(a.name.lower() for a in r.alternatives if a.valid)

        # Normalise: for each parent/name, find which root ring it contains
        compound_rings: set = set()
        for text in list(parents) + all_names:
            for ring in _KNOWN_RING_NAMES:
                # Match both full form ("quinoline") and stem ("quinolin")
                ring_stem = ring.rstrip('e')
                if ring in text or ring_stem in text:
                    compound_rings.add(ring)
        ring_counts.update(compound_rings)

        # Remember which rings the final product has
        if smi == final_product_smiles:
            final_prod_rings = compound_rings.copy()

    if not ring_counts:
        return ""

    # Pick the ring present in the most compounds.
    # Tiebreaker: prefer rings from the final product (the target scaffold),
    # then larger ring systems.
    best_ring = max(
        ring_counts,
        key=lambda r: (ring_counts[r],
                       1 if r in final_prod_rings else 0,
                       len(r)))
    _log(f"Preferred naming parent: {best_ring} "
         f"(in {ring_counts[best_ring]}/{len(principal_smiles)} compounds"
         f"{', final-product' if best_ring in final_prod_rings else ''})")
    return best_ring


def _enrich_aligned_names(desc: "SchemeDescription") -> None:
    """Populate aligned_iupac on species and molecular_diff_text on steps.

    For each step, finds the principal SM/product pair (largest MW),
    runs ``find_aligned_names`` to get MCS-based aligned IUPAC names,
    and fills ``format_molecular_diff`` text on the step.

    Uses a global "preferred parent" strategy: pre-scans all principal
    species to find the dominant ring system, then passes it as a hint
    to every step so the entire scheme uses a consistent naming backbone.

    Gracefully degrades if aligned_namer is unavailable.
    """
    try:
        from ..naming.aligned_namer import (
            find_aligned_names,
            format_molecular_diff,
        )
    except ImportError:
        return

    # Find the globally preferred naming parent
    preferred_parent = _find_preferred_parent(desc)

    for step in desc.steps:
        sm_list = [desc.species[sid] for sid in step.reactant_ids
                   if sid in desc.species and desc.species[sid].smiles]
        prod_list = [desc.species[sid] for sid in step.product_ids
                     if sid in desc.species and desc.species[sid].smiles]

        if not sm_list or not prod_list:
            continue

        # Principal pair: largest MW (the "core" substrate, not additives)
        sm_sp = max(sm_list, key=lambda s: s.mw or 0)
        prod_sp = max(prod_list, key=lambda s: s.mw or 0)

        if not sm_sp.smiles or not prod_sp.smiles:
            continue

        try:
            ar = find_aligned_names(sm_sp.smiles, prod_sp.smiles,
                                    preferred_parent=preferred_parent or None)

            # Only set aligned_iupac if not already assigned by a previous
            # step.  This preserves naming consistency for intermediates.
            if ar.best_sm_name and not sm_sp.aligned_iupac:
                sm_sp.aligned_iupac = ar.best_sm_name
            if ar.best_prod_name and not prod_sp.aligned_iupac:
                prod_sp.aligned_iupac = ar.best_prod_name

            diff_text = format_molecular_diff(
                sm_sp.smiles, prod_sp.smiles, ar)
            if diff_text:
                step.molecular_diff_text = diff_text
        except Exception:
            # Non-critical enrichment — don't break scheme reading
            pass


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def read_scheme(
    cdxml_path: str,
    use_network: bool = True,
    use_chemscript: bool = False,
    verbose: bool = False,
    segment: bool = False,
    _scheme_filter: Optional[Set[str]] = None,
) -> SchemeDescription:
    """Read a CDXML reaction scheme and return a structured description.

    Primary path: uses <scheme><step> attributes if present.
    Fallback: geometry-based arrow detection.

    Parameters
    ----------
    cdxml_path : str
        Path to CDXML file.
    use_network : bool
        Allow PubChem network lookups for text label resolution.
    use_chemscript : bool
        Use ChemScript for SMILES extraction (best abbreviation resolution,
        requires ChemDraw 16+ on Windows).  Falls back to RDKit-based
        resolution if ChemScript is unavailable.
    verbose : bool
        Print debug info to stderr.
    segment : bool
        Auto-segment multi-panel CDXML files into independent sub-schemes.
        When True, the returned SchemeDescription may have a non-empty
        ``sub_schemes`` list with independent sub-scheme descriptions.
    _scheme_filter : set of str, optional
        Internal parameter used by the segmenter.  If provided, only
        process ``<scheme>`` elements whose ``id`` is in this set.

    Returns
    -------
    SchemeDescription
        Complete structured description with species, steps, topology,
        and narrative.
    """
    global _verbose
    _verbose = verbose

    from ..cdxml_utils import parse_cdxml, build_id_map

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return SchemeDescription(
            source_file=os.path.abspath(cdxml_path),
            warnings=["No <page> element found in CDXML"],
        )

    id_map = build_id_map(page)

    # -----------------------------------------------------------------------
    # Auto-segmentation: detect independent sub-schemes
    # -----------------------------------------------------------------------
    if segment and _scheme_filter is None:
        from .scheme_segmenter import segment_scheme as _segment_scheme
        seg_result = _segment_scheme(cdxml_path, verbose=verbose)
        if seg_result.is_multi_panel and seg_result.num_segments > 1:
            _log(f"Multi-panel detected: {seg_result.num_segments} segments")
            sub_schemes = []
            all_species: Dict[str, SpeciesRecord] = {}
            all_steps: List[StepRecord] = []
            for seg in seg_result.segments:
                filter_ids = set(seg.scheme_element_ids)
                sub_desc = read_scheme(
                    cdxml_path,
                    use_network=use_network,
                    use_chemscript=use_chemscript,
                    verbose=verbose,
                    segment=False,
                    _scheme_filter=filter_ids,
                )
                sub_desc.source_file = os.path.abspath(cdxml_path)
                sub_schemes.append(sub_desc)
                all_species.update(sub_desc.species)
                all_steps.extend(sub_desc.steps)

            # Build composite description
            total_steps = sum(s.num_steps for s in sub_schemes)
            composite = SchemeDescription(
                source_file=os.path.abspath(cdxml_path),
                topology="parallel",
                content_type="composite",
                num_steps=total_steps,
                species=all_species,
                steps=all_steps,
                sub_schemes=sub_schemes,
                narrative=_generate_composite_narrative(sub_schemes),
            )
            return composite

    # Dual-strategy parsing:
    #  - Geometry engine: works on all files, including pycdxml-converted CDX
    #  - Step-attribute path: uses ChemDraw's <scheme><step> when available
    #
    # Preference: use step attributes when available (they encode the
    # author's explicit grouping).  Use geometry engine as primary when
    # step attributes are missing (pycdxml output, manual drawings).
    # The geometry engine also provides layout_pattern and confidence metadata
    # regardless of which strategy is used for the final assignment.
    parse_method = ""
    layout_pattern = None
    confidence_map: Dict[str, float] = {}

    # Always run geometry engine (for metadata + fallback)
    geo_steps = _parse_from_spatial_engine(page, id_map)
    _sa_meta = getattr(_parse_from_spatial_engine, "_last_meta", {})
    layout_pattern = _sa_meta.get("layout_pattern")
    confidence_map = _sa_meta.get("confidences", {})
    if geo_steps:
        _log(f"Spatial engine: {len(geo_steps)} step(s), "
             f"layout={layout_pattern}")

    # Try step-attribute path
    attr_steps = _parse_from_step_attributes(page, id_map,
                                             scheme_filter=_scheme_filter)
    if attr_steps:
        _log(f"Step-attribute path: {len(attr_steps)} step(s)")

    # Choose strategy
    if attr_steps:
        raw_steps = attr_steps
        parse_method = "step_attribute"
    elif geo_steps:
        raw_steps = geo_steps
        parse_method = "geometry"
    else:
        raw_steps = []

    if not raw_steps:
        # No reaction steps — still enumerate all structures on the page
        species_dict = _build_static_species_registry(
            page, id_map, use_network=use_network,
            use_chemscript=use_chemscript)
        content_type = "target_array" if species_dict else "unknown"
        desc = SchemeDescription(
            source_file=os.path.abspath(cdxml_path),
            content_type=content_type,
            species=species_dict,
            warnings=["No reaction steps found "
                       "(no <step> attributes, no arrows)"],
        )
        desc.narrative = _generate_narrative(desc)
        return desc

    # Recover orphan transition arrows (serpentine vertical connectors
    # that the renderer places outside <scheme><step> elements)
    if parse_method == "step_attribute":
        pre_count = len(raw_steps)
        raw_steps = _recover_orphan_transition_steps(page, raw_steps, id_map)
        if len(raw_steps) > pre_count:
            _log(f"Recovered {len(raw_steps) - pre_count} orphan "
                 f"transition step(s)")

    _log(f"Found {len(raw_steps)} step(s)")

    # Build species registry
    species_dict, elem_to_species = _build_species_registry(
        raw_steps, id_map, page,
        use_network=use_network,
        use_chemscript=use_chemscript,
    )
    _log(f"Built registry with {len(species_dict)} species")

    # Convert to step records
    steps = _build_step_records(raw_steps, elem_to_species, species_dict,
                                id_map, page)

    # Resolve footnote conditions (e.g. "(a) Pd2(dba)3, BINAP, ...")
    # for steps that use condition_ref letters
    registered_eids = set(elem_to_species.keys())
    footnotes = _collect_footnotes(page, registered_eids)
    if footnotes:
        _resolve_footnote_conditions(steps, species_dict, footnotes)
        _log(f"Resolved {len(footnotes)} footnote(s)")

    # Link repeated structures across separate <scheme> elements
    # (wrap-repeat layouts re-draw intermediates with new element IDs)
    _link_repeated_species(steps, species_dict)

    # Detect topology
    topology = _detect_topology(steps)
    _log(f"Detected topology: {topology}")

    # Detect content type
    content_type = _detect_content_type(steps, species_dict)
    _log(f"Detected content type: {content_type}")

    # Detect substrate scope table (orphaned structures + yield annotations)
    scope_entries, scope_species = _detect_scope_table(
        page, id_map, raw_steps, species_dict, elem_to_species,
        use_network=use_network, use_chemscript=use_chemscript,
    )
    if scope_species:
        species_dict.update(scope_species)
    if scope_entries:
        _log(f"Detected {len(scope_entries)} scope table entries")
        if content_type == "synthesis":
            content_type = "substrate_scope"

    desc = SchemeDescription(
        source_file=os.path.abspath(cdxml_path),
        topology=topology,
        content_type=content_type,
        num_steps=len(steps),
        species=species_dict,
        steps=steps,
        scope_entries=scope_entries,
        layout_pattern=layout_pattern,
        parse_method=parse_method,
        assignment_confidences=confidence_map,
    )

    # Add warnings for low-confidence assignments
    for elem_id, conf in confidence_map.items():
        if conf < 0.5:
            desc.warnings.append(
                f"Low confidence ({conf:.2f}) assigning element {elem_id}")

    # Enrich with aligned IUPAC names + molecular diffs
    _enrich_aligned_names(desc)

    # Generate narrative
    desc.narrative = _generate_narrative(desc)

    return desc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scheme_reader",
        description="Read a CDXML reaction scheme and produce structured JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python -m cdxml_toolkit.scheme_reader scheme.cdxml
  python -m cdxml_toolkit.scheme_reader scheme.cdxml -o description.json
  python -m cdxml_toolkit.scheme_reader scheme.cdxml --narrative-only
""",
    )
    parser.add_argument("input", help="Input CDXML file with reaction scheme")
    parser.add_argument("-o", "--output",
                        help="Output JSON path (default: stdout)")
    parser.add_argument("--pretty", action="store_true", default=True,
                        help="Pretty-print JSON (default: yes)")
    parser.add_argument("--no-pretty", dest="pretty", action="store_false")
    parser.add_argument("--no-network", action="store_true",
                        help="Disable network lookups (PubChem, OPSIN)")
    parser.add_argument("--chemscript", action="store_true",
                        help="Use ChemScript for SMILES (best abbreviation "
                             "resolution, requires ChemDraw 16+ on Windows)")
    parser.add_argument("--narrative-only", action="store_true",
                        help="Print only the narrative text to stdout")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print debug info to stderr")

    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    desc = read_scheme(
        args.input,
        use_network=not args.no_network,
        use_chemscript=args.chemscript,
        verbose=args.verbose,
    )

    if args.narrative_only:
        print(desc.narrative)
        return 0

    if args.output:
        desc.to_json(args.output, pretty=args.pretty)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        out = json.dumps(desc.to_dict(), indent=2 if args.pretty else None,
                         ensure_ascii=False)
        sys.stdout.buffer.write(out.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
