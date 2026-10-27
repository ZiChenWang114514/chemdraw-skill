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
| `gemini` | `~/.gemini/skills/` | `.gemini/skills/` | Gemini CLI |
| `copilot` | `~/.copilot/skills/` | `.github/skills/` | GitHub Copilot (VS Code and CLI) |
| `cursor` | `~/.cursor/skills/` | `.cursor/skills/` | Cursor |
| `opencode` | `~/.config/opencode/skills/` | `.opencode/skills/` | OpenCode |

Discovery folders change between agent releases; check your agent's documentation when a copy is not picked up, and use `--destination` for any folder not listed. An agent that reads several of these folders may list the Skill once per copy; keep only the copies it needs.

**Agents without Skill discovery.** Copy the Skill anywhere (`--destination`) and add one line to the agent's instruction file (`AGENTS.md`, `GEMINI.md`, `.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, a system prompt):

```text
For chemical structures, reactions, ChemDraw/CDXML files or chemistry figures, read <skill>/SKILL.md first and follow it.
```

## Runtime

All copies share one toolkit venv: `%LOCALAPPDATA%\chemdraw-skill\venv` on Windows, `$XDG_DATA_HOME/chemdraw-skill/venv` (default `~/.local/share/...`) elsewhere. `--runtime-dir` puts it somewhere else; the installer then writes `runtime.local.json` into each copy, and into the repository checkout it was run from, so the Skill still finds it. Replaced installations are moved to `chemdraw-skill/backups/` in the same data folder, outside every Skill folder, with a `BACKUP_ORIGIN.txt` naming where they came from.

`cdx.py` looks for the runtime in this order and re-launches itself there when started from any other Python 3.9+ (a candidate whose interpreter no longer starts, for example a venv whose base Python was removed, is skipped):

1. `CHEMDRAW_MCP_PYTHON`
2. `runtime.local.json` in the Skill folder
3. a `chemdraw-venv` folder beside the Skill folder (older layout; still honored and reused by the installer)
4. the shared venv above
5. a conda environment named `cdxml` (from `~/.conda/environments.txt`)

## Command permissions

Every Skill action is one command prefix, so a single allowlist entry stops repeated approval prompts. Allow `python <skill>/scripts/cdx.py` in your agent's command allowlist (use the interpreter name you actually run: `python3`, `python` or `py`). For example, in Claude Code `settings.json`:

```json
{"permissions": {"allow": ["Bash(python ~/.claude/skills/chemdraw/scripts/cdx.py:*)"]}}
```

This entry also allows `cdx.py py`, which runs any Python script or `-c` code in the runtime, so it grants as much as allowing that Python interpreter. Where that is too broad, allow the specific subcommands instead (`cdx.py call:*`, `cdx.py render:*`, `cdx.py doctor:*`, ...) and approve `cdx.py py` calls one at a time.

## Why the command line instead of MCP

- `cdx.py call` runs every registered tool through the same isolated worker an MCP server would use: worker timeout, native ChemDraw mutex, input/output limits and the JSON result envelope are unchanged.
- Large results go to a file and only a summary is printed, so tool output does not flood the conversation.
- No resident server, no client registration to keep in sync, nothing to restart after an upgrade, and it works in every agent that has a shell.

An MCP server remains available for clients that want typed tool calls. Register the runtime interpreter (the `"runtime"` value printed by `cdx.py doctor`) with no profile flag; the default profile is the full tool set. Most clients accept the common `mcpServers` JSON shape:

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

```text
cdx.py tools [--detail summary]           list tools, timeouts and native-lock use
cdx.py sig TOOL                           print one generated signature
cdx.py call TOOL --json '{...}' | --args FILE [--out NEW.json]
cdx.py render A.cdxml [B.cdxml ...] [--out-dir DIR] [--replace]
cdx.py build SPEC.json NEW.cdxml [--render]
cdx.py decimer IMAGE [--hand-drawn] [--preflight] [--out NEW.json]
cdx.py markush init|next|submit|status WORKDIR [TASK ANSWER.json] [--image IMG --text CLAIM --crop X0 Y0 X1 Y1 --reuse OLD]
cdx.py office-edit DOCUMENT [--object N] [--workdir NEW_DIR] [--no-open]
cdx.py office-edit DOCUMENT|EDIT_DIR --finish [--output NEW] [--wait S] [--pdf]
cdx.py chemscript-info SAVED.cdxml        direct ChemScript reading, under the native lock
cdx.py doctor [--paths] [--native] [--office] [--chemscript] [--full]
cdx.py py ARGS...                         run the runtime Python (helper scripts, -m modules, tests)
cdx.py regen-signatures                   after a toolkit upgrade
cdx.py regen-catalog [--check]            rewrite (or only check) the generated ChemDraw interface pages
```

`call` prints results up to about 6 KB directly; larger results go to a new file under the temp folder's `chemdraw-cdx` directory (or `--out`) and a short summary with the path is printed. `ok` means the tool ran without error. Existing result files are never overwritten.

`render` writes to a temporary name and publishes the PNG only after a successful render, so a failed render keeps the previous image. It replaces an existing PNG only when it rendered that exact file before; any other PNG of the same name is refused with its path unless `--replace` is given, and two inputs that would share one PNG are refused. `build` never replaces an existing CDXML. `markush` and `office-edit` are described in [Markush structures](markush.md) and [operations](operations.md#macos).

On a shell that does not pass JSON quotes through intact (Windows PowerShell 5, `cmd.exe`), write the arguments to a file and use `--args`.

## Subagents

Subagents load the same Skill. Give them the `cdx.py` command form, never a guessed interpreter path. Native work is serialized by the ChemDraw mutex however many agents run.
