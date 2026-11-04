from __future__ import annotations

import re
from pathlib import Path
import unittest

import smoke_all_tools

SIGNATURES = Path(__file__).resolve().parents[1] / 'references' / 'mcp-signatures.md'


class SmokeCaseTests(unittest.TestCase):
    def test_every_documented_tool_has_a_smoke_case(self):
        documented = set(re.findall(r'^### `(\w+)\(', SIGNATURES.read_text(encoding='utf-8'), re.M))
        covered = {case['tool'] for case in smoke_all_tools.CASES}
        self.assertEqual(sorted(documented - covered), [], 'tools without a smoke case')
        self.assertEqual(sorted(covered - documented), [], 'smoke cases for tools that are not documented')

    def test_needs_are_ones_the_context_understands(self):
        known = {'chemdraw', 'chemscript', 'network', 'lcms', 'lcms2', 'ocsr'}
        for case in smoke_all_tools.CASES:
            for need in case.get('needs', []):
                self.assertTrue(need in known or need.startswith('engine:'), (case['tool'], need))

    def test_a_missing_need_skips_the_case_with_its_reason(self):
        ctx = smoke_all_tools.Context(Path('.'), False, [], {'chemdraw': False}, {})
        rows = smoke_all_tools.run(ctx, [{'tool': 'render_to_png', 'needs': ['chemdraw'], 'args': {}}])
        self.assertEqual(rows, [{'case': 1, 'tool': 'render_to_png', 'status': 'skipped', 'reason': 'needs chemdraw'}])


if __name__ == '__main__':
    unittest.main()
