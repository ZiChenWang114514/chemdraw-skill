# Wünsch et al., Molecules 2025: CK2 SAR table (Table 1), mdpi_molecules card, sar_table

Source: Wünsch et al., "Structure-activity relationship studies of tetracyclic pyrrolocarbazoles inhibiting heterotetrameric CK2", *Molecules* **2025**. DOI: [10.3390/molecules30010063](https://doi.org/10.3390/molecules30010063).

Licence: CC BY 4.0 (from the house-style card). The reference crop (`reference.png`) is Table 1 of that article, reproduced under that licence.

Drawing style: the `mdpi_molecules` house style (base preset ACS Document 1996); figure type `sar_table`.

## What is reproduced

The ten compound rows of Table 1, (±)-9a to (±)-17: each row's full structure, its R and R′ as drawn (9b carries N-CH3 at the imide nitrogen), and the three columns of data (test concentration, KD′ as mean ± SD, Ki) with the footnote letters b, c and d and "n.s.".

The table has no drawer in the tools. The closest tool is a substrate-scope panel (`"kind": "scope"`), so each compound is drawn as its own full structure with its values under it. The table's three rules, header row, column alignment and the shared core drawn above the table are not reproduced (see the table below and "Tool gaps").

Not reproduced: the three core structures above the table (the 9–17 core appears only through its ten rows; 18a–20a and 21–23 are not table rows and are not drawn); the footnote texts a to d (only the letters are visible in the crop); the compound numbers are carried with their citation brackets, e.g. "(±)-9a [40]".

## Structures

All ten SMILES are in `brief.json`. They were written by reading the crop, not by OCSR. RDKit parses all ten and gives the expected formulas. The core for the 9 series is `CCOC(=O)C1c2[nH]c3ccccc3c2C(c2cc(OC)c(OC)c(OC)c2)C2C(=O)NC(=O)C12` (9a), with R varied at the C4 carbonyl and R′ at the imide nitrogen. Relative stereochemistry (3a, 4, 10, 10a) is not written in the SMILES, so the replica has no wedges or hashes. The 3-pyridyl amide in (±)-15 was read from a small zoom; the position of the ring nitrogen is the least certain reading.

## Replica

- `brief.json`: `kind: scope`, `style: mdpi_molecules`, three fields (test concentration, KD′, Ki), ten species with `group: "9–17"`. Drawn with the default page size (180 × 240 mm), which gives three pages of 4, 4 and 2 compounds.
- `rendered.png`: the three ChemDraw pages stacked and downscaled to 1100 px wide. Page one has 9a, 9b, 10 and 11; page two has 12 to 15; page three has 16 and 17.
- `replay.py`: the jacs-au replay with an updated docstring. It calls `draw_figure` with an output path of `figure.cdxml`, which for a scope brief names a folder. It was not run for this case, so it is untested.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `table_style` horizontal_rules: three black rules, no verticals | rule above the header, rule under the header, bottom rule | no rules; each compound is a block of lines | no |
| signature: three black horizontal rules, no vertical rules | yes | no | no |
| signature: core structures drawn above the table with R and R′ positions | core 9–17, 18a–20a and 21–23 drawn above, R and R′ labelled | no core and no R or R′ labels; each compound is a full structure | no |
| signature: substituents as small structures in the R column | text (OEt, NHCH3, NHCH2C6H5) and small structures for rows 15 to 17 | no R column; the substituent sits inside each full structure | no |
| `activity_format` "{mean} ± {sd}" | "59 ± 25", "758 ± 338" in the KD′ column | "59 ± 25" and so on, typed as text (the tool does not apply the format) | yes |
| `variation_color` null | all black | all black | yes |
| `highlight_fill` null | none | none | yes |
| compound labels: bold numbers, plain "(±)" | "(±)" regular, number bold | plain text, no bold | no |
| compound label colour #000000 | black; citation numbers "[40]" are blue | black, citation brackets included | no |
| methoxy as H3CO / OCH3, not MeO | H3CO and OCH3 labels | OMe drawn as O bonded to a methyl line; no OCH3 label | no |
| `aromatic_rings` kekule | Kekulé indole and aryl rings | Kekulé indole and aryl rings | yes |
| label font Arial (structure labels) | sans-serif labels | Arial (ChemDraw) | yes |
| table body text serif (card note) | serif table text | sans-serif text (Arial) | no |

Matched 6 of 13 claimed; after the audit below, 5 of 13 hold. Rows with no value in this table (Ph, yields, conditions) are left out. The CO2Et abbreviation is in the card's abbreviate_groups and is not applied to the 9a and 9b ester (see Audit). The bond-length and cap-height measurements are null for this crop and were not compared.

## Differences from the paper

- Layout: the table becomes a scope panel. There are no rules, no header row, and no column alignment. Each compound is a block of "Label", "Conc. test compd. (µM): value", "KD′ (nM): value", "Ki (µM): value" lines, spread over three pages.
- Orientation: the core is drawn with the indole at the top, not at the lower left as in the paper.
- Stereochemistry: the relative configuration at 3a, 4, 10 and 10a is not drawn. The paper uses hashed and wedged bonds.
- Labels: compound labels are plain. The paper has bold numbers under a regular "(±)".
- Groups: "Substrate scope" (the default title) is printed on every page. "9–17" is printed on page one and "9–17 (continued)" on pages two and three. The paper has neither.
- Methoxy: OMe is drawn as O-CH3 with no abbreviation; the paper writes H3CO and OCH3.
- The R at C4 is drawn as the full group (for example C(=O)OCH2CH3) and not as the "OEt" text used in the paper's R column.
- Footnote letters b, c and d are superscripts, but their texts are not drawn (they are not in the crop).
- Colour: all black. The paper's citation numbers "[40]" are blue; the replica prints them black.

## Tool gaps

- No table drawer: no horizontal-rule table with a header row, column alignment and rules; a scope panel gives label-and-value lines under each structure.
- No shared-core mode: no way to draw one core with R and R′ labelled, or a column of small substituent structures.
- House conventions do not apply to scope panels. The report says "house conventions apply to schemes only; the base preset was applied", so the bold compound labels and the H3CO/OCH3 and CO2Et/Ph abbreviations are not produced.
- The serif table text in the card's note has no option; scope values use the base preset font (Arial).
- Relative-stereo depiction: the SMILES route needs stereo written in and drawn as wedges or hashes. Not attempted, because the relative configuration was not derived.
- Title: the default "Substrate scope" title and the group heading are printed on each page. Whether the title can be left empty was not tested.
- Page packing: with the default 180 × 240 mm page, ten compounds take three pages. A single 180 × 420 mm page was requested but the draw timed out, so one-page output was not obtained.
- Locants: the paper numbers the core atoms (10, 10a, 3a, 4) in small plain type beside the stereocentres. The replica has no locant labels, and this was not listed before.
- Mixed-weight labels: brief.json gives each species one label string, so a bold compound number with a plain "(±)" was not drawn.
- Coloured label runs: the citation numbers "[40]" are blue in the paper; a single label string gives no blue run.
- Subscript, italic and bracket units in field labels: the paper's K_D′ and K_i (italic K) and its "[nM]" and "[µM]" units are written as plain text in the replica, "KD′" and "(nM)". Whether the scope fields accept subscript or italic runs was not tested.
- Core orientation: the indole is at the top in the replica and at the lower left in the paper. Whether the scope kind can set the 2D orientation was not tested.

## Rendering notes

Each `draw` without `--render` took 58 to 210 s. Each ChemDraw render of one page took about 5 minutes; the first render attempt on page one stopped with a worker timeout (exit 143), and the retry succeeded. Other ChemDraw and Python processes were running on the machine at the time.

## Audit

Checked against reference.png and rendered.png, including 2x crops of the 9a structure and of the reference table row.

- Overclaim, corrected: the compound-label colour row. The citation numbers "[40]" are blue in the paper and black in the replica, so the row is now "no". The bold-number row was already "no".
- Overclaim, corrected: the group line. "9–17" appears only on page one; pages two and three read "9–17 (continued)".
- Overclaim, corrected: the CO2Et abbreviation is not a 21–23-only convention. The card lists CO2Et in abbreviate_groups, and the 9a and 9b C4 ester is drawn in full in the replica.
- Matched on output strings only: the activity row. The values "59 ± 25" and so on are typed in brief.json, and the toolkit applies no format. The replica also uses "(nM)" where the paper uses "[nM]", and writes "KD′" without the subscript D.
- Confirmed: Kekulé indole and aryl rings (visible in the 9a crop), Arial structure labels, all-black structures apart from the citation colour, no highlight fill, and variation colour null. Structure labels and rules were checked against the table layout.
- Not checked: the RDKit formula claim, the position of the ring nitrogen in (±)-15, and the card-level measured values (bond length to cap height 2.0, line width 0.042 of bond length). The replica did not measure any of them.
- Corrected count: 5 of 13 (activity format on output strings, variation colour, highlight fill, aromatic rings, label font). The replica claimed 6.
