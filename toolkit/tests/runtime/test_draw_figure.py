from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import figure_draw
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

ASPIRIN = {
    "species": [
        {"id": "SA", "smiles": "OC(=O)c1ccccc1O", "label": "1"},
        {"id": "Ac2O", "smiles": "CC(=O)OC(C)=O"},
        {"id": "ASP", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "label": "2"},
    ],
    "steps": [
        {
            "substrates": ["SA", "Ac2O"],
            "products": ["ASP"],
            "above": ["H2SO4 (cat.)"],
            "below": ["RT, 2 hrs"],
            "yield": "85%",
        }
    ],
}

ROUTE = {
    "species": [
        {"id": "A", "smiles": "c1ccccc1C(=O)O", "label": "1"},
        {"id": "B", "smiles": "c1ccccc1C(=O)OC", "label": "2"},
        {"id": "C", "smiles": "c1ccccc1C(=O)N", "label": "3"},
        {"id": "D", "smiles": "c1ccccc1C#N", "label": "4"},
        {"id": "E", "smiles": "c1ccccc1C", "label": "5"},
    ],
    "steps": [
        {"substrates": ["A"], "products": ["B"], "above": ["MeOH, H2SO4"]},
        {"substrates": ["B"], "products": ["C"], "above": ["NH3, MeOH"]},
        {"substrates": ["C"], "products": ["D"], "above": ["POCl3, 80 C"]},
        {"substrates": ["D"], "products": ["E"], "above": ["H2, Pd/C"]},
    ],
}


CONVERGENT = {
    "species": [
        {"id": "A", "smiles": "OC(=O)c1ccccc1", "label": "1"},
        {"id": "B", "smiles": "ClC(=O)c1ccccc1", "label": "2"},
        {"id": "C", "smiles": "Nc1ccccc1", "label": "3"},
        {"id": "D", "smiles": "Cc1ccc(N)cc1", "label": "4"},
        {"id": "E", "smiles": "O=C(Nc1ccc(C)cc1)c1ccccc1", "label": "5"},
    ],
    "steps": [
        {"substrates": ["A"], "products": ["B"], "above": ["SOCl2"]},
        {"substrates": ["C"], "products": ["D"], "above": ["MeBr"]},
        {"substrates": ["B", "D"], "products": ["E"], "above": ["Et3N, DCM"], "yield": "81%"},
    ],
}

DIVERGENT = {
    "species": [
        {"id": "A", "smiles": "OC(=O)c1ccccc1", "label": "1"},
        {"id": "B", "smiles": "COC(=O)c1ccccc1", "label": "2"},
        {"id": "C", "smiles": "NC(=O)c1ccccc1", "label": "3"},
    ],
    "steps": [
        {"substrates": ["A"], "products": ["B"], "above": ["MeOH, H2SO4"]},
        {"substrates": ["A"], "products": ["C"], "above": ["SOCl2; NH3"]},
    ],
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def _brief(source, **changes):
    brief = copy.deepcopy(source)
    brief.update(changes)
    return brief


def _cdxml(report):
    text = open(report["output_path"], encoding="utf-8").read()
    return ET.fromstring(text[text.index("<CDXML"):])


def test_a_one_step_brief_draws_a_checked_file(tmp_path):
    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "aspirin.cdxml"))

    assert report["ok"] is True
    assert (tmp_path / "aspirin.cdxml").is_file()
    assert report["lint"]["issues"] == []
    assert report["readback"]["status"] == "matched"
    assert [s["id"] for s in report["species"]] == ["SA", "Ac2O", "ASP"]
    assert {s["source"] for s in report["species"]} == {"user"}


def test_conditions_are_normalised_and_nothing_is_added(tmp_path):
    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "aspirin.cdxml"))

    text = " ".join("".join(t.itertext()) for t in _cdxml(report).iter("t"))
    assert "rt, 2 h" in text
    assert "85%" in text
    assert "hrs" not in text


def test_the_brief_may_be_json_text(tmp_path):
    report = draw_figure(json.dumps(ASPIRIN), output_path=str(tmp_path / "aspirin.cdxml"))

    assert report["ok"] is True


def test_a_known_name_is_resolved_from_the_curated_table(tmp_path):
    brief = _brief(ASPIRIN)
    brief["species"][1] = {"id": "Ac2O", "name": "Ac2O"}

    report = draw_figure(brief, output_path=str(tmp_path / "aspirin.cdxml"))

    assert report["ok"] is True
    reagent = next(s for s in report["species"] if s["id"] == "Ac2O")
    assert reagent["source"] != "user"
    assert reagent["smiles"]


def test_an_unresolved_name_stops_the_run_and_writes_nothing(tmp_path):
    brief = _brief(ASPIRIN)
    brief["species"][0] = {"id": "SA", "name": "zzz-not-a-real-compound"}

    report = draw_figure(brief, output_path=str(tmp_path / "out.cdxml"))

    assert report["ok"] is False
    assert "SA" in report["errors"][0]
    assert not (tmp_path / "out.cdxml").exists()


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda b: b.pop("steps"), "steps"),
        (lambda b: b["steps"][0].update(products=["nope"]), "nope"),
        (lambda b: b["species"].append({"id": "SA", "smiles": "C"}), "duplicate"),
        (lambda b: b["species"][0].update(smiles=None), "smiles or a name"),
        (lambda b: b.update(kind="bogus"), "bogus"),
    ],
)
def test_a_bad_brief_is_returned_as_errors_and_never_guessed(tmp_path, mutate, fragment):
    brief = copy.deepcopy(ASPIRIN)
    mutate(brief)

    report = draw_figure(brief, output_path=str(tmp_path / "out.cdxml"))

    assert report["ok"] is False
    assert fragment in " ".join(report["errors"])
    assert not (tmp_path / "out.cdxml").exists()


def test_an_unbalanced_step_is_reported_but_still_drawn(tmp_path):
    brief = {
        "species": [
            {"id": "A", "smiles": "OC(=O)c1ccccc1"},
            {"id": "B", "smiles": "COC(=O)c1ccccc1"},
        ],
        "steps": [{"substrates": ["A"], "products": ["B"]}],
    }

    report = draw_figure(brief, output_path=str(tmp_path / "out.cdxml"))

    assert report["ok"] is True
    assert report["steps"][0]["balanced"] is False
    assert any("balance" in w.lower() for w in report["warnings"])


def test_a_missing_by_product_is_named_not_drawn(tmp_path):
    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"))

    # Salicylic acid + Ac2O gives aspirin and acetic acid.
    assert report["steps"][0]["balanced"] is False
    assert report["steps"][0]["missing"] == {"side": "products", "formula": "C2H4O2",
                                             "name": "acetic acid"}


def test_missing_conditions_stay_blank_with_a_note(tmp_path):
    brief = _brief(ROUTE)
    brief["steps"][1].pop("above")
    report = draw_figure(brief, output_path=str(tmp_path / "route2.cdxml"))
    assert any("step 2" in n and "no conditions" in n for n in report["notes"])


def test_a_long_route_is_wrapped_to_the_width_budget(tmp_path):
    report = draw_figure(
        _brief(ROUTE, max_width=420), output_path=str(tmp_path / "route.cdxml")
    )

    assert report["ok"] is True
    assert report["lint"]["issues"] == []
    arrows = {round(float(a.get("Tail3D").split()[1])) for a in _cdxml(report).iter("arrow")}
    assert len(arrows) > 1


def test_the_route_shape_is_reported(tmp_path):
    assert draw_figure(ASPIRIN, output_path=str(tmp_path / "a.cdxml"))["layout"] == "linear"
    assert draw_figure(ROUTE, output_path=str(tmp_path / "b.cdxml"))["layout"] == "sequential"


def test_two_arms_that_merge_are_drawn_as_a_convergent_route(tmp_path):
    report = draw_figure(CONVERGENT, output_path=str(tmp_path / "c.cdxml"))

    assert report["ok"] is True
    assert report["layout"] == "convergent"
    assert report["readback"]["status"] == "matched"
    assert report["checks_passed"] is True
    rows = {round(float(a.get("Tail3D").split()[1])) for a in _cdxml(report).iter("arrow")}
    assert len(rows) == 3


def test_one_starting_material_with_several_products_is_drawn_as_a_divergent_scheme(tmp_path):
    report = draw_figure(DIVERGENT, output_path=str(tmp_path / "d.cdxml"))

    assert report["ok"] is True
    assert report["layout"] == "divergent"
    assert report["readback"]["status"] == "matched"
    assert report["lint"]["issues"] == []


def test_steps_given_out_of_order_are_drawn_in_route_order(tmp_path):
    brief = _brief(ROUTE)
    brief["steps"] = list(reversed(brief["steps"]))

    report = draw_figure(brief, output_path=str(tmp_path / "r.cdxml"))

    assert report["ok"] is True
    assert report["readback"]["status"] == "matched"
    first_x = {a.get("Tail3D").split()[0] for a in _cdxml(report).iter("arrow")}
    assert first_x  # drawn
    text = [" ".join("".join(t.itertext()).split()) for t in _cdxml(report).iter("t")]
    assert text.index("MeOH, H2SO4") < text.index("H2, Pd/C")


def test_a_route_that_fits_no_layout_is_refused_not_approximated(tmp_path):
    brief = _brief(ROUTE)
    brief["steps"] = [brief["steps"][0], brief["steps"][2]]  # A->B and C->D are unconnected

    report = draw_figure(brief, output_path=str(tmp_path / "x.cdxml"))

    assert report["ok"] is False
    assert "not a linear route" in " ".join(report["errors"])
    assert not (tmp_path / "x.cdxml").exists()


@pytest.mark.parametrize("arrow, head", [("reversible", "HalfLeft"), ("resonance", "Full")])
def test_reversible_and_resonance_arrows_can_be_asked_for(tmp_path, arrow, head):
    brief = {
        "species": [{"id": "A", "smiles": "CC(C)=O"}, {"id": "B", "smiles": "C=C(C)O"}],
        "steps": [{"substrates": ["A"], "products": ["B"], "arrow": arrow}],
    }

    report = draw_figure(brief, output_path=str(tmp_path / "t.cdxml"))

    (drawn,) = _cdxml(report).iter("arrow")
    assert drawn.get("ArrowheadTail") == head


def test_a_wrapped_route_keeps_every_structure_verified(tmp_path):
    report = draw_figure(_brief(ROUTE, max_width=420), output_path=str(tmp_path / "route.cdxml"))

    assert report["readback"]["fragment_roundtrip"] == "preserved"
    assert report["checks_passed"] is True


def test_unverified_structures_do_not_count_as_passed(tmp_path, monkeypatch):
    real = figure_draw.renderer.render

    def unverified(scheme, *args, **kwargs):
        result = real(scheme, *args, **kwargs)
        result.chemistry_validation = {"status": "unverified", "fragments": []}
        return result

    monkeypatch.setattr(figure_draw.renderer, "render", unverified)

    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"))

    assert report["checks_passed"] is False
    assert any("unverified" in w for w in report["warnings"])


def test_a_failed_check_triggers_one_relayout_and_says_what_changed(tmp_path, monkeypatch):
    real = figure_draw.figure_lint.lint_cdxml
    calls = []

    def flaky(text, max_width=None):
        calls.append(max_width)
        if len(calls) == 1:
            return [{"kind": "overlap", "ids": ["1", "2"], "message": "fake overlap"}]
        return real(text, max_width=max_width)

    monkeypatch.setattr(figure_draw.figure_lint, "lint_cdxml", flaky)

    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"))

    assert len(calls) == 2
    assert report["lint"]["relayout"]["changed"]
    assert report["lint"]["relayout"]["first_issues"][0]["message"] == "fake overlap"
    assert report["lint"]["issues"] == []
    assert report["ok"] is True


def test_a_width_that_cannot_be_met_is_judged_against_the_requested_budget(tmp_path):
    # One reaction cannot wrap: the relayout narrows the layout budget, but the
    # report must keep measuring against what the user asked for.
    report = draw_figure(_brief(ASPIRIN, max_width=250), output_path=str(tmp_path / "out.cdxml"))

    assert report["checks_passed"] is False
    assert report["lint"]["relayout"]["changed"]
    remaining = [i for i in report["lint"]["issues"] if i["kind"] == "too_wide"]
    assert remaining and remaining[0]["budget"] == 250
    assert report["lint"]["max_width"] == 250


def test_a_long_condition_line_is_broken_at_its_commas_to_fit(tmp_path):
    line = "N2H4·H2O, KOH, diethylene glycol, 200 °C, 6 h, then aqueous workup"
    brief = _brief(ASPIRIN)
    brief["steps"][0]["above"] = [line]
    report = draw_figure(brief, output_path=str(tmp_path / "out.cdxml"))

    assert [i for i in report["lint"]["issues"] if i["kind"] == "too_wide"] == []
    assert any("line" in change for change in report["lint"]["relayout"]["changed"])
    drawn = " ".join(" ".join("".join(t.itertext()).split()) for t in _cdxml(report).iter("t"))
    # Every part of the conditions is still drawn, in order; only the line breaks changed.
    parts = [part.strip() for part in line.split(",")]
    positions = [drawn.find(part) for part in parts]
    assert -1 not in positions and positions == sorted(positions), (parts, drawn)


def test_remaining_issues_after_the_relayout_are_reported_not_hidden(tmp_path, monkeypatch):
    issue = {"kind": "overlap", "ids": ["1", "2"], "message": "still overlapping"}
    monkeypatch.setattr(figure_draw.figure_lint, "lint_cdxml", lambda text, max_width=None: [issue])

    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"))

    assert report["ok"] is True
    assert report["lint"]["issues"] == [issue]
    assert any("still overlapping" in w for w in report["warnings"])


def test_the_readback_catches_a_missing_structure(tmp_path, monkeypatch):
    real = figure_draw.document_inventory

    def lossy(path):
        inventory = real(path)
        inventory.pop(next(iter(inventory)))
        return inventory

    monkeypatch.setattr(figure_draw, "document_inventory", lossy)

    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"))

    assert report["readback"]["status"] == "mismatch"
    assert report["readback"]["missing"]


def test_an_existing_output_is_never_overwritten(tmp_path):
    target = tmp_path / "out.cdxml"
    target.write_text("keep me", encoding="utf-8")

    report = draw_figure(ASPIRIN, output_path=str(target))

    assert report["ok"] is False
    assert target.read_text(encoding="utf-8") == "keep me"


def test_without_a_path_a_fresh_file_is_made_in_the_temp_directory(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    first = draw_figure(ASPIRIN)
    second = draw_figure(ASPIRIN)

    assert first["ok"] and second["ok"]
    assert first["output_path"].endswith(".cdxml")
    assert first["output_path"] != second["output_path"]


def test_native_rendering_is_reported_as_not_run_unless_it_happened(tmp_path):
    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"))

    assert report["native"]["status"] == "not_run"
    assert "png_path" not in report["native"]


def test_native_rendering_failure_is_not_a_pass(tmp_path, monkeypatch):
    def unavailable(cdxml_path, png_path):
        raise RuntimeError("ChemDraw is not installed")

    monkeypatch.setattr(figure_draw, "_render_png", unavailable)

    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"), render=True)

    assert report["ok"] is True
    assert report["native"]["status"] == "not_run"
    assert "not installed" in report["native"]["reason"]


def test_native_rendering_success_returns_the_png_path(tmp_path, monkeypatch):
    def fake(cdxml_path, png_path):
        with open(png_path, "wb") as handle:
            handle.write(b"\x89PNG")
        return png_path

    monkeypatch.setattr(figure_draw, "_render_png", fake)

    report = draw_figure(ASPIRIN, output_path=str(tmp_path / "out.cdxml"), render=True)

    assert report["native"]["status"] == "rendered"
    assert report["native"]["png_path"].endswith(".png")


def test_the_tool_is_registered():
    from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

    assert "draw_figure" in build_registry()
