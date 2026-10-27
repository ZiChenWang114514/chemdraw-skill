# Bundled toolkit (`cdxml_toolkit`)

This folder is the chemistry runtime of the [ChemDraw Skill](../README.md): the `cdxml_toolkit` Python package with its MCP service, isolated tool workers, ChemDraw/ChemScript/Office automation, tests and generated tool reference. The Skill's single entry point, `skill/chemdraw/scripts/cdx.py`, runs every tool from this package.

Users do not install this folder by hand. `python scripts/install.py --runtime --apply` at the repository root builds the shared runtime from it. Start with the [repository README](../README.md) and the [setup guide](../docs/guide.md).

## What it provides

| Area | Practical result |
| --- | --- |
| Chemistry grounding | Resolve names, abbreviations, CAS numbers, formulas and recognized image candidates through databases, ChemScript, OPSIN or DECIMER. |
| Controlled structure work | Compare molecules, apply named transformations, preserve stereochemistry and inspect MCS-based structural differences. |
| ChemDraw output | Draw molecules, clean or merge schemes, convert CDX/CDXML and render native PNG or SVG files. |
| Laboratory figures | Native TLC objects and Rf measurement; editable apparatus assembled from installed ChemDraw templates. |
| Scientific data | Peak picking and selected-region integration for processed 1D NMR; editable numerical plots. No automatic atom assignment or complete FID pipeline. |
| Office workflows | Extract, inspect, replace and batch-embed editable ChemDraw OLE objects in PowerPoint and Word, and fill templates. |
| Experiment workflows | Parse ELN exports, SciFinder RDF, LCMS or NMR reports and assemble structured lab-book material. |
| Agent service | Run through stdio locally or authenticated Streamable HTTP for a trusted remote computer. |

## How the runtime works

- Tool calls run in subprocess workers with hard timeouts and structured errors. Unexpected exceptions are logged to `%LOCALAPPDATA%\chemdraw-skill\logs` (or the temp folder) and returned as an `error_id`, never as raw tracebacks.
- ChemDraw, Word and PowerPoint automation share one serialized native-resource mutex.
- Output-producing tools validate artifacts and refuse to replace existing files unintentionally.
- Metrics record counts, durations, timeouts and failures without tool arguments or molecular content.
- `get_toolkit_capabilities` reports the available local features before an agent chooses a workflow.

## Tool profiles

| Profile | Tools | Focus |
| --- | ---: | --- |
| `full` (default) | 59 | Complete local and remote collection |
| `core` | 16 | Compatible core tools plus capability discovery |
| `office` | 21 | Office inspection, replacement, templates and batch embedding |
| `analysis` | 21 | Experiment discovery, LCMS series, lab books, SciFinder RDF and scientific workflows |
| `chemscript` | 22 | Molecule comparison, controlled ChemScript SDK access and ChemDraw chemical properties |

`codex` is accepted as an alias of `full`, so existing client configurations keep working. The generated [MCP tool reference](docs/mcp-tools.md) and [JSON schema](docs/mcp-schema.json) contain the exact live signatures; CI rejects drift.

## Command line

| Command | Purpose |
| --- | --- |
| `cdxml-mcp` | Complete MCP runtime (`full` profile by default) |
| `cdxml-mcp-core` | Compatible 15-tool core server |
| `cdxml-doctor` | Read-only diagnostics, tests and explicit ChemScript setup (`--no-tests --configure-chemscript`) |
| `cdxml-render` | Render JSON, YAML or compact text to CDXML |
| `cdxml-image` | Render CDXML to PNG or SVG |
| `cdxml-merge` / `cdxml-layout` | Merge schemes or clean reaction layout |
| `cdxml-ole` | Embed editable ChemDraw objects in PPTX or DOCX |
| `cdxml-lcms` / `cdxml-nmr` | Parse instrument reports |
| `cdxml-mcp-docs` | Regenerate the Markdown and JSON tool references |

Inside the Skill, prefer `cdx.py call TOOL` or `cdx.py py -m MODULE`; both select the runtime interpreter. The scheme renderer accepts YAML, reaction JSON and a compact text syntax described in the [showcase catalog](experiments/scheme_dsl/showcase/INDEX.md). The [developer reference](docs/agent-reference.md) describes the core tools, package layout and parser rules.

## Streamable HTTP

Stdio is the local default. An activated Windows workstation can serve a trusted remote computer:

```powershell
$env:CHEMDRAW_MCP_HTTP_API_KEY = "generate-a-long-random-value"
cdxml-mcp --transport streamable-http --host 0.0.0.0 --port 8029 `
  --allowed-host chemdraw-host.example:8029 `
  --allowed-origin https://trusted-client.example
```

Remote binding requires a bearer key and an explicit host list. `/health` contains no molecule data; `/metrics` requires authentication when the server is remotely reachable. The built-in listener has no TLS; use an encrypted tunnel or HTTPS reverse proxy.

## Development

Requires 64-bit Python 3.10–3.13. From this folder:

```powershell
python -m pip install -e ".[dev,windows,office,analysis,image,scientific]"
python -m pytest -m "not network" -q
python -m cdxml_toolkit.mcp_runtime.generate_reference --markdown docs/mcp-tools.md --json docs/mcp-schema.json
python -m build
python -m twine check dist/*
```

Hosted CI runs these on Python 3.10–3.13 with MCP SDK 1.x and 2.x. Native ChemDraw, ChemScript, Word and PowerPoint checks run on a licensed Windows workstation (`.github/workflows/native-validate.yml` at the repository root). See the [contribution guide](../.github/contributing.md), the [security policy](../.github/SECURITY.md) and the [maintenance guide](docs/maintenance.md).

## Provenance and license

The package started as Hiu Fung Kevin Lee's [`cdxml-toolkit`](https://github.com/leehiufung911/cdxml-toolkit), was continued as the community project `cdxml-toolkit-community`, and is now maintained inside this repository. Its complete Git history was imported with `git subtree`. The original commits stored files at their old repository root, so a path-filtered `git log -- toolkit` does not list them; `git log --oneline "$(git log --format=%H -1 --grep=git-subtree-dir)^2"` does. The distribution name `cdxml-toolkit-community` and the import package `cdxml_toolkit` are unchanged for compatibility.

- Original author: Hiu Fung Kevin Lee ([@leehiufung911](https://github.com/leehiufung911))
- Maintainer: [ZiChenWang114514](https://github.com/ZiChenWang114514)
- License: [MIT](LICENSE), with third-party data notices in [NOTICE.md](NOTICE.md)

The original project was directed by Hiu Fung Kevin Lee, a PhD organic chemist, and documented as built and tested with Claude Code (Opus 4.6).
