#!/usr/bin/env python
"""
scheme_aligner.py - Align reaction scheme structures using RDKit MCS.

Experimental tool. Uses Maximum Common Substructure (MCS) to find shared
scaffolds between the product and every other drawn structure (reactants,
reagents) in a CDXML reaction scheme, then aligns each structure's 2D
coordinates to match the product's orientation via RDKit's
GenerateDepictionMatching2DStructure.

The product is the reference — everything else aligns to it.

Inspired by:
  https://greglandrum.github.io/rdkit-blog/posts/2021-08-07-rgd-and-highlighting.html

Usage:
    python scheme_aligner.py reaction.cdxml
    python scheme_aligner.py reaction.cdxml -o aligned.cdxml --svg
"""

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from ...constants import ACS_BOND_LENGTH

try:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import AllChem, rdFMCS, rdDepictor
    from rdkit.Chem.Draw import rdMolDraw2D
    from rdkit.Geometry import Point3D
    RDLogger.logger().setLevel(RDLogger.ERROR)
except ImportError:
    sys.exit("Error: RDKit is required. Activate the LLMChem environment.")


# ---------------------------------------------------------------------------
# CDXML parsing
# ---------------------------------------------------------------------------

def parse_cdxml(path):
    """Parse CDXML file. Returns (tree, fragments_dict, reaction_steps)."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    page = root.find('.//page')
    if page is None:
        sys.exit("No <page> element in CDXML.")

    fragments = {int(f.get('id')): f for f in page.findall('fragment')}

    steps = []
    for s in root.findall('.//step'):
        steps.append({
            'reactants': _ids(s.get('ReactionStepReactants', '')),
            'products': _ids(s.get('ReactionStepProducts', '')),
            'above':    _ids(s.get('ReactionStepObjectsAboveArrow', '')),
            'below':    _ids(s.get('ReactionStepObjectsBelowArrow', '')),
        })

    return tree, fragments, steps


def _ids(s):
    return [int(x) for x in s.split() if x]


# ---------------------------------------------------------------------------
# Fragment -> RDKit Mol
# ---------------------------------------------------------------------------

def fragment_to_mol(frag_elem):
    """Convert a CDXML <fragment> to an RDKit Mol (no conformer set).

    Returns (mol, atoms_list) where atoms_list has per-atom metadata
    including original CDXML coordinates and XML element references.
    """
    atoms, id_map = [], {}

    for n in frag_elem.findall('n'):
        nid = int(n.get('id'))
        if n.get('NodeType') == 'ExternalConnectionPoint':
            continue

        px, py = [float(v) for v in n.get('p', '0 0').split()]
        elem = int(n.get('Element', '6'))
        num_h_attr = n.get('NumHydrogens')
        num_h = int(num_h_attr) if num_h_attr is not None else None
        is_abbrev = n.get('NodeType') == 'Fragment'

        idx = len(atoms)
        id_map[nid] = idx
        atoms.append({
            'id': nid, 'idx': idx,
            'x': px, 'y': py,
            'elem': elem, 'num_h': num_h,
            'is_abbrev': is_abbrev,
            'xml': n,
        })

    bonds = []
    for b in frag_elem.findall('b'):
        bi, ei = int(b.get('B')), int(b.get('E'))
        if bi in id_map and ei in id_map:
            bonds.append((id_map[bi], id_map[ei], int(b.get('Order', '1'))))

    em = Chem.RWMol()
    for a in atoms:
        ra = Chem.Atom(0 if a['is_abbrev'] else a['elem'])
        if a['num_h'] is not None:
            ra.SetNoImplicit(True)
            ra.SetNumExplicitHs(a['num_h'])
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
            Chem.SanitizeMol(mol,
                Chem.SanitizeFlags.SANITIZE_ALL ^
                Chem.SanitizeFlags.SANITIZE_PROPERTIES)
        except Exception:
            pass

    return mol, atoms


# ---------------------------------------------------------------------------
# Scale helpers
# ---------------------------------------------------------------------------

def avg_bond_length(atoms_data, mol):
    """Average bond length computed from CDXML atom coordinates."""
    total, count = 0.0, 0
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        dx = atoms_data[i]['x'] - atoms_data[j]['x']
        dy = atoms_data[i]['y'] - atoms_data[j]['y']
        total += math.sqrt(dx * dx + dy * dy)
        count += 1
    return total / count if count else ACS_BOND_LENGTH


_rdkit_bl_cache = None

def rdkit_bond_length():
    """RDKit's default 2D depiction bond length (cached)."""
    global _rdkit_bl_cache
    if _rdkit_bl_cache is None:
        m = Chem.MolFromSmiles('CC')
        AllChem.Compute2DCoords(m)
        c = m.GetConformer()
        p0, p1 = c.GetAtomPosition(0), c.GetAtomPosition(1)
        _rdkit_bl_cache = math.sqrt(
            (p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2)
    return _rdkit_bl_cache


def set_cdxml_coords(mol, atoms_data, scale=1.0):
    """Set conformer from CDXML coordinates (y-flipped, optionally scaled)."""
    conf = Chem.Conformer(mol.GetNumAtoms())
    for a in atoms_data:
        conf.SetAtomPosition(a['idx'],
            Point3D(a['x'] * scale, -a['y'] * scale, 0.0))
    mol.RemoveAllConformers()
    mol.AddConformer(conf, assignId=True)


# ---------------------------------------------------------------------------
# MCS finding
# ---------------------------------------------------------------------------

def find_mcs(ref_mol, target_mol, timeout=30):
    """Find MCS. Returns (mcs_result, atom_map [(ref_idx, tgt_idx)])."""
    mcs = rdFMCS.FindMCS(
        [ref_mol, target_mol],
        timeout=timeout,
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareOrder,
        ringMatchesRingOnly=True,
        completeRingsOnly=True,
    )

    if mcs.numAtoms < 3:
        return None, None

    core = Chem.MolFromSmarts(mcs.smartsString)
    if core is None:
        return None, None

    ref_match = ref_mol.GetSubstructMatch(core)
    target_match = target_mol.GetSubstructMatch(core)
    if not ref_match or not target_match:
        return None, None

    return mcs, list(zip(ref_match, target_match))


# ---------------------------------------------------------------------------
# Alignment via GenerateDepictionMatching2DStructure
# ---------------------------------------------------------------------------

def align_fragment(ref_mol, tgt_mol, atom_map):
    """Align target fragment to reference (product) using
    GenerateDepictionMatching2DStructure.

    ref_mol must already have its conformer set at RDKit scale.
    Modifies tgt_mol conformer in-place.
    Returns MCS RMSD in RDKit units.
    """
    rdDepictor.GenerateDepictionMatching2DStructure(
        tgt_mol, ref_mol, atom_map)

    # RMSD of MCS atoms (should be ~0)
    rc = ref_mol.GetConformer()
    tc = tgt_mol.GetConformer()
    ss = sum(
        (rc.GetAtomPosition(ri).x - tc.GetAtomPosition(ti).x) ** 2 +
        (rc.GetAtomPosition(ri).y - tc.GetAtomPosition(ti).y) ** 2
        for ri, ti in atom_map)
    return math.sqrt(ss / len(atom_map))


# ---------------------------------------------------------------------------
# Coordinate writeback
# ---------------------------------------------------------------------------

def _translate_subtree(elem, dx, dy):
    """Recursively shift all p and BoundingBox attributes by (dx, dy)."""
    p = elem.get('p')
    if p:
        parts = p.split()
        if len(parts) >= 2:
            elem.set('p',
                f"{float(parts[0])+dx:.2f} {float(parts[1])+dy:.2f}")

    bb = elem.get('BoundingBox')
    if bb:
        parts = bb.split()
        if len(parts) == 4:
            elem.set('BoundingBox',
                f"{float(parts[0])+dx:.2f} {float(parts[1])+dy:.2f} "
                f"{float(parts[2])+dx:.2f} {float(parts[3])+dy:.2f}")

    for child in elem:
        _translate_subtree(child, dx, dy)


def write_aligned_coords(frag_elem, mol, atoms_data, scale,
                         original_center):
    """Convert aligned RDKit coords back to CDXML space and write to XML."""
    conf = mol.GetConformer()
    inv = 1.0 / scale

    # Aligned positions in CDXML space
    aligned = []
    for a in atoms_data:
        pos = conf.GetAtomPosition(a['idx'])
        aligned.append((pos.x * inv, -pos.y * inv))   # scale + flip y

    # Translate to keep fragment at its original center
    acx = sum(p[0] for p in aligned) / len(aligned)
    acy = sum(p[1] for p in aligned) / len(aligned)
    gdx = original_center[0] - acx
    gdy = original_center[1] - acy

    for i, a in enumerate(atoms_data):
        new_x = aligned[i][0] + gdx
        new_y = aligned[i][1] + gdy
        adx = new_x - a['x']
        ady = new_y - a['y']

        node = a['xml']
        node.set('p', f"{new_x:.2f} {new_y:.2f}")

        for child in node:
            _translate_subtree(child, adx, ady)

    # Recompute fragment BoundingBox
    xs, ys = [], []
    for n in frag_elem.findall('n'):
        if n.get('NodeType') == 'ExternalConnectionPoint':
            continue
        p = n.get('p')
        if p:
            parts = p.split()
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
    if xs and ys:
        margin = 15.0
        frag_elem.set('BoundingBox',
            f"{min(xs)-margin:.2f} {min(ys)-margin:.2f} "
            f"{max(xs)+margin:.2f} {max(ys)+margin:.2f}")


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def save_svg(mol, highlight_atoms, label, out_dir, stem):
    """Save a single SVG with highlighted atoms."""
    drawer = rdMolDraw2D.MolDraw2DSVG(600, 450)
    drawer.drawOptions().addAtomIndices = False
    drawer.DrawMolecule(mol, highlightAtoms=highlight_atoms)
    drawer.FinishDrawing()
    svg_path = out_dir / f"{stem}-{label}.svg"
    svg_path.write_text(drawer.GetDrawingText())
    print(f"      SVG: {svg_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _centroid(atoms_data):
    n = len(atoms_data)
    return (sum(a['x'] for a in atoms_data) / n,
            sum(a['y'] for a in atoms_data) / n)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description='Align all structures in a reaction scheme to the '
                    'product orientation via RDKit MCS.',
    )
    ap.add_argument('input', help='Input CDXML file with reaction scheme')
    ap.add_argument('-o', '--output',
                    help='Output CDXML (default: <input>-aligned.cdxml)')
    ap.add_argument('--svg', action='store_true',
                    help='Save SVGs showing MCS-highlighted structures')
    ap.add_argument('--timeout', type=int, default=30,
                    help='MCS timeout in seconds (default: 30)')
    args = ap.parse_args(argv)

    inp = Path(args.input)
    if not inp.exists():
        print(f"File not found: {inp}", file=sys.stderr)
        return 1

    out = Path(args.output) if args.output else \
        inp.parent / (inp.stem + '-aligned.cdxml')

    tree, fragments, steps = parse_cdxml(inp)
    if not steps:
        print("No reaction scheme found in CDXML.", file=sys.stderr)
        return 1

    print(f"Input: {inp}")
    print(f"Fragments: {list(fragments.keys())}")
    print(f"Reaction steps: {len(steps)}")

    for si, step in enumerate(steps):
        if not step['products']:
            print(f"\nStep {si+1}: no products, skipping.")
            continue

        # --- Product is the reference ---
        prod_id = step['products'][0]
        prod_mol, prod_atoms = fragment_to_mol(fragments[prod_id])

        # Compute scale from product's bond length
        cdxml_bl = avg_bond_length(prod_atoms, prod_mol)
        rdk_bl = rdkit_bond_length()
        scale = rdk_bl / cdxml_bl

        # Set product conformer at RDKit scale (the reference for all alignments)
        set_cdxml_coords(prod_mol, prod_atoms, scale)

        print(f"\nStep {si+1}:")
        print(f"  Product = reference (fragment {prod_id}): "
              f"{prod_mol.GetNumAtoms()} atoms, "
              f"{prod_mol.GetNumBonds()} bonds")
        print(f"  Bond length: CDXML {cdxml_bl:.1f} pts -> "
              f"RDKit {rdk_bl:.2f}")

        if args.svg:
            save_svg(prod_mol, list(range(prod_mol.GetNumAtoms())),
                     'product-ref', out.parent, out.stem)

        # --- Collect all other drawn structures in this step ---
        other_ids = []
        for fid in (step['reactants'] + step['above'] + step['below']):
            if fid in fragments and fid != prod_id and fid not in other_ids:
                other_ids.append(fid)

        for fid in other_ids:
            frag_mol, frag_atoms = fragment_to_mol(fragments[fid])
            frag_center = _centroid(frag_atoms)

            print(f"\n  Fragment {fid}: "
                  f"{frag_mol.GetNumAtoms()} atoms, "
                  f"{frag_mol.GetNumBonds()} bonds")

            # Find MCS with product
            mcs, amap = find_mcs(prod_mol, frag_mol, args.timeout)
            if mcs is None:
                print(f"    MCS < 3 atoms, skipping.")
                continue

            print(f"    MCS: {mcs.numAtoms} atoms, {mcs.numBonds} bonds")

            # Align this fragment to the product
            rmsd = align_fragment(prod_mol, frag_mol, amap)
            print(f"    MCS RMSD: {rmsd:.4f}")

            # Write aligned coords back to CDXML
            write_aligned_coords(
                fragments[fid], frag_mol, frag_atoms, scale, frag_center)
            print(f"    Coordinates updated.")

            if args.svg:
                hl = [ti for ri, ti in amap]
                save_svg(frag_mol, hl, f'frag{fid}', out.parent, out.stem)

    tree.write(str(out), xml_declaration=True, encoding='UTF-8')
    print(f"\nOutput: {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
