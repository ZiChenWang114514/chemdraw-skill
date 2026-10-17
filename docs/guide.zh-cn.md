# ChemDraw Skill setup and operations

The Skill works with any agent that can read local instructions and run shell commands; Claude Code discovers it automatically. Everything runs through one entry point, `skill/chemdraw/scripts/cdx.py`. See [agent integration](../skill/chemdraw/references/agent-integration.md) for the layout and command reference.

## First-Time Windows Setup

You need a 64-bit Python 3.10–3.13 to build the runtime (3.12 is the tested version). Portable CDXML/RDKit work needs no desktop application. Native output requires activated Windows ChemDraw; Office and ChemScript are needed only for their workflows.

```powershell
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
Set-Location .\chemdraw-skill
.\scripts\check_prerequisites.ps1 -Capabilities core,native     # read-only host report
.\scripts\install.ps1 -Runtime                                   # preview
.\scripts\install.ps1 -Runtime -Apply                            # install Skill + runtime
```

By default the Skill goes to `~/.claude/skills/chemdraw` and the runtime venv to `~/.claude/skills/chemdraw-venv`. Use `-Destination <folder>` for another agent's Skill directory, `-Python <python.exe>` when auto-detection does not find a suitable interpreter, and `-Extras` to choose toolkit extras (default: `publication scientific office analysis image chemscript`).

The installer stages and verifies the copy, moves an existing installation to `backups/skills/chemdraw` (outside the discovery folder), restores it on failure, installs the runtime, and writes `manifest.json` so later drift can be detected. Re-running it upgrades the Skill and reuses the venv.

The runtime revision is the exact commit in [runtime.json](../skill/chemdraw/runtime.json); CI installs the same commit. To install a runtime by hand, or on macOS/Linux:

```bash
python3 -m venv ~/.claude/skills/chemdraw-venv
~/.claude/skills/chemdraw-venv/bin/python skill/chemdraw/scripts/install_runtime.py --extras publication scientific
cp -r skill/chemdraw ~/.claude/skills/chemdraw
```

`install_runtime.py --print-requirement` prints the requirement without installing; `--toolkit-path <checkout>` installs a local toolkit checkout for development.

## Check the installation

```powershell
python $HOME\.claude\skills\chemdraw\scripts\cdx.py doctor              # versions, extras, drift, capability matrix
python $HOME\.claude\skills\chemdraw\scripts\cdx.py doctor --native     # + ChemScript ping and a native PNG render
python $HOME\.claude\skills\chemdraw\scripts\cdx.py doctor --office     # + Word/PowerPoint OLE probes
```

Any Python can start `cdx.py`; it re-launches itself in the runtime. Skipped probes are not verified features. See [operations](../skill/chemdraw/references/operations.md) for bitness, timeouts, DECIMER and failure codes.

In Claude Code, allow the entry point once to avoid permission prompts:

```json
{"permissions": {"allow": ["Bash(python ~/.claude/skills/chemdraw/scripts/cdx.py:*)"]}}
```

## MCP (optional)

The command line covers every tool, so no server is required. Clients that prefer MCP can register `<runtime-python> -m cdxml_toolkit.mcp_runtime` (no profile flag needed); `cdx.py doctor` prints the runtime path. For a remote Windows host, see the HTTP section of [operations](../skill/chemdraw/references/operations.md#remote-http-only-when-asked).

## Development validation

```powershell
python scripts/validate_distribution.py                           # repository checks and installer tests
python skill/chemdraw/scripts/cdx.py py -m pip install pytest
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py regen-signatures             # after a toolkit upgrade
```

Validate final structure readback separately from visual comparison. Read only the relevant [workflow](../skill/chemdraw/references/workflow-router.md); exact interfaces live in the [generated signatures](../skill/chemdraw/references/mcp-signatures.md). Keep chemistry, source files and credentials out of logs and public repositories. Repository content uses [MIT](../LICENSE); dependencies and desktop software retain their own terms.
