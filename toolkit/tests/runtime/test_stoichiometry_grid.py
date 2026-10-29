"""ChemDraw's own stoichiometry grid (Structure > Analyze Stoichiometry): run it and read it back.

The fixture was saved by ChemDraw 22.2 after Analyze Stoichiometry on benzyl alcohol + acetyl
chloride (triethylamine above the arrow, CH2Cl2 below it) giving benzyl acetate, with 1.0814 g
typed as the sample mass of benzyl alcohol.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

import pytest

from cdxml_toolkit.chemdraw import stoichiometry_grid as sg

FIXTURE = Path(__file__).parent / "data" / "stoichiometry-grid.cdxml"
LIVE = sys.platform in ("win32", "darwin") and os.environ.get("CDXML_LIVE_CHEMDRAW") == "1"


def _row(result, object_id):
    return next(row for row in result["grids"][0]["rows"] if row["object_id"] == object_id)


class ReadGridTests(unittest.TestCase):
    def test_rows_follow_the_reaction_roles(self):
        result = sg.read_grid(FIXTURE)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["grids"]), 1)
        roles = {row["object_id"]: row["role"] for row in result["grids"][0]["rows"]}
        self.assertEqual(roles, {"1000": "reactant", "1037": "reactant", "1057": "agent",
                                 "1140": "agent", "1088": "product"})

    def test_cells_carry_chemdraw_values_and_displayed_text(self):
        alcohol = _row(sg.read_grid(FIXTURE), "1000")["cells"]
        self.assertEqual(alcohol["Formula"]["text"], "C7H8O")
        self.assertEqual(alcohol["MW"]["value"], 108.14)
        self.assertEqual(alcohol["Sample Mass"], {"value": 1.0814, "text": "1.08g", "edited": True})
        self.assertEqual(alcohol["Reactant Moles"]["value"], 0.01)
        self.assertEqual(alcohol["Reactant Moles"]["text"], "10.00mmol")
        self.assertIs(alcohol["Limiting?"]["value"], True)
        self.assertNotIn("Limit Moles", alcohol, "hidden cells are left out")

    def test_product_rows_use_the_product_columns(self):
        product = _row(sg.read_grid(FIXTURE), "1088")["cells"]
        self.assertIn("%Yield", product)
        self.assertIn("Expected Mass", product)
        self.assertNotIn("Sample Mass", product)

    def test_a_file_without_a_grid_names_the_command(self):
        text = FIXTURE.read_text(encoding="utf-8")
        start, end = text.index("<stoichiometrygrid"), text.index("</stoichiometrygrid>")
        plain = Path(_folder(self)) / "plain.cdxml"
        plain.write_text(text[:start] + text[end + len("</stoichiometrygrid>"):], encoding="utf-8")
        with self.assertRaisesRegex(sg.StoichiometryGridError, "Analyze Stoichiometry"):
            sg.read_grid(plain)

    def test_every_grid_is_read_and_a_second_one_is_reported(self):
        text = FIXTURE.read_text(encoding="utf-8")
        start, end = text.index("<stoichiometrygrid"), text.index("</stoichiometrygrid>") + len("</stoichiometrygrid>")
        doubled = Path(_folder(self)) / "doubled.cdxml"
        doubled.write_text(text[:end] + text[start:end] + text[end:], encoding="utf-8")
        result = sg.read_grid(doubled)
        self.assertEqual(len(result["grids"]), 2)
        self.assertTrue(any("2 stoichiometry grids" in warning for warning in result["warnings"]))

    def test_only_cdxml_is_read(self):
        with self.assertRaisesRegex(ValueError, "CDXML"):
            sg.read_grid(FIXTURE.with_suffix(".cdx"))


def _folder(test):
    import tempfile
    folder = tempfile.TemporaryDirectory()
    test.addCleanup(folder.cleanup)
    return folder.name


# --- a fake ChemDraw ------------------------------------------------------------------

class _Grids:
    def __init__(self):
        self.Count = 0


class _Document:
    def __init__(self, app, path):
        self.app, self.path = app, path
        self.StoichiometryGrids = _Grids()
        self.Objects = mock.Mock()
        self.closed_with = None

    def Activate(self):
        pass

    def SaveAs(self, path):
        self.app.events.append(("save", path))
        shutil.copyfile(FIXTURE, path)

    def Close(self, save_changes):
        self.app.events.append(("close", save_changes))
        self.closed_with = save_changes


class _Item:
    def __init__(self, app, command_id, caption, enabled=True):
        self.app, self.CommandID, self.caption, self.Enabled = app, command_id, caption, enabled

    def Execute(self):
        self.app.events.append(("execute", self.CommandID, self.app.Visible))
        if self.app.creates_grid:
            self.app.document.StoichiometryGrids.Count += 1


class _Collection:
    def __init__(self, items, attribute):
        self._items = items
        self.Count = len(items)
        self._attribute = attribute

    def Item(self, index):
        return self._items[index - 1]


class _App:
    def __init__(self, *, enabled=True, creates_grid=True):
        self.events = []
        self.Visible = False
        self.creates_grid = creates_grid
        self.document = None
        structure = mock.Mock(caption="&Structure")
        structure.MenuItems = _Collection([_Item(self, 362, "Map Reaction Atoms"),
                                           _Item(self, sg.COMMAND_ID, sg.MENU_CAPTION, enabled)], "items")
        menus = _Collection([structure], "menus")
        self.MenuBars = _Collection([mock.Mock(Menus=menus)], "bars")
        self.Documents = mock.Mock()
        self.Documents.Open.side_effect = self._open

    def _open(self, path):
        self.events.append(("open", path))
        self.document = _Document(self, path)
        return self.document

    def Quit(self):
        self.events.append(("quit",))


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(_folder(self))
        text = FIXTURE.read_text(encoding="utf-8")
        start, end = text.index("<stoichiometrygrid"), text.index("</stoichiometrygrid>")
        self.source = self.folder / "reaction.cdxml"
        self.source.write_text(text[:start] + text[end + len("</stoichiometrygrid>"):], encoding="utf-8")
        self.original = self.source.read_bytes()

    def _run(self, app, **kwargs):
        with mock.patch.object(sg.sys, "platform", "win32"), \
                mock.patch.object(sg, "_dispatch", return_value=app), \
                mock.patch.object(sg, "_apartment", return_value=_nullcontext()), \
                mock.patch.object(sg, "_settle"), \
                mock.patch.object(sg, "native_resource_lock", return_value=_nullcontext()), \
                mock.patch.object(sg, "open_in_chemdraw") as opener:
            result = sg.analyze(str(self.source), **kwargs)
        return result, opener

    def test_runs_the_menu_command_in_a_visible_window_on_a_copy(self):
        app = _App()
        result, _ = self._run(app)
        execute = [event for event in app.events if event[0] == "execute"]
        self.assertEqual(execute, [("execute", sg.COMMAND_ID, True)])
        opened = Path(next(event[1] for event in app.events if event[0] == "open"))
        self.assertNotEqual(opened, self.source, "ChemDraw never opens the source itself")
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(Path(result["path"]).name, "reaction-stoichiometry.cdxml")
        self.assertEqual(len(result["grids"]), 1)

    def test_the_document_is_closed_unsaved_before_chemdraw_quits(self):
        app = _App()
        self._run(app)
        kinds = [event[0] for event in app.events]
        self.assertEqual(kinds[-2:], ["close", "quit"])
        self.assertEqual(app.events[-2], ("close", False))
        self.assertLess(kinds.index("save"), kinds.index("close"))

    def test_an_existing_output_is_never_replaced(self):
        taken = self.folder / "reaction-stoichiometry.cdxml"
        taken.write_text("keep", encoding="utf-8")
        result, _ = self._run(_App())
        self.assertEqual(taken.read_text(encoding="utf-8"), "keep")
        self.assertEqual(Path(result["path"]).name, "reaction-stoichiometry_2.cdxml")

    def test_a_disabled_command_means_no_reaction(self):
        app = _App(enabled=False)
        with self.assertRaises(sg.StoichiometryGridError) as caught:
            self._run(app)
        self.assertEqual(caught.exception.error_code, "no_reaction")
        self.assertEqual([event[0] for event in app.events][-2:], ["close", "quit"])

    def test_a_command_that_draws_no_grid_is_an_error(self):
        with self.assertRaises(sg.StoichiometryGridError) as caught:
            self._run(_App(creates_grid=False))
        self.assertEqual(caught.exception.error_code, "no_grid")

    def test_a_file_that_already_holds_a_grid_is_refused_before_chemdraw_starts(self):
        shutil.copyfile(FIXTURE, self.source)
        app = _App()
        with self.assertRaisesRegex(ValueError, "already holds"):
            self._run(app)
        self.assertEqual(app.events, [])

    def test_the_result_opens_in_chemdraw_only_when_asked(self):
        _, opener = self._run(_App())
        opener.assert_not_called()
        result, opener = self._run(_App(), open_result=True)
        opener.assert_called_once_with(Path(result["path"]))

    def test_other_platforms_are_told_what_is_needed(self):
        with mock.patch.object(sg.sys, "platform", "linux"):
            with self.assertRaises(sg.StoichiometryGridError) as caught:
                sg.analyze(str(self.source))
        self.assertEqual(caught.exception.error_code, "chemdraw_unavailable")


class ReactionSmilesTests(unittest.TestCase):
    def test_agents_are_drawn_above_the_arrow(self):
        folder = Path(_folder(self))
        target = sg.reaction_document("OCc1ccccc1.CC(=O)Cl>CCN(CC)CC>CC(=O)OCc1ccccc1", folder / "r.cdxml")
        import xml.etree.ElementTree as ET
        step = next(ET.parse(target).getroot().iter("step"))
        self.assertEqual(len(step.get("ReactionStepReactants").split()), 2)
        self.assertEqual(len(step.get("ReactionStepObjectsAboveArrow").split()), 1)
        self.assertEqual(len(step.get("ReactionStepProducts").split()), 1)

    def test_text_that_is_not_a_reaction_is_refused(self):
        with self.assertRaisesRegex(ValueError, "reaction SMILES"):
            sg.reaction_document("OCc1ccccc1", Path("unused.cdxml"))


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


class ToolTests(unittest.TestCase):
    def test_read_mode_needs_no_chemdraw(self):
        from cdxml_toolkit.mcp_runtime.report_tools import stoichiometry_grid
        with mock.patch.object(sg, "analyze", side_effect=AssertionError("ChemDraw started")):
            result = stoichiometry_grid(str(FIXTURE), mode="read")
        self.assertEqual(result["mode"], "read")
        self.assertEqual(len(result["grids"][0]["rows"]), 5)

    def test_unknown_modes_and_options_are_refused(self):
        from cdxml_toolkit.mcp_runtime.report_tools import stoichiometry_grid
        with self.assertRaisesRegex(ValueError, "mode"):
            stoichiometry_grid(str(FIXTURE), mode="compute")
        with self.assertRaisesRegex(ValueError, "scale_mmol"):
            stoichiometry_grid(str(FIXTURE), mode="read", options={"scale_mmol": 1})

    def test_the_tool_runs_under_the_chemdraw_lock(self):
        from cdxml_toolkit.mcp_runtime import tool_registry
        self.assertEqual(tool_registry._resource_class("stoichiometry_grid", "win32"), "chemdraw_com")
        registry = tool_registry.build_registry()
        self.assertIn("stoichiometry_grid", registry)
        self.assertNotIn("reaction_calculator", registry)


@pytest.mark.skipif(not LIVE, reason="drives ChemDraw; set CDXML_LIVE_CHEMDRAW=1 on Windows or macOS")
def test_live_chemdraw_draws_its_grid(tmp_path):
    result = sg.analyze("OCc1ccccc1.CC(=O)Cl>CCN(CC)CC>CC(=O)OCc1ccccc1",
                        output_path=str(tmp_path / "live.cdxml"))
    rows = result["grids"][0]["rows"]
    assert {row["role"] for row in rows} == {"reactant", "agent", "product"}
    assert any(row["cells"].get("MW", {}).get("value") == 108.14 for row in rows)
