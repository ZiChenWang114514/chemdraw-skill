"""Headless geometry checks for a drawn figure.

Reads the saved CDXML and reports problems that need no ChemDraw: objects
that overlap, text too small to read, an empty page, and a drawing wider than
a requested budget. Every object is measured by its ``BoundingBox``; a
structure also includes the atom labels that overhang its own box.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

MIN_FONT_SIZE = 6.0

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
