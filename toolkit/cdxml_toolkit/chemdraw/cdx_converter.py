#!/usr/bin/env python3
"""
CDX ↔ CDXML Converter
Converts between ChemDraw CDX (binary) and CDXML (XML) formats.

Backends (tried in order):
  1. ChemDraw COM automation (most reliable, requires ChemDraw installed)
  2. pycdxml library (good open-source fallback)
  3. Open Babel CLI (last resort, patchy for complex structures)

Usage:
    python cdx_converter.py input.cdx [-o output.cdxml] [--method com|pycdxml|obabel]
    python cdx_converter.py input.cdxml [-o output.cdx] [--method com|pycdxml|obabel]

Python API:
    from cdxml_toolkit.chemdraw.cdx_converter import convert_cdx_to_cdxml, convert_file
    cdxml_str = convert_cdx_to_cdxml(cdx_bytes)
    convert_file("input.cdx", "output.cdxml")
"""

import argparse
import json
import os
import sys
import subprocess
import tempfile
from typing import Optional

# ---------------------------------------------------------------------------
# Backend availability detection
# ---------------------------------------------------------------------------

HAS_COM = False
HAS_PYCDXML = False
HAS_OBABEL = False

try:
    import win32com.client
    HAS_COM = True
except ImportError:
    pass

try:
    from pycdxml import cdxml_converter as _pycdxml
    HAS_PYCDXML = True
except ImportError:
    pass

try:
    result = subprocess.run(
        ["obabel", "-V"], capture_output=True, timeout=5
    )
    if result.returncode == 0:
        HAS_OBABEL = True
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass

BACKEND_ORDER = ["com", "pycdxml", "obabel"]

# ---------------------------------------------------------------------------
# CDXML sanitiser
# ---------------------------------------------------------------------------

import re as _re


def sanitise_cdxml(cdxml: str) -> str:
    """Remove content that makes ChemDraw's strict XML parser reject the file.

    Findmolecule embeds internal GUIDs as raw binary bytes inside
    <objecttag Name="Molecule ID" Value="..."/> attributes.  These bytes
    include XML-illegal control characters (< 0x09, 0x0B-0x0C, 0x0E-0x1F)
    that cause ChemDraw to report "not well-formed (invalid token)".

    The Molecule ID tags carry no chemistry information — they are ELN
    bookkeeping handles that ChemDraw doesn't need to render the structure.
    We strip the entire element.  Any remaining stray control characters are
    also removed so the file is clean XML 1.0.
    """
    # 1. Strip all <objecttag ... Name="Molecule ID" .../> elements (self-closing).
    #    Attribute order in ChemDraw CDXML can vary, so match both orderings.
    cdxml_bytes = cdxml.encode("utf-8", errors="replace")
    cdxml_bytes = _re.sub(
        rb'<objecttag\s[^>]*Name="Molecule ID"[^>]*/\s*>',
        b"",
        cdxml_bytes,
    )

    # 2. Strip XML 1.0 illegal control characters anywhere in the file.
    #    Legal: 0x09 (tab), 0x0A (LF), 0x0D (CR), 0x20+ (printable + high bytes)
    out = bytearray()
    for byte in cdxml_bytes:
        if byte == 0x09 or byte == 0x0A or byte == 0x0D or byte >= 0x20:
            out.append(byte)

    return out.decode("utf-8", errors="replace")


def sanitise_cdxml_file(path: str) -> None:
    """Sanitise a CDXML file in-place."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    cleaned = sanitise_cdxml(content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cleaned)


# ---------------------------------------------------------------------------
# COM backend
# ---------------------------------------------------------------------------

def _get_chemdraw():
    """Get a ChemDraw COM instance, reusing an existing session if available.

    Returns (app, launched) where launched is True if we started a new instance.
    Always sets Visible=False to suppress flashing.
    """
    try:
        app = win32com.client.GetActiveObject("ChemDraw.Application")
        launched = False
    except Exception:
        app = win32com.client.Dispatch("ChemDraw.Application")
        launched = True
    return app, launched


def _com_convert_file(input_path: str, output_path: str) -> None:
    """Convert using ChemDraw COM automation."""
    app, launched = _get_chemdraw()
    was_visible = app.Visible
    app.Visible = False
    try:
        doc = app.Documents.Open(os.path.abspath(input_path))
        doc.SaveAs(os.path.abspath(output_path))
        doc.Close()
    finally:
        if launched:
            app.Quit()
        else:
            app.Visible = was_visible
    if output_path.lower().endswith(".cdxml"):
        sanitise_cdxml_file(output_path)


def _com_cdx_to_cdxml(cdx_data: bytes) -> str:
    """Convert CDX bytes → CDXML string via COM (uses temp files)."""
    with tempfile.NamedTemporaryFile(suffix=".cdx", delete=False) as tmp_in:
        tmp_in.write(cdx_data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path.replace(".cdx", ".cdxml")
    try:
        _com_convert_file(tmp_in_path, tmp_out_path)
        with open(tmp_out_path, "r", encoding="utf-8") as f:
            return f.read()  # sanitise_cdxml_file already ran inside _com_convert_file
    finally:
        for p in (tmp_in_path, tmp_out_path):
            if os.path.exists(p):
                os.unlink(p)


def _com_cdxml_to_cdx(cdxml_data: str) -> bytes:
    """Convert CDXML string → CDX bytes via COM (uses temp files)."""
    with tempfile.NamedTemporaryFile(
        suffix=".cdxml", delete=False, mode="w", encoding="utf-8"
    ) as tmp_in:
        tmp_in.write(cdxml_data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path.replace(".cdxml", ".cdx")
    try:
        _com_convert_file(tmp_in_path, tmp_out_path)
        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        for p in (tmp_in_path, tmp_out_path):
            if os.path.exists(p):
                os.unlink(p)

# ---------------------------------------------------------------------------
# pycdxml backend
# ---------------------------------------------------------------------------

def _pycdxml_convert_file(input_path: str, output_path: str) -> None:
    """Convert using pycdxml library."""
    in_ext = os.path.splitext(input_path)[1].lower()
    if in_ext == ".cdx":
        doc = _pycdxml.read_cdx(input_path)
        cdxml_str = doc.to_cdxml()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cdxml_str)
    elif in_ext == ".cdxml":
        doc = _pycdxml.read_cdxml(input_path)
        _pycdxml.write_cdx_file(doc, output_path)
    else:
        raise ValueError(f"Unsupported input extension: {in_ext}")


def _pycdxml_cdx_to_cdxml(cdx_data: bytes) -> str:
    """Convert CDX bytes → CDXML string via pycdxml (uses temp files)."""
    with tempfile.NamedTemporaryFile(suffix=".cdx", delete=False) as tmp_in:
        tmp_in.write(cdx_data)
        tmp_in_path = tmp_in.name
    try:
        doc = _pycdxml.read_cdx(tmp_in_path)
        return doc.to_cdxml()
    finally:
        if os.path.exists(tmp_in_path):
            os.unlink(tmp_in_path)


def _pycdxml_cdxml_to_cdx(cdxml_data: str) -> bytes:
    """Convert CDXML string → CDX bytes via pycdxml (uses temp files)."""
    with tempfile.NamedTemporaryFile(
        suffix=".cdxml", delete=False, mode="w", encoding="utf-8"
    ) as tmp_in:
        tmp_in.write(cdxml_data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path.replace(".cdxml", ".cdx")
    try:
        doc = _pycdxml.read_cdxml(tmp_in_path)
        _pycdxml.write_cdx_file(doc, tmp_out_path)
        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        for p in (tmp_in_path, tmp_out_path):
            if os.path.exists(p):
                os.unlink(p)

# ---------------------------------------------------------------------------
# Open Babel backend
# ---------------------------------------------------------------------------

def _obabel_convert_file(input_path: str, output_path: str) -> None:
    """Convert using Open Babel CLI."""
    result = subprocess.run(
        ["obabel", os.path.abspath(input_path), "-O", os.path.abspath(output_path)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"obabel failed: {result.stderr}")


def _obabel_cdx_to_cdxml(cdx_data: bytes) -> str:
    """Convert CDX bytes → CDXML string via obabel (uses temp files)."""
    with tempfile.NamedTemporaryFile(suffix=".cdx", delete=False) as tmp_in:
        tmp_in.write(cdx_data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path.replace(".cdx", ".cdxml")
    try:
        _obabel_convert_file(tmp_in_path, tmp_out_path)
        with open(tmp_out_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        for p in (tmp_in_path, tmp_out_path):
            if os.path.exists(p):
                os.unlink(p)


def _obabel_cdxml_to_cdx(cdxml_data: str) -> bytes:
    """Convert CDXML string → CDX bytes via obabel (uses temp files)."""
    with tempfile.NamedTemporaryFile(
        suffix=".cdxml", delete=False, mode="w", encoding="utf-8"
    ) as tmp_in:
        tmp_in.write(cdxml_data)
        tmp_in_path = tmp_in.name
    tmp_out_path = tmp_in_path.replace(".cdxml", ".cdx")
    try:
        _obabel_convert_file(tmp_in_path, tmp_out_path)
        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        for p in (tmp_in_path, tmp_out_path):
            if os.path.exists(p):
                os.unlink(p)

# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------

_FILE_CONVERTERS = {
    "com": _com_convert_file if HAS_COM else None,
    "pycdxml": _pycdxml_convert_file if HAS_PYCDXML else None,
    "obabel": _obabel_convert_file if HAS_OBABEL else None,
}

_CDX_TO_CDXML = {
    "com": _com_cdx_to_cdxml if HAS_COM else None,
    "pycdxml": _pycdxml_cdx_to_cdxml if HAS_PYCDXML else None,
    "obabel": _obabel_cdx_to_cdxml if HAS_OBABEL else None,
}

_CDXML_TO_CDX = {
    "com": _com_cdxml_to_cdx if HAS_COM else None,
    "pycdxml": _pycdxml_cdxml_to_cdx if HAS_PYCDXML else None,
    "obabel": _obabel_cdxml_to_cdx if HAS_OBABEL else None,
}


def _pick_backend(method: str, dispatch_table: dict):
    """Select a backend function. 'auto' tries in priority order."""
    if method == "auto":
        for name in BACKEND_ORDER:
            fn = dispatch_table.get(name)
            if fn is not None:
                return name, fn
        raise RuntimeError(
            "No conversion backend available. "
            "Install ChemDraw (COM), pycdxml, or Open Babel."
        )
    fn = dispatch_table.get(method)
    if fn is None:
        available = {k: v for k, v in dispatch_table.items() if v}
        raise RuntimeError(
            f"Backend '{method}' not available. "
            f"Available: {list(available.keys()) or 'none'}"
        )
    return method, fn

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_cdx_to_cdxml(cdx_data: bytes, method: str = "auto") -> str:
    """Convert raw CDX bytes to CDXML string."""
    name, fn = _pick_backend(method, _CDX_TO_CDXML)
    return fn(cdx_data)


def convert_cdxml_to_cdx(cdxml_data: str, method: str = "auto") -> bytes:
    """Convert CDXML string to raw CDX bytes."""
    name, fn = _pick_backend(method, _CDXML_TO_CDX)
    return fn(cdxml_data)


def batch_convert_files(
    input_paths: list, method: str = "auto"
) -> dict:
    """Convert multiple CDX/CDXML files in a single COM session.

    Returns dict mapping input_path -> {"output": path, "error": None} on
    success, or {"output": None, "error": message} on failure.

    For COM backend: one GetActiveObject/Dispatch, loop through all files,
    one conditional Quit.  For non-COM backends: falls back to per-file
    convert_file().
    """
    results = {}
    if not input_paths:
        return results

    name, _ = _pick_backend(method, _FILE_CONVERTERS)

    if name == "com":
        app, launched = _get_chemdraw()
        was_visible = app.Visible
        app.Visible = False
        try:
            for inp in input_paths:
                in_ext = os.path.splitext(inp)[1].lower()
                if in_ext == ".cdx":
                    out_ext = ".cdxml"
                elif in_ext == ".cdxml":
                    out_ext = ".cdx"
                else:
                    results[inp] = {
                        "output": None,
                        "error": f"Unsupported extension: {in_ext}",
                    }
                    continue
                out = os.path.splitext(inp)[0] + out_ext
                try:
                    doc = app.Documents.Open(os.path.abspath(inp))
                    doc.SaveAs(os.path.abspath(out))
                    doc.Close()
                    if out.lower().endswith(".cdxml"):
                        sanitise_cdxml_file(out)
                    results[inp] = {"output": out, "error": None}
                except Exception as e:
                    results[inp] = {"output": None, "error": str(e)}
        finally:
            if launched:
                app.Quit()
            else:
                app.Visible = was_visible
    else:
        # Non-COM: fall back to per-file conversion
        for inp in input_paths:
            try:
                out = convert_file(inp, method=method)
                results[inp] = {"output": out, "error": None}
            except Exception as e:
                results[inp] = {"output": None, "error": str(e)}

    return results


def convert_file(
    input_path: str, output_path: Optional[str] = None, method: str = "auto"
) -> str:
    """Convert a file between CDX and CDXML. Returns output path."""
    in_ext = os.path.splitext(input_path)[1].lower()
    if in_ext == ".cdx":
        out_ext = ".cdxml"
    elif in_ext == ".cdxml":
        out_ext = ".cdx"
    else:
        raise ValueError(f"Unsupported file extension: {in_ext}. Use .cdx or .cdxml.")

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + out_ext

    name, fn = _pick_backend(method, _FILE_CONVERTERS)
    fn(input_path, output_path)
    return output_path

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert between ChemDraw CDX (binary) and CDXML (XML) formats."
    )
    parser.add_argument(
        "input", nargs="?", help="Input file (.cdx or .cdxml)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: same name with swapped extension)"
    )
    parser.add_argument(
        "--method",
        choices=["auto", "com", "pycdxml", "obabel"],
        default="auto",
        help="Conversion backend (default: auto — tries com, pycdxml, obabel)"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        metavar="FILE",
        help="Batch-convert multiple files in one COM session"
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Show available backends and exit"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON to stdout"
    )
    args = parser.parse_args(argv)

    if args.list_backends:
        print("Available backends:")
        for name in BACKEND_ORDER:
            status = "available" if _FILE_CONVERTERS.get(name) else "not available"
            print(f"  {name}: {status}")
        return 0

    # --batch mode: convert multiple files in one COM session
    if args.batch:
        missing = [f for f in args.batch if not os.path.isfile(f)]
        if missing:
            for f in missing:
                print(f"Error: file not found: {f}", file=sys.stderr)
            return 1
        try:
            results = batch_convert_files(args.batch, args.method)
            backend_name, _ = _pick_backend(args.method, _FILE_CONVERTERS)
            if args.json:
                json_results = []
                for inp, info in results.items():
                    entry = {"input": os.path.abspath(inp), "method": backend_name}
                    if info["error"]:
                        entry["error"] = info["error"]
                    else:
                        entry["output"] = os.path.abspath(info["output"])
                    json_results.append(entry)
                print(json.dumps(json_results, indent=2))
            else:
                ok = sum(1 for v in results.values() if v["error"] is None)
                fail = len(results) - ok
                for inp, info in results.items():
                    if info["error"]:
                        print(f"  FAIL: {inp} — {info['error']}")
                    else:
                        size = os.path.getsize(info["output"])
                        print(f"  OK: {inp} -> {info['output']} ({size:,} bytes)")
                print(f"Batch: {ok} converted, {fail} failed [backend: {backend_name}]")
            return 1 if any(v["error"] for v in results.values()) else 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if not args.input:
        parser.error("the following arguments are required: input (or --batch)")

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        out = convert_file(args.input, args.output, args.method)
        backend_name, _ = _pick_backend(args.method, _FILE_CONVERTERS)
        if args.json:
            in_ext = os.path.splitext(args.input)[1].lower().lstrip(".")
            out_ext = os.path.splitext(out)[1].lower().lstrip(".")
            result = {
                "input": os.path.abspath(args.input),
                "output": os.path.abspath(out),
                "input_format": in_ext,
                "output_format": out_ext,
                "method": backend_name,
            }
            print(json.dumps(result, indent=2))
        else:
            size = os.path.getsize(out)
            print(f"Converted: {args.input} -> {out} ({size:,} bytes) [backend: {backend_name}]")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
