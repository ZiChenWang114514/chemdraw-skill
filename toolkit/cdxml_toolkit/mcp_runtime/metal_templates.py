"""Drawn templates for common metal complexes.

A reagent table stores a complex such as Pd(PPh3)4 as a lone metal atom beside its
ligands, because SMILES has no bond for a phosphine donor or an eta-5 ring. Drawn
that way the metal floats next to loose ligands. Each template here keeps the same
atoms and adds what the drawing needs:

* donor bonds (``P->[Pd]``) written in the template SMILES, so the complex is one
  connected structure, and
* eta-n attachments (``hapto``): a ChemDraw multi-attachment node at the centre of
  the ring, bonded to the metal, for sandwich ligands such as cyclopentadienyl.

A species is matched to a template by name or by structure (the template with its
donor bonds removed). The template structures were assembled from the toolkit's
reagent table entries by adding those bonds; no atom was invented.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Geometry import Point2D

from ..chemistry_semantics import read_fragment_element, semantic_key

_PPH3 = "P(c1ccccc1)(c1ccccc1)c1ccccc1"
_PCY3 = "P(C4CCCCC4)(C4CCCCC4)C4CCCCC4"  # ring digit 4: it is spliced inside open rings 1-3


@dataclass(frozen=True)
class MetalTemplate:
    id: str
    names: tuple[str, ...]
    smiles: str  # donor bonds written as dative bonds; eta-n rings left unbonded
    hapto: tuple[tuple[int, tuple[int, ...]], ...] = field(default=())  # (metal atom, ring atoms)


TEMPLATES: tuple[MetalTemplate, ...] = (
    MetalTemplate(
        "pd_pph3_4", ("Pd(PPh3)4", "tetrakis(triphenylphosphine)palladium",
                      "tetrakis(triphenylphosphine)palladium(0)"),
        f"{_PPH3}->[Pd](<-{_PPH3})(<-{_PPH3})<-{_PPH3}",
    ),
    MetalTemplate(
        "wilkinson", ("Wilkinson's catalyst", "RhCl(PPh3)3", "Rh(PPh3)3Cl",
                      "chlorotris(triphenylphosphine)rhodium", "chlorotris(triphenylphosphine)rhodium(I)"),
        f"Cl[Rh](<-{_PPH3})(<-{_PPH3})<-{_PPH3}",
    ),
    MetalTemplate(
        "grubbs_ii", ("Grubbs II", "Grubbs 2nd generation catalyst", "Grubbs second generation catalyst",
                      "Grubbs catalyst 2nd generation"),
        "Cc1cc(C)c(N2CCN(c3c(C)cc(C)cc3C)[C]2=[Ru](Cl)(Cl)(=[CH]c2ccccc2)<-" + _PCY3 + ")c(C)c1",
    ),
    MetalTemplate(
        "ferrocene", ("ferrocene", "Cp2Fe", "FeCp2", "bis(cyclopentadienyl)iron"),
        "[cH-]1cccc1.[Fe+2].[cH-]1cccc1",
        hapto=((5, (0, 1, 2, 3, 4)), (5, (6, 7, 8, 9, 10))),
    ),
    MetalTemplate(
        "pd_dppf_cl2", ("Pd(dppf)Cl2", "PdCl2(dppf)",
                        "[1,1'-bis(diphenylphosphino)ferrocene]dichloropalladium(II)"),
        "[cH-]1cccc1P(c1ccccc1)(c1ccccc1)->[Pd](Cl)(Cl)<-P(c1ccccc1)(c1ccccc1)c1ccc[cH-]1.[Fe+2]",
        hapto=((39, (0, 1, 2, 3, 4)), (39, (34, 35, 36, 37, 38))),
    ),
)


def _without_dative(mol: Chem.Mol) -> Chem.Mol:
    rw = Chem.RWMol(mol)
    for bond in reversed(list(rw.GetBonds())):
        if bond.GetBondType() == Chem.BondType.DATIVE:
            rw.RemoveBond(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())
    out = rw.GetMol()
    Chem.SanitizeMol(out)
    return out


@lru_cache(maxsize=None)
def _keys() -> dict[str, MetalTemplate]:
    """Structure keys (connected and loose form) of every template."""
    keys: dict[str, MetalTemplate] = {}
    for template in TEMPLATES:
        mol = Chem.MolFromSmiles(template.smiles)
        keys[semantic_key(mol)] = template
        keys[semantic_key(_without_dative(mol))] = template
    return keys


def _norm(name: str) -> str:
    return "".join(str(name).lower().replace("’", "'").split())


def find_template(name: str | None = None, smiles: str | None = None) -> MetalTemplate | None:
    """The template a species name or SMILES describes, else None."""
    if name:
        wanted = _norm(name)
        for template in TEMPLATES:
            if wanted in {_norm(n) for n in template.names}:
                return template
    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            return _keys().get(semantic_key(mol))
    return None


def fragment_graph(fragment: ET.Element) -> Chem.Mol:
    """The drawn connectivity of a fragment, eta-n attachments counted as bonds to every ring atom.

    Element and charge come from the nodes; bond orders are not needed for a
    connectivity check, so every bond is single. Implicit hydrogens are ignored.
    """
    rw = Chem.RWMol()
    index: dict[str, int] = {}
    attach: dict[str, list[str]] = {}
    for node in fragment.findall("n"):
        if node.get("NodeType") == "MultiAttachment":
            attach[node.get("id", "")] = (node.get("Attachments") or "").split()
            continue
        atom = Chem.Atom(int(node.get("Element") or 6))
        atom.SetFormalCharge(int(node.get("Charge") or 0))
        atom.SetNoImplicit(True)
        index[node.get("id", "")] = rw.AddAtom(atom)
    for bond in fragment.findall("b"):
        begin, end = bond.get("B", ""), bond.get("E", "")
        ends = [[begin], [end]]
        for k, ref in enumerate((begin, end)):
            if ref in attach:
                ends[k] = attach[ref]
        for a in ends[0]:
            for b in ends[1]:
                if a in index and b in index and rw.GetBondBetweenAtoms(index[a], index[b]) is None:
                    rw.AddBond(index[a], index[b], Chem.BondType.SINGLE)
    return rw.GetMol()


def _ordered_ring(mol: Chem.Mol, atoms: tuple[int, ...]) -> list[int]:
    wanted = set(atoms)
    for ring in mol.GetRingInfo().AtomRings():
        if set(ring) == wanted:
            return list(ring)
    raise ValueError("hapto atoms are not one ring")


def _coordinates(template: MetalTemplate) -> Chem.Mol:
    """Template molecule with 2D coordinates: each eta-n ring a regular polygon above or below its metal."""
    mol = Chem.MolFromSmiles(template.smiles)
    rings = [(metal, _ordered_ring(mol, atoms)) for metal, atoms in template.hapto]
    # Depict a proxy in which the metal is bonded to its rings, so RDKit lays the
    # substituents out around the fixed core; the proxy bonds are not drawn.
    proxy = Chem.RWMol(mol)
    coord_map: dict[int, Point2D] = {}
    bond = 1.5
    for k, (metal, ring) in enumerate(rings):
        coord_map[metal] = Point2D(0.0, 0.0)
        radius = bond / (2 * math.sin(math.pi / len(ring)))
        cy = (1 if k % 2 == 0 else -1) * (radius + bond)
        for j, atom in enumerate(ring):
            angle = math.pi / 2 + 2 * math.pi * j / len(ring)
            coord_map[atom] = Point2D(radius * math.cos(angle), cy + radius * math.sin(angle) * 0.55)
        if proxy.GetBondBetweenAtoms(metal, ring[0]) is None:
            proxy.AddBond(metal, ring[0], Chem.BondType.SINGLE)
    proxy_mol = proxy.GetMol()
    proxy_mol.UpdatePropertyCache(strict=False)
    rdDepictor.Compute2DCoords(proxy_mol, coordMap=coord_map)
    conf = proxy_mol.GetConformer()
    mol.RemoveAllConformers()
    out = Chem.Conformer(mol.GetNumAtoms())
    for i in range(mol.GetNumAtoms()):
        out.SetAtomPosition(i, conf.GetAtomPosition(i))
    mol.AddConformer(out, assignId=True)
    return mol


def hapto_fragment(template: MetalTemplate, center_x: float, center_y: float, first_id: int) -> ET.Element:
    """A CDXML fragment of an eta-n template centred on the given point, ids from ``first_id``."""
    from ..image.structure_from_image import normalize_for_cdxml
    from ..render import renderer

    mol = _coordinates(template)
    source = Chem.Mol(mol)
    kek = Chem.RWMol(mol)
    try:
        Chem.Kekulize(kek, clearAromaticFlags=True)
        mol = kek.GetMol()
    except Exception:
        pass
    atoms, bonds = renderer._extract_mol_atom_bond_dicts(mol, source_mol=source)
    atoms, bonds = normalize_for_cdxml(atoms, bonds, center_x, center_y)
    ids = renderer._IDGen(first_id)
    xml, atom_map, _ = renderer._build_fragment(atoms, bonds, ids)
    fragment = ET.fromstring(xml)
    by_index = {a["index"]: a for a in atoms}
    for metal, ring in template.hapto:
        pts = [by_index[k + 1] for k in ring]
        cx = sum(p["x"] for p in pts) / len(pts)
        cy = sum(p["y"] for p in pts) / len(pts)
        node_id = str(ids.next())
        ET.SubElement(fragment, "n", {"id": node_id, "p": f"{cx:.2f} {cy:.2f}", "NodeType": "MultiAttachment",
                                      "Attachments": " ".join(str(atom_map[k + 1]) for k in ring)})
        ET.SubElement(fragment, "b", {"id": str(ids.next()), "B": str(atom_map[metal + 1]), "E": node_id,
                                      "Order": "dative"})
    return fragment


def strip_hapto(fragment: ET.Element) -> ET.Element:
    """A copy of a fragment without its multi-attachment nodes and their bonds (for structure read-back)."""
    import copy

    out = copy.deepcopy(fragment)
    ids = {n.get("id") for n in out.findall("n") if n.get("NodeType") == "MultiAttachment"}
    for node in list(out.findall("n")):
        if node.get("id") in ids:
            out.remove(node)
    for bond in list(out.findall("b")):
        if bond.get("B") in ids or bond.get("E") in ids:
            out.remove(bond)
    return out


def apply_hapto_templates(cdxml: str, templates: dict[str, MetalTemplate]) -> str:
    """Replace each drawn fragment whose structure is an eta-n template by the template drawing.

    ``templates`` maps a structure key (of the SMILES the renderer drew) to its template.
    """
    if not templates:
        return cdxml
    text = str(cdxml)
    head, sep, body = text.partition("?>") if text.lstrip().startswith("<?xml") else ("", "", text)
    root = ET.fromstring(body)
    used = [int(v) for el in root.iter() for v in [el.get("id")] if v and v.isdigit()]
    next_id = max(used, default=0) + 1
    changed = False
    for page in root.iter("page"):
        for k, fragment in enumerate(list(page)):
            if fragment.tag != "fragment":
                continue
            try:
                mols = read_fragment_element(fragment)
            except Exception:
                continue
            if len(mols) != 1:
                continue
            template = templates.get(semantic_key(mols[0]))
            if template is None or not template.hapto:
                continue
            pts = [tuple(map(float, n.get("p", "0 0").split()[:2])) for n in fragment.findall("n")]
            cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
            cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
            new = hapto_fragment(template, cx, cy, next_id)
            next_id = max(int(v) for el in new.iter() for v in [el.get("id")] if v and v.isdigit()) + 1
            new.set("id", fragment.get("id", new.get("id")))
            page.remove(fragment)
            page.insert(k, new)
            changed = True
    if not changed:
        return cdxml
    out = (head + sep if sep else "") + ("\n" if sep else "") + ET.tostring(root, encoding="unicode")
    from ..render import renderer

    wrapped = renderer._ValidatedCDXML(out)
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped
