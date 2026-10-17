"""Unified CLI, ACS-1996 builder and installation-manifest contracts."""
import json
import re
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock
import xml.etree.ElementTree as ET

import pytest

import acs_builder
import cdx
import check_installation

SKILL_ROOT = Path(__file__).resolve().parents[1]


def test_call_uses_registered_timeout(tmp_path):
    from cdxml_toolkit.mcp_runtime import mcp_server
    with mock.patch.object(mcp_server, '_execute_worker_process',
                           return_value=(0, b'{"ok":true,"result":{"ok":true}}', b'')) as process:
        cdx.main(['call', 'modify_molecule', '--json', '{}', '--out', str(tmp_path / 'r.json')])
    assert process.call_args.kwargs['timeout_seconds'] == 90


def test_large_result_goes_to_evidence_file_and_summary_is_small(tmp_path, capsys):
    result = {'ok': True, 'result': {'ok': True, 'raw_response': 'x' * 40000, 'warnings': ['Inspect chirality']}}
    with mock.patch.object(cdx, '_worker', return_value=result):
        cdx.main(['call', 'extract_structures_via_decimer_api', '--json', '{}', '--out', str(tmp_path / 'e.json')])
    summary = json.loads(capsys.readouterr().out)
    assert summary['warning_count'] == 1 and summary['evidence'].endswith('e.json')
    assert 'raw_response' not in json.dumps(summary)
    assert json.loads((tmp_path / 'e.json').read_text(encoding='utf-8')) == result


def test_existing_evidence_file_is_refused(tmp_path):
    target = tmp_path / 'e.json'
    target.write_text('{}')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}), pytest.raises(SystemExit):
        cdx.main(['call', 'modify_molecule', '--json', '{}', '--out', str(target)])


def test_nested_failure_is_reported(tmp_path, capsys):
    result = {'ok': True, 'result': json.dumps({'ok': False, 'error': 'bad input'})}
    with mock.patch.object(cdx, '_worker', return_value=result):
        code = cdx.main(['call', 'modify_molecule', '--json', '{}', '--out', str(tmp_path / 'e.json')])
    assert code == 1
    assert json.loads(capsys.readouterr().out)['error'] == 'bad input'


def test_render_replaces_previous_png(tmp_path, capsys):
    src = tmp_path / 'a.cdxml'
    src.write_text('<CDXML/>')
    old = tmp_path / 'a.png'
    old.write_bytes(b'old')
    seen = {}

    def fake(tool, kwargs, args=()):
        seen['existed'] = Path(kwargs['output_path']).exists()
        Path(kwargs['output_path']).write_bytes(b'new')
        return {'ok': True, 'result': {'ok': True}}
    with mock.patch.object(cdx, '_worker', side_effect=fake):
        assert cdx.main(['render', str(src)]) == 0
    assert seen['existed'] is False and old.read_bytes() == b'new'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['a.cdxml', 'a.png']


def test_failed_render_keeps_previous_png(tmp_path, capsys):
    src = tmp_path / 'a.cdxml'
    src.write_text('<CDXML/>')
    (tmp_path / 'a.png').write_bytes(b'old')
    with mock.patch.object(cdx, '_worker', return_value={'ok': False, 'error': 'COM failure'}):
        assert cdx.main(['render', str(src)]) == 1
    assert (tmp_path / 'a.png').read_bytes() == b'old'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['a.cdxml', 'a.png']


def test_sig_prints_one_section(capsys):
    cdx.main(['sig', 'render_cdxml_files'])
    out = capsys.readouterr().out
    assert out.startswith('### `render_cdxml_files(') and '### `' not in out[5:]


def _isolated_copy(tmp_path):
    scripts = tmp_path / 'skills' / 'chemdraw' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'cdx.py').write_bytes((SKILL_ROOT / 'scripts' / 'cdx.py').read_bytes())
    env = {k: v for k, v in os.environ.items() if k not in ('CHEMDRAW_MCP_PYTHON', cdx.REEXEC_FLAG)}
    env.update(USERPROFILE=str(tmp_path), HOME=str(tmp_path), LOCALAPPDATA=str(tmp_path / 'data'),
               XDG_DATA_HOME=str(tmp_path / 'data'))
    return scripts / 'cdx.py', env


def test_without_runtime_the_message_names_the_search_locations(tmp_path):
    script, env = _isolated_copy(tmp_path)
    proc = subprocess.run([sys.executable, '-I', '-S', str(script), 'tools'],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 2
    assert 'CHEMDRAW_MCP_PYTHON' in proc.stderr and 'chemdraw-venv' in proc.stderr


def test_any_python_relaunches_into_the_runtime(tmp_path):
    script, env = _isolated_copy(tmp_path)
    env['CHEMDRAW_MCP_PYTHON'] = sys.executable
    # -S hides site-packages, so this interpreter cannot import the toolkit itself.
    proc = subprocess.run([sys.executable, '-I', '-S', str(script), 'tools', '--detail', 'summary'],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith('39 tools')


def test_sibling_venv_is_a_runtime_candidate(tmp_path, monkeypatch):
    venv = tmp_path / 'chemdraw-venv'
    (venv / 'Scripts').mkdir(parents=True)
    (venv / 'Scripts' / 'python.exe').write_bytes(b'')
    (venv / 'Lib' / 'site-packages' / 'cdxml_toolkit' / 'mcp_runtime').mkdir(parents=True)
    monkeypatch.setattr(cdx, 'SKILL_ROOT', tmp_path / 'chemdraw')
    monkeypatch.delenv('CHEMDRAW_MCP_PYTHON', raising=False)
    monkeypatch.setattr(cdx.Path, 'home', lambda: tmp_path)
    found = cdx.runtime_candidates()
    assert found[0][0] == 'chemdraw-venv' and cdx._has_toolkit(found[0][1])


def _fake_env(root):
    python = root / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    python.parent.mkdir(parents=True)
    python.write_bytes(b'')
    return python


def test_shared_venv_and_local_config_are_runtime_candidates(tmp_path, monkeypatch):
    monkeypatch.setattr(cdx, 'SKILL_ROOT', tmp_path / 'skills' / 'chemdraw')
    monkeypatch.setattr(cdx, 'LOCAL_CONFIG', tmp_path / 'skills' / 'chemdraw' / 'runtime.local.json')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'data'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    monkeypatch.delenv('CHEMDRAW_MCP_PYTHON', raising=False)
    monkeypatch.setattr(cdx.Path, 'home', lambda: tmp_path)
    shared = _fake_env(tmp_path / 'data' / 'chemdraw-skill' / 'venv')
    assert cdx.default_runtime_dir() == tmp_path / 'data' / 'chemdraw-skill' / 'venv'
    assert cdx.runtime_candidates() == [('shared venv', shared)]
    custom = _fake_env(tmp_path / 'elsewhere')
    cdx.LOCAL_CONFIG.parent.mkdir(parents=True)
    cdx.LOCAL_CONFIG.write_text(json.dumps({'runtime_python': str(custom)}), encoding='utf-8')
    assert [s for s, _ in cdx.runtime_candidates()] == ['runtime.local.json', 'shared venv']


def test_py_passes_arguments_to_the_runtime(capfd):
    assert cdx.main(['py', '-c', 'import cdxml_toolkit, sys; print("rt-ok", sys.argv[1:])', 'x']) == 0
    assert "rt-ok ['x']" in capfd.readouterr().out


def test_builder_spec_writes_acs1996_cdxml(tmp_path):
    spec = tmp_path / 's.json'
    spec.write_text(json.dumps({'objects': [
        {'type': 'molecule', 'smiles': '[*:1]CC(=O)O', 'labels': {'1': 'C10H21'}},
        {'type': 'text', 'at': [100, 140], 'text': '{b:A}\uff08\u6ce8\uff09'},
        {'type': 'arrow', 'from': [150, 100], 'to': [200, 100]}]}), encoding='utf-8')
    out = acs_builder.build_from_spec(spec, tmp_path / 'o.cdxml')
    root = ET.parse(out).getroot()
    assert root.get('BondLength') == '14.4' and root.get('LineWidth') == '0.6'
    nick = root.find('.//n[@NodeType="GenericNickname"]')
    assert nick.get('GenericNickname') == 'C10H21'
    assert [s.text for s in nick.iter('s')][:2] in (['C', '10'], ['H', '21'])
    assert any(s.get('font') == '5' for s in root.iter('s'))


def test_manifest_ignores_line_endings(tmp_path):
    (tmp_path / 'a.md').write_bytes(b'x\ny\n')
    (tmp_path / 'b.png').write_bytes(b'\r\n')
    check_installation.write_manifest(tmp_path)
    (tmp_path / 'a.md').write_bytes(b'x\r\ny\r\n')
    assert check_installation.check_manifest(tmp_path)['ok']
    (tmp_path / 'b.png').write_bytes(b'\n')
    assert check_installation.check_manifest(tmp_path)['modified'] == ['b.png']


def test_skill_instructions_are_client_neutral():
    # Agent product names belong only in the per-agent installation guide.
    brands = re.compile(r'\b(claude|co' + r'dex|open' + r'ai|gemini|copilot|opencode)\b|\bCursor\b|\.cursor/', re.I)
    hits = [p.relative_to(SKILL_ROOT).as_posix() for p in SKILL_ROOT.rglob('*')
            if p.is_file() and p.suffix in {'.md', '.py', '.json', '.ps1', '.yaml', '.cdxml', '.csv'}
            and '__pycache__' not in p.parts and p.name not in {'manifest.json', 'agent-integration.md', 'test_cdx.py'}
            and brands.search(p.read_text(encoding='utf-8', errors='ignore').replace('$cursor', ''))]
    assert hits == []
    assert not (SKILL_ROOT / 'agents').exists(), 'no client-specific adapter folders'


def test_only_cjk_characters_switch_font():
    xml = acs_builder.runs('EtOH\uff0c25 \u00b0C {b:K}')
    runs = ET.fromstring(f'<t>{xml}</t>').findall('s')
    assert [(s.text, s.get('font')) for s in runs] == [
        ('EtOH', '3'), ('\uff0c', '5'), ('25 \u00b0C ', '3'), ('K', '3')]


def test_loop_guard_is_not_inherited_by_children(monkeypatch):
    monkeypatch.setenv(cdx.REEXEC_FLAG, '1')
    cdx._ensure_runtime([])
    assert cdx.REEXEC_FLAG not in os.environ
