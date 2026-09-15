import importlib.util
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


class InstalledBundleTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('cdxml_toolkit'), 'toolkit required for example execution')
    def test_replay_output_and_preserve_existing_directory(self):
        script = ROOT/'skill/chemdraw/assets/paper-replica/example/replay.py'
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'example'
            result = subprocess.run([sys.executable, '-B', str(script), str(out)], capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            original = (out/'figure.cdxml').read_bytes()
            result = subprocess.run([sys.executable, '-B', str(script), str(out)], capture_output=True, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((out/'figure.cdxml').read_bytes(), original)

    @unittest.skipUnless(importlib.util.find_spec('cdxml_toolkit'), 'toolkit required for example execution')
    def test_rebuild_validation_survives_optimization(self):
        script = ROOT/'skill/chemdraw/assets/paper-reconstructions/rebuild.py'
        code = '''
import runpy, sys
from pathlib import Path
from collections import Counter
import cdxml_toolkit.chemistry_semantics as chemistry
original = chemistry.document_inventory
def broken(path):
    if Path(path).name.startswith('synthesis-'):
        return Counter({'corrupted':1})
    return original(path)
chemistry.document_inventory = broken
sys.argv = [sys.argv[1], sys.argv[2]]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'example'
            result = subprocess.run([sys.executable, '-O', '-c', code, str(script), str(out)],
                                    capture_output=True, text=True, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('assembly changed inventory', result.stderr)
            self.assertFalse(out.exists())

    def test_drift_and_cache_exclusions(self):
        spec = importlib.util.spec_from_file_location('check_installation', ROOT/'skill/chemdraw/scripts/check_installation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            source, installed = Path(folder)/'source', Path(folder)/'installed'
            source.mkdir(); installed.mkdir()
            (source/'missing').write_text('a')
            (source/'changed').write_text('a'); (installed/'changed').write_text('b')
            (installed/'extra').write_text('c')
            (installed/'__pycache__').mkdir()
            (installed/'__pycache__/ignored.pyc').write_bytes(b'cache')
            result = module.compare_trees(source, installed)
            self.assertEqual(result['missing'], ['missing'])
            self.assertEqual(result['modified'], ['changed'])
            self.assertEqual(result['extra'], ['extra'])
            self.assertFalse(result['ok'])

    def test_example_contract(self):
        spec = importlib.util.spec_from_file_location('check_installation', ROOT/'skill/chemdraw/scripts/check_installation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.check_examples(ROOT/'skill/chemdraw'), [])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            example = root/'assets/paper-replica/example'
            example.mkdir(parents=True)
            (example/'replay.py').write_text("print('wrong.cdxml')")
            errors = module.check_examples(root)
            self.assertTrue(any('figure.json' in e for e in errors))
            self.assertTrue(any('figure.cdxml' in e for e in errors))
