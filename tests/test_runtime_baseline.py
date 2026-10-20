import importlib.util
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skill/chemdraw/scripts/install_runtime.py'
TOOLKIT = ROOT / 'toolkit'


class RuntimeBaselineTests(unittest.TestCase):
    def installer(self):
        spec = importlib.util.spec_from_file_location('install_runtime', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def baseline(self):
        return json.loads((SCRIPT.parents[1] / 'runtime.json').read_text(encoding='utf-8'))

    def test_toolkit_source_is_part_of_this_repository(self):
        self.assertTrue((TOOLKIT / 'pyproject.toml').is_file())
        self.assertTrue((TOOLKIT / 'cdxml_toolkit' / 'mcp_runtime').is_dir())
        self.assertTrue((TOOLKIT / 'LICENSE').is_file(), 'the original MIT notice must stay with the code')

    def test_runtime_json_points_at_this_repository_and_matches_the_toolkit_version(self):
        baseline = self.baseline()
        self.assertEqual(baseline['repository'], 'https://github.com/ZiChenWang114514/chemdraw-skill.git')
        self.assertEqual(baseline['subdirectory'], 'toolkit')
        self.assertRegex(baseline['commit'], r'^[0-9a-f]{40}$')
        pyproject = (TOOLKIT / 'pyproject.toml').read_text(encoding='utf-8')
        version = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
        self.assertEqual(baseline['toolkit_version'], version)
        init = (TOOLKIT / 'cdxml_toolkit' / '__init__.py').read_text(encoding='utf-8')
        self.assertIn(f'"{version}"', init)

    def test_a_checkout_installs_its_own_toolkit_folder(self):
        module = self.installer()
        requirement = module.requirement(['office', 'publication'])
        self.assertEqual(requirement, str(TOOLKIT.resolve()) + '[office,publication]')
        with patch.object(module.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(module.main(['--extras', 'office', 'publication']), 0)
        self.assertEqual(run.call_args.args[0][-1], requirement)

    def test_an_installed_copy_uses_the_pinned_repository_subdirectory(self):
        module = self.installer()
        baseline = self.baseline()
        with patch.object(module, 'local_toolkit', return_value=None):
            requirement = module.requirement(['office'])
        self.assertEqual(requirement, 'cdxml-toolkit-community[office] @ git+' + baseline['repository'] + '@'
                         + baseline['commit'] + '#subdirectory=toolkit')

    def test_explicit_toolkit_path_wins(self):
        module = self.installer()
        self.assertEqual(module.requirement([], str(TOOLKIT)), str(TOOLKIT.resolve()))

    def test_docs_and_ci_use_the_same_install_entrypoint(self):
        for name in ['docs/guide.md', 'docs/guide.zh-cn.md', '.github/workflows/validate.yml']:
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertIn('skill/chemdraw/scripts/install_runtime.py', text, name)
            self.assertNotRegex(text, r'\.git@[a-f0-9]{40}', name)

    def test_nothing_points_at_the_retired_toolkit_repository(self):
        retired = 'cdxml-toolkit-community.git'
        for name in ['README.md', 'README.zh-cn.md', 'docs/guide.md', 'docs/guide.zh-cn.md',
                     'skill/chemdraw/runtime.json', '.github/workflows/validate.yml']:
            self.assertNotIn(retired, (ROOT / name).read_text(encoding='utf-8'), name)
        for name in ['README.md', 'README.zh-cn.md']:
            self.assertNotIn('ZiChenWang114514/cdxml-toolkit-community/', (ROOT / name).read_text(encoding='utf-8'), name)

    def test_printing_requirement_does_not_install(self):
        module = self.installer()
        with patch.object(module.subprocess, 'run') as run:
            self.assertEqual(module.main(['--print-requirement']), 0)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
