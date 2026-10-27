"""Run-verified recipes: small programs for the generic tools, with the results they must give.

A recipe is evidence that a catalog symbol is reachable through a generic tool, so a row can
be tiered T2. ``check`` compares a run's results with the recipe's ``expect`` list;
``run`` executes the recipe on the installed ChemDraw (Windows) and returns the failures.
"""

from __future__ import annotations

import copy
import json
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any, Optional


def load() -> list[dict[str, Any]]:
    text = resources.files(__package__).joinpath("data", "recipes.json").read_text(encoding="utf-8")
    return json.loads(text)["recipes"]


def _matches(expectation: dict[str, Any], value: Any) -> bool:
    if "equals" in expectation:
        return value == expectation["equals"]
    if "approx" in expectation:
        return isinstance(value, (int, float)) and abs(value - expectation["approx"]) <= expectation.get("tolerance", 1e-6)
    if "contains" in expectation:
        return isinstance(value, str) and expectation["contains"] in value
    if "type" in expectation:
        return isinstance(value, dict) and str(value.get("$type", "")).endswith(expectation["type"])
    if "object" in expectation:
        return isinstance(value, dict) and value.get("object") == expectation["object"]
    if "at_least" in expectation:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= expectation["at_least"]
    if "kind" in expectation:
        kinds = {"bool": bool, "int": int, "str": str}
        return type(value) is kinds[expectation["kind"]]
    return False


def check(recipe: dict[str, Any], results: list[dict[str, Any]]) -> list[str]:
    """Return one message per expectation the results do not meet."""
    by_step = {item["step"]: item for item in results}
    failures = []
    for expectation in recipe["expect"]:
        step = expectation["step"]
        if step not in by_step:
            failures.append(f"step {step}: result missing")
        elif not _matches(expectation, by_step[step]["value"]):
            wanted = {k: v for k, v in expectation.items() if k != "step"}
            failures.append(f"step {step}: expected {wanted}, got {by_step[step]['value']!r}"[:300])
    return failures


def declaring_type(catalog: dict[str, Any], type_name: str, member: str) -> Optional[str]:
    """The type of the ChemScript catalog that declares ``member``, following base types."""
    types = {t["name"]: t for t in catalog["types"]}
    current: Optional[str] = type_name
    while current in types:
        entry = types[current]
        if any(m["name"] == member for m in entry.get("members", [])):
            return current
        current = entry.get("base")
    return None


def fill_program(program: list[dict[str, Any]], *, fixture: str, out: str) -> list[dict[str, Any]]:
    """Copy a COM recipe program with ``{fixture}`` and ``{out}`` replaced in every string."""

    def fill(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("{fixture}", fixture).replace("{out}", out)
        if isinstance(value, list):
            return [fill(item) for item in value]
        if isinstance(value, dict):
            return {key: fill(item) for key, item in value.items()}
        return value

    return fill(copy.deepcopy(program))


def _run_com(recipe: dict[str, Any]) -> list[str]:
    from ..mcp_runtime import com_call

    with tempfile.TemporaryDirectory() as temp:
        fixture = Path(temp) / "fixture.cdxml"
        fixture.write_text(recipe["fixture"], encoding="utf-8")
        out = Path(temp) / "out"
        out.mkdir()
        program = fill_program(recipe["program"], fixture=str(fixture), out=str(out))
        try:
            response = com_call.chemdraw_com_call(program=program, allow_file_io=True)
        except Exception as error:
            return [f"execution failed: {str(error)[:200]}"]
        failures = check(recipe, response["outputs"]["results"])
        wanted = recipe.get("written")
        written = response["outputs"]["written"]
        if wanted is not None and len(written) != wanted:
            failures.append(f"expected {wanted} written files, got {len(written)}")
        return failures


def run(recipe: dict[str, Any]) -> list[str]:
    """Execute a recipe on the installed ChemDraw and return its failures."""
    if recipe["tool"] == "chemdraw_com_call":
        return _run_com(recipe)
    from ..mcp_runtime import chemscript_sdk

    try:
        response = chemscript_sdk.execute_chemscript_sdk(program=recipe["program"])
    except Exception as error:
        return [f"execution failed: {str(error)[:200]}"]
    return check(recipe, response["outputs"]["results"])
