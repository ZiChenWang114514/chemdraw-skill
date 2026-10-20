"""Tests for cdxml_toolkit.spatial_assignment — geometry-first scheme parsing.

Uses synthetic CDXML via ET.fromstring() — no filesystem fixtures needed.
Tests all four RxnIM layout patterns (single-line, multi-line, branch, cycle)
plus edge cases (vertical arrows, angled arrows, confidence scoring).
"""

import math
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.perception.spatial_assignment import (
    ArrowVector,
    AssignmentResult,
    FragmentInfo,
    LayoutPattern,
    RawStep,
    TextInfo,
    assign_elements,
    build_arrow_vector,
    build_arrow_vectors,
    classify_layout,
    cluster_arrows_into_rows,
    collect_fragments,
    collect_texts,
    project_onto_arrow,
    point_to_segment_distance,
    _assign_single_line,
    _assign_multi_line,
    _assign_branch,
    _assign_cycle,
    _is_horizontal,
    _is_vertical,
    _distance_score,
    _compute_confidence,
    _role_from_projection,
)


# ---------------------------------------------------------------------------
# Helpers: build synthetic CDXML pages
# ---------------------------------------------------------------------------

def _make_arrow(arrow_id, tail_x, tail_y, head_x, head_y):
    """Build a minimal CDXML <arrow> element string."""
    return (
        f'<arrow id="{arrow_id}" '
        f'Tail3D="{tail_x} {tail_y} 0" '
        f'Head3D="{head_x} {head_y} 0" />'
    )


def _make_fragment(frag_id, atoms):
    """Build a minimal CDXML <fragment> with atoms at given positions.

    atoms: list of (atom_id, x, y)
    """
    atom_strs = "\n".join(
        f'  <n id="{aid}" p="{x} {y}" />' for aid, x, y in atoms
    )
    return f'<fragment id="{frag_id}">\n{atom_strs}\n</fragment>'


def _make_text(text_id, x, y, content="reagent"):
    """Build a minimal CDXML <t> element."""
    return (
        f'<t id="{text_id}" p="{x} {y}">'
        f'<s>{content}</s></t>'
    )


def _make_page(*elements):
    """Wrap elements into a <page> element."""
    inner = "\n".join(elements)
    return ET.fromstring(f"<page>\n{inner}\n</page>")


# ---------------------------------------------------------------------------
# Projection primitives
# ---------------------------------------------------------------------------

class TestProjectOntoArrow:

    def test_horizontal_ltr_behind_tail(self):
        """Point behind the tail of a horizontal L->R arrow."""
        par, perp = project_onto_arrow((100, 200), (200, 200), (400, 200))
        assert par < 0  # behind tail
        assert abs(perp) < 1e-6  # on the axis

    def test_horizontal_ltr_past_head(self):
        """Point past the head of a horizontal L->R arrow."""
        par, perp = project_onto_arrow((500, 200), (200, 200), (400, 200))
        assert par > 200  # past head (arrow length = 200)

    def test_horizontal_ltr_above(self):
        """Point above a horizontal L->R arrow (smaller y = above in CDXML)."""
        par, perp = project_onto_arrow((300, 150), (200, 200), (400, 200))
        assert 0 < par < 200  # within arrow span
        assert perp < 0  # above (negative perpendicular)

    def test_horizontal_ltr_below(self):
        """Point below a horizontal L->R arrow (larger y = below in CDXML)."""
        par, perp = project_onto_arrow((300, 250), (200, 200), (400, 200))
        assert 0 < par < 200
        assert perp > 0  # below

    def test_vertical_down_arrow(self):
        """Vertical downward arrow: 'above' = left side in screen coords."""
        # Arrow pointing straight down: tail at (200, 100), head at (200, 300)
        par, perp = project_onto_arrow((200, 50), (200, 100), (200, 300))
        assert par < 0  # behind tail (above the arrow)
        assert abs(perp) < 1e-6  # on the axis

    def test_vertical_down_product(self):
        """Point below a downward arrow = product (past head)."""
        par, perp = project_onto_arrow((200, 350), (200, 100), (200, 300))
        assert par > 200  # past head

    def test_45_degree_arrow(self):
        """Point on the axis of a 45-degree arrow."""
        # Arrow from (0, 0) to (100, 100)
        par, perp = project_onto_arrow((50, 50), (0, 0), (100, 100))
        assert abs(perp) < 1e-6  # on the axis
        expected_par = 50 * math.sqrt(2)
        assert abs(par - expected_par) < 1e-6

    def test_degenerate_zero_length(self):
        """Zero-length arrow returns distance from tail."""
        par, perp = project_onto_arrow((10, 0), (0, 0), (0, 0))
        assert par == 0.0
        assert abs(perp - 10.0) < 1e-6


class TestPointToSegmentDistance:

    def test_perpendicular_to_midpoint(self):
        """Point directly above the midpoint of a segment."""
        dist = point_to_segment_distance((5, 0), (0, 5), (10, 5))
        assert abs(dist - 5.0) < 1e-6

    def test_closest_to_endpoint(self):
        """Point closest to one endpoint of the segment."""
        dist = point_to_segment_distance((0, 0), (10, 0), (20, 0))
        assert abs(dist - 10.0) < 1e-6


# ---------------------------------------------------------------------------
# Arrow vector construction
# ---------------------------------------------------------------------------

class TestBuildArrowVector:

    def test_horizontal_arrow(self):
        xml = '<arrow id="1" Tail3D="100 200 0" Head3D="300 200 0" />'
        el = ET.fromstring(xml)
        av = build_arrow_vector(el)
        assert av.element_id == "1"
        assert av.tail == (100.0, 200.0)
        assert av.head == (300.0, 200.0)
        assert abs(av.length - 200.0) < 1e-6
        assert abs(av.angle_deg) < 1e-6 or abs(av.angle_deg - 360) < 1e-6
        assert av.arrow_type == "solid"

    def test_vertical_down_arrow(self):
        xml = '<arrow id="2" Tail3D="200 100 0" Head3D="200 300 0" />'
        av = build_arrow_vector(ET.fromstring(xml))
        assert abs(av.angle_deg - 90.0) < 1e-6

    def test_failed_arrow(self):
        xml = '<arrow id="3" Tail3D="0 0 0" Head3D="100 0 0" NoGo="Cross" />'
        av = build_arrow_vector(ET.fromstring(xml))
        assert av.arrow_type == "failed"

    def test_dashed_arrow(self):
        xml = '<arrow id="4" Tail3D="0 0 0" Head3D="100 0 0" LineType="dashed" />'
        av = build_arrow_vector(ET.fromstring(xml))
        assert av.arrow_type == "dashed"

    def test_normal_vector_horizontal(self):
        """Normal of a rightward arrow points downward (positive y).

        Convention: perpendicular < 0 = "above", > 0 = "below".
        For a rightward arrow, the normal (0, 1) points downward so that
        a point with smaller y (above) yields a negative perpendicular.
        """
        xml = '<arrow id="5" Tail3D="0 200 0" Head3D="100 200 0" />'
        av = build_arrow_vector(ET.fromstring(xml))
        # Normal should be approximately (0, 1) — pointing downward
        assert abs(av.normal[0]) < 1e-6
        assert av.normal[1] > 0


class TestIsHorizontalVertical:

    def test_horizontal(self):
        xml = '<arrow id="1" Tail3D="0 200 0" Head3D="100 200 0" />'
        av = build_arrow_vector(ET.fromstring(xml))
        assert _is_horizontal(av)
        assert not _is_vertical(av)

    def test_vertical(self):
        xml = '<arrow id="1" Tail3D="200 0 0" Head3D="200 100 0" />'
        av = build_arrow_vector(ET.fromstring(xml))
        assert _is_vertical(av)
        assert not _is_horizontal(av)

    def test_diagonal_neither(self):
        xml = '<arrow id="1" Tail3D="0 0 0" Head3D="100 100 0" />'
        av = build_arrow_vector(ET.fromstring(xml))
        assert not _is_horizontal(av)
        assert not _is_vertical(av)


# ---------------------------------------------------------------------------
# Layout classification
# ---------------------------------------------------------------------------

class TestClassifyLayout:

    def test_single_horizontal_arrow(self):
        page = _make_page(_make_arrow("1", 100, 200, 300, 200))
        arrows = build_arrow_vectors(page)
        assert classify_layout(arrows) == LayoutPattern.SINGLE_LINE

    def test_two_horizontal_same_row(self):
        """Two arrows in the same row = single line."""
        page = _make_page(
            _make_arrow("1", 100, 200, 200, 200),
            _make_arrow("2", 300, 200, 400, 200),
        )
        arrows = build_arrow_vectors(page)
        assert classify_layout(arrows) == LayoutPattern.SINGLE_LINE

    def test_two_horizontal_different_rows(self):
        """Two arrows in different rows = multi-line."""
        page = _make_page(
            _make_arrow("1", 100, 100, 300, 100),
            _make_arrow("2", 100, 300, 300, 300),
        )
        arrows = build_arrow_vectors(page)
        assert classify_layout(arrows) == LayoutPattern.MULTI_LINE

    def test_serpentine(self):
        """Horizontal arrows + vertical connector = serpentine."""
        page = _make_page(
            _make_arrow("1", 100, 100, 300, 100),  # row 1
            _make_arrow("v", 350, 100, 350, 300),   # vertical connector
            _make_arrow("2", 300, 300, 100, 300),   # row 2 (R->L)
        )
        arrows = build_arrow_vectors(page)
        layout = classify_layout(arrows)
        assert layout == LayoutPattern.SERPENTINE

    def test_branch_shared_tail(self):
        """Two arrows from the same point = branch (divergent)."""
        page = _make_page(
            _make_arrow("1", 200, 200, 400, 100),
            _make_arrow("2", 200, 200, 400, 300),
        )
        arrows = build_arrow_vectors(page)
        assert classify_layout(arrows) == LayoutPattern.BRANCH

    def test_cycle_triangle(self):
        """Three arrows forming a triangle = cycle."""
        # Arrow 1: left -> right
        # Arrow 2: right -> bottom
        # Arrow 3: bottom -> left
        page = _make_page(
            _make_arrow("1", 100, 100, 300, 100),
            _make_arrow("2", 300, 100, 200, 300),
            _make_arrow("3", 200, 300, 100, 100),
        )
        arrows = build_arrow_vectors(page)
        assert classify_layout(arrows) == LayoutPattern.CYCLE


# ---------------------------------------------------------------------------
# Row clustering
# ---------------------------------------------------------------------------

class TestClusterArrowsIntoRows:

    def test_single_row(self):
        page = _make_page(
            _make_arrow("1", 100, 200, 200, 200),
            _make_arrow("2", 300, 200, 400, 200),
        )
        arrows = build_arrow_vectors(page)
        rows = cluster_arrows_into_rows(arrows)
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_two_rows(self):
        page = _make_page(
            _make_arrow("1", 100, 100, 200, 100),
            _make_arrow("2", 100, 400, 200, 400),
        )
        arrows = build_arrow_vectors(page)
        rows = cluster_arrows_into_rows(arrows)
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------

class TestRoleFromProjection:

    def test_reactant(self):
        assert _role_from_projection(-50, 0, 200) == "reactant"

    def test_product(self):
        assert _role_from_projection(250, 0, 200) == "product"

    def test_above(self):
        assert _role_from_projection(100, -30, 200) == "above"

    def test_below(self):
        assert _role_from_projection(100, 30, 200) == "below"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidence:

    def test_high_confidence(self):
        """Fragment very close to one arrow, far from others."""
        conf = _compute_confidence(10.0, 200.0)
        assert conf > 0.8

    def test_low_confidence_equidistant(self):
        """Fragment equidistant between two arrows."""
        conf = _compute_confidence(50.0, 50.0)
        assert abs(conf - 0.5) < 0.01

    def test_single_arrow(self):
        """Only one arrow => confidence 1.0."""
        conf = _compute_confidence(10.0, 0.0)
        assert conf == 1.0


# ---------------------------------------------------------------------------
# Full assignment: single-line
# ---------------------------------------------------------------------------

class TestAssignSingleLine:

    def test_simple_ltr(self):
        """A → B: one arrow, reactant left, product right."""
        page = _make_page(
            _make_arrow("a1", 200, 200, 400, 200),
            _make_fragment("f1", [("n1", 100, 200)]),       # reactant (left)
            _make_fragment("f2", [("n2", 500, 200)]),       # product (right)
            _make_text("t1", 300, 170, "Pd(PPh3)4"),        # above arrow
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert len(steps) == 1
        step = steps[0]
        assert "f1" in step.reactant_ids
        assert "f2" in step.product_ids
        assert "t1" in step.above_arrow_ids

    def test_two_step_sequential(self):
        """A → B → C: two arrows in a row."""
        page = _make_page(
            _make_arrow("a1", 200, 200, 300, 200),
            _make_arrow("a2", 400, 200, 500, 200),
            _make_fragment("f1", [("n1", 100, 200)]),       # reactant of step 1
            _make_fragment("f2", [("n2", 350, 200)]),       # product of 1 / reactant of 2
            _make_fragment("f3", [("n3", 600, 200)]),       # product of step 2
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert len(steps) == 2
        assert "f1" in steps[0].reactant_ids
        assert "f2" in steps[0].product_ids or "f2" in steps[1].reactant_ids
        assert "f3" in steps[1].product_ids


class TestAssignVerticalArrow:

    def test_vertical_down(self):
        """Vertical downward arrow: reactant above, product below."""
        page = _make_page(
            _make_arrow("a1", 200, 100, 200, 300),
            _make_fragment("f1", [("n1", 200, 50)]),        # reactant (above tail)
            _make_fragment("f2", [("n2", 200, 350)]),       # product (below head)
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert len(steps) == 1
        assert "f1" in steps[0].reactant_ids
        assert "f2" in steps[0].product_ids


class TestAssignAngled:

    def test_45_degree(self):
        """45-degree arrow: reactant behind tail, product past head."""
        page = _make_page(
            _make_arrow("a1", 100, 100, 300, 300),
            # Behind tail: point up-left of tail
            _make_fragment("f1", [("n1", 30, 30)]),
            # Past head: point down-right of head
            _make_fragment("f2", [("n2", 370, 370)]),
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert len(steps) == 1
        assert "f1" in steps[0].reactant_ids
        assert "f2" in steps[0].product_ids


# ---------------------------------------------------------------------------
# Full assignment: multi-line
# ---------------------------------------------------------------------------

class TestAssignMultiLine:

    def test_two_row_wrap(self):
        """Two-row scheme with intermediates linking."""
        page = _make_page(
            # Row 1: arrows at y=100
            _make_arrow("a1", 100, 100, 200, 100),
            _make_arrow("a2", 300, 100, 400, 100),
            # Row 2: arrows at y=400
            _make_arrow("a3", 100, 400, 200, 400),
            # Fragments
            _make_fragment("f1", [("n1", 50, 100)]),        # reactant row 1
            _make_fragment("f2", [("n2", 250, 100)]),       # intermediate
            _make_fragment("f3", [("n3", 450, 100)]),       # end of row 1
            _make_fragment("f4", [("n4", 50, 400)]),        # start of row 2
            _make_fragment("f5", [("n5", 250, 400)]),       # product row 2
        )

        arrows = build_arrow_vectors(page)
        layout = classify_layout(arrows)
        assert layout == LayoutPattern.MULTI_LINE

        steps, results = assign_elements(arrows, page, layout)
        assert len(steps) == 3


# ---------------------------------------------------------------------------
# Full assignment: branch
# ---------------------------------------------------------------------------

class TestAssignBranch:

    def test_divergent(self):
        """One reactant, two arrows going to different products."""
        page = _make_page(
            _make_arrow("a1", 200, 200, 400, 100),
            _make_arrow("a2", 200, 200, 400, 300),
            _make_fragment("f1", [("n1", 100, 200)]),       # shared reactant
            _make_fragment("f2", [("n2", 500, 100)]),       # product 1
            _make_fragment("f3", [("n3", 500, 300)]),       # product 2
        )

        arrows = build_arrow_vectors(page)
        layout = classify_layout(arrows)
        assert layout == LayoutPattern.BRANCH

        steps, results = assign_elements(arrows, page, layout)
        assert len(steps) == 2
        # Both steps should share the reactant
        assert "f1" in steps[0].reactant_ids or "f1" in steps[1].reactant_ids


# ---------------------------------------------------------------------------
# Full assignment: cycle
# ---------------------------------------------------------------------------

class TestAssignCycle:

    def test_triangle_cycle(self):
        """Three arrows forming a triangle with fragments between them."""
        page = _make_page(
            _make_arrow("a1", 100, 100, 300, 100),   # top: L -> R
            _make_arrow("a2", 300, 100, 200, 300),   # right: top -> bottom
            _make_arrow("a3", 200, 300, 100, 100),   # left: bottom -> top
            _make_fragment("f1", [("n1", 200, 70)]),   # top (between a1 head/tail)
            _make_fragment("f2", [("n2", 280, 200)]),  # right
            _make_fragment("f3", [("n3", 120, 230)]),  # left
        )

        arrows = build_arrow_vectors(page)
        layout = classify_layout(arrows)
        assert layout == LayoutPattern.CYCLE

        steps, results = assign_elements(arrows, page, layout)
        assert len(steps) == 3


# ---------------------------------------------------------------------------
# Topology detection (cycle)
# ---------------------------------------------------------------------------

class TestTopologyCycle:

    def test_cycle_detected(self):
        """_detect_topology recognises a cycle."""
        from cdxml_toolkit.perception.scheme_reader import _detect_topology, StepRecord
        steps = [
            StepRecord(step_index=0, reactant_ids=["a"], product_ids=["b"]),
            StepRecord(step_index=1, reactant_ids=["b"], product_ids=["c"]),
            StepRecord(step_index=2, reactant_ids=["c"], product_ids=["a"]),
        ]
        assert _detect_topology(steps) == "cycle"

    def test_linear_not_cycle(self):
        from cdxml_toolkit.perception.scheme_reader import _detect_topology, StepRecord
        steps = [
            StepRecord(step_index=0, reactant_ids=["a"], product_ids=["b"]),
            StepRecord(step_index=1, reactant_ids=["b"], product_ids=["c"]),
        ]
        assert _detect_topology(steps) == "linear"


# ---------------------------------------------------------------------------
# Text assignment
# ---------------------------------------------------------------------------

class TestTextAssignment:

    def test_text_above_arrow(self):
        """Text above an arrow is assigned as 'above'."""
        page = _make_page(
            _make_arrow("a1", 200, 200, 400, 200),
            _make_text("t1", 300, 170, "Cs2CO3"),
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert len(steps) == 1
        assert "t1" in steps[0].above_arrow_ids

    def test_text_below_arrow(self):
        """Text below an arrow is assigned as 'below'."""
        page = _make_page(
            _make_arrow("a1", 200, 200, 400, 200),
            _make_text("t1", 300, 230, "rt, 2h"),
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert len(steps) == 1
        assert "t1" in steps[0].below_arrow_ids

    def test_text_far_from_arrow_not_assigned(self):
        """Text far from any arrow is not assigned."""
        page = _make_page(
            _make_arrow("a1", 200, 200, 400, 200),
            _make_text("t1", 300, 500, "unrelated note"),  # 300pt below arrow
        )

        arrows = build_arrow_vectors(page)
        steps, results = assign_elements(arrows, page)

        assert "t1" not in steps[0].above_arrow_ids
        assert "t1" not in steps[0].below_arrow_ids


# ---------------------------------------------------------------------------
# Collect helpers
# ---------------------------------------------------------------------------

class TestCollect:

    def test_collect_fragments(self):
        page = _make_page(
            _make_fragment("f1", [("n1", 100, 200), ("n2", 120, 200)]),
        )
        frags = collect_fragments(page)
        assert len(frags) == 1
        assert frags[0].element_id == "f1"
        assert frags[0].centroid == (110.0, 200.0)

    def test_collect_texts(self):
        page = _make_page(
            _make_text("t1", 100, 200, "NaOH"),
        )
        texts = collect_texts(page)
        assert len(texts) == 1
        assert texts[0].element_id == "t1"
        assert texts[0].position == (100.0, 200.0)

    def test_collect_arrows(self):
        page = _make_page(
            _make_arrow("a1", 100, 200, 300, 200),
        )
        arrows = build_arrow_vectors(page)
        assert len(arrows) == 1
        assert arrows[0].element_id == "a1"
