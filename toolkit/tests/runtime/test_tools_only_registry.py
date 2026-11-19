"""A process that only calls tools gets the same registry without importing the MCP SDK."""

import json
import subprocess
import sys

SCRIPT = """
import json, sys
if sys.argv[1] == "light":
    from cdxml_toolkit.mcp_server import _compat
    _compat.tools_only()
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry
registry = build_registry("full")
print(json.dumps({
    "mcp_loaded": "mcp" in sys.modules,
    "tools": {name: [spec.description, spec.timeout_seconds, spec.resource_class, spec.group]
              for name, spec in sorted(registry.items())},
}))
"""


def _registry(mode):
    done = subprocess.run([sys.executable, "-c", SCRIPT, mode], capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_tools_only_registry_matches_the_server_registry_and_skips_the_sdk():
    full, light = _registry("full"), _registry("light")
    assert full["mcp_loaded"] is True
    assert light["mcp_loaded"] is False
    assert light["tools"] == full["tools"]


def test_the_committed_manifest_is_current():
    from cdxml_toolkit.mcp_runtime import tool_registry

    assert tool_registry.MANIFEST_PATH.read_text(encoding="utf-8") == tool_registry.render_manifest(), (
        "run `cdx.py regen-signatures`"
    )


def test_every_tool_loads_alone_as_the_same_spec():
    from cdxml_toolkit.mcp_runtime import tool_registry

    registry = tool_registry.build_registry("full")
    assert set(tool_registry.tool_manifest()) == set(registry)
    for name, spec in registry.items():
        alone = tool_registry.load_tool(name)
        assert alone is not None, name
        assert alone.function is spec.function, name
        assert (alone.timeout_seconds, alone.resource_class, alone.group, alone.description) == (
            spec.timeout_seconds, spec.resource_class, spec.group, spec.description), name


def test_a_tool_the_manifest_does_not_place_falls_back_to_the_full_registry(monkeypatch):
    from cdxml_toolkit.mcp_runtime import tool_registry

    monkeypatch.setattr(tool_registry, "tool_manifest", lambda: {"resolve_name": {"group": "extended", "module": "ui_apps", "attribute": "UI_APP_TOOLS"}})
    assert tool_registry.load_tool("resolve_name") is None
    assert tool_registry.load_tool("no_such_tool") is None


def test_one_extended_tool_does_not_import_the_other_tool_modules():
    script = (
        "import sys\n"
        "from cdxml_toolkit.mcp_server import _compat; _compat.tools_only()\n"
        "from cdxml_toolkit.mcp_runtime.tool_registry import load_tool\n"
        "assert load_tool('get_toolkit_capabilities') is not None\n"
        "loaded = [m for m in ('figure_tools', 'report_tools', 'markush_tools') if 'cdxml_toolkit.mcp_runtime.' + m in sys.modules]\n"
        "print('LOADED', loaded)\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    assert "LOADED []" in done.stdout
