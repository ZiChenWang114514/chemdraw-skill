"""Unit tests for format_procedure_entry and procedure_writer relative imports."""

from __future__ import annotations

import argparse
import sys
import types
from types import SimpleNamespace
from unittest import mock

import pytest

from cdxml_toolkit.analysis import format_procedure_entry as fpe
from cdxml_toolkit.analysis.deterministic import procedure_writer
from cdxml_toolkit.perception.eln_csv_parser import ExperimentData


def _fake_report() -> SimpleNamespace:
    dp_peak = SimpleNamespace(
        rt=1.42,
        ms_spectra=[SimpleNamespace(mode="ES+", top_ions=[346.1, 368.1])],
        uv_lambda_max=[218.2, 254.0],
        area_pct=91.4,
        area_pct_220nm=98.2,
        area_pct_254nm=97.6,
    )
    sm_peak = SimpleNamespace(
        rt=0.88,
        ms_spectra=[SimpleNamespace(mode="ES+", top_ions=[275.1])],
        uv_lambda_max=[220.0],
        area_pct=8.6,
        area_pct_220nm=1.8,
        area_pct_254nm=2.4,
    )
    return SimpleNamespace(
        instrument="Waters Acquity",
        method_short="2min_acidic",
        peaks=[sm_peak, dp_peak],
    )


class TestProcessNmr:
    def test_nmr_with_content_string(self) -> None:
        line = "1H NMR (400 MHz, DMSO-d6) delta 8.12 (s, 1H), 7.45 (d, J = 8.0 Hz, 2H)."
        out = fpe.process_entries([{"type": "nmr", "content": f"  {line}  "}])
        assert out == line

    def test_nmr_with_content_list_strips_blank_items(self) -> None:
        h_nmr = "1H NMR (400 MHz, CDCl3) delta 7.26 (s, 5H)."
        c_nmr = "13C NMR (101 MHz, CDCl3) delta 128.4, 127.1."
        out = fpe.process_entries([
            {"type": "nmr", "content": [h_nmr, "", "   ", f" {c_nmr} "]},
        ])
        assert out == f"{h_nmr}\n{c_nmr}"

    def test_nmr_with_data_string_and_list(self) -> None:
        h_nmr = "1H NMR (400 MHz, DMSO-d6) delta 9.01 (s, 1H)."
        f_nmr = "19F NMR (376 MHz, DMSO-d6) delta -62.4."
        assert fpe.process_entries([{"type": "nmr", "data": h_nmr}]) == h_nmr
        assert fpe.process_entries([{"type": "nmr", "data": [h_nmr, "", f_nmr]}]) == f"{h_nmr}\n{f_nmr}"

    def test_nmr_prefers_non_none_data_and_falls_back_when_data_missing_or_none(self) -> None:
        h_nmr = "1H NMR (400 MHz, DMSO-d6) delta 7.10 (s, 2H)."
        assert fpe.process_entries([{"type": "nmr", "data": None, "content": h_nmr}]) == h_nmr

    @pytest.mark.parametrize(
        "entry",
        [
            {"type": "nmr"},
            {"type": "nmr", "content": ""},
            {"type": "nmr", "content": "   \n  "},
            {"type": "nmr", "content": ["", "   "]},
            {"type": "nmr", "data": []},
            {"type": "nmr", "data": "   "},
        ],
    )
    def test_empty_or_missing_nmr_raises_value_error(self, entry: dict) -> None:
        with pytest.raises(ValueError, match="nmr entry requires non-empty 'content' or 'data'"):
            fpe.process_entries([entry])


class TestLcmsAndTextEntries:
    def test_text_entry_passthrough(self) -> None:
        entries = [
            {"type": "text", "content": "PROCEDURE\nStirred at rt for 2 h."},
            {"type": "text", "content": "CHARACTERIZATION"},
        ]
        assert fpe.process_entries(entries) == "PROCEDURE\nStirred at rt for 2 h.\nCHARACTERIZATION"

    def test_lcms_species_default_all_detectors_when_purity_true(self) -> None:
        report = _fake_report()
        with mock.patch.object(fpe, "_get_report", return_value=report):
            out = fpe.process_entries([
                {
                    "type": "lcms-species",
                    "label": "Purified LCMS",
                    "file": "final.rpt",
                    "peaks": [{"name": "DP", "rt": 1.42, "purity": True}],
                }
            ])
        assert out == (
            "Purified LCMS (Waters Acquity, 2min_acidic): "
            "DP RT = 1.42 min, ESI+ 346.1, \u03bbmax 218, 254 nm, "
            "purity TAC 91.4%, 220nm 98.2%, 254nm 97.6%"
        )

    @pytest.mark.parametrize(
        "detector, expected_purity",
        [
            ("220nm", "purity 220nm 98.2%"),
            ("220", "purity 220nm 98.2%"),
            ("254nm", "purity 254nm 97.6%"),
            ("254", "purity 254nm 97.6%"),
            ("TAC", "purity TAC 91.4%"),
            ("total", "purity TAC 91.4%"),
            ("220, 254", "purity 220nm 98.2%, 254nm 97.6%"),
            (["254nm", "TAC"], "purity 254nm 97.6%, TAC 91.4%"),
        ],
    )
    def test_lcms_species_purity_honors_detector_selection(
        self, detector, expected_purity: str
    ) -> None:
        report = _fake_report()
        with mock.patch.object(fpe, "_get_report", return_value=report):
            out = fpe.process_entries([
                {
                    "type": "lcms-species",
                    "label": "Purified LCMS",
                    "file": "final.rpt",
                    "peaks": [{"name": "DP", "rt": 1.42, "purity": True, "detector": detector}],
                }
            ])
        assert out.endswith(expected_purity)
        if "TAC" not in expected_purity:
            assert "TAC" not in out

    def test_lcms_species_unknown_detector_raises_value_error(self) -> None:
        report = _fake_report()
        with mock.patch.object(fpe, "_get_report", return_value=report):
            with pytest.raises(ValueError, match="Unknown detector"):
                fpe.process_entries([
                    {
                        "type": "lcms-species",
                        "file": "final.rpt",
                        "peaks": [{"name": "DP", "rt": 1.42, "purity": True, "detector": "ELSD"}],
                    }
                ])

    def test_lcms_areas_formats_percentages_and_conversion(self) -> None:
        report = _fake_report()
        with mock.patch.object(fpe, "_get_report", return_value=report):
            out = fpe.process_entries([
                {
                    "type": "lcms-areas",
                    "label": "IPC 2 h",
                    "file": "ipc.rpt",
                    "detector": "220nm",
                    "show_conversion": True,
                    "peaks": [
                        {"name": "SM", "rt": 0.88, "compound_related": True},
                        {"name": "DP", "rt": 1.42, "compound_related": True},
                    ],
                }
            ])
        assert out == "IPC 2 h (Waters Acquity, 2min_acidic), 220nm: SM 1.8% (98% conversion), DP 98.2%"


class TestProcedureWriterRelativeImport:
    def test_procedure_writer_uses_relative_mass_resolver_import(self, tmp_path) -> None:
        assert procedure_writer.__package__ == "cdxml_toolkit.analysis.deterministic"

        exp = ExperimentData(
            experiment_name="EXP-001",
            labbook_name="LB",
            procedure_html="",
            procedure_text="A mixture was stirred.",
            reaction_type="",
            start_date="",
        )
        out_file = tmp_path / "entry.txt"
        args = argparse.Namespace(
            input_dir=str(tmp_path),
            experiment="EXP-001",
            sm_mass=None,
            product_mass=None,
            predict_byproducts=True,
            flower_json=None,
            tracking_json=None,
            output=str(out_file),
            json_errors=False,
        )

        written_calls = []
        fake_flower_mod = types.ModuleType("experiments.byproduct_prediction.flower_predictor")
        fake_flower_mod.write_byproducts_cdxml = lambda preds, path: written_calls.append((preds, path))

        fake_preds = [{"smiles": "CCO", "score": 0.9}]
        with mock.patch.object(procedure_writer, "discover_files", return_value=exp), \
             mock.patch.object(procedure_writer, "extract_expected_masses", return_value=[]), \
             mock.patch(
                 "cdxml_toolkit.analysis.deterministic.mass_resolver.get_last_flower_predictions",
                 return_value=fake_preds,
             ) as get_preds, \
             mock.patch.dict(
                 sys.modules,
                 {
                     "experiments": types.ModuleType("experiments"),
                     "experiments.byproduct_prediction": types.ModuleType("experiments.byproduct_prediction"),
                     "experiments.byproduct_prediction.flower_predictor": fake_flower_mod,
                 },
             ):
            rc = procedure_writer._main_inner(args)

        assert rc == 0
        assert out_file.is_file()
        get_preds.assert_called_once()
        assert written_calls == [(fake_preds, f"{tmp_path / 'entry'}-flower-predictions.cdxml")]
