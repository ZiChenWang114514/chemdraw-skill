"""ChemScript-grounded molecular identity with RDKit fingerprint similarity."""

from __future__ import annotations

import re
from typing import Any


FINGERPRINTS = {"morgan", "rdkit", "maccs"}
MAX_BATCH_PAIRS = 256
MAX_REPRESENTATION_CHARS = 1_000_000
_PAIR_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")


def _bridge_factory():
    from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge

    return ChemScriptBridge()


def _contract(outputs: dict[str, Any], warnings=None, metadata=None) -> dict[str, Any]:
    return {
        "ok": True,
        "outputs": outputs,
        "warnings": list(warnings or []),
        "metadata": dict(metadata or {}),
    }


def _validate_options(fingerprint: str, radius: int, n_bits: int) -> str:
    fingerprint = str(fingerprint).strip().lower()
    if fingerprint not in FINGERPRINTS:
        raise ValueError(f"fingerprint must be one of {sorted(FINGERPRINTS)}")
    if isinstance(radius, bool) or not isinstance(radius, int) or not 1 <= radius <= 4:
        raise ValueError("radius must be an integer from 1 through 4")
    if isinstance(n_bits, bool) or not isinstance(n_bits, int) or not 128 <= n_bits <= 65536:
        raise ValueError("n_bits must be an integer from 128 through 65536")
    return fingerprint


def _representation(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty molecule representation or file path")
    if len(value) > MAX_REPRESENTATION_CHARS:
        raise ValueError(f"{label} exceeds the configured character limit")
    return value


def _molecule_from_info(info: dict[str, Any], label: str):
    from rdkit import Chem

    if not isinstance(info, dict) or info.get("type") != "structure":
        raise ValueError(f"ChemScript did not resolve {label} as one molecular structure")
    smiles = info.get("smiles")
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError(f"ChemScript did not return SMILES for {label}")
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"RDKit could not parse ChemScript output for {label}")
    return molecule


def _fingerprint(molecule, kind: str, radius: int, n_bits: int, use_chirality: bool):
    from rdkit import Chem
    from rdkit.Chem import MACCSkeys, rdFingerprintGenerator

    if kind == "morgan":
        generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=radius,
            fpSize=n_bits,
            includeChirality=use_chirality,
        )
        return generator.GetFingerprint(molecule)
    if kind == "rdkit":
        return Chem.RDKFingerprint(molecule, fpSize=n_bits)
    return MACCSkeys.GenMACCSKeys(molecule)


def _normalized(info: dict[str, Any], molecule) -> dict[str, Any]:
    from rdkit import Chem

    return {
        "formula": info.get("formula"),
        "inchi": info.get("inchi"),
        "canonical_smiles": Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True),
        "atom_count": info.get("atom_count"),
        "bond_count": info.get("bond_count"),
    }


def _compare_infos(
    info_a: dict[str, Any],
    info_b: dict[str, Any],
    *,
    fingerprint: str,
    radius: int,
    n_bits: int,
) -> tuple[dict[str, Any], list[str]]:
    from rdkit import DataStructs

    molecule_a = _molecule_from_info(info_a, "molecule_a")
    molecule_b = _molecule_from_info(info_b, "molecule_b")
    canonical_a = _normalized(info_a, molecule_a)
    canonical_b = _normalized(info_b, molecule_b)
    inchi_a = info_a.get("inchi")
    inchi_b = info_b.get("inchi")
    if isinstance(inchi_a, str) and inchi_a and isinstance(inchi_b, str) and inchi_b:
        exact_match = inchi_a == inchi_b
        identity_basis = "ChemScript InChI"
    else:
        exact_match = canonical_a["canonical_smiles"] == canonical_b["canonical_smiles"]
        identity_basis = "RDKit canonical isomeric SMILES (ChemScript InChI unavailable)"

    fingerprint_a = _fingerprint(molecule_a, fingerprint, radius, n_bits, True)
    fingerprint_b = _fingerprint(molecule_b, fingerprint, radius, n_bits, True)
    connectivity_a = _fingerprint(molecule_a, fingerprint, radius, n_bits, False)
    connectivity_b = _fingerprint(molecule_b, fingerprint, radius, n_bits, False)
    tanimoto = round(float(DataStructs.TanimotoSimilarity(fingerprint_a, fingerprint_b)), 6)
    connectivity = round(
        float(DataStructs.TanimotoSimilarity(connectivity_a, connectivity_b)), 6
    )
    warnings = []
    if not inchi_a or not inchi_b:
        warnings.append("ChemScript did not return both InChI values; exact identity used canonical isomeric SMILES")
    if not exact_match and connectivity == 1.0:
        warnings.append(
            "Connectivity fingerprints match while exact identity differs; inspect stereochemistry, isotopes, charge, or tautomer state"
        )
    if canonical_a.get("formula") != canonical_b.get("formula"):
        warnings.append("ChemScript molecular formulas differ")
    return (
        {
            "exact_match": bool(exact_match),
            "identity_basis": identity_basis,
            "tanimoto": tanimoto,
            "connectivity_tanimoto": connectivity,
            "fingerprint": fingerprint,
            "molecule_a": canonical_a,
            "molecule_b": canonical_b,
        },
        warnings,
    )


def compare_molecules(
    molecule_a: str,
    molecule_b: str,
    fingerprint: str = "morgan",
    radius: int = 2,
    n_bits: int = 2048,
) -> dict[str, Any]:
    """Compare two molecule representations using ChemScript identity and RDKit Tanimoto fingerprints."""
    fingerprint = _validate_options(fingerprint, radius, n_bits)
    molecule_a = _representation(molecule_a, "molecule_a")
    molecule_b = _representation(molecule_b, "molecule_b")
    bridge = _bridge_factory()
    try:
        outputs, warnings = _compare_infos(
            bridge.get_info(molecule_a),
            bridge.get_info(molecule_b),
            fingerprint=fingerprint,
            radius=radius,
            n_bits=n_bits,
        )
    finally:
        bridge.close()
    return _contract(
        outputs,
        warnings,
        {
            "identity_engine": "ChemScriptBridge",
            "fingerprint_engine": "RDKit",
            "radius": radius,
            "n_bits": n_bits,
            "network_used": False,
        },
    )


def _validated_pairs(pairs: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("pairs must be a non-empty list")
    if len(pairs) > MAX_BATCH_PAIRS:
        raise ValueError(f"pairs may contain at most {MAX_BATCH_PAIRS} entries")
    result = []
    seen = set()
    for index, pair in enumerate(pairs, start=1):
        if not isinstance(pair, dict):
            raise ValueError(f"pairs[{index - 1}] must be an object")
        pair_id = pair.get("pair_id") or f"pair_{index}"
        if not isinstance(pair_id, str) or not _PAIR_ID.fullmatch(pair_id):
            raise ValueError("pair_id must use 1-100 ASCII letters, digits, dots, underscores, or hyphens")
        if pair_id in seen:
            raise ValueError(f"pair_id values must be unique: {pair_id}")
        seen.add(pair_id)
        result.append(
            (
                pair_id,
                _representation(pair.get("mol1"), f"pairs[{index - 1}].mol1"),
                _representation(pair.get("mol2"), f"pairs[{index - 1}].mol2"),
            )
        )
    return result


def batch_compare_molecules(
    pairs: list[dict[str, Any]],
    fingerprint: str = "morgan",
    radius: int = 2,
    n_bits: int = 2048,
) -> dict[str, Any]:
    """Compare up to 256 molecule pairs with one ChemScript bridge session."""
    fingerprint = _validate_options(fingerprint, radius, n_bits)
    validated = _validated_pairs(pairs)
    bridge = _bridge_factory()
    cache: dict[str, dict[str, Any]] = {}
    results = []
    warnings = []
    succeeded = 0
    try:
        for pair_id, molecule_a, molecule_b in validated:
            try:
                if molecule_a not in cache:
                    cache[molecule_a] = bridge.get_info(molecule_a)
                if molecule_b not in cache:
                    cache[molecule_b] = bridge.get_info(molecule_b)
                comparison, pair_warnings = _compare_infos(
                    cache[molecule_a],
                    cache[molecule_b],
                    fingerprint=fingerprint,
                    radius=radius,
                    n_bits=n_bits,
                )
                results.append(
                    {"pair_id": pair_id, "ok": True, **comparison, "warnings": pair_warnings}
                )
                succeeded += 1
            except Exception:
                results.append(
                    {
                        "pair_id": pair_id,
                        "ok": False,
                        "error": {
                            "code": "molecule_comparison_failed",
                            "message": "This pair could not be parsed and compared",
                        },
                    }
                )
    finally:
        bridge.close()
    failed = len(validated) - succeeded
    if failed:
        warnings.append(f"{failed} pair(s) could not be compared; successful pairs remain available")
    return _contract(
        {"results": results},
        warnings,
        {
            "total": len(validated),
            "succeeded": succeeded,
            "failed": failed,
            "identity_engine": "ChemScriptBridge",
            "fingerprint_engine": "RDKit",
            "fingerprint": fingerprint,
            "radius": radius,
            "n_bits": n_bits,
            "network_used": False,
        },
    )


COMPARISON_TOOLS = {
    "compare_molecules": compare_molecules,
    "batch_compare_molecules": batch_compare_molecules,
}
