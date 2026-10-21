#!/usr/bin/env python3
"""
Mass Resolver — Structure-Based Mass Determination for LCMS Identification

Extracts expected species (starting materials, products, reagents) from
CDX/RXN structure files via ChemScript + RDKit, computes monoisotopic
exact masses, and builds expected ESI adduct m/z tables.

Three tiers of mass resolution:
  1. ChemScript + RDKit (CDX or RXN → SMILES → exact mass)
  2. RDKit only (RXN → exact mass, with SUP abbreviation correction)
  3. CSV MW fallback (average MW from ELN export)

Usage:
    from mass_resolver import extract_expected_masses, ExpectedSpecies

    species = extract_expected_masses(exp)
    for sp in species:
        print(f"{sp.name}: {sp.exact_mass:.3f} Da")
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

from cdxml_toolkit.constants import MW_MATCH_TOLERANCE

# --- Optional: structure-based mass determination ---
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    _HAS_RDKIT = True
except ImportError:
    _HAS_RDKIT = False

try:
    from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
    _HAS_CHEMSCRIPT = True
except ImportError:
    _HAS_CHEMSCRIPT = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard ESI adducts: name -> (ESI mode, mass offset from neutral)
ADDUCTS = {
    "[M+H]+":       ("ES+",  1.008),
    "[M-H]-":       ("ES-", -1.008),
    "[M+Na]+":      ("ES+", 22.990),
    "[M+formate]-": ("ES-", 44.998),
}

# Adduct reporting priority: prefer [M+H]+/[M-H]- (proton transfer)
# over [M+Na]+/[M+formate]- (adduct ions).  Lower number = preferred.
ADDUCT_PRIORITY = {
    "[M+H]+":       0,
    "[M-H]-":       0,
    "[M+Na]+":      1,
    "[M+formate]-": 1,
}

# ESI mode preference for breaking ties: ESI+ preferred over ESI-
MODE_PREFERENCE = {"ES+": 0, "ES-": 1}

# Lazy-built table mapping SUP abbreviation labels to fragment exact masses.
# Populated on first use by _get_abbrev_mass_table() (requires RDKit).
_ABBREV_MASS_TABLE: Optional[Dict[str, float]] = None

# Cache of raw FlowER predictions (before deduplication), set by
# extract_expected_masses() when predict_byproducts=True.
_last_flower_predictions: List = []

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ExpectedSpecies:
    """A chemical species with predicted LCMS adduct masses."""
    name: str               # display name: "SM", "DP", formula, or IUPAC name
    role: str               # "substrate", "reactant", "product"
    exact_mass: float       # monoisotopic neutral mass
    smiles: str
    adducts: Dict[str, float] = field(default_factory=dict)
    source_file: str = ""    # CDX/RXN path if from structure, "" if CSV

# ---------------------------------------------------------------------------
# Mass computation
# ---------------------------------------------------------------------------

def compute_masses(smiles: str) -> Optional[Tuple[float, float]]:
    """
    Compute monoisotopic masses from SMILES.

    Returns (neutral_mass, full_mass) where:
      - neutral_mass: mass of the largest fragment (free base / free acid),
        used for LCMS adduct matching
      - full_mass: mass of the entire molecule including any counterions,
        used for matching against CSV MW which may record the salt form

    For non-salt molecules, both values are identical.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    full_mass = Descriptors.ExactMolWt(mol)

    # Split multi-component SMILES (salts)
    frags = Chem.GetMolFrags(mol, asMols=True)
    if len(frags) > 1:
        neutral_mol = max(frags, key=lambda m: m.GetNumHeavyAtoms())
        neutral_mass = Descriptors.ExactMolWt(neutral_mol)
    else:
        neutral_mass = full_mass

    return (neutral_mass, full_mass)


# Backward-compatible aliases (were private, now public)
_compute_masses = compute_masses


def build_adducts(exact_mass: float) -> Dict[str, float]:
    """Build expected adduct m/z dict from neutral exact mass."""
    return {name: exact_mass + offset for name, (_, offset) in ADDUCTS.items()}


# Backward-compatible alias
_build_adducts = build_adducts


# ---------------------------------------------------------------------------
# CSV name matching
# ---------------------------------------------------------------------------

def _match_csv_name(neutral_mass: float,
                    full_mass: float,
                    reagents,
                    used_indices: set) -> Optional[str]:
    """
    Match a structure's mass to a CSV reagent row by MW.

    Tries both the neutral (free base) mass and the full (salt) mass
    against each CSV MW.  This handles:
      - Free-form structure vs free-form CSV MW  (neutral ≈ CSV)
      - Salt structure vs salt CSV MW            (full ≈ CSV)
      - Salt structure vs free-form CSV MW       (neutral ≈ CSV)

    Returns the CSV reagent name if a match is found (within 2 Da),
    or None.  Marks matched index as used to prevent double-matching.
    """
    best_name = None
    best_delta = 2.0
    best_idx = -1

    for idx, reagent in enumerate(reagents):
        if idx in used_indices or reagent.mw <= 0:
            continue

        # Try neutral mass (free base/acid) against CSV MW
        delta = abs(neutral_mass - reagent.mw)
        if delta < best_delta:
            best_delta = delta
            best_name = reagent.name.strip()
            best_idx = idx

        # Try full mass (including counterion) against CSV MW
        if full_mass != neutral_mass:
            delta = abs(full_mass - reagent.mw)
            if delta < best_delta:
                best_delta = delta
                best_name = reagent.name.strip()
                best_idx = idx

    if best_name and best_idx >= 0:
        used_indices.add(best_idx)
    return best_name


# ---------------------------------------------------------------------------
# SUP abbreviation mass correction (RDKit RXN loading)
# ---------------------------------------------------------------------------

def _get_abbrev_mass_table() -> Dict[str, float]:
    """Build (once) a table of SUP abbreviation label → fragment exact mass.

    The fragment mass is the monoisotopic mass of the group that gets attached
    to the molecule, i.e. the abbreviation minus its '*' attachment-point atom.
    For example COOH → C(=O)OH fragment → 44.998 Da.

    Used to correct masses when RDKit reads SUP SGroup atoms as plain CH3
    placeholders instead of the real abbreviated group.
    """
    global _ABBREV_MASS_TABLE
    if _ABBREV_MASS_TABLE is not None:
        return _ABBREV_MASS_TABLE

    table: Dict[str, float] = {}

    if _HAS_RDKIT:
        H_mass = 1.00794

        def _frag_mass(smiles_with_star: str) -> Optional[float]:
            """Exact mass of the fragment (abbreviation minus the * atom)."""
            full_smi = smiles_with_star.replace("*", "[H]", 1)
            mol = Chem.MolFromSmiles(full_smi)
            if mol is None:
                return None
            return Descriptors.ExactMolWt(mol) - H_mass

        # RDKit built-in abbreviations (COOH, OBn, NHBoc, etc.)
        # Note: abbrev.mol is a query mol with no implicit Hs; extract SMILES
        # from it and re-parse via MolFromSmiles for correct mass computation.
        try:
            from rdkit.Chem import rdAbbreviations
            for abbrev in rdAbbreviations.GetDefaultAbbreviations():
                smi = Chem.MolToSmiles(abbrev.mol)
                fm = _frag_mass(smi)
                if fm is not None:
                    table[abbrev.label] = fm
        except Exception:
            pass

        # Supplementary abbreviations not in RDKit's default list
        _EXTRA_SMILES: Dict[str, str] = {
            "COOtBu":  "*C(=O)OC(C)(C)C",
            "CO2tBu":  "*C(=O)OC(C)(C)C",
            "tBuOOC":  "*C(=O)OC(C)(C)C",
            "OTs":     "*OS(=O)(=O)c1ccc(C)cc1",
            "OTf":     "*OS(=O)(=O)C(F)(F)F",
            "OMs":     "*OS(=O)(=O)C",
            "OMe":     "*OC",
            "OEt":     "*OCC",
            "OiPr":    "*OC(C)C",
            "OBu":     "*OCCCC",
            "OtBu":    "*OC(C)(C)C",
            "OAc":     "*OC(C)=O",
            "OBn":     "*OCc1ccccc1",
            "Ph":      "*c1ccccc1",
            "Bn":      "*Cc1ccccc1",
            "Boc":     "*C(=O)OC(C)(C)C",
            "NBoc":    "*NC(=O)OC(C)(C)C",
            "NHBoc":   "*NC(=O)OC(C)(C)C",
            "Cbz":     "*C(=O)OCc1ccccc1",
            "Fmoc":    "*C(=O)OCC1c2ccccc2-c2ccccc21",
            "TMS":     "*[Si](C)(C)C",
            "TBS":     "*[Si](C)(C)C(C)(C)C",
            "TIPS":    "*[Si](C(C)C)(C(C)C)C(C)C",
            "PMB":     "*Cc1ccc(OC)cc1",
            "MOM":     "*OCOC",
            "Ac":      "*C(C)=O",
            "Piv":     "*C(=O)C(C)(C)C",
        }
        for label, smi in _EXTRA_SMILES.items():
            if label not in table:
                fm = _frag_mass(smi)
                if fm is not None:
                    table[label] = fm

    _ABBREV_MASS_TABLE = table
    return table


def _sup_mass_correction(mol) -> float:
    """Compute total exact-mass correction (Da) for SUP abbreviation groups.

    RDKit reads each SUP SGroup placeholder atom as a plain carbon with
    implicit Hs (e.g., CH3 for degree-1 attachment).  This function computes
    the correction needed to get the true mass of each abbreviated group.

    Returns 0.0 if RDKit is unavailable, no SGroups exist, or all labels are
    unknown.
    """
    if not _HAS_RDKIT:
        return 0.0

    try:
        sgroups = Chem.GetMolSubstanceGroups(mol)
    except Exception:
        return 0.0

    if not sgroups:
        return 0.0

    table = _get_abbrev_mass_table()
    C_mass = 12.000
    H_mass = 1.00794
    total = 0.0

    for sg in sgroups:
        try:
            if sg.GetProp("TYPE") != "SUP":
                continue
            label = sg.GetProp("LABEL")
        except Exception:
            continue

        if label not in table:
            print(f"  Warning: Unknown SUP abbreviation '{label}' — "
                  f"mass may be incorrect", file=sys.stderr)
            continue

        atom_indices = list(sg.GetAtoms())
        if not atom_indices:
            continue

        atom = mol.GetAtomWithIdx(atom_indices[0])
        num_h = atom.GetTotalNumHs()
        placeholder_mass = C_mass + num_h * H_mass
        delta = table[label] - placeholder_mass
        total += delta
        print(f"  SUP correction: '{label}' (C+{num_h}H placeholder) "
              f"{delta:+.3f} Da", file=sys.stderr)

    return total


# ---------------------------------------------------------------------------
# Structure-file extraction (ChemScript + RDKit)
# ---------------------------------------------------------------------------

def _extract_from_structure(source, exp) -> List[ExpectedSpecies]:
    """Load reaction from CDX/RXN and extract species with exact masses."""
    try:
        cs = ChemScriptBridge()
        rxn_data = cs.load_reaction(source)
    except Exception as e:
        print(f"  Warning: Could not load reaction from {source}: {e}",
              file=sys.stderr)
        return []

    species = []
    used_csv_indices: set = set()  # track matched CSV rows

    # Process reactants
    for i, rct in enumerate(rxn_data.get("reactants", [])):
        smiles = rct.get("smiles", "")
        if not smiles:
            continue
        masses = _compute_masses(smiles)
        if masses is None:
            continue
        neutral_mass, full_mass = masses

        # Determine role: match against CSV substrate MW
        # Try both neutral and full mass (CSV may record salt or free form)
        role = "reactant"
        is_substrate = False
        if exp.sm_mass:
            if (abs(neutral_mass - exp.sm_mass) < MW_MATCH_TOLERANCE or
                    abs(full_mass - exp.sm_mass) < MW_MATCH_TOLERANCE):
                is_substrate = True
        if is_substrate:
            role = "substrate"
            name = "SM"
        else:
            # Use CSV reagent name if available, else ChemScript name
            csv_name = _match_csv_name(neutral_mass, full_mass,
                                       exp.reactants, used_csv_indices)
            name = csv_name or rct.get("name") or rct.get(
                "formula", f"Reactant {i+1}")

        sp = ExpectedSpecies(
            name=name, role=role,
            exact_mass=neutral_mass, smiles=smiles,
            source_file=source,
        )
        sp.adducts = _build_adducts(neutral_mass)
        species.append(sp)

    # Process products
    for i, prod in enumerate(rxn_data.get("products", [])):
        smiles = prod.get("smiles", "")
        if not smiles:
            continue
        masses = _compute_masses(smiles)
        if masses is None:
            continue
        neutral_mass, full_mass = masses

        # If there's only one product, label it "DP" (desired product)
        if len(rxn_data.get("products", [])) == 1:
            name = "DP"
        else:
            name = prod.get("name") or prod.get("formula", f"Product {i+1}")

        sp = ExpectedSpecies(
            name=name, role="product",
            exact_mass=neutral_mass, smiles=smiles,
            source_file=source,
        )
        sp.adducts = _build_adducts(neutral_mass)
        species.append(sp)

    return species


# ---------------------------------------------------------------------------
# RXN extraction (RDKit only — no ChemScript)
# ---------------------------------------------------------------------------

def _extract_from_rxn_rdkit(rxn_path: str, exp) -> List[ExpectedSpecies]:
    """Load RXN file directly with RDKit and extract species with exact masses.

    This is the Tier 2 fallback when ChemScript is unavailable but RDKit is.
    RDKit can read V2000 and V3000 RXN files natively.
    """
    try:
        from rdkit.Chem import AllChem
    except ImportError:
        return []

    try:
        rxn = AllChem.ReactionFromRxnFile(rxn_path)
        if rxn is None:
            print(f"  Warning: RDKit could not parse {rxn_path}",
                  file=sys.stderr)
            return []
    except Exception as e:
        print(f"  Warning: RDKit RXN load failed for {rxn_path}: {e}",
              file=sys.stderr)
        return []

    species = []
    used_csv_indices: set = set()

    # Process reactants
    for i in range(rxn.GetNumReactantTemplates()):
        mol = rxn.GetReactantTemplate(i)
        if mol is None or mol.GetNumAtoms() == 0:
            continue
        try:
            # Sanitize so we can compute MW
            Chem.SanitizeMol(mol)
        except Exception:
            continue

        smiles = Chem.MolToSmiles(mol)
        masses = _compute_masses(smiles)
        if masses is None:
            continue
        neutral_mass, full_mass = masses

        # Correct for SUP (superatom) abbreviation groups — RDKit reads them
        # as CH3 placeholders; apply delta to get the true exact mass.
        correction = _sup_mass_correction(mol)
        if correction:
            neutral_mass += correction
            full_mass += correction

        role = "reactant"
        is_substrate = False
        if exp.sm_mass:
            if (abs(neutral_mass - exp.sm_mass) < MW_MATCH_TOLERANCE or
                    abs(full_mass - exp.sm_mass) < MW_MATCH_TOLERANCE):
                is_substrate = True
        if is_substrate:
            role = "substrate"
            name = "SM"
        else:
            csv_name = _match_csv_name(neutral_mass, full_mass,
                                       exp.reactants, used_csv_indices)
            name = csv_name or f"Reactant {i+1}"

        sp = ExpectedSpecies(
            name=name, role=role,
            exact_mass=neutral_mass, smiles=smiles,
            source_file=rxn_path,
        )
        sp.adducts = _build_adducts(neutral_mass)
        species.append(sp)

    # Process products
    for i in range(rxn.GetNumProductTemplates()):
        mol = rxn.GetProductTemplate(i)
        if mol is None or mol.GetNumAtoms() == 0:
            continue
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            continue

        smiles = Chem.MolToSmiles(mol)
        masses = _compute_masses(smiles)
        if masses is None:
            continue
        neutral_mass, full_mass = masses

        correction = _sup_mass_correction(mol)
        if correction:
            neutral_mass += correction
            full_mass += correction

        if rxn.GetNumProductTemplates() == 1:
            name = "DP"
        else:
            name = f"Product {i+1}"

        sp = ExpectedSpecies(
            name=name, role="product",
            exact_mass=neutral_mass, smiles=smiles,
            source_file=rxn_path,
        )
        sp.adducts = _build_adducts(neutral_mass)
        species.append(sp)

    if species:
        print(f"  Loaded reaction via RDKit from {os.path.basename(rxn_path)} "
              f"({len(species)} species)", file=sys.stderr)
    return species


# ---------------------------------------------------------------------------
# CSV MW fallback
# ---------------------------------------------------------------------------

def _fallback_from_csv(exp) -> List[ExpectedSpecies]:
    """Create expected species from CSV MW values (fallback)."""
    species = []

    if exp.sm_mass:
        sp = ExpectedSpecies(
            name="SM", role="substrate",
            exact_mass=exp.sm_mass, smiles="",
        )
        sp.adducts = _build_adducts(exp.sm_mass)
        species.append(sp)

    if exp.product_mass:
        sp = ExpectedSpecies(
            name="DP", role="product",
            exact_mass=exp.product_mass, smiles="",
        )
        sp.adducts = _build_adducts(exp.product_mass)
        species.append(sp)

    return species


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_expected_masses(exp, predict_byproducts=False) -> List[ExpectedSpecies]:
    """
    Extract expected species masses from CDX/RXN structure files.

    Uses ChemScript to load the reaction and extract SMILES for each
    component, then RDKit to compute monoisotopic exact masses and handle
    salt splitting. Falls back to CSV MW values if structure files or
    required libraries are unavailable.

    Args:
        exp: Experiment object with cdx_path, rxn_path, reactants, etc.
        predict_byproducts: If True, run FlowER beam search to predict
            reaction byproducts and add them to the expected species list.
            Requires the 'flower' conda environment. Results are cached.
    """
    sources = [s for s in [exp.cdx_path, exp.rxn_path] if s]

    # Tier 1: ChemScript + RDKit (can load CDX and RXN)
    if sources and _HAS_CHEMSCRIPT and _HAS_RDKIT:
        for source in sources:
            species = _extract_from_structure(source, exp)
            if species:
                break
        else:
            species = None
    else:
        species = None

    # Tier 2: RDKit only — load RXN directly (no ChemScript needed)
    if species is None and _HAS_RDKIT and exp.rxn_path:
        species = _extract_from_rxn_rdkit(exp.rxn_path, exp)

    # Tier 3: CSV MW values (least accurate — average MW, not monoisotopic)
    if species is None:
        species = _fallback_from_csv(exp)

    # Optional: FlowER byproduct prediction
    global _last_flower_predictions
    _last_flower_predictions = []
    if predict_byproducts and exp.rxn_path:
        try:
            from experiments.byproduct_prediction.flower_predictor import (
                predict_byproducts as _predict_bp,
            )
            csv_path = getattr(exp, '_csv_path', '') or ''
            bp_species = _predict_bp(
                rxn_path=exp.rxn_path,
                csv_path=csv_path,
            )
            if bp_species:
                print(f"  FlowER predicted {len(bp_species)} byproduct(s)",
                      file=sys.stderr)
                # Save full list before deduplication (for CDXML output)
                _last_flower_predictions = list(bp_species)
                # Filter out byproducts that duplicate existing species
                # (SM, DP, or CSV reagents) by exact mass
                existing_masses = [s.exact_mass for s in species]
                from cdxml_toolkit.constants import MASS_TOLERANCE
                kept = []
                for bp in bp_species:
                    if any(abs(bp.exact_mass - em) < MASS_TOLERANCE
                           for em in existing_masses):
                        print(f"    Skipping {bp.name} "
                              f"(mass {bp.exact_mass:.1f} duplicates "
                              f"an existing species)", file=sys.stderr)
                        continue
                    # Try to match against CSV reagent names by MW
                    if hasattr(exp, 'reactants') and exp.reactants and bp.smiles:
                        masses = _compute_masses(bp.smiles) if _HAS_RDKIT else None
                        if masses:
                            neutral_m, full_m = masses
                        else:
                            neutral_m = full_m = bp.exact_mass
                        csv_name = _match_csv_name(
                            neutral_m, full_m, exp.reactants, set())
                        if csv_name:
                            bp.name = f"BP-{csv_name}"
                    kept.append(bp)
                if len(kept) < len(bp_species):
                    print(f"    Kept {len(kept)} byproduct(s) after "
                          f"deduplication", file=sys.stderr)
                species.extend(kept)
        except ImportError:
            print("  FlowER predictor not available — "
                  "skipping byproduct prediction", file=sys.stderr)
        except Exception as e:
            print(f"  FlowER prediction failed: {e}", file=sys.stderr)

    return species


def get_last_flower_predictions() -> List[ExpectedSpecies]:
    """Return the full FlowER prediction list from the last call to
    ``extract_expected_masses(predict_byproducts=True)``.

    This is the pre-deduplication list (all predictions after basic MW
    filtering).  Used by procedure_writer to generate the reference CDXML.
    """
    return list(_last_flower_predictions)


# ---------------------------------------------------------------------------
# CLI placeholder
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("mass_resolver: no standalone CLI — "
          "import extract_expected_masses() from procedure_writer.py")
