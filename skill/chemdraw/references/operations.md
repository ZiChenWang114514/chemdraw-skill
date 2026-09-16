# Operations

## When To Load

Load for installation, MCP startup, worker timeout, ChemDraw COM, ChemScript, DECIMER, or path-discovery problems.

## Installation Prerequisites

Run `scripts/check_prerequisites.ps1` before a first installation or upgrade. It is read-only: it does not launch ChemDraw, read chemistry files, install packages, or change configuration. Pass the intended MCP runtime with `-Python` and select only the intended features with `-Capabilities`; add `-Json` when a structured support report is useful.

Classify requirements by requested capability:

- Portable CDXML and RDKit work runs on Windows, macOS, and Linux with a 64-bit Python 3.10-3.13 runtime, `cdxml-toolkit-community`, MCP SDK, and an agent with MCP or Python execution access. Python 3.12, `cdxml-toolkit-community==0.7.0a1`, and MCP 1.x/2.x are tested. PowerShell is needed only for the supplied `.ps1` helpers.
- Native rendering, CDX conversion, and ChemDraw cleanup additionally require licensed Windows desktop ChemDraw, .NET Framework 4.8 for current releases, working `ChemDraw.Application` COM registration, and manual activation confirmation.
- Molecular comparison and ChemScript SDK execution additionally require managed and native ChemScript DLLs. Keep the main MCP Python 64-bit; use a separate helper Python when a legacy ChemScript DLL is 32-bit.
- Editable DOCX/PPTX objects require the corresponding desktop Office application. Office is optional for other workflows.
- Local OCSR requires DECIMER model weights. Remote OCSR remains an explicit upload decision and does not replace local prerequisites.

Examples:

```powershell
# Portable CDXML and RDKit only; this is the default selection.
scripts/check_prerequisites.ps1 -Python <path> -Capabilities core

# Licensed Windows workstation with every local native feature.
scripts/check_prerequisites.ps1 -Python <path> `
  -Capabilities core,native,chemscript,office,decimer
```

Install from a repository checkout with `python -m pip install -e ".[dev]"` for portable development, or select the documented extras needed by the requested workflow. Use [agent integration](agent-integration.md) for generic MCP/CLI setup. The optional `scripts/configure_mcp.ps1` adapter configures one client only; it is not a universal installer. After refreshing your agent, select the appropriate verification:

- `health_check.ps1 -SkipNativeChemDraw` for code, package, test, and MCP checks without native applications.
- `health_check.ps1 -SkipOffice` for native ChemDraw PNG and ChemScript checks without Word or PowerPoint.
- `health_check.ps1` for complete native and Office validation.

Do not report a skipped capability as verified. A manual ChemDraw activation check remains required because the prerequisite script intentionally avoids launching licensed software.

## Runtime Discovery

Path precedence is explicit argument, environment variable, active Conda/current Python, PATH/common installation locations, then a legacy machine fallback. Supported variables:

- `CHEMDRAW_MCP_PYTHON`
- `CHEMDRAW_SKILL_ROOT`
- `CHEMDRAW_EXE`
- `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS`
- `CHEMDRAW_MCP_WORKER_INPUT_BYTES`
- `CHEMDRAW_MCP_WORKER_OUTPUT_BYTES`
- `CHEMDRAW_MCP_TRANSPORT`
- `CHEMDRAW_MCP_HTTP_HOST`
- `CHEMDRAW_MCP_HTTP_PORT`
- `CHEMDRAW_MCP_HTTP_API_KEY`
- `CHEMSCRIPT_PYTHON`
- `CHEMSCRIPT_CONFIG_PATH`

Workers also preserve `CHEMSCRIPT_*`, `CONDA_PREFIX`, and `JAVA_HOME` so an
explicitly configured ChemScript or Java runtime remains visible after process
isolation. Credentials and unrelated shell variables are not forwarded.

Run `scripts/runtime_discovery.py` from Python when debugging discovery code. Register the runtime using your client settings. Only the optional Codex adapter uses `scripts/configure_mcp.ps1`; it is read-only unless `-Apply` is supplied.

## Health And Smoke Tests

Run MCP `diagnose_runtime()` for an offline, read-only capability matrix. It reports the Python runtime, installed `cdxml-toolkit` and MCP SDK distribution versions, ChemDraw discovery and COM registration, ChemScript, Java/OPSIN, Office dependencies, DECIMER markers, and live tool count without importing DECIMER or downloading weights. Set `run_chemscript_probe=true` for an independent bridge ping. `run_native_probe=true` runs that ping first and then a temporary CDXML-to-PNG probe, so a ChemDraw COM timeout cannot hide the ChemScript result. Set `run_office_probe=true` for separate temporary PPTX and DOCX ChemDraw OLE probes. ChemScript is capped at 30 seconds, native rendering at 75 seconds, and each Office stage at 60 seconds. Results include stage duration, timeout, and cleanup status. Normal completion never force-terminates ChemDraw; timeout cleanup is limited to newly observed automation processes that can be attributed to the probe.

Run `scripts/health_check.ps1` for the complete repository validation. It consumes the same diagnostic matrix, checks Python packages, generated signatures and inventory, Skill tests, optional client registration (`-CheckCodex`), and, unless skipped, the native and Office probes. Every subprocess is time-bounded.

Run `scripts/smoke_test.py --output-dir <directory>` for name resolution, editable aspirin CDXML, native ChemDraw PNG rendering, and raster validation.

## Streamable HTTP And Metrics

`scripts/mcp_server.py` uses stdio unless `--transport streamable-http` is supplied. HTTP defaults to `127.0.0.1:8029`. Non-loopback listening requires `CHEMDRAW_MCP_HTTP_API_KEY`; wildcard listening additionally requires `--allowed-host`. The key must contain at least 32 UTF-8 bytes, remains in the parent server, and is removed from every worker environment. Use the standard `Authorization: Bearer ...` header.

`/health` is intentionally public and returns only uptime, registered tool count, active worker count, and local ChemDraw scheduler state. `/metrics` uses Prometheus text format and requires the bearer token when HTTP authentication is enabled. It records tool duration, hard timeouts, stable worker failure codes, active workers, and the local ChemDraw queue. It never records arguments, molecule strings, filenames, document content, outputs, or credentials.

The parent process schedules one local ChemDraw COM worker at a time and reports callers waiting there. The named per-user mutex remains active inside each worker to coordinate with another local server process.

## DECIMER

Local image recognition requires official DECIMER weights. Install both with `scripts/install_decimer_models.py`, or select one with `--model standard` / `--model handdrawn`. Each model is downloaded and extracted in isolation, verified against the MD5 published with the [standard model](https://zenodo.org/records/8300489) or [hand-drawn model](https://zenodo.org/records/10781330), assigned a computed SHA-256 receipt, and atomically installed only after its complete marker exists. Missing local weights are a warning and do not block other tools.

Remote recognition uses the configured `DECIMER_API_URL` or the Steinbeck Lab default. It enforces image decoding, request/response size limits, timeout, and explicit `confirm_upload=true`. Relevant limits:

- `DECIMER_API_MAX_IMAGE_BYTES`
- `DECIMER_API_MAX_RESPONSE_BYTES`

Read [decimer-api.md](decimer-api.md) for the HTTP contract.

Expected DECIMER client errors are returned as `ok=false` with the specific error.
HTTP 502/503/504 indicates a gateway/service failure and does not establish a local
ChemDraw or model-installation problem. Check the configured proxy and API
reachability, then verify recovery with an authorized recognition request. See
[DECIMER failure diagnosis](decimer-api.md#diagnosing-failed-requests) for bounded
retries and the distinction between reachability and successful recognition.

## Failure Modes

- MCP startup timeout: verify discovered Python and import `mcp_server.py` directly.
- MCP SDK mismatch: use a supported MCP 1.x or 2.x release. The community runtime supplies the compatibility alias required by its core service.
- Tool timeout: raise the worker timeout only after confirming the operation is legitimately long-running.
- Molecular analysis timeout: `modify_molecule` is limited to 90 seconds because ChemScript naming and decomposition can become expensive for complex fused structures. Trusted SMILES can be drawn directly when no modification is requested.
- Native resource busy: ChemDraw COM operations share a named per-user mutex. Let the active render, conversion, or Office operation finish before retrying; ordinary parsing remains concurrent.
- Worker error id: inspect `%LOCALAPPDATA%\Codex\chemdraw-mcp\logs\worker-<id>.log`; detailed exceptions are intentionally not returned over MCP.
- COM failure: verify registration and run the smoke test. Rendering requests a dedicated automation instance so an already open interactive session is not reused, waits for a stable file, and retries one silent `SaveAs`. Batch rendering reuses one dedicated application instance.
- Native path failure: the Skill copies inputs into an ASCII-only workspace before ChemDraw or Office COM calls, validates native output there, and publishes it transactionally to the requested path. `CHEMDRAW_NATIVE_TEMP` can select an explicit writable ASCII root. `native_ascii_workspace_unavailable`, `native_saveas_silent_failure`, `native_output_missing`, and `native_output_invalid` identify failures before publication.
- `chemdraw_license_unavailable`: ChemDraw COM returned HRESULT `-2147221230` or an equivalent license message. Stop native validation and inspect the installed product license, Python bitness, and COM registration. Do not treat showing a hidden application window as an activation fix, and do not alter an activated interactive installation as a shortcut.
- ChemScript failure: inspect the bridge health output; do not call the private server protocol.
- Config drift: run the config script without `-Apply`, review its proposed block, then apply with automatic backup. Failed writes restore only when the config fingerprint still matches the last known state; concurrent edits are preserved.

## Do Not Use Directly

Do not edit `config.toml` with ad hoc string replacement, launch private ChemScript server commands, or bypass the worker registry.

## Installed Skill Consistency

Use the repository `skill/chemdraw/` as the maintained source. Before and after an upgrade, run `python <skill>/scripts/check_installation.py --source <repository>/skill/chemdraw --installed <installed-skill>`. This read-only check compares SHA-256 hashes, reports missing/modified/extra files, and checks example dependencies and the `figure.cdxml` output contract. It ignores Python bytecode and named test/type-checker caches. Preserve the full previous installation through the repository installer backup before replacing it; additional local files remain recoverable in that backup.
