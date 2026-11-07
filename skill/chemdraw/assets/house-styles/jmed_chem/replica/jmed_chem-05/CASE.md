# J. Med. Chem. 2025: inhibitor grid, Figure 1A (LIMK inhibitors, two rows of four)

Source: Baldwin, Ward et al., "Discovery of MDI-114215: a potent and selective LIMK inhibitor to treat fragile X syndrome", *J. Med. Chem.* 2025. DOI: [10.1021/acs.jmedchem.4c02694](https://doi.org/10.1021/acs.jmedchem.4c02694).

Licence: CC BY 4.0 (from the house-style card). The reference crop is reproduced under that licence.

Style card: `jmed_chem` (`skill/chemdraw/assets/house-styles/jmed_chem/` card, figure type `structure_panel`), base preset ACS Document 1996.

## What is reproduced

Panel A of Figure 1: the eight literature inhibitors in a 4 x 2 grid, bold "A" at top left, each caption as plain name followed by the compound number in bold parentheses. Compounds 1 to 4 are in the crop. Compounds 5 to 8 are in the full figure (`jm4c02694_0001.jpg`), because the crop cuts off the second-row captions. Those captions (Pyr1 (5), TH-257 (6), TH-300 (7), TH-470 (8)) come from the full figure. That file is not in this folder, so these captions were not checked here.

Structures were read from the paper image by hand and checked with RDKit (formulas ok, all eight preserved in the CDXML round trip). No OCSR was run. The RDKit check was not re-run in the audit below.

| ID | Name in caption | SMILES (in `figure-manifest.json`) |
| --- | --- | --- |
| 1 | LIMKi3 (BMS-5) | `CC(C)C(=O)Nc1ncc(s1)-c1cc(nn1-c1c(Cl)cccc1Cl)C(F)F` |
| 2 | FRAX486 | `CCN1C(=O)C(c2ccc(Cl)cc2Cl)=CC2=CN=C(Nc3ccc(N4CCNCC4)c(F)c3)N=C21` |
| 3 | LX7101 | `CN(C)C(=O)Oc1cccc(NC(=O)C2(CN)CCN(CC2)c2ncnc3[nH]cc(C)c23)c1` |
| 4 | SR7826 | `OCCN(c1ccccc1)C(=O)Nc1ccc(cc1)-c1ncnc2[nH]cc(C)c12` |
| 5 | Pyr1 | `Cc1c2cc[nH]c(=O)c2c(C)c2[nH]c3ccc(OC(=O)c4ccccc4)cc3c12` |
| 6 | TH-257 | `CCCCN(Cc1ccccc1)C(=O)c1ccc(cc1)S(=O)(=O)Nc1ccccc1` |
| 7 | TH-300 | `CCCN(Cc1ccccc1)C(=O)c1ccc(cc1)S(=O)(=O)Nc1cccc(Cl)c1` |
| 8 | TH-470 | `CC(C)C(=O)Nc1nc(cs1)C(=O)NCCN(Cc1ccccc1)C(=O)c1ccc(cc1)S(=O)(=O)Nc1ccccc1` |

The drawing was made with `compose_chemical_figure` from `figure-manifest.json` (explicit grid, text captions with runs). Files: `figure.cdxml` (editable), `rendered.png` (native ChemDraw render, downscaled to 1200 px wide), `reference.png` (the crop).

No `brief.json` is kept. The `draw_figure` brief route does not support this figure type, so the replica uses the manifest instead. `replay.py` runs `compose_chemical_figure` on `figure-manifest.json` and writes into a new folder.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jmed_chem/replica/jmed_chem-05/replay.py NEW_DIR
```

## Replica attempts

- Try 1: `draw_figure` scope panel (eight SMILES, `style: jmed_chem`), with and without `--render`. Without render it returned a flow layout of one compound per column, paged into 2 to 5 compounds per page, with each label at its own height. With render it hit the 300 s tool timeout (native ChemDraw lock under concurrent load). Not used.
- Try 2: manifest grid, 4 columns, 165 pt cells, captions at a fixed offset. Structures and captions overlapped in row 2 (SR7826 caption on TH-470).
- Try 3: manifest grid, 190 pt cells, 230 pt rows, captions at 175 pt offset (this is `figure.cdxml`). Overlaps remain: the SR7826 (4) caption sits directly above the top sulfonamide of TH-470 (row 2, column 4), so it reads as a label for TH-470, and the "A" letter touches the LIMKi3 Cl label. Captions also sit well below their structures.

## Differences from the paper

- Layout: the paper's rows are centred under each structure with captions close beneath (about one bond length below in the crop). In the render, row 1 captions sit about 180 px below the row 1 structures (roughly eight bond lengths at the render's scale), which puts them closer to the row 2 structures than to their own. Row 2 captions are also about 180 px below their structures. Captions are placed at fixed positions, not centred: the LIMKi3 caption centre is about 75 px right of its structure's centre.
- Panel letter "A" sits inside the LIMKi3 cell beside its Cl label, not at the panel's top-left corner as in the reference, and touches that Cl label.
- Captions are one run of text with a bold number, but the spacing is not optimised (no per-structure measurement).
- Structure drawing is ACS 1996 at 14.4 pt bonds with 9 pt Arial labels. The bond-to-cap-height ratio (about 2.2 from these settings, card value 2.25) is a settings value, not a measurement of the output. The paper's line weight and label sizes are not verified against the 696 px original, and caption text is about 15% smaller relative to structure width than in the reference (approximate ink-run measurement).
- Pyr1 (5): the ester substituent is drawn as a benzoate read from the image. The bond to the benzo ring was checked against the paper image only at low resolution.
- TH-470 (8): the thiazole substitution pattern (2-amido, 4-carboxamide) and the linker are read from the image; not verified against the SI or the source file.
- LIMKi3 (1): the thiazole is attached through C5 and the pyrazole carries CHF2 at C3, read from the image at low resolution.
- The panel letter is a plain text run in bold, not a native label.

## Tool gaps

- `draw_figure` has no `structure_panel` kind (only scheme, scope and mechanism). A grid of unrelated structures with captions cannot be expressed as a reaction brief.
- Scope panels (`kind: "scope"`) lay structures out in a single flow, one row per page, with no 2-D grid and no common baseline for labels. A 4 x 2 panel with aligned captions cannot be made this way.
- Scope captions cannot mix a plain name with a bold number on one line (`LIMKi3 (BMS-5, **1**)`); the label is a separate line above the value. This is a scope-only limit: manifest captions already mix plain and bold runs (see `figure-manifest.json`).
- The house-style conventions are not applied outside schemes. The report says "house conventions apply to schemes only", so `jmed_chem` structure_panel conventions (captions, bold numbers) are not applied to scope or manifest output.
- `compose_chemical_figure` grid placement does not fit captions to structures. Captions must be positioned by hand from the rendered output, with no bounding-box or text-to-structure binding.
- Native rendering under concurrent load times out (draw with `--render` hit the 300 s limit). Not a permanent gap, but it made iteration slow.

## Audit (2026-11-07)

Scope: re-checked against `reference.png`, `rendered.png` (1200 x 738), `reference.png` (696 x 300), `figure.cdxml` and the house card `toolkit/cdxml_toolkit/publication/house_styles/jmed_chem.json`. `brief.json` is not in this folder (see Replay). This file had no convention table with match rows, so the "3 of 5 matched" count from the replica report is not recorded here; the table below replaces it.

Measured facts (ink runs on the PNGs; scale estimated from the manifest's roughly 790 pt width):

- Render: row 1 structures end near y 165 and row 1 captions start near y 345, a gap of about 180 px. Reference: gap about 12 px. A bond is about 22 px in the render (estimate), so the gap is about eight bond lengths against about one.
- Render: the SR7826 (4) caption sits at about x 1047 to 1120, y 345 to 360, directly above the top sulfonamide of TH-470 (row 2, column 4).
- Render: LIMKi3 caption centre about x 187; its structure centre about x 112.
- `figure.cdxml`: BondLength 14.4, LabelSize 9.0, LineWidth 1.0, BoldWidth 2, LabelFont 1001, which the fonttable names Arial.

| Row | Verdict | Basis |
| --- | --- | --- |
| Proportions (bond to cap height) | Not matched | Settings give about 2.2, matching the card's 2.25 at settings level only; the output was not measured. Caption text is about 15% smaller relative to structure width than in the reference (approximate). |
| Line weight | Not matched | Output line width not measured; the body above says so. |
| Label face and colour | Matched (captions) | LabelFont 1001 is Arial. Caption crop shows a plain name with a bold number, in black. |
| Yield placement and format | N/A | Card has yield_placement null; a structure panel has no yields. |
| Conditions placement | N/A | Card's conditions_split is a scheme rule; the panel has no conditions. |
| Abbreviations | Matched (trivially) | Reference and render both draw CHF2 and NMe2 expanded. The card's Boc and CF3 rule is for schemes. |
| Colours | Matched | Black on white in both. |
| Layout | Not matched | Caption gap about eight bond lengths against about one; SR7826 caption on TH-470; A inside the LIMKi3 cell beside Cl; captions not centred under structures. |

Corrected matched count: 3 of 6 applicable rows (label face and colour, abbreviations, colours). Two rows are N/A and three are not matched.

Overclaims found and corrected above:

- "No overlaps" (Try 3) is false: the SR7826 caption sits on TH-470's top and the "A" touches the LIMKi3 Cl label.
- The caption gap of "60 to 90 pt" understated the render; the measured gap is about 180 px.
- "The bond-to-cap-height ratio was matched" describes settings, not output.
- The mixed-run caption limit applies to scope output only; manifest captions already mix runs.
- Captions 5 to 8 (full figure) and the RDKit formula check cannot be reproduced from this folder and are not verified here.

Tool gaps the replica report missed:

- No overlap or bounding-box check on composed output. The collision above went undetected, and the "no overlaps" claim had no check behind it.
- No measurement of output against card values (bond to cap height, line width, label size), so the card numbers are never checked on rendered output.
- The manifest style (font, bond length, line width, label size) is typed by hand and not read from the house card, so card conventions cannot flow into `compose_chemical_figure`.
- No panel-letter object anchored to the figure's top-left corner; "A" is placed by absolute offset.
- No automatic row height or caption offset from each structure's bounding box; both are tuned by hand, and captions are placed at fixed positions rather than centred on their structures.
- Native render timeouts under ChemDraw lock contention are an operations problem, not a missing drawing capability, and are not listed as a gap here.
