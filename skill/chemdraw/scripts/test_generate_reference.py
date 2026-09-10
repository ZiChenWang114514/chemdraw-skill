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
    assert json.loads(schema.read_text(encoding="utf-8"))["tool_count"] == 38
