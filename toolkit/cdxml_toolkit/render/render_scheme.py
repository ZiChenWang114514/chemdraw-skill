#!/usr/bin/env python3
"""
render_scheme.py — CLI entry point for scheme → CDXML rendering.

Accepts both YAML and compact syntax input files.

Usage:
    python experiments/scheme_dsl/render_scheme.py examples/simple_linear.yaml -o output.cdxml
    python experiments/scheme_dsl/render_scheme.py examples/buchwald.yaml
    python experiments/scheme_dsl/render_scheme.py scheme.txt --format compact
"""

import argparse
import os
import sys

from .parser import SchemeParseError, parse_yaml
from .compact_parser import parse_compact_file, ParseError
from .scheme_yaml_writer import write_scheme_yaml
from .renderer import render, render_to_file

# File extensions that trigger compact syntax parsing
_COMPACT_EXTENSIONS = {".rxn", ".scheme", ".txt"}
_YAML_EXTENSIONS = {".yaml", ".yml"}


def _detect_format(input_path: str) -> str:
    """Detect input format from file extension or content.

    Returns "yaml" or "compact".
    """
    ext = os.path.splitext(input_path)[1].lower()
    if ext in _YAML_EXTENSIONS:
        return "yaml"
    if ext in _COMPACT_EXTENSIONS:
        return "compact"

    # Fallback: sniff content — if first non-comment line contains -->, it's compact
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "-->" in stripped or "..>" in stripped or "X>" in stripped or "x>" in stripped:
                    return "compact"
                break
    except OSError:
        pass

    return "yaml"


def main():
    parser = argparse.ArgumentParser(
        description="Render a reaction scheme (YAML, compact syntax, or JSON) to CDXML.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Input file (YAML or compact syntax)",
    )
    parser.add_argument(
        "--from-json",
        nargs="+",
        default=None,
        metavar="JSON",
        help="Render from one or more reaction_parser JSON files",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output CDXML file (default: input stem + .cdxml)",
    )
    parser.add_argument(
        "--format",
        choices=["yaml", "compact"],
        default=None,
        help="Input format (auto-detected from extension if omitted)",
    )
    parser.add_argument(
        "--layout",
        default="auto",
        help="Layout override for --from-json (default: auto)",
    )
    parser.add_argument(
        "--no-run-arrows",
        action="store_true",
        help="Suppress run arrows (SM mass → product yield)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress to stderr",
    )
    args = parser.parse_args()

    # --- Handle --from-json mode ---
    if args.from_json:
        json_paths = args.from_json
        for jp in json_paths:
            if not os.path.exists(jp):
                print(f"Error: JSON file not found: {jp}", file=sys.stderr)
                sys.exit(1)

        include_run = not args.no_run_arrows

        if len(json_paths) == 1:
            # Single JSON: existing behavior
            json_path = json_paths[0]
            output_path = args.output
            if output_path is None:
                stem = os.path.splitext(os.path.basename(json_path))[0]
                output_path = os.path.join(
                    os.path.dirname(json_path) or ".", f"{stem}-scheme.cdxml")

            yaml_path = os.path.splitext(output_path)[0] + ".yaml"
            if args.verbose:
                print(f"Writing scheme YAML: {json_path} -> {yaml_path}",
                      file=sys.stderr)

            try:
                write_scheme_yaml(
                    json_path, yaml_path,
                    layout=args.layout,
                    include_run_arrows=include_run,
                )
            except Exception as e:
                print(f"YAML writer error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Multiple JSONs: produce individual + merged
            output_path = args.output
            if output_path is None:
                output_path = os.path.join(
                    os.path.dirname(json_paths[0]) or ".",
                    "merged-scheme.cdxml")

            # Individual files
            for jp in json_paths:
                stem = os.path.splitext(os.path.basename(jp))[0]
                ind_yaml = os.path.join(
                    os.path.dirname(jp) or ".", f"{stem}-scheme.yaml")
                ind_cdxml = os.path.join(
                    os.path.dirname(jp) or ".", f"{stem}-scheme.cdxml")
                try:
                    write_scheme_yaml(jp, ind_yaml, layout=args.layout,
                                      include_run_arrows=include_run)
                    ind_scheme = parse_yaml(ind_yaml)
                    ind_dir = os.path.dirname(os.path.abspath(ind_yaml))
                    render_to_file(ind_scheme, ind_cdxml, yaml_dir=ind_dir)
                    if args.verbose:
                        print(f"Individual: {ind_cdxml}", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: individual render failed for {jp}: {e}",
                          file=sys.stderr)

            # Merged YAML
            yaml_path = os.path.splitext(output_path)[0] + ".yaml"
            if args.verbose:
                print(f"Writing merged YAML: {yaml_path}", file=sys.stderr)

            try:
                from .scheme_yaml_writer import write_merged_scheme_yaml
                write_merged_scheme_yaml(
                    json_paths, yaml_path,
                    layout=args.layout,
                    include_run_arrows=include_run,
                )
            except Exception as e:
                print(f"Merged YAML writer error: {e}", file=sys.stderr)
                sys.exit(1)

        # Render YAML → CDXML
        if args.verbose:
            print(f"Rendering: {yaml_path} -> {output_path}", file=sys.stderr)

        try:
            scheme = parse_yaml(yaml_path)
        except SchemeParseError as e:
            print(f"Parse error in generated YAML: {e}", file=sys.stderr)
            sys.exit(1)

        if args.verbose:
            n_steps = len(scheme.steps) + sum(
                len(s.steps) for s in scheme.sections)
            print(
                f"  {len(scheme.structures)} structures, "
                f"{n_steps} steps, "
                f"layout={scheme.layout}",
                file=sys.stderr,
            )

        try:
            yaml_dir = os.path.dirname(os.path.abspath(yaml_path))
            render_to_file(scheme, output_path, yaml_dir=yaml_dir)
        except Exception as e:
            print(f"Render error: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"Written: {output_path}")
        return

    # --- Standard YAML/compact mode ---
    if not args.input:
        print("Error: input file required (or use --from-json)", file=sys.stderr)
        sys.exit(1)

    # Resolve input path
    input_path = args.input
    if not os.path.isabs(input_path):
        # Try relative to CWD first, then relative to script dir
        if not os.path.exists(input_path):
            alt = os.path.join(os.path.dirname(__file__), input_path)
            if os.path.exists(alt):
                input_path = alt

    if not os.path.exists(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve output path
    output_path = args.output
    if output_path is None:
        stem = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(os.path.dirname(input_path), f"{stem}.cdxml")

    # Detect format
    fmt = args.format or _detect_format(input_path)

    # Parse
    if args.verbose:
        print(f"Parsing {input_path} (format: {fmt})...", file=sys.stderr)
    try:
        if fmt == "compact":
            scheme = parse_compact_file(input_path)
        else:
            scheme = parse_yaml(input_path)
    except (SchemeParseError, ParseError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        source_info = f", source={scheme.source}" if scheme.source else ""
        print(
            f"  {len(scheme.structures)} structures, "
            f"{len(scheme.steps)} steps, "
            f"layout={scheme.layout}{source_info}",
            file=sys.stderr,
        )

    # Render
    if args.verbose:
        print(f"Rendering to {output_path}...", file=sys.stderr)
    try:
        yaml_dir = os.path.dirname(os.path.abspath(input_path))
        render_to_file(scheme, output_path, yaml_dir=yaml_dir)
    except Exception as e:
        print(f"Render error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Written: {output_path}")


if __name__ == "__main__":
    main()
