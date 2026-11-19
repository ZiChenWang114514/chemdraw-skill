"""One worker process can run the same tool once per item."""

import pytest

from cdxml_toolkit.mcp_runtime import mcp_server


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def test_each_call_gets_its_own_result_from_one_process(monkeypatch):
    launches = []
    real = mcp_server._execute_worker_process

    def counting(*args, **kwargs):
        launches.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(mcp_server, "_execute_worker_process", counting)
    calls = [{"molecules": [{"smiles": smiles}]} for smiles in ("CC=O", "CC(=O)O")]
    single = [mcp_server._run_worker("rdkit_workbench", [], kwargs) for kwargs in calls]
    launches.clear()
    batch = mcp_server._run_worker_each("rdkit_workbench", calls)
    assert len(launches) == 1
    assert [item["ok"] for item in batch] == [item["ok"] for item in single]
    assert [item["result"]["results"] for item in batch] == [item["result"]["results"] for item in single]
    assert [row["formula"] for item in batch for row in item["result"]["results"]] == ["C2H4O", "C2H4O2"]


def test_one_bad_item_does_not_stop_the_others():
    good = {"molecules": [{"smiles": "CCO"}]}
    batch = mcp_server._run_worker_each("rdkit_workbench", [good, {"molecules": 7}, good])
    assert [item["ok"] for item in batch] == [True, False, True]
    assert batch[1]["error"]["code"]
    assert batch[0]["result"]["results"] == batch[2]["result"]["results"]


def test_a_failed_worker_reports_the_failure_for_every_call(monkeypatch):
    monkeypatch.setattr(mcp_server, "_execute_worker_process", lambda *a, **k: (mcp_server._TIMEOUT_RETURN_CODE, b"", b""))
    batch = mcp_server._run_worker_each("rdkit_workbench", [{}, {}])
    assert [item["error"]["code"] for item in batch] == ["tool_timeout", "tool_timeout"]
    assert mcp_server._run_worker_each("rdkit_workbench", []) == []
