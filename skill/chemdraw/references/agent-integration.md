# Agent integration

The Skill follows the open Agent Skills layout (a folder with `SKILL.md`, `references/`, `scripts/`, `assets/`) and needs only two things from an agent: it can read the files and run shell commands. Image reconstruction also needs vision (or a human reviewer). Native ChemDraw output needs licensed desktop ChemDraw: COM on Windows, or ChemDraw for macOS through AppleScript (the first call asks for the macOS Automation permission; see [operations](operations.md#macos)).

## Install for an agent

From a repository checkout, `scripts/install.py` copies the Skill into each agent's Skill folder and can build the shared toolkit runtime. It prints a JSON proposal first; add `--apply` to install.

```bash
python scripts/install.py --agent claude agents --runtime          # proposal
python scripts/install.py --agent claude agents --runtime --apply  # install
python scripts/install.py --agent copilot --project <repo> --apply # project-scoped copy
python scripts/install.py --destination <any skills folder>/chemdraw --apply
```

| `--agent` | User folder | Project folder (`--project DIR`) | Typical readers |
| --- | --- | --- | --- |
| `claude` | `~/.claude/skills/` | `.claude/skills/` | Claude Code; also read by GitHub Copilot and OpenCode |
| `agents` | `~/.agents/skills/` | `.agents/skills/` | The shared folder of the Agent Skills convention: Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode and others |
| `codex` | `~/.agents/skills/` | `.agents/skills/` | Alias for `agents` (Codex CLI and app) |
| `gemini` | `~/.gemini/skills/` | `.gemini/skills/` | Gemini CLI |
| `antigravity` | `~/.gemini/antigravity/skills/` | `.agent/skills/` | Antigravity |
| `copilot` | `~/.copilot/skills/` | `.github/skills/` | GitHub Copilot (VS Code and CLI) |
| `cursor` | `~/.cursor/skills/` | `.cursor/skills/` | Cursor |
| `windsurf` | `~/.codeium/windsurf/skills/` | `.windsurf/skills/` | Windsurf |
| `opencode` | `~/.config/opencode/skills/` | `.opencode/skills/` | OpenCode |
| `kimi` | `~/.kimi-code/skills/` | `.kimi-code/skills/` | Kimi Code CLI & Desktop app (`--mcp` writes `~/.kimi-code/mcp.json` & `~/.kimi/mcp.json`) |
| `zcode` | `~/.zcode/skills/` | `.zcode/skills/` | ZCode CLI & ZCode GUI (`--mcp` updates `mcp.servers` in `~/.zcode/cli/config.json`) |
| `dsh` | `~/.dsh/skills/` | `.dsh/skills/` | DeepSeek Harness CLI & Web UI (`--mcp` updates `~/.dsh/cordis.patch.yml`) |
| `qoder` | `~/.qoder/skills/` | `.qoder/skills/` | Qoder & Qoder CN IDE (`~/.qoder-cn/skills/`, `--mcp` writes `mcp.json`) |
| `codebuddy` | `~/.codebuddy/skills/` | `.codebuddy/skills/` | CodeBuddy & WorkBuddy (`--mcp` writes `~/.codebuddy/mcp.json`) |
| `lingma` | `~/.lingma/skills/` | `.lingma/skills/` | Tongyi Lingma |
| `comate` | `~/.comate/skills/` | `.comate/skills/` | Baidu Comate |
| `bailian` | `~/.bailian/skills/` | `.bailian/skills/` | Bailian CLI |
| `codegeex` | `~/.codegeex/skills/` | `.codegeex/skills/` | CodeGeeX |
| `pi` | `~/.pi/agent/skills/` | `.pi/skills/` | pi; also reads `~/.agents/skills/`; runs shell commands without asking |
| `cline` | `~/.cline/skills/` | `.cline/skills/` | Cline CLI & VS Code extension |
| `roo` | `~/.roo/skills/` | `.roo/skills/` | Roo Code VS Code extension |
| `goose` | `~/.config/goose/skills/` | `.goose/skills/` | Goose CLI & Desktop |
| `trae` | `~/.trae/skills/` | `.trae/skills/` | Trae, Trae CN & Trae Solo |
| `kiro` | `~/.kiro/skills/` | `.kiro/skills/` | Kiro IDE & CLI |
| `aider` | `~/.aider/skills/` | `.aider/skills/` | Aider (`--mcp` adds `SKILL.md` to `~/.aider.conf.yml`) |
| `amp` | `~/.config/agents/skills/` | `.agents/skills/` | Sourcegraph Amp CLI |
| `qwen` | `~/.qwen/skills/` | `.qwen/skills/` | Qwen Code CLI |
| `continue` | `~/.continue/skills/` | `.continue/skills/` | Continue CLI (`cn`) & IDE |
| `zed` | `~/.zed/skills/` | `.zed/skills/` | Zed Editor |
| `openhands` | `~/.openhands/skills/` | `.openhands/skills/` | OpenHands |

Pass `--mcp` with `--apply` (for example `python scripts/install.py --agent codex cursor windsurf goose cline --runtime --mcp --apply`) to automatically register or update the `cdxml-toolkit` MCP server configuration across each harness's native TOML, YAML, JSON, or JSONC config file.

Discovery folders change between agent releases; check your agent's documentation when a copy is not picked up, and use `--destination` for any folder not listed. An agent that reads several of these folders may list the Skill once per copy; keep only the copies it needs.

**Agents without Skill discovery.** Copy the Skill anywhere (`--destination`) and add one line to the agent's instruction file (`AGENTS.md`, `GEMINI.md`, `.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, a system prompt):

```text
For chemical structures, reactions, ChemDraw/CDXML files or chemistry figures, read <skill>/SKILL.md first and follow it.
```

## Runtime

All copies share one toolkit venv: `%LOCALAPPDATA%\chemdraw-skill\venv` on Windows, `$XDG_DATA_HOME/chemdraw-skill/venv` (default `~/.local/share/...`) elsewhere. `--runtime-dir` puts it somewhere else. Whenever the search below would not pick the venv the installer just built (a custom `--runtime-dir`, or an older `chemdraw-venv` beside the Skill folder that would win), the installer writes `runtime.local.json` into each copy, and into the repository checkout it was run from, so the Skill uses the new venv; when the search already picks it, a leftover `runtime.local.json` is removed instead. A set `CHEMDRAW_MCP_PYTHON` still comes first, and the installer's report says so. Replaced installations are moved to `chemdraw-skill/backups/` in the same data folder, outside every Skill folder, with a `BACKUP_ORIGIN.txt` naming where they came from.

`cdx.py` looks for the runtime in this order and re-launches itself there when started from any other Python 3.9+ (a candidate whose interpreter no longer starts, for example a venv whose base Python was removed, is skipped):

1. `CHEMDRAW_MCP_PYTHON`
2. `runtime.local.json` in the Skill folder
3. a `chemdraw-venv` folder beside the Skill folder (older layout; still honored and reused by the installer)
4. the shared venv above
5. a conda environment named `cdxml` (from `~/.conda/environments.txt`)

## Command permissions

Every Skill action is one command prefix, so a single allowlist entry stops repeated approval prompts. Allow `python <skill>/scripts/cdx.py` in your agent's command allowlist (use the interpreter name you actually run: `python3`, `python` or `py`). For example, in Claude Code `settings.json`:

<!-- example: fragment -->
```json
{"permissions": {"allow": ["Bash(python ~/.claude/skills/chemdraw/scripts/cdx.py:*)"]}}
```

This entry also allows `cdx.py py`, which runs any Python script or `-c` code in the runtime, so it grants as much as allowing that Python interpreter. Where that is too broad, allow the specific subcommands instead (`cdx.py call:*`, `cdx.py render:*`, `cdx.py doctor:*`, ...) and approve `cdx.py py` calls one at a time.

## Why the command line instead of MCP

- `cdx.py call` runs every registered tool through the same isolated worker an MCP server would use: worker timeout, native ChemDraw lock, input/output limits and the JSON result envelope are unchanged.
- Large results go to a file and only a summary is printed, so tool output does not flood the conversation.
- No resident server, no client registration to keep in sync, nothing to restart after an upgrade, and it works in every agent that has a shell.

An MCP server remains available for clients that want typed tool calls. Register the runtime interpreter (the `"runtime"` value printed by `cdx.py doctor`) with no profile flag for the `standard` set (the core tools plus `draw_figure`, `rdkit_workbench`, the checking and diagnosis tools and the two interactive apps), or add `"--profile", "full"` to the arguments to list every tool. `cdx.py call` reaches every tool either way. Most clients accept the common `mcpServers` JSON shape:

<!-- example: fragment -->
```json
{"mcpServers": {"cdxml-toolkit": {"command": "<runtime-python>", "args": ["-m", "cdxml_toolkit.mcp_runtime"]}}}
```

TOML-configured clients use the same command and arguments:

```toml
[mcp_servers.cdxml-toolkit]
command = "<runtime-python>"
args = ["-m", "cdxml_toolkit.mcp_runtime"]
```

Command-line registration, for example `claude mcp add --scope user cdxml-toolkit -- <runtime-python> -m cdxml_toolkit.mcp_runtime`. For a remote Windows host, see the HTTP section of [operations](operations.md).

## Command reference

<!-- example: commands -->
```text
cdx.py tools [QUERY] [--detail summary]   list tools, timeouts and native-lock use
cdx.py sig TOOL...                        print one or more generated signatures
cdx.py resolve QUERY... [--offline] [--out FILE] [--full|--summary]   resolve names, CAS numbers or formulas to SMILES
cdx.py inspect FILE [--objects] [--keep DIR] [--out FILE] [--full|--summary]   inspect structures, objects or peaks in CDXML/CDX/SDF/Office/LCMS; --keep saves each Office object as CDXML
cdx.py catalog LAYER NAME                 one ChemDraw type's members (layer: chemscript, com, cdxml)
cdx.py report [TARGET...] [--smiles S] [--name N] [--balance RXN] [--hrms] [--map RXN] [--output FILE] [--out FILE] [--full|--summary]   property sheet, HRMS, balance or atom mapping
cdx.py call TOOL [-a KEY=VAL ...] [--json '{...}' | --args FILE] [--out NEW.json] [--full|--summary] [--accel auto|on|off]
cdx.py render A.cdxml [B.cdxml ...] [--out-dir DIR] [--replace]
cdx.py build SPEC.json NEW.cdxml [--render] [--allow-draft]
cdx.py scientific nmr|plot|tlc|apparatus|mechanism|stack_nmr|lcms_plate SPEC.json OUTPUT [--render]
cdx.py draw [BRIEF.json|--name NAME|--smiles SMILES|--reaction RXN|--compact DSL] [OUTPUT] [--above TEXT] [--below TEXT] [--yield Y] [--arrow STYLE] [--layout L] [--label L] [--title T] [--abbreviate G] [--columns N] [--number [STYLE]] [--properties] [--render] [--style PRESET] [--out NEW.json] [--full|--summary]   checked molecule, scheme, scope panel or mechanism
cdx.py styles [PRESET] [--json]          built-in journal style presets (ChemDraw stock style sheets)
cdx.py decimer IMAGE [--hand-drawn] [--preflight] [--timeout S] [--out NEW.json]
cdx.py ocsr IMAGE [--engines a,b|all] [--hand-drawn] [--preflight] [--no-upload] [--timeout S] [--out NEW.json] [--accel MODE]   several OCSR engines, compared (`decimer` is `ocsr IMAGE --engines decimer-api`)
cdx.py predict products|retro|nmr|conditions SMILES [--products P] [--engine NAME] [-a KEY=VAL ...] [--json ARGS] [--args FILE] [--out FILE] [--accel MODE]   model predictions (see engines.md)
cdx.py engines [--sizes] [--recommend NEED]   which optional engines are installed, their disk use; what to install for a need
cdx.py stop-daemons                       end the resident engine workers that --accel started
cdx.py install-engines NAME... [--bundle B] [--task T] [--dry-run] [--status]   optional engines, each in its own environment
cdx.py remove-engines NAME... [--yes]     delete installed engines (dry run without --yes)
cdx.py markush init|next|submit|status WORKDIR [TASK ANSWER.json] [--image IMG --text CLAIM --crop X0 Y0 X1 Y1 --reuse OLD]
cdx.py office-edit DOCUMENT [--object N] [--workdir NEW_DIR] [--no-open]
cdx.py office-edit DOCUMENT|EDIT_DIR --finish [--output NEW] [--wait S] [--pdf]
cdx.py calc REACTION|FILE.cdxml [--output NEW.cdxml] [--no-open]   ChemDraw's own stoichiometry grid, opened in ChemDraw
cdx.py calc --read SAVED.cdxml            read the grid's numbers back as JSON (no ChemDraw needed)
cdx.py install-mappers [rxnmapper] [localmapper] [--dry-run] [--status]   optional atom-mapping backends
cdx.py doctor [--paths] [--native] [--office] [--chemscript] [--full] [--text] [--log ID|latest]
cdx.py molstar [TARGET] [--smiles S] [--pdb ID] [--rep R] [--output FILE.html] [--no-browser] [--out FILE]
cdx.py studio [TEMPLATE] [--cdxml FILE] [--smiles S] [--style S] [--output FILE.html] [--fragment FRAG.html] [--serve] [--port P] [--sync-dir DIR] [--no-browser] [--out FILE]
cdx.py py ARGS...                         run the runtime Python (helper scripts, -m modules, tests)
```

`call` deduplicates matching top-level `outputs` on stdout and prints results up to about 6 KB directly (pass `--full` to print any size, or `--summary` to force a compact summary); larger results go to a new file under the temp folder's `chemdraw-cdx` directory (or `--out`) and print an enriched summary with `output_path`, `png_path`, `checks_passed`, `readback`, warnings preview and the evidence path. `ok` means the tool ran without error. Existing result files are never overwritten (refusals include `(next available: ...)`).

`render` writes to a temporary name and publishes the PNG only after a successful render, so a failed render keeps the previous image. It replaces an existing PNG only when it rendered that exact file before; any other PNG of the same name is refused with its path unless `--replace` is given, and two inputs that would share one PNG are refused. `build` never replaces an existing CDXML. `draw` runs `draw_figure` (or `render_scheme` with `--compact`) and never replaces an existing output ([scheme drawing](scheme-drawing.md)). `markush` and `office-edit` are described in [Markush structures](markush.md) and [operations](operations.md#macos).

On PowerShell or `cmd.exe`, prefer `cdx.py resolve`, `cdx.py inspect`, `cdx.py report`, `cdx.py draw --reaction`, or `-a KEY=VALUE` on `cdx.py call` to avoid JSON quoting; for complex nested dicts, put them in a file and pass `--args`.

## Subagents

Subagents load the same Skill. Give them the `cdx.py` command form, never a guessed interpreter path. Native work is serialized by the ChemDraw lock however many agents run.

## Inline 2D Studio across coding agents

Every coding agent renders interactive tools through one of four host surfaces; `open_drawing_studio` and `cdx.py studio` emit the artifacts for all four from one shared HTML fragment core:

1. **MCP Apps & Apps SDK hosts (`Cursor`, `VS Code` / `GitHub Copilot`, `Goose`, `Windsurf`, `Codex` MCP Apps)**: calling the MCP tool `open_drawing_studio` returns `CallToolResult.structuredContent` alongside `_meta.ui.resourceUri` (`ui://cdxml-toolkit/drawing-studio.html`, `text/html;profile=mcp-app`) and `_meta["openai/outputTemplate"]`, mounting the interactive 2D board inline inside the tool card.
2. **Inline `visualize` fragment hosts (`Codex` Desktop & `ZCode` GUI)**: write a pure HTML fragment (no `<html>`/`<head>`/`<body>` tags) into a writable session directory via `cdx.py studio blank --no-browser --fragment <workdir>/chemdraw-studio.html`, then emit the host's single-line `visualize` reference (`path` set to the absolute fragment path, `"mode":"wide"` — `::visualize{...}` in ZCode GUI) so the 2D board mounts directly inside the answer bubble with `widgetState` persistence and follow-up prompt dispatch (`window.zcode` / host bridge).
3. **Artifact-embed & VSIX IDE hosts (`Antigravity`, `VS Code`, `Cursor`, `Windsurf`, `Qoder`, `Trae`, `Kiro`, `Cline`, `Roo Code`, `Kimi Code` IDE)**: in Antigravity emit `<agent-embed src="file:///<artifact_dir>/chemdraw-studio.html"></agent-embed>`; in any VS Code-family IDE install `vscode/dist/chemdraw-studio-0.7.0.vsix` (`python vscode/scripts/build_vsix.py --install-all`) to open `.cdxml`/`.mol` directly as 2D canvases or dock the 2D Studio beside any AI chat sidebar (`Ctrl+Alt+M`).
4. **Terminal CLI agents (`Gemini CLI`, `OpenCode` TUI, `Aider`, `Kimi`, `Qwen`, `Amp`, `Continue`)**: run `cdx.py studio TEMPLATE --serve --sync-dir <workdir>`; clicking **Send to Agent** in the browser writes `studio-live.cdxml` and `studio-live.json` straight back to `<workdir>` and copies a ready-to-paste prompt to the clipboard.

## Agent notes

Codex's Windows sandbox needs Python 3.12's temp-folder workaround that the runtime applies itself (see [operations](operations.md#failure-modes)); pi needs `--approve` to load a project-level Skill.

