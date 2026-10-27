from __future__ import annotations

import copy
import math
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import figure_mechanism
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

# Hydroxide adds to acetaldehyde: the lone pair of O attacks C, the C=O pi bond moves to O.
ADDITION = {
    "kind": "mechanism",
    "species": [
        {"id": "ald", "smiles": "CC=O", "label": "1"},
        {"id": "hyd", "smiles": "[OH-]"},
        {"id": "alk", "smiles": "CC([O-])O", "label": "2"},
    ],
    "steps": [
        {
            "substrates": ["ald", "hyd"],
            "products": ["alk"],
            "above": ["H2O"],
            "moves": [
                {"from": {"species": "hyd", "atom": 0}, "to": {"species": "ald", "atom": 1}},
                {"from": {"species": "ald", "bond": [1, 2]}, "to": {"species": "ald", "atom": 2}},
            ],
        }
    ],
}

# tert-Butyl chloride ionises, then water captures the cation: the cation is drawn once.
SN1 = {
    "kind": "mechanism",
    "species": [
        {"id": "tbuCl", "smiles": "CC(C)(C)Cl", "label": "1"},
        {"id": "cat", "smiles": "C[C+](C)C"},
        {"id": "chl", "smiles": "[Cl-]"},
        {"id": "wat", "smiles": "O"},
        {"id": "ox", "smiles": "CC(C)(C)[OH2+]", "label": "2"},
    ],
    "steps": [
        {"substrates": ["tbuCl"], "products": ["cat", "chl"], "above": ["slow"],
         "moves": [{"from": {"species": "tbuCl", "bond": [1, 4]}, "to": {"species": "tbuCl", "atom": 4}}]},
        {"substrates": ["cat", "wat"], "products": ["ox"],
         "moves": [{"from": {"species": "wat", "atom": 0}, "to": {"species": "cat", "atom": 1}}]},
    ],
}


# A cyclobutylcarbinyl cation forms, then expands to a cyclopentyl cation: each step has one substrate
# and one product, so the intermediate is drawn once between the two arrows.
CHAIN = {
    "kind": "mechanism",
    "species": [
        {"id": "open", "smiles": "C=CCC[CH2+]", "label": "1"},
        {"id": "ring4", "smiles": "[CH2+]C1CCC1"},
        {"id": "ring5", "smiles": "C1CC[CH+]C1", "label": "2"},
    ],
    "steps": [
        {"substrates": ["open"], "products": ["ring4"],
         "moves": [{"from": {"species": "open", "bond": [0, 1]}, "to": {"species": "open", "atom": 4}}]},
        {"substrates": ["ring4"], "products": ["ring5"],
         "moves": [{"from": {"species": "ring4", "bond": [1, 2]}, "to": {"species": "ring4", "atom": 0}}]},
    ],
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def _brief(base, **changes):
    brief = copy.deepcopy(base)
    brief.update(changes)
    return brief


def _draw(tmp_path, brief, **kwargs):
    return draw_figure(brief, output_path=str(tmp_path / "m.cdxml"), **kwargs)


def _root(report):
    return ET.parse(report["output_path"]).getroot()


def _fragments(root):
    """Atom positions of each drawn structure, in document order."""
    return [[tuple(map(float, n.get("p").split())) for n in f.findall("n")] for f in root.iter("fragment")]


def _rows(root):
    """Distinct vertical centres of the drawn structures, one per row."""
    return {round((min(p[1] for p in f) + max(p[1] for p in f)) / 2) for f in _fragments(root)}


def _curves(root):
    out = []
    for curve in root.iter("curve"):
        values = list(map(float, curve.get("CurvePoints").split()))
        out.append((curve, list(zip(values[0::2], values[1::2]))))
    return out


def test_a_mechanism_is_drawn_with_one_curved_arrow_per_move(tmp_path):
    report = _draw(tmp_path, ADDITION)

    assert report["ok"] is True
    assert report["kind"] == "mechanism"
    assert report["readback"]["status"] == "matched"
    assert report["checks_passed"] is True
    assert len(_curves(_root(report))) == 2
    assert [m["electrons"] for m in report["moves"]] == [2, 2]


def test_each_arrow_runs_from_its_source_atom_to_its_target_atom(tmp_path):
    report = _draw(tmp_path, ADDITION)
    root = _root(report)
    ald, hyd = _fragments(root)[0], _fragments(root)[1]
    (_, first), (_, second) = _curves(root)

    def near(point, targets, limit=14.0):
        return min(math.dist(point, t) for t in targets) <= limit

    assert near(first[0], hyd) and near(first[-1], [ald[1]])
    bond_middle = ((ald[1][0] + ald[2][0]) / 2, (ald[1][1] + ald[2][1]) / 2)
    assert near(second[0], [bond_middle], 6.0) and near(second[-1], [ald[2]])


def test_a_two_electron_arrow_has_a_full_head_and_a_one_electron_arrow_a_half_head(tmp_path):
    brief = _brief(ADDITION)
    brief["steps"][0]["moves"][0]["electrons"] = 1

    report = _draw(tmp_path, brief)
    heads = [c.get("ArrowheadHead") for c, _ in _curves(_root(report))]

    assert heads == ["HalfLeft", "Full"]


def test_an_arrow_does_not_pass_through_another_atom(tmp_path):
    report = _draw(tmp_path, ADDITION)

    assert report["arrows"]["crossings"] == []


def test_the_conditions_given_are_drawn_above_the_step_arrow(tmp_path):
    report = _draw(tmp_path, ADDITION)
    texts = ["".join(t.itertext()).strip() for t in _root(report).iter("t")]

    assert "H2O" in texts
    assert "+" in texts


def test_an_intermediate_that_feeds_the_next_step_is_drawn_once(tmp_path):
    report = _draw(tmp_path, CHAIN)
    root = _root(report)

    assert report["ok"] is True
    assert report["readback"]["status"] == "matched"
    assert len(_fragments(root)) == 3  # no species twice
    assert len(_rows(root)) == 1
    assert len(_curves(root)) == 2
    # the second arrow runs inside the middle structure
    middle = _fragments(root)[1]
    (_, _), (_, last) = _curves(root)
    assert min(math.dist(last[-1], p) for p in middle) <= 14.0


def test_a_step_with_several_substrates_starts_a_new_row_with_the_cation_drawn_again(tmp_path):
    report = _draw(tmp_path, SN1)
    root = _root(report)
    fragments = _fragments(root)

    assert report["ok"] is True
    assert len(fragments) == 6
    assert any("again" in note for note in report["notes"])
    assert report["readback"]["status"] == "matched"
    assert len(_rows(root)) == 2
    # the second arrow ends on the cation drawn in the second row
    cation_again = fragments[3]
    (_, _), (_, last) = _curves(root)
    assert min(math.dist(last[-1], p) for p in cation_again) <= 14.0


def test_a_chain_that_does_not_fit_wraps_with_the_intermediate_drawn_again(tmp_path):
    report = _draw(tmp_path, _brief(CHAIN, max_width=150))
    root = _root(report)

    assert report["ok"] is True
    assert len(_fragments(root)) == 4
    assert any("again" in note for note in report["notes"])
    assert report["readback"]["status"] == "matched"
    assert len(_rows(root)) == 2


def test_a_two_electron_arrow_from_an_atom_without_a_lone_pair_is_flagged_but_drawn(tmp_path):
    brief = _brief(ADDITION)
    brief["steps"][0]["moves"][0]["from"] = {"species": "ald", "atom": 0}  # the methyl carbon

    report = _draw(tmp_path, brief)

    assert report["ok"] is True
    assert report["moves"][0]["checks"]
    assert any("lone pair" in w for w in report["warnings"])


def test_atom_numbers_can_be_shown_on_a_draft(tmp_path):
    plain = _draw(tmp_path, ADDITION)
    numbered = draw_figure(_brief(ADDITION, show_atom_numbers=True), output_path=str(tmp_path / "n.cdxml"))

    count = lambda r: len(list(ET.parse(r["output_path"]).getroot().iter("t")))
    assert count(numbered) > count(plain)
    assert any("atom numbers" in w for w in numbered["warnings"])


def test_species_report_lists_the_atom_numbers_the_moves_refer_to(tmp_path):
    report = _draw(tmp_path, ADDITION)

    assert report["species"][0]["atoms"].startswith("0 C, 1 C, 2 O")


def test_an_unbalanced_step_is_reported_but_still_drawn(tmp_path):
    brief = _brief(ADDITION)
    brief["species"][2]["smiles"] = "CC(O)O"  # the charge is lost

    report = _draw(tmp_path, brief)

    assert report["ok"] is True
    assert any("does not balance" in w for w in report["warnings"])


def test_a_crossing_arrow_is_retried_once_and_the_change_reported(tmp_path, monkeypatch):
    real = figure_mechanism._crossings
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        found = real(*args, **kwargs)
        return found or ([{"step": 1, "move": 1, "with": "fake"}] if len(calls) == 1 else [])

    monkeypatch.setattr(figure_mechanism, "_crossings", flaky)

    report = _draw(tmp_path, ADDITION)

    assert report["arrows"]["relayout"]["changed"]
    assert report["arrows"]["crossings"] == []


def test_native_rendering_is_not_claimed_when_it_did_not_run(tmp_path):
    report = _draw(tmp_path, ADDITION)

    assert report["native"]["status"] == "not_run"


def test_a_native_render_returns_the_png(tmp_path, monkeypatch):
    def fake(cdxml_path, png_path):
        open(png_path, "wb").write(b"png")
        return png_path

    monkeypatch.setattr("cdxml_toolkit.mcp_runtime.figure_draw._render_png", fake)

    report = _draw(tmp_path, ADDITION, render=True)

    assert report["native"]["status"] == "rendered"


def test_an_existing_output_is_never_overwritten(tmp_path):
    (tmp_path / "m.cdxml").write_text("mine", encoding="utf-8")

    report = _draw(tmp_path, ADDITION)

    assert report["ok"] is False
    assert (tmp_path / "m.cdxml").read_text(encoding="utf-8") == "mine"


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda b: b["steps"][0].pop("moves"), "moves"),
        (lambda b: b["steps"][0].update(moves=[]), "moves"),
        (lambda b: b["steps"][0]["moves"][0].update(electrons=3), "electrons"),
        (lambda b: b["steps"][0]["moves"][0]["to"].update(species="alk"), "substrates"),
        (lambda b: b["steps"][0]["moves"][0]["to"].update(species="nope"), "nope"),
        (lambda b: b["steps"][0]["moves"][0]["to"].update(atom=9), "atom 9"),
        (lambda b: b["steps"][0]["moves"][1]["from"].update(bond=[0, 2]), "bond"),
        (lambda b: b["steps"][0]["moves"][0]["from"].update(bond=[0, 1]), "exactly one"),
        (lambda b: b["steps"][0]["moves"][0].update(extra=1), "unknown"),
        (lambda b: b.update(surprise=1), "Unknown brief keys"),
        (lambda b: b["steps"][0].update(arrow="dashed"), "arrow"),
        (lambda b: b["species"][0].update(smiles=None), "smiles or a name"),
    ],
)
def test_a_malformed_mechanism_is_refused_with_a_reason(tmp_path, change, message):
    brief = copy.deepcopy(ADDITION)
    change(brief)

    report = _draw(tmp_path, brief)

    assert report["ok"] is False
    assert message in " ".join(report["errors"])
    assert not (tmp_path / "m.cdxml").exists()


def test_a_species_produced_twice_is_refused(tmp_path):
    brief = copy.deepcopy(SN1)
    brief["steps"][1]["products"] = ["cat"]

    report = _draw(tmp_path, brief)

    assert report["ok"] is False
    assert "cat" in " ".join(report["errors"])


def test_an_unresolved_name_stops_the_run(tmp_path):
    brief = copy.deepcopy(ADDITION)
    brief["species"][1] = {"id": "hyd", "name": "no-such-compound-zzz"}

    report = _draw(tmp_path, brief)

    assert report["ok"] is False
    assert "no-such-compound-zzz" in " ".join(report["errors"])


def test_the_validator_names_the_mechanism_keys():
    assert {"show_atom_numbers", "steps", "species"} <= figure_mechanism.MECH_KEYS
