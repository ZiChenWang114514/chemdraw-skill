# ChemDraw Skill — AI Chemical Drawing with MCP

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="ChemDraw Skill for any AI agent: editable chemical structures and native ChemDraw previews through MCP">
</p>

**Bring ChemDraw workflows to any AI agent.** Draw editable chemical structures, reconstruct paper figures, and turn structure tables into substrate-scope and SAR panels. Update data after ChemDraw editing while preserving unrelated layout and annotations. Connect through MCP or Python/CLI.

<p align="center">
  <a href="README.zh-cn.md"><img src="https://img.shields.io/badge/-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-007c83?style=flat" height="22" alt="简体中文"></a>&nbsp;
  <a href="docs/guide.md#first-time-windows-setup"><img src="https://img.shields.io/badge/-Installation-17242b?style=flat" height="22" alt="Installation"></a>&nbsp;
  <a href="skill/chemdraw/references/workflow-router.md"><img src="https://img.shields.io/badge/-Workflow%20catalog-007c83?style=flat" height="22" alt="Workflow catalog"></a>&nbsp;
  <a href=".github/SECURITY.md"><img src="https://img.shields.io/badge/-Security-d94f70?style=flat" height="22" alt="Security"></a>
</p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/chemdraw-skill/actions/workflows/validate.yml"><img src="https://github.com/ZiChenWang114514/chemdraw-skill/actions/workflows/validate.yml/badge.svg?style=flat" height="22" alt="Validate workflow status"></a>&nbsp;
  <img src="https://img.shields.io/badge/-Core%3A%20Windows%20%7C%20macOS%20%7C%20Linux-007c83?style=flat" height="22" alt="Portable core supports Windows, macOS, and Linux">&nbsp;
  <img src="https://img.shields.io/badge/-Python%203.10--3.13-3776AB?style=flat&amp;logo=python&amp;logoColor=white" height="22" alt="Python 3.10 through 3.13">&nbsp;
  <img src="https://img.shields.io/badge/-MCP%201.x%20%7C%202.x%20tested-17242b?style=flat" height="22" alt="MCP 1.x and 2.x tested">&nbsp;
  <a href="LICENSE"><img src="https://img.shields.io/badge/-MIT-d94f70?style=flat" height="22" alt="MIT License"></a>
</p>

<p align="center"><a href="#featured-demos">Explore featured demos</a> · <a href="#quick-start-any-agent">Quick start</a></p>

<a id="data-driven-publication-figures"></a>

## SAR and substrate-scope figures from CSV or Excel

Create substrate-scope and full-structure SAR panels from CSV/XLSX and trusted structures. Stable compound IDs bind measurements to editable ChemDraw objects. Update data or replace a structure after native editing while preserving unrelated layout and annotations; ambiguous matches produce conflict drafts. See the [workflow and examples](skill/chemdraw/references/data-driven-figures.md). XLSX support requires the toolkit `publication` extra.

## Featured demos

Explore real paper images and data through native previews, reference comparisons and editable downloads.

| Case | What it demonstrates | Available scope |
| --- | --- | --- |
| [Paper reaction scheme](#paper-scheme-demo) | Five structures, conditions, yields and wavy bonds | Complete figure; not pixel-identical |
| [Sceptrin mechanism](#mechanism-demo) | Eight structures, electron arrows, charges and conditions | Complete figure; not pixel-identical |
| [Native TLC](#tlc-demo) | Editable lanes, spots and Rf | Runnable example |
| [Native apparatus](#apparatus-demo) | Assembly from native ChemDraw templates | Runnable example |
| [Experimental NMR](#nmr-demo) | Real processed 1D data and an editable spectrum | Runnable example |
| [Simulated reaction kinetics](#kinetics-demo) | Numerical data as editable curves | Runnable example |
| [Complex synthesis: 101–112](#synthesis-101-demo) | Full native scheme and electron arrows | Stereo acceptance pending; not 1:1 |
| [Complex synthesis: 113–122](#synthesis-113-demo) | Full native scheme and electron arrows | Stereo acceptance pending; not 1:1 |

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

## Reconstruction scope and structure review

Both complex synthesis examples contain the complete layout, native molecular structures, text, brackets and electron arrows. Molecules remain editable atoms, bonds and expandable abbreviations; screenshots and traced outlines do not substitute for molecular objects.

| Check | Current result |
| --- | --- |
| Connectivity, elements, charge, isotopes and alkene geometry after native saving | Save-cycle checks pass for both figures |
| Complete stereochemistry | Not accepted; RDKit and ChemScript return opposing assignments at some bridgeheads |
| Visual comparison with the reference | Native previews and full comparisons inspected; font, arrow and some line geometry still differ |
| Strict pixel-for-pixel 1:1 | Not achieved |

Save-cycle agreement does not establish perfect recognition of the reference. Compounds 105–109, 115–120 and 121 contain conflicting specified configurations; some expanded chains and abbreviation definitions in the source also need clarification. The reconstructions preserve each depiction rather than silently making the route chemically self-consistent. The [atom-level comparison](skill/chemdraw/assets/paper-reconstructions/stereochemistry-check.json) records component hashes and atom mappings for review; absence of a disagreement does not independently establish source stereochemistry.

After installing the runtime, rebuild these two layouts offline without repeating DECIMER recognition:

```powershell
python skill/chemdraw/assets/paper-reconstructions/rebuild.py ./paper-figures-output
```

Use a new output directory. This assembles saved molecular components; native previews still require Windows ChemDraw. See the [rebuild example and limitations](skill/chemdraw/assets/paper-reconstructions/README.md). Source paper artwork is not relicensed under the software license.

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

[Fast replication guide](skill/chemdraw/references/image-visual-review.md) · [Minimal task template](skill/chemdraw/assets/paper-replica/task-template.json) · [Drawing examples](skill/chemdraw/assets/paper-replica/example/CASE.md)

| Need | Ready-to-use route |
| --- | --- |
| Crop and review an image | Existing crop/mask and comparison helpers; keep region-to-result mapping |
| Match a folded chain or bridged ring | Trace source coordinates, then check crossings and bond order |
| Correct stereochemistry | Inspect atom indices, apply an explicit edit, and read back final CDXML |
| Assemble the final scheme | Fixed-coordinate figures, rich conditions, arrows and native preview |
| Work beyond drawing | RDKit stereo/tautomer enumeration, MCS and R-group decomposition |

Remote DECIMER calls require upload authorization. Visual review remains an agent task; pixel metrics do not certify chemistry or universal 1:1 fidelity.

## What It Handles

- **Structures and reactions:** resolve names and identifiers; draw, edit, clean, merge, polish, segment, convert, and render CDXML or CDX documents.
- **Molecule comparison:** use ChemScript exact-identity checks together with RDKit fingerprint similarity for one molecule pair or a bounded batch.
- **Image recognition:** extract candidate structures, confidence values, and bounding boxes with local DECIMER models or an explicitly confirmed remote request. Recognition candidates still require source review.
- **TLC and apparatus:** use native TLC plates, lanes, spots and ChemDraw apparatus templates, with Rf calculation and editable assembly.
- **Spectra and scientific plots:** pick peaks and integrate selected regions in processed 1D NMR data; turn numerical data into editable curves. Automatic atom assignment and a complete FID-processing pipeline are not included.
- **Reaction mechanisms:** compose explicit atom coordinates and electron-arrow endpoints to illustrate supplied mechanisms; drawing does not establish mechanistic validity.
- **Office documents:** embed editable ChemDraw objects in supported desktop versions of Word and PowerPoint.
- **Experimental records:** discover files and process selected LCMS, SciFinder RDF, and lab-book workflows.
- **ChemScript SDK:** inspect the installed public catalog and run supported declarative calls in a separate worker process. Process separation limits stalled calls; it is not an operating-system security sandbox.
- **Remote workstation access:** keep stdio as the default or expose the Windows host through optional Streamable HTTP with health and Prometheus endpoints.

The project audits 637 public `cdxml-toolkit-community` symbols. That number describes the toolkit inventory, not the 39-tool full MCP profile. Full public ChemScript catalog coverage means the interface can be discovered and reported; successful execution still depends on the installed SDK, license, architecture, and individual member behavior.

## Choose the Required Components

| Goal | Add to the core setup |
| --- | --- |
| Create and edit CDXML | Any agent, 64-bit Python 3.10-3.13, MCP 1.x or 2.x, and `cdxml-toolkit-community` at the commit pinned in Quick Start; runs on Windows, macOS, and Linux |
| Native PNG, CDX, or ChemDraw cleanup | Licensed and activated Windows desktop ChemDraw with working COM automation |
| Molecule comparison or ChemScript SDK calls | Installed ChemScript DLLs compatible with the selected worker runtime |
| Editable Word or PowerPoint objects | Supported desktop Microsoft Word and/or PowerPoint |
| Local optical structure recognition | DECIMER model weights and their runtime dependencies |
| Remote access to a ChemDraw workstation | A Windows host plus authenticated HTTP configuration and an encrypted network path |

ChemDraw, Microsoft Office, ChemScript, and DECIMER model weights are not bundled. For a first installation, use the [step-by-step Chinese guide](docs/zh-cn.md#从零开始安装) or the [detailed English guide](docs/guide.md#first-time-windows-setup).

## Quick Start: any agent

Load `skill/chemdraw/SKILL.md` in your agent, then connect MCP or use Python/CLI. Clients with Skill discovery can install the whole `chemdraw` folder in their own Skill directory. Otherwise, point the agent's project instructions to the file.

```powershell
git clone https://github.com/ZiChenWang114514/chemdraw-skill.git
Set-Location .\chemdraw-skill
python -m pip install "cdxml-toolkit-community[scientific,publication] @ git+https://github.com/ZiChenWang114514/cdxml-toolkit-community.git@e07add1ecc27879f07a27780b1603cdfa596f2c2"
python -m cdxml_toolkit.mcp_runtime
```

This starts the stdio server from the pinned toolkit revision. Data-driven figures require a toolkit build exposing `publication_figure`; check `get_toolkit_capabilities()` after installation. The current Skill targets the 39-tool full profile. Register the same absolute Python executable and arguments in your client's MCP settings. Image reconstruction needs vision or human visual review.

On Windows, preview `scripts/install.ps1 -Destination <your-skill-directory>`, then add `-Apply`. Its default storage path is `$HOME/.agents/skills/chemdraw`; individual clients may use different discovery paths. Client configuration is not changed by default. On macOS/Linux, copy the entire Skill folder directly.

[Generic MCP, CLI and optional client adapters](skill/chemdraw/references/agent-integration.md) · [Windows native setup](docs/guide.md#first-time-windows-setup) · [Chinese walkthrough](docs/zh-cn.md)

```powershell
# Generic health check; no particular agent CLI or native application required
.\skill\chemdraw\scripts\health_check.ps1 -Python <absolute-python-path> -SkipNativeChemDraw
```

For native rendering, ChemScript or Office, add the corresponding dependencies and select the checks described in the setup guide.

## Validation and Safety

- GitHub Actions validates the portable runtime on Windows and Linux with Python 3.12, MCP 1.28.1 and 2.0.0, and `cdxml-toolkit-community` at the commit pinned in Quick Start. Python 3.10-3.13 is supported.
- Native ChemDraw, ChemScript, and Office behavior must be checked on a licensed local Windows host because those applications are unavailable in hosted CI.
- Structural changes can be checked with source identity, MCS-based diffs, chemistry metadata, and native rendering. Scientific acceptance remains the user's responsibility.
- Standard modifying tools create a new output path and reject accidental replacement. ChemScript SDK file access and replacement are available only when their explicit permission and overwrite options are enabled.
- Remote image recognition refuses upload unless the caller explicitly confirms it. The guided replication route requires explicit structure-role assignment and visual review; it is not an unattended reaction-image converter.
- The built-in HTTP listener does not provide TLS. Non-loopback use requires bearer authentication and an allowed `Host`; place it behind an encrypted tunnel or HTTPS reverse proxy. `/health` exposes status only, while `/metrics` requires authentication.
- Worker processes provide timeout and failure isolation, but they do not sandbox ChemDraw, Office, Python dependencies, or filesystem access. Review the [security policy](.github/SECURITY.md) before enabling native file operations or remote access.

## ChemDraw AI and MCP: common questions

### Can any AI agent use this ChemDraw Skill?

Yes. An agent needs access to the Skill instructions and either MCP (Model Context Protocol) tool calls or Python/CLI execution. See [agent setup](skill/chemdraw/references/agent-integration.md). Native ChemDraw rendering requires a licensed Windows host; portable CDXML and RDKit workflows also run on macOS and Linux.

### Can I generate SAR figures from an Excel spreadsheet?

Use trusted structures with CSV or XLSX measurements to produce editable structure–activity relationship (SAR) panels or substrate-scope figures. Stable compound IDs retain data binding, and project updates preserve unrelated manual layout changes. See the [data-driven figure workflow](skill/chemdraw/references/data-driven-figures.md).

### Can I reconstruct a paper figure as an editable ChemDraw file?

The [paper reconstruction workflow](skill/chemdraw/references/image-visual-review.md) combines grounded structures, layout reconstruction and native visual review. It produces editable CDXML; image recognition and stereochemistry require validation, and pixel-identical reproduction is not guaranteed.

## Documentation

- [Chinese setup and first use](docs/zh-cn.md)
- [Installation, troubleshooting, architecture, and operations](docs/guide.md)
- [Task-oriented workflow catalog](skill/chemdraw/references/workflow-router.md)
- [Generated MCP tool signatures](skill/chemdraw/references/mcp-signatures.md)
- [Audited `cdxml-toolkit-community` public inventory](skill/chemdraw/references/toolkit-public-inventory.md)
- [Streamable HTTP setup](docs/guide.md#streamable-http)
- [Contributing guide](.github/contributing.md)
- [Security policy](.github/SECURITY.md)

The deployable Skill lives in [`skill/chemdraw`](skill/chemdraw). Repository-specific contributor instructions are in [`AGENTS.md`](AGENTS.md).

## License

Repository-authored code and documentation are licensed under the [MIT License](LICENSE). ChemDraw, Microsoft Office, agent clients, `cdxml-toolkit-community`, the MCP Python SDK, RDKit, DECIMER, and their dependencies retain their respective licenses and usage terms.

This is an independent community project. It is not affiliated with or endorsed by Revvity, OpenAI, Microsoft, or the maintainers of the upstream `cdxml-toolkit`, the MCP Python SDK, RDKit, or DECIMER.
