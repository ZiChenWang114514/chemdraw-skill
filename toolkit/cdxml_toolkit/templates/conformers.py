"""Pure-Python deterministic 2D conformer and perspective projection generators for CDXML.

Provides exact parametric coordinate and CDXML fragment/graphic builders for:
  - chair_cyclohexane (chair1 and ring-flipped chair2 with vertical axial and parallel equatorial vectors)
  - newman_projection (staggered and eclipsed with circle graphic and perimeter-clipped rear spokes)
  - haworth_pyranose (alpha/beta 6-membered perspective pyranose ring with Bold and WedgeBegin lower bonds)
  - fischer_projection (orthogonal Fischer cross backbone)
  - bicyclic_cage (norbornane, bicyclo_222, and adamantane with CrossingBonds)
  - build_conformer_cdxml (dispatcher to full ACS 1996 CDXML document)
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape as xml_escape


_SIMPLE_ELEMENTS: dict[str, int] = {
    "H": 1,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "Si": 14,
    "P": 15,
    "S": 16,
    "Cl": 17,
    "Br": 35,
    "I": 53,
}


def _runs_xml(label: str, font: int = 3, size: int = 10) -> str:
    """Format a chemical label with subscripted digits as CDXML <s> runs."""
    parts = re.split(r"(?<=[A-Za-z\)])(\d+)", label)
    out: list[str] = []
    for idx, piece in enumerate(parts):
        if not piece:
            continue
        face = 32 if (idx % 2 == 1 and piece.isdigit()) else 0
        out.append(
            f'<s font="{font}" size="{size}" color="0" face="{face}">{xml_escape(piece)}</s>'
        )
    if not out:
        out.append(f'<s font="{font}" size="{size}" color="0" face="0">{xml_escape(label)}</s>')
    return "".join(out)


# Labels that are one heavy atom plus hydrogens: written as a plain element node.
_HYDRIDE_LABELS: dict[str, tuple[int, int]] = {
    "OH": (8, 1), "HO": (8, 1), "NH2": (7, 2), "H2N": (7, 2), "SH": (16, 1), "HS": (16, 1),
    "Me": (6, 3), "CH3": (6, 3), "H3C": (6, 3), "NH": (7, 1),
}

# Multi-atom labels: written as ChemDraw abbreviations (NodeType="Fragment" with the expansion);
# the first SMILES atom is the attachment atom.
_ABBREVIATION_SMILES: dict[str, str] = {
    "CH2OH": "CO", "HOCH2": "CO", "CHO": "C=O", "OHC": "C=O", "COOH": "C(=O)O", "CO2H": "C(=O)O",
    "HOOC": "C(=O)O", "CO2Me": "C(=O)OC", "MeO2C": "C(=O)OC", "OMe": "OC", "MeO": "OC",
    "OAc": "OC(C)=O", "AcO": "OC(C)=O", "NHAc": "NC(C)=O", "AcHN": "NC(C)=O", "Et": "CC",
    "iPr": "C(C)C", "tBu": "C(C)(C)C", "Ph": "c1ccccc1", "CN": "C#N", "NC": "C#N",
    "CH2OAc": "COC(C)=O", "CH2NH2": "CN", "OBn": "OCc1ccccc1", "BnO": "OCc1ccccc1",
}


def _abbreviation_inner_fragment(smiles: str, ax: float, ay: float, next_id) -> str:
    """Inner <fragment> expansion of an abbreviation, attached through an ExternalConnectionPoint."""
    from rdkit import Chem
    from rdkit.Chem import rdDepictor

    mol = Chem.MolFromSmiles(smiles)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    p0 = conf.GetAtomPosition(0)
    scale = 14.4 / 1.5
    ids = {a.GetIdx(): next_id() for a in mol.GetAtoms()}
    lines = [f'<fragment id="{next_id()}">']
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        x, y = ax + (pos.x - p0.x) * scale, ay - (pos.y - p0.y) * scale
        extra = ""
        if atom.GetAtomicNum() != 6:
            extra = f' Element="{atom.GetAtomicNum()}" NumHydrogens="{atom.GetTotalNumHs()}"'
        lines.append(f'<n id="{ids[atom.GetIdx()]}" p="{x:.2f} {y:.2f}"{extra}/>')
    for bond in mol.GetBonds():
        order = {Chem.BondType.DOUBLE: ' Order="2"', Chem.BondType.TRIPLE: ' Order="3"',
                 Chem.BondType.AROMATIC: ' Order="1.5"'}.get(bond.GetBondType(), "")
        lines.append(f'<b id="{next_id()}" B="{ids[bond.GetBeginAtomIdx()]}" E="{ids[bond.GetEndAtomIdx()]}"{order}/>')
    ecp = next_id()
    lines.append(f'<n id="{ecp}" NodeType="ExternalConnectionPoint" p="{ax - 14.4:.2f} {ay:.2f}" ExternalConnectionNum="1"/>')
    lines.append(f'<b id="{next_id()}" B="{ecp}" E="{ids[0]}"/>')
    lines.append("</fragment>")
    return "".join(lines)


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    """Return True if open segment AB strictly intersects open segment CD."""
    def ccw(p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> float:
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

    d1 = ccw(a, b, c)
    d2 = ccw(a, b, d)
    d3 = ccw(c, d, a)
    d4 = ccw(c, d, b)
    return (d1 * d2 < -1e-6) and (d3 * d4 < -1e-6)


def _build_fragment_and_cdxml(
    atoms: list[dict[str, Any]],
    bonds: list[dict[str, Any]],
    *,
    graphics_xml: list[str] | None = None,
    bond_length: float = 14.4,
    start_id: int = 1000,
) -> tuple[str, str, dict[int, int], dict[int, int]]:
    """Build `<fragment>` XML and full ACS 1996 `<CDXML>` document from atom/bond dicts."""
    nid = start_id

    def next_id() -> int:
        nonlocal nid
        nid += 1
        return nid

    frag_id = next_id()
    xs = [float(a["x"]) for a in atoms] if atoms else [0.0]
    ys = [float(a["y"]) for a in atoms] if atoms else [0.0]
    pad = 12.0
    bb_x1, bb_y1 = min(xs) - pad, min(ys) - pad
    bb_x2, bb_y2 = max(xs) + pad, max(ys) + pad

    atom_id_map: dict[int, int] = {}
    bond_id_map: dict[int, int] = {}

    for a in atoms:
        atom_id_map[int(a["index"])] = next_id()
    for b in bonds:
        bond_id_map[int(b["index"])] = next_id()

    frag_lines: list[str] = [
        f'<fragment id="{frag_id}" BoundingBox="{min(xs):.2f} {min(ys):.2f} {max(xs):.2f} {max(ys):.2f}" Z="{next_id()}">'
    ]

    for a in atoms:
        idx = int(a["index"])
        aid = atom_id_map[idx]
        ax = float(a["x"])
        ay = float(a["y"])
        sym = str(a.get("symbol", "C"))
        show_label = bool(a.get("show_label", sym != "C"))
        z_atom = next_id()
        attrs = [f'id="{aid}"', f'p="{ax:.2f} {ay:.2f}"', f'Z="{a.get("z", z_atom)}"']

        if not show_label and sym == "C":
            frag_lines.append(f'<n {" ".join(attrs)}/>')
            continue

        inner_xml = ""
        if sym in _SIMPLE_ELEMENTS and not a.get("generic"):
            el_num = _SIMPLE_ELEMENTS[sym]
            nh = int(a.get("num_hydrogens", 0))
            attrs.append(f'Element="{el_num}"')
            attrs.append(f'NumHydrogens="{nh}"')
        elif sym in _HYDRIDE_LABELS and not a.get("generic"):
            el_num, nh = _HYDRIDE_LABELS[sym]
            attrs.append(f'Element="{el_num}"')
            attrs.append(f'NumHydrogens="{nh}"')
        elif sym in _ABBREVIATION_SMILES and not a.get("generic"):
            attrs.append('NodeType="Fragment"')
            inner_xml = _abbreviation_inner_fragment(_ABBREVIATION_SMILES[sym], ax, ay, next_id)
        else:
            attrs.append('NodeType="GenericNickname"')
            attrs.append(f'GenericNickname="{xml_escape(sym)}"')

        just = str(a.get("justification", "Left"))
        tid = next_id()
        lx = ax - 3.25
        ly = ay + 3.50
        w = max(6.0, len(sym) * 5.5)
        frag_lines.append(
            f'<n {" ".join(attrs)}>{inner_xml}'
            f'<t id="{tid}" p="{lx:.2f} {ly:.2f}" '
            f'BoundingBox="{lx:.2f} {ay - 7.5:.2f} {lx + w:.2f} {ay:.2f}" '
            f'LabelJustification="{just}" LabelAlignment="{just}">'
            f'{_runs_xml(sym)}</t></n>'
        )

    for b in bonds:
        b_idx = int(b["index"])
        bid = bond_id_map[b_idx]
        a1 = atom_id_map[int(b["atom1"])]
        a2 = atom_id_map[int(b["atom2"])]
        z_bond = next_id()
        attrs = [f'id="{bid}"', f'Z="{b.get("z", z_bond)}"', f'B="{a1}"', f'E="{a2}"']
        order = b.get("order", 1)
        if order in (2, "2"):
            attrs.append('Order="2"')
        elif order in (3, "3"):
            attrs.append('Order="3"')
        elif order == "dative":
            attrs.append('Order="dative"')

        display = b.get("display")
        if display:
            attrs.append(f'Display="{display}"')

        crossing = b.get("crossing_bonds") or []
        if crossing:
            crossed_xml_ids = " ".join(str(bond_id_map[int(c)]) for c in crossing if int(c) in bond_id_map)
            if crossed_xml_ids:
                attrs.append(f'CrossingBonds="{crossed_xml_ids}"')

        frag_lines.append(f'<b {" ".join(attrs)}/>')

    frag_lines.append("</fragment>")
    fragment_xml = "\n".join(frag_lines)

    page_items: list[str] = []
    if graphics_xml:
        page_items.extend(graphics_xml)
    page_items.append(fragment_xml)

    cdxml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd">\n'
        f'<CDXML BoundingBox="{bb_x1:.2f} {bb_y1:.2f} {bb_x2:.2f} {bb_y2:.2f}" '
        f'BondLength="{bond_length:g}" LabelFont="3" LabelSize="10" LabelFace="96" '
        'CaptionFont="3" CaptionSize="10" LineWidth="0.6" BoldWidth="2" HashSpacing="2.5" '
        'MarginWidth="1.6" BondSpacing="18" ChainAngle="120" LabelJustification="Auto" '
        'CaptionJustification="Left" color="0" bgcolor="1">'
        '<colortable>'
        '<color r="1" g="1" b="1"/>'
        '<color r="0" g="0" b="0"/>'
        '<color r="0.8392" g="0.9176" b="0.9725"/>'
        '</colortable>'
        '<fonttable>'
        '<font id="3" charset="iso-8859-1" name="Arial"/>'
        '<font id="5" charset="Unicode" name="SimSun"/>'
        '</fonttable>'
        '<page id="1">\n'
        + "\n".join(page_items)
        + "\n</page></CDXML>\n"
    )
    return fragment_xml, cdxml, atom_id_map, bond_id_map


def chair_cyclohexane(
    *,
    flip: bool = False,
    substituents: Mapping[int, Mapping[str, str]] | None = None,
    cx: float = 180.0,
    cy: float = 160.0,
    bond_length: float = 14.4,
) -> dict[str, Any]:
    """Generate a 6-membered chair cyclohexane (chair1 or ring-flipped chair2).

    Parameters
    ----------
    flip : bool
        When False (`chair1`), C1/C3/C5 are down-puckered (`+y` axial) and C2/C4/C6
        are up-puckered (`-y` axial). When True (`chair2`), puckers and axial vectors
        invert while opposite ring bonds remain strictly parallel.
    substituents : mapping of 1..6 -> {"ax": label, "eq": label}, optional
        Substituents placed along exact vertical axial or parallel equatorial vectors.
    cx, cy : float
        Ring centroid in CDXML points.
    bond_length : float
        Target C-C and substituent bond length in points (default 14.4).
    """
    L = float(bond_length)
    sign_y = -1.0 if flip else 1.0

    # Three generator bond vectors (u = C1->C2, v = C2->C3, w = C3->C4) of exact length L.
    # Central symmetry guarantees opposite bonds (C4->C5 = -u, C5->C6 = -v, C6->C1 = -w)
    # are strictly parallel and equal in length.
    u = (L * math.cos(math.radians(-55.0)), sign_y * L * math.sin(math.radians(-55.0)))
    v = (L * math.cos(math.radians(160.0)), sign_y * L * math.sin(math.radians(160.0)))
    w = (L * math.cos(math.radians(-160.0)), sign_y * L * math.sin(math.radians(-160.0)))

    p1 = (cx - 0.5 * (u[0] + v[0] + w[0]), cy - 0.5 * (u[1] + v[1] + w[1]))
    p2 = (p1[0] + u[0], p1[1] + u[1])
    p3 = (p2[0] + v[0], p2[1] + v[1])
    p4 = (2.0 * cx - p1[0], 2.0 * cy - p1[1])
    p5 = (2.0 * cx - p2[0], 2.0 * cy - p2[1])
    p6 = (2.0 * cx - p3[0], 2.0 * cy - p3[1])
    ring_coords: list[tuple[float, float]] = [p1, p2, p3, p4, p5, p6]

    # Exact vertical axial vectors:
    # flip=False: C1, C3, C5 down (+L), C2, C4, C6 up (-L)
    # flip=True:  C1, C3, C5 up (-L), C2, C4, C6 down (+L)
    axial_vectors: dict[int, tuple[float, float]] = {}
    equatorial_vectors: dict[int, tuple[float, float]] = {}

    for k in range(6):
        pos = k + 1
        is_odd = (pos % 2 == 1)
        ay_dir = (1.0 if is_odd else -1.0) * sign_y
        axial_vectors[pos] = (0.0, ay_dir * L)

        # Equatorial vector is strictly parallel to the (k+1 -> k+2) and (k-1 -> k-2) ring bonds,
        # oriented outward from the ring centroid (cx, cy).
        b_start = ring_coords[(k + 1) % 6]
        b_end = ring_coords[(k + 2) % 6]
        dx = b_end[0] - b_start[0]
        dy = b_end[1] - b_start[1]
        norm = math.hypot(dx, dy) or 1.0
        ux, uy = dx / norm, dy / norm
        outward_x = ring_coords[k][0] - cx
        outward_y = ring_coords[k][1] - cy
        if ux * outward_x + uy * outward_y < 0.0:
            ux, uy = -ux, -uy
        equatorial_vectors[pos] = (ux * L, uy * L)

    atoms: list[dict[str, Any]] = []
    bonds: list[dict[str, Any]] = []
    for k, (rx, ry) in enumerate(ring_coords, start=1):
        atoms.append({"index": k, "symbol": "C", "x": rx, "y": ry, "ring_position": k})
    for k in range(6):
        bonds.append({
            "index": k + 1,
            "atom1": k + 1,
            "atom2": ((k + 1) % 6) + 1,
            "order": 1,
            "is_ring_bond": True,
        })

    if substituents:
        for raw_pos, sub_map in substituents.items():
            pos = int(raw_pos)
            if not (1 <= pos <= 6) or not isinstance(sub_map, Mapping):
                continue
            rx, ry = ring_coords[pos - 1]
            for key, vec in (("ax", axial_vectors[pos]), ("axial", axial_vectors[pos]),
                             ("eq", equatorial_vectors[pos]), ("equatorial", equatorial_vectors[pos])):
                if key not in sub_map or not sub_map[key]:
                    continue
                label = str(sub_map[key]).strip()
                if not label:
                    continue
                new_idx = len(atoms) + 1
                sx, sy = rx + vec[0], ry + vec[1]
                atoms.append({
                    "index": new_idx,
                    "symbol": label,
                    "x": sx,
                    "y": sy,
                    "show_label": True,
                    "attachment": "ax" if key.startswith("ax") else "eq",
                    "ring_position": pos,
                })
                bonds.append({
                    "index": len(bonds) + 1,
                    "atom1": pos,
                    "atom2": new_idx,
                    "order": 1,
                    "attachment": "ax" if key.startswith("ax") else "eq",
                })

    fragment_xml, cdxml, _, _ = _build_fragment_and_cdxml(atoms, bonds, bond_length=L)
    return {
        "template": "chair",
        "conformation": "chair2" if flip else "chair1",
        "flip": bool(flip),
        "cx": float(cx),
        "cy": float(cy),
        "bond_length": L,
        "ring_coords": ring_coords,
        "axial_vectors": axial_vectors,
        "equatorial_vectors": equatorial_vectors,
        "atoms": atoms,
        "bonds": bonds,
        "fragment_xml": fragment_xml,
        "graphics_xml": [],
        "cdxml": cdxml,
    }


def newman_projection(
    *,
    conformation: str = "staggered",
    dihedral_offset: float | None = None,
    front: Sequence[str] = ("Me", "H", "H"),
    rear: Sequence[str] = ("Br", "H", "Me"),
    cx: float = 180.0,
    cy: float = 160.0,
    bond_length: float = 24.0,
) -> dict[str, Any]:
    """Generate a Newman projection (staggered or eclipsed) with circle graphic and perimeter-clipped rear spokes.

    The molecule is a connected substituted ethane: the front carbon and one rear carbon share
    the projection centre and are bonded; rear bonds belong to the rear carbon and sit beneath
    the filled circle, so they appear to start at its rim. ``conformation="eclipsed"`` uses a
    14 degree dihedral offset (reported as ``dihedral_offset``) rather than 0, so eclipsed rear
    bonds stay visible beside the front bonds; pass ``dihedral_offset=0`` for exact eclipsing.
    """
    if len(front) != 3 or len(rear) != 3:
        raise ValueError("Newman projection requires exactly 3 front and 3 rear substituents.")

    L = float(bond_length)
    R = 0.48 * L
    front_angles = (-90.0, 30.0, 150.0)
    if dihedral_offset is not None:
        offset = float(dihedral_offset)
    else:
        conf_norm = conformation.strip().lower()
        if conf_norm == "staggered":
            offset = 60.0
        elif conf_norm == "eclipsed":
            offset = 14.0
        else:
            raise ValueError(f"Unsupported Newman conformation: {conformation!r}")
    rear_angles = tuple(a + offset for a in front_angles)

    atoms: list[dict[str, Any]] = [
        {"index": 1, "symbol": "C", "x": float(cx), "y": float(cy), "role": "front_center"}
    ]
    bonds: list[dict[str, Any]] = []
    front_spoke_ends: list[tuple[float, float]] = []
    rear_spoke_starts: list[tuple[float, float]] = []
    rear_spoke_ends: list[tuple[float, float]] = []

    for theta_deg, label in zip(front_angles, front):
        rad = math.radians(theta_deg)
        ex = cx + L * math.cos(rad)
        ey = cy + L * math.sin(rad)
        front_spoke_ends.append((ex, ey))
        sub_idx = len(atoms) + 1
        atoms.append({
            "index": sub_idx,
            "symbol": str(label),
            "x": ex,
            "y": ey,
            "show_label": True,
            "role": "front_substituent",
            "angle_deg": theta_deg,
        })
        bonds.append({
            "index": len(bonds) + 1,
            "atom1": 1,
            "atom2": sub_idx,
            "order": 1,
            "role": "front_spoke",
        })

    # One real rear carbon behind the front carbon, bonded to it: the graph is a substituted
    # ethane. Rear spokes start at the rear carbon but are drawn beneath the filled disk, so
    # only the part outside the circle shows (the Newman convention).
    rear_idx = len(atoms) + 1
    atoms.append({
        "index": rear_idx, "symbol": "C", "x": float(cx), "y": float(cy),
        "show_label": False, "role": "rear_center", "z": 3,
    })
    bonds.append({
        "index": len(bonds) + 1, "atom1": 1, "atom2": rear_idx, "order": 1,
        "role": "front_rear", "z": 4,
    })
    for theta_deg, label in zip(rear_angles, rear):
        rad = math.radians(theta_deg)
        sx = cx + R * math.cos(rad)
        sy = cy + R * math.sin(rad)
        ex = cx + L * math.cos(rad)
        ey = cy + L * math.sin(rad)
        rear_spoke_starts.append((sx, sy))
        rear_spoke_ends.append((ex, ey))
        sub_idx = len(atoms) + 1
        atoms.append({
            "index": sub_idx,
            "symbol": str(label),
            "x": ex,
            "y": ey,
            "show_label": True,
            "role": "rear_substituent",
            "angle_deg": theta_deg,
        })
        bonds.append({
            "index": len(bonds) + 1,
            "atom1": rear_idx,
            "atom2": sub_idx,
            "order": 1,
            "role": "rear_spoke",
            "z": 5 + len(bonds),
        })

    circle_graphic = (
        f'<graphic id="950" GraphicType="Oval" OvalType="Circle Filled" color="2" Z="100" '
        f'BoundingBox="{cx - R:.2f} {cy - R:.2f} {cx + R:.2f} {cy + R:.2f}" '
        f'Center3D="{cx:.2f} {cy:.2f} 0" MajorAxisEnd3D="{cx + R:.2f} {cy:.2f} 0" '
        f'MinorAxisEnd3D="{cx:.2f} {cy + R:.2f} 0"/>'
    )
    circle_outline_graphic = (
        f'<graphic id="951" GraphicType="Oval" OvalType="Circle" color="3" Z="101" '
        f'BoundingBox="{cx - R:.2f} {cy - R:.2f} {cx + R:.2f} {cy + R:.2f}" '
        f'Center3D="{cx:.2f} {cy:.2f} 0" MajorAxisEnd3D="{cx + R:.2f} {cy:.2f} 0" '
        f'MinorAxisEnd3D="{cx:.2f} {cy + R:.2f} 0"/>'
    )
    fragment_xml, cdxml, _, _ = _build_fragment_and_cdxml(
        atoms, bonds, graphics_xml=[circle_graphic, circle_outline_graphic], bond_length=L
    )
    return {
        "template": "newman",
        "conformation": conformation,
        "dihedral_offset": offset,
        "cx": float(cx),
        "cy": float(cy),
        "bond_length": L,
        "circle_radius": R,
        "front_angles": front_angles,
        "rear_angles": rear_angles,
        "front_spoke_ends": front_spoke_ends,
        "rear_spoke_starts": rear_spoke_starts,
        "rear_spoke_ends": rear_spoke_ends,
        "graphic_xml": circle_graphic,
        "graphics_xml": [circle_graphic, circle_outline_graphic],
        "atoms": atoms,
        "bonds": bonds,
        "fragment_xml": fragment_xml,
        "cdxml": cdxml,
    }


def _lower_up(sub_spec: Mapping[Any, Any], pos: int) -> bool:
    """True when ring atom ``pos`` carries an up substituent."""
    entry = sub_spec.get(pos) or sub_spec.get(str(pos)) or {}
    return bool(isinstance(entry, Mapping) and entry.get("up"))


def haworth_pyranose(
    *,
    anomer: str = "beta",
    substituents: Mapping[int, Mapping[str, str]] | None = None,
    cx: float = 180.0,
    cy: float = 160.0,
    bond_length: float = 18.0,
) -> dict[str, Any]:
    """Generate a 6-membered Haworth perspective pyranose ring."""
    L = float(bond_length)
    anomer_norm = anomer.strip().lower()
    if anomer_norm not in ("alpha", "beta"):
        raise ValueError(f"anomer must be 'alpha' or 'beta', got {anomer!r}")

    # Ring vertices: C1 rightmost, C2 bottom-right, C3 bottom-left, C4 leftmost, C5 top-left, O6 top-right
    ring_coords: dict[int, tuple[float, float]] = {
        1: (cx + 1.35 * L, cy),
        2: (cx + 0.65 * L, cy + 0.72 * L),
        3: (cx - 0.65 * L, cy + 0.72 * L),
        4: (cx - 1.35 * L, cy),
        5: (cx - 0.65 * L, cy - 0.72 * L),
        6: (cx + 0.65 * L, cy - 0.72 * L),
    }

    atoms: list[dict[str, Any]] = []
    for pos in range(1, 7):
        rx, ry = ring_coords[pos]
        if pos == 6:
            atoms.append({
                "index": 6,
                "symbol": "O",
                "x": rx,
                "y": ry,
                "show_label": True,
                "num_hydrogens": 0,
                "ring_position": 6,
            })
        else:
            atoms.append({
                "index": pos,
                "symbol": "C",
                "x": rx,
                "y": ry,
                "show_label": False,
                "ring_position": pos,
            })

    # Perspective ring bonds:
    # C2-C3 bottom horizontal with Display="Bold"
    # Slanted lower bonds C1-C2 and C4-C3 with Display="WedgeBegin"
    bonds: list[dict[str, Any]] = [
        {"index": 1, "atom1": 1, "atom2": 2, "order": 1, "display": "WedgeBegin", "is_ring_bond": True},
        {"index": 2, "atom1": 2, "atom2": 3, "order": 1, "display": "Bold", "is_ring_bond": True},
        {"index": 3, "atom1": 4, "atom2": 3, "order": 1, "display": "WedgeBegin", "is_ring_bond": True},
        {"index": 4, "atom1": 4, "atom2": 5, "order": 1, "is_ring_bond": True},
        {"index": 5, "atom1": 5, "atom2": 6, "order": 1, "is_ring_bond": True},
        {"index": 6, "atom1": 6, "atom2": 1, "order": 1, "is_ring_bond": True},
    ]

    if substituents is None:
        c1_map = {"up": "OH"} if anomer_norm == "beta" else {"down": "OH"}
        sub_spec: Mapping[Any, Mapping[str, str]] = {
            1: c1_map,
            2: {"down": "OH"},
            3: {"up": "OH"},
            4: {"down": "OH"},
            5: {"up": "CH2OH"},
        }
    else:
        sub_spec = substituents

    for raw_pos, pos_map in sub_spec.items():
        pos = int(raw_pos)
        if not (1 <= pos <= 5) or not isinstance(pos_map, Mapping):
            continue
        rx, ry = ring_coords[pos]
        for direction, dy_sign in (("up", -1.0), ("down", 1.0)):
            label = pos_map.get(direction)
            if not label:
                continue
            new_idx = len(atoms) + 1
            sx, sy = rx, ry + dy_sign * L
            just = "Left"
            side = 1.0 if pos in (1, 2) else -1.0
            if direction == "up" and pos in (2, 3):
                # A vertical up bond from a lower ring atom would put the label inside the ring:
                # lean it outward so the label sits above the ring plane, outside the polygon.
                sx, sy = rx + side * 0.9 * L, ry - 0.2 * L
                just = "Left" if side > 0 else "Right"
            elif direction == "down" and pos in (1, 4) and _lower_up(sub_spec, 2 if pos == 1 else 3):
                # Make room for the neighbouring lower atom's outward up label: tuck this bond
                # under the ring, away from that label.
                sx, sy = rx - side * 0.42 * L, ry + 1.1 * L
            atoms.append({
                "index": new_idx,
                "symbol": str(label),
                "x": sx,
                "y": sy,
                "show_label": True,
                "justification": just,
                "direction": direction,
                "ring_position": pos,
            })
            bonds.append({
                "index": len(bonds) + 1,
                "atom1": pos,
                "atom2": new_idx,
                "order": 1,
                "direction": direction,
            })

    fragment_xml, cdxml, _, _ = _build_fragment_and_cdxml(atoms, bonds, bond_length=L)
    return {
        "template": "haworth",
        "anomer": anomer_norm,
        "cx": float(cx),
        "cy": float(cy),
        "bond_length": L,
        "ring_coords": ring_coords,
        "atoms": atoms,
        "bonds": bonds,
        "fragment_xml": fragment_xml,
        "graphics_xml": [],
        "cdxml": cdxml,
    }


def fischer_projection(
    *,
    centers: Sequence[Mapping[str, str]] = ({"left": "H", "right": "OH"},),
    top: str = "CHO",
    bottom: str = "CH2OH",
    cx: float = 180.0,
    cy: float = 120.0,
    bond_length: float = 18.0,
) -> dict[str, Any]:
    """Generate an orthogonal Fischer projection cross backbone."""
    if not centers:
        centers = ({"left": "H", "right": "OH"},)
    L = float(bond_length)
    n_centers = len(centers)
    y_start = float(cy)

    atoms: list[dict[str, Any]] = [
        {"index": 1, "symbol": str(top), "x": float(cx), "y": y_start, "show_label": True, "role": "top"}
    ]
    bonds: list[dict[str, Any]] = []
    backbone_indices: list[int] = [1]

    for k, center in enumerate(centers, start=1):
        yk = y_start + k * L
        c_idx = len(atoms) + 1
        atoms.append({
            "index": c_idx,
            "symbol": "C",
            "x": float(cx),
            "y": yk,
            "show_label": False,
            "role": "chiral_center",
            "center_number": k,
        })
        bonds.append({
            "index": len(bonds) + 1,
            "atom1": backbone_indices[-1],
            "atom2": c_idx,
            "order": 1,
            "orientation": "vertical",
        })
        backbone_indices.append(c_idx)

        left_label = str(center.get("left", "H"))
        right_label = str(center.get("right", "OH"))

        left_idx = len(atoms) + 1
        atoms.append({
            "index": left_idx,
            "symbol": left_label,
            "x": float(cx) - L,
            "y": yk,
            "show_label": True,
            "justification": "Right",
            "role": "left",
            "center_number": k,
        })
        bonds.append({
            "index": len(bonds) + 1,
            "atom1": c_idx,
            "atom2": left_idx,
            "order": 1,
            "orientation": "horizontal",
        })

        right_idx = len(atoms) + 1
        atoms.append({
            "index": right_idx,
            "symbol": right_label,
            "x": float(cx) + L,
            "y": yk,
            "show_label": True,
            "justification": "Left",
            "role": "right",
            "center_number": k,
        })
        bonds.append({
            "index": len(bonds) + 1,
            "atom1": c_idx,
            "atom2": right_idx,
            "order": 1,
            "orientation": "horizontal",
        })

    bot_idx = len(atoms) + 1
    y_bot = y_start + (n_centers + 1) * L
    atoms.append({
        "index": bot_idx,
        "symbol": str(bottom),
        "x": float(cx),
        "y": y_bot,
        "show_label": True,
        "role": "bottom",
    })
    bonds.append({
        "index": len(bonds) + 1,
        "atom1": backbone_indices[-1],
        "atom2": bot_idx,
        "order": 1,
        "orientation": "vertical",
    })

    fragment_xml, cdxml, _, _ = _build_fragment_and_cdxml(atoms, bonds, bond_length=L)
    return {
        "template": "fischer",
        "cx": float(cx),
        "cy": float(cy),
        "bond_length": L,
        "centers_count": n_centers,
        "atoms": atoms,
        "bonds": bonds,
        "fragment_xml": fragment_xml,
        "graphics_xml": [],
        "cdxml": cdxml,
    }


def bicyclic_cage(
    *,
    scaffold: str = "norbornane",
    substituents: Mapping[int, str] | None = None,
    cx: float = 180.0,
    cy: float = 160.0,
    bond_length: float = 16.0,
) -> dict[str, Any]:
    """Generate a 3D perspective bridged cage (norbornane, bicyclo_222, adamantane) with CrossingBonds."""
    L = float(bond_length)
    scaf = scaffold.strip().lower()

    if scaf == "norbornane":
        # Bicyclo[2.2.1]heptane: C1, C4 bridgeheads; C2-C3 front; C6-C5 rear; C7 top methano bridge.
        # C1-C7 and C4-C7 cross in front of rear bond C5-C6.
        coords = {
            1: (cx - 1.15 * L, cy + 0.15 * L),
            2: (cx - 0.60 * L, cy + 0.85 * L),
            3: (cx + 0.60 * L, cy + 0.85 * L),
            4: (cx + 1.15 * L, cy + 0.15 * L),
            5: (cx + 0.42 * L, cy - 0.25 * L),
            6: (cx - 0.42 * L, cy - 0.25 * L),
            7: (cx, cy - 1.10 * L),
        }
        raw_bonds = [
            (1, 2, False),
            (2, 3, False),
            (3, 4, False),
            (4, 5, False),
            (5, 6, False),  # bond 5: rear horizontal C5-C6
            (6, 1, False),
            (1, 7, True),   # bond 7: front bridge C1-C7 crosses bond 5
            (4, 7, True),   # bond 8: front bridge C4-C7 crosses bond 5
        ]
    elif scaf in ("bicyclo_222", "bicyclo[2.2.2]octane"):
        scaf = "bicyclo_222"
        coords = {
            1: (cx, cy - 1.20 * L),
            2: (cx - 0.95 * L, cy - 0.50 * L),
            3: (cx - 0.95 * L, cy + 0.50 * L),
            4: (cx, cy + 1.20 * L),
            5: (cx + 0.95 * L, cy - 0.45 * L),
            6: (cx + 0.95 * L, cy + 0.45 * L),
            7: (cx + 0.32 * L, cy - 0.35 * L),
            8: (cx + 0.32 * L, cy + 0.35 * L),
        }
        raw_bonds = [
            (1, 2, False),
            (2, 3, False),
            (3, 4, False),
            (1, 5, False),
            (5, 6, False),
            (6, 4, False),
            (1, 7, True),
            (7, 8, True),   # front bridge C7-C8
            (8, 4, True),
        ]
    elif scaf == "adamantane":
        coords = {
            1: (cx, cy - 1.35 * L),
            2: (cx - 0.95 * L, cy - 0.65 * L),
            3: (cx - 0.95 * L, cy + 0.35 * L),
            4: (cx, cy + 0.95 * L),
            5: (cx + 0.95 * L, cy + 0.35 * L),
            6: (cx + 0.95 * L, cy - 0.65 * L),
            7: (cx - 0.35 * L, cy - 0.10 * L),
            8: (cx + 0.35 * L, cy - 0.85 * L),
            9: (cx + 0.35 * L, cy + 0.15 * L),
            10: (cx - 0.35 * L, cy + 0.90 * L),
        }
        raw_bonds = [
            (1, 2, False),
            (2, 3, False),
            (3, 10, False),
            (10, 5, False),
            (5, 6, False),
            (6, 8, False),
            (8, 1, False),
            (1, 7, True),
            (7, 4, True),   # front bridge crosses rear cage bond
            (4, 5, True),
            (3, 4, True),
            (6, 9, False),
        ]
    else:
        raise ValueError(f"Unsupported bicyclic/cage scaffold: {scaffold!r}")

    atoms: list[dict[str, Any]] = [
        {"index": idx, "symbol": "C", "x": pt[0], "y": pt[1], "show_label": False}
        for idx, pt in sorted(coords.items())
    ]

    bonds: list[dict[str, Any]] = []
    for b_idx, (a1, a2, is_front) in enumerate(raw_bonds, start=1):
        bonds.append({
            "index": b_idx,
            "atom1": a1,
            "atom2": a2,
            "order": 1,
            "is_front": is_front,
            "crossing_bonds": [],
        })

    # Detect geometric crossings between front bonds and rear bonds
    any_crossing = False
    for fb in bonds:
        if not fb["is_front"]:
            continue
        p1 = coords[fb["atom1"]]
        p2 = coords[fb["atom2"]]
        for rb in bonds:
            if rb["is_front"] or rb["index"] == fb["index"]:
                continue
            if len({fb["atom1"], fb["atom2"], rb["atom1"], rb["atom2"]}) < 4:
                continue
            q1 = coords[rb["atom1"]]
            q2 = coords[rb["atom2"]]
            if _segments_intersect(p1, p2, q1, q2):
                fb["crossing_bonds"].append(rb["index"])
                any_crossing = True

    if not any_crossing:
        # Ensure the primary front bridge carries explicit CrossingBonds over the rear bridge
        front_candidates = [b for b in bonds if b["is_front"]]
        rear_candidates = [b for b in bonds if not b["is_front"]]
        if front_candidates and rear_candidates:
            front_candidates[0]["crossing_bonds"].append(rear_candidates[-1]["index"])

    if substituents:
        for raw_pos, label in substituents.items():
            pos = int(raw_pos)
            if pos not in coords or not label:
                continue
            px, py = coords[pos]
            dx, dy = px - cx, py - cy
            norm = math.hypot(dx, dy) or 1.0
            sx, sy = px + (dx / norm) * L, py + (dy / norm) * L
            new_idx = len(atoms) + 1
            atoms.append({
                "index": new_idx,
                "symbol": str(label),
                "x": sx,
                "y": sy,
                "show_label": True,
                "attached_to": pos,
            })
            bonds.append({
                "index": len(bonds) + 1,
                "atom1": pos,
                "atom2": new_idx,
                "order": 1,
                "is_front": False,
                "crossing_bonds": [],
            })

    fragment_xml, cdxml, _, _ = _build_fragment_and_cdxml(atoms, bonds, bond_length=L)
    return {
        "template": scaf,
        "scaffold": scaf,
        "cx": float(cx),
        "cy": float(cy),
        "bond_length": L,
        "atoms": atoms,
        "bonds": bonds,
        "fragment_xml": fragment_xml,
        "graphics_xml": [],
        "cdxml": cdxml,
    }


def build_conformer_cdxml(
    spec: Mapping[str, Any],
    output_path: str | Path | None = None,
) -> str:
    """Dispatch on ``spec['template']`` and return a complete ACS 1996 CDXML document."""
    if not isinstance(spec, Mapping):
        raise ValueError("spec must be a mapping with a 'template' key.")
    tmpl = str(spec.get("template") or spec.get("scaffold") or "").strip().lower()
    at = spec.get("at") or spec.get("center")
    cx = float(at[0] if isinstance(at, (list, tuple)) and len(at) >= 2 else spec.get("cx", 180.0))
    cy = float(at[1] if isinstance(at, (list, tuple)) and len(at) >= 2 else spec.get("cy", 160.0))

    if tmpl in ("chair", "chair_cyclohexane"):
        res = chair_cyclohexane(
            flip=bool(spec.get("flip", False)),
            substituents=spec.get("substituents"),
            cx=cx,
            cy=cy,
            bond_length=float(spec.get("bond_length", 14.4)),
        )
    elif tmpl in ("newman", "newman_projection"):
        res = newman_projection(
            conformation=str(spec.get("conformation", "staggered")),
            dihedral_offset=(float(spec["dihedral_offset"]) if spec.get("dihedral_offset") is not None else None),
            front=tuple(spec.get("front", ("Me", "H", "H"))),
            rear=tuple(spec.get("rear", ("Br", "H", "Me"))),
            cx=cx,
            cy=cy,
            bond_length=float(spec.get("bond_length", 24.0)),
        )
    elif tmpl in ("haworth", "haworth_pyranose"):
        res = haworth_pyranose(
            anomer=str(spec.get("anomer", "beta")),
            substituents=spec.get("substituents"),
            cx=cx,
            cy=cy,
            bond_length=float(spec.get("bond_length", 18.0)),
        )
    elif tmpl in ("fischer", "fischer_projection"):
        res = fischer_projection(
            centers=tuple(spec.get("centers", ({"left": "H", "right": "OH"},))),
            top=str(spec.get("top", "CHO")),
            bottom=str(spec.get("bottom", "CH2OH")),
            cx=cx,
            cy= float(at[1] if isinstance(at, (list, tuple)) and len(at) >= 2 else spec.get("cy", 120.0)),
            bond_length=float(spec.get("bond_length", 18.0)),
        )
    elif tmpl in ("norbornane", "bicyclo_222", "adamantane", "bicyclic_cage", "cage"):
        scaffold_name = str(spec.get("scaffold", "norbornane" if tmpl in ("bicyclic_cage", "cage") else tmpl))
        res = bicyclic_cage(
            scaffold=scaffold_name,
            substituents=spec.get("substituents"),
            cx=cx,
            cy=cy,
            bond_length=float(spec.get("bond_length", 16.0)),
        )
    else:
        raise ValueError(f"Unknown conformer template: {tmpl!r}")

    cdxml = str(res["cdxml"])
    if output_path is not None:
        Path(output_path).write_text(cdxml, encoding="utf-8")
    return cdxml
