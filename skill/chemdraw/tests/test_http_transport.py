from __future__ import annotations

import asyncio
import json
import time
import unittest
from unittest import mock

from cdxml_toolkit.mcp_runtime import mcp_server
from cdxml_toolkit.mcp_runtime import telemetry
async def asgi_request(app, path: str, headers: list[tuple[bytes, bytes]] | None = None):
    sent = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8029),
    }
    await app(scope, receive, send)
    status = next(item["status"] for item in sent if item["type"] == "http.response.start")
    body = b"".join(item.get("body", b"") for item in sent if item["type"] == "http.response.body")
    return status, body


class HttpTransportTests(unittest.TestCase):
    def setUp(self):
        telemetry.reset_for_tests()

    def test_stdio_remains_the_default_transport(self):
        args = mcp_server.parse_args([])
        self.assertEqual(args.transport, "stdio")

    def test_http_interrupt_exits_without_a_traceback(self):
        with mock.patch.object(
            mcp_server, "run_streamable_http", side_effect=KeyboardInterrupt
        ):
            self.assertIsNone(
                mcp_server.main(["--transport", "streamable-http"])
            )

    def test_remote_bind_requires_api_key_and_explicit_allowed_host(self):
        with self.assertRaisesRegex(ValueError, "API key"):
            mcp_server.resolve_http_configuration(
                host="0.0.0.0", port=8029, allowed_hosts=[], allowed_origins=[], environ={}
            )
        with self.assertRaisesRegex(ValueError, "allowed host"):
            mcp_server.resolve_http_configuration(
                host="0.0.0.0",
                port=8029,
                allowed_hosts=[],
                allowed_origins=[],
                environ={"CHEMDRAW_MCP_HTTP_API_KEY": "x" * 32},
            )

    def test_bearer_auth_protects_mcp_and_metrics_but_health_is_public(self):
        async def downstream(scope, receive, send):
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        app = mcp_server.ApiKeyMiddleware(downstream, "secret-token", public_paths={"/health"})
        status, _ = asyncio.run(asgi_request(app, "/mcp"))
        self.assertEqual(status, 401)
        status, _ = asyncio.run(asgi_request(app, "/metrics"))
        self.assertEqual(status, 401)
        status, _ = asyncio.run(asgi_request(app, "/health"))
        self.assertEqual(status, 204)
        status, _ = asyncio.run(
            asgi_request(app, "/mcp", [(b"authorization", b"Bearer secret-token")])
        )
        self.assertEqual(status, 204)

    def test_metrics_record_duration_timeout_worker_error_and_queue_without_payload(self):
        secret_molecule = "F/C=C\\F private"
        telemetry.configure_tools({"compare_molecules", "render_to_png"})
        telemetry.worker_started("compare_molecules")
        telemetry.worker_finished(
            "compare_molecules", duration_seconds=0.25, ok=True, error_code=None
        )
        telemetry.worker_started("render_to_png")
        telemetry.native_wait_started()
        telemetry.native_wait_finished()
        telemetry.worker_finished(
            "render_to_png", duration_seconds=2.0, ok=False, error_code="tool_timeout"
        )
        telemetry.worker_started("render_to_png")
        telemetry.worker_finished(
            "render_to_png", duration_seconds=0.1, ok=False, error_code="worker_protocol_error"
        )
        rendered = telemetry.render_prometheus()
        self.assertIn("chemdraw_mcp_tool_duration_seconds_bucket", rendered)
        self.assertIn("chemdraw_mcp_worker_timeouts_total", rendered)
        self.assertIn("chemdraw_mcp_worker_failures_total", rendered)
        self.assertIn("chemdraw_mcp_chemdraw_queue_length 0", rendered)
        self.assertNotIn(secret_molecule, rendered)

    def test_health_snapshot_is_content_free(self):
        telemetry.configure_tools({"compare_molecules"})
        snapshot = telemetry.health_snapshot(tool_count=34)
        encoded = json.dumps(snapshot)
        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(snapshot["tool_count"], 34)
        self.assertNotIn("molecule", encoded.lower())
        self.assertLessEqual(snapshot["uptime_seconds"], time.monotonic())

    def test_parent_scheduler_reports_one_waiting_chemdraw_call(self):
        async def exercise():
            release = asyncio.Event()
            first_started = asyncio.Event()
            call_count = 0

            async def fake_worker(name, args, kwargs, timeout_seconds=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    first_started.set()
                    await release.wait()
                return {"ok": True, "result": name, "metadata": {"tool": name}}

            with mock.patch.object(
                mcp_server, "_run_worker_async_unlocked", side_effect=fake_worker
            ):
                first = asyncio.create_task(
                    mcp_server._run_worker_async(
                        "render_to_png", [], {}, resource_class="chemdraw_com"
                    )
                )
                await first_started.wait()
                second = asyncio.create_task(
                    mcp_server._run_worker_async(
                        "render_to_png", [], {}, resource_class="chemdraw_com"
                    )
                )
                await asyncio.sleep(0.05)
                during = telemetry.health_snapshot(tool_count=34)
                release.set()
                await asyncio.gather(first, second)
                after = telemetry.health_snapshot(tool_count=34)
            return during, after

        telemetry.configure_tools({"render_to_png"})
        during, after = asyncio.run(exercise())
        self.assertEqual(during["chemdraw_active"], 1)
        self.assertEqual(during["chemdraw_queue_length"], 1)
        self.assertEqual(after["chemdraw_active"], 0)
        self.assertEqual(after["chemdraw_queue_length"], 0)


if __name__ == "__main__":
    unittest.main()
