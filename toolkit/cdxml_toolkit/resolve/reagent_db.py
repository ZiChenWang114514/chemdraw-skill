#!/usr/bin/env python3
"""
reagent_db.py — Shared reagent database loader (two-tier).

Loads a curated ``reagent_abbreviations.json`` (tier-1, ~172 entries with
roles) and a larger ``chemscanner_abbreviations.json`` (tier-2, ~5,800
entries, no roles) for name/SMILES → display/role resolution.

Tier-1 always wins.  Tier-2 is consulted only when tier-1 returns None,
and entries listed in ``chemscanner_quarantine.json`` are never loaded.
Role lookups and ``entry_for_smiles`` are tier-1 only.  Salt, hydrate and
solvate names ("Et3N·HCl") resolve component by component.

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

# Separators between the components of a salt, hydrate or solvate name
# ("Et3N·HCl", "CuSO4.5H2O"). Components are kept, never dropped.
_COMPONENT_SEPARATOR = re.compile(r"\s*[·•⋅.]\s*")
# Leading stoichiometric count of a component ("5h2o").
_COMPONENT_COUNT = re.compile(r"^(\d+)\s*(?=[a-z(\[])")

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

        # Lazily import RDKit only when runtime SMILES canonicalization is needed
        self._rdkit_Chem = sys.modules.get("rdkit.Chem")
        self._rdkit_checked = self._rdkit_Chem is not None

        self._index_entries(raw, self._by_name, self._by_smiles)

        # --- Tier-2: ChemScanner (optional) ---
        self._cs_by_name: Dict[str, dict] = {}
        self._cs_by_smiles: Dict[str, dict] = {}

        if os.path.exists(secondary_path):
            try:
                with open(secondary_path, encoding="utf-8") as f:
                    cs_raw: Dict[str, dict] = json.load(f)
                # Quarantined entries (see reagent_quality.py) never take part.
                quarantine_path = os.path.join(os.path.dirname(secondary_path),
                                               "chemscanner_quarantine.json")
                if os.path.exists(quarantine_path):
                    with open(quarantine_path, encoding="utf-8") as f:
                        quarantined = set(json.load(f).get("entries", {}))
                    cs_raw = {k: v for k, v in cs_raw.items() if k not in quarantined}
                self._index_entries(cs_raw, self._cs_by_name,
                                    self._cs_by_smiles,
                                    canonical_defaults_to_smiles=True)
            except Exception as exc:
                print(f"[reagent_db] Warning: could not load tier-2 "
                      f"database: {exc}", file=sys.stderr)

    def _get_rdkit_chem(self):
        if not self._rdkit_checked:
            self._rdkit_checked = True
            try:
                from rdkit import Chem
                self._rdkit_Chem = Chem
            except ImportError:
                self._rdkit_Chem = None
        return self._rdkit_Chem

    def _index_entries(self, raw: Dict[str, dict],
                       by_name: Dict[str, dict],
                       by_smiles: Dict[str, dict],
                       canonical_defaults_to_smiles: bool = False):
        """Index a set of JSON entries into name and SMILES lookup dicts.

        An entry without ``canonical_smiles`` is canonicalized with RDKit at load time, unless
        ``canonical_defaults_to_smiles`` says the stored ``smiles`` already is canonical (the ChemScanner
        file stores ``canonical_smiles`` only where it differs, which keeps loading free of RDKit).
        """
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
                canon_val = entry.get("canonical_smiles")
                if canon_val is not None:
                    canon_list: List[str] = (
                        canon_val if isinstance(canon_val, list)
                        else [canon_val]
                    )
                    for canon in canon_list:
                        by_smiles[canon] = entry
                elif not canonical_defaults_to_smiles:
                    chem = self._get_rdkit_chem()
                    if chem is not None:
                        try:
                            from rdkit import rdBase
                            block = rdBase.BlockLogs()
                        except Exception:
                            block = None
                        try:
                            for smi in smiles_list:
                                try:
                                    mol = chem.MolFromSmiles(smi)
                                    if mol:
                                        canon = chem.MolToSmiles(mol)
                                        by_smiles[canon] = entry
                                except Exception:
                                    pass
                        finally:
                            del block

    # ----- name-based lookups -----

    def _lookup_single(self, key: str, tiers: Tuple[str, ...]
                       ) -> Optional[Tuple[dict, str]]:
        """Exact, then rac-/(±)-stripped lookup of one normalized name."""
        candidates = [key]
        stripped_rac = _RAC_PREFIX.sub("", key).strip()
        if stripped_rac != key:
            candidates.append(stripped_rac)
        for cand in candidates:
            for tier in tiers:
                index = self._by_name if tier == "primary" else self._cs_by_name
                entry = index.get(cand)
                if entry:
                    return entry, tier
        return None

    @staticmethod
    def entry_smiles(entry: dict) -> Optional[str]:
        for field in ("canonical_smiles", "smiles"):
            value = entry.get(field)
            if isinstance(value, list):
                value = value[0] if value else None
            if value:
                return value
        return None

    def _lookup_composite(self, key: str, tiers: Tuple[str, ...]
                          ) -> Optional[Tuple[dict, str]]:
        """Resolve a salt, hydrate or solvate name component by component.

        ``"et3n·hcl"`` becomes Et3N + HCl and ``"cuso4·5h2o"`` CuSO4 + 5 H2O;
        every component must be known, otherwise the whole name is unknown.
        """
        parts = [p for p in _COMPONENT_SEPARATOR.split(key) if p]
        if len(parts) < 2:
            return None
        components = []
        for part in parts:
            count = 1
            match = _COMPONENT_COUNT.match(part)
            if match:
                count = int(match.group(1))
                part = part[match.end():]
            found = self._lookup_single(part, tiers)
            if found is None:
                return None
            entry, tier = found
            smiles = self.entry_smiles(entry)
            if smiles is None:
                return None
            components.append({"name": part, "display": entry["display"],
                               "smiles": smiles, "count": count, "tier": tier})
        display = "·".join((f"{c['count']}" if c["count"] > 1 else "") + c["display"]
                                for c in components)
        smiles = ".".join(".".join([c["smiles"]] * c["count"]) for c in components)
        tier = "primary" if all(c["tier"] == "primary" for c in components) else "secondary"
        composite = {"display": display, "smiles": smiles, "components": components}
        role = self._by_name.get(components[0]["name"], {}).get("role")
        if role:
            composite["role"] = role
        return composite, tier

    def lookup_name(self, name: str, tiers: Tuple[str, ...] = ("primary", "secondary")
                    ) -> Optional[Tuple[dict, str]]:
        """Return ``(entry, tier)`` for a name, or None.

        ``tier`` is ``"primary"`` (curated table) or ``"secondary"`` (large
        table, quarantined entries removed). Salt, hydrate and solvate names
        without their own entry resolve to a composite entry whose
        ``components`` list every part; nothing is silently dropped.
        """
        key = _normalize_name(name)
        for tier in tiers:
            found = self._lookup_single(key, (tier,))
            if found:
                return found
        return self._lookup_composite(key, tiers)

    def _lookup_name_entry(self, name: str, tier1_only: bool = False
                           ) -> Optional[dict]:
        """Name lookup: tier-1 first, then tier-2 (unless tier1_only)."""
        tiers = ("primary",) if tier1_only else ("primary", "secondary")
        found = self.lookup_name(name, tiers)
        return found[0] if found else None

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
        chem = self._get_rdkit_chem()
        if chem is not None:
            try:
                mol = chem.MolFromSmiles(smiles)
                if mol:
                    canon = chem.MolToSmiles(mol)
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
        """Return the curated (tier-1) entry for a SMILES, or None.

        Tier-2 is not consulted: its names are not reviewed, so a reverse
        lookup there could label a structure with the wrong name.
        """
        return self._lookup_smiles_entry(smiles, self._by_smiles)

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
