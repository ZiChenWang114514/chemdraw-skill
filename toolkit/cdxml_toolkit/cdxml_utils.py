"""Shared CDXML geometry and IO utilities.

Extracted from duplicated code across reaction_cleanup.py,
eln_enrichment.py, and scheme_polisher.py for v0.3 consolidation.

Key design decisions (from CLAUDE.md / reaction_cleanup FINDINGS):
  - Fragment bounding boxes use direct-child <n> atom "p" positions ONLY.
    XML BoundingBox attributes are unreliable, especially for
    NodeType="Fragment" abbreviation groups (OTs, Boc) which report
    the expanded inner structure, not the visible abbreviation.
  - Hanging label detection: when N or P is the bottommost atom with
    <=2 explicit bonds, ChemDraw renders H as a vertical stack below
    the atom symbol, requiring extra layout gap (16pt vs 8pt).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple

from .constants import LAYOUT_HANGING_LABEL_GAP


# ---------------------------------------------------------------------------
# Fragment geometry
# ---------------------------------------------------------------------------

def fragment_bbox(
    frag: ET.Element,
) -> Optional[Tuple[float, float, float, float]]:
    """Atom-only bounding box for a <fragment> element.

    Uses direct-child <n> atom ``p`` positions only (NOT recursive,
    NOT XML BoundingBox).  XML BoundingBox is unreliable for
    ``NodeType='Fragment'`` abbreviation groups.

    Returns ``(min_x, min_y, max_x, max_y)`` or *None* if the
    fragment has no atoms with ``p`` attributes and no fallback
    BoundingBox.
    """
    xs: list[float] = []
    ys: list[float] = []

    for n in frag.findall("n"):          # direct children only
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                xs.append(float(parts[0]))
                ys.append(float(parts[1]))

    if xs:
        return min(xs), min(ys), max(xs), max(ys)

    # Fallback: use XML BoundingBox if present
    bb = frag.get("BoundingBox", "")
    if bb:
        vals = [float(v) for v in bb.split()]
        if len(vals) >= 4:
            return vals[0], vals[1], vals[2], vals[3]

    return None


def fragment_centroid(frag: ET.Element) -> Optional[Tuple[float, float]]:
    """Center point of :func:`fragment_bbox`.

    Returns ``(cx, cy)`` or *None* when no bbox can be computed.
    """
    bbox = fragment_bbox(frag)
    if bbox is None:
        return None
    return (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0


def fragment_bottom_has_hanging_label(frag: ET.Element) -> bool:
    """True if the bottommost atom has a label that hangs below it.

    In ChemDraw, when N (Element=7) or P (Element=15) is the bottommost
    atom of a fragment and has only 2 or fewer explicit bonds, the
    implicit H is rendered as a vertical stack (N above, H below).
    This causes the label to extend below the atom coordinate.

    Returns *True* when extra gap is needed below this fragment.
    """
    HANGING_ELEMENTS = {"7", "15"}

    atoms: list[tuple[ET.Element, float]] = []  # (node, y)
    for n in frag.findall("n"):
        p = n.get("p")
        if p:
            parts = p.split()
            if len(parts) >= 2:
                atoms.append((n, float(parts[1])))

    if not atoms:
        return False

    max_y = max(a[1] for a in atoms)

    for n, y in atoms:
        if y < max_y - 1.0:
            continue
        if n.get("Element", "") not in HANGING_ELEMENTS:
            continue

        node_id = n.get("id", "")
        bond_count = 0
        for b in frag.findall("b"):
            if b.get("B") == node_id or b.get("E") == node_id:
                bond_count += 1

        if bond_count <= 2:
            return True

    return False


def fragment_bbox_with_label_extension(
    frag: ET.Element,
) -> Optional[Tuple[float, float, float, float]]:
    """Atom-only bounding box with hanging-label extension.

    Delegates to :func:`fragment_bbox` for the base bbox, then extends
    ``max_y`` by :data:`constants.LAYOUT_HANGING_LABEL_GAP` (+16 pt) when
    :func:`fragment_bottom_has_hanging_label` is True.

    This accounts for N-H / P-H labels that render as a vertical stack
    below the atom coordinate in ChemDraw.
    """
    bbox = fragment_bbox(frag)
    if bbox is None:
        return None
    min_x, min_y, max_x, max_y = bbox
    if fragment_bottom_has_hanging_label(frag):
        max_y += LAYOUT_HANGING_LABEL_GAP
    return (min_x, min_y, max_x, max_y)


# ---------------------------------------------------------------------------
# Text geometry
# ---------------------------------------------------------------------------

def recompute_text_bbox(t_elem: ET.Element) -> None:
    """Recompute and set BoundingBox on a ``<t>`` element.

    Uses the ``p`` attribute (anchor position) and aggregated ``<s>``
    text content to estimate bounds.  Char width 5.8 pt (Arial 10 pt),
    line height 12 pt.  Handles multi-line text and Left/Center/Right
    justification.
    """
    p = t_elem.get("p", "")
    if not p:
        return
    parts = [float(v) for v in p.split()]
    if len(parts) < 2:
        return
    px, py = parts[0], parts[1]

    text_content = "".join(s.text or "" for s in t_elem.iter("s"))
    lines = text_content.split("\n") if "\n" in text_content else [text_content]
    max_line_len = max((len(l) for l in lines), default=0)
    n_lines = max(1, len(lines))

    char_w = 5.8
    line_h = 12.0
    w = max_line_len * char_w
    h = n_lines * line_h  # noqa: F841  (kept for clarity)

    just = t_elem.get(
        "CaptionJustification", t_elem.get("Justification", "Left")
    )
    if just == "Center":
        x1 = px - w / 2.0
        x2 = px + w / 2.0
    elif just == "Right":
        x1 = px - w
        x2 = px
    else:  # Left (default)
        x1 = px
        x2 = px + w

    y1 = py - line_h                              # ascender above baseline
    y2 = py + (n_lines - 1) * line_h + 3.0        # descender below last

    t_elem.set("BoundingBox", f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}")


# ---------------------------------------------------------------------------
# ID map
# ---------------------------------------------------------------------------

def build_id_map(parent: ET.Element) -> Dict[str, ET.Element]:
    """Build ``{id_string: element}`` map for all descendants with an
    ``id`` attribute.

    This is **recursive** — it walks the entire subtree via
    ``parent.iter()``, so nested elements at any depth are included.

    Note: ``reaction_cleanup._build_id_map()`` is intentionally
    **shallow** (direct children only via ``for el in page``).
    The two are NOT interchangeable.
    """
    m: Dict[str, ET.Element] = {}
    for el in parent.iter():
        eid = el.get("id", "")
        if eid:
            m[eid] = el
    return m


# ---------------------------------------------------------------------------
# Arrow geometry
# ---------------------------------------------------------------------------

def arrow_endpoints(
    arrow: ET.Element,
) -> Tuple[float, float, float, float]:
    """Return ``(tail_x, tail_y, head_x, head_y)`` from an arrow element.

    Reads ``Head3D`` and ``Tail3D`` attributes first, falling back to
    ``BoundingBox``.  Returns a default (450, 250, 550, 250) if neither
    is available.
    """
    head = arrow.get("Head3D", "")
    tail = arrow.get("Tail3D", "")
    if head and tail:
        hp = [float(v) for v in head.split()]
        tp = [float(v) for v in tail.split()]
        return tp[0], tp[1], hp[0], hp[1]
    # Fallback: BoundingBox
    bb = arrow.get("BoundingBox", "")
    if bb:
        vals = [float(v) for v in bb.split()]
        return vals[0], (vals[1] + vals[3]) / 2, vals[2], (vals[1] + vals[3]) / 2
    return 450.0, 250.0, 550.0, 250.0


# ---------------------------------------------------------------------------
# CDXML IO
# ---------------------------------------------------------------------------

def parse_cdxml(path: str) -> ET.ElementTree:
    """Parse a CDXML file, returning an :class:`~xml.etree.ElementTree.ElementTree`."""
    return ET.parse(path)


def write_cdxml(tree: ET.ElementTree, path: str) -> None:
    """Write *tree* to *path*, re-inserting the DOCTYPE declaration.

    ``ElementTree.write()`` drops the DOCTYPE.  This function writes
    the XML first, then patches the file to re-add it and strip any
    ``ns0:`` namespace prefixes.
    """
    tree.write(path, xml_declaration=True, encoding="UTF-8")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "<!DOCTYPE" not in content:
        content = content.replace(
            "?>",
            '?>\n<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >',
            1,
        )

    # Strip namespace prefixes that ElementTree may inject
    content = content.replace("ns0:", "").replace(":ns0", "")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("cdxml_utils self-test\n" + "=" * 40)

    # Minimal fragment with 3 atoms and 2 bonds
    xml_str = """\
    <fragment id="100">
      <n id="1" p="100 200" Element="6" />
      <n id="2" p="120 180" Element="7" NumHydrogens="1" />
      <n id="3" p="140 200" />
      <b id="10" B="1" E="2" />
      <b id="11" B="2" E="3" />
    </fragment>"""
    frag = ET.fromstring(xml_str)

    # fragment_bbox
    bbox = fragment_bbox(frag)
    assert bbox is not None, "bbox should not be None"
    assert bbox == (100.0, 180.0, 140.0, 200.0), f"unexpected bbox: {bbox}"
    print(f"  fragment_bbox:    {bbox}  OK")

    # fragment_centroid
    c = fragment_centroid(frag)
    assert c is not None
    assert c == (120.0, 190.0), f"unexpected centroid: {c}"
    print(f"  fragment_centroid: {c}  OK")

    # hanging label — atom 2 (N, Element=7) is NOT bottommost (y=180 < 200)
    assert not fragment_bottom_has_hanging_label(frag), "should be False"
    print("  hanging_label (no):  OK")

    # Fragment where N IS bottommost
    xml_hang = """\
    <fragment id="200">
      <n id="1" p="100 180" />
      <n id="2" p="120 200" Element="7" />
      <b id="10" B="1" E="2" />
    </fragment>"""
    frag_hang = ET.fromstring(xml_hang)
    assert fragment_bottom_has_hanging_label(frag_hang), "should be True"
    print("  hanging_label (yes): OK")

    # Empty fragment — no atoms
    frag_empty = ET.fromstring('<fragment id="300" />')
    assert fragment_bbox(frag_empty) is None, "empty frag should return None"
    assert fragment_centroid(frag_empty) is None
    print("  empty fragment:      OK")

    # recompute_text_bbox
    t_xml = '<t id="50" p="100 200"><s>Hello</s></t>'
    t_el = ET.fromstring(t_xml)
    recompute_text_bbox(t_el)
    bb = t_el.get("BoundingBox")
    assert bb is not None, "BoundingBox should be set"
    vals = [float(v) for v in bb.split()]
    assert len(vals) == 4
    print(f"  recompute_text_bbox: {bb}  OK")

    # build_id_map
    page_xml = '<page><n id="1" /><n id="2"><n id="3" /></n></page>'
    page = ET.fromstring(page_xml)
    m = build_id_map(page)
    assert "1" in m and "2" in m and "3" in m, f"missing ids: {set(m)}"
    print(f"  build_id_map:      {len(m)} entries  OK")

    print("\nAll tests passed.")
