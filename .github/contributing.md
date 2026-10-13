# Contributing

Contributions should keep the Skill focused, portable, and verifiable on a real Windows/ChemDraw installation.

## Development Setup

1. Fork and clone the repository.
2. Create or activate a Python 3.10-3.13 environment.
3. Install the dependencies required by `skill/chemdraw` and `cdxml-toolkit-community`.
4. Run the baseline validation before making changes.

```powershell
python scripts/validate_distribution.py
python -m pytest skill/chemdraw/scripts -q
.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
```

See the [project guide](../docs/guide.md#development-validation) for native ChemDraw, Office, and network-gated checks.

## Change Rules

- Keep `skill/chemdraw/SKILL.md` a compact task router; put detailed guidance in the existing reference hierarchy.
- Preserve public MCP tool names and response contracts unless the change is intentionally breaking and documented in the pull request.
- Add a failing test before implementing a bug fix or new behavior.
- Use runtime discovery instead of machine-specific usernames or installation paths.
- Do not commit credentials, proprietary binaries, ChemDraw installers, Office files containing private data, or DECIMER model weights.
- Keep repository documentation consolidated. Do not add a standalone document when an existing section is the authoritative home.

## Issues and Pull Requests

Use the repository issue forms for reproducible bugs and focused feature proposals. Include the operating system, Python version, ChemDraw version, exact command, and sanitized error output when relevant.

Pull requests should be small enough to review, explain user-visible behavior changes, and list the validation actually run. Native automation claims require evidence from a licensed ChemDraw installation; network-dependent tests must remain opt-in.

Be respectful and keep technical discussion focused on the work. Harassment, discriminatory language, threats, and disclosure of another person's private information are not acceptable.

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), not in a public issue.
