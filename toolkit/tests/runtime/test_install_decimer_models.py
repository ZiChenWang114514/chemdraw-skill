from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from cdxml_toolkit.mcp_runtime import install_decimer_models
def model_fixture(payload: bytes) -> dict[str, str]:
    return {
        "key": "standard",
        "name": "DECIMER",
        "url": "https://example.invalid/models.zip",
        "md5": hashlib.md5(payload).hexdigest(),
        "marker": "DECIMER_model/saved_model.pb",
    }


def archive_bytes(root: Path, content: bytes = b"model") -> bytes:
    archive = root / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("DECIMER_model/saved_model.pb", content)
        bundle.writestr("DECIMER_model/assets/tokenizer_SMILES.pkl", b"tokenizer")
    return archive.read_bytes()


class DecimerInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "models"

    def tearDown(self):
        self.temp.cleanup()

    def test_model_install_is_staged_verified_and_records_sha256(self):
        payload = archive_bytes(self.root)
        model = model_fixture(payload)

        def download(_url, destination, _proxy):
            Path(destination).write_bytes(payload)

        result = install_decimer_models.install_model(
            model, self.target, proxy=None, downloader=download
        )

        marker = self.target / model["marker"]
        receipt = marker.parent / ".model.json"
        self.assertTrue(marker.is_file())
        self.assertTrue(receipt.is_file())
        metadata = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(metadata["md5"], model["md5"])
        self.assertEqual(metadata["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["sha256"], metadata["sha256"])
        self.assertEqual(list(self.target.parent.glob(".decimer-install-*")), [])

    def test_checksum_failure_leaves_no_partial_model(self):
        payload = archive_bytes(self.root)
        model = model_fixture(payload)
        model["md5"] = "0" * 32

        with self.assertRaisesRegex(RuntimeError, "MD5"):
            install_decimer_models.install_model(
                model,
                self.target,
                proxy=None,
                downloader=lambda _url, destination, _proxy: Path(destination).write_bytes(payload),
            )

        self.assertFalse((self.target / "DECIMER_model").exists())
        self.assertEqual(list(self.target.parent.glob(".decimer-install-*")), [])

    def test_failed_reinstall_preserves_existing_incomplete_directory(self):
        existing = self.target / "DECIMER_model"
        existing.mkdir(parents=True)
        sentinel = existing / "keep.txt"
        sentinel.write_text("existing", encoding="utf-8")
        payload = archive_bytes(self.root)
        model = model_fixture(payload)

        with mock.patch.object(
            install_decimer_models,
            "safe_extract",
            side_effect=RuntimeError("extract failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "extract failed"):
                install_decimer_models.install_model(
                    model,
                    self.target,
                    proxy=None,
                    downloader=lambda _url, destination, _proxy: Path(destination).write_bytes(payload),
                )

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing")

    def test_model_selection_is_explicit(self):
        selected = install_decimer_models.select_models(["handdrawn"])
        self.assertEqual([model["key"] for model in selected], ["handdrawn"])
        with self.assertRaisesRegex(ValueError, "unknown"):
            install_decimer_models.select_models(["unknown"])


if __name__ == "__main__":
    unittest.main()
