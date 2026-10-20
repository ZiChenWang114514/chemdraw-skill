#!/usr/bin/env python3
"""
scheme_maker.py -- Build CDXML reaction scheme from reaction JSON (experimental).

Takes a reaction JSON file (v1.2 from reaction_parser.py) and produces a
publication-ready CDXML reaction scheme.  The output is equivalent to what
the current polishing pipeline produces (scheme_polisher_v2 + eln_enrichment
+ reaction_cleanup), but built from semantic data rather than CDXML surgery.

When species have ``original_geometry`` data (stored by reaction_parser v1.2),
the original CDXML coordinates and abbreviation groups are used by default.
This preserves the input orientation and re-abbreviates groups like OTs, Boc,
etc. instead of expanding them to full structures.

This tool is EXPERIMENTAL.  It coexists with the existing pipeline and does
not replace it.

CLI:
    python scheme_maker.py reaction.json -o scheme.cdxml
    python scheme_maker.py reaction.json --approach chemdraw_mimic --align-mode rdkit
    python scheme_maker.py reaction.json --no-run-arrow --verbose

Python API:
    from cdxml_toolkit.render.scheme_maker import build_scheme
    cdxml_path = build_scheme("reaction.json", output="scheme.cdxml")
"""

import argparse
import json
import math
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Lazy imports — defer heavy dependencies to call time
# ---------------------------------------------------------------------------

_HAS_RDKIT = None


def _check_rdkit() -> bool:
    global _HAS_RDKIT
    if _HAS_RDKIT is None:
        try:
            from rdkit import Chem  # noqa: F401
            _HAS_RDKIT = True
        except ImportError:
            _HAS_RDKIT = False
    return _HAS_RDKIT


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_verbose = False


def _log(msg: str) -> None:
    if _verbose:
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Core: SMILES → atom/bond dicts (via structure_from_image)
# ---------------------------------------------------------------------------

def _smiles_to_mol_data(smiles: str, offset: int = 0) -> Optional[Dict]:
    """Convert SMILES to atom/bond dicts using RDKit 2D coords.

    Returns dict with 'atoms' and 'bonds' lists, or None on failure.
    Uses structure_from_image.smiles_to_coords which handles Kekulization,
    explicit H removal, and bond direction annotation.
    """
    try:
        from ..image.structure_from_image import smiles_to_coords
    except ImportError:
        raise RuntimeError(
            "structure_from_image.py is required (for smiles_to_coords). "
            "Ensure it is in the same directory."
        )

    return smiles_to_coords(smiles, offset_index=offset)


def _normalize_mol(mol_data: Dict, center_x: float = 0.0,
                   center_y: float = 0.0) -> Tuple[List, List]:
    """Normalize atom coords to ACS bond length (14.40 pt), flip y, center."""
    from ..coord_normalizer import normalize_coords
    return normalize_coords(
        mol_data["atoms"], mol_data["bonds"],
        center_x=center_x, center_y=center_y,
        flip_y=True,
    )


# ---------------------------------------------------------------------------
# Original geometry → mol_data conversion
# ---------------------------------------------------------------------------

def _geometry_to_mol_data(geom: Dict[str, Any],
                          offset: int = 0) -> Optional[Dict]:
    """Convert ``original_geometry`` from a SpeciesDescriptor to mol_data.

    The returned dict has ``"atoms"`` and ``"bonds"`` lists in the same
    format that ``smiles_to_coords`` / ``_smiles_to_mol_data`` returns,
    including extra keys for abbreviation and generic groups.

    Coordinates are negated on the y-axis so that subsequent
    ``normalize_coords(flip_y=True)`` produces correct CDXML-space output
    (the double-negation cancels out).
    """
    if not geom or not geom.get("atoms"):
        return None

    atoms: List[Dict[str, Any]] = []
    id_remap: Dict[int, int] = {}  # original id → new 1-based index

    for i, a in enumerate(geom["atoms"]):
        idx = offset + i + 1
        orig_id = a.get("id", i)
        id_remap[orig_id] = idx

        atom_d: Dict[str, Any] = {
            "index": idx,
            "symbol": a.get("symbol", "C"),
            "x": a["x"],
            "y": -a["y"],  # negate so flip_y=True restores original
        }

        if "num_hydrogens" in a:
            atom_d["num_hydrogens"] = a["num_hydrogens"]

        if "charge" in a:
            atom_d["charge"] = a["charge"]

        # Abbreviation groups (OTs, Boc, Me, …)
        if a.get("is_abbreviation"):
            atom_d["is_abbreviation"] = True
            atom_d["abbrev_label"] = a.get("label", "?")
            atom_d["abbrev_smiles"] = a.get("label_smiles")
            # Use a placeholder symbol that won't be stripped as explicit H
            atom_d["symbol"] = "X"

        # Generic variable groups (R, X, Ar, R1, …)
        elif a.get("is_generic"):
            atom_d["is_generic"] = True
            atom_d["generic_label"] = a.get("label", "R")
            atom_d["node_type"] = a.get("node_type", "GenericNickname")
            atom_d["symbol"] = "X"

        atoms.append(atom_d)

    bonds: List[Dict[str, Any]] = []
    for j, b in enumerate(geom["bonds"]):
        bi = id_remap.get(b["begin"])
        ei = id_remap.get(b["end"])
        if bi is None or ei is None:
            continue
        bond_d: Dict[str, Any] = {
            "index": offset + len(geom["atoms"]) + j + 1,
            "order": b.get("order", 1),
            "atom1": bi,
            "atom2": ei,
        }
        if "double_position" in b:
            bond_d["double_pos"] = b["double_position"]
        # Preserve stereo config
        if "cfg" in b:
            bond_d["cfg"] = b["cfg"]
        bonds.append(bond_d)

    return {"atoms": atoms, "bonds": bonds}


def _species_mol_data(sp, offset: int = 0) -> Optional[Dict]:
    """Get mol_data for a species, preferring original geometry.

    When a species has ``original_geometry`` (from reaction_parser v1.2),
    uses the original CDXML coordinates and abbreviation data.  Falls back
    to SMILES-based 2D coordinate generation.
    """
    # Prefer original geometry (preserves orientation + abbreviations)
    if sp.original_geometry:
        mol = _geometry_to_mol_data(sp.original_geometry, offset=offset)
        if mol is not None:
            _log(f"  Using original geometry for '{sp.name or sp.smiles}'")
            return mol

    # Fallback: generate from SMILES
    if sp.smiles:
        return _smiles_to_mol_data(sp.smiles, offset=offset)

    return None


# ---------------------------------------------------------------------------
# Role priority ordering for above-arrow text
# ---------------------------------------------------------------------------

# Priority: lower number = higher priority = closer to top.
# Catalyst and ligand are always first (defining the reaction).
# Remaining reagents cluster around 50.  Solvent is last.
_ROLE_PRIORITY = {
    "catalyst":             10,
    "ligand":               20,
    "coupling_reagent":     40,
    "activating_agent":     41,
    "reducing_agent":       42,
    "oxidant":              43,
    "halogenating_agent":   44,
    "fluorinating_agent":   45,
    "borylating_agent":     46,
    "lewis_acid":           47,
    "protecting_group":     48,
    "deprotecting_agent":   49,
    "acid":                 50,
    "base":                 51,
    "additive":             55,
    "reagent":              60,
    "reductant":            65,
    "drying_agent":         70,
    "solvent":              80,
}
_DEFAULT_ROLE_PRIORITY = 59  # unknown roles sort just before "reagent"


def _sort_by_role_priority(
    entries: List[Tuple[str, str, float]],
) -> List[Tuple[str, str, float]]:
    """Sort (text, role_detail, equiv) entries by reagent role priority.

    Catalyst → Ligand → Coupling reagent → … → Base → Acid → Solvent.
    Within the same priority (or all at _DEFAULT_ROLE_PRIORITY for
    unclassified reagents), lower equivalents = higher priority.
    This heuristic reflects that catalysts/ligands are typically used
    in smaller amounts than stoichiometric reagents.
    """
    return sorted(
        entries,
        key=lambda e: (_ROLE_PRIORITY.get(e[1], _DEFAULT_ROLE_PRIORITY), e[2]),
    )


def _merge_condition_tokens(condition_lines: List[str]) -> List[str]:
    """Merge temperature and time tokens into a single comma-separated line.

    Input:  ["105 °C", "24 h"]
    Output: ["105 °C, 24 h"]

    Other condition tokens (atmosphere, etc.) stay on separate lines.
    """
    temp_time_tokens = []
    other_tokens = []

    # Patterns for temperature and time
    temp_pat = re.compile(
        r"^-?\d+\.?\d*\s*°?\s*[cCfF]$"       # "105 °C", "80°C", "-78 °C"
        r"|^rt$|^RT$|^room\s+temp"              # "rt", "RT", "room temp"
        r"|^reflux$"                            # "reflux"
        r"|^-?\d+\s*to\s*-?\d+\s*°?\s*[cCfF]$" # "0 to 25 °C"
        , re.IGNORECASE
    )
    time_pat = re.compile(
        r"^\d+\.?\d*\s*(h|hr|hrs|hours?|min|minutes?|d|days?|s|sec|seconds?|overnight|o/?n)$",
        re.IGNORECASE
    )

    for tok in condition_lines:
        tok = tok.strip()
        if not tok:
            continue
        if temp_pat.match(tok) or time_pat.match(tok):
            temp_time_tokens.append(tok)
        else:
            other_tokens.append(tok)

    result = []
    if temp_time_tokens:
        result.append(", ".join(temp_time_tokens))
    result.extend(other_tokens)
    return result


# ---------------------------------------------------------------------------
# Core: Build CDXML from reaction JSON
# ---------------------------------------------------------------------------

def build_scheme(
    input_path: str,
    output: Optional[str] = None,
    approach: str = "chemdraw_mimic",
    align_mode: str = "rdkit",
    run_arrow: bool = True,
    verbose: bool = False,
) -> str:
    """Build a CDXML reaction scheme from a reaction JSON file.

    Args:
        input_path: Path to reaction JSON (v1.1 from reaction_parser)
        output: Path for output CDXML (default: {stem}-scheme.cdxml)
        approach: Layout approach for reaction_cleanup
        align_mode: Alignment strategy (rdkit/rxnmapper/kabsch/none)
        run_arrow: Add run arrow with mass/yield if ELN data available
        verbose: Print diagnostic messages

    Returns:
        Path to the output CDXML file.
    """
    global _verbose
    _verbose = verbose

    if not _check_rdkit():
        print("ERROR: RDKit is required for scheme_maker.", file=sys.stderr)
        sys.exit(1)

    # --- Step 1: Load and validate JSON ---
    from ..perception.reaction_parser import ReactionDescriptor

    desc = ReactionDescriptor.from_json(input_path)
    _log(f"Loaded JSON: {desc.experiment}, {len(desc.species)} species, "
         f"version={desc.version}")

    # Validate: need at least one product with SMILES
    products_with_smiles = [
        sp for sp in desc.species
        if sp.role == "product" and sp.smiles
    ]
    if not products_with_smiles:
        print("ERROR: No product species with SMILES found in JSON.",
              file=sys.stderr)
        sys.exit(1)

    # --- Step 2: Partition species into layout groups ---
    reactant_species = []
    product_species = []
    # Each entry is (text, role_detail, equiv) for priority sorting later.
    # equiv is used as a tiebreaker: lower equiv = higher priority (catalysts
    # are typically used in small amounts like 0.05 eq.).
    above_arrow_entries = []     # (text, role_detail, equiv) tuples
    above_arrow_mol_species = [] # structural species above arrow
    condition_lines = []         # below-arrow condition text (temp, time, atm)

    def _parse_equiv(sp) -> float:
        """Parse csv_equiv to a float for sorting. Missing = 999."""
        if sp.csv_equiv:
            try:
                return float(sp.csv_equiv)
            except (ValueError, TypeError):
                pass
        return 999.0

    for sp in desc.species:
        # Derive position from chemical role (no dependency on scheme_position)
        if sp.role == "product":
            pos = "product"
        elif sp.role == "atom_contributing":
            if sp.is_substrate or sp.is_sm:
                pos = "reactant"
            else:
                pos = "above_arrow"
        elif sp.is_solvent:
            pos = "above_arrow"
        elif sp.role == "non_contributing":
            pos = "above_arrow"
        else:
            pos = "above_arrow"

        if pos == "product":
            if sp.smiles:
                product_species.append(sp)
            else:
                _log(f"  WARNING: Product '{sp.name}' has no SMILES, skipping")
        elif pos == "reactant":
            if sp.smiles:
                reactant_species.append(sp)
            else:
                # No SMILES — convert to text label above arrow
                _log(f"  WARNING: Reactant '{sp.name}' has no SMILES, "
                     "converting to text")
                text = sp.display_text or sp.name or sp.csv_name or "?"
                role_d = sp.role_detail or sp.rxn_insight_role or ""
                above_arrow_entries.append((text, role_d, _parse_equiv(sp)))
        elif pos == "above_arrow":
            if (sp.smiles and sp.source in ("fragment", "rxn")
                    and sp.role == "atom_contributing"):
                # Structural species above arrow (non-substrate atom-contributing
                # reactant, e.g. coupling partner)
                above_arrow_mol_species.append(sp)
            else:
                # Text species above arrow (reagents, catalysts, solvents)
                text = sp.display_text or sp.name or sp.csv_name or "?"
                role_d = sp.role_detail or sp.rxn_insight_role or ""
                if sp.is_solvent and not role_d:
                    role_d = "solvent"
                above_arrow_entries.append((text, role_d, _parse_equiv(sp)))
        elif pos == "below_arrow":
            text = sp.display_text or sp.name or sp.csv_name or "?"
            role_d = sp.role_detail or sp.rxn_insight_role or ""
            if sp.is_solvent and not role_d:
                role_d = "solvent"
            above_arrow_entries.append((text, role_d, _parse_equiv(sp)))

    # Add condition tokens (temp, time, atmosphere)
    condition_lines.extend(desc.conditions)

    # Deduplicate above-arrow entries (case-insensitive)
    seen_above = set()
    deduped_entries = []
    for txt, role_d, eq in above_arrow_entries:
        key = txt.strip().lower()
        if key not in seen_above:
            seen_above.add(key)
            deduped_entries.append((txt, role_d, eq))
    above_arrow_entries = deduped_entries

    # Sort entries by role priority:
    # catalyst > ligand > coupling_reagent > … > base/acid > solvent
    # Within same role priority, lower equiv = higher priority.
    above_arrow_entries = _sort_by_role_priority(above_arrow_entries)

    above_arrow_texts = [txt for txt, _, _ in above_arrow_entries]

    _log(f"  Reactants: {len(reactant_species)}, "
         f"Products: {len(product_species)}, "
         f"Above-arrow text: {len(above_arrow_texts)}, "
         f"Above-arrow structures: {len(above_arrow_mol_species)}, "
         f"Conditions: {len(condition_lines)}")

    # --- Step 3: Generate 2D coords for each structural species ---
    # Prefer original geometry when available (preserves orientation and
    # abbreviation groups like OTs, Boc).  Fall back to SMILES→RDKit→coords.
    _log("Generating 2D coordinates...")

    atom_offset = 0
    reactant_mols = []
    for sp in reactant_species:
        mol_data = _species_mol_data(sp, offset=atom_offset)
        if mol_data is None:
            _log(f"  WARNING: Could not generate coords for '{sp.name}' "
                 f"(SMILES: {sp.smiles})")
            above_arrow_texts.append(sp.display_text or sp.name or "?")
            continue
        atom_offset += len(mol_data["atoms"]) + len(mol_data["bonds"])
        reactant_mols.append(mol_data)

    product_mols = []
    for sp in product_species:
        mol_data = _species_mol_data(sp, offset=atom_offset)
        if mol_data is None:
            _log(f"  WARNING: Could not generate coords for product "
                 f"'{sp.name}' (SMILES: {sp.smiles})")
            continue
        atom_offset += len(mol_data["atoms"]) + len(mol_data["bonds"])
        product_mols.append(mol_data)

    above_arrow_mols = []
    for sp in above_arrow_mol_species:
        mol_data = _species_mol_data(sp, offset=atom_offset)
        if mol_data is None:
            _log(f"  WARNING: Could not generate coords for '{sp.name}', "
                 "converting to text")
            above_arrow_texts.append(sp.display_text or sp.name or "?")
            continue
        atom_offset += len(mol_data["atoms"]) + len(mol_data["bonds"])
        above_arrow_mols.append(mol_data)

    if not product_mols:
        print("ERROR: No product structures could be generated.",
              file=sys.stderr)
        sys.exit(1)

    # --- Step 4: Normalize coordinates ---
    _log("Normalizing coordinates...")
    from ..coord_normalizer import normalize_reaction

    norm_reactants, norm_products = normalize_reaction(
        reactant_mols, product_mols,
        reactant_start_x=50.0,
        product_start_x=350.0,
        molecule_gap=80.0,
    )

    # --- Step 5: Build conditions dict ---
    # Merge all text into a single below-arrow block.  reaction_cleanup
    # puts all <t> elements below the arrow anyway, and multiple <t>
    # elements can overlap.  A single merged block with \n-separated
    # lines avoids this.  This matches the --merge-conditions behavior
    # of scheme_polisher.
    #
    # Condition tokens (temp + time) are merged onto a single
    # comma-separated line: "105 °C, 24 h".
    merged_conditions = _merge_condition_tokens(condition_lines)
    merged_text = above_arrow_texts + merged_conditions
    conditions = {}
    if merged_text:
        conditions["below"] = merged_text

    _log(f"  Conditions: {conditions}")

    # --- Step 6: Assemble initial CDXML ---
    _log("Assembling CDXML...")
    from ..cdxml_builder import build_reaction_cdxml

    cdxml_str = build_reaction_cdxml(
        norm_reactants, norm_products,
        conditions=conditions if conditions else None,
    )

    # Write to temp file for subsequent processing
    tmp_dir = tempfile.mkdtemp(prefix="scheme_maker_")
    tmp_assembled = os.path.join(tmp_dir, "assembled.cdxml")
    with open(tmp_assembled, "w", encoding="utf-8") as f:
        f.write(cdxml_str)

    _log(f"  Assembled CDXML: {tmp_assembled}")

    # --- Step 7: Insert above-arrow structures (if any) ---
    if above_arrow_mols:
        _log("Inserting above-arrow structures...")
        _insert_above_arrow_structures(tmp_assembled, above_arrow_mols)

    # --- Step 8: Apply text formatting (subscripts/italics) ---
    _log("Applying text formatting...")
    _apply_text_formatting(tmp_assembled)

    # --- Step 9: Run alignment ---
    if align_mode != "none" and len(reactant_mols) > 0:
        _log(f"Running alignment ({align_mode})...")
        _run_alignment(tmp_assembled, align_mode)

    # --- Step 10: Run reaction_cleanup (final layout) ---
    _log(f"Running layout ({approach})...")
    from ..layout.reaction_cleanup import run_cleanup

    # Determine output path
    if output is None:
        stem = os.path.splitext(os.path.basename(input_path))[0]
        output = os.path.join(os.path.dirname(input_path) or ".",
                              f"{stem}-scheme.cdxml")

    result = run_cleanup(tmp_assembled, output, approach=approach,
                         verbose=verbose)
    _log(f"  Layout complete: {result.get('num_reactants', '?')} reactants, "
         f"{result.get('num_products', '?')} products")

    # --- Step 11: Add run arrow (optional) ---
    if run_arrow and desc.eln_data:
        _log("Adding run arrow...")
        _add_run_arrow(output, desc.eln_data)

    # Cleanup temp files
    try:
        os.unlink(tmp_assembled)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    _log(f"Output: {output}")
    return output


# ---------------------------------------------------------------------------
# Step 7: Insert above-arrow structures
# ---------------------------------------------------------------------------

def _insert_above_arrow_structures(cdxml_path: str,
                                   above_mols: List[Dict]) -> None:
    """Insert structural fragments above the arrow in the CDXML.

    Normalizes each above-arrow molecule, builds its fragment XML,
    and inserts it into the page.  Updates <step> metadata.
    """
    from ..cdxml_utils import parse_cdxml, write_cdxml
    from ..cdxml_builder import _build_fragment, _IDGen  # noqa: private API

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return

    step = page.find(".//scheme/step")
    if step is None:
        return

    # Find arrow center for positioning
    arrow = page.find(".//arrow")
    if arrow is None:
        return
    bbox = arrow.get("BoundingBox", "0 0 100 300")
    parts = bbox.split()
    if len(parts) >= 4:
        arrow_cx = (float(parts[0]) + float(parts[2])) / 2.0
        arrow_cy = float(parts[1]) - 30.0  # above the arrow
    else:
        arrow_cx = 200.0
        arrow_cy = 270.0

    # Get current max ID
    max_id = 0
    for el in root.iter():
        eid = el.get("id")
        if eid:
            try:
                max_id = max(max_id, int(eid))
            except ValueError:
                pass

    id_gen = _IDGen(start=max_id + 1)

    above_ids = step.get("ReactionStepObjectsAboveArrow", "")
    above_ids_list = above_ids.split() if above_ids else []

    y_offset = 0.0
    for mol_data in above_mols:
        # Normalize to ACS bond length
        atoms, bonds = _normalize_mol(mol_data,
                                       center_x=arrow_cx,
                                       center_y=arrow_cy - y_offset)

        frag_xml, _, frag_id_val = _build_fragment(atoms, bonds, id_gen)

        # Parse fragment XML and insert into page
        frag_elem = ET.fromstring(frag_xml)
        # Insert before scheme element
        scheme = page.find("scheme")
        if scheme is not None:
            idx = list(page).index(scheme)
            page.insert(idx, frag_elem)
        else:
            page.append(frag_elem)

        frag_id = frag_elem.get("id")
        if frag_id:
            above_ids_list.append(frag_id)

        y_offset += 60.0  # stack vertically

    # Update step metadata
    if above_ids_list:
        step.set("ReactionStepObjectsAboveArrow", " ".join(above_ids_list))

    write_cdxml(tree, cdxml_path)


# ---------------------------------------------------------------------------
# Step 8: Apply text formatting
# ---------------------------------------------------------------------------

def _apply_text_formatting(cdxml_path: str) -> None:
    """Apply subscript/italic formatting to standalone caption text elements.

    Handles multi-line condition text by formatting each line independently
    and preserving line breaks.  Condition tokens (temperatures, times,
    atmospheres) are left unformatted to avoid spurious subscripts.
    """
    from ..cdxml_utils import parse_cdxml, write_cdxml

    try:
        from ..text_formatting import build_formatted_s_xml
    except ImportError:
        _log("  text_formatting not available, skipping")
        return

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return

    # Condition tokens should not be formatted (would get spurious subscripts)
    try:
        from ..perception.reaction_parser import _is_condition_token
    except ImportError:
        _is_condition_token = None

    modified = False
    # Only process direct children of <page> — these are standalone captions
    # (conditions text, labels).  Skip <t> inside <fragment><n> (atom labels).
    for t_elem in list(page):
        if t_elem.tag != "t":
            continue

        s_elems = t_elem.findall("s")
        if not s_elems:
            continue

        text = "".join(s.text or "" for s in s_elems)
        if not text.strip():
            continue

        # Get style attributes from the first <s> element
        first_s = s_elems[0]
        font = first_s.get("font", "3")
        size = first_s.get("size", "10")
        face = first_s.get("face", "1")

        # Handle multi-line: format each line separately
        lines = text.split("\n")
        new_s_elements = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Don't format condition tokens (temperatures, times, etc.)
            is_condition = False
            if _is_condition_token is not None:
                is_condition = _is_condition_token(line)

            if is_condition:
                # Plain text — no subscripts
                s_elem = ET.Element("s")
                s_elem.set("font", font)
                s_elem.set("size", size)
                s_elem.set("face", face)
                s_elem.text = line
                new_s_elements.append(s_elem)
            else:
                # Apply chemical formatting
                formatted_xml = build_formatted_s_xml(line)
                if formatted_xml:
                    try:
                        wrapper = ET.fromstring(f"<t>{formatted_xml}</t>")
                        for s in wrapper:
                            if not s.get("font"):
                                s.set("font", font)
                            if not s.get("size"):
                                s.set("size", size)
                            new_s_elements.append(s)
                    except ET.ParseError:
                        # Fallback: plain text
                        s_elem = ET.Element("s")
                        s_elem.set("font", font)
                        s_elem.set("size", size)
                        s_elem.set("face", face)
                        s_elem.text = line
                        new_s_elements.append(s_elem)
                else:
                    s_elem = ET.Element("s")
                    s_elem.set("font", font)
                    s_elem.set("size", size)
                    s_elem.set("face", face)
                    s_elem.text = line
                    new_s_elements.append(s_elem)

            # Insert newline between lines (append to last <s> text)
            if i < len(lines) - 1 and new_s_elements:
                last = new_s_elements[-1]
                last.text = (last.text or "") + "\n"

        if not new_s_elements:
            continue

        # Replace <s> children
        for s in list(s_elems):
            t_elem.remove(s)

        for s_elem in new_s_elements:
            t_elem.append(s_elem)
        modified = True

    if modified:
        write_cdxml(tree, cdxml_path)


# ---------------------------------------------------------------------------
# Step 9: Run alignment
# ---------------------------------------------------------------------------

def _run_alignment(cdxml_path: str, align_mode: str) -> None:
    """Align reactant structures to match product orientation."""
    from ..cdxml_utils import parse_cdxml, write_cdxml

    tree = parse_cdxml(cdxml_path)

    aligned = 0
    if align_mode == "rxnmapper":
        try:
            from ..layout.alignment import rxnmapper_align_to_product
            aligned = rxnmapper_align_to_product(tree, verbose=_verbose)
            _log(f"  RXNMapper aligned {aligned} fragments")
        except (ImportError, Exception) as e:
            _log(f"  RXNMapper alignment failed ({e}), falling back to RDKit MCS")
            align_mode = "rdkit"

    if align_mode == "rdkit":
        try:
            from ..layout.alignment import rdkit_align_to_product
            aligned = rdkit_align_to_product(tree, verbose=_verbose)
            _log(f"  RDKit MCS aligned {aligned} fragments")
        except (ImportError, Exception) as e:
            _log(f"  RDKit alignment failed ({e}), falling back to Kabsch")
            align_mode = "kabsch"

    if align_mode == "kabsch":
        try:
            from ..layout.alignment import kabsch_align_to_product
            aligned = kabsch_align_to_product(tree, verbose=_verbose)
            _log(f"  Kabsch aligned {aligned} fragments")
        except (ImportError, Exception) as e:
            _log(f"  Kabsch alignment failed: {e}")

    if aligned > 0:
        # Alignment rotates fragments, which invalidates pre-computed
        # DoublePosition values (they are relative to the B→E bond vector,
        # which has rotated).  Strip them — ChemDraw recomputes correct
        # values automatically via NeedsClean.
        for bond_el in tree.iter("b"):
            if bond_el.get("DoublePosition"):
                del bond_el.attrib["DoublePosition"]
        write_cdxml(tree, cdxml_path)


# ---------------------------------------------------------------------------
# Step 11: Add run arrow with mass/yield
# ---------------------------------------------------------------------------

def _add_run_arrow(cdxml_path: str, eln_data: Dict[str, Any]) -> None:
    """Add a run arrow below the scheme with SM mass and product yield.

    The run arrow matches the reaction arrow's X-extent and is positioned
    below all existing content (text + structures).
    """
    from ..cdxml_utils import parse_cdxml, write_cdxml

    sm_mass = eln_data.get("sm_mass", "")
    product_obtained = eln_data.get("product_obtained", "")
    product_yield = eln_data.get("product_yield", "")

    if not sm_mass and not product_obtained:
        _log("  No mass/yield data, skipping run arrow")
        return

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return

    # Find the existing reaction arrow to match its X-extent
    rxn_arrow = page.find(".//arrow")
    if rxn_arrow is None:
        _log("  No reaction arrow found, skipping run arrow")
        return

    # Get reaction arrow tail/head X from Tail3D/Head3D
    tail_3d = rxn_arrow.get("Tail3D", "")
    head_3d = rxn_arrow.get("Head3D", "")
    if tail_3d and head_3d:
        arrow_x1 = float(tail_3d.split()[0])
        arrow_x2 = float(head_3d.split()[0])
    else:
        # Fallback: use BoundingBox
        bbox = rxn_arrow.get("BoundingBox", "0 0 100 300").split()
        arrow_x1 = float(bbox[0])
        arrow_x2 = float(bbox[2])

    # Find bottom of all content (including text below arrow)
    max_y = 0.0
    for elem in page:
        if elem.tag == "fragment":
            for node in elem.findall("n"):
                p = node.get("p", "")
                if p:
                    parts = p.split()
                    if len(parts) >= 2:
                        max_y = max(max_y, float(parts[1]))
        elif elem.tag == "t":
            # Check text bounding box or p position
            bb = elem.get("BoundingBox", "")
            if bb:
                parts = bb.split()
                if len(parts) >= 4:
                    max_y = max(max_y, float(parts[3]))
            else:
                p = elem.get("p", "")
                if p:
                    parts = p.split()
                    if len(parts) >= 2:
                        max_y = max(max_y, float(parts[1]) + 5.0)

    if max_y == 0.0:
        return

    # Get max id for new elements
    max_id = 0
    for el in root.iter():
        eid = el.get("id")
        if eid:
            try:
                max_id = max(max_id, int(eid))
            except ValueError:
                pass

    next_id = max_id + 1

    # Position run arrow below all content
    arrow_y = max_y + 18.0

    # Create arrow element (same X-extent as reaction arrow)
    arrow_elem = ET.SubElement(page, "arrow")
    arrow_elem.set("id", str(next_id))
    next_id += 1
    arrow_elem.set("Z", str(next_id))
    next_id += 1
    bbox = f"{arrow_x1:.2f} {arrow_y - 2:.2f} {arrow_x2:.2f} {arrow_y + 2:.2f}"
    arrow_elem.set("BoundingBox", bbox)
    arrow_elem.set("FillType", "None")
    arrow_elem.set("ArrowheadHead", "Full")
    arrow_elem.set("ArrowheadType", "Solid")
    arrow_elem.set("Head3D", f"{arrow_x2:.2f} {arrow_y:.2f} 0")
    arrow_elem.set("Tail3D", f"{arrow_x1:.2f} {arrow_y:.2f} 0")

    # Text baseline should vertically centre on the arrow.
    # Arial 10pt has ~7pt cap height; p (anchor) is at the text baseline,
    # so baseline ≈ arrow_y + 3.5  centres the text on the arrow line.
    text_baseline_y = arrow_y + 3.5

    # Left label: SM mass (positioned left of arrow tail)
    if sm_mass:
        t_left = ET.SubElement(page, "t")
        t_left.set("id", str(next_id))
        next_id += 1
        text_width = len(sm_mass) * 5.8
        lx = arrow_x1 - 5.0 - text_width
        ly_top = text_baseline_y - 8.0
        ly_bot = text_baseline_y + 2.0
        t_left.set("p", f"{arrow_x1 - 5:.2f} {text_baseline_y:.2f}")
        t_left.set("BoundingBox",
                    f"{lx:.2f} {ly_top:.2f} {arrow_x1 - 5:.2f} {ly_bot:.2f}")
        t_left.set("Justification", "Right")
        t_left.set("CaptionJustification", "Right")
        t_left.set("InterpretChemically", "no")
        s_left = ET.SubElement(t_left, "s")
        s_left.set("font", "3")
        s_left.set("size", "10")
        s_left.set("face", "0")
        s_left.text = sm_mass

    # Right label: product obtained + yield (positioned right of arrow head)
    # Format: "1.60 g, 72%" (comma-separated, no parentheses)
    right_text_parts = []
    if product_obtained:
        right_text_parts.append(product_obtained)
    if product_yield:
        # Strip extra whitespace in yield (e.g. "72 %" → "72%")
        yield_clean = product_yield.replace(" %", "%").replace("% ", "%")
        right_text_parts.append(yield_clean)
    if right_text_parts:
        right_text = ", ".join(right_text_parts)
        text_width = len(right_text) * 5.8
        t_right = ET.SubElement(page, "t")
        t_right.set("id", str(next_id))
        next_id += 1
        rx = arrow_x2 + 5.0
        ry_top = text_baseline_y - 8.0
        ry_bot = text_baseline_y + 2.0
        t_right.set("p", f"{rx:.2f} {text_baseline_y:.2f}")
        t_right.set("BoundingBox",
                     f"{rx:.2f} {ry_top:.2f} {rx + text_width:.2f} {ry_bot:.2f}")
        t_right.set("InterpretChemically", "no")
        s_right = ET.SubElement(t_right, "s")
        s_right.set("font", "3")
        s_right.set("size", "10")
        s_right.set("face", "0")
        s_right.text = right_text

    write_cdxml(tree, cdxml_path)
    _log(f"  Run arrow added: {sm_mass} -> {' '.join(right_text_parts)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build CDXML reaction scheme from reaction JSON "
                    "(experimental).",
    )
    p.add_argument("input", help="Reaction JSON file (from reaction_parser)")
    p.add_argument("-o", "--output", default=None,
                   help="Output CDXML file (default: {stem}-scheme.cdxml)")
    p.add_argument("--approach", default="chemdraw_mimic",
                   choices=["chemdraw_mimic", "compact", "bbox_center",
                            "arrow_driven", "proportional", "golden_ratio"],
                   help="Layout approach (default: chemdraw_mimic)")
    p.add_argument("--align-mode", default="rdkit",
                   choices=["rdkit", "rxnmapper", "kabsch", "none"],
                   help="Alignment strategy (default: rdkit)")
    p.add_argument("--no-run-arrow", action="store_true",
                   help="Skip run arrow even if ELN data is available")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--json-errors", action="store_true",
                   help="Structured JSON errors to stderr")
    return p


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        if args.json_errors:
            err = {"error": "file_not_found",
                   "detail": f"Input file not found: {args.input}"}
            print(json.dumps(err), file=sys.stderr)
        else:
            print(f"ERROR: Input file not found: {args.input}",
                  file=sys.stderr)
        sys.exit(1)

    try:
        output = build_scheme(
            input_path=args.input,
            output=args.output,
            approach=args.approach,
            align_mode=args.align_mode,
            run_arrow=not args.no_run_arrow,
            verbose=args.verbose,
        )
        print(f"Output: {output}")
    except Exception as e:
        if args.json_errors:
            err = {"error": "scheme_build_failed", "detail": str(e)}
            print(json.dumps(err), file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
