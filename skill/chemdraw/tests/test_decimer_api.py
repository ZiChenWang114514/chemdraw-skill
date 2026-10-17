"""Tests for the DECIMER remote API client."""

from __future__ import annotations

import hashlib
from io import StringIO
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
import warnings


from cdxml_toolkit.mcp_runtime import decimer_api as _decimer_api_module
MODULE_PATH = Path(_decimer_api_module.__file__)
from cdxml_toolkit.mcp_runtime import remote_tools as _remote_tools_module
REMOTE_TOOLS_PATH = Path(_remote_tools_module.__file__)


def load_client():
    if not MODULE_PATH.is_file():
        raise AssertionError("cdxml_toolkit.mcp_runtime.decimer_api.py has not been implemented")
    spec = importlib.util.spec_from_file_location("decimer_api", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_remote_tools(client):
    spec = importlib.util.spec_from_file_location("cdxml_toolkit.mcp_runtime.remote_tools_under_test", REMOTE_TOOLS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with mock.patch.dict(sys.modules, {"cdxml_toolkit.mcp_runtime.decimer_api": client}):
        spec.loader.exec_module(module)
    return module


class DecimerAPITests(unittest.TestCase):
    PNG_1X1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03"
        b"\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def test_rejects_upload_without_confirmation(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "image.png"
            image.write_bytes(self.PNG_1X1)
            with self.assertRaisesRegex(client.DecimerAPIError, "confirm_upload"):
                client.recognize_image(str(image))

    def test_tool_returns_http_failure_instead_of_worker_crash(self):
        client = load_client()
        remote_tools = load_remote_tools(client)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            from io import BytesIO
            error = HTTPError(client.DEFAULT_ENDPOINT, 502, "Bad Gateway", {},
                              BytesIO(b"Bad Gateway"))
            with mock.patch.object(client, "urlopen", side_effect=error):
                result = remote_tools.extract_structures_via_decimer_api(
                    str(image), confirm_upload=True
                )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "DECIMER API HTTP 502: Bad Gateway")

    def test_rejects_fake_image_before_network(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "fake.png"
            image.write_text("not an image", encoding="utf-8")
            with mock.patch.object(client, "urlopen") as request:
                with self.assertRaisesRegex(client.DecimerAPIError, "decode"):
                    client.recognize_image(str(image), confirm_upload=True)
            request.assert_not_called()

    def _valid_image(self, root: str) -> Path:
        from PIL import Image

        path = Path(root) / "image.png"
        Image.new("RGB", (8, 8), "white").save(path)
        return path

    def _response(self, client, *, final_url: str | None = None):
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'{"reference": null, "smiles": "CCO"}'
        response.geturl.return_value = final_url or client.DEFAULT_ENDPOINT
        response.__enter__.return_value = response
        return response

    def test_unconfirmed_tool_returns_preflight_without_network(self):
        client = load_client()
        remote_tools = load_remote_tools(client)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            expected_sha256 = hashlib.sha256(image.read_bytes()).hexdigest()
            with mock.patch.object(client, "urlopen") as request:
                try:
                    result = remote_tools.extract_structures_via_decimer_api(str(image))
                except client.DecimerAPIError:
                    result = None

            self.assertIsInstance(result, dict)
            self.assertFalse(result["ok"])
            self.assertIn("confirm_upload", result["error"])
            self.assertEqual(result["preflight"]["sha256"], expected_sha256)
            self.assertEqual(result["preflight"]["file_size_bytes"], image.stat().st_size)
            self.assertEqual(result["preflight"]["image_format"], "PNG")
            self.assertEqual(result["preflight"]["mime_type"], "image/png")
            self.assertEqual(result["preflight"]["image_dimensions"], [8, 8])
            self.assertEqual(
                result["preflight"]["api_origin"], "https://api.naturalproducts.net"
            )
            request.assert_not_called()

    def test_oversized_stat_is_rejected_before_file_read(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            reads = []
            original_read_bytes = Path.read_bytes

            def tracked_read_bytes(path):
                reads.append(path)
                return original_read_bytes(path)

            with mock.patch.dict(
                client.os.environ, {"DECIMER_API_MAX_IMAGE_BYTES": "1"}, clear=False
            ):
                with mock.patch.object(Path, "read_bytes", tracked_read_bytes):
                    with self.assertRaisesRegex(
                        client.DecimerAPIError, "DECIMER_API_MAX_IMAGE_BYTES"
                    ):
                        client.recognize_image(str(image), confirm_upload=True)
            self.assertEqual(reads, [])

    def test_decode_uses_the_supplied_bytes_instead_of_reopening_path(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "changed-after-read.png"
            source.write_text("not the bytes selected for upload", encoding="utf-8")
            try:
                image_format, dimensions, mime_type = client._decode_image(
                    self.PNG_1X1, source, max_pixels=100
                )
            except TypeError as exc:
                self.fail(f"byte-buffer decode contract is missing: {exc}")

            self.assertEqual(image_format, "PNG")
            self.assertEqual(dimensions, (1, 1))
            self.assertEqual(mime_type, "image/png")

    def test_pixel_limit_is_checked_before_full_image_load(self):
        from PIL import Image

        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            image_bytes = image.read_bytes()
            with mock.patch.object(Image.Image, "load", autospec=True) as full_load:
                with self.assertRaisesRegex(client.DecimerAPIError, "MAX_IMAGE_PIXELS"):
                    try:
                        client._decode_image(image_bytes, image, max_pixels=63)
                    except TypeError as exc:
                        self.fail(f"pixel-limit decode contract is missing: {exc}")
            full_load.assert_not_called()

    def test_mime_type_comes_from_decoded_format_not_filename(self):
        from PIL import Image

        client = load_client()
        response = self._response(client)
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "misleading.png"
            Image.new("RGB", (8, 8), "white").save(image, format="JPEG")
            with mock.patch.object(client, "urlopen", return_value=response) as request:
                client.recognize_image(str(image), confirm_upload=True)

            upload_request = request.call_args.args[0]
            self.assertIn(b"Content-Type: image/jpeg", upload_request.data)
            self.assertNotIn(b"Content-Type: image/png", upload_request.data)

    def test_custom_origin_requires_canonical_matching_approval(self):
        client = load_client()
        response = self._response(client, final_url="https://custom.example/upload")
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ,
                {"DECIMER_API_URL": "https://custom.example/upload"},
                clear=False,
            ):
                with mock.patch.object(client, "urlopen", return_value=response) as request:
                    with self.assertRaisesRegex(client.DecimerAPIError, "approved_origin"):
                        client.recognize_image(str(image), confirm_upload=True)
                request.assert_not_called()

                with mock.patch.object(client, "urlopen", return_value=response) as request:
                    try:
                        result = client.recognize_image(
                            str(image),
                            confirm_upload=True,
                            approved_origin="HTTPS://CUSTOM.EXAMPLE:443/",
                        )
                    except TypeError as exc:
                        self.fail(f"origin-bound approval argument is missing: {exc}")
                request.assert_called_once()
                self.assertEqual(result["api_origin"], "https://custom.example")

    def test_same_origin_custom_endpoint_still_requires_approval(self):
        client = load_client()
        endpoint = "https://api.naturalproducts.net/private-upload-route"
        response = self._response(client, final_url=endpoint)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ, {"DECIMER_API_URL": endpoint}, clear=False
            ):
                with mock.patch.object(client, "urlopen", return_value=response) as request:
                    with self.assertRaisesRegex(client.DecimerAPIError, "approved_origin"):
                        client.recognize_image(str(image), confirm_upload=True)
                request.assert_not_called()

                with mock.patch.object(client, "urlopen", return_value=response) as request:
                    result = client.recognize_image(
                        str(image),
                        confirm_upload=True,
                        approved_origin="https://api.naturalproducts.net",
                    )
                request.assert_called_once()
                self.assertEqual(result["api_url"], "https://api.naturalproducts.net")

    def test_sha256_approval_is_bound_to_exact_upload_bytes(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.object(client, "urlopen") as request:
                try:
                    def call():
                        return client.recognize_image(
                            str(image),
                            confirm_upload=True,
                            approved_sha256="0" * 64,
                        )

                    with self.assertRaisesRegex(client.DecimerAPIError, "approved_sha256"):
                        call()
                except TypeError as exc:
                    self.fail(f"SHA-bound approval argument is missing: {exc}")
            request.assert_not_called()

    def test_remote_tool_keeps_existing_arguments_and_defaults(self):
        client = load_client()
        remote_tools = load_remote_tools(client)
        parameters = inspect.signature(
            remote_tools.extract_structures_via_decimer_api
        ).parameters
        expected_defaults = {
            "image_path": inspect.Parameter.empty,
            "hand_drawn": False,
            "output_path": None,
            "timeout_seconds": 600,
            "confirm_upload": False,
        }
        self.assertEqual(
            {name: parameters[name].default for name in expected_defaults},
            expected_defaults,
        )
        self.assertIn("approved_sha256", parameters)
        self.assertIn("approved_origin", parameters)

    def test_http_endpoint_is_rejected_even_when_explicitly_approved(self):
        client = load_client()
        endpoint = "http://custom.example/upload"
        response = self._response(client, final_url=endpoint)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ,
                {"DECIMER_API_URL": endpoint},
                clear=False,
            ):
                with mock.patch.object(
                    client, "urlopen", return_value=response
                ) as request:
                    with self.assertRaisesRegex(client.DecimerAPIError, "HTTPS"):
                        client.recognize_image(
                            str(image),
                            confirm_upload=True,
                            approved_origin="http://custom.example",
                        )
                request.assert_not_called()

    def test_endpoint_rejects_url_userinfo_without_leaking_it(self):
        client = load_client()
        secret = "user:top-secret"
        endpoint = f"https://{secret}@custom.example/upload"
        response = self._response(client, final_url=endpoint)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ, {"DECIMER_API_URL": endpoint}, clear=False
            ):
                with mock.patch.object(
                    client, "urlopen", return_value=response
                ) as request:
                    with self.assertRaises(client.DecimerAPIError) as raised:
                        client.recognize_image(
                            str(image),
                            confirm_upload=True,
                            approved_origin="https://custom.example",
                        )
                request.assert_not_called()
            self.assertIn("userinfo", str(raised.exception))
            self.assertNotIn("top-secret", str(raised.exception))

    def test_endpoint_rejects_query_secrets_without_leaking_them(self):
        client = load_client()
        secret = "query-secret-value"
        endpoint = f"https://custom.example/upload?token={secret}"
        response = self._response(client, final_url=endpoint)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ, {"DECIMER_API_URL": endpoint}, clear=False
            ):
                with mock.patch.object(
                    client, "urlopen", return_value=response
                ) as request:
                    with self.assertRaises(client.DecimerAPIError) as raised:
                        client.recognize_image(
                            str(image),
                            confirm_upload=True,
                            approved_origin="https://custom.example",
                        )
                request.assert_not_called()
            self.assertIn("query", str(raised.exception))
            self.assertNotIn(secret, str(raised.exception))

    def _redirect_handler(self, client):
        try:
            return client._SameOriginHTTPSRedirectHandler(
                "https://api.naturalproducts.net"
            )
        except AttributeError as exc:
            self.fail(f"same-origin redirect policy is missing: {exc}")

    def test_redirect_handler_rejects_cross_origin_before_following(self):
        client = load_client()
        handler = self._redirect_handler(client)
        request = client.Request(
            client.DEFAULT_ENDPOINT, data=b"upload", method="POST"
        )
        with self.assertRaisesRegex(client.DecimerAPIError, "cross-origin redirect"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://attacker.example/collect",
            )

    def test_redirect_handler_rejects_https_downgrade_before_following(self):
        client = load_client()
        handler = self._redirect_handler(client)
        request = client.Request(
            client.DEFAULT_ENDPOINT, data=b"upload", method="POST"
        )
        with self.assertRaisesRegex(client.DecimerAPIError, "HTTPS downgrade"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "http://api.naturalproducts.net/collect",
            )

    def test_redirect_handler_allows_same_origin_https_target(self):
        client = load_client()
        handler = self._redirect_handler(client)
        request = client.Request(
            client.DEFAULT_ENDPOINT, data=b"upload", method="POST"
        )
        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "/latest/ocsr/process-upload/",
        )
        self.assertEqual(
            client._canonical_origin(redirected.full_url),
            "https://api.naturalproducts.net",
        )

    def test_rejects_cross_origin_or_downgraded_final_url(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            final_urls = (
                "https://attacker.example/collect",
                "http://api.naturalproducts.net/collect",
            )
            for final_url in final_urls:
                with self.subTest(final_url=final_url):
                    response = self._response(client, final_url=final_url)
                    with mock.patch.object(client, "urlopen", return_value=response):
                        with self.assertRaisesRegex(client.DecimerAPIError, "final URL"):
                            client.recognize_image(str(image), confirm_upload=True)

    def test_http_error_body_read_is_bounded_and_closed(self):
        client = load_client()

        class RecordingReader:
            def __init__(self, data):
                self.data = data
                self.read_sizes = []
                self.closed = False

            def read(self, size=-1):
                self.read_sizes.append(size)
                return self.data if size < 0 else self.data[:size]

            def close(self):
                self.closed = True

        body = RecordingReader(b"failure!https://example.invalid/?token=do-not-read")
        error = HTTPError(
            client.DEFAULT_ENDPOINT, 503, "down", {}, body
        )
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ,
                {"DECIMER_API_MAX_RESPONSE_BYTES": "8"},
                clear=False,
            ):
                with mock.patch.object(client, "urlopen", side_effect=error):
                    with self.assertRaisesRegex(client.DecimerAPIError, "HTTP 503"):
                        client.recognize_image(str(image), confirm_upload=True)
        self.assertEqual(body.read_sizes, [9])
        self.assertTrue(body.closed)

    def test_normal_response_body_read_remains_bounded(self):
        client = load_client()
        response = self._response(client)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ,
                {"DECIMER_API_MAX_RESPONSE_BYTES": "64"},
                clear=False,
            ):
                with mock.patch.object(client, "urlopen", return_value=response):
                    client.recognize_image(str(image), confirm_upload=True)
        response.read.assert_called_once_with(65)

    def test_transport_error_redacts_url_credentials_and_query(self):
        client = load_client()
        leaked_url = "https://user:password@example.invalid/path?token=query-secret"
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.object(
                client, "urlopen", side_effect=URLError(f"failed at {leaked_url}")
            ):
                with self.assertRaises(client.DecimerAPIError) as raised:
                    client.recognize_image(str(image), confirm_upload=True)
        message = str(raised.exception)
        self.assertIn("connection failed", message)
        self.assertNotIn("password", message)
        self.assertNotIn("query-secret", message)

    def test_custom_endpoint_metadata_is_reduced_to_approved_origin(self):
        client = load_client()
        endpoint = "https://custom.example/private-route-value/upload"
        response = self._response(client, final_url=endpoint)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ, {"DECIMER_API_URL": endpoint}, clear=False
            ):
                with mock.patch.object(client, "urlopen", return_value=response):
                    result = client.recognize_image(
                        str(image),
                        confirm_upload=True,
                        approved_origin="https://custom.example",
                    )
        self.assertEqual(result["api_url"], "https://custom.example")
        self.assertNotIn("private-route-value", json.dumps(result))

    def test_invalid_response_limit_is_normalized_before_network(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ,
                {"DECIMER_API_MAX_RESPONSE_BYTES": "not-an-integer"},
                clear=False,
            ):
                with mock.patch.object(client, "urlopen") as request:
                    with self.assertRaisesRegex(
                        client.DecimerAPIError,
                        "DECIMER_API_MAX_RESPONSE_BYTES must be a positive integer",
                    ):
                        client.recognize_image(str(image), confirm_upload=True)
                request.assert_not_called()

    def test_existing_output_is_rejected_before_upload(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            destination = Path(tmp) / "result.json"
            destination.write_text("keep-me", encoding="utf-8")
            with mock.patch.object(client, "urlopen", return_value=self._response(client)) as request:
                with self.assertRaisesRegex(client.DecimerAPIError, "overwrite"):
                    client.recognize_image(
                        str(image),
                        confirm_upload=True,
                        output_path=str(destination),
                    )
            request.assert_not_called()
            self.assertEqual(destination.read_text(encoding="utf-8"), "keep-me")

    def test_unwritable_output_parent_is_rejected_before_upload(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            destination = Path(tmp) / "missing" / "result.json"
            with mock.patch.object(
                client.tempfile, "mkstemp", side_effect=PermissionError("denied")
            ), mock.patch.object(client, "urlopen") as request:
                with self.assertRaisesRegex(client.DecimerAPIError, "output directory"):
                    client.recognize_image(
                        str(image),
                        output_path=str(destination),
                        confirm_upload=True,
                    )
            request.assert_not_called()

    def test_atomic_write_does_not_clobber_racing_destination(self):
        client = load_client()
        response = self._response(client)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            destination = Path(tmp) / "result.json"

            def racing_install(_temporary, target):
                Path(target).write_text("competitor", encoding="utf-8")
                raise FileExistsError("destination won the race")

            with mock.patch.object(client, "urlopen", return_value=response):
                with mock.patch.object(client.os, "link", side_effect=racing_install):
                    with self.assertRaisesRegex(client.DecimerAPIError, "overwrite"):
                        client.recognize_image(
                            str(image),
                            confirm_upload=True,
                            output_path=str(destination),
                        )

            self.assertEqual(destination.read_text(encoding="utf-8"), "competitor")
            self.assertEqual(list(Path(tmp).glob(".result.json.*.tmp")), [])

    def test_disk_bytes_exactly_serialize_returned_result(self):
        client = load_client()
        response = self._response(client)
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            destination = Path(tmp) / "result.json"
            with mock.patch.object(client, "urlopen", return_value=response):
                result = client.recognize_image(
                    str(image),
                    confirm_upload=True,
                    output_path=str(destination),
                )

            expected_bytes = json.dumps(result, indent=2).encode("utf-8")
            self.assertEqual(destination.read_bytes(), expected_bytes)
            self.assertEqual(json.loads(expected_bytes), result)

    def test_cli_forwards_optional_sha256_and_origin_approvals(self):
        client = load_client()
        digest = "a" * 64
        stdout = StringIO()
        argv = [
            "decimer_api.py",
            "image.png",
            "--confirm-upload",
            "--approved-sha256",
            digest,
            "--approved-origin",
            "https://custom.example",
        ]
        with mock.patch.object(client, "recognize_image", return_value={"ok": True}) as recognize:
            with mock.patch.object(client.sys, "argv", argv):
                with mock.patch.object(client.sys, "stdout", stdout):
                    try:
                        exit_code = client.main()
                    except SystemExit as exc:
                        self.fail(f"CLI approval arguments are missing: {exc}")

        self.assertEqual(exit_code, 0)
        self.assertEqual(recognize.call_args.kwargs["approved_sha256"], digest)
        self.assertEqual(
            recognize.call_args.kwargs["approved_origin"], "https://custom.example"
        )

    def test_canonical_origin_normalizes_idna_trailing_dot_and_default_port(self):
        client = load_client()
        self.assertEqual(
            client._canonical_origin("https://BÜCHER.example.:443/upload"),
            "https://xn--bcher-kva.example",
        )

    def test_non_json_error_redacts_secret_url(self):
        client = load_client()
        leaked_url = "https://user:password@example.invalid/path?token=query-secret"
        response = self._response(client)
        response.read.return_value = f"failed at {leaked_url}".encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.object(client, "urlopen", return_value=response):
                with self.assertRaises(client.DecimerAPIError) as raised:
                    client.recognize_image(str(image), confirm_upload=True)
        message = str(raised.exception)
        self.assertIn("non-JSON", message)
        self.assertNotIn("password", message)
        self.assertNotIn("query-secret", message)

    def test_api_error_payload_is_redacted_and_bounded(self):
        client = load_client()
        leaked_url = "https://user:password@example.invalid/path?token=query-secret"
        detail = f"failed at {leaked_url} " + ("x" * 5000)
        with self.assertRaises(client.DecimerAPIError) as raised:
            client.normalize_api_payload({"detail": detail})
        message = str(raised.exception)
        self.assertNotIn("password", message)
        self.assertNotIn("query-secret", message)
        self.assertLessEqual(len(message), 1100)

    def test_http_error_read_failure_is_normalized_redacted_and_closed(self):
        client = load_client()

        class FailingReader:
            def __init__(self):
                self.read_sizes = []
                self.closed = False

            def read(self, size=-1):
                self.read_sizes.append(size)
                raise OSError(
                    "failed at https://user:password@example.invalid/?token=query-secret"
                )

            def close(self):
                self.closed = True

        body = FailingReader()
        error = HTTPError(client.DEFAULT_ENDPOINT, 503, "down", {}, body)
        caught = None
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.dict(
                client.os.environ,
                {"DECIMER_API_MAX_RESPONSE_BYTES": "8"},
                clear=False,
            ):
                with mock.patch.object(client, "urlopen", side_effect=error):
                    try:
                        client.recognize_image(str(image), confirm_upload=True)
                    except Exception as exc:
                        caught = exc
        self.assertIsInstance(caught, client.DecimerAPIError)
        self.assertIn("HTTP 503", str(caught))
        self.assertNotIn("password", str(caught))
        self.assertNotIn("query-secret", str(caught))
        self.assertEqual(body.read_sizes, [9])
        self.assertTrue(body.closed)

    def test_decompression_bomb_warning_is_normalized(self):
        from PIL import Image

        client = load_client()
        original_open = Image.open

        def warned_open(*args, **kwargs):
            warnings.warn("suspicious dimensions", Image.DecompressionBombWarning)
            return original_open(*args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.object(Image, "open", side_effect=warned_open):
                with self.assertRaisesRegex(client.DecimerAPIError, "decompression bomb"):
                    client._decode_image(image.read_bytes(), image, max_pixels=100)

    def test_invalid_image_limits_are_normalized_before_read_or_network(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            for name in (
                "DECIMER_API_MAX_IMAGE_BYTES",
                "DECIMER_API_MAX_IMAGE_PIXELS",
            ):
                with self.subTest(name=name):
                    with mock.patch.dict(
                        client.os.environ, {name: "invalid"}, clear=False
                    ):
                        with mock.patch.object(client, "_read_image_bytes") as read_image:
                            with mock.patch.object(client, "urlopen") as request:
                                with self.assertRaisesRegex(
                                    client.DecimerAPIError,
                                    f"{name} must be a positive integer",
                                ):
                                    client.recognize_image(
                                        str(image), confirm_upload=True
                                    )
                        read_image.assert_not_called()
                        request.assert_not_called()

    def test_missing_pillow_dependency_is_normalized(self):
        client = load_client()
        original_import = __import__

        def controlled_import(name, *args, **kwargs):
            if name == "PIL":
                raise ImportError("Pillow is unavailable")
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "image.png"
            source.write_bytes(self.PNG_1X1)
            with mock.patch("builtins.__import__", side_effect=controlled_import):
                with self.assertRaisesRegex(client.DecimerAPIError, "Pillow"):
                    client._decode_image(self.PNG_1X1, source, max_pixels=100)

    def test_cli_fallback_error_redacts_secret_url(self):
        client = load_client()
        leaked_url = "https://user:password@example.invalid/path?token=query-secret"
        stdout = StringIO()
        with mock.patch.object(client.sys, "argv", ["decimer_api.py", "image.png"]):
            with mock.patch.object(client.sys, "stdout", stdout):
                with mock.patch.object(
                    client,
                    "recognize_image",
                    side_effect=RuntimeError(f"failed at {leaked_url}"),
                ):
                    exit_code = client.main()
        output = stdout.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertNotIn("password", output)
        self.assertNotIn("query-secret", output)

    def test_normalizes_http_error(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            error = HTTPError("https://example.invalid", 503, "down", {}, None)
            error.read = mock.Mock(return_value=b"service unavailable")
            with mock.patch.object(client, "urlopen", side_effect=error):
                with self.assertRaisesRegex(client.DecimerAPIError, "HTTP 503"):
                    client.recognize_image(str(image), confirm_upload=True)

    def test_normalizes_connection_and_timeout_errors(self):
        client = load_client()
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            with mock.patch.object(client, "urlopen", side_effect=URLError("offline")):
                with self.assertRaisesRegex(client.DecimerAPIError, "connection failed"):
                    client.recognize_image(str(image), confirm_upload=True)
            with mock.patch.object(client, "urlopen", side_effect=TimeoutError("late")):
                with self.assertRaisesRegex(client.DecimerAPIError, "transport failed"):
                    client.recognize_image(str(image), confirm_upload=True)

    def test_written_result_matches_returned_result(self):
        client = load_client()
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'{"reference": null, "smiles": "CCO"}'
        response.__enter__.return_value = response
        with tempfile.TemporaryDirectory() as tmp:
            image = self._valid_image(tmp)
            destination = Path(tmp) / "result.json"
            with mock.patch.object(client, "urlopen", return_value=response):
                result = client.recognize_image(
                    str(image), confirm_upload=True, output_path=str(destination)
                )
            self.assertEqual(result, __import__("json").loads(destination.read_text(encoding="utf-8")))

    def test_normalizes_documented_string_response(self):
        client = load_client()
        result = client.normalize_api_payload(
            {"message": "Success", "reference": "sample", "smiles": "CCO"}
        )
        self.assertEqual(result["reference"], "sample")
        self.assertEqual(result["smiles"], ["CCO"])

    def test_normalizes_live_array_response(self):
        client = load_client()
        result = client.normalize_api_payload(
            {"reference": None, "smiles": ["CC(=O)O", "[Cr]"]}
        )
        self.assertIsNone(result["reference"])
        self.assertEqual(result["smiles"], ["CC(=O)O", "[Cr]"])

    def test_rejects_missing_smiles(self):
        client = load_client()
        with self.assertRaises(client.DecimerAPIError):
            client.normalize_api_payload({"detail": "processing failed"})

    def test_multipart_uses_openapi_field_names(self):
        client = load_client()
        content_type, body = client.build_multipart_body(
            filename="structure.png",
            mime_type="image/png",
            image_bytes=b"PNGDATA",
            hand_drawn=True,
            boundary="test-boundary",
        )
        self.assertEqual(content_type, "multipart/form-data; boundary=test-boundary")
        self.assertIn(b'name="file"; filename="structure.png"', body)
        self.assertIn(b"Content-Type: image/png", body)
        self.assertIn(b'name="hand_drawn"', body)
        self.assertIn(b"true", body)
        self.assertIn(b"PNGDATA", body)


if __name__ == "__main__":
    unittest.main()
