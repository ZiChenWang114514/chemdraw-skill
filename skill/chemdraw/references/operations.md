# Operations

## When To Load

Load for installation, upgrade, worker timeout, ChemDraw COM, ChemDraw for macOS, ChemScript, DECIMER, or path problems. Agent setup and the command reference are in [agent integration](agent-integration.md).

## Health check

```bash
cdx.py doctor                 # toolkit/Python versions, missing extras, signature drift, installation manifest, capability matrix
cdx.py doctor --paths         # also worker-log folder, native mutex name, native temp root, ChemScript path
cdx.py doctor --native        # + ChemScript ping and a temporary CDXML -> PNG render through ChemDraw (COM or macOS)
cdx.py doctor --office        # + PPTX and DOCX ChemDraw-OLE embedding probes (packages built and validated; Office is not opened)
cdx.py doctor --full          # include the complete diagnose_runtime() result
```

The report is read-only. A skipped probe is not a verified capability. ChemScript is capped at 30 s, native rendering at 75 s and each Office stage at 60 s; timeout cleanup touches only automation processes started by the probe. Exit code 1 means signature drift or a mismatch against `manifest.json`.

`cdx.py py <skill>/scripts/smoke_test.py --output-dir NEW_DIR` runs an end-to-end check: name resolution, editable aspirin CDXML, native PNG and raster validation.

## Requirements by capability

- Portable CDXML and RDKit work: 64-bit Python 3.10–3.13 with the bundled `cdxml_toolkit` runtime (3.14 and newer are not supported by the toolkit yet; the installer picks an older interpreter or takes `--python`). The pinned source is `runtime.json` (`repository`, `commit`, `toolkit_version`).
- Native rendering, CDX conversion and ChemDraw cleanup: licensed desktop ChemDraw. Windows: .NET Framework 4.8 and a working `ChemDraw.Application` COM registration. macOS: ChemDraw for macOS in `/Applications` and the Automation permission ([macOS](#macos)). Confirm activation manually once.
- Molecular comparison and ChemScript: Windows uses the managed and native ChemScript DLLs (`pythonnet`); keep the main runtime 64-bit, and a legacy 32-bit ChemScript needs a separate helper Python (`CHEMSCRIPT_PYTHON`). macOS has no ChemScript; the same commands run on ChemDraw for macOS, OPSIN and RDKit. The raw ChemScript SDK tools are Windows-only.
- Editable DOCX/PPTX objects: building, inspecting, replacing and extracting them needs only ChemDraw; PDF previews need desktop Word/PowerPoint (activated Microsoft 365 on macOS).
- Recognition: the remote DECIMER API needs no local weights. Local OCSR needs DECIMER weights (below).

Optional dependency groups (`pip` extras) and what fails without them:

| Extra | Packages | Needed for |
| --- | --- | --- |
| `publication` | openpyxl | XLSX tables in data-driven figures |
| `scientific` | numpy, scipy, matplotlib, nmrglue | NMR, plots, `assets/scientific` examples |
| `office` | python-docx, python-pptx, olefile (+ pywin32 on Windows) | Office extraction, embedding, replacement |
| `analysis` | pdfplumber, pymupdf | LCMS/NMR PDF reports |
| `image` | opencv-python, pytesseract | image segmentation helpers |
| `chemscript` | pythonnet (Windows); py2opsin (macOS) | ChemScript bridge |
| `decimer` | tensorflow, decimer | local OCSR only |

## Install or upgrade

From a repository checkout, on any OS (preview first, then `--apply`):

```bash
python scripts/install.py --agent <name> --runtime              # proposal
python scripts/install.py --agent <name> --runtime --apply      # install; add --python <3.10-3.13> if none is found
python scripts/install.py --destination <other skills folder>/chemdraw --apply
python scripts/install.py --runtime --opsin --apply             # also download the OPSIN JAR (SHA-256 verified)
```

The installer stages and verifies each copy, moves a previous installation to the shared backup folder, restores it on failure, then (with `--runtime`) creates or reuses the shared venv and installs the pinned toolkit with every extra that applies to the OS. It writes `manifest.json` last. Agent presets, folders and the runtime search order are in [agent integration](agent-integration.md).

A manual runtime works too; point `CHEMDRAW_MCP_PYTHON` at it if it is not in a searched location:

```bash
python3 -m venv <venv>
<venv>/bin/python <skill>/scripts/install_runtime.py --extras publication scientific
```

`install_runtime.py` builds from the repository's `toolkit/` folder when the Skill sits in a checkout, otherwise from the exact commit in `runtime.json`; `--toolkit-path` selects another toolkit source folder and `--print-requirement` only prints the requirement. Never upgrade the runtime unasked. After a toolkit change:

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
- `CHEMDRAW_EXE` — explicit ChemDraw executable (on macOS the binary inside the `.app` or the bundle; otherwise `/Applications/ChemDraw*.app` is found)
- `OPSIN_JAR`, `CDXML_TOOLKIT_OPSIN_JAR` — explicit OPSIN JAR (otherwise the one `install.py --opsin` placed beside the shared venv)
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

- `cdx.py: no working cdxml-toolkit runtime found`: install one (`scripts/install.py --runtime --apply`) or set `CHEMDRAW_MCP_PYTHON` to the runtime interpreter. A venv is skipped when its interpreter no longer starts (base Python removed or blocked); re-run the installer to rebuild it.
- Tool timeout: raise `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS` only after confirming the operation is legitimately long-running. `modify_molecule` is limited to 90 s because ChemScript naming and decomposition can be expensive for fused systems; trusted SMILES can be drawn directly when no modification is needed.
- Native resource busy: ChemDraw COM operations share one per-user mutex (`cdx.py doctor --paths` shows its name). Let the active render, conversion or Office operation finish; ordinary parsing stays concurrent. Do not start a second COM session to bypass it.
- `tool_execution_failed` with an `error_id`: read `worker-<id>.log` in the folder printed by `cdx.py doctor --paths`. Detailed exceptions are deliberately kept out of results.
- COM failure: run `cdx.py doctor --native`. Rendering uses a dedicated automation instance (an open interactive ChemDraw is not reused), waits for a stable file and retries one silent `SaveAs`.
- Native path failure: inputs are copied into an ASCII-only workspace before COM calls and published transactionally. `native_ascii_workspace_unavailable`, `native_saveas_silent_failure`, `native_output_missing` and `native_output_invalid` identify failures before publication. Set `CHEMDRAW_NATIVE_TEMP` if the default temp path is unusable.
- `chemdraw_license_unavailable` (HRESULT `-2147221230`): stop native validation and check the product license, Python bitness and COM registration. Showing a hidden window is not an activation fix.
- ChemScript failure: `cdx.py doctor --chemscript`; for one file `cdx.py chemscript-info FILE`. Do not call the private bridge server protocol.
- macOS failures (`chemdraw_automation_not_authorized`, `chemdraw_in_use`, `office_not_ready`, ...): see [macOS](#macos).
- Rendered PNG unchanged after an edit: an old PNG with the same name blocked the write. `cdx.py render` removes it first; other routes must write a new name.

## macOS

ChemDraw for macOS is driven through AppleScript (`osascript`) instead of COM. The tools, arguments and outputs are the same as on Windows; the differences below are what an agent may see.

- **Permission.** The first native call asks macOS to let the terminal or agent app control ChemDraw (and Word/PowerPoint for PDF previews). If it was denied, the call fails with `chemdraw_automation_not_authorized` (`office_automation_not_authorized`); allow the app under System Settings > Privacy & Security > Automation. Do not loop retries.
- **Hidden instance.** The toolkit launches ChemDraw in the background without a window (`open -g -j`) and quits it afterwards. It records the instances it starts in `~/Library/Caches/chemdraw-skill/launched` and terminates those, and only those, when their owning process died or a quit was blocked by a dialog. A ChemDraw the user opened is never quit or killed. A window may flash briefly while ChemDraw opens a document.
- **Fonts.** ChemDraw for macOS stops on a "font is not available" alert when a document names a missing Windows font. Staged copies replace missing fonts with installed equivalents (SimSun and its Chinese name → Songti SC, SimHei → Heiti SC, Microsoft YaHei → PingFang SC, Calibri → Helvetica Neue, ...); the source file is not changed.
- **ChemScript.** There is no ChemScript for macOS. Names → structures use OPSIN first and ChemDraw's Name to Structure as fallback; structure → name, cleanup and conversion use ChemDraw; formula, mass, substructure, MCS and overlay use RDKit. Results can differ from ChemScript in naming style. A name neither OPSIN nor ChemDraw recognizes costs about 6 s, because ChemDraw's alert is cleared by restarting the hidden instance; the rejection is cached for the session, so repeats fail at once. `execute_chemscript_sdk` and `inspect_chemscript_sdk` run on an emulation of the ChemScript members the toolkit uses: `StructureData` (`LoadData`, `LoadFile`, `ReadFile`, `MimeTypes`, `Formula`, `ChemicalName`, `WriteData`, `WriteFile`, `CleanupStructure`, `Overlay`, `ContainsSubstructure`, `AtomByAtomSearch`, `Atoms`, `Bonds`), `ReactionData` (`LoadData`, `LoadFile`, `Reactants`, `Products`, `Formula`, `WriteData`, `WriteFile`) and `LargestCommonSubstructure` (`Compute`, `AtomMapM1`, `AtomMapM2`). Programs written against these run unchanged; `inspect_chemscript_sdk` lists exactly these members, and any other type or member is refused.
- **Formats.** ChemDraw for macOS saves CDX, CDXML, PNG (300 dpi), SVG, PDF, TIFF, GIF, JPEG, BMP, EPS, molfile, SDfile, RXN, CML, SKC and TGF. It cannot write EMF; the toolkit converts ChemDraw's SVG export into a vector EMF (paths and text), so OLE previews in DOCX/PPTX and `.emf` outputs stay vector. Drawings whose SVG uses features the converter does not reproduce (arcs, partial transparency, rotated text) fall back to a bitmap EMF wrapping the 300 dpi PNG. PPTX objects also carry the picture in the `mc:Choice` branch so Quick Look and PowerPoint without an OLE server show it.
- **Office.** Building, inspecting, replacing and extracting ChemDraw objects need only ChemDraw. PDF previews of the result run Word/PowerPoint for macOS on a copy in the Office group container; Office must have been started once, signed in and activated. Otherwise the call fails with `office_not_ready` after its timeout: activate Office, or pass `render_pdf_preview=False` where the tool offers it. Office for macOS cannot open embedded ChemDraw objects by double-click. Edit one with `cdx.py office-edit DOCUMENT [--object N]`: it extracts the drawing to `<document>_chemdraw_edit/object_NNN.cdxml` and opens it in ChemDraw; after saving there, `cdx.py office-edit DOCUMENT --finish [--output NEW]` writes a new document with the object replaced, its preview regenerated and its frame resized to the new drawing (`replace_chemdraw_objects_in_office(resize_frames=True)`). The input document is not changed.
- **Captions.** ChemDraw for macOS turns a free caption that reads like a formula (`MeOH`, `Et3N`) into a structure fragment during Clean Up and other menu commands. The toolkit marks captions as plain text in the staged copy for the duration of the command and removes the mark from the output, so reaction roles and caption text are unchanged.
- **ELN cleanup.** `cleanup_eln_cdx` applies the ACS Document 1996 settings through CDXML (bond length, Arial 10 pt bold captions) before ChemDraw's Clean Up Structure/Reaction, because ChemDraw for macOS cannot apply style sheets from AppleScript. A custom `.cds` `style_path` is read directly (bond length, angles, line widths, label and caption fonts) and applied the same way. ChemDraw opens `.cds`/`.cts` files as untitled stationery, so the toolkit never opens them in ChemDraw (`native_format_unsupported`).
- **Errors.** `chemdraw_not_found` (install ChemDraw in `/Applications` or set `CHEMDRAW_EXE`), `chemdraw_in_use` (name conversion only runs in a ChemDraw the toolkit started; close the user's ChemDraw or retry later), `native_timeout` (a dialog is open in ChemDraw), `chemdraw_not_running`, `native_format_unsupported`, `chemdraw_license_unavailable`.

## Remote HTTP (only when asked)

`cdx.py py -m cdxml_toolkit.mcp_runtime --transport streamable-http` serves the tools over HTTP, default `127.0.0.1:8029`. Non-loopback listening requires `CHEMDRAW_MCP_HTTP_API_KEY` (at least 32 bytes, bearer header); wildcard hosts additionally need `--allowed-host`. `/health` is public and content-free; `/metrics` (Prometheus) needs the token when authentication is on and never records arguments, molecules, filenames or outputs. The server schedules one ChemDraw COM worker at a time; different ports do not bypass the mutex. Related variables: `CHEMDRAW_MCP_TRANSPORT`, `CHEMDRAW_MCP_HTTP_HOST`, `CHEMDRAW_MCP_HTTP_PORT`, `CHEMDRAW_MCP_HTTP_API_KEY`.

## Do Not Use Directly

Do not launch private ChemScript server commands, call ChemDraw COM outside the worker, or bypass the tool registry.
