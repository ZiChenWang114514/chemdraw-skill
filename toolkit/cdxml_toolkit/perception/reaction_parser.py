#!/usr/bin/env python3
"""
reaction_parser.py — Unified reaction semantic layer.

Parses ELN export files (any combination of CDX, CDXML, RXN, CSV) into a
single persisted JSON descriptor listing every chemical species with:
  - Canonical SMILES (full + neutral/salt-split)
  - Role classification (atom_contributing / non_contributing / product)
  - Display name (SM, DP, curated abbreviation, CSV name, or formula)
  - Mass data (exact mass, MW, ESI adducts)

The JSON output serves as the single source of truth for downstream tools
(procedure_writer, scheme_merger, flower_predictor, etc.).

CLI:
    python reaction_parser.py experiment.cdxml -o reaction.json
    python reaction_parser.py experiment.cdxml --csv exp.csv --pretty
    python reaction_parser.py --input-dir path/ --experiment KL-7001-004

Python API:
    from cdxml_toolkit.perception.reaction_parser import parse_reaction, ReactionDescriptor
    desc = parse_reaction(cdxml="scheme.cdxml", csv="exp.csv")
    desc.to_json("reaction.json")
"""

import argparse
import json
import os
import re
import sys
import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from ..constants import MW_MATCH_TOLERANCE, MASS_TOLERANCE

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
_verbose = False


def _log(msg: str) -> None:
    if _verbose:
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SpeciesDescriptor:
    """A single chemical species in the reaction."""
    id: str = ""                            # "sp_0", "sp_1", ...
    smiles: Optional[str] = None            # canonical, full (salts together)
    smiles_neutral: Optional[str] = None    # largest fragment (for LCMS)
    name: str = ""                          # display name
    role: str = ""                          # atom_contributing | non_contributing | product
    role_detail: Optional[str] = None       # from reagent_db: base, catalyst, ...
    rxn_insight_role: Optional[str] = None  # from RXN Insight
    classification_method: str = ""         # role_lookup, rxnmapper, mcs, csv_type, ...
    is_sm: bool = False
    is_dp: bool = False
    exact_mass: float = 0.0                 # monoisotopic, neutral
    exact_mass_full: float = 0.0            # monoisotopic, full salt
    mw: float = 0.0                         # average MW
    formula: Optional[str] = None
    adducts: Dict[str, float] = field(default_factory=dict)
    source: str = ""                        # fragment, text_label, csv_only, rxn
    source_id: Optional[str] = None         # CDXML element id
    csv_equiv: Optional[str] = None
    csv_mass: Optional[str] = None
    csv_name: Optional[str] = None
    csv_volume: Optional[str] = None
    csv_supplier: Optional[str] = None
    # v1.1 fields — ELN enrichment
    is_substrate: bool = False              # True = equiv 1.0 in CSV (for scheme layout)
    is_solvent: bool = False                # From CSV SOLVENT section or reagent_db role
    display_text: Optional[str] = None      # Formatted text for scheme: "Cs2CO3 (2 eq.)"
    # v1.2 fields — original CDXML geometry preservation
    original_geometry: Optional[Dict[str, Any]] = field(default=None)
    # Structure of original_geometry:
    # {
    #   "atoms": [
    #     {"id": 42, "x": 100.0, "y": 200.0, "symbol": "C"},
    #     {"id": 43, "x": 114.4, "y": 207.2, "symbol": "N", "num_hydrogens": 1},
    #     {"id": 44, "x": 128.8, "y": 200.0, "is_abbreviation": True,
    #      "label": "OTs", "label_smiles": "O[S](=O)(C1=CC=C(C)C=C1)=O",
    #      "is_generic": False},
    #     {"id": 45, "x": 140.0, "y": 210.0, "is_generic": True,
    #      "label": "R", "node_type": "GenericNickname"},
    #   ],
    #   "bonds": [
    #     {"begin": 42, "end": 43, "order": 1},
    #     {"begin": 43, "end": 44, "order": 1, "double_position": "Left"},
    #   ],
    #   "bond_length": 14.4,  # average bond length in CDXML points
    # }

    def to_dict(self) -> dict:
        d = asdict(self)
        # Drop None values for cleaner JSON
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ReactionDescriptor:
    """Complete parsed reaction description."""
    version: str = "1.3"
    experiment: str = ""
    input_files: Dict[str, Optional[str]] = field(default_factory=dict)
    reaction_smiles: Optional[str] = None
    reaction_class: Optional[str] = None
    reaction_name: Optional[str] = None
    classification_confidence: Optional[float] = None
    species: List[SpeciesDescriptor] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # v1.1 fields — scheme layout and ELN enrichment
    conditions: List[str] = field(default_factory=list)       # ["80 °C", "24 h", "N2"]
    eln_data: Optional[Dict[str, Any]] = field(default=None)  # run arrow data + procedure

    def to_dict(self) -> dict:
        d = {
            "version": self.version,
            "experiment": self.experiment,
            "input_files": self.input_files,
            "reaction_smiles": self.reaction_smiles,
            "reaction_class": self.reaction_class,
            "reaction_name": self.reaction_name,
            "classification_confidence": self.classification_confidence,
            "species": [sp.to_dict() for sp in self.species],
            "warnings": self.warnings,
            "metadata": self.metadata,
            "conditions": self.conditions,
            "eln_data": self.eln_data,
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ReactionDescriptor":
        species_raw = d.get("species", [])
        species = []
        for sp_d in species_raw:
            sp = SpeciesDescriptor(**{k: v for k, v in sp_d.items()
                                     if k in SpeciesDescriptor.__dataclass_fields__})
            species.append(sp)
        return cls(
            version=d.get("version", "1.0"),
            experiment=d.get("experiment", ""),
            input_files=d.get("input_files", {}),
            reaction_smiles=d.get("reaction_smiles"),
            reaction_class=d.get("reaction_class"),
            reaction_name=d.get("reaction_name"),
            classification_confidence=d.get("classification_confidence"),
            species=species,
            warnings=d.get("warnings", []),
            metadata=d.get("metadata", {}),
            conditions=d.get("conditions", []),
            eln_data=d.get("eln_data"),
        )

    def to_json(self, path: str, pretty: bool = True) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2 if pretty else None,
                      ensure_ascii=False)

    @classmethod
    def from_json(cls, path: str) -> "ReactionDescriptor":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def get_sm(self) -> Optional[SpeciesDescriptor]:
        """Return the starting material species, or None."""
        for sp in self.species:
            if sp.is_sm:
                return sp
        return None

    def get_dp(self) -> Optional[SpeciesDescriptor]:
        """Return the desired product species, or None."""
        for sp in self.species:
            if sp.is_dp:
                return sp
        return None

    def get_expected_species(self) -> List[dict]:
        """Return ExpectedSpecies-compatible dicts for LCMS matching."""
        result = []
        for sp in self.species:
            if sp.exact_mass > 0 and sp.smiles:
                result.append({
                    "name": sp.name,
                    "role": _lcms_role(sp),
                    "exact_mass": sp.exact_mass,
                    "smiles": sp.smiles_neutral or sp.smiles,
                    "adducts": dict(sp.adducts),
                })
        return result

    # -- Default field sets for summary() ------------------------------------
    DEFAULT_SPECIES_FIELDS = [
        "id", "name", "role", "role_detail", "smiles",
        "display_text", "formula", "mw",
    ]
    DEFAULT_TOP_FIELDS = [
        "experiment", "conditions",
    ]
    DEFAULT_ELN_FIELDS = [
        "product_yield", "reaction_type",
    ]
    ALL_SPECIES_FIELDS = [
        f.name for f in SpeciesDescriptor.__dataclass_fields__.values()
    ]
    ALL_TOP_FIELDS = [
        "version", "experiment", "input_files", "reaction_smiles",
        "reaction_class", "reaction_name", "classification_confidence",
        "warnings", "metadata", "conditions",
    ]
    ALL_ELN_FIELDS = [
        "sm_mass", "product_obtained", "product_yield", "procedure_text",
        "procedure_plain", "reaction_type", "start_date", "labbook_name",
        "solvents", "solvent_details",
    ]

    def summary(
        self,
        species_fields: Optional[List[str]] = None,
        top_fields: Optional[List[str]] = None,
        eln_fields: Optional[List[str]] = None,
    ) -> dict:
        """Return a slim summary dict for LLM context.

        Parameters
        ----------
        species_fields : list of str, optional
            Per-species fields to include.  ``None`` → DEFAULT_SPECIES_FIELDS.
            Pass ``["*"]`` for all fields.
        top_fields : list of str, optional
            Top-level reaction fields to include.  ``None`` → DEFAULT_TOP_FIELDS.
            Pass ``["*"]`` for all fields.
        eln_fields : list of str, optional
            ``eln_data`` sub-fields to include.  ``None`` → DEFAULT_ELN_FIELDS.
            Pass ``["*"]`` for all eln_data fields.  Pass ``[]`` to omit eln_data.

        Returns
        -------
        dict
            A filtered copy of the reaction descriptor.
        """
        sp_keys = (self.ALL_SPECIES_FIELDS if species_fields == ["*"]
                   else (species_fields or self.DEFAULT_SPECIES_FIELDS))
        t_keys = (self.ALL_TOP_FIELDS if top_fields == ["*"]
                  else (top_fields or self.DEFAULT_TOP_FIELDS))
        e_keys = (self.ALL_ELN_FIELDS if eln_fields == ["*"]
                  else (eln_fields if eln_fields is not None
                        else self.DEFAULT_ELN_FIELDS))

        # Top-level fields
        full = self.to_dict()
        out: Dict[str, Any] = {}
        for k in t_keys:
            if k in full:
                out[k] = full[k]

        # Species
        species_out = []
        for sp in self.species:
            sp_d = sp.to_dict()
            species_out.append({k: sp_d[k] for k in sp_keys if k in sp_d})
        out["species"] = species_out

        # ELN data
        if e_keys and self.eln_data:
            eln_out = {k: self.eln_data[k] for k in e_keys
                       if k in self.eln_data}
            if eln_out:
                out["eln_data"] = eln_out

        return out


def reaction_summary(
    json_path: str,
    species_fields: Optional[List[str]] = None,
    top_fields: Optional[List[str]] = None,
    eln_fields: Optional[List[str]] = None,
) -> dict:
    """Load a reaction JSON and return a slim summary for LLM context.

    Convenience wrapper around ``ReactionDescriptor.from_json().summary()``.
    See :meth:`ReactionDescriptor.summary` for parameter docs.

    Available species fields
    ------------------------
    id, name, role, role_detail, smiles, smiles_neutral, classification_method,
    is_sm, is_dp, is_substrate, is_solvent, exact_mass, exact_mass_full, mw,
    formula, adducts, source, source_id, csv_equiv, csv_mass, csv_name,
    csv_volume, csv_supplier, display_text, original_geometry

    Available top-level fields
    --------------------------
    version, experiment, input_files, reaction_smiles, reaction_class,
    reaction_name, classification_confidence, warnings, metadata, conditions

    Available eln_data fields
    -------------------------
    sm_mass, product_obtained, product_yield, procedure_text, procedure_plain,
    reaction_type, start_date, labbook_name, solvents, solvent_details
    """
    desc = ReactionDescriptor.from_json(json_path)
    return desc.summary(
        species_fields=species_fields,
        top_fields=top_fields,
        eln_fields=eln_fields,
    )


def _lcms_role(sp: SpeciesDescriptor) -> str:
    """Map SpeciesDescriptor role to ExpectedSpecies role string."""
    if sp.is_sm:
        return "substrate"
    if sp.is_dp:
        return "product"
    if sp.role == "product":
        return "product"
    return "reactant"


# ---------------------------------------------------------------------------
# Condition text splitting
# ---------------------------------------------------------------------------

# Patterns that identify non-chemical condition tokens
_CONDITION_PATTERNS = [
    re.compile(r"^-?\d+\.?\d*\s+.{0,2}C.*$"),             # temperature: "80 °C", "105 C", encoding issues
    re.compile(r"^-?\d+\.?\d*\s*[°\u00b0\ufffd].*$"),     # temperature: "80°C", degree prefix
    re.compile(r"^r\.?t\.?$", re.IGNORECASE),       # room temperature
    re.compile(r"^reflux$", re.IGNORECASE),
    re.compile(r"^refl\.?$", re.IGNORECASE),
    re.compile(r"^\d+\.?\d*\s*(h|hr|hrs|min|d|days?)$", re.IGNORECASE),  # time
    re.compile(r"^\d+\.?\d*\s*mol\s*%$", re.IGNORECASE),   # catalyst loading
    re.compile(r"^overnight$", re.IGNORECASE),
    re.compile(r"^o\.?n\.?$", re.IGNORECASE),
    re.compile(r"^\d+\.?\d*\s*bar$", re.IGNORECASE),       # pressure
    re.compile(r"^N[2\u2082]\s*(atm)?$"),                   # N2 atmosphere
    re.compile(r"^Ar\s*(atm)?$"),                           # argon atmosphere
    re.compile(r"^MW$", re.IGNORECASE),                     # microwave
    re.compile(r"^sealed\s+tube$", re.IGNORECASE),
    re.compile(r"^-?\d+\s+to\s+-?\d+", re.IGNORECASE),     # temp range: "-78 to RT", "0 to 25"
    re.compile(r"^-?\d+\s*(?:°|[\u00b0\ufffd])?\s*(?:C\s+)?to\s+(?:RT|r\.?t\.?|-?\d+)", re.IGNORECASE),
    re.compile(r"^\d+\.?\d*\s*equiv?\.?$", re.IGNORECASE),  # equivalents
    re.compile(r"^\d+\.?\d*\s*eq\.?$", re.IGNORECASE),
    re.compile(r"^\d+\s*M$"),                               # molarity: "2 M"
    re.compile(r"^\d+\.?\d*\s*mL$", re.IGNORECASE),         # volume
    re.compile(r"^then$", re.IGNORECASE),
]


def _is_condition_token(token: str) -> bool:
    """Return True if token is a reaction condition, not a chemical name."""
    return any(p.match(token) for p in _CONDITION_PATTERNS)


def split_condition_text(text: str) -> List[str]:
    """Split a merged condition text block into individual chemical tokens.

    Handles merged ``<t>`` blocks where reagent names are separated by
    newlines and/or commas.  Filters out non-chemical tokens (temperature,
    time, "rt", "reflux", etc.).

    Returns a list of chemical name strings.
    """
    from ..resolve.reagent_db import get_reagent_db
    db = get_reagent_db()

    # Split on newlines first (scheme_polisher merges with \n)
    lines = text.split("\n")
    tokens: List[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Strip trailing equiv annotations: "Cs2CO3 (2 eq.)" → "Cs2CO3"
        line = re.sub(r"\s*\(\d+\.?\d*\s*eq\.?\)\s*$", "", line,
                      flags=re.IGNORECASE)

        # If the entire line (before comma-split) is a known reagent, keep it
        if db.entry_for_name(line.strip().lower()):
            tokens.append(line.strip())
            continue

        # Split on comma/semicolon, but protect names like "1,4-dioxane"
        # Strategy: try splitting, and if any resulting segment is a known
        # chemical, use the split; otherwise keep the line intact.
        parts = re.split(r"[;,]\s*", line)
        if len(parts) == 1:
            # No delimiter found
            token = parts[0].strip()
            if token and not _is_condition_token(token):
                tokens.append(token)
        else:
            # Multiple parts — filter each
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if _is_condition_token(part):
                    continue
                tokens.append(part)

    return tokens


def extract_conditions_from_text(text: str) -> List[str]:
    """Extract condition tokens (temperature, time, atmosphere) from text.

    Inverse of ``split_condition_text`` — returns ONLY the non-chemical
    tokens that represent reaction conditions.
    """
    conditions: List[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip trailing equiv annotations before splitting
        line = re.sub(r"\s*\(\d+\.?\d*\s*eq\.?\)\s*$", "", line,
                      flags=re.IGNORECASE)
        parts = re.split(r"[;,]\s*", line)
        for part in parts:
            part = part.strip()
            if part and _is_condition_token(part):
                conditions.append(part)
    return conditions


# ---------------------------------------------------------------------------
# Text label → SMILES resolution
# ---------------------------------------------------------------------------

def _resolve_text_label(text: str,
                        use_network: bool = True) -> Optional[str]:
    """Resolve a text label to canonical SMILES.

    Resolution chain (first success wins):
      1. reagent_db name → SMILES  (curated dictionary)
      2. condensed formula parser  (generative, offline)
      3. OPSIN                     (offline, IUPAC/systematic names)
      4. PubChem                   (online, if *use_network*)

    Returns canonical SMILES or None.
    """
    from ..resolve.reagent_db import get_reagent_db
    db = get_reagent_db()

    # Normalize: strip equiv annotations, whitespace
    clean = re.sub(r"\s*\(\d+\.?\d*\s*eq\.?\)\s*$", "", text,
                   flags=re.IGNORECASE).strip()

    # 1. Reagent DB name → SMILES
    entry = db.entry_for_name(clean.lower())
    if entry:
        smi = entry.get("smiles")
        if smi:
            # May be a list of SMILES variants — take the first
            if isinstance(smi, list):
                smi = smi[0]
            # Try to canonicalize
            try:
                from rdkit import Chem
                mol = Chem.MolFromSmiles(smi)
                if mol:
                    return Chem.MolToSmiles(mol)
            except ImportError:
                pass
            return smi

    # 2. Condensed formula parser (generative, offline)
    try:
        from ..resolve.condensed_formula import resolve_condensed_formula
        smi = resolve_condensed_formula(clean)
        if smi:
            return smi
    except (ImportError, Exception):
        pass

    # 3. OPSIN (offline)
    try:
        from .reactant_heuristic import _opsin_name_to_smiles
        smi = _opsin_name_to_smiles(clean)
        if smi:
            return smi
    except (ImportError, Exception):
        pass

    # 4. PubChem (online)
    if use_network:
        try:
            from ..resolve.cas_resolver import resolve_name_to_smiles
            smi = resolve_name_to_smiles(clean)
            if smi:
                return smi
        except (ImportError, Exception):
            pass

    return None


# ---------------------------------------------------------------------------
# Arrow detection and side assignment (does NOT use <step> attributes)
# ---------------------------------------------------------------------------

def _find_arrow(page: ET.Element) -> Optional[ET.Element]:
    """Find the main reaction arrow on the page.

    Looks for ``<arrow>`` elements first, then ``<graphic>`` elements with
    arrow-type attributes.  Returns the first found, or None.
    """
    # Direct <arrow> elements
    for el in page:
        if el.tag == "arrow":
            return el

    # <graphic> with arrow attributes (ChemDraw CDXML variant)
    for el in page:
        if el.tag == "graphic":
            if el.get("GraphicType") == "Line" and el.get("ArrowType"):
                return el
            # SupersededBy linkage
            if el.get("SupersededBy"):
                continue

    return None


def _arrow_endpoints(arrow: ET.Element) -> Tuple[float, float, float, float]:
    """Return (tail_x, tail_y, head_x, head_y) from an arrow element."""
    from ..cdxml_utils import arrow_endpoints
    return arrow_endpoints(arrow)


def _fragment_centroid(frag: ET.Element) -> Tuple[float, float]:
    """Compute centroid from direct-child atom positions."""
    xs, ys = [], []
    for n in frag.findall("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
    if xs:
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return 0.0, 0.0


def _text_anchor(t_elem: ET.Element) -> Tuple[float, float]:
    """Get approximate position of a text element."""
    p = t_elem.get("p")
    if p:
        parts = p.split()
        return float(parts[0]), float(parts[1])
    bb = t_elem.get("BoundingBox")
    if bb:
        vals = [float(v) for v in bb.split()]
        return (vals[0] + vals[2]) / 2, (vals[1] + vals[3]) / 2
    return 0.0, 0.0


def _extract_geometry(frag_elem) -> Optional[Dict[str, Any]]:
    """Extract original CDXML geometry from a <fragment> element.

    Returns a dict with atoms, bonds, and average bond length that can be
    stored in ``SpeciesDescriptor.original_geometry``.  Abbreviation groups
    (``NodeType="Fragment"``) and generic groups (``GenericNickname``, etc.)
    are flagged with their label text so downstream tools can re-abbreviate.
    """
    _GENERIC_NODETYPES = {"GenericNickname", "Nickname", "Unspecified"}

    atoms = []
    id_set = set()
    for n in frag_elem.findall("n"):
        nid_str = n.get("id")
        if nid_str is None:
            continue
        nid = int(nid_str)
        node_type = n.get("NodeType")
        if node_type == "ExternalConnectionPoint":
            continue

        p = n.get("p", "0 0").split()
        x, y = float(p[0]), float(p[1])
        elem = int(n.get("Element", "6"))
        sym = _ELEM_SYMBOLS.get(elem, "C")
        num_h_attr = n.get("NumHydrogens")

        atom_d: Dict[str, Any] = {"id": nid, "x": x, "y": y, "symbol": sym}
        if num_h_attr is not None:
            atom_d["num_hydrogens"] = int(num_h_attr)

        # Abbreviation groups (real superatom abbreviations)
        if node_type == "Fragment":
            # Get label text
            label = None
            for t in n.findall("t"):
                parts = []
                for s in t.findall("s"):
                    if s.text:
                        parts.append(s.text)
                if parts:
                    label = "".join(parts)
                    break
            atom_d["is_abbreviation"] = True
            atom_d["is_generic"] = False
            if label:
                atom_d["label"] = label
                # Look up the SMILES for this abbreviation
                try:
                    from ..resolve.superatom_table import lookup_smiles
                    lsmi = lookup_smiles(label)
                    if lsmi:
                        atom_d["label_smiles"] = lsmi
                except ImportError:
                    pass

        # Generic variable groups (R, X, Ar, R1, etc.)
        elif node_type in _GENERIC_NODETYPES:
            label = None
            # Try GenericNickname attribute first
            label = n.get("GenericNickname")
            if not label:
                for t in n.findall("t"):
                    parts = []
                    for s in t.findall("s"):
                        if s.text:
                            parts.append(s.text)
                    if parts:
                        label = "".join(parts)
                        break
            atom_d["is_abbreviation"] = False
            atom_d["is_generic"] = True
            atom_d["node_type"] = node_type
            if label:
                atom_d["label"] = label

        atoms.append(atom_d)
        id_set.add(nid)

    bonds = []
    bond_lengths = []
    atom_pos = {a["id"]: (a["x"], a["y"]) for a in atoms}
    for b in frag_elem.findall("b"):
        bi, ei = int(b.get("B", "0")), int(b.get("E", "0"))
        if bi not in id_set or ei not in id_set:
            continue
        order = int(b.get("Order", "1"))
        bond_d: Dict[str, Any] = {"begin": bi, "end": ei, "order": order}
        dp = b.get("DoublePosition")
        if dp:
            bond_d["double_position"] = dp
        bonds.append(bond_d)
        # Compute bond length for average
        if bi in atom_pos and ei in atom_pos:
            dx = atom_pos[bi][0] - atom_pos[ei][0]
            dy = atom_pos[bi][1] - atom_pos[ei][1]
            bl = (dx * dx + dy * dy) ** 0.5
            if bl > 0:
                bond_lengths.append(bl)

    if not atoms:
        return None

    result: Dict[str, Any] = {"atoms": atoms, "bonds": bonds}
    if bond_lengths:
        result["bond_length"] = round(sum(bond_lengths) / len(bond_lengths), 2)
    return result


# Element number → symbol mapping for _extract_geometry
_ELEM_SYMBOLS = {
    1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F",
    14: "Si", 15: "P", 16: "S", 17: "Cl", 35: "Br", 53: "I",
    3: "Li", 11: "Na", 12: "Mg", 19: "K", 20: "Ca", 26: "Fe",
    29: "Cu", 30: "Zn", 46: "Pd", 55: "Cs", 78: "Pt",
}


def _get_text_content(t_elem: ET.Element) -> str:
    """Extract plain text content from a <t> element."""
    parts = []
    for s in t_elem.iter("s"):
        if s.text:
            parts.append(s.text)
    return "".join(parts).strip()


# ---------------------------------------------------------------------------
# CDXML extraction (fragments + text labels)
# ---------------------------------------------------------------------------

def _extract_from_cdxml(cdxml_path: str,
                        use_network: bool = True,
                        ) -> Tuple[List[SpeciesDescriptor], List[str], List[str]]:
    """Extract species from a CDXML scheme.

    Returns (species_list, warnings, conditions).
    Determines product vs reactant by position relative to the arrow,
    NOT from ``<step>`` attributes.  Conditions are non-chemical tokens
    (temperatures, times, atmospheres) from text labels near the arrow.
    """
    from ..cdxml_utils import parse_cdxml

    tree = parse_cdxml(cdxml_path)
    root = tree.getroot()
    page = root.find(".//page")
    if page is None:
        return [], ["No <page> element found in CDXML"], []

    # Find the arrow
    arrow = _find_arrow(page)
    if arrow is None:
        return [], ["No reaction arrow found in CDXML"], []

    tail_x, tail_y, head_x, head_y = _arrow_endpoints(arrow)
    # Ensure tail is left of head
    if tail_x > head_x:
        tail_x, head_x = head_x, tail_x
        tail_y, head_y = head_y, tail_y

    arrow_y = (tail_y + head_y) / 2.0
    _log(f"  Arrow: tail=({tail_x:.1f}, {tail_y:.1f}), "
         f"head=({head_x:.1f}, {head_y:.1f})")

    # Collect the arrow element id (and any graphic superseding it)
    arrow_ids = set()
    aid = arrow.get("id")
    if aid:
        arrow_ids.add(aid)
    # Also find graphic SupersededBy this arrow
    for el in page:
        if el.tag == "graphic" and el.get("SupersededBy") == aid:
            gid = el.get("id")
            if gid:
                arrow_ids.add(gid)

    species = []
    warnings = []
    sp_idx = 0

    # Try to import frag_to_smiles (prefer resolved version for abbreviations)
    _frag_to_smiles_resolved = None
    _frag_to_smiles_plain = None
    try:
        from ..rdkit_utils import frag_to_smiles_resolved as _frag_to_smiles_resolved
        from ..rdkit_utils import frag_to_smiles as _frag_to_smiles_plain
        from ..rdkit_utils import frag_to_mw as _frag_to_mw
    except ImportError:
        _frag_to_mw = None

    # Process all fragments
    for el in page:
        if el.tag != "fragment":
            continue

        eid = el.get("id", "")
        if eid in arrow_ids:
            continue

        cx, cy = _fragment_centroid(el)

        # Determine role by position relative to arrow
        if cx > head_x:
            pos_role = "product"
        else:
            pos_role = "candidate"  # reactant or reagent — classified later

        # Extract SMILES — prefer resolved (abbreviation-expanded) version
        smi = None
        if _frag_to_smiles_resolved is not None:
            smi = _frag_to_smiles_resolved(el)

        # Fallback to plain SMILES (may have [*] for abbreviations)
        if smi is None and _frag_to_smiles_plain is not None:
            smi = _frag_to_smiles_plain(el)

        # If still has unresolved abbreviations, try ChemScript
        if smi is not None and '*' in smi:
            cs_smi = _try_chemscript_smiles(el, cdxml_path)
            if cs_smi and '*' not in cs_smi:
                smi = cs_smi

        if smi is None:
            # Try ChemScript fallback for total failures
            smi = _try_chemscript_smiles(el, cdxml_path)

        mw = 0.0
        if _frag_to_mw is not None:
            mw_val = _frag_to_mw(el)
            if mw_val is not None:
                mw = mw_val

        # Extract original geometry (coordinates + abbreviation data)
        geom = _extract_geometry(el)

        sp = SpeciesDescriptor(
            id=f"sp_{sp_idx}",
            smiles=smi,
            name="",
            role=pos_role,
            source="fragment",
            source_id=eid,
            mw=mw,
            original_geometry=geom,
        )
        species.append(sp)
        sp_idx += 1
        _log(f"  Fragment id={eid}: smiles={smi}, pos_role={pos_role}, mw={mw:.1f}")

    # Process text labels (may contain reagent names and condition tokens)
    cdxml_conditions: List[str] = []

    for el in page:
        if el.tag != "t":
            continue

        eid = el.get("id", "")
        if eid in arrow_ids:
            continue

        text = _get_text_content(el)
        if not text:
            continue

        tx, ty = _text_anchor(el)

        # Skip text to the right of the arrow (product labels)
        if tx > head_x:
            continue

        # Extract condition tokens from this text block
        conds = extract_conditions_from_text(text)
        cdxml_conditions.extend(conds)

        # Split merged condition text into individual chemical tokens
        tokens = split_condition_text(text)
        if not tokens:
            continue

        for token in tokens:
            smi = _resolve_text_label(token, use_network=use_network)

            sp = SpeciesDescriptor(
                id=f"sp_{sp_idx}",
                smiles=smi,
                name=token,  # provisional — may be overwritten by display names
                role="candidate",
                source="text_label",
                source_id=eid,
            )
            species.append(sp)
            sp_idx += 1
            _log(f"  Text id={eid}: token='{token}', smiles={smi}")

    return species, warnings, cdxml_conditions


def _try_chemscript_smiles(frag_elem: ET.Element,
                           cdxml_path: str) -> Optional[str]:
    """Try to extract SMILES from a fragment via ChemScript.

    Wraps the fragment in a minimal CDXML, writes to temp file,
    and calls ChemScript to export SMILES.
    """
    try:
        from ..chemdraw.chemscript_bridge import ChemScriptBridge
        from ..constants import CDXML_MINIMAL_HEADER, CDXML_FOOTER
    except ImportError:
        return None

    import tempfile

    # Build minimal CDXML containing just this fragment
    frag_xml = ET.tostring(frag_elem, encoding="unicode")
    cdxml_str = f"{CDXML_MINIMAL_HEADER}<page>{frag_xml}</page>{CDXML_FOOTER}"

    try:
        with tempfile.NamedTemporaryFile(suffix=".cdxml", delete=False,
                                         mode="w", encoding="utf-8") as f:
            f.write(cdxml_str)
            tmp_path = f.name
        try:
            cs = ChemScriptBridge()
            smi = cs.write_data(tmp_path, "smiles")
            return smi.strip() if smi else None
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception:
        return None


# ---------------------------------------------------------------------------
# RXN file extraction
# ---------------------------------------------------------------------------

def _extract_from_rxn(rxn_path: str) -> Tuple[List[SpeciesDescriptor], List[str]]:
    """Extract species from an RXN file.

    Tier 1: ChemScript ``load_reaction()`` → SMILES for each component.
    Tier 2: RDKit ``ReactionFromRxnFile()`` → MOL templates → SMILES.

    .. warning::
        Neither tier handles V2000 S-group superatom abbreviations
        (``M  STY ... SUP`` / ``M  SMT ... label``).  Findmolecule RXN
        exports commonly use these for groups like COOH, COOtBu, etc.
        The placeholder atom is read as bare C, producing an incorrect
        SMILES.  **Best practice:** parse CDX (via ChemDraw COM) + CSV
        together; RXN is a supplementary source only.

    Returns (species_list, warnings).
    """
    species = []
    warnings = []

    # Tier 1: ChemScript
    try:
        from ..chemdraw.chemscript_bridge import ChemScriptBridge
        cs = ChemScriptBridge()
        result = cs.load_reaction(rxn_path)
        if result and result.get("ok"):
            sp_idx = 0
            for rct in result.get("reactants", []):
                sp = SpeciesDescriptor(
                    id=f"sp_{sp_idx}",
                    smiles=rct.get("smiles"),
                    name=rct.get("name", ""),
                    role="candidate",
                    source="rxn",
                    formula=rct.get("formula"),
                )
                species.append(sp)
                sp_idx += 1
            for prod in result.get("products", []):
                sp = SpeciesDescriptor(
                    id=f"sp_{sp_idx}",
                    smiles=prod.get("smiles"),
                    name=prod.get("name", ""),
                    role="product",
                    source="rxn",
                    formula=prod.get("formula"),
                )
                species.append(sp)
                sp_idx += 1
            _log(f"  RXN via ChemScript: {len(species)} species")
            return species, warnings
    except Exception as e:
        _log(f"  ChemScript RXN load failed: {e}")

    # Tier 2: RDKit
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem

        rxn = AllChem.ReactionFromRxnFile(rxn_path)
        if rxn is None:
            warnings.append(f"RDKit could not parse RXN file: {rxn_path}")
            return [], warnings

        sp_idx = 0
        for i in range(rxn.GetNumReactantTemplates()):
            mol = rxn.GetReactantTemplate(i)
            if mol is None or mol.GetNumAtoms() == 0:
                continue
            try:
                Chem.SanitizeMol(mol)
            except Exception:
                pass
            smi = Chem.MolToSmiles(mol) if mol else None
            sp = SpeciesDescriptor(
                id=f"sp_{sp_idx}",
                smiles=smi,
                role="candidate",
                source="rxn",
            )
            species.append(sp)
            sp_idx += 1

        for i in range(rxn.GetNumProductTemplates()):
            mol = rxn.GetProductTemplate(i)
            if mol is None or mol.GetNumAtoms() == 0:
                continue
            try:
                Chem.SanitizeMol(mol)
            except Exception:
                pass
            smi = Chem.MolToSmiles(mol) if mol else None
            sp = SpeciesDescriptor(
                id=f"sp_{sp_idx}",
                smiles=smi,
                role="product",
                source="rxn",
            )
            species.append(sp)
            sp_idx += 1

        _log(f"  RXN via RDKit: {len(species)} species")
    except ImportError:
        warnings.append("Neither ChemScript nor RDKit available for RXN parsing")
    except Exception as e:
        warnings.append(f"RXN parsing failed: {e}")

    return species, warnings


# ---------------------------------------------------------------------------
# CSV matching
# ---------------------------------------------------------------------------

def _match_csv_data(species: List[SpeciesDescriptor],
                    csv_path: str) -> Tuple[List[SpeciesDescriptor], List[str], Any]:
    """Match CSV reagent data to species by MW or name.

    Supplements species with CSV metadata (equiv, mass, name, substrate flag).
    Species not matched to any structural source are added as csv_only.

    Returns (updated_species, warnings, exp_data).
    """
    warnings = []

    try:
        from .eln_csv_parser import parse_eln_csv
    except ImportError:
        warnings.append("eln_csv_parser not available for CSV parsing")
        return species, warnings, None

    exp_data = parse_eln_csv(csv_path)
    if exp_data is None:
        warnings.append(f"Could not parse CSV: {csv_path}")
        return species, warnings, None

    from ..resolve.reagent_db import get_reagent_db
    db = get_reagent_db()

    # Build match tracking
    matched_species = set()     # species indices already matched
    matched_csv = set()         # CSV reagent indices already matched

    # --- Pass 1: Name match ---
    for ci, rgt in enumerate(exp_data.reactants):
        if ci in matched_csv:
            continue
        csv_name_lower = rgt.name.strip().lower()
        csv_display = db.resolve_display(rgt.name)

        for si, sp in enumerate(species):
            if si in matched_species:
                continue
            if sp.role == "product":
                continue

            # Compare against text label name
            sp_name_lower = (sp.name or "").strip().lower()
            sp_display_lower = db.resolve_display(sp.name or "").lower()

            if (sp_name_lower and (sp_name_lower == csv_name_lower
                                   or sp_display_lower == csv_display.lower())):
                _apply_csv_match(sp, rgt)
                matched_species.add(si)
                matched_csv.add(ci)
                _log(f"  CSV name match: '{rgt.name}' → sp_{si}")
                break

    # --- Pass 2: MW match (species with known MW) ---
    for ci, rgt in enumerate(exp_data.reactants):
        if ci in matched_csv:
            continue
        if rgt.mw <= 0:
            continue

        best_si = None
        best_delta = MW_MATCH_TOLERANCE

        for si, sp in enumerate(species):
            if si in matched_species:
                continue
            if sp.role == "product":
                continue
            if sp.mw <= 0:
                continue

            delta = abs(sp.mw - rgt.mw)
            if delta < best_delta:
                best_delta = delta
                best_si = si

        if best_si is not None:
            _apply_csv_match(species[best_si], rgt)
            matched_species.add(best_si)
            matched_csv.add(ci)
            _log(f"  CSV MW match: '{rgt.name}' (MW={rgt.mw:.1f}) "
                 f"→ sp_{best_si} (MW={species[best_si].mw:.1f})")

    # --- Pass 3: MW match via SMILES from reagent_db ---
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors
        has_rdkit = True
    except ImportError:
        has_rdkit = False

    if has_rdkit:
        for ci, rgt in enumerate(exp_data.reactants):
            if ci in matched_csv:
                continue
            if rgt.mw <= 0:
                continue

            for si, sp in enumerate(species):
                if si in matched_species:
                    continue
                if sp.role == "product":
                    continue
                if sp.smiles or sp.mw > 0:
                    continue  # already has structural data

                # Try to get SMILES from reagent_db for this text label
                sp_name = (sp.name or "").strip()
                if not sp_name:
                    continue
                entry = db.entry_for_name(sp_name.lower())
                if not entry:
                    continue
                smi = entry.get("smiles")
                if not smi:
                    continue
                if isinstance(smi, list):
                    smi = smi[0]

                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    continue
                text_mw = Descriptors.MolWt(mol)
                delta = abs(text_mw - rgt.mw)
                if delta < MW_MATCH_TOLERANCE:
                    sp.smiles = Chem.MolToSmiles(mol)
                    sp.mw = text_mw
                    _apply_csv_match(sp, rgt)
                    matched_species.add(si)
                    matched_csv.add(ci)
                    _log(f"  CSV MW→DB match: '{rgt.name}' → sp_{si} "
                         f"via DB SMILES '{sp_name}'")
                    break

    # --- Add unmatched CSV reagents as csv_only species ---
    sp_idx = max((int(sp.id.split("_")[1]) for sp in species), default=-1) + 1
    for ci, rgt in enumerate(exp_data.reactants):
        if ci in matched_csv:
            continue
        sp = SpeciesDescriptor(
            id=f"sp_{sp_idx}",
            name=rgt.name,
            role="candidate",
            source="csv_only",
            mw=rgt.mw,
            csv_name=rgt.name,
            csv_equiv=rgt.equiv,
            csv_mass=rgt.mass,
        )
        # Try to resolve SMILES from name
        smi = _resolve_text_label(rgt.name, use_network=False)
        if smi:
            sp.smiles = smi
        if rgt.is_substrate:
            sp.is_sm = True
        species.append(sp)
        sp_idx += 1
        _log(f"  CSV-only species: '{rgt.name}' (MW={rgt.mw:.1f})")

    # --- Match product to CSV ---
    if exp_data.product and exp_data.product.mw > 0:
        for sp in species:
            if sp.role != "product":
                continue
            if sp.mw > 0:
                delta = abs(sp.mw - exp_data.product.mw)
                if delta < MW_MATCH_TOLERANCE:
                    sp.csv_name = exp_data.product.name
                    sp.is_dp = True
                    _log(f"  Product CSV match: '{exp_data.product.name}'")
                    break

    return species, warnings, exp_data


def _apply_csv_match(sp: SpeciesDescriptor, rgt) -> None:
    """Apply CSV reagent data to a species descriptor."""
    sp.csv_name = rgt.name
    sp.csv_equiv = rgt.equiv
    sp.csv_mass = rgt.mass
    if hasattr(rgt, "volume") and rgt.volume:
        sp.csv_volume = rgt.volume
    if hasattr(rgt, "supplier") and rgt.supplier:
        sp.csv_supplier = rgt.supplier
    if hasattr(rgt, "is_substrate") and rgt.is_substrate:
        sp.is_sm = True  # Mark from CSV substrate flag
        sp.is_substrate = True


# ---------------------------------------------------------------------------
# Species classification
# ---------------------------------------------------------------------------

def _classify_species(species: List[SpeciesDescriptor],
                      use_rxnmapper: bool = True,
                      use_rxn_insight: bool = True,
                      ) -> Optional[float]:
    """Classify non-product species using the tiered pipeline.

    Returns Schneider FP score (if classification ran), or None.
    use_rxnmapper is deprecated and ignored (kept for API compat).
    """
    from .reactant_heuristic import (
        ReagentInfo, classify_reagents, role_lookup,
    )

    # Find product SMILES (needed for classification)
    product_smiles = None
    for sp in species:
        if sp.role == "product" and sp.smiles:
            product_smiles = sp.smiles
            break

    if not product_smiles:
        _log("  WARNING: No product SMILES found, cannot classify reagents")
        return None

    # Build ReagentInfo list for the classification pipeline
    reagents = []
    sp_to_ri = {}  # map species index → ReagentInfo index
    for i, sp in enumerate(species):
        if sp.role == "product":
            continue
        if sp.role == "candidate":
            ri = ReagentInfo(
                source_id=sp.source_id or sp.id,
                source_type=sp.source,
                name=sp.name or None,
                smiles=sp.smiles,
                position="reactant",
                classification="",
                classification_method="",
            )
            sp_to_ri[i] = len(reagents)
            reagents.append(ri)

    if not reagents:
        return None

    # Run 2-tier classification (Schneider FP → DB enrichment)
    classify_reagents(reagents, product_smiles)

    # Apply results back to species
    schneider_score = None
    for sp_i, ri_i in sp_to_ri.items():
        ri = reagents[ri_i]
        sp = species[sp_i]
        sp.role = ri.classification or "unclassified"
        sp.classification_method = ri.classification_method
        sp.role_detail = ri.role
        if ri.schneider_score is not None and schneider_score is None:
            schneider_score = ri.schneider_score

    # --- Optional RXN Insight enrichment ---
    rxn_class = None
    rxn_name = None
    if use_rxn_insight:
        rxn_class, rxn_name = _try_rxn_insight(species, product_smiles)

    return schneider_score


def _try_rxn_insight(species: List[SpeciesDescriptor],
                     product_smiles: str,
                     ) -> Tuple[Optional[str], Optional[str]]:
    """Try RXN Insight enrichment for reaction class and per-species roles.

    Returns (reaction_class, reaction_name) or (None, None).
    """
    try:
        from experiments.role_classification.rxn_role_classifier import (
            classify_roles_enriched,
        )
    except ImportError:
        return None, None

    # Build full reaction SMILES: all reactant/reagent SMILES >> product
    lhs_parts = []
    for sp in species:
        if sp.role != "product" and sp.smiles:
            lhs_parts.append(sp.smiles)
    if not lhs_parts:
        return None, None

    rxn_smi = ".".join(lhs_parts) + ">>" + product_smiles

    try:
        result = classify_roles_enriched(rxn_smi)
    except Exception as e:
        _log(f"  RXN Insight failed: {e}")
        return None, None

    if not result:
        return None, None

    rxn_class = result.get("reaction_class")
    rxn_name = result.get("reaction_name")

    # Map per-component roles back to species
    try:
        from rdkit import Chem
        def _canon(smi):
            mol = Chem.MolFromSmiles(smi)
            return Chem.MolToSmiles(mol) if mol else smi
    except ImportError:
        def _canon(smi):
            return smi

    comp_map = {}
    for comp in result.get("components", []):
        canon = _canon(comp.get("smiles", ""))
        comp_map[canon] = comp.get("role")

    for sp in species:
        if sp.smiles and sp.role != "product":
            canon = _canon(sp.smiles)
            insight_role = comp_map.get(canon)
            if insight_role:
                sp.rxn_insight_role = insight_role

    _log(f"  RXN Insight: class={rxn_class}, name={rxn_name}")
    return rxn_class, rxn_name


# ---------------------------------------------------------------------------
# SM / DP identification and display names
# ---------------------------------------------------------------------------

def _identify_sm_dp(species: List[SpeciesDescriptor]) -> None:
    """Identify SM and DP, then apply display name precedence rules."""

    # --- DP: single product or largest product ---
    products = [sp for sp in species if sp.role == "product"]
    if len(products) == 1:
        products[0].is_dp = True
    elif len(products) > 1:
        # If one already matched CSV product, it stays DP
        dp_found = any(sp.is_dp for sp in products)
        if not dp_found:
            # Pick largest by MW
            best = max(products, key=lambda sp: sp.mw)
            best.is_dp = True

    # --- SM: CSV substrate flag → most contributing → largest ---
    # Priority 0: Check if CSV already marked a substrate
    csv_substrates = [sp for sp in species
                      if sp.is_sm and sp.role != "product"]
    if csv_substrates:
        # Pick largest MW among CSV substrates (handles multi-substrate)
        sm = max(csv_substrates, key=lambda sp: sp.mw)
        # Clear other substrate flags — only keep the primary SM
        for sp in csv_substrates:
            if sp is not sm:
                sp.is_sm = False
    else:
        # Priority 1: Largest atom_contributing non-solvent by MW
        atom_contributing = [sp for sp in species
                             if sp.role == "atom_contributing"
                             and not sp.is_solvent and sp.mw > 50]
        if atom_contributing:
            sm = max(atom_contributing, key=lambda sp: sp.mw)
            sm.is_sm = True
        else:
            # Priority 2: Largest non-product, non-solvent species by MW
            # Exclude counterions (MW < 50: HCl=36, HBr=81 — use 50 cutoff)
            fallback = [sp for sp in species
                        if sp.role != "product"
                        and not sp.is_solvent
                        and sp.mw > 50]
            if fallback:
                sm = max(fallback, key=lambda sp: sp.mw)
                sm.is_sm = True


def _apply_display_names(species: List[SpeciesDescriptor]) -> None:
    """Apply display name precedence rules to all species."""
    from ..resolve.reagent_db import get_reagent_db
    db = get_reagent_db()

    for sp in species:
        # SM / DP are identified by is_sm / is_dp flags — their display names
        # follow the same precedence as other species (no special "SM"/"DP"
        # override; compound labels are a layout-layer decision).

        # 1. Reagent DB display name from SMILES
        if sp.smiles:
            display = db.display_for_smiles(sp.smiles)
            if display:
                sp.name = display
                continue

        # 3. Reagent DB display name from name
        if sp.name:
            display = db.resolve_display(sp.name)
            if display and display.lower() != sp.name.lower():
                sp.name = display
                continue
            # Keep existing name if resolve_display just returns input
            if display:
                sp.name = display
                continue

        # 3b. Reagent DB display name from csv_name (abbreviation > full name)
        if sp.csv_name:
            display = db.display_for_name(sp.csv_name.lower())
            if display:
                sp.name = display
                continue

        # 4. CSV name
        if sp.csv_name:
            sp.name = sp.csv_name
            continue

        # 5. Molecular formula
        if sp.formula:
            sp.name = sp.formula
            continue

        # 6. SMILES as last resort
        if sp.smiles:
            sp.name = sp.smiles




def _detect_solvents(species: List[SpeciesDescriptor],
                     exp_data: Optional[Any] = None) -> None:
    """Mark solvent species from CSV SOLVENT section and reagent_db role."""
    from ..resolve.reagent_db import get_reagent_db
    db = get_reagent_db()

    # From reagent_db role_detail
    for sp in species:
        if sp.role_detail == "solvent":
            sp.is_solvent = True

    if exp_data is None:
        return

    # From CSV SOLVENT section — match by name to existing species
    csv_solvents = getattr(exp_data, "solvents", [])
    matched_solvent_names = set()

    for solv in csv_solvents:
        solv_name = solv.name.strip()
        if not solv_name:
            continue
        solv_lower = solv_name.lower()
        solv_display = db.resolve_display(solv_name).lower()

        for sp in species:
            sp_name_lower = (sp.name or "").strip().lower()
            sp_csv_lower = (sp.csv_name or "").strip().lower()
            sp_display_lower = db.resolve_display(sp.name or "").lower()
            sp_display_text_lower = (sp.display_text or "").strip().lower()
            candidates = {sp_name_lower, sp_csv_lower, sp_display_lower,
                          sp_display_text_lower} - {""}
            if candidates & {solv_lower, solv_display}:
                sp.is_solvent = True
                matched_solvent_names.add(solv_lower)
                break

    # Add unmatched solvents as csv_only species
    sp_idx = max((int(sp.id.split("_")[1]) for sp in species), default=-1) + 1
    for solv in csv_solvents:
        solv_name = solv.name.strip()
        if not solv_name or solv_name.lower() in matched_solvent_names:
            continue
        # Check if this is a known reagent
        smi = None
        entry = db.entry_for_name(solv_name.lower())
        if entry:
            smi_val = entry.get("smiles")
            if isinstance(smi_val, list):
                smi_val = smi_val[0] if smi_val else None
            smi = smi_val
        sp = SpeciesDescriptor(
            id=f"sp_{sp_idx}",
            name=solv_name,
            role="non_contributing",
            role_detail="solvent",
            source="csv_only",
            smiles=smi,
            is_solvent=True,
        )
        species.append(sp)
        sp_idx += 1
        matched_solvent_names.add(solv_lower)  # prevent duplicate csv_only entries
        _log(f"  CSV solvent added: '{solv_name}'")


def _format_equiv(equiv_str: str) -> str:
    """Format equivalents for display: '2.0' → '2', '0.05' → '0.05'."""
    if not equiv_str:
        return ""
    try:
        val = float(equiv_str)
        if val == int(val):
            return str(int(val))
        return equiv_str.strip()
    except (ValueError, TypeError):
        return equiv_str.strip()


def _build_display_texts(species: List[SpeciesDescriptor]) -> None:
    """Build display_text for each species (name + equiv annotation).

    display_text is what would appear on a rendered scheme:
      - Reagents with equiv > 1: "Cs2CO3 (2 eq.)"
      - Solvents: just the name (no equiv)
      - SM/DP substrates: just the name (equiv=1 suppressed)
    """
    for sp in species:
        base = sp.name or ""
        if not base:
            sp.display_text = None
            continue

        # Substrates and products: just the name
        if sp.is_substrate or sp.is_sm or sp.is_dp:
            sp.display_text = base
        elif sp.is_solvent:
            sp.display_text = base
        elif sp.csv_equiv:
            # Non-substrate species with equiv → "Name (X eq.)"
            equiv_str = _format_equiv(sp.csv_equiv)
            if equiv_str and equiv_str != "1":
                sp.display_text = f"{base} ({equiv_str} eq.)"
            else:
                sp.display_text = base
        else:
            sp.display_text = base


def _populate_eln_data(desc: "ReactionDescriptor",
                       exp_data: Optional[Any]) -> None:
    """Populate desc.eln_data from parsed CSV ExperimentData."""
    if exp_data is None:
        return

    eln = {}

    # SM mass from substrate species
    sm = desc.get_sm()
    if sm and sm.csv_mass:
        eln["sm_mass"] = sm.csv_mass.strip()

    # Product yield data
    product = getattr(exp_data, "product", None)
    if product:
        if hasattr(product, "obtained_mass") and product.obtained_mass:
            eln["product_obtained"] = product.obtained_mass.strip()
        if hasattr(product, "yield_pct") and product.yield_pct:
            eln["product_yield"] = product.yield_pct.strip()

    # Procedure text (HTML + plain text)
    procedure = getattr(exp_data, "procedure_html", "")
    if procedure:
        eln["procedure_text"] = procedure
    procedure_plain = getattr(exp_data, "procedure_text", "")
    if procedure_plain:
        eln["procedure_plain"] = procedure_plain

    # Experiment metadata
    reaction_type = getattr(exp_data, "reaction_type", "")
    if reaction_type:
        eln["reaction_type"] = reaction_type
    start_date = getattr(exp_data, "start_date", "")
    if start_date:
        eln["start_date"] = start_date
    labbook = getattr(exp_data, "labbook_name", "")
    if labbook:
        eln["labbook_name"] = labbook

    # Solvents list (names only, backward compat)
    solvents = getattr(exp_data, "solvents", [])
    if solvents:
        eln["solvents"] = [s.name.strip() for s in solvents if s.name.strip()]
        # Full solvent details with volume/concentration
        eln["solvent_details"] = [
            {
                "name": s.name.strip(),
                "volume": getattr(s, "volume", "").strip(),
                "concentration": getattr(s, "concentration", "").strip(),
            }
            for s in solvents if s.name.strip()
        ]

    if eln:
        desc.eln_data = eln


# ---------------------------------------------------------------------------
# Mass computation
# ---------------------------------------------------------------------------

def _compute_all_masses(species: List[SpeciesDescriptor]) -> None:
    """Compute exact masses, neutral masses, MW, formula, and adducts."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        has_rdkit = True
    except ImportError:
        has_rdkit = False

    for sp in species:
        if not sp.smiles or not has_rdkit:
            continue

        mol = Chem.MolFromSmiles(sp.smiles)
        if mol is None:
            continue

        # Full mass (including counterions)
        sp.exact_mass_full = Descriptors.ExactMolWt(mol)

        # Average MW (for CSV matching)
        if sp.mw <= 0:
            sp.mw = Descriptors.MolWt(mol)

        # Formula
        if not sp.formula:
            sp.formula = rdMolDescriptors.CalcMolFormula(mol)

        # Salt splitting: neutral = largest fragment
        frags = Chem.GetMolFrags(mol, asMols=True)
        if len(frags) > 1:
            neutral_mol = max(frags, key=lambda m: m.GetNumHeavyAtoms())
            sp.exact_mass = Descriptors.ExactMolWt(neutral_mol)
            sp.smiles_neutral = Chem.MolToSmiles(neutral_mol)
        else:
            sp.exact_mass = sp.exact_mass_full
            sp.smiles_neutral = sp.smiles

        # Adducts from neutral mass (for LCMS matching)
        # [M+H]+, [M-H]-, [M+Na]+, [M+formate]-
        sp.adducts = {
            "[M+H]+": sp.exact_mass + 1.00728,
            "[M-H]-": sp.exact_mass - 1.00728,
            "[M+Na]+": sp.exact_mass + 22.98922,
            "[M+formate]-": sp.exact_mass + 44.99820,
        }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _deduplicate_species(species: List[SpeciesDescriptor]) -> List[SpeciesDescriptor]:
    """Remove duplicate species by canonical SMILES.

    When duplicates exist, prefer the one with the most metadata
    (CSV match, fragment source, etc.).  SMILES are canonicalized via
    RDKit before comparison so that different representations of the
    same molecule (kekulized vs aromatic, different atom ordering) are
    recognized as duplicates.

    Species with no SMILES are merged into a SMILES-bearing entry by MW,
    but only when MW values are unambiguous (no two remaining species
    share the same MW within tolerance).
    """
    if not species:
        return species

    # --- Build canonicalizer ---
    try:
        from rdkit import Chem

        def _canon(smi: str) -> str:
            mol = Chem.MolFromSmiles(smi)
            return Chem.MolToSmiles(mol) if mol else smi
    except ImportError:
        def _canon(smi: str) -> str:
            return smi

    _ROLE_PRIO = {"product": 0, "atom_contributing": 1,
                  "non_contributing": 2, "candidate": 3,
                  "unclassified": 4}

    seen: Dict[str, int] = {}  # canonical SMILES → index in result
    result = []

    for sp in species:
        if not sp.smiles:
            result.append(sp)
            continue

        key = _canon(sp.smiles)
        # Also update the stored SMILES to canonical form
        sp.smiles = key

        if key in seen:
            _merge_into(result[seen[key]], sp, _ROLE_PRIO)
        else:
            seen[key] = len(result)
            result.append(sp)

    # --- MW-based merge for no-SMILES entries ---
    # Only when MW values are unambiguous: if two SMILES-bearing entries
    # have the same MW (within tolerance), skip MW-based merging entirely
    # to avoid wrong matches.
    try:
        from rdkit.Chem import Descriptors as _Desc
        from rdkit import Chem as _Chem
        _has_rdkit = True
    except ImportError:
        _has_rdkit = False

    merged_indices: set = set()
    if _has_rdkit:
        # Compute MW for all SMILES-bearing entries
        smiles_mws: List[Tuple[int, float]] = []  # (index, mw)
        for i, sp in enumerate(result):
            if not sp.smiles:
                continue
            mol = _Chem.MolFromSmiles(sp.smiles)
            if mol is not None:
                smiles_mws.append((i, _Desc.MolWt(mol)))

        # Check for ambiguous MWs (two entries within tolerance)
        mw_ambiguous = False
        for a_idx in range(len(smiles_mws)):
            for b_idx in range(a_idx + 1, len(smiles_mws)):
                if abs(smiles_mws[a_idx][1] - smiles_mws[b_idx][1]) < MW_MATCH_TOLERANCE:
                    mw_ambiguous = True
                    break
            if mw_ambiguous:
                break

        if not mw_ambiguous:
            for i, sp in enumerate(result):
                if sp.smiles:
                    continue
                sp_mw = sp.mw
                if not sp_mw:
                    continue
                best_delta = MW_MATCH_TOLERANCE
                best_idx = -1
                for j, mw_val in smiles_mws:
                    if j in merged_indices:
                        continue
                    delta = abs(mw_val - sp_mw)
                    if delta < best_delta:
                        best_delta = delta
                        best_idx = j
                if best_idx >= 0:
                    _merge_into(result[best_idx], sp, _ROLE_PRIO)
                    merged_indices.add(i)
                    _log(f"  Dedup MW-merge: {sp.name or sp.csv_name} → "
                         f"{result[best_idx].name or result[best_idx].csv_name} "
                         f"(delta={best_delta:.1f} Da)")
        elif any(not sp.smiles and sp.mw for sp in result):
            _log("  Dedup: skipping MW-merge (ambiguous MW among species)")

    if merged_indices:
        result = [sp for i, sp in enumerate(result) if i not in merged_indices]

    # Re-index
    for i, sp in enumerate(result):
        sp.id = f"sp_{i}"

    return result


def _merge_into(existing: "SpeciesDescriptor", incoming: "SpeciesDescriptor",
                role_prio: Dict[str, int]) -> None:
    """Merge *incoming* metadata into *existing*, mutating existing in place."""
    if not existing.csv_name and incoming.csv_name:
        existing.csv_name = incoming.csv_name
        existing.csv_equiv = incoming.csv_equiv
        existing.csv_mass = incoming.csv_mass
    if not existing.name and incoming.name:
        existing.name = incoming.name
    if incoming.is_sm:
        existing.is_sm = True
    if incoming.is_dp:
        existing.is_dp = True
    if incoming.is_substrate and not existing.is_substrate:
        existing.is_substrate = True
    if incoming.is_solvent and not existing.is_solvent:
        existing.is_solvent = True
    # Prefer non-empty role_detail
    if not existing.role_detail and incoming.role_detail:
        existing.role_detail = incoming.role_detail
    # Prefer source with more info: fragment > rxn > text_label > csv_only
    _SRC_PRIO = {"fragment": 0, "rxn": 1, "text_label": 2, "csv_only": 3}
    if _SRC_PRIO.get(incoming.source, 9) < _SRC_PRIO.get(existing.source, 9):
        existing.source = incoming.source
    # Keep higher role (product > atom_contributing > non_contributing)
    if role_prio.get(incoming.role, 5) < role_prio.get(existing.role, 5):
        existing.role = incoming.role
    # Prefer SMILES from the incoming entry if existing has none
    if not existing.smiles and incoming.smiles:
        existing.smiles = incoming.smiles
    # Merge MW
    if not existing.mw and incoming.mw:
        existing.mw = incoming.mw


# ---------------------------------------------------------------------------
# Build reaction SMILES
# ---------------------------------------------------------------------------

def _build_reaction_smiles(species: List[SpeciesDescriptor]) -> Optional[str]:
    """Build full reaction SMILES from species list."""
    lhs_parts = []
    rhs_parts = []

    for sp in species:
        if not sp.smiles:
            continue
        if sp.role == "product":
            rhs_parts.append(sp.smiles)
        else:
            lhs_parts.append(sp.smiles)

    if not rhs_parts or not lhs_parts:
        return None

    return ".".join(lhs_parts) + ">>" + ".".join(rhs_parts)


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def parse_reaction(
    cdxml: Optional[str] = None,
    cdx: Optional[str] = None,
    csv: Optional[str] = None,
    rxn: Optional[str] = None,
    input_dir: Optional[str] = None,
    experiment: Optional[str] = None,
    use_rxnmapper: bool = False,
    use_rxn_insight: bool = True,
    use_network: bool = True,
    verbose: bool = False,
) -> ReactionDescriptor:
    """Parse reaction from ELN files and return a ReactionDescriptor.

    Accepts any combination of input files.  Each contributes different
    information (see plan).

    Args:
        cdxml: Path to CDXML file (polished or raw)
        cdx: Path to CDX file (converted to CDXML internally)
        csv: Path to Findmolecule ELN CSV
        rxn: Path to RXN file
        input_dir: Directory to auto-discover files from
        experiment: Experiment name (with input_dir)
        use_rxnmapper: Deprecated, ignored. Classification uses Schneider FP.
        use_rxn_insight: Enable RXN Insight enrichment
        use_network: Enable PubChem name resolution
        verbose: Print diagnostic messages to stderr

    Returns:
        ReactionDescriptor with all species and metadata.
    """
    global _verbose
    _verbose = verbose

    # --- Step 0: Auto-discover files if input_dir given ---
    if input_dir and experiment:
        try:
            from discover_experiment_files import discover_experiment_files
            disc = discover_experiment_files(input_dir, experiment)
            if not cdxml and disc.cdx_files:
                cdx = cdx or disc.cdx_files[0]
            if not csv and disc.csv_files:
                csv = csv or disc.csv_files[0]
            if not rxn and disc.rxn_files:
                rxn = rxn or disc.rxn_files[0]
        except Exception as e:
            _log(f"  File discovery failed: {e}")

    # --- Step 0b: CDX → CDXML conversion ---
    if cdx and not cdxml:
        cdxml = _convert_cdx_to_cdxml(cdx)

    desc = ReactionDescriptor(
        experiment=experiment or _stem(cdxml or cdx or rxn or csv or "unknown"),
        input_files={
            "cdxml": cdxml,
            "csv": csv,
            "rxn": rxn,
            "cdx": cdx,
        },
    )

    # Metadata
    desc.metadata["parser_version"] = "1.3"
    desc.metadata["timestamp"] = datetime.datetime.now().isoformat(
        timespec="seconds")
    desc.metadata["rdkit_available"] = _check_rdkit()
    desc.metadata["chemscript_available"] = _check_chemscript()

    # --- Step 1: Extract species from structural source ---
    species: List[SpeciesDescriptor] = []
    warnings: List[str] = []
    cdxml_conditions: List[str] = []

    if cdxml:
        _log(f"Extracting from CDXML: {os.path.basename(cdxml)}")
        sp, w, conds = _extract_from_cdxml(cdxml, use_network=use_network)
        species.extend(sp)
        warnings.extend(w)
        cdxml_conditions.extend(conds)
    elif rxn:
        _log(f"Extracting from RXN: {os.path.basename(rxn)}")
        sp, w = _extract_from_rxn(rxn)
        species.extend(sp)
        warnings.extend(w)

    # --- Step 2: Match CSV data (also returns exp_data for ELN enrichment) ---
    exp_data = None
    if csv:
        _log(f"Matching CSV: {os.path.basename(csv)}")
        species, w, exp_data = _match_csv_data(species, csv)
        warnings.extend(w)

    # --- Step 3: Deduplicate ---
    species = _deduplicate_species(species)

    # --- Step 4: Compute masses (needed before classification MW checks) ---
    _compute_all_masses(species)

    # --- Step 5: Classify roles ---
    _log("Classifying species roles...")
    confidence = _classify_species(
        species,
        use_rxnmapper=use_rxnmapper,
        use_rxn_insight=use_rxn_insight,
    )
    desc.classification_confidence = confidence

    # --- Step 6: Identify SM and DP ---
    _identify_sm_dp(species)

    # --- Step 6.5: Detect solvents (from CSV + reagent_db) ---
    _detect_solvents(species, exp_data=exp_data)

    # --- Step 7: Apply display names ---
    _apply_display_names(species)

    # --- Step 8.5: Build display_text ---
    _build_display_texts(species)

    # --- Step 9: Build reaction SMILES ---
    desc.reaction_smiles = _build_reaction_smiles(species)

    # --- Step 10: Get RXN Insight reaction class (from classify step) ---
    for sp in species:
        if sp.rxn_insight_role:
            # _try_rxn_insight was called — check if it set reaction class
            break

    desc.species = species
    desc.warnings = warnings

    # --- Step 11: Populate ELN data (run arrow, procedure, solvents) ---
    _populate_eln_data(desc, exp_data)

    # --- Step 12: Populate conditions (from CDXML text extraction) ---
    desc.conditions = cdxml_conditions

    _log(f"Parsed {len(species)} species, "
         f"{sum(1 for s in species if s.is_sm)} SM, "
         f"{sum(1 for s in species if s.is_dp)} DP")

    return desc


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _stem(path: str) -> str:
    """Filename stem without extension."""
    return os.path.splitext(os.path.basename(path))[0]


def _check_rdkit() -> bool:
    try:
        from rdkit import Chem  # noqa: F401
        return True
    except ImportError:
        return False


def _check_chemscript() -> bool:
    try:
        from ..chemdraw.chemscript_bridge import ChemScriptBridge  # noqa: F401
        return True
    except ImportError:
        return False


def _convert_cdx_to_cdxml(cdx_path: str) -> Optional[str]:
    """Convert CDX to CDXML via cdx_converter.py subprocess."""
    import subprocess
    import tempfile

    out_path = os.path.splitext(cdx_path)[0] + ".cdxml"
    if os.path.isfile(out_path):
        return out_path

    script_dir = os.path.dirname(os.path.abspath(__file__))
    converter = os.path.join(script_dir, "cdx_converter.py")

    if not os.path.isfile(converter):
        _log(f"  cdx_converter.py not found at {converter}")
        return None

    try:
        result = subprocess.run(
            [sys.executable, converter, cdx_path, "-o", out_path],
            capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.isfile(out_path):
            _log(f"  Converted CDX → CDXML: {out_path}")
            return out_path
        else:
            _log(f"  CDX conversion failed: {result.stderr}")
            return None
    except Exception as e:
        _log(f"  CDX conversion error: {e}")
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Parse reaction from ELN files into a persisted JSON descriptor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reaction_parser.py experiment.cdxml -o reaction.json
  python reaction_parser.py experiment.cdxml --csv exp.csv --pretty
  python reaction_parser.py --input-dir path/ --experiment KL-7001-004
""",
    )
    # Input files
    p.add_argument("cdxml_positional", nargs="?", default=None,
                   help="Input CDXML file (positional)")
    p.add_argument("--cdxml", dest="cdxml_named", default=None,
                   help="Input CDXML file (named)")
    p.add_argument("--cdx", default=None,
                   help="Input CDX file (converted to CDXML)")
    p.add_argument("--csv", default=None,
                   help="Findmolecule ELN CSV file")
    p.add_argument("--rxn", default=None,
                   help="RXN file")
    p.add_argument("--input-dir", default=None,
                   help="Experiment directory (auto-discover files)")
    p.add_argument("--experiment", default=None,
                   help="Experiment name (with --input-dir)")
    # Output
    p.add_argument("-o", "--output", default=None,
                   help="Output JSON file (default: stdout)")
    p.add_argument("--pretty", action="store_true",
                   help="Pretty-print JSON output")
    # Options
    p.add_argument("--no-rxnmapper", action="store_true",
                   help="Deprecated (RXNMapper no longer used for classification)")
    p.add_argument("--no-rxn-insight", action="store_true",
                   help="Skip RXN Insight enrichment")
    p.add_argument("--no-network", action="store_true",
                   help="Skip PubChem name resolution (offline only)")
    p.add_argument("--json-errors", action="store_true",
                   help="Output structured JSON errors to stderr")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Print diagnostic messages to stderr")
    return p


def main(argv=None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Resolve CDXML from positional or named argument
    cdxml = args.cdxml_positional or args.cdxml_named

    if not any([cdxml, args.cdx, args.csv, args.rxn,
                args.input_dir]):
        parser.error("No input files specified")

    try:
        desc = parse_reaction(
            cdxml=cdxml,
            cdx=args.cdx,
            csv=args.csv,
            rxn=args.rxn,
            input_dir=args.input_dir,
            experiment=args.experiment,
            use_rxnmapper=not args.no_rxnmapper,
            use_rxn_insight=not args.no_rxn_insight,
            use_network=not args.no_network,
            verbose=args.verbose,
        )

        if args.output:
            desc.to_json(args.output, pretty=args.pretty)
            print(f"Wrote {args.output} ({len(desc.species)} species)",
                  file=sys.stderr)
        else:
            output = json.dumps(desc.to_dict(),
                                indent=2 if args.pretty else None,
                                ensure_ascii=False)
            print(output)

        return 0

    except Exception as e:
        if args.json_errors:
            err = {"error": "parse_failed", "detail": str(e)}
            print(json.dumps(err), file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
