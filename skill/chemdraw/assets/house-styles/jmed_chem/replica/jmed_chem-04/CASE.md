# jmed_chem: Figure 1 clinical compounds (structure panel)

Source: Cottrell et al., "Discovery of TNG462: a highly potent and selective MTA-cooperative PRMT5 inhibitor", *J. Med. Chem.* 2025, DOI [10.1021/acs.jmedchem.4c03067](https://doi.org/10.1021/acs.jmedchem.4c03067). Licence: CC BY 4.0. The reference crop (`reference.png`) is Figure 1 of that paper, reproduced under that licence.

House style: `jmed_chem` (Journal of Medicinal Chemistry, ACS; base preset `acs1996`), figure type `structure_panel`, card at `toolkit/cdxml_toolkit/publication/house_styles/jmed_chem.json`.

## What is reproduced

The 2 x 2 grid of four clinical compounds, each with its name under the structure: AMG 193, BMS-986504, TNG908, AZD3470. Structures were read from the crop and checked against OCSR (DECIMER API, `model_prediction`). OCSR returned four candidates. The BMS-986504 candidate was wrong (ethyl in place of CH2NH2, a non-aromatic ring), so that structure was written from the image. The stereo of the other three was taken from the image and checked with RDKit CIP labels against the OCSR stereo.

| ID | SMILES in brief.json | Stereo |
| --- | --- | --- |
| AMG 193 | `Nc1nc2cnc(C(=O)N3CCOC[C@@H]3c3ccc(C(F)(F)F)cc3)cc2c2c1COC2` | morpholine C3 (S) |
| BMS-986504 | `Cn1ncc(-c2ccc3c(=O)[nH]nc(CN)c3c2)c1-c1c(F)c(Cl)cc(OC2CC2)c1C#N` | none drawn |
| TNG908 | `Cc1cc(NC(=O)C(=O)N2C[C@@H](C)CC[C@@H]2c2ccc3scnc3c2)cnc1N` | piperidine C2 (R), C5 (S) |
| AZD3470 | `CC#CCN1CC[C@@]2(C1=O)c1ccc(F)cc1C(=O)N2Cc1cc2nc(N)c(F)cc2[nH]1` | spiro carbon (S) |

Caption names are the paper's names. No compound numbers appear in this crop.

## Status

Not rendered. Calls to `draw_figure` through the MCP server did not complete in this session (300 s tool timeout or worker exit 143). `draw_figure` is in the `chemdraw_com` resource class (`mcp_runtime/tool_registry.py`, `mcp_runtime/mcp_server.py`), so every call waits for the shared native lock, with or without `render`. The lock is the blocker, not the drawing code: `replay.py` run in-process, which skips the lock, finished in seconds with `ok: true`, both checks passed and 4 of 4 structures read back. That output was not saved into this folder. It is four unrendered pages, `page-001` to `page-004`, one structure each. There is no `rendered.png`. The comparison below uses the brief, the card and the page CDXML.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| 2 x 2 grid of structures, black only | yes | four pages, one structure each (page 120 mm square); the brief has no grid option; colour not verified | no |
| no highlight or colour on changed region | yes | no highlight fill in the file; every element uses colour index 3, which the two-entry colour table does not define; not checked natively | not verified |
| plain name caption under each structure | plain Helvetica | caption run has face 0 (plain), font Arial, 8.0 pt; position not checked | yes (face only) |
| caption larger than atom labels (clinical names) | caption cap height 22 px vs atom label 17 px (card; reference.png measures about 23 to 24 px vs 17 px) | LabelSize and CaptionSize are both 8.0 pt, so equal | no |
| compound number bold in parentheses | not present in this crop | not drawn | not applicable |
| abbreviated CF3 (abbreviate_groups) | CF3 with subscript 3 | CF3 drawn as a carbon with three F atoms | no |
| nitrile written as NC | yes (BMS-986504) | nitrile drawn as N with a triple bond | no |
| Kekule aromatic rings | yes | explicit single and double bonds, no aromatic 1.5 bonds | yes (file only; not rendered) |
| stereo as hashed and bold wedges | AMG 193 hash; TNG908 hash and wedge; AZD3470 wedge | AMG 193: the only stereo bond on the page is a bold wedge (WedgeBegin), paper is hashed; TNG908: one wedge and one hash; AZD3470: one wedge (counts only) | no |
| bond length / cap height about 2.25 | about 2.35 (40 px / 17 px) | BondLength 14.4 pt over Arial 8.0 pt, cap height about 5.7 pt (0.716 em, derived, not measured): ratio about 2.5 | no |
| line width / bond length about 0.07 | about 0.06 (2.5 px / 40 px) | LineWidth 0.6 pt / BondLength 14.4 pt = 0.042 | no |
| no title on the figure | no title | "Substrate scope" on every page (the default when the brief has no title) | no |

## Differences from the paper

- No native render. The comparison is at file level: label sizes, line weight, bond ratio, bond display types and page layout are read from the CDXML, not seen on a picture.
- Layout: four pages with one structure each, not a 2 x 2 grid.
- Title: every page carries "Substrate scope". The paper's Figure 1 has no title.
- Abbreviations: the house style's CF3 abbreviation and the NC nitrile form are not applied to scope panels. The file draws CF3 as a carbon with three F atoms, and the nitrile as N with a triple bond.
- Captions: plain Arial at the same size as the atom labels (8.0 pt). The paper's captions are larger than its atom labels.
- Stereo: the AMG 193 stereo bond is a bold wedge where the paper hashes it.
- Colour: all elements reference colour index 3, which the page's colour table does not define (it holds only white and black).
- BMS-986504 structure was drawn from the image, not from OCSR.

## Tool gaps

- No `structure_panel` kind in `draw_figure`. Its kinds are `scheme`, `scope` and `mechanism` (`mcp_runtime/figure_draw.py`). The closest brief is `kind: "scope"`.
- Scope layout: the brief has no grid, row or column option (`SCOPE_KEYS` in `mcp_runtime/figure_scope.py`). The packer placed one structure per 120 mm page here.
- Scope style: only the base preset is applied. The house conventions are skipped ("house conventions apply to schemes only"), so there is no abbreviation, no card line width or bond/cap ratio, and no separate caption size. Caption and atom labels share one font size (`create_pages` in `publication/layout.py`).
- Title: the brief title defaults to "Substrate scope" (`_write_inputs` in `mcp_runtime/figure_scope.py`). There is no way to omit the title.
- Colour: the colour helper in `mcp_runtime/figure_tools.py` writes index 3 by default into a two-entry colour table. For a custom colour it returns `len(colors) + 1` after appending, which looks off by one. Needs a native check.
- Lock: `draw_figure` always takes the native lock through the MCP server, so a scope draw with `render` off also waits behind other ChemDraw work. No lock-free MCP route exists for scope panels.
- `replay.py`: the earlier note said this replay cannot reproduce the case. That was wrong. It runs and exits 0. It writes a folder named `figure.cdxml` that holds the pages, and the printed path points at that folder. The fix is to give the scope its own folder name inside the new output directory (for example `out / "scope"`) and print that folder.
- Card: `compound_label_face` is "bold" in the card, but the structure-panel captions are plain. A tool that applied the card's label face would bold the names, against this figure.

## Audit

Checked against `reference.png`, the card, the brief and the page CDXML from an in-process replay run (not saved in this folder).

Overclaims found and corrected:
- Status said scope drawing did not complete. That holds for MCP calls, which wait on the native lock and a 300 s timeout. The drawing code completed.
- The `replay.py` tool gap was wrong. The replay runs, exits 0 and writes a folder named `figure.cdxml`.
- Rows marked not verified or not applied can be checked from the file. Caption size equals atom label size. Line weight is 0.042 of bond length. Bond/cap ratio is about 2.5. The AMG 193 stereo bond is a wedge. Every page has a title. Layout is four pages.
- Caption cap height on `reference.png` measures about 23 to 24 px, not 22 px, against about 17 px for atom labels. The ratio is about 1.4, not 1.29.
- The CIP labels in the table match RDKit for the SMILES in `brief.json`. The OCSR candidates and their comparison are not in this folder, so that check remains unverified. The four calls listed in the earlier Status have no logs here and remain unverified.
- The earlier Differences said no layout, label or stereo comparison was possible. A file-level comparison was possible, and is recorded above.

Corrected matched count: 2 of 11 applicable rows (plain caption face and Kekule), both from the file alone, neither from a render.

Still open: the colour index problem. Only a native render can show what ChemDraw does with index 3 in a two-entry colour table, and that check decides the colour rows.
