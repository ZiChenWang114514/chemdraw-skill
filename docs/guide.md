# ChemDraw Skill setup and operations

The Skill works with any agent that can read local instructions and run shell commands. Everything runs through one entry point, `skill/chemdraw/scripts/cdx.py`. See [agent integration](../skill/chemdraw/references/agent-integration.md) for per-agent Skill folders, runtime discovery, command allowlisting and the command reference.

## First-time setup

You need a 64-bit Python 3.10–3.13 to build the runtime (3.12 is the tested version); the installer itself runs on any Python 3.9+. Python 3.14 and newer are not supported by the bundled toolkit yet: if that is your only Python, install 3.12 first (for example `uv python install 3.12`) or pass `--python <interpreter>`. Portable CDXML/RDKit work needs no desktop application and runs on Windows, macOS and Linux. Native output requires activated Windows ChemDraw; Office and ChemScript are needed only for their workflows.

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
pwsh ./scripts/check_prerequisites.ps1 -Capabilities core,native     # optional read-only Windows host report
python scripts/install.py --agent claude agents --runtime            # preview
python scripts/install.py --agent claude agents --runtime --apply    # install Skill copies + shared runtime
```

`--agent` takes one or more of `claude`, `agents` (the shared `~/.agents/skills` folder read by most agents), `gemini`, `copilot`, `cursor` and `opencode`; `--project <repo>` installs project-scoped copies instead, and `--destination <folder>` installs anywhere. `--python <interpreter>` picks the base interpreter when auto-detection finds none, `--extras` chooses toolkit extras (default: every extra that applies to the OS), and `--runtime-dir` moves the shared venv.

The installer stages and verifies each copy, moves an existing installation to the shared backup folder (outside every Skill folder), restores it on failure, installs the runtime once for all copies, and writes `manifest.json` so later drift can be detected. Re-running it upgrades the Skill and reuses the venv. When the venv is not in a location `cdx.py` searches, the installer writes `runtime.local.json` into each copy and into the repository checkout (ignored by Git), so `cdx.py` also works from the checkout.

The runtime is built from this repository's [`toolkit/`](../toolkit) folder, so it always matches the Skill you install; CI builds it the same way. An installed Skill copy without a checkout falls back to the exact commit in [runtime.json](../skill/chemdraw/runtime.json). To build a runtime by hand instead:

```bash
python3 -m venv <venv>
<venv>/bin/python skill/chemdraw/scripts/install_runtime.py --extras publication scientific
export CHEMDRAW_MCP_PYTHON=<venv>/bin/python      # only if <venv> is not a location cdx.py searches
```

`install_runtime.py --print-requirement` prints the requirement without installing; `--toolkit-path <folder>` (also accepted by `install.py`) builds from another toolkit source folder. For toolkit development, `python -m pip install -e "./toolkit[dev]"` into the runtime gives an editable install.

## Check the installation

```bash
python <skill>/scripts/cdx.py doctor              # versions, extras, drift, capability matrix
python <skill>/scripts/cdx.py doctor --native     # + ChemScript ping and a native PNG render
python <skill>/scripts/cdx.py doctor --office     # + Word/PowerPoint OLE probes
```

Any Python can start `cdx.py`; it re-launches itself in the runtime and skips a candidate whose interpreter no longer starts. Skipped probes are not verified features. See [operations](../skill/chemdraw/references/operations.md) for bitness, timeouts, DECIMER and failure codes.

Allow the `python <skill>/scripts/cdx.py` prefix once in your agent's command allowlist to avoid permission prompts; [agent integration](../skill/chemdraw/references/agent-integration.md#command-permissions) has an example.

## MCP (optional)

The command line covers every tool, so no server is required. Clients that prefer MCP can register `<runtime-python> -m cdxml_toolkit.mcp_runtime` (no profile flag needed); `cdx.py doctor` prints the runtime path. For a remote Windows host, see the HTTP section of [operations](../skill/chemdraw/references/operations.md#remote-http-only-when-asked).

## Development validation

```powershell
python scripts/validate_distribution.py                           # repository checks and installer tests
python skill/chemdraw/scripts/cdx.py py -m pip install pytest
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py regen-signatures             # after a toolkit change
cd toolkit; python -m pytest -m "not network" -q                 # toolkit tests (runtime Python)
```

Validate final structure readback separately from visual comparison. Read only the relevant [workflow](../skill/chemdraw/references/workflow-router.md); exact interfaces live in the [generated signatures](../skill/chemdraw/references/mcp-signatures.md). Keep chemistry, source files and credentials out of logs and public repositories. Repository content uses [MIT](../LICENSE); dependencies and desktop software retain their own terms.
