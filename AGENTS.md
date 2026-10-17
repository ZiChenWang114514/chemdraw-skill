# Repository Instructions

## Scope

Treat `skill/chemdraw/` as the deployable agent Skill and the source of truth for runtime behavior. Root Markdown is intentionally limited to `README.md`, its `README.zh-cn.md` translation, and `AGENTS.md`. Put detailed project guidance and direct translations in `docs/`, and GitHub-only policy in `.github/`; do not create standalone changelog, support, conduct, notice, or release ledgers when an existing authoritative section or GitHub feature is sufficient. Do not add repository-facing documents inside the deployable Skill.

## Skill Design

- Keep `SKILL.md` concise and route detail to one-level references.
- Preserve the progressive path: metadata -> core rules/router -> workflow/domain guide -> generated signatures -> inventory shards.
- Keep exact tool signatures generated in `references/mcp-signatures.md` (`cdx.py regen-signatures`); do not duplicate handwritten signatures elsewhere.
- Keep `scripts/cdx.py` the single entry point: new workflows get a subcommand or run through `cdx.py call` / `cdx.py py`, never a guessed interpreter path. Its bootstrap section must stay standard-library only.
- Keep the Skill client-neutral: no client-specific adapters, branding or configuration writers inside `skill/chemdraw/`.
- Preserve existing public tool names unless a documented breaking release is intentional.
- Keep chemistry grounded: do not invent or hand-edit SMILES, do not silently resolve ambiguous OCSR, and do not overwrite source artifacts.
- For image-recognition tasks, use the DECIMER API directly (`cdx.py decimer`); do not add a separate upload-confirmation question, except once for sources marked unpublished or confidential. Respect explicit local/offline or no-upload requests. Keep the no-upload preflight (`--preflight`) available.

## Changes

- Add or update a failing test before changing behavior.
- Use deterministic parsers/APIs instead of ad hoc text rewriting.
- Keep machine-specific paths, credentials, user data, generated caches, and proprietary test artifacts out of Git.
- Regenerate generated references after changing registry signatures:

```powershell
python .\skill\chemdraw\scripts\cdx.py regen-signatures
python .\skill\chemdraw\scripts\cdx.py py .\skill\chemdraw\scripts\audit_toolkit_interfaces.py --output-dir .\skill\chemdraw\references
```

## Verification

Run portable validation for every change:

```powershell
python .\scripts\validate_distribution.py
```

Run the full Skill suite in the toolkit runtime (`cdx.py py` selects it):

```powershell
python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q
python skill/chemdraw/scripts/cdx.py doctor
```

For native or Office changes, also validate with an activated ChemDraw installation, native PNG rendering, and open/render checks for DOCX/PPTX outputs. Never report those gates as passed when they were skipped.

## Public-facing language

Write public documentation and example captions for readers without conversation history. Do not expose internal experiment identifiers, development stage names, handoff notes, session references or intermediate work logs. Explain technical terms when they help users; retain exact API names, scientific notation, paper compound numbering and necessary compatibility/version requirements. Keep test data identifiers out of homepage artwork and marketing examples.

## Language

Use English for all Skill instructions, references, scripts, and repository documentation except `README.zh-cn.md`. Keep non-ASCII test fixtures as Unicode escapes when needed to preserve test behavior.
