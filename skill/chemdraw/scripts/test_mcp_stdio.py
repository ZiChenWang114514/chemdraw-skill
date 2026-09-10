"""Cross-process MCP protocol smoke tests that do not invoke ChemDraw COM."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import LATEST_PROTOCOL_VERSION

from cdxml_toolkit.mcp_runtime import mcp_compat
SERVER_MODULE = "cdxml_toolkit.mcp_runtime.mcp_server"


def _input_schema(tool):
    """Read the SDK model field used by MCP 1.x or 2.x."""
    schema = getattr(tool, "input_schema", None)
    return schema if schema is not None else getattr(tool, "inputSchema")


def _model_field(model, snake_case: str, camel_case: str):
    value = getattr(model, snake_case, None)
    return value if value is not None else getattr(model, camel_case)


async def _list_tools():
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {
            "APPDATA", "COMSPEC", "LOCALAPPDATA", "PATH", "PATHEXT",
            "PROGRAMDATA", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "WINDIR",
        }
    }
    environment.update({"TF_CPP_MIN_LOG_LEVEL": "3", "TF_ENABLE_ONEDNN_OPTS": "0"})
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env=environment,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            return initialized, (await session.list_tools()).tools


class MCPStdioTests(unittest.TestCase):
    def test_server_initializes_and_lists_expected_schemas(self):
        initialized, tools = asyncio.run(asyncio.wait_for(_list_tools(), timeout=30))
        expected_protocol = LATEST_PROTOCOL_VERSION
        if mcp_compat.sdk_major() == 2:
            from mcp_types.version import LATEST_HANDSHAKE_VERSION

            expected_protocol = LATEST_HANDSHAKE_VERSION
        self.assertEqual(
            _model_field(initialized, "protocol_version", "protocolVersion"),
            expected_protocol,
        )
        by_name = {tool.name: tool for tool in tools}
        self.assertEqual(len(by_name), 38)
        self.assertIn("inspect_chemdraw_objects_in_office", by_name)
        self.assertIn("replace_chemdraw_objects_in_office", by_name)
        self.assertIn("resolve_name", by_name)
        self.assertIn("embed_cdxml_in_office", by_name)
        self.assertIn("extract_structures_via_decimer_api", by_name)
        self.assertIn("clean_scheme_layout", by_name)
        self.assertIn("diagnose_runtime", by_name)
        self.assertIn("compare_molecules", by_name)
        self.assertIn("batch_compare_molecules", by_name)
        self.assertIn("inspect_chemscript_sdk", by_name)
        self.assertIn("execute_chemscript_sdk", by_name)

        self.assertEqual(
            set(_input_schema(by_name["resolve_name"]).get("required", [])),
            {"query"},
        )
        self.assertEqual(
            set(
                _input_schema(by_name["embed_cdxml_in_office"]).get("required", [])
            ),
            {"cdxml_path", "office_path"},
        )
        self.assertEqual(
            set(
                _input_schema(by_name["inspect_chemdraw_objects_in_office"]).get(
                    "required", []
                )
            ),
            {"input_path"},
        )
        self.assertEqual(
            set(
                _input_schema(by_name["replace_chemdraw_objects_in_office"]).get(
                    "required", []
                )
            ),
            {"input_path", "replacements_manifest"},
        )
        remote_properties = _input_schema(
            by_name["extract_structures_via_decimer_api"]
        )["properties"]
        self.assertIn("confirm_upload", remote_properties)
        self.assertFalse(remote_properties["confirm_upload"]["default"])
        self.assertEqual(
            set(_input_schema(by_name["compare_molecules"]).get("required", [])),
            {"molecule_a", "molecule_b"},
        )
        self.assertEqual(
            set(_input_schema(by_name["batch_compare_molecules"]).get("required", [])),
            {"pairs"},
        )
        self.assertEqual(
            set(_input_schema(by_name["execute_chemscript_sdk"]).get("required", [])),
            {"program"},
        )


if __name__ == "__main__":
    unittest.main()
