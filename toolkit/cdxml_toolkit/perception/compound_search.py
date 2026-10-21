#!/usr/bin/env python3
"""
compound_search.py — Search for a molecule across a directory of experiments.

Given a query SMILES and a directory of experiment subdirectories (each
containing ELN exports: .cdxml, .csv, .rxn), parses every experiment and
compares the query against all species using RDKit exact-match and Tanimoto
fingerprint similarity.

Python API:
    from cdxml_toolkit.perception.compound_search import search_compound
    results = search_compound(
        smiles="NCCCCCOc1cccc2c1C(=O)N(C1CCC(=O)NC1=O)C2=O",
        experiment_dir="/path/to/KL-7001",
    )
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical(smiles: str) -> Optional[str]:
    """Return canonical SMILES, or None if invalid."""
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


def _morgan_fp(smiles: str):
    """Return Morgan fingerprint (radius=2, 2048 bits), or None."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
    except Exception:
        return None


def _tanimoto(fp1, fp2) -> float:
    """Tanimoto similarity between two RDKit fingerprints."""
    from rdkit import DataStructs
    return DataStructs.TanimotoSimilarity(fp1, fp2)


def _discover_files(exp_dir: Path):
    """Return (cdxml_path, csv_path) for a single experiment subdirectory."""
    cdxml_files = list(exp_dir.glob("*.cdxml"))
    csv_files = list(exp_dir.glob("*.csv"))
    cdxml = str(cdxml_files[0]) if cdxml_files else None
    csv = str(csv_files[0]) if csv_files else None
    return cdxml, csv


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_compound(
    smiles: str,
    experiment_dir: str,
    similarity_threshold: float = 0.85,
) -> Dict[str, Any]:
    """Search for a molecule (by SMILES) across all experiments in a directory.

    Args:
        smiles: Query molecule as a SMILES string.
        experiment_dir: Path to a directory whose immediate subdirectories are
            individual experiments (each containing .cdxml / .csv files).
        similarity_threshold: Minimum Tanimoto similarity (0–1) for a species
            to appear in ``similar_matches``.  Exact matches (same canonical
            SMILES) are always reported regardless of this threshold.

    Returns:
        A dict with keys:
            ok (bool), query_smiles (str), query_canonical (str),
            exact_matches (list), similar_matches (list),
            experiments_searched (int), experiments_parsed_ok (int),
            parse_errors (list of {"experiment": str, "error": str}).
    """
    from cdxml_toolkit.perception.reaction_parser import parse_reaction

    # Validate query
    query_canonical = _canonical(smiles)
    if query_canonical is None:
        return {
            "ok": False,
            "error": f"Invalid query SMILES: {smiles!r}",
            "query_smiles": smiles,
        }

    query_fp = _morgan_fp(query_canonical)

    root = Path(experiment_dir)
    if not root.is_dir():
        return {
            "ok": False,
            "error": f"experiment_dir does not exist or is not a directory: {experiment_dir!r}",
            "query_smiles": smiles,
        }

    # Collect experiment subdirectories (immediate children only)
    exp_dirs = sorted(p for p in root.iterdir() if p.is_dir())

    exact_matches: List[Dict[str, Any]] = []
    similar_matches: List[Dict[str, Any]] = []
    parse_errors: List[Dict[str, str]] = []
    experiments_parsed_ok = 0

    for exp_dir in exp_dirs:
        exp_name = exp_dir.name
        cdxml, csv = _discover_files(exp_dir)

        if cdxml is None:
            # No CDXML → skip silently (no reaction to parse)
            continue

        try:
            desc = parse_reaction(
                cdxml=cdxml,
                csv=csv,
                use_network=False,  # keep offline for batch search
                verbose=False,
            )
        except Exception as exc:
            parse_errors.append({
                "experiment": exp_name,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            })
            continue

        experiments_parsed_ok += 1

        # Pull eln_data fields once per experiment
        eln = desc.eln_data or {}
        product_yield = eln.get("product_yield")
        product_obtained = eln.get("product_obtained")
        sm_mass = eln.get("sm_mass")

        for sp in desc.species:
            # Prefer the full SMILES; also check neutral form for exact matching
            sp_smiles = sp.smiles or sp.smiles_neutral
            if not sp_smiles:
                continue

            sp_canonical = _canonical(sp_smiles)
            if sp_canonical is None:
                continue

            # Neutral canonical (largest fragment, salt-stripped) for comparison
            sp_neutral_canonical = (
                _canonical(sp.smiles_neutral) if sp.smiles_neutral else None
            )

            # --- Exact match ---
            # Check both the full canonical and the neutral (salt-free) form.
            # This lets "NCCCCCOc1..." match "Cl.NCCCCCOc1..." (HCl salt).
            matched_as_exact = (
                sp_canonical == query_canonical
                or (sp_neutral_canonical and sp_neutral_canonical == query_canonical)
            )
            if matched_as_exact:
                reported_smiles = (
                    sp_neutral_canonical
                    if sp_neutral_canonical == query_canonical
                    else sp_canonical
                )
                record: Dict[str, Any] = {
                    "experiment": exp_name,
                    "species_name": sp.name or sp.id,
                    "role": sp.role,
                    "smiles": reported_smiles,
                }
                if sp_canonical != reported_smiles:
                    record["smiles_full"] = sp_canonical  # show the salt form too
                if product_yield:
                    record["yield"] = product_yield
                if product_obtained:
                    record["amount_obtained"] = product_obtained
                if sm_mass:
                    record["sm_mass"] = sm_mass
                exact_matches.append(record)
                continue  # don't also report as similar

            # --- Similarity match ---
            # Use the neutral form for fingerprint comparison when available
            # (avoids artificially low similarity for salt vs free base).
            fp_smiles = sp_neutral_canonical or sp_canonical
            if query_fp is not None:
                sp_fp = _morgan_fp(fp_smiles)
                if sp_fp is not None:
                    sim = _tanimoto(query_fp, sp_fp)
                    if sim >= similarity_threshold:
                        similar_matches.append({
                            "experiment": exp_name,
                            "species_name": sp.name or sp.id,
                            "role": sp.role,
                            "similarity": round(sim, 4),
                            "smiles": sp_canonical,
                        })

    # Sort similar matches by descending similarity
    similar_matches.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "ok": True,
        "query_smiles": smiles,
        "query_canonical": query_canonical,
        "exact_matches": exact_matches,
        "similar_matches": similar_matches,
        "experiments_searched": len(exp_dirs),
        "experiments_parsed_ok": experiments_parsed_ok,
        "parse_errors": parse_errors,
    }
