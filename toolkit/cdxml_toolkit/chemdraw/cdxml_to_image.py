#!/usr/bin/env python3
"""
cdxml_to_image.py — Render a CDXML file to PNG or SVG via ChemDraw COM.

Requires ChemDraw to be installed (ChemDraw Professional 16+).
ChemDraw does NOT need to be open — it is launched as a hidden background
process and closed automatically after export.

Usage
-----
  python cdxml_to_image.py input.cdxml                 # PNG alongside input file
  python cdxml_to_image.py input.cdxml -o out.png      # explicit output path
  python cdxml_to_image.py input.cdxml -o out.svg      # SVG output
  python cdxml_to_image.py input.cdxml --dpi 150       # lower resolution PNG
  python cdxml_to_image.py --batch f1.cdxml f2.cdxml   # batch render (one COM session)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# ChemDraw COM helpers
# ---------------------------------------------------------------------------

def _get_chemdraw():
    """Get a ChemDraw COM instance, reusing an existing session if available.

    Returns (app, launched) where launched is True if we started a new instance.
    """
    import win32com.client as win32
    try:
        app = win32.GetActiveObject("ChemDraw.Application")
        launched = False
    except Exception:
        app = win32.Dispatch("ChemDraw.Application")
        launched = True
    return app, launched


# ---------------------------------------------------------------------------
# ChemDraw COM backend
# ---------------------------------------------------------------------------

def cdxml_to_image(
    cdxml_path: str,
    output_path: Optional[str] = None,
    png_dpi: int = 300,
) -> str:
    """
    Render a CDXML file to PNG or SVG using ChemDraw via COM automation.

    ChemDraw infers the output format from the file extension (.png, .svg,
    .emf, .cdxml, …).  TransparentPNGs is forced off so the background is
    solid white rather than a transparent checkerboard.

    Parameters
    ----------
    cdxml_path  : path to the source .cdxml file
    output_path : destination file; if None, derived from cdxml_path as .png
    png_dpi     : resolution for PNG export (default 300 dpi)

    Returns
    -------
    Absolute path to the written output file.
    """
    src = Path(cdxml_path)
    if not src.exists():
        raise FileNotFoundError(f"CDXML file not found: {cdxml_path}")

    if output_path is None:
        output_path = str(src.with_suffix(".png"))

    cdxml_abs = str(src.resolve())
    out_abs   = str(Path(output_path).resolve())

    app, launched = _get_chemdraw()
    was_visible = app.Visible
    app.Visible = False
    doc = None
    try:
        prefs = app.Preferences
        prefs.TransparentPNGs = False   # solid white background
        prefs.PNGResolution   = png_dpi

        doc = app.Documents.Open(cdxml_abs)
        doc.SaveAs(out_abs)

        return out_abs

    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        if launched:
            try:
                app.Quit()
            except Exception:
                pass
        else:
            app.Visible = was_visible


def batch_render(
    cdxml_paths: list,
    png_dpi: int = 300,
) -> dict:
    """Render multiple CDXML files to PNG in a single COM session.

    Returns dict mapping input_path -> {"output": path, "error": None} on
    success, or {"output": None, "error": message} on failure.
    """
    results = {}
    if not cdxml_paths:
        return results

    app, launched = _get_chemdraw()
    was_visible = app.Visible
    app.Visible = False
    try:
        prefs = app.Preferences
        prefs.TransparentPNGs = False
        prefs.PNGResolution   = png_dpi

        for cdxml_path in cdxml_paths:
            src = Path(cdxml_path)
            out_path = str(src.with_suffix(".png"))
            cdxml_abs = str(src.resolve())
            out_abs = str(Path(out_path).resolve())
            try:
                doc = app.Documents.Open(cdxml_abs)
                doc.SaveAs(out_abs)
                doc.Close(False)
                results[cdxml_path] = {"output": out_abs, "error": None}
            except Exception as e:
                results[cdxml_path] = {"output": None, "error": str(e)}
    finally:
        if launched:
            try:
                app.Quit()
            except Exception:
                pass
        else:
            app.Visible = was_visible

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Render a CDXML file to PNG or SVG using ChemDraw.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "input", nargs="?",
        help="Input CDXML file",
    )
    p.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: <input>.png). "
             "Extension determines format: .png or .svg",
    )
    p.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="PNG resolution in DPI (default: 300)",
    )
    p.add_argument(
        "--batch",
        nargs="+",
        metavar="FILE",
        help="Batch-render multiple CDXML files in one COM session",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON to stdout",
    )
    return p


def main(argv: Optional[list] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # --batch mode
    if args.batch:
        missing = [f for f in args.batch if not Path(f).exists()]
        if missing:
            for f in missing:
                print(f"Error: file not found: {f}", file=sys.stderr)
            return 1
        results = batch_render(args.batch, png_dpi=args.dpi)
        if args.json:
            json_results = []
            for inp, info in results.items():
                entry = {"input": str(Path(inp).resolve())}
                if info["error"]:
                    entry["error"] = info["error"]
                else:
                    entry["output"] = info["output"]
                json_results.append(entry)
            print(json.dumps(json_results, indent=2))
        else:
            ok = sum(1 for v in results.values() if v["error"] is None)
            fail = len(results) - ok
            for inp, info in results.items():
                if info["error"]:
                    print(f"  FAIL: {inp} — {info['error']}")
                else:
                    print(f"  OK: {inp} -> {info['output']}")
            print(f"Batch: {ok} rendered, {fail} failed")
        return 1 if any(v["error"] for v in results.values()) else 0

    if not args.input:
        parser.error("the following arguments are required: input (or --batch)")

    try:
        out = cdxml_to_image(
            args.input,
            output_path=args.output,
            png_dpi=args.dpi,
        )
        if args.json:
            out_path = Path(out)
            fmt = out_path.suffix.lstrip(".").lower()
            try:
                from PIL import Image
                with Image.open(out) as img:
                    width, height = img.size
            except Exception:
                width, height = None, None
            result = {
                "input": str(Path(args.input).resolve()),
                "output": out,
                "format": fmt,
                "width": width,
                "height": height,
            }
            print(json.dumps(result, indent=2))
        else:
            print(out)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
