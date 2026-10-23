"""Read ChemDraw style sheets (.cds) and apply them to CDXML.

A ChemDraw style sheet is a CDX file whose document object carries the
drawing settings (bond length, line widths, label and caption fonts).
ChemDraw for Windows applies one with ``Settings.ApplySettings``; ChemDraw for
macOS has no scriptable equivalent and opens a .cds as an untitled stationery
document.  This module reads the settings from the CDX binary directly and
writes them onto the root ``<CDXML>`` element, so the same Clean Up commands
then work to the style sheet's settings on both platforms.
"""

from __future__ import annotations

from pathlib import Path
import struct
import xml.etree.ElementTree as ET

_CDX_SIGNATURE = b"VjCD0100"
_CDX_HEADER_SIZE = 22
_OBJECT_FLAG = 0x8000
_DOCUMENT = 0x8000

_FONT_TABLE = 0x0100
_CHAIN_ANGLE = 0x0803
_BOND_SPACING = 0x0804
# CDXCoordinate settings (1/65536 point), by CDXML attribute.
_COORDINATES = {
    0x0805: "BondLength",
    0x0806: "BoldWidth",
    0x0807: "LineWidth",
    0x0808: "MarginWidth",
    0x0809: "HashSpacing",
}
_LABEL_STYLE = 0x080A
_CAPTION_STYLE = 0x080B

# Windows code pages in CDX font tables, as CDXML charset names.
_CHARSETS = {
    0: "x-mac-roman",
    932: "shift_jis",
    936: "gb2312",
    949: "ks_c_5601-1987",
    950: "big5",
    1250: "windows-1250",
    1251: "windows-1251",
    1252: "iso-8859-1",
    1253: "windows-1253",
    1254: "windows-1254",
    65001: "utf-8",
}

_STYLE_ORDER = (
    "BondLength", "ChainAngle", "BoldWidth", "LineWidth", "MarginWidth",
    "HashSpacing", "BondSpacing", "LabelFont", "LabelSize", "LabelFace",
    "CaptionFont", "CaptionSize", "CaptionFace",
)


class StyleSheetError(ValueError):
    """The file is not a ChemDraw style sheet this module can read."""


def _number(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _document_properties(data: bytes) -> dict[int, bytes]:
    """Properties of the CDX document object (nested objects are skipped)."""
    if not data.startswith(_CDX_SIGNATURE) or len(data) < _CDX_HEADER_SIZE + 6:
        raise StyleSheetError("not a CDX file")
    offset = _CDX_HEADER_SIZE
    tag, = struct.unpack_from("<H", data, offset)
    if tag != _DOCUMENT:
        raise StyleSheetError("CDX file has no document object")
    offset += 6  # tag and object id
    properties: dict[int, bytes] = {}
    depth = 0
    while offset + 2 <= len(data):
        tag, = struct.unpack_from("<H", data, offset)
        offset += 2
        if tag == 0:
            if depth == 0:
                return properties
            depth -= 1
            continue
        if tag & _OBJECT_FLAG:
            offset += 4
            depth += 1
            continue
        if offset + 2 > len(data):
            break
        length, = struct.unpack_from("<H", data, offset)
        offset += 2
        if length == 0xFFFF:
            length, = struct.unpack_from("<I", data, offset)
            offset += 4
        value = data[offset:offset + length]
        if len(value) != length:
            raise StyleSheetError("CDX file is truncated")
        offset += length
        if depth == 0:
            properties[tag] = value
    return properties


def _font_table(value: bytes) -> dict[int, tuple[str, str]]:
    fonts: dict[int, tuple[str, str]] = {}
    if len(value) < 4:
        return fonts
    count, = struct.unpack_from("<H", value, 2)
    offset = 4
    for _ in range(count):
        if offset + 6 > len(value):
            break
        font_id, charset, name_length = struct.unpack_from("<HHH", value, offset)
        offset += 6
        name = value[offset:offset + name_length].decode("latin-1")
        offset += name_length
        fonts[font_id] = (name, _CHARSETS.get(charset, "iso-8859-1"))
    return fonts


def read_style_sheet(path: str | Path) -> dict:
    """Drawing settings of a ChemDraw style sheet (.cds) or CDX document.

    Returns ``{"attributes": {...}, "fonts": {"label": (name, charset), ...}}``
    where the attributes use CDXML names and units (points, degrees, percent
    of bond length) and the label and caption fonts are given by name.
    """
    data = Path(path).expanduser().read_bytes()
    properties = _document_properties(data)
    fonts = _font_table(properties.get(_FONT_TABLE, b""))
    attributes: dict[str, str] = {}
    for tag, name in _COORDINATES.items():
        if len(properties.get(tag, b"")) == 4:
            attributes[name] = _number(struct.unpack("<i", properties[tag])[0] / 65536)
    if len(properties.get(_CHAIN_ANGLE, b"")) == 4:
        attributes["ChainAngle"] = _number(struct.unpack("<i", properties[_CHAIN_ANGLE])[0] / 65536)
    if len(properties.get(_BOND_SPACING, b"")) == 2:
        attributes["BondSpacing"] = _number(struct.unpack("<h", properties[_BOND_SPACING])[0] / 10)
    style_fonts = {}
    for tag, prefix in ((_LABEL_STYLE, "Label"), (_CAPTION_STYLE, "Caption")):
        value = properties.get(tag, b"")
        if len(value) < 6:
            continue
        font_id, face, size = struct.unpack_from("<HHH", value)
        attributes[f"{prefix}Face"] = str(face)
        attributes[f"{prefix}Size"] = _number(size / 20)
        if font_id in fonts:
            style_fonts[prefix.lower()] = fonts[font_id]
    if "BondLength" not in attributes:
        raise StyleSheetError("style sheet has no bond length setting")
    return {"attributes": attributes, "fonts": style_fonts}


def _font_id(fonttable: ET.Element, name: str, charset: str) -> str:
    for font in fonttable.iter("font"):
        if (font.get("name") or "").casefold() == name.casefold():
            return font.get("id")
    ids = [int(font.get("id")) for font in fonttable.iter("font") if (font.get("id") or "").isdigit()]
    new_id = str(max(ids, default=2) + 1)
    ET.SubElement(fonttable, "font", id=new_id, charset=charset, name=name)
    return new_id


def apply_style_sheet(cdxml_text: str, style: dict, *, rescale: bool = True) -> str:
    """Write the settings from :func:`read_style_sheet` onto a CDXML document.

    With ``rescale``, coordinates are rescaled to the new bond length, as the
    ACS Document 1996 settings are elsewhere in the toolkit.  Without it only
    the settings change, as with ``ApplySettings`` in ChemDraw for Windows, and
    ChemDraw's Clean Up then works to them.
    """
    from .chemscript_bridge import _rescale_cdxml_coords

    attributes = dict(style["attributes"])
    root = ET.fromstring(cdxml_text)
    old_length = float(root.get("BondLength") or 0) or None
    new_length = float(attributes["BondLength"])
    if rescale and old_length and abs(new_length / old_length - 1) > 0.001:
        root = ET.fromstring(_rescale_cdxml_coords(cdxml_text, new_length / old_length))
    fonttable = root.find("fonttable")
    if fonttable is None:
        fonttable = ET.Element("fonttable")
        root.insert(0, fonttable)
    for role, (name, charset) in style.get("fonts", {}).items():
        attributes["LabelFont" if role == "label" else "CaptionFont"] = _font_id(fonttable, name, charset)
    for name in _STYLE_ORDER:
        if name in attributes:
            root.set(name, attributes[name])
    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")
