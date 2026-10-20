"""Regression checks for public execution and artifact contracts."""
import asyncio
import json
from pathlib import Path
import sys

import pytest

from cdxml_toolkit.mcp_runtime import mcp_server as server, runtime_discovery


def interpret(value):
    return server._interpret_worker_result('draw_molecule', 0,
        json.dumps({'ok': True, 'result': value}).encode(), b'',
        timeout=90, duration=0.1, output_limit=4096)


@pytest.mark.parametrize('encoded', [False, True])
@pytest.mark.parametrize('error', ['Invalid structure', {'code': 'invalid_structure', 'message': 'Invalid structure'}])
def test_business_failure_propagates_without_losing_original_result(encoded, error):
    value = {'ok': False, 'error': error, 'warnings': ['review']}
    original = json.dumps(value) if encoded else value
    result = interpret(original)
    assert result['ok'] is False
    assert result['result'] == original
    assert result['error']['message'] == 'Invalid structure'
    assert result['warnings'] == ['review']


@pytest.mark.parametrize('value', [
    {'ok': True, 'native': {'status': 'failed'}, 'validation_status': 'not_run'},
    {'outputs': {'ok': False}}, 'plain text', '[1,2]', 'null'])
def test_success_is_not_inferred_from_nested_acceptance_states(value):
    assert interpret(value)['ok'] is True


@pytest.mark.parametrize('name,explicit,expected', [
    ('modify_molecule', None, 90), ('modify_molecule', 7, 7),
    ('resolve_name', None, 570)])
def test_direct_worker_uses_tool_timeout(monkeypatch, name, explicit, expected):
    monkeypatch.delenv('CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS', raising=False)
    observed = {}
    def execute(payload, **options):
        observed.update(options)
        return 0, b'{"ok":true,"result":"done"}', b''
    monkeypatch.setattr(server, '_execute_worker_process', execute)
    server._run_worker(name, [], {}, timeout_seconds=explicit)
    assert observed['timeout_seconds'] == expected


def test_server_instances_pass_their_profile_without_mutating_environment(monkeypatch):
    monkeypatch.setenv('CHEMDRAW_MCP_PROFILE', 'analysis')
    def execute(payload, **options):
        request = json.loads(payload)
        return 0, json.dumps({'ok': True, 'result': request['profile']}).encode(), b''
    monkeypatch.setattr(server, '_execute_worker_process', execute)
    async def scenario():
        core = server._adapt_tool('get_toolkit_capabilities', lambda: None, profile='core')
        office = server._adapt_tool('get_toolkit_capabilities', lambda: None, profile='office')
        return await asyncio.gather(core(), office())
    assert asyncio.run(scenario()) == ['core', 'office']
    import os
    assert os.environ['CHEMDRAW_MCP_PROFILE'] == 'analysis'


def test_core_python_discovery_does_not_require_optional_com(monkeypatch):
    from types import SimpleNamespace
    def run(command, **options):
        assert 'win32com' not in command[-1]
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime_discovery.subprocess, 'run', run)
    assert runtime_discovery._probe_python(Path(sys.executable)) is None


def test_loaded_source_has_version_and_content_identity(monkeypatch):
    import cdxml_toolkit
    from cdxml_toolkit.mcp_runtime import capabilities
    monkeypatch.setattr(capabilities, '_distribution', lambda name: '0.7.0a1' if name == 'cdxml-toolkit-community' else None)
    result = capabilities.get_toolkit_capabilities('summary')
    identity = result['outputs']['runtime_identity']
    assert identity['version'] == cdxml_toolkit.__version__
    assert identity['version'] != '0.7.0a1'
    assert len(identity['code_sha256']) == 64
    assert any('metadata' in warning for warning in result['warnings'])


def test_code_identity_changes_on_module_content_not_cache(tmp_path):
    from cdxml_toolkit.mcp_runtime.capabilities import _code_digest
    module = tmp_path / 'module.py'
    module.write_text('value = 1\n')
    first = _code_digest(tmp_path)
    cache = tmp_path / '__pycache__'
    cache.mkdir()
    (cache / 'junk.pyc').write_bytes(b'cache')
    assert _code_digest(tmp_path) == first
    module.write_text('value = 2\n')
    assert _code_digest(tmp_path) != first


def test_business_failure_is_counted_as_error(monkeypatch):
    from cdxml_toolkit.mcp_runtime import telemetry
    telemetry.configure_tools(['draw_molecule'])
    before = telemetry.render_prometheus()
    monkeypatch.setattr(server, '_execute_worker_process', lambda *a, **k:
        (0, b'{"ok":true,"result":{"ok":false,"error":"invalid"}}', b''))
    result = asyncio.run(server._run_worker_async('draw_molecule', [], {}))
    assert result['ok'] is False
    after = telemetry.render_prometheus()
    label = 'chemdraw_mcp_tool_calls_total{tool="draw_molecule",status="error"}'
    def count(text):
        return next((int(line.split()[-1]) for line in text.splitlines() if line.startswith(label)), 0)
    assert count(after) == count(before) + 1


@pytest.mark.parametrize('profile', ['core', 'codex', 'office', 'analysis', 'chemscript'])
def test_stdio_capabilities_match_listed_tools_and_business_failure(profile):
    import os
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from cdxml_toolkit.mcp_runtime.tool_registry import build_registry
    async def run():
        env = {k: v for k, v in os.environ.items() if k.upper() in {
            'PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP'}}
        env['CHEMDRAW_MCP_PROFILE'] = 'analysis'  # Explicit CLI option must take precedence.
        params = StdioServerParameters(command=sys.executable,
            args=['-B', '-m', 'cdxml_toolkit.mcp_runtime', '--profile', profile], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                names = {tool.name for tool in (await client.list_tools()).tools}
                report = await client.call_tool('get_toolkit_capabilities', {'detail': 'full'})
                value = json.loads(next(c.text for c in report.content if c.type == 'text'))['outputs']
                assert names == set(build_registry(profile)) == {t['name'] for t in value['tools']}
                assert value['profile'] == profile
                assert value['tool_count'] == value['capabilities']['tool_registry']['count'] == len(names)
                result = await client.call_tool('draw_molecule', {'mol_json': {'smiles': 'not-a-smiles'}})
                assert getattr(result, 'is_error', getattr(result, 'isError', False)) is True
    asyncio.run(asyncio.wait_for(run(), timeout=60))


def test_reference_version_follows_loaded_code_not_stale_metadata(monkeypatch):
    import cdxml_toolkit
    from cdxml_toolkit.mcp_runtime.generate_reference import manifest
    assert manifest()['version'] == cdxml_toolkit.__version__
