#!/usr/bin/env python3
"""
cdxml_to_image_rdkit.py — BACKUP renderer for CDXML → PNG/SVG using RDKit.

⚠️  USE cdxml_to_image.py (ChemDraw COM) INSTEAD WHENEVER POSSIBLE. ⚠️

This script exists only as a fallback for environments where ChemDraw is not
installed (e.g. a remote server, CI, or a colleague's machine).

Known limitations vs ChemDraw COM
----------------------------------
- Single molecules only — reaction schemes with arrows are NOT supported.
- Bond geometry is recomputed by RDKit from scratch; the original ChemDraw
  layout is discarded.
- Aromatic systems are re-perceived by RDKit, which may differ from the
  Kekulé form stored in the CDXML.
- Superatom / nickname nodes (R-groups, OTs, Boc, etc.) are not rendered;
  the script will abort with an error if any are present.
- Stereo wedges are not transferred from the CDXML.
- No reaction conditions text, no yield labels, no compound numbering.
- RDKit in this environment lacks Cairo support, so PNG output requires
  cairosvg or wand to be installed; otherwise only SVG is produced.

Usage
-----
  python cdxml_to_image_rdkit.py input.cdxml
  python cdxml_to_image_rdkit.py input.cdxml -o out.svg
  python cdxml_to_image_rdkit.py input.cdxml -o out.png
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# CDXML → atom/bond parser  (minimal — just what RDKit needs)
# ---------------------------------------------------------------------------

ELEMENT_SYMBOLS: Dict[int, str] = {
    1: "H",  5: "B",  6: "C",  7: "N",  8: "O",
    9: "F",  14: "Si", 15: "P", 16: "S", 17: "Cl",
    34: "Se", 35: "Br", 53: "I",
}

_BOND_ORDER_MAP = {"1": 1, "2": 2, "3": 3, "1.5": 4, "": 1}


def _parse_cdxml(path: str):
    """
    Parse a CDXML file and return (atoms, bonds).

    atoms : dict  id → {"symbol": str, "x": float, "y": float}
    bonds : list  of {"b": int, "e": int, "order": int}

    Raises ValueError if reaction arrows or unsupported node types are found.
    """
    with open(path, "rb") as fh:
        raw_bytes = fh.read()

    raw_bytes = re.sub(rb'<objecttag\b[^/]*/>', b'', raw_bytes)
    raw_bytes = re.sub(rb'<objecttag\b.*?</objecttag>', b'', raw_bytes,
                       flags=re.DOTALL)
    raw = raw_bytes.decode("latin-1", errors="replace")
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffe\uffff]', '', raw)
    raw = re.sub(r'<!DOCTYPE[^>]*>', '', raw)

    root = ET.fromstring(raw)

    atoms: Dict[int, dict] = {}
    bonds: List[dict] = []
    has_arrows = False

    def walk(elem):
        nonlocal has_arrows
        tag = elem.tag

        if tag == "arrow":
            has_arrows = True

        elif tag == "n":
            aid = int(elem.get("id", "0"))
            px, py = elem.get("p", "0 0").split()[:2]

            el_num = elem.get("Element")
            symbol = ELEMENT_SYMBOLS.get(int(el_num), "?") if el_num else "C"

            node_type = elem.get("NodeType", "")
            if node_type in ("Fragment", "Nickname", "Unspecified"):
                raise ValueError(
                    f"Superatom / nickname node (id={aid}) found — "
                    "RDKit cannot render abbreviated groups. "
                    "Use cdxml_to_image.py (ChemDraw COM) instead."
                )

            atoms[aid] = {"symbol": symbol, "x": float(px), "y": float(py)}

        elif tag == "b":
            order_str = elem.get("Order", "1")
            bonds.append({
                "b": int(elem.get("B", "0")),
                "e": int(elem.get("E", "0")),
                "order": _BOND_ORDER_MAP.get(order_str, 1),
            })

        for child in elem:
            if tag == "n" and child.tag in ("n", "t"):
                continue
            walk(child)

    walk(root)

    if has_arrows:
        raise ValueError(
            "Reaction scheme detected (arrow elements present). "
            "RDKit cannot render multi-fragment reaction schemes. "
            "Use cdxml_to_image.py (ChemDraw COM) instead."
        )

    return atoms, bonds


# ---------------------------------------------------------------------------
# RDKit renderer
# ---------------------------------------------------------------------------

def _render(atoms: dict, bonds: list, output_path: str,
            width: int, height: int) -> str:
    try:
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D
    except ImportError:
        raise RuntimeError("RDKit is not installed in this environment.")

    rw = Chem.RWMol()
    atom_idx: Dict[int, int] = {}

    bond_type_map = {
        1: Chem.BondType.SINGLE,
        2: Chem.BondType.DOUBLE,
        3: Chem.BondType.TRIPLE,
        4: Chem.BondType.AROMATIC,
    }

    for aid, atom in atoms.items():
        sym = atom["symbol"]
        try:
            rd_atom = Chem.Atom(sym)
        except Exception:
            raise ValueError(f"RDKit does not recognise element '{sym}'.")
        atom_idx[aid] = rw.AddAtom(rd_atom)

    for bond in bonds:
        b = atom_idx.get(bond["b"])
        e = atom_idx.get(bond["e"])
        if b is None or e is None:
            raise ValueError(f"Bond references unknown atom id: {bond}")
        rw.AddBond(b, e, bond_type_map.get(bond["order"], Chem.BondType.SINGLE))

    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        raise ValueError(f"RDKit sanitization failed: {exc}")

    # Attach original 2D coordinates from CDXML
    conf = Chem.Conformer(mol.GetNumAtoms())
    for aid, rd_idx in atom_idx.items():
        conf.SetAtomPosition(rd_idx, (atoms[aid]["x"], atoms[aid]["y"], 0.0))
    mol.AddConformer(conf, assignId=True)

    out = Path(output_path)
    ext = out.suffix.lower()

    if ext == ".svg":
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.drawOptions().addStereoAnnotation = False
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        out.write_text(drawer.GetDrawingText(), encoding="utf-8")
        return str(out)

    # PNG — try Cairo, then MolToImage, then save SVG as fallback
    if hasattr(rdMolDraw2D, "MolDraw2DCairo"):
        drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
        drawer.drawOptions().addStereoAnnotation = False
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        out.write_bytes(drawer.GetDrawingText())
        return str(out)

    # Try cairosvg via intermediate SVG
    svg_drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    svg_drawer.drawOptions().addStereoAnnotation = False
    svg_drawer.DrawMolecule(mol)
    svg_drawer.FinishDrawing()
    svg_text = svg_drawer.GetDrawingText()

    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_text.encode(), write_to=str(out))
        return str(out)
    except ImportError:
        pass

    # Final fallback: write SVG and warn
    svg_out = out.with_suffix(".svg")
    svg_out.write_text(svg_text, encoding="utf-8")
    print(
        f"[warning] No PNG renderer available (RDKit Cairo / cairosvg not installed).\n"
        f"          Saved as SVG instead: {svg_out}\n"
        f"          Use cdxml_to_image.py (ChemDraw COM) for proper PNG output.",
        file=sys.stderr,
    )
    return str(svg_out)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def cdxml_to_image_rdkit(
    cdxml_path: str,
    output_path: Optional[str] = None,
    width: int = 600,
    height: int = 400,
) -> str:
    """
    Render a single-molecule CDXML to PNG or SVG using RDKit.

    PREFER cdxml_to_image.py (ChemDraw COM) over this function.
    See module docstring for limitations.
    """
    src = Path(cdxml_path)
    if not src.exists():
        raise FileNotFoundError(f"CDXML file not found: {cdxml_path}")

    if output_path is None:
        output_path = str(src.with_suffix(".png"))

    atoms, bonds = _parse_cdxml(str(src))

    if not atoms:
        raise ValueError("No atoms found in CDXML.")

    return _render(atoms, bonds, output_path, width, height)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "⚠  BACKUP ONLY — render CDXML to PNG/SVG using RDKit.\n"
            "   Use cdxml_to_image.py (ChemDraw COM) whenever possible."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", help="Input CDXML file (single molecule only)")
    p.add_argument(
        "--output", "-o",
        default=None,
        help="Output file (default: <input>.png). Extension sets format.",
    )
    p.add_argument("--width",  type=int, default=600, help="Canvas width px (default 600)")
    p.add_argument("--height", type=int, default=400, help="Canvas height px (default 400)")
    args = p.parse_args(argv)

    print(
        "⚠  cdxml_to_image_rdkit.py: backup renderer — output quality is limited.\n"
        "   Use cdxml_to_image.py (ChemDraw COM) for production use.",
        file=sys.stderr,
    )

    try:
        out = cdxml_to_image_rdkit(
            args.input,
            output_path=args.output,
            width=args.width,
            height=args.height,
        )
        print(out)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
