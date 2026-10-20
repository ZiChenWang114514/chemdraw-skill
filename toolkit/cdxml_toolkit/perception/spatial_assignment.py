"""
spatial_assignment.py — Geometry-first spatial assignment of scheme elements to arrows.

Replaces the naive x-band assignment in scheme_reader._parse_from_geometry()
with a rotation-invariant, distance-based approach that handles arbitrary arrow
orientations, multi-row layouts, branching, and cycles.

Algorithmic influences:
  - ReactionDataExtractor (Cambridge, 2021/2023): arrow-centric equidistant scan
  - RxnIM (HKUST, 2025): layout pattern taxonomy (single/multi-line/branch/cycle)
  - CDXML advantage: exact coordinates from XML, no detection/OCR needed

Key design decisions:
  - Arrow-relative projection: every point is transformed into (parallel, perp)
    coordinates relative to each arrow. This makes role assignment
    rotation-invariant.
  - Distance-based assignment: fragments go to the nearest arrow by a combined
    distance score, not by hard x-coordinate bands.
  - Layout classifier: detects the scheme pattern first, then delegates to a
    pattern-specific strategy that handles edge cases for that layout type.
  - Confidence scoring: every assignment carries a 0-1 confidence based on
    the ratio of nearest to second-nearest arrow distance.

API:
    from cdxml_toolkit.perception.spatial_assignment import (
        build_arrow_vectors, classify_layout, assign_elements,
    )
    arrows = build_arrow_vectors(page_element)
    layout = classify_layout(arrows)
    steps, results = assign_elements(arrows, page_element, layout)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from xml.etree import ElementTree as ET

from ..constants import ACS_BOND_LENGTH


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ArrowVector:
    """Fully characterised arrow with direction, type, and spatial metadata."""
    element_id: str
    element: ET.Element
    tail: Tuple[float, float]
    head: Tuple[float, float]
    midpoint: Tuple[float, float]
    direction: Tuple[float, float]   # unit vector tail -> head
    normal: Tuple[float, float]      # perpendicular — points to "above" side
    length: float
    angle_deg: float                 # 0=right, 90=down, 180=left, 270=up
    arrow_type: str                  # "solid", "dashed", "failed", "equilibrium"


class LayoutPattern(Enum):
    SINGLE_LINE = "single_line"
    MULTI_LINE = "multi_line"
    BRANCH = "branch"
    CYCLE = "cycle"
    SERPENTINE = "serpentine"
    MIXED = "mixed"


@dataclass
class FragmentInfo:
    """Spatial metadata for a CDXML fragment."""
    element_id: str
    element: ET.Element
    centroid: Tuple[float, float]
    bbox: Tuple[float, float, float, float]


@dataclass
class TextInfo:
    """Spatial metadata for a CDXML text element."""
    element_id: str
    element: ET.Element
    position: Tuple[float, float]


@dataclass
class AssignmentResult:
    """Single element-to-arrow assignment with confidence."""
    element_id: str
    arrow_id: str
    role: str           # "reactant", "product", "above", "below"
    confidence: float   # 0.0 – 1.0
    distance: float     # perpendicular distance to arrow axis


@dataclass
class RawStep:
    """One reaction step derived from spatial assignment."""
    arrow_id: str
    arrow_element: Optional[ET.Element] = None
    reactant_ids: List[str] = field(default_factory=list)
    product_ids: List[str] = field(default_factory=list)
    above_arrow_ids: List[str] = field(default_factory=list)
    below_arrow_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0
    layout_row: int = 0              # row index for multi-line layouts


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

def _unit_vector(dx: float, dy: float) -> Tuple[float, float]:
    """Normalise (dx, dy) to a unit vector.  Returns (0, 0) for zero-length."""
    mag = math.hypot(dx, dy)
    if mag < 1e-9:
        return (0.0, 0.0)
    return (dx / mag, dy / mag)


def project_onto_arrow(
    point: Tuple[float, float],
    tail: Tuple[float, float],
    head: Tuple[float, float],
) -> Tuple[float, float]:
    """Project *point* into the arrow-relative coordinate system.

    Returns ``(parallel, perpendicular)`` where:
      - *parallel*: signed distance along the arrow axis from the tail.
        Negative = behind the tail, > arrow length = past the head.
      - *perpendicular*: signed distance from the arrow axis.
        Negative = "above" side, positive = "below" side.

    Sign convention for perpendicular (CDXML y-axis points downward):
      - For a horizontal L-to-R arrow: y < arrow → above → perp < 0
      - For a vertical downward arrow: x > arrow → right side → perp < 0
        (right side is "above" when the arrow points down)
    """
    dx = head[0] - tail[0]
    dy = head[1] - tail[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        # Degenerate arrow — return distance from tail
        dist = math.hypot(point[0] - tail[0], point[1] - tail[1])
        return (0.0, dist)

    # Direction unit vector
    ux, uy = dx / length, dy / length
    # Normal: rotate direction 90° counter-clockwise in math coords,
    # which is clockwise on screen (y-down).
    # For a rightward arrow (ux=1, uy=0) this gives (0, 1) i.e. downward.
    # Convention: perpendicular < 0 = "above" side, > 0 = "below" side.
    nx, ny = -uy, ux

    # Vector from tail to point
    vx = point[0] - tail[0]
    vy = point[1] - tail[1]

    parallel = vx * ux + vy * uy
    perpendicular = vx * nx + vy * ny

    return (parallel, perpendicular)


def point_to_segment_distance(
    point: Tuple[float, float],
    seg_start: Tuple[float, float],
    seg_end: Tuple[float, float],
) -> float:
    """Shortest distance from *point* to the line segment [seg_start, seg_end]."""
    sx, sy = seg_start
    ex, ey = seg_end
    dx, dy = ex - sx, ey - sy
    len_sq = dx * dx + dy * dy

    if len_sq < 1e-18:
        return math.hypot(point[0] - sx, point[1] - sy)

    # Parameter t for projection onto the infinite line
    t = ((point[0] - sx) * dx + (point[1] - sy) * dy) / len_sq
    t = max(0.0, min(1.0, t))

    proj_x = sx + t * dx
    proj_y = sy + t * dy
    return math.hypot(point[0] - proj_x, point[1] - proj_y)


# ---------------------------------------------------------------------------
# Arrow vector construction
# ---------------------------------------------------------------------------

def _classify_arrow_type(arrow: ET.Element) -> str:
    """Classify arrow type from CDXML attributes."""
    if arrow.get("NoGo") == "Cross":
        return "failed"
    line_type = (arrow.get("LineType") or "").lower()
    if line_type in ("dash", "dashed", "dot"):
        return "dashed"
    if (arrow.get("ArrowheadType") or "").lower() == "dashed":
        return "dashed"
    # Check for equilibrium arrows (double-headed)
    arrow_type_attr = (arrow.get("ArrowType") or "").lower()
    if "equilibrium" in arrow_type_attr:
        return "equilibrium"
    return "solid"


def build_arrow_vector(arrow: ET.Element) -> ArrowVector:
    """Build an :class:`ArrowVector` from a CDXML ``<arrow>`` or ``<graphic>`` element."""
    from ..cdxml_utils import arrow_endpoints

    tx, ty, hx, hy = arrow_endpoints(arrow)

    dx = hx - tx
    dy = hy - ty
    length = math.hypot(dx, dy)

    direction = _unit_vector(dx, dy)
    # Normal: perpendicular < 0 = "above" side, > 0 = "below" side.
    # For a rightward arrow (1, 0) this gives (0, 1) pointing downward.
    normal = (-direction[1], direction[0])

    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad) % 360

    return ArrowVector(
        element_id=arrow.get("id", ""),
        element=arrow,
        tail=(tx, ty),
        head=(hx, hy),
        midpoint=((tx + hx) / 2, (ty + hy) / 2),
        direction=direction,
        normal=normal,
        length=length,
        angle_deg=angle_deg,
        arrow_type=_classify_arrow_type(arrow),
    )


def build_arrow_vectors(page: ET.Element) -> List[ArrowVector]:
    """Find all arrows on the page and build ArrowVector objects.

    Searches for ``<arrow>`` elements and ``<graphic>`` elements with
    ``GraphicType="Line"`` and an ``ArrowType`` attribute.
    """
    seen: Set[str] = set()
    arrows: List[ArrowVector] = []

    for el in page:
        if el.tag == "arrow":
            eid = el.get("id", "")
            if eid not in seen:
                arrows.append(build_arrow_vector(el))
                seen.add(eid)

    for el in page:
        if el.tag == "graphic":
            if el.get("GraphicType") == "Line" and el.get("ArrowType"):
                eid = el.get("id", "")
                if eid not in seen:
                    arrows.append(build_arrow_vector(el))
                    seen.add(eid)

    return arrows


# ---------------------------------------------------------------------------
# Fragment and text collection
# ---------------------------------------------------------------------------

def collect_fragments(page: ET.Element) -> List[FragmentInfo]:
    """Collect all fragments on the page with spatial metadata."""
    from ..cdxml_utils import fragment_bbox, fragment_centroid

    frags: List[FragmentInfo] = []
    for el in page:
        if el.tag == "fragment":
            centroid = fragment_centroid(el)
            bbox = fragment_bbox(el)
            if centroid is None or bbox is None:
                continue
            frags.append(FragmentInfo(
                element_id=el.get("id", ""),
                element=el,
                centroid=centroid,
                bbox=bbox,
            ))
    return frags


def collect_texts(page: ET.Element) -> List[TextInfo]:
    """Collect all free text elements on the page with positions."""
    texts: List[TextInfo] = []
    for el in page:
        if el.tag == "t":
            p = el.get("p")
            if p:
                parts = p.split()
                if len(parts) >= 2:
                    pos = (float(parts[0]), float(parts[1]))
                    texts.append(TextInfo(
                        element_id=el.get("id", ""),
                        element=el,
                        position=pos,
                    ))
                    continue
            # Fallback: BoundingBox center
            bb = el.get("BoundingBox", "")
            if bb:
                vals = [float(v) for v in bb.split()]
                if len(vals) >= 4:
                    pos = ((vals[0] + vals[2]) / 2, (vals[1] + vals[3]) / 2)
                    texts.append(TextInfo(
                        element_id=el.get("id", ""),
                        element=el,
                        position=pos,
                    ))
    return texts


# ---------------------------------------------------------------------------
# Layout classification
# ---------------------------------------------------------------------------

_HORIZONTAL_ANGLE_TOLERANCE = 30.0  # degrees from horizontal (0 or 180)
_VERTICAL_ANGLE_TOLERANCE = 30.0    # degrees from vertical (90 or 270)


def _is_horizontal(arrow: ArrowVector) -> bool:
    """True if arrow is within tolerance of horizontal (L->R or R->L)."""
    a = arrow.angle_deg
    return (a < _HORIZONTAL_ANGLE_TOLERANCE
            or a > 360 - _HORIZONTAL_ANGLE_TOLERANCE
            or abs(a - 180) < _HORIZONTAL_ANGLE_TOLERANCE)


def _is_vertical(arrow: ArrowVector) -> bool:
    """True if arrow is within tolerance of vertical (down or up)."""
    a = arrow.angle_deg
    return (abs(a - 90) < _VERTICAL_ANGLE_TOLERANCE
            or abs(a - 270) < _VERTICAL_ANGLE_TOLERANCE)


def cluster_arrows_into_rows(
    arrows: List[ArrowVector],
    gap_threshold: Optional[float] = None,
) -> List[List[ArrowVector]]:
    """Cluster arrows into horizontal rows by y-coordinate.

    Uses single-linkage clustering with a gap threshold derived from the
    median arrow length (default 1.5x).  Returns rows sorted top-to-bottom
    (increasing y), with arrows within each row sorted left-to-right.
    """
    if not arrows:
        return []

    if gap_threshold is None:
        lengths = sorted(a.length for a in arrows if a.length > 0)
        median_len = lengths[len(lengths) // 2] if lengths else ACS_BOND_LENGTH * 3
        # Use half the median arrow length as the row clustering threshold.
        # Arrows within this vertical distance belong to the same row.
        # For ACS-style schemes (arrow ~43pt), this gives ~21pt tolerance,
        # which is enough for slight vertical jitter but not enough to merge
        # genuinely separate rows.
        gap_threshold = 0.5 * median_len

    # Sort by midpoint y
    sorted_arrows = sorted(arrows, key=lambda a: a.midpoint[1])

    rows: List[List[ArrowVector]] = [[sorted_arrows[0]]]
    for arrow in sorted_arrows[1:]:
        # Check if this arrow belongs to the current row
        row_y_center = sum(a.midpoint[1] for a in rows[-1]) / len(rows[-1])
        if abs(arrow.midpoint[1] - row_y_center) <= gap_threshold:
            rows[-1].append(arrow)
        else:
            rows.append([arrow])

    # Sort arrows within each row by midpoint x
    for row in rows:
        row.sort(key=lambda a: a.midpoint[0])

    return rows


def _arrows_form_cycle(arrows: List[ArrowVector],
                       proximity_threshold: Optional[float] = None) -> bool:
    """Check if arrows form a closed cycle (head of each -> tail of next, closing loop).

    Uses proximity matching: arrow i's head must be near arrow j's tail for
    some permutation that forms a cycle.
    """
    if len(arrows) < 2:
        return False

    if proximity_threshold is None:
        avg_length = sum(a.length for a in arrows) / len(arrows)
        proximity_threshold = avg_length * 0.8

    # Build a directed graph: arrow i -> arrow j if head_i is near tail_j
    n = len(arrows)
    adj: Dict[int, List[int]] = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dist = math.hypot(
                arrows[i].head[0] - arrows[j].tail[0],
                arrows[i].head[1] - arrows[j].tail[1],
            )
            if dist < proximity_threshold:
                adj[i].append(j)

    # DFS cycle detection from each node
    WHITE, GRAY, BLACK = 0, 1, 2
    color = [WHITE] * n

    def dfs(u: int) -> bool:
        color[u] = GRAY
        for v in adj[u]:
            if color[v] == GRAY:
                return True  # back edge -> cycle
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for i in range(n):
        if color[i] == WHITE and dfs(i):
            return True
    return False


def _arrows_share_endpoint(
    arrows: List[ArrowVector],
    proximity_threshold: Optional[float] = None,
) -> bool:
    """Check if any arrows share a tail or head region (branch indicator)."""
    if len(arrows) < 2:
        return False

    if proximity_threshold is None:
        avg_length = sum(a.length for a in arrows) / len(arrows)
        proximity_threshold = avg_length * 0.5

    # Check for shared tails (divergent) or shared heads (convergent)
    for i in range(len(arrows)):
        for j in range(i + 1, len(arrows)):
            # Shared tail = divergent
            tail_dist = math.hypot(
                arrows[i].tail[0] - arrows[j].tail[0],
                arrows[i].tail[1] - arrows[j].tail[1],
            )
            if tail_dist < proximity_threshold:
                return True
            # Shared head = convergent
            head_dist = math.hypot(
                arrows[i].head[0] - arrows[j].head[0],
                arrows[i].head[1] - arrows[j].head[1],
            )
            if head_dist < proximity_threshold:
                return True
    return False


def classify_layout(arrows: List[ArrowVector]) -> LayoutPattern:
    """Classify the scheme layout pattern from arrow geometry.

    Taxonomy (from RxnIM):
      - SINGLE_LINE:  all horizontal, single row
      - MULTI_LINE:   all horizontal, multiple rows
      - SERPENTINE:    horizontal arrows with vertical connectors between rows
      - BRANCH:       arrows share tail or head endpoints (divergent/convergent)
      - CYCLE:        arrows form a closed polygon
      - MIXED:        fallback
    """
    if not arrows:
        return LayoutPattern.SINGLE_LINE
    if len(arrows) == 1:
        return LayoutPattern.SINGLE_LINE

    horizontal = [a for a in arrows if _is_horizontal(a)]
    vertical = [a for a in arrows if _is_vertical(a)]

    # Check for cycle first (arrows closing a loop)
    if _arrows_form_cycle(arrows):
        return LayoutPattern.CYCLE

    # Check for branching (shared endpoints)
    if _arrows_share_endpoint(arrows):
        return LayoutPattern.BRANCH

    # Check for serpentine (horizontal + vertical connectors)
    if horizontal and vertical and len(horizontal) >= 2:
        rows = cluster_arrows_into_rows(horizontal)
        if len(rows) >= 2:
            return LayoutPattern.SERPENTINE

    # All horizontal — check row count
    if len(horizontal) == len(arrows):
        rows = cluster_arrows_into_rows(arrows)
        if len(rows) == 1:
            return LayoutPattern.SINGLE_LINE
        return LayoutPattern.MULTI_LINE

    # Mostly horizontal with some non-horizontal — still multi-line if clustered
    if len(horizontal) >= len(arrows) * 0.7:
        rows = cluster_arrows_into_rows(arrows)
        if len(rows) == 1:
            return LayoutPattern.SINGLE_LINE
        return LayoutPattern.MULTI_LINE

    return LayoutPattern.MIXED


# ---------------------------------------------------------------------------
# Distance scoring
# ---------------------------------------------------------------------------

# Penalty factor for parallel overshoot (fragment is past arrow tip).
# Higher values make fragments prefer arrows whose span they fall within.
_PARALLEL_OVERSHOOT_PENALTY = 0.5


def _distance_score(
    point: Tuple[float, float],
    arrow: ArrowVector,
) -> float:
    """Combined distance score from a point to an arrow.

    Score = |perpendicular| + penalty * max(0, overshoot)

    where overshoot is how far past either arrow tip the point projects.
    Lower score = stronger association.
    """
    parallel, perp = project_onto_arrow(point, arrow.tail, arrow.head)

    overshoot = 0.0
    if parallel < 0:
        overshoot = -parallel
    elif parallel > arrow.length:
        overshoot = parallel - arrow.length

    return abs(perp) + _PARALLEL_OVERSHOOT_PENALTY * overshoot


def _compute_confidence(dist_nearest: float, dist_second: float) -> float:
    """Confidence from ratio of nearest to second-nearest distances.

    Returns 1.0 when nearest is far from alternatives, ~0.5 when equidistant.
    """
    if dist_second <= 0:
        return 1.0
    total = dist_nearest + dist_second
    if total < 1e-9:
        return 0.5
    return 1.0 - (dist_nearest / total)


# ---------------------------------------------------------------------------
# Role assignment from projection
# ---------------------------------------------------------------------------

def _role_from_projection(
    parallel: float,
    perpendicular: float,
    arrow_length: float,
) -> str:
    """Determine role from arrow-relative coordinates.

    - parallel < 0 → reactant (behind tail)
    - parallel > arrow_length → product (past head)
    - 0 ≤ parallel ≤ arrow_length:
        perpendicular < 0 → above (reagent/condition)
        perpendicular ≥ 0 → below (condition/yield)
    """
    if parallel < 0:
        return "reactant"
    if parallel > arrow_length:
        return "product"
    if perpendicular < 0:
        return "above"
    return "below"


# ---------------------------------------------------------------------------
# Core assignment engine
# ---------------------------------------------------------------------------

def _assign_to_nearest_arrow(
    point: Tuple[float, float],
    arrows: List[ArrowVector],
    element_id: str,
) -> AssignmentResult:
    """Assign a point to the nearest arrow with role and confidence."""
    if len(arrows) == 1:
        arrow = arrows[0]
        par, perp = project_onto_arrow(point, arrow.tail, arrow.head)
        role = _role_from_projection(par, perp, arrow.length)
        return AssignmentResult(
            element_id=element_id,
            arrow_id=arrow.element_id,
            role=role,
            confidence=1.0,
            distance=abs(perp),
        )

    # Score against all arrows
    scores = []
    for arrow in arrows:
        score = _distance_score(point, arrow)
        scores.append((score, arrow))
    scores.sort(key=lambda s: s[0])

    best_score, best_arrow = scores[0]
    second_score = scores[1][0] if len(scores) > 1 else best_score * 10

    par, perp = project_onto_arrow(point, best_arrow.tail, best_arrow.head)
    role = _role_from_projection(par, perp, best_arrow.length)
    confidence = _compute_confidence(best_score, second_score)

    return AssignmentResult(
        element_id=element_id,
        arrow_id=best_arrow.element_id,
        role=role,
        confidence=confidence,
        distance=abs(perp),
    )


def _assign_text_to_arrow(
    text: TextInfo,
    arrows: List[ArrowVector],
    margin: float = 30.0,
    max_perp: float = ACS_BOND_LENGTH * 2.5,
) -> Optional[AssignmentResult]:
    """Assign a text element to an arrow.

    Text is only assigned if it falls within the arrow's parallel span
    (extended by *margin* on each side) AND within *max_perp* perpendicular
    distance.  This prevents distant text from being mis-assigned.
    """
    best: Optional[AssignmentResult] = None
    best_score = float("inf")

    for arrow in arrows:
        par, perp = project_onto_arrow(text.position, arrow.tail, arrow.head)

        # Check parallel range (within arrow span + margin)
        if par < -margin or par > arrow.length + margin:
            continue
        # Check perpendicular range
        if abs(perp) > max_perp:
            continue

        score = _distance_score(text.position, arrow)
        if score < best_score:
            best_score = score
            role = "above" if perp < 0 else "below"
            best = AssignmentResult(
                element_id=text.element_id,
                arrow_id=arrow.element_id,
                role=role,
                confidence=1.0,  # refined below
                distance=abs(perp),
            )

    # Compute confidence if we found a match
    if best is not None and len(arrows) > 1:
        scores_all = []
        for arrow in arrows:
            par, perp = project_onto_arrow(text.position, arrow.tail, arrow.head)
            if -margin <= par <= arrow.length + margin and abs(perp) <= max_perp:
                scores_all.append(_distance_score(text.position, arrow))
        if len(scores_all) >= 2:
            scores_all.sort()
            best.confidence = _compute_confidence(scores_all[0], scores_all[1])

    return best


# ---------------------------------------------------------------------------
# Layout-specific strategies
# ---------------------------------------------------------------------------

def _assign_single_line(
    arrows: List[ArrowVector],
    fragments: List[FragmentInfo],
    texts: List[TextInfo],
) -> Tuple[List[RawStep], List[AssignmentResult]]:
    """Assignment for single-row layouts (horizontal or any orientation)."""
    steps: List[RawStep] = []
    results: List[AssignmentResult] = []

    # Create a step per arrow
    for arrow in arrows:
        steps.append(RawStep(
            arrow_id=arrow.element_id,
            arrow_element=arrow.element,
        ))

    # Assign fragments
    for frag in fragments:
        result = _assign_to_nearest_arrow(frag.centroid, arrows, frag.element_id)
        results.append(result)
        # Find the corresponding step
        for step in steps:
            if step.arrow_id == result.arrow_id:
                if result.role == "reactant":
                    step.reactant_ids.append(frag.element_id)
                elif result.role == "product":
                    step.product_ids.append(frag.element_id)
                elif result.role == "above":
                    step.above_arrow_ids.append(frag.element_id)
                elif result.role == "below":
                    step.below_arrow_ids.append(frag.element_id)
                break

    # Assign texts
    for text in texts:
        result = _assign_text_to_arrow(text, arrows)
        if result is not None:
            results.append(result)
            for step in steps:
                if step.arrow_id == result.arrow_id:
                    if result.role == "above":
                        step.above_arrow_ids.append(text.element_id)
                    else:
                        step.below_arrow_ids.append(text.element_id)
                    break

    # Compute step-level confidence
    for step in steps:
        step_results = [r for r in results if r.arrow_id == step.arrow_id]
        if step_results:
            step.confidence = sum(r.confidence for r in step_results) / len(step_results)

    return steps, results


def _assign_multi_line(
    arrows: List[ArrowVector],
    fragments: List[FragmentInfo],
    texts: List[TextInfo],
) -> Tuple[List[RawStep], List[AssignmentResult]]:
    """Assignment for multi-row horizontal layouts.

    1. Cluster arrows into rows
    2. For each row, assign fragments/texts using proximity
    3. Link cross-row intermediates (last product row N -> first reactant row N+1)
    """
    rows = cluster_arrows_into_rows(arrows)

    all_steps: List[RawStep] = []
    all_results: List[AssignmentResult] = []

    for row_idx, row_arrows in enumerate(rows):
        # Filter fragments/texts to those closest to this row
        row_y_center = sum(a.midpoint[1] for a in row_arrows) / len(row_arrows)
        row_y_half_span = max(
            (a.length for a in row_arrows), default=ACS_BOND_LENGTH * 3
        )

        row_frags = [f for f in fragments
                     if abs(f.centroid[1] - row_y_center) < row_y_half_span]
        row_texts = [t for t in texts
                     if abs(t.position[1] - row_y_center) < row_y_half_span]

        row_steps, row_results = _assign_single_line(row_arrows, row_frags, row_texts)

        for step in row_steps:
            step.layout_row = row_idx

        all_steps.extend(row_steps)
        all_results.extend(row_results)

    # Link cross-row intermediates
    _link_cross_row_intermediates(all_steps, rows)

    return all_steps, all_results


def _assign_serpentine(
    arrows: List[ArrowVector],
    fragments: List[FragmentInfo],
    texts: List[TextInfo],
) -> Tuple[List[RawStep], List[AssignmentResult]]:
    """Assignment for serpentine layouts (horizontal arrows + vertical connectors).

    Vertical arrows are treated as connectors between rows, not as independent
    reaction steps with their own reactants/products.
    """
    horizontal = [a for a in arrows if _is_horizontal(a)]
    vertical = [a for a in arrows if _is_vertical(a)]

    # Assign using horizontal arrows only
    steps, results = _assign_multi_line(horizontal, fragments, texts)

    # Vertical arrows become connector metadata (not separate steps)
    # They link end-of-row to start-of-next-row
    rows = cluster_arrows_into_rows(horizontal)
    for vert in vertical:
        # Find which row boundary this vertical arrow bridges
        for row_idx in range(len(rows) - 1):
            row_bottom = max(a.midpoint[1] for a in rows[row_idx])
            next_row_top = min(a.midpoint[1] for a in rows[row_idx + 1])
            if row_bottom <= vert.midpoint[1] <= next_row_top:
                # This vertical arrow bridges row_idx and row_idx+1
                # Ensure the last product of row_idx is linked to first
                # reactant of row_idx+1
                break

    return steps, results


def _assign_branch(
    arrows: List[ArrowVector],
    fragments: List[FragmentInfo],
    texts: List[TextInfo],
) -> Tuple[List[RawStep], List[AssignmentResult]]:
    """Assignment for divergent/convergent branching layouts.

    Identifies shared fragments (near multiple arrow tails or heads) and
    assigns them as shared reactants (divergent) or shared products (convergent).
    """
    # Fall back to the general nearest-arrow assignment
    # The shared-endpoint logic is handled by the fact that a fragment near
    # a shared tail region will be closest to multiple arrows — we assign it
    # to all arrows that share that endpoint
    steps, results = _assign_single_line(arrows, fragments, texts)

    # Post-process: detect shared endpoints and duplicate assignments
    avg_length = sum(a.length for a in arrows) / len(arrows)
    proximity = avg_length * 0.5

    # Find arrows with shared tails (divergent)
    for i in range(len(arrows)):
        for j in range(i + 1, len(arrows)):
            tail_dist = math.hypot(
                arrows[i].tail[0] - arrows[j].tail[0],
                arrows[i].tail[1] - arrows[j].tail[1],
            )
            if tail_dist < proximity:
                # These arrows share a tail — ensure they share reactants
                step_i = next((s for s in steps if s.arrow_id == arrows[i].element_id), None)
                step_j = next((s for s in steps if s.arrow_id == arrows[j].element_id), None)
                if step_i and step_j:
                    # Share reactants between the two steps
                    shared = set(step_i.reactant_ids) | set(step_j.reactant_ids)
                    step_i.reactant_ids = list(shared)
                    step_j.reactant_ids = list(shared)

    # Find arrows with shared heads (convergent)
    for i in range(len(arrows)):
        for j in range(i + 1, len(arrows)):
            head_dist = math.hypot(
                arrows[i].head[0] - arrows[j].head[0],
                arrows[i].head[1] - arrows[j].head[1],
            )
            if head_dist < proximity:
                step_i = next((s for s in steps if s.arrow_id == arrows[i].element_id), None)
                step_j = next((s for s in steps if s.arrow_id == arrows[j].element_id), None)
                if step_i and step_j:
                    shared = set(step_i.product_ids) | set(step_j.product_ids)
                    step_i.product_ids = list(shared)
                    step_j.product_ids = list(shared)

    return steps, results


def _assign_cycle(
    arrows: List[ArrowVector],
    fragments: List[FragmentInfo],
    texts: List[TextInfo],
) -> Tuple[List[RawStep], List[AssignmentResult]]:
    """Assignment for cyclic reaction networks (catalytic cycles).

    Orders arrows around the cycle and assigns fragments between consecutive
    arrow endpoints.
    """
    # Order arrows into a cycle by chaining head -> nearest tail
    ordered = _order_arrows_cyclic(arrows)

    steps, results = _assign_single_line(ordered, fragments, texts)

    # In a cycle, the "product" of the last step should connect back to the
    # "reactant" of the first step.  We don't modify the assignment — the
    # topology detector in scheme_reader will recognize this as a cycle.

    return steps, results


def _order_arrows_cyclic(arrows: List[ArrowVector]) -> List[ArrowVector]:
    """Order arrows into a cycle by greedily chaining head_i -> nearest tail_j."""
    if len(arrows) <= 1:
        return list(arrows)

    remaining = list(arrows)
    ordered = [remaining.pop(0)]

    while remaining:
        last_head = ordered[-1].head
        # Find the arrow whose tail is closest to last_head
        best_idx = 0
        best_dist = float("inf")
        for idx, arrow in enumerate(remaining):
            dist = math.hypot(
                last_head[0] - arrow.tail[0],
                last_head[1] - arrow.tail[1],
            )
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        ordered.append(remaining.pop(best_idx))

    return ordered


# ---------------------------------------------------------------------------
# Shared intermediate handling
# ---------------------------------------------------------------------------

def _link_shared_intermediates(steps: List[RawStep]) -> None:
    """Propagate products to next step's reactants when reactants are empty.

    For sequential schemes, the product of step i is the reactant of step i+1.
    When step i+1 has no reactants, copy step i's products.
    """
    for i in range(len(steps) - 1):
        if not steps[i + 1].reactant_ids and steps[i].product_ids:
            steps[i + 1].reactant_ids = list(steps[i].product_ids)


def _link_cross_row_intermediates(
    steps: List[RawStep],
    rows: List[List[ArrowVector]],
) -> None:
    """Link the last step of row N to the first step of row N+1.

    For multi-line layouts, the last product of row N wraps to become the
    first reactant of row N+1.
    """
    if len(rows) < 2:
        _link_shared_intermediates(steps)
        return

    # Group steps by row
    row_steps: Dict[int, List[RawStep]] = {}
    for step in steps:
        row_steps.setdefault(step.layout_row, []).append(step)

    # Within each row, link shared intermediates
    for row_idx in sorted(row_steps):
        _link_shared_intermediates(row_steps[row_idx])

    # Across rows: last step of row N -> first step of row N+1
    sorted_rows = sorted(row_steps.keys())
    for i in range(len(sorted_rows) - 1):
        curr_row = row_steps[sorted_rows[i]]
        next_row = row_steps[sorted_rows[i + 1]]
        if curr_row and next_row:
            last_step = curr_row[-1]
            first_step = next_row[0]
            if last_step.product_ids and not first_step.reactant_ids:
                first_step.reactant_ids = list(last_step.product_ids)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assign_elements(
    arrows: List[ArrowVector],
    page: ET.Element,
    layout: Optional[LayoutPattern] = None,
) -> Tuple[List[RawStep], List[AssignmentResult]]:
    """Assign all fragments and texts on the page to arrows.

    This is the main entry point.  If *layout* is None, it is auto-detected.

    Returns:
      - steps: list of :class:`RawStep`, one per arrow
      - results: list of :class:`AssignmentResult`, one per assigned element
    """
    if not arrows:
        return [], []

    if layout is None:
        layout = classify_layout(arrows)

    fragments = collect_fragments(page)
    texts = collect_texts(page)

    dispatch = {
        LayoutPattern.SINGLE_LINE: _assign_single_line,
        LayoutPattern.MULTI_LINE: _assign_multi_line,
        LayoutPattern.SERPENTINE: _assign_serpentine,
        LayoutPattern.BRANCH: _assign_branch,
        LayoutPattern.CYCLE: _assign_cycle,
        LayoutPattern.MIXED: _assign_single_line,  # fallback
    }

    strategy = dispatch.get(layout, _assign_single_line)
    steps, results = strategy(arrows, fragments, texts)

    # Final pass: link shared intermediates for sequential schemes
    if layout in (LayoutPattern.SINGLE_LINE, LayoutPattern.MIXED):
        _link_shared_intermediates(steps)

    return steps, results
