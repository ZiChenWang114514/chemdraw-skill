from __future__ import annotations

import sys
import unittest

from cdxml_toolkit.mcp_runtime import mcp_compat
class MCPCompatibilityTests(unittest.TestCase):
    def test_installed_sdk_major_is_supported(self):
        self.assertIn(mcp_compat.sdk_major(), mcp_compat.SUPPORTED_MCP_MAJORS)

    def test_server_class_matches_installed_sdk(self):
        server_type = mcp_compat.server_class()
        expected_name = "MCPServer" if mcp_compat.sdk_major() == 2 else "FastMCP"
        self.assertEqual(server_type.__name__, expected_name)

    def test_legacy_alias_is_available_after_installation(self):
        mcp_compat.install_legacy_fastmcp_alias()
        from mcp.server.fastmcp import FastMCP

        self.assertIs(FastMCP, mcp_compat.server_class())
        self.assertIn("mcp.server.fastmcp", sys.modules)

    def test_unsupported_major_has_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported MCP Python SDK 3.0.0"):
            mcp_compat.sdk_major("3.0.0")


if __name__ == "__main__":
    unittest.main()
