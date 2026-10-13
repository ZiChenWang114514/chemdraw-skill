import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skill/chemdraw/scripts/install_runtime.py'


class RuntimeBaselineTests(unittest.TestCase):
    def installer(self):
        spec = importlib.util.spec_from_file_location('install_runtime', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_install_command_uses_the_bundled_exact_commit(self):
        module = self.installer()
        baseline = json.loads((SCRIPT.parents[1] / 'runtime.json').read_text())
        requirement = module.requirement(['office', 'publication'])
        self.assertEqual(requirement, 'cdxml-toolkit-community[office,publication] @ git+' +
                         baseline['repository'] + '@' + baseline['commit'])
        self.assertRegex(baseline['commit'], r'^[0-9a-f]{40}$')
        with patch.object(module.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(module.main(['--extras', 'office', 'publication']), 0)
        self.assertEqual(run.call_args.args[0][-1], requirement)

    def test_docs_and_ci_use_the_same_install_entrypoint(self):
        for name in ['docs/guide.md', 'docs/guide.zh-cn.md', '.github/workflows/validate.yml']:
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertIn('skill/chemdraw/scripts/install_runtime.py', text, name)
            self.assertNotRegex(text, r'cdxml-toolkit-community\.git@[a-f0-9]{40}', name)

    def test_printing_requirement_does_not_install(self):
        module = self.installer()
        with patch.object(module.subprocess, 'run') as run:
            self.assertEqual(module.main(['--print-requirement']), 0)
            run.assert_not_called()
