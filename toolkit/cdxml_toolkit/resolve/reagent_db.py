#!/usr/bin/env python3
"""
reagent_db.py — Shared reagent database loader (two-tier).

Loads a curated ``reagent_abbreviations.json`` (tier-1, ~172 entries with
roles) and a larger ``chemscanner_abbreviations.json`` (tier-2, ~5,800
entries, no roles) for name/SMILES → display/role resolution.

Tier-1 always wins.  Tier-2 is consulted only when tier-1 returns None.
Role lookups are tier-1 only (ChemScanner has no role data).

Usage:
    from cdxml_toolkit.resolve.reagent_db import get_reagent_db

    db = get_reagent_db()
    db.display_for_name("cs2co3")        # "Cs2CO3"  (tier-1)
    db.role_for_name("cs2co3")           # "base"    (tier-1 only)
    db.display_for_name("hatu")          # "HATU"    (tier-2 fallback)
    db.display_for_smiles(canon_smi)     # "Et3N"    (if SMILES matches)
    db.resolve_display("cs2co3")         # "Cs2CO3"  (or original if unknown)
"""

import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Name normalization helpers
# ---------------------------------------------------------------------------

# Unicode subscript digits → ASCII digits
_SUBSCRIPT_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

# Common solvate/salt suffixes to strip (middle-dot or ASCII dot)
_SOLVATE_SUFFIXES = re.compile(
    r"[·.](?:chcl3|dcm|ch2cl2|h2o|hcl|thf|dme|meoh|etoh|et2o)\s*$",
    re.IGNORECASE,
)

# Racemic/stereochemical prefixes to strip
_RAC_PREFIX = re.compile(r"^(?:rac-|\(±\)-)", re.IGNORECASE)


def _normalize_name(name: str) -> str:
    """Normalize a reagent name for lookup.

    Converts Unicode subscript digits to ASCII and lowercases.
    """
    return name.translate(_SUBSCRIPT_MAP).strip().lower()


class ReagentDB:
    """In-memory reagent database with two-tier lookup.

    Tier-1: ``reagent_abbreviations.json`` (curated, with roles).
    Tier-2: ``chemscanner_abbreviations.json`` (large, no roles).
    """

    def __init__(self, json_path: Optional[str] = None,
                 secondary_path: Optional[str] = None):
        module_dir = os.path.dirname(os.path.abspath(__file__))

        if json_path is None:
            json_path = os.path.join(module_dir, "reagent_abbreviations.json")
        if secondary_path is None:
            secondary_path = os.path.join(module_dir,
                                          "chemscanner_abbreviations.json")

        # --- Tier-1: curated ---
        with open(json_path, encoding="utf-8") as f:
            raw: Dict[str, dict] = json.load(f)

        self._by_name: Dict[str, dict] = {}
        self._by_smiles: Dict[str, dict] = {}

        # Try to import RDKit for SMILES canonicalization
        self._rdkit_Chem = None
        try:
            from rdkit import Chem
            self._rdkit_Chem = Chem
        except ImportError:
            pass

        self._index_entries(raw, self._by_name, self._by_smiles)

        # --- Tier-2: ChemScanner (optional) ---
        self._cs_by_name: Dict[str, dict] = {}
        self._cs_by_smiles: Dict[str, dict] = {}

        if os.path.exists(secondary_path):
            try:
                with open(secondary_path, encoding="utf-8") as f:
                    cs_raw: Dict[str, dict] = json.load(f)
                self._index_entries(cs_raw, self._cs_by_name,
                                    self._cs_by_smiles)
            except Exception as exc:
                print(f"[reagent_db] Warning: could not load tier-2 "
                      f"database: {exc}", file=sys.stderr)

    def _index_entries(self, raw: Dict[str, dict],
                       by_name: Dict[str, dict],
                       by_smiles: Dict[str, dict]):
        """Index a set of JSON entries into name and SMILES lookup dicts."""
        for key, entry in raw.items():
            # Index by primary key
            by_name[key] = entry

            # Index by aliases
            for alias in entry.get("aliases", []):
                by_name[alias] = entry

            # Index by SMILES
            smiles_val = entry.get("smiles")
            if smiles_val is not None:
                smiles_list: List[str] = (
                    smiles_val if isinstance(smiles_val, list)
                    else [smiles_val]
                )
                for smi in smiles_list:
                    by_smiles[smi] = entry
                    if self._rdkit_Chem is not None:
                        try:
                            mol = self._rdkit_Chem.MolFromSmiles(smi)
                            if mol:
                                canon = self._rdkit_Chem.MolToSmiles(mol)
                                by_smiles[canon] = entry
                        except Exception:
                            pass

    # ----- name-based lookups -----

    def _lookup_name_entry(self, name: str, tier1_only: bool = False
                           ) -> Optional[dict]:
        """Internal progressive-normalization name lookup.

        Tries (in order):
          1. Exact (lowered, subscript-normalized)
          2. With solvate suffix stripped  ("·CHCl3", ".DCM", etc.)
          3. With rac-/(±)- prefix stripped
          4. With both solvate suffix and rac- prefix stripped

        Each step checks tier-1 first, then tier-2 (unless tier1_only).
        """
        key = _normalize_name(name)
        candidates = [key]

        # Strip solvate suffix
        stripped_solvate = _SOLVATE_SUFFIXES.sub("", key).strip()
        if stripped_solvate != key:
            candidates.append(stripped_solvate)

        # Strip rac-/(±)- prefix
        stripped_rac = _RAC_PREFIX.sub("", key).strip()
        if stripped_rac != key:
            candidates.append(stripped_rac)

        # Strip both
        stripped_both = _RAC_PREFIX.sub("", stripped_solvate).strip()
        if stripped_both not in candidates:
            candidates.append(stripped_both)

        for cand in candidates:
            entry = self._by_name.get(cand)
            if entry:
                return entry
            if not tier1_only:
                entry = self._cs_by_name.get(cand)
                if entry:
                    return entry

        return None

    def display_for_name(self, name: str) -> Optional[str]:
        """Return display string for a name/alias, or None if unknown.

        Checks tier-1 (curated) first, then tier-2 (ChemScanner).
        Uses progressive normalization (subscripts, solvate stripping,
        rac- prefix stripping).
        """
        entry = self._lookup_name_entry(name)
        return entry["display"] if entry else None

    def role_for_name(self, name: str) -> Optional[str]:
        """Return role string for a name/alias, or None.

        Tier-1 only — ChemScanner entries have no roles.
        """
        entry = self._lookup_name_entry(name, tier1_only=True)
        return entry.get("role") if entry else None

    def entry_for_name(self, name: str) -> Optional[dict]:
        """Return the full entry dict for a name/alias, or None.

        Checks tier-1 first, then tier-2.
        """
        return self._lookup_name_entry(name)

    # ----- SMILES-based lookups -----

    def _lookup_smiles_entry(self, smiles: str,
                             by_smiles: Dict[str, dict]) -> Optional[dict]:
        """Look up a SMILES in a single index (raw then canonicalized)."""
        entry = by_smiles.get(smiles)
        if entry:
            return entry
        if self._rdkit_Chem is not None:
            try:
                mol = self._rdkit_Chem.MolFromSmiles(smiles)
                if mol:
                    canon = self._rdkit_Chem.MolToSmiles(mol)
                    entry = by_smiles.get(canon)
                    if entry:
                        return entry
            except Exception:
                pass
        return None

    def display_for_smiles(self, smiles: str) -> Optional[str]:
        """Return display string for a SMILES, or None if unknown.

        Checks tier-1 first, then tier-2.
        """
        entry = self._lookup_smiles_entry(smiles, self._by_smiles)
        if entry:
            return entry["display"]
        entry = self._lookup_smiles_entry(smiles, self._cs_by_smiles)
        return entry["display"] if entry else None

    def role_for_smiles(self, smiles: str) -> Optional[str]:
        """Return role string for a SMILES, or None.

        Tier-1 only — ChemScanner entries have no roles.
        """
        entry = self._lookup_smiles_entry(smiles, self._by_smiles)
        return entry.get("role") if entry else None

    def entry_for_smiles(self, smiles: str) -> Optional[dict]:
        """Return the full entry dict for a SMILES, or None.

        Checks tier-1 first, then tier-2.
        """
        entry = self._lookup_smiles_entry(smiles, self._by_smiles)
        if entry:
            return entry
        return self._lookup_smiles_entry(smiles, self._cs_by_smiles)

    # ----- convenience -----

    def resolve_display(self, name: str) -> str:
        """Return the display string for *name*, or *name* itself if unknown.

        Drop-in replacement for the old ``ABBREVIATIONS.get(key, text)``
        pattern.  Checks tier-1 first, then tier-2.
        """
        display = self.display_for_name(name)
        return display if display is not None else name

    def smiles_role_display(self, smiles: str) -> Optional[Tuple[str, str]]:
        """Return (role, display) for a SMILES, matching the old
        ROLE_BY_SMILES dict interface.

        Tier-1 only (requires role).  Returns None if unknown.
        """
        entry = self._lookup_smiles_entry(smiles, self._by_smiles)
        if entry and "role" in entry:
            return (entry["role"], entry["display"])
        return None


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_instance: Optional[ReagentDB] = None


def get_reagent_db() -> ReagentDB:
    """Return the shared ReagentDB singleton (loaded on first call)."""
    global _instance
    if _instance is None:
        _instance = ReagentDB()
    return _instance
