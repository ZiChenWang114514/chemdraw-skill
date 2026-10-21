#!/usr/bin/env python3
"""
OLE Extractor — Extract embedded ChemDraw objects from Office files.

Supports four Office formats:
  - PPTX / DOCX / XLSX  — ZIP archives containing OLE blobs in known paths.
  - XLS                  — OLE2 compound documents with MBD* sub-storages.

ChemDraw objects are stored as CDX data inside the OLE "CONTENTS" stream.
This tool extracts and optionally converts them to CDXML.

Usage:
    python ole_extractor.py input.pptx [-o output_dir/] [--format cdxml|cdx|both]
    python ole_extractor.py input.docx [-o output_dir/] [--format cdxml|cdx|both]
    python ole_extractor.py input.xlsx [-o output_dir/] [--format cdxml|cdx|both]
    python ole_extractor.py input.xls  [-o output_dir/] [--format cdxml|cdx|both]

Requires: olefile, cdx_converter (for CDXML conversion)
"""

import argparse
import io
import os
import sys
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional

import olefile

# ChemDraw OLE CLSID (CS ChemDraw Drawing / CS ChemDraw 3D)
CHEMDRAW_CLSIDS = {
    "41BA6D21-A02E-11CE-8FD9-0020AFD1F20C",  # ChemDraw Drawing
}

# CDX binary magic bytes
CDX_MAGIC = b"VjCD"

# Where Office stores OLE embeddings (ZIP-based formats)
EMBEDDING_PATTERNS = {
    ".pptx": "ppt/embeddings/",
    ".docx": "word/embeddings/",
    ".xlsx": "xl/embeddings/",
}

# OLE2-native formats (not ZIP-based) — handled separately
OLE2_FORMATS = {".xls"}


@dataclass
class ExtractedObject:
    """A single extracted ChemDraw object."""
    source_path: str  # path inside ZIP (e.g. ppt/embeddings/oleObject1.bin)
    cdx_data: bytes
    cdx_output: Optional[str] = None  # path where CDX was saved
    cdxml_output: Optional[str] = None  # path where CDXML was saved
    error: Optional[str] = None


def find_ole_entries(zip_path: str) -> List[str]:
    """List OLE embedding paths inside a PPTX/DOCX/XLSX ZIP."""
    ext = os.path.splitext(zip_path)[1].lower()
    prefix = EMBEDDING_PATTERNS.get(ext)
    if prefix is None:
        raise ValueError(
            f"Unsupported ZIP-based file type: {ext}. "
            f"Use .pptx, .docx, or .xlsx."
        )

    with zipfile.ZipFile(zip_path, "r") as zf:
        return [
            name for name in zf.namelist()
            if name.startswith(prefix) and name.lower().endswith(".bin")
        ]


def is_chemdraw_ole(ole: olefile.OleFileIO) -> bool:
    """Check if an OLE container holds a ChemDraw object."""
    # Check CLSID
    clsid = ole.root.clsid.upper() if ole.root.clsid else ""
    if clsid in CHEMDRAW_CLSIDS:
        return True

    # Check for CONTENTS stream with CDX magic
    if ole.exists("CONTENTS"):
        header = ole.openstream("CONTENTS").read(4)
        if header == CDX_MAGIC:
            return True

    return False


def extract_cdx_from_ole(ole_data: bytes) -> Optional[bytes]:
    """Extract raw CDX bytes from an OLE compound document."""
    if not olefile.isOleFile(io.BytesIO(ole_data)):
        return None

    ole = olefile.OleFileIO(io.BytesIO(ole_data))
    try:
        if not is_chemdraw_ole(ole):
            return None

        if ole.exists("CONTENTS"):
            cdx = ole.openstream("CONTENTS").read()
            if cdx[:4] == CDX_MAGIC:
                return cdx

        # Fallback: check \x01Ole10Native stream
        if ole.exists("\x01Ole10Native"):
            data = ole.openstream("\x01Ole10Native").read()
            # Skip 4-byte length prefix
            if len(data) > 4 and data[4:8] == CDX_MAGIC:
                return data[4:]

        return None
    finally:
        ole.close()


def _get_converter(output_format: str):
    """Lazy-import cdx_converter if CDXML output is requested."""
    if output_format not in ("cdxml", "both"):
        return None
    try:
        from ..chemdraw import cdx_converter
        return cdx_converter
    except ImportError:
        print(
            "Warning: cdx_converter not found. CDX files will be saved "
            "but CDXML conversion is unavailable.",
            file=sys.stderr,
        )
        return None


def _save_extracted_object(
    cdx_data: bytes,
    source_path: str,
    entry_name: str,
    output_dir: str,
    output_format: str,
    convert_method: str,
    _converter,
) -> ExtractedObject:
    """Save a single extracted CDX blob to disk (CDX and/or CDXML)."""
    obj = ExtractedObject(source_path=source_path, cdx_data=cdx_data)

    # Save CDX
    if output_format in ("cdx", "both"):
        cdx_path = os.path.join(output_dir, f"{entry_name}.cdx")
        with open(cdx_path, "wb") as f:
            f.write(cdx_data)
        obj.cdx_output = cdx_path

    # Convert to CDXML
    if output_format in ("cdxml", "both"):
        cdxml_path = os.path.join(output_dir, f"{entry_name}.cdxml")
        if _converter is not None:
            try:
                cdxml_str = _converter.convert_cdx_to_cdxml(
                    cdx_data, method=convert_method
                )
                with open(cdxml_path, "w", encoding="utf-8") as f:
                    f.write(cdxml_str)
                obj.cdxml_output = cdxml_path
            except Exception as e:
                obj.error = f"CDXML conversion failed: {e}"
                # Still save CDX as fallback
                if obj.cdx_output is None:
                    fallback = os.path.join(output_dir, f"{entry_name}.cdx")
                    with open(fallback, "wb") as f:
                        f.write(cdx_data)
                    obj.cdx_output = fallback
        else:
            # No converter — save CDX instead
            if obj.cdx_output is None:
                fallback = os.path.join(output_dir, f"{entry_name}.cdx")
                with open(fallback, "wb") as f:
                    f.write(cdx_data)
                obj.cdx_output = fallback
            obj.error = "cdx_converter unavailable; saved CDX only"

    return obj


def _extract_from_zip(
    input_path: str,
    output_dir: str,
    output_format: str,
    convert_method: str,
    _converter,
) -> List[ExtractedObject]:
    """Extract ChemDraw objects from a ZIP-based Office file (PPTX/DOCX/XLSX)."""
    ole_entries = find_ole_entries(input_path)
    results = []

    with zipfile.ZipFile(input_path, "r") as zf:
        for entry in ole_entries:
            ole_data = zf.read(entry)
            cdx_data = extract_cdx_from_ole(ole_data)

            if cdx_data is None:
                # Not a ChemDraw object — skip silently
                continue

            entry_name = os.path.splitext(os.path.basename(entry))[0]
            obj = _save_extracted_object(
                cdx_data, entry, entry_name,
                output_dir, output_format, convert_method, _converter,
            )
            results.append(obj)

    return results


def _extract_from_xls(
    input_path: str,
    output_dir: str,
    output_format: str,
    convert_method: str,
    _converter,
) -> List[ExtractedObject]:
    """Extract ChemDraw objects from an OLE2-native XLS file.

    XLS files are OLE2 compound documents. Embedded objects are stored as
    sub-storages with names starting with 'MBD' (e.g. MBD078DC381).
    ChemDraw objects contain a CONTENTS stream with CDX binary data.
    """
    results = []
    ole = olefile.OleFileIO(input_path)
    try:
        # Find top-level MBD* storages (embedded OLE objects)
        seen_storages = set()
        for entry in ole.listdir(storages=True, streams=False):
            if len(entry) >= 1 and entry[0].startswith("MBD"):
                seen_storages.add(entry[0])

        obj_index = 0
        for storage_name in sorted(seen_storages):
            contents_path = f"{storage_name}/CONTENTS"
            if not ole.exists(contents_path):
                continue

            cdx = ole.openstream(contents_path).read()
            if len(cdx) < 4 or cdx[:4] != CDX_MAGIC:
                continue

            obj_index += 1
            source_path = f"{storage_name}/CONTENTS"
            entry_name = f"oleObject{obj_index}"
            obj = _save_extracted_object(
                cdx, source_path, entry_name,
                output_dir, output_format, convert_method, _converter,
            )
            results.append(obj)
    finally:
        ole.close()

    return results


def extract_from_office(
    input_path: str,
    output_dir: Optional[str] = None,
    output_format: str = "cdxml",
    convert_method: str = "auto",
) -> List[ExtractedObject]:
    """Extract all ChemDraw objects from an Office file.

    Args:
        input_path: Path to .pptx, .docx, .xlsx, or .xls file.
        output_dir: Directory for extracted files. Default: <basename>_chemdraw/
        output_format: "cdx", "cdxml", or "both".
        convert_method: Backend for CDX→CDXML conversion (passed to cdx_converter).

    Returns:
        List of ExtractedObject with extraction results.
    """
    ext = os.path.splitext(input_path)[1].lower()

    if ext not in EMBEDDING_PATTERNS and ext not in OLE2_FORMATS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Use .pptx, .docx, .xlsx, or .xls."
        )

    if output_dir is None:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.join(os.path.dirname(input_path) or ".", f"{basename}_chemdraw")

    os.makedirs(output_dir, exist_ok=True)
    _converter = _get_converter(output_format)

    if ext in OLE2_FORMATS:
        return _extract_from_xls(
            input_path, output_dir, output_format, convert_method, _converter,
        )
    else:
        return _extract_from_zip(
            input_path, output_dir, output_format, convert_method, _converter,
        )


def print_summary(results: List[ExtractedObject], input_path: str) -> None:
    """Print extraction summary to stdout."""
    print(f"{'=' * 60}")
    print(f"OLE Extractor - {os.path.basename(input_path)}")
    print(f"{'=' * 60}")

    if not results:
        print("No ChemDraw objects found.")
        return

    print(f"Found {len(results)} ChemDraw object(s):\n")
    for i, obj in enumerate(results, 1):
        print(f"  [{i}] {obj.source_path}")
        print(f"      CDX size: {len(obj.cdx_data):,} bytes")
        if obj.cdx_output:
            print(f"      CDX:   {obj.cdx_output}")
        if obj.cdxml_output:
            size = os.path.getsize(obj.cdxml_output)
            print(f"      CDXML: {obj.cdxml_output} ({size:,} bytes)")
        if obj.error:
            print(f"      Note:  {obj.error}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract embedded ChemDraw objects from Office files."
    )
    parser.add_argument("input", help="Input file (.pptx, .docx, .xlsx, or .xls)")
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (default: <input_basename>_chemdraw/)"
    )
    parser.add_argument(
        "--format",
        choices=["cdxml", "cdx", "both"],
        default="cdxml",
        help="Output format (default: cdxml)"
    )
    parser.add_argument(
        "--method",
        choices=["auto", "com", "pycdxml", "obabel"],
        default="auto",
        help="CDX→CDXML conversion backend (default: auto)"
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        results = extract_from_office(
            args.input,
            output_dir=args.output_dir,
            output_format=args.format,
            convert_method=args.method,
        )
        print_summary(results, args.input)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
