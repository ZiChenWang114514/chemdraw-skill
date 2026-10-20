# Project Instructions

- This folder is the bundled runtime of the ChemDraw Skill; the repository-root `AGENTS.md` also applies.
- Preserve the `cdxml_toolkit` import package, the `cdxml-toolkit-community` distribution name, the 15 compatible core MCP tool names, and the shared ChemDraw COM mutex name.
- Keep the runtime client-neutral: no agent-specific configuration writers, defaults, paths or product names (the `codex` profile alias is the only compatibility exception).
- Use `cdxml_toolkit.mcp_runtime` for the complete service and `cdxml_toolkit.mcp_server` only for core compatibility work.
- Ground molecular connectivity in a trusted user value, resolver, parser, or OCSR result. Do not invent SMILES.
- Route structural changes through `modify_molecule` and inspect its MCS diff.
- Preserve inputs. Generated artifacts use new paths unless overwrite permission is explicit.
- Keep native ChemDraw work in isolated workers and under the shared native resource lock.
- Do not record molecular content, file contents, credentials, or tool arguments in metrics or health responses.
- Regenerate `docs/mcp-tools.md` and `docs/mcp-schema.json` after changing the tool registry.
- Run `pytest -m "not network" -q`, package checks, and applicable native probes before release.

## Public-facing language

Write public documentation and example captions for readers without conversation history. Do not expose internal experiment identifiers, development stage names, handoff notes, session references or intermediate work logs. Explain technical terms when they help users; retain exact API names, scientific notation, paper compound numbering and necessary compatibility/version requirements. Keep test data identifiers out of homepage artwork and marketing examples.
