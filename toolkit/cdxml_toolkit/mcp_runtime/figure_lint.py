"""Headless geometry checks for a drawn figure.

Reads the saved CDXML and reports problems that need no ChemDraw: objects
that overlap, text too small to read, an empty page, a drawing wider than
a requested budget, a "+" that is not between two species or crowds one, and
atom labels of one structure that run into each other.
Every object is measured by its ``BoundingBox`` (or, when the file stores none,
from its atoms, arrow ends or text anchor); a structure also includes the
atom labels that overhang its own box.  When a structure's box meets another
object, only its ink counts: its bonds and atom labels, so a caption in the
empty corner of a bent molecule is not an overlap.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from ..cdxml_utils import drawn_fragment_bbox, label_boxes

MIN_FONT_SIZE = 6.0
# A "+" between two species: at least this much white space on each side,
# and no further than this from either (three ACS bond lengths).
PLUS_MIN_CLEARANCE = 3.0  # the renderer leaves about 3.5 pt
PLUS_MAX_GAP = 43.2
# Two atom labels of one structure clash when they share a line (their boxes,
# which include line spacing, overlap this much in height) and run into each
# other by more than LABEL_CLASH_X (pt).
LABEL_CLASH_Y = 3.0
LABEL_CLASH_X = 1.0
# Half a bond's line width and a little white space: ink closer than this touches.
INK_CLEARANCE = 1.0
# Half the width of an arrowhead whose size the arrow does not give.
ARROW_HALF_WIDTH = 4.0
# Text measured from its anchor (the first baseline), per point of font size:
# rough Arial character widths, ink above and below the baseline, line pitch.
TEXT_CHAR_WIDTH = 0.55
_NARROW_CHARS = {**dict.fromkeys("ijlI|", 0.22), **dict.fromkeys(" .,:;'!ftr()[]-/", 0.3)}
_WIDE_CHARS = {**dict.fromkeys("mwMW%", 0.85), **dict.fromkeys("ABCDEFGHKLNOPQRSTUVXYZ", 0.68)}
SCRIPT_SCALE = 0.7
TEXT_ASCENT = 0.75
TEXT_DESCENT = 0.25
TEXT_LINE_PITCH = 1.2
# A text box already includes line spacing, so text gets no clearance, and
# boxes that meet a text box by no more than this (pt) only share that spacing.
TEXT_SLACK = 1.0

Box = Tuple[float, float, float, float]
Point = Tuple[float, float]


def _box(value: Optional[str]) -> Optional[Box]:
    if not value:
        return None
    try:
        x1, y1, x2, y2 = (float(part) for part in value.split()[:4])
    except ValueError:
        return None
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def _union(boxes: List[Box]) -> Box:
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _pad(box: Box, by: float) -> Box:
    return (box[0] - by, box[1] - by, box[2] + by, box[3] + by)


def _segment_hits_box(a: Point, b: Point, box: Box) -> bool:
    """Whether the segment a-b passes through ``box`` (Liang-Barsky clipping)."""
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - box[0]), (dx, box[2] - a[0]), (-dy, a[1] - box[1]), (dy, box[3] - a[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _segment_distance(a: Point, b: Point, c: Point, d: Point) -> float:
    """Shortest distance between segments a-b and c-d."""
    def cross(o: Point, p: Point, q: Point) -> float:
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    if (cross(a, b, c) * cross(a, b, d) < 0) and (cross(c, d, a) * cross(c, d, b) < 0):
        return 0.0

    def to_segment(p: Point, s: Point, e: Point) -> float:
        dx, dy = e[0] - s[0], e[1] - s[1]
        length = dx * dx + dy * dy
        t = 0.0 if length == 0 else max(0.0, min(1.0, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / length))
        return math.hypot(p[0] - s[0] - t * dx, p[1] - s[1] - t * dy)

    return min(to_segment(a, c, d), to_segment(b, c, d), to_segment(c, a, b), to_segment(d, a, b))


def _ink(fragment: ET.Element) -> Optional[Tuple[List[Tuple[Point, Point]], List[Box]]]:
    """A structure's bonds (segments) and atom labels (boxes); None if it has no atoms."""
    points: Dict[str, Point] = {}
    for n in fragment.findall("n"):
        parts = n.get("p", "").split()
        if n.get("NodeType") != "ExternalConnectionPoint" and len(parts) >= 2:
            points[n.get("id", "")] = (float(parts[0]), float(parts[1]))
    if not points:
        return None
    segments = [(points[b.get("B")], points[b.get("E")]) for b in fragment.findall("b")
                if b.get("B") in points and b.get("E") in points]
    boxes = [box for _, box in label_boxes(fragment)]
    bonded = {p for segment in segments for p in segment}
    boxes += [(x, y, x, y) for x, y in points.values() if (x, y) not in bonded]
    return segments, boxes


def _arrow_ink(arrow: ET.Element) -> Optional[Tuple[List[Tuple[Point, Point]], List[Box]]]:
    """A straight arrow's shaft (a segment) and a box around its head; None if curved."""
    if any(arrow.get(name) for name in ("Center3D", "MajorAxisEnd3D", "AngularSize")):
        return None
    ends = [arrow.get(name, "").split() for name in ("Tail3D", "Head3D")]
    if any(len(end) < 2 for end in ends):
        return None
    tail, head = ((float(end[0]), float(end[1])) for end in ends)
    boxes = [] if arrow.get("ArrowheadHead") == "None" else [_arrowhead(arrow, tail, head)]
    if arrow.get("ArrowheadTail", "None") != "None":
        boxes.append(_arrowhead(arrow, head, tail))
    return [(tail, head)], boxes


def _arrowhead(arrow: ET.Element, start: Point, tip: Point) -> Box:
    """Box around the head at ``tip`` of an arrow drawn from ``start``.

    ``ArrowheadWidth`` (half the head's width) and ``HeadSize`` (its length)
    are hundredths of ``LineWidth``.
    """
    try:
        line = float(arrow.get("LineWidth", "0.6"))
        half = float(arrow.get("ArrowheadWidth")) / 100.0 * line
        length = float(arrow.get("HeadSize", "1000")) / 100.0 * line
    except (TypeError, ValueError):
        return _pad((*tip, *tip), ARROW_HALF_WIDTH)
    shaft = math.hypot(tip[0] - start[0], tip[1] - start[1]) or 1.0
    ux, uy = (tip[0] - start[0]) / shaft, (tip[1] - start[1]) / shaft
    base = (tip[0] - ux * length, tip[1] - uy * length)
    corners = [tip, (base[0] - uy * half, base[1] + ux * half), (base[0] + uy * half, base[1] - ux * half)]
    return (min(x for x, _ in corners), min(y for _, y in corners),
            max(x for x, _ in corners), max(y for _, y in corners))


def _ink_meets_box(ink: Tuple[List[Tuple[Point, Point]], List[Box]], box: Box,
                   clearance: float = INK_CLEARANCE) -> bool:
    segments, boxes = ink
    padded = _pad(box, clearance)
    return (any(_overlaps(label, padded) for label in boxes)
            or any(_segment_hits_box(a, b, padded) for a, b in segments))


def _inks_meet(first: Tuple[List[Tuple[Point, Point]], List[Box]],
               second: Tuple[List[Tuple[Point, Point]], List[Box]]) -> bool:
    if any(_ink_meets_box(first, box) for box in second[1]) \
            or any(_ink_meets_box(second, box) for box in first[1]):
        return True
    return any(_segment_distance(a, b, c, d) < 2 * INK_CLEARANCE
               for a, b in first[0] for c, d in second[0])


def _stroke(node: ET.Element) -> bool:
    """An arrow with no head at either end: a line drawn as part of a structure."""
    return node.tag == "arrow" and node.get("ArrowheadHead") == "None" \
        and node.get("ArrowheadTail", "None") == "None"


def _collide(first: Dict[str, Any], second: Dict[str, Any]) -> bool:
    if not _overlaps(first["box"], second["box"]):
        return False
    tags = (first["tag"], second["tag"])
    if "fragment" in tags and (_stroke(first["node"]) or _stroke(second["node"])):
        return False
    first_ink, second_ink = first.get("ink"), second.get("ink")
    if first_ink and second_ink:
        return _inks_meet(first_ink, second_ink)
    if first_ink or second_ink:
        ink, other = (first_ink, second) if first_ink else (second_ink, first)
        return _ink_meets_box(ink, other["box"], 0.0 if other["tag"] == "t" else INK_CLEARANCE)
    if "t" in (first["tag"], second["tag"]):
        return _overlaps(_pad(first["box"], -TEXT_SLACK / 2.0), _pad(second["box"], -TEXT_SLACK / 2.0))
    return True


def _measured_box(node: ET.Element) -> Optional[Box]:
    """A box for an object whose CDXML stores none (ChemDraw computes it on open)."""
    if node.tag == "fragment":
        return drawn_fragment_bbox(node)
    if node.tag == "arrow":
        ends = [node.get(name, "").split() for name in ("Tail3D", "Head3D")]
        if any(len(end) < 2 for end in ends):
            return None
        (x1, y1), (x2, y2) = ((float(end[0]), float(end[1])) for end in ends)
        length = math.hypot(x2 - x1, y2 - y1) or 1.0
        # The arrowhead widens the shaft sideways only.
        across_x = ARROW_HALF_WIDTH * abs(y2 - y1) / length
        across_y = ARROW_HALF_WIDTH * abs(x2 - x1) / length
        return (min(x1, x2) - across_x, min(y1, y2) - across_y,
                max(x1, x2) + across_x, max(y1, y2) + across_y)
    anchor = node.get("p", "").split()
    if len(anchor) < 2:
        return None
    x, y = float(anchor[0]), float(anchor[1])
    sizes = [float(run.get("size")) for run in node.iter("s") if run.get("size")]
    size = max(sizes, default=10.0)
    widths = [0.0]
    for run in node.iter("s"):
        run_size = float(run.get("size") or size)
        if int(run.get("face") or 0) & 0x60 in (0x20, 0x40):
            run_size *= SCRIPT_SCALE
        for n, line in enumerate((run.text or "").split("\n")):
            if n:
                widths.append(0.0)
            widths[-1] += run_size * sum(_NARROW_CHARS.get(c, _WIDE_CHARS.get(c, TEXT_CHAR_WIDTH))
                                         for c in line)
    lines = len(widths)
    width = max(widths)
    justification = node.get("CaptionJustification", node.get("Justification", "Left"))
    left = x - width / 2.0 if justification == "Center" else x - width if justification == "Right" else x
    return (left, y - TEXT_ASCENT * size,
            left + width, y + ((lines - 1) * TEXT_LINE_PITCH + TEXT_DESCENT) * size)


def _objects(page: ET.Element) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for child in page:
        if child.tag not in ("fragment", "arrow", "t"):
            continue
        box = _box(child.get("BoundingBox")) or _measured_box(child)
        if box is None:
            continue
        if child.tag == "fragment":
            labels = [b for b in (_box(t.get("BoundingBox")) for t in child.iter("t")) if b]
            box = _union([box, *labels])
        ink = _ink(child) if child.tag == "fragment" else _arrow_ink(child) if child.tag == "arrow" else None
        found.append({"id": child.get("id", ""), "tag": child.tag, "box": box, "node": child, "ink": ink})
    return found


def _text_of(node: ET.Element) -> str:
    return "".join("".join(node.itertext()).split())


def _plus_issues(objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A "+" must sit on the line of two species, one either side, close to both."""
    species = []
    for obj in objects:
        if obj["tag"] == "arrow" or (obj["tag"] == "t" and _text_of(obj["node"]) in ("", "+")):
            continue
        box = obj["box"]
        if obj["tag"] == "fragment":
            # A label box often names only its first letter: count the whole label.
            drawn = drawn_fragment_bbox(obj["node"])
            box = _union([box, drawn]) if drawn else box
        species.append((obj, box))
    issues: List[Dict[str, Any]] = []
    for plus in (o for o in objects if o["tag"] == "t" and _text_of(o["node"]) == "+"):
        x1, y1, x2, y2 = plus["box"]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        level = [(obj, box) for obj, box in species if box[1] <= cy <= box[3]]
        left = max((box[2] for _, box in level if (box[0] + box[2]) / 2.0 < cx), default=None)
        right = min((box[0] for _, box in level if (box[0] + box[2]) / 2.0 > cx), default=None)
        if left is None or right is None or x1 - left > PLUS_MAX_GAP or right - x2 > PLUS_MAX_GAP:
            issues.append({
                "kind": "stray_plus",
                "ids": [plus["id"]],
                "message": f"The + {plus['id']} is not between two species on its line.",
            })
        elif 0 <= min(x1 - left, right - x2) < PLUS_MIN_CLEARANCE:
            issues.append({
                "kind": "crowded_plus",
                "ids": [plus["id"]],
                "clearance": round(min(x1 - left, right - x2), 1),
                "message": f"The + {plus['id']} has less than {PLUS_MIN_CLEARANCE:g} pt "
                           "of space beside a species.",
            })
    return issues


def lint_cdxml(cdxml_text: str, max_width: Optional[float] = None) -> List[Dict[str, Any]]:
    """Return a list of issues; an empty list means the geometry checks passed."""
    root = ET.fromstring(cdxml_text)
    page = root.find("page")
    objects = _objects(page) if page is not None else []
    if not objects:
        return [{"kind": "empty", "ids": [], "message": "The page has no drawn objects."}]

    issues: List[Dict[str, Any]] = []
    for first, second in combinations(objects, 2):
        if first["tag"] == second["tag"] == "arrow":
            continue
        if _collide(first, second):
            issues.append({
                "kind": "overlap",
                "ids": [first["id"], second["id"]],
                "message": f"{first['tag']} {first['id']} overlaps {second['tag']} {second['id']}.",
            })

    for obj in objects:
        for run in obj["node"].iter("s"):
            try:
                size = float(run.get("size", ""))
            except ValueError:
                continue
            if size < MIN_FONT_SIZE:
                issues.append({
                    "kind": "small_text",
                    "ids": [obj["id"]],
                    "size": size,
                    "message": f"Text in {obj['tag']} {obj['id']} is {size:g} pt, below {MIN_FONT_SIZE:g} pt.",
                })
                break

    for obj in objects:
        if obj["tag"] != "fragment":
            continue
        for (first, a), (second, b) in combinations(label_boxes(obj["node"]), 2):
            if (min(a[2], b[2]) - max(a[0], b[0]) > LABEL_CLASH_X
                    and min(a[3], b[3]) - max(a[1], b[1]) > LABEL_CLASH_Y):
                issues.append({
                    "kind": "label_clash",
                    "ids": [obj["id"]],
                    "atoms": [first.get("id"), second.get("id")],
                    "message": f"Two atom labels of fragment {obj['id']} run into each other.",
                })

    issues.extend(_plus_issues(objects))

    if max_width is not None:
        left, _, right, _ = _union([o["box"] for o in objects])
        width = right - left
        if width > max_width:
            issues.append({
                "kind": "too_wide",
                "ids": [],
                "width": round(width, 1),
                "budget": max_width,
                "message": f"The drawing is {width:.0f} pt wide; the budget is {max_width:g} pt.",
            })
    return issues
