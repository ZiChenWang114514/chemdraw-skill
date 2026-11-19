"""draw_figure: name/SMILES cross-check, arrow-reagent balance and metal-complex templates."""
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit import postconditions
from cdxml_toolkit.mcp_runtime import figure_draw, metal_templates


def _step(substrates, products, above=("rt",)):
    return {"substrates": substrates, "products": products, "above": list(above)}


def test_a_name_that_resolves_to_another_structure_stops_the_run(tmp_path):
    brief = {"species": [{"id": "a", "name": "benzene", "smiles": "Cc1ccccc1"},
                         {"id": "b", "smiles": "OCc1ccccc1"}],
             "steps": [_step(["a"], ["b"])]}
    report = figure_draw.draw_figure(brief, str(tmp_path / "x.cdxml"))
    assert report["ok"] is False
    assert "benzene" in report["errors"][0] and "c1ccccc1" in report["errors"][0]
    assert "Cc1ccccc1" in report["errors"][0]


def test_a_matching_name_an_unknown_name_and_a_free_text_label_pass(tmp_path):
    brief = {"species": [{"id": "a", "name": "toluene", "smiles": "Cc1ccccc1", "label": "benzene"},
                         {"id": "b", "name": "my alcohol 7", "smiles": "OCc1ccccc1"}],
             "steps": [_step(["a"], ["b"])]}
    report = figure_draw.draw_figure(brief, str(tmp_path / "x.cdxml"))
    assert report["ok"] is True, report.get("errors")


def test_above_arrow_reagents_with_structures_count_toward_the_balance(tmp_path):
    # Br2 above the arrow supplies the missing atoms: C6H6 + Br2 -> C6H5Br + HBr.
    brief = {"species": [{"id": "s", "smiles": "c1ccccc1"}, {"id": "p", "smiles": "Brc1ccccc1"},
                         {"id": "hbr", "smiles": "Br"}, {"id": "br2", "smiles": "BrBr"}],
             "steps": [_step(["s"], ["p", "hbr"], above=["br2, FeBr3 (cat.)", "rt, 2 h"])]}
    report = figure_draw.draw_figure(brief, str(tmp_path / "x.cdxml"))
    step = report["steps"][0]
    assert step["balanced"] is True
    assert step["arrow_reagents_counted"] == ["br2"]


def test_checks_passed_agrees_with_an_unbalanced_step(tmp_path):
    brief = {"species": [{"id": "s", "smiles": "CC(=O)Cl"}, {"id": "p", "smiles": "CC(N)=O"}],
             "steps": [_step(["s"], ["p"], above=["heat"])]}
    report = figure_draw.draw_figure(brief, str(tmp_path / "x.cdxml"))
    assert report["steps"][0]["balanced"] is False
    assert report["checks_passed"] is False


def _fragments(path):
    return [f for f in ET.parse(str(path)).getroot().iter("fragment")]


@pytest.mark.parametrize("name", ["Pd(PPh3)4", "Pd(dppf)Cl2", "ferrocene", "Grubbs II", "Wilkinson's catalyst"])
def test_metal_complexes_are_drawn_connected(tmp_path, name):
    brief = {"species": [{"id": "s", "smiles": "Brc1ccccc1"}, {"id": "cat", "name": name},
                         {"id": "p", "smiles": "c1ccccc1"}],
             "steps": [_step(["s", "cat"], ["p"])]}
    out = tmp_path / "x.cdxml"
    report = figure_draw.draw_figure(brief, str(out))
    assert report["ok"] is True, report.get("errors")
    assert report["readback"]["status"] == "matched"
    assert report["readback"]["metal_connectivity"] == []
    for fragment in _fragments(out):
        assert postconditions.check_connected_metal(metal_templates.fragment_graph(fragment)).ok
    template = metal_templates.find_template(name=name)
    if template.hapto:
        assert any(n.get("NodeType") == "MultiAttachment" for f in _fragments(out) for n in f.findall("n"))


@pytest.mark.parametrize("template", metal_templates.TEMPLATES, ids=lambda t: t.id)
def test_each_template_has_the_reagent_table_atoms(template):
    from rdkit import Chem
    from cdxml_toolkit.chemistry_semantics import semantic_key

    mol = Chem.MolFromSmiles(template.smiles)
    assert mol is not None
    # The primary name, where the reagent table has it, has the same atoms as the template.
    table = figure_draw.offline_structure(template.names[0])
    if table:
        assert semantic_key(metal_templates._without_dative(mol)) == semantic_key(Chem.MolFromSmiles(table))


def test_a_loose_reagent_table_smiles_is_upgraded_to_the_template(tmp_path):
    loose = "[Pd]." + ".".join(["P(c1ccccc1)(c1ccccc1)c1ccccc1"] * 4)
    assert not postconditions.check_connected_metal(loose).ok
    brief = {"species": [{"id": "s", "smiles": "Brc1ccccc1"}, {"id": "cat", "smiles": loose, "name": "Pd(PPh3)4"},
                         {"id": "p", "smiles": "c1ccccc1"}],
             "steps": [_step(["s", "cat"], ["p"])]}
    report = figure_draw.draw_figure(brief, str(tmp_path / "x.cdxml"))
    assert report["ok"] is True, report.get("errors")
    assert report["species"][1]["template"] == "pd_pph3_4"
    assert postconditions.check_connected_metal(report["species"][1]["smiles"]).ok


@pytest.mark.parametrize("style", [None, "acs1996", "wiley", "rsc", "nature"])
def test_compound_numbers_are_bold_under_journal_presets(tmp_path, style):
    brief = {"species": [{"id": "a", "smiles": "Cc1ccccc1", "label": "1"},
                         {"id": "b", "smiles": "OCc1ccccc1", "label": "2a"}],
             "steps": [_step(["a"], ["b"])]}
    if style:
        brief["style"] = style
    out = tmp_path / "x.cdxml"
    report = figure_draw.draw_figure(brief, str(out))
    assert report["ok"] is True
    runs = [s for s in ET.parse(str(out)).getroot().iter("s") if s.text in ("1", "2a")]
    assert len(runs) == 2
    assert all(int(s.get("face")) & 1 for s in runs)
