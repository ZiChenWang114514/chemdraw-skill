"""Wrap a raster picture in a minimal Enhanced Metafile (EMF).

ChemDraw for Windows exports OLE previews as vector EMF. ChemDraw for macOS
cannot write EMF, so on macOS the 300 dpi PNG export is wrapped in a single
``EMR_STRETCHDIBITS`` record. The result is a valid EMF that Word and
PowerPoint (Windows and macOS) display at the picture's physical size, and it
keeps every ``olePreview*.emf`` part name and ``image/x-emf`` content type
unchanged.
"""

from __future__ import annotations

from pathlib import Path
import struct

_EMR_HEADER = 1
_EMR_EOF = 14
_EMR_STRETCHDIBITS = 81
_ENHMETA_SIGNATURE = 0x464D4520
_HEADER_SIZE = 108
_STRETCHDIBITS_FIXED = 80
_BITMAPINFOHEADER_SIZE = 40
_EOF_SIZE = 20
_SRCCOPY = 0x00CC0020
_DIB_RGB_COLORS = 0
_DEFAULT_DPI = 300


def _flattened_rgb(path: Path):
    from PIL import Image

    with Image.open(path) as image:
        image.load()
        dpi = image.info.get("dpi", (_DEFAULT_DPI, _DEFAULT_DPI))
        rgba = image.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, "white")
    flattened.paste(rgba, mask=rgba.getchannel("A"))
    resolution = float(dpi[0]) if dpi and float(dpi[0]) > 0 else _DEFAULT_DPI
    return flattened, resolution


def _dib_rows(image) -> bytes:
    width, height = image.size
    stride = (width * 3 + 3) & ~3
    padding = b"\0" * (stride - width * 3)
    raw = image.tobytes("raw", "BGR")
    row_bytes = width * 3
    rows = [raw[y * row_bytes:(y + 1) * row_bytes] + padding for y in range(height - 1, -1, -1)]
    return b"".join(rows)


def png_to_emf(path: str | Path) -> bytes:
    """Return EMF bytes that draw the PNG at ``path`` on a white background."""
    image, dpi = _flattened_rgb(Path(path))
    width, height = image.size
    bits = _dib_rows(image)

    bitmap_info = struct.pack(
        "<IiiHHIIiiII",
        _BITMAPINFOHEADER_SIZE, width, height, 1, 24, 0, len(bits),
        round(dpi / 0.0254), round(dpi / 0.0254), 0, 0,
    )
    record_size = _STRETCHDIBITS_FIXED + len(bitmap_info) + len(bits)
    bounds = (0, 0, width - 1, height - 1)
    stretch = struct.pack(
        "<II4i6i4iIIii",
        _EMR_STRETCHDIBITS, record_size, *bounds,
        0, 0, 0, 0, width, height,
        _STRETCHDIBITS_FIXED, len(bitmap_info),
        _STRETCHDIBITS_FIXED + len(bitmap_info), len(bits),
        _DIB_RGB_COLORS, _SRCCOPY, width, height,
    ) + bitmap_info + bits

    eof = struct.pack("<IIIII", _EMR_EOF, _EOF_SIZE, 0, 16, _EOF_SIZE)

    # Reference device: one device pixel per picture pixel at the picture's dpi.
    hundredths = lambda pixels: round(pixels * 2540 / dpi)  # noqa: E731
    micrometers = lambda pixels: round(pixels * 25400 / dpi)  # noqa: E731
    total = _HEADER_SIZE + len(stretch) + len(eof)
    header = struct.pack(
        "<II4i4iIIIIHHIIIiiiiIIIii",
        _EMR_HEADER, _HEADER_SIZE, *bounds,
        0, 0, hundredths(width) - 1, hundredths(height) - 1,
        _ENHMETA_SIGNATURE, 0x00010000, total, 3, 1, 0, 0, 0, 0,
        width, height,
        max(1, round(micrometers(width) / 1000)), max(1, round(micrometers(height) / 1000)),
        0, 0, 0,
        micrometers(width), micrometers(height),
    )
    return header + stretch + eof
