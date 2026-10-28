# Repository Instructions

## Scope

Treat `skill/chemdraw/` as the deployable agent Skill and the source of truth for Skill behavior, and `toolkit/` as the bundled `cdxml_toolkit` runtime it drives (its own `toolkit/AGENTS.md` adds toolkit rules). The toolkit's history was imported with `git subtree`; keep its `LICENSE` and `NOTICE.md`, and sync upstream as described in `toolkit/docs/maintenance.md`. Root Markdown is intentionally limited to `README.md`, its `README.zh-cn.md` translation, and `AGENTS.md`. Put detailed project guidance and direct translations in `docs/`, toolkit developer documentation in `toolkit/docs/`, GitHub-only policy in the root `.github/`, and the GitHub Pages landing page in `site/` (see `docs/website.md`); do not create standalone changelog, support, conduct, notice, or release ledgers when an existing authoritative section or GitHub feature is sufficient. Do not add repository-facing documents inside the deployable Skill.

## Skill Design

- Keep `SKILL.md` concise and route detail to one-level references.
- Preserve the progressive path: metadata -> core rules/router -> workflow/domain guide -> generated signatures -> inventory shards.
- Keep exact tool signatures generated in `references/mcp-signatures.md` (`cdx.py regen-signatures`); do not duplicate handwritten signatures elsewhere.
- Keep `scripts/cdx.py` the single entry point: new workflows get a subcommand or run through `cdx.py call` / `cdx.py py`, never a guessed interpreter path. Its bootstrap section must stay standard-library only.
- Keep the Skill client-neutral: no client-specific adapters, branding or configuration writers inside `skill/chemdraw/`. Agent names appear only where users choose an install target (`scripts/install.py`, `references/agent-integration.md`, README and guide).
- Keep `scripts/install.py` and the `cdx.py` bootstrap standard-library only and portable across Windows, macOS and Linux. New agent presets go into `AGENTS` in `install.py` and the table in `agent-integration.md`.
- Preserve existing public tool names unless a documented breaking release is intentional.
- Keep chemistry grounded: do not invent or hand-edit SMILES, do not silently resolve ambiguous OCSR, and do not overwrite source artifacts.
- For image-recognition tasks, use the DECIMER API directly (`cdx.py decimer`); do not add a separate upload-confirmation question, except once for sources marked unpublished or confidential. Respect explicit local/offline or no-upload requests. Keep the no-upload preflight (`--preflight`) available.

## Changes

- Add or update a failing test before changing behavior.
- Use deterministic parsers/APIs instead of ad hoc text rewriting.
- Keep machine-specific paths, credentials, user data, generated caches, and proprietary test artifacts out of Git.
- The ChemDraw interface pages (`interface-chemscript.md`, `interface-com.md`, `interface-cdxml-model.md`, `interface-menu.md`, `recipes-chemdraw.md` and their shards) are generated from `toolkit/cdxml_toolkit/catalog/data`; rebuild a catalog with `python -m cdxml_toolkit.catalog <layer>` on a machine with ChemDraw, edit tiers only in `classification.json` or by running a recipe, and never hand-edit the pages.
- Regenerate generated references after changing registry signatures or catalog data:

```powershell
python .\skill\chemdraw\scripts\cdx.py regen-signatures
python .\skill\chemdraw\scripts\cdx.py py .\skill\chemdraw\scripts\audit_toolkit_interfaces.py --output-dir .\skill\chemdraw\references
python .\skill\chemdraw\scripts\cdx.py regen-catalog
```

## Verification

Run portable validation for every change:

```powershell
python .\scripts\validate_distribution.py
```

Run the full Skill suite in the toolkit runtime (`cdx.py py` selects it; `scripts/install.py --runtime-only --apply` builds it and records it for this checkout in the ignored `skill/chemdraw/runtime.local.json`, otherwise set `CHEMDRAW_MCP_PYTHON`):

```powershell
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py doctor
```

For changes under `toolkit/`, also run its suite with the runtime Python from inside `toolkit/` (the checkout code is imported first), then rebuild the runtime with `scripts/install.py --runtime-only --apply` (it leaves installed Skill copies alone; add `--agent ... --runtime` only when the installed copies should be replaced too) before native or Office checks:

```powershell
cd toolkit; python -m pytest -m "not network" -q
```

On macOS the toolkit suite never starts ChemDraw or Office: `tests/conftest.py` hides ChemDraw and blocks `open`/`osascript`, so ChemScript-marked tests skip. Set `CDXML_LIVE_CHEMDRAW=1` only for a targeted live check (`-k`), after telling the user: the live suite restarts their ChemDraw repeatedly and runs for over an hour.

For native or Office changes, also validate with an activated ChemDraw installation, native PNG rendering, and open/render checks for DOCX/PPTX outputs. Never report those gates as passed when they were skipped.

## Public-facing language

Write public documentation and example captions for readers without conversation history. Do not expose internal experiment identifiers, development stage names, handoff notes, session references or intermediate work logs. Explain technical terms when they help users; retain exact API names, scientific notation, paper compound numbering and necessary compatibility/version requirements. Keep test data identifiers out of homepage artwork and marketing examples.

## Language

Use English for all Skill instructions, references, scripts, and repository documentation except the Chinese translations `README.zh-cn.md`, `docs/guide.zh-cn.md` and `docs/zh-cn.md`, which must be real translations kept in step with their English counterparts (`docs/zh-cn.md` is a short Chinese quick start that follows the README Quick start and has no separate English page), and the Chinese landing pages `site/index.html` and `site/404.html` (`site/en/index.html` is their English counterpart). Keep non-ASCII test fixtures as Unicode escapes when needed to preserve test behavior.
