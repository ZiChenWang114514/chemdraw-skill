"""
LLM-assisted molecule construction via IUPAC name manipulation.

Provides composable tools designed for use with an LLM orchestrator.
The LLM translates natural language descriptions of molecules into tool calls
that manipulate IUPAC names, which are then validated and converted to
structures.

Architecture::

    NL description --> LLM orchestrator --> tool calls --> IUPAC name --> CDXML

The key insight: IUPAC names are a lossless text representation of molecules.
Instead of having an LLM generate SMILES or manipulate CDXML directly, we let
the LLM do "name surgery" — assembling, modifying, and validating IUPAC names
using grounded tools.  This avoids hallucinated SMILES while leveraging LLMs'
strength with natural language.

Layer 2 — Name manipulation tools:
    resolve_to_smiles   — Resolve any chemical identifier to SMILES
    get_prefix_form     — Get IUPAC substituent prefix for a group
    assemble_name       — Build IUPAC name from parent + substituents
    modify_name         — Add/swap/remove substituents in an existing name
    validate_name       — Check if an IUPAC name resolves to a valid molecule
    name_to_structure   — Convert validated name to CDXML
    enumerate_names     — List alternative IUPAC name forms for a molecule

Layer 3 — Graph manipulation tools (for structural transformations):
    list_reactions      — List available named reaction templates
    apply_reaction      — Apply a reaction template (Suzuki, Buchwald, etc.)
    deprotect           — Remove protecting groups (Boc, Fmoc, Cbz, etc.)

Meta:
    get_tool_definitions — Export all tool schemas for LLM function calling

Usage (Python)::

    from cdxml_toolkit.naming.mol_builder import (
        get_prefix_form, assemble_name, validate_name, name_to_structure,
    )

    pf = get_prefix_form("CF3")
    # {'prefix': 'trifluoromethyl', 'source': 'table', 'ok': True}

    result = assemble_name("pyridine", [
        {"locant": "2", "prefix": "chloro"},
        {"locant": "3", "prefix": pf["prefix"]},
    ])
    # {'name': '2-chloro-3-(trifluoromethyl)pyridine', 'valid': True,
    #  'smiles': '...', 'ok': True}

    cdxml = name_to_structure(result["name"])
    # {'cdxml': '<?xml ...', 'ok': True}
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singletons — avoid import-time cost for heavy dependencies
# ---------------------------------------------------------------------------

_cs_instance = None
_cs_failed = False


def _get_cs():
    """Lazily obtain a ChemScriptBridge instance (or None)."""
    global _cs_instance, _cs_failed
    if _cs_failed:
        return None
    if _cs_instance is not None:
        return _cs_instance
    try:
        from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
        _cs_instance = ChemScriptBridge()
        return _cs_instance
    except Exception as exc:
        logger.debug("ChemScript unavailable: %s", exc)
        _cs_failed = True
        return None


def _rdkit_canonical(smiles: str) -> Optional[str]:
    """Canonical SMILES via RDKit, or None."""
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol else None


# ---------------------------------------------------------------------------
# Prefix lookup table — covers common med-chem substituents
# ---------------------------------------------------------------------------

# Maps group identifiers (abbreviations, names, formulae) to IUPAC prefix
# form suitable for direct insertion into a substituted name.
# The table is checked case-insensitively.
_PREFIX_TABLE: Dict[str, str] = {
    # --- Halogens ---
    "f": "fluoro", "cl": "chloro", "br": "bromo", "i": "iodo",
    "fluorine": "fluoro", "chlorine": "chloro",
    "bromine": "bromo", "iodine": "iodo",

    # --- Oxygen ---
    "oh": "hydroxy", "ome": "methoxy", "oet": "ethoxy",
    "oac": "acetyloxy", "obn": "benzyloxy", "oph": "phenoxy",
    "methoxy": "methoxy", "ethoxy": "ethoxy", "hydroxy": "hydroxy",
    "ocf3": "trifluoromethoxy", "oipr": "isopropoxy",

    # --- Nitrogen ---
    "nh2": "amino", "nhme": "methylamino", "nme2": "dimethylamino",
    "nhac": "acetamido", "no2": "nitro", "n3": "azido",
    "amino": "amino", "nitro": "nitro", "azido": "azido",

    # --- Simple carbon ---
    "me": "methyl", "et": "ethyl", "pr": "propyl", "npr": "propyl",
    "ipr": "propan-2-yl", "bu": "butyl", "nbu": "butyl",
    "tbu": "tert-butyl", "sbu": "sec-butyl", "ibu": "isobutyl",
    "methyl": "methyl", "ethyl": "ethyl",
    "vinyl": "ethenyl", "allyl": "prop-2-en-1-yl",
    "isopropyl": "propan-2-yl",

    # --- Cycloalkyl ---
    "cyclopropyl": "cyclopropyl", "cyclobutyl": "cyclobutyl",
    "cyclopentyl": "cyclopentyl", "cyclohexyl": "cyclohexyl",
    "cyclopropane": "cyclopropyl", "cyclobutane": "cyclobutyl",
    "cyclopentane": "cyclopentyl", "cyclohexane": "cyclohexyl",

    # --- Aryl ---
    "ph": "phenyl", "bn": "benzyl", "bz": "benzoyl",
    "phenyl": "phenyl", "benzyl": "benzyl",

    # --- Functional groups (abbreviations) ---
    "cn": "cyano", "cho": "formyl", "cooh": "carboxy",
    "co2h": "carboxy", "-cooh": "carboxy", "-co2h": "carboxy",
    "come": "acetyl", "ac": "acetyl",
    "conh2": "carbamoyl", "-conh2": "carbamoyl",
    "coome": "methoxycarbonyl", "co2me": "methoxycarbonyl",
    "meo2c": "methoxycarbonyl", "meoco": "methoxycarbonyl",
    "cooch3": "methoxycarbonyl", "-cooch3": "methoxycarbonyl",
    "-coome": "methoxycarbonyl", "-co2me": "methoxycarbonyl",
    "cooet": "ethoxycarbonyl", "co2et": "ethoxycarbonyl",
    "eto2c": "ethoxycarbonyl", "etoco": "ethoxycarbonyl",
    "cooipr": "isopropoxycarbonyl", "co2ipr": "isopropoxycarbonyl",
    "cootbu": "tert-butoxycarbonyl", "co2tbu": "tert-butoxycarbonyl",
    "-cho": "formyl",

    # --- Functional group descriptors (natural language → prefix) ---
    "methyl ester": "methoxycarbonyl",
    "me ester": "methoxycarbonyl",
    "ome ester": "methoxycarbonyl",
    "ethyl ester": "ethoxycarbonyl",
    "et ester": "ethoxycarbonyl",
    "isopropyl ester": "isopropoxycarbonyl",
    "tert-butyl ester": "tert-butoxycarbonyl",
    "aldehyde": "formyl",
    "ketone": "oxo",
    "carboxylic acid": "carboxy",
    "nitrile": "cyano",
    "amide": "carbamoyl",
    "primary amide": "carbamoyl",
    "alcohol": "hydroxy",
    "hydroxyl": "hydroxy",
    "thiol": "sulfanyl",
    "mercaptan": "sulfanyl",
    "sulfonic acid": "sulfo",
    "sulfonamide": "sulfamoyl",

    # --- Fluorocarbons ---
    "cf3": "trifluoromethyl", "chf2": "difluoromethyl",
    "ccl3": "trichloromethyl",

    # --- Sulphur ---
    "sh": "sulfanyl", "sme": "methylsulfanyl",
    "so2me": "methanesulfonyl", "ms": "methanesulfonyl",
    "so2nh2": "sulfamoyl",

    # --- Heterocycles as substituent prefix ---
    "morpholine": "morpholino", "morpholinyl": "morpholino",
    "morpholino": "morpholino",
    "piperidine": "piperidin-1-yl", "piperidinyl": "piperidin-1-yl",
    "piperazine": "piperazin-1-yl", "piperazinyl": "piperazin-1-yl",
    "pyrrolidine": "pyrrolidin-1-yl", "pyrrolidinyl": "pyrrolidin-1-yl",
    "pyridine": "pyridinyl", "pyridinyl": "pyridinyl",
    "pyrimidine": "pyrimidinyl",
    "thiophene": "thiophen-2-yl", "thienyl": "thiophen-2-yl",
    "furan": "furan-2-yl", "furyl": "furan-2-yl",
    "pyrrole": "pyrrol-1-yl",
    "imidazole": "imidazolyl", "imidazolyl": "imidazolyl",
    "thiazole": "thiazolyl", "thiazolyl": "thiazolyl",
    "oxazole": "oxazolyl", "oxazolyl": "oxazolyl",
    "indole": "indolyl",
}

# IUPAC multiplying prefixes for identical substituents
_MULTIPLIERS = {2: "di", 3: "tri", 4: "tetra", 5: "penta", 6: "hexa"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_query(query: str, use_network: bool = True) -> Optional[Dict]:
    """Multi-tier resolution chain: reagent DB → formula → ChemScript → PubChem.

    Returns {"smiles": ..., "source": ...} or None.
    """
    from rdkit import Chem

    clean = query.strip()
    if not clean:
        return None

    # Tier 1: Reagent DB
    try:
        from cdxml_toolkit.resolve.reagent_db import get_reagent_db
        db = get_reagent_db()
        entry = db.entry_for_name(clean.lower())
        if entry:
            smi = entry.get("smiles")
            if isinstance(smi, list):
                smi = smi[0]
            if smi and Chem.MolFromSmiles(smi):
                return {"smiles": _rdkit_canonical(smi), "source": "reagent_db"}
    except Exception:
        pass

    # Tier 2: Condensed formula
    try:
        from cdxml_toolkit.resolve.condensed_formula import resolve_condensed_formula
        smi = resolve_condensed_formula(clean)
        if smi:
            canon = _rdkit_canonical(smi)
            if canon:
                return {"smiles": canon, "source": "formula"}
    except Exception:
        pass

    # Tier 3: ChemScript (name → SMILES)
    cs = _get_cs()
    if cs is not None:
        try:
            smi = cs.write_data(clean, "smiles", source_format="name")
            if smi and Chem.MolFromSmiles(smi):
                return {"smiles": _rdkit_canonical(smi), "source": "chemscript"}
        except Exception:
            pass

    # Tier 3b: OPSIN (offline IUPAC name → SMILES, bundled JRE)
    try:
        from cdxml_toolkit.resolve.jre_manager import ensure_java_on_path
        if ensure_java_on_path():
            import warnings, tempfile, os
            from py2opsin import py2opsin as _py2opsin
            tmp = os.path.join(tempfile.gettempdir(), "py2opsin_temp_input.txt")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                smi = _py2opsin(clean, tmp_fpath=tmp)
            if smi and Chem.MolFromSmiles(smi):
                return {"smiles": _rdkit_canonical(smi), "source": "opsin"}
    except (ImportError, FileNotFoundError):
        pass
    except Exception:
        pass

    # Tier 4: PubChem (online)
    if use_network:
        try:
            from cdxml_toolkit.resolve.cas_resolver import resolve_name_to_smiles
            smi = resolve_name_to_smiles(clean)
            if smi:
                canon = _rdkit_canonical(smi)
                if canon:
                    return {"smiles": canon, "source": "pubchem"}
        except Exception:
            pass

    return None


def _name_to_smiles_cs(name: str) -> Optional[str]:
    """Resolve an IUPAC name to SMILES via ChemScript."""
    cs = _get_cs()
    if cs is None:
        return None
    try:
        smi = cs.write_data(name, "smiles", source_format="name")
        if smi:
            return _rdkit_canonical(smi)
    except Exception:
        pass
    return None


def _smiles_to_name_cs(smiles: str) -> Optional[str]:
    """Get IUPAC name for a SMILES string via ChemScript."""
    cs = _get_cs()
    if cs is None:
        return None
    try:
        return cs.get_name(smiles)
    except Exception:
        return None


def _is_complex_prefix(prefix: str) -> bool:
    """Check if a prefix needs parentheses when inserted into a name.

    Complex prefixes contain hyphens, digits, or commas that would be
    ambiguous without enclosing parentheses.
    """
    # Already parenthesised
    if prefix.startswith("(") and prefix.endswith(")"):
        return False
    # Contains internal structure that needs brackets
    return bool(re.search(r"[\d,]", prefix)) and "-" in prefix


def _locant_sort_key(loc: str):
    """Sort locants: numeric before alphabetic, ascending."""
    m = re.match(r"(\d+)(.*)", loc)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, loc)


def _prefix_alpha_key(prefix: str) -> str:
    """IUPAC alphabetical sort key: ignore leading locants/multipliers.

    ``"1,1-difluoroethyl"`` → ``"difluoroethyl"``
    ``"tert-butyl"`` → ``"tert-butyl"``
    """
    stripped = re.sub(r"^[\d,]+-", "", prefix)
    return stripped.lower()


def _try_validate(name: str, use_network: bool = True) -> Optional[str]:
    """Try to resolve a name to canonical SMILES via offline resolvers.

    Uses ChemScript then OPSIN.  Never hits the network — the
    *use_network* parameter is accepted for call-site compatibility
    but ignored.

    Returns canonical SMILES or None.
    """
    from rdkit import Chem

    # ChemScript (most reliable for IUPAC names)
    smi = _name_to_smiles_cs(name)
    if smi:
        return smi

    # OPSIN fallback (offline IUPAC name resolution, bundled JRE)
    try:
        from cdxml_toolkit.resolve.jre_manager import ensure_java_on_path
        if ensure_java_on_path():
            import warnings, tempfile, os
            from py2opsin import py2opsin as _py2opsin
            tmp = os.path.join(tempfile.gettempdir(), "py2opsin_temp_input.txt")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                smi = _py2opsin(name, tmp_fpath=tmp)
            if smi and Chem.MolFromSmiles(smi):
                return _rdkit_canonical(smi)
    except (ImportError, FileNotFoundError):
        pass
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# RDKit property helpers
# ---------------------------------------------------------------------------

def _rdkit_properties(smiles: str) -> Dict[str, Any]:
    """Compute formula, MW, and exact mass from a SMILES via RDKit.

    Returns a dict with keys ``formula``, ``mw``, ``exact_mass``.
    Values are None if RDKit is unavailable or the molecule is invalid.
    """
    props: Dict[str, Any] = {"formula": None, "mw": None, "exact_mass": None}
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return props
        props["formula"] = rdMolDescriptors.CalcMolFormula(mol)
        props["mw"] = round(Descriptors.MolWt(mol), 4)
        props["exact_mass"] = round(Descriptors.ExactMolWt(mol), 4)
    except Exception:
        pass
    return props


# ---------------------------------------------------------------------------
# Tool 1: resolve_compound (rich resolver)
# ---------------------------------------------------------------------------

def resolve_compound(query: str, use_network: bool = True) -> Dict[str, Any]:
    """Resolve any chemical identifier to a rich molecule descriptor.

    Consolidates all resolution pathways (reagent DB, condensed formula,
    ChemScript, PubChem) and enriches the result with molecular properties
    computed via RDKit and metadata from the reagent database.

    Args:
        query: Chemical identifier — common name, IUPAC name, abbreviation,
               condensed formula, or CAS number.  Examples:
               ``"aspirin"``, ``"PhB(OH)2"``, ``"2-chloropyridine"``,
               ``"534-17-8"``, ``"deucravacitinib"``.
        use_network: Allow PubChem lookup (requires internet).

    Returns:
        Dict with keys:

        - ``ok`` (bool): True on success.
        - ``name`` (str): Input query echoed back.
        - ``smiles`` (str): Isomeric/canonical SMILES.
        - ``formula`` (str | None): Molecular formula (e.g. ``"C9H8O4"``).
        - ``mw`` (float | None): Molecular weight.
        - ``exact_mass`` (float | None): Monoisotopic mass.
        - ``iupac_name`` (str | None): IUPAC name from ChemScript or PubChem.
        - ``source`` (str): Which tier resolved the SMILES (``"reagent_db"``,
          ``"formula"``, ``"chemscript"``, ``"pubchem"``).
        - ``role`` (str | None): Reagent role from the curated DB if known
          (e.g. ``"base"``, ``"solvent"``, ``"catalyst"``).
        - ``display_text`` (str | None): Preferred display name from the
          reagent DB, or the IUPAC name if available.
        - ``prefix_form`` (str | None): IUPAC substituent prefix for use in
          ``assemble_name`` (e.g. ``"trifluoromethyl"`` for ``CF3``,
          ``"morpholino"`` for morpholine).  ``None`` if the compound is not
          a substituent group or no prefix could be determined.

        On failure: ``ok=False`` with an ``error`` key.

    Example::

        >>> resolve_compound("Cs2CO3")
        {'ok': True, 'name': 'Cs2CO3', 'smiles': 'O=C([O-])[O-].[Cs+].[Cs+]',
         'formula': 'CCs2O3', 'mw': 325.82, 'exact_mass': 325.82,
         'iupac_name': None, 'source': 'reagent_db',
         'role': 'base', 'display_text': 'Cs2CO3', 'prefix_form': None}

        >>> resolve_compound("Et3N")
        {'ok': True, 'name': 'Et3N', 'smiles': 'CCN(CC)CC',
         'formula': 'C6H15N', 'mw': 101.19, 'exact_mass': 101.12,
         'iupac_name': None, 'source': 'formula',
         'role': None, 'display_text': None, 'prefix_form': None}

        >>> resolve_compound("CF3")
        {'ok': True, ..., 'prefix_form': 'trifluoromethyl'}

        >>> resolve_compound("morpholine")
        {'ok': True, ..., 'prefix_form': 'morpholino'}
    """
    # --- Step 1: resolve SMILES via the existing 4-tier chain ---
    resolved = _resolve_query(query, use_network=use_network)
    if not resolved:
        return {"ok": False, "error": f"Could not resolve '{query}' to a structure."}

    smiles = resolved["smiles"]
    source = resolved["source"]

    # --- Step 2: compute molecular properties via RDKit ---
    props = _rdkit_properties(smiles)

    # --- Step 3: IUPAC name via ChemScript (best quality) ---
    iupac_name: Optional[str] = None
    if source == "chemscript":
        # ChemScript already resolved this name — get the canonical IUPAC back
        iupac_name = _smiles_to_name_cs(smiles)
    elif source != "reagent_db":
        # For formula/pubchem sources, try ChemScript name generation
        iupac_name = _smiles_to_name_cs(smiles)

    # --- Step 4: role and display_text from reagent_db ---
    role: Optional[str] = None
    display_text: Optional[str] = None
    try:
        from cdxml_toolkit.resolve.reagent_db import get_reagent_db
        db = get_reagent_db()
        # Try by name first (fastest), then by resolved SMILES
        entry = db.entry_for_name(query.lower())
        if entry is None:
            entry = db.entry_for_smiles(smiles)
        if entry is not None:
            role = entry.get("role")
            display_text = entry.get("display")
    except Exception:
        pass

    # Fall back: display_text from IUPAC name if reagent_db had nothing
    if display_text is None and iupac_name:
        display_text = iupac_name

    # --- Step 5: IUPAC substituent prefix form ---
    prefix_form: Optional[str] = None
    pf_result = get_prefix_form(query)
    if pf_result.get("ok"):
        prefix_form = pf_result["prefix"]
    else:
        # Try on the resolved SMILES as a fallback
        pf_result2 = get_prefix_form(smiles)
        if pf_result2.get("ok"):
            prefix_form = pf_result2["prefix"]

    return {
        "ok": True,
        "name": query,
        "smiles": smiles,
        "formula": props["formula"],
        "mw": props["mw"],
        "exact_mass": props["exact_mass"],
        "iupac_name": iupac_name,
        "source": source,
        "role": role,
        "display_text": display_text,
        "prefix_form": prefix_form,
    }


# ---------------------------------------------------------------------------
# Tool 2 (legacy thin wrapper): resolve_to_smiles
# ---------------------------------------------------------------------------

def resolve_to_smiles(query: str, use_network: bool = True) -> Dict[str, Any]:
    """Resolve a chemical identifier to its canonical SMILES string.

    Accepts common names, IUPAC names, abbreviations, condensed formulae,
    and CAS numbers.  Uses a 4-tier resolution chain:
    reagent DB → condensed formula → ChemScript → PubChem.

    .. note::
        For richer output (formula, MW, exact mass, role, display text),
        use :func:`resolve_compound` instead.

    Args:
        query: Chemical identifier.  Examples: ``"aspirin"``,
               ``"PhB(OH)2"``, ``"2-chloropyridine"``, ``"534-17-8"``.
        use_network: Allow PubChem lookup (requires internet).

    Returns:
        Dict with keys ``ok``, ``smiles``, ``source``.
        On failure: ``ok=False`` with an ``error`` message.

    Example::

        >>> resolve_to_smiles("Et3N")
        {'ok': True, 'smiles': 'CCN(CC)CC', 'source': 'formula'}
    """
    result = resolve_compound(query, use_network=use_network)
    if result["ok"]:
        return {"ok": True, "smiles": result["smiles"], "source": result["source"]}
    return {"ok": False, "error": result.get("error", f"Could not resolve '{query}'.")}


# ---------------------------------------------------------------------------
# Tool 2: get_prefix_form
# ---------------------------------------------------------------------------

def get_prefix_form(group: str) -> Dict[str, Any]:
    """Get the IUPAC substituent prefix form for a chemical group.

    Given a group name, abbreviation, or formula, returns the prefix
    string suitable for insertion into an IUPAC name.

    Uses a curated lookup table for common groups (fast, offline), then
    falls back to ChemScript-based naming with the Se-probe for anything
    not in the table.

    Args:
        group: Group identifier.  Examples: ``"CF3"``, ``"morpholine"``,
               ``"NO2"``, ``"cyclopropyl"``, ``"OMe"``.

    Returns:
        Dict with keys ``ok``, ``prefix``, ``source``.
        ``source`` is ``"table"`` for lookup hits, ``"probe"`` for
        ChemScript probe, or ``"passthrough"`` if the input was already
        a valid prefix form.

    Examples::

        >>> get_prefix_form("CF3")
        {'ok': True, 'prefix': 'trifluoromethyl', 'source': 'table'}
        >>> get_prefix_form("morpholine")
        {'ok': True, 'prefix': 'morpholino', 'source': 'table'}
    """
    clean = group.strip()
    if not clean:
        return {"ok": False, "error": "Empty group."}

    # --- Table lookup (case-insensitive) ---
    key = clean.lower()
    if key in _PREFIX_TABLE:
        return {"ok": True, "prefix": _PREFIX_TABLE[key], "source": "table"}

    # --- Check if it's already a valid prefix ---
    # If appending it to "benzene" gives a valid name, it's a prefix.
    test_name = f"1-{clean}benzene" if not clean[0].isdigit() else f"{clean}benzene"
    smi = _try_validate(test_name)
    if smi:
        return {"ok": True, "prefix": clean, "source": "passthrough"}

    # --- Se-probe via name_fragment_as_substituent ---
    # Resolve group to SMILES, add [*] attachment, call the decomposer.
    resolved = _resolve_query(clean, use_network=True)
    if resolved:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(resolved["smiles"])
        if mol:
            # Build [*]-fragment SMILES by attaching dummy at the most
            # likely bonding position (first atom in canonical SMILES).
            # For many simple groups this is correct.
            edit = Chem.RWMol(mol)
            dummy_idx = edit.AddAtom(Chem.Atom(0))  # [*]
            edit.AddBond(0, dummy_idx, Chem.BondType.SINGLE)
            try:
                Chem.SanitizeMol(edit)
                frag_smi = Chem.MolToSmiles(edit.GetMol())
                from .name_decomposer import name_fragment_as_substituent
                prefix = name_fragment_as_substituent(frag_smi, verbose=False)
                if prefix:
                    return {"ok": True, "prefix": prefix, "source": "probe"}
            except Exception:
                pass

    return {
        "ok": False,
        "error": f"Could not determine prefix form for '{group}'.",
    }


# ---------------------------------------------------------------------------
# Tool 3: assemble_name
# ---------------------------------------------------------------------------

def assemble_name(parent: str,
                  substituents: List[Dict[str, str]],
                  validate: bool = True,
                  use_network: bool = True) -> Dict[str, Any]:
    """Assemble an IUPAC name from a parent and substituent list.

    Handles alphabetical ordering, multiplicative prefixes (di-, tri-),
    and parenthesisation of complex substituents.  Optionally validates
    the assembled name by resolving it to SMILES.

    Args:
        parent: Parent ring or chain name (e.g. ``"pyridine"``,
                ``"benzene"``, ``"pentane"``).
        substituents: List of dicts, each with ``"locant"`` (str) and
                      ``"prefix"`` (str).  Example::

                          [{"locant": "2", "prefix": "chloro"},
                           {"locant": "3", "prefix": "methyl"}]
        validate: If True, resolve the assembled name and confirm validity.
        use_network: Allow PubChem for validation.

    Returns:
        Dict with ``ok``, ``name``, and (if validated) ``valid``, ``smiles``.

    Example::

        >>> assemble_name("pyridine", [
        ...     {"locant": "2", "prefix": "chloro"},
        ...     {"locant": "5", "prefix": "nitro"},
        ... ])
        {'ok': True, 'name': '2-chloro-5-nitropyridine', 'valid': True,
         'smiles': '...'}
    """
    if not parent:
        return {"ok": False, "error": "Parent name is required."}
    if not substituents:
        # Bare parent — still valid
        if validate:
            smi = _try_validate(parent, use_network=use_network)
            if smi:
                return {"ok": True, "name": parent, "valid": True, "smiles": smi}
            return {"ok": True, "name": parent, "valid": False, "smiles": None}
        return {"ok": True, "name": parent}

    # --- Group identical prefixes for multipliers ---
    from collections import defaultdict
    groups: Dict[str, List[str]] = defaultdict(list)
    for sub in substituents:
        prefix = sub.get("prefix", "").strip()
        locant = sub.get("locant", "").strip()
        if prefix:
            groups[prefix].append(locant)

    # --- Build prefix fragments, sorted alphabetically by prefix ---
    fragments = []
    for prefix in sorted(groups.keys(), key=_prefix_alpha_key):
        locants = sorted(groups[prefix], key=_locant_sort_key)
        locant_str = ",".join(loc for loc in locants if loc)
        n = len(locants)

        # Format the prefix with optional multiplier
        if n > 1 and prefix in _MULTIPLIERS:
            mult = _MULTIPLIERS.get(n, str(n))
        elif n > 1:
            mult = _MULTIPLIERS.get(n, str(n))
        else:
            mult = ""

        # Parenthesise complex prefixes
        needs_parens = _is_complex_prefix(prefix)
        pfx = f"({prefix})" if needs_parens else prefix

        if mult:
            part = f"{locant_str}-{mult}{pfx}" if locant_str else f"{mult}{pfx}"
        else:
            part = f"{locant_str}-{pfx}" if locant_str else pfx

        fragments.append(part)

    # --- Assemble final name ---
    name = "-".join(fragments) + parent

    result: Dict[str, Any] = {"ok": True, "name": name}

    if validate:
        smi = _try_validate(name, use_network=use_network)
        result["valid"] = smi is not None
        result["smiles"] = smi
        if not smi:
            # Try without parentheses as alternative
            alt_frags = []
            for prefix in sorted(groups.keys(), key=_prefix_alpha_key):
                locants = sorted(groups[prefix], key=_locant_sort_key)
                locant_str = ",".join(loc for loc in locants if loc)
                n = len(locants)
                mult = _MULTIPLIERS.get(n, "") if n > 1 else ""
                part = f"{locant_str}-{mult}{prefix}" if locant_str else f"{mult}{prefix}"
                alt_frags.append(part)
            alt_name = "-".join(alt_frags) + parent
            if alt_name != name:
                alt_smi = _try_validate(alt_name, use_network=use_network)
                if alt_smi:
                    result["name"] = alt_name
                    result["valid"] = True
                    result["smiles"] = alt_smi

    return result


# ---------------------------------------------------------------------------
# Tool 4: modify_name
# ---------------------------------------------------------------------------

def modify_name(name: str,
                operation: str,
                target: Optional[str] = None,
                replacement: Optional[str] = None,
                locant: Optional[str] = None,
                validate: bool = True,
                use_network: bool = True) -> Dict[str, Any]:
    """Modify an IUPAC name by swapping, adding, or removing a substituent.

    Operations:

    - ``"swap"``: Replace *target* prefix with *replacement*.
      E.g. swap "nitro" → "amino" in "4-nitropyridine" → "4-aminopyridine".

    - ``"add"``: Insert *replacement* at *locant*.
      E.g. add "methyl" at "3" to "2-chloropyridine" → "2-chloro-3-methylpyridine".

    - ``"remove"``: Delete the *target* prefix.
      E.g. remove "chloro" from "2-chloro-3-methylpyridine" → "3-methylpyridine".

    For ``"swap"``, the name is re-alphabetised automatically.

    Args:
        name: The IUPAC name to modify.
        operation: ``"swap"``, ``"add"``, or ``"remove"``.
        target: Prefix to replace (swap) or remove (remove).
        replacement: New prefix (swap) or prefix to insert (add).
        locant: Position for insertion (add only).
        validate: Resolve the result to confirm validity.
        use_network: Allow PubChem for validation.

    Returns:
        Dict with ``ok``, ``name``, ``valid``, ``smiles``.

    Examples::

        >>> modify_name("4-nitropyridine", "swap",
        ...             target="nitro", replacement="amino")
        {'ok': True, 'name': '4-aminopyridine', ...}

        >>> modify_name("2-chloropyridine", "add",
        ...             replacement="methyl", locant="3")
        {'ok': True, 'name': '2-chloro-3-methylpyridine', ...}
    """
    if operation == "swap":
        return _modify_swap(name, target, replacement, validate, use_network)
    elif operation == "add":
        return _modify_add(name, replacement, locant, validate, use_network)
    elif operation == "remove":
        return _modify_remove(name, target, validate, use_network)
    else:
        return {"ok": False, "error": f"Unknown operation '{operation}'. "
                "Use 'swap', 'add', or 'remove'."}


def _parse_name_components(name: str) -> Optional[Dict]:
    """Best-effort parse of a substituted IUPAC name into components.

    Splits a name like ``"2-chloro-5-(trifluoromethyl)pyridine"`` into::

        {"parent": "pyridine",
         "substituents": [{"locant": "2", "prefix": "chloro"},
                          {"locant": "5", "prefix": "trifluoromethyl"}]}

    Uses the aligned namer's ring system list for parent detection.
    """
    try:
        from .aligned_namer import _KNOWN_RINGS
        rings = _KNOWN_RINGS
    except ImportError:
        rings = set()

    # Also try common chain parents
    chains = [
        "icosane", "nonadecane", "octadecane", "heptadecane", "hexadecane",
        "pentadecane", "tetradecane", "tridecane", "dodecane", "undecane",
        "decane", "nonane", "octane", "heptane", "hexane", "pentane",
        "butane", "propane", "ethane", "methane",
        "icosanoic acid", "nonadecanoic acid", "octadecanoic acid",
    ]
    all_parents = sorted(
        list(rings) + chains, key=len, reverse=True
    )

    # Find the parent: longest known name that matches the tail
    parent = None
    prefix_part = ""
    for p in all_parents:
        if name.endswith(p):
            prefix_part = name[:-len(p)]
            parent = p
            break

    # Fallback: if no known parent, try splitting at the last segment
    # that doesn't start with a digit
    if parent is None:
        # Try to identify parent as the last non-prefixed segment
        # Pattern: everything after the last "-" that isn't a locant-prefix pair
        parts = name.rsplit("-", 1)
        if len(parts) == 2 and not re.match(r"^\d", parts[1]):
            parent = parts[1]
            prefix_part = parts[0] + "-"
        else:
            parent = name
            prefix_part = ""

    if not prefix_part.strip("-"):
        return {"parent": parent, "substituents": []}

    # Parse prefix_part into (locant, prefix) pairs
    prefix_str = prefix_part.rstrip("-")
    substituents = []

    # Pattern: locant(s)-[multiplier][(]prefix[)] or locant(s)-[multiplier]prefix
    # Walk through segments
    segments = _split_prefix_segments(prefix_str)
    for seg in segments:
        parsed = _parse_single_prefix(seg)
        if parsed:
            substituents.extend(parsed)

    return {"parent": parent, "substituents": substituents}


def _split_prefix_segments(prefix_str: str) -> List[str]:
    """Split a prefix string into individual prefix segments.

    Handles parenthesised prefixes correctly:
    ``"2-chloro-3-(trifluoromethyl)"`` → ``["2-chloro", "3-(trifluoromethyl)"]``
    """
    segments = []
    current = ""
    depth = 0
    for ch in prefix_str:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "-" and depth == 0:
            if current:
                # Check: is this a separator between segments, or within one?
                # A segment boundary is after a prefix (lowercase letter or ')').
                # Within a segment: after a locant (digit) or multiplier.
                if current and (current[-1].isalpha() and current[-1].islower()
                                or current[-1] == ")"):
                    segments.append(current)
                    current = ""
                else:
                    current += ch
            else:
                current += ch
        else:
            current += ch
    if current:
        segments.append(current)
    return segments


def _parse_single_prefix(segment: str) -> Optional[List[Dict[str, str]]]:
    """Parse a single prefix segment like '2-chloro' or '2,4-dichloro'.

    Returns list of {"locant": ..., "prefix": ...} dicts.
    """
    # Handle multiplied: 2,4-dichloro
    m = re.match(
        r"^([\d,]+)-(?:di|tri|tetra|penta|hexa)"
        r"[\(\[]?([a-zA-Z][\w,\-]*?)[\)\]]?$",
        segment,
    )
    if m:
        locants = m.group(1).split(",")
        prefix = m.group(2)
        return [{"locant": loc, "prefix": prefix} for loc in locants]

    # Handle parenthesised: 3-(trifluoromethyl)
    m = re.match(r"^(\d+\w?)-\((.+)\)$", segment)
    if m:
        return [{"locant": m.group(1), "prefix": m.group(2)}]

    # Handle simple: 2-chloro
    m = re.match(r"^(\d+\w?)-([a-zA-Z][\w\-]*)$", segment)
    if m:
        return [{"locant": m.group(1), "prefix": m.group(2)}]

    # No locant: just a prefix (e.g., "amino" without locant)
    if re.match(r"^[a-zA-Z]", segment):
        return [{"locant": "", "prefix": segment}]

    return None


def _modify_swap(name, target, replacement, validate, use_network):
    """Swap one prefix for another and re-assemble."""
    if not target or not replacement:
        return {"ok": False, "error": "Both 'target' and 'replacement' required for swap."}

    parsed = _parse_name_components(name)
    if parsed is None:
        return {"ok": False, "error": f"Could not parse name '{name}'."}

    subs = parsed["substituents"]
    found = False
    for sub in subs:
        if sub["prefix"] == target:
            sub["prefix"] = replacement
            found = True
    if not found:
        return {
            "ok": False,
            "error": f"Prefix '{target}' not found in '{name}'.",
            "found_prefixes": [s["prefix"] for s in subs],
        }

    return assemble_name(parsed["parent"], subs, validate=validate,
                         use_network=use_network)


def _modify_add(name, prefix, locant, validate, use_network):
    """Add a new substituent to an existing name."""
    if not prefix:
        return {"ok": False, "error": "'replacement' (prefix to add) is required."}
    if not locant:
        return {"ok": False, "error": "'locant' is required for add operation."}

    parsed = _parse_name_components(name)
    if parsed is None:
        return {"ok": False, "error": f"Could not parse name '{name}'."}

    parsed["substituents"].append({"locant": locant, "prefix": prefix})
    return assemble_name(parsed["parent"], parsed["substituents"],
                         validate=validate, use_network=use_network)


def _modify_remove(name, target, validate, use_network):
    """Remove a substituent from a name."""
    if not target:
        return {"ok": False, "error": "'target' prefix is required for remove."}

    parsed = _parse_name_components(name)
    if parsed is None:
        return {"ok": False, "error": f"Could not parse name '{name}'."}

    original_len = len(parsed["substituents"])
    parsed["substituents"] = [
        s for s in parsed["substituents"] if s["prefix"] != target
    ]
    if len(parsed["substituents"]) == original_len:
        return {
            "ok": False,
            "error": f"Prefix '{target}' not found in '{name}'.",
            "found_prefixes": [s["prefix"] for s in parsed["substituents"]],
        }

    return assemble_name(parsed["parent"], parsed["substituents"],
                         validate=validate, use_network=use_network)


# ---------------------------------------------------------------------------
# Tool 5: validate_name
# ---------------------------------------------------------------------------

def validate_name(name: str,
                  use_network: bool = True) -> Dict[str, Any]:
    """Validate an IUPAC name and return its SMILES if valid.

    Attempts to resolve the name to a structure using ChemScript
    (preferred) or PubChem (fallback).  Returns whether the name is
    valid and the canonical SMILES.

    Args:
        name: IUPAC name to validate.
        use_network: Allow PubChem lookup.

    Returns:
        Dict with ``ok``, ``valid``, ``smiles``, ``name``.

    Example::

        >>> validate_name("2-chloropyridine")
        {'ok': True, 'valid': True, 'smiles': 'Clc1ccccn1', 'name': '2-chloropyridine'}
    """
    smi = _try_validate(name, use_network=use_network)
    if smi:
        # Also get the canonical IUPAC name if ChemScript is available
        canonical = _smiles_to_name_cs(smi)
        return {
            "ok": True,
            "valid": True,
            "smiles": smi,
            "name": name,
            "canonical_name": canonical,
        }
    return {"ok": True, "valid": False, "smiles": None, "name": name}


# ---------------------------------------------------------------------------
# Tool 6: name_to_structure
# ---------------------------------------------------------------------------

def name_to_structure(name: str,
                      output_format: str = "cdxml") -> Dict[str, Any]:
    """Convert a chemical name to a structure in the requested format.

    Resolves the name, generates 2D coordinates, and returns the
    structure as a string (CDXML, SMILES, or MOL).

    Args:
        name: IUPAC or common name.
        output_format: ``"cdxml"`` (default), ``"smiles"``, or ``"mol"``.

    Returns:
        Dict with ``ok`` and the structure data (key matches format name).

    Example::

        >>> result = name_to_structure("2-chloropyridine")
        >>> result["ok"]
        True
        >>> result["cdxml"][:20]
        '<?xml version="1.0"'
    """
    fmt = output_format.lower()

    if fmt == "smiles":
        smi = _try_validate(name)
        if smi:
            return {"ok": True, "smiles": smi}
        return {"ok": False, "error": f"Could not resolve '{name}'."}

    # For CDXML and MOL, prefer ChemScript (gives ACS-styled 2D)
    cs = _get_cs()
    if cs is not None:
        try:
            if fmt == "cdxml":
                cdxml = cs.name_to_cdxml(name)
                return {"ok": True, "cdxml": cdxml}
            elif fmt == "mol":
                mol_data = cs.write_data(name, "mol", source_format="name")
                return {"ok": True, "mol": mol_data}
        except Exception:
            pass

    # Fallback: resolve to SMILES, then generate structure via RDKit
    smi = _try_validate(name)
    if not smi:
        return {"ok": False, "error": f"Could not resolve '{name}'."}

    if fmt == "cdxml":
        # Try ChemScript with SMILES input
        if cs is not None:
            try:
                cdxml = cs.smiles_to_cdxml(smi)
                return {"ok": True, "cdxml": cdxml}
            except Exception:
                pass
        return {"ok": False,
                "error": "CDXML output requires ChemScript. "
                         f"Name resolved to SMILES: {smi}",
                "smiles": smi}

    if fmt == "mol":
        from rdkit import Chem
        from rdkit.Chem import AllChem
        mol = Chem.MolFromSmiles(smi)
        if mol:
            AllChem.Compute2DCoords(mol)
            return {"ok": True, "mol": Chem.MolToMolBlock(mol)}
        return {"ok": False, "error": "RDKit could not generate MOL block."}

    return {"ok": False, "error": f"Unknown format '{fmt}'. Use cdxml, smiles, or mol."}


# ---------------------------------------------------------------------------
# Tool 7: enumerate_names
# ---------------------------------------------------------------------------

def enumerate_names(identifier: str,
                    use_network: bool = True) -> Dict[str, Any]:
    """Enumerate alternative IUPAC name forms for a molecule.

    Given a chemical name or SMILES, returns the canonical IUPAC name plus
    alternative forms where substituents appear as different prefixes or
    where a different parent ring/chain is chosen.  This is essential for
    name surgery: it lets you see functional groups as swappable prefixes.

    For example, ``"1-(4-bromophenyl)ethan-1-one"`` (a ketone in suffix
    form) generates alternatives including ``"1-acetyl-4-bromobenzene"``
    where the ketone appears as the prefix ``"acetyl"`` — now swappable
    via ``modify_name``.

    Args:
        identifier: Chemical name, SMILES, abbreviation, or any
            identifier accepted by ``resolve_to_smiles``.
        use_network: Allow PubChem for resolution.

    Returns:
        Dict with:

        - ``ok``: bool
        - ``canonical_name``: the ChemDraw canonical IUPAC name
        - ``smiles``: canonical SMILES
        - ``names``: list of dicts, each with ``name`` (str),
          ``valid`` (bool), ``strategy`` (str), and ``prefixes``
          (list of prefix strings visible in that name form).
          The canonical name is always the first entry.

    Example::

        >>> result = enumerate_names("1-(4-bromophenyl)ethan-1-one")
        >>> for n in result["names"]:
        ...     print(n["name"], n["prefixes"])
        1-(4-bromophenyl)ethan-1-one  ['(4-bromophenyl)']
        1-acetyl-4-bromobenzene       ['acetyl', 'bromo']
        ...
    """
    # Resolve to SMILES — try direct SMILES parse first, then name resolution
    from rdkit import Chem as _Chem
    _test_mol = _Chem.MolFromSmiles(identifier)
    if _test_mol is not None:
        smiles = _Chem.MolToSmiles(_test_mol)
    else:
        resolved = _resolve_query(identifier, use_network=use_network)
        if not resolved:
            return {"ok": False,
                    "error": f"Could not resolve '{identifier}' to a structure."}
        smiles = resolved["smiles"]

    # Run decomposition
    try:
        from .name_decomposer import decompose_name
        result = decompose_name(smiles, verbose=False, timeout=30.0)
    except Exception as exc:
        return {"ok": False,
                "error": f"Decomposition failed: {exc}",
                "smiles": smiles}

    if result.errors:
        return {"ok": False,
                "error": "; ".join(result.errors),
                "smiles": smiles}

    canon = result.canonical_name
    if not canon:
        return {"ok": False,
                "error": "Could not determine canonical name.",
                "smiles": smiles}

    # Build the output list, canonical first
    names = []

    # Parse prefixes from each name form
    canon_parsed = _parse_name_components(canon)
    canon_prefixes = ([s["prefix"] for s in canon_parsed["substituents"]]
                      if canon_parsed else [])
    names.append({
        "name": canon,
        "valid": True,
        "strategy": "canonical",
        "prefixes": canon_prefixes,
    })

    # Add valid alternatives
    seen = {canon}
    for alt in result.alternatives:
        if not alt.valid:
            continue
        if alt.name in seen:
            continue
        seen.add(alt.name)

        parsed = _parse_name_components(alt.name)
        prefixes = ([s["prefix"] for s in parsed["substituents"]]
                    if parsed else [])
        names.append({
            "name": alt.name,
            "valid": True,
            "strategy": alt.strategy,
            "prefixes": prefixes,
        })

    return {
        "ok": True,
        "canonical_name": canon,
        "smiles": smiles,
        "names": names,
    }


# ---------------------------------------------------------------------------
# Layer 3: Graph manipulation — reaction templates
# ---------------------------------------------------------------------------

# Hand-curated templates for common med-chem transformations that an LLM
# will recognise by name.  These supplement the larger collection loaded
# from reactions_datamol.json.
_CLASSIC_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "suzuki_coupling": {
        "description": "Suzuki coupling: aryl halide + boronic acid to biaryl",
        "smarts": "[c:1][Br,I].[#6:2][B]([OH])[OH]>>[c:1]-[#6:2]",
        "n_reactants": 2,
        "substrate_hint": "aryl bromide or iodide",
        "reagent_hint": "boronic acid",
        "conditions": ["Pd(dppf)Cl2", "K2CO3", "dioxane/H2O", "80 °C"],
        "category": "coupling",
    },
    "buchwald_amination": {
        "description":
            "Buchwald-Hartwig amination: aryl halide + amine to aryl amine",
        "smarts": "[c:1][Cl,Br,I].[NX3;H2,H1:2]>>[c:1]-[N:2]",
        "n_reactants": 2,
        "substrate_hint": "aryl halide",
        "reagent_hint": "primary or secondary amine",
        "conditions": ["Pd2(dba)3", "XPhos", "Cs2CO3", "toluene", "100 °C"],
        "category": "coupling",
    },
    "snar": {
        "description":
            "Nucleophilic aromatic substitution: activated aryl halide + "
            "nucleophile",
        "smarts": "[c:1][F,Cl].[NX3;H2,H1:2]>>[c:1]-[N:2]",
        "n_reactants": 2,
        "substrate_hint": "electron-poor aryl fluoride or chloride",
        "reagent_hint": "amine nucleophile",
        "conditions": ["DIPEA", "DMSO or NMP", "80-120 °C"],
        "category": "coupling",
    },
    "amide_coupling": {
        "description": "Amide bond formation: carboxylic acid + amine",
        "smarts":
            "[C:1](=[O:2])[OH].[NX3;H2,H1:3]>>[C:1](=[O:2])-[N:3]",
        "n_reactants": 2,
        "substrate_hint": "carboxylic acid",
        "reagent_hint": "primary or secondary amine",
        "conditions": ["HATU", "DIPEA", "DMF", "rt"],
        "category": "coupling",
    },
    "reductive_amination": {
        "description":
            "Reductive amination: aldehyde or ketone + amine to amine",
        "smarts": "[C:1](=[O:2]).[NX3;H2,H1:3]>>[C:1]-[N:3]",
        "n_reactants": 2,
        "substrate_hint": "aldehyde or ketone",
        "reagent_hint": "primary or secondary amine",
        "conditions": ["NaBH(OAc)3", "AcOH", "DCE", "rt"],
        "category": "functional_group",
    },
    "nitro_reduction": {
        "description": "Nitro group reduction to amine (ArNO2 to ArNH2)",
        "smarts": "[c:1][N+](=[O])[O-]>>[c:1]N",
        "n_reactants": 1,
        "substrate_hint": "aromatic nitro compound",
        "reagent_hint": None,
        "conditions": ["SnCl2·2H2O", "EtOH", "80 °C"],
        "category": "functional_group",
    },
    "ester_hydrolysis": {
        "description": "Ester hydrolysis to carboxylic acid",
        "smarts":
            "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[OH]",
        "n_reactants": 1,
        "substrate_hint": "ester",
        "reagent_hint": None,
        "conditions": ["LiOH", "THF/H2O", "rt"],
        "category": "functional_group",
    },
    "n_alkylation": {
        "description": "N-Alkylation: amine + alkyl halide",
        "smarts":
            "[NX3;H2,H1:1].[C:2][Cl,Br,I]>>[N:1]-[C:2]",
        "n_reactants": 2,
        "substrate_hint": "amine",
        "reagent_hint": "alkyl halide",
        "conditions": ["K2CO3", "DMF", "60 °C"],
        "category": "coupling",
    },
    "sonogashira_coupling": {
        "description":
            "Sonogashira coupling: aryl halide + terminal alkyne",
        "smarts":
            "[c:1][Br,I].[CH:2]#[C:3]>>[c:1]-[C:2]#[C:3]",
        "n_reactants": 2,
        "substrate_hint": "aryl bromide or iodide",
        "reagent_hint": "terminal alkyne",
        "conditions": [
            "PdCl2(PPh3)2", "CuI", "Et3N", "THF", "rt",
        ],
        "category": "coupling",
    },
    "heck_reaction": {
        "description":
            "Heck reaction: aryl halide + alkene to substituted alkene",
        "smarts":
            "[c:1][Br,I].[CH:2]=[CH2:3]>>[c:1]/[CH:2]=[CH2:3]",
        "n_reactants": 2,
        "substrate_hint": "aryl halide",
        "reagent_hint": "terminal alkene",
        "conditions": [
            "Pd(OAc)2", "P(o-tol)3", "Et3N", "DMF", "100 °C",
        ],
        "category": "coupling",
    },
    "alcohol_oxidation": {
        "description": "Alcohol oxidation to aldehyde or ketone",
        "smarts":
            "[C:1][OH:2]>>[C:1]=[O:2]",
        "n_reactants": 1,
        "substrate_hint": "primary or secondary alcohol",
        "reagent_hint": None,
        "conditions": ["Dess-Martin periodinane", "DCM", "rt"],
        "category": "functional_group",
    },
    "grignard_addition": {
        "description":
            "Grignard / organometallic addition to aldehyde or ketone",
        "smarts":
            "[C:1](=[O:2])[#6:4].[#6:3][Mg]>>[C:1]([OH:2])([#6:4])-[#6:3]",
        "n_reactants": 2,
        "substrate_hint": "aldehyde or ketone",
        "reagent_hint": "Grignard reagent (RMgBr SMILES)",
        "conditions": ["THF", "-78 °C to rt"],
        "category": "functional_group",
    },
    # --- Hartenfeller-Schneider extras (not in datamol) ---
    "amide_hydrolysis": {
        "description":
            "Amide hydrolysis to carboxylic acid (RCONHR' \u2192 RCOOH)",
        "smarts": "[C:1](=[O:2])[NX3:3]>>[C:1](=[O:2])[OH]",
        "n_reactants": 1,
        "substrate_hint": "amide (primary, secondary, or tertiary)",
        "reagent_hint": None,
        "conditions": ["6M HCl or 2M NaOH", "reflux"],
        "category": "functional_group",
    },
    "wittig": {
        "description":
            "Wittig olefination: aldehyde/ketone + alkyl halide to alkene",
        "smarts":
            "[#6:3]-[C;H1,$([CH0](-[#6])[#6]);!$(CC=O):1]=[OD1]"
            ".[Cl,Br,I][C;H2;$(C-[#6]);!$(CC[I,Br]);!$(CCO[CH3]):2]"
            ">>[C:3][C:1]=[C:2]",
        "n_reactants": 2,
        "substrate_hint": "aldehyde or ketone",
        "reagent_hint": "alkyl halide (ylide precursor)",
        "conditions": ["PPh3", "n-BuLi", "THF", "0 \u00b0C to rt"],
        "category": "functional_group",
    },
    "niementowski_quinazoline": {
        "description":
            "Niementowski quinazoline: anthranilic acid + amide "
            "\u2192 4-quinazolinone",
        "smarts":
            "[c:1](-[C;$(C-c1ccccc1):2](=[OD1:3])-[OH1])"
            ":[c:4](-[NH2:5])"
            ".[N;!H0;!$(N-N);!$(N-C=N);!$(N(-C=O)-C=O):6]"
            "-[C;H1,$(C-[#6]):7]=[OD1]"
            ">>[c:4]2:[c:1]-[C:2](=[O:3])-[N:6]-[C:7]=[N:5]-2",
        "n_reactants": 2,
        "substrate_hint": "anthranilic acid derivative",
        "reagent_hint": "amide or formamide",
        "conditions": ["neat or AcOH", "120\u2013150 \u00b0C"],
        "category": "heterocycle_formation",
    },
    "grignard_carbonyl": {
        "description":
            "Grignard on nitrile: nitrile + aryl/alkyl halide \u2192 ketone",
        "smarts":
            "[#6:1][C:2]#[#7;D1]"
            ".[Cl,Br,I][#6;$([#6]~[#6]);"
            "!$([#6]([Cl,Br,I])[Cl,Br,I]);!$([#6]=O):3]"
            ">>[#6:1][C:2](=O)[#6:3]",
        "n_reactants": 2,
        "substrate_hint": "nitrile (R\u2212C\u2261N)",
        "reagent_hint": "aryl or alkyl halide (Grignard precursor)",
        "conditions": ["Mg", "THF", "then H3O+"],
        "category": "functional_group",
    },
    # --- Deprotection templates (SMARTS from RDKit rdDeprotect source) ---
    "cbz_deprotection": {
        "description": "Remove Cbz (carbobenzyloxy) from amine",
        "smarts":
            "[NX3;H0,H1:1][C;R0](=O)[O;R0][C;R0]"
            "c1[c;H1][c;H1][c;H1][c;H1][c;H1]1>>[N:1]",
        "n_reactants": 1,
        "substrate_hint": "Cbz-protected amine",
        "reagent_hint": None,
        "conditions": ["H2", "Pd/C", "MeOH", "rt"],
        "category": "deprotection",
    },
    "fmoc_deprotection": {
        "description": "Remove Fmoc (9-fluorenylmethyloxycarbonyl) from amine",
        "smarts":
            "[NX3;H0,H1:1][#6](=O)-[#8]-[#6]-[#6]-1"
            "-c2ccccc2-c2ccccc-12>>[N:1]",
        "n_reactants": 1,
        "substrate_hint": "Fmoc-protected amine",
        "reagent_hint": None,
        "conditions": ["piperidine", "DMF", "rt"],
        "category": "deprotection",
    },
    "tbs_deprotection": {
        "description": "Remove TBS (tert-butyldimethylsilyl) from alcohol",
        "smarts": "CC(C)([Si](C)(C)[O;H0:1])C>>[O;H1:1]",
        "n_reactants": 1,
        "substrate_hint": "TBS-protected alcohol",
        "reagent_hint": None,
        "conditions": ["TBAF", "THF", "rt"],
        "category": "deprotection",
    },
    "bn_deprotection_o": {
        "description": "Remove benzyl (Bn) from alcohol",
        "smarts":
            "[O;!$(*C(=O)):1][CH2]"
            "c1[c;H1][c;H1][c;H1][c;H1][c;H1]1>>[O;H1:1]",
        "n_reactants": 1,
        "substrate_hint": "Bn-protected alcohol",
        "reagent_hint": None,
        "conditions": ["H2", "Pd/C", "EtOAc", "rt"],
        "category": "deprotection",
    },
    "bn_deprotection_n": {
        "description": "Remove benzyl (Bn) from amine",
        "smarts":
            "[NX3;H0,H1;!$(NC=O):1][C;H2]"
            "c1[c;H1][c;H1][c;H1][c;H1][c;H1]1>>[N:1]",
        "n_reactants": 1,
        "substrate_hint": "Bn-protected amine",
        "reagent_hint": None,
        "conditions": ["H2", "Pd/C", "MeOH", "rt"],
        "category": "deprotection",
    },
    "ac_deprotection_o": {
        "description": "Remove acetyl (Ac) from alcohol",
        "smarts": "[O;R0:1][C;R0](=O)[C;H3]>>[O:1]",
        "n_reactants": 1,
        "substrate_hint": "Ac-protected alcohol",
        "reagent_hint": None,
        "conditions": ["K2CO3", "MeOH", "rt"],
        "category": "deprotection",
    },
    "ac_deprotection_n": {
        "description": "Remove acetyl (Ac) from amine",
        "smarts": "[NX3;H0,H1:1][C;R0](=O)[C;H3]>>[N:1]",
        "n_reactants": 1,
        "substrate_hint": "Ac-protected amine",
        "reagent_hint": None,
        "conditions": ["6M HCl", "reflux"],
        "category": "deprotection",
    },
    "pmb_deprotection": {
        "description": "Remove PMB (para-methoxybenzyl) from alcohol",
        "smarts":
            "[c;H1]1[c;H1]c(O[C;H3])[c;H1][c;H1]c1"
            "[C;H2][O;D2&R0:1]>>[O;H1:1]",
        "n_reactants": 1,
        "substrate_hint": "PMB-protected alcohol",
        "reagent_hint": None,
        "conditions": ["DDQ", "DCM/H2O", "rt"],
        "category": "deprotection",
    },
    "ts_deprotection": {
        "description": "Remove tosyl (Ts) from amine",
        "smarts":
            "[C;H3]c1[c;H1][c;H1]c(S(=O)(=O)"
            "[NX3;H0,H1;!$(NC=O):1])[c;H1][c;H1]1>>[N:1]",
        "n_reactants": 1,
        "substrate_hint": "Ts-protected amine",
        "reagent_hint": None,
        "conditions": ["Mg", "MeOH", "sonication"],
        "category": "deprotection",
    },
    "tfa_deprotection": {
        "description": "Remove trifluoroacetyl (TFA) from amine",
        "smarts": "[N;H0,H1:1]C(=O)C(F)(F)F>>[N:1]",
        "n_reactants": 1,
        "substrate_hint": "TFA-protected amine",
        "reagent_hint": None,
        "conditions": ["K2CO3", "MeOH/H2O", "rt"],
        "category": "deprotection",
    },
    # --- Protection templates (reversed deprotection SMARTS, unimolecular) ---
    "cbz_protection": {
        "description": "Add Cbz (carbobenzyloxy) to amine",
        "smarts": "[NX3;H1,H2:1]>>[N:1]C(=O)OCc1ccccc1",
        "n_reactants": 1,
        "substrate_hint": "free amine",
        "reagent_hint": None,
        "conditions": ["CbzCl", "NaOH", "dioxane/H2O", "0 \u00b0C"],
        "category": "protection",
    },
    "fmoc_protection": {
        "description": "Add Fmoc (9-fluorenylmethyloxycarbonyl) to amine",
        "smarts":
            "[NX3;H1,H2:1]>>[N:1]C(=O)OCC1c2ccccc2-c2ccccc21",
        "n_reactants": 1,
        "substrate_hint": "free amine",
        "reagent_hint": None,
        "conditions": ["Fmoc-OSu", "NaHCO3", "dioxane/H2O", "rt"],
        "category": "protection",
    },
    "tbs_protection": {
        "description": "Add TBS (tert-butyldimethylsilyl) to alcohol",
        "smarts": "[O;H1:1]>>[O:1][Si](C)(C)C(C)(C)C",
        "n_reactants": 1,
        "substrate_hint": "free alcohol",
        "reagent_hint": None,
        "conditions": ["TBSCl", "imidazole", "DMF", "rt"],
        "category": "protection",
    },
    "bn_protection_o": {
        "description": "Add benzyl (Bn) to alcohol",
        "smarts": "[O;H1:1]>>[O:1]Cc1ccccc1",
        "n_reactants": 1,
        "substrate_hint": "free alcohol",
        "reagent_hint": None,
        "conditions": ["BnBr", "NaH", "DMF", "0 \u00b0C"],
        "category": "protection",
    },
    "bn_protection_n": {
        "description": "Add benzyl (Bn) to amine",
        "smarts": "[NX3;H1,H2;!$(NC=O):1]>>[N:1]Cc1ccccc1",
        "n_reactants": 1,
        "substrate_hint": "free amine",
        "reagent_hint": None,
        "conditions": ["BnBr", "K2CO3", "DMF", "60 \u00b0C"],
        "category": "protection",
    },
    "ac_protection_o": {
        "description": "Add acetyl (Ac) to alcohol",
        "smarts": "[O;H1:1]>>[O:1]C(C)=O",
        "n_reactants": 1,
        "substrate_hint": "free alcohol",
        "reagent_hint": None,
        "conditions": ["Ac2O", "pyridine", "rt"],
        "category": "protection",
    },
    "ac_protection_n": {
        "description": "Add acetyl (Ac) to amine",
        "smarts": "[NX3;H1,H2:1]>>[N:1]C(C)=O",
        "n_reactants": 1,
        "substrate_hint": "free amine",
        "reagent_hint": None,
        "conditions": ["Ac2O", "Et3N", "DCM", "rt"],
        "category": "protection",
    },
    "pmb_protection": {
        "description": "Add PMB (para-methoxybenzyl) to alcohol",
        "smarts": "[O;H1:1]>>[O:1]Cc1ccc(OC)cc1",
        "n_reactants": 1,
        "substrate_hint": "free alcohol",
        "reagent_hint": None,
        "conditions": ["PMBCl", "NaH", "DMF", "0 \u00b0C"],
        "category": "protection",
    },
    "ts_protection": {
        "description": "Add tosyl (Ts) to amine",
        "smarts":
            "[NX3;H1,H2;!$(NC=O):1]>>[N:1]S(=O)(=O)c1ccc(C)cc1",
        "n_reactants": 1,
        "substrate_hint": "free amine",
        "reagent_hint": None,
        "conditions": ["TsCl", "Et3N", "DCM", "0 \u00b0C"],
        "category": "protection",
    },
}


# ---------------------------------------------------------------------------
# Dynamic loading of reaction templates from datamol
# ---------------------------------------------------------------------------

_datamol_cache: Optional[Dict[str, Dict[str, Any]]] = None


def _category_from_tags(tags: set) -> str:
    """Derive a template category from datamol tags."""
    if tags & {"heterocycle formation", "cyclization", "ring formation"}:
        return "heterocycle_formation"
    if tags & {"amide coupling", "amide"}:
        return "coupling"
    # Datamol uses "protecting group", also match "protection"/"deprotection"
    if tags & {"protecting group", "protection", "deprotection"}:
        # Distinguish protection vs deprotection by tag name
        tag_lc = {t.lower() for t in tags}
        if any("deprotect" in t for t in tag_lc):
            return "deprotection"
        if any("protect" in t for t in tag_lc):
            return "protection"
        return "protecting_group"
    if tags & {"C-C bond formation", "C-N bond formation",
               "C-O bond formation", "C-S bond formation",
               "N-arylation", "O-arylation", "S-arylation"}:
        return "coupling"
    return "functional_group"


def _load_datamol_templates() -> Dict[str, Dict[str, Any]]:
    """Load all reaction templates from datamol JSON.

    Reads ``reactions_datamol.json`` (127 curated reaction templates from
    the datamol project, Apache 2.0) and converts each entry to our
    standard template format with snake_case keys.  Includes heterocycle
    formation, couplings, functional group transforms, ester/amide
    chemistry, protection/deprotection, and more.

    Returns:
        Dict mapping template name to template dict.
    """
    global _datamol_cache
    if _datamol_cache is not None:
        return _datamol_cache

    json_path = os.path.join(os.path.dirname(__file__), "reactions_datamol.json")
    if not os.path.exists(json_path):
        logger.warning("reactions_datamol.json not found — datamol "
                        "templates unavailable")
        _datamol_cache = {}
        return _datamol_cache

    with open(json_path, encoding="utf-8") as fh:
        raw = json.load(fh)

    templates: Dict[str, Dict[str, Any]] = {}

    for key, entry in raw.items():
        syn_smarts = entry.get("syn_smarts", "")
        if not syn_smarts:
            continue

        tags = set(entry.get("tags", []))

        # Derive template name: JSON key is already kebab-case
        # Convert to snake_case for consistency
        tname = key.replace("-", "_")

        # Count reactant fragments (separated by '.')
        reactant_part = syn_smarts.split(">>")[0] if ">>" in syn_smarts else ""
        # Count top-level dots (outside brackets)
        n_reactants = 1
        depth = 0
        for ch in reactant_part:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            elif ch == "." and depth == 0:
                n_reactants += 1

        templates[tname] = {
            "description": entry.get("description", entry.get("long_name", key)),
            "long_name": entry.get("long_name", ""),
            "smarts": syn_smarts,
            "n_reactants": n_reactants,
            "substrate_hint": ", ".join(entry.get("rhs_classes", [])),
            "reagent_hint": (", ".join(entry.get("rhs_classes", [])[1:])
                             if n_reactants > 1 and len(entry.get("rhs_classes", [])) > 1
                             else None),
            "conditions": [],  # literature conditions vary
            "category": _category_from_tags(tags),
            "tags": list(tags),
            "source": "datamol",
        }

    _datamol_cache = templates
    logger.debug("Loaded %d templates from datamol", len(templates))
    return _datamol_cache


# Merged registry: classic hand-written + all datamol templates
_merged_templates: Optional[Dict[str, Dict[str, Any]]] = None


def _get_reaction_templates() -> Dict[str, Dict[str, Any]]:
    """Return the merged reaction template registry (lazy-loaded).

    Classic hand-written templates (couplings, functional group transforms,
    protection/deprotection) are merged with all datamol templates
    (heterocycle formation, couplings, FG transforms, and more).
    Classic templates take priority on name collisions.
    """
    global _merged_templates
    if _merged_templates is not None:
        return _merged_templates

    datamol = _load_datamol_templates()
    merged = dict(datamol)  # datamol first, classic overrides
    merged.update(_CLASSIC_TEMPLATES)
    _merged_templates = merged
    return _merged_templates


# ---------------------------------------------------------------------------
# Tool 7: list_reactions
# ---------------------------------------------------------------------------

def list_reactions(category: Optional[str] = None) -> Dict[str, Any]:
    """List available named reaction templates.

    Returns a summary of each reaction: name, description, number of
    reactants required, and typical conditions.  Use this to find the
    right template before calling ``apply_reaction``.

    Args:
        category: Optional filter.  One of ``"coupling"``,
            ``"functional_group"``, or ``"heterocycle_formation"``.
            If *None*, all templates are returned.

    Returns:
        Dict with ``ok``, ``reactions`` (list of summaries), and
        ``categories`` (list of available category names).

    Example::

        >>> result = list_reactions()
        >>> for r in result["reactions"]:
        ...     print(r["name"], "—", r["description"])
        suzuki_coupling — Suzuki coupling: aryl halide + boronic acid to biaryl
        ...
        >>> result = list_reactions(category="heterocycle_formation")
    """
    templates = _get_reaction_templates()
    rxns = []
    cats = set()
    for name, tmpl in templates.items():
        cat = tmpl.get("category", "other")
        cats.add(cat)
        if category and cat != category:
            continue
        rxns.append({
            "name": name,
            "description": tmpl["description"],
            "n_reactants": tmpl["n_reactants"],
            "substrate_hint": tmpl["substrate_hint"],
            "reagent_hint": tmpl.get("reagent_hint"),
            "conditions": tmpl.get("conditions", []),
            "category": cat,
        })
    return {"ok": True, "reactions": rxns, "categories": sorted(cats)}


# ---------------------------------------------------------------------------
# Tool 8: apply_reaction
# ---------------------------------------------------------------------------

def apply_reaction(reaction_name: str,
                   substrate: str,
                   reagent: Optional[str] = None) -> Dict[str, Any]:
    """Apply a named reaction template to transform a substrate.

    Takes a substrate SMILES (and optionally a reagent SMILES for
    bimolecular reactions) and returns the product(s).

    Args:
        reaction_name: Template name from ``list_reactions()``.
        substrate: SMILES of the main substrate.
        reagent: SMILES of the coupling partner (for 2-reactant rxns).
                 Can also be a chemical name or abbreviation.

    Returns:
        Dict with ``ok``, ``products`` (list of product dicts with
        ``smiles`` and ``name`` keys), and ``conditions``.

    Example::

        >>> apply_reaction("nitro_reduction", "c1ccc([N+](=O)[O-])cc1")
        {'ok': True,
         'products': [{'smiles': 'Nc1ccccc1', 'name': 'aniline'}],
         'conditions': ['SnCl2·2H2O', 'EtOH', '80 °C']}
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    # Look up template
    templates = _get_reaction_templates()
    tmpl = templates.get(reaction_name)
    # Case-insensitive fallback
    if tmpl is None:
        lower_map = {k.lower(): k for k in templates}
        real_key = lower_map.get(reaction_name.lower())
        if real_key:
            tmpl = templates[real_key]
    if tmpl is None:
        # Fuzzy match: find closest reaction names
        query_lower = reaction_name.lower().replace("-", "_").replace(" ", "_")
        scored = []
        for k in templates:
            k_lower = k.lower()
            # Substring match
            if query_lower in k_lower or k_lower in query_lower:
                scored.append((0, k))
            else:
                # Count shared words
                q_parts = set(query_lower.split("_"))
                k_parts = set(k_lower.split("_"))
                overlap = len(q_parts & k_parts)
                if overlap > 0:
                    scored.append((1, k))
        scored.sort()
        suggestions = [s[1] for s in scored[:5]]
        if suggestions:
            hint = f"Did you mean: {', '.join(suggestions)}?"
        else:
            # Show a sample of available reactions
            all_names = sorted(templates.keys())
            hint = f"Some available reactions: {', '.join(all_names[:15])}... ({len(all_names)} total)"
        return {
            "ok": False,
            "error": f"Unknown reaction '{reaction_name}'. {hint}",
        }

    # Parse reaction SMARTS
    try:
        rxn = AllChem.ReactionFromSmarts(tmpl["smarts"])
    except Exception as exc:
        return {"ok": False, "error": f"Invalid reaction SMARTS: {exc}"}

    # Parse substrate
    sub_mol = Chem.MolFromSmiles(substrate)
    if sub_mol is None:
        # Maybe it's a name — try resolving
        resolved = _resolve_query(substrate)
        if resolved:
            sub_mol = Chem.MolFromSmiles(resolved["smiles"])
        if sub_mol is None:
            return {"ok": False, "error": f"Could not parse substrate '{substrate}'."}

    # Handle reagent for bimolecular reactions
    if tmpl["n_reactants"] == 2:
        if not reagent:
            return {
                "ok": False,
                "error": f"Reaction '{reaction_name}' requires a reagent. "
                         f"Expected: {tmpl.get('reagent_hint', 'coupling partner')}.",
            }
        rea_mol = Chem.MolFromSmiles(reagent)
        if rea_mol is None:
            # Try resolving as name
            resolved = _resolve_query(reagent)
            if resolved:
                rea_mol = Chem.MolFromSmiles(resolved["smiles"])
            if rea_mol is None:
                return {"ok": False,
                        "error": f"Could not parse reagent '{reagent}'."}
        reactants = (sub_mol, rea_mol)
    else:
        reactants = (sub_mol,)

    # Run reaction
    try:
        product_sets = rxn.RunReactants(reactants)
    except Exception as exc:
        return {"ok": False, "error": f"Reaction failed: {exc}"}

    if not product_sets:
        # Try swapped reactant order for bimolecular reactions
        if tmpl["n_reactants"] == 2:
            try:
                product_sets = rxn.RunReactants((reactants[1], reactants[0]))
            except Exception:
                pass
        if not product_sets:
            return {
                "ok": False,
                "error": "No products formed. Check that the substrate "
                         f"matches: {tmpl['substrate_hint']}.",
            }

    # Collect unique products
    seen = set()
    products = []
    for prod_tuple in product_sets:
        for prod in prod_tuple:
            try:
                Chem.SanitizeMol(prod)
                smi = Chem.MolToSmiles(prod)
                if smi not in seen:
                    seen.add(smi)
                    name = _smiles_to_name_cs(smi)
                    products.append({"smiles": smi, "name": name})
            except Exception:
                continue

    if not products:
        return {"ok": False, "error": "Products could not be sanitised."}

    return {
        "ok": True,
        "products": products,
        "conditions": tmpl["conditions"],
        "reaction": reaction_name,
    }


# ---------------------------------------------------------------------------
# Tool 9: deprotect
# ---------------------------------------------------------------------------

def _detect_deprotection_templates(mol) -> List[str]:
    """Return names of all deprotection templates that fire on *mol*.

    Used internally by :func:`deprotect` to route single-PG cases through
    :func:`apply_reaction` and multi-PG (or unrecognised) cases through
    RDKit's ``rdDeprotect`` library.

    Args:
        mol: RDKit ``Mol`` object.

    Returns:
        List of template names (from the merged registry) whose SMARTS
        match at least one site on *mol*.
    """
    from rdkit.Chem import AllChem

    templates = _get_reaction_templates()
    fired: List[str] = []
    for name, tmpl in templates.items():
        if tmpl.get("category") not in ("deprotection",):
            continue
        if tmpl.get("n_reactants", 1) != 1:
            continue
        try:
            rxn = AllChem.ReactionFromSmarts(tmpl["smarts"])
            if rxn.RunReactants((mol,)):
                fired.append(name)
        except Exception:
            continue
    return fired


# Map from apply_reaction template name to PG abbreviation used in the
# ``removed`` list that callers expect.  Keeps the public return format
# stable even when template names are refactored.
_TEMPLATE_TO_PG_ABBREV: Dict[str, str] = {
    "BOC_deprotection": "Boc",
    "cbz_deprotection": "Cbz",
    "fmoc_deprotection": "Fmoc",
    "tbs_deprotection": "TBS",
    "bn_deprotection_o": "Bn",
    "bn_deprotection_n": "Bn",
    "ac_deprotection_o": "Ac",
    "ac_deprotection_n": "Ac",
    "pmb_deprotection": "PMB",
    "ts_deprotection": "Ts",
    "tfa_deprotection": "TFA",
}


def deprotect(smiles: str) -> Dict[str, Any]:
    """Remove common protecting groups from a molecule.

    For substrates carrying a **single recognisable protecting group**,
    this function delegates to :func:`apply_reaction` using the
    appropriate named template (e.g. ``"BOC_deprotection"``,
    ``"fmoc_deprotection"``).  This keeps the deprotection logic
    centralised in the reaction-template registry and makes the
    single-PG path available to agents via :func:`apply_reaction`
    directly.

    For substrates with **multiple protecting groups**, or when the PG is
    not covered by the named-template registry, the function falls back to
    RDKit's built-in ``rdDeprotect`` library (25+ templates covering Boc,
    Fmoc, Cbz, TBS, THP, Bn, Ac, PMB, Tr, and more).

    The return format is identical in all cases, so existing callers are
    unaffected.

    Args:
        smiles: SMILES of the protected molecule.

    Returns:
        Dict with ``ok``, ``product_smiles``, ``product_name``,
        and ``removed`` (list of protecting group abbreviations removed).

    Example::

        >>> deprotect("O=C(OC(C)(C)C)Nc1ccccc1")  # Boc-aniline
        {'ok': True, 'product_smiles': 'Nc1ccccc1', 'product_name': 'aniline',
         'removed': ['Boc']}

    Note:
        Single-PG deprotections can also be called directly via
        :func:`apply_reaction`, e.g.
        ``apply_reaction("BOC_deprotection", smiles)``.  Use that form
        when you know the specific protecting group in advance.
    """
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        resolved = _resolve_query(smiles)
        if resolved:
            mol = Chem.MolFromSmiles(resolved["smiles"])
        if mol is None:
            return {"ok": False, "error": f"Could not parse '{smiles}'."}

    original_smi = Chem.MolToSmiles(mol)

    # --- Fast path: exactly one named template fires → delegate to apply_reaction ---
    fired = _detect_deprotection_templates(mol)
    if len(fired) == 1:
        tname = fired[0]
        ar_result = apply_reaction(tname, original_smi)
        if ar_result.get("ok") and ar_result.get("products"):
            product_smi = ar_result["products"][0]["smiles"]
            pg_abbrev = _TEMPLATE_TO_PG_ABBREV.get(tname, tname)
            return {
                "ok": True,
                "product_smiles": product_smi,
                "product_name": _smiles_to_name_cs(product_smi),
                "removed": [pg_abbrev],
            }
        # apply_reaction unexpectedly failed — fall through to rdDeprotect

    # --- Fallback: rdDeprotect handles multiple PGs or unrecognised ones ---
    try:
        from rdkit.Chem import rdDeprotect
        result = rdDeprotect.Deprotect(mol)
    except ImportError:
        if fired:
            # rdDeprotect unavailable but we know which PG(s) to remove —
            # run apply_reaction for each in sequence
            current_smi = original_smi
            removed_abbrevs: List[str] = []
            for tname in fired:
                ar = apply_reaction(tname, current_smi)
                if ar.get("ok") and ar.get("products"):
                    current_smi = ar["products"][0]["smiles"]
                    removed_abbrevs.append(_TEMPLATE_TO_PG_ABBREV.get(tname, tname))
            if removed_abbrevs:
                return {
                    "ok": True,
                    "product_smiles": current_smi,
                    "product_name": _smiles_to_name_cs(current_smi),
                    "removed": removed_abbrevs,
                }
        return {
            "ok": False,
            "error": (
                "rdDeprotect not available in this RDKit build. "
                "Use apply_reaction() with a specific template name "
                "(e.g. 'BOC_deprotection') for single-PG removal."
            ),
        }
    except Exception as exc:
        return {"ok": False, "error": f"Deprotection failed: {exc}"}

    product_smi = Chem.MolToSmiles(result)

    if product_smi == original_smi:
        return {
            "ok": True,
            "product_smiles": product_smi,
            "product_name": _smiles_to_name_cs(product_smi),
            "removed": [],
            "note": "No protecting groups detected.",
        }

    # Identify which PGs were removed by checking each rdDeprotect template
    removed = []
    try:
        from rdkit.Chem import AllChem
        deprots = rdDeprotect.GetDeprotections()
        for d in deprots:
            rxn_sma = d.reaction_smarts
            rxn = AllChem.ReactionFromSmarts(rxn_sma)
            try:
                prods = rxn.RunReactants((mol,))
                if prods:
                    for ptuple in prods:
                        for p in ptuple:
                            try:
                                Chem.SanitizeMol(p)
                                if Chem.MolToSmiles(p) != original_smi:
                                    removed.append(d.abbreviation)
                                    break
                            except Exception:
                                continue
                        if removed and removed[-1] == d.abbreviation:
                            break
            except Exception:
                continue
    except Exception:
        pass

    name = _smiles_to_name_cs(product_smi)
    return {
        "ok": True,
        "product_smiles": product_smi,
        "product_name": name,
        "removed": removed,
    }


# ---------------------------------------------------------------------------
# Tool 10: draw_molecule
# ---------------------------------------------------------------------------

def draw_molecule(
    mol_json: Dict[str, Any],
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Render a single molecule to a standalone CDXML document.

    Takes a molecule dict (as returned by ``resolve_compound`` or any dict
    containing at minimum a ``smiles`` field) and generates a CDXML string
    suitable for opening directly in ChemDraw.  No arrow, no reaction scheme —
    just the structure, centred on a page.

    An optional text label (compound name or custom label) is placed below the
    structure when the input dict contains a ``label``, ``name``, or
    ``iupac_name`` field (checked in that priority order).

    Args:
        mol_json: Dict with at minimum ``"smiles"``.  Optional display keys:
            ``"label"`` (used verbatim), ``"name"``, ``"iupac_name"``.
            Any other fields are ignored.
        output_path: If given, the CDXML string is also written to this file
            path.

    Returns:
        Dict with keys:

        - ``ok``: bool
        - ``cdxml``: CDXML document string (on success)
        - ``output_path``: echoed path if *output_path* was specified
        - ``error``: error message (when ``ok=False``)

    Example::

        >>> result = draw_molecule({"smiles": "CC(=O)Oc1ccccc1C(=O)O",
        ...                         "name": "aspirin"})
        >>> result["ok"]
        True
        >>> result["cdxml"][:20]
        '<?xml version="1.0"'
    """
    # --- Validate input ---
    smiles = mol_json.get("smiles")
    if not smiles:
        return {"ok": False, "error": "mol_json must contain a 'smiles' field."}

    # --- Resolve display label (priority: label > name > iupac_name) ---
    label: Optional[str] = (
        mol_json.get("label")
        or mol_json.get("name")
        or mol_json.get("iupac_name")
    )

    # --- Import renderer internals (lazy — avoids import-time cost) ---
    try:
        from cdxml_toolkit.render.renderer import (
            _IDGen,
            _smiles_to_fragment_data,
            _build_fragment,
            _build_text_element,
            _fragment_bbox,
            _bbox_center,
            _shift_atoms,
        )
    except ImportError as exc:
        return {"ok": False, "error": f"Renderer not available: {exc}"}

    from cdxml_toolkit.constants import (
        CDXML_FOOTER,
        CDXML_HEADER,
        ACS_LABEL_FONT,
        ACS_LABEL_SIZE,
        ACS_LABEL_FACE,
        ACS_CAPTION_SIZE,
        ACS_HASH_SPACING,
        ACS_MARGIN_WIDTH,
        ACS_LINE_WIDTH,
        ACS_BOLD_WIDTH,
        ACS_BOND_LENGTH_STR,
        ACS_BOND_SPACING,
        ACS_CHAIN_ANGLE_STR,
    )

    # --- Generate 2D coordinates ---
    CENTER_X, CENTER_Y = 200.0, 200.0

    result = _smiles_to_fragment_data(smiles, CENTER_X, CENTER_Y)
    if result is None:
        return {
            "ok": False,
            "error": f"Could not generate 2D coordinates for SMILES: {smiles!r}",
        }

    atoms, bonds = result

    # Re-centre the structure at the desired origin
    bbox = _fragment_bbox(atoms)
    cx, cy = _bbox_center(bbox)
    _shift_atoms(atoms, CENTER_X - cx, CENTER_Y - cy)
    bbox = _fragment_bbox(atoms)

    # --- Build XML ---
    ids = _IDGen(1000)
    frag_xml, _, _ = _build_fragment(atoms, bonds, ids)

    xml_parts = [frag_xml]

    # --- Optional label below the structure ---
    if label:
        label_y = bbox[3] + 14.0  # 14 pt below the structure bottom
        lbl_xml, _ = _build_text_element(
            [label], CENTER_X, label_y, ids,
            justification="Center", use_formatting=False,
        )
        xml_parts.append(lbl_xml)

    inner_xml = "\n".join(xml_parts)

    # --- Wrap in CDXML document ---
    page_id = ids.next()

    header = CDXML_HEADER.format(
        bbox="0 0 1620 2160",
        label_font=ACS_LABEL_FONT,
        label_size=ACS_LABEL_SIZE,
        label_face=ACS_LABEL_FACE,
        caption_size=ACS_CAPTION_SIZE,
        hash_spacing=ACS_HASH_SPACING,
        margin_width=ACS_MARGIN_WIDTH,
        line_width=ACS_LINE_WIDTH,
        bold_width=ACS_BOLD_WIDTH,
        bond_length=ACS_BOND_LENGTH_STR,
        bond_spacing=ACS_BOND_SPACING,
        chain_angle=ACS_CHAIN_ANGLE_STR,
    )

    page_open = (
        f'<page id="{page_id}" BoundingBox="0 0 1620 2160" '
        f'HeaderPosition="36" FooterPosition="36" '
        f'PrintTrimMarks="yes" HeightPages="3" WidthPages="3">'
    )

    cdxml = "\n".join([header, page_open, inner_xml, "</page>", CDXML_FOOTER])

    # --- Write to file if requested ---
    ret: Dict[str, Any] = {"ok": True, "cdxml": cdxml}
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(cdxml)
            ret["output_path"] = output_path
        except OSError as exc:
            return {"ok": False, "error": f"Failed to write '{output_path}': {exc}"}

    return ret


# ---------------------------------------------------------------------------
# Tool 11: modify_molecule
# ---------------------------------------------------------------------------

def _compute_formula(smiles: str) -> Optional[str]:
    """Get molecular formula string from SMILES using RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return rdMolDescriptors.CalcMolFormula(mol)
    except Exception:
        return None


def _compute_mw(smiles: str) -> Optional[float]:
    """Get exact molecular weight (monoisotopic) from SMILES using RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return round(Descriptors.ExactMolWt(mol), 4)
    except Exception:
        return None


def _parse_formula_counts(formula: str) -> Dict[str, int]:
    """Parse a molecular formula string into element counts.

    Handles simple formulas like ``C26H26N8O3``.  Returns a dict mapping
    element symbol to count.
    """
    counts: Dict[str, int] = {}
    for sym, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        if sym:
            counts[sym] = counts.get(sym, 0) + (int(n) if n else 1)
    return counts


def _delta_formula(formula_in: str, formula_out: str) -> str:
    """Compute element-by-element formula difference as a compact string.

    Example: ``C20H20`` to ``C26H26`` gives ``+C6H6``.
    Returns a string like ``"+C6H4, -D3"`` or ``"(no change)"``.
    """
    counts_in = _parse_formula_counts(formula_in)
    counts_out = _parse_formula_counts(formula_out)

    all_elems = sorted(set(list(counts_in.keys()) + list(counts_out.keys())))
    added: List[str] = []
    removed: List[str] = []

    for elem in all_elems:
        n_in = counts_in.get(elem, 0)
        n_out = counts_out.get(elem, 0)
        delta = n_out - n_in
        if delta > 0:
            added.append(f"{elem}{delta if delta > 1 else ''}")
        elif delta < 0:
            removed.append(f"{elem}{abs(delta) if abs(delta) > 1 else ''}")

    parts = []
    if added:
        parts.append("+" + "".join(added))
    if removed:
        parts.append("-" + "".join(removed))
    return ", ".join(parts) if parts else "(no change)"


def _build_mol_diff(input_smiles: str, output_smiles: str) -> Dict[str, Any]:
    """Build the ``diff`` sub-dict using MCS + formula comparison."""
    diff: Dict[str, Any] = {
        "atoms_added": [],
        "atoms_removed": [],
        "atoms_changed": [],
        "mcs_smarts": None,
        "delta_formula": None,
        "delta_mw": None,
    }

    try:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS
        from cdxml_toolkit.naming.aligned_namer import molecular_diff

        md = molecular_diff(input_smiles, output_smiles)

        if not md.fallback_used:
            try:
                sm_mol = Chem.MolFromSmiles(input_smiles)
                prod_mol = Chem.MolFromSmiles(output_smiles)
                if sm_mol and prod_mol:
                    mcs = rdFMCS.FindMCS(
                        [sm_mol, prod_mol],
                        threshold=1.0,
                        ringMatchesRingOnly=True,
                        completeRingsOnly=True,
                        atomCompare=rdFMCS.AtomCompare.CompareElements,
                        bondCompare=rdFMCS.BondCompare.CompareOrder,
                        timeout=5,
                    )
                    if not mcs.canceled and mcs.numAtoms >= 3:
                        diff["mcs_smarts"] = mcs.smartsString
            except Exception:
                pass

        for ch in md.changes:
            if ch.change_type == "addition":
                diff["atoms_added"].append(ch.prod_name)
            elif ch.change_type == "removal":
                diff["atoms_removed"].append(ch.sm_name)
            elif ch.change_type == "replace":
                diff["atoms_changed"].append(
                    {"from": ch.sm_name, "to": ch.prod_name}
                )
    except Exception:
        pass

    # Formula and MW delta (always computed — does not need MCS)
    formula_in = _compute_formula(input_smiles)
    formula_out = _compute_formula(output_smiles)
    mw_in = _compute_mw(input_smiles)
    mw_out = _compute_mw(output_smiles)

    if formula_in and formula_out:
        diff["delta_formula"] = _delta_formula(formula_in, formula_out)
    if mw_in is not None and mw_out is not None:
        diff["delta_mw"] = round(mw_out - mw_in, 4)

    from cdxml_toolkit.chemistry_diff import structural_diff
    comparison = structural_diff(input_smiles, output_smiles)
    diff.update(comparison)
    return diff


def _build_aligned_names(input_smiles: str, output_smiles: str) -> str:
    """Build an aligned name comparison string for two SMILES.

    Returns a string like ``"X \u2192 Y\\n  changes: ..."``.
    Falls back to a simple ``"name1 \u2192 name2"`` via ChemScript.
    """
    try:
        from cdxml_toolkit.naming.aligned_namer import (
            find_aligned_names, format_name_diff,
        )
        ar = find_aligned_names(input_smiles, output_smiles)
        if ar.best_sm_name and ar.best_prod_name:
            diff_str = format_name_diff(ar.best_sm_name, ar.best_prod_name)
            return (
                f"{ar.best_sm_name} \u2192 {ar.best_prod_name}"
                f"\n  changes: {diff_str}"
            )
    except Exception:
        pass

    n1 = _smiles_to_name_cs(input_smiles) or ""
    n2 = _smiles_to_name_cs(output_smiles) or ""
    if n1 and n2:
        return f"{n1} \u2192 {n2}"
    return ""


def modify_molecule(mol_json: Dict[str, Any],
                    operation: str,
                    **kwargs: Any) -> Dict[str, Any]:
    """Modify a molecule and verify the change with a structural diff.

    This is the molecular editor for LLM orchestration.  It takes a
    molecule (as a dict with at least a ``smiles`` key), applies an
    operation, and returns the modified molecule with a structural diff
    so the LLM can verify the change happened as intended.

    Parameters
    ----------
    mol_json : dict
        Source molecule dict.  Must contain ``smiles`` (canonical SMILES).
        May also contain ``name`` or ``iupac_name`` for display.
    operation : str
        One of:

        - ``"analyze"`` — inspect the molecule without modifying it.
          Returns functional groups, alternative IUPAC names, bracket
          tree, prefix form, formula, and MW.  No additional kwargs.

        - ``"name_surgery"`` — modify via IUPAC name manipulation.
          Additional kwargs:

          - ``add``: list of ``{"locant": str, "prefix": str}`` dicts
          - ``remove``: list of prefix strings to remove

        - ``"smarts"`` — apply a SMARTS reaction transform.
          Additional kwargs:

          - ``smarts``: reaction SMARTS string, e.g. ``"[c:1][F]>>[c:1][Cl]"``
          - ``reaction_name``: name from ``list_reactions()`` (alternative)

        - ``"set_smiles"`` — accept new SMILES from the LLM.
          Additional kwargs:

          - ``new_smiles``: str (validated with RDKit)
          - ``description``: str (optional, for context)

        - ``"reaction"`` — apply a named reaction template (calls
          ``apply_reaction()`` internally).  Additional kwargs:

          - ``reaction_name``: str (required) — template from ``list_reactions()``
          - ``reagent``: dict with ``smiles`` key (for binary reactions)

    Returns
    -------
    dict
        For ``"analyze"`` operation:

        - ``ok``: bool
        - ``input_smiles``: canonical SMILES of input
        - ``canonical_name``: IUPAC name (from ChemScript, or empty)
        - ``alternative_names``: list of alternative IUPAC names (round-trip
          validated) showing different parent/substituent perspectives
        - ``functional_groups``: list of functional group names present
          (e.g. ``["aryl chloride", "pyridine", "amide"]``)
        - ``prefix_form``: IUPAC prefix if this could be a substituent, or
          ``None``
        - ``bracket_tree``: the canonical IUPAC name with its bracket
          hierarchy preserved (same as ``canonical_name``); the caller can
          parse parenthesised groups to see substituents at each depth
        - ``formula``: molecular formula string
        - ``mw``: exact monoisotopic MW (float)

        For modification operations (``"name_surgery"``, ``"smarts"``,
        ``"set_smiles"``):

        - ``ok``: bool
        - ``input_smiles``: canonical SMILES of input
        - ``output_smiles``: canonical SMILES of output
        - ``input_name``: IUPAC name of input
        - ``output_name``: IUPAC name of output (from ChemScript)
        - ``aligned_names``: side-by-side aligned name comparison string
        - ``diff``: sub-dict with:

          - ``atoms_added``: list of fragment names added
          - ``atoms_removed``: list of fragment names removed
          - ``atoms_changed``: list of ``{"from": ..., "to": ...}`` dicts
          - ``mcs_smarts``: maximum common substructure SMARTS (str or None)
          - ``delta_formula``: formula difference (e.g. ``"+C6H5, -F"``)
          - ``delta_mw``: MW difference in Da (float)

        - ``formula``: molecular formula of output
        - ``mw``: exact monoisotopic MW of output

    Examples
    --------
    ::

        # Swap a CD3 for benzyl via SMARTS
        result = modify_molecule(
            {"smiles": "C([2H])([2H])[2H]"},
            "smarts",
            smarts="[C:1]([2H])([2H])[2H]>>[C:1]Cc1ccccc1",
        )

        # Add a fluoro group via name surgery
        result = modify_molecule(
            {"smiles": "Clc1ccncc1"},
            "name_surgery",
            add=[{"locant": "3", "prefix": "fluoro"}],
        )

        # Directly set new SMILES and verify
        result = modify_molecule(
            {"smiles": "Clc1ccncc1"},
            "set_smiles",
            new_smiles="Clc1cc(F)ncc1",
            description="added fluoro at C3",
        )
    """
    from rdkit import Chem

    # ---- Validate input ----
    input_smiles_raw = mol_json.get("smiles", "")
    if not input_smiles_raw:
        return {"ok": False, "error": "mol_json must contain 'smiles'."}

    in_mol = Chem.MolFromSmiles(input_smiles_raw)
    if in_mol is None:
        return {"ok": False,
                "error": f"Could not parse input SMILES: '{input_smiles_raw}'."}
    input_smiles = Chem.MolToSmiles(in_mol)

    output_smiles: Optional[str] = None
    alternative_products: List[Dict[str, Any]] = []

    # ---- Dispatch operation ----
    if operation == "set_smiles":
        new_smiles = kwargs.get("new_smiles", "")
        if not new_smiles:
            return {"ok": False, "error": "'new_smiles' is required for set_smiles."}
        out_mol = Chem.MolFromSmiles(new_smiles)
        if out_mol is None:
            return {"ok": False,
                    "error": f"'new_smiles' is not a valid SMILES: '{new_smiles}'."}
        output_smiles = Chem.MolToSmiles(out_mol)

    elif operation == "smarts":
        smarts_str = kwargs.get("smarts", "")
        reaction_name = kwargs.get("reaction_name", "")

        if reaction_name and not smarts_str:
            templates = _get_reaction_templates()
            tmpl = templates.get(reaction_name)
            if tmpl is None:
                return {"ok": False,
                        "error": f"Unknown reaction_name '{reaction_name}'."}
            smarts_str = tmpl["smarts"]

        if not smarts_str:
            return {"ok": False,
                    "error": "'smarts' or 'reaction_name' is required for smarts."}

        try:
            from rdkit.Chem import AllChem
            rxn = AllChem.ReactionFromSmarts(smarts_str)
        except Exception as exc:
            return {"ok": False, "error": f"Invalid reaction SMARTS: {exc}"}

        try:
            product_sets = rxn.RunReactants((in_mol,))
        except Exception as exc:
            return {"ok": False, "error": f"SMARTS reaction failed: {exc}"}

        if not product_sets:
            # Detect common patterns and suggest named reactions
            hints = []
            s = smarts_str
            # Check most specific patterns first
            if any(p in s for p in ["OC(C)(C)C", "Boc", "BOC", "boc", "tBu"]):
                hints.append("For Boc deprotection, try: operation='reaction', reaction_name='BOC_deprotection'")
            elif any(p in s for p in ["Fmoc", "fmoc", "fluorenyl"]):
                hints.append("For Fmoc deprotection, try: operation='reaction', reaction_name='fmoc_deprotection'")
            elif "C(=O)N" in s and "OC(=O)N" not in s:
                hints.append("For amide hydrolysis, try: operation='reaction', reaction_name='amide_hydrolysis'")
            elif "C(=O)O" in s:
                hints.append("For ester hydrolysis, try: operation='reaction', reaction_name='ester_hydrolysis'")
            if not hints:
                hints.append("Hint: use operation='reaction' with a reaction_name for common transformations. Call modify_molecule with operation='reaction' and no reaction_name to see all available reactions.")
            return {
                "ok": False,
                "error": (
                    "SMARTS pattern did not match the input molecule. "
                    + " ".join(hints)
                ),
                "input_smiles": input_smiles,
            }

        for prod_tuple in product_sets:
            for prod in prod_tuple:
                try:
                    Chem.SanitizeMol(prod)
                    output_smiles = Chem.MolToSmiles(prod)
                    break
                except Exception:
                    continue
            if output_smiles:
                break

        if not output_smiles:
            return {"ok": False,
                    "error": "SMARTS reaction produced no valid products."}

    elif operation == "name_surgery":
        iupac_name = (mol_json.get("iupac_name")
                      or mol_json.get("name")
                      or _smiles_to_name_cs(input_smiles))

        if not iupac_name:
            return {
                "ok": False,
                "error": (
                    "name_surgery requires an IUPAC name.  "
                    "Provide 'iupac_name' in mol_json, or ensure ChemScript "
                    "is available to auto-generate one."
                ),
            }

        add_list: List[Dict[str, str]] = kwargs.get("add", [])
        remove_list: List[str] = kwargs.get("remove", [])

        current_name = iupac_name

        for prefix_to_remove in remove_list:
            # Auto-resolve abbreviations to IUPAC prefix form
            pfx_r = get_prefix_form(prefix_to_remove)
            if pfx_r.get("ok"):
                prefix_to_remove = pfx_r["prefix"]
            res = _modify_remove(current_name, prefix_to_remove,
                                 validate=True, use_network=False)
            if not res.get("ok"):
                return {
                    "ok": False,
                    "error": (f"name_surgery remove '{prefix_to_remove}' "
                              f"failed: {res.get('error', '?')}"),
                    "input_smiles": input_smiles,
                    "tried_name": current_name,
                }
            if res.get("valid") and res.get("smiles"):
                current_name = res["name"]
            else:
                return {
                    "ok": False,
                    "error": (f"name_surgery remove '{prefix_to_remove}' "
                              f"produced invalid name: '{res.get('name')}'."),
                    "input_smiles": input_smiles,
                }

        for sub in add_list:
            prefix = sub.get("prefix", "")
            locant = sub.get("locant", "")
            if not prefix:
                continue
            # Auto-resolve abbreviations/formulae to IUPAC prefix form
            # so the agent can say "CF3" instead of "trifluoromethyl".
            pfx_result = get_prefix_form(prefix)
            if pfx_result.get("ok"):
                prefix = pfx_result["prefix"]
            res = _modify_add(current_name, prefix, locant,
                              validate=True, use_network=False)
            if not res.get("ok"):
                return {
                    "ok": False,
                    "error": (f"name_surgery add '{prefix}' at '{locant}' "
                              f"failed: {res.get('error', '?')}"),
                    "input_smiles": input_smiles,
                    "tried_name": current_name,
                }
            if res.get("valid") and res.get("smiles"):
                current_name = res["name"]
            else:
                return {
                    "ok": False,
                    "error": (f"name_surgery add '{prefix}' produced "
                              f"invalid name: '{res.get('name')}'."),
                    "input_smiles": input_smiles,
                }

        output_smiles = _try_validate(current_name, use_network=False)
        if not output_smiles:
            return {
                "ok": False,
                "error": f"Could not validate name surgery result: '{current_name}'.",
                "input_smiles": input_smiles,
                "output_name_attempted": current_name,
            }
        out_mol = Chem.MolFromSmiles(output_smiles)
        if out_mol:
            output_smiles = Chem.MolToSmiles(out_mol)

    elif operation == "reaction":
        # ---- Reaction: apply a named reaction template via apply_reaction ----
        reaction_name = kwargs.get("reaction_name", "")
        if not reaction_name:
            rxn_list = list_reactions()
            names = [r["name"] for r in rxn_list.get("reactions", [])]
            return {
                "ok": False,
                "error": (
                    "'reaction_name' is required for the reaction operation. "
                    f"Available reactions: {', '.join(names)}"
                ),
                "input_smiles": input_smiles,
            }

        reagent_dict = kwargs.get("reagent", None)
        reagent_smiles = reagent_dict.get("smiles") if isinstance(reagent_dict, dict) else None

        rxn_result = apply_reaction(reaction_name, input_smiles, reagent_smiles)
        if not rxn_result.get("ok"):
            return {
                "ok": False,
                "error": rxn_result.get("error", "Reaction failed."),
                "input_smiles": input_smiles,
                "reaction_name": reaction_name,
            }

        products = rxn_result.get("products", [])
        if not products:
            return {
                "ok": False,
                "error": "Reaction produced no products.",
                "input_smiles": input_smiles,
                "reaction_name": reaction_name,
            }

        # Primary product is first; store remaining as alternatives
        output_smiles = products[0]["smiles"]
        alternative_products = products[1:] if len(products) > 1 else []

    elif operation == "analyze":
        # ---- Analyze: reason about a molecule without modifying it ----
        # Functional group SMARTS (name → SMARTS pattern).
        _FG_SMARTS: List[tuple] = [
            # Halogens
            ("aryl fluoride",        "[F][c]"),
            ("aryl chloride",        "[Cl][c]"),
            ("aryl bromide",         "[Br][c]"),
            ("aryl iodide",          "[I][c]"),
            ("alkyl fluoride",       "[F][CX4]"),
            ("alkyl chloride",       "[Cl][CX4]"),
            ("alkyl bromide",        "[Br][CX4]"),
            ("alkyl iodide",         "[I][CX4]"),
            # Nitrogen
            ("primary amine",        "[NH2][CX4]"),
            ("secondary amine",      "[NH1]([CX4])[CX4]"),
            ("tertiary amine",       "[NX3;!$(N=*)]([CX4])([CX4])[CX4]"),
            ("aromatic amine",       "[NH2][c]"),
            ("amide",                "[CX3](=[OX1])[NX3]"),
            ("sulfonamide",          "[SX4](=[OX1])(=[OX1])[NX3]"),
            ("nitro",                "[$([NX3](=O)=O),$([NX3+](=O)[O-])]"),
            ("nitrile",              "[CX2]#[NX1]"),
            ("isocyanate",           "[NX2]=[C]=[OX1]"),
            ("urea",                 "[NX3][CX3](=[OX1])[NX3]"),
            ("carbamate",            "[NX3][CX3](=[OX1])[OX2]"),
            # Oxygen
            ("carboxylic acid",      "[CX3](=[OX1])[OX2H1]"),
            ("ester",                "[CX3](=[OX1])[OX2][CX4]"),
            ("ketone",               "[CX3](=[OX1])[CX4]"),
            ("aldehyde",             "[CX3H1](=[OX1])"),
            ("alcohol",              "[OX2H][CX4]"),
            ("phenol",               "[OX2H][c]"),
            ("ether",                "[OX2]([CX4])[CX4]"),
            ("aryl ether",           "[OX2]([c])[CX4,c]"),
            ("epoxide",              "[C]1[O][C]1"),
            ("anhydride",            "[CX3](=[OX1])[OX2][CX3](=[OX1])"),
            # Sulfur
            ("thiol",                "[SX2H]"),
            ("thioether",            "[SX2]([CX4])[CX4]"),
            ("sulfoxide",            "[$([SX3]=O)]"),
            ("sulfone",              "[$([SX4](=[OX1])(=[OX1]))]"),
            # Phosphorus
            ("phosphate",            "[PX4](=[OX1])([OX2])([OX2])[OX2]"),
            ("phosphonic acid",      "[PX4](=[OX1])([OX2H])([OX2H])"),
            # Boron
            ("boronic acid",         "[BX3]([OX2H])[OX2H]"),
            ("boronate ester",       "[BX3]([OX2])[OX2]"),
            # Heterocycles (aromatic)
            ("pyridine",             "c1ccncc1"),
            ("pyrimidine",           "c1cnccn1"),
            ("pyrazine",             "c1cnccn1"),
            ("imidazole",            "c1cnc[nH]1"),
            ("pyrazole",             "c1cc[nH]n1"),
            ("triazole",             "c1cn[nH]n1"),
            ("tetrazole",            "c1nnn[nH]1"),
            ("oxazole",              "c1cocn1"),
            ("thiazole",             "c1cscn1"),
            ("indole",               "c1ccc2[nH]ccc2c1"),
            ("benzimidazole",        "c1cnc2ccccc2n1"),
            ("quinoline",            "c1ccc2ncccc2c1"),
            ("isoquinoline",         "c1ccc2cnccc2c1"),
            ("piperidine",           "[NH]1CCCCC1"),
            ("piperazine",           "N1CCNCC1"),
            ("morpholine",           "O1CCNCC1"),
            ("pyrrolidine",          "[NH]1CCCC1"),
            ("azetidine",            "[NH]1CCC1"),
            # Protected amines
            ("Boc-protected amine",  "[NX3][CX3](=[OX1])OC(C)(C)C"),
            ("Cbz-protected amine",  "[NX3][CX3](=[OX1])OCc1ccccc1"),
            ("Fmoc-protected amine", "[NX3][CX3](=[OX1])OCC1c2ccccc2-c2ccccc21"),
        ]

        # Remove any broken SMARTS (the sulfone pattern has a typo guard)
        valid_fg_patterns: List[tuple] = []
        for fg_name, fg_smarts in _FG_SMARTS:
            try:
                from rdkit.Chem import MolFromSmarts
                patt = MolFromSmarts(fg_smarts)
                if patt is not None:
                    valid_fg_patterns.append((fg_name, patt))
            except Exception:
                pass

        # Detect functional groups
        functional_groups: List[str] = []
        for fg_name, patt in valid_fg_patterns:
            if in_mol.HasSubstructMatch(patt):
                functional_groups.append(fg_name)

        # Get canonical IUPAC name from ChemScript
        canonical_name = _smiles_to_name_cs(input_smiles) or ""

        # Get decomposition (alternatives + bracket tree)
        alternative_names: List[str] = []
        bracket_tree_str: Optional[str] = None
        try:
            from cdxml_toolkit.naming.name_decomposer import decompose_name
            decomp = decompose_name(input_smiles)
            if decomp.alternatives:
                alternative_names = [a.name for a in decomp.alternatives
                                     if a.valid and a.name]
            if decomp.bracket_tree is not None:
                bracket_tree_str = decomp.canonical_name
            if not canonical_name and decomp.canonical_name:
                canonical_name = decomp.canonical_name
        except Exception:
            pass

        # Get prefix form (substituent name)
        prefix_form: Optional[str] = None
        try:
            pfx_result = get_prefix_form(canonical_name or input_smiles)
            if pfx_result.get("ok"):
                prefix_form = pfx_result["prefix"]
        except Exception:
            pass

        formula = _compute_formula(input_smiles)
        mw_val = _compute_mw(input_smiles)

        return {
            "ok": True,
            "input_smiles": input_smiles,
            "canonical_name": canonical_name,
            "alternative_names": alternative_names,
            "functional_groups": functional_groups,
            "prefix_form": prefix_form,
            "bracket_tree": bracket_tree_str,
            "formula": formula,
            "mw": mw_val,
        }

    elif operation == "set_name":
        # ---- Set name: resolve a new IUPAC name to SMILES, validate, diff ----
        new_name = kwargs.get("new_name", "")
        if not new_name:
            return {"ok": False, "error": "'new_name' is required for set_name."}

        # Try to resolve the name to SMILES
        output_smiles = _try_validate(new_name, use_network=True)
        if not output_smiles:
            # Also try resolve_to_smiles in case it's a common name
            r = resolve_to_smiles(new_name, use_network=True)
            if r.get("ok"):
                output_smiles = r["smiles"]

        if not output_smiles:
            return {
                "ok": False,
                "error": f"Could not resolve name '{new_name}' to a valid structure.",
                "input_smiles": input_smiles,
            }
        out_mol = Chem.MolFromSmiles(output_smiles)
        if out_mol is None:
            return {
                "ok": False,
                "error": f"Name '{new_name}' resolved but SMILES is invalid.",
                "input_smiles": input_smiles,
            }
        output_smiles = Chem.MolToSmiles(out_mol)

    else:
        return {
            "ok": False,
            "error": (f"Unknown operation '{operation}'. "
                      "Use 'analyze', 'name_surgery', 'smarts', "
                      "'set_smiles', 'set_name', or 'reaction'."),
        }

    # ---- Build output ----
    input_name = (mol_json.get("iupac_name")
                  or mol_json.get("name")
                  or _smiles_to_name_cs(input_smiles)
                  or "")
    output_name = _smiles_to_name_cs(output_smiles) or ""

    aligned_names = _build_aligned_names(input_smiles, output_smiles)
    diff = _build_mol_diff(input_smiles, output_smiles)

    formula = _compute_formula(output_smiles)
    mw_out = _compute_mw(output_smiles)

    result = {
        "ok": True,
        "input_smiles": input_smiles,
        "output_smiles": output_smiles,
        "input_name": input_name,
        "output_name": output_name,
        "aligned_names": aligned_names,
        "diff": diff,
        "formula": formula,
        "mw": mw_out,
    }
    if alternative_products:
        result["alternative_products"] = alternative_products
    return result


# ---------------------------------------------------------------------------
# Tool definitions for LLM function calling
# ---------------------------------------------------------------------------

def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return tool schemas suitable for LLM function calling (Claude/OpenAI).

    Each tool definition follows the Anthropic tool-use format::

        {"name": "...", "description": "...", "input_schema": {...}}

    The LLM orchestrator should register these as available tools and
    call the corresponding Python functions based on the LLM's output.

    Returns:
        List of tool definition dicts.
    """
    return [
        {
            "name": "resolve_compound",
            "description": (
                "Resolve a chemical identifier to a rich molecule descriptor "
                "with SMILES, molecular formula, MW, exact mass, IUPAC name, "
                "reagent role, display text, and IUPAC substituent prefix form.  "
                "This is the preferred resolver — use it whenever you need more "
                "than just SMILES.\n\n"
                "Accepts common names, IUPAC names, abbreviations, condensed "
                "formulae, and CAS numbers.  Resolution order:\n"
                "  1. Curated reagent DB (~186 entries with roles)\n"
                "  2. Generative condensed formula parser (offline)\n"
                "  3. ChemScript IUPAC name engine (offline)\n"
                "  4. PubChem API (online, if use_network=True)\n\n"
                "Output fields include:\n"
                "  - smiles, formula, mw, exact_mass, iupac_name, source\n"
                "  - role, display_text (from curated reagent DB if known)\n"
                "  - prefix_form: IUPAC substituent prefix for use in "
                "assemble_name (e.g. 'trifluoromethyl' for CF3, 'morpholino' "
                "for morpholine); null if not a substituent group.\n\n"
                "Examples of valid queries:\n"
                '  - Common names: "aspirin", "morpholine", "HATU"\n'
                '  - Abbreviations: "Cs2CO3", "DIPEA", "Et3N"\n'
                '  - IUPAC names: "2-chloropyridine"\n'
                '  - Formulae: "PhB(OH)2", "CF3COOH"\n'
                '  - CAS numbers: "534-17-8"\n'
                '  - Drug names: "deucravacitinib"\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Chemical identifier to resolve.",
                    },
                    "use_network": {
                        "type": "boolean",
                        "description": (
                            "Allow PubChem lookup (default: true). "
                            "Set false for offline-only resolution."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "resolve_to_smiles",
            "description": (
                "Resolve a chemical identifier (name, abbreviation, formula, "
                "or CAS number) to a canonical SMILES string.  Use this when "
                "you need only the SMILES; for richer output (formula, MW, "
                "exact mass, role) use resolve_compound instead.\n\n"
                "Examples of valid queries:\n"
                '  - Common names: "aspirin", "morpholine", "HATU"\n'
                '  - IUPAC names: "2-chloropyridine", "4-methylbenzoic acid"\n'
                '  - Formulae: "PhB(OH)2", "Et3N", "CF3COOH"\n'
                '  - CAS numbers: "534-17-8"\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Chemical identifier to resolve.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_prefix_form",
            "description": (
                "Get the IUPAC substituent prefix form for a chemical group "
                "so it can be used in assemble_name.  Returns the prefix "
                "string (e.g. 'trifluoromethyl' for 'CF3', 'morpholino' for "
                "'morpholine').\n\n"
                "Use this when you know what group to attach but need its "
                "correct IUPAC prefix name.\n\n"
                "Examples:\n"
                '  - "CF3" -> "trifluoromethyl"\n'
                '  - "NO2" -> "nitro"\n'
                '  - "OMe" -> "methoxy"\n'
                '  - "morpholine" -> "morpholino"\n'
                '  - "cyclopropane" -> "cyclopropyl"\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "description": (
                            "Group to look up: abbreviation ('CF3', 'OMe'), "
                            "name ('morpholine'), or formula ('CHF2')."
                        ),
                    },
                },
                "required": ["group"],
            },
        },
        {
            "name": "assemble_name",
            "description": (
                "Build an IUPAC name from a parent ring/chain and a list of "
                "substituents.  Handles alphabetical ordering and multiplying "
                "prefixes (di-, tri-) automatically.  Validates the assembled "
                "name by resolving it to a structure.\n\n"
                "Example:\n"
                "  parent: 'pyridine'\n"
                "  substituents: [\n"
                '    {"locant": "2", "prefix": "chloro"},\n'
                '    {"locant": "5", "prefix": "trifluoromethyl"}\n'
                "  ]\n"
                "  -> '2-chloro-5-(trifluoromethyl)pyridine'\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "parent": {
                        "type": "string",
                        "description": (
                            "Parent ring or chain name "
                            "(e.g. 'pyridine', 'benzene', 'pentane')."
                        ),
                    },
                    "substituents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "locant": {
                                    "type": "string",
                                    "description": "Position number (e.g. '2', '3').",
                                },
                                "prefix": {
                                    "type": "string",
                                    "description": (
                                        "IUPAC prefix (e.g. 'chloro', 'methyl'). "
                                        "Use get_prefix_form first if unsure."
                                    ),
                                },
                            },
                            "required": ["locant", "prefix"],
                        },
                        "description": "List of substituents with positions.",
                    },
                },
                "required": ["parent", "substituents"],
            },
        },
        {
            "name": "modify_name",
            "description": (
                "Modify an existing IUPAC name by swapping, adding, or "
                "removing a substituent.  The name is re-alphabetised and "
                "validated automatically.\n\n"
                "Operations:\n"
                "  - 'swap': Replace target prefix with replacement.\n"
                "    Example: swap 'nitro' -> 'amino' in '4-nitropyridine'\n"
                "  - 'add': Insert replacement prefix at locant.\n"
                "    Example: add 'methyl' at '3' to '2-chloropyridine'\n"
                "  - 'remove': Delete the target prefix.\n"
                "    Example: remove 'chloro' from '2-chloro-3-methylpyridine'\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The IUPAC name to modify.",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["swap", "add", "remove"],
                        "description": "Type of modification.",
                    },
                    "target": {
                        "type": "string",
                        "description": "Prefix to replace (swap) or remove (remove).",
                    },
                    "replacement": {
                        "type": "string",
                        "description": "New prefix (swap) or prefix to insert (add).",
                    },
                    "locant": {
                        "type": "string",
                        "description": "Position for insertion (add only).",
                    },
                },
                "required": ["name", "operation"],
            },
        },
        {
            "name": "validate_name",
            "description": (
                "Check whether an IUPAC name is valid by attempting to "
                "resolve it to a molecular structure.  Returns the canonical "
                "SMILES if valid.  Use this to verify names before generating "
                "structures.\n\n"
                "Example:\n"
                '  "2-chloro-3-(trifluoromethyl)pyridine" -> valid, SMILES\n'
                '  "2-chloro-99-methylpyridine" -> invalid\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "IUPAC name to validate.",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "name_to_structure",
            "description": (
                "Convert a validated chemical name to a structure file "
                "(CDXML for ChemDraw, or SMILES/MOL).  This is the final "
                "step: call this after assembling and validating the name.\n\n"
                "Output formats:\n"
                '  - "cdxml": ChemDraw XML (requires ChemScript)\n'
                '  - "smiles": canonical SMILES string\n'
                '  - "mol": MDL MOL block with 2D coordinates\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Chemical name to convert.",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["cdxml", "smiles", "mol"],
                        "description": "Output format (default: cdxml).",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "enumerate_names",
            "description": (
                "List alternative IUPAC name forms for a molecule.  "
                "Given a name or SMILES, returns the canonical name plus "
                "alternative forms that express the same molecule using "
                "different parent rings/chains and substituent prefixes.\n\n"
                "IMPORTANT: Call this BEFORE modify_name when doing name "
                "surgery on functional groups that appear as suffixes in "
                "the canonical name (ketones '-one', alcohols '-ol', "
                "amines '-amine', acids '-oic acid', etc.).  The "
                "alternatives expose these groups as swappable prefixes.\n\n"
                "Example:\n"
                "  '1-(4-bromophenyl)ethan-1-one'  (ketone as suffix)\n"
                "  -> alternatives include '1-acetyl-4-bromobenzene'\n"
                "     where the ketone is now the prefix 'acetyl'\n"
                "  -> you can then swap 'acetyl' for another prefix\n\n"
                "Each name form includes a 'prefixes' list showing "
                "which substituent prefixes are visible and swappable.\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": (
                            "Chemical name, SMILES, abbreviation, or any "
                            "identifier.  Will be resolved to a structure."
                        ),
                    },
                },
                "required": ["identifier"],
            },
        },
        # --- Layer 3: Graph manipulation tools ---
        {
            "name": "list_reactions",
            "description": (
                "List available named reaction templates.  Returns the "
                "name, description, number of reactants, and typical "
                "conditions for each reaction.  Call this to find the "
                "right template before using apply_reaction.\n\n"
                "Categories:\n"
                "  - 'coupling': Suzuki, Buchwald, SNAr, amide, "
                "Sonogashira, Heck, N-alkylation\n"
                "  - 'functional_group': nitro reduction, ester hydrolysis, "
                "alcohol oxidation, reductive amination, Grignard\n"
                "  - 'heterocycle_formation': ~60 ring-forming reactions "
                "including Huisgen triazole, Fischer indole, Paal-Knorr "
                "pyrrole, Hantzsch pyridine/thiazole, benzimidazole, "
                "benzoxazole, Pictet-Spengler, Biginelli, and many more\n\n"
                "Use the optional category filter to narrow results.\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "coupling",
                            "functional_group",
                            "heterocycle_formation",
                        ],
                        "description": (
                            "Optional: filter by category. "
                            "Omit to list all reactions."
                        ),
                    },
                },
                "required": [],
            },
        },
        {
            "name": "apply_reaction",
            "description": (
                "Apply a named reaction template to a substrate molecule.  "
                "For two-component reactions (e.g. Suzuki, Buchwald), "
                "provide both substrate and reagent SMILES.  For single-"
                "component reactions (e.g. nitro reduction), only the "
                "substrate is needed.\n\n"
                "This tool covers ~70 reactions including:\n"
                "  - Classic couplings (Suzuki, Buchwald, Heck, etc.)\n"
                "  - Functional group transforms (reductions, oxidations)\n"
                "  - Ring-forming heterocyclic reactions (Fischer indole, "
                "Huisgen triazole, Paal-Knorr pyrrole, Hantzsch thiazole, "
                "benzimidazole synthesis, Pictet-Spengler, etc.)\n\n"
                "Use list_reactions() to find the right template name.\n\n"
                "The substrate and reagent can be SMILES strings or "
                "chemical names/abbreviations (they will be resolved "
                "automatically).\n\n"
                "Returns the product SMILES, IUPAC name, and suggested "
                "reaction conditions.\n\n"
                "Examples:\n"
                '  - apply_reaction("nitro_reduction", '
                '"c1ccc([N+](=O)[O-])cc1")\n'
                '  - apply_reaction("suzuki_coupling", '
                '"c1ccc(Br)cc1", "c1ccc(B(O)O)cc1")\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "reaction_name": {
                        "type": "string",
                        "description": (
                            "Reaction template name from list_reactions "
                            "(e.g. 'suzuki_coupling', 'nitro_reduction')."
                        ),
                    },
                    "substrate": {
                        "type": "string",
                        "description": (
                            "SMILES or name of the main substrate."
                        ),
                    },
                    "reagent": {
                        "type": "string",
                        "description": (
                            "SMILES or name of the coupling partner "
                            "(for 2-reactant reactions only)."
                        ),
                    },
                },
                "required": ["reaction_name", "substrate"],
            },
        },
        {
            "name": "deprotect",
            "description": (
                "Remove common protecting groups from a molecule.  "
                "Uses 25 built-in deprotection templates covering:\n"
                "  Boc, Fmoc, Cbz (amines)\n"
                "  TBS/TBDMS, THP, Bn, Ac, PMB, TMS (alcohols)\n"
                "  Acetal/Ketal (carbonyls)\n\n"
                "Accepts SMILES or a chemical name.  Returns the "
                "deprotected product and which PGs were removed.\n\n"
                "Example:\n"
                '  deprotect("O=C(OC(C)(C)C)Nc1ccccc1")  # Boc-aniline\n'
                '  -> product: aniline, removed: [Boc]\n'
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "smiles": {
                        "type": "string",
                        "description": (
                            "SMILES or chemical name of the "
                            "protected molecule."
                        ),
                    },
                },
                "required": ["smiles"],
            },
        },
        # --- Reaction JSON summary ---
        {
            "name": "reaction_summary",
            "description": (
                "Load a reaction JSON file and return a slim summary "
                "with only the fields you need.  Use this instead of "
                "reading the full JSON, which contains bulky geometry "
                "and mass data.\n\n"
                "Default fields (per species): id, name, role, "
                "role_detail, smiles, display_text, formula, mw.\n"
                "Default top-level: experiment, conditions.\n"
                "Default eln_data: product_yield, reaction_type.\n\n"
                "Request additional fields by name when needed:\n"
                "  - LCMS: add species fields ['exact_mass', 'adducts']\n"
                "  - Procedure: add species fields ['csv_mass', "
                "'csv_equiv', 'csv_volume'] and eln fields "
                "['procedure_plain', 'product_obtained', 'sm_mass']\n"
                "  - Scheme drawing: defaults are sufficient\n"
                "  - Pass ['*'] to any field list for all fields.\n\n"
                "Available species fields:\n"
                "  id, name, role, role_detail, smiles, smiles_neutral, "
                "classification_method, is_sm, is_dp, is_substrate, "
                "is_solvent, exact_mass, exact_mass_full, mw, formula, "
                "adducts, source, source_id, csv_equiv, csv_mass, "
                "csv_name, csv_volume, csv_supplier, display_text, "
                "original_geometry\n\n"
                "Available top-level fields:\n"
                "  version, experiment, input_files, reaction_smiles, "
                "reaction_class, reaction_name, "
                "classification_confidence, warnings, metadata, "
                "conditions\n\n"
                "Available eln_data fields:\n"
                "  sm_mass, product_obtained, product_yield, "
                "procedure_text, procedure_plain, reaction_type, "
                "start_date, labbook_name, solvents, solvent_details\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "json_path": {
                        "type": "string",
                        "description": "Path to the reaction JSON file.",
                    },
                    "species_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Per-species fields to include. Omit for "
                            "defaults. Pass ['*'] for all fields."
                        ),
                    },
                    "top_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Top-level fields to include. Omit for "
                            "defaults. Pass ['*'] for all fields."
                        ),
                    },
                    "eln_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "eln_data sub-fields to include. Omit for "
                            "defaults. Pass ['*'] for all. Pass [] to "
                            "omit eln_data entirely."
                        ),
                    },
                },
                "required": ["json_path"],
            },
        },
        # --- Single-molecule rendering ---
        {
            "name": "draw_molecule",
            "description": (
                "Render a single molecule structure to a standalone CDXML "
                "document (no arrow, no reaction scheme).  The output opens "
                "directly in ChemDraw and uses ACS Document 1996 style.\n\n"
                "Input is a dict with at minimum a 'smiles' field.  "
                "An optional label (compound name or custom text) is placed "
                "below the structure.  Use the 'output_path' argument to "
                "write the CDXML to a file as well.\n\n"
                "Label priority: 'label' > 'name' > 'iupac_name'.\n\n"
                "Examples:\n"
                "  draw_molecule({'smiles': 'CC(=O)Oc1ccccc1C(=O)O', "
                "'name': 'aspirin'})\n"
                "  draw_molecule({'smiles': 'c1ccccc1'}, "
                "output_path='benzene.cdxml')\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "mol_json": {
                        "type": "object",
                        "description": (
                            "Molecule dict.  Required key: 'smiles'. "
                            "Optional display keys: 'label', 'name', "
                            "'iupac_name'."
                        ),
                        "properties": {
                            "smiles": {
                                "type": "string",
                                "description": "SMILES string of the molecule.",
                            },
                            "label": {
                                "type": "string",
                                "description": "Custom label shown below the structure.",
                            },
                            "name": {
                                "type": "string",
                                "description": "Compound name (used as label if 'label' not set).",
                            },
                            "iupac_name": {
                                "type": "string",
                                "description": "IUPAC name (used as label if 'name' not set).",
                            },
                        },
                        "required": ["smiles"],
                    },
                    "output_path": {
                        "type": "string",
                        "description": (
                            "Optional file path to write the CDXML to "
                            "(e.g. 'molecule.cdxml').  The CDXML string is "
                            "always returned in the response regardless."
                        ),
                    },
                },
                "required": ["mol_json"],
            },
        },
        # --- Molecular editor ---
        {
            "name": "modify_molecule",
            "description": (
                "Modify a molecule and verify the change with a structural "
                "diff.  This is the premier tool for editing chemical "
                "structures with verification — like drawing in ChemDraw "
                "and visually checking the result.\n\n"
                "Input is a mol_json dict (with at minimum a 'smiles' key, "
                "e.g. from resolve_compound).  The tool applies the "
                "requested operation, validates the result with RDKit, "
                "and returns the output molecule with:\n\n"
                "  - aligned_names: side-by-side IUPAC name comparison "
                "(so you can see what changed in words)\n"
                "  - diff.atoms_changed: MCS-based fragment diff "
                "(so you can see what atoms were added/removed/replaced)\n"
                "  - diff.delta_formula / diff.delta_mw: formula and MW "
                "change numbers for sanity-checking\n\n"
                "Six operation modes:\n\n"
                "  'analyze' — DOES NOT modify the molecule.  Returns "
                "a rich description: functional groups present, alternative "
                "IUPAC names from different perspectives, canonical name, "
                "bracket tree (hierarchical name decomposition), substituent "
                "prefix form, formula, and MW.  Call this FIRST when you "
                "need to understand a molecule before deciding what surgery "
                "to do.\n\n"
                "  'set_smiles' — LLM provides the new SMILES directly.  "
                "Tool validates it and computes the diff.  Use when you "
                "already know the exact SMILES.\n\n"
                "  'set_name' — LLM provides an IUPAC or common name for "
                "the desired product.  Tool resolves to SMILES and computes "
                "the diff.  Use when you know the target molecule by name.\n\n"
                "  'smarts' — apply a SMARTS reaction transform.  "
                "Provide either a 'smarts' reaction SMARTS string "
                "(e.g. '[c:1][F]>>[c:1][Cl]') or a 'reaction_name' from "
                "list_reactions().  Good for specific bond transformations.\n\n"
                "  'reaction' — apply a named reaction template via "
                "apply_reaction().  Provide 'reaction_name' (required) and "
                "optionally 'reagent' dict (with 'smiles' key) for binary "
                "reactions.  Returns the primary product with the standard "
                "diff fields; additional products go in 'alternative_products'."
                "  Use list_reactions() to find available template names.\n\n"
                "  'name_surgery' — modify via IUPAC name manipulation.  "
                "Requires ChemScript.  Provide 'add' "
                "(list of {locant, prefix} dicts) and/or 'remove' "
                "(list of prefix strings).  Best for simple substituent "
                "swaps on drug-like molecules.\n\n"
                "Examples:\n"
                "  # CD3 → benzyl swap\n"
                "  modify_molecule({'smiles': '...'}, 'smarts',\n"
                "    smarts='[C:1]([2H])([2H])[2H]>>[C:1]Cc1ccccc1')\n\n"
                "  # Add fluoro at C3\n"
                "  modify_molecule({'smiles': 'Clc1ccncc1'}, 'name_surgery',\n"
                "    add=[{'locant': '3', 'prefix': 'fluoro'}])\n\n"
                "  # Set explicit SMILES\n"
                "  modify_molecule({'smiles': 'Clc1ccncc1'}, 'set_smiles',\n"
                "    new_smiles='Clc1cc(F)ncc1', "
                "description='fluoro at C3')\n"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "mol_json": {
                        "type": "object",
                        "description": (
                            "Source molecule dict.  Required key: 'smiles'. "
                            "Optional: 'name', 'iupac_name' (used as "
                            "starting point for name_surgery)."
                        ),
                        "properties": {
                            "smiles": {
                                "type": "string",
                                "description": "SMILES of the molecule to modify.",
                            },
                            "name": {
                                "type": "string",
                                "description": "Common name (optional).",
                            },
                            "iupac_name": {
                                "type": "string",
                                "description": (
                                    "IUPAC name (used as starting point for "
                                    "name_surgery if provided)."
                                ),
                            },
                        },
                        "required": ["smiles"],
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["analyze", "name_surgery", "smarts", "set_smiles", "set_name", "reaction"],
                        "description": (
                            "Operation to apply.  Use 'analyze' to inspect a "
                            "molecule without modifying it; use 'name_surgery', "
                            "'smarts', 'set_smiles', 'set_name', or 'reaction' to edit it."
                        ),
                    },
                    "new_smiles": {
                        "type": "string",
                        "description": (
                            "[set_smiles only] The new SMILES string. "
                            "Will be validated with RDKit."
                        ),
                    },
                    "new_name": {
                        "type": "string",
                        "description": (
                            "[set_name only] An IUPAC or common name for "
                            "the desired product. Will be resolved to "
                            "SMILES and validated."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "[set_smiles/set_name] Optional description of "
                            "the change (for logging/context)."
                        ),
                    },
                    "smarts": {
                        "type": "string",
                        "description": (
                            "[smarts only] Reaction SMARTS string. "
                            "Use atom-map numbers for bond-order-preserving "
                            "transforms, e.g. '[c:1][F]>>[c:1][Cl]'."
                        ),
                    },
                    "reaction_name": {
                        "type": "string",
                        "description": (
                            "[smarts, reaction] Named reaction from list_reactions(). "
                            "For 'smarts': used as the SMARTS transform (alternative to "
                            "providing 'smarts' directly). "
                            "For 'reaction': required — selects the reaction template "
                            "to apply via apply_reaction()."
                        ),
                    },
                    "reagent": {
                        "type": "object",
                        "description": (
                            "[reaction only] The coupling partner for binary reactions "
                            "(e.g. amide_coupling, suzuki_coupling). "
                            "Must contain at minimum a 'smiles' key."
                        ),
                        "properties": {
                            "smiles": {
                                "type": "string",
                                "description": "SMILES of the reagent/coupling partner.",
                            },
                        },
                        "required": ["smiles"],
                    },
                    "add": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "locant": {
                                    "type": "string",
                                    "description": "Position number (e.g. '3').",
                                },
                                "prefix": {
                                    "type": "string",
                                    "description": "IUPAC prefix (e.g. 'fluoro', 'methyl').",
                                },
                            },
                            "required": ["locant", "prefix"],
                        },
                        "description": (
                            "[name_surgery only] Substituents to add. "
                            "Each entry needs 'locant' and 'prefix'."
                        ),
                    },
                    "remove": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "[name_surgery only] List of IUPAC prefix "
                            "strings to remove (e.g. ['chloro', 'methyl'])."
                        ),
                    },
                },
                "required": ["mol_json", "operation"],
            },
        },
    ]
