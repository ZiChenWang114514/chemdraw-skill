from __future__ import annotations

import json
from unittest import mock

from cdxml_toolkit.mcp_runtime import capabilities, mcp_server, tool_registry


def test_profiles_are_stable_and_capability_aware():
    expected_counts = {
        "core": 16,
        "codex": 38,
        "office": 21,
        "analysis": 20,
        "chemscript": 20,
    }
    assert {
        profile: len(tool_registry.build_registry(profile))
        for profile in expected_counts
    } == expected_counts
    assert "get_toolkit_capabilities" in tool_registry.build_registry("core")
    assert "fill_office_template" in tool_registry.build_registry("office")
    assert "analyze_lcms_series" in tool_registry.build_registry("analysis")
    assert "execute_chemscript_sdk" in tool_registry.build_registry("chemscript")


def test_capability_report_is_content_free_and_has_schema_digest():
    with mock.patch.object(
        capabilities, "_distribution", side_effect=lambda name: {"mcp": "2.0.0"}.get(name)
    ), mock.patch(
        "cdxml_toolkit.mcp_runtime.runtime_diagnostics.diagnose_runtime",
        return_value={"capabilities": {"office": {"status": "available"}}},
    ):
        result = capabilities.get_toolkit_capabilities()

    assert result["ok"] is True
    assert result["metadata"] == {"content_free": True}
    assert result["outputs"]["tool_count"] == 38
    assert len(result["outputs"]["tool_schema_sha256"]) == 64
    assert "request_payload" not in result["outputs"]


def test_worker_success_envelope_preserves_result_and_adds_uniform_fields():
    raw_result = {
        "ok": True,
        "outputs": {"value": 3},
        "warnings": ["review"],
        "metadata": {"source": "fixture"},
    }
    envelope = json.dumps({"ok": True, "result": raw_result}).encode()
    result = mcp_server._interpret_worker_result(
        "fixture_tool",
        0,
        envelope,
        b"",
        timeout=30,
        duration=0.125,
        output_limit=1024,
    )

    assert result["ok"] is True
    assert result["result"] == raw_result
    assert result["outputs"] == {"value": 3}
    assert result["warnings"] == ["review"]
    assert result["artifacts"] == []
    assert result["metadata"]["duration_ms"] == 125
