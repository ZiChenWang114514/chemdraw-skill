"""CHEMDRAW_OFFLINE=1 keeps every remote lookup and download on the machine."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest
from PIL import Image

from cdxml_toolkit.mcp_runtime import decimer_api
from cdxml_toolkit.mcp_runtime.mcp_server import _worker_environment
from cdxml_toolkit.resolve import cas_resolver, jre_manager, network_policy


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setenv(network_policy.OFFLINE_ENV, "1")


def _no_network(*args, **kwargs):
    raise AssertionError("network used while offline")


def test_offline_flag_values(monkeypatch):
    for value in ("1", "true", "YES", "on"):
        monkeypatch.setenv(network_policy.OFFLINE_ENV, value)
        assert network_policy.network_allowed() is False
    for value in ("", "0", "false"):
        monkeypatch.setenv(network_policy.OFFLINE_ENV, value)
        assert network_policy.network_allowed() is True


def test_offline_pubchem_lookups_never_open_a_connection(offline, monkeypatch):
    monkeypatch.setattr(cas_resolver.urllib.request, "urlopen", _no_network)
    assert cas_resolver.resolve_name_to_smiles("aspirin") is None
    assert cas_resolver._fetch_properties("50-78-2") is None
    assert cas_resolver._fetch_2d_coords(2244) is None


def test_offline_flag_reaches_tool_workers(offline):
    assert _worker_environment()[network_policy.OFFLINE_ENV] == "1"


def test_offline_jre_download_is_refused(offline, monkeypatch, tmp_path):
    monkeypatch.setattr(jre_manager, "_JRE_BASE", tmp_path / "jre")
    monkeypatch.setattr(jre_manager.os, "name", "nt")
    monkeypatch.setattr(jre_manager.urllib.request, "urlopen", _no_network)
    assert jre_manager._download_jre() is None


class _Response:
    def __init__(self, data, headers):
        self._data, self.headers = BytesIO(data), headers

    def read(self, size=-1):
        return self._data.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_jre_download_without_a_published_checksum_is_not_installed(monkeypatch, tmp_path):
    monkeypatch.delenv(network_policy.OFFLINE_ENV, raising=False)
    monkeypatch.setattr(jre_manager, "_JRE_BASE", tmp_path / "jre")
    monkeypatch.setattr(jre_manager.os, "name", "nt")
    monkeypatch.setattr(jre_manager.urllib.request, "urlopen", lambda *a, **k: _Response(b"zip", {}))
    with mock.patch.object(jre_manager, "install_jre_archive") as install:
        assert jre_manager._download_jre() is None
    install.assert_not_called()


def _png(path: Path, **info) -> Path:
    image = Image.new("RGB", (8, 8), "white")
    from PIL import PngImagePlugin
    meta = PngImagePlugin.PngInfo()
    for key, value in info.items():
        meta.add_text(key, value)
    image.save(path, pnginfo=meta)
    return path


def test_offline_decimer_upload_is_refused_with_preflight(offline, tmp_path):
    image = _png(tmp_path / "a.png")
    with mock.patch.object(decimer_api, "urlopen", _no_network):
        with pytest.raises(decimer_api.DecimerAPIError, match="CHEMDRAW_OFFLINE") as caught:
            decimer_api.recognize_image(str(image), confirm_upload=True)
    assert caught.value.preflight["sha256"]


def test_decimer_upload_hides_the_file_name_and_strips_metadata(monkeypatch, tmp_path):
    monkeypatch.delenv(network_policy.OFFLINE_ENV, raising=False)
    image = _png(tmp_path / "unpublished-patent-draft.png", Author="Dr. Example")
    sent = {}

    def fake_urlopen(request, *, timeout):
        sent["body"] = request.data
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'{"reference": null, "smiles": "CCO"}'
        response.geturl.return_value = decimer_api.DEFAULT_ENDPOINT
        response.__enter__.return_value = response
        return response

    monkeypatch.setattr(decimer_api, "urlopen", fake_urlopen)
    result = decimer_api.recognize_image(str(image), confirm_upload=True)
    assert b"unpublished-patent-draft" not in sent["body"]
    assert b"Dr. Example" not in sent["body"]
    assert result["metadata_removed"] == ["Author"]
    assert result["upload_filename"] == "image.png"
