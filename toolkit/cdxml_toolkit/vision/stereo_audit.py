"""Stereochemistry auditing, wedge geometry, oriented depiction, and surgical graph editing."""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from rdkit import Chem, RDLogger, rdBase
from rdkit.Chem import Draw, rdCIPLabeler, rdDepictor, rdFMCS, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

try:
    _FONT = ImageFont.truetype("arial.ttf", 15)
    _BIG = ImageFont.truetype("arialbd.ttf", 17)
except OSError:
    _FONT = _BIG = ImageFont.load_default()

GREEN, RED, BLUE = (0, 160, 60), (220, 30, 30), (30, 90, 230)
KINDS = {
    "wedge": "wedge",
    "solid wedge": "wedge",
    "solid_wedge": "wedge",
    "wedgebegin": "wedge",
    "bold": "wedge",
    "solid": "wedge",
    "up": "wedge",
    "hash": "hash",
    "dashed wedge": "hash",
    "dashed_wedge": "hash",
    "wedgedhashbegin": "hash",
    "hashed": "hash",
    "dash": "hash",
    "dashed": "hash",
    "down": "hash",
    "plain": "plain",
    "single": "plain",
    "none": "plain",
}
_COMPASS = {
    "up": (0.0, -1.0),
    "down": (0.0, 1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
    "up-left": (-0.7, -0.7),
    "up-right": (0.7, -0.7),
    "down-left": (-0.7, 0.7),
    "down-right": (0.7, 0.7),
}
_ORDER = {
    1: Chem.BondType.SINGLE,
    2: Chem.BondType.DOUBLE,
    3: Chem.BondType.TRIPLE,
    4: Chem.BondType.AROMATIC,
}
_BOND_TYPE_BY_NAME = {
    "single": Chem.BondType.SINGLE,
    "1": Chem.BondType.SINGLE,
    "double": Chem.BondType.DOUBLE,
    "2": Chem.BondType.DOUBLE,
    "triple": Chem.BondType.TRIPLE,
    "3": Chem.BondType.TRIPLE,
    "aromatic": Chem.BondType.AROMATIC,
    "4": Chem.BondType.AROMATIC,
}
_SILYL = (
    "TBS = [Si](C)(C)C(C)(C)C, TMS = [Si](C)(C)C, "
    "TES = [Si](CC)(CC)CC, TIPS = [Si](C(C)C)(C(C)C)C(C)C"
)
SKELETON_OPS = ("set_atom", "set_bond", "add_group", "remove_atoms")
WEAK = 0.65


class EditedSmiles(str):
    """A canonical SMILES string that also supports dict-style metadata lookup."""

    def __new__(cls, value: str, meta: dict[str, Any] | None = None):
        obj = super().__new__(cls, value)
        obj._meta = dict(meta or {})
        obj._meta.setdefault("smiles", str(value))
        obj._meta.setdefault("canonical_smiles", str(value))
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self._meta:
                return self._meta[key]
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        return self._meta.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._meta)


class SmilesErrorDiagnosis(str):
    """Diagnostic string from diagnose_smiles_error that also exposes structured fields."""

    def __new__(cls, value: str, data: dict[str, Any] | None = None):
        obj = super().__new__(cls, value)
        obj._data = dict(data or {})
        obj._data.setdefault("valid", False)
        obj._data.setdefault("error", str(value))
        obj._data.setdefault("message", str(value))
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self._data:
                return self._data[key]
            raise KeyError(key)
        return super().__getitem__(key)

    def __contains__(self, item) -> bool:
        return super().__contains__(str(item)) or (item in self._data)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


class StereoFromWedgesResult(dict):
    """Result of stereo_from_wedges(atoms, bonds), supporting both dict keys and atom-index lookup."""

    def __init__(self, data: dict[str, Any], mol: Chem.Mol | None = None):
        super().__init__(data)
        self._mol = mol

    @property
    def mol(self) -> Chem.Mol | None:
        return self._mol

    def __getitem__(self, key):
        if isinstance(key, int) and "centers" in self and key in self["centers"]:
            return self["centers"][key]
        if key == "mol":
            return self._mol
        return super().__getitem__(key)

    def __contains__(self, key) -> bool:
        if isinstance(key, int) and "centers" in self and key in self["centers"]:
            return True
        if key == "mol":
            return self._mol is not None
        return super().__contains__(key)

    def __getattr__(self, name: str):
        if self._mol is not None and hasattr(self._mol, name):
            return getattr(self._mol, name)
        raise AttributeError(name)


class TransferStereoResult(dict):
    """Result of transfer_stereo, usable as dict, (smiles, report) tuple, or RDKit Mol proxy."""

    def __init__(self, smiles: str, mol: Chem.Mol, report: dict[str, Any]):
        data = {
            "smiles": smiles,
            "canonical_smiles": smiles,
            **report,
        }
        super().__init__(data)
        self._mol = mol

    @property
    def mol(self) -> Chem.Mol:
        return self._mol

    def __getitem__(self, key):
        if key == "mol":
            return self._mol
        if isinstance(key, int):
            if key == 0:
                return self["smiles"]
            if key == 1:
                return dict(self)
        return super().__getitem__(key)

    def __iter__(self):
        yield self["smiles"]
        yield dict(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            other_mol = Chem.MolFromSmiles(other)
            if other_mol is not None:
                return Chem.MolToSmiles(self._mol) == Chem.MolToSmiles(other_mol)
            return self["smiles"] == other
        if isinstance(other, Chem.Mol):
            return Chem.MolToSmiles(self._mol) == Chem.MolToSmiles(other)
        return super().__eq__(other)

    def __getattr__(self, name: str):
        if hasattr(self._mol, name):
            return getattr(self._mol, name)
        raise AttributeError(name)


class ReadWedgesResult(dict):
    """Result of read_wedges(smiles, wedges), usable as dict or unpacked as (smiles, cip_labels)."""

    def __getitem__(self, key):
        if isinstance(key, int):
            if key == 0:
                return self["smiles"]
            if key == 1:
                return self["cip_labels"]
        return super().__getitem__(key)

    def __iter__(self):
        yield self["smiles"]
        yield self["cip_labels"]

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            other_mol = Chem.MolFromSmiles(other)
            my_mol = Chem.MolFromSmiles(self["smiles"])
            if other_mol is not None and my_mol is not None:
                return Chem.MolToSmiles(my_mol) == Chem.MolToSmiles(other_mol)
            return self["smiles"] == other
        return super().__eq__(other)


class ImageResultDict(dict):
    """JSON-serializable result dictionary that also proxies PIL.Image.Image attributes."""

    def __init__(self, data: dict[str, Any], image: Image.Image | None = None):
        super().__init__(data)
        self._image = image

    @property
    def image(self) -> Image.Image | None:
        return self._image

    def __getitem__(self, key):
        if key == "image":
            return self._image
        return super().__getitem__(key)

    def __getattr__(self, name: str):
        if self._image is not None and hasattr(self._image, name):
            return getattr(self._image, name)
        raise AttributeError(name)


class SnappedPoint(dict):
    """2D atom coordinate supporting both point['x']/point['y'] and point[0]/point[1]."""

    def __getitem__(self, key):
        if key == 0:
            return super().__getitem__("x")
        if key == 1:
            return super().__getitem__("y")
        return super().__getitem__(key)

    def __iter__(self):
        yield float(super().__getitem__("x"))
        yield float(super().__getitem__("y"))

    def __len__(self) -> int:
        return 2

    def __array__(self, dtype=None):
        return np.array([super().__getitem__("x"), super().__getitem__("y")], dtype=dtype or float)


class SnappedPointsList(list):
    """List of SnappedPoint entries that also behaves like an (N, 2) numpy float array."""

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self), 2)

    def __array__(self, dtype=None):
        if not self:
            return np.zeros((0, 2), dtype=dtype or float)
        return np.array([[p["x"], p["y"]] for p in self], dtype=dtype or float)

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            return np.asarray(self)[idx]
        return super().__getitem__(idx)


class MarkushEnumerationResult(dict):
    """Dictionary mapping label -> canonical SMILES while also exposing .products/.results metadata."""

    def __init__(self, mapping: dict[str, Any], meta: dict[str, Any] | None = None):
        super().__init__(mapping)
        self._meta = dict(meta or {})

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        if key in self._meta:
            return self._meta[key]
        raise KeyError(key)

    def get(self, key, default=None):
        if super().__contains__(key):
            return super().__getitem__(key)
        return self._meta.get(key, default)


def _mol(smiles: str | Chem.Mol | None) -> Chem.Mol | None:
    if isinstance(smiles, Chem.Mol):
        return Chem.Mol(smiles) if smiles.GetNumAtoms() else None
    mol = Chem.MolFromSmiles(str(smiles or ""))
    return mol if mol is not None and mol.GetNumAtoms() else None


def _parity(perm: list[int]) -> int:
    perm = list(perm)
    swaps = 0
    for i in range(len(perm)):
        while perm[i] != i:
            j = perm[i]
            perm[i], perm[j] = perm[j], perm[i]
            swaps += 1
    return swaps % 2


def cip_labels(mol: Chem.Mol | str) -> dict[int, str]:
    """Atom index -> R/S (or '?' when unassigned) for each tetrahedral stereocenter."""
    parsed = _mol(mol)
    if parsed is None:
        return {}
    m = Chem.Mol(parsed)
    rdCIPLabeler.AssignCIPLabels(m)
    return {
        i: m.GetAtomWithIdx(i).GetPropsAsDict().get("_CIPCode", c)
        for i, c in Chem.FindMolChiralCenters(m, includeUnassigned=True, useLegacyImplementation=False)
    }


def mcs_map(tgt: Chem.Mol, src: Chem.Mol, timeout: int = 20) -> tuple[dict[int, int], int]:
    """Source atom index -> target atom index over the maximum common substructure, and its size."""
    res = rdFMCS.FindMCS(
        [tgt, src],
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareOrder,
        ringMatchesRingOnly=True,
        completeRingsOnly=True,
        timeout=timeout,
    )
    if res.numAtoms < 0.6 * min(tgt.GetNumHeavyAtoms(), src.GetNumHeavyAtoms()):
        res = rdFMCS.FindMCS(
            [tgt, src],
            atomCompare=rdFMCS.AtomCompare.CompareAny,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            timeout=timeout,
        )
    if not res.numAtoms:
        return {}, 0
    patt = Chem.MolFromSmarts(res.smartsString)
    if patt is None:
        return {}, 0
    src_match = src.GetSubstructMatch(patt)
    tgt_match = tgt.GetSubstructMatch(patt)
    if not src_match or not tgt_match:
        return {}, 0
    return dict(zip(src_match, tgt_match)), res.numAtoms


def copy_stereo(tgt: Chem.Mol, src: Chem.Mol, s2t: dict[int, int]) -> tuple[Chem.Mol, list[dict]]:
    """Target molecule (same atom order) carrying the source's tetrahedral stereo over the atom map s2t."""
    centers = []
    out = Chem.RWMol(tgt)
    for a in out.GetAtoms():
        a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
    for sa in src.GetAtoms():
        tag = sa.GetChiralTag()
        if tag not in (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW):
            continue
        si = sa.GetIdx()
        if si not in s2t:
            centers.append({"source_atom": si, "status": "unmapped"})
            continue
        ti = s2t[si]
        ta = out.GetAtomWithIdx(ti)
        s_nbrs = [b.GetOtherAtomIdx(si) for b in sa.GetBonds()]
        t_nbrs = [b.GetOtherAtomIdx(ti) for b in ta.GetBonds()]
        mapped = [s2t.get(n) for n in s_nbrs]
        missing_t = [n for n in t_nbrs if n not in mapped]
        if mapped.count(None) == 1 and len(missing_t) == 1:
            mapped[mapped.index(None)] = missing_t[0]
        if None in mapped or len(mapped) != len(t_nbrs) or sorted(mapped) != sorted(t_nbrs):
            centers.append({"source_atom": si, "target_atom": ti, "status": "ambiguous"})
            continue
        perm = [t_nbrs.index(m) for m in mapped]
        flip = _parity(perm) == 1
        if len(s_nbrs) == 3 and (sa.GetTotalNumHs() == 1) != (ta.GetTotalNumHs() == 1):
            centers.append({"source_atom": si, "target_atom": ti, "status": "hydrogen mismatch"})
            continue
        new = (
            tag
            if not flip
            else (
                Chem.ChiralType.CHI_TETRAHEDRAL_CCW
                if tag == Chem.ChiralType.CHI_TETRAHEDRAL_CW
                else Chem.ChiralType.CHI_TETRAHEDRAL_CW
            )
        )
        ta.SetChiralTag(new)
        centers.append({"source_atom": si, "target_atom": ti, "status": "copied"})
    mol = out.GetMol()
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    return mol, centers


def _count_specified_tetrahedral(mol: Chem.Mol) -> int:
    tetra = (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW)
    return sum(1 for a in mol.GetAtoms() if a.GetChiralTag() in tetra)


def transfer_stereo(
    src_mol: Chem.Mol | str,
    dst_mol: Chem.Mol | str,
    timeout: int = 20,
) -> TransferStereoResult:
    """Transfer tetrahedral stereocenters from src_mol onto dst_mol over their MCS map.

    Also supports (target_flat, source_chiral) argument ordering when the first
    argument has no specified tetrahedral stereocenters and the second does.
    """
    m1 = _mol(src_mol)
    m2 = _mol(dst_mol)
    if m1 is None or m2 is None:
        raise ValueError("invalid SMILES or molecule for transfer_stereo")
    if _count_specified_tetrahedral(m1) == 0 and _count_specified_tetrahedral(m2) > 0:
        src, tgt = m2, m1
    else:
        src, tgt = m1, m2
    s2t, n = mcs_map(tgt, src, timeout)
    mol, centers = copy_stereo(tgt, src, s2t)
    smiles = Chem.MolToSmiles(mol)
    report = {
        "mcs_atoms": n,
        "target_atoms": tgt.GetNumHeavyAtoms(),
        "source_atoms": src.GetNumHeavyAtoms(),
        "centers": centers,
        "atom_map": s2t,
        "cip_labels": cip_labels(mol),
    }
    return TransferStereoResult(smiles, mol, report)


def _stereo_from_wedges_mapped(
    mapped_smiles: str,
    centers: dict[int, dict[int, tuple]],
    *,
    flip_y: bool = True,
) -> str:
    """Assign tetrahedral centers from wedge drawings on an atom-mapped SMILES."""
    params = Chem.SmilesParserParams()
    params.removeHs = False
    mol = Chem.MolFromSmiles(mapped_smiles, params)
    if mol is None:
        raise ValueError("invalid mapped SMILES")
    by_map = {a.GetAtomMapNum(): a.GetIdx() for a in mol.GetAtoms() if a.GetAtomMapNum()}
    final = Chem.RWMol(mol)
    y_sign = -1.0 if flip_y else 1.0
    for cmap, nbrs in centers.items():
        work = Chem.RWMol(mol)
        c = by_map[cmap]
        missing = [
            n.GetIdx()
            for n in mol.GetAtomWithIdx(c).GetNeighbors()
            if n.GetAtomicNum() > 1 and n.GetAtomMapNum() not in nbrs
        ]
        if missing:
            raise ValueError(f"center {cmap}: directions missing for neighbour atom(s) {missing}")
        rdDepictor.Compute2DCoords(work)
        conf = work.GetConformer()
        conf.SetAtomPosition(c, (0.0, 0.0, 0.0))
        for nmap, (dx, dy, kind) in nbrs.items():
            n = by_map[nmap]
            length = (dx * dx + dy * dy) ** 0.5 or 1.0
            conf.SetAtomPosition(n, (dx / length, y_sign * dy / length, 0.0))
            bond = work.GetBondBetweenAtoms(c, n)
            order = bond.GetBondType()
            work.RemoveBond(c, n)
            work.AddBond(c, n, order)
            bond = work.GetBondBetweenAtoms(c, n)
            norm_kind = KINDS.get(str(kind).lower().strip(), "plain")
            bond.SetBondDir(
                {
                    "wedge": Chem.BondDir.BEGINWEDGE,
                    "hash": Chem.BondDir.BEGINDASH,
                }.get(norm_kind, Chem.BondDir.NONE)
            )
        m = work.GetMol()
        Chem.SanitizeMol(m)
        Chem.AssignChiralTypesFromBondDirs(m)
        tag = m.GetAtomWithIdx(c).GetChiralTag()
        wedged = any(KINDS.get(str(v[2]).lower().strip(), "plain") in ("wedge", "hash") for v in nbrs.values())
        if tag not in (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW):
            if wedged:
                raise ValueError(f"center {cmap}: the wedges do not define a tetrahedral configuration")
            continue
        # Copy the tag by neighbour-order parity (bond order differs between work and final),
        # so centres without an R/S label (ring cis/trans, pseudoasymmetric) survive.
        order_m = [b.GetOtherAtomIdx(c) for b in m.GetAtomWithIdx(c).GetBonds()]
        order_f = [b.GetOtherAtomIdx(c) for b in final.GetAtomWithIdx(c).GetBonds()]
        perm = [order_m.index(i) for i in order_f]
        swaps = sum(1 for i in range(len(perm)) for j in range(i + 1, len(perm)) if perm[i] > perm[j])
        if swaps % 2:
            tag = (
                Chem.ChiralType.CHI_TETRAHEDRAL_CCW
                if tag == Chem.ChiralType.CHI_TETRAHEDRAL_CW
                else Chem.ChiralType.CHI_TETRAHEDRAL_CW
            )
        final.GetAtomWithIdx(c).SetChiralTag(tag)
    out = final.GetMol()
    for a in out.GetAtoms():
        a.SetAtomMapNum(0)
    Chem.AssignStereochemistry(out, cleanIt=True, force=True)
    return Chem.MolToSmiles(Chem.RemoveHs(out))


def _atom_from_symbol(symbol: str, charge: int = 0) -> Chem.Atom:
    sym = str(symbol or "C").strip()
    if sym.startswith("[") and sym.endswith("]"):
        sub = Chem.MolFromSmiles(sym, sanitize=False)
        if sub is not None and sub.GetNumAtoms() == 1:
            atom = Chem.Atom(sub.GetAtomWithIdx(0))
            atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
            if charge:
                atom.SetFormalCharge(int(charge))
            return atom
        sym = sym[1:-1].strip()
    pt = Chem.GetPeriodicTable()
    num = 0
    if sym and sym not in ("*", "R", "X", "Ar", "Ph", "Me", "Et", "Pr", "Bu", "Bn", "Bz", "Ac", "Boc", "TBS", "OTBS", "TMS", "TIPS"):
        try:
            cand_sym = sym[0].upper() + sym[1:].lower() if len(sym) <= 2 and sym.isalpha() else ""
            if cand_sym:
                num = pt.GetAtomicNumber(cand_sym)
        except Exception:
            num = 0
    atom = Chem.Atom(max(0, num))
    if charge:
        atom.SetFormalCharge(int(charge))
    return atom


def _build_mol_from_atoms_bonds(
    atoms: list[dict[str, Any]],
    bonds: list[dict[str, Any]],
    *,
    flip_y: bool = True,
) -> tuple[Chem.Mol, dict[int, list[float]]]:
    """Construct an RDKit molecule with a 2D conformer and bond dirs from atom/bond dicts."""
    rw = Chem.RWMol()
    for idx, a in enumerate(atoms):
        sym = a.get("symbol", a.get("element", "C"))
        charge = int(a.get("charge", 0) or 0)
        rd_atom = _atom_from_symbol(sym, charge=charge)
        rd_atom.SetIntProp("ms_i", idx)
        rw.AddAtom(rd_atom)

    degrees = Counter()
    parsed_bonds = []
    for b in bonds or []:
        pair = b.get("atoms")
        if pair is None:
            pair = [b.get("begin", b.get("u")), b.get("end", b.get("v"))]
        u, v = int(pair[0]), int(pair[1])
        degrees[u] += 1
        degrees[v] += 1
        parsed_bonds.append((u, v, b))

    wedge_conf_by_atom: dict[int, list[float]] = {}
    for u, v, b in parsed_bonds:
        raw_type = str(b.get("type", b.get("order", "single"))).lower().strip()
        kind = KINDS.get(raw_type, "plain")
        if kind in ("wedge", "hash"):
            order = Chem.BondType.SINGLE
        else:
            order = _BOND_TYPE_BY_NAME.get(raw_type, Chem.BondType.SINGLE)
        # Ensure the stereocenter (higher-degree atom when the other is degree 1) is the begin atom
        begin, end, eff_kind = u, v, kind
        if kind in ("wedge", "hash") and degrees[u] == 1 and degrees[v] >= 3:
            begin, end = v, u
            if b.get("molscribe_convention"):
                eff_kind = "hash" if kind == "wedge" else "wedge"
        if rw.GetBondBetweenAtoms(begin, end) is None:
            rw.AddBond(begin, end, order)
        bond = rw.GetBondBetweenAtoms(begin, end)
        if eff_kind == "wedge":
            bond.SetBondDir(Chem.BondDir.BEGINWEDGE)
        elif eff_kind == "hash":
            bond.SetBondDir(Chem.BondDir.BEGINDASH)
        if kind in ("wedge", "hash"):
            b_conf = b.get("confidence")
            val = float(b_conf) if b_conf is not None else float(atoms[begin].get("confidence", 1.0) or 1.0)
            wedge_conf_by_atom.setdefault(begin, []).append(val)
            wedge_conf_by_atom.setdefault(end, []).append(val)

    conf = Chem.Conformer(len(atoms))
    y_sign = -1.0 if flip_y else 1.0
    for idx, a in enumerate(atoms):
        x = float(a.get("x", 0.0))
        y = float(a.get("y", 0.0))
        conf.SetAtomPosition(idx, (x, y_sign * y, 0.0))
    mol = rw.GetMol()
    mol.AddConformer(conf, assignId=True)
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        mol.UpdatePropertyCache(strict=False)
        Chem.FastFindRings(mol)
    Chem.AssignChiralTypesFromBondDirs(mol)
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    rdCIPLabeler.AssignCIPLabels(mol)
    return mol, wedge_conf_by_atom


def stereo_from_wedges(
    atoms: list[dict[str, Any]] | str,
    bonds: list[dict[str, Any]] | dict[int, dict[int, tuple]],
    *,
    flip_y: bool = True,
) -> StereoFromWedgesResult | str:
    """Build an RDKit 2D conformer from MolScribe (x, y) + wedges and extract per-atom (R/S, confidence).

    Also supports the atom-mapped SMILES signature stereo_from_wedges(mapped_smiles, centers).
    """
    if isinstance(atoms, str):
        return _stereo_from_wedges_mapped(atoms, bonds, flip_y=flip_y)

    mol, wedge_conf_by_atom = _build_mol_from_atoms_bonds(list(atoms), list(bonds), flip_y=flip_y)
    cips = cip_labels(mol)
    centers: dict[int, tuple[str, float]] = {}
    details: list[dict[str, Any]] = []
    for idx, label in sorted(cips.items()):
        if label not in ("R", "S") and idx not in wedge_conf_by_atom:
            continue
        w_confs = wedge_conf_by_atom.get(idx)
        if w_confs:
            conf_val = float(min(w_confs))
        else:
            atom_conf = atoms[idx].get("confidence") if idx < len(atoms) else None
            conf_val = float(atom_conf) if atom_conf is not None else 1.0
        centers[idx] = (label, conf_val)
        details.append({"atom": idx, "cip": label, "confidence": conf_val})

    mol_no_h = Chem.RemoveHs(mol, sanitize=False)
    try:
        Chem.SanitizeMol(mol_no_h)
    except Exception:
        mol_no_h.UpdatePropertyCache(strict=False)
    Chem.AssignStereochemistry(mol_no_h, cleanIt=True, force=True)
    smiles = Chem.MolToSmiles(mol_no_h)
    return StereoFromWedgesResult(
        {
            "smiles": smiles,
            "centers": centers,
            "cip_labels": {idx: lab for idx, (lab, _) in centers.items()},
            "confidence": {idx: conf for idx, (_, conf) in centers.items()},
            "details": details,
        },
        mol=mol_no_h,
    )


def _counts(mol: Chem.Mol) -> Counter:
    c: Counter = Counter()
    for a in mol.GetAtoms():
        c[a.GetSymbol()] += 1
        c["H"] += a.GetTotalNumHs()
    return c


def _delta(a: Chem.Mol, b: Chem.Mol) -> str:
    ca, cb = _counts(a), _counts(b)
    parts = [
        f"{'+' if ca[e] > cb[e] else '-'}{abs(ca[e] - cb[e])}{e}"
        for e in sorted(set(ca) | set(cb))
        if ca[e] != cb[e]
    ]
    return " ".join(parts)


def _rings(mol: Chem.Mol) -> list[int]:
    return sorted(len(r) for r in mol.GetRingInfo().AtomRings())


def mol_key(mol: Chem.Mol, stereo: bool = True) -> str:
    """Identity key of a molecule: InChIKey or canonical SMILES when dummy atoms are present."""
    if not any(a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
        key = Chem.MolToInchiKey(mol)
        if key:
            return key if stereo else key.split("-")[0]
    m = Chem.Mol(mol)
    for a in m.GetAtoms():
        if a.GetAtomicNum() == 0:
            a.SetAtomMapNum(0)
            a.SetIsotope(0)
    return "smiles:" + Chem.MolToSmiles(m, isomericSmiles=stereo)


def stereo_compare(cand: Chem.Mol, src: Chem.Mol, s2t: dict[int, int]) -> list[dict]:
    """Per candidate stereocenter: compare implied source label with candidate's own label."""
    img, centers = copy_stereo(cand, src, s2t)
    yours, theirs = cip_labels(cand), cip_labels(img)
    out, seen = [], set()
    for c in centers:
        t = c.get("target_atom")
        if t is None:
            continue
        seen.add(t)
        if c["status"] == "copied":
            if t in theirs:
                out.append(
                    {
                        "atom": t,
                        "source_atom": c["source_atom"],
                        "reading": theirs[t],
                        "yours": yours.get(t, "none"),
                        "same": theirs[t] == yours.get(t),
                    }
                )
        else:
            out.append(
                {
                    "atom": t,
                    "source_atom": c["source_atom"],
                    "reading": "?",
                    "yours": yours.get(t, "none"),
                    "same": None,
                    "note": c["status"],
                }
            )
    for t, lab in yours.items():
        if t not in seen and lab != "?":
            out.append({"atom": t, "reading": "none", "yours": lab, "same": None, "note": "no stereo in the reading"})
    return sorted(out, key=lambda x: x["atom"])


def reader_labels(yours: str, reader: str) -> dict[int, str] | None:
    """CIP label each stereocentre of yours has in reader's SMILES; None when skeletons differ."""
    a, b = _mol(yours), _mol(reader)
    if a is None or b is None or mol_key(a, False) != mol_key(b, False):
        return None
    match = b.GetSubstructMatch(a)
    s2t = {bi: ai for ai, bi in enumerate(match)} if match else mcs_map(a, b, 10)[0]
    return {c["atom"]: c["reading"] for c in stereo_compare(a, b, s2t) if c["reading"] in ("R", "S")}


def compare(
    a_smiles: str,
    b_smiles: str,
    a_name: str = "yours",
    b_name: str = "the reading",
    stereo: bool = True,
) -> list[str]:
    """Plain-language differences between two SMILES; atom indices are those of a_smiles."""
    a, b = _mol(a_smiles), _mol(b_smiles)
    if a is None or b is None:
        return [f"{b_name}: no valid SMILES to compare."]
    if mol_key(a) == mol_key(b):
        return [f"{b_name}: no difference from {a_name} (a reading, not a check of the image)."]
    if not stereo and mol_key(a, False) == mol_key(b, False):
        return [f"{b_name}: no skeleton difference from {a_name} (a reading, not a check of the image)."]
    lines = []
    if mol_key(a, False) == mol_key(b, False):
        match = b.GetSubstructMatch(a)
        s2t = {bi: ai for ai, bi in enumerate(match)} if match else mcs_map(a, b, 10)[0]
        head = f"{b_name}: no skeleton difference from {a_name}"
    else:
        s2t, _ = mcs_map(a, b, 10)
        common = set(s2t.values())
        outside = [f"{i} {a.GetAtomWithIdx(i).GetSymbol()}" for i in range(a.GetNumAtoms()) if i not in common]
        extra = b.GetNumAtoms() - len(s2t)
        head = (
            f"{b_name}: skeleton differs from {a_name}. Formula {a_name} {rdMolDescriptors.CalcMolFormula(a)}, "
            f"{b_name} {rdMolDescriptors.CalcMolFormula(b)} "
            + (
                f"({a_name} {_delta(a, b)} relative to {b_name}). "
                if _delta(a, b)
                else "(same formula: the same atoms connected differently, e.g. a substituent at another position). "
            )
            + f"Ring sizes {a_name} {_rings(a)}, {b_name} {_rings(b)}. "
        )
        head += (
            f"Atoms of {a_name} outside the common part: {', '.join(outside[:15])}"
            f"{' ...' if len(outside) > 15 else ''}"
            if outside
            else f"All atoms of {a_name} are in the common part"
        )
        head += f"; {b_name} has {extra} atom(s) not matched in {a_name}" if extra else ""
        lines.append(head + ".")
        head = None
    diff = [c for c in stereo_compare(a, b, s2t) if c["same"] is False] if stereo else []
    if diff:
        lines.append(
            (head + "; stereo differs at " if head else "Stereo on the common part differs at ")
            + "; ".join(f"atom {c['atom']} ({a_name} {c['yours']}, {b_name} {c['reading']})" for c in diff)
            + "."
        )
    elif head and stereo:
        lines.append(
            head
            + "; tetrahedral stereo agrees where both define it (the difference is elsewhere, "
            "e.g. a double-bond geometry or an undefined centre)."
        )
    return lines


def ms_mol(reading: dict) -> tuple[Chem.Mol | None, np.ndarray | None]:
    """Convert a MolScribe reading dict into an RDKit molecule and per-atom (x, y) pixel array."""
    if not isinstance(reading, dict) or reading.get("ok") is False:
        return None, None
    full = None
    if reading.get("molfile"):
        full = Chem.MolFromMolBlock(reading["molfile"], removeHs=False)
        if full is None:
            full = Chem.MolFromMolBlock(reading["molfile"], sanitize=False, removeHs=False)
            if full is not None:
                full.UpdatePropertyCache(strict=False)
                Chem.AssignChiralTypesFromBondDirs(full)
                Chem.AssignStereochemistry(full, cleanIt=True, force=True)
    atoms = reading.get("atoms") or []
    bonds = reading.get("bonds") or []
    if full is None and atoms and bonds:
        try:
            full, _ = _build_mol_from_atoms_bonds(atoms, bonds, flip_y=False)
        except Exception:
            full = None
    if full is None and reading.get("smiles"):
        full = Chem.MolFromSmiles(str(reading["smiles"]))
        if full is not None:
            for a in full.GetAtoms():
                a.SetIntProp("ms_i", a.GetIdx())
    if full is None:
        return None, None
    for a in full.GetAtoms():
        if not a.HasProp("ms_i"):
            a.SetIntProp("ms_i", a.GetIdx())
    mol = Chem.RemoveHs(full, sanitize=False)
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        mol.UpdatePropertyCache(strict=False)
        Chem.FastFindRings(mol)
    xy = None
    if atoms and len(atoms) >= full.GetNumAtoms():
        try:
            xy = np.array(
                [[float(atoms[a.GetIntProp("ms_i")]["x"]), float(atoms[a.GetIntProp("ms_i")]["y"])] for a in mol.GetAtoms()],
                dtype=float,
            )
        except Exception:
            xy = None
    elif atoms and len(atoms) == mol.GetNumAtoms():
        try:
            xy = np.array([[float(a["x"]), float(a["y"])] for a in atoms], dtype=float)
        except Exception:
            xy = None
    return mol, xy


_T = np.linspace(0.15, 0.85, 12)


def _along(ink: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Mean ink along the segments a -> b (arrays of points, last axis x/y)."""
    h, w = ink.shape
    sx = a[..., 0, None] + (b[..., 0, None] - a[..., 0, None]) * _T
    sy = a[..., 1, None] + (b[..., 1, None] - a[..., 1, None]) * _T
    return ink[np.clip(sy.round().astype(int), 0, h - 1), np.clip(sx.round().astype(int), 0, w - 1)].mean(-1)


def _open_image(image_or_path: str | Path | Image.Image) -> Image.Image:
    if isinstance(image_or_path, Image.Image):
        return image_or_path
    return Image.open(Path(image_or_path))


def _snap_core(
    image: Image.Image,
    xy: np.ndarray,
    bond_pairs: list[tuple[int, int]],
    num_atoms: int,
    extra: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    if not bond_pairs or len(xy) == 0:
        return xy.copy(), (None if extra is None else extra.copy())
    ink_arr = (np.asarray(image.convert("L").filter(ImageFilter.MinFilter(3)), float) < 150).astype(float)
    bonds = np.array(bond_pairs, dtype=int)
    length = float(np.median(np.hypot(*(xy[bonds[:, 0]] - xy[bonds[:, 1]]).T))) or 10.0
    c = xy.mean(0)
    scales = np.array([(a, b) for a in np.arange(0.7, 1.31, 0.05) for b in np.arange(0.7, 1.31, 0.05)])
    steps = np.arange(-0.6 * length, 0.6 * length + 0.1, max(1.0, length / 12))
    shifts = np.array([(a, b) for a in steps for b in steps])
    scale, shift = np.ones(2), np.zeros(2)
    for _ in range(3):
        pts = c + (xy[None] - c) * scales[:, None, :] + shift
        score = _along(ink_arr, pts[:, bonds[:, 0]], pts[:, bonds[:, 1]]).mean(1) - 0.01 * np.abs(scales - 1).sum(1)
        scale = scales[int(np.argmax(score))]
        pts = c + (xy[None] - c) * scale + shifts[:, None, :]
        score = _along(ink_arr, pts[:, bonds[:, 0]], pts[:, bonds[:, 1]]).mean(1) - 0.01 * np.hypot(*shifts.T) / length
        shift = shifts[int(np.argmax(score))]
    start = c + (xy - c) * scale + shift
    moved = None if extra is None else c + (extra - c) * scale + shift
    pts = start.copy()
    nbrs: list[list[int]] = [[] for _ in range(num_atoms)]
    for u, v in bond_pairs:
        if 0 <= u < num_atoms and 0 <= v < num_atoms:
            nbrs[u].append(v)
            nbrs[v].append(u)
    r = int(max(2, 0.3 * length))
    offs = np.array(
        [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if dx * dx + dy * dy <= r * r],
        float,
    )
    for _ in range(3):
        for i, nb in enumerate(nbrs):
            if nb:
                cands = start[i] + offs
                score = sum(_along(ink_arr, cands, np.broadcast_to(pts[j], cands.shape)) for j in nb) / len(nb)
                pts[i] = cands[int(np.argmax(score - 0.003 * np.hypot(*offs.T)))]
    return pts, moved


def snap_with(
    image_path: str | Path | Image.Image,
    atoms: list[dict[str, Any]] | Chem.Mol | np.ndarray,
    bonds: list[dict[str, Any]] | np.ndarray,
    extra: np.ndarray | None = None,
):
    """Align MolScribe 2D atom coordinates onto dark bond ink in image_path.

    Supports both:
    - snap_with(image_path, atoms, bonds): where atoms is a list of {'x', 'y', ...} dicts
      and bonds is a list of {'atoms': [u, v], ...} dicts.
    - snap_with(image, mol, xy, extra=None): where mol is an RDKit Mol and xy is an (N, 2) array.
    """
    image = _open_image(image_path)
    if isinstance(atoms, Chem.Mol):
        mol = atoms
        xy = np.asarray(bonds, dtype=float)
        bond_pairs = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()]
        return _snap_core(image, xy, bond_pairs, mol.GetNumAtoms(), extra=extra)

    atoms_list = list(atoms)
    if atoms_list and isinstance(atoms_list[0], dict):
        xy = np.array([[float(a["x"]), float(a["y"])] for a in atoms_list], dtype=float)
    else:
        xy = np.asarray(atoms, dtype=float)

    bond_pairs = []
    for b in bonds or []:
        if isinstance(b, dict):
            pair = b.get("atoms") or [b.get("begin", b.get("u")), b.get("end", b.get("v"))]
            bond_pairs.append((int(pair[0]), int(pair[1])))
        else:
            bond_pairs.append((int(b[0]), int(b[1])))

    pts, moved = _snap_core(image, xy, bond_pairs, len(xy), extra=extra)
    if extra is not None:
        return pts, moved
    out = SnappedPointsList()
    for idx, (nx, ny) in enumerate(pts):
        base = dict(atoms_list[idx]) if idx < len(atoms_list) and isinstance(atoms_list[idx], dict) else {}
        base["x"] = float(nx)
        base["y"] = float(ny)
        out.append(SnappedPoint(base))
    return out


def snap(image: Image.Image | str | Path, mol: Chem.Mol, xy: np.ndarray) -> np.ndarray:
    """MolScribe atom positions moved onto the drawn bonds."""
    return snap_with(image, mol, xy)[0]


def _wedges(
    reading: dict,
    mol: Chem.Mol,
    s2t: dict[int, int],
    centres: set[int],
    xy: np.ndarray | None = None,
    hpos: dict[int, np.ndarray] | None = None,
) -> dict[int, list[dict]]:
    """Extract MolScribe wedge and hash bonds mapped to candidate stereocenters."""
    full2red = {a.GetIntProp("ms_i"): a.GetIdx() for a in mol.GetAtoms() if a.HasProp("ms_i")}
    if not full2red:
        full2red = {i: i for i in range(mol.GetNumAtoms())}
    flip = {"wedge": "hash", "hash": "wedge"}
    out: dict[int, list[dict]] = {}
    for b in reading.get("bonds") or []:
        raw_type = str(b.get("type", "")).lower().strip()
        kind = KINDS.get(raw_type)
        if kind not in ("wedge", "hash"):
            if "wedge" in raw_type:
                kind = "wedge" if raw_type.startswith("solid") else "hash"
            else:
                continue
        pair = b.get("atoms") or [b.get("begin", b.get("u")), b.get("end", b.get("v"))]
        i, j = int(pair[0]), int(pair[1])
        for c_ms, n_ms, k in ((i, j, kind), (j, i, flip[kind])):
            c = s2t.get(full2red.get(c_ms, -1))
            if c is None or c not in centres:
                continue
            n = "H" if n_ms not in full2red else s2t.get(full2red[n_ms])
            if n is not None:
                entry = {"atom": c, "neighbor": n, "kind": k, "confidence": b.get("confidence")}
                if n == "H" and xy is not None and hpos and n_ms in hpos:
                    entry["dir"] = [float(v) for v in hpos[n_ms] - xy[full2red[c_ms]]]
                out.setdefault(c, []).append(entry)
    return out


def _extend(cand: Chem.Mol, mol: Chem.Mol, s2t: dict[int, int]) -> dict[int, int]:
    """Pair a lone unmapped candidate neighbor with a lone unmapped reading neighbor around each mapped atom."""
    ext = dict(s2t)
    for s, t in s2t.items():
        open_c = [n.GetIdx() for n in cand.GetAtomWithIdx(t).GetNeighbors() if n.GetIdx() not in ext.values()]
        open_r = [n.GetIdx() for n in mol.GetAtomWithIdx(s).GetNeighbors() if n.GetIdx() not in ext]
        if len(open_c) == 1 and len(open_r) == 1:
            ext[open_r[0]] = open_c[0]
    return ext


def audit_stereo_wedges(
    candidate_smiles: str,
    molscribe_reading: dict,
    image_path: str | Path | Image.Image | None = None,
) -> dict:
    """Map candidate_smiles onto molscribe_reading via MCS and return stereocenter agreement/conflict diagnostics."""
    cand = _mol(candidate_smiles)
    mol, xy = ms_mol(molscribe_reading)
    if cand is None or mol is None:
        return {
            "status": "unusable",
            "agreed": [],
            "conflicts": [],
            "missing_in_candidate": [],
            "unreadable_in_image": [],
            "centers": [],
            "coverage": 0.0,
            "s2t": {},
            "mol": mol,
            "xy": xy,
            "cand": cand,
            "pos": {},
        }
    atoms = molscribe_reading.get("atoms") or []
    h_ms = [i for i, at in enumerate(atoms) if str(at.get("symbol", "")).strip("[]") == "H"]
    h_raw = np.array([[atoms[i]["x"], atoms[i]["y"]] for i in h_ms], float) if h_ms else None
    hxy = h_raw
    if image_path is not None and xy is not None:
        image = _open_image(image_path)
        xy, hxy = snap_with(image, mol, xy, h_raw)
    hpos = dict(zip(h_ms, hxy)) if hxy is not None else {}
    s2t, _ = mcs_map(cand, mol, 10)
    real = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() > 0]
    coverage = sum(i in s2t for i in real) / max(1, len(real))
    yours = cip_labels(cand)
    ext = _extend(cand, mol, s2t)
    wedges = _wedges(molscribe_reading, mol, ext, set(yours), xy, hpos) if xy is not None else {}
    pos = {t: (float(xy[s][0]), float(xy[s][1])) for s, t in ext.items()} if xy is not None else {}
    fallback_by_atom = {c["atom"]: c for c in stereo_compare(cand, mol, s2t)}

    centers = []
    agreed = []
    conflicts = []
    missing_in_candidate = []
    unreadable_in_image = []

    for c in sorted(yours):
        cand_label = yours.get(c, "none")
        entry: dict[str, Any] = {
            "atom": c,
            "yours": cand_label,
            "candidate": cand_label,
            "reading": "none",
            "same": None,
        }
        label = None
        conf_val = None
        if c in wedges and pos:
            try:
                new, _ = read_wedges(candidate_smiles, wedges[c], [pos])
                newmol = _mol(new)
                if newmol is not None:
                    match = newmol.GetSubstructMatch(cand)
                    if match:
                        label = cip_labels(newmol).get(match[c])
                        conf_val = min(
                            (float(w["confidence"]) if w.get("confidence") is not None else 1.0)
                            for w in wedges[c]
                        )
            except (ValueError, IndexError) as exc:
                entry["note"] = f"wedge not usable: {exc}"
        if label is None and c in fallback_by_atom:
            fb = fallback_by_atom[c]
            if fb.get("reading") in ("R", "S"):
                label = fb["reading"]
                conf_val = float(molscribe_reading.get("confidence", 1.0) or 1.0)

        if label in ("R", "S"):
            entry["reading"] = label
            if conf_val is not None:
                entry["confidence"] = conf_val
            if cand_label in ("R", "S"):
                is_same = label == cand_label
                entry["same"] = is_same
                if is_same:
                    entry["status"] = "agreed"
                    agreed.append(entry)
                else:
                    entry["status"] = "conflict"
                    conflicts.append(entry)
            else:
                entry["same"] = None
                entry["status"] = "missing_in_candidate"
                entry["note"] = "stereocenter has wedge in reading but is unassigned in candidate"
                missing_in_candidate.append(entry)
        else:
            if "note" not in entry:
                entry["note"] = "no wedge read at this centre" if c in set(s2t.values()) else "not mapped"
            if cand_label in ("R", "S"):
                entry["status"] = "unreadable_in_image"
                unreadable_in_image.append(entry)
            else:
                entry["status"] = "unassigned"
        centers.append(entry)

    if conflicts:
        status = "conflict"
    elif missing_in_candidate:
        status = "missing_stereo"
    elif agreed and not unreadable_in_image:
        status = "agreed"
    elif agreed:
        status = "partial"
    elif unreadable_in_image:
        status = "unreadable"
    else:
        status = "no_stereo"

    return {
        "status": status,
        "agreed": agreed,
        "conflicts": conflicts,
        "missing_in_candidate": missing_in_candidate,
        "unreadable_in_image": unreadable_in_image,
        "centers": centers,
        "coverage": coverage,
        "s2t": s2t,
        "mol": mol,
        "xy": xy,
        "cand": cand,
        "pos": pos,
    }


def audit(cand_smiles: str, reading: dict, image: Image.Image | str | Path | None = None) -> dict | None:
    """Backward-compatible wrapper around audit_stereo_wedges returning None when unusable."""
    res = audit_stereo_wedges(cand_smiles, reading, image_path=image)
    if res.get("status") == "unusable":
        return None
    return res


def audit_text(a: dict, confidence: float | None = None) -> str:
    """Format human-readable stereocenter audit report."""
    conf = f", confidence {confidence:.2f}" if confidence is not None else ""
    checked = [c for c in a["centers"] if c["same"] is not None]
    bad = [c for c in checked if not c["same"]]
    lines = [
        f"Stereo check: the wedges MolScribe found in this box{conf}, at its atom positions snapped onto the "
        "drawn bonds, turned into R/S by RDKit on your skeleton:"
    ]
    if not a["centers"]:
        lines.append("  no stereocenters in your SMILES or in the reading.")
    weak = confidence is not None and confidence < WEAK
    for c in bad:
        wc = c.get("confidence") or 0
        if wc < WEAK or weak:
            lines.append(
                f"  atom {c['atom']}: a low-confidence wedge reading (wedge {wc:.2f}"
                f"{f', whole reading {confidence:.2f}' if weak else ''}) gives {c['reading']}, your SMILES has "
                f"{c['yours']}. This is only a hint: MolScribe is often wrong at this confidence; decide from the "
                "image, and keep your reading if the wedges there look as you wrote them."
            )
        else:
            lines.append(
                f"  atom {c['atom']}: the image wedges give {c['reading']}, your SMILES has {c['yours']}  "
                f"<-- differs (wedge confidence {wc:.2f})"
            )
    if checked and not bad:
        lines.append(f"  all {len(checked)} centre(s) MolScribe could map agree with your SMILES.")
    elif checked:
        lines.append(f"  {len(checked) - len(bad)} other centre(s) agree.")
    rest = [c for c in a["centers"] if c["same"] is None]
    if rest:
        lines.append("  not checked: " + ", ".join(f"atom {c['atom']} ({c.get('note', '')})" for c in rest) + ".")
    if bad:
        lines.append(
            "  MolScribe misreads wedges too: zoom on each differing centre (the patches below) and decide "
            "from the image; then fix it with read_wedges or edit_structure."
        )
    return "\n".join(lines)


def _render_overlay_with_stats(
    crop: Image.Image,
    a: dict,
    max_patches: int = 4,
) -> tuple[Image.Image | None, dict[str, int]]:
    xy, mol, cand, s2t = a["xy"], a["mol"], a["cand"], a["s2t"]
    if xy is None or mol is None or cand is None:
        return None, {"shared_bonds": 0, "candidate_only_bonds": 0, "reading_only_bonds": 0, "patch_count": 0}
    t2s = {t: s for s, t in s2t.items()}
    f = max(1.0, 700 / max(crop.size))
    base = crop.convert("RGB").resize((round(crop.width * f), round(crop.height * f)), Image.LANCZOS)
    im = Image.blend(base, Image.new("RGB", base.size, "white"), 0.6)
    d = ImageDraw.Draw(im)
    p = lambda s: (float(xy[s][0] * f), float(xy[s][1] * f))  # noqa: E731
    shared_bonds = 0
    cand_only_bonds = 0
    reading_only_bonds = 0
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if mol.GetAtomWithIdx(i).GetAtomicNum() == 0 or mol.GetAtomWithIdx(j).GetAtomicNum() == 0:
            continue
        if i not in s2t or j not in s2t or cand.GetBondBetweenAtoms(s2t[i], s2t[j]) is None:
            d.line([p(i), p(j)], fill=BLUE, width=5)
            reading_only_bonds += 1
    for b in cand.GetBonds():
        i, j = t2s.get(b.GetBeginAtomIdx()), t2s.get(b.GetEndAtomIdx())
        if i is None or j is None:
            cand_only_bonds += 1
            continue
        ok = mol.GetBondBetweenAtoms(i, j) is not None
        if ok:
            shared_bonds += 1
        else:
            cand_only_bonds += 1
        d.line([p(i), p(j)], fill=GREEN if ok else RED, width=3 if ok else 5)
    for s in range(mol.GetNumAtoms()):
        if s not in s2t and mol.GetAtomWithIdx(s).GetAtomicNum() > 0:
            x, y = p(s)
            d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=BLUE, width=3)
    bad = [c for c in a["centers"] if c["same"] is False and c["atom"] in t2s]
    for c in a["centers"]:
        if c["atom"] in t2s:
            x, y = p(t2s[c["atom"]])
            col = RED if c["same"] is False else (0, 0, 0)
            if c["same"] is False:
                d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=RED, width=3)
            d.text((x + 9, y - 22), f"{c['atom']}:{c['yours']}", fill=col, font=_BIG)
    d.text(
        (6, 4),
        "green: bond in both   red: only in your SMILES   blue: only in the MolScribe reading",
        fill=(0, 0, 0),
        font=_FONT,
    )
    patches = []
    if bad:
        lengths = [np.hypot(*(xy[b.GetBeginAtomIdx()] - xy[b.GetEndAtomIdx()])) for b in mol.GetBonds()]
        r = 1.8 * float(np.median(lengths)) if lengths else 40.0
        for c in bad[:max_patches]:
            s = t2s[c["atom"]]
            cx, cy = xy[s]
            box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
            g = 240 / (2 * r)
            patch = crop.convert("RGB").crop(box).resize((240, 240), Image.LANCZOS)
            pd = ImageDraw.Draw(patch)
            for n in [s] + [nb.GetIdx() for nb in mol.GetAtomWithIdx(s).GetNeighbors()]:
                if n in s2t:
                    px, py = (xy[n][0] - box[0]) * g, (xy[n][1] - box[1]) * g
                    pd.text((px + 5, py - 18), str(s2t[n]), fill=RED if n == s else BLUE, font=_BIG)
            title = Image.new("RGB", (240, 22), "white")
            ImageDraw.Draw(title).text(
                (3, 3),
                f"atom {c['atom']}: image {c['reading']}, yours {c['yours']}",
                fill=RED,
                font=_FONT,
            )
            col = Image.new("RGB", (240, 262), "white")
            col.paste(title, (0, 0))
            col.paste(patch, (0, 22))
            patches.append(col)
    stats = {
        "shared_bonds": shared_bonds,
        "candidate_only_bonds": cand_only_bonds,
        "reading_only_bonds": reading_only_bonds,
        "patch_count": len(patches),
    }
    if not patches:
        return im, stats
    h = max(im.height, 262 * ((len(patches) + 1) // 2))
    out = Image.new("RGB", (im.width + 10 + 245 * min(2, len(patches)), h), "white")
    out.paste(im, (0, 0))
    for k, pt in enumerate(patches):
        out.paste(pt, (im.width + 10 + 245 * (k % 2), 262 * (k // 2)))
    return out, stats


def overlay(crop: Image.Image, a: dict, max_patches: int = 4) -> Image.Image | None:
    """Candidate bonds drawn at MolScribe's atom positions over the washed-out crop plus zoomed conflict patches."""
    im, _ = _render_overlay_with_stats(crop, a, max_patches=max_patches)
    return im


def render_diff_overlay(
    image_path: str | Path | Image.Image,
    candidate_smiles: str,
    molscribe_reading: dict,
    output_path: str | Path | None = None,
) -> ImageResultDict:
    """Render green (shared), red (candidate-only), and blue (reading-only) bond overlays plus 240x240 patches."""
    crop = _open_image(image_path)
    audit_res = audit_stereo_wedges(candidate_smiles, molscribe_reading, image_path=crop)
    im, stats = _render_overlay_with_stats(crop, audit_res)
    if im is None:
        im = crop.convert("RGB")
    out_str = None
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        im.save(target)
        out_str = str(target.resolve())
    return ImageResultDict(
        {
            "ok": True,
            "output_path": out_str,
            "width": im.width,
            "height": im.height,
            "size": [im.width, im.height],
            "status": audit_res["status"],
            "agreed": audit_res["agreed"],
            "conflicts": audit_res["conflicts"],
            "missing_in_candidate": audit_res["missing_in_candidate"],
            "unreadable_in_image": audit_res["unreadable_in_image"],
            "coverage": audit_res["coverage"],
            **stats,
        },
        image=im,
    )


def _centre_list(mol: Chem.Mol) -> str:
    cs = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    return (
        "; ".join(
            f"atom {i} ({', '.join(f'{n.GetIdx()} {n.GetSymbol()}' for n in mol.GetAtomWithIdx(i).GetNeighbors())})"
            for i, _ in cs
        )
        or "none"
    )


def read_wedges(
    smiles: str,
    wedges: list[dict],
    positions: list[dict[int, tuple[float, float]]] | dict[int, tuple[float, float]] | None = None,
) -> ReadWedgesResult:
    """Set stereocenters in smiles from visual wedges and return canonical SMILES + per-center CIP labels."""
    mol = _mol(smiles)
    if mol is None:
        raise ValueError("the SMILES does not parse")
    by_center: dict[int, dict] = {}
    hdir: dict[int, tuple[float, float]] = {}
    for b in wedges:
        try:
            c = int(b["atom"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"each wedge needs an integer atom index, got {b.get('atom')!r}") from None
        nb = b.get("neighbor")
        kind = KINDS.get(str(b.get("kind", "")).lower().strip())
        if kind is None:
            raise ValueError(f"atom {c}: kind must be wedge, hash or plain, not {b.get('kind')!r}")
        if not 0 <= c < mol.GetNumAtoms():
            raise ValueError(
                f"atom {c} is not in the SMILES, which has atoms 0 to {mol.GetNumAtoms() - 1}; "
                f"stereocentres: {_centre_list(mol)}"
            )
        try:
            nb = "H" if str(nb).upper() == "H" else int(nb)
        except (TypeError, ValueError):
            raise ValueError(f"atom {c}: neighbor must be an atom index or \"H\", got {nb!r}") from None
        if nb != "H" and mol.GetBondBetweenAtoms(c, nb) is None:
            near = ", ".join(f"{n.GetIdx()} {n.GetSymbol()}" for n in mol.GetAtomWithIdx(c).GetNeighbors())
            raise ValueError(f"atoms {c} and {nb} are not bonded in this SMILES; atom {c} is bonded to {near}")
        if nb == "H" and mol.GetAtomWithIdx(c).GetTotalNumHs() != 1:
            near = ", ".join(f"{n.GetIdx()} {n.GetSymbol()}" for n in mol.GetAtomWithIdx(c).GetNeighbors())
            raise ValueError(
                f"atom {c} has no single implicit H to carry a wedge; its neighbours are {near}. "
                "Give the wedge as one of these atom indices (a wedge to a drawn H label only counts "
                "when the atom has exactly one H)"
            )
        if nb == "H":
            d = b.get("dir") or _COMPASS.get(str(b.get("h_at", "")).lower().replace(" ", "-").replace("_", "-"))
            if d is not None:
                hdir[c] = (float(d[0]), float(d[1]))
            elif b.get("h_at"):
                raise ValueError(f"h_at must be one of {', '.join(_COMPASS)}, not {b.get('h_at')!r}")
        by_center.setdefault(c, {})[nb] = kind

    for c, nbs in by_center.items():
        if not any(k != "plain" for k in nbs.values()):
            raise ValueError(f"atom {c}: no wedge or hash given; list the wedge or hashed bond at this centre")
    for c, nbs in by_center.items():
        if "H" in nbs and c not in hdir and any(k != "plain" for n, k in nbs.items() if n != "H"):
            del nbs["H"]

    if positions is None:
        mol_2d = Chem.Mol(mol)
        rdDepictor.Compute2DCoords(mol_2d)
        conf_2d = mol_2d.GetConformer()
        default_pos = {
            i: (float(conf_2d.GetAtomPosition(i).x), float(-conf_2d.GetAtomPosition(i).y))
            for i in range(mol_2d.GetNumAtoms())
        }
        pos_list = [default_pos]
        used_default = True
    elif isinstance(positions, dict):
        pos_list = [positions]
        used_default = False
    else:
        pos_list = list(positions)
        used_default = False

    h_centers = [c for c, nbs in by_center.items() if "H" in nbs]
    molh = Chem.AddHs(mol, onlyOnAtoms=tuple(h_centers)) if h_centers else Chem.Mol(mol)
    for a in molh.GetAtoms():
        a.SetAtomMapNum(a.GetIdx() + 1)
    centers, notes = {}, []
    for c, nbs in by_center.items():
        heavy = [n.GetIdx() for n in mol.GetAtomWithIdx(c).GetNeighbors()]
        pos = next((pm for pm in pos_list if pm and c in pm and all(n in pm for n in heavy)), None)
        if pos is None:
            raise ValueError(f"atom {c}: no image positions for this centre and its neighbours")
        src = "rdkit_2d" if used_default else ("image" if pos is pos_list[0] else "drawing")
        cx, cy = pos[c]
        vec = {n: (pos[n][0] - cx, pos[n][1] - cy) for n in heavy}
        entry = {n + 1: (dx, dy, nbs.get(n, "plain")) for n, (dx, dy) in vec.items()}
        if "H" in nbs:
            h = next(n.GetIdx() for n in molh.GetAtomWithIdx(c).GetNeighbors() if n.GetAtomicNum() == 1)
            if c in hdir:
                hx, hy = hdir[c]
            else:
                units = [np.array(v) / (np.hypot(*v) or 1.0) for v in vec.values()]
                hx, hy = -sum(units) if np.hypot(*sum(units)) > 0.3 else (-units[0][1], units[0][0])
            entry[h + 1] = (float(hx), float(hy), nbs["H"])
        centers[c + 1] = entry
        notes.append((c, src))
    try:
        new = _stereo_from_wedges_mapped(Chem.MolToSmiles(molh), centers)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"RDKit could not set the stereocentres from these wedges ({type(exc).__name__}); check that "
            f"every wedge names a bonded neighbour of its atom. Stereocentres: {_centre_list(mol)}"
        ) from None
    newmol = _mol(new)
    match = newmol.GetSubstructMatch(mol) if newmol is not None else ()
    before, after = cip_labels(mol), cip_labels(newmol) if newmol is not None else {}
    out_notes = []
    mapped_cips: dict[int, str] = {}
    for i in range(mol.GetNumAtoms()):
        if match and i < len(match) and match[i] in after:
            mapped_cips[i] = after[match[i]]
    for c, src in notes:
        old = before.get(c, "none")
        now = after.get(match[c], "none") if match else "?"
        where = (
            "RDKit 2D coordinates"
            if src == "rdkit_2d"
            else ("MolScribe atom positions on the image" if src == "image" else "the compare_structure drawing")
        )
        out_notes.append(f"atom {c}: {old} -> {now}" if old != now else f"atom {c}: stays {now}")
        out_notes[-1] += f" (directions from {where})"
    return ReadWedgesResult(
        {
            "smiles": new,
            "canonical_smiles": new,
            "cip_labels": mapped_cips,
            "output_cip_labels": after,
            "notes": out_notes,
        }
    )


def stereo_notes(smiles: str) -> list[str]:
    """'atom 3 C: R' for each stereocenter, in the atom order of smiles."""
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return []
    rdCIPLabeler.AssignCIPLabels(mol)
    centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    return [
        f"atom {i} {mol.GetAtomWithIdx(i).GetSymbol()}: "
        f"{mol.GetAtomWithIdx(i).GetPropsAsDict().get('_CIPCode', c)}"
        for i, c in centers
    ]


def ink(im: Image.Image, n: int = 64) -> np.ndarray:
    g = im.convert("L")
    ys, xs = np.nonzero(np.asarray(g) < 200)
    if len(xs) == 0:
        return np.zeros((n, n))
    g = g.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).filter(ImageFilter.MinFilter(5))
    return (np.asarray(g.resize((n, n), Image.BILINEAR)) < 200).astype(float)


def _draw_acs(mol: Chem.Mol, w: int, h: int) -> Image.Image:
    """ACS 1996 style drawing of a molecule with coordinates, scaled to fit a w x h canvas."""
    from rdkit.Chem.Draw import rdMolDraw2D

    bond = Draw.MeanBondLength(mol) or 1.0

    def render(f):
        d = rdMolDraw2D.MolDraw2DCairo(-1, -1)
        rdMolDraw2D.SetACS1996Mode(d.drawOptions(), bond / f)
        d.drawOptions().annotationFontScale = 0.9
        rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
        d.FinishDrawing()
        return Image.open(io.BytesIO(d.GetDrawingText())).convert("RGB")

    probe = render(1.0)
    img = render(max(0.5, min(8.0, 0.95 * min(w / probe.width, h / probe.height))))
    if img.width > w or img.height > h:
        f = min(w / img.width, h / img.height)
        img = img.resize((max(1, int(img.width * f)), max(1, int(img.height * f))), Image.LANCZOS)
    out = Image.new("RGB", (w, h), "white")
    out.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
    return out


def depict_like(
    smiles: str,
    reference_image_path: str | Path | Image.Image,
    output_path: str | Path | None = None,
    annotate_indices: bool = True,
    *,
    size: int = 500,
    annotate: bool | None = None,
    coords: bool = False,
):
    """Search all 16 rotations/reflections (8 x 45 deg x flip) against reference_image_path ink mask."""
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return (None, None) if coords else None
    do_annotate = annotate_indices if annotate is None else bool(annotate)
    if do_annotate:
        notes = stereo_notes(smiles)
        if notes:
            for note in notes:
                i, label = int(note.split()[1]), note.rsplit(": ", 1)[1]
                mol.GetAtomWithIdx(i).SetProp("atomNote", f"{i}:{label}")
                for n in mol.GetAtomWithIdx(i).GetNeighbors():
                    if not n.HasProp("atomNote"):
                        n.SetProp("atomNote", str(n.GetIdx()))
        else:
            for a in mol.GetAtoms():
                a.SetProp("atomNote", str(a.GetIdx()))
    rdDepictor.SetPreferCoordGen(True)
    try:
        rdDepictor.Compute2DCoords(mol)
    finally:
        rdDepictor.SetPreferCoordGen(False)
    base = mol.GetConformer().GetPositions()[:, :2]
    ref_im = _open_image(reference_image_path)
    ref = ink(ref_im)
    w, h = (
        (size, max(150, int(size * ref_im.height / max(1, ref_im.width))))
        if ref_im.width >= ref_im.height
        else (max(150, int(size * ref_im.width / max(1, ref_im.height))), size)
    )
    best = None
    for k in range(16):
        ang = (k % 8) * np.pi / 4
        rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        xy = base @ rot.T
        if k >= 8:
            xy[:, 0] *= -1
        m = Chem.Mol(mol)
        conf = m.GetConformer()
        for i, (x, y) in enumerate(xy):
            conf.SetAtomPosition(i, (float(x), float(y), 0.0))
        Chem.WedgeMolBonds(m, conf)
        img = _draw_acs(m, w, h)
        a = ink(img)
        score = float((a * ref).sum() / max(1.0, ((a + ref) > 0).sum()))
        if best is None or score > best[0]:
            best = (score, img, xy, k)

    best_score, best_img, best_xy, best_k = best
    final_img = best_img
    out_str = None
    if output_path is not None:
        ref_rgb = ref_im.convert("RGB")
        scale = best_img.height / max(1, ref_rgb.height)
        ref_resized = ref_rgb.resize((max(1, int(round(ref_rgb.width * scale))), best_img.height), Image.LANCZOS)
        side_by_side = Image.new("RGB", (ref_resized.width + 10 + best_img.width, best_img.height), "white")
        side_by_side.paste(ref_resized, (0, 0))
        side_by_side.paste(best_img, (ref_resized.width + 10, 0))
        final_img = side_by_side
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(target)
        out_str = str(target.resolve())

    if coords:
        return (final_img, best_xy)

    return ImageResultDict(
        {
            "ok": True,
            "smiles": Chem.MolToSmiles(Chem.MolFromSmiles(smiles)),
            "output_path": out_str,
            "reference_image_path": str(reference_image_path) if isinstance(reference_image_path, (str, Path)) else None,
            "best_score": best_score,
            "best_transform": {
                "index": best_k,
                "angle_deg": (best_k % 8) * 45,
                "flipped": bool(best_k >= 8),
            },
            "width": final_img.width,
            "height": final_img.height,
            "coordinates": [[float(x), float(y)] for x, y in best_xy],
        },
        image=final_img,
    )


def _syntax_notes(smiles: str) -> tuple[list[str], dict[str, list]]:
    """Problems visible in the SMILES string itself: parentheses, brackets, and ring-closure digits."""
    notes, stack, rings, i = [], [], {}, 0
    unclosed_brackets = []
    unmatched_close_parens = []
    while i < len(smiles):
        ch = smiles[i]
        if ch == "[":
            j = smiles.find("]", i)
            if j < 0:
                notes.append(f"'[' at position {i} has no closing ']'")
                unclosed_brackets.append(i)
                break
            i = j + 1
            continue
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            if stack:
                stack.pop()
            else:
                notes.append(f"')' at position {i} has no matching '('")
                unmatched_close_parens.append(i)
        elif ch == "%" or ch.isdigit():
            label, step = (smiles[i + 1 : i + 3], 3) if ch == "%" else (ch, 1)
            if label in rings:
                del rings[label]
            else:
                rings[label] = i
            i += step
            continue
        i += 1
    notes += [f"'(' at position {k} is never closed" for k in stack]
    if rings:
        notes.append(
            "ring-closure digit(s) opened but never closed: "
            + ", ".join(f"{lab} (position {pos})" for lab, pos in rings.items())
            + "; every ring digit must appear exactly twice (a digit can be reused after it closes)"
        )
    details = {
        "unclosed_parens": list(stack) + unmatched_close_parens,
        "unclosed_brackets": unclosed_brackets,
        "unclosed_rings": [{"digit": lab, "position": pos} for lab, pos in rings.items()],
    }
    return notes, details


def diagnose_smiles_error(smiles: str) -> SmilesErrorDiagnosis:
    """Capture RDKit parse errors and pinpoint unclosed parens/brackets, unclosed ring digits, and bare-bracket radicals."""
    smiles = str(smiles or "")
    msgs: list[str] = []

    class Catch(logging.Handler):
        def emit(self, rec):
            msgs.append(re.sub(r"^\[[\d:]+\]\s*", "", rec.getMessage().strip()))

    log = logging.getLogger("rdkit")
    h, kept, propagate = Catch(), log.handlers[:], log.propagate
    log.handlers, log.propagate = [h], False
    rdBase.LogToPythonLogger()
    mol = None
    try:
        mol = Chem.MolFromSmiles(smiles)
    finally:
        log.handlers, log.propagate = kept, propagate
        rdBase.LogToCppStreams()
    seen = []
    for m in msgs:
        m = re.sub(r"\s+for input:\s*'.*$", "", m.splitlines()[0] if m else "").strip()
        if m and m not in seen:
            seen.append(m)
    notes, syntax_details = _syntax_notes(smiles)
    hints = []
    bare_radicals = [
        {"match": m.group(0), "element": m.group(1), "position": m.start()}
        for m in re.finditer(r"\[(C|N|O|S|P|B)\]", smiles)
    ]
    if "(H)" in smiles:
        hints.append("write hydrogens implicitly (C, not C(H)) or inside brackets ([C@H])")
    if bare_radicals:
        hints.append("[C], [N] etc. in brackets carry no hydrogens (radical); write C, N, O or give the count ([CH2])")
    if "OO" in smiles.replace("O=O", ""):
        hints.append("OO is a peroxide; check that two oxygens are really bonded to each other")
    if "." in smiles:
        hints.append("a dot separates fragments; join a ring or substituent with a bond or ring digit")
    if any("valence" in m.lower() for m in seen):
        hints.append("an atom has more bonds than its valence allows; remove a bond or add a charge")
    if mol is not None and mol.GetNumAtoms() > 0:
        rad_atoms = [f"{a.GetSymbol()} (atom {a.GetIdx()})" for a in mol.GetAtoms() if a.GetNumRadicalElectrons()]
        if rad_atoms and not any("radical" in h for h in hints):
            hints.append(
                f"radical at {', '.join(rad_atoms)}: a bracket atom gets no implicit H, so [C] or [CH] is a radical."
            )
    reason = "; ".join(seen[:2]) or ("the string is not valid SMILES" if not notes and mol is None else "")
    if mol is None or mol.GetNumAtoms() == 0:
        out = "RDKit cannot parse this SMILES" + (f": {reason}" if reason else "") + "."
    elif bare_radicals or notes or hints:
        out = "SMILES warning" + (f": {reason}" if reason else "") + "."
    else:
        out = "Valid SMILES."
    if notes:
        out += " In the string: " + "; ".join(notes) + "."
    if hints:
        out += " Hints: " + "; ".join(hints) + "."
    return SmilesErrorDiagnosis(
        out,
        data={
            "valid": bool(mol is not None and mol.GetNumAtoms() > 0),
            "smiles": smiles,
            "error": out,
            "message": out,
            "rdkit_errors": seen,
            "syntax_notes": notes,
            "hints": hints,
            "bare_bracket_radicals": bare_radicals,
            **syntax_details,
        },
    )


parse_error = diagnose_smiles_error


def smiles_warnings(mol: Chem.Mol, centers=None) -> list[str]:
    """Things that parse in RDKit but are almost never what a journal figure shows."""
    out = []
    rad = [f"{a.GetSymbol()} (atom {a.GetIdx()})" for a in mol.GetAtoms() if a.GetNumRadicalElectrons()]
    if rad:
        out.append(
            f"radical at {', '.join(rad)}: a bracket atom gets no implicit H, so [C] or [CH] is a radical. "
            "Write C, or [C@H]/[C@@H] with its H."
        )
    n_frag = len(Chem.GetMolFrags(mol))
    if n_frag > 1:
        out.append(f"{n_frag} disconnected fragments: fine for a salt, otherwise a bond is missing.")
    charge = Chem.GetFormalCharge(mol)
    if charge:
        out.append(f"net charge {charge:+d}: check that the drawing shows these charges.")
    if centers is None:
        centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    if any(c == "?" for _, c in centers):
        out.append("some stereocenters have no configuration: set them if the drawing has wedges there.")
    return out


def check_smiles(smiles: str) -> dict:
    """Validity, canonical form, formula, stereocenters, and warnings of a SMILES."""
    quiet = rdBase.BlockLogs()
    mol = Chem.MolFromSmiles(smiles or "")
    del quiet
    if mol is None or mol.GetNumAtoms() == 0:
        diag = diagnose_smiles_error(smiles or "")
        return {"valid": False, "error": str(diag), "diagnosis": diag.to_dict()}
    centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    return {
        "valid": True,
        "canonical": Chem.MolToSmiles(mol),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "stereocenters": [f"atom {i} {mol.GetAtomWithIdx(i).GetSymbol()}: {c}" for i, c in centers],
        "unassigned_stereocenters": sum(c == "?" for _, c in centers),
        "rings": mol.GetRingInfo().NumRings(),
        "warnings": smiles_warnings(mol, centers),
        "checkpoints": visual_checkpoints(smiles),
    }


def _normalize_edit_ops(
    ops: list[dict] | None = None,
    *,
    set_atom: list[dict] | None = None,
    set_bond: list[dict] | None = None,
    add_group: list[dict] | None = None,
    remove_atoms: list[int] | list[dict] | None = None,
    set_ez: list[dict] | None = None,
    set_stereo: list[dict] | dict | None = None,
) -> list[dict]:
    normalized: list[dict] = [dict(op) for op in (ops or [])]
    for item in set_atom or []:
        entry = {"op": "set_atom", "atom": item["atom"], "element": item["element"]}
        if item.get("charge") is not None:
            entry["charge"] = item["charge"]
        h_val = item.get("h", item.get("hs", None))
        if h_val is not None:
            entry["hs"] = h_val
        normalized.append(entry)
    for item in set_bond or []:
        normalized.append({"op": "set_bond", "atoms": item["atoms"], "order": item.get("order", 1)})
    for item in add_group or []:
        grp = item.get("smiles", item.get("group", ""))
        normalized.append({"op": "add_group", "atom": item["atom"], "group": grp})
    if remove_atoms:
        flat_rem: list[int] = []
        for x in remove_atoms:
            if isinstance(x, dict):
                if "atoms" in x:
                    flat_rem.extend(int(a) for a in x["atoms"])
                elif "atom" in x:
                    flat_rem.append(int(x["atom"]))
            else:
                flat_rem.append(int(x))
        if flat_rem:
            normalized.append({"op": "remove_atoms", "atoms": flat_rem})
    for item in set_ez or []:
        geom = item.get("geometry", item.get("label", ""))
        normalized.append({"op": "set_ez", "atoms": item["atoms"], "label": geom})
    if isinstance(set_stereo, dict):
        for atom_idx, st in set_stereo.items():
            st_str = str(st).strip()
            if st_str.lower() == "invert":
                normalized.append({"op": "invert", "atom": int(atom_idx)})
            elif st_str.lower() in ("none", "unspecified", "clear"):
                normalized.append({"op": "clear_stereo", "atom": int(atom_idx)})
            else:
                normalized.append({"op": "set_rs", "atom": int(atom_idx), "label": st_str.upper()})
    else:
        for item in set_stereo or []:
            st_str = str(item.get("stereo", item.get("label", ""))).strip()
            atom_target = item.get("atom", "all")
            if st_str.lower() == "invert":
                normalized.append({"op": "invert", "atom": atom_target})
            elif st_str.lower() in ("none", "unspecified", "clear"):
                normalized.append({"op": "clear_stereo", "atom": atom_target})
            else:
                normalized.append({"op": "set_rs", "atom": atom_target, "label": st_str.upper()})
    return normalized


def edit_structure(
    smiles: str,
    ops: list[dict] | None = None,
    *,
    set_atom: list[dict] | None = None,
    set_bond: list[dict] | None = None,
    add_group: list[dict] | None = None,
    remove_atoms: list[int] | list[dict] | None = None,
    set_ez: list[dict] | None = None,
    set_stereo: list[dict] | dict | None = None,
) -> EditedSmiles:
    """Surgical atom-index molecular graph and stereochemistry editor."""
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        raise ValueError("RDKit cannot parse this SMILES")
    all_ops = _normalize_edit_ops(
        ops,
        set_atom=set_atom,
        set_bond=set_bond,
        add_group=add_group,
        remove_atoms=remove_atoms,
        set_ez=set_ez,
        set_stereo=set_stereo,
    )
    rw = Chem.RWMol(mol)
    tetra = (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW)
    skeleton = any(isinstance(op, dict) and op.get("op") in SKELETON_OPS for op in all_ops)
    if skeleton:
        Chem.Kekulize(rw, clearAromaticFlags=True)
    removed: list[int] = []

    def atom(i):
        i = int(i)
        if not 0 <= i < rw.GetNumAtoms():
            raise ValueError(f"atom {i} is out of range (0..{rw.GetNumAtoms() - 1})")
        return rw.GetAtomWithIdx(i)

    gained: dict[int, int] = {}

    def bonds_changed(a, delta):
        gained[a.GetIdx()] = gained.get(a.GetIdx(), 0) + delta

    def cip(i=None, bond=None):
        m = Chem.Mol(rw)
        rdCIPLabeler.AssignCIPLabels(m)
        obj = m.GetAtomWithIdx(i) if bond is None else m.GetBondBetweenAtoms(*bond)
        return obj.GetPropsAsDict().get("_CIPCode", "")

    for op in all_ops:
        kind = op.get("op")
        if kind == "invert":
            a = atom(op["atom"])
            if a.GetChiralTag() not in tetra:
                raise ValueError(f"atom {a.GetIdx()} has no configuration to invert; use set_rs")
            a.InvertChirality()
        elif kind in ("set_rs", "set_stereo"):
            raw_label = str(op.get("label", op.get("stereo", ""))).strip()
            if raw_label.lower() == "invert":
                a = atom(op["atom"])
                if a.GetChiralTag() not in tetra:
                    raise ValueError(f"atom {a.GetIdx()} has no configuration to invert; use set_rs")
                a.InvertChirality()
            elif raw_label.lower() in ("none", "unspecified", "clear"):
                if op.get("atom", "all") == "all":
                    for a in rw.GetAtoms():
                        a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
                else:
                    atom(op["atom"]).SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
            else:
                a, want = atom(op["atom"]), raw_label.upper()
                for tag in tetra:
                    a.SetChiralTag(tag)
                    if cip(a.GetIdx()) == want:
                        break
                else:
                    raise ValueError(f"atom {a.GetIdx()} cannot be {want!r}: it is not a stereocenter")
        elif kind == "clear_stereo":
            if op.get("atom", "all") == "all":
                for a in rw.GetAtoms():
                    a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
                for b in rw.GetBonds():
                    b.SetStereo(Chem.BondStereo.STEREONONE)
                    b.SetBondDir(Chem.BondDir.NONE)
            else:
                atom(op["atom"]).SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
        elif kind == "set_ez":
            i, j = (atom(x).GetIdx() for x in op["atoms"])
            b = rw.GetBondBetweenAtoms(i, j)
            want = str(op.get("label", op.get("geometry", ""))).strip().upper()
            if b is None or b.GetBondType() != Chem.BondType.DOUBLE:
                raise ValueError(f"atoms {i} and {j} are not joined by a double bond")
            for other in rw.GetBonds():
                other.SetBondDir(Chem.BondDir.NONE)
            if want in ("NONE", "UNSPECIFIED", ""):
                b.SetStereo(Chem.BondStereo.STEREONONE)
            else:
                ni = next((x.GetIdx() for x in rw.GetAtomWithIdx(i).GetNeighbors() if x.GetIdx() != j), None)
                nj = next((x.GetIdx() for x in rw.GetAtomWithIdx(j).GetNeighbors() if x.GetIdx() != i), None)
                if ni is None or nj is None:
                    raise ValueError(f"the double bond {i}={j} has no E/Z (a terminal atom)")
                b.SetStereoAtoms(ni, nj)
                for tag in (Chem.BondStereo.STEREOCIS, Chem.BondStereo.STEREOTRANS):
                    b.SetStereo(tag)
                    if cip(bond=(i, j)) == want:
                        break
                else:
                    raise ValueError(f"the double bond {i}={j} cannot be {want!r}")
        elif kind == "set_atom":
            a = atom(op["atom"])
            try:
                num = Chem.GetPeriodicTable().GetAtomicNumber(str(op.get("element", "")).capitalize())
            except RuntimeError:
                num = 0
            if num <= 0:
                raise ValueError(f"unknown element {op.get('element')!r}")
            a.SetAtomicNum(num)
            a.SetIsAromatic(False)
            if op.get("charge") is not None:
                a.SetFormalCharge(int(op["charge"]))
            h_val = op.get("hs", op.get("h", None))
            if h_val is not None:
                a.SetNumExplicitHs(int(h_val))
                a.SetNoImplicit(True)
            else:
                a.SetNumExplicitHs(0)
                a.SetNoImplicit(False)
        elif kind == "set_bond":
            i, j = (atom(x).GetIdx() for x in op["atoms"])
            order = int(op.get("order", 1))
            if i == j or order not in (0, 1, 2, 3):
                raise ValueError("set_bond needs two different atoms and an order of 0, 1, 2 or 3")
            b = rw.GetBondBetweenAtoms(i, j)
            old = int(b.GetBondTypeAsDouble()) if b is not None else 0
            if order == 0:
                if b is not None:
                    rw.RemoveBond(i, j)
            elif b is None:
                rw.AddBond(i, j, _ORDER[order])
            else:
                b.SetBondType(_ORDER[order])
                b.SetIsAromatic(False)
            for k in (i, j):
                bonds_changed(rw.GetAtomWithIdx(k), order - old)
        elif kind == "add_group":
            a = atom(op["atom"])
            grp_str = str(op.get("group", op.get("smiles", "")))
            frag = Chem.MolFromSmiles(grp_str)
            stars = [x.GetIdx() for x in frag.GetAtoms() if x.GetAtomicNum() == 0] if frag is not None else []
            if frag is None or len(stars) != 1 or frag.GetAtomWithIdx(stars[0]).GetDegree() != 1:
                raise ValueError("group must be a SMILES with exactly one [*], e.g. [*]C(C)(C)C")
            Chem.Kekulize(frag, clearAromaticFlags=True)
            nbr = frag.GetAtomWithIdx(stars[0]).GetNeighbors()[0].GetIdx()
            new = {x.GetIdx(): rw.AddAtom(Chem.Atom(x)) for x in frag.GetAtoms() if x.GetIdx() != stars[0]}
            for b in frag.GetBonds():
                u, v = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
                if u in new and v in new:
                    rw.AddBond(new[u], new[v], b.GetBondType())
            bond = frag.GetBondBetweenAtoms(stars[0], nbr)
            rw.AddBond(a.GetIdx(), new[nbr], bond.GetBondType())
            bonds_changed(a, int(bond.GetBondTypeAsDouble()))
        elif kind == "remove_atoms":
            removed += [atom(x).GetIdx() for x in op.get("atoms") or []]
        else:
            raise ValueError(
                f"unknown op {kind!r}; use invert, set_rs, clear_stereo, set_ez, set_atom, set_bond, "
                "add_group or remove_atoms"
            )
    for i in removed:
        a = rw.GetAtomWithIdx(i)
        for b in a.GetBonds():
            bonds_changed(b.GetOtherAtom(a), -int(b.GetBondTypeAsDouble()))
    for i, d in gained.items():
        a = rw.GetAtomWithIdx(i)
        if i not in removed and (a.GetNoImplicit() or a.GetNumExplicitHs()):
            a.SetNumExplicitHs(max(0, a.GetNumExplicitHs() - d))
    for i in sorted(set(removed), reverse=True):
        rw.RemoveAtom(i)
    try:
        if skeleton:
            Chem.SanitizeMol(rw)
    except Exception as exc:
        raise ValueError(f"the edit gave an invalid structure ({str(exc).splitlines()[0]})") from None
    out = Chem.MolToSmiles(rw)
    out_mol = Chem.MolFromSmiles(out)
    if out_mol is None:
        raise ValueError("the edit gave an invalid structure")
    if skeleton and out.count(".") > Chem.MolToSmiles(mol).count("."):
        raise ValueError(f"the edit splits the structure into pieces ({out}); remove or reconnect the loose atoms")
    return EditedSmiles(
        out,
        meta={
            "smiles": out,
            "canonical_smiles": out,
            "formula": rdMolDescriptors.CalcMolFormula(out_mol),
            "before_formula": rdMolDescriptors.CalcMolFormula(mol),
            "checkpoints": visual_checkpoints(out),
        },
    )


def _classify_silyl_group(mol: Chem.Mol, si_atom: Chem.Atom, carbon_count: int) -> str | None:
    if carbon_count == 3:
        return "TMS"
    if carbon_count == 6:
        c_nbrs = [x for x in si_atom.GetNeighbors() if x.GetSymbol() == "C"]
        branch_sizes = []
        for cn in c_nbrs:
            visited = {si_atom.GetIdx()}
            stack = [cn]
            while stack:
                cur = stack.pop()
                if cur.GetIdx() not in visited:
                    visited.add(cur.GetIdx())
                    stack.extend(
                        y for y in cur.GetNeighbors() if y.GetSymbol() == "C" and not y.IsInRing()
                    )
            branch_sizes.append(len(visited) - 1)
        if sorted(branch_sizes) == [1, 1, 4]:
            return "TBS"
        if sorted(branch_sizes) == [2, 2, 2]:
            return "TES"
    if carbon_count == 9:
        return "TIPS"
    if carbon_count == 16:
        return "TBDPS"
    return None


def visual_checkpoints(smiles: str, limit: int = 12) -> list[str]:
    """Flag terminal =CH2, Si carbon counts (TMS/TES/TBS/TIPS), and benzene ortho/meta/para substitution indices."""
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return []
    out = []
    dbl = [b for b in mol.GetBonds() if b.GetBondType() == Chem.BondType.DOUBLE]
    if dbl:
        out.append(
            "double bonds outside aromatic rings (is each drawn, and to the right atom?): "
            + ", ".join(
                f"{b.GetBeginAtomIdx()}{b.GetBeginAtom().GetSymbol()}={b.GetEndAtomIdx()}{b.GetEndAtom().GetSymbol()}"
                for b in dbl[:limit]
            )
        )
    ch2 = [
        b
        for b in dbl
        if any(x.GetSymbol() == "C" and x.GetDegree() == 1 for x in (b.GetBeginAtom(), b.GetEndAtom()))
    ]
    if ch2:
        out.append(
            "terminal =CH2 at "
            + ", ".join(f"{b.GetBeginAtomIdx()}={b.GetEndAtomIdx()}" for b in ch2)
            + ": readers often turn a drawn C=O into C=CH2; is an O written there?"
        )
    het = [a for a in mol.GetAtoms() if a.GetSymbol() not in ("C", "H", "*", "Si")]
    if het:
        out.append(
            "heteroatoms (right element in the right place?): "
            + ", ".join(f"{a.GetIdx()} {a.GetSymbol()}" for a in het[:limit])
        )
    for a in mol.GetAtoms():
        if a.GetSymbol() == "Si":
            seen, todo = {a.GetIdx()}, [x for x in a.GetNeighbors() if x.GetSymbol() == "C"]
            while todo:
                x = todo.pop()
                if x.GetIdx() not in seen:
                    seen.add(x.GetIdx())
                    todo += [y for y in x.GetNeighbors() if y.GetSymbol() == "C" and not y.IsInRing()]
            c_count = len(seen) - 1
            silyl_tag = _classify_silyl_group(mol, a, c_count)
            tag_str = f" [{silyl_tag}]" if silyl_tag else ""
            out.append(
                f"Si at atom {a.GetIdx()} carries {c_count} carbons{tag_str}: check the label drawn there ({_SILYL})."
            )
    rel = {1: "ortho", 2: "meta", 3: "para"}
    for ring in mol.GetRingInfo().AtomRings():
        if len(ring) != 6 or not all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in ring):
            continue
        subs = [
            (p, i)
            for p, i in enumerate(ring)
            if any(n.GetIdx() not in ring for n in mol.GetAtomWithIdx(i).GetNeighbors())
        ]
        if 2 <= len(subs) <= 4:
            pairs = [
                f"{i}/{j} {rel[min(abs(p - q), 6 - abs(p - q))]}"
                for k, (p, i) in enumerate(subs)
                for q, j in subs[k + 1 :]
            ]
            out.append(
                f"benzene-type ring {'-'.join(map(str, ring))}: substituents at "
                f"{', '.join(str(i) for _, i in subs)} ({'; '.join(pairs)})"
            )
    rdCIPLabeler.AssignCIPLabels(mol)
    centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    if centers:
        out.append(
            "stereocentres (is a wedge drawn at each, and which way?): "
            + ", ".join(f"{i} {c}" for i, c in centers[:limit])
        )
    return out


check_points = visual_checkpoints


def _zip_single_markush(core: str, frags: str | list[str]) -> str | None:
    params = Chem.SmilesParserParams()
    params.removeHs = False
    mol = Chem.MolFromSmiles(core or "", params)
    if mol is None:
        return None
    try:
        frag_list = [frags] if isinstance(frags, str) else list(frags)
        for f in frag_list:
            norm_f = re.sub(r"^(\[\*:\d+\])H$", r"\1[H]", str(f).strip())
            frag_mol = Chem.MolFromSmiles(norm_f, params)
            if frag_mol is None:
                return None
            mol = Chem.molzip(mol, frag_mol)
        mol = Chem.RemoveHs(mol)
        Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


def enumerate_markush_r_groups(
    core_smiles: str,
    r_groups_by_label: dict[str, list[str] | str] | list[str] | str,
):
    """Take a [*:1]/[*:2] core SMILES and r_groups_by_label (e.g. {'5a': ['[*:1]F', '[*:2]C']}) and enumerate products via Chem.molzip."""
    if isinstance(r_groups_by_label, (str, list, tuple)):
        return _zip_single_markush(core_smiles, r_groups_by_label)
    if not isinstance(r_groups_by_label, dict):
        raise ValueError("r_groups_by_label must be a dict, list, or str")

    core_mol = Chem.MolFromSmiles(core_smiles or "")
    if core_mol is None:
        raise ValueError("core_smiles is not a valid SMILES")

    core_points = sorted(set(re.findall(r"\[\*:(\d+)\]", core_smiles)), key=int)
    products: dict[str, Any] = {}
    errors: dict[str, str] = {}
    records: list[dict[str, Any]] = []

    for label, raw_frags in r_groups_by_label.items():
        if isinstance(raw_frags, dict):
            frags = [
                v if re.search(r"\[\*:\d+\]", str(v)) else f"[*:{str(k).lstrip('R*:[]')}]{v}"
                for k, v in raw_frags.items()
            ]
        elif isinstance(raw_frags, str):
            frags = [raw_frags]
        else:
            frags = list(raw_frags)

        given = [p for f in frags for p in re.findall(r"\[\*:(\d+)\]", str(f))]
        problems = []
        for f in frags:
            if "." in str(f):
                problems.append(f"fragment {f!r} has a dot")
            if re.search(r"\[\*:\d+\]", str(f)) is None:
                problems.append(f"fragment {f!r} has no [*:n] attachment point")
        if core_points and sorted(set(given), key=int) != core_points:
            problems.append(f"core has points {core_points}, fragments give {sorted(set(given), key=int)}")
        if len(given) != len(set(given)):
            problems.append("an attachment point is given twice")

        smi = None if problems else _zip_single_markush(core_smiles, frags)
        if smi is None and not problems:
            problems.append("Chem.molzip failed to join fragments onto core")

        if problems or smi is None:
            err_msg = "; ".join(problems)
            errors[str(label)] = err_msg
            records.append({"label": str(label), "valid": False, "smiles": None, "error": err_msg})
        else:
            prod_mol = Chem.MolFromSmiles(smi)
            formula = rdMolDescriptors.CalcMolFormula(prod_mol) if prod_mol is not None else ""
            item = EditedSmiles(
                smi,
                meta={
                    "label": str(label),
                    "valid": True,
                    "smiles": smi,
                    "canonical_smiles": smi,
                    "formula": formula,
                    "checkpoints": visual_checkpoints(smi),
                },
            )
            products[str(label)] = item
            records.append(item.to_dict())

    return MarkushEnumerationResult(
        products,
        meta={
            "core": core_smiles,
            "products": dict(products),
            "members": dict(products),
            "results": records,
            "errors": errors,
        },
    )


enumerate_markush = enumerate_markush_r_groups


def _is_line(comp: np.ndarray, glyph: int) -> bool:
    ys, xs = np.nonzero(comp)
    pts = np.stack([xs, ys], 1).astype(float)
    pts -= pts.mean(0)
    _, vecs = np.linalg.eigh(pts.T @ pts)
    off = np.abs(pts @ vecs[:, 0])
    return float((off <= 0.3 * glyph).mean()) >= 0.75


def _is_frame(comp: np.ndarray) -> bool:
    h, w = comp.shape
    if min(h, w) < 20:
        return False
    edges = [
        comp[:3].any(axis=0).mean(),
        comp[-3:].any(axis=0).mean(),
        comp[:, :3].any(axis=1).mean(),
        comp[:, -3:].any(axis=1).mean(),
    ]
    return min(edges) > 0.6


def find_structures(im: Image.Image | str | Path, min_side: int = 40) -> list[list[int]]:
    """Candidate boxes [x0, y0, x1, y1] of drawn structures, from connected ink."""
    from scipy import ndimage

    image = _open_image(im)
    ink_mask = np.asarray(image.convert("L")) < 160
    lab, n = ndimage.label(ink_mask, structure=np.ones((3, 3)))
    if n == 0:
        return []
    heights = sorted(s[0].stop - s[0].start for s in ndimage.find_objects(lab))
    glyph = max(8, heights[len(heights) // 2])
    run = 5 * glyph
    ink_mask = ink_mask & ~(
        ndimage.binary_opening(ink_mask, np.ones((1, run)))
        | ndimage.binary_opening(ink_mask, np.ones((run, 1)))
    )
    lab, n = ndimage.label(ink_mask, structure=np.ones((3, 3)))
    slices = ndimage.find_objects(lab)
    boxes = [(s[1].start, s[0].start, s[1].stop, s[0].stop) for s in slices]
    seeds, small = [], []
    for k, (b, sl) in enumerate(zip(boxes, slices)):
        w, h = b[2] - b[0], b[3] - b[1]
        if max(w, h) < 2.5 * glyph:
            small.append(b)
            continue
        comp = lab[sl] == k + 1
        if _is_line(comp, glyph) or _is_frame(comp):
            continue
        seeds.append(list(b))
    pad = 0.9 * glyph

    def near(a, b, p):
        return a[0] - p <= b[2] and b[0] - p <= a[2] and a[1] - p <= b[3] and b[1] - p <= a[3]

    def union(a, b):
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

    def merge(p):
        merged = True
        while merged:
            merged = False
            for i in range(len(seeds)):
                j = next((j for j in range(i + 1, len(seeds)) if near(seeds[i], seeds[j], p)), None)
                if j is not None:
                    seeds[i] = union(seeds[i], seeds.pop(j))
                    merged = True
                    break

    merge(pad)
    words = []
    for b in sorted(small):
        w = next(
            (
                w
                for w in words
                if b[0] - w[2] <= 0.35 * glyph
                and w[0] <= b[2]
                and min(w[3], b[3]) - max(w[1], b[1]) > 0.3 * min(w[3] - w[1], b[3] - b[1])
            ),
            None,
        )
        if w is None:
            words.append(list(b))
        else:
            w[:] = union(w, b)
    for k, s in enumerate(list(seeds)):
        for w in words:
            if near(s, w, 0.6 * glyph):
                seeds[k] = union(seeds[k], w)
    merge(0)
    out = [s for s in seeds if min(s[2] - s[0], s[3] - s[1]) >= min_side]
    return sorted(out, key=lambda b: (b[1] // max(1, 4 * glyph), b[0]))
