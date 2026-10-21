#!/usr/bin/env python3
"""
eln_enrichment.py -- Enrich a polished reaction scheme with ELN CSV data.

Given a polished CDXML (from scheme_polisher) and a Findmolecule ELN CSV,
annotates the scheme with:
  - Equivalents on each reagent (text labels and above-arrow structures)
  - A "run arrow" below the scheme showing SM mass and product yield

Two-phase design:
  Phase A (before layout): Inject equivalents into text content so that
    text widths are correct for arrow length computation.
  Phase B (after layout): Add run arrow, above-arrow eq labels, and
    side eq labels using finalized positions.

Usage (via scheme_polisher_v2.py):
    python scheme_polisher_v2.py input.cdx --eln-csv experiment.csv -o out.cdxml
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

from ...cdxml_utils import (
    fragment_bbox,
    fragment_bbox_with_label_extension,
    fragment_bottom_has_hanging_label,
    recompute_text_bbox,
)
from ...constants import (
    CDXML_FOOTER,
    CDXML_MINIMAL_HEADER,
    MW_MATCH_TOLERANCE,
    MW_MATCH_TOLERANCE_LOOSE,
)
from ...text_formatting import build_formatted_s_xml


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MatchedReagent:
    """A CSV reagent matched to a scheme element."""
    csv_name: str
    csv_equiv: str          # raw equiv string from CSV, e.g. "2.0"
    csv_mass: str           # e.g. "2.15 g"
    csv_is_substrate: bool
    csv_mw: float
    scheme_element_id: str  # id of the matched <t> or <fragment>
    scheme_position: str    # "reactant", "above_arrow", "below_arrow"
    scheme_display: str     # display text on the scheme (e.g. "Cs2CO3")
    is_solvent: bool = False


@dataclass
class EnrichmentData:
    """All enrichment info extracted from CSV + scheme matching."""
    matches: List[MatchedReagent] = field(default_factory=list)
    substrate: Optional[MatchedReagent] = None  # equiv=1.0, is_substrate
    sm_mass: str = ""           # e.g. "2.15 g"
    product_obtained: str = ""  # e.g. "1.6 g"
    product_yield: str = ""     # e.g. "72%"
    solvent_names: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_equiv(equiv_str: str) -> str:
    """Format equivalents for display: '2.0' -> '2', '0.05' -> '0.05'."""
    try:
        val = float(equiv_str)
        if val == int(val) and val >= 1:
            return str(int(val))
        # Strip trailing zeros but keep significant decimals
        formatted = f"{val:g}"
        return formatted
    except (ValueError, TypeError):
        return equiv_str


def _get_text_content(el: ET.Element) -> str:
    """Extract concatenated text from all <s> children of a <t> element."""
    parts = []
    for s in el.iter("s"):
        if s.text:
            parts.append(s.text)
    return "".join(parts).strip()


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, strip whitespace."""
    return re.sub(r'\s+', ' ', name.strip().lower())


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


# ---------------------------------------------------------------------------
# Step 1: CSV-to-scheme matching
# ---------------------------------------------------------------------------

def match_csv_to_scheme(
    root: ET.Element,
    csv_path: str,
    verbose: bool = False,
) -> EnrichmentData:
    """Match CSV reagents/solvents/product to scheme elements.

    Uses two passes:
      1. Name match via reagent_db.resolve_display()
      2. MW match via RDKit (fallback for CSV names that don't resolve)

    Parameters
    ----------
    root : ET.Element
        Parsed CDXML root element (after polish_scheme).
    csv_path : str
        Path to Findmolecule ELN CSV file.
    verbose : bool
        Print matching details to stderr.

    Returns
    -------
    EnrichmentData with all matches + product info.
    """
    from ...perception.eln_csv_parser import parse_eln_csv
    from ...resolve.reagent_db import get_reagent_db

    def log(msg: str):
        if verbose:
            print(f"  [enrich] {msg}", file=sys.stderr)

    # Parse CSV
    exp = parse_eln_csv(csv_path)
    if exp is None:
        log("WARNING: Could not parse CSV")
        return EnrichmentData()

    db = get_reagent_db()
    enrichment = EnrichmentData()

    # Collect solvent names from CSV
    for s in exp.solvents:
        enrichment.solvent_names.append(_normalize_name(s.name))

    # Product info
    if exp.product:
        enrichment.product_obtained = exp.product.obtained_mass.strip()
        enrichment.product_yield = exp.product.yield_pct.strip()

    # --- Build scheme element inventory ---
    page = root.find("page")
    if page is None:
        return enrichment

    scheme = page.find("scheme")
    step = scheme.find("step") if scheme is not None else None
    if step is None:
        return enrichment

    reactant_ids = step.get("ReactionStepReactants", "").split()
    product_ids = step.get("ReactionStepProducts", "").split()
    above_ids = step.get("ReactionStepObjectsAboveArrow", "").split()
    below_ids = step.get("ReactionStepObjectsBelowArrow", "").split()

    # Build id -> (element, position) map
    id_to_el: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    # Build scheme_elements: list of (element_id, position, display_text, smiles_or_none, mw_or_none)
    scheme_elements: List[Dict] = []

    def _add_element(eid: str, position: str):
        el = id_to_el.get(eid)
        if el is None:
            return
        if el.tag == "t":
            text = _get_text_content(el)
            # For merged text blocks, split into lines
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines:
                scheme_elements.append({
                    "element_id": eid,
                    "position": position,
                    "display": line,
                    "tag": "t",
                    "is_line_in_merged": len(lines) > 1,
                })
        elif el.tag == "fragment":
            # Get the display name from the fragment (check if it was replaced by text)
            # For fragments, we need to look at what the polisher classified it as
            # The display name might be derived from SMILES or classification
            # For matching, we'll try to compute MW from atom coordinates
            frag_mw = _compute_fragment_mw(el)
            scheme_elements.append({
                "element_id": eid,
                "position": position,
                "display": None,
                "tag": "fragment",
                "mw": frag_mw,
                "is_line_in_merged": False,
            })

    for rid in reactant_ids:
        _add_element(rid, "reactant")
    for eid in above_ids:
        _add_element(eid, "above_arrow")
    for eid in below_ids:
        _add_element(eid, "below_arrow")

    # --- Pass 1: Name match ---
    matched_csv_indices = set()
    matched_scheme_ids = set()

    for i, reagent in enumerate(exp.reactants):
        csv_display = db.resolve_display(reagent.name)
        csv_norm = _normalize_name(csv_display)
        csv_name_norm = _normalize_name(reagent.name)

        for se in scheme_elements:
            if se["element_id"] in matched_scheme_ids and not se["is_line_in_merged"]:
                continue
            if se["tag"] != "t" or se["display"] is None:
                continue

            scheme_display = se["display"]
            scheme_norm = _normalize_name(scheme_display)

            # Compare: resolved display vs scheme text (ignoring existing equiv annotations)
            scheme_clean = re.sub(r'\s*\([\d.]+\s*eq\.\)\s*$', '', scheme_norm)

            if csv_norm == scheme_clean or csv_name_norm == scheme_clean:
                match = MatchedReagent(
                    csv_name=reagent.name,
                    csv_equiv=reagent.equiv,
                    csv_mass=reagent.mass,
                    csv_is_substrate=reagent.is_substrate,
                    csv_mw=reagent.mw,
                    scheme_element_id=se["element_id"],
                    scheme_position=se["position"],
                    scheme_display=scheme_display,
                    is_solvent=_normalize_name(reagent.name) in enrichment.solvent_names,
                )
                enrichment.matches.append(match)
                matched_csv_indices.add(i)
                if not se["is_line_in_merged"]:
                    matched_scheme_ids.add(se["element_id"])
                log(f"Name match: CSV '{reagent.name}' -> scheme '{scheme_display}' "
                    f"(pos={se['position']}, equiv={reagent.equiv})")
                break

    # Also match solvents by name (they appear in scheme text but don't get equiv)
    for solvent in exp.solvents:
        solv_display = db.resolve_display(solvent.name)
        solv_norm = _normalize_name(solv_display)
        solv_name_norm = _normalize_name(solvent.name)

        for se in scheme_elements:
            if se["tag"] != "t" or se["display"] is None:
                continue
            scheme_norm = _normalize_name(se["display"])
            scheme_clean = re.sub(r'\s*\([\d.]+\s*eq\.\)\s*$', '', scheme_norm)
            if solv_norm == scheme_clean or solv_name_norm == scheme_clean:
                log(f"Solvent match: CSV '{solvent.name}' -> scheme '{se['display']}'")
                break

    # --- Pass 2: MW match (fallback for unmatched CSV reactants) ---
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors
        _has_rdkit = True
    except ImportError:
        _has_rdkit = False

    if _has_rdkit:
        for i, reagent in enumerate(exp.reactants):
            if i in matched_csv_indices:
                continue

            csv_mw = reagent.mw
            if csv_mw <= 0:
                continue

            # Try to match against fragment MW — pick closest within window
            best_se = None
            best_delta = MW_MATCH_TOLERANCE  # threshold
            for se in scheme_elements:
                se_id = se["element_id"]
                if se_id in matched_scheme_ids:
                    continue
                if se["tag"] != "fragment":
                    continue
                frag_mw = se.get("mw")
                if frag_mw is None or frag_mw <= 0:
                    continue
                delta = abs(frag_mw - csv_mw)
                if delta < best_delta:
                    best_delta = delta
                    best_se = se
            if best_se is not None:
                se_id = best_se["element_id"]
                frag_mw = best_se["mw"]
                match = MatchedReagent(
                    csv_name=reagent.name,
                    csv_equiv=reagent.equiv,
                    csv_mass=reagent.mass,
                    csv_is_substrate=reagent.is_substrate,
                    csv_mw=reagent.mw,
                    scheme_element_id=se_id,
                    scheme_position=best_se["position"],
                    scheme_display=f"fragment_{se_id}",
                    is_solvent=False,
                )
                enrichment.matches.append(match)
                matched_csv_indices.add(i)
                matched_scheme_ids.add(se_id)
                log(f"MW match: CSV '{reagent.name}' (MW={csv_mw:.1f}) -> "
                    f"fragment {se_id} (MW={frag_mw:.1f}, delta={best_delta:.2f}, "
                    f"pos={best_se['position']}, equiv={reagent.equiv})")

            # Also try matching against text elements by resolving their
            # display name to SMILES (via reagent_db) and computing MW
            # Pick closest match within window
            if i not in matched_csv_indices:
                best_text_se = None
                best_text_mw = None
                best_text_delta = MW_MATCH_TOLERANCE  # threshold
                best_text_display = None
                for se in scheme_elements:
                    if se["tag"] != "t" or se["display"] is None:
                        continue
                    se_id = se["element_id"]
                    scheme_display = se["display"]
                    # Check not already matched as a line in merged text
                    already_matched_line = False
                    for existing in enrichment.matches:
                        if (existing.scheme_element_id == se_id
                                and existing.scheme_display == scheme_display):
                            already_matched_line = True
                            break
                    if already_matched_line:
                        continue
                    # Look up the entry in reagent_db by scheme display name
                    entry = db.entry_for_name(
                        _normalize_name(scheme_display).replace(" ", "")
                    )
                    if entry is None:
                        continue
                    smi_val = entry.get("smiles")
                    if not smi_val:
                        continue
                    smiles_list = smi_val if isinstance(smi_val, list) else [smi_val]
                    for smi in smiles_list:
                        mol = Chem.MolFromSmiles(smi)
                        if mol:
                            mw = Descriptors.ExactMolWt(mol)
                            delta = abs(mw - csv_mw)
                            if delta < best_text_delta:
                                best_text_delta = delta
                                best_text_se = se
                                best_text_mw = mw
                                best_text_display = scheme_display
                if best_text_se is not None:
                    match = MatchedReagent(
                        csv_name=reagent.name,
                        csv_equiv=reagent.equiv,
                        csv_mass=reagent.mass,
                        csv_is_substrate=reagent.is_substrate,
                        csv_mw=reagent.mw,
                        scheme_element_id=best_text_se["element_id"],
                        scheme_position=best_text_se["position"],
                        scheme_display=best_text_display,
                        is_solvent=False,
                    )
                    enrichment.matches.append(match)
                    matched_csv_indices.add(i)
                    log(f"MW-via-SMILES match: CSV '{reagent.name}' "
                        f"(MW={csv_mw:.1f}) -> scheme '{best_text_display}' "
                        f"(MW={best_text_mw:.1f}, delta={best_text_delta:.2f})")

    # --- Identify substrate (SM for run arrow) ---
    # Use the reagent with equiv=1.0 and is_substrate=True
    # If multiple substrates, use the one with largest MW (main SM)
    substrate_candidates = [
        m for m in enrichment.matches
        if m.csv_is_substrate
    ]
    if substrate_candidates:
        # Prefer equiv=1.0 substrate; if none, use largest MW
        eq1_substrates = [m for m in substrate_candidates
                          if _format_equiv(m.csv_equiv) == "1"]
        if eq1_substrates:
            enrichment.substrate = max(eq1_substrates, key=lambda m: m.csv_mw)
        else:
            enrichment.substrate = max(substrate_candidates, key=lambda m: m.csv_mw)
        enrichment.sm_mass = enrichment.substrate.csv_mass.strip()
        log(f"Substrate: '{enrichment.substrate.csv_name}' "
            f"(mass={enrichment.sm_mass})")

    # Report unmatched
    for i, reagent in enumerate(exp.reactants):
        if i not in matched_csv_indices:
            log(f"WARNING: Unmatched CSV reactant: '{reagent.name}' "
                f"(MW={reagent.mw})")

    return enrichment


def _compute_fragment_mw(frag: ET.Element) -> Optional[float]:
    """Compute MW from a CDXML fragment element.

    Three-tier resolution:
      1. ChemScript SMILES → RDKit MolWt (exact average MW)
      2. RDKit-direct from CDXML fragment (no ChemScript needed)
      3. Manual atom counting (less accurate for heteroatoms)
    Returns None if fragment has no atoms.
    """
    # --- Tier 1: ChemScript + RDKit ---
    mw = _compute_fragment_mw_via_smiles(frag)
    if mw is not None:
        return mw

    # --- Tier 2: RDKit-direct from CDXML fragment ---
    mw = _compute_fragment_mw_rdkit_direct(frag)
    if mw is not None:
        return mw

    # --- Tier 3: manual atom counting ---
    return _compute_fragment_mw_manual(frag)


def _compute_fragment_mw_rdkit_direct(frag: ET.Element) -> Optional[float]:
    """Compute MW directly from CDXML fragment via RDKit (no ChemScript).

    Uses rdkit_utils.frag_to_mw() which converts CDXML atoms/bonds to
    an RDKit Mol and computes average MW.  Returns None if the fragment
    contains abbreviation groups (element 0 / dummy atoms).
    """
    try:
        from ...rdkit_utils import frag_to_mw
        return frag_to_mw(frag)
    except ImportError:
        return None
    except Exception:
        return None


def _compute_fragment_mw_via_smiles(frag: ET.Element) -> Optional[float]:
    """Compute MW via ChemScript SMILES export + RDKit."""
    try:
        from ...chemdraw.chemscript_bridge import ChemScriptBridge
        from rdkit import Chem
        from rdkit.Chem import Descriptors
    except ImportError:
        return None

    import tempfile

    # Wrap fragment in minimal CDXML document
    frag_xml = ET.tostring(frag, encoding="unicode")
    cdxml_doc = (
        CDXML_MINIMAL_HEADER + "\n<page id=\"1\">\n"
        + frag_xml
        + "\n</page>\n" + CDXML_FOOTER
    )

    try:
        bridge = ChemScriptBridge()
        # Write temp CDXML file for ChemScript
        tmp = tempfile.NamedTemporaryFile(
            suffix=".cdxml", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(cdxml_doc)
        tmp.close()

        smiles = bridge.write_data(tmp.name, "chemical/x-smiles")
        os.unlink(tmp.name)

        if not smiles or not smiles.strip():
            return None

        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            return None

        # Use average MW (MolWt) to match CSV values, not monoisotopic
        return Descriptors.MolWt(mol)
    except Exception:
        return None


def _compute_fragment_mw_manual(frag: ET.Element) -> Optional[float]:
    """Fallback: compute approximate MW from CDXML atom elements.

    Counts atoms by element type, adds implicit H from NumHydrogens
    attribute.  Only estimates implicit H for carbon (valence 4);
    heteroatom implicit H requires NumHydrogens to be present.
    """
    ATOMIC_WEIGHTS = {
        1: 1.008, 5: 10.81, 6: 12.011, 7: 14.007, 8: 15.999,
        9: 18.998, 14: 28.086, 15: 30.974, 16: 32.065, 17: 35.453,
        35: 79.904, 53: 126.904, 11: 22.990, 19: 39.098,
        46: 106.42, 55: 132.905, 29: 63.546, 30: 65.38,
    }

    def _collect_atoms_bonds(container):
        nodes = {}  # id -> Element
        bonds = []
        for n in container.findall("n"):
            nid = n.get("id", "")
            node_type = n.get("NodeType", "")
            if node_type == "Fragment":
                inner = n.find("fragment")
                if inner is not None:
                    inner_nodes, inner_bonds = _collect_atoms_bonds(inner)
                    nodes.update(inner_nodes)
                    bonds.extend(inner_bonds)
                continue
            if node_type == "ExternalConnectionPoint":
                continue
            if nid:
                nodes[nid] = n
        bonds.extend(container.findall("b"))
        return nodes, bonds

    all_nodes, all_bonds = _collect_atoms_bonds(frag)

    total_mw = 0.0
    atom_count = 0

    for nid, n in all_nodes.items():
        elem = n.get("Element", "6")
        try:
            elem_num = int(elem)
        except ValueError:
            elem_num = 6

        weight = ATOMIC_WEIGHTS.get(elem_num, 0)
        total_mw += weight
        atom_count += 1

        nh = n.get("NumHydrogens")
        if nh is not None:
            try:
                total_mw += int(nh) * 1.008
            except ValueError:
                pass
        elif elem_num == 6:
            bond_count = 0
            for b in all_bonds:
                if b.get("B") == nid or b.get("E") == nid:
                    order = b.get("Order", "1")
                    try:
                        bond_count += int(order)
                    except ValueError:
                        bond_count += 1
            implicit_h = max(0, 4 - bond_count)
            total_mw += implicit_h * 1.008

    return total_mw if atom_count > 0 else None


# ---------------------------------------------------------------------------
# Step 1.5: Reposition non-substrate reactant to above-arrow
# ---------------------------------------------------------------------------

def reposition_reactant_above_arrow(
    root: ET.Element,
    csv_path: str,
    verbose: bool = False,
) -> bool:
    """Move a non-substrate reactant from left-of-arrow to above-arrow.

    When two atom-contributing structures sit to the left of the arrow
    and nothing is drawn above it, the non-substrate (the one that is
    NOT 1.0 eq in the ELN CSV) should be moved above the arrow.  The
    substrate stays on the left.

    Only modifies ``<step>`` metadata (``ReactionStepReactants`` and
    ``ReactionStepObjectsAboveArrow``).  Physical repositioning is
    handled downstream by ``reaction_cleanup``'s ``_stack_above_below``.

    Parameters
    ----------
    root : ET.Element
        Parsed CDXML root (after scheme_polisher).
    csv_path : str
        Path to Findmolecule ELN CSV file.
    verbose : bool
        Print details to stderr.

    Returns
    -------
    True if a fragment was repositioned, False otherwise.
    """
    from ...perception.eln_csv_parser import parse_eln_csv

    def log(msg: str):
        if verbose:
            print(f"  [reposition] {msg}", file=sys.stderr)

    # Parse CSV to identify substrate
    exp = parse_eln_csv(csv_path)
    if exp is None:
        log("Could not parse CSV")
        return False

    # Find step metadata
    page = root.find("page")
    if page is None:
        return False
    scheme = page.find("scheme")
    step = scheme.find("step") if scheme is not None else None
    if step is None:
        return False

    reactant_ids = step.get("ReactionStepReactants", "").split()
    above_ids = step.get("ReactionStepObjectsAboveArrow", "").split()

    # Build id -> element map
    id_to_el: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    # Identify fragment elements among reactants and above-arrow
    reactant_frags = []  # (id, element)
    for rid in reactant_ids:
        el = id_to_el.get(rid)
        if el is not None and el.tag == "fragment":
            reactant_frags.append((rid, el))

    above_frags = []
    for aid in above_ids:
        el = id_to_el.get(aid)
        if el is not None and el.tag == "fragment":
            above_frags.append((aid, el))

    # Condition: 2+ fragment reactants, 0 fragment above arrow
    if len(reactant_frags) < 2 or len(above_frags) > 0:
        if verbose and len(reactant_frags) < 2:
            log(f"Only {len(reactant_frags)} fragment reactant(s), "
                f"no repositioning needed")
        if verbose and len(above_frags) > 0:
            log(f"{len(above_frags)} fragment(s) already above arrow, "
                f"no repositioning needed")
        return False

    log(f"Found {len(reactant_frags)} fragment reactant(s), "
        f"0 fragments above arrow")

    # Find the substrate from CSV (equiv=1.0 and/or is_substrate=True)
    substrate_mw = None
    substrate_name = None
    for reagent in exp.reactants:
        if reagent.is_substrate:
            substrate_mw = reagent.mw
            substrate_name = reagent.name
            break
    if substrate_mw is None:
        # Fallback: look for equiv=1.0
        for reagent in exp.reactants:
            try:
                eq = float(reagent.equiv)
            except (ValueError, TypeError):
                continue
            if abs(eq - 1.0) < 0.01:
                substrate_mw = reagent.mw
                substrate_name = reagent.name
                break
    if substrate_mw is None or substrate_mw <= 0:
        log("Could not identify substrate MW from CSV")
        return False

    log(f"Substrate from CSV: '{substrate_name}' (MW={substrate_mw:.1f})")

    # Match substrate to a fragment by MW
    substrate_frag_id = None
    best_delta = float("inf")
    for fid, frag_el in reactant_frags:
        frag_mw = _compute_fragment_mw(frag_el)
        if frag_mw is None:
            continue
        delta = abs(frag_mw - substrate_mw)
        log(f"  Fragment {fid}: MW={frag_mw:.1f}, delta={delta:.1f}")
        if delta < best_delta and delta < MW_MATCH_TOLERANCE_LOOSE:
            best_delta = delta
            substrate_frag_id = fid

    if substrate_frag_id is None:
        log("Could not match substrate to any reactant fragment by MW")
        return False

    log(f"Substrate matched to fragment {substrate_frag_id} "
        f"(delta={best_delta:.1f})")

    # Move the OTHER fragment(s) to above-arrow
    moved = False
    new_reactant_ids = list(reactant_ids)
    new_above_ids = list(above_ids)
    for fid, frag_el in reactant_frags:
        if fid == substrate_frag_id:
            continue
        # Move from reactants to above-arrow
        if fid in new_reactant_ids:
            new_reactant_ids.remove(fid)
        new_above_ids.append(fid)
        log(f"Moving fragment {fid} from reactants to above-arrow")
        moved = True

    if moved:
        step.set("ReactionStepReactants", " ".join(new_reactant_ids))
        step.set("ReactionStepObjectsAboveArrow",
                  " ".join(new_above_ids))

    return moved


# ---------------------------------------------------------------------------
# Step 2: Phase A -- Inject equivalents into text content (before layout)
# ---------------------------------------------------------------------------

def enrich_phase_a(
    root: ET.Element,
    enrichment: EnrichmentData,
    merged_text_id: Optional[str],
    verbose: bool = False,
) -> None:
    """Inject equivalents into text labels (modifies root in-place).

    In merged mode: rebuilds <s> elements in the merged text block.
    In non-merged mode: appends ' (X eq.)' to each matching <t> element.

    Must be called BEFORE layout (compact + reaction_cleanup) so that
    text widths are correct for arrow length computation.
    """
    def log(msg: str):
        if verbose:
            print(f"  [enrich-A] {msg}", file=sys.stderr)

    page = root.find("page")
    if page is None:
        return

    # Build match lookup: scheme_display (normalized) -> MatchedReagent
    # For merged text, we match by line content
    match_by_display: Dict[str, MatchedReagent] = {}
    for m in enrichment.matches:
        if m.scheme_position in ("below_arrow", "above_arrow") and m.scheme_display:
            # Only inject equiv for non-substrate reagents in text
            # (Substrates are structures on left/right — handled in Phase B)
            if not m.is_solvent:
                match_by_display[_normalize_name(m.scheme_display)] = m

    if not match_by_display:
        log("No text-based equiv matches to inject")
        return

    if merged_text_id:
        _inject_merged(page, merged_text_id, match_by_display,
                        enrichment.solvent_names, log)
    else:
        _inject_separate(page, match_by_display,
                          enrichment.solvent_names, log)


def _inject_merged(
    page: ET.Element,
    merged_text_id: str,
    match_by_display: Dict[str, 'MatchedReagent'],
    solvent_names: List[str],
    log,
) -> None:
    """Inject equiv into a merged text block (single <t> with newlines)."""
    # Find the merged text element
    merged_el = None
    for el in page:
        if el.get("id") == merged_text_id and el.tag == "t":
            merged_el = el
            break

    if merged_el is None:
        log(f"WARNING: Merged text element id={merged_text_id} not found")
        return

    # Extract current text content
    full_text = _get_text_content(merged_el)
    lines = full_text.split("\n")

    # Build new <s> XML for each line
    new_s_parts = []
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        line_norm = _normalize_name(line_stripped)
        # Check if this line is a condition (time/temp) — skip
        is_condition = bool(
            re.search(r'\d+\s*°', line_stripped)
            or re.search(r'\d+\s*[hm](?:\s|$|,)', line_stripped)
        )
        # Check if this line is a solvent — skip equiv
        is_solvent = line_norm in solvent_names

        matched = match_by_display.get(line_norm)
        is_last_line = (i == len(lines) - 1)

        if matched and not is_condition and not is_solvent:
            equiv_str = _format_equiv(matched.csv_equiv)
            # Build formatted reagent name (with subscripts/italics)
            reagent_s_xml = build_formatted_s_xml(line_stripped)
            # Append equiv in plain face; newline must be INSIDE <s> text
            if not is_last_line:
                equiv_s_xml = (
                    f'<s font="3" size="10" color="0"> '
                    f'({equiv_str} eq.)\n</s>'
                )
            else:
                equiv_s_xml = (
                    f'<s font="3" size="10" color="0"> '
                    f'({equiv_str} eq.)</s>'
                )
            new_s_parts.append(reagent_s_xml + equiv_s_xml)
            log(f"  Merged line '{line_stripped}' -> ({equiv_str} eq.)")
        else:
            # Keep original line with its formatting
            reagent_s_xml = build_formatted_s_xml(line_stripped)
            # Newline must be INSIDE <s> text to be preserved in CDXML
            if not is_last_line:
                new_s_parts.append(
                    reagent_s_xml
                    + '<s font="3" size="10" color="0">\n</s>'
                )
            else:
                new_s_parts.append(reagent_s_xml)

    # Clear existing <s> children and rebuild
    for s in list(merged_el.findall("s")):
        merged_el.remove(s)

    # Parse and insert new <s> elements
    combined_xml = "".join(new_s_parts)

    # Wrap for parsing
    wrapper = f"<t>{combined_xml}</t>"
    try:
        temp_t = ET.fromstring(wrapper)
        for s in temp_t.findall("s"):
            merged_el.append(s)
    except ET.ParseError as e:
        log(f"WARNING: Failed to rebuild merged text: {e}")
        log(f"  XML was: {wrapper[:200]}...")
        return

    log(f"Rebuilt merged text block (id={merged_text_id})")


def _inject_separate(
    page: ET.Element,
    match_by_display: Dict[str, 'MatchedReagent'],
    solvent_names: List[str],
    log,
) -> None:
    """Inject equiv into separate text elements (non-merged mode)."""

    for el in page.findall("t"):
        text = _get_text_content(el)
        text_norm = _normalize_name(text)

        # Skip conditions
        if re.search(r'\d+\s*°', text) or re.search(r'\d+\s*[hm](?:\s|$|,)', text):
            continue
        # Skip solvents
        if text_norm in solvent_names:
            continue

        matched = match_by_display.get(text_norm)
        if matched is None:
            continue

        equiv_str = _format_equiv(matched.csv_equiv)

        # Rebuild <s> children
        for s in list(el.findall("s")):
            el.remove(s)

        reagent_s_xml = build_formatted_s_xml(text)
        equiv_s_xml = (
            f'<s font="3" size="10" color="0"> '
            f'({equiv_str} eq.)</s>'
        )
        wrapper = f"<t>{reagent_s_xml}{equiv_s_xml}</t>"
        try:
            temp_t = ET.fromstring(wrapper)
            for s in temp_t.findall("s"):
                el.append(s)
        except ET.ParseError as e:
            log(f"WARNING: Failed to rebuild text for '{text}': {e}")
            continue

        # Recompute bounding box
        recompute_text_bbox(el)
        log(f"  Separate text '{text}' -> ({equiv_str} eq.)")


# ---------------------------------------------------------------------------
# Step 3: Phase B -- Post-layout additions (run arrow + eq labels)
# ---------------------------------------------------------------------------

def enrich_phase_b(
    root: ET.Element,
    enrichment: EnrichmentData,
    verbose: bool = False,
) -> None:
    """Add run arrow and structural eq labels after layout.

    Must be called AFTER reaction_cleanup has finalized positions.
    Modifies root in-place.
    """
    def log(msg: str):
        if verbose:
            print(f"  [enrich-B] {msg}", file=sys.stderr)

    page = root.find("page")
    if page is None:
        return

    # --- Find reaction arrow ---
    arrow_el = None
    for el in page:
        if el.tag == "arrow":
            arrow_el = el
            break
    # Fallback: look for <graphic> with ArrowType
    if arrow_el is None:
        for el in page:
            if el.tag == "graphic" and el.get("ArrowType"):
                arrow_el = el
                break

    if arrow_el is None:
        log("WARNING: No reaction arrow found")
        return

    # Get arrow coordinates
    if arrow_el.tag == "arrow":
        head3d = arrow_el.get("Head3D", "")
        tail3d = arrow_el.get("Tail3D", "")
        if head3d and tail3d:
            head_parts = head3d.split()
            tail_parts = tail3d.split()
            arrow_head_x = float(head_parts[0])
            arrow_tail_x = float(tail_parts[0])
            arrow_y = float(head_parts[1])
        else:
            bb = arrow_el.get("BoundingBox", "").split()
            if len(bb) >= 4:
                arrow_tail_x = float(bb[0])
                arrow_head_x = float(bb[2])
                arrow_y = (float(bb[1]) + float(bb[3])) / 2.0
            else:
                log("WARNING: Cannot determine arrow position")
                return
    else:
        bb = arrow_el.get("BoundingBox", "").split()
        if len(bb) >= 4:
            # graphic BoundingBox: head_x, y, tail_x, y (reversed)
            arrow_head_x = float(bb[0])
            arrow_tail_x = float(bb[2])
            arrow_y = float(bb[1])
        else:
            log("WARNING: Cannot determine arrow position")
            return

    # Ensure tail_x < head_x
    if arrow_tail_x > arrow_head_x:
        arrow_tail_x, arrow_head_x = arrow_head_x, arrow_tail_x

    arrow_cx = (arrow_tail_x + arrow_head_x) / 2.0
    arrow_len = arrow_head_x - arrow_tail_x
    log(f"Arrow: tail={arrow_tail_x:.1f}, head={arrow_head_x:.1f}, "
        f"y={arrow_y:.2f}, len={arrow_len:.1f}")

    # --- Get step metadata for element positions ---
    scheme = page.find("scheme")
    step = scheme.find("step") if scheme is not None else None
    above_ids = step.get("ReactionStepObjectsAboveArrow", "").split() if step is not None else []
    below_ids = step.get("ReactionStepObjectsBelowArrow", "").split() if step is not None else []
    reactant_ids = step.get("ReactionStepReactants", "").split() if step is not None else []
    product_ids = step.get("ReactionStepProducts", "").split() if step is not None else []

    id_to_el: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    # --- ID allocation ---
    next_id = _get_max_id(root) + 1
    next_z = _get_max_z(root) + 1

    # --- Above-arrow structure eq labels ---
    for m in enrichment.matches:
        if m.scheme_position != "above_arrow":
            continue
        if m.is_solvent:
            continue

        el = id_to_el.get(m.scheme_element_id)
        if el is None or el.tag != "fragment":
            continue

        equiv_str = _format_equiv(m.csv_equiv)
        if equiv_str == "1":
            continue  # Don't show (1 eq.) for 1.0

        # Get fragment bottom from atom positions only
        frag_bb = fragment_bbox_with_label_extension(el)
        if frag_bb is None:
            continue
        frag_bottom = frag_bb[3]

        # Shift fragment UP to make room for eq label
        # Ensure at least 20pt between fragment bottom and arrow
        gap_needed = 20.0
        current_gap = arrow_y - frag_bottom
        if current_gap < gap_needed:
            shift_up = gap_needed - current_gap
            _shift_fragment(el, 0, -shift_up)
            frag_bb = fragment_bbox_with_label_extension(el)
            frag_bottom = frag_bb[3]
            log(f"  Shifted fragment {m.scheme_element_id} up by {shift_up:.1f}pt")

        # Place eq label midway between fragment bottom and arrow,
        # centered on the arrow midpoint (not the fragment center)
        label_y = (frag_bottom + arrow_y) / 2.0 + 3.0  # +3 for baseline offset
        label_text = f"({equiv_str} eq.)"

        eq_label = _create_text_element(
            next_id, next_z, arrow_cx, label_y, label_text,
            justify="Center",
        )
        page.append(eq_label)
        # Add to above-arrow objects in step
        if step is not None:
            above_str = step.get("ReactionStepObjectsAboveArrow", "")
            step.set("ReactionStepObjectsAboveArrow",
                      f"{above_str} {next_id}".strip())

        log(f"  Above-arrow eq label: '{label_text}' at ({arrow_cx:.1f}, {label_y:.1f})")
        next_id += 1
        next_z += 1

    # --- Left/right side structure eq labels ---
    for m in enrichment.matches:
        if m.scheme_position not in ("reactant",):
            continue
        if m.is_solvent:
            continue

        el = id_to_el.get(m.scheme_element_id)
        if el is None or el.tag != "fragment":
            continue

        equiv_str = _format_equiv(m.csv_equiv)
        if equiv_str == "1":
            continue  # Don't show (1 eq.) for 1.0

        frag_bb = fragment_bbox_with_label_extension(el)
        if frag_bb is None:
            continue
        frag_bottom = frag_bb[3]
        frag_cx = (frag_bb[0] + frag_bb[2]) / 2.0

        # Place label below fragment (no shifting)
        label_y = frag_bottom + 12.0
        label_text = f"({equiv_str} eq.)"

        eq_label = _create_text_element(
            next_id, next_z, frag_cx, label_y, label_text,
            justify="Center",
        )
        page.append(eq_label)
        log(f"  Side eq label: '{label_text}' below fragment {m.scheme_element_id}")
        next_id += 1
        next_z += 1

    # --- Run arrow ---
    if enrichment.sm_mass or enrichment.product_obtained:
        _create_run_arrow(
            page, root, arrow_tail_x, arrow_head_x, arrow_y,
            enrichment, id_to_el, below_ids,
            next_id, next_z, log,
        )


def _create_run_arrow(
    page: ET.Element,
    root: ET.Element,
    arrow_tail_x: float,
    arrow_head_x: float,
    arrow_y: float,
    enrichment: EnrichmentData,
    id_to_el: Dict[str, ET.Element],
    below_ids: List[str],
    next_id: int,
    next_z: int,
    log,
) -> None:
    """Create the run arrow with SM mass and product yield."""
    # Find bottom of all content below arrow
    content_bottom = arrow_y
    for el in page:
        eid = el.get("id", "")
        if el.tag in ("fragment", "t"):
            bb = _get_element_bbox(el)
            if bb and bb[3] > content_bottom:
                content_bottom = bb[3]

    # Run arrow y position: below all content
    run_arrow_y = content_bottom + 20.0

    log(f"  Run arrow at y={run_arrow_y:.1f} "
        f"(content_bottom={content_bottom:.1f})")

    # Create <graphic> element (the old-style reference)
    graphic_id = next_id
    next_id += 1
    arrow_id = next_id
    next_id += 1

    graphic = ET.SubElement(page, "graphic")
    graphic.set("id", str(graphic_id))
    graphic.set("SupersededBy", str(arrow_id))
    graphic.set("BoundingBox",
                f"{arrow_head_x:.2f} {run_arrow_y:.2f} "
                f"{arrow_tail_x:.2f} {run_arrow_y:.2f}")
    graphic.set("Z", str(next_z))
    next_z += 1
    graphic.set("GraphicType", "Line")
    graphic.set("ArrowType", "FullHead")
    graphic.set("HeadSize", "1000")

    # Create <arrow> element
    arrow = ET.SubElement(page, "arrow")
    arrow.set("id", str(arrow_id))
    bb_top = run_arrow_y - 1.64
    bb_bot = run_arrow_y + 1.52
    arrow.set("BoundingBox",
              f"{arrow_tail_x:.2f} {bb_top:.2f} "
              f"{arrow_head_x:.2f} {bb_bot:.2f}")
    arrow.set("Z", str(next_z))
    next_z += 1
    arrow.set("FillType", "None")
    arrow.set("ArrowheadHead", "Full")
    arrow.set("ArrowheadType", "Solid")
    arrow.set("HeadSize", "1000")
    arrow.set("ArrowheadCenterSize", "875")
    arrow.set("ArrowheadWidth", "250")
    arrow.set("Head3D", f"{arrow_head_x:.2f} {run_arrow_y:.2f} 0")
    arrow.set("Tail3D", f"{arrow_tail_x:.2f} {run_arrow_y:.2f} 0")
    # Center3D / MajorAxisEnd3D / MinorAxisEnd3D (cosmetic, approximated)
    cx_3d = (arrow_tail_x + arrow_head_x) / 2.0 + 290.0
    cy_3d = run_arrow_y + 129.0
    arrow.set("Center3D", f"{cx_3d:.2f} {cy_3d:.2f} 0")
    arrow.set("MajorAxisEnd3D",
              f"{cx_3d + (arrow_head_x - arrow_tail_x) / 2.0:.2f} {cy_3d:.2f} 0")
    arrow.set("MinorAxisEnd3D",
              f"{cx_3d:.2f} {cy_3d + (arrow_head_x - arrow_tail_x) / 2.0:.2f} 0")

    # --- SM mass text (left of run arrow) ---
    sm_text_y = run_arrow_y + 2.25  # baseline slightly below arrow
    if enrichment.sm_mass:
        sm_label = _create_text_element(
            next_id, next_z,
            arrow_tail_x - 4.0,  # right edge aligned near arrow tail
            sm_text_y,
            enrichment.sm_mass,
            justify="Right",
        )
        page.append(sm_label)
        log(f"  SM mass: '{enrichment.sm_mass}' at x={arrow_tail_x - 4.0:.1f}")
        next_id += 1
        next_z += 1

    # --- Product yield text (right of run arrow) ---
    if enrichment.product_obtained or enrichment.product_yield:
        yield_parts = []
        if enrichment.product_obtained:
            yield_parts.append(enrichment.product_obtained)
        if enrichment.product_yield:
            yield_parts.append(enrichment.product_yield)
        yield_text = ", ".join(yield_parts)

        yield_label = _create_text_element(
            next_id, next_z,
            arrow_head_x + 4.0,  # left edge aligned near arrow head
            sm_text_y,
            yield_text,
            justify="Left",
        )
        page.append(yield_label)
        log(f"  Product yield: '{yield_text}' at x={arrow_head_x + 4.0:.1f}")
        next_id += 1
        next_z += 1

    # --- Update document BoundingBox ---
    _update_document_bbox(root, page)


# ---------------------------------------------------------------------------
# Element creation helpers
# ---------------------------------------------------------------------------

def _create_text_element(
    elem_id: int,
    z_order: int,
    x: float,
    y: float,
    text: str,
    justify: str = "Left",
) -> ET.Element:
    """Create a standalone <t> element with plain text content."""
    t = ET.Element("t")
    t.set("id", str(elem_id))
    t.set("p", f"{x:.2f} {y:.2f}")
    t.set("Z", str(z_order))
    t.set("Warning", "Chemical Interpretation is not possible for this label")
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

    # Compute bounding box
    char_w = 5.8
    line_h = 12.0
    w = len(text) * char_w

    if justify == "Center":
        x1 = x - w / 2.0
        x2 = x + w / 2.0
    elif justify == "Right":
        x1 = x - w
        x2 = x
    else:
        x1 = x
        x2 = x + w

    y1 = y - line_h + 3.0
    y2 = y + 3.0

    t.set("BoundingBox", f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}")
    return t


def _shift_fragment(frag: ET.Element, dx: float, dy: float):
    """Shift all coordinates in a fragment by (dx, dy)."""
    for n in frag.iter("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                nx = float(parts[0]) + dx
                ny = float(parts[1]) + dy
                n.set("p", f"{nx:.2f} {ny:.2f}")

    for t in frag.iter("t"):
        p = t.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                nx = float(parts[0]) + dx
                ny = float(parts[1]) + dy
                t.set("p", f"{nx:.2f} {ny:.2f}")
        bb = t.get("BoundingBox")
        if bb:
            vals = [float(v) for v in bb.split()]
            if len(vals) >= 4:
                vals[0] += dx
                vals[1] += dy
                vals[2] += dx
                vals[3] += dy
                t.set("BoundingBox",
                      " ".join(f"{v:.2f}" for v in vals))

    bb = frag.get("BoundingBox")
    if bb:
        vals = [float(v) for v in bb.split()]
        if len(vals) >= 4:
            vals[0] += dx
            vals[1] += dy
            vals[2] += dx
            vals[3] += dy
            frag.set("BoundingBox",
                     " ".join(f"{v:.2f}" for v in vals))

    # Inner fragments (abbreviation groups)
    for inner in frag.iter("fragment"):
        if inner is not frag:
            ib = inner.get("BoundingBox")
            if ib:
                vals = [float(v) for v in ib.split()]
                if len(vals) >= 4:
                    vals[0] += dx
                    vals[1] += dy
                    vals[2] += dx
                    vals[3] += dy
                    inner.set("BoundingBox",
                              " ".join(f"{v:.2f}" for v in vals))


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
        # Fallback from p attribute
        p = el.get("p", "")
        if p:
            parts = [float(v) for v in p.split()]
            text = _get_text_content(el)
            w = len(text) * 5.8
            return (parts[0] - w/2, parts[1] - 12.0, parts[0] + w/2, parts[1])
    return None


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
