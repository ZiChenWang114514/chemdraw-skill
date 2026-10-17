from __future__ import annotations

import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

try:
    from cdxml_toolkit.mcp_runtime import native_io
except ImportError:
    native_io = None


MINIMAL_CDXML = "<CDXML><page/></CDXML>"


def _valid_emf() -> bytes:
    data = bytearray(108)
    struct.pack_into("<II", data, 0, 1, 108)
    struct.pack_into("<I", data, 40, 0x464D4520)
    struct.pack_into("<III", data, 44, 0x00010000, len(data), 1)
    struct.pack_into("<H", data, 56, 1)
    return bytes(data)


class NativeIOBridgeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(native_io, "native_io bridge module is required")

    def test_file_bridge_hides_unicode_paths_from_native_operation(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "\u4e2d\u6587\u8f93\u5165" / "\u7ed3\u6784.cdxml"
            destination = root / "\u4e2d\u6587\u8f93\u51fa" / "\u9884\u89c8.png"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_text(MINIMAL_CDXML, encoding="utf-8")
            native_root = root / "native-ascii"

            def render(native_source: Path, native_destination: Path):
                self.assertTrue(str(native_source).isascii())
                self.assertTrue(str(native_destination).isascii())
                self.assertEqual(native_source.read_text(encoding="utf-8"), MINIMAL_CDXML)
                Image.new("RGB", (7, 9), "white").save(native_destination)
                return {"ok": True, "output": str(native_destination)}

            with mock.patch.dict(
                os.environ, {"CHEMDRAW_NATIVE_TEMP": str(native_root)}, clear=False
            ):
                result = native_io.bridge_file(
                    source, destination, render, output_kind="png"
                )

            self.assertTrue(destination.is_file())
            self.assertEqual(result["output"], str(destination.resolve()))

    def test_silent_native_save_failure_has_stable_error_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.cdxml"
            destination = root / "result.png"
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            with self.assertRaises(native_io.NativeIOError) as raised:
                native_io.bridge_file(
                    source,
                    destination,
                    lambda _source, _destination: None,
                    output_kind="png",
                )

            self.assertEqual(
                raised.exception.error_code, "native_saveas_silent_failure"
            )
            self.assertFalse(destination.exists())

    def test_invalid_native_output_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.cdxml"
            destination = root / "result.png"
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            def render(_source: Path, native_destination: Path):
                native_destination.write_bytes(b"not-a-png")

            with self.assertRaises(native_io.NativeIOError) as raised:
                native_io.bridge_file(
                    source, destination, render, output_kind="png"
                )

            self.assertEqual(raised.exception.error_code, "native_output_invalid")
            self.assertFalse(destination.exists())

    def test_publish_race_preserves_concurrent_destination(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.cdxml"
            destination = root / "result.png"
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            def render(_source: Path, native_destination: Path):
                Image.new("RGB", (2, 2), "white").save(native_destination)
                destination.write_bytes(b"concurrent-owner")

            with self.assertRaises(FileExistsError):
                native_io.bridge_file(source, destination, render, output_kind="png")

            self.assertEqual(destination.read_bytes(), b"concurrent-owner")

    def test_truncated_structured_outputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = {
                "short.cdx": b"VjCD0100",
                "short.emf": b"EMF",
                "short.pdf": b"%PDF-1.7",
            }
            for name, payload in cases.items():
                with self.subTest(name=name):
                    candidate = root / name
                    candidate.write_bytes(payload)
                    with self.assertRaises(native_io.NativeIOError):
                        native_io.validate_native_output(candidate)

    def test_path_results_are_rewritten_before_workspace_cleanup(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.cdxml"
            destination = root / "result.png"
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            def render(_source: Path, native_destination: Path):
                Image.new("RGB", (2, 2), "white").save(native_destination)
                return {"output": native_destination}

            result = native_io.bridge_file(source, destination, render, output_kind="png")

            self.assertEqual(result["output"], destination.resolve())

    def test_source_context_is_copied_for_office_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "\u4e2d\u6587" / "deck.pptx"
            sidecar = source.parent / "linked-data.csv"
            destination = root / "preview.pdf"
            source.parent.mkdir()
            source.write_bytes(b"office")
            sidecar.write_text("linked", encoding="utf-8")

            def export(native_source: Path, native_destination: Path):
                self.assertTrue((native_source.parent / sidecar.name).is_file())
                self.assertTrue(str(native_source).isascii())
                native_destination.write_bytes(
                    b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\n"
                    b"xref\n0 1\n0000000000 65535 f \ntrailer<< /Root 1 0 R >>\n"
                    b"startxref\n45\n%%EOF\n"
                )

            with mock.patch.dict(
                os.environ,
                {"CHEMDRAW_NATIVE_TEMP": str(source.parent / "native-temp")},
                clear=False,
            ):
                native_io.bridge_file(
                    source,
                    destination,
                    export,
                    output_kind="pdf",
                    preserve_source_context=True,
                )

            self.assertTrue(destination.is_file())

    def test_shadow_manifest_rechecks_path_containment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_dir = root / "manifest"
            workspace = root / "workspace"
            manifest_dir.mkdir()
            workspace.mkdir()
            (root / "outside.cdxml").write_text(MINIMAL_CDXML, encoding="utf-8")
            manifest = manifest_dir / "manifest.json"
            manifest.write_text(
                '{"slots":[{"type":"cdxml","file":"../outside.cdxml"}]}',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                native_io.write_shadow_manifest(manifest, workspace)

    def test_batch_convert_uses_ascii_inputs_and_restores_source_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = []
            for name in ("\u7ed3\u6784\u4e00.cdxml", "\u7ed3\u6784\u4e8c.cdxml"):
                path = root / "\u4e2d\u6587" / name
                path.parent.mkdir(exist_ok=True)
                path.write_text(MINIMAL_CDXML, encoding="utf-8")
                sources.append(path)

            def batch_convert(native_paths):
                self.assertTrue(all(str(path).isascii() for path in native_paths))
                return [
                    {
                        "path": path,
                        "name": Path(path).stem,
                        "cdx_data": b"VjCD0100" + (b"\0" * 24),
                        "emf_data": _valid_emf(),
                    }
                    for path in native_paths
                ]

            converted = native_io.batch_convert_cdxml(sources, batch_convert)

            self.assertEqual(
                [Path(item["path"]) for item in converted],
                [path.resolve() for path in sources],
            )
            self.assertEqual(
                [item["name"] for item in converted], [path.stem for path in sources]
            )

    def test_cdx_bytes_conversion_uses_ascii_temp_files(self):
        def convert(native_source, native_destination, *, method):
            self.assertEqual(method, "auto")
            self.assertTrue(str(native_source).isascii())
            self.assertTrue(str(native_destination).isascii())
            self.assertTrue(Path(native_source).read_bytes().startswith(b"VjCD0100"))
            Path(native_destination).write_text(MINIMAL_CDXML, encoding="utf-8")

        result = native_io.convert_cdx_bytes_to_cdxml(
            b"VjCD0100" + (b"\0" * 24), convert
        )

        self.assertEqual(result, MINIMAL_CDXML)


class NativeIOIntegrationTests(unittest.TestCase):
    def test_parse_reaction_explicit_cdx_restores_original_path_in_json(self):
        import json
        from cdxml_toolkit.mcp_runtime import official_overrides
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "\u4e2d\u6587" / "\u7ed3\u6784.cdx"
            output = root / "reaction.json"
            source.parent.mkdir()
            source.write_bytes(b"VjCD0100" + (b"\0" * 24))

            def parse(**kwargs):
                self.assertTrue(str(kwargs["cdx"]).isascii())
                Path(kwargs["output_path"]).write_text(
                    json.dumps({"input_files": [kwargs["cdx"]]}), encoding="utf-8"
                )
                return {"ok": True, "output_path": kwargs["output_path"]}

            with mock.patch(
                "cdxml_toolkit.mcp_server.server.parse_reaction", side_effect=parse
            ):
                official_overrides.parse_reaction(
                    cdx=str(source), output_path=str(output)
                )

            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(written["input_files"], [str(source.resolve())])

    def test_parse_reaction_directory_stages_discovered_cdx_under_ascii_path(self):
        import json
        from cdxml_toolkit.mcp_runtime import official_overrides
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "\u4e2d\u6587\u5b9e\u9a8c"
            output = root / "reaction.json"
            input_dir.mkdir()
            (input_dir / "\u7ed3\u6784.cdx").write_bytes(b"VjCD0100" + (b"\0" * 24))

            def parse(**kwargs):
                native_dir = Path(kwargs["input_dir"])
                self.assertTrue(str(native_dir).isascii())
                self.assertTrue(all(str(path).isascii() for path in native_dir.iterdir()))
                discovered = next(native_dir.glob("*.cdx"))
                Path(kwargs["output_path"]).write_text(
                    json.dumps({"ok": True, "input_files": [str(discovered)]}),
                    encoding="utf-8",
                )
                return {"ok": True, "output_path": kwargs["output_path"]}

            with mock.patch(
                "cdxml_toolkit.mcp_server.server.parse_reaction", side_effect=parse
            ):
                result = official_overrides.parse_reaction(
                    input_dir=str(input_dir), output_path=str(output)
                )

            self.assertTrue(result["ok"])
            self.assertTrue(output.is_file())
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                written["input_files"], [str((input_dir / "\u7ed3\u6784.cdx").resolve())]
            )

    def test_office_preview_renderer_receives_only_ascii_paths(self):
        from PIL import Image
        from cdxml_toolkit.mcp_runtime import office_objects
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "\u4e2d\u6587" / "\u7ed3\u6784.cdxml"
            destination = root / "\u4e2d\u6587" / "\u9884\u89c8.png"
            source.parent.mkdir()
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            def render(native_source, native_destination, *, png_dpi):
                self.assertEqual(png_dpi, 300)
                self.assertTrue(str(native_source).isascii())
                self.assertTrue(str(native_destination).isascii())
                Image.new("RGB", (5, 6), "white").save(native_destination)

            with mock.patch("pythoncom.CoInitialize"), mock.patch(
                "pythoncom.CoUninitialize"
            ), mock.patch(
                "cdxml_toolkit.mcp_runtime.office_objects.native_renderer.render_cdxml",
                side_effect=lambda source, destination, *, dpi: render(
                    source, destination, png_dpi=dpi
                ),
            ):
                office_objects._render_cdxml_preview(source, destination)

            self.assertTrue(destination.is_file())

    def test_official_render_override_bridges_unicode_source_and_destination(self):
        from PIL import Image
        from cdxml_toolkit.mcp_runtime import official_overrides
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "\u4e2d\u6587\u8f93\u5165" / "\u7ed3\u6784.cdxml"
            destination = root / "\u4e2d\u6587\u8f93\u51fa" / "\u7ed3\u6784.png"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_text(MINIMAL_CDXML, encoding="utf-8")

            def render(native_source, output_path=None):
                self.assertTrue(str(native_source).isascii())
                self.assertTrue(str(output_path).isascii())
                Image.new("RGB", (8, 10), "white").save(output_path)
                return {"ok": True, "output": str(output_path)}

            with mock.patch(
                "cdxml_toolkit.mcp_runtime.official_overrides.native_renderer.render_cdxml",
                side_effect=lambda source, destination, *, dpi: (
                    render(source, output_path=destination), str(destination)
                )[1],
            ):
                result = official_overrides.render_to_png(
                    str(source), output_path=str(destination)
                )

            self.assertTrue(result["ok"])
            self.assertEqual(Path(result["output"]), destination.resolve())
            self.assertTrue(destination.is_file())


if __name__ == "__main__":
    unittest.main()
