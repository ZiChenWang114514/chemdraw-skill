#!/usr/bin/env python3
"""
cdxml_to_image_rdkit.py — BACKUP renderer for CDXML → PNG/SVG using RDKit.

⚠️  USE cdxml_to_image.py (ChemDraw COM) INSTEAD WHENEVER POSSIBLE. ⚠️

This script exists only as a fallback for environments where ChemDraw is not
installed (e.g. a remote server, CI, or a colleague's machine).

Known limitations vs ChemDraw COM
----------------------------------
- Single molecules only — reaction schemes with arrows are NOT supported.
- Aromatic systems are re-perceived by RDKit, which may differ from the
  Kekulé form stored in the CDXML.
- Superatom / nickname nodes (R-groups, OTs, Boc, etc.) are not rendered;
  the script will abort with an error if any are present.
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
from typing import Optional


# ---------------------------------------------------------------------------
# CDXML → RDKit molecule (shared toolkit reader)
# ---------------------------------------------------------------------------

_ABBREVIATION_NODETYPES = ("Fragment", "Nickname", "Unspecified", "GenericNickname")


def _read_root(path: str) -> ET.Element:
    with open(path, "rb") as fh:
        raw_bytes = fh.read()

    raw_bytes = re.sub(rb'<objecttag\b[^/]*/>', b'', raw_bytes)
    raw_bytes = re.sub(rb'<objecttag\b.*?</objecttag>', b'', raw_bytes,
                       flags=re.DOTALL)
    raw = raw_bytes.decode("latin-1", errors="replace")
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffe\uffff]', '', raw)
    raw = re.sub(r'<!DOCTYPE[^>]*>', '', raw)
    return ET.fromstring(raw)


def cdxml_to_rdkit_mol(path: str):
    """Read a single-molecule CDXML into one RDKit Mol with its drawn 2D layout.

    Atoms, charges, isotopes and stereo come from the toolkit's CDXML reader
    (:func:`cdxml_toolkit.rdkit_utils.frag_to_mol`); the conformer holds the
    CDXML coordinates with the Y axis flipped (CDXML Y grows downward).

    Raises ValueError for reaction schemes and abbreviated groups.
    """
    from rdkit import Chem
    from ..rdkit_utils import frag_to_mol, set_cdxml_conformer

    root = _read_root(path)
    if root.find(".//arrow") is not None:
        raise ValueError(
            "Reaction scheme detected (arrow elements present). "
            "RDKit cannot render multi-fragment reaction schemes. "
            "Use cdxml_to_image.py (ChemDraw COM) instead."
        )
    nested = {id(f) for n in root.iter("n") for f in n.iter("fragment")}
    mol = None
    for frag in root.iter("fragment"):
        if id(frag) in nested:
            continue
        for node in frag.findall("n"):
            if node.get("NodeType", "") in _ABBREVIATION_NODETYPES:
                raise ValueError(
                    f"Superatom / nickname node (id={node.get('id')}) found — "
                    "RDKit cannot render abbreviated groups. "
                    "Use cdxml_to_image.py (ChemDraw COM) instead."
                )
        part, atoms = frag_to_mol(frag)
        if part is None:
            raise ValueError(f"RDKit could not read fragment {frag.get('id', '?')}.")
        set_cdxml_conformer(part, atoms, scale=1.0)
        mol = part if mol is None else Chem.CombineMols(mol, part)
    if mol is None or mol.GetNumAtoms() == 0:
        raise ValueError("No atoms found in CDXML.")
    return mol


# ---------------------------------------------------------------------------
# RDKit renderer
# ---------------------------------------------------------------------------

def _render(mol, output_path: str, width: int, height: int) -> str:
    try:
        from rdkit.Chem.Draw import rdMolDraw2D
    except ImportError:
        raise RuntimeError("RDKit is not installed in this environment.")

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

    return _render(cdxml_to_rdkit_mol(str(src)), output_path, width, height)


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
