<a id="top"></a>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/readme/hero-dark.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="ChemDraw Skill: editable chemistry for any AI agent. A request is grounded, drawn in native ChemDraw and verified.">
  </picture>
</p>

<h3 align="center">Editable ChemDraw chemistry for any AI coding agent</h3>

<p align="center">
  Draw structures, rebuild paper figures, turn spreadsheets into SAR panels and place live ChemDraw objects in Word and PowerPoint —<br>
  from Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode or any agent that can run a shell command.
</p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/chemdraw-skill/actions/workflows/validate.yml"><img src="https://github.com/ZiChenWang114514/chemdraw-skill/actions/workflows/validate.yml/badge.svg?style=flat" height="20" alt="Validate workflow status"></a>
  <img src="https://img.shields.io/badge/python-3.10--3.13-3776AB?style=flat&amp;logo=python&amp;logoColor=white" height="20" alt="Python 3.10 through 3.13">
  <img src="https://img.shields.io/badge/runtime-Windows%20%7C%20macOS%20%7C%20Linux-007c83?style=flat" height="20" alt="Portable runtime on Windows, macOS and Linux">
  <a href="skill/chemdraw/references/agent-integration.md"><img src="https://img.shields.io/badge/agents-any%20with%20a%20shell-17242b?style=flat" height="20" alt="Works with any agent that has a shell"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-d94f70?style=flat" height="20" alt="MIT License"></a>
</p>

<p align="center">
  <b>English</b> · <a href="README.zh-cn.md">&#31616;&#20307;&#20013;&#25991;</a>
  <br>
  <a href="#quick-start">Quick start</a> · <a href="#gallery">Gallery</a> · <a href="#what-it-handles">What it handles</a> · <a href="#featured-demos">Demos</a> · <a href="#platform-support">Platforms</a> · <a href="#common-questions">FAQ</a> · <a href="docs/guide.md">Guide</a>
</p>

<br>

<table>
  <tr>
    <td width="25%" valign="top"><b>Grounded chemistry</b><br><sub>Structures come from databases, ChemScript, OPSIN or DECIMER, never from invented SMILES.</sub></td>
    <td width="25%" valign="top"><b>Truly editable</b><br><sub>Every result is native CDXML: atoms, bonds and text you can keep editing in ChemDraw.</sub></td>
    <td width="25%" valign="top"><b>One entry point</b><br><sub>A single <code>cdx.py</code> command works in any agent. MCP is optional.</sub></td>
    <td width="25%" valign="top"><b>Stated limits</b><br><sub>Native renders, save-cycle read-back and explicit differences instead of a silent "looks right".</sub></td>
  </tr>
</table>

## Gallery

Every card is a native ChemDraw render of an editable file in this repository. Click one to open its case.

<table>
  <tr>
    <td width="33%" align="center" valign="top">
      <a href="#paper-scheme-demo"><img src="assets/readme/gallery/paper-scheme.png" alt="Editable reconstruction of a published reaction scheme (detail)"></a>
      <br><b>Paper reaction scheme</b><br><sub>Structures, conditions and yields rebuilt from a figure</sub>
    </td>
    <td width="33%" align="center" valign="top">
      <a href="#mechanism-demo"><img src="assets/readme/gallery/mechanism.png" alt="Native ChemDraw reconstruction of the sceptrin mechanism"></a>
      <br><b>Reaction mechanism</b><br><sub>Electron arrows, charges and counterions</sub>
    </td>
    <td width="33%" align="center" valign="top">
      <a href="#stereo-reconstruction-demo"><img src="assets/readme/gallery/twenty-structures.png" alt="Twenty-structure synthesis scheme reconstructed in ChemDraw"></a>
      <br><b>Twenty-structure synthesis</b><br><sub>Stereo agreement across chemistry readers: 20/20</sub>
    </td>
  </tr>
  <tr>
    <td width="33%" align="center" valign="top">
      <a href="#exam-and-lecture-drawings-in-acs-document-1996-style"><img src="assets/readme/gallery/acs1996.png" alt="ACS Document 1996 hydrogenation drawing built from a JSON spec"></a>
      <br><b>Exam and lecture figures</b><br><sub>ACS Document 1996 style from a small JSON spec</sub>
    </td>
    <td width="33%" align="center" valign="top">
      <a href="#tlc-demo"><img src="assets/readme/gallery/tlc-apparatus.png" alt="Native TLC plate and reflux apparatus"></a>
      <br><b>TLC and apparatus</b><br><sub>Native plates, Rf values and ChemDraw templates</sub>
    </td>
    <td width="33%" align="center" valign="top">
      <a href="#nmr-demo"><img src="assets/readme/gallery/nmr.png" alt="Editable experimental NMR spectrum"></a>
      <br><b>Spectra and plots</b><br><sub>Processed 1D NMR and numerical data as curves</sub>
    </td>
  </tr>
</table>

## Quick start

**1. Install.** The installer needs Python 3.9+ and finds a 64-bit Python 3.10–3.13 for the toolkit runtime on its own (through the `py` launcher, `uv`-managed interpreters or `python3.x` on PATH).

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
python scripts/install.py --agent claude agents --runtime          # preview: prints what would be installed
python scripts/install.py --agent claude agents --runtime --apply  # install the Skill and the shared runtime
```

**2. Check** what works on this machine:

```bash
python ~/.claude/skills/chemdraw/scripts/cdx.py doctor
```

**3. Ask** your agent in plain language:

```text
Use the ChemDraw Skill to draw aspirin as editable CDXML, render it natively and show me the PNG.
```

> [!NOTE]
> Python 3.14 and newer are not supported by the bundled toolkit yet. If that is your only Python, install 3.12 (for example `uv python install 3.12`) or pass `--python <interpreter>`.

<details>
<summary><b>Choose agents and install locations</b></summary>
<br>

| `--agent` | Skill folder | Read by |
| --- | --- | --- |
| `claude` | `~/.claude/skills/` | Claude Code (also GitHub Copilot and OpenCode) |
| `agents` | `~/.agents/skills/` | The shared Agent Skills folder: Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode and others |
| `gemini`, `copilot`, `cursor`, `opencode` | each agent's own folder | when you prefer the agent-specific location |

- `--project <repo>` installs project-scoped copies (`.claude/skills/`, `.agents/skills/`, `.github/skills/`, ...); `--destination <folder>` installs anywhere.
- Agents without Skill discovery need one line in their instruction file pointing at `SKILL.md`.
- All copies share one runtime. Re-running the installer upgrades in place; a replaced copy is backed up and restored if anything fails.

Details for each agent, command allowlisting and optional MCP registration: [agent integration](skill/chemdraw/references/agent-integration.md).

</details>

<details>
<summary><b>The <code>cdx.py</code> entry point</b></summary>
<br>

Agents call one entry point, which any Python can start; it re-launches itself in the toolkit runtime:

```bash
python <skill>/scripts/cdx.py tools                                         # the registered tools
python <skill>/scripts/cdx.py call resolve_name --json '{"query": "aspirin"}'
python <skill>/scripts/cdx.py render figure.cdxml                           # native 300 dpi PNG
python <skill>/scripts/cdx.py decimer crop.png                              # structure recognition
```

</details>

## What it handles

| Area | What you get |
| --- | --- |
| **Structures and reactions** | Resolve names and identifiers; draw, edit, clean, merge, polish, segment, convert and render CDXML or CDX documents. |
| **Exam, lecture and paper figures** | ACS Document 1996 drawings from a JSON spec, with abbreviation nodes, rich text, Chinese notes, arrows and boxed compound codes. |
| **Data-driven figures** | Substrate-scope and SAR panels from CSV/XLSX that stay editable and updatable. |
| **Image recognition** | Candidate structures, confidence values and bounding boxes through the DECIMER API or, on request, local DECIMER models. Candidates still require source review. |
| **Molecule comparison** | RDKit fingerprint similarity everywhere; ChemScript exact-identity checks on a Windows host with the compatible SDK. |
| **TLC and apparatus** | Native TLC plates, lanes, spots and ChemDraw apparatus templates, with Rf calculation and editable assembly. |
| **Spectra and scientific plots** | Peak picking and selected-region integration of processed 1D NMR data; numerical data as editable curves. No automatic atom assignment or complete FID processing. |
| **Reaction mechanisms** | Explicit atom coordinates and electron-arrow endpoints for supplied mechanisms; drawing does not establish mechanistic validity. |
| **Office documents** | Editable ChemDraw objects in supported desktop Word and PowerPoint on Windows. |
| **Experimental records** | File discovery and selected LCMS, SciFinder RDF and lab-book workflows. |
| **ChemScript SDK** | Inspect the installed public catalog and run supported declarative calls in a separate worker process on Windows. Process separation limits stalled calls; it is not an operating-system sandbox. |
| **Remote workstation access** | Optionally expose a Windows native host through Streamable HTTP with health and Prometheus endpoints. |

The generated [public inventory](skill/chemdraw/references/toolkit-public-inventory.md) lists the audited symbols of the bundled toolkit, separately from the registered tools (`cdx.py tools` prints the current count). Full ChemScript catalog coverage means an interface can be discovered and reported; whether it executes still depends on the installed SDK, license, architecture and member behavior.

### Exam and lecture drawings in ACS Document 1996 style

Describe a figure as a small JSON spec — SMILES with abbreviation nodes such as C10H21, conditions, arrows, bold compound codes, Chinese notes — and get editable ACS 1996 CDXML plus a native ChemDraw PNG:

```bash
python skill/chemdraw/scripts/cdx.py build skill/chemdraw/assets/acs1996/example.json example.cdxml --render
```

<p align="center"><img src="skill/chemdraw/assets/acs1996/example.png" width="80%" alt="ACS Document 1996 reaction drawn from a JSON spec: an alpha,beta-unsaturated ester with a C10H21 abbreviation is hydrogenated with H2 and Pd/C"></p>

Abbreviations stay real `GenericNickname` nodes with correct subscripts and label direction. Chinese characters are set in a CJK font while Latin text, digits and symbols stay in Arial. See the [ACS 1996 drawing guide](skill/chemdraw/references/acs1996-drawings.md).

<a id="data-driven-publication-figures"></a>

### SAR and substrate-scope figures from CSV or Excel

Create substrate-scope and full-structure SAR panels from CSV/XLSX and trusted structures. Stable compound IDs bind measurements to editable ChemDraw objects. Update data or replace a structure after native editing while preserving unrelated layout and annotations; ambiguous matches produce conflict drafts. See the [workflow and examples](skill/chemdraw/references/data-driven-figures.md). XLSX support requires the toolkit `publication` extra.

## Featured demos

Real paper images and data, with native previews, reference comparisons and editable downloads.

| Case | What it demonstrates | Available scope |
| --- | --- | --- |
| [Twenty structures](#stereo-reconstruction-demo) | Resolving stereo disagreement between chemistry readers | 20/20 reader agreement; not pixel-identical |
| [Paper reaction scheme](#paper-scheme-demo) | Five structures, conditions, yields and wavy bonds | Complete figure; not pixel-identical |
| [Sceptrin mechanism](#mechanism-demo) | Eight structures, electron arrows, charges and conditions | Complete figure; not pixel-identical |
| [Native TLC](#tlc-demo) | Editable lanes, spots and Rf | Runnable example |
| [Native apparatus](#apparatus-demo) | Assembly from native ChemDraw templates | Runnable example |
| [Experimental NMR](#nmr-demo) | Real processed 1D data and an editable spectrum | Runnable example |
| [Simulated reaction kinetics](#kinetics-demo) | Numerical data as editable curves | Runnable example |
| [Complex synthesis: 101–112](#synthesis-101-demo) | Full native scheme and electron arrows | Stereo acceptance pending; not 1:1 |
| [Complex synthesis: 113–122](#synthesis-113-demo) | Full native scheme and electron arrows | Stereo acceptance pending; not 1:1 |

<a id="stereo-reconstruction-demo"></a>

### Twenty structures: resolving stereo-reader disagreement

![ChemDraw reconstruction of a twenty-structure synthesis scheme](toolkit/assets/readme/stereo-reconstruction/native.png)

The source-oriented reconstruction disagreed between ChemScript and RDKit for 16 structures. The saved interoperability revision agrees for **20/20**, preserving the reviewed molecular targets. Compound **1** uses explicit stereobonds and therefore differs visually from the source. Same-scale ink IoU: **0.6960**; this is not pixel-identical or independent experimental stereo validation.

[Editable CDXML](toolkit/assets/readme/stereo-reconstruction/reconstruction.cdxml) · [Failure analysis, workflow and rights](toolkit/assets/readme/stereo-reconstruction/CASE.md) · [Per-compound evidence and versions](toolkit/assets/readme/stereo-reconstruction/verification.json)

The embedded X-ray is a source crop. Paper-derived artwork is excluded from the MIT license; see the case's source and rights statement.

<details>
<summary><b>Incremental workflow:</b> three caption edits, 8 → 2 native calls</summary>
<br>

Linked structure and scene records, verified candidate caching, local checks and explicit dual-variant acceptance. A controlled replay of three caption edits reduced native calls from 8 to 2 (33.53 s to 8.88 s); this is not an end-to-end recognition speed claim. [Source-oriented version](toolkit/assets/readme/stereo-reconstruction/source-oriented.cdxml) · [Workflow](skill/chemdraw/references/incremental-reconstruction.md) · [Measured evidence](toolkit/assets/readme/stereo-reconstruction/incremental-verification.json)

</details>

<a id="paper-scheme-demo"></a>

### Paper reaction scheme

**Turn a published reaction scheme into an editable ChemDraw document.** This example preserves the five structures, reaction conditions, yields and compound labels shown in the reference image.

**Original paper figure**

![Original paper scheme showing compounds 13a, 14, 15, 16 and the shared 17a/17b depiction](assets/readme/paper-replica/original.png)

**Editable reconstruction — ChemDraw-native output**

![Editable ChemDraw reconstruction preserving the original scheme orientation, conditions and compound labels](assets/readme/paper-replica/replica.png)

[Download editable CDXML](assets/readme/paper-replica/replica.cdxml) · [Inspect structure-by-structure comparisons](assets/readme/paper-replica/structure-comparison.png) · [Source and verification details](assets/readme/paper-replica/provenance.json)

Structures extracted from the saved CDXML match the five reviewed reference structures. The shared wavy bond for 17a/17b remains unspecified, as in the original figure.

> [!NOTE]
> **Visually reviewed and editable; not pixel-identical.** Font metrics, arrows and some line geometry still differ. Matching saved structures does not independently prove that every detail was recognized correctly.

<a id="mechanism-demo"></a>

### Sceptrin mechanism

![Native ChemDraw reconstruction with eight structures, electron arrows and reaction conditions](assets/readme/mechanism/native.png)

<details>
<summary>Show the reference excerpt</summary>
<br>

![Reference mechanism showing compounds 192 through 199](assets/readme/mechanism/reference.png)

</details>

[Editable CDXML](assets/readme/mechanism/mechanism.cdxml) · [Native CDX](assets/readme/mechanism/mechanism.cdx) · [Side-by-side comparison](assets/readme/mechanism/comparison.png) · [Verification and source limitations](assets/readme/mechanism/provenance.json)

Eight numbered structures and six chloride counterions retain their molecular inventory, depicted stereochemistry and formal charges through an actual ChemDraw CDXML → CDX → CDXML save cycle. Undefined R groups remain generic substituents. The reconstruction is visually reviewed, **not pixel-identical**: font metrics, electron-arrow paths, some bridge geometry and the placement of the delocalized charge indicators differ. The source's cropped recrystallization statement is not completed by inference.

### Native scientific drawings

<table>
  <tr>
    <td width="50%" valign="top">
      <a id="tlc-demo"></a>
      <b>Native TLC</b><br>
      <sub>Native TLC plate, lane and spot objects with illustrative Rf values.</sub><br><br>
      <p align="center"><img src="assets/readme/scientific/tlc.png" alt="Native TLC" height="280"></p>
      <sub><a href="assets/readme/scientific/tlc.cdxml">Editable CDXML</a> · <a href="skill/chemdraw/references/scientific-workflows.md">Run this example</a> · <a href="assets/readme/scientific/provenance.json">Data and template provenance</a></sub>
    </td>
    <td width="50%" valign="top">
      <a id="apparatus-demo"></a>
      <b>Native apparatus</b><br>
      <sub>Built from installed ChemDraw apparatus templates, preserving their editable native artwork.</sub><br><br>
      <p align="center"><img src="assets/readme/scientific/apparatus.png" alt="Native apparatus" height="280"></p>
      <sub><a href="assets/readme/scientific/apparatus.cdxml">Editable CDXML</a> · <a href="skill/chemdraw/references/scientific-workflows.md">Run this example</a> · <a href="assets/readme/scientific/provenance.json">Data and template provenance</a></sub>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <a id="nmr-demo"></a>
      <b>Experimental NMR</b><br>
      <sub>Real processed 1D NMR data, with peak picking and selected-region integration available. No automatic atom assignment.</sub><br><br>
      <img src="assets/readme/scientific/nmr.png" alt="Experimental NMR"><br>
      <sub><a href="assets/readme/scientific/nmr.cdxml">Editable CDXML</a> · <a href="skill/chemdraw/references/scientific-workflows.md">Run this example</a> · <a href="assets/readme/scientific/provenance.json">Data and template provenance</a></sub>
    </td>
    <td width="50%" valign="top">
      <a id="kinetics-demo"></a>
      <b>Simulated reaction kinetics</b><br>
      <sub>Explicitly simulated first-order decay demonstrates the numerical-data-to-figure workflow.</sub><br><br>
      <img src="assets/readme/scientific/kinetics.png" alt="Simulated reaction kinetics"><br>
      <sub><a href="assets/readme/scientific/kinetics.cdxml">Editable CDXML</a> · <a href="skill/chemdraw/references/scientific-workflows.md">Run this example</a> · <a href="assets/readme/scientific/provenance.json">Data and template provenance</a></sub>
    </td>
  </tr>
</table>

<a id="synthesis-101-demo"></a>

### Complex synthesis: 101–112

**Full scheme with editable structures.** Includes every compound number, reaction condition and mechanism arrow. Native saving preserves connectivity, charge, isotopes and alkene geometry. Bridgehead stereochemistry remains unresolved, and font and line geometry differ; this is not a validated 1:1 reproduction.

![Complex synthesis: 101–112](assets/readme/synthesis-101-112/reconstructed.png)

[Full editable CDXML](assets/readme/synthesis-101-112/figure.cdxml) · [Reference comparison](assets/readme/synthesis-101-112/comparison-full.png) · [Acceptance and provenance](assets/readme/synthesis-101-112/provenance.json)

<details>
<summary>Compare the complete reference and reconstruction</summary>

![Complex synthesis: 101–112 — comparison](assets/readme/synthesis-101-112/comparison-full.png)

</details>

<a id="synthesis-113-demo"></a>

### Complex synthesis: 113–122

**Full scheme with editable structures.** Includes every compound number, reaction condition and mechanism arrow. Native saving preserves connectivity, charge, isotopes and alkene geometry. Bridgehead stereochemistry remains unresolved, and font and line geometry differ; this is not a validated 1:1 reproduction.

![Complex synthesis: 113–122](assets/readme/synthesis-113-122/reconstructed.png)

[Full editable CDXML](assets/readme/synthesis-113-122/figure.cdxml) · [Reference comparison](assets/readme/synthesis-113-122/comparison-full.png) · [Acceptance and provenance](assets/readme/synthesis-113-122/provenance.json)

<details>
<summary>Compare the complete reference and reconstruction</summary>

![Complex synthesis: 113–122 — comparison](assets/readme/synthesis-113-122/comparison-full.png)

</details>

## Reproduce a paper figure

Start with the whole figure, then follow one route:

<p align="center">
  <code>Inspect</code> → <code>Crop structures</code> → <code>DECIMER</code> → <code>Match orientation</code> → <code>Side-by-side review</code> → <code>Correct chemistry</code> → <code>Assemble layout</code> → <code>Native preview</code>
</p>

```text
Use the ChemDraw Skill to reproduce this paper figure. Read the whole scheme,
crop each complete structure, and obtain DECIMER candidates. Match the original
orientation, inspect actual side-by-side previews, and correct only the affected
structures. Transcribe conditions visually, then deliver editable CDXML and a
native preview with unresolved chemistry or visual differences stated clearly.
```

[Image reconstruction guide](skill/chemdraw/references/image-visual-review.md) · [Minimal task template](skill/chemdraw/assets/paper-replica/task-template.json) · [Drawing examples](skill/chemdraw/assets/paper-replica/example/CASE.md)

| Need | Ready-to-use route |
| --- | --- |
| Crop and review an image | Crop/mask and comparison helpers that keep the region-to-result mapping |
| Match a folded chain or bridged ring | Trace source coordinates, then check crossings and bond order |
| Correct stereochemistry | Inspect atom indices, apply an explicit edit, and read back the final CDXML |
| Assemble the final scheme | Fixed-coordinate figures, rich conditions, arrows and native preview |
| Work beyond drawing | RDKit stereo/tautomer enumeration, MCS and R-group decomposition |

Recognition uploads only the task images and crops to the DECIMER API (`cdx.py decimer --preflight` shows what would be sent; offline requests are honored). Visual review remains the agent's task; pixel metrics do not certify chemistry.

<details>
<summary><b>Reconstruction scope and structure review</b></summary>
<br>

Both complex synthesis examples contain the complete layout, native molecular structures, text, brackets and electron arrows. Molecules remain editable atoms, bonds and expandable abbreviations; screenshots and traced outlines do not substitute for molecular objects.

| Check | Current result |
| --- | --- |
| Connectivity, elements, charge, isotopes and alkene geometry after native saving | Save-cycle checks pass for both figures |
| Complete stereochemistry | Not accepted; RDKit and ChemScript return opposing assignments at some bridgeheads |
| Visual comparison with the reference | Native previews and full comparisons inspected; font, arrow and some line geometry still differ |
| Strict pixel-for-pixel 1:1 | Not achieved |

Save-cycle agreement does not establish perfect recognition of the reference. Compounds 105–109, 115–120 and 121 contain conflicting specified configurations; some expanded chains and abbreviation definitions in the source also need clarification. The reconstructions preserve each depiction rather than silently making the route chemically self-consistent. The [atom-level comparison](skill/chemdraw/assets/paper-reconstructions/stereochemistry-check.json) records component hashes and atom mappings for review; absence of a disagreement does not independently establish source stereochemistry.

After installing the runtime, rebuild these two layouts offline without repeating DECIMER recognition (use a new output directory):

```bash
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/paper-reconstructions/rebuild.py ./paper-figures-output
```

This assembles saved molecular components; native previews still require Windows ChemDraw. See the [rebuild example and limitations](skill/chemdraw/assets/paper-reconstructions/README.md). Source paper artwork is not relicensed under the software license.

</details>

## Platform support

The portable chemistry layer — CDXML generation and editing, RDKit validation, the command line and MCP — runs on Windows, macOS and Linux. Native ChemDraw rendering and cleanup, the ChemScript bridge and Office objects are validated on Windows only.

| Capability | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| CDXML, RDKit, command-line and MCP workflows | ✅ | ✅ | ✅ |
| ChemDraw-native rendering and cleanup | ✅ <sub>activated install</sub> | 🚧 <sub>not yet</sub> | — |
| ChemScript SDK bridge | ✅ <sub>compatible SDK</sub> | — | — |
| Editable Office ChemDraw objects | ✅ <sub>desktop Office</sub> | 🚧 <sub>not yet</sub> | — |

<sub>✅ supported · 🚧 not yet supported, contributions welcome · — not supported (no bridge exists)</sub>

Installing ChemDraw on macOS does not make the Windows COM/.NET bridge available. Native macOS save/export automation needs an AppleScript/JXA adapter that does not exist yet; see [building the macOS path together](#building-the-macos-path-together).

<details>
<summary><b>Required components</b></summary>
<br>

| Goal | Add to the core setup |
| --- | --- |
| Create and edit CDXML | Any agent with shell access, 64-bit Python 3.10–3.13, and the bundled toolkit runtime (built from `toolkit/` by `scripts/install.py --runtime`) |
| Native PNG, CDX or ChemDraw cleanup | Licensed and activated Windows desktop ChemDraw with working COM automation |
| Molecule comparison or ChemScript SDK calls | RDKit for portable similarity; compatible ChemScript DLLs on a Windows host for exact checks |
| Editable Word or PowerPoint objects | Supported desktop Microsoft Word and/or PowerPoint on Windows |
| Local optical structure recognition | DECIMER model weights and their runtime dependencies |
| Remote access to a ChemDraw workstation | A Windows host plus authenticated HTTP configuration and an encrypted network path |

ChemDraw, Microsoft Office, ChemScript and DECIMER model weights are not bundled. The [setup guide](docs/guide.md#first-time-setup) covers installation options, manual runtimes and diagnostics.

</details>

## Validation and safety

- GitHub Actions runs the Skill tests on Windows and Linux with Python 3.12 and MCP 1.28.1 and 2.0.0, runs the toolkit test suite on Python 3.10–3.13, and installs the Skill end to end on Windows, Linux and macOS. This is not macOS native-app certification.
- Native ChemDraw, ChemScript and Office behavior must be checked on a licensed local Windows host because hosted CI does not have those applications.
- Structural changes can be checked with source identity, MCS-based diffs, chemistry metadata and native rendering. Scientific acceptance remains the user's responsibility.
- Standard modifying tools create a new output path and reject accidental replacement. ChemScript SDK file access and replacement are available only when their explicit permission and overwrite options are enabled.
- Remote image recognition sends only the selected task images to the DECIMER API; `--preflight` reports size, format and destination without uploading. The guided reconstruction route requires explicit structure-role assignment and visual review; it is not an unattended reaction-image converter.
- The built-in HTTP listener does not provide TLS. Non-loopback use requires bearer authentication and an allowed `Host`; place it behind an encrypted tunnel or HTTPS reverse proxy. `/health` exposes status only, while `/metrics` requires authentication.
- Worker processes provide timeout and failure isolation, but they do not sandbox ChemDraw, Office, Python dependencies or filesystem access. Review the [security policy](.github/SECURITY.md) before enabling native file operations or remote access.

## Common questions

<details>
<summary><b>Can any AI agent use this ChemDraw Skill?</b></summary>
<br>

Yes, within the platform limits above. An agent needs to read the Skill instructions and run shell commands; every tool runs through `cdx.py`. The installer places the Skill where Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode and other agents that read `SKILL.md` folders discover it. Agents without Skill discovery can be pointed at `SKILL.md` from their instruction file, and clients that prefer MCP (Model Context Protocol) can register the bundled server. See [agent integration](skill/chemdraw/references/agent-integration.md).

</details>

<details>
<summary><b>Do I need an MCP server?</b></summary>
<br>

No. The command line covers every tool and keeps the same worker isolation, native ChemDraw lock and timeouts. MCP remains available for clients that want typed tool calls.

</details>

<details>
<summary><b>Can I generate SAR figures from an Excel spreadsheet?</b></summary>
<br>

Yes. Use trusted structures with CSV or XLSX measurements to produce editable structure–activity relationship (SAR) panels or substrate-scope figures. Stable compound IDs retain data binding, and project updates preserve unrelated manual layout changes. See the [data-driven figure workflow](skill/chemdraw/references/data-driven-figures.md).

</details>

<details>
<summary><b>Can I reconstruct a paper figure as an editable ChemDraw file?</b></summary>
<br>

The [paper reconstruction workflow](skill/chemdraw/references/image-visual-review.md) combines grounded structures, layout reconstruction and native visual review. It produces editable CDXML; image recognition and stereochemistry require validation, and pixel-identical reproduction is not guaranteed.

</details>

## Building the macOS path together

macOS support is welcome as a community effort. The highest-value work is a small, reproducible native adapter rather than a platform-specific fork of the whole Skill:

- verify ChemDraw's actual AppleScript/JXA scripting dictionary on supported macOS and ChemDraw versions;
- implement isolated open/save/export operations with timeouts, single-instance locking, temporary files, hash checks and save-cycle read-back;
- map ChemScript-only behavior to portable chemistry backends where the semantics are equivalent, and report unsupported operations explicitly where they are not;
- add Apple Silicon and Intel coverage when hardware is available, including clean install, permissions, crash recovery and upgrade tests.

Please open a focused issue or pull request with the exact macOS version, chip, ChemDraw build, permission prompts, command output and a minimal reproducible file. Do not submit proprietary papers, credentials or licensed ChemDraw assets. Start with the [contributing guide](.github/contributing.md) and keep platform claims tied to passing evidence; a portable-runtime pass is not native-app certification.

## Documentation

| Start here | Go deeper |
| --- | --- |
| [Installation, troubleshooting and operations](docs/guide.md) | [Generated tool signatures](skill/chemdraw/references/mcp-signatures.md) |
| [Quick start in Chinese](docs/zh-cn.md) · [Chinese setup guide](docs/guide.zh-cn.md) | [Audited public inventory of the bundled toolkit](skill/chemdraw/references/toolkit-public-inventory.md) |
| [Agent integration and `cdx.py` command reference](skill/chemdraw/references/agent-integration.md) | [Toolkit developer reference](toolkit/docs/agent-reference.md) · [Generated MCP tool reference](toolkit/docs/mcp-tools.md) |
| [Task-oriented workflow catalog](skill/chemdraw/references/workflow-router.md) | [Remote HTTP setup](skill/chemdraw/references/operations.md#remote-http-only-when-asked) |
| [Contributing guide](.github/contributing.md) · [Security policy](.github/SECURITY.md) | [Repository instructions for contributors](AGENTS.md) |

The deployable Skill lives in [`skill/chemdraw`](skill/chemdraw). The chemistry runtime it drives, the `cdxml_toolkit` Python package, lives in [`toolkit`](toolkit) with its own tests.

## License

Repository-authored code and documentation are licensed under the [MIT License](LICENSE). The bundled toolkit in [`toolkit/`](toolkit) is based on Hiu Fung Kevin Lee's original `cdxml-toolkit` and keeps its own [MIT License](toolkit/LICENSE) and [third-party notices](toolkit/NOTICE.md). ChemDraw, Microsoft Office, agent clients, the MCP Python SDK, RDKit, DECIMER and their dependencies retain their respective licenses and usage terms.

This is an independent community project. It is not affiliated with or endorsed by Revvity, Anthropic, OpenAI, Google, GitHub, Microsoft, Anysphere, the OpenCode maintainers, or the maintainers of the upstream `cdxml-toolkit`, the MCP Python SDK, RDKit or DECIMER.

<p align="right"><a href="#top">Back to top ↑</a></p>
