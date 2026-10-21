from pathlib import Path
import subprocess
import sys


def test_rebuild_optimized_failure_does_not_publish(tmp_path):
    script = Path(__file__).resolve().parents[1]/'examples/paper-reconstructions/rebuild.py'
    output = tmp_path/'output'
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
    result = subprocess.run([sys.executable, '-O', '-c', code, str(script), str(output)],
        capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert 'assembly changed inventory' in result.stderr
    assert not output.exists()
