from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock
import zipfile

from PIL import Image
from cdxml_toolkit.office.ole_embedder import (
    build_docx as build_fixture_docx,
    build_ole_compound_file as build_fixture_ole,
    build_pptx as build_fixture_pptx,
)

from cdxml_toolkit.mcp_runtime import extended_tools
MINIMAL_CDXML = """<?xml version="1.0" encoding="UTF-8"?>
<CDXML BondLength="14.40"><page id="1"><fragment id="2"/></page></CDXML>
"""

CFB_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
CHEMDRAW_CLSID = bytes.fromhex("216DBA412EA0CE118FD90020AFD1F20C")


@contextmanager
def mocked_module(full_name: str, **members):
    modules = {}
    parent = None
    parts = full_name.split(".")
    for index in range(len(parts)):
        name = ".".join(parts[: index + 1])
        module = types.ModuleType(name)
        if index < len(parts) - 1:
            module.__path__ = []
        modules[name] = module
        if parent is not None:
            setattr(parent, parts[index], module)
        parent = module
    for name, value in members.items():
        setattr(parent, name, value)
    with mock.patch.dict(sys.modules, modules):
        yield parent


def write_png(path: str | Path, width: int = 2, height: int = 3) -> None:
    Image.new("RGB", (width, height), "white").save(path, format="PNG")


def valid_emf(marker: bytes = b"") -> bytes:
    data = bytearray(108 + len(marker))
    struct.pack_into("<II", data, 0, 1, 108)
    struct.pack_into("<I", data, 40, 0x464D4520)
    struct.pack_into("<III", data, 44, 0x00010000, len(data), 1)
    struct.pack_into("<H", data, 56, 1)
    data[108:] = marker
    return bytes(data)


def valid_chemdraw_ole() -> bytes:
    return build_fixture_ole(b"VjCD0100" + (b"\0" * 5000))


def marker_only_chemdraw_ole() -> bytes:
    data = bytearray(1024)
    data[:8] = CFB_SIGNATURE
    struct.pack_into("<H", data, 24, 0x003E)
    struct.pack_into("<H", data, 26, 0x0003)
    struct.pack_into("<H", data, 28, 0xFFFE)
    struct.pack_into("<H", data, 30, 9)
    struct.pack_into("<H", data, 32, 6)
    struct.pack_into("<I", data, 44, 1)
    struct.pack_into("<I", data, 48, 0)
    markers = (
        CHEMDRAW_CLSID
        + b"CS ChemDraw Drawing\x00"
        + b"ChemDraw.Document.6.0\x00"
        + "CONTENTS".encode("utf-16le")
    )
    data[512 : 512 + len(markers)] = markers
    return bytes(data)


def write_ooxml(path: str | Path, ole_payloads=()) -> None:
    path = Path(path)
    is_pptx = path.suffix.lower() == ".pptx"
    if not is_pptx and path.suffix.lower() != ".docx":
        raise ValueError("OOXML test fixture must be .pptx or .docx")
    path.parent.mkdir(parents=True, exist_ok=True)
    items = [
        {
            "ole_data": payload,
            "emf_data": b"EMF",
            "width_emu": 914400,
            "height_emu": 914400,
            "name": f"fixture-{index}",
        }
        for index, payload in enumerate(ole_payloads, start=1)
    ]
    (build_fixture_pptx if is_pptx else build_fixture_docx)(items, str(path))


class ExtendedToolContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "scheme.cdxml"
        self.source.write_text(MINIMAL_CDXML, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_clean_scheme_rejects_overwrite(self):
        with self.assertRaisesRegex(ValueError, "overwrite"):
            extended_tools.clean_scheme_layout(str(self.source), str(self.source), render_preview=False)

    def test_clean_scheme_returns_uniform_contract(self):
        destination = self.root / "cleaned.cdxml"
        with mock.patch.object(extended_tools, "_run_cleanup", create=True) as cleanup:
            cleanup.side_effect = lambda src, dst, approach: Path(dst).write_text(
                MINIMAL_CDXML, encoding="utf-8"
            )
            result = extended_tools.clean_scheme_layout(
                str(self.source), str(destination), render_preview=False
            )
        self.assertEqual(set(result), {"ok", "outputs", "warnings", "metadata"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["outputs"]["cdxml"], str(destination.resolve()))

    def test_clean_scheme_rejects_malformed_cdxml_input_before_cleanup(self):
        self.source.write_text("<CDXML>", encoding="utf-8")
        with mock.patch.object(extended_tools, "_run_cleanup") as cleanup:
            with self.assertRaisesRegex(ValueError, "CDXML|XML"):
                extended_tools.clean_scheme_layout(str(self.source), render_preview=False)
        cleanup.assert_not_called()

    def test_clean_scheme_rejects_malformed_cdxml_output(self):
        destination = self.root / "malformed.cdxml"
        with mock.patch.object(extended_tools, "_run_cleanup") as cleanup:
            cleanup.side_effect = lambda src, dst, approach: Path(dst).write_text(
                "<CDXML>", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "CDXML|XML"):
                extended_tools.clean_scheme_layout(
                    str(self.source), str(destination), render_preview=False
                )

    def test_clean_preview_failure_leaves_no_cdxml_or_preview(self):
        destination = self.root / "cleaned.cdxml"

        def write_valid(_source, output, _approach):
            Path(output).write_text(MINIMAL_CDXML, encoding="utf-8")

        with mock.patch.object(extended_tools, "_run_cleanup", side_effect=write_valid), mock.patch.object(
            extended_tools, "_render_cdxml", side_effect=RuntimeError("render failed")
        ):
            with self.assertRaisesRegex(RuntimeError, "render failed"):
                extended_tools.clean_scheme_layout(
                    str(self.source), str(destination), render_preview=True
                )
        self.assertFalse(destination.exists())
        self.assertFalse((self.root / "cleaned_preview.png").exists())

    def test_clean_preflights_preview_conflict_before_cleanup(self):
        destination = self.root / "cleaned.cdxml"
        (self.root / "cleaned_preview.png").write_bytes(b"existing")
        with mock.patch.object(extended_tools, "_run_cleanup") as cleanup:
            with self.assertRaisesRegex(ValueError, "preview"):
                extended_tools.clean_scheme_layout(
                    str(self.source), str(destination), render_preview=True
                )
        cleanup.assert_not_called()

    def test_render_validates_format_and_dpi(self):
        with self.assertRaisesRegex(ValueError, "format"):
            extended_tools.render_cdxml_files([str(self.source)], format="pdf")
        with self.assertRaisesRegex(ValueError, "dpi"):
            extended_tools.render_cdxml_files([str(self.source)], dpi=0)

    def test_render_precomputes_and_rejects_duplicate_destinations(self):
        first = self.root / "first" / "same.cdxml"
        second = self.root / "second" / "same.cdxml"
        first.parent.mkdir()
        second.parent.mkdir()
        first.write_text(MINIMAL_CDXML, encoding="utf-8")
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        output_dir = self.root / "renders"
        with mock.patch.object(extended_tools, "_render_cdxml") as render:
            with self.assertRaisesRegex(ValueError, "duplicate|same destination|conflict"):
                extended_tools.render_cdxml_files(
                    [str(first), str(second)], output_dir=str(output_dir)
                )
        render.assert_not_called()

    def test_render_rejects_all_conflicts_before_rendering(self):
        second = self.root / "second.cdxml"
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        existing = self.root / "second.png"
        existing.write_bytes(b"existing")
        with mock.patch.object(extended_tools, "_render_cdxml") as render:
            with self.assertRaisesRegex(ValueError, "overwrite|existing|conflict"):
                extended_tools.render_cdxml_files([str(self.source), str(second)])
        render.assert_not_called()
        self.assertFalse((self.root / "scheme.png").exists())

    def test_render_failure_leaves_no_partial_outputs_or_temps(self):
        second = self.root / "second.cdxml"
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        output_dir = self.root / "renders"
        calls = 0

        def render(src, dst, dpi):
            nonlocal calls
            calls += 1
            if calls == 1:
                write_png(dst)
            else:
                Path(dst).write_bytes(b"not a decodable PNG")

        with mock.patch.object(extended_tools, "_render_cdxml", side_effect=render):
            with self.assertRaisesRegex(RuntimeError, "PNG|image|decode"):
                extended_tools.render_cdxml_files(
                    [str(self.source), str(second)], output_dir=str(output_dir)
                )
        self.assertFalse((output_dir / "scheme.png").exists())
        self.assertFalse((output_dir / "second.png").exists())
        if output_dir.exists():
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_render_publish_cleanup_failure_rolls_back_final_name(self):
        output_dir = self.root / "renders"
        original_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.parent.name.startswith(".render-"):
                raise OSError("staged cleanup failed")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(
            extended_tools, "_render_cdxml", side_effect=lambda src, dst, dpi: write_png(dst)
        ), mock.patch.object(Path, "unlink", new=unlink):
            with self.assertRaisesRegex(OSError, "staged cleanup failed"):
                extended_tools.render_cdxml_files(
                    [str(self.source)], output_dir=str(output_dir)
                )
        self.assertFalse((output_dir / "scheme.png").exists())
        if output_dir.exists():
            self.assertEqual(list(output_dir.iterdir()), [])

    def test_render_publish_race_preserves_competing_destination(self):
        output_dir = self.root / "renders"
        output_dir.mkdir()
        destination = output_dir / "scheme.png"

        def racing_link(source, target):
            Path(target).write_bytes(b"competitor")
            raise OSError("hardlinks unavailable")

        with mock.patch.object(
            extended_tools, "_render_cdxml", side_effect=lambda src, dst, dpi: write_png(dst)
        ), mock.patch.object(extended_tools.os, "link", side_effect=racing_link):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                extended_tools.render_cdxml_files(
                    [str(self.source)], output_dir=str(output_dir)
                )
        self.assertEqual(destination.read_bytes(), b"competitor")

    def test_render_validates_svg_xml(self):
        output_dir = self.root / "renders"
        with mock.patch.object(extended_tools, "_render_cdxml") as render:
            render.side_effect = lambda src, dst, dpi: Path(dst).write_text(
                "<svg>", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "SVG|XML"):
                extended_tools.render_cdxml_files(
                    [str(self.source)], output_dir=str(output_dir), format="svg"
                )
        self.assertFalse((output_dir / "scheme.svg").exists())

    def test_render_rejects_non_png_payload_with_png_extension(self):
        output_dir = self.root / "renders"

        def render(src, dst, dpi):
            Image.new("RGB", (2, 3), "white").save(dst, format="JPEG")

        with mock.patch.object(extended_tools, "_render_cdxml", side_effect=render):
            with self.assertRaisesRegex(RuntimeError, "PNG|format"):
                extended_tools.render_cdxml_files(
                    [str(self.source)], output_dir=str(output_dir), format="png"
                )
        self.assertFalse((output_dir / "scheme.png").exists())

    def test_render_commits_valid_png_after_validation(self):
        output_dir = self.root / "renders"
        with mock.patch.object(extended_tools, "_render_cdxml", side_effect=lambda src, dst, dpi: write_png(dst)):
            result = extended_tools.render_cdxml_files(
                [str(self.source)], output_dir=str(output_dir)
            )
        destination = output_dir / "scheme.png"
        self.assertEqual(result["outputs"]["rendered"], [str(destination.resolve())])
        with Image.open(destination) as image:
            image.load()
            self.assertEqual(image.size, (2, 3))

    def test_merge_requires_two_inputs(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            extended_tools.merge_reaction_schemes([str(self.source)], render_preview=False)

    def test_auto_merge_rejects_non_linear_sequential_plan(self):
        second = self.root / "step2.cdxml"
        third = self.root / "step3.cdxml"
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        third.write_text(MINIMAL_CDXML, encoding="utf-8")
        schemes = [mock.Mock(name=name) for name in ("first", "second", "third")]
        plan = types.SimpleNamespace(
            parallel_groups=[[0], [1], [2]],
            sequential_chain=[0, 1, 2],
            unrelated_groups=[],
            describe=lambda: "Sequential chain: 0 -> 1 -> 2",
        )

        def classify(left, right):
            pair = (schemes.index(left), schemes.index(right))
            return {
                (0, 1): "sequential_ab",
                (0, 2): "sequential_ab",
                (1, 2): "unrelated",
            }[pair]

        with mock.patch(
            "cdxml_toolkit.layout.scheme_merger.parse_scheme", side_effect=schemes
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.auto_detect", return_value=plan
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.classify_pair", side_effect=classify
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.execute_merge_plan"
        ) as execute, mock.patch(
            "cdxml_toolkit.cdxml_utils.write_cdxml",
            side_effect=lambda _tree, output: Path(output).write_text(
                MINIMAL_CDXML, encoding="utf-8"
            ),
        ):
            with self.assertRaisesRegex(ValueError, "auto-detected|non-linear"):
                extended_tools.merge_reaction_schemes(
                    [str(self.source), str(second), str(third)],
                    mode="auto",
                    render_preview=False,
                )
        execute.assert_not_called()

    def test_forced_auto_merge_surfaces_non_linear_warning(self):
        second = self.root / "step2.cdxml"
        third = self.root / "step3.cdxml"
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        third.write_text(MINIMAL_CDXML, encoding="utf-8")
        schemes = [mock.Mock(name=name) for name in ("first", "second", "third")]
        plan = types.SimpleNamespace(
            parallel_groups=[[0], [1], [2]],
            sequential_chain=[0, 1, 2],
            unrelated_groups=[],
            describe=lambda: "Sequential chain: 0 -> 1 -> 2",
        )

        def classify(left, right):
            pair = (schemes.index(left), schemes.index(right))
            return {
                (0, 1): "sequential_ab",
                (0, 2): "sequential_ab",
                (1, 2): "unrelated",
            }[pair]

        with mock.patch(
            "cdxml_toolkit.layout.scheme_merger.parse_scheme", side_effect=schemes
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.auto_detect", return_value=plan
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.classify_pair", side_effect=classify
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.execute_merge_plan", return_value=object()
        ), mock.patch(
            "cdxml_toolkit.cdxml_utils.write_cdxml",
            side_effect=lambda _tree, output: Path(output).write_text(
                MINIMAL_CDXML, encoding="utf-8"
            ),
        ):
            result = extended_tools.merge_reaction_schemes(
                [str(self.source), str(second), str(third)],
                output_path=str(self.root / "forced-auto.cdxml"),
                mode="auto",
                force_sequential=True,
                render_preview=False,
            )
        self.assertTrue(any("forced" in item.lower() for item in result["warnings"]))

    def test_sequential_merge_rejects_unlinked_steps(self):
        second = self.root / "step2.cdxml"
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        first_scheme = mock.Mock()
        first_scheme.get_product_smiles_set.return_value = {"CC"}
        second_scheme = mock.Mock()
        second_scheme.get_reactant_smiles_set.return_value = {"CCC"}
        with mock.patch(
            "cdxml_toolkit.layout.scheme_merger.parse_scheme",
            side_effect=[first_scheme, second_scheme],
        ), mock.patch("cdxml_toolkit.layout.scheme_merger.sequential_merge") as merge:
            with self.assertRaisesRegex(ValueError, "not chemically linked"):
                extended_tools.merge_reaction_schemes(
                    [str(self.source), str(second)],
                    mode="sequential",
                    render_preview=False,
                )
        merge.assert_not_called()

    def test_forced_sequential_merge_surfaces_warning(self):
        second = self.root / "step2.cdxml"
        second.write_text(MINIMAL_CDXML, encoding="utf-8")
        first_scheme = mock.Mock()
        first_scheme.get_product_smiles_set.return_value = {"CC"}
        second_scheme = mock.Mock()
        second_scheme.get_reactant_smiles_set.return_value = {"CCC"}

        def write_valid(_tree, output):
            Path(output).write_text(MINIMAL_CDXML, encoding="utf-8")

        with mock.patch(
            "cdxml_toolkit.layout.scheme_merger.parse_scheme",
            side_effect=[first_scheme, second_scheme],
        ), mock.patch(
            "cdxml_toolkit.layout.scheme_merger.sequential_merge", return_value=object()
        ), mock.patch("cdxml_toolkit.cdxml_utils.write_cdxml", side_effect=write_valid):
            result = extended_tools.merge_reaction_schemes(
                [str(self.source), str(second)],
                output_path=str(self.root / "forced.cdxml"),
                mode="sequential",
                force_sequential=True,
                render_preview=False,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(any("forced" in warning.lower() for warning in result["warnings"]))

    def test_missing_input_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            extended_tools.clean_scheme_layout(str(self.root / "missing.cdxml"))

    def test_analysis_rejects_invalid_tolerance_before_parsing(self):
        fake_pdf = self.root / "report.pdf"
        second_pdf = self.root / "report-2.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")
        second_pdf.write_bytes(b"%PDF-1.4\n")
        with self.assertRaisesRegex(ValueError, "positive"):
            extended_tools.analyze_lcms_series(
                [str(fake_pdf), str(second_pdf)], rt_tolerance=0
            )

    def test_analysis_requires_at_least_two_files(self):
        fake_pdf = self.root / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")
        main = mock.Mock(return_value=0)
        with mocked_module(
            "cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer", main=main
        ):
            with self.assertRaisesRegex(ValueError, "at least two"):
                extended_tools.analyze_lcms_series([str(fake_pdf)])
        main.assert_not_called()

    def test_analysis_uses_json_output_and_handles_multiple_groups(self):
        files = []
        for index in range(2):
            path = self.root / f"report-{index}.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            files.append(str(path))
        captured = []
        groups = [
            {"method": "positive", "warnings": ["positive warning"]},
            {"method": "negative", "warnings": ["negative warning"]},
        ]

        def main(argv):
            captured.extend(argv)
            if "--json-output" not in argv:
                return 2
            output = Path(argv[argv.index("--json-output") + 1])
            output.write_text(json.dumps(groups), encoding="utf-8")
            return 0

        destination = self.root / "analysis.json"
        with mocked_module(
            "cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer", main=main
        ):
            result = extended_tools.analyze_lcms_series(
                files, output_path=str(destination)
            )
        self.assertIn("--json-output", captured)
        self.assertNotIn("--json", captured)
        self.assertNotIn("--output", captured)
        self.assertEqual(result["metadata"]["group_count"], 2)
        self.assertEqual(
            result["warnings"], ["positive warning", "negative warning"]
        )
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), groups)

    def test_analysis_rejects_invalid_json_without_partial_output(self):
        files = []
        for index in range(2):
            path = self.root / f"invalid-{index}.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            files.append(str(path))

        def main(argv):
            flag = "--json-output" if "--json-output" in argv else "--output"
            output = Path(argv[argv.index(flag) + 1])
            output.write_text("{invalid", encoding="utf-8")
            return 0

        destination = self.root / "invalid.json"
        with mocked_module(
            "cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer", main=main
        ):
            with self.assertRaisesRegex(RuntimeError, "JSON"):
                extended_tools.analyze_lcms_series(
                    files, output_path=str(destination)
                )
        self.assertFalse(destination.exists())

    def test_analysis_json_output_tolerates_binary_stdout_writer(self):
        files = []
        for index in range(2):
            path = self.root / f"stdout-{index}.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            files.append(str(path))

        def main(argv):
            sys.stdout.buffer.write(b"discarded text report\n")
            output = Path(argv[argv.index("--json-output") + 1])
            output.write_text(json.dumps({"warnings": []}), encoding="utf-8")
            return 0

        destination = self.root / "stdout.json"
        with mocked_module(
            "cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer", main=main
        ):
            result = extended_tools.analyze_lcms_series(
                files, output_path=str(destination)
            )
        self.assertEqual(result["metadata"]["group_count"], 1)
        self.assertTrue(destination.is_file())

    def test_reaction_image_tool_is_withheld(self):
        self.assertNotIn("reaction_image_to_cdxml", extended_tools.PUBLIC_TOOLS)

    def test_discovery_writes_same_payload_it_returns(self):
        destination = self.root / "discovery.json"
        fake = mock.Mock()
        fake.to_dict.return_value = {"experiment": "EXP-1", "csv_files": []}
        with mock.patch.object(extended_tools, "_discover_experiment", return_value=fake, create=True):
            result = extended_tools.discover_experiment_files(
                str(self.root), experiment="EXP-1", output_path=str(destination)
            )
        on_disk = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["outputs"], result["outputs"])
        self.assertEqual(on_disk["warnings"], result["warnings"])
        self.assertEqual(
            result["metadata"]["artifacts"][0]["path"], str(destination.resolve())
        )

    def test_discovery_commit_failure_leaves_no_final_json(self):
        destination = self.root / "discovery.json"
        fake = mock.Mock()
        fake.to_dict.return_value = {"experiment": "EXP-1"}
        with mock.patch.object(
            extended_tools, "_discover_experiment", return_value=fake
        ), mock.patch.object(
            extended_tools, "_commit_staged_outputs", side_effect=RuntimeError("commit failed")
        ):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                extended_tools.discover_experiment_files(
                    str(self.root), output_path=str(destination)
                )
        self.assertFalse(destination.exists())

    def test_discovery_normalizes_system_exit(self):
        with mock.patch.object(
            extended_tools, "_discover_experiment", side_effect=SystemExit(3)
        ):
            with self.assertRaisesRegex(RuntimeError, "3|exit"):
                extended_tools.discover_experiment_files(str(self.root))

    def test_discovery_promotes_warnings_to_contract(self):
        fake = mock.Mock()
        fake.to_dict.return_value = {
            "experiment": "EXP-1",
            "warnings": ["No LCMS PDF files found"],
        }
        with mock.patch.object(extended_tools, "_discover_experiment", return_value=fake):
            result = extended_tools.discover_experiment_files(str(self.root))
        self.assertEqual(result["warnings"], ["No LCMS PDF files found"])

    def test_fill_rejects_absolute_cdxml_path_in_nested_manifest(self):
        template = self.root / "template.pptx"
        manifest = self.root / "manifest.json"
        write_ooxml(template)
        manifest.write_text(
            json.dumps(
                {
                    "sections": [
                        {"slots": [{"type": "cdxml", "file": str(self.source)}]}
                    ]
                }
            ),
            encoding="utf-8",
        )
        main = mock.Mock(return_value=0)
        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(ValueError, "absolute"):
                extended_tools.fill_office_template(str(template), str(manifest))
        main.assert_not_called()

    def test_fill_rejects_cdxml_traversal_from_manifest_directory(self):
        template = self.root / "template.pptx"
        manifest_dir = self.root / "manifests"
        manifest_dir.mkdir()
        manifest = manifest_dir / "manifest.json"
        write_ooxml(template)
        manifest.write_text(
            json.dumps(
                {
                    "nested": {
                        "slot": {"type": "cdxml", "file": "../scheme.cdxml"}
                    }
                }
            ),
            encoding="utf-8",
        )
        main = mock.Mock(return_value=0)
        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(ValueError, "traversal|manifest directory"):
                extended_tools.fill_office_template(str(template), str(manifest))
        main.assert_not_called()

    def test_fill_enumerates_nested_cdxml_and_requires_matching_embed_count(self):
        template = self.root / "template.pptx"
        manifest = self.root / "manifest.json"
        output = self.root / "filled.pptx"
        nested = self.root / "assets" / "nested.cdxml"
        nested.parent.mkdir()
        nested.write_text(MINIMAL_CDXML, encoding="utf-8")
        write_ooxml(template)
        manifest.write_text(
            json.dumps(
                {
                    "sections": [
                        {"slots": [{"type": "cdxml", "file": "assets/nested.cdxml"}]}
                    ]
                }
            ),
            encoding="utf-8",
        )

        def main(argv):
            write_ooxml(argv[argv.index("--output") + 1])
            print(json.dumps({"slots_filled": 0, "ole_objects": 0, "warnings": []}))
            return 0

        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(RuntimeError, "requested|embedded|OLE"):
                extended_tools.fill_office_template(
                    str(template), str(manifest), str(output)
                )
        self.assertFalse(output.exists())

    def test_fill_validates_template_package_before_toolkit(self):
        template = self.root / "broken.pptx"
        manifest = self.root / "manifest.json"
        template.write_bytes(b"not a zip package")
        manifest.write_text(json.dumps({"slots": []}), encoding="utf-8")
        main = mock.Mock(return_value=0)
        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(ValueError, "OOXML|package|ZIP"):
                extended_tools.fill_office_template(str(template), str(manifest))
        main.assert_not_called()

    def test_fill_rejects_well_formed_non_ooxml_package_parts(self):
        template = self.root / "wrong-root.pptx"
        manifest = self.root / "manifest.json"
        with zipfile.ZipFile(template, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr("[Content_Types].xml", "<NotContentTypes/>")
            package.writestr(
                "_rels/.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
            )
            package.writestr(
                "ppt/presentation.xml",
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>',
            )
        manifest.write_text(json.dumps({"slots": []}), encoding="utf-8")

        def main(argv):
            write_ooxml(argv[argv.index("--output") + 1])
            print(json.dumps({"slots_filled": 0, "ole_objects": 0, "warnings": []}))
            return 0

        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(ValueError, "Content_Types|content types"):
                extended_tools.fill_office_template(str(template), str(manifest))

    def test_fill_rejects_invalid_chemdraw_ole_and_removes_partial_output(self):
        template = self.root / "template.pptx"
        manifest = self.root / "manifest.json"
        output = self.root / "filled.pptx"
        write_ooxml(template)
        manifest.write_text(
            json.dumps(
                {
                    "slots": [
                        {
                            "placeholder": "{{STRUCTURE}}",
                            "type": "cdxml",
                            "file": "scheme.cdxml",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        def main(argv):
            write_ooxml(argv[argv.index("--output") + 1], [b"not valid OLE"])
            print(json.dumps({"slots_filled": 1, "ole_objects": 1, "warnings": []}))
            return 0

        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(RuntimeError, "OLE|ChemDraw"):
                extended_tools.fill_office_template(
                    str(template), str(manifest), str(output)
                )
        self.assertFalse(output.exists())

    def test_marker_bytes_do_not_make_a_valid_chemdraw_ole(self):
        with self.assertRaisesRegex(ValueError, "compound|stream|ChemDraw"):
            extended_tools._validate_chemdraw_ole_bytes(
                marker_only_chemdraw_ole(), "marker-only.bin"
            )

    def test_short_cdx_is_padded_to_a_valid_compound_file_contents_stream(self):
        import io
        import olefile

        cdx = b"VjCD0100" + (b"\0" * 120)
        ole_data = extended_tools._build_chemdraw_ole(cdx)
        extended_tools._validate_chemdraw_ole_bytes(ole_data, "short-cdx")
        compound = olefile.OleFileIO(io.BytesIO(ole_data))
        try:
            contents = compound.openstream("CONTENTS").read()
        finally:
            compound.close()
        self.assertGreaterEqual(len(contents), 4096)
        self.assertTrue(contents.startswith(cdx))

    def test_fill_accepts_valid_package_with_requested_chemdraw_ole(self):
        template = self.root / "template.pptx"
        manifest = self.root / "manifest.json"
        output = self.root / "filled.pptx"
        write_ooxml(template)
        manifest.write_text(
            json.dumps(
                {
                    "slots": [
                        {
                            "placeholder": "{{STRUCTURE}}",
                            "type": "cdxml",
                            "file": "scheme.cdxml",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        def main(argv):
            write_ooxml(argv[argv.index("--output") + 1], [valid_chemdraw_ole()])
            print(json.dumps({"slots_filled": 1, "ole_objects": 1, "warnings": []}))
            return 0

        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            result = extended_tools.fill_office_template(
                str(template), str(manifest), str(output)
            )
        self.assertEqual(result["outputs"]["office"], str(output.resolve()))
        self.assertTrue(output.is_file())

    def test_fill_counts_new_ole_objects_beyond_existing_template_objects(self):
        template = self.root / "template-existing.pptx"
        manifest = self.root / "manifest-existing.json"
        output = self.root / "filled-existing.pptx"
        write_ooxml(template, [valid_chemdraw_ole()])
        manifest.write_text(
            json.dumps(
                {
                    "slots": [
                        {
                            "placeholder": "{{STRUCTURE}}",
                            "type": "cdxml",
                            "file": "scheme.cdxml",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        def main(argv):
            write_ooxml(argv[argv.index("--output") + 1], [valid_chemdraw_ole()])
            print(json.dumps({"slots_filled": 1, "ole_objects": 1, "warnings": []}))
            return 0

        with mocked_module("cdxml_toolkit.office.doc_from_template", main=main):
            with self.assertRaisesRegex(RuntimeError, "requested|embedded|OLE"):
                extended_tools.fill_office_template(
                    str(template), str(manifest), str(output)
                )
        self.assertFalse(output.exists())

    def _batch_module(self, converted, *, ole_data=None, build_docx=None):
        build_ole = mock.Mock(return_value=ole_data or valid_chemdraw_ole())
        build_docx = build_docx or mock.Mock(
            side_effect=lambda items, path: write_ooxml(
                path, [item["ole_data"] for item in items]
            )
        )
        build_pptx = mock.Mock(
            side_effect=lambda items, path: write_ooxml(
                path, [item["ole_data"] for item in items]
            )
        )
        members = {
            "batch_convert": mock.Mock(return_value=converted),
            "build_docx": build_docx,
            "build_ole_compound_file": build_ole,
            "build_pptx": build_pptx,
            "get_cdxml_content_size": mock.Mock(return_value=(100, 200)),
        }
        return mocked_module("cdxml_toolkit.office.ole_embedder", **members), members

    def test_batch_embed_rejects_empty_cdx(self):
        output = self.root / "batch.docx"
        converted = [
            {
                "path": str(self.source.resolve()),
                "name": "scheme",
                "cdx_data": b"",
                "emf_data": valid_emf(),
            }
        ]
        module, members = self._batch_module(converted)
        with module:
            with self.assertRaisesRegex(RuntimeError, "CDX|empty"):
                extended_tools.batch_embed_cdxml_in_office(
                    [str(self.source)], str(output)
                )
        members["build_ole_compound_file"].assert_not_called()
        self.assertFalse(output.exists())

    def test_batch_embed_rejects_empty_emf(self):
        output = self.root / "batch.docx"
        converted = [
            {
                "path": str(self.source.resolve()),
                "name": "scheme",
                "cdx_data": b"VjCD0100" + (b"\0" * 120),
                "emf_data": b"",
            }
        ]
        module, members = self._batch_module(converted)
        with module:
            with self.assertRaisesRegex(RuntimeError, "EMF|empty"):
                extended_tools.batch_embed_cdxml_in_office(
                    [str(self.source)], str(output)
                )
        members["build_ole_compound_file"].assert_not_called()
        self.assertFalse(output.exists())

    def test_batch_embed_validates_ole_before_building_package(self):
        output = self.root / "batch.docx"
        converted = [
            {
                "path": str(self.source.resolve()),
                "name": "scheme",
                "cdx_data": b"VjCD0100" + (b"\0" * 120),
                "emf_data": valid_emf(),
            }
        ]
        module, members = self._batch_module(converted, ole_data=b"not OLE")
        with module:
            with self.assertRaisesRegex(RuntimeError, "OLE|ChemDraw"):
                extended_tools.batch_embed_cdxml_in_office(
                    [str(self.source)], str(output)
                )
        members["build_docx"].assert_not_called()
        self.assertFalse(output.exists())

    def test_batch_embed_failure_never_leaves_partial_final(self):
        output = self.root / "batch.docx"
        converted = [
            {
                "path": str(self.source.resolve()),
                "name": "scheme",
                "cdx_data": b"VjCD0100" + (b"\0" * 120),
                "emf_data": valid_emf(),
            }
        ]

        def fail_after_partial(items, path):
            Path(path).write_bytes(b"partial")
            raise RuntimeError("builder failed")

        module, _ = self._batch_module(
            converted, build_docx=mock.Mock(side_effect=fail_after_partial)
        )
        with module:
            with self.assertRaisesRegex(RuntimeError, "builder failed"):
                extended_tools.batch_embed_cdxml_in_office(
                    [str(self.source)], str(output)
                )
        self.assertFalse(output.exists())

    def test_batch_embed_validates_docx_and_commits(self):
        output = self.root / "batch.docx"
        converted = [
            {
                "path": str(self.source.resolve()),
                "name": "scheme",
                "cdx_data": b"VjCD0100" + (b"\0" * 120),
                "emf_data": valid_emf(),
            }
        ]
        module, _ = self._batch_module(converted)
        with module:
            result = extended_tools.batch_embed_cdxml_in_office(
                [str(self.source)], str(output)
            )
        self.assertEqual(result["metadata"]["objects_embedded"], 1)
        self.assertTrue(output.is_file())

    def test_rdf_resolution_requires_explicit_pubchem_confirmation(self):
        rdf = self.root / "reaction.rdf"
        rdf.write_text("$RDFILE 1\n", encoding="utf-8")
        parse_rdf = mock.Mock(return_value=[object()])
        with mocked_module(
            "cdxml_toolkit.perception.rdf_parser",
            parse_rdf=parse_rdf,
            reaction_to_dict=mock.Mock(return_value={}),
            resolve_cas_numbers=mock.Mock(),
        ):
            with self.assertRaisesRegex(ValueError, "PubChem|confirm"):
                extended_tools.parse_scifinder_rdf(str(rdf), resolve_cas=True)
        parse_rdf.assert_not_called()

    def test_rdf_rejects_empty_reaction_set_without_output(self):
        rdf = self.root / "reaction.rdf"
        rdf.write_text("$RDFILE 1\n", encoding="utf-8")
        output = self.root / "parsed.json"
        with mocked_module(
            "cdxml_toolkit.perception.rdf_parser",
            parse_rdf=mock.Mock(return_value=[]),
            reaction_to_dict=mock.Mock(),
            resolve_cas_numbers=mock.Mock(),
        ):
            with self.assertRaisesRegex(ValueError, "no reactions|empty"):
                extended_tools.parse_scifinder_rdf(
                    str(rdf), output_path=str(output)
                )
        self.assertFalse(output.exists())

    def test_rdf_reports_total_and_unique_cas_counts(self):
        rdf = self.root / "reaction.rdf"
        rdf.write_text("$RDFILE 1\n", encoding="utf-8")
        reaction = object()
        before_record = {
            "reactants": [{"cas": "50-00-0"}],
            "products": [{"cas": "50-00-0"}],
            "variations": [
                {"reagents": [{"cas": "64-17-5"}]}
            ],
        }
        after_record = {
            "reactants": [{"cas": "50-00-0"}],
            "products": [{"cas": "50-00-0"}],
            "variations": [
                {"reagents": [{"cas": "64-17-5", "name": "ethanol", "smiles": "CCO"}]}
            ],
        }
        resolve = mock.Mock()
        with mocked_module(
            "cdxml_toolkit.perception.rdf_parser",
            parse_rdf=mock.Mock(return_value=[reaction]),
            reaction_to_dict=mock.Mock(side_effect=[before_record, after_record]),
            resolve_cas_numbers=resolve,
        ):
            result = extended_tools.parse_scifinder_rdf(
                str(rdf), resolve_cas=True, confirm_pubchem=True
            )
        resolve.assert_called_once_with(reaction)
        self.assertEqual(result["metadata"]["cas_count"], 3)
        self.assertEqual(result["metadata"]["unique_cas_count"], 2)
        self.assertEqual(result["metadata"]["attempted_cas_resolution_count"], 1)
        self.assertEqual(result["metadata"]["resolved_cas_count"], 1)
        self.assertEqual(result["metadata"]["unresolved_cas_count"], 0)

    def test_rdf_does_not_count_preexisting_name_as_cas_resolution(self):
        rdf = self.root / "reaction.rdf"
        rdf.write_text("$RDFILE 1\n", encoding="utf-8")
        reaction = object()
        unchanged = {
            "variations": [
                {"reagents": [{"cas": "64-17-5", "name": "ethanol"}]}
            ]
        }
        with mocked_module(
            "cdxml_toolkit.perception.rdf_parser",
            parse_rdf=mock.Mock(return_value=[reaction]),
            reaction_to_dict=mock.Mock(return_value=unchanged),
            resolve_cas_numbers=mock.Mock(),
        ):
            result = extended_tools.parse_scifinder_rdf(
                str(rdf), resolve_cas=True, confirm_pubchem=True
            )

        self.assertEqual(result["metadata"]["resolved_cas_count"], 0)
        self.assertEqual(result["metadata"]["unresolved_cas_count"], 1)
        self.assertEqual(
            result["metadata"]["cas_resolutions"],
            [
                {
                    "cas": "64-17-5",
                    "status": "unresolved",
                    "fields_added": [],
                }
            ],
        )

    def test_rdf_snapshots_fields_before_in_place_resolution(self):
        rdf = self.root / "reaction.rdf"
        rdf.write_text("$RDFILE 1\n", encoding="utf-8")
        reaction = object()
        shared_record = {
            "variations": [{"reagents": [{"cas": "64-17-5"}]}]
        }

        def resolve(_reaction):
            shared_record["variations"][0]["reagents"][0]["name"] = "ethanol"

        with mocked_module(
            "cdxml_toolkit.perception.rdf_parser",
            parse_rdf=mock.Mock(return_value=[reaction]),
            reaction_to_dict=mock.Mock(return_value=shared_record),
            resolve_cas_numbers=resolve,
        ):
            result = extended_tools.parse_scifinder_rdf(
                str(rdf), resolve_cas=True, confirm_pubchem=True
            )

        self.assertEqual(result["metadata"]["resolved_cas_count"], 1)
        self.assertEqual(
            result["metadata"]["cas_resolutions"][0]["fields_added"], ["name"]
        )

    def test_lab_book_failure_leaves_no_partial_output(self):
        destination = self.root / "assembled.txt"

        def fail_after_write(argv):
            output = Path(argv[argv.index("--output") + 1])
            output.write_text("partial", encoding="utf-8")
            return 1

        with mocked_module(
            "cdxml_toolkit.analysis.deterministic.procedure_writer",
            main=fail_after_write,
        ):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                extended_tools.assemble_lab_book(
                    str(self.root), output_path=str(destination)
                )
        self.assertFalse(destination.exists())

    def test_polish_rejects_unsupported_align_mode_before_pipeline(self):
        pipeline = mock.Mock(
            side_effect=lambda src, dst, **kwargs: Path(dst).write_text(
                MINIMAL_CDXML, encoding="utf-8"
            )
        )
        with mocked_module(
            "cdxml_toolkit.deterministic_pipeline.legacy.scheme_polisher_v2",
            run_pipeline=pipeline,
        ):
            with self.assertRaisesRegex(ValueError, "align_mode"):
                extended_tools.polish_reaction_scheme(
                    str(self.source), align_mode="unknown", render_preview=False
                )
        pipeline.assert_not_called()

    def test_polish_rejects_unsupported_cleanup_approach(self):
        pipeline = mock.Mock(
            side_effect=lambda src, dst, **kwargs: Path(dst).write_text(
                MINIMAL_CDXML, encoding="utf-8"
            )
        )
        with mocked_module(
            "cdxml_toolkit.deterministic_pipeline.legacy.scheme_polisher_v2",
            run_pipeline=pipeline,
        ):
            with self.assertRaisesRegex(ValueError, "approach"):
                extended_tools.polish_reaction_scheme(
                    str(self.source), approach="unknown", render_preview=False
                )
        pipeline.assert_not_called()

    def test_segmentation_rejects_zero_segments_without_output(self):
        output = self.root / "segments.json"
        result = mock.Mock(num_segments=0)
        result.to_dict.return_value = {"segments": []}
        with mocked_module(
            "cdxml_toolkit.perception.scheme_segmenter",
            classify_scheme_complexity=mock.Mock(return_value="simple"),
            segment_scheme=mock.Mock(return_value=result),
        ):
            with self.assertRaisesRegex(RuntimeError, "zero|no segments"):
                extended_tools.segment_large_scheme(
                    str(self.source), output_path=str(output)
                )
        self.assertFalse(output.exists())

    def test_segmentation_commit_failure_leaves_no_final_json(self):
        output = self.root / "segments.json"
        result = mock.Mock(num_segments=1)
        result.to_dict.return_value = {"segments": [{"id": 1}]}
        with mocked_module(
            "cdxml_toolkit.perception.scheme_segmenter",
            classify_scheme_complexity=mock.Mock(return_value="simple"),
            segment_scheme=mock.Mock(return_value=result),
        ), mock.patch.object(
            extended_tools, "_commit_staged_outputs", side_effect=RuntimeError("commit failed")
        ):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                extended_tools.segment_large_scheme(
                    str(self.source), output_path=str(output)
                )
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
