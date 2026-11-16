"""Tests for Mol* 3D viewer and 2D ChemDraw Template Studio MCP App views."""

from __future__ import annotations

import asyncio
from pathlib import Path

from cdxml_toolkit.cdxml_builder import mol_to_cdxml
from cdxml_toolkit.mcp_runtime import mcp_compat, mcp_server, tool_registry, ui_apps


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


def test_open_drawing_studio_templates_and_cdxml(tmp_path):
    res = ui_apps.open_drawing_studio(
        "suzuki_coupling",
        style="jacs",
        output_path=str(tmp_path / "suzuki.html"),
        launch_browser=False,
    )
    assert res["ok"] is True
    assert res["template"] == "suzuki_coupling"
    assert res["style"] == "jacs"
    assert res["ui_resource_uri"] == ui_apps.DRAWING_STUDIO_RESOURCE_URI
    assert res["atom_count"] > 10
    assert (tmp_path / "suzuki.html").is_file()
    html = (tmp_path / "suzuki.html").read_text(encoding="utf-8")
    assert "Suzuki-Miyaura Coupling" in html
    assert "ui/initialize" in html

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


def test_mcp_server_registers_ui_apps_metadata_and_resources():
    registry = tool_registry.build_registry("full")
    assert "view_molecule_3d" in registry
    assert "open_drawing_studio" in registry
    assert registry["view_molecule_3d"].meta == {"ui": {"resourceUri": ui_apps.MOLSTAR_RESOURCE_URI}}
    assert registry["open_drawing_studio"].meta == {"ui": {"resourceUri": ui_apps.DRAWING_STUDIO_RESOURCE_URI}}

    server = mcp_server.build_server(profile="full")
    assert ui_apps.MOLSTAR_RESOURCE_URI in server._chemdraw_registered_resources
    assert ui_apps.DRAWING_STUDIO_RESOURCE_URI in server._chemdraw_registered_resources

    async def inspect_mcp():
        tools = await server.list_tools()
        resources = await server.list_resources()
        return tools, resources

    tools, resources = asyncio.run(inspect_mcp())
    by_name = {t.name: t for t in tools}
    if mcp_compat.sdk_major() >= 2:
        meta_3d = getattr(by_name["view_molecule_3d"], "meta", None) or by_name["view_molecule_3d"].model_dump(by_alias=True).get("_meta")
        meta_studio = getattr(by_name["open_drawing_studio"], "meta", None) or by_name["open_drawing_studio"].model_dump(by_alias=True).get("_meta")
        assert meta_3d == {"ui": {"resourceUri": ui_apps.MOLSTAR_RESOURCE_URI}}
        assert meta_studio == {"ui": {"resourceUri": ui_apps.DRAWING_STUDIO_RESOURCE_URI}}
    by_uri = {str(r.uri): r for r in resources}
    assert ui_apps.MOLSTAR_RESOURCE_URI in by_uri
    assert ui_apps.DRAWING_STUDIO_RESOURCE_URI in by_uri
    mime_3d = getattr(by_uri[ui_apps.MOLSTAR_RESOURCE_URI], "mime_type", None) or getattr(by_uri[ui_apps.MOLSTAR_RESOURCE_URI], "mimeType", None)
    assert mime_3d == "text/html;profile=mcp-app"
