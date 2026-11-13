"""Unified CLI, ACS-1996 builder and installation-manifest contracts."""
import argparse
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


def test_args_and_json_each_take_inline_json_or_a_file(tmp_path):
    arguments = tmp_path / 'a.json'
    arguments.write_text('﻿{"x": 1}', encoding='utf-8')
    def load(**given):
        return cdx._load_args(argparse.Namespace(**{'json': None, 'args': None, **given}))

    assert load(args='{"x": 1}') == {'x': 1}
    assert load(json=str(arguments)) == {'x': 1}
    assert load(args=str(arguments)) == {'x': 1}
    assert load(json='{"y": 2}') == {'y': 2}
    assert load() == {}


def test_arguments_that_are_neither_json_nor_a_file_get_a_plain_message(tmp_path):
    ns = argparse.Namespace(json=None, args=str(tmp_path / 'missing.json'))
    with pytest.raises(SystemExit) as error:
        cdx._load_args(ns)
    assert '--json' in str(error.value) and 'missing.json' in str(error.value)


def test_broken_json_arguments_get_a_plain_message():
    with pytest.raises(SystemExit) as error:
        cdx._load_args(argparse.Namespace(json='{bad', args=None))
    assert 'not valid JSON' in str(error.value) and '{bad' in str(error.value)


def test_broken_json_in_a_file_names_the_file(tmp_path):
    arguments = tmp_path / 'a.json'
    arguments.write_text('{bad', encoding='utf-8')
    with pytest.raises(SystemExit) as error:
        cdx._load_args(argparse.Namespace(json=str(arguments), args=None))
    assert 'a.json' in str(error.value) and 'not valid JSON' in str(error.value)


@pytest.mark.parametrize('task, field, words', [
    ('products', 'reactants', 'cdx.py predict products'),
    ('retro', 'product', 'cdx.py predict retro'),
    ('nmr', 'smiles', 'cdx.py predict nmr'),
    ('conditions', 'reactants', '--products'),
])
def test_predict_without_a_molecule_shows_an_example_instead_of_a_python_error(task, field, words):
    with mock.patch.object(cdx, '_worker') as worker, pytest.raises(SystemExit) as error:
        cdx.main(['predict', task])
    assert words in str(error.value) and not worker.called


def test_predict_conditions_needs_the_product_as_well():
    with mock.patch.object(cdx, '_worker') as worker, pytest.raises(SystemExit) as error:
        cdx.main(['predict', 'conditions', 'CCO'])
    assert '--products' in str(error.value) and not worker.called


def test_predict_conditions_takes_the_product_as_a_flag(capsys):
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
        cdx.main(['predict', 'conditions', 'CCO.CC(=O)O', '--products', 'CCOC(C)=O', '--engine', 'reacon'])
    assert worker.call_args.args == ('predict_conditions',
                                     {'reactants': 'CCO.CC(=O)O', 'products': 'CCOC(C)=O', 'engine': 'reacon'})


def test_predict_products_flag_is_refused_outside_conditions():
    with mock.patch.object(cdx, '_worker') as worker, pytest.raises(SystemExit) as error:
        cdx.main(['predict', 'nmr', 'CCO', '--products', 'CC'])
    assert 'predict conditions' in str(error.value) and not worker.called


def test_predict_json_gets_the_same_handling_as_call(tmp_path):
    arguments = tmp_path / 'a.json'
    arguments.write_text('{"steps": "multi"}', encoding='utf-8')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
        cdx.main(['predict', 'retro', 'CCO', '--json', str(arguments)])
    assert worker.call_args.args == ('predict_retrosynthesis', {'steps': 'multi', 'product': 'CCO'})
    with mock.patch.object(cdx, '_worker') as worker, pytest.raises(SystemExit) as error:
        cdx.main(['predict', 'retro', 'CCO', '--json', '{bad'])
    assert 'not valid JSON' in str(error.value) and not worker.called


def _message(capsys, *argv):
    """What the user reads when a command stops: one plain line, never a Python traceback."""
    with pytest.raises(SystemExit) as stopped:
        cdx.main(list(argv))
    assert isinstance(stopped.value.code, str)
    assert 'Traceback' not in stopped.value.code and '\n' not in stopped.value.code
    return stopped.value.code


def test_build_and_draw_name_a_missing_file(tmp_path, capsys):
    spec = str(tmp_path / 'missing.json')
    assert 'missing.json' in _message(capsys, 'build', spec, str(tmp_path / 'new.cdxml'))
    assert 'missing.json' in _message(capsys, 'draw', spec)


@pytest.mark.parametrize('text, words', [
    ('{bad', 'not valid JSON'),
    ('{}', 'objects'),
    ('{"objects": [{"type": "molecule"}]}', 'smiles'),
])
def test_build_explains_a_spec_it_cannot_use(tmp_path, capsys, text, words):
    spec = tmp_path / 'spec.json'
    spec.write_text(text, encoding='utf-8')
    target = tmp_path / 'new.cdxml'
    assert words in _message(capsys, 'build', str(spec), str(target))
    assert not target.exists()


def test_render_reports_a_missing_file_in_its_usual_line(tmp_path, capsys, render_log):
    with mock.patch.object(cdx, '_worker') as worker:
        assert cdx.main(['render', str(tmp_path / 'gone' / 'a.cdxml')]) == 1
    line = json.loads(capsys.readouterr().out)
    assert line['ok'] is False and line['png'] is None and 'not found' in line['error']
    assert not worker.called and not (tmp_path / 'gone').exists()


def test_a_missing_markush_image_leaves_no_folder_behind(tmp_path, capsys):
    work = tmp_path / 'run'
    assert 'a.png' in _message(capsys, 'markush', 'init', str(work), '--image', str(tmp_path / 'a.png'))
    assert not work.exists()


def test_a_markush_step_without_a_session_says_how_to_start_one(tmp_path, capsys):
    for action in ('next', 'status'):
        assert 'cdx.py markush init' in _message(capsys, 'markush', action, str(tmp_path / 'run'))


def test_markush_without_the_image_packages_says_what_is_missing(tmp_path, capsys):
    (tmp_path / 'state.json').write_text('{}', encoding='utf-8')
    with mock.patch.dict(sys.modules, {'cdxml_toolkit.markush.workflow': None}):
        message = _message(capsys, 'markush', 'status', str(tmp_path))
    assert 'image extra' in message


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


@pytest.fixture
def render_log(tmp_path, monkeypatch):
    """Keep the record of rendered PNGs out of the user's data folder."""
    log = tmp_path / 'state' / 'render-log.json'
    monkeypatch.setattr(cdx, 'render_log_path', lambda: log)
    return log


def _fake_render(content):
    def fake(tool, kwargs, args=()):
        Path(kwargs['output_path']).write_bytes(content)
        return {'ok': True, 'result': {'ok': True}}
    return fake


def test_render_replaces_a_png_it_rendered_before(tmp_path, render_log, capsys):
    src = tmp_path / 'a.cdxml'
    src.write_text('<CDXML/>')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_render(b'first')):
        assert cdx.main(['render', str(src)]) == 0
    seen = {}

    def fake(tool, kwargs, args=()):
        seen['existed'] = Path(kwargs['output_path']).exists()
        Path(kwargs['output_path']).write_bytes(b'second')
        return {'ok': True, 'result': {'ok': True}}
    with mock.patch.object(cdx, '_worker', side_effect=fake):
        assert cdx.main(['render', str(src)]) == 0
    assert seen['existed'] is False and (tmp_path / 'a.png').read_bytes() == b'second'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['a.cdxml', 'a.png', 'state']


def test_render_never_replaces_a_png_it_did_not_write(tmp_path, render_log, capsys):
    # The user's source screenshot often shares the stem of the reconstructed CDXML.
    src = tmp_path / 'scheme.cdxml'
    src.write_text('<CDXML/>')
    (tmp_path / 'scheme.png').write_bytes(b'source screenshot')
    with mock.patch.object(cdx, '_worker') as worker:
        assert cdx.main(['render', str(src)]) == 1
    worker.assert_not_called()
    assert (tmp_path / 'scheme.png').read_bytes() == b'source screenshot'
    report = json.loads(capsys.readouterr().out)
    assert report['ok'] is False and '--out-dir' in report['error'] and '--replace' in report['error']


def test_render_replace_flag_overrides_the_ownership_check(tmp_path, render_log, capsys):
    src = tmp_path / 'a.cdxml'
    src.write_text('<CDXML/>')
    (tmp_path / 'a.png').write_bytes(b'old')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_render(b'new')):
        assert cdx.main(['render', str(src), '--replace']) == 0
    assert (tmp_path / 'a.png').read_bytes() == b'new'


def test_render_refuses_two_inputs_with_the_same_png_name(tmp_path, render_log, capsys):
    (tmp_path / 'x').mkdir()
    (tmp_path / 'y').mkdir()
    for folder in ('x', 'y'):
        (tmp_path / folder / 'a.cdxml').write_text('<CDXML/>')
    with mock.patch.object(cdx, '_worker') as worker, pytest.raises(SystemExit) as exc:
        cdx.main(['render', str(tmp_path / 'x' / 'a.cdxml'), str(tmp_path / 'y' / 'a.cdxml'),
                  '--out-dir', str(tmp_path / 'out')])
    worker.assert_not_called()
    assert 'a.png' in str(exc.value)


def test_failed_render_keeps_previous_png(tmp_path, render_log, capsys):
    src = tmp_path / 'a.cdxml'
    src.write_text('<CDXML/>')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_render(b'old')):
        assert cdx.main(['render', str(src)]) == 0
    with mock.patch.object(cdx, '_worker', return_value={'ok': False, 'error': 'COM failure'}):
        assert cdx.main(['render', str(src)]) == 1
    assert (tmp_path / 'a.png').read_bytes() == b'old'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['a.cdxml', 'a.png', 'state']


def test_build_refuses_an_existing_output(tmp_path):
    spec = tmp_path / 's.json'
    spec.write_text(json.dumps({'objects': [{'type': 'text', 'at': [10, 10], 'text': 'A'}]}), encoding='utf-8')
    out = tmp_path / 'o.cdxml'
    out.write_text('<CDXML keep="1"/>')
    with pytest.raises(SystemExit):
        cdx.main(['build', str(spec), str(out)])
    assert out.read_text() == '<CDXML keep="1"/>'


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


def _isolated_copy_with_references(tmp_path):
    script, env = _isolated_copy(tmp_path)
    skill = script.parents[1]
    (skill / 'references').mkdir()
    for name in ('references/mcp-signatures.md', 'runtime.json'):
        (skill / name).write_bytes((SKILL_ROOT / name).read_bytes())
    return script, env


def test_sig_and_help_work_without_a_runtime(tmp_path):
    script, env = _isolated_copy_with_references(tmp_path)
    proc = subprocess.run([sys.executable, '-I', '-S', str(script), 'sig', 'render_cdxml_files'],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith('### `render_cdxml_files(')
    proc = subprocess.run([sys.executable, '-I', '-S', str(script), '--help'], capture_output=True, text=True, env=env)
    assert proc.returncode == 0 and 'doctor' in proc.stdout


def test_without_runtime_doctor_explains_how_to_install_one(tmp_path):
    script, env = _isolated_copy_with_references(tmp_path)
    proc = subprocess.run([sys.executable, '-I', '-S', str(script), 'doctor'], capture_output=True, text=True, env=env)
    assert proc.returncode == 2
    report = json.loads(proc.stdout)
    assert report['runtime'] == 'missing' and report['searched']
    text = json.dumps(report)
    # An installed copy has no repository installer: name the Skill's own route and the repository.
    assert 'install_runtime.py' in text and 'github.com' in text


def test_any_python_relaunches_into_the_runtime(tmp_path):
    script, env = _isolated_copy(tmp_path)
    env['CHEMDRAW_MCP_PYTHON'] = sys.executable
    # -S hides site-packages, so this interpreter cannot import the toolkit itself.
    proc = subprocess.run([sys.executable, '-I', '-S', str(script), 'tools', '--detail', 'summary'],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert re.match(r'\d+ tools: ', proc.stdout)


def test_sibling_venv_is_a_runtime_candidate(tmp_path, monkeypatch):
    venv = tmp_path / 'chemdraw-venv'
    (venv / 'Scripts').mkdir(parents=True)
    (venv / 'Scripts' / 'python.exe').write_bytes(b'')
    (venv / 'Lib' / 'site-packages' / 'cdxml_toolkit' / 'mcp_runtime').mkdir(parents=True)
    monkeypatch.setattr(cdx, 'SKILL_ROOT', tmp_path / 'chemdraw')
    monkeypatch.setattr(cdx, 'LOCAL_CONFIG', tmp_path / 'chemdraw' / 'runtime.local.json')
    monkeypatch.delenv('CHEMDRAW_MCP_PYTHON', raising=False)
    monkeypatch.setattr(cdx.Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(cdx, '_runs', lambda python, code, timeout: True)
    found = cdx.runtime_candidates()
    assert found[0][0] == 'chemdraw-venv' and cdx._has_toolkit(found[0][1])


def test_venv_whose_interpreter_does_not_start_is_skipped(tmp_path):
    # A site-packages match is not enough: the venv launcher must actually run
    # (base interpreter removed or blocked -> "Unable to create process").
    venv = tmp_path / 'chemdraw-venv'
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    python.parent.mkdir(parents=True)
    python.write_bytes(b'')
    for pattern in ('Lib/site-packages', 'lib/python3.12/site-packages'):
        (venv / pattern / 'cdxml_toolkit' / 'mcp_runtime').mkdir(parents=True)
    assert cdx._has_toolkit(python) is False


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
    # A root BoundingBox is required by Office embedding (OLE extent) and normal for ChemDraw files.
    x1, y1, x2, y2 = map(float, root.get('BoundingBox').split())
    xs = [float(n.get('p').split()[0]) for n in root.iter('n')]
    assert x1 < min(xs) and max(xs) < x2 and y1 < y2
    nick = root.find('.//n[@NodeType="GenericNickname"]')
    assert nick.get('GenericNickname') == 'C10H21'
    assert [s.text for s in nick.iter('s')][:2] in (['C', '10'], ['H', '21'])
    assert any(s.get('font') == '5' for s in root.iter('s'))
    # Page captions are annotations: ChemDraw must not turn a code such as "B" into a boron atom.
    page_text = root.find('page').findall('t')
    assert page_text and all(t.get('InterpretChemically') == 'no' for t in page_text)


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
            and '__pycache__' not in p.parts
            # manifest.json / runtime.local.json are per-machine files written by the installer.
            and p.name not in {'manifest.json', 'runtime.local.json', 'agent-integration.md', 'test_cdx.py'}
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


def test_doctor_paths_name_the_current_worker_log_folder(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    (tmp_path / 'chemdraw-skill' / 'logs').mkdir(parents=True)
    (tmp_path / 'OldClient' / 'chemdraw-mcp' / 'logs').mkdir(parents=True)
    logs = cdx.runtime_paths()['worker_logs']
    assert str(tmp_path / 'chemdraw-skill' / 'logs') in logs
    assert str(tmp_path / 'OldClient' / 'chemdraw-mcp' / 'logs') in logs


def _doctor(monkeypatch, capsys, fingerprint):
    monkeypatch.setattr(cdx, 'runtime_fingerprint', lambda: fingerprint)
    monkeypatch.setattr(cdx, '_signatures_current', lambda: True)
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'outputs': {}}}):
        code = cdx.main(['doctor'])
    return code, json.loads(capsys.readouterr().out)


def test_doctor_flags_a_runtime_built_from_another_toolkit_revision(monkeypatch, capsys):
    code, report = _doctor(monkeypatch, capsys, 'f' * 64)
    assert code == 1 and report['runtime_matches_skill'] is False
    assert 'install' in report['runtime_hint']


def test_doctor_accepts_a_runtime_built_from_the_pinned_toolkit(monkeypatch, capsys):
    code, report = _doctor(monkeypatch, capsys, cdx.expected_fingerprint())
    assert report['runtime_matches_skill'] is True and 'runtime_hint' not in report


def test_doctor_names_the_skill_release_and_where_its_runtime_comes_from(monkeypatch, capsys):
    # A user comparing an installed copy with the releases page needs the Skill's own version,
    # not only the version of the runtime package it happens to run.
    baseline = json.loads(cdx.BASELINE.read_text(encoding='utf-8'))
    code, report = _doctor(monkeypatch, capsys, cdx.expected_fingerprint())
    assert report['skill_version'] == baseline['toolkit_version']
    assert report['runtime_source'] == (baseline.get('ref') or baseline['commit'][:12])
    assert list(report)[:2] == ['skill_version', 'toolkit']


def test_regen_signatures_refuses_a_runtime_from_another_toolkit_revision(monkeypatch):
    # Regenerating from a stale runtime would roll the committed reference back.
    monkeypatch.setattr(cdx, 'runtime_fingerprint', lambda: 'f' * 64)
    with mock.patch.object(cdx, 'write_signatures') as write, pytest.raises(SystemExit) as exc:
        cdx.main(['regen-signatures'])
    write.assert_not_called()
    assert 'runtime' in str(exc.value)


def test_unknown_tool_suggests_a_stale_runtime():
    with pytest.raises(SystemExit) as exc:
        cdx.main(['call', 'no_such_tool_name'])
    assert 'doctor' in str(exc.value)


def test_tools_listing_names_the_default_timeout(capsys):
    cdx.main(['tools'])
    out = capsys.readouterr().out
    assert 'timeout=Nones' not in out and 'timeout=default' in out


def test_doctor_extras_follow_the_platform():
    windows = cdx.extras_for('win32')
    mac = cdx.extras_for('darwin')

    assert 'win32com.client' in windows['office'] and windows['chemscript'] == ['clr']
    assert 'win32com.client' not in mac['office'] and {'docx', 'pptx', 'olefile'} <= set(mac['office'])
    assert mac['chemscript'] == ['py2opsin']


def _fake_inspection(objects):
    def worker(tool, args, *rest):
        if tool != 'inspect_chemdraw_objects_in_office':
            raise AssertionError(tool)
        out = Path(args['output_dir'])
        (out / 'objects').mkdir(parents=True)
        records = []
        for number in range(1, objects + 1):
            (out / 'objects' / f'object_{number:03d}.cdxml').write_text(f'<CDXML n="{number}"/>', encoding='utf-8')
            records.append({'ordinal': number, 'object_id': f'chemdraw-{number}', 'host': {'kind': 'slide'},
                            'cdxml': f'objects/object_{number:03d}.cdxml'})
        (out / 'manifest.json').write_text(json.dumps({'source_sha256': 'abc', 'objects': records}), encoding='utf-8')
        return {'ok': True, 'result': {'ok': True}}
    return worker


def test_office_edit_opens_the_chosen_object_and_writes_a_replacement_manifest(tmp_path, capsys):
    deck = tmp_path / 'deck.pptx'
    deck.write_bytes(b'PK')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_inspection(2)), \
            mock.patch.object(cdx, '_open_in_chemdraw', return_value=True) as opened:
        assert cdx.main(['office-edit', str(deck), '--object', '2']) == 0
    workdir = tmp_path / 'deck_chemdraw_edit'
    assert opened.call_args.args[0] == workdir / 'object_002.cdxml'
    assert (workdir / 'object_002.cdxml').read_text(encoding='utf-8') == '<CDXML n="2"/>'
    manifest = json.loads((workdir / 'replacements.json').read_text(encoding='utf-8'))
    assert manifest == {'schema_version': 1, 'source_sha256': 'abc',
                        'replacements': [{'object_id': 'chemdraw-2', 'replacement_cdxml': 'object_002.cdxml'}]}
    assert json.loads(capsys.readouterr().out)['opened_in_chemdraw'] is True


def test_office_edit_lists_objects_when_the_choice_is_ambiguous(tmp_path, capsys):
    deck = tmp_path / 'deck.pptx'
    deck.write_bytes(b'PK')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_inspection(2)), \
            mock.patch.object(cdx, '_open_in_chemdraw', return_value=True) as opened:
        assert cdx.main(['office-edit', str(deck)]) == 2
        assert not opened.called
        assert [item['object'] for item in json.loads(capsys.readouterr().out)['objects']] == [1, 2]
        # The listing leaves nothing behind, so the advised rerun works.
        assert not (tmp_path / 'deck_chemdraw_edit').exists()
        for wrong in ('0', '3'):
            with pytest.raises(SystemExit, match='No ChemDraw object'):
                cdx.main(['office-edit', str(deck), '--object', wrong])
            assert not (tmp_path / 'deck_chemdraw_edit').exists()
        assert cdx.main(['office-edit', str(deck), '--object', '2']) == 0


def test_office_edit_finish_writes_back_only_a_saved_drawing_and_resizes_its_frame(tmp_path, capsys):
    deck = tmp_path / 'deck.pptx'
    deck.write_bytes(b'PK')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_inspection(1)), \
            mock.patch.object(cdx, '_open_in_chemdraw', return_value=True):
        cdx.main(['office-edit', str(deck)])
    workdir = tmp_path / 'deck_chemdraw_edit'
    capsys.readouterr()
    with mock.patch.object(cdx, '_worker') as worker:
        assert cdx.main(['office-edit', '--finish', str(workdir)]) == 1
    assert not worker.called

    edited = workdir / 'object_001.cdxml'
    edited.write_text('<CDXML n="edited"/>', encoding='utf-8')
    os.utime(edited, (edited.stat().st_atime, edited.stat().st_mtime - 5))
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['office-edit', '--finish', str(workdir), '--output', str(tmp_path / 'new.pptx')]) == 0
    tool, args = worker.call_args.args[:2]
    assert tool == 'replace_chemdraw_objects_in_office'
    assert args == {'input_path': str(deck.resolve()), 'replacements_manifest': str(workdir / 'replacements.json'),
                    'render_pdf_preview': False, 'resize_frames': True, 'output_path': str(tmp_path / 'new.pptx')}


def test_office_edit_finish_accepts_the_document_and_finds_its_edit_folder(tmp_path, capsys):
    deck = tmp_path / 'deck.pptx'
    deck.write_bytes(b'PK')
    custom = tmp_path / 'my edit'
    with mock.patch.object(cdx, '_worker', side_effect=_fake_inspection(1)), \
            mock.patch.object(cdx, '_open_in_chemdraw', return_value=True):
        cdx.main(['office-edit', str(deck), '--workdir', str(custom)])
    edited = custom / 'object_001.cdxml'
    edited.write_text('<CDXML n="edited"/>', encoding='utf-8')
    os.utime(edited, (edited.stat().st_atime, edited.stat().st_mtime - 5))
    capsys.readouterr()
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['office-edit', str(deck), '--finish', '--workdir', str(custom)]) == 0
    assert worker.call_args.args[1]['replacements_manifest'] == str(custom.resolve() / 'replacements.json')

    other = tmp_path / 'other.docx'
    other.write_bytes(b'PK')
    with mock.patch.object(cdx, '_worker') as worker:
        assert cdx.main(['office-edit', str(other), '--finish']) == 2
    assert not worker.called
    assert 'office-edit' in capsys.readouterr().out


def test_office_edit_finish_waits_for_a_fresh_save_to_settle(tmp_path, capsys):
    deck = tmp_path / 'deck.pptx'
    deck.write_bytes(b'PK')
    with mock.patch.object(cdx, '_worker', side_effect=_fake_inspection(1)), \
            mock.patch.object(cdx, '_open_in_chemdraw', return_value=True):
        cdx.main(['office-edit', str(deck)])
    workdir = tmp_path / 'deck_chemdraw_edit'
    edited = workdir / 'object_001.cdxml'
    edited.unlink()  # mid-save
    capsys.readouterr()
    with mock.patch.object(cdx, '_worker') as worker:
        assert cdx.main(['office-edit', '--finish', str(workdir)]) == 1
    assert not worker.called
    assert 'has not been saved' in capsys.readouterr().out

    edited.write_text('<CDXML n="edited"/>', encoding='utf-8')  # saved just now
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['office-edit', '--finish', str(workdir)]) == 0
    assert worker.called


def test_doctor_paths_name_the_native_lock_of_this_platform():
    from cdxml_toolkit.mcp_runtime import resource_lock
    expected = resource_lock.CHEMDRAW_COM_MUTEX if os.name == 'nt' else str(resource_lock.CHEMDRAW_LOCK_FILE)
    assert cdx.runtime_paths()['native_lock'] == expected


def test_doctor_paths_include_the_runtime_log_folder(tmp_path, monkeypatch):
    from cdxml_toolkit.mcp_runtime import tool_worker
    monkeypatch.delenv('LOCALAPPDATA', raising=False)
    monkeypatch.delenv('TEMP', raising=False)
    folder = tmp_path / 'Logs' / 'chemdraw-skill'
    folder.mkdir(parents=True)
    monkeypatch.setattr(tool_worker, 'worker_log_dir', lambda: folder)
    assert str(folder) in cdx.runtime_paths()['worker_logs']


def test_install_mappers_hands_every_argument_to_the_backend_installer():
    with mock.patch.object(cdx, '_ensure_runtime'), mock.patch.object(cdx.subprocess, 'call', return_value=0) as call:
        assert cdx.main(['install-mappers', 'localmapper', '--dry-run']) == 0
    assert call.call_args.args[0][1:] == ['-m', 'cdxml_toolkit.mapping_backends', 'localmapper', '--dry-run']


def test_install_mappers_accepts_an_option_before_any_backend_name():
    with mock.patch.object(cdx, '_ensure_runtime'), mock.patch.object(cdx.subprocess, 'call', return_value=0) as call:
        assert cdx.main(['install-mappers', '--status']) == 0
    assert call.call_args.args[0][1:] == ['-m', 'cdxml_toolkit.mapping_backends', '--status']


def test_calc_hands_every_argument_to_the_stoichiometry_grid_module():
    with mock.patch.object(cdx, '_ensure_runtime'), mock.patch.object(cdx.subprocess, 'call', return_value=0) as call:
        assert cdx.main(['calc', 'A.B>>C', '--output', 'out.cdxml', '--no-open']) == 0
    assert call.call_args.args[0][1:] == ['-m', 'cdxml_toolkit.chemdraw.stoichiometry_grid', 'A.B>>C',
                                          '--output', 'out.cdxml', '--no-open']


def test_draw_hands_the_brief_and_options_to_draw_figure(tmp_path, capsys):
    brief = {'species': [{'id': 'A', 'smiles': 'C'}], 'steps': [{'substrates': ['A'], 'products': ['A']}]}
    path = tmp_path / 'brief.json'
    path.write_text(json.dumps(brief), encoding='utf-8')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', str(path), str(tmp_path / 'out.cdxml'), '--render']) == 0
    tool, kwargs = worker.call_args.args
    assert tool == 'draw_figure'
    assert kwargs == {'brief': brief, 'output_path': str(tmp_path / 'out.cdxml'), 'render': True}


def test_draw_without_an_output_lets_the_tool_choose_a_fresh_name(tmp_path):
    path = tmp_path / 'brief.json'
    path.write_text('{}', encoding='utf-8')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        cdx.main(['draw', str(path)])
    assert worker.call_args.args[1] == {'brief': {}, 'render': False}


def test_draw_reads_the_brief_from_standard_input(monkeypatch):
    import io
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{"species": []}'))
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        cdx.main(['draw', '-'])
    assert worker.call_args.args[1]['brief'] == {'species': []}


def test_draw_rejects_a_brief_that_is_not_json(tmp_path):
    path = tmp_path / 'brief.json'
    path.write_text('species: [', encoding='utf-8')
    with pytest.raises(SystemExit, match='not valid JSON'):
        cdx.main(['draw', str(path)])


def test_draw_failure_sets_the_exit_code(tmp_path, capsys):
    path = tmp_path / 'brief.json'
    path.write_text('{}', encoding='utf-8')
    failed = {'ok': True, 'result': {'ok': False, 'errors': ['steps: give at least one step']}}
    with mock.patch.object(cdx, '_worker', return_value=failed):
        assert cdx.main(['draw', str(path)]) == 1


def _engine_listing(*installed):
    names = ['decimer-api', 'molscribe', 'molnextr', 'molvec', 'magnet']
    return {'ok': True, 'engines': {n: {'task': 'nmr' if n == 'magnet' else 'ocsr', 'kind': 'remote' if n == 'decimer-api' else 'local',
                                        'available': n == 'decimer-api' or n in installed} for n in names}}


def test_ocsr_without_upload_and_without_engines_names_the_local_choices(capsys):
    with mock.patch.object(cdx, '_worker', return_value=_engine_listing('molscribe', 'magnet')) as worker:
        with pytest.raises(SystemExit) as stopped:
            cdx.main(['ocsr', 'x.png', '--no-upload'])
    message = str(stopped.value)
    assert 'no local engine selected, use --engines molscribe' in message and '(installed: molscribe)' in message
    assert 'magnet' not in message and 'upload' not in message  # not the nmr engine, not the upload refusal
    assert [call.args[0] for call in worker.call_args_list] == ['list_engines']


def test_ocsr_without_upload_and_nothing_installed_says_how_to_install(capsys):
    with mock.patch.object(cdx, '_worker', return_value=_engine_listing()):
        with pytest.raises(SystemExit) as stopped:
            cdx.main(['ocsr', 'x.png', '--no-upload'])
    assert 'installed: none' in str(stopped.value) and 'install-engines molscribe' in str(stopped.value)


def test_ocsr_keeps_decimer_api_as_the_default_and_obeys_a_named_engine(tmp_path):
    image = tmp_path / 'x.png'
    image.write_bytes(b'x')
    for argv, engines, confirm in ((['ocsr', str(image)], 'decimer-api', True),
                                   (['ocsr', str(image), '--no-upload', '--engines', 'molscribe'], 'molscribe', False)):
        with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
            cdx.main(argv)
        assert worker.call_args.args[:1] == ('recognize_structure',)
        assert worker.call_args.args[1]['engines'] == engines and worker.call_args.args[1]['confirm_upload'] is confirm


def test_engines_passes_sizes_on_to_the_listing():
    with mock.patch.object(cdx.subprocess, 'call', return_value=0) as call:
        cdx.main(['engines', '--sizes'])
    assert call.call_args.args[0][-2:] == ['--status', '--sizes']


def test_draw_accepts_utf8_bom_in_file_and_stdin(tmp_path, monkeypatch):
    import io
    brief = {'species': [{'id': 'A', 'smiles': 'CCO'}], 'steps': []}
    path = tmp_path / 'bom_brief.json'
    path.write_bytes(b'\xef\xbb\xbf' + json.dumps(brief).encode('utf-8'))
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', str(path)]) == 0
    assert worker.call_args.args[1]['brief'] == brief

    monkeypatch.setattr(sys, 'stdin', io.StringIO('\ufeff' + json.dumps(brief)))
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', '-']) == 0
    assert worker.call_args.args[1]['brief'] == brief


def test_load_args_reads_stdin_when_dash_is_given(monkeypatch):
    import io
    monkeypatch.setattr(sys, 'stdin', io.StringIO('\ufeff{"smiles": "CCO"}'))
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
        assert cdx.main(['call', 'modify_molecule', '--args', '-']) == 0
    assert worker.call_args.args == ('modify_molecule', {'smiles': 'CCO'})


def test_ocsr_writes_envelope_to_out_file(tmp_path, capsys):
    image = tmp_path / 'crop.png'
    image.write_bytes(b'png')
    out_file = tmp_path / 'res.json'
    envelope = {'ok': True, 'result': {'ok': True, 'engines': {'molscribe': {'smiles': 'CCO'}}}}
    with mock.patch.object(cdx, '_worker', return_value=envelope) as worker:
        assert cdx.main(['ocsr', str(image), '--engines', 'molscribe,molvec', '--out', str(out_file)]) == 0
    assert 'output_path' not in worker.call_args.args[1]
    assert out_file.is_file()
    assert json.loads(out_file.read_text(encoding='utf-8')) == envelope
    summary = json.loads(capsys.readouterr().out)
    assert summary['ok'] is True and Path(summary['evidence']) == out_file.resolve()


def test_predict_supports_args_file_stdin_and_out(tmp_path, monkeypatch, capsys):
    import io
    args_file = tmp_path / 'pred_args.json'
    args_file.write_bytes(b'\xef\xbb\xbf{"reactants": "CCO.CC(=O)O", "top_k": 3}')
    out_file = tmp_path / 'pred_out.json'
    envelope = {'ok': True, 'result': {'ok': True, 'predictions': ['CCOC(C)=O']}}
    with mock.patch.object(cdx, '_worker', return_value=envelope) as worker:
        assert cdx.main(['predict', 'products', '--args', str(args_file), '--out', str(out_file)]) == 0
    assert worker.call_args.args == ('predict_products', {'reactants': 'CCO.CC(=O)O', 'top_k': 3})
    assert json.loads(out_file.read_text(encoding='utf-8')) == envelope
    summary = json.loads(capsys.readouterr().out)
    assert summary['ok'] is True and Path(summary['evidence']) == out_file.resolve()

    monkeypatch.setattr(sys, 'stdin', io.StringIO('\ufeff{"smiles": "CCOC(C)=O", "nucleus": "1H"}'))
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
        assert cdx.main(['predict', 'nmr', '--args', '-']) == 0
    assert worker.call_args.args == ('predict_nmr', {'smiles': 'CCOC(C)=O', 'nucleus': '1H'})


def test_sig_accepts_multiple_tools_and_suggests_matches_when_not_found(capsys):
    assert cdx.main(['sig', 'render_cdxml_files', 'draw_figure']) == 0
    out = capsys.readouterr().out
    assert '### `render_cdxml_files(' in out and '### `draw_figure(' in out
    # Direct Namespace call with a string remains backward-compatible.
    assert cdx.cmd_sig(argparse.Namespace(tool='render_cdxml_files')) == 0
    assert capsys.readouterr().out.startswith('### `render_cdxml_files(')

    msg = _message(capsys, 'sig', 'embed_cdxml_office')
    assert 'Did you mean:' in msg and 'embed_cdxml_in_office' in msg
    msg_sub = _message(capsys, 'sig', 'stoichiometry')
    assert 'Did you mean:' in msg_sub


def test_tools_filters_by_case_insensitive_substring(capsys):
    assert cdx.main(['tools', 'OFFICE', '--detail', 'summary']) == 0
    summary = capsys.readouterr().out.strip()
    assert 'embed_cdxml_in_office' in summary and 'draw_figure' not in summary

    assert cdx.main(['tools', 'office']) == 0
    full = capsys.readouterr().out
    assert 'embed_cdxml_in_office' in full and 'draw_figure' not in full


def test_doctor_returns_nonzero_when_requested_probe_fails_without_breaking_default_doctor(monkeypatch, capsys):
    monkeypatch.setattr(cdx, 'expected_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, 'runtime_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, '_signatures_current', lambda: True)
    monkeypatch.setattr(cdx, 'catalog_stale', lambda: [])
    unverified_caps = {
        'chemdraw': {'status': 'missing'},
        'office': {'status': 'unverified'},
        'chemscript': {'status': 'unverified'},
    }
    # Default `cdx.py doctor` stays 0 even when optional desktop capabilities are missing/unverified.
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'outputs': {'capabilities': unverified_caps, 'passive_capabilities': {'chemscript_dll': 'missing', 'office_com': 'available'}}}}):
        assert cdx.main(['doctor']) == 0
    doc_out = json.loads(capsys.readouterr().out)
    assert doc_out['passive_capabilities'] == {'chemscript_dll': 'missing', 'office_com': 'available'}
    assert doc_out['capabilities']['chemscript'] == 'unverified'
    assert doc_out['capabilities']['office'] == 'unverified'

    # Explicit probe fails when inner['ok'] is False or the requested capability is not available.
    for flag in ('--native', '--office', '--chemscript'):
        with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'outputs': {'capabilities': unverified_caps}}}):
            assert cdx.main(['doctor', flag]) == 1
        capsys.readouterr()

    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': False, 'outputs': {'capabilities': {'chemdraw': {'status': 'available'}}}}}):
        assert cdx.main(['doctor', '--native']) == 1
    capsys.readouterr()

    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'outputs': {'capabilities': {'chemdraw': {'status': 'available'}, 'office': {'status': 'unverified'}}}}}):
        assert cdx.main(['doctor', '--native']) == 0
    capsys.readouterr()


def test_accel_flag_reaches_the_environment_and_stop_daemons_is_its_own_command(monkeypatch):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}):
        assert cdx.main(['predict', 'nmr', 'CCO', '--accel', 'on']) == 0
    assert os.environ.pop('CHEMDRAW_ACCEL') == 'on'
    for removed in ('simple', 'complex'):  # only auto, on and off remain
        with pytest.raises(SystemExit):
            cdx.main(['predict', 'nmr', 'CCO', '--accel', removed])
    with pytest.raises(SystemExit):  # the hint option is gone
        cdx.main(['predict', 'nmr', 'CCO', '--task-hint', 'x'])

    with mock.patch.object(cdx.subprocess, 'call', return_value=0) as call:
        assert cdx.main(['stop-daemons']) == 0
    assert call.call_args.args[0][-3:] == ['-m', 'cdxml_toolkit.engines', '--stop-daemons']


def test_stop_daemons_never_rides_on_a_prediction_or_the_engine_listing():
    for argv in (['predict', 'nmr', 'CCO', '--stop-daemons'], ['predict', 'stop-daemons'], ['engines', '--stop-daemons']):
        with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
            with pytest.raises(SystemExit):
                cdx.main(argv)
        assert not worker.called


def test_decimer_is_an_alias_of_ocsr_with_the_decimer_api_engine(tmp_path):
    image = tmp_path / 'x.png'
    image.write_bytes(b'x')
    for flags, confirm in (([], True), (['--preflight'], False)):
        with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
            cdx.main(['decimer', str(image), '--hand-drawn', *flags])
        tool, kwargs = worker.call_args.args
        assert tool == 'recognize_structure'
        assert kwargs['engines'] == 'decimer-api' and kwargs['hand_drawn'] is True and kwargs['confirm_upload'] is confirm


def test_maintainer_commands_stay_callable_but_out_of_the_main_help(capsys):
    with pytest.raises(SystemExit):
        cdx.main(['--help'])
    listing = capsys.readouterr().out
    for hidden in ('regen-signatures', 'regen-catalog', 'chemscript-info', 'SUPPRESS'):
        assert hidden not in listing
    for shown in ('doctor', 'ocsr', 'decimer', 'predict', 'stop-daemons'):
        assert shown in listing
    with pytest.raises(SystemExit) as helped:
        cdx.main(['regen-signatures', '--help'])
    assert helped.value.code == 0


def test_doctor_reports_only_the_runtimes_own_passive_capabilities(monkeypatch, capsys):
    monkeypatch.setattr(cdx, 'expected_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, 'runtime_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, '_signatures_current', lambda: True)
    monkeypatch.setattr(cdx, 'catalog_stale', lambda: [])
    caps = {'chemdraw': {'status': 'available'}, 'office': {'status': 'unverified'},
            'chemscript': {'status': 'unverified'}, 'chemdraw_com': {'status': 'available'}}
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'outputs': {'capabilities': caps}}}):
        assert cdx.main(['doctor']) == 0
    report = json.loads(capsys.readouterr().out)
    assert 'passive_capabilities' not in report  # unverified is never relabelled as available
    assert report['capabilities']['office'] == 'unverified'


def test_styles_lists_the_journal_presets(capsys):
    assert cdx.main(['styles']) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith('acs1996') and '14.4 pt' in lines[0]
    assert any(line.startswith('nature ') and '10.8 pt' in line for line in lines)


def _example_house_style(tmp_path, monkeypatch):
    from cdxml_toolkit.publication import house_styles
    card = {
        'slug': '_example', 'kind': 'group', 'display_name': 'Example Group', 'base_preset': 'rsc',
        'measured': {}, 'conventions': {'compound_label_face': 'bold', 'notes': 'shown, not applied'},
        'evidence': [{'doi': '10.0000/a'}, {'doi': '10.0000/b'}],
    }
    (tmp_path / '_example.json').write_text(json.dumps(card), encoding='utf-8')
    monkeypatch.setattr(house_styles, 'DATA_DIR', tmp_path)


def test_styles_lists_house_styles_in_a_second_section(capsys, tmp_path, monkeypatch):
    _example_house_style(tmp_path, monkeypatch)
    assert cdx.main(['styles']) == 0
    out = capsys.readouterr().out
    presets, houses = out.split('House styles', 1)
    assert 'acs1996' in presets and '_example' not in presets
    line = next(l for l in houses.splitlines() if l.startswith('_example'))
    assert 'group' in line and 'base rsc' in line and '2 evidence' in line and 'Example Group' in line


def test_styles_prints_a_house_style_card(capsys, tmp_path, monkeypatch):
    _example_house_style(tmp_path, monkeypatch)
    assert cdx.main(['styles', '_example']) == 0
    card = json.loads(capsys.readouterr().out)
    assert card['slug'] == '_example' and card['conventions']['notes'] == 'shown, not applied'


def test_styles_prints_one_preset_as_json(capsys):
    assert cdx.main(['styles', 'Wiley Document']) == 0
    preset = json.loads(capsys.readouterr().out)
    assert preset['slug'] == 'wiley' and preset['attributes']['BondLength'] == '17'


def test_draw_style_flag_sets_the_brief_style(tmp_path):
    brief = tmp_path / 'brief.json'
    brief.write_text('{"species": [], "steps": []}', encoding='utf-8')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
        cdx.main(['draw', str(brief), '--style', 'rsc'])
    assert worker.call_args[0][1]['brief']['style'] == 'rsc'


def test_build_applies_a_style_preset(tmp_path):
    spec = {'style': 'nature', 'objects': [{'type': 'molecule', 'smiles': 'c1ccccc1', 'at': [100, 100]}]}
    root = ET.fromstring(acs_builder.build_from_spec(spec))
    assert root.get('BondLength') == '10.8'
    with pytest.raises(ValueError, match='acs1996'):
        acs_builder.build_from_spec({**spec, 'style': 'no-such-journal'})


def test_draw_supports_name_and_smiles_shorthand_without_a_brief_file(tmp_path):
    out = str(tmp_path / 'aspirin.cdxml')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', '--name', 'aspirin', out, '--style', 'nature', '--render']) == 0
    assert worker.call_args.args == ('draw_figure', {
        'brief': {'kind': 'molecule', 'species': [{'id': 's1', 'name': 'aspirin'}], 'style': 'nature'},
        'render': True,
        'output_path': out,
    })

    # Output path before --name also works, as does repeating --smiles/--label/--abbreviate/--columns.
    out2 = str(tmp_path / 'grid.cdxml')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main([
            'draw', out2, '--smiles', 'COc1ccccc1', '--name', 'benzene',
            '--label', '1', '--label', '2', '--abbreviate', 'OMe,OTBS', '--columns', '2', '--title', 'Panel',
        ]) == 0
    assert worker.call_args.args[1]['brief'] == {
        'kind': 'molecule',
        'species': [
            {'id': 's1', 'smiles': 'COc1ccccc1', 'label': '1', 'abbreviate': ['OMe', 'OTBS']},
            {'id': 's2', 'name': 'benzene', 'label': '2', 'abbreviate': ['OMe', 'OTBS']},
        ],
        'title': 'Panel',
        'columns': 2,
    }
    assert worker.call_args.args[1]['output_path'] == out2


def test_draw_shorthand_validation_errors(tmp_path, capsys):
    assert 'brief JSON file' in _message(capsys, 'draw')
    brief = tmp_path / 'b.json'
    brief.write_text('{}', encoding='utf-8')
    assert 'cannot combine' in _message(capsys, 'draw', str(brief), str(tmp_path / 'o.cdxml'), '--name', 'aspirin')
    assert 'cannot combine' in _message(capsys, 'draw', str(brief), '--name', 'aspirin')
    assert '--label' in _message(capsys, 'draw', '--smiles', 'CCO', '--label', '1', '--label', '2')
    assert 'shorthand' in _message(capsys, 'draw', str(brief), '--label', '1')


def test_draw_number_and_properties_flags_and_arg_order(tmp_path, capsys):
    out = str(tmp_path / 'panel.cdxml')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', '--smiles', 'CCO', '--smiles', 'c1ccccc1', '--number', out, '--properties']) == 0
    assert worker.call_args.args[1]['brief'] == {
        'kind': 'molecule',
        'species': [{'id': 's1', 'smiles': 'CCO'}, {'id': 's2', 'smiles': 'c1ccccc1'}],
        'numbering': 'arabic',
        'properties': True,
    }
    assert worker.call_args.args[1]['output_path'] == out

    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', '--smiles', 'CCO', out, '--number', 'roman']) == 0
    assert worker.call_args.args[1]['brief']['numbering'] == 'roman'

    brief = tmp_path / 'scheme.json'
    brief.write_text('{"kind": "scheme", "species": [], "steps": []}', encoding='utf-8')
    assert '--number' in _message(capsys, 'draw', str(brief), '--number')


def test_regen_signatures_check_reports_clean_and_stale_states(monkeypatch, capsys):
    monkeypatch.setattr(cdx, 'expected_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, 'runtime_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, 'signatures_stale', lambda: [])
    assert cdx.main(['regen-signatures', '--check']) == 0
    assert json.loads(capsys.readouterr().out) == {'signatures_current': True, 'stale': []}

    monkeypatch.setattr(cdx, 'signatures_stale', lambda: ['references/mcp-signatures.md'])
    assert cdx.main(['regen-signatures', '--check']) == 1
    assert json.loads(capsys.readouterr().out) == {
        'signatures_current': False,
        'stale': ['references/mcp-signatures.md'],
    }


def test_call_arg_key_value_pairs_and_value_coercion(tmp_path):
    base = tmp_path / 'base.json'
    base.write_text('{"timeout_seconds": 30, "query": "old"}', encoding='utf-8')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}) as worker:
        assert cdx.main([
            'call', 'resolve_name', '--args', str(base),
            '-a', 'query=534-17-8',
            '-a', 'use_network=false',
            '-a', 'retries=3',
            '-a', 'ratio=0.75',
            '-a', 'tags=["a","b"]',
        ]) == 0
    assert worker.call_args.args == ('resolve_name', {
        'timeout_seconds': 30,
        'query': '534-17-8',
        'use_network': False,
        'retries': 3,
        'ratio': 0.75,
        'tags': ['a', 'b'],
    })

    with mock.patch.object(cdx, '_worker') as worker, pytest.raises(SystemExit) as bad:
        cdx.main(['call', 'resolve_name', '-a', 'missing_equals'])
    assert 'KEY=VALUE' in str(bad.value) and not worker.called


def test_emit_deduplicates_inline_outputs_and_enriches_large_summary(tmp_path, capsys):
    inner = {
        'ok': True,
        'output_path': '/tmp/rxn.cdxml',
        'native': {'status': 'rendered', 'png_path': '/tmp/rxn.png'},
        'checks_passed': True,
        'readback': {'status': 'matched'},
        'warnings': ['Step 1 has no conditions'],
    }
    inline_env = {'ok': True, 'result': inner, 'outputs': dict(inner)}
    with mock.patch.object(cdx, '_worker', return_value=inline_env):
        assert cdx.main(['call', 'draw_figure', '--json', '{}']) == 0
    shown = json.loads(capsys.readouterr().out)
    assert 'outputs' not in shown and shown['result'] == inner

    large = {
        'ok': True,
        'result': {**inner, 'raw_response': 'x' * 20000},
        'outputs': {**inner, 'raw_response': 'x' * 20000},
    }
    ev = tmp_path / 'large.json'
    with mock.patch.object(cdx, '_worker', return_value=large):
        assert cdx.main(['call', 'draw_figure', '--json', '{}', '--out', str(ev)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['ok'] is True
    assert summary['output_path'] == '/tmp/rxn.cdxml'
    assert summary['png_path'] == '/tmp/rxn.png'
    assert summary['checks_passed'] is True
    assert summary['readback'] == 'matched'
    assert summary['warnings_preview'] == ['Step 1 has no conditions']
    assert 'raw_response' not in json.dumps(summary)
    assert json.loads(ev.read_text(encoding='utf-8')) == large

    # --summary forces compact summary even when inline payload is small; --full forces full inline output.
    with mock.patch.object(cdx, '_worker', return_value=inline_env):
        assert cdx.main(['call', 'draw_figure', '--json', '{}', '--summary']) == 0
    compact = json.loads(capsys.readouterr().out)
    assert compact['output_path'] == '/tmp/rxn.cdxml' and 'result' not in compact

    with mock.patch.object(cdx, '_worker', return_value=large):
        assert cdx.main(['call', 'draw_figure', '--json', '{}', '--full']) == 0
    full_out = json.loads(capsys.readouterr().out)
    assert full_out['result']['raw_response'] == 'x' * 20000


def test_draw_reaction_and_compact_shorthands(tmp_path):
    out = str(tmp_path / 'route.cdxml')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main([
            'draw',
            '--reaction', 'CC(=O)O.CCO>O=S(=O)(O)O>CCOC(C)=O',
            '--reaction', 'CCOC(C)=O>NaOH>CC(=O)O',
            '--above', 'rt, 2 h', '--above', 'H2O, reflux; then H+',
            '--yield', '88%', '--yield', '95%',
            '--layout', 'sequential', '--style', 'rsc',
            out,
        ]) == 0
    tool, kwargs = worker.call_args.args
    assert tool == 'draw_figure'
    assert kwargs['output_path'] == out
    brief = kwargs['brief']
    assert brief['kind'] == 'scheme' and brief['layout'] == 'sequential' and brief['style'] == 'rsc'
    # Species are deduplicated across the two steps (CC(=O)O, CCO, CCOC(C)=O, NaOH? Wait: NaOH is agent, 3 unique species).
    assert len(brief['species']) == 3
    assert brief['steps'][0]['substrates'] == ['s1', 's2']
    assert brief['steps'][0]['products'] == ['s3']
    assert brief['steps'][0]['above'] == ['H2SO4', 'rt, 2 h']
    assert brief['steps'][0]['yield'] == '88%'
    assert brief['steps'][1]['substrates'] == ['s3']
    assert brief['steps'][1]['products'] == ['s1']
    assert brief['steps'][1]['above'] == ['NaOH', 'H2O, reflux', 'then H+']
    assert brief['steps'][1]['yield'] == '95%'

    # Dative bonds (`->`) inside SMILES do not break reaction arrow splitting.
    dative_out = str(tmp_path / 'dative.cdxml')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', '--reaction', '[NH3]->[BH3]>>[NH3+][BH3-]', dative_out]) == 0
    assert worker.call_args.args[1]['brief']['species'][0]['smiles'] == '[NH3]->[BH3]'

    # --compact routes to render_scheme and reads a DSL file if given.
    dsl = tmp_path / 'scheme.dsl'
    dsl.write_text('A: {CCO}\nB: {CC=O}\nA --> B\n', encoding='utf-8')
    compact_out = str(tmp_path / 'compact.cdxml')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['draw', '--compact', str(dsl), compact_out]) == 0
    assert worker.call_args.args == ('render_scheme', {
        'compact_text': 'A: {CCO}\nB: {CC=O}\nA --> B\n',
        'output_path': compact_out,
    })


def test_resolve_inspect_and_report_shortcuts(tmp_path, capsys):
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'smiles': 'CCO'}}) as worker:
        assert cdx.main(['resolve', 'ethanol', '--offline']) == 0
    assert worker.call_args.args == ('resolve_name', {'query': 'ethanol', 'use_network': False})
    capsys.readouterr()

    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'smiles': 'CCO'}}) as worker:
        assert cdx.main(['resolve', 'ethanol', 'methanol']) == 0
    batch = json.loads(capsys.readouterr().out)
    assert batch['ok'] is True and batch['count'] == 2 and len(batch['results']) == 2

    cdxml = tmp_path / 'rxn.cdxml'
    cdxml.write_text('<CDXML><page><scheme><step/></scheme></page></CDXML>', encoding='utf-8')
    def fake_inspect(tool, kwargs, *rest):
        if tool == 'export_structures':
            return {'ok': True, 'result': {'ok': True, 'structures': [{'smiles': 'CCO'}]}}
        if tool == 'parse_scheme':
            assert 'output_path' in kwargs and not str(kwargs['output_path']).startswith(str(tmp_path))
            Path(kwargs['output_path']).write_text(
                json.dumps({'ok': True, 'topology': 'linear', 'steps': [{'id': '1'}]}),
                encoding='utf-8',
            )
            return {'ok': True, 'result': {'ok': True, 'output_path': kwargs['output_path'], 'size': 42}}
        if tool == 'parse_analysis_file':
            assert 'output_path' in kwargs and not str(kwargs['output_path']).startswith(str(tmp_path))
            Path(kwargs['output_path']).write_text(
                json.dumps({'ok': True, 'source_format': 'pdf', 'peaks': [{'rt': 1.02}]}),
                encoding='utf-8',
            )
            return {'ok': True, 'result': {'ok': True, 'output_path': kwargs['output_path'], 'size': 42}}
        raise AssertionError(tool)
    with mock.patch.object(cdx, '_worker', side_effect=fake_inspect):
        assert cdx.main(['inspect', str(cdxml)]) == 0
    insp = json.loads(capsys.readouterr().out)
    assert insp['result']['scheme']['topology'] == 'linear'
    assert not list(tmp_path.glob('*_parsed.json'))

    pdf_file = tmp_path / 'lcms.pdf'
    pdf_file.write_bytes(b'%PDF-1.4\n')
    with mock.patch.object(cdx, '_worker', side_effect=fake_inspect):
        assert cdx.main(['inspect', str(pdf_file)]) == 0
    pdf_insp = json.loads(capsys.readouterr().out)
    assert pdf_insp['result']['source_format'] == 'pdf'
    assert pdf_insp['result']['peaks'] == [{'rt': 1.02}]
    assert not list(tmp_path.glob('*_parsed.json'))

    with pytest.raises(SystemExit, match='does not exist'):
        cdx.main(['inspect', str(tmp_path / 'missing.cdxml')])

    # report --balance & --hrms & --map
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'balanced': True}}) as worker:
        assert cdx.main(['report', '--balance', 'CCO.CC(=O)O>>CCOC(C)=O', '--scale-mmol', '2.5']) == 0
    assert worker.call_args.args == ('check_reaction_balance', {
        'reaction': 'CCO.CC(=O)O>>CCOC(C)=O',
        'options': {'scale_mmol': 2.5},
    })

    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['report', 'CCO', '--hrms', '--adduct', '[M+Na]+', '--found', '69.0311']) == 0
    assert worker.call_args.args == ('hrms_line', {
        'molecules': [{'smiles': 'CCO', 'adduct': '[M+Na]+', 'found_mz': 69.0311}],
    })

    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True}}) as worker:
        assert cdx.main(['report', '--map', str(cdxml), '--method', 'mcs', '--classify']) == 0
    assert worker.call_args.args == ('map_reaction_atoms', {
        'reaction': {'cdxml': str(cdxml.resolve())},
        'options': {'method': 'mcs', 'classify': True},
    })


def test_fuzzy_suggestions_next_free_path_and_doctor_log_and_text(tmp_path, monkeypatch, capsys):
    # Unknown style prints 1-line SystemExit with suggestions instead of a traceback.
    style_msg = _message(capsys, 'styles', 'acs1995')
    assert 'Did you mean:' in style_msg and 'acs1996' in style_msg

    # Unknown tool keeps doctor hint and adds close matches when available.
    tool_msg = _message(capsys, 'call', 'draw_figur')
    assert 'doctor' in tool_msg and 'draw_figure' in tool_msg

    # Overwrite refusal reports the next available file path.
    existing = tmp_path / 'out.json'
    existing.write_text('{}', encoding='utf-8')
    with mock.patch.object(cdx, '_worker', return_value={'ok': True}):
        ev_msg = _message(capsys, 'call', 'modify_molecule', '--json', '{}', '--out', str(existing))
    assert 'out_2.json' in ev_msg

    # doctor --log finds the requested log id and `latest`.
    from cdxml_toolkit.mcp_runtime import tool_worker
    log_dir = tmp_path / 'logs'
    log_dir.mkdir()
    older = log_dir / 'worker-abc111.log'
    newer = log_dir / 'worker-def222.log'
    older.write_text('old failure traceback\n', encoding='utf-8')
    newer.write_text('newest failure traceback\n', encoding='utf-8')
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    monkeypatch.setattr(tool_worker, 'worker_log_dir', lambda: log_dir)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))

    assert cdx.main(['doctor', '--log', 'abc111']) == 0
    assert 'old failure traceback' in capsys.readouterr().out
    assert cdx.main(['doctor', '--log', 'latest']) == 0
    assert 'newest failure traceback' in capsys.readouterr().out

    # doctor --text prints a readable summary.
    monkeypatch.setattr(cdx, 'expected_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, 'runtime_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(cdx, '_signatures_current', lambda: True)
    monkeypatch.setattr(cdx, 'catalog_stale', lambda: [])
    with mock.patch.object(cdx, '_worker', return_value={'ok': True, 'result': {'ok': True, 'outputs': {'capabilities': {'chemdraw': {'status': 'available'}}}}}):
        assert cdx.main(['doctor', '--text']) == 0
    txt = capsys.readouterr().out
    assert 'ChemDraw Skill' in txt and 'healthy=True' in txt and 'chemdraw=available' in txt
