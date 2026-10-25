# Contributing

Contributions should keep the Skill focused, portable, and verifiable on a real Windows/ChemDraw installation.

## Development Setup

1. Fork and clone the repository.
2. Install a runtime: `python scripts/install.py --runtime-only --apply` (or create one by hand with `install_runtime.py`, see the guide).
3. Run the baseline validation before making changes.

```powershell
python scripts/validate_distribution.py
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py doctor
```

See the [project guide](../docs/guide.md#development-validation) for native ChemDraw, Office, and network-gated checks.

## Change Rules

- Keep `skill/chemdraw/SKILL.md` a compact task router; put detailed guidance in the existing reference hierarchy.
- Preserve public tool names, `cdx.py` commands and response contracts unless the change is intentionally breaking and documented in the pull request.
- Add a failing test before implementing a bug fix or new behavior.
- Use runtime discovery instead of machine-specific usernames or installation paths.
- Do not commit credentials, proprietary binaries, ChemDraw installers, Office files containing private data, or DECIMER model weights.
- Keep repository documentation consolidated. Do not add a standalone document when an existing section is the authoritative home.

## Toolkit (`toolkit/`)

`toolkit/` holds the `cdxml_toolkit` package that the Skill runs on. It keeps its own `pyproject.toml`, tests and generated MCP reference.

```powershell
cd toolkit
python -m pip install -e ".[dev,windows,office,analysis,image,scientific]"
python -m pytest -m "not network" -q
python -m cdxml_toolkit.mcp_runtime.generate_reference --markdown docs/mcp-tools.md --json docs/mcp-schema.json
```

- Preserve stereochemistry, isotopes, formal charges, atom mapping and CDXML document validity.
- Mark tests that need the network with `@pytest.mark.network`; keep native tests separate from portable tests and report skipped applications.
- When changing the version, update `toolkit/pyproject.toml`, `toolkit/cdxml_toolkit/__init__.py` and `skill/chemdraw/runtime.json` together.
- After changing the tool registry, regenerate `toolkit/docs/mcp-tools.md` and `mcp-schema.json`, then `cdx.py regen-signatures` for the Skill.
- Keep the import package `cdxml_toolkit`, its public tool names and the shared ChemDraw COM mutex name stable.

## Issues and Pull Requests

Use the repository issue forms for reproducible bugs and focused feature proposals. Include the operating system, Python version, ChemDraw version, exact command, and sanitized error output when relevant.

Pull requests should be small enough to review, explain user-visible behavior changes, and list the validation actually run. Native automation claims require evidence from a licensed ChemDraw installation; network-dependent tests must remain opt-in.

Be respectful and keep technical discussion focused on the work. Harassment, discriminatory language, threats, and disclosure of another person's private information are not acceptable.

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), not in a public issue.
