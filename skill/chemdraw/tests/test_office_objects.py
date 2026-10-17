from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zipfile

from PIL import Image
from cdxml_toolkit.office.ole_embedder import (
    build_docx,
    build_ole_compound_file,
    build_pptx,
)

from cdxml_toolkit.mcp_runtime import extended_tools
from cdxml_toolkit.mcp_runtime import office_objects
MINIMAL_CDXML = """<?xml version="1.0" encoding="UTF-8"?>
<CDXML BondLength="14.40"><page id="1"><fragment id="2"/></page></CDXML>
"""


def _ole(marker: bytes) -> bytes:
    cdx = b"VjCD0100" + marker + (b"\0" * (5000 - len(marker)))
    return build_ole_compound_file(cdx)


def _emf(marker: bytes = b"") -> bytes:
    data = bytearray(108 + len(marker))
    struct.pack_into("<II", data, 0, 1, 108)
    struct.pack_into("<I", data, 40, 0x464D4520)
    struct.pack_into("<III", data, 44, 0x00010000, len(data), 1)
    struct.pack_into("<H", data, 56, 1)
    data[108:] = marker
    return bytes(data)


def _write_dual_office(path: Path) -> None:
    items = [
        {
            "ole_data": _ole(f"OBJECT-{index}".encode("ascii")),
            "emf_data": f"EMF-{index}".encode("ascii"),
            "width_emu": 914400 * index,
            "height_emu": 457200 * index,
            "name": f"fixture-{index}",
        }
        for index in (1, 2)
    ]
    (build_pptx if path.suffix == ".pptx" else build_docx)(items, str(path))


def _write_many_office(path: Path, count: int) -> None:
    items = [
        {
            "ole_data": _ole(f"OBJECT-{index}".encode("ascii")),
            "emf_data": f"EMF-{index}".encode("ascii"),
            "width_emu": 914400,
            "height_emu": 457200,
            "name": f"fixture-{index}",
        }
        for index in range(1, count + 1)
    ]
    (build_pptx if path.suffix == ".pptx" else build_docx)(items, str(path))


def _package_parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as package:
        return {name: package.read(name) for name in package.namelist()}


def _render_png(_source: str, destination: str) -> None:
    Image.new("RGB", (16, 12), "white").save(destination, format="PNG")


class OfficeInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _inspect(self, suffix: str, *, render_previews: bool = True):
        source = self.root / f"dual{suffix}"
        output = self.root / f"inspection-{suffix[1:]}"
        _write_dual_office(source)
        with mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects._convert_cdx_to_cdxml", return_value=MINIMAL_CDXML
        ), mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects._render_cdxml_preview", side_effect=_render_png
        ):
            result = extended_tools.inspect_chemdraw_objects_in_office(
                str(source), str(output), render_previews=render_previews
            )
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        return source, output, result, manifest

    def test_inspect_pptx_records_stable_bindings_geometry_and_numbered_outputs(self):
        source, output, result, manifest = self._inspect(".pptx")

        self.assertTrue(result["ok"])
        self.assertEqual(result["metadata"]["objects"], 2)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(
            manifest["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest()
        )
        self.assertEqual(len({item["object_id"] for item in manifest["objects"]}), 2)
        first = manifest["objects"][0]
        self.assertEqual(first["host_part"], "ppt/slides/slide1.xml")
        self.assertEqual(first["host"]["kind"], "slide")
        self.assertEqual(first["host"]["number"], 1)
        self.assertEqual(first["relationship_id"], "rIdOle1")
        self.assertEqual(first["embedding_part"], "ppt/embeddings/oleObject1.bin")
        self.assertEqual(first["preview_relationship_id"], "rIdOleImg1")
        self.assertEqual(first["preview_part"], "ppt/media/olePreview1.emf")
        self.assertEqual(first["shape_name"], "Object 1")
        self.assertEqual(first["geometry"]["width_emu"], 914400)
        self.assertEqual(first["geometry"]["height_emu"], 457200)
        self.assertEqual(first["cdxml"], "objects/object_001.cdxml")
        self.assertEqual(first["preview_png"], "previews/object_001.png")
        self.assertTrue((output / first["cdxml"]).is_file())
        self.assertTrue((output / first["preview_png"]).is_file())

    def test_inspect_docx_records_paragraph_host_and_vml_dimensions(self):
        _, output, _, manifest = self._inspect(".docx")

        first = manifest["objects"][0]
        self.assertEqual(first["host_part"], "word/document.xml")
        self.assertEqual(first["host"]["kind"], "document")
        self.assertEqual(first["host"]["paragraph"], 2)
        self.assertIsNone(first["host"]["page"])
        self.assertEqual(first["relationship_id"], "rIdOle1")
        self.assertEqual(first["preview_relationship_id"], "rIdOleImg1")
        self.assertEqual(first["shape_name"], "_x0000_s1026")
        self.assertEqual(first["geometry"]["width_emu"], 914400)
        self.assertEqual(first["geometry"]["height_emu"], 457200)
        self.assertTrue((output / "objects" / "object_002.cdxml").is_file())

    def test_inspect_without_previews_does_not_invoke_renderer(self):
        source = self.root / "dual.pptx"
        output = self.root / "inspection"
        _write_dual_office(source)
        with mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects._convert_cdx_to_cdxml", return_value=MINIMAL_CDXML
        ), mock.patch("cdxml_toolkit.mcp_runtime.office_objects._render_cdxml_preview") as renderer:
            result = extended_tools.inspect_chemdraw_objects_in_office(
                str(source), str(output), render_previews=False
            )

        renderer.assert_not_called()
        self.assertEqual(result["outputs"]["previews"], [])
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("preview_png", manifest["objects"][0])

    def test_inspect_rolls_back_directory_when_conversion_fails(self):
        source = self.root / "dual.pptx"
        output = self.root / "inspection"
        _write_dual_office(source)
        with mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects._convert_cdx_to_cdxml", side_effect=RuntimeError("convert")
        ):
            with self.assertRaisesRegex(RuntimeError, "convert"):
                extended_tools.inspect_chemdraw_objects_in_office(
                    str(source), str(output), render_previews=False
                )
        self.assertFalse(output.exists())

    def test_inspect_numbers_outputs_in_numeric_host_order_beyond_nine(self):
        source = self.root / "many.pptx"
        output = self.root / "inspection"
        _write_many_office(source, 11)
        with mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects._convert_cdx_to_cdxml", return_value=MINIMAL_CDXML
        ):
            extended_tools.inspect_chemdraw_objects_in_office(
                str(source), str(output), render_previews=False
            )

        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [item["host"]["number"] for item in manifest["objects"]],
            list(range(1, 12)),
        )

    def test_native_conversion_initializes_and_releases_com_apartment(self):
        def convert(native_source, native_destination, *, method):
            self.assertEqual(method, "auto")
            self.assertTrue(str(native_source).isascii())
            self.assertTrue(str(native_destination).isascii())
            Path(native_destination).write_text(MINIMAL_CDXML, encoding="utf-8")

        with mock.patch("pythoncom.CoInitialize") as initialize, mock.patch(
            "pythoncom.CoUninitialize"
        ) as uninitialize, mock.patch(
            "cdxml_toolkit.chemdraw.cdx_converter.convert_file",
            side_effect=convert,
        ):
            result = office_objects._convert_cdx_to_cdxml(
                b"VjCD0100" + (b"\0" * 24)
            )

        self.assertEqual(result, MINIMAL_CDXML)
        initialize.assert_called_once_with()
        uninitialize.assert_called_once_with()

    def test_native_preview_initializes_and_releases_com_apartment(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.cdxml"
            destination = Path(temp_dir) / "preview.png"
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            def render(native_source, native_destination, *, png_dpi):
                self.assertEqual(png_dpi, 300)
                self.assertTrue(str(native_source).isascii())
                self.assertTrue(str(native_destination).isascii())
                Image.new("RGB", (4, 5), "white").save(native_destination)

            with mock.patch("pythoncom.CoInitialize") as initialize, mock.patch(
                "pythoncom.CoUninitialize"
            ) as uninitialize, mock.patch(
                "cdxml_toolkit.mcp_runtime.office_objects.native_renderer.render_cdxml",
                side_effect=lambda source, destination, *, dpi: render(
                    source, destination, png_dpi=dpi
                ),
            ) as renderer:
                office_objects._render_cdxml_preview(source, destination)

        renderer.assert_called_once()
        initialize.assert_called_once_with()
        uninitialize.assert_called_once_with()


class OfficeReplacementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.replacement = self.root / "replacement.cdxml"
        self.replacement.write_text(MINIMAL_CDXML, encoding="utf-8")
        self.replacement_ole = _ole(b"REPLACEMENT")
        self.replacement_emf = _emf(b"REPLACEMENT")

    def tearDown(self):
        self.temp.cleanup()

    def _inspection_manifest(self, suffix: str):
        source = self.root / f"dual{suffix}"
        inspection = self.root / f"inspection-{suffix[1:]}"
        _write_dual_office(source)
        with mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects._convert_cdx_to_cdxml", return_value=MINIMAL_CDXML
        ):
            extended_tools.inspect_chemdraw_objects_in_office(
                str(source), str(inspection), render_previews=False
            )
        manifest = json.loads(
            (inspection / "manifest.json").read_text(encoding="utf-8")
        )
        return source, manifest

    def _write_replacements(self, manifest: dict, entries: list[dict]) -> Path:
        path = self.root / "replacements.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_sha256": manifest["source_sha256"],
                    "replacements": entries,
                }
            ),
            encoding="utf-8",
        )
        return path

    def _replace(self, source: Path, manifest_path: Path, output: Path):
        converted = [
            {
                "path": str(self.replacement),
                "name": self.replacement.stem,
                "cdx_data": b"VjCD0100replacement",
                "emf_data": self.replacement_emf,
            }
        ]
        with mock.patch(
            "cdxml_toolkit.office.ole_embedder.batch_convert",
            return_value=converted,
        ), mock.patch.object(
            extended_tools, "_build_chemdraw_ole", return_value=self.replacement_ole
        ):
            return extended_tools.replace_chemdraw_objects_in_office(
                str(source), str(manifest_path), str(output), render_pdf_preview=False
            )

    def _assert_single_object_replaced(self, suffix: str) -> None:
        source, manifest = self._inspection_manifest(suffix)
        first, second = manifest["objects"]
        replacement_manifest = self._write_replacements(
            manifest,
            [
                {
                    "object_id": first["object_id"],
                    "replacement_cdxml": self.replacement.name,
                }
            ],
        )
        output = self.root / f"replaced{suffix}"
        before = _package_parts(source)

        result = self._replace(source, replacement_manifest, output)

        after = _package_parts(output)
        self.assertTrue(result["ok"])
        self.assertEqual(result["metadata"]["objects_replaced"], 1)
        self.assertEqual(after[first["embedding_part"]], self.replacement_ole)
        self.assertEqual(after[first["preview_part"]], self.replacement_emf)
        self.assertEqual(after[second["embedding_part"]], before[second["embedding_part"]])
        self.assertEqual(after[second["preview_part"]], before[second["preview_part"]])
        for part in (first["host_part"], second["host_part"]):
            self.assertEqual(after[part], before[part])
        relationship_parts = {
            item["relationship_part"] for item in manifest["objects"]
        }
        for part in relationship_parts:
            self.assertEqual(after[part], before[part])

    def test_replace_one_of_two_pptx_objects_preserves_other_parts_and_geometry(self):
        self._assert_single_object_replaced(".pptx")

    def test_replace_one_of_two_docx_objects_preserves_other_parts_and_geometry(self):
        self._assert_single_object_replaced(".docx")

    def test_replace_rejects_unsafe_and_ambiguous_manifest_entries(self):
        source, manifest = self._inspection_manifest(".pptx")
        object_id = manifest["objects"][0]["object_id"]
        cases = {
            "absolute": [
                {
                    "object_id": object_id,
                    "replacement_cdxml": str(self.replacement.resolve()),
                }
            ],
            "traversal": [
                {"object_id": object_id, "replacement_cdxml": "../replacement.cdxml"}
            ],
            "duplicate": [
                {"object_id": object_id, "replacement_cdxml": self.replacement.name},
                {"object_id": object_id, "replacement_cdxml": self.replacement.name},
            ],
            "unknown": [
                {"object_id": "chemdraw-unknown", "replacement_cdxml": self.replacement.name}
            ],
        }
        for label, entries in cases.items():
            with self.subTest(label=label):
                path = self._write_replacements(manifest, entries)
                output = self.root / f"unsafe-{label}.pptx"
                with self.assertRaisesRegex(
                    (ValueError, FileNotFoundError),
                    "absolute|traversal|duplicate|unknown|recognized",
                ):
                    extended_tools.replace_chemdraw_objects_in_office(
                        str(source), str(path), str(output), render_pdf_preview=False
                    )
                self.assertFalse(output.exists())

    def test_replace_rejects_source_changed_after_inspection(self):
        source, manifest = self._inspection_manifest(".pptx")
        path = self._write_replacements(
            manifest,
            [
                {
                    "object_id": manifest["objects"][0]["object_id"],
                    "replacement_cdxml": self.replacement.name,
                }
            ],
        )
        with source.open("ab") as handle:
            handle.write(b"changed")

        with self.assertRaisesRegex(ValueError, "SHA-256|changed|source"):
            extended_tools.replace_chemdraw_objects_in_office(
                str(source), str(path), render_pdf_preview=False
            )

    def test_replace_rolls_back_office_and_pdf_when_office_export_fails(self):
        source, manifest = self._inspection_manifest(".pptx")
        path = self._write_replacements(
            manifest,
            [
                {
                    "object_id": manifest["objects"][0]["object_id"],
                    "replacement_cdxml": self.replacement.name,
                }
            ],
        )
        output = self.root / "replaced.pptx"
        converted = [
            {
                "path": str(self.replacement),
                "name": self.replacement.stem,
                "cdx_data": b"VjCD0100replacement",
                "emf_data": self.replacement_emf,
            }
        ]

        def fail_export(_office: Path, pdf: Path) -> None:
            pdf.write_bytes(b"partial")
            raise RuntimeError("Office export failed")

        with mock.patch(
            "cdxml_toolkit.office.ole_embedder.batch_convert",
            return_value=converted,
        ), mock.patch.object(
            extended_tools, "_build_chemdraw_ole", return_value=self.replacement_ole
        ), mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects.render_office_pdf", side_effect=fail_export
        ):
            with self.assertRaisesRegex(RuntimeError, "Office export failed"):
                extended_tools.replace_chemdraw_objects_in_office(
                    str(source), str(path), str(output), render_pdf_preview=True
                )

        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".pdf").exists())

    def test_replace_batch_conversion_runs_inside_com_apartment(self):
        source, manifest = self._inspection_manifest(".pptx")
        path = self._write_replacements(
            manifest,
            [
                {
                    "object_id": manifest["objects"][0]["object_id"],
                    "replacement_cdxml": self.replacement.name,
                }
            ],
        )
        output = self.root / "apartment.pptx"
        converted = [
            {
                "path": str(self.replacement),
                "name": self.replacement.stem,
                "cdx_data": b"VjCD0100replacement",
                "emf_data": self.replacement_emf,
            }
        ]
        with mock.patch(
            "cdxml_toolkit.office.ole_embedder.batch_convert",
            return_value=converted,
        ), mock.patch.object(
            extended_tools, "_build_chemdraw_ole", return_value=self.replacement_ole
        ), mock.patch(
            "cdxml_toolkit.mcp_runtime.office_objects.com_apartment", create=True
        ) as apartment:
            extended_tools.replace_chemdraw_objects_in_office(
                str(source), str(path), str(output), render_pdf_preview=False
            )

        apartment.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
