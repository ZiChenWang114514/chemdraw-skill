"""Generate MCP signatures and a machine-readable schema from the live registry."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import typing

from .tool_registry import build_registry


def _signature(function) -> str:
    try:
        hints = typing.get_type_hints(function)
    except Exception:
        hints = getattr(function, "__annotations__", {})
    signature = inspect.signature(function)
    parameters = [
        parameter.replace(annotation=hints.get(parameter.name, parameter.annotation))
        for parameter in signature.parameters.values()
    ]
    return str(
        signature.replace(
            parameters=parameters,
            return_annotation=hints.get("return", signature.return_annotation),
        )
    )


def manifest(profile: str = "codex") -> dict:
    registry = build_registry(profile=profile)
    from cdxml_toolkit import __version__ as version
    return {
        "schema_version": 1,
        "distribution": "cdxml-toolkit-community",
        "version": version,
        "profile": profile,
        "tool_count": len(registry),
        "tools": [
            {
                "name": name,
                "signature": _signature(spec.function),
                "group": spec.group,
                "resource_class": spec.resource_class,
                "timeout_seconds": spec.timeout_seconds,
                "description": spec.description,
            }
            for name, spec in sorted(registry.items())
        ],
    }


def render_markdown(profile: str = "codex") -> str:
    data = manifest(profile)
    lines = [
        "# MCP Tool Reference",
        "",
        "> Generated from the live community registry. Do not edit manually.",
        "",
        f"Distribution: `{data['distribution']} {data['version']}`",
        f"Profile: `{profile}`",
        f"Tools: `{data['tool_count']}`",
        "",
    ]
    tools_by_group: dict[str, list[dict]] = {}
    for tool in data["tools"]:
        tools_by_group.setdefault(tool["group"], []).append(tool)
    for group, tools in sorted(tools_by_group.items()):
        lines.extend([f"## {group.title()} Tools", ""])
        for tool in tools:
            lines.extend(
                [
                    f"### `{tool['name']}{tool['signature']}`",
                    "",
                    "\n".join(
                        line.rstrip()
                        for line in tool["description"].strip().splitlines()
                    )
                    or "No public description.",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def render_reference(profile: str = "codex") -> str:
    """Compatibility alias used by ChemDraw Skill catalog checks."""
    return render_markdown(profile)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="codex")
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.output:
        if args.markdown or args.json_path:
            parser.error("--output cannot be combined with --markdown or --json")
        args.markdown = args.output
    elif not args.markdown or not args.json_path:
        parser.error("--markdown and --json are required")
    markdown = render_markdown(args.profile)
    data = manifest(args.profile)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown, encoding="utf-8", newline="\n")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
