from __future__ import annotations

import json

from cdxml_toolkit.mcp_runtime import generate_reference


def test_legacy_reference_interface_matches_generated_markdown(tmp_path):
    output = tmp_path / "mcp-signatures.md"

    assert generate_reference.render_reference() == generate_reference.render_markdown()
    assert generate_reference.main(["--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == generate_reference.render_markdown()


def test_current_reference_interface_writes_markdown_and_json(tmp_path):
    markdown = tmp_path / "tools.md"
    schema = tmp_path / "schema.json"

    assert (
        generate_reference.main(
            ["--markdown", str(markdown), "--json", str(schema)]
        )
        == 0
    )
    assert markdown.read_text(encoding="utf-8") == generate_reference.render_markdown()
    assert json.loads(schema.read_text(encoding="utf-8"))["tool_count"] == 51


def test_descriptions_are_dedented_on_every_python_version(monkeypatch):
    # Python 3.13+ strips docstring indentation at compile time; 3.12 keeps it.
    real = generate_reference.manifest

    def indented(profile="full"):
        data = real(profile)
        for tool in data["tools"]:
            tool["description"] = "Summary.\n\n    Args:\n        x: value."
        return data

    monkeypatch.setattr(generate_reference, "manifest", indented)
    assert "\nArgs:\n    x: value." in generate_reference.render_markdown()


def test_official_tool_descriptions_are_dedented():
    from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

    description = build_registry()["convert_cdx_cdxml"].description
    assert "\nDirection is detected" in description
    assert "\n    Direction" not in description


def test_reference_is_the_same_on_every_host(monkeypatch):
    from cdxml_toolkit.mcp_runtime import tool_registry

    references = []
    for platform in ("win32", "darwin", "linux"):
        monkeypatch.setattr(tool_registry.sys, "platform", platform)
        references.append(generate_reference.manifest())
    assert references[1] == references[0]
    assert references[2] == references[0]
