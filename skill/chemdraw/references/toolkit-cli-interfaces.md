# Command-Line Workflows

## When To Load

Load only when MCP lacks an operation, when reproducing a workflow outside the MCP client, or when diagnosing the Python layer.

## Preferred Entry Points

Use installed `cdxml-*` console commands rather than guessing module paths. In cdxml-toolkit-community 0.7.0a1 the installed entry points cover the complete and core MCP services, generated MCP references, build, conversion, discovery, doctor, entry formatting, image rendering, layout, LCMS/NMR, merge, multi-LCMS, OLE, reaction parsing, polish, procedure writing, and scheme rendering. Template filling, SciFinder RDF parsing, and scheme segmentation are Python/MCP workflows; they are not installed console scripts.

Prefer the equivalent MCP extended tool during normal agent work because it adds isolated execution, timeout handling, overwrite refusal, and a stable JSON contract.

## Inputs And Outputs

Pass absolute paths on Windows. Request JSON or structured errors when supported. Direct every modifying command to a new output path and validate the resulting file.

## Failure Modes

Console scripts can resolve to the wrong Python environment, write status text to stdout, exit through `SystemExit`, or lack worker timeouts. Verify the executable path and capture stdout/stderr separately.

## Supporting APIs

CLI implementations use the high-level Python functions described in the domain references. Use each command's `--help` as the authority for command-only flags.

## Do Not Use Directly

Do not assemble commands from the exhaustive symbol inventory. Do not invoke private ChemScript server commands or rely on machine-specific Scripts paths in Skill instructions.
