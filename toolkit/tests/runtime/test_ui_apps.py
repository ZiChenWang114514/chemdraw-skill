"""Tests for Mol* 3D viewer and publication-grade 2D ChemDraw Studio MCP App views."""

from __future__ import annotations

import asyncio
from html.parser import HTMLParser
import json
import urllib.request

from cdxml_toolkit.cdxml_builder import mol_to_cdxml
from cdxml_toolkit.mcp_runtime import mcp_compat, mcp_server, tool_registry, ui_apps


class _StrictFragmentCheck(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forbidden: list[str] = []

    def handle_decl(self, decl: str) -> None:
        if decl.lower().startswith("doctype"):
            self.forbidden.append("doctype")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"html", "head", "body"}:
            self.forbidden.append(tag.lower())


def test_view_molecule_3d_from_name_and_cdxml(tmp_path):
    res = ui_apps.view_molecule_3d(
        "caffeine",
        output_path=str(tmp_path / "caffeine.html"),
        launch_browser=False,
    )
    assert res["ok"] is True
    assert res["ui_resource_uri"] == ui_apps.MOLSTAR_RESOURCE_URI
    assert res["formula"] == "C8H10N4O2"
    assert res["atom_count"] >= 24
    assert res["bond_count"] >= 25
    html_file = tmp_path / "caffeine.html"
    assert html_file.is_file()
    html = html_file.read_text(encoding="utf-8")
    assert "molstar.Viewer" in html
    assert "C8H10N4O2" in html

    cdxml_file = tmp_path / "aspirin.cdxml"
    cdxml_file.write_text(mol_to_cdxml("CC(=O)Oc1ccccc1C(=O)O"), encoding="utf-8")
    res_cdx = ui_apps.view_molecule_3d(
        structure_path=str(cdxml_file),
        output_path=str(tmp_path / "aspirin-3d.html"),
        launch_browser=False,
    )
    assert res_cdx["ok"] is True
    assert res_cdx["source_kind"] == "cdxml-3d"
    assert res_cdx["formula"] == "C9H8O4"


def test_view_molecule_3d_pdb_id_and_pdb_file(tmp_path):
    res_id = ui_apps.view_molecule_3d(
        pdb_id="1crn",
        output_path=str(tmp_path / "1crn.html"),
        launch_browser=False,
    )
    assert res_id["ok"] is True
    assert res_id["pdb_id"] == "1CRN"
    assert res_id["format"] == "mmcif"

    pdb_file = tmp_path / "mini.pdb"
    pdb_file.write_text(
        "ATOM      1  N   ALA A   1      11.104  13.207   8.551  1.00 20.00           N\n"
        "ATOM      2  CA  ALA A   1      12.560  13.100   8.600  1.00 20.00           C\n"
        "CONECT    1    2\nEND\n",
        encoding="utf-8",
    )
    res_file = ui_apps.view_molecule_3d(
        structure_path=str(pdb_file),
        output_path=str(tmp_path / "mini.html"),
        launch_browser=False,
    )
    assert res_file["ok"] is True
    assert res_file["atom_count"] == 2
    assert res_file["bond_count"] == 1


def test_open_drawing_studio_fragment_and_cdxml(tmp_path):
    res = ui_apps.open_drawing_studio(
        "suzuki_coupling",
        style="jacs",
        output_path=str(tmp_path / "suzuki.html"),
        fragment_path=str(tmp_path / "suzuki-fragment.html"),
        launch_browser=False,
    )
    assert res["ok"] is True
    assert res["template"] == "suzuki_coupling"
    assert res["style"] == "jacs"
    assert res["ui_resource_uri"] == ui_apps.DRAWING_STUDIO_RESOURCE_URI
    assert res["atom_count"] > 10
    assert (tmp_path / "suzuki.html").is_file()
    assert (tmp_path / "suzuki-fragment.html").is_file()

    frag = (tmp_path / "suzuki-fragment.html").read_text(encoding="utf-8")
    checker = _StrictFragmentCheck()
    checker.feed(frag)
    checker.close()
    assert checker.forbidden == []
    import re
    assert not re.search(r"<!doctype\s|<\s*(?:html|head|body)(?:\s|>)", frag, re.IGNORECASE)
    assert len(frag.encode("utf-8")) < 200_000
    assert 'id="cdx-studio-root"' in frag
    assert "fuseRingOnBond" in frag
    assert "graphToSmiles" in frag
    assert "toMolfileV2000" in frag
    assert "parseMolfileV2000" in frag
    assert "clean2D" in frag
    assert "PT_DATA" in frag

    res_blank = ui_apps.open_drawing_studio(
        output_path=str(tmp_path / "blank.html"),
        launch_browser=False,
    )
    assert res_blank["ok"] is True
    assert res_blank["template"] == "blank"
    assert res_blank["atom_count"] == 0

    res_pen = ui_apps.open_drawing_studio(
        "penicillin",
        output_path=str(tmp_path / "penicillin.html"),
        launch_browser=False,
    )
    assert any(b.get("o") in {4, 5} for b in res_pen["graph"]["bonds"])

    cdxml_file = tmp_path / "phenol.cdxml"
    cdxml_file.write_text(mol_to_cdxml("Oc1ccccc1"), encoding="utf-8")
    res_cdx = ui_apps.open_drawing_studio(
        cdxml_path=str(cdxml_file),
        output_path=str(tmp_path / "phenol.html"),
        launch_browser=False,
    )
    assert res_cdx["ok"] is True
    assert res_cdx["atom_count"] == 7
    assert res_cdx["formula"] == "C6H6O"


def test_serve_drawing_studio_live_sync_roundtrip(tmp_path):
    import threading

    server, url, sync_cdxml = ui_apps.serve_drawing_studio(
        template="benzene",
        sync_dir=tmp_path,
        open_browser=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            page = resp.read().decode("utf-8")
        assert "__CDX_LIVE_SYNC_URL__" in page
        import re
        from urllib.error import HTTPError

        sync_path = re.search(r'__CDX_LIVE_SYNC_URL__ = "(/api/studio-sync[?]token=[^"]+)"', page).group(1)
        body = json.dumps({"smiles": "c1ccccc1", "style": "acs1996", "cdxml": "<CDXML/>", "graph": {}}).encode("utf-8")

        def post(path, **headers):
            req = urllib.request.Request(url.rstrip("/") + path, data=body, method="POST",
                                         headers={"Content-Type": "application/json", **headers})
            try:
                with urllib.request.urlopen(req, timeout=5) as answer:
                    return answer.status, json.loads(answer.read().decode("utf-8"))
            except HTTPError as refused:
                return refused.code, None

        # Another page in the browser can reach a loopback port: it must not be able to write files.
        assert post("/api/studio-sync")[0] == 403
        assert post("/api/studio-sync?token=guess")[0] == 403
        assert post(sync_path, Origin="https://example.org")[0] == 403
        assert post(sync_path, Host="attacker.example:80")[0] == 403
        assert not sync_cdxml.exists()

        status, out = post(sync_path, Origin=url.rstrip("/"))
        assert status == 200 and out["ok"] is True
        assert sync_cdxml.read_text(encoding="utf-8") == "<CDXML/>"
    finally:
        server.shutdown()
        server.server_close()


def test_mcp_server_registers_ui_apps_metadata_structured_content_and_resources():
    registry = tool_registry.build_registry("full")
    assert "view_molecule_3d" in registry
    assert "open_drawing_studio" in registry
    assert registry["view_molecule_3d"].meta["ui"] == {"resourceUri": ui_apps.MOLSTAR_RESOURCE_URI}
    assert registry["view_molecule_3d"].meta["openai/outputTemplate"] == ui_apps.MOLSTAR_RESOURCE_URI
    assert registry["open_drawing_studio"].meta["ui"] == {"resourceUri": ui_apps.DRAWING_STUDIO_RESOURCE_URI}
    assert registry["open_drawing_studio"].meta["openai/outputTemplate"] == ui_apps.DRAWING_STUDIO_RESOURCE_URI

    server = mcp_server.build_server(profile="full")
    assert ui_apps.MOLSTAR_RESOURCE_URI in server._chemdraw_registered_resources
    assert ui_apps.DRAWING_STUDIO_RESOURCE_URI in server._chemdraw_registered_resources

    async def inspect_mcp():
        tools = await server.list_tools()
        resources = await server.list_resources()
        call_res = await server.call_tool("open_drawing_studio", {"template": "benzene"})
        return tools, resources, call_res

    tools, resources, call_res = asyncio.run(inspect_mcp())
    by_name = {t.name: t for t in tools}
    if mcp_compat.sdk_major() >= 2:
        meta_studio = getattr(by_name["open_drawing_studio"], "meta", None) or by_name["open_drawing_studio"].model_dump(by_alias=True).get("_meta")
        assert meta_studio["ui"] == {"resourceUri": ui_apps.DRAWING_STUDIO_RESOURCE_URI}
        assert meta_studio["openai/outputTemplate"] == ui_apps.DRAWING_STUDIO_RESOURCE_URI
        structured = getattr(call_res, "structured_content", None) or getattr(call_res, "structuredContent", None)
        assert isinstance(structured, dict) and structured["ok"] is True
        assert structured["formula"] == "C6H6"
    by_uri = {str(r.uri): r for r in resources}
    assert ui_apps.MOLSTAR_RESOURCE_URI in by_uri
    assert ui_apps.DRAWING_STUDIO_RESOURCE_URI in by_uri
    mime_3d = getattr(by_uri[ui_apps.MOLSTAR_RESOURCE_URI], "mime_type", None) or getattr(by_uri[ui_apps.MOLSTAR_RESOURCE_URI], "mimeType", None)
    assert mime_3d == "text/html;profile=mcp-app"


def test_the_3d_viewer_loads_one_pinned_build_with_integrity_checks():
    page = ui_apps.render_molstar_app_html()
    assert "molstar@latest" not in page
    assert page.count(f"molstar@{ui_apps.MOLSTAR_VERSION}/") == 2
    assert page.count('integrity="sha384-') == 2 and page.count('crossorigin="anonymous"') == 2
