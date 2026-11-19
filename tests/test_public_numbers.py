"""Numbers quoted on public pages are the repository's own counts."""

from __future__ import annotations

import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import public_numbers  # noqa: E402


# The counts come from the toolkit; the portable job has no runtime, the runtime job runs this file.
@unittest.skipUnless(find_spec("rdkit") and find_spec("cdxml_toolkit") and find_spec("mcp"),
                     "needs the toolkit runtime (RDKit, MCP and cdxml_toolkit)")
class PublicNumberTests(unittest.TestCase):
    def test_every_quoted_number_matches_the_repository(self):
        self.assertEqual(public_numbers.wrong_claims(), [])

    def test_a_stale_number_is_reported(self):
        numbers = {**public_numbers.counts(), "house_styles": 1}
        self.assertTrue(any("house_styles is 1" in line for line in public_numbers.wrong_claims(numbers)))

    def test_every_claim_form_is_quoted_somewhere(self):
        import re

        text = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in public_numbers.PAGES)
        self.assertEqual([pattern for pattern, _ in public_numbers.CLAIMS if not re.search(pattern, text)], [])


if __name__ == "__main__":
    unittest.main()
