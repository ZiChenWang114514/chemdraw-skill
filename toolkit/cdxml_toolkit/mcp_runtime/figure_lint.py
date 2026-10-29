"""Headless geometry checks for a drawn figure.

Reads the saved CDXML and reports problems that need no ChemDraw: objects
that overlap, text too small to read, an empty page, a drawing wider than
a requested budget, a "+" that is not between two species or crowds one, and
atom labels of one structure that run into each other.
Every object is measured by its ``BoundingBox``; a structure also includes the
atom labels that overhang its own box.
"""

from __future__ import annotations

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

Box = Tuple[float, float, float, float]


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


def _objects(page: ET.Element) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for child in page:
        if child.tag not in ("fragment", "arrow", "t"):
            continue
        box = _box(child.get("BoundingBox"))
        if box is None:
            continue
        if child.tag == "fragment":
            labels = [b for b in (_box(t.get("BoundingBox")) for t in child.iter("t")) if b]
            box = _union([box, *labels])
        found.append({"id": child.get("id", ""), "tag": child.tag, "box": box, "node": child})
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
        if _overlaps(first["box"], second["box"]):
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
