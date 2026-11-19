"""The templates the server hands out are examples that work."""

import json

from cdxml_toolkit.mcp_runtime import mcp_server
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
from cdxml_toolkit.render.schema import VALID_LAYOUTS


def test_the_catalytic_cycle_template_draws(tmp_path):
    brief = json.loads(mcp_server._BUILTIN_TEMPLATES["catalytic-cycle"])
    report = draw_figure(brief, str(tmp_path / "cycle.cdxml"))
    assert report["ok"], report
    assert report["layout"] == "catalytic-cycle"


def test_scheme_layouts_named_to_agents_are_the_ones_the_parser_accepts():
    assert set(mcp_server.SCHEME_LAYOUTS) == set(VALID_LAYOUTS)
