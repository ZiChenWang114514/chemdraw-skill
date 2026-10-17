# Operations

## When To Load

Load for installation, upgrade, worker timeout, ChemDraw COM, ChemScript, DECIMER, or path problems. Agent setup and the command reference are in [agent integration](agent-integration.md).

## Health check

```bash
cdx.py doctor                 # toolkit/Python versions, missing extras, signature drift, installation manifest, capability matrix
cdx.py doctor --paths         # also worker-log folder, native mutex name, native temp root, ChemScript path
cdx.py doctor --native        # + ChemScript ping and a temporary CDXML -> PNG render through ChemDraw COM
cdx.py doctor --office        # + Word and PowerPoint ChemDraw-OLE probes
cdx.py doctor --full          # include the complete diagnose_runtime() result
```

The report is read-only. A skipped probe is not a verified capability. ChemScript is capped at 30 s, native rendering at 75 s and each Office stage at 60 s; timeout cleanup touches only automation processes started by the probe. Exit code 1 means signature drift or a mismatch against `manifest.json`.

`cdx.py py <skill>/scripts/smoke_test.py --output-dir NEW_DIR` runs an end-to-end check: name resolution, editable aspirin CDXML, native PNG and raster validation.

## Requirements by capability

- Portable CDXML and RDKit work: 64-bit Python 3.10–3.13 with `cdxml-toolkit-community`. The pinned source is `runtime.json` (`repository`, `commit`, `toolkit_version`).
- Native rendering, CDX conversion and ChemDraw cleanup: licensed desktop ChemDraw, .NET Framework 4.8, working `ChemDraw.Application` COM registration. Confirm activation manually once.
- Molecular comparison and ChemScript SDK: managed and native ChemScript DLLs (`pythonnet`). Keep the main runtime 64-bit; a legacy 32-bit ChemScript needs a separate helper Python (`CHEMSCRIPT_PYTHON`).
- Editable DOCX/PPTX objects: desktop Word/PowerPoint.
- Recognition: the remote DECIMER API needs no local weights. Local OCSR needs DECIMER weights (below).

Optional dependency groups (`pip` extras) and what fails without them:

| Extra | Packages | Needed for |
| --- | --- | --- |
| `publication` | openpyxl | XLSX tables in data-driven figures |
| `scientific` | numpy, scipy, matplotlib, nmrglue | NMR, plots, `assets/scientific` examples |
| `office` | pywin32, python-docx, python-pptx, olefile | Office extraction, embedding, replacement |
| `analysis` | pdfplumber, pymupdf | LCMS/NMR PDF reports |
| `image` | opencv-python, pytesseract | image segmentation helpers |
| `chemscript` | pythonnet | ChemScript bridge |
| `decimer` | tensorflow, decimer | local OCSR only |

## Install or upgrade

From a repository checkout, on any OS (preview first, then `--apply`):

```bash
python scripts/install.py --agent <name> --runtime              # proposal
python scripts/install.py --agent <name> --runtime --apply      # install; add --python <3.10-3.13> if none is found
python scripts/install.py --destination <other skills folder>/chemdraw --apply
```

The installer stages and verifies each copy, moves a previous installation to the shared backup folder, restores it on failure, then (with `--runtime`) creates or reuses the shared venv and installs the pinned toolkit with every extra that applies to the OS. It writes `manifest.json` last. Agent presets, folders and the runtime search order are in [agent integration](agent-integration.md).

A manual runtime works too; point `CHEMDRAW_MCP_PYTHON` at it if it is not in a searched location:

```bash
python3 -m venv <venv>
<venv>/bin/python <skill>/scripts/install_runtime.py --extras publication scientific
```

`install_runtime.py` installs exactly the commit in `runtime.json`; `--toolkit-path` selects a local checkout for development and `--print-requirement` only prints the requirement. Never upgrade the runtime unasked. After a toolkit change:

```bash
cdx.py regen-signatures
cdx.py py -m pip install pytest
cdx.py py -m pytest <skill>/tests -q
```

## Installed skill consistency

`manifest.json` (written by the installer) lists a SHA-256 per file; text files are hashed after CRLF→LF normalization, so Git `autocrlf` checkouts do not show false modifications. `cdx.py doctor` reports drift; for details:

```bash
cdx.py py <skill>/scripts/check_installation.py                        # installed copy vs its manifest
cdx.py py <skill>/scripts/check_installation.py --source <repo>/skill/chemdraw   # installed copy vs a checkout
cdx.py py <skill>/scripts/check_installation.py --write-manifest       # accept intended local edits
```

## Environment variables

Runtime selection and workers:

- `CHEMDRAW_MCP_PYTHON` — runtime interpreter for `cdx.py` (otherwise `runtime.local.json`, a sibling `chemdraw-venv`, the shared venv, then a conda env named `cdxml`)
- `CHEMDRAW_EXE` — explicit ChemDraw executable
- `CHEMDRAW_NATIVE_TEMP` — writable ASCII-only root for native staging
- `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS`, `CHEMDRAW_MCP_WORKER_INPUT_BYTES`, `CHEMDRAW_MCP_WORKER_OUTPUT_BYTES`
- `CHEMSCRIPT_PYTHON`, `CHEMSCRIPT_CONFIG_PATH`

DECIMER (see [decimer-api.md](decimer-api.md)):

- `DECIMER_API_URL` — custom endpoint; requires a matching `approved_origin`
- `DECIMER_API_MAX_IMAGE_BYTES` — default 25 MiB
- `DECIMER_API_MAX_IMAGE_PIXELS` — default 40,000,000
- `DECIMER_API_MAX_RESPONSE_BYTES` — default 2 MiB

Workers also keep `CHEMSCRIPT_*`, `CONDA_PREFIX` and `JAVA_HOME`. Credentials and unrelated shell variables are not forwarded. (`CHEMDRAW_MCP_*` names are the toolkit's own identifiers and apply equally to `cdx.py`.)

## DECIMER weights

Local recognition requires official DECIMER weights: `cdx.py py -m cdxml_toolkit.mcp_runtime.install_decimer_models` (both) or `--model standard` / `--model handdrawn`. Archives come from the [standard](https://zenodo.org/records/8300489) and [hand-drawn](https://zenodo.org/records/10781330) model records and are checksum-verified on install. Missing weights are a warning only.

HTTP 502/503/504 from the remote API indicates a gateway or service failure, not a local ChemDraw or model problem. Follow [DECIMER failure diagnosis](decimer-api.md#diagnosing-failed-requests).

## Failure Modes

- `cdx.py: no cdxml-toolkit runtime found`: install one (`scripts/install.py --runtime --apply`) or set `CHEMDRAW_MCP_PYTHON` to the runtime interpreter.
- Tool timeout: raise `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS` only after confirming the operation is legitimately long-running. `modify_molecule` is limited to 90 s because ChemScript naming and decomposition can be expensive for fused systems; trusted SMILES can be drawn directly when no modification is needed.
- Native resource busy: ChemDraw COM operations share one per-user mutex (`cdx.py doctor --paths` shows its name). Let the active render, conversion or Office operation finish; ordinary parsing stays concurrent. Do not start a second COM session to bypass it.
- `tool_execution_failed` with an `error_id`: read `worker-<id>.log` in the folder printed by `cdx.py doctor --paths`. Detailed exceptions are deliberately kept out of results.
- COM failure: run `cdx.py doctor --native`. Rendering uses a dedicated automation instance (an open interactive ChemDraw is not reused), waits for a stable file and retries one silent `SaveAs`.
- Native path failure: inputs are copied into an ASCII-only workspace before COM calls and published transactionally. `native_ascii_workspace_unavailable`, `native_saveas_silent_failure`, `native_output_missing` and `native_output_invalid` identify failures before publication. Set `CHEMDRAW_NATIVE_TEMP` if the default temp path is unusable.
- `chemdraw_license_unavailable` (HRESULT `-2147221230`): stop native validation and check the product license, Python bitness and COM registration. Showing a hidden window is not an activation fix.
- ChemScript failure: `cdx.py doctor --chemscript`; for one file `cdx.py chemscript-info FILE`. Do not call the private bridge server protocol.
- Rendered PNG unchanged after an edit: an old PNG with the same name blocked the write. `cdx.py render` removes it first; other routes must write a new name.

## Remote HTTP (only when asked)

`cdx.py py -m cdxml_toolkit.mcp_runtime --transport streamable-http` serves the tools over HTTP, default `127.0.0.1:8029`. Non-loopback listening requires `CHEMDRAW_MCP_HTTP_API_KEY` (at least 32 bytes, bearer header); wildcard hosts additionally need `--allowed-host`. `/health` is public and content-free; `/metrics` (Prometheus) needs the token when authentication is on and never records arguments, molecules, filenames or outputs. The server schedules one ChemDraw COM worker at a time; different ports do not bypass the mutex. Related variables: `CHEMDRAW_MCP_TRANSPORT`, `CHEMDRAW_MCP_HTTP_HOST`, `CHEMDRAW_MCP_HTTP_PORT`, `CHEMDRAW_MCP_HTTP_API_KEY`.

## Do Not Use Directly

Do not launch private ChemScript server commands, call ChemDraw COM outside the worker, or bypass the tool registry.
