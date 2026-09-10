# Connect any agent

This Skill is client-independent guidance plus Python tools. Any agent that can read local instructions and call MCP tools or execute Python can use it. Image reconstruction additionally needs agent vision (or explicit human visual review); a text-only agent cannot certify pixels it has not inspected. Native ChemDraw output requires a licensed Windows rendering host.

## Load the instructions

Load `SKILL.md` from this folder's parent. A client with native Skill support may install the entire `chemdraw` folder in its own discovery directory. Otherwise, provide the absolute `SKILL.md` path in the agent's project instructions. Resolve linked references and scripts relative to that folder. `agents/openai.yaml` is optional metadata for one client family, not a runtime dependency.

## Connect the runtime

In an MCP-capable client, register a stdio server using its own settings format:

```json
{
  "command": "/absolute/path/to/python",
  "args": ["-m", "cdxml_toolkit.mcp_runtime", "--profile", "codex"]
}
```

Use the interpreter in the installed toolkit environment. `codex` is the runtime's existing full-profile identifier (38 tools), accepted by any MCP client; it does not require that product. Keep this literal identifier until the runtime provides a compatible replacement. Restart or refresh the client, list tools, then call `get_toolkit_capabilities()`.

Without MCP, use the [Python/CLI routes](toolkit-cli-interfaces.md) and [figure CLI](publication-figures.md#immediate-cli-fallback). A remote client may connect to the Windows host's authenticated Streamable HTTP endpoint; see [operations](operations.md). Client configuration schemas differ, so do not copy another product's settings file verbatim.

## Installation helpers

The repository Windows installer accepts `-Destination` for any client or project folder. Its default storage location is `$HOME/.agents/skills/chemdraw`; this is this installer's default, not a claim that every client auto-discovers it. The source folder can also be copied on macOS/Linux without PowerShell.

Prerequisite and health checks do not require a particular agent CLI by default. Use `health_check.ps1 -SkipNativeChemDraw` for portable validation. Inspect client tool discovery separately when using generic MCP integration.

## Optional Codex adapter

Only for users of this client: repository `scripts/install.ps1 -ConfigureMcp` selects its conventional destination and invokes `scripts/configure_mcp.ps1`. `-Apply` performs the inspected proposal. The adapter preserves configuration and existing Skill backups. Add `-CheckCodex` to prerequisite/health checks when you want to verify this client's CLI or MCP registration. Existing `-SkipCodex` on the prerequisite checker remains supported.

The `.codex` paths, `CODEX_HOME`, `codex mcp` commands, `codex_config` module and generated signatures identify actual compatibility interfaces; do not replace their spelling with generic prose.
