# ChemDraw Skill setup and operations

For any agent that can load local instructions and call MCP or Python. Start with [generic integration](../skill/chemdraw/references/agent-integration.md). If the client does not discover Skills, supply the absolute `SKILL.md` path through project instructions. Client configuration formats differ.

## First-Time Windows Setup

Use 64-bit Python 3.10–3.13, preferably in a dedicated Python 3.12 environment. Portable CDXML/RDKit work needs no desktop application. Native output requires activated Windows ChemDraw; install Office and ChemScript only for the selected workflows.

```powershell
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
Set-Location .\chemdraw-skill
python skill/chemdraw/scripts/install_runtime.py --extras windows office chemscript publication
```

```powershell
$python = (Get-Command python).Source
.\scripts\check_prerequisites.ps1 -Python $python -Capabilities core
# Use your client's actual Skill discovery path, or load this folder explicitly.
.\scripts\install.ps1 -Destination "$HOME/.agents/skills/chemdraw" -Python $python
.\scripts\install.ps1 -Destination "$HOME/.agents/skills/chemdraw" -Python $python -Apply
```

The installer previews first; `-Apply` backs up and installs. It does not configure a client by default. On macOS/Linux, copy the Skill folder and use the same Python MCP arguments. The full service arguments are `-m cdxml_toolkit.mcp_runtime --profile codex`; this profile name is a compatibility identifier.

The install helper and CI read the same exact commit from [runtime.json](../skill/chemdraw/runtime.json). Use no extras for core-only work; `--print-requirement` prints the selected requirement without installing. Extras select features, not a different source revision.

The pinned baseline includes the `0.7.0a2` runtime fixes. For a local development checkout, use `python skill/chemdraw/scripts/install_runtime.py --toolkit-path <local-toolkit-checkout> --extras office publication`. When changing the recommended runtime, update `runtime.json` to its complete published commit and validate that combination.

## Validation and troubleshooting

```powershell
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipNativeChemDraw -SkipDevelopmentChecks
# Native ChemDraw + ChemScript, without Office:
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipOffice
# Complete licensed workstation checks:
.\skill\chemdraw\scripts\health_check.ps1 -Python $python
```

Success ends with `ChemDraw agent integration: OK`. Generic checks do not validate a particular client registration: refresh the agent tool list and call `get_toolkit_capabilities()`. Select `core,native,chemscript,office,decimer` as needed; skipped features are not verified. See [operations](../skill/chemdraw/references/operations.md) for bitness, timeouts, remote hosting and DECIMER.

<details>
<summary>Optional Codex client adapter</summary>

Only for this client, after its CLI is already installed:

```powershell
.\scripts\install.ps1 -Python $python -ConfigureMcp
.\scripts\install.ps1 -Python $python -ConfigureMcp -Apply
codex mcp get cdxml-toolkit --json
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipNativeChemDraw -SkipDevelopmentChecks -CheckCodex
```

This opt-in adapter uses `$HOME/.codex/skills/chemdraw` (or `CODEX_HOME`) and preserves the client's configuration. `configure_mcp.ps1` configures only this client. Other agents use their own MCP registration settings.

</details>

## Streamable HTTP

Register the host MCP URL and authentication in your own client settings. Server arguments and access controls are documented in [operations](../skill/chemdraw/references/operations.md#streamable-http-and-metrics).

Runtime-only checks use `-SkipDevelopmentChecks`: this explicitly skips pytest and reference regeneration. Development checks require pytest and the test dependencies (`office`, `publication`, and requests), plus a toolkit checkout matching the generated reference version. This distinction lets core-only installations run health checks without optional native or test dependencies.

## Development validation

```powershell
python scripts/validate_distribution.py
python -m pytest skill/chemdraw/scripts -q
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipNativeChemDraw
```

Validate final structure readback separately from visual comparison. Read only the relevant [workflow](../skill/chemdraw/references/workflow-router.md); exact interfaces live in the [generated signatures](../skill/chemdraw/references/mcp-signatures.md). Keep chemistry, source files and credentials out of logs and public repositories. Repository content uses [MIT](../LICENSE); dependencies and desktop software retain their own terms.
