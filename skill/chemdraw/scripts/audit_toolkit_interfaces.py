"""Generate a progressive public-interface inventory for cdxml-toolkit."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import importlib.metadata
import importlib.util
from pathlib import Path
from typing import Any


DOMAIN_REFERENCES = {
    "scientific": "scientific-workflows.md",
    "analysis": "toolkit-analysis-interfaces.md",
    "chemdraw": "toolkit-office-chemdraw-interfaces.md",
    "deterministic_pipeline": "toolkit-perception-image-interfaces.md",
    "image": "toolkit-perception-image-interfaces.md",
    "layout": "toolkit-render-layout-interfaces.md",
    "mcp_server": "toolkit-tools.md",
    "naming": "toolkit-chemistry-resolution-interfaces.md",
    "office": "toolkit-office-chemdraw-interfaces.md",
    "perception": "toolkit-perception-image-interfaces.md",
    "render": "toolkit-render-layout-interfaces.md",
    "resolve": "toolkit-chemistry-resolution-interfaces.md",
}

ROOT_MODULE_REFERENCES = {
    "cdxml_builder": "toolkit-render-layout-interfaces.md",
    "cdxml_utils": "toolkit-render-layout-interfaces.md",
    "coord_normalizer": "toolkit-render-layout-interfaces.md",
    "rdkit_utils": "toolkit-chemistry-resolution-interfaces.md",
    "text_formatting": "toolkit-render-layout-interfaces.md",
}


def _annotation(node: ast.expr | None) -> str:
    return ast.unparse(node) if node is not None else ""


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef, *, method: bool) -> str:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults)) + list(
        args.defaults
    )
    rendered = []
    for index, (arg, default) in enumerate(zip(positional, defaults)):
        if method and index == 0 and arg.arg in {"self", "cls"}:
            continue
        value = arg.arg
        if arg.annotation is not None:
            value += f": {_annotation(arg.annotation)}"
        if default is not None:
            value += f" = {ast.unparse(default)}"
        rendered.append(value)
        if args.posonlyargs and index + 1 == len(args.posonlyargs):
            rendered.append("/")
    if args.vararg is not None:
        value = f"*{args.vararg.arg}"
        if args.vararg.annotation is not None:
            value += f": {_annotation(args.vararg.annotation)}"
        rendered.append(value)
    elif args.kwonlyargs:
        rendered.append("*")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        value = arg.arg
        if arg.annotation is not None:
            value += f": {_annotation(arg.annotation)}"
        if default is not None:
            value += f" = {ast.unparse(default)}"
        rendered.append(value)
    if args.kwarg is not None:
        value = f"**{args.kwarg.arg}"
        if args.kwarg.annotation is not None:
            value += f": {_annotation(args.kwarg.annotation)}"
        rendered.append(value)
    result = f"{node.name}({', '.join(rendered)})"
    if node.returns is not None:
        result += f" -> {_annotation(node.returns)}"
    return result


def _summary(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or "No public docstring in the audited version."
    paragraph = doc.strip().split("\n\n", 1)[0]
    return " ".join(line.strip() for line in paragraph.splitlines())


def _module_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or root.name


def scan_package(package_root: Path) -> list[dict[str, Any]]:
    """Return every top-level public function/class and public class method."""
    package_root = Path(package_root).resolve()
    symbols: list[dict[str, Any]] = []
    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"Could not audit Python module {path}: {exc}") from exc
        module = _module_name(package_root, path)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") or node.name == "main":
                    continue
                symbols.append(
                    {
                        "module": module,
                        "qualified_name": node.name,
                        "kind": "async function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                        "signature": _function_signature(node, method=False),
                        "summary": _summary(node),
                        "line": node.lineno,
                    }
                )
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                symbols.append(
                    {
                        "module": module,
                        "qualified_name": node.name,
                        "kind": "class",
                        "signature": node.name,
                        "summary": _summary(node),
                        "line": node.lineno,
                    }
                )
                for child in node.body:
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if child.name.startswith("_") or child.name == "main":
                        continue
                    is_property = any(
                        isinstance(decorator, ast.Name) and decorator.id == "property"
                        for decorator in child.decorator_list
                    )
                    symbols.append(
                        {
                            "module": module,
                            "qualified_name": f"{node.name}.{child.name}",
                            "kind": "property" if is_property else "method",
                            "signature": (
                                f"{node.name}.{child.name}"
                                if is_property
                                else f"{node.name}.{_function_signature(child, method=True)}"
                            ),
                            "summary": _summary(child),
                            "line": child.lineno,
                        }
                    )
    return sorted(symbols, key=lambda item: (item["module"], item["qualified_name"].lower()))


def _reference_for_module(module: str) -> str:
    first = module.split(".", 1)[0]
    if first in DOMAIN_REFERENCES:
        return DOMAIN_REFERENCES[first]
    return ROOT_MODULE_REFERENCES.get(first, "toolkit-reviewed-exclusions.md")


def render_inventory(version: str, symbols: list[dict[str, Any]]) -> str:
    """Render a generated Markdown inventory grouped by module."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in symbols:
        grouped[symbol["module"]].append(symbol)
    function_count = sum(item["kind"] in {"function", "async function"} for item in symbols)
    class_count = sum(item["kind"] == "class" for item in symbols)
    method_count = sum(item["kind"] == "method" for item in symbols)
    lines = [
        f"# cdxml-toolkit {version} Public Symbol Inventory",
        "",
        "> Generated by `scripts/audit_toolkit_interfaces.py`. Do not hand-edit.",
        "> This is a discovery index, not a recommendation to call every symbol directly.",
        "",
        "## Scope",
        "",
        f"- Top-level public functions: {function_count}",
        f"- Public classes: {class_count}",
        f"- Public class methods: {method_count}",
        f"- Total listed symbols: {len(symbols)}",
        "- Private underscore-prefixed symbols and CLI `main` functions are omitted.",
        "",
        "Start with [interface-catalog.md](interface-catalog.md). It classifies direct, supporting, internal, legacy, and unsafe surfaces. Load this generated file only for exhaustive symbol lookup.",
        "",
    ]
    for module in sorted(grouped):
        reference = _reference_for_module(module)
        lines.extend(
            [
                f"## `{module}`",
                "",
                f"Curated guidance: [{reference}]({reference})",
                "",
            ]
        )
        for symbol in grouped[module]:
            summary = symbol["summary"] or "No public docstring in the audited version."
            lines.append(
                f"- **{symbol['kind']}**, line {symbol['line']}: "
                f"`{symbol['signature']}` - {summary}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_inventory_shards(
    version: str, symbols: list[dict[str, Any]]
) -> tuple[str, dict[str, str]]:
    """Render a compact index plus domain shards for progressive lookup."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in symbols:
        grouped[_reference_for_module(symbol["module"])].append(symbol)
    shards: dict[str, str] = {}
    index_lines = [
        f"# cdxml-toolkit {version} Public Inventory Index",
        "",
        "> Generated by `scripts/audit_toolkit_interfaces.py`. Do not hand-edit.",
        "> Load one shard or search by symbol. Do not load every shard for routine work.",
        "",
        f"Total audited public symbols: **{len(symbols)}**.",
        "",
        "| Domain shard | Symbols | Curated guidance |",
        "| --- | ---: | --- |",
    ]
    for reference in sorted(grouped):
        slug = reference.removeprefix("toolkit-").removesuffix("-interfaces.md").removesuffix(".md")
        shard_name = f"{slug}.md"
        domain_symbols = grouped[reference]
        index_lines.append(
            f"| [inventory/{shard_name}](inventory/{shard_name}) | "
            f"{len(domain_symbols)} | [{reference}]({reference}) |"
        )
        by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for symbol in domain_symbols:
            by_module[symbol["module"]].append(symbol)
        lines = [
            f"# {slug.replace('-', ' ').title()} Public Symbols",
            "",
            f"> Generated from cdxml-toolkit {version}. Curated guidance: "
            f"[../{reference}](../{reference}).",
            "",
        ]
        for module in sorted(by_module):
            lines.extend([f"## `{module}`", ""])
            for symbol in by_module[module]:
                lines.append(
                    f"- **{symbol['kind']}**, line {symbol['line']}: "
                    f"`{symbol['signature']}` - {symbol['summary']}"
                )
            lines.append("")
        shards[shard_name] = "\n".join(lines).rstrip() + "\n"
    return "\n".join(index_lines).rstrip() + "\n", shards


def _default_package_root() -> Path:
    spec = importlib.util.find_spec("cdxml_toolkit")
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError("cdxml_toolkit is not installed")
    return Path(next(iter(spec.submodule_search_locations)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--version", default=None)
    args = parser.parse_args()
    package_root = args.package_root or _default_package_root()
    version = args.version or importlib.metadata.version("cdxml-toolkit-community")
    if not args.output and not args.output_dir:
        parser.error("one of --output or --output-dir is required")
    symbols = scan_package(package_root)
    if args.output_dir:
        output_dir = args.output_dir.resolve()
        shard_dir = output_dir / "inventory"
        shard_dir.mkdir(parents=True, exist_ok=True)
        index, shards = render_inventory_shards(version, symbols)
        index_path = output_dir / "toolkit-public-inventory.md"
        index_path.write_text(index, encoding="utf-8", newline="\n")
        expected = set(shards)
        for stale in shard_dir.glob("*.md"):
            if stale.name not in expected:
                stale.unlink()
        for name, content in shards.items():
            (shard_dir / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {index_path} and {len(shards)} domain shards")
    if args.output:
        inventory = render_inventory(version, symbols)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(inventory, encoding="utf-8", newline="\n")
        print(f"Wrote {args.output} ({len(inventory)} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
