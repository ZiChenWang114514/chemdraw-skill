# Agent integration

The Skill needs an agent that can read `SKILL.md` and run shell commands. Image reconstruction additionally needs vision (or a human reviewer). Native ChemDraw output needs a licensed Windows host.

## Layout

| Item | Default location (Claude Code) |
| --- | --- |
| Skill folder | `~/.claude/skills/chemdraw/` — discovered automatically |
| Toolkit runtime | `~/.claude/skills/chemdraw-venv/` — a sibling of the Skill; created by `install.ps1 -Runtime` |
| Entry point | `<skill>/scripts/cdx.py` |
| Installation manifest | `<skill>/manifest.json`, written by the installer |
| Backups of replaced installs | `~/.claude/backups/skills/chemdraw/` (outside `skills/`, so never loaded as a second Skill) |

Other agents: install with `install.ps1 -Destination <their skill folder>`, or point their project instructions at `<skill>/SKILL.md`. The runtime venv always sits beside the Skill folder.

`cdx.py` finds the runtime in this order: `CHEMDRAW_MCP_PYTHON`, the sibling `chemdraw-venv`, a conda environment named `cdxml` (from `~/.conda/environments.txt`). Started from any other Python, it re-launches itself there.

To stop permission prompts in Claude Code, allow the entry point in `settings.json`:

```json
{"permissions": {"allow": ["Bash(python ~/.claude/skills/chemdraw/scripts/cdx.py:*)"]}}
```

## Why the command line instead of MCP

- `cdx.py call` runs every registered tool through the same isolated worker an MCP server would use: worker timeout, native ChemDraw mutex, input/output limits and the JSON result envelope are unchanged.
- Large results go to a file and only a summary is printed, so tool output does not flood the conversation.
- No resident server, no client registration to keep in sync, nothing to restart after an upgrade.

An MCP server remains available for clients that want typed tool calls. Register it with the runtime interpreter and no profile flag (the default profile is the full tool set), for example in Claude Code:

```bash
claude mcp add --scope user cdxml-toolkit -- <runtime-python> -m cdxml_toolkit.mcp_runtime
```

`<runtime-python>` is the `"runtime"` value printed by `cdx.py doctor`. For a remote Windows host, see the HTTP section of [operations](operations.md).

## Command reference

```text
cdx.py tools [--detail summary]           list tools, timeouts and native-lock use
cdx.py sig TOOL                           print one generated signature
cdx.py call TOOL --json '{...}' | --args FILE [--out NEW.json]
cdx.py render A.cdxml [B.cdxml ...] [--out-dir DIR]
cdx.py build SPEC.json OUT.cdxml [--render]
cdx.py decimer IMAGE [--hand-drawn] [--preflight] [--out NEW.json]
cdx.py chemscript-info SAVED.cdxml        direct ChemScript reading, under the native lock
cdx.py doctor [--paths] [--native] [--office] [--chemscript] [--full]
cdx.py py ARGS...                         run the runtime Python (helper scripts, -m modules, tests)
cdx.py regen-signatures                   after a toolkit upgrade
```

`call` prints results up to about 6 KB directly; larger results go to a new file under the temp folder's `chemdraw-cdx` directory (or `--out`) and a short summary with the path is printed. `ok` means the tool ran without error. Existing result files are never overwritten.

`render` writes to a temporary name and replaces the old PNG only after a successful render, so a failed render keeps the previous image.

## Subagents

Subagents load the same Skill. Give them the `cdx.py` command form, never a guessed interpreter path. Native work is serialized by the ChemDraw mutex however many agents run.
