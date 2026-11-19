"""One result contract for every tool call.

``ok`` says whether the call completed and its result passed its checks,
``status`` carries the tool's own conclusion, ``error`` is ``{code, message, hint?}``
and ``result`` is always an object, never a JSON document inside a string.
"""

from __future__ import annotations

import json

from cdxml_toolkit.mcp_runtime import mcp_server


def _interpret(raw_result, returncode=0):
    envelope = json.dumps({"ok": True, "result": raw_result}).encode()
    return mcp_server._interpret_worker_result(
        "fixture_tool", returncode, envelope, b"", timeout=30, duration=0.1, output_limit=1 << 20
    )


def test_json_text_result_is_returned_as_an_object():
    outcome = _interpret(json.dumps({"ok": True, "smiles": "CCO"}))
    assert outcome["result"] == {"ok": True, "smiles": "CCO"}


def test_plain_text_result_stays_text():
    outcome = _interpret("<CDXML/>")
    assert outcome["ok"] is True
    assert outcome["result"] == "<CDXML/>"


def test_outputs_is_not_a_second_copy_of_the_result():
    outcome = _interpret({"smiles": "CCO"})
    assert "outputs" not in outcome
    assert _interpret({"ok": True, "outputs": {"value": 3}})["outputs"] == {"value": 3}


def test_status_is_lifted_and_does_not_decide_ok():
    outcome = _interpret({"ok": True, "status": "needs_review", "outputs": {}})
    assert outcome["ok"] is True
    assert outcome["status"] == "needs_review"
    assert "status" not in _interpret({"smiles": "CCO"})


def test_business_failure_keeps_code_message_and_hint():
    outcome = _interpret({
        "ok": False,
        "error": {"code": "postcondition_failed", "message": "structure changed", "hint": "inspect rejected_result"},
        "rejected_result": {"smiles": "CC"},
    })
    assert outcome["ok"] is False
    assert outcome["error"] == {
        "code": "postcondition_failed",
        "message": "structure changed",
        "hint": "inspect rejected_result",
    }
    assert outcome["result"]["rejected_result"] == {"smiles": "CC"}


def test_json_text_failure_is_a_failure():
    outcome = _interpret(json.dumps({"ok": False, "error": "no such name"}))
    assert outcome["ok"] is False
    assert outcome["error"]["code"] == "tool_business_error"
    assert outcome["error"]["message"] == "no such name"
