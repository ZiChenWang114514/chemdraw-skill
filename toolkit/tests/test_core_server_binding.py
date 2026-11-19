"""The core server has no authentication, so it only ever listens on this machine."""

import pytest

pytest.importorskip("mcp")

from cdxml_toolkit.mcp_server import server  # noqa: E402


def test_http_listens_on_loopback_by_default():
    assert server.http_bind_host(None) == "127.0.0.1"
    assert server.http_bind_host("localhost") == "localhost"
    assert server.http_bind_host("::1") == "::1"


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.20", "example.org"])
def test_a_network_address_is_refused_with_the_way_out(host):
    with pytest.raises(SystemExit) as error:
        server.http_bind_host(host)
    assert "cdxml-mcp" in str(error.value) and "CHEMDRAW_MCP_HTTP_API_KEY" in str(error.value)
