# Command-Line Workflows

## When To Load

Load only when no registered tool covers an operation, or when diagnosing the Python layer. Normal work goes through `cdx.py`.

## Preferred Entry Points

Use the `cdxml-*` console commands installed in the runtime environment (its `Scripts`/`bin` folder; `cdx.py doctor` prints the runtime) rather than guessing module paths; never copies that a PATH lookup finds elsewhere. In the toolkit version pinned in `runtime.json` the installed entry points cover the complete and core MCP services, generated MCP references, build, conversion, discovery, doctor, entry formatting, image rendering, layout, LCMS/NMR, merge, multi-LCMS, OLE, reaction parsing, polish, procedure writing, and scheme rendering. Template filling, SciFinder RDF parsing, and scheme segmentation are Python or tool workflows; they are not installed console scripts.

Prefer the equivalent tool through `cdx.py call` during normal work because it adds isolated execution, timeout handling, overwrite refusal, and a stable JSON contract.

## Inputs And Outputs

Pass absolute paths on Windows. Request JSON or structured errors when supported. Direct every modifying command to a new output path and validate the resulting file.

## Failure Modes

Console scripts can resolve to the wrong Python environment, write status text to stdout, exit through `SystemExit`, or lack worker timeouts. Verify the executable path and capture stdout/stderr separately.

## Supporting APIs

CLI implementations use the high-level Python functions described in the domain references. Use each command's `--help` as the authority for command-only flags.

## Do Not Use Directly

Do not assemble commands from the exhaustive symbol inventory. Do not invoke private ChemScript server commands or rely on machine-specific Scripts paths in Skill instructions.
