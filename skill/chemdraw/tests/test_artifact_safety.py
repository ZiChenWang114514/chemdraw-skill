from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

from cdxml_toolkit.office import ole_extractor
from cdxml_toolkit.mcp_runtime import artifact_safety
from cdxml_toolkit.mcp_runtime import official_overrides
MINIMAL_CDXML = "<CDXML><page id=\"1\"/></CDXML>\n"


class ArtifactSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_destination_uses_semantic_suffix_and_avoids_conflicts(self):
        source = self.root / "scheme.cdxml"
        source.write_text(MINIMAL_CDXML, encoding="utf-8")
        (self.root / "scheme_rendered.png").write_bytes(b"sentinel")

        destination = artifact_safety.resolve_destination(
            source=source,
            output_path=None,
            tag="rendered",
            suffix=".png",
        )

        self.assertEqual(destination, (self.root / "scheme_rendered_2.png").resolve())

    def test_default_destination_without_source_does_not_duplicate_tag(self):
        destination = artifact_safety.resolve_destination(
            source=None,
            output_path=None,
            tag="result",
            suffix=".json",
            base_dir=self.root,
        )

        self.assertEqual(destination, (self.root / "result.json").resolve())

    def test_explicit_destination_rejects_existing_sentinel(self):
        destination = self.root / "result.json"
        destination.write_text("do-not-replace", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "overwrite"):
            artifact_safety.resolve_destination(
                source=None,
                output_path=str(destination),
                tag="result",
                suffix=".json",
            )

        self.assertEqual(destination.read_text(encoding="utf-8"), "do-not-replace")

    def test_publish_race_preserves_competing_destination(self):
        staged = self.root / ".result.tmp"
        staged.write_text("ours", encoding="utf-8")
        destination = self.root / "result.txt"

        def competing_link(_source, target):
            Path(target).write_text("competitor", encoding="utf-8")
            raise FileExistsError(target)

        with mock.patch("cdxml_toolkit.mcp_runtime.artifact_safety.os.link", side_effect=competing_link):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                artifact_safety.publish_file(staged, destination)

        self.assertEqual(destination.read_text(encoding="utf-8"), "competitor")

    def test_batch_publish_rolls_back_earlier_outputs(self):
        first_stage = self.root / ".first.tmp"
        second_stage = self.root / ".second.tmp"
        first_stage.write_text("first", encoding="utf-8")
        second_stage.write_text("second", encoding="utf-8")
        first = self.root / "first.txt"
        second = self.root / "second.txt"

        real_publish = artifact_safety.publish_file

        def publish(source, destination):
            if Path(destination) == second:
                second.write_text("competitor", encoding="utf-8")
                raise ValueError("Refusing to overwrite an existing file")
            return real_publish(source, destination)

        with mock.patch("cdxml_toolkit.mcp_runtime.artifact_safety.publish_file", side_effect=publish):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                artifact_safety.publish_files(
                    [(first_stage, first), (second_stage, second)]
                )

        self.assertFalse(first.exists())
        self.assertEqual(second.read_text(encoding="utf-8"), "competitor")

    def test_publish_directory_retries_transient_permission_error(self):
        staged = self.root / ".inspection.tmp"
        staged.mkdir()
        (staged / "manifest.json").write_text("{}", encoding="ascii")
        destination = self.root / "inspection"
        real_rename = Path.rename
        attempts = 0

        def flaky_rename(source, target):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise PermissionError(5, "temporarily unavailable", str(source))
            return real_rename(source, target)

        with mock.patch.object(Path, "rename", autospec=True, side_effect=flaky_rename):
            artifact_safety.publish_directory(staged, destination)

        self.assertEqual(attempts, 2)
        self.assertEqual(
            (destination / "manifest.json").read_text(encoding="ascii"), "{}"
        )

    def test_publish_directory_preserves_competing_destination(self):
        staged = self.root / ".inspection.tmp"
        staged.mkdir()
        (staged / "manifest.json").write_text("ours", encoding="ascii")
        destination = self.root / "inspection"

        def competing_rename(_source, target):
            Path(target).mkdir()
            (Path(target) / "manifest.json").write_text(
                "competitor", encoding="ascii"
            )
            raise PermissionError(5, "temporarily unavailable", str(target))

        with mock.patch.object(
            Path, "rename", autospec=True, side_effect=competing_rename
        ):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                artifact_safety.publish_directory(staged, destination)

        self.assertEqual(
            (destination / "manifest.json").read_text(encoding="ascii"),
            "competitor",
        )
        self.assertTrue(staged.exists())

    def test_artifact_record_contains_absolute_path_size_and_sha256(self):
        output = self.root / "artifact.bin"
        output.write_bytes(b"artifact-data")

        record = artifact_safety.artifact_record(output)

        self.assertEqual(record["path"], str(output.resolve()))
        self.assertEqual(record["bytes"], len(b"artifact-data"))
        self.assertEqual(
            record["sha256"], hashlib.sha256(b"artifact-data").hexdigest()
        )


class OfficialArtifactAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_draw_molecule_rejects_existing_output_before_upstream_call(self):
        output = self.root / "molecule.cdxml"
        output.write_text("sentinel", encoding="utf-8")

        with mock.patch(
            "cdxml_toolkit.mcp_server.server.draw_molecule"
        ) as upstream:
            with self.assertRaisesRegex(ValueError, "overwrite"):
                official_overrides.draw_molecule(
                    {"smiles": "CCO"}, output_path=str(output)
                )

        upstream.assert_not_called()
        self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")

    def test_draw_molecule_stages_and_reports_verified_artifact(self):
        output = self.root / "molecule.cdxml"

        def draw(_mol, output_path=None):
            Path(output_path).write_text(MINIMAL_CDXML, encoding="utf-8")
            return {"ok": True, "output_path": output_path, "size": 1}

        with mock.patch(
            "cdxml_toolkit.mcp_server.server.draw_molecule", side_effect=draw
        ), mock.patch(
            "cdxml_toolkit.mcp_runtime.structure_fidelity.repair_and_validate_drawn_cdxml",
            return_value={"status": "preserved"},
        ):
            result = official_overrides.draw_molecule(
                {"smiles": "CCO"}, output_path=str(output)
            )

        self.assertEqual(result["output_path"], str(output.resolve()))
        self.assertEqual(result["size"], output.stat().st_size)
        self.assertEqual(result["metadata"]["artifacts"][0]["path"], str(output.resolve()))
        self.assertEqual(
            result["metadata"]["artifacts"][0]["sha256"],
            hashlib.sha256(output.read_bytes()).hexdigest(),
        )

    def test_draw_molecule_preserves_upstream_stringified_json_input(self):
        output = self.root / "molecule.cdxml"

        def draw(mol_json, output_path=None):
            self.assertIsInstance(mol_json, str)
            Path(output_path).write_text(MINIMAL_CDXML, encoding="utf-8")
            return {"ok": True, "output_path": output_path}

        with mock.patch(
            "cdxml_toolkit.mcp_server.server.draw_molecule", side_effect=draw
        ), mock.patch(
            "cdxml_toolkit.mcp_runtime.structure_fidelity.repair_and_validate_drawn_cdxml",
            return_value={"status": "preserved"},
        ):
            result = official_overrides.draw_molecule(
                '{"smiles":"CCO"}', output_path=str(output)
            )

        self.assertTrue(result["ok"])
        self.assertTrue(output.is_file())

    def test_draw_molecule_calls_raw_function_beneath_mcp_json_wrapper(self):
        output = self.root / "molecule.cdxml"

        def raw(_mol, output_path=None):
            Path(output_path).write_text(MINIMAL_CDXML, encoding="utf-8")
            return {"ok": True, "output_path": output_path}

        def decorated(*args, **kwargs):
            return "serialized MCP result"

        decorated.__wrapped__ = raw
        with mock.patch(
            "cdxml_toolkit.mcp_server.server.draw_molecule", new=decorated
        ), mock.patch(
            "cdxml_toolkit.mcp_runtime.structure_fidelity.repair_and_validate_drawn_cdxml",
            return_value={"status": "preserved"},
        ):
            result = official_overrides.draw_molecule(
                {"smiles": "CCO"}, output_path=str(output)
            )

        self.assertTrue(result["ok"])
        self.assertTrue(output.is_file())

    def test_extract_office_rolls_back_when_any_object_fails(self):
        office = self.root / "source.pptx"
        office.write_bytes(b"office fixture")
        destination = self.root / "objects"

        def extract(_file_path, output_dir=None, output_format=None):
            stage = Path(output_dir)
            good = stage / "object_1.cdxml"
            good.parent.mkdir(parents=True, exist_ok=True)
            good.write_text(MINIMAL_CDXML, encoding="utf-8")
            return [
                types.SimpleNamespace(
                    source_path="ppt/embeddings/oleObject1.bin",
                    cdxml_output=str(good),
                    cdx_output=None,
                    error=None,
                ),
                types.SimpleNamespace(
                    source_path="ppt/embeddings/oleObject2.bin",
                    cdxml_output=None,
                    cdx_output=None,
                    error="conversion failed",
                ),
            ]

        with mock.patch.object(ole_extractor, "extract_from_office", side_effect=extract):
            result = official_overrides.extract_cdxml_from_office(
                str(office), output_dir=str(destination)
            )

        self.assertFalse(result["ok"])
        self.assertIn("conversion failed", result["error"])
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
