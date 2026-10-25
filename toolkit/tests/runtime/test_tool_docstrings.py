"""Tool descriptions only send callers to tools and APIs that exist."""

from __future__ import annotations

import re

from cdxml_toolkit.mcp_runtime import tool_registry


def test_reaction_templates_are_named_through_an_existing_interface():
    registry = tool_registry.build_registry()
    doc = registry["modify_molecule"].description
    assert "list_reactions" not in registry
    # A bare "from list_reactions" reads like a tool the caller can invoke.
    assert not re.search(r"from list_reactions\b(?!\()", doc)
    assert "cdxml_toolkit.naming.mol_builder.list_reactions()" in doc
