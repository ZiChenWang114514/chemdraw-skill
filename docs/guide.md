# Project Guide

[简体中文](guide.zh-cn.md)

This is the single detailed guide for installing, understanding, testing, and operating the project. The root README stays intentionally short.

## Installation

### Choose the required feature set

| Feature | Additional requirement |
| --- | --- |
| CDXML parsing, name resolution, and ordinary drawing | Codex, Python runtime, `cdxml-toolkit-community`, and MCP SDK |
| Native PNG rendering, CDX conversion, and ChemDraw cleanup | Licensed Windows desktop ChemDraw with working COM registration |
| Molecule comparison and full ChemScript SDK access | Managed and native ChemScript DLLs; older 32-bit releases may need a separate helper Python |
| Editable ChemDraw objects in DOCX or PPTX | The corresponding Microsoft Word or PowerPoint desktop application |
| Offline image recognition | DECIMER model weights and additional memory, disk space, and download time |
| Access from another computer | A configured Windows server plus authenticated Streamable HTTP over an encrypted network |

Office, DECIMER, and the ChemScript helper environment are optional until a workflow needs them.

### Host prerequisites

- Portable CDXML and RDKit workflows run on Windows, macOS, and Linux. Native ChemDraw COM, ChemScript, and editable Office objects require a 64-bit Windows 10 or Windows 11 host.
- Windows PowerShell 5.1 or PowerShell 7 is required for the supplied installer and checker. Portable package commands can run in the platform's usual shell.
- A working `codex` command and a completed Codex sign-in. Follow the [official Codex CLI guide](https://developers.openai.com/codex/cli).
- A licensed Windows desktop ChemDraw installation is needed only for native features. Browser-only ChemDraw does not expose COM or ChemScript. ChemDraw 22.0 is tested; review the [current Revvity system requirements](https://support.revvitysignals.com/hc/en-us/articles/43424307511572-ChemDraw-What-are-the-System-requirements-for-ChemDraw-ChemOffice) for the installed release.
- A 64-bit Python 3.10-3.13 runtime. Python 3.12 is tested and a dedicated Conda environment is recommended.
- [Git](https://git-scm.com/downloads), or a GitHub ZIP download if Git is unavailable.
- At least 10 GiB free disk space and 8 GiB RAM are practical minimums for the complete Python environment. Local DECIMER use benefits from 16 GiB RAM and additional free space.
- Initial network access for the repository and Python dependencies. Local DECIMER adds a separate model download.

The tested runtime is `cdxml-toolkit-community==0.7.0a1` with MCP SDK 1.x or 2.x. Keep the main MCP environment 64-bit. When an older ChemScript DLL is 32-bit, configure a separate helper environment instead of changing the main runtime.

### First-Time Windows Setup

1. Install and activate desktop ChemDraw. Open it manually, create and save a small document, then close the application. The project does not install or alter product licensing.
2. Install Codex with the current official Windows command below, run `codex --version`, start `codex`, and complete sign-in. On a managed computer that blocks downloaded scripts, ask the administrator to use the Windows method in the [official Codex CLI guide](https://developers.openai.com/codex/cli) instead of disabling organizational security controls.

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

3. Install [64-bit Miniconda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/windows.html) and Git. Open **Anaconda PowerShell Prompt** so `conda` is available.
4. Clone the repository and create the isolated runtime:

```powershell
Set-Location "$HOME\Documents"
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
Set-Location .\codex-chemdraw-skill

conda create -n cdxml python=3.12 pip -y
conda activate cdxml
python -m pip install --upgrade pip
python -m pip install "cdxml-toolkit-community[windows,office,chemscript] @ git+https://github.com/ZiChenWang114514/cdxml-toolkit-community.git@57db286ea4fa1c74a524e7a329dd5ba3f39dc21e"
python -m pip check
python -c "import cdxml_toolkit, mcp, rdkit, win32com.client; print('Python runtime OK')"
$python = (python -c "import sys; print(sys.executable)").Trim()
```

Package installation includes scientific, Office-file processing, PDF, image, and machine-learning dependencies and can take considerably longer than a small Python package. These Python libraries do not install Microsoft Word or PowerPoint; editable Office-object workflows still require the desktop application.

Run the read-only prerequisite report before installation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\check_prerequisites.ps1 -Python $python -Capabilities core,native,chemscript,office
```

`PASS` satisfies a check, `WARN` identifies an optional or manual item, `FAIL` requires attention, and `SKIP` means that no conclusion was obtained. The checker does not launch ChemDraw, inspect molecule files, or change system configuration. Add `-Json` for a machine-readable report. Use `-Capabilities core` for a portable-only installation and `-SkipPythonPackages` only for an early host check before package installation.

If molecule comparison or ChemScript SDK tools are required, configure and ping the bridge:

```powershell
& $python -m cdxml_toolkit.chemdraw.chemscript_bridge configure
& $python -m cdxml_toolkit.chemdraw.chemscript_bridge ping
```

When a 32-bit ChemScript installation has no compatible helper Python, activate `cdxml` and run `cdxml-doctor --no-tests`, then follow its dedicated helper-environment instructions. Keep the main `cdxml` environment 64-bit.

Preview the Skill installation first, inspect the reported Python and destination, then apply it:

```powershell
& .\scripts\install.ps1 -Python $python -ConfigureMcp
& .\scripts\install.ps1 -Python $python -Apply -ConfigureMcp
```

Without `-Apply`, the installer reports its proposed paths without modifying them. With `-Apply`, it preserves the existing Skill under `$HOME\.codex\backups\skills\chemdraw` before installing to `$HOME\.codex\skills\chemdraw`. `-ConfigureMcp` also preserves and updates `$HOME\.codex\config.toml`.

Restart Codex and verify registration:

```powershell
codex mcp get cdxml-toolkit --json
& "$HOME\.codex\skills\chemdraw\scripts\check_prerequisites.ps1" -Python $python -Capabilities core,native,chemscript,office
```

Choose the health check that matches the installed applications:

```powershell
# Portable code, package, test, and MCP checks; no native application probes.
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python -SkipNativeChemDraw

# Native ChemDraw PNG and ChemScript checks without Word or PowerPoint.
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python -SkipOffice

# Full native, ChemScript, PowerPoint, and Word validation.
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python
```

Close manually opened ChemDraw and Office applications before native probes. A selected health check succeeds only when it ends with `ChemDraw/Codex integration: OK`.

### Installation Troubleshooting

- `git`, `conda`, or `codex` is not recognized: reopen PowerShell after installation and confirm the correct user account. Use Anaconda PowerShell Prompt for Conda.
- `No usable Python runtime found`: recompute `$python` from the `cdxml` environment and pass that exact path with `-Python`.
- Package import or `pip check` fails: create a fresh `cdxml` environment and install the tested community release there; avoid sharing the environment with unrelated projects.
- `ChemDraw.Application` is absent: verify that Windows desktop ChemDraw is installed, open it once, and repair the installation if COM registration remains missing.
- ChemDraw is activated but a license probe fails: open and save a test document manually, close ChemDraw, and run the selected native check again. Do not change a working license as a diagnostic shortcut.
- ChemScript files exist but `ping` fails: rerun `configure`, inspect DLL bitness, and use a separate helper Python for a 32-bit release.
- Office is not installed: use `-SkipOffice`; use `-SkipNativeChemDraw` only when all native checks are intentionally omitted.
- Codex cannot see the tools: fully restart Codex, run `codex mcp get cdxml-toolkit --json`, then run `codex doctor --all`.
- Local DECIMER models are missing: ordinary drawing and ChemDraw workflows remain available. Install models only when offline image recognition is needed.

### Runtime Discovery

The MCP runtime resolves executables and applications in this order:

1. Explicit tool parameter.
2. Supported environment variable.
3. Active Python or Conda environment.
4. Windows registry and common installation locations.
5. A structured error describing what is missing.

No username, Conda root, ChemDraw directory, or Office directory should be hard-coded in repository code.

### Activation and Bitness

An activated ChemDraw desktop application does not guarantee that every automation interface is available. `diagnose_runtime()` reports separate capability states; the full health check adds temporary native PNG, ChemScript, and PPTX/DOCX OLE probes.

If a native workflow fails, confirm that the main Python is 64-bit and any legacy ChemScript helper matches its DLL architecture, then run the appropriate check:

```powershell
.\skill\chemdraw\scripts\health_check.ps1 -Python $python -SkipOffice
codex doctor --all
```

## Architecture

The Skill uses progressive disclosure so routine prompts load only the context they need:

1. `SKILL.md` provides trigger metadata, scientific constraints, privacy rules, and task routing.
2. Workflow references describe end-to-end drawing, reaction, recognition, Office, analysis, and diagnostic tasks.
3. Domain references provide decision rules and failure modes.
4. Generated API references provide exact callable signatures.
5. Inventory shards support targeted audit by module or function name.

Public MCP tools are registered through one extension registry and executed in isolated workers with hard timeouts and structured errors. New tools return `ok`, `outputs`, `warnings`, and `metadata`; established tools retain their compatible names and contracts.

Molecule comparison resolves both inputs through the installed `ChemScriptBridge`, uses ChemScript InChI for exact identity when available, and computes chirality-aware plus connectivity-only RDKit fingerprints. Batch comparison reuses one bridge process, accepts at most 256 pairs, and does not repeat source representations in its result rows.

The ChemScript SDK adapter reflects the installed managed assembly at runtime. It catalogs every SDK-declared public type and member, then reports both catalog coverage and execution-path coverage. A declarative program can construct objects, call static or instance methods, read or write members, index and enumerate collections, and dispose objects. File access, replacement of existing files, and SWIG pointer/handle interoperability each require an explicit option. This gives every public member a discoverable record while keeping native interop isolated from the MCP process.

The tested server runtime supports MCP Python SDK 1.x and 2.x. Compatibility handling lives in `cdxml-toolkit-community==0.7.0a1`, and CI exercises both supported SDK generations.

Generated signatures and inventory files must be regenerated from source. Do not manually duplicate those signatures in narrative documentation.

### Streamable HTTP

stdio remains the default and requires no network listener. To serve a licensed ChemDraw workstation to another computer, generate a bearer token and start the optional HTTP mode. The example listens on all interfaces but accepts only the workstation address supplied in `--allowed-host`:

```powershell
$env:CHEMDRAW_MCP_HTTP_API_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
python .\skill\chemdraw\scripts\mcp_server.py `
  --transport streamable-http `
  --host 0.0.0.0 `
  --port 8029 `
  --allowed-host "192.168.1.20:*"
```

On the client computer, place the same token in a different local environment variable and register the URL:

```powershell
$env:CHEMDRAW_REMOTE_TOKEN = "<same token>"
codex mcp add chemdraw-remote `
  --url "http://192.168.1.20:8029/mcp" `
  --bearer-token-env-var CHEMDRAW_REMOTE_TOKEN
```

Use Tailscale, WireGuard, or an HTTPS reverse proxy when traffic leaves a fully trusted host-only network. Plain HTTP does not encrypt the bearer token. Non-loopback listening refuses to start without a token; wildcard listening also requires an explicit allowed Host pattern. The public `/health` response contains only process state. `/metrics` requires the bearer token whenever authentication is configured and exports call duration, timeout, worker failure, active-worker, and local ChemDraw queue metrics. Metric labels contain only registered tool names and stable status codes.

## Development and Validation

Run repository validation and the complete Skill test suite before submitting changes:

```powershell
python scripts/validate_distribution.py
python -m pytest skill/chemdraw/scripts -q -v
.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
```

Focused tests must cover valid input, invalid parameters, missing files, overwrite refusal, timeout handling, and structured failures. Distribution validation checks the packaged tree, documentation links, generated references, portability, and accidental secret patterns.

Claims involving ChemDraw or Office require a licensed local installation and a real output that opens or renders successfully. CDXML rendering should use ChemDraw's native renderer where that is the behavior under test. Remote DECIMER tests are opt-in and must use non-sensitive fixtures.

GitHub Actions runs the portable checks. Machine-specific native checks remain local because hosted runners do not include licensed ChemDraw or Office applications.

## Safety and Privacy

- Remote image recognition requires `confirm_upload=true`; the default is refusal.
- Remote inputs must be real decoded images and are subject to size, response, and timeout limits.
- Modifying tools generate a new output path by default and reject unintended overwrite.
- Temporary files and outputs inherit local filesystem permissions; inspect them before sharing.
- Never commit API keys, credentials, personal experiment data, proprietary documents, or licensed binaries.
- HTTP authentication values remain in the parent server and are removed from worker environments.
- Treat recognized or generated chemistry as a hypothesis until it is checked against the source and chemically validated.

## Third-Party Boundaries

The repository's own code and documentation use the MIT License. It does not redistribute ChemDraw, Microsoft Office, Codex, DECIMER weights, or other proprietary components.

- [ChemDraw](https://revvitysignals.com/products/research/chemdraw) is proprietary software licensed by Revvity Signals.
- [cdxml-toolkit-community](https://github.com/ZiChenWang114514/cdxml-toolkit-community) is the maintained runtime used by this Skill and continues the upstream `cdxml-toolkit` project.
- [DECIMER](https://github.com/Kohulan/DECIMER-Image_Classifier) components and model weights use their upstream terms.
- Codex and Microsoft Office are optional external runtimes governed by their vendors.

Review the license metadata of the exact dependency versions used in an environment before redistribution. Project history and release notes belong in Git and GitHub Releases rather than duplicate Markdown ledgers.
