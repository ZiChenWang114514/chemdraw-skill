# ChemDraw Skill — editable chemistry for AI coding agents

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="ChemDraw Skill for AI agents: editable chemical structures and native ChemDraw previews">
</p>

**Bring ChemDraw workflows to any AI coding agent.** Draw editable chemical structures, reconstruct paper figures, turn structure tables into substrate-scope and SAR panels, and draw exam and lecture figures in ACS Document 1996 style. Everything runs through one command-line entry point, so it works in Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode and any other agent with a shell. MCP is optional.

<p align="center">
  <a href="README.zh-cn.md"><img src="https://img.shields.io/badge/-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-007c83?style=flat" height="22" alt="Simplified Chinese"></a>&nbsp;
  <a href="docs/guide.md#first-time-setup"><img src="https://img.shields.io/badge/-Installation-17242b?style=flat" height="22" alt="Installation"></a>&nbsp;
  <a href="skill/chemdraw/references/workflow-router.md"><img src="https://img.shields.io/badge/-Workflow%20catalog-007c83?style=flat" height="22" alt="Workflow catalog"></a>&nbsp;
  <a href=".github/SECURITY.md"><img src="https://img.shields.io/badge/-Security-d94f70?style=flat" height="22" alt="Security"></a>
</p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/chemdraw-skill/actions/workflows/validate.yml"><img src="https://github.com/ZiChenWang114514/chemdraw-skill/actions/workflows/validate.yml/badge.svg?style=flat" height="22" alt="Validate workflow status"></a>&nbsp;
  <a href="skill/chemdraw/references/agent-integration.md"><img src="https://img.shields.io/badge/-Any%20agent%20with%20a%20shell-17242b?style=flat" height="22" alt="Works with any agent that has a shell"></a>&nbsp;
  <img src="https://img.shields.io/badge/-Portable%20runtime%3A%20Windows%20%7C%20macOS%20%7C%20Linux-007c83?style=flat" height="22" alt="Portable runtime supports Windows, macOS, and Linux">&nbsp;
  <img src="https://img.shields.io/badge/-Python%203.10--3.13-3776AB?style=flat&amp;logo=python&amp;logoColor=white" height="22" alt="Python 3.10 through 3.13">&nbsp;
  <a href="LICENSE"><img src="https://img.shields.io/badge/-MIT-d94f70?style=flat" height="22" alt="MIT License"></a>
</p>

<p align="center"><a href="#quick-start">Quick start</a> · <a href="#what-it-handles">What it handles</a> · <a href="#featured-demos">Featured demos</a> · <a href="#platform-support">Platform support</a></p>

## Quick start

You need Python 3.9+ to run the installer and a 64-bit Python 3.10–3.13 for the toolkit runtime; the installer finds one automatically (through the `py` launcher, `uv`-managed interpreters or `python3.x` on PATH). Python 3.14 and newer are not supported by `cdxml-toolkit-community` yet: if that is your only Python, install 3.12 (for example `uv python install 3.12`) or pass `--python <interpreter>`.

```bash
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
cd chemdraw-skill
python scripts/install.py --agent claude agents --runtime          # preview: prints what would be installed
python scripts/install.py --agent claude agents --runtime --apply  # install the Skill and the shared runtime
python ~/.claude/skills/chemdraw/scripts/cdx.py doctor             # what works on this machine
```

Choose one or more agents with `--agent`:

| `--agent` | Skill folder | Read by |
| --- | --- | --- |
| `claude` | `~/.claude/skills/` | Claude Code (also GitHub Copilot and OpenCode) |
| `agents` | `~/.agents/skills/` | The shared Agent Skills folder: Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode and others |
| `gemini`, `copilot`, `cursor`, `opencode` | each agent's own folder | when you prefer the agent-specific location |

- `--project <repo>` installs project-scoped copies (`.claude/skills/`, `.agents/skills/`, `.github/skills/`, ...); `--destination <folder>` installs anywhere.
- Agents without Skill discovery need one line in their instruction file pointing at `SKILL.md`.
- All copies share one runtime. Re-running the installer upgrades in place; a replaced copy is backed up and restored if anything fails.

Details for each agent, command allowlisting and optional MCP registration: [agent integration](skill/chemdraw/references/agent-integration.md).

Then ask your agent, for example:

```text
Use the ChemDraw Skill to draw aspirin as editable CDXML, render it natively and show me the PNG.
```

Agents call one entry point, which any Python can start; it re-launches itself in the toolkit runtime:

```bash
python <skill>/scripts/cdx.py tools                                         # the registered tools
python <skill>/scripts/cdx.py call resolve_name --json '{"query": "aspirin"}'
python <skill>/scripts/cdx.py render figure.cdxml                           # native 300 dpi PNG
python <skill>/scripts/cdx.py decimer crop.png                              # structure recognition
```

## What it handles

- **Structures and reactions:** resolve names and identifiers; draw, edit, clean, merge, polish, segment, convert and render CDXML or CDX documents.
- **Exam, lecture and paper figures:** ACS Document 1996 drawings from a JSON spec, with abbreviation nodes, rich text, Chinese notes, arrows and boxed compound codes.
- **Data-driven figures:** substrate-scope and SAR panels from CSV/XLSX that stay editable and updatable.
- **Image recognition:** candidate structures, confidence values and bounding boxes through the DECIMER API or, on request, local DECIMER models. Candidates still require source review.
- **Molecule comparison:** RDKit fingerprint similarity everywhere; ChemScript exact-identity checks on a Windows host with the compatible SDK.
- **TLC and apparatus:** native TLC plates, lanes, spots and ChemDraw apparatus templates, with Rf calculation and editable assembly.
- **Spectra and scientific plots:** peak picking and selected-region integration of processed 1D NMR data; numerical data as editable curves. No automatic atom assignment or complete FID processing.
- **Reaction mechanisms:** explicit atom coordinates and electron-arrow endpoints for supplied mechanisms; drawing does not establish mechanistic validity.
- **Office documents:** editable ChemDraw objects in supported desktop Word and PowerPoint on Windows.
- **Experimental records:** file discovery and selected LCMS, SciFinder RDF and lab-book workflows.
- **ChemScript SDK:** inspect the installed public catalog and run supported declarative calls in a separate worker process on Windows. Process separation limits stalled calls; it is not an operating-system sandbox.
- **Remote workstation access:** optionally expose a Windows native host through Streamable HTTP with health and Prometheus endpoints.

The generated [public inventory](skill/chemdraw/references/toolkit-public-inventory.md) lists the audited `cdxml-toolkit-community` symbols, separately from the registered tools (`cdx.py tools` prints the current count). Full ChemScript catalog coverage means an interface can be discovered and reported; whether it executes still depends on the installed SDK, license, architecture and member behavior.

### Exam and lecture drawings in ACS Document 1996 style

Describe a figure as a small JSON spec — SMILES with abbreviation nodes such as C10H21, conditions, arrows, bold compound codes, Chinese notes — and get editable ACS 1996 CDXML plus a native ChemDraw PNG:

```bash
python skill/chemdraw/scripts/cdx.py build skill/chemdraw/assets/acs1996/example.json example.cdxml --render
```

![ACS Document 1996 reaction drawn from a JSON spec: an alpha,beta-unsaturated ester with a C10H21 abbreviation is hydrogenated with H2 and Pd/C](skill/chemdraw/assets/acs1996/example.png)

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

![ChemDraw reconstruction of a twenty-structure synthesis scheme](https://raw.githubusercontent.com/ZiChenWang114514/cdxml-toolkit-community/main/assets/readme/stereo-reconstruction/native.png)

The source-oriented reconstruction disagreed between ChemScript and RDKit for 16 structures. The saved interoperability revision agrees for **20/20**, preserving the reviewed molecular targets. Compound **1** uses explicit stereobonds and therefore differs visually from the source. Same-scale ink IoU: **0.6960**; this is not pixel-identical or independent experimental stereo validation.

[Editable CDXML](https://github.com/ZiChenWang114514/cdxml-toolkit-community/blob/main/assets/readme/stereo-reconstruction/reconstruction.cdxml) · [Failure analysis, workflow and rights](https://github.com/ZiChenWang114514/cdxml-toolkit-community/blob/main/assets/readme/stereo-reconstruction/CASE.md) · [Per-compound evidence and versions](https://github.com/ZiChenWang114514/cdxml-toolkit-community/blob/main/assets/readme/stereo-reconstruction/verification.json)

The embedded X-ray is a source crop. Paper-derived artwork is excluded from the MIT license; see the case's source and rights statement.

**Incremental workflow:** linked structure and scene records, verified candidate caching, local checks and explicit dual-variant acceptance. A controlled replay of three caption edits reduced native calls from 8 to 2 (33.53 s to 8.88 s); this is not an end-to-end recognition speed claim. [Source-oriented version](https://github.com/ZiChenWang114514/cdxml-toolkit-community/blob/main/assets/readme/stereo-reconstruction/source-oriented.cdxml) · [Workflow](skill/chemdraw/references/incremental-reconstruction.md) · [Measured evidence](https://github.com/ZiChenWang114514/cdxml-toolkit-community/blob/main/assets/readme/stereo-reconstruction/incremental-verification.json)

<a id="paper-scheme-demo"></a>

### Paper reaction scheme

**Turn a published reaction scheme into an editable ChemDraw document.** This example preserves the five structures, reaction conditions, yields and compound labels shown in the reference image.

**Original paper figure**

![Original paper scheme showing compounds 13a, 14, 15, 16 and the shared 17a/17b depiction](assets/readme/paper-replica/original.png)

**Editable reconstruction — ChemDraw-native output**

![Editable ChemDraw reconstruction preserving the original scheme orientation, conditions and compound labels](assets/readme/paper-replica/replica.png)

[Download editable CDXML](assets/readme/paper-replica/replica.cdxml) · [Inspect structure-by-structure comparisons](assets/readme/paper-replica/structure-comparison.png) · [Source and verification details](assets/readme/paper-replica/provenance.json)

Structures extracted from the saved CDXML match the five reviewed reference structures. The shared wavy bond for 17a/17b remains unspecified, as in the original figure.

**Visually reviewed and editable; not pixel-identical.** Font metrics, arrows and some line geometry still differ. Matching saved structures does not independently prove that every detail was recognized correctly.

<a id="mechanism-demo"></a>

### Sceptrin mechanism

**Reference excerpt**

![Reference mechanism showing compounds 192 through 199](assets/readme/mechanism/reference.png)

**ChemDraw reconstruction**

![Native ChemDraw reconstruction with eight structures, electron arrows and reaction conditions](assets/readme/mechanism/native.png)

[Editable CDXML](assets/readme/mechanism/mechanism.cdxml) · [Native CDX](assets/readme/mechanism/mechanism.cdx) · [Side-by-side comparison](assets/readme/mechanism/comparison.png) · [Verification and source limitations](assets/readme/mechanism/provenance.json)

Eight numbered structures and six chloride counterions retain their molecular inventory, depicted stereochemistry and formal charges through an actual ChemDraw CDXML → CDX → CDXML save cycle. Undefined R groups remain generic substituents. The reconstruction is visually reviewed, **not pixel-identical**: font metrics, electron-arrow paths, some bridge geometry and the placement of the delocalized charge indicators differ. The source's cropped recrystallization statement is not completed by inference.

<a id="tlc-demo"></a>

### Native TLC

Native TLC plate, lane and spot objects with illustrative Rf values.

![Native TLC](assets/readme/scientific/tlc.png)

[Editable CDXML](assets/readme/scientific/tlc.cdxml) · [Run this example](skill/chemdraw/references/scientific-workflows.md) · [Data and template provenance](assets/readme/scientific/provenance.json)

<a id="apparatus-demo"></a>

### Native apparatus

Built from installed ChemDraw apparatus templates, preserving their editable native artwork.

![Native apparatus](assets/readme/scientific/apparatus.png)

[Editable CDXML](assets/readme/scientific/apparatus.cdxml) · [Run this example](skill/chemdraw/references/scientific-workflows.md) · [Data and template provenance](assets/readme/scientific/provenance.json)

<a id="nmr-demo"></a>

### Experimental NMR

Real processed 1D NMR data, with peak picking and selected-region integration available. No automatic atom assignment.

![Experimental NMR](assets/readme/scientific/nmr.png)

[Editable CDXML](assets/readme/scientific/nmr.cdxml) · [Run this example](skill/chemdraw/references/scientific-workflows.md) · [Data and template provenance](assets/readme/scientific/provenance.json)

<a id="kinetics-demo"></a>

### Simulated reaction kinetics

Explicitly simulated first-order decay demonstrates the numerical-data-to-figure workflow.

![Simulated reaction kinetics](assets/readme/scientific/kinetics.png)

[Editable CDXML](assets/readme/scientific/kinetics.cdxml) · [Run this example](skill/chemdraw/references/scientific-workflows.md) · [Data and template provenance](assets/readme/scientific/provenance.json)

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

**Inspect → crop structures → DECIMER → match orientation → inspect side-by-side → correct chemistry → assemble conditions and layout → native preview.**

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

### Reconstruction scope and structure review

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

## Platform support

The portable chemistry layer — CDXML generation and editing, RDKit validation, the command line and MCP — runs on Windows, macOS and Linux. Native ChemDraw rendering and cleanup, the ChemScript bridge and Office objects are validated on Windows only.

| Capability | Windows | macOS | Linux |
| --- | --- | --- | --- |
| CDXML, RDKit, command-line and MCP workflows | Supported | Supported | Supported |
| ChemDraw-native rendering and cleanup | Supported with an activated installation | Not yet supported | Not supported |
| ChemScript SDK bridge | Supported with the compatible SDK | No supported bridge | No supported bridge |
| Editable Office ChemDraw objects | Supported on desktop Office | Not yet supported | Not supported |

Installing ChemDraw on macOS does not make the Windows COM/.NET bridge available. Native macOS save/export automation needs an AppleScript/JXA adapter that does not exist yet; see [building the macOS path together](#building-the-macos-path-together).

### Required components

| Goal | Add to the core setup |
| --- | --- |
| Create and edit CDXML | Any agent with shell access, 64-bit Python 3.10–3.13, and `cdxml-toolkit-community` at the pinned commit (installed by `scripts/install.py --runtime`) |
| Native PNG, CDX or ChemDraw cleanup | Licensed and activated Windows desktop ChemDraw with working COM automation |
| Molecule comparison or ChemScript SDK calls | RDKit for portable similarity; compatible ChemScript DLLs on a Windows host for exact checks |
| Editable Word or PowerPoint objects | Supported desktop Microsoft Word and/or PowerPoint on Windows |
| Local optical structure recognition | DECIMER model weights and their runtime dependencies |
| Remote access to a ChemDraw workstation | A Windows host plus authenticated HTTP configuration and an encrypted network path |

ChemDraw, Microsoft Office, ChemScript and DECIMER model weights are not bundled. The [setup guide](docs/guide.md#first-time-setup) covers installation options, manual runtimes and diagnostics.

## Validation and safety

- GitHub Actions runs the Skill tests on Windows and Linux with Python 3.12, MCP 1.28.1 and 2.0.0, and `cdxml-toolkit-community` at the pinned commit, and installs the Skill end to end on Windows, Linux and macOS. This is not macOS native-app certification.
- Native ChemDraw, ChemScript and Office behavior must be checked on a licensed local Windows host because hosted CI does not have those applications.
- Structural changes can be checked with source identity, MCS-based diffs, chemistry metadata and native rendering. Scientific acceptance remains the user's responsibility.
- Standard modifying tools create a new output path and reject accidental replacement. ChemScript SDK file access and replacement are available only when their explicit permission and overwrite options are enabled.
- Remote image recognition sends only the selected task images to the DECIMER API; `--preflight` reports size, format and destination without uploading. The guided reconstruction route requires explicit structure-role assignment and visual review; it is not an unattended reaction-image converter.
- The built-in HTTP listener does not provide TLS. Non-loopback use requires bearer authentication and an allowed `Host`; place it behind an encrypted tunnel or HTTPS reverse proxy. `/health` exposes status only, while `/metrics` requires authentication.
- Worker processes provide timeout and failure isolation, but they do not sandbox ChemDraw, Office, Python dependencies or filesystem access. Review the [security policy](.github/SECURITY.md) before enabling native file operations or remote access.

## Common questions

### Can any AI agent use this ChemDraw Skill?

Yes, within the platform limits above. An agent needs to read the Skill instructions and run shell commands; every tool runs through `cdx.py`. The installer places the Skill where Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, OpenCode and other agents that read `SKILL.md` folders discover it. Agents without Skill discovery can be pointed at `SKILL.md` from their instruction file, and clients that prefer MCP (Model Context Protocol) can register the bundled server. See [agent integration](skill/chemdraw/references/agent-integration.md).

### Do I need an MCP server?

No. The command line covers every tool and keeps the same worker isolation, native ChemDraw lock and timeouts. MCP remains available for clients that want typed tool calls.

### Can I generate SAR figures from an Excel spreadsheet?

Yes. Use trusted structures with CSV or XLSX measurements to produce editable structure–activity relationship (SAR) panels or substrate-scope figures. Stable compound IDs retain data binding, and project updates preserve unrelated manual layout changes. See the [data-driven figure workflow](skill/chemdraw/references/data-driven-figures.md).

### Can I reconstruct a paper figure as an editable ChemDraw file?

The [paper reconstruction workflow](skill/chemdraw/references/image-visual-review.md) combines grounded structures, layout reconstruction and native visual review. It produces editable CDXML; image recognition and stereochemistry require validation, and pixel-identical reproduction is not guaranteed.

## Building the macOS path together

macOS support is welcome as a community effort. The highest-value work is a small, reproducible native adapter rather than a platform-specific fork of the whole Skill:

- verify ChemDraw's actual AppleScript/JXA scripting dictionary on supported macOS and ChemDraw versions;
- implement isolated open/save/export operations with timeouts, single-instance locking, temporary files, hash checks and save-cycle read-back;
- map ChemScript-only behavior to portable chemistry backends where the semantics are equivalent, and report unsupported operations explicitly where they are not;
- add Apple Silicon and Intel coverage when hardware is available, including clean install, permissions, crash recovery and upgrade tests.

Please open a focused issue or pull request with the exact macOS version, chip, ChemDraw build, permission prompts, command output and a minimal reproducible file. Do not submit proprietary papers, credentials or licensed ChemDraw assets. Start with the [contributing guide](.github/contributing.md) and keep platform claims tied to passing evidence; a portable-runtime pass is not native-app certification.

## Documentation

- [Installation, troubleshooting and operations](docs/guide.md)
- [Quick start in Chinese](docs/zh-cn.md) · [Chinese setup guide](docs/guide.zh-cn.md)
- [Agent integration and `cdx.py` command reference](skill/chemdraw/references/agent-integration.md)
- [Task-oriented workflow catalog](skill/chemdraw/references/workflow-router.md)
- [Generated tool signatures](skill/chemdraw/references/mcp-signatures.md)
- [Audited `cdxml-toolkit-community` public inventory](skill/chemdraw/references/toolkit-public-inventory.md)
- [Remote HTTP setup](skill/chemdraw/references/operations.md#remote-http-only-when-asked)
- [Contributing guide](.github/contributing.md) · [Security policy](.github/SECURITY.md)

The deployable Skill lives in [`skill/chemdraw`](skill/chemdraw). Repository-specific contributor instructions are in [`AGENTS.md`](AGENTS.md).

## License

Repository-authored code and documentation are licensed under the [MIT License](LICENSE). ChemDraw, Microsoft Office, agent clients, `cdxml-toolkit-community`, the MCP Python SDK, RDKit, DECIMER and their dependencies retain their respective licenses and usage terms.

This is an independent community project. It is not affiliated with or endorsed by Revvity, Anthropic, OpenAI, Google, GitHub, Microsoft, Anysphere, the OpenCode maintainers, or the maintainers of the upstream `cdxml-toolkit`, the MCP Python SDK, RDKit or DECIMER.
