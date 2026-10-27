# ChemDraw Skill setup and operations

The Skill works with any agent that can read local instructions and run shell commands. Everything runs through one entry point, `skill/chemdraw/scripts/cdx.py`. See [agent integration](../skill/chemdraw/references/agent-integration.md) for per-agent Skill folders, runtime discovery, command allowlisting and the command reference.

## First-time setup

You need a 64-bit Python 3.10–3.13 to build the runtime (3.12 is the tested version); the installer itself runs on any Python 3.9+. Python 3.14 and newer are not supported by the bundled toolkit yet: if that is your only Python, install 3.12 first (for example `uv python install 3.12`) or pass `--python <interpreter>`. Portable CDXML/RDKit work needs no desktop application and runs on Windows, macOS and Linux. Native output requires activated desktop ChemDraw (Windows, or ChemDraw for macOS); Office and ChemScript are needed only for their workflows.

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
pwsh ./scripts/check_prerequisites.ps1 -Capabilities core,native     # optional read-only Windows host report
python scripts/install.py --agent claude agents --runtime            # preview
python scripts/install.py --agent claude agents --runtime --apply    # install Skill copies + shared runtime
```

`--agent` takes one or more of `claude`, `agents` (the shared `~/.agents/skills` folder read by most agents), `gemini`, `copilot`, `cursor` and `opencode`; `--project <repo>` installs project-scoped copies instead, and `--destination <folder>` installs anywhere. `--python <interpreter>` picks the base interpreter when auto-detection finds none, `--extras` chooses toolkit extras (default: every extra that applies to the OS), and `--runtime-dir` moves the shared venv.

The installer stages and verifies each copy, moves an existing installation to the shared backup folder (outside every Skill folder), restores it on failure, installs the runtime once for all copies, and writes `manifest.json` so later drift can be detected. Re-running it upgrades the Skill and reuses the venv. When the venv is not in a location `cdx.py` searches, the installer writes `runtime.local.json` into each copy and into the repository checkout (ignored by Git), so `cdx.py` also works from the checkout.

### macOS

```bash
python3 scripts/install.py --agent claude agents --runtime --opsin --apply   # also fetch the OPSIN JAR (SHA-256 verified)
python3 scripts/install.py --runtime --mapping --apply                       # optional: RXNMapper and LocalMapper atom mapping (several hundred MB)
python3 skill/chemdraw/scripts/cdx.py doctor --native --office --chemscript
```

ChemDraw for macOS is found in `/Applications` without configuration (`CHEMDRAW_EXE` overrides it). The first native call asks macOS to let your terminal or agent app control ChemDraw; allow it once, or later under System Settings > Privacy & Security > Automation. ChemScript is replaced by ChemDraw, OPSIN and RDKit, and Office PDF previews need an activated Microsoft 365. The full list of macOS differences is in [operations](../skill/chemdraw/references/operations.md#macos).

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
python <skill>/scripts/cdx.py doctor --office     # + PPTX/DOCX ChemDraw-OLE probes
```

Any Python can start `cdx.py`; it re-launches itself in the runtime and skips a candidate whose interpreter no longer starts. Skipped probes are not verified features. See [operations](../skill/chemdraw/references/operations.md) for bitness, timeouts, DECIMER and failure codes.

Allow the `python <skill>/scripts/cdx.py` prefix once in your agent's command allowlist to avoid permission prompts; [agent integration](../skill/chemdraw/references/agent-integration.md#command-permissions) has an example. That prefix also covers `cdx.py py`, which runs arbitrary Python in the runtime, so allow individual subcommands instead if that is too broad.

For confidential or offline work set `CHEMDRAW_OFFLINE=1`: PubChem lookups, the Java runtime download and DECIMER image uploads are then refused ([operations](../skill/chemdraw/references/operations.md#environment-variables)).

## ChemDraw interface coverage

The Skill catalogues what ChemDraw 22.2 exposes on Windows and states, for every entry, how far it is supported. Four layers are covered: the ChemScript SDK, ChemDraw's COM automation objects, the CDXML document model and the menu commands. Each entry has a tier:

- **T1**: a dedicated tool does the operation (for example `chemdraw_object` for CDXML elements, `chemdraw_chemical_properties` for ChemDraw's own formula, masses and ClogP, `structure_to_name`, `convert_cdx_cdxml`).
- **T2**: reachable through a generic tool (`execute_chemscript_sdk` or `chemdraw_com_call`) with a recipe that was run against ChemDraw and checked.
- **T3**: documented only, with the reason (internal plumbing, a hidden or blocked member, or no recipe has been run yet). Do not treat a T3 entry as verified.

| Layer | Entries | T1 | T2 | T3 |
| --- | --- | --- | --- | --- |
| ChemScript SDK | 576 | 7 | 9 | 560 |
| COM automation objects | 1,666 | 8 | 17 | 1,641 |
| CDXML elements | 50 | 37 | 0 | 13 |
| Menu commands | 159 | 0 | 0 | 159 |

Ask the catalog with `chemdraw_inventory(layer, query, tier)`, or open the generated pages under `skill/chemdraw/references` (`interface-chemscript.md`, `interface-com.md`, `interface-cdxml-model.md`, `interface-menu.md`, `recipes-chemdraw.md`). The pages are rebuilt with `python <skill>/scripts/cdx.py regen-catalog`.

What this does not claim: the numbers were checked on ChemDraw 22.2.0 for Windows only. macOS answers the ChemScript operations and a subset of the SDK, other ChemDraw versions may differ, binary CDX files are converted through ChemDraw rather than edited directly, and menu commands (for example NMR prediction) are not opened as tools because ChemDraw runs them only from a visible window. `chemdraw_com_call` refuses printing, the clipboard, menu objects and preference changes, and writes a file only when file access is allowed explicitly.

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
