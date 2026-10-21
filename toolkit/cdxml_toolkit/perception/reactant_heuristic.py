#!/usr/bin/env python3
"""
reactant_heuristic.py — Classify reaction reagents as atom-contributing
or non-contributing using role lookup + RDKit MCS.

Two input modes:
  cdxml   Parse a CDXML reaction file; extract fragments + text from <step>
  smiles  Accept reagent SMILES + product SMILES directly on the CLI

Examples:
  python reactant_heuristic.py cdxml -i reaction.cdxml --pretty
  python reactant_heuristic.py smiles --reagents "C1COCCN1" "c1cc2scnc2Br" \\
         --product "c1cc2scnc2N1CCOCC1" --pretty
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from ..constants import CDXML_FOOTER, CDXML_MINIMAL_HEADER


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReagentInfo:
    """Information about a single reagent being classified."""
    source_id: str = ""
    source_type: str = ""          # "fragment", "text", "smiles_input"
    name: Optional[str] = None
    smiles: Optional[str] = None
    position: str = ""             # "reactant", "above_arrow", "below_arrow"
    classification: str = ""       # "atom_contributing", "non_contributing", "unclassified"
    classification_method: str = ""  # "schneider_fp", "role_lookup", "fm_type", etc.
    mcs_ratio: Optional[float] = None
    rxnmapper_confidence: Optional[float] = None  # deprecated — kept for compat
    schneider_score: Optional[float] = None  # Schneider FP combo score
    role: Optional[str] = None     # "catalyst", "ligand", "base", "solvent", etc.


# ---------------------------------------------------------------------------
# Role Lookup  (Tier 1) — via shared reagent database
# ---------------------------------------------------------------------------

from ..resolve.reagent_db import get_reagent_db

# Transition metals commonly used as catalysts (by atomic number)
CATALYST_METALS = {46, 28, 29, 77, 45, 44, 78, 76, 79}
# Pd=46, Ni=28, Cu=29, Ir=77, Rh=45, Ru=44, Pt=78, Os=76, Au=79


# ---------------------------------------------------------------------------
# CDXML Parsing Helpers  (adapted from cdxml_combiner.py)
# ---------------------------------------------------------------------------

def _get_page(root: ET.Element) -> ET.Element:
    """Find the <page> element in a CDXML root."""
    page = root.find("page")
    if page is None:
        raise SystemExit("ERROR: no <page> element in CDXML")
    return page


def _count_heavy_atoms(frag: ET.Element) -> int:
    """Count non-hydrogen atoms in a fragment."""
    count = 0
    for n in frag.iter("n"):
        if n.get("NodeType") in ("ExternalConnectionPoint", "Fragment",
                                  "Unspecified"):
            continue
        count += 1
    return count


def _get_text_content(el: ET.Element) -> str:
    """Extract concatenated text from all <s> children of a <t> element."""
    parts = []
    for s in el.iter("s"):
        if s.text:
            parts.append(s.text.strip())
    return " ".join(parts).strip()


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


def _attrs_to_str(el: ET.Element) -> str:
    parts = []
    for k, v in el.attrib.items():
        v = v.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        parts.append(f'{k}="{v}"')
    return " ".join(parts)


def _element_to_string(el: ET.Element) -> str:
    tag = el.tag
    attrs = _attrs_to_str(el)
    children = list(el)
    text = el.text or ""
    if attrs:
        open_tag = f"<{tag} {attrs}"
    else:
        open_tag = f"<{tag}"
    if not children and not text.strip():
        return f"{open_tag}/>"
    result = f"{open_tag}>"
    if text.strip():
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        result += safe
    for child in children:
        result += _element_to_string(child)
    result += f"</{tag}>"
    return result


def _fragment_to_cdxml(frag: ET.Element) -> str:
    """Wrap a single <fragment> in a minimal CDXML document."""
    return (
        CDXML_MINIMAL_HEADER + "\n<page id=\"1\">\n"
        + _element_to_string(frag)
        + "\n</page>\n" + CDXML_FOOTER
    )


# ---------------------------------------------------------------------------
# SMILES Extraction
# ---------------------------------------------------------------------------

# Lazy ChemScript singleton
_cs_instance = None
_cs_tried = False


def _get_chemscript():
    """Return a ChemScriptBridge instance (lazy singleton), or None."""
    global _cs_instance, _cs_tried
    if _cs_tried:
        return _cs_instance
    _cs_tried = True
    try:
        from ..chemdraw.chemscript_bridge import ChemScriptBridge
        _cs_instance = ChemScriptBridge()
    except Exception as e:
        print(f"  [warn] ChemScript not available: {e}", file=sys.stderr)
        _cs_instance = None
    return _cs_instance


def _fragment_to_smiles(frag: ET.Element) -> Optional[str]:
    """Convert a CDXML <fragment> to SMILES via ChemScript or RDKit."""
    # Try ChemScript first (handles abbreviation groups better)
    cs = _get_chemscript()
    if cs is not None:
        cdxml_str = _fragment_to_cdxml(frag)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".cdxml", mode="w",
                                              delete=False, encoding="utf-8") as f:
                f.write(cdxml_str)
                tmp_path = f.name
            smiles = cs.write_data(tmp_path, "smiles")
            if smiles and smiles.strip():
                return smiles.strip()
        except Exception as e:
            print(f"  [warn] ChemScript fragment→SMILES failed: {e}",
                  file=sys.stderr)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # RDKit fallback
    try:
        from ..rdkit_utils import frag_to_mol
        from rdkit import Chem
        mol, _ = frag_to_mol(frag)
        if mol is not None:
            return Chem.MolToSmiles(mol)
    except Exception as e:
        print(f"  [warn] RDKit fragment→SMILES failed: {e}",
              file=sys.stderr)

    return None


def _text_to_smiles(text_content: str) -> Optional[str]:
    """Resolve a reagent name to SMILES.

    Resolution chain (first success wins):
      1. py2opsin name->SMILES (offline, handles IUPAC/systematic names)
      2. PubChem name->SMILES via cas_resolver (online, fallback)
    """
    # --- Try OPSIN first (offline) ---
    smiles = _opsin_name_to_smiles(text_content)
    if smiles:
        return smiles

    # --- Fall back to PubChem (online) ---
    try:
        from ..resolve.cas_resolver import resolve_name_to_smiles
        return resolve_name_to_smiles(text_content)
    except Exception as e:
        print(f"  [warn] name->SMILES failed for '{text_content}': {e}",
              file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# OPSIN name resolution (offline)
# ---------------------------------------------------------------------------

_opsin_available: Optional[bool] = None
_java_exe: Optional[str] = None


def _find_java() -> Optional[str]:
    """Find the Java executable for OPSIN.

    Discovery order:
      1. ``java`` on PATH (system-installed)
      2. ``JAVA_HOME`` environment variable
      3. Bundled JRE alongside test data (``CHEM_TEST_DATA`` env var)
      4. Known default location for the project JRE

    Returns the full path to the ``java`` (or ``java.exe``) binary,
    or None if no JRE is found.
    """
    import shutil

    # 1. Already on PATH?
    java = shutil.which("java")
    if java:
        return java

    # 2. JAVA_HOME env var
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = os.path.join(java_home, "bin", "java.exe")
        if os.path.isfile(candidate):
            return candidate
        candidate = os.path.join(java_home, "bin", "java")
        if os.path.isfile(candidate):
            return candidate

    # 3. Bundled JRE relative to CHEM_TEST_DATA
    test_data = os.environ.get("CHEM_TEST_DATA")
    if test_data:
        # Look for any JRE directory inside CHEM_TEST_DATA
        _jre = _scan_for_jre(test_data)
        if _jre:
            return _jre

    # 4. Known default location (project-specific)
    _known = os.path.expanduser(
        os.path.join("~", "chem-test-data",
                     "OpenJDK21U-jre_x64_windows_hotspot_21.0.10_7"))
    if os.path.isdir(_known):
        _jre = _scan_for_jre(_known)
        if _jre:
            return _jre

    return None


def _scan_for_jre(base_dir: str) -> Optional[str]:
    """Scan a directory tree (1 level deep) for a JRE bin/java."""
    for name in ("bin",):
        candidate = os.path.join(base_dir, name, "java.exe")
        if os.path.isfile(candidate):
            return candidate
        candidate = os.path.join(base_dir, name, "java")
        if os.path.isfile(candidate):
            return candidate

    # Check one level of subdirectories (e.g. jdk-21.0.10+7-jre/bin/)
    try:
        for entry in os.listdir(base_dir):
            subdir = os.path.join(base_dir, entry)
            if os.path.isdir(subdir):
                candidate = os.path.join(subdir, "bin", "java.exe")
                if os.path.isfile(candidate):
                    return candidate
                candidate = os.path.join(subdir, "bin", "java")
                if os.path.isfile(candidate):
                    return candidate
    except OSError:
        pass
    return None


def _opsin_name_to_smiles(name: str) -> Optional[str]:
    """Try to resolve a chemical name to SMILES via OPSIN (offline).

    OPSIN handles systematic/IUPAC names and many common names well
    (e.g. "cesium carbonate", "triethylamine", "sodium tert-butoxide").
    Fails on abbreviations (BINAP, Pd2dba3) and some organometallics.

    Requires the py2opsin package.  A JRE is auto-downloaded on first
    use if no system Java is found (via :mod:`cdxml_toolkit.resolve.jre_manager`).
    """
    global _opsin_available, _java_exe
    if _opsin_available is False:
        return None
    try:
        import warnings
        from py2opsin import py2opsin

        # Ensure Java is discoverable by py2opsin's subprocess call.
        # Uses the centralized JRE manager which auto-downloads if needed.
        from cdxml_toolkit.resolve.jre_manager import ensure_java_on_path
        if not ensure_java_on_path():
            # Fall back to legacy _find_java for non-standard locations
            if _java_exe is None:
                _java_exe = _find_java()
            if _java_exe and _java_exe not in os.environ.get("PATH", ""):
                java_bin_dir = os.path.dirname(_java_exe)
                os.environ["PATH"] = java_bin_dir + os.pathsep + os.environ.get("PATH", "")
                java_home = os.path.dirname(java_bin_dir)
                os.environ["JAVA_HOME"] = java_home

        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "py2opsin_temp_input.txt")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = py2opsin(name, tmp_fpath=tmp)
        if result:
            _opsin_available = True
            return result
        _opsin_available = True
        return None
    except FileNotFoundError:
        if _opsin_available is None:
            print("  [info] OPSIN unavailable (Java not found)", file=sys.stderr)
        _opsin_available = False
        return None
    except ImportError:
        if _opsin_available is None:
            print("  [info] py2opsin not installed", file=sys.stderr)
        _opsin_available = False
        return None
    except Exception as e:
        print(f"  [info] OPSIN name->SMILES failed for '{name}': {e}",
              file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Tier 1 — Role Lookup
# ---------------------------------------------------------------------------

def _contains_catalyst_metal(smiles: str) -> bool:
    """Check if a molecule contains a transition-metal catalyst atom."""
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        return any(a.GetAtomicNum() in CATALYST_METALS for a in mol.GetAtoms())
    except Exception:
        return False


def _is_inorganic(smiles: str) -> bool:
    """Heuristic: molecule has no carbons, or only 1 C with ≥4 heavy atoms
    (likely carbonate, cyanide, etc.)."""
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        carbons = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 6)
        total = mol.GetNumHeavyAtoms()
        if carbons == 0:
            return True
        if carbons == 1 and total >= 4:
            return True
        return False
    except Exception:
        return False


def role_lookup(smiles: Optional[str], name: Optional[str]
                ) -> Optional[Tuple[str, str]]:
    """Tier 1 classification.  Returns (role, method) or None."""
    db = get_reagent_db()

    # 1. SMILES-based lookup (exact canonical match)
    if smiles:
        role = db.role_for_smiles(smiles)
        if role:
            return (role, "role_lookup")

    # 1b. Stereo-agnostic SMILES lookup.  RDKit-only SMILES extraction
    #     often omits E/Z on double bonds (e.g. DEAD's N=N) because
    #     frag_to_mol doesn't set bond stereo from 2D coordinates.
    if smiles:
        role = _role_for_smiles_no_stereo(smiles, db)
        if role:
            return (role, "role_lookup_no_stereo")

    # 2. Name-based lookup
    if name:
        role = db.role_for_name(name)
        if role:
            return (role, "role_lookup")

    # 3. Metal-containing → catalyst
    if smiles and _contains_catalyst_metal(smiles):
        return ("catalyst", "metal_check")

    # 4. Inorganic salt
    if smiles and _is_inorganic(smiles):
        return ("inorganic_salt", "inorganic_check")

    return None


def _role_for_smiles_no_stereo(smiles: str, db) -> Optional[str]:
    """Match SMILES against DB after stripping stereochemistry."""
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        Chem.RemoveStereochemistry(mol)
        flat_smi = Chem.MolToSmiles(mol)

        for smi_key, entry in db._by_smiles.items():
            mol2 = Chem.MolFromSmiles(smi_key)
            if mol2 is None:
                continue
            Chem.RemoveStereochemistry(mol2)
            if flat_smi == Chem.MolToSmiles(mol2):
                return entry.get("role")
    except ImportError:
        pass
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Tier 2 — RDKit MCS  (kept for alignment use; no longer used for classification)
# ---------------------------------------------------------------------------

def mcs_ratio(reagent_smiles: str, product_smiles: str) -> Optional[float]:
    """Compute MCS heavy-atom ratio: MCS_atoms / reagent_heavy_atoms.

    NOTE: No longer used for classification (replaced by Schneider FP).
    Kept because alignment.py may call it for 2D coordinate matching.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS

        reagent_mol = Chem.MolFromSmiles(reagent_smiles)
        product_mol = Chem.MolFromSmiles(product_smiles)
        if reagent_mol is None or product_mol is None:
            return None

        reagent_heavy = reagent_mol.GetNumHeavyAtoms()
        if reagent_heavy == 0:
            return None

        result = rdFMCS.FindMCS(
            [reagent_mol, product_mol],
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareAny,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            timeout=10,
        )

        if result.canceled or result.numAtoms == 0:
            return 0.0

        return result.numAtoms / reagent_heavy

    except Exception as e:
        print(f"  [warn] MCS failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Tier 1 — Schneider FP-based reaction role assignment
# ---------------------------------------------------------------------------
# Implements the algorithm from Schneider et al., JCIM 2016:
# "What's What: The (Nearly) Definitive Guide to Reaction Role Assignment"
#
# Context-aware: considers the specific product to determine which candidates
# are atom-contributing (reactants) vs non-contributing (reagents).

# Common reagents mined from 1.3M USPTO patent reactions (appear in >1000
# reactions across >100 reaction types).  Canonical SMILES.
_SCHNEIDER_COMMON_REAGENTS: Optional[set] = None


def _get_common_reagents() -> set:
    """Lazily build the canonical common-reagent set."""
    global _SCHNEIDER_COMMON_REAGENTS
    if _SCHNEIDER_COMMON_REAGENTS is not None:
        return _SCHNEIDER_COMMON_REAGENTS
    try:
        from rdkit import Chem
    except ImportError:
        _SCHNEIDER_COMMON_REAGENTS = set()
        return _SCHNEIDER_COMMON_REAGENTS

    raw = [
        # Solvents
        "ClCCl", "C(Cl)(Cl)Cl", "CS(C)=O", "CCOC(C)=O", "CC#N",
        "C1CCOC1", "C1COCCO1", "CO", "CCO", "CC(C)=O",
        "c1ccncc1", "CN(C)C=O", "c1ccccc1", "Cc1ccccc1", "CCOCC",
        "CC(C)O", "ClC(Cl)Cl", "O", "CC(=O)O",
        # Bases
        "CCN(CC)CC", "CN(C)C",
        # Common ions / salts
        "[Na+]", "[K+]", "[Li+]", "[Cs+]",
        "[OH-]", "[Cl-]", "[Br-]", "[I-]", "[F-]", "[H-]",
        "[NH4+]", "O=C([O-])[O-]", "O=S([O-])([O-])=O",
        # Catalyst metals
        "[Pd]", "[Pt]", "[Ni]",
    ]
    result = set()
    for smi in raw:
        mol = Chem.MolFromSmiles(smi)
        if mol:
            result.add(Chem.MolToSmiles(mol))
    _SCHNEIDER_COMMON_REAGENTS = result
    return result


def _is_schneider_common_reagent(mol) -> bool:
    """Check if a molecule (or all its fragments) are common reagents."""
    from rdkit import Chem
    common = _get_common_reagents()
    can_smi = Chem.MolToSmiles(mol)
    if can_smi in common:
        return True
    frags = Chem.GetMolFrags(mol, asMols=True)
    if len(frags) > 1:
        return all(Chem.MolToSmiles(f) in common for f in frags)
    return False


def _schneider_fp(mol, scaffold: bool = False):
    """Count-based Morgan FP (radius=1) as a dict."""
    from rdkit.Chem import rdFingerprintGenerator as rfg
    gen = rfg.GetMorganGenerator(
        radius=1,
        atomInvariantsGenerator=(
            rfg.GetMorganAtomInvGen(includeRingMembership=False)
            if scaffold else None
        ),
    )
    return dict(gen.GetCountFingerprint(mol).GetNonzeroElements())


def _schneider_sum_fps(fps):
    """Sum multiple count fingerprints."""
    from collections import Counter
    r = Counter()
    for fp in fps:
        for k, v in fp.items():
            r[k] += v
    return dict(r)


def _schneider_score(prod_fp: dict, react_fp: dict) -> float:
    """Score a reactant combination against the product FP.

    First term:  coverage (how well reactants explain the product)
    Second term: leaving-group penalty (weighted less — sqrt)
    """
    keys = set(prod_fp) | set(react_fp)
    total = sum(prod_fp.values())
    if not keys or total == 0:
        return 0.0
    pos = sum(max(0, prod_fp.get(k, 0) - react_fp.get(k, 0)) for k in keys)
    neg = sum(max(0, react_fp.get(k, 0) - prod_fp.get(k, 0)) for k in keys)
    return max(0.0, (1.0 - pos / total) - 0.5 * (neg / total) ** 0.5)


def _schneider_classify(reagents: List[ReagentInfo],
                         product_smiles: str) -> None:
    """Tier 1: Schneider FP-based reaction role assignment.

    Classifies unclassified reagents as atom_contributing or non_contributing
    by finding the combination of candidates whose Morgan fingerprints best
    explain the product fingerprint.

    Modifies reagents in place.
    """
    if not product_smiles:
        return

    try:
        from rdkit import Chem
    except ImportError:
        return

    import itertools

    # Parse product(s) — may contain fragments separated by '.'
    prod_mol = Chem.MolFromSmiles(product_smiles)
    if prod_mol is None:
        return

    prod_fp_d = _schneider_fp(prod_mol, scaffold=False)
    prod_fp_s = _schneider_fp(prod_mol, scaffold=True)
    total_prod_atoms = prod_mol.GetNumHeavyAtoms()

    if total_prod_atoms == 0:
        return

    # Collect unclassified reagents that have parseable SMILES
    candidates = []
    for r in reagents:
        if r.classification:
            continue
        if not r.smiles:
            continue
        mol = Chem.MolFromSmiles(r.smiles)
        if mol is None:
            continue
        candidates.append({
            "reagent": r,
            "mol": mol,
            "fp_d": _schneider_fp(mol, scaffold=False),
            "fp_s": _schneider_fp(mol, scaffold=True),
            "n_atoms": mol.GetNumHeavyAtoms(),
            "is_common": _is_schneider_common_reagent(mol),
        })

    if not candidates:
        return

    def _find_best(cand_list):
        """Find the best-scoring reactant combination."""
        best_score, best_combo = -1.0, None
        n = len(cand_list)
        if n == 0 or n > 18:
            return best_combo, best_score
        for r in range(1, min(n + 1, 6)):  # max 5 reactants
            for combo in itertools.combinations(cand_list, r):
                na = sum(c["n_atoms"] for c in combo)
                if na < total_prod_atoms * 0.5 or na > total_prod_atoms * 6:
                    continue
                fp_d = _schneider_sum_fps([c["fp_d"] for c in combo])
                fp_s = _schneider_sum_fps([c["fp_s"] for c in combo])
                sc = (_schneider_score(prod_fp_d, fp_d) +
                      _schneider_score(prod_fp_s, fp_s))
                if sc > best_score:
                    best_score, best_combo = sc, combo
        return best_combo, best_score

    # Phase 1: try without common reagents
    non_common = [c for c in candidates if not c["is_common"]]
    best_combo, best_score = _find_best(non_common)

    # Phase 2: if no good result, include common reagents
    if best_combo is None or best_score < 0.5:
        combo2, score2 = _find_best(candidates)
        if score2 > best_score:
            best_combo, best_score = combo2, score2

    # Apply results
    reactant_set = set()
    if best_combo:
        reactant_set = {id(c["reagent"]) for c in best_combo}

    for c in candidates:
        r = c["reagent"]
        if id(r) in reactant_set:
            r.classification = "atom_contributing"
        else:
            r.classification = "non_contributing"
        r.classification_method = "schneider_fp"
        r.schneider_score = round(best_score, 4)

    # Mark any remaining unclassified (no SMILES) as unclassified
    for r in reagents:
        if not r.classification:
            r.classification = "unclassified"
            r.classification_method = "none"

    print(f"  Schneider FP classification (score={best_score:.3f}): "
          f"{sum(1 for c in candidates if c['reagent'].classification == 'atom_contributing')} "
          f"reactant(s), "
          f"{sum(1 for c in candidates if c['reagent'].classification == 'non_contributing')} "
          f"reagent(s)",
          file=sys.stderr)


# ---------------------------------------------------------------------------
# Main Classification Logic
# ---------------------------------------------------------------------------

def classify_reagents(reagents: List[ReagentInfo],
                      product_smiles: str,
                      mcs_threshold: float = 0.3,
                      use_rxnmapper: bool = True) -> List[ReagentInfo]:
    """Classify each reagent using a two-tier strategy.

    Tier 1: Schneider FP scoring — context-aware binary classification
            (atom_contributing vs non_contributing).
    Tier 2: Curated DB lookup — semantic role enrichment for non-contributing
            species (adds labels like 'base', 'catalyst', 'solvent').

    Schneider always wins on the binary question.  The DB never overrides it.

    Args:
        mcs_threshold: deprecated, ignored (kept for API compat)
        use_rxnmapper: deprecated, ignored (kept for API compat)
    """
    # --- Tier 1: Schneider FP-based classification (context-aware) ---
    _schneider_classify(reagents, product_smiles)

    # --- Tier 2: Semantic role enrichment for non-contributing species ---
    for r in reagents:
        if r.classification == "non_contributing" and not r.role:
            result = role_lookup(r.smiles, r.name)
            if result:
                role, _method = result
                r.role = role  # "base", "catalyst", "solvent", etc.

    return reagents


def _try_rxnmapper_classification(reagents: List[ReagentInfo],
                                   product_smiles: str) -> None:
    """Tier 1.5: Use RXNMapper atom maps to classify unclassified reagents.

    Builds a reaction SMILES from all unclassified reagent SMILES + product,
    calls RXNMapper via subprocess (rxn-experiments env), and uses the atom
    map results to determine which reagents are atom-contributing.

    Modifies reagents in place. Silently returns if RXNMapper is unavailable.
    """
    if not product_smiles:
        return

    # Collect unclassified reagents that have SMILES
    unclassified = [r for r in reagents if not r.classification and r.smiles]
    if not unclassified:
        return

    # Build reaction SMILES: all unclassified reagent SMILES >> product
    reactant_smiles_list = [r.smiles for r in unclassified]
    rxn_smi = ".".join(reactant_smiles_list) + ">>" + product_smiles

    # Try to call RXNMapper
    try:
        from experiments.atom_mapping.rxn_atom_mapper import classify_roles
    except ImportError:
        # rxn_atom_mapper not available — skip silently
        return

    try:
        result = classify_roles(rxn_smi)
    except Exception as exc:
        print(f"  [info] RXNMapper classification failed: {exc}",
              file=sys.stderr)
        return

    if result is None:
        return

    confidence = result.get("confidence", 0.0)
    components = result.get("components", [])

    if not components:
        return

    print(f"  RXNMapper classification (confidence={confidence:.4f}):",
          file=sys.stderr)

    # Match results back to reagents by canonical SMILES
    try:
        from rdkit import Chem
        def _canon(smi):
            mol = Chem.MolFromSmiles(smi)
            return Chem.MolToSmiles(mol) if mol else smi
    except ImportError:
        def _canon(smi):
            return smi

    # Build lookup: canonical SMILES → RXNMapper component info
    rxnm_by_smi = {}
    for comp in components:
        canon = _canon(comp["smiles"])
        rxnm_by_smi[canon] = comp

    # Apply to unclassified reagents
    for r in unclassified:
        canon = _canon(r.smiles)
        comp = rxnm_by_smi.get(canon)
        if comp is None:
            continue

        is_contributing = comp.get("atom_contributing")
        if is_contributing is None:
            continue

        if is_contributing:
            r.classification = "atom_contributing"
            r.classification_method = "rxnmapper"
            n_atoms = comp.get("n_product_atoms", 0)
            print(f"    {r.smiles[:50]:50s} → atom_contributing "
                  f"({n_atoms} atoms in product)", file=sys.stderr)
        else:
            r.classification = "non_contributing"
            r.classification_method = "rxnmapper"
            print(f"    {r.smiles[:50]:50s} → non_contributing",
                  file=sys.stderr)

        r.rxnmapper_confidence = confidence


# ---------------------------------------------------------------------------
# CDXML Mode Entry Point
# ---------------------------------------------------------------------------

def classify_from_cdxml(cdxml_path: str,
                        mcs_threshold: float = 0.3,
                        use_rxnmapper: bool = False) -> Dict[str, Any]:
    """Parse a CDXML reaction file and classify all reagents.

    mcs_threshold and use_rxnmapper are deprecated and ignored (kept for
    API compat).  Classification uses Schneider FP scoring internally.
    """
    tree = ET.parse(cdxml_path)
    root = tree.getroot()
    page = _get_page(root)

    # --- Parse <step> metadata ---
    scheme = page.find("scheme")
    step = scheme.find("step") if scheme is not None else None
    if step is None:
        raise SystemExit("ERROR: no <scheme><step> found in CDXML")

    reactant_ids = step.get("ReactionStepReactants", "").split()
    product_ids  = step.get("ReactionStepProducts",  "").split()
    above_ids    = step.get("ReactionStepObjectsAboveArrow", "").split()
    below_ids    = step.get("ReactionStepObjectsBelowArrow", "").split()

    # Build id → element map
    id_to_el: Dict[str, ET.Element] = {}
    for el in page:
        eid = el.get("id", "")
        if eid:
            id_to_el[eid] = el

    # --- Extract product SMILES ---
    product_smiles = None
    for pid in product_ids:
        el = id_to_el.get(pid)
        if el is not None and el.tag == "fragment":
            product_smiles = _fragment_to_smiles(el)
            if product_smiles:
                break
    if not product_smiles:
        raise SystemExit("ERROR: could not extract product SMILES")

    print(f"Product SMILES: {product_smiles}", file=sys.stderr)

    # --- Collect reagents ---
    reagents: List[ReagentInfo] = []
    seen_ids: set = set()

    def _process_element(eid: str, position: str):
        """Process a single element (fragment or text) as a potential reagent."""
        if eid in seen_ids:
            return
        seen_ids.add(eid)

        el = id_to_el.get(eid)
        if el is None:
            return

        fm_type = _get_fm_molecule_type(el)

        # Skip products and condition text
        if fm_type == 3:
            return
        if fm_type == 2:
            return

        ri = ReagentInfo(source_id=eid, position=position)

        # FM type = 1 → solvent hint (Schneider may override)
        if fm_type == 1:
            ri.source_type = el.tag
            ri.role = "solvent"  # hint only; Schneider decides classification
            if el.tag == "t":
                ri.name = _get_text_content(el)

        # Fragment → extract SMILES via ChemScript
        if el.tag == "fragment":
            ri.source_type = "fragment"
            ri.smiles = _fragment_to_smiles(el)
            if ri.smiles:
                print(f"  Fragment {eid}: {ri.smiles}", file=sys.stderr)

        # Text → resolve name to SMILES via PubChem
        elif el.tag == "t":
            ri.source_type = "text"
            text = _get_text_content(el)
            ri.name = text
            ri.smiles = _text_to_smiles(text)
            if ri.smiles:
                print(f"  Text '{text}' → {ri.smiles}", file=sys.stderr)
            else:
                print(f"  Text '{text}' → no SMILES (name-only)", file=sys.stderr)
        else:
            return

        reagents.append(ri)

    # Process reactants first, then above/below arrow
    for rid in reactant_ids:
        _process_element(rid, "reactant")
    for eid in above_ids:
        _process_element(eid, "above_arrow")
    for eid in below_ids:
        _process_element(eid, "below_arrow")

    # --- Classify ---
    classify_reagents(reagents, product_smiles, mcs_threshold,
                      use_rxnmapper=use_rxnmapper)

    return {
        "cdxml_file": os.path.basename(cdxml_path),
        "product_smiles": product_smiles,
        "reagents": [_reagent_to_dict(r) for r in reagents],
    }


# ---------------------------------------------------------------------------
# SMILES Mode Entry Point
# ---------------------------------------------------------------------------

def classify_from_smiles(reagent_smiles: List[str],
                         product_smiles: str,
                         reagent_names: Optional[List[str]] = None,
                         mcs_threshold: float = 0.3,
                         use_rxnmapper: bool = True) -> Dict[str, Any]:
    """Classify reagents given as SMILES strings."""
    reagents: List[ReagentInfo] = []
    for i, smi in enumerate(reagent_smiles):
        name = reagent_names[i] if reagent_names and i < len(reagent_names) else None
        ri = ReagentInfo(source_type="smiles_input", smiles=smi, name=name)
        reagents.append(ri)
    classify_reagents(reagents, product_smiles, mcs_threshold,
                      use_rxnmapper=use_rxnmapper)
    return {
        "product_smiles": product_smiles,
        "reagents": [_reagent_to_dict(r) for r in reagents],
    }


# ---------------------------------------------------------------------------
# Output Helpers
# ---------------------------------------------------------------------------

def _reagent_to_dict(r: ReagentInfo) -> Dict[str, Any]:
    d = asdict(r)
    # Drop empty/None optional fields for cleaner output
    if d["mcs_ratio"] is None:
        del d["mcs_ratio"]
    if d.get("rxnmapper_confidence") is None:
        d.pop("rxnmapper_confidence", None)
    if d.get("schneider_score") is None:
        d.pop("schneider_score", None)
    if d["role"] is None:
        del d["role"]
    if d["name"] is None:
        del d["name"]
    return d


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify reaction reagents as atom-contributing "
                    "or non-contributing (role lookup + RDKit MCS).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="mode", required=True,
                                help="Input mode")

    # Shared args for both modes
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-o", "--output",
                        help="Output JSON file (default: stdout)")
    common.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON output")
    common.add_argument("--threshold", type=float, default=0.5,
                        help="MCS ratio threshold (default: 0.5)")

    # CDXML mode
    p_cdxml = sub.add_parser("cdxml", parents=[common],
                              help="Classify from a CDXML reaction file")
    p_cdxml.add_argument("-i", "--input", required=True,
                          help="Input CDXML file")

    # SMILES mode
    p_smi = sub.add_parser("smiles", parents=[common],
                            help="Classify from SMILES strings")
    p_smi.add_argument("--reagents", nargs="+", required=True,
                        help="Reagent SMILES strings")
    p_smi.add_argument("--product", required=True,
                        help="Product SMILES")
    p_smi.add_argument("--names", nargs="+", default=None,
                        help="Reagent names (parallel to --reagents)")

    args = parser.parse_args(argv)

    if args.mode == "cdxml":
        result = classify_from_cdxml(args.input, args.threshold)
    elif args.mode == "smiles":
        result = classify_from_smiles(
            args.reagents, args.product, args.names, args.threshold)
    else:
        parser.print_help()
        return 1

    indent = 2 if args.pretty else None
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str + "\n")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
