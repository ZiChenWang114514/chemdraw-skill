"""Tests for batch OCSR, richer consensus, precomputed ReagentDB canonical SMILES,
CAS short-circuit & caching, batched RXNMapper / GPU LocalMapper, single-call
tool_worker registry build, and runtime diagnostics status accuracy.
"""

from __future__ import annotations

import io
import json
import sys
import time
import types
import urllib.request
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Batch OCSR & Document Extraction + Richer Consensus
# ---------------------------------------------------------------------------


def test_recognize_batch_worker_and_per_image_engines(tmp_path, monkeypatch):
    from cdxml_toolkit.engines import env, envelope, ocsr

    img1 = tmp_path / "mol1.png"
    img2 = tmp_path / "mol2.png"
    img3 = tmp_path / "mol3.png"
    for p in (img1, img2, img3):
        p.write_bytes(b"fake-png")

    worker_calls = []
    molvec_calls = []

    def fake_call(name, action, params, timeout=0):
        worker_calls.append((name, action, list(params["images"]), params.get("hand_drawn")))
        return [{"smiles": "c1ccccc1"}, {"smiles": "CCO"}, {"smiles": "CC(=O)O"}]

    def fake_local(name, image, hand_drawn, timeout):
        assert name == "molvec"
        molvec_calls.append(image)
        smi = "c1ccccc1" if "mol1" in image else ("CCO" if "mol2" in image else "CC(=O)O")
        return [envelope.describe(smi)]

    monkeypatch.setattr(env, "call", fake_call)
    monkeypatch.setattr(
        env,
        "last_call_meta",
        lambda name: {"device": "cuda", "device_fallback": False},
    )
    monkeypatch.setattr(ocsr, "_local", fake_local)

    out = ocsr.recognize_batch(
        [str(img1), str(img2), str(img3)],
        engines="molscribe,molvec",
        hand_drawn=True,
        expected_formula="C2H6O",
    )

    assert len(out) == 3
    # Worker engine called exactly ONCE for all 3 images
    assert len(worker_calls) == 1
    assert worker_calls[0][0] == "molscribe"
    assert len(worker_calls[0][2]) == 3
    assert worker_calls[0][3] is True
    # MolVec called per image
    assert len(molvec_calls) == 3

    assert out[0]["comparison"]["agreed_smiles"] == "c1ccccc1"
    assert out[0]["comparison"]["groups"][0]["matches_expected_formula"] is False
    assert out[1]["comparison"]["agreed_smiles"] == "CCO"
    assert out[1]["comparison"]["groups"][0]["matches_expected_formula"] is True
    assert out[2]["comparison"]["agreed_smiles"] == "CC(=O)O"


def test_recognize_batch_worker_failure_isolated_across_batch(tmp_path, monkeypatch):
    from cdxml_toolkit.engines import env, ocsr

    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"1")
    img2.write_bytes(b"2")

    def fake_call(name, action, params, timeout=0):
        if name == "molscribe":
            raise env.EngineError("worker crashed")
        return [{"smiles": "CCO"}, {"smiles": "CCC"}]

    monkeypatch.setattr(env, "call", fake_call)
    monkeypatch.setattr(env, "last_call_meta", lambda name: {"device": "cpu", "device_fallback": False})

    reports = ocsr.recognize_batch([str(img1), str(img2)], engines="molscribe,molnextr")
    assert len(reports) == 2
    for idx, expected in enumerate(("CCO", "CCC")):
        assert reports[idx]["ok"] is True
        by_engine = {r["engine"]: r for r in reports[idx]["engines"]}
        assert by_engine["molscribe"]["ok"] is False
        assert "worker crashed" in by_engine["molscribe"]["error"]
        assert by_engine["molnextr"]["ok"] is True
        # Since molscribe failed and only molnextr returned a structure, needs_review is True and top group is expected
        assert reports[idx]["comparison"]["groups"][0]["canonical"] == expected


def test_consensus_stereo_protonation_tautomer_and_formula_notes():
    from cdxml_toolkit.engines import consensus

    # 1. Omitted vs specified E/Z double-bond stereochemistry
    ez_omitted = consensus.compare(
        [
            {"engine": "molscribe", "ok": True, "smiles": "CC=CC"},
            {"engine": "molnextr", "ok": True, "smiles": "C/C=C/C"},
        ]
    )
    assert ez_omitted["connectivity_match"] is True
    assert any("omitted stereochemistry" in n for n in ez_omitted["notes"])

    # 2. Inverted E/Z stereochemistry
    ez_inverted = consensus.compare(
        [
            {"engine": "molscribe", "ok": True, "smiles": "C/C=C/C"},
            {"engine": "molnextr", "ok": True, "smiles": r"C/C=C\C"},
        ]
    )
    assert ez_inverted["connectivity_match"] is True
    assert any("inverted stereochemistry" in n for n in ez_inverted["notes"])

    # 3. Protonation / charge difference (same skeleton & stereo, different block 3)
    protonated = consensus.compare(
        [
            {"engine": "molscribe", "ok": True, "smiles": "CC(=O)O"},
            {"engine": "molnextr", "ok": True, "smiles": "CC(=O)[O-]"},
        ]
    )
    assert protonated["connectivity_match"] is True
    assert any("protonation or charge" in n for n in protonated["notes"])

    # 4. Canonical tautomers with different connectivity block (acetylacetone diketo vs enol)
    taut = consensus.compare(
        [
            {"engine": "molscribe", "ok": True, "smiles": "CC(=O)CC(=O)C"},
            {"engine": "molnextr", "ok": True, "smiles": "CC(=O)/C=C(/O)C"},
        ],
        expected_formula="C5H8O2",
    )
    assert taut["connectivity_match"] is False
    assert any("canonical tautomer" in n for n in taut["notes"])
    assert all(g["matches_expected_formula"] is True for g in taut["groups"])
    assert any("expected formula" in n for n in taut["notes"])


# ---------------------------------------------------------------------------
# 2. Precomputed canonical_smiles in ReagentDB + CAS Short-circuit & Cache
# ---------------------------------------------------------------------------


def test_reagent_db_uses_precomputed_canonical_smiles_without_rdkit_at_startup(monkeypatch):
    from rdkit import Chem
    from cdxml_toolkit.resolve.reagent_db import ReagentDB

    monkeypatch.setattr(
        Chem,
        "MolFromSmiles",
        lambda *a, **k: pytest.fail("ReagentDB() should not call Chem.MolFromSmiles when canonical_smiles is precomputed"),
    )

    t0 = time.perf_counter()
    db = ReagentDB()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 250.0  # typically ~15-35 ms
    assert db.resolve_display("pd(dppf)cl2") == "Pd(dppf)Cl2"
    # Direct canonical SMILES lookup uses precomputed canonical_smiles without calling MolFromSmiles
    assert db.display_for_smiles("C1CCOC1") == "THF"


def test_reagent_db_falls_back_to_rdkit_when_canonical_smiles_missing(tmp_path):
    from cdxml_toolkit.resolve.reagent_db import ReagentDB

    custom_json = tmp_path / "custom_reagents.json"
    empty_cs = tmp_path / "empty_cs.json"
    custom_json.write_text(
        json.dumps(
            {
                "custom_etoh": {
                    "display": "EtOH-custom",
                    "smiles": "OCC",
                    "role": "solvent",
                }
            }
        ),
        encoding="utf-8",
    )
    empty_cs.write_text("{}", encoding="utf-8")
    db = ReagentDB(json_path=str(custom_json), secondary_path=str(empty_cs))
    assert db.display_for_smiles("CCO") == "EtOH-custom"


def test_mol_builder_short_circuits_valid_cas_before_local_parsers(monkeypatch):
    from cdxml_toolkit.naming import mol_builder
    from cdxml_toolkit.resolve import cas_resolver, condensed_formula

    monkeypatch.setattr(
        cas_resolver,
        "resolve_cas",
        lambda cas: {"cas": cas, "smiles": "CC(=O)Oc1ccccc1C(=O)O", "name": "aspirin"} if cas == "50-78-2" else None,
    )
    monkeypatch.setattr(
        condensed_formula,
        "resolve_condensed_formula",
        lambda q: pytest.fail("Valid CAS should short-circuit before condensed_formula"),
    )

    res = mol_builder._resolve_query("50-78-2", use_network=True)
    assert res is not None
    assert res["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert res["source"] == "pubchem"

    # When use_network=False or CHEMDRAW_OFFLINE=1, valid CAS that is not in Tier 1 does not call local parsers or network
    res_off = mol_builder._resolve_query("50-78-2", use_network=False)
    assert res_off is None


def test_cas_resolver_memory_and_disk_cache(tmp_path, monkeypatch):
    from cdxml_toolkit.resolve import cas_resolver

    cache_file = tmp_path / "pubchem_cas_cache.json"
    monkeypatch.setattr(cas_resolver, "_CACHE", {})
    monkeypatch.setattr(cas_resolver, "_DISK_CACHE_LOADED", False)
    monkeypatch.setattr(cas_resolver, "_CACHE_FILE", cache_file)

    network_calls = []
    rate_limit_calls = []

    def fake_urlopen(req, timeout=10):
        network_calls.append(req.full_url if hasattr(req, "full_url") else str(req))
        payload = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 750,
                        "CanonicalSMILES": "C(C(=O)O)N",
                        "IUPACName": "glycine",
                        "MolecularWeight": 75.07,
                        "MolecularFormula": "C2H5NO2",
                    }
                ]
            }
        }
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(cas_resolver, "_rate_limit", lambda: rate_limit_calls.append(1))

    # First call hits network and persists to disk cache
    res1 = cas_resolver.resolve_cas("56-40-6")
    assert res1 is not None and res1["smiles"] == "C(C(=O)O)N"
    assert len(network_calls) == 1
    assert len(rate_limit_calls) == 1
    assert cache_file.exists()

    # Second call uses in-memory cache without hitting network
    res2 = cas_resolver.resolve_cas("56-40-6")
    assert res2 is not None and res2["smiles"] == "C(C(=O)O)N"
    assert len(network_calls) == 1

    # Simulate fresh process by clearing in-memory cache and reloading from disk cache
    cas_resolver._CACHE.clear()
    monkeypatch.setattr(cas_resolver, "_DISK_CACHE_LOADED", False)
    res3 = cas_resolver.resolve_cas("56-40-6")
    assert res3 is not None and res3["smiles"] == "C(C(=O)O)N"
    assert len(network_calls) == 1


# ---------------------------------------------------------------------------
# 3. Batched RXNMapper & GPU LocalMapper, Tool Worker, Runtime Diagnostics
# ---------------------------------------------------------------------------


def test_rxnmapper_batches_in_chunks_and_falls_back_per_reaction_on_failure(monkeypatch):
    import cdxml_toolkit.atom_mapping_worker as worker

    batch_calls = []

    class FakeRXNMapper:
        def get_attention_guided_atom_maps(self, rxns):
            batch_calls.append(list(rxns))
            if any("BAD" in r for r in rxns):
                if len(rxns) > 1:
                    raise RuntimeError("Batch failed on bad reaction")
                raise ValueError("Invalid SMILES: BAD")
            return [{"mapped_rxn": f"mapped:{r}", "confidence": 0.91} for r in rxns]

    fake_mod = types.SimpleNamespace(RXNMapper=FakeRXNMapper)
    monkeypatch.setitem(sys.modules, "rxnmapper", fake_mod)

    # 20 clean reactions -> 2 batch calls (16 + 4) instead of 20 single calls
    rxns_20 = [f"C>>C.{i}" for i in range(20)]
    res_20 = worker._rxnmapper(rxns_20)
    assert len(res_20) == 20
    assert [len(c) for c in batch_calls] == [16, 4]
    assert res_20[0]["mapped_rxn"] == "mapped:C>>C.0"

    # Chunk with 1 bad reaction falls back per-reaction so good reactions still succeed
    batch_calls.clear()
    mixed = ["CC>>CC", "BAD>>RXN", "CO>>CO"]
    res_mixed = worker._rxnmapper(mixed)
    assert res_mixed[0]["mapped_rxn"] == "mapped:CC>>CC"
    assert "mapped_rxn" not in res_mixed[1]
    assert "Invalid SMILES: BAD" in res_mixed[1]["error"]
    assert res_mixed[2]["mapped_rxn"] == "mapped:CO>>CO"


def test_localmapper_uses_cuda_when_available_and_falls_back_to_cpu(monkeypatch):
    import cdxml_toolkit.atom_mapping_worker as worker

    init_devices = []

    class FakeLocalMapper:
        def __init__(self, device="cpu"):
            init_devices.append(device)
            self.device = device
            if device == "cuda" and getattr(FakeLocalMapper, "fail_init", False):
                raise RuntimeError("CUDA OOM on init")

        def get_atom_map(self, rxn, return_dict=True):
            if self.device == "cuda" and getattr(FakeLocalMapper, "fail_infer", False):
                raise RuntimeError("CUDA kernel error")
            return {"mapped_rxn": f"{self.device}:{rxn}", "confident": True, "template": "t1"}

    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True))
    fake_lm_mod = types.SimpleNamespace(localmapper=FakeLocalMapper)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "localmapper", fake_lm_mod)
    monkeypatch.delenv("CHEMDRAW_ENGINE_DEVICE", raising=False)

    # 1. Uses cuda when available
    FakeLocalMapper.fail_init = False
    FakeLocalMapper.fail_infer = False
    out = worker._localmapper(["A>>B"])
    assert init_devices == ["cuda"]
    assert out[0]["mapped_rxn"] == "cuda:A>>B"

    # 2. Falls back to cpu on CUDA init failure
    init_devices.clear()
    FakeLocalMapper.fail_init = True
    out = worker._localmapper(["A>>B"])
    assert init_devices == ["cuda", "cpu"]
    assert out[0]["mapped_rxn"] == "cpu:A>>B"

    # 3. Falls back to cpu on CUDA inference failure
    init_devices.clear()
    FakeLocalMapper.fail_init = False
    FakeLocalMapper.fail_infer = True
    out = worker._localmapper(["A>>B"])
    assert init_devices == ["cuda", "cpu"]
    assert out[0]["mapped_rxn"] == "cpu:A>>B"

    # 4. Respects CHEMDRAW_ENGINE_DEVICE=cpu
    init_devices.clear()
    monkeypatch.setenv("CHEMDRAW_ENGINE_DEVICE", "cpu")
    out = worker._localmapper(["A>>B"])
    assert init_devices == ["cpu"]


def test_tool_worker_builds_registry_only_once(tmp_path, monkeypatch):
    from cdxml_toolkit.mcp_runtime import tool_registry, tool_worker

    build_calls = []

    class DummySpec:
        name = "dummy_tool"
        resource_class = None

        @staticmethod
        def function(x=1):
            return {"echo": x}

    def fake_build_registry(profile=None):
        build_calls.append(profile)
        return {"dummy_tool": DummySpec()}

    req_file = tmp_path / "req.json"
    req_file.write_text(
        json.dumps({"tool": "dummy_tool", "kwargs": {"x": 42}, "profile": "core"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(tool_registry, "build_registry", fake_build_registry)
    monkeypatch.setattr(sys, "argv", ["tool_worker.py", "--request-file", str(req_file)])
    stdout_buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout_buf)

    rc = tool_worker.main()
    assert rc == 0
    assert len(build_calls) == 1
    payload = json.loads(stdout_buf.getvalue())
    assert payload["ok"] is True
    assert payload["result"] == {"echo": 42}


def test_runtime_diagnostics_chemscript_detail_and_platform_missing_statuses(monkeypatch):
    from cdxml_toolkit.chemdraw import mac_automation
    from cdxml_toolkit.mcp_runtime import runtime_diagnostics as diag

    # Accurate detail string when unverified
    cap_avail = {"status": "available"}
    monkeypatch.setattr(mac_automation, "is_macos", lambda: False)
    monkeypatch.setattr(diag.sys, "platform", "win32")
    monkeypatch.setattr(diag, "_module_available", lambda name: True)
    cs = diag._chemscript_capability(cap_avail)
    assert cs["status"] == "unverified"
    assert "run_chemscript_probe (--chemscript)" in cs["detail"]

    # Windows with missing ChemDraw and no ChemScript DLLs -> missing
    monkeypatch.setattr(diag, "_has_windows_chemscript_dlls", lambda: False)
    cs_win_missing = diag._chemscript_capability({"status": "missing"})
    assert cs_win_missing["status"] == "missing"

    # Linux -> both chemscript and office report missing
    monkeypatch.setattr(diag.sys, "platform", "linux")
    cs_linux = diag._chemscript_capability({"status": "missing"})
    office_linux = diag._office_capability()
    assert cs_linux["status"] == "missing"
    assert office_linux["status"] == "missing"
