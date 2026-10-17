from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

import smoke_test


class SmokeScriptTests(unittest.TestCase):
    def test_smoke_is_offline_and_compares_stereoisomers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "smoke"

            def render(source: Path, destination: Path):
                text = source.read_text(encoding="utf-8")
                color = "black" if "WedgedHash" in text else "white"
                Image.new("RGB", (64, 48), color).save(destination)
                return {"ok": True, "output": str(destination)}

            with mock.patch.object(
                smoke_test, "render_with_timeout", side_effect=render
            ), mock.patch(
                "sys.argv", ["smoke_test.py", "--output-dir", str(output)]
            ), redirect_stdout(io.StringIO()) as captured:
                code = smoke_test.main()

            self.assertEqual(code, 0)
            self.assertIn('"ok": true', captured.getvalue())
            self.assertTrue((output / "aspirin.cdxml").is_file())
            self.assertTrue((output / "aspirin.png").is_file())
            self.assertNotEqual(
                (output / "stereoisomer-1.cdxml").read_bytes(),
                (output / "stereoisomer-2.cdxml").read_bytes(),
            )
            self.assertNotEqual(
                (output / "stereoisomer-1.png").read_bytes(),
                (output / "stereoisomer-2.png").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
