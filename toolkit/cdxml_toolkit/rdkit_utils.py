"""RDKit-based CDXML fragment utilities.

Complements cdxml_utils.py (which provides pure XML geometry — bounding
boxes, centroids, text bbox, IO) with RDKit-powered chemical operations:

  - frag_to_mol()              — CDXML <fragment> → RDKit Mol (with metadata)
  - frag_to_smiles()           — CDXML <fragment> → canonical SMILES
  - frag_to_mw()               — CDXML <fragment> → molecular weight
  - frag_to_molblock()         — CDXML <fragment> → MOL block (CDXML coords)
  - cleanup_fragment_rdkit()   — 2D cleanup with Kabsch orientation preservation
  - set_cdxml_conformer()      — Set RDKit conformer from CDXML coordinates
  - rdkit_default_bond_length() — RDKit's default 2D depiction bond length
  - avg_bond_length_from_atoms() — Average bond length from CDXML atom coords

Uses shared modules (constants.py for ACS_BOND_LENGTH).

All RDKit imports are lazy so this module can be imported even if RDKit
is not installed (functions will raise ImportError at call time).
"""

import math
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from .constants import ACS_BOND_LENGTH


# ---------------------------------------------------------------------------
# Core: CDXML <fragment> → RDKit Mol
# ---------------------------------------------------------------------------

def frag_to_mol(frag_elem: ET.Element):
    """Convert a CDXML <fragment> to an RDKit Mol with atom metadata.

    Returns ``(mol, atoms_data)`` where *atoms_data* is a list of dicts
    with keys: id, idx, x, y, elem, num_h, is_abbrev, xml.

    Abbreviation groups (``NodeType="Fragment"``) become dummy atoms
    (element 0) so they participate in connectivity but not MCS element
    matching.

    Returns ``(None, None)`` if conversion fails.
    """
    from rdkit import Chem

    atoms: List[dict] = []
    id_map: Dict[int, int] = {}

    # NodeTypes that are NOT real atoms — they become dummy atoms (element 0)
    # or get skipped entirely.
    _SKIP_NODETYPES = {"ExternalConnectionPoint"}
    _DUMMY_NODETYPES = {
        "Fragment",          # Real abbreviation groups (Boc, OTs, Me, etc.)
        "GenericNickname",   # Generic variable groups (R, X, Ar, etc.)
        "Nickname",          # Alternative label form (may or may not be real)
        "Unspecified",       # Uninterpretable text labels
    }

    for n in frag_elem.findall("n"):
        nid = int(n.get("id"))
        node_type = n.get("NodeType")
        if node_type in _SKIP_NODETYPES:
            continue

        px, py = [float(v) for v in n.get("p", "0 0").split()]
        elem = int(n.get("Element", "6"))
        num_h_attr = n.get("NumHydrogens")
        num_h = int(num_h_attr) if num_h_attr is not None else None
        is_abbrev = node_type in _DUMMY_NODETYPES

        idx = len(atoms)
        id_map[nid] = idx
        atoms.append({
            "id": nid, "idx": idx,
            "x": px, "y": py,
            "elem": elem, "num_h": num_h,
            "is_abbrev": is_abbrev,
            "xml": n,
        })

    bonds = []
    for b in frag_elem.findall("b"):
        bi, ei = int(b.get("B")), int(b.get("E"))
        if bi in id_map and ei in id_map:
            bonds.append((id_map[bi], id_map[ei], int(b.get("Order", "1"))))

    em = Chem.RWMol()
    for a in atoms:
        ra = Chem.Atom(0 if a["is_abbrev"] else a["elem"])
        if a["num_h"] is not None:
            ra.SetNoImplicit(True)
            ra.SetNumExplicitHs(a["num_h"])
        em.AddAtom(ra)

    BT = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE,
          3: Chem.BondType.TRIPLE}
    for bi, ei, order in bonds:
        em.AddBond(bi, ei, BT.get(order, Chem.BondType.SINGLE))

    mol = em.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        try:
            Chem.SanitizeMol(
                mol,
                Chem.SanitizeFlags.SANITIZE_ALL
                ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES,
            )
        except Exception:
            pass

    return mol, atoms


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def frag_to_smiles(frag_elem: ET.Element) -> Optional[str]:
    """Convert a CDXML <fragment> to a canonical SMILES string.

    Returns None if conversion fails.
    """
    from rdkit import Chem
    result = frag_to_mol(frag_elem)
    if result is None or result[0] is None:
        return None
    mol, _ = result
    try:
        smi = Chem.MolToSmiles(mol)
        return smi if smi else None
    except Exception:
        return None


def frag_to_smiles_resolved(frag_elem: ET.Element) -> Optional[str]:
    """Convert a CDXML <fragment> to SMILES, resolving abbreviation groups.

    Unlike :func:`frag_to_smiles`, which turns abbreviation groups
    (``NodeType="Fragment"``) into ``[*]`` dummy atoms, this function
    attempts to replace each dummy with the real fragment SMILES from
    the superatom table.

    Falls back to :func:`frag_to_smiles` if resolution fails.
    """
    from rdkit import Chem

    result = frag_to_mol(frag_elem)
    if result is None or result[0] is None:
        return None
    mol, atoms_data = result

    # Check for abbreviation groups — only resolve real abbreviations
    # (NodeType="Fragment"), NOT generic groups (R, X, Ar — GenericNickname,
    # Nickname, Unspecified) which should stay as [*].
    abbrev_atoms = [(a["idx"], a) for a in atoms_data
                    if a["is_abbrev"]
                    and a["xml"].get("NodeType") == "Fragment"]
    if not abbrev_atoms:
        # No abbreviations — standard path
        try:
            smi = Chem.MolToSmiles(mol)
            return smi if smi else None
        except Exception:
            return None

    # Try to resolve each abbreviation
    try:
        from .resolve.superatom_table import get_abbrev_label, lookup_smiles
    except ImportError:
        return frag_to_smiles(frag_elem)

    em = Chem.RWMol(mol)

    # Process abbreviations in reverse index order to keep indices stable
    replacements = []
    for idx, a in sorted(abbrev_atoms, key=lambda x: x[0], reverse=True):
        label = get_abbrev_label(a["xml"])
        if not label:
            return frag_to_smiles(frag_elem)  # Can't resolve — fallback

        abbrev_smi = lookup_smiles(label)
        if not abbrev_smi:
            return frag_to_smiles(frag_elem)  # Unknown abbreviation — fallback

        abbrev_mol = Chem.MolFromSmiles(abbrev_smi)
        if abbrev_mol is None:
            return frag_to_smiles(frag_elem)

        # Find the bond connecting dummy to core
        dummy_atom = em.GetAtomWithIdx(idx)
        dummy_bonds = list(dummy_atom.GetBonds())
        if len(dummy_bonds) != 1:
            return frag_to_smiles(frag_elem)  # Multi-attachment — too complex

        bond = dummy_bonds[0]
        core_idx = bond.GetOtherAtomIdx(idx)
        bond_type = bond.GetBondType()

        replacements.append((idx, core_idx, bond_type, abbrev_mol))

    # Apply replacements (still in reverse order)
    for idx, core_idx, bond_type, abbrev_mol in replacements:
        # Remove bond between dummy and core
        em.RemoveBond(idx, core_idx)

        # Add abbreviation atoms
        offset = em.GetNumAtoms()
        for i in range(abbrev_mol.GetNumAtoms()):
            new_atom = Chem.Atom(abbrev_mol.GetAtomWithIdx(i).GetAtomicNum())
            src = abbrev_mol.GetAtomWithIdx(i)
            new_atom.SetFormalCharge(src.GetFormalCharge())
            if src.GetNoImplicit():
                new_atom.SetNoImplicit(True)
                new_atom.SetNumExplicitHs(src.GetNumExplicitHs())
            em.AddAtom(new_atom)

        for b in abbrev_mol.GetBonds():
            em.AddBond(offset + b.GetBeginAtomIdx(),
                       offset + b.GetEndAtomIdx(),
                       b.GetBondType())

        # Connect first atom of abbreviation to core
        em.AddBond(core_idx, offset, bond_type)

    # Remove dummy atoms (highest index first — they were sorted in reverse)
    for idx, _, _, _ in replacements:
        em.RemoveAtom(idx)

    try:
        resolved = em.GetMol()
        Chem.SanitizeMol(resolved)
        smi = Chem.MolToSmiles(resolved)
        return smi if smi else frag_to_smiles(frag_elem)
    except Exception:
        return frag_to_smiles(frag_elem)


def frag_to_smiles_chemscript(frag_elem: ET.Element) -> Optional[str]:
    """Convert a CDXML ``<fragment>`` to SMILES using ChemScript.

    ChemScript (PerkinElmer ChemDraw .NET library) natively understands
    ALL ChemDraw abbreviation groups (Nicknames, Fragments, generic groups)
    and expands them to full structures.  This gives far better results than
    :func:`frag_to_smiles_resolved` for fragments with complex or rare
    abbreviations (NHTrs, PO(OH)₂, Bn, etc.).

    Falls back to ``None`` if ChemScript is unavailable or fails.
    Requires ChemDraw 16+ installed on Windows.
    """
    import copy
    import tempfile
    import os

    try:
        from .chemdraw.chemscript_bridge import ChemScriptBridge
    except ImportError:
        return None

    # Wrap the fragment in a minimal CDXML document
    frag_copy = copy.deepcopy(frag_elem)
    wrapper = ET.Element("CDXML")
    page_el = ET.SubElement(wrapper, "page")
    page_el.append(frag_copy)

    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".cdxml", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write('<?xml version="1.0" encoding="UTF-8" ?>')
        tmp.write(ET.tostring(wrapper, encoding="unicode"))
        tmp.close()
        tmp_path = tmp.name

        cs = ChemScriptBridge()
        info = cs.get_info(tmp_path)
        if info and info.get("ok"):
            smi = info.get("smiles")
            if smi:
                return smi
            # Reaction-type response — shouldn't happen for a single fragment
            # but handle gracefully
            reactants = info.get("reactants", [])
            if reactants and reactants[0].get("smiles"):
                return reactants[0]["smiles"]
        return None
    except Exception:
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def frag_to_mw(frag_elem: ET.Element) -> Optional[float]:
    """Compute molecular weight from a CDXML <fragment>.

    If the fragment contains abbreviation groups (``NodeType="Fragment"``),
    attempts to resolve their MW via the superatom lookup table
    (``superatom_table.py``).  Falls back to None only if an abbreviation
    label cannot be resolved.
    """
    from rdkit.Chem import Descriptors
    result = frag_to_mol(frag_elem)
    if result is None or result[0] is None:
        return None
    mol, atoms_data = result

    abbrev_atoms = [a for a in atoms_data if a["is_abbrev"]]
    if not abbrev_atoms:
        # No abbreviations — straightforward MW
        try:
            return Descriptors.MolWt(mol)
        except Exception:
            return None

    # Has abbreviation groups — try superatom-assisted MW.
    # Strategy: MolWt(mol_with_dummies) gives MW of the core (dummy atoms
    # contribute 0 Da).  For each abbreviation, look up its standalone MW
    # and subtract 1.008 (one H lost when it bonds to the core).
    try:
        from .resolve.superatom_table import get_abbrev_label, lookup_mw
    except ImportError:
        return None

    H_MASS = 1.008
    abbrev_mw_total = 0.0
    for a in abbrev_atoms:
        label = get_abbrev_label(a["xml"])
        if label is None:
            return None  # can't read label
        mw = lookup_mw(label)
        if mw is None:
            return None  # unknown abbreviation
        # Count bonds from this dummy atom to the rest of the molecule
        dummy_idx = a["idx"]
        n_bonds = sum(1 for bond in mol.GetBonds()
                      if bond.GetBeginAtomIdx() == dummy_idx
                      or bond.GetEndAtomIdx() == dummy_idx)
        # Each bond replaces one H on the abbreviation fragment
        abbrev_mw_total += mw - (n_bonds * H_MASS)

    try:
        core_mw = Descriptors.MolWt(mol)
    except Exception:
        return None

    return core_mw + abbrev_mw_total


def frag_to_molblock(frag_elem: ET.Element) -> Optional[str]:
    """Convert a CDXML <fragment> to a MOL block string (with CDXML coords).

    Sets the RDKit conformer from CDXML coordinates before export so the
    MOL block preserves the drawn layout.

    Returns None if conversion fails.
    """
    from rdkit import Chem
    result = frag_to_mol(frag_elem)
    if result is None or result[0] is None:
        return None
    mol, atoms_data = result

    set_cdxml_conformer(mol, atoms_data, scale=1.0)

    try:
        return Chem.MolToMolBlock(mol)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 2D Cleanup with orientation preservation
# ---------------------------------------------------------------------------

def cleanup_fragment_rdkit(frag_elem: ET.Element,
                           verbose: bool = False) -> bool:
    """Clean up a single fragment's 2D geometry using RDKit.

    Uses ``AllChem.Compute2DCoords()`` for cleanup, then applies Kabsch
    rotation to restore the original orientation.

    Abbreviation groups (``NodeType="Fragment"``) are included as dummy
    atoms (element 0) in the RDKit mol — they participate in layout but
    not element matching.  When an abbreviation node moves, its inner
    fragment atoms and text label are translated by the same delta.

    Modifies *frag_elem* in place.  Returns True if cleanup was applied.
    """
    import copy as _copy
    from rdkit import Chem
    from rdkit.Chem import AllChem

    result = frag_to_mol(frag_elem)
    if result is None or result[0] is None:
        return False
    mol, atoms_data = result

    if mol.GetNumAtoms() < 2:
        return False

    # Save original coordinates
    orig_coords = [(a["x"], a["y"]) for a in atoms_data]

    # Compute new 2D coords
    mol_copy = _copy.deepcopy(mol)
    AllChem.Compute2DCoords(mol_copy)
    conf = mol_copy.GetConformer()

    # Get new coords (RDKit space: y-up)
    new_coords_rdk = []
    for i in range(mol_copy.GetNumAtoms()):
        pos = conf.GetAtomPosition(i)
        new_coords_rdk.append((pos.x, pos.y))

    # Scale new coords to ACS standard bond length
    avg_bl_new = _avg_bond_length_from_conf(mol_copy)
    if avg_bl_new < 1e-6:
        return False
    scale = ACS_BOND_LENGTH / avg_bl_new

    # Convert to CDXML space (y-flip + scale)
    new_coords_cdxml = [(x * scale, -y * scale) for x, y in new_coords_rdk]

    # Kabsch: find best rotation from new → original
    cx_orig = sum(x for x, y in orig_coords) / len(orig_coords)
    cy_orig = sum(y for x, y in orig_coords) / len(orig_coords)
    cx_new = sum(x for x, y in new_coords_cdxml) / len(new_coords_cdxml)
    cy_new = sum(y for x, y in new_coords_cdxml) / len(new_coords_cdxml)

    orig_centered = [(x - cx_orig, y - cy_orig) for x, y in orig_coords]
    new_centered = [(x - cx_new, y - cy_new) for x, y in new_coords_cdxml]

    # Compute optimal rotation angle via atan2(cross, dot)
    dot_sum = 0.0
    cross_sum = 0.0
    for (ox, oy), (nx, ny) in zip(orig_centered, new_centered):
        dot_sum += nx * ox + ny * oy
        cross_sum += nx * oy - ny * ox
    angle = math.atan2(cross_sum, dot_sum)

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # Apply rotation to new coords and translate to original centroid
    final_coords = []
    for x, y in new_centered:
        rx = x * cos_a - y * sin_a + cx_orig
        ry = x * sin_a + y * cos_a + cy_orig
        final_coords.append((rx, ry))

    # For salt products (disconnected components like amine + HCl):
    # RDKit's Compute2DCoords places disconnected fragments arbitrarily.
    # The Kabsch rotation preserves overall orientation but scrambles the
    # relative position of small counterions. Fix: reposition small
    # components to preserve their original offset from the main structure.
    frags = Chem.GetMolFrags(mol)
    if len(frags) > 1:
        largest = max(frags, key=len)
        # Original centroid of largest component
        ocx_main = sum(orig_coords[i][0] for i in largest) / len(largest)
        ocy_main = sum(orig_coords[i][1] for i in largest) / len(largest)
        # New centroid of largest component (after Kabsch)
        ncx_main = sum(final_coords[i][0] for i in largest) / len(largest)
        ncy_main = sum(final_coords[i][1] for i in largest) / len(largest)
        for comp in frags:
            if comp is largest:
                continue
            # Original offset from main component
            ocx_s = sum(orig_coords[i][0] for i in comp) / len(comp)
            ocy_s = sum(orig_coords[i][1] for i in comp) / len(comp)
            off_x = ocx_s - ocx_main
            off_y = ocy_s - ocy_main
            # Where it should be (preserve original offset from main)
            tgt_x = ncx_main + off_x
            tgt_y = ncy_main + off_y
            # Where it currently is
            cur_x = sum(final_coords[i][0] for i in comp) / len(comp)
            cur_y = sum(final_coords[i][1] for i in comp) / len(comp)
            # Shift
            dx = tgt_x - cur_x
            dy = tgt_y - cur_y
            for idx in comp:
                fx, fy = final_coords[idx]
                final_coords[idx] = (fx + dx, fy + dy)

    # Write back to CDXML — also translate inner abbreviation fragments
    has_abbrev = False
    for atom_d, (fx, fy) in zip(atoms_data, final_coords):
        node = atom_d["xml"]
        old_x, old_y = atom_d["x"], atom_d["y"]
        node.set("p", f"{fx:.4f} {fy:.4f}")

        if atom_d["is_abbrev"]:
            has_abbrev = True
            dx = fx - old_x
            dy = fy - old_y
            inner_frag = node.find("fragment")
            if inner_frag is not None:
                for inner_n in inner_frag.findall("n"):
                    ip = inner_n.get("p")
                    if ip:
                        ix, iy = [float(v) for v in ip.split()]
                        inner_n.set("p", f"{ix + dx:.4f} {iy + dy:.4f}")
            for t_elem in node.findall("t"):
                tp = t_elem.get("p")
                if tp:
                    tx, ty = [float(v) for v in tp.split()]
                    t_elem.set("p", f"{tx + dx:.4f} {ty + dy:.4f}")
                bb = t_elem.get("BoundingBox")
                if bb:
                    bvals = [float(v) for v in bb.split()]
                    if len(bvals) == 4:
                        t_elem.set("BoundingBox",
                                   f"{bvals[0]+dx:.4f} {bvals[1]+dy:.4f} "
                                   f"{bvals[2]+dx:.4f} {bvals[3]+dy:.4f}")

    if verbose:
        import sys
        frag_id = frag_elem.get("id", "?")
        abbrev_note = " (with abbreviations)" if has_abbrev else ""
        print(f"    [RDKit cleanup] fragment {frag_id}: "
              f"{mol.GetNumAtoms()} atoms{abbrev_note}",
              file=sys.stderr)

    return True


# ---------------------------------------------------------------------------
# Scale / coordinate helpers
# ---------------------------------------------------------------------------

_rdk_bl_cache: Optional[float] = None


def rdkit_default_bond_length() -> float:
    """RDKit's default 2D depiction bond length (cached)."""
    global _rdk_bl_cache
    if _rdk_bl_cache is None:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        m = Chem.MolFromSmiles("CC")
        AllChem.Compute2DCoords(m)
        c = m.GetConformer()
        p0, p1 = c.GetAtomPosition(0), c.GetAtomPosition(1)
        _rdk_bl_cache = math.sqrt(
            (p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2)
    return _rdk_bl_cache


def avg_bond_length_from_atoms(atoms_data: List[dict], mol) -> float:
    """Average bond length computed from CDXML atom coordinates."""
    return _avg_bond_length(atoms_data, mol)


def set_cdxml_conformer(mol, atoms_data: List[dict], scale: float = 1.0):
    """Set conformer from CDXML coordinates (y-flipped, scaled to RDKit space).

    CDXML y-axis points down; RDKit y-axis points up. The *scale* factor
    converts from CDXML points (~14.40 pt bond length) to RDKit units
    (~1.5 unit bond length).
    """
    from rdkit import Chem
    from rdkit.Geometry import Point3D

    conf = Chem.Conformer(mol.GetNumAtoms())
    for a in atoms_data:
        conf.SetAtomPosition(
            a["idx"], Point3D(a["x"] * scale, -a["y"] * scale, 0.0))
    mol.RemoveAllConformers()
    mol.AddConformer(conf, assignId=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _avg_bond_length(atoms_data: List[dict], mol) -> float:
    """Average bond length from CDXML atom coordinates."""
    total, count = 0.0, 0
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        dx = atoms_data[i]["x"] - atoms_data[j]["x"]
        dy = atoms_data[i]["y"] - atoms_data[j]["y"]
        total += math.sqrt(dx * dx + dy * dy)
        count += 1
    return total / count if count else ACS_BOND_LENGTH


def _avg_bond_length_from_conf(mol) -> float:
    """Average bond length from RDKit conformer coordinates."""
    conf = mol.GetConformer()
    total, count = 0.0, 0
    for bond in mol.GetBonds():
        p0 = conf.GetAtomPosition(bond.GetBeginAtomIdx())
        p1 = conf.GetAtomPosition(bond.GetEndAtomIdx())
        total += math.sqrt(
            (p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2)
        count += 1
    return total / count if count else 1.5
