"""Budgets for what an MCP client loads before the first call: the tools/list payload and tool counts.

Every listed tool costs a client context before any work starts, so growth must be a decision. The
ceilings below are the only place these budgets live. They were set at the measured size plus about
5 % (default `standard` profile: about 50,000 bytes and 26 tools; `full` is 71 tools and about
100,000 bytes); later work is expected to lower them, never to
raise them silently. When a change trips a budget, shrink descriptions or schemas, move the tool
to a narrower profile, or raise the ceiling in the same change with the reason in its message.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from cdxml_toolkit.mcp_runtime import mcp_server
from cdxml_toolkit.mcp_runtime.tool_registry import DEFAULT_PROFILE, build_registry

# Compact JSON of the default profile's tools/list result, in UTF-8 bytes.
DEFAULT_PROFILE_SCHEMA_BYTES_MAX = 53_000
# Most tools each profile may list.
PROFILE_TOOL_COUNT_MAX = {"full": 71, "standard": 26, "core": 16, "office": 21, "analysis": 21, "chemscript": 22}


def _listed_tools(profile: str):
    return asyncio.run(mcp_server.build_server(profile=profile).list_tools())


def test_default_profile_tools_list_stays_within_its_size_budget():
    tools = _listed_tools(DEFAULT_PROFILE)
    payload = json.dumps(
        [tool.model_dump(mode="json", exclude_none=True) for tool in tools],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert len(payload) <= DEFAULT_PROFILE_SCHEMA_BYTES_MAX, (
        f"tools/list for the {DEFAULT_PROFILE!r} profile is {len(payload)} bytes, "
        f"over the {DEFAULT_PROFILE_SCHEMA_BYTES_MAX} byte budget"
    )


@pytest.mark.parametrize("profile", sorted(PROFILE_TOOL_COUNT_MAX))
def test_profile_tool_count_stays_within_its_budget(profile):
    count = len(build_registry(profile))
    assert count <= PROFILE_TOOL_COUNT_MAX[profile], (
        f"the {profile!r} profile lists {count} tools, over its budget of {PROFILE_TOOL_COUNT_MAX[profile]}"
    )


def test_every_profile_has_a_budget():
    from cdxml_toolkit.mcp_runtime.tool_registry import SUPPORTED_PROFILES

    assert set(SUPPORTED_PROFILES) == set(PROFILE_TOOL_COUNT_MAX)


def test_no_tool_lists_a_catch_all_argument():
    for tool in _listed_tools("full"):
        schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
        assert not {"args", "kwargs"} & set(schema.get("properties", {})), tool.name
        assert not {"args", "kwargs"} & set(schema.get("required", [])), tool.name
