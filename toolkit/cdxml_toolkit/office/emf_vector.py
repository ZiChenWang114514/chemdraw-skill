"""Convert ChemDraw's SVG export to a vector Enhanced Metafile (EMF).

ChemDraw for Windows exports OLE previews as vector EMF.  ChemDraw for macOS
cannot write EMF, but its SVG export is a flat list of filled and stroked
paths and positioned text runs.  This module replays that SVG as EMF path,
pen, brush and text records, so Office previews stay vector on macOS too.

Only the SVG features ChemDraw writes are supported (paths without arcs,
basic shapes, ``<g>`` groups, opaque colours, unrotated text).  Anything else
raises :class:`UnsupportedSvg`, and callers fall back to the bitmap preview
in :mod:`cdxml_toolkit.office.emf_preview`.
"""

from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
import re
import struct
from typing import Iterable, Optional
import xml.etree.ElementTree as ET

# One logical unit is a twip (1/20 point); the reference device has 1440 dpi.
_UNITS_PER_POINT = 20
_DEVICE_MM = 254
_DEVICE_PIXELS = 14400

_EMR_HEADER = 1
_EMR_POLYBEZIERTO = 5
_EMR_EOF = 14
_EMR_SETBKMODE = 18
_EMR_SETPOLYFILLMODE = 19
_EMR_SETTEXTALIGN = 22
_EMR_SETTEXTCOLOR = 24
_EMR_MOVETOEX = 27
_EMR_SELECTOBJECT = 37
_EMR_CREATEBRUSHINDIRECT = 39
_EMR_DELETEOBJECT = 40
_EMR_LINETO = 54
_EMR_BEGINPATH = 59
_EMR_ENDPATH = 60
_EMR_CLOSEFIGURE = 61
_EMR_FILLPATH = 62
_EMR_STROKEANDFILLPATH = 63
_EMR_STROKEPATH = 64
_EMR_EXTCREATEFONTINDIRECTW = 82
_EMR_EXTTEXTOUTW = 84
_EMR_EXTCREATEPEN = 95

_ENHMETA_SIGNATURE = 0x464D4520
_TRANSPARENT = 1
_ALTERNATE, _WINDING = 1, 2
_TA_BASELINE = 24
_TA_CENTER = 6
_TA_RIGHT = 2
_GM_COMPATIBLE = 1
_PS_GEOMETRIC = 0x00010000
_PS_ENDCAP = {"round": 0x0000, "square": 0x0100, "butt": 0x0200}
_PS_JOIN = {"round": 0x0000, "bevel": 0x1000, "miter": 0x2000}
_FW_NORMAL, _FW_BOLD = 400, 700
_DEFAULT_CHARSET = 1
# Object table slots: 0 is reserved, then one pen, one brush and one font.
_PEN, _BRUSH, _FONT = 1, 2, 3
_HANDLES = 4

_NAMED_COLOURS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "blue": (0, 0, 255), "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}
_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtZzAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_INHERITED = ("fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
              "fill-rule", "font-family", "font-size", "font-weight", "font-style",
              "text-anchor", "opacity", "fill-opacity", "stroke-opacity")


class UnsupportedSvg(ValueError):
    """The SVG uses a feature this converter does not reproduce exactly."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# ---------------------------------------------------------------------------
# SVG parsing
# ---------------------------------------------------------------------------

Matrix = tuple[float, float, float, float, float, float]
_IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _multiply(m: Matrix, n: Matrix) -> Matrix:
    """The transform that applies ``n`` first, then ``m``."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


def _apply(m: Matrix, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _transform(text: Optional[str]) -> Matrix:
    result = _IDENTITY
    for name, arguments in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)", text or ""):
        values = [float(v) for v in _NUMBER.findall(arguments)]
        if name == "matrix" and len(values) == 6:
            step = tuple(values)
        elif name == "translate" and values:
            step = (1.0, 0.0, 0.0, 1.0, values[0], values[1] if len(values) > 1 else 0.0)
        elif name == "scale" and values:
            step = (values[0], 0.0, 0.0, values[1] if len(values) > 1 else values[0], 0.0, 0.0)
        elif name == "rotate" and len(values) == 1:
            angle = math.radians(values[0])
            step = (math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0.0, 0.0)
        else:
            raise UnsupportedSvg(f"transform {name}({arguments})")
        result = _multiply(result, step)
    return result


def _length(value: Optional[str], default: float = 0.0) -> float:
    if value is None:
        return default
    match = _NUMBER.match(value.strip())
    if not match:
        return default
    number = float(match.group(0))
    unit = value.strip()[match.end():].strip()
    if unit in ("", "px", "pt"):
        return number
    if unit == "in":
        return number * 72
    if unit == "mm":
        return number * 72 / 25.4
    if unit == "cm":
        return number * 72 / 2.54
    raise UnsupportedSvg(f"length unit {unit}")


def _colour(value: Optional[str]) -> Optional[tuple[int, int, int]]:
    """RGB for an SVG paint, or None for no paint; partial transparency is unsupported."""
    if value is None:
        return None
    text = value.strip().lower()
    if text in ("none", "transparent", ""):
        return None
    if text in _NAMED_COLOURS:
        return _NAMED_COLOURS[text]
    match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})", text)
    if match:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        if len(digits) == 8:
            alpha = int(digits[6:], 16)
            if alpha == 0:
                return None
            if alpha != 255:
                raise UnsupportedSvg(f"translucent colour {value}")
        return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)
    match = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", text)
    if match:
        return tuple(int(v) for v in match.groups())
    raise UnsupportedSvg(f"colour {value}")


def _style(element: ET.Element, inherited: dict) -> dict:
    style = dict(inherited)
    for name in _INHERITED:
        if element.get(name) is not None:
            style[name] = element.get(name)
    for declaration in (element.get("style") or "").split(";"):
        if ":" in declaration:
            name, value = (part.strip() for part in declaration.split(":", 1))
            if name in _INHERITED:
                style[name] = value
    for name in ("opacity", "fill-opacity", "stroke-opacity"):
        if name in style and abs(float(style[name]) - 1.0) > 1e-6:
            if float(style[name]) == 0.0:
                style["fill" if name != "stroke-opacity" else "stroke"] = "none"
                if name == "opacity":
                    style["stroke"] = "none"
            else:
                raise UnsupportedSvg(f"{name} {style[name]}")
    return style


def _path_figures(d: str) -> list[list[tuple]]:
    """Absolute figures from SVG path data: ("M", p), ("L", p), ("C", p1, p2, p3), ("Z",)."""
    tokens = _PATH_TOKEN.findall(d or "")
    figures: list[list[tuple]] = []
    figure: list[tuple] = []
    index = 0
    command = None
    current = start = (0.0, 0.0)
    last_control: Optional[tuple[float, float]] = None
    last_quadratic: Optional[tuple[float, float]] = None

    def numbers(count: int) -> list[float]:
        nonlocal index
        values = tokens[index:index + count]
        if len(values) != count or any(v.isalpha() for v in values):
            raise UnsupportedSvg("malformed path data")
        index += count
        return [float(v) for v in values]

    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            command = token
            index += 1
            if command in "Aa":
                raise UnsupportedSvg("elliptical arc in path")
        elif command is None:
            raise UnsupportedSvg("path data does not start with a command")
        relative = command.islower()
        kind = command.upper()
        base = current if relative else (0.0, 0.0)
        if kind == "Z":
            if figure:
                figure.append(("Z",))
                figures.append(figure)
                figure = []
            current = start
            last_control = last_quadratic = None
            continue
        if kind == "M":
            x, y = numbers(2)
            current = start = (base[0] + x, base[1] + y)
            if figure:
                figures.append(figure)
            figure = [("M", current)]
            command = "l" if relative else "L"
            last_control = last_quadratic = None
            continue
        if not figure:
            figure = [("M", current)]
            start = current
        if kind in "LHV":
            if kind == "L":
                x, y = numbers(2)
                point = (base[0] + x, base[1] + y)
            elif kind == "H":
                x, = numbers(1)
                point = ((current[0] if relative else 0.0) + x, current[1])
            else:
                y, = numbers(1)
                point = (current[0], (current[1] if relative else 0.0) + y)
            figure.append(("L", point))
            current = point
            last_control = last_quadratic = None
        elif kind in "CS":
            if kind == "C":
                x1, y1, x2, y2, x, y = numbers(6)
                first = (base[0] + x1, base[1] + y1)
            else:
                x2, y2, x, y = numbers(4)
                first = (2 * current[0] - last_control[0], 2 * current[1] - last_control[1]) \
                    if last_control else current
            second = (base[0] + x2, base[1] + y2)
            end = (base[0] + x, base[1] + y)
            figure.append(("C", first, second, end))
            current, last_control, last_quadratic = end, second, None
        elif kind in "QT":
            if kind == "Q":
                qx, qy, x, y = numbers(4)
                control = (base[0] + qx, base[1] + qy)
            else:
                x, y = numbers(2)
                control = (2 * current[0] - last_quadratic[0], 2 * current[1] - last_quadratic[1]) \
                    if last_quadratic else current
            end = (base[0] + x, base[1] + y)
            first = (current[0] + 2 / 3 * (control[0] - current[0]), current[1] + 2 / 3 * (control[1] - current[1]))
            second = (end[0] + 2 / 3 * (control[0] - end[0]), end[1] + 2 / 3 * (control[1] - end[1]))
            figure.append(("C", first, second, end))
            current, last_control, last_quadratic = end, None, control
    if figure:
        figures.append(figure)
    return figures


def _ellipse_figure(cx: float, cy: float, rx: float, ry: float) -> list[tuple]:
    k = 0.5522847498
    return [
        ("M", (cx + rx, cy)),
        ("C", (cx + rx, cy + k * ry), (cx + k * rx, cy + ry), (cx, cy + ry)),
        ("C", (cx - k * rx, cy + ry), (cx - rx, cy + k * ry), (cx - rx, cy)),
        ("C", (cx - rx, cy - k * ry), (cx - k * rx, cy - ry), (cx, cy - ry)),
        ("C", (cx + k * rx, cy - ry), (cx + rx, cy - k * ry), (cx + rx, cy)),
        ("Z",),
    ]


def _points(text: Optional[str]) -> list[tuple[float, float]]:
    values = [float(v) for v in _NUMBER.findall(text or "")]
    return list(zip(values[0::2], values[1::2]))


def _shape_figures(element: ET.Element, tag: str) -> list[list[tuple]]:
    if tag == "path":
        return _path_figures(element.get("d", ""))
    if tag == "rect":
        if _length(element.get("rx")) or _length(element.get("ry")):
            raise UnsupportedSvg("rounded rectangle")
        x, y = _length(element.get("x")), _length(element.get("y"))
        w, h = _length(element.get("width")), _length(element.get("height"))
        return [[("M", (x, y)), ("L", (x + w, y)), ("L", (x + w, y + h)), ("L", (x, y + h)), ("Z",)]]
    if tag == "line":
        return [[("M", (_length(element.get("x1")), _length(element.get("y1")))),
                 ("L", (_length(element.get("x2")), _length(element.get("y2"))))]]
    if tag in ("polyline", "polygon"):
        points = _points(element.get("points"))
        if not points:
            return []
        figure = [("M", points[0])] + [("L", point) for point in points[1:]]
        if tag == "polygon":
            figure.append(("Z",))
        return [figure]
    if tag == "circle":
        r = _length(element.get("r"))
        return [_ellipse_figure(_length(element.get("cx")), _length(element.get("cy")), r, r)]
    if tag == "ellipse":
        return [_ellipse_figure(_length(element.get("cx")), _length(element.get("cy")),
                                _length(element.get("rx")), _length(element.get("ry")))]
    raise UnsupportedSvg(f"element {tag}")


# ---------------------------------------------------------------------------
# Text metrics
# ---------------------------------------------------------------------------

@lru_cache(maxsize=32)
def _font_file(family: str, bold: bool, italic: bool) -> Optional[str]:
    try:
        from matplotlib import font_manager

        properties = font_manager.FontProperties(
            family=family, weight="bold" if bold else "normal", style="italic" if italic else "normal",
        )
        return font_manager.findfont(properties, fallback_to_default=False)
    except Exception:
        return None


@lru_cache(maxsize=64)
def _font(path: str, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(path, size)


def _advances(text: str, family: str, size_units: int, bold: bool, italic: bool) -> list[int]:
    """Advance width of every UTF-16 code unit of ``text``, in logical units."""
    path = _font_file(family, bold, italic)
    widths = []
    for character in text:
        width = None
        if path:
            try:
                # Measure at 100x for precision, then scale.
                width = _font(path, 100 * _UNITS_PER_POINT).getlength(character) * size_units / (100 * _UNITS_PER_POINT)
            except Exception:
                width = None
        if width is None:
            width = 0.55 * size_units
        widths.append(round(width))
        if ord(character) > 0xFFFF:
            widths.append(0)
    return widths


# ---------------------------------------------------------------------------
# EMF records
# ---------------------------------------------------------------------------

def _record(kind: int, payload: bytes = b"") -> bytes:
    return struct.pack("<II", kind, 8 + len(payload)) + payload


def _colorref(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    return r | (g << 8) | (b << 16)


class _Writer:
    def __init__(self, width_pt: float, height_pt: float):
        self.width = max(1, round(width_pt * _UNITS_PER_POINT))
        self.height = max(1, round(height_pt * _UNITS_PER_POINT))
        self.width_pt, self.height_pt = width_pt, height_pt
        self.records: list[bytes] = [
            _record(_EMR_SETBKMODE, struct.pack("<I", _TRANSPARENT)),
        ]

    def _bounds(self) -> bytes:
        return struct.pack("<4i", 0, 0, self.width - 1, self.height - 1)

    @staticmethod
    def _point(point: tuple[float, float]) -> tuple[int, int]:
        return round(point[0] * _UNITS_PER_POINT), round(point[1] * _UNITS_PER_POINT)

    def _path(self, figures: Iterable[list[tuple]]) -> None:
        self.records.append(_record(_EMR_BEGINPATH))
        for figure in figures:
            for segment in figure:
                if segment[0] == "M":
                    self.records.append(_record(_EMR_MOVETOEX, struct.pack("<ii", *self._point(segment[1]))))
                elif segment[0] == "L":
                    self.records.append(_record(_EMR_LINETO, struct.pack("<ii", *self._point(segment[1]))))
                elif segment[0] == "C":
                    points = b"".join(struct.pack("<ii", *self._point(p)) for p in segment[1:])
                    self.records.append(_record(_EMR_POLYBEZIERTO, self._bounds() + struct.pack("<I", 3) + points))
                else:
                    self.records.append(_record(_EMR_CLOSEFIGURE))
        self.records.append(_record(_EMR_ENDPATH))

    def shape(self, figures: list[list[tuple]], style: dict, scale: float) -> None:
        fill = _colour(style.get("fill", "black"))
        stroke = _colour(style.get("stroke"))
        width = _length(style.get("stroke-width"), 1.0) * scale
        if fill is None and (stroke is None or width <= 0):
            return
        if not figures:
            return
        if fill is not None:
            mode = _ALTERNATE if style.get("fill-rule") == "evenodd" else _WINDING
            self.records.append(_record(_EMR_SETPOLYFILLMODE, struct.pack("<I", mode)))
            self.records.append(_record(_EMR_CREATEBRUSHINDIRECT, struct.pack("<IIII", _BRUSH, 0, _colorref(fill), 0)))
            self.records.append(_record(_EMR_SELECTOBJECT, struct.pack("<I", _BRUSH)))
        if stroke is not None and width > 0:
            pen_style = (_PS_GEOMETRIC | _PS_ENDCAP.get(style.get("stroke-linecap", "butt"), 0x0200)
                         | _PS_JOIN.get(style.get("stroke-linejoin", "miter"), 0x2000))
            pen_width = max(1, round(width * _UNITS_PER_POINT))
            self.records.append(_record(_EMR_EXTCREATEPEN, struct.pack(
                "<5I6I", _PEN, 0, 0, 0, 0, pen_style, pen_width, 0, _colorref(stroke), 0, 0)))
            self.records.append(_record(_EMR_SELECTOBJECT, struct.pack("<I", _PEN)))
        self._path(figures)
        if fill is not None and stroke is not None and width > 0:
            self.records.append(_record(_EMR_STROKEANDFILLPATH, self._bounds()))
        elif fill is not None:
            self.records.append(_record(_EMR_FILLPATH, self._bounds()))
        else:
            self.records.append(_record(_EMR_STROKEPATH, self._bounds()))
        if fill is not None:
            self.records.append(_record(_EMR_SELECTOBJECT, struct.pack("<I", 0x80000005)))  # NULL_BRUSH
            self.records.append(_record(_EMR_DELETEOBJECT, struct.pack("<I", _BRUSH)))
        if stroke is not None and width > 0:
            self.records.append(_record(_EMR_SELECTOBJECT, struct.pack("<I", 0x80000008)))  # NULL_PEN
            self.records.append(_record(_EMR_DELETEOBJECT, struct.pack("<I", _PEN)))

    def text(self, text: str, origin: tuple[float, float], size_pt: float, style: dict) -> None:
        colour = _colour(style.get("fill", "black"))
        if colour is None or not text:
            return
        family = (style.get("font-family") or "Arial").split(",")[0].strip().strip("'\"")
        bold = style.get("font-weight", "normal") in ("bold", "bolder", "600", "700", "800", "900")
        italic = style.get("font-style", "normal") in ("italic", "oblique")
        size_units = max(1, round(size_pt * _UNITS_PER_POINT))
        face = family.encode("utf-16-le")[:62].ljust(64, b"\0")
        logfont = struct.pack(
            "<5i8B", -size_units, 0, 0, 0, _FW_BOLD if bold else _FW_NORMAL,
            1 if italic else 0, 0, 0, _DEFAULT_CHARSET, 0, 0, 0, 0,
        ) + face
        self.records.append(_record(_EMR_EXTCREATEFONTINDIRECTW, struct.pack("<I", _FONT) + logfont))
        self.records.append(_record(_EMR_SELECTOBJECT, struct.pack("<I", _FONT)))
        anchor = {"middle": _TA_CENTER, "end": _TA_RIGHT}.get(style.get("text-anchor", "start"), 0)
        self.records.append(_record(_EMR_SETTEXTALIGN, struct.pack("<I", _TA_BASELINE | anchor)))
        self.records.append(_record(_EMR_SETTEXTCOLOR, struct.pack("<I", _colorref(colour))))

        encoded = text.encode("utf-16-le")
        units = len(encoded) // 2
        advances = _advances(text, family, size_units, bold, italic)
        string = encoded + b"\0" * (-len(encoded) % 4)
        x, y = self._point(origin)
        fixed = 16 + 4 + 4 + 4 + 8 + 4 + 4 + 4 + 16 + 4  # bounds .. offDx
        offset_string = 8 + fixed
        offset_dx = offset_string + len(string)
        payload = (
            self._bounds()
            + struct.pack("<Iff", _GM_COMPATIBLE, 0.0, 0.0)
            + struct.pack("<iiIII", x, y, units, offset_string, 0)
            + struct.pack("<4i", 0, 0, -1, -1)
            + struct.pack("<I", offset_dx)
            + string
            + struct.pack(f"<{units}i", *advances)
        )
        self.records.append(_record(_EMR_EXTTEXTOUTW, payload))
        self.records.append(_record(_EMR_SELECTOBJECT, struct.pack("<I", 0x8000000D)))  # SYSTEM_FONT
        self.records.append(_record(_EMR_DELETEOBJECT, struct.pack("<I", _FONT)))

    def finish(self) -> bytes:
        eof = _record(_EMR_EOF, struct.pack("<III", 0, 16, 20))
        body = b"".join(self.records) + eof
        hundredths = lambda points: round(points * 2540 / 72)  # noqa: E731
        header_size = 108
        header = struct.pack(
            "<II4i4iIIIIHHIIIiiiiIIIii",
            _EMR_HEADER, header_size, 0, 0, self.width - 1, self.height - 1,
            0, 0, hundredths(self.width_pt) - 1, hundredths(self.height_pt) - 1,
            _ENHMETA_SIGNATURE, 0x00010000, header_size + len(body), len(self.records) + 2,
            _HANDLES, 0, 0, 0, 0,
            _DEVICE_PIXELS, _DEVICE_PIXELS, _DEVICE_MM, _DEVICE_MM,
            0, 0, 0,
            _DEVICE_MM * 1000, _DEVICE_MM * 1000,
        )
        return header + body


def _walk(element: ET.Element, matrix: Matrix, style: dict, writer: _Writer) -> None:
    for child in element:
        tag = _local(child.tag)
        if tag in ("title", "desc", "metadata", "defs", "style"):
            if tag in ("defs", "style") and len(child):
                raise UnsupportedSvg(f"element {tag}")
            continue
        child_matrix = _multiply(matrix, _transform(child.get("transform")))
        child_style = _style(child, style)
        if tag == "g":
            _walk(child, child_matrix, child_style, writer)
            continue
        a, b, c, d, _e, _f = child_matrix
        determinant = a * d - b * c
        scale = math.sqrt(abs(determinant))
        if tag == "text":
            if len(child):
                raise UnsupportedSvg("text with nested elements")
            if abs(b) > 1e-9 or abs(c) > 1e-9 or a <= 0 or abs(a - d) > 1e-9:
                raise UnsupportedSvg("rotated, skewed or mirrored text")
            text = re.sub(r"\s+", " ", child.text or "").strip()
            origin = _apply(child_matrix, _length(child.get("x")), _length(child.get("y")))
            size = _length(child_style.get("font-size"), 16.0) * a
            writer.text(text, origin, size, child_style)
            continue
        figures = [
            [(segment[0], *(_apply(child_matrix, *p) for p in segment[1:])) for segment in figure]
            for figure in _shape_figures(child, tag)
        ]
        if child_style.get("stroke") not in (None, "none") and abs(abs(a) - abs(d)) > 1e-6 * max(abs(a), 1):
            raise UnsupportedSvg("stroke under non-uniform scale")
        writer.shape(figures, child_style, scale)


def svg_to_emf(svg: str | Path | bytes) -> bytes:
    """EMF bytes that draw a ChemDraw SVG export at its physical size.

    ``svg`` is a path or the SVG document itself.  SVG user units are points
    (ChemDraw writes ``px`` for points).  Raises :class:`UnsupportedSvg` when
    the drawing uses a feature that would not be reproduced exactly.
    """
    if isinstance(svg, Path) or (isinstance(svg, str) and not svg.lstrip().startswith("<")):
        data = Path(svg).read_bytes()
    else:
        data = svg.encode("utf-8") if isinstance(svg, str) else svg
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise UnsupportedSvg(f"invalid SVG: {exc}") from exc
    if _local(root.tag) != "svg":
        raise UnsupportedSvg("not an SVG document")
    width = _length(root.get("width"))
    height = _length(root.get("height"))
    view_box = [float(v) for v in _NUMBER.findall(root.get("viewBox") or "")]
    matrix = _IDENTITY
    if len(view_box) == 4 and view_box[2] > 0 and view_box[3] > 0:
        if not width or not height:
            width, height = view_box[2], view_box[3]
        sx, sy = width / view_box[2], height / view_box[3]
        if abs(sx - sy) > 1e-6:
            raise UnsupportedSvg("non-uniform viewBox scale")
        matrix = (sx, 0.0, 0.0, sy, -view_box[0] * sx, -view_box[1] * sy)
    if not width or not height:
        raise UnsupportedSvg("SVG has no size")
    writer = _Writer(width, height)
    _walk(root, matrix, {"fill": "black"}, writer)
    return writer.finish()
