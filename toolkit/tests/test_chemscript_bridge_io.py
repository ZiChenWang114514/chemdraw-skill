"""The ChemScript bridge never waits forever and never blocks on a full stderr pipe."""

import sys

import pytest

from cdxml_toolkit.chemdraw import chemscript_bridge
from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge

SERVER = """
import json, sys, time
print(json.dumps({"ready": True}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    if request["cmd"] == "hang":
        time.sleep(60)
    if request["cmd"] == "noisy":
        sys.stderr.write("x" * 400000)
        sys.stderr.flush()
    if request["cmd"] == "quit":
        break
    print(json.dumps({"ok": True, "cmd": request["cmd"]}), flush=True)
"""


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    script = tmp_path / "server.py"
    script.write_text(SERVER, encoding="utf-8")
    monkeypatch.setattr(chemscript_bridge, "_load_config", lambda: {})
    made = object.__new__(ChemScriptBridge)
    made._mac = None
    made._proc = None
    made._python32 = sys.executable
    made._server_script = str(script)
    yield made
    made.close()


def test_a_call_that_never_answers_times_out_and_the_server_is_stopped(bridge, monkeypatch):
    monkeypatch.setattr(chemscript_bridge, "CALL_TIMEOUT_SECONDS", 1.0)
    assert bridge._call("ping")["ok"] is True
    process = bridge._proc
    with pytest.raises(RuntimeError, match="did not answer within"):
        bridge._call("hang")
    assert process.wait(timeout=10) is not None
    assert bridge._call("ping")["ok"] is True  # a fresh server answers the next call


def test_a_server_that_writes_a_lot_to_stderr_still_answers(bridge, monkeypatch):
    monkeypatch.setattr(chemscript_bridge, "CALL_TIMEOUT_SECONDS", 20.0)
    for _ in range(3):
        assert bridge._call("noisy") == {"ok": True, "cmd": "noisy"}
