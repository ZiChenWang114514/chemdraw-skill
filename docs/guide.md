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

`--agent` takes `auto` (detects which agent folders already exist on the machine), one or more of the primary targets `claude`, `agents` (the shared `~/.agents/skills` folder read by most agents), `gemini`, `copilot`, `cursor`, `opencode`, `kimi` and `pi`, or the CLI aliases `codex`, `antigravity` and `windsurf`; `--project <repo>` installs project-scoped copies instead, `--destination <folder>` installs anywhere, and `--runtime-only --apply` upgrades the shared runtime from this checkout without copying Skill folders. `--python <interpreter>` picks the base interpreter when auto-detection finds none, `--extras` chooses toolkit extras (default: every extra that applies to the OS), and `--runtime-dir` moves the shared venv.

The installer stages and verifies each copy, moves an existing installation to the shared backup folder (outside every Skill folder), restores it on failure, installs the runtime once for all copies, and writes `manifest.json` so later drift can be detected. Re-running it upgrades the Skill and reuses the venv. When `cdx.py` would not pick this venv by itself (it sits in a custom location, or an older `chemdraw-venv` beside the Skill folder comes first), the installer writes `runtime.local.json` into each copy and into the repository checkout (ignored by Git), so `cdx.py` also uses it from the checkout; a leftover `runtime.local.json` that is no longer needed is removed.

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
python <skill>/scripts/cdx.py doctor --text       # readable checklist + recent run log summary
python <skill>/scripts/cdx.py doctor --native     # + ChemScript ping and a native PNG render
python <skill>/scripts/cdx.py doctor --office     # + PPTX/DOCX ChemDraw-OLE probes
python <skill>/scripts/cdx.py doctor --log latest # inspect details of the latest cdx.py run
```

Any Python can start `cdx.py`; it re-launches itself in the runtime and skips a candidate whose interpreter no longer starts. Skipped probes are not verified features. See [operations](../skill/chemdraw/references/operations.md) for bitness, timeouts, DECIMER and failure codes.

Allow the `python <skill>/scripts/cdx.py` prefix once in your agent's command allowlist to avoid permission prompts; [agent integration](../skill/chemdraw/references/agent-integration.md#command-permissions) has an example. That prefix also covers `cdx.py py`, which runs arbitrary Python in the runtime, so allow individual subcommands instead if that is too broad.

For confidential or offline work set `CHEMDRAW_OFFLINE=1`: PubChem lookups, the Java runtime download and DECIMER image uploads are then refused ([operations](../skill/chemdraw/references/operations.md#environment-variables)).

## Optional prediction engines

`cdx.py engines` lists the engines that can read structure images with more than one model, find the structures in a PDF, and predict products, precursors, routes, reaction conditions and 1H/13C shifts. `cdx.py engines --recommend ocsr` says what is worth installing for a need and what it costs, without downloading anything. `cdx.py install-engines --bundle ocsr-standard` (or engine names, or `--task ocsr`; `--dry-run` first for sizes) installs each one in its own environment, only after you agree, and `cdx.py remove-engines NAME --yes` deletes one again; model files are downloaded once, checked against a pinned hash, and every later run is offline. An engine takes from 2 MB up to about 8.5 GB (RetroChimera, which also needs about 14 GB of free memory to run); the sizes of the Windows installs include the CUDA build of PyTorch, and a CPU install is smaller. `decimer-local` runs the DECIMER model on this computer and installs into the toolkit runtime itself. The engines use an NVIDIA GPU when one is present, and `CHEMDRAW_ENGINE_DEVICE=cpu` turns that off. A one-off call is a clean process; a batch of inputs or a multi-step search (or `--accel on`, `CHEMDRAW_ACCEL`) keeps the model in a loopback-only resident worker for the next call, and `cdx.py stop-daemons` ends it. Every reply records `execution.device`. In the scientific and analytical workflows (which need no engine), 1D NMR loads native Bruker `1r`/`fid`, JCAMP-DX `.jdx`/`.dx`, JEOL `.jdf` and Varian/Agilent `.fid` via `nmrglue` alongside CSV/FT, and LCMS workflows parse Waters PDF, OpenLynx `.rpt`, Waters `.raw`, Shimadzu `.daml`, Agilent `report.txt` and open `mzML`/`mzXML` with Cl/Br `M+2` isotope checks and internal-standard (`IS`) normalization. `CHEMDRAW_ENGINE_HOME` moves the engines to another disk and must stay set afterwards. Results are labelled model predictions. Engines that disagree about an image are shown side by side and never merged. MolParser's weights may not be used commercially, RetroChimera is released for research use, and Reacon's authors state no licence, so it is downloaded from their repository only when you ask for it. Details, limits and the engines that were considered and left out: [engines](../skill/chemdraw/references/engines.md).

## Drawing styles

Every figure takes a `style` name, in a draw, scope or mechanism brief, a compose manifest or a `cdx.py build` spec, or as `cdx.py draw --style NAME` (including direct single-molecule, reaction-SMILES, or grid flags such as `cdx.py draw --name aspirin out.cdxml --style acs_jacs --render`, `cdx.py draw --reaction ... --compact`, or `--number --properties mw,formula`). `cdx.py styles` lists the sixteen measurement presets read from ChemDraw's stock style sheets (bond length, line widths, fonts; `acs1996` by default) and the 28 house styles (journals, publishers, patents, textbooks and research groups) that add, on top of a preset, how each draws 23 kinds of figure, measured from 179 crops of openly licensed figures; a brief can also set a title, panel letter, captions, boxes and colours for one figure; `cdx.py styles NAME` prints one card with its evidence, and MCP clients read it from `chemdraw://style-guide/{name}`. See [journal and group house styles](../README.md#journal-and-group-house-styles) and the [style gallery](../skill/chemdraw/assets/house-styles/gallery/README.md), which also indexes 47 published figures redrawn in their own style.

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
| Menu commands | 159 | 1 | 0 | 158 |

Ask the catalog with `chemdraw_inventory(layer, query, tier)`, or open the generated pages under `skill/chemdraw/references` (`interface-chemscript.md`, `interface-com.md`, `interface-cdxml-model.md`, `interface-menu.md`, `recipes-chemdraw.md`). The pages are rebuilt with `python <skill>/scripts/cdx.py regen-catalog`.

What this does not claim: the numbers were checked on ChemDraw 22.2.0 for Windows only. macOS answers the ChemScript operations and a subset of the SDK, other ChemDraw versions may differ, binary CDX files are converted through ChemDraw rather than edited directly, and menu commands (for example NMR prediction) are not opened as tools because ChemDraw runs them only from a visible window; the one exception is Analyze Stoichiometry, which `stoichiometry_grid` runs in a private ChemDraw window shown briefly. `chemdraw_com_call` refuses printing, the clipboard, menu objects and preference changes, and writes a file only when file access is allowed explicitly.

## MCP (optional)

The command line covers every tool, so no server is required. Clients that prefer MCP can register `<runtime-python> -m cdxml_toolkit.mcp_runtime` (no profile flag needed); `cdx.py doctor` prints the runtime path. The MCP server also registers `@mcp.resource` (`chemdraw://references/{slug}`, `chemdraw://templates/{slug}`, `chemdraw://style-guide/{preset}`) and `@mcp.prompt` (`draw_reaction_scheme`, `reconstruct_figure`, `analyze_nmr_and_lcms`, `build_acs1996_figure`) protocol endpoints, plus `live_chemdraw_session` (non-destructive live desktop ChemDraw window integration) and `build_acs_figure`. For a remote Windows host, see the HTTP section of [operations](../skill/chemdraw/references/operations.md#remote-http-only-when-asked).

## Development validation

```powershell
python scripts/validate_distribution.py                           # repository checks and installer tests
python skill/chemdraw/scripts/cdx.py py -m pip install pytest
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py regen-signatures             # after a toolkit change (syncs signatures, schema, inventories & runtime.json; --check verifies)
cd toolkit; python -m pytest -m "not network" -q                 # toolkit tests (runtime Python)
```

Validate final structure readback separately from visual comparison. Read only the relevant [workflow](../skill/chemdraw/references/workflow-router.md); exact interfaces live in the [generated signatures](../skill/chemdraw/references/mcp-signatures.md). Keep chemistry, source files and credentials out of logs and public repositories. Repository content is licensed for noncommercial use under [PolyForm Strict 1.0.0 and CC BY-NC-ND 4.0](../LICENSE) (upstream toolkit code retains [MIT](../toolkit/LICENSE)); dependencies and desktop software retain their own terms.
