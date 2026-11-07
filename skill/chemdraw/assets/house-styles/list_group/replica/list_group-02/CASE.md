# List et al., Nature 2022: substrate scope, aliphatic ketones (Figure 2, top)

Source: List et al., "Organocatalytic stereoselective cyanosilylation of small ketones", *Nature* **2022**. DOI: [10.1038/s41586-022-04531-5](https://doi.org/10.1038/s41586-022-04531-5).

Licence: CC BY 4.0. Reference crop `reference.png` is reproduced under that licence (evidence crop `list_group-02.png`).

House style: `list_group` (card `toolkit/cdxml_toolkit/publication/house_styles/list_group.json`, figure type `substrate_scope`, base preset `nature`).

## What is reproduced

The aliphatic-ketone block of the scope grid, entries 6 to 11: the six products of the cyanosilylation of the methyl ketones given in the paper (6, 7, 8, 9, 10, 11), with their yields and e.r. values, under the group heading "Aliphatic ketones" and the reaction conditions (TMSCN 1 (2.0 equiv.), IDPi (0.5 mol%), Toluene (0.2 M), T (°C), 24 h).

Not reproduced: the top reaction scheme (ketone R-C(=O)CH3 and the 0.2 mmol label), the IDPi catalyst schematics 2 to 5, the functionalised, cyclic and aryl-substituted rows, and the footnote texts.

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| 6 | `CC[C@@](C)(C#N)O[Si](C)(C)C` | RDKit: single stereocentre, S. Yield 91%, 98:2 e.r. |
| 7 | `CCC[C@@](C)(C#N)O[Si](C)(C)C` | S. 95%, 95:5 e.r. |
| 8 | `CCCC[C@@](C)(C#N)O[Si](C)(C)C` | S. 96%, 98:2 e.r. |
| 9 | `CCCCC[C@@](C)(C#N)O[Si](C)(C)C` | S. 90%, 96:4 e.r. |
| 10 | `CC(C)C[C@@](C)(C#N)O[Si](C)(C)C` | S. 93%, 93:7 e.r. |
| 11 | `CC(C)CC[C@@](C)(C#N)O[Si](C)(C)C` | S. 97%, 95:5 e.r. |

Structures were read from the crop by eye (no OCSR run). The chain lengths follow from the ketone series (2-butanone to 5-methyl-2-hexanone) and the crop's skeletons; they were not checked against the paper's SI. The absolute configuration was taken from the wedge pattern in the crop: a bold wedge to OTMS and a hashed bond to CN, with ethyl (or the longer chain) to the lower left and methyl to the lower right. RDKit gives S for all six, because CIP priorities are the same across the series.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout: grid (rows of entries under group headings) | rows of 4 to 7 per row under headings | one row of 5 per page at 240 mm, so 6 entries over two pages | no |
| variation_color: null | no colour on the structures | no colour | yes |
| yield_format `{value}%` | `91%` with superscript letter | `91%` with a Unicode superscript letter (`ᵃ`, `ᵇ`) | yes |
| selectivity_format `{value} e.r.` | `98:2 e.r.` | `98:2 e.r.` | yes |
| conditions_position: scheme_on_top | reagents above the scheme, solvent and T, time below it, above the grid | one text line above the grid, no scheme (the panel cannot draw a scheme) | no |
| highlight_fill: null | none | none | yes |
| signature 1: bold number, comma, yield on one line, e.r. on the next, centred under the structure | `**6**, 91%ᵃ` then `98:2 e.r.`, centred | number, yield and e.r. on three plain lines, left-aligned under each structure | no |
| signature 2: thin grey rules with centred category titles | full-width grey rules, title centred | plain left-aligned heading, no rules | no |
| signature 3: footnote letters as superscripts after the yield | superscript a and b after the yield | superscript a and b after the yield (footnote texts absent) | no |
| top level: compound_label_face bold | bold label | plain label | no |
| top level: compound_label_color #000000 | black | black | yes |
| top level: yield_placement | yield on the label line (`6, 91%`) in this crop | yield on its own line under the label | no |
| top level: conditions_split reagents above, solvent below | `TMSCN 1`, `IDPi` above; `Toluene (0.2 M)`, `T (°C), 24 h` below | all conditions in one line | no |
| top level: abbreviate_groups (OTMS, CN) | `OTMS`, `CN` abbreviated; Si(CH3)3 as OTMS | full `O[Si](C)(C)C` drawn, CN drawn as C#N | no |
| top level: stereo bonds (bold wedge on O, hashed on CN) | bold wedge to OTMS, hashed to CN | bold wedge to the methyl, hashed to CN | no |
| top level: plain arrow, label font Helvetica | arrow in the scheme (not in the panel) | sans-serif labels, no arrow | no |

## Differences from the paper

- The panel has no reaction header: the ketone, TMSCN arrow and product of the top scheme are missing, and the conditions are one line instead of reagents above and solvent below.
- Compound labels are plain, not bold; the number, yield and e.r. are three lines, not `6, 91%` over `98:2 e.r.`.
- The group heading is left-aligned, with no grey rules, instead of centred between rules.
- Yield and e.r. carry field names in the default layout; blank field labels (`"label": ""`) remove them.
- The stereo wedge is on the methyl bond in the replica, where the paper puts it on OTMS; the CN hashed bond matches. The whole molecule is also rotated (CN lower left, chain upper left), while the paper has the chain lower left.
- OTMS is drawn with its full trimethylsilyl group, and the CN carbon is drawn as C#N.
- Entry 11 falls onto a second page, and the replica repeats the group heading as "Aliphatic ketones (continued)".
- Footnote letters are kept, but the footnote texts are not in the crop, so no footnote list is given.
- The IDPi catalyst structures (2 to 5) and the other rows of the grid are not drawn.
- Scale: the replica's structures look larger relative to the labels than in the paper. Bond lengths were not measured, so no ratio is claimed.

## Tool gaps

- Scope panels apply only the base preset: the house conventions (bold compound labels, `label, yield` on one line, abbreviations such as OTMS, reagents above and solvent below the scheme) are not applied to scope panels, so the card's `substrate_scope` signature features cannot be reproduced.
- No scheme header: a scope panel cannot draw a reaction scheme (a generic R ketone, reagents on an arrow) above the grid.
- No control of the stereo wedge: the tool chooses which bond carries the wedge (here the methyl), and the brief cannot say which bond to wedge or fix the orientation of the substituents.
- No centred category heading with grey rules; group headings are left-aligned plain text.
- No row or column control: the grid is packed by page width and split into pages, with no way to set entries per row. A 320 mm page was requested to keep six entries on one page, but the draw worker crashed on two attempts.
- Field labels: `label` must be set to an empty string to remove the default field names.
- Footnotes are a separate list with text; footnote letters have no supported superscript field, so they were typed as Unicode superscripts.
- Draw and render were slow and unreliable during this run (about 3 minutes for one draw, and worker crashes with code 143 and `worker_crashed`), with several ChemDraw instances running on the machine.
- No baseline alignment: each structure's label block is placed under its own drawing, so in the replica the entry 9 block sits about 25 px lower than entries 8 and 10 (visible in `rendered.png`). The reference aligns all labels of a row on one baseline.
- No mixed-run text: the `**6**, 91%ᵃ` line needs a bold run followed by a regular run in one field, and the scope field values take a single style.
- No bond-length, line-width or label-size setting for a scope panel: the house `measured` block (bond length / cap height 2.65, line width 0.044, bold width 0.13, label font Helvetica) is not applied, which is why the scale and label face differ.

## Audit

Audited against `reference.png`, `rendered.png`, `brief.json` and the house JSON (`toolkit/cdxml_toolkit/publication/house_styles/list_group.json`). Zoomed crops of both images were checked.

- The replicator's "4 of 9" does not match this table, which has 16 rows. Before the audit it showed 5 rows marked yes, plus three marked partial.
- Three partial rows were refuted and changed to no: conditions_position (the replica has one line with no scheme and no reagent/solvent split), footnote superscripts (typed as Unicode glyphs, footnote texts absent), and plain arrow/label font (no arrow in the panel; the replica's sans-serif face was not shown to be Helvetica).
- yield_placement stays no: in the reference zoom, the label and yield share a line ("6, 91%ᵃ"), and the e.r. follows on the next line. The replica stacks three lines.
- stereo bonds stays no: the replica wedge is on the methyl bond, not on OTMS. The CN hashed bond is not confirmed as matching at this resolution.
- yield_format and selectivity_format are kept as yes for the format strings only. The superscript letters are Unicode glyphs, not true superscripts.
- The rotation claim (CN lower left, chain upper left in the replica; chain lower left in the reference) is confirmed.
- RDKit: `Chem.MolFromSmiles` plus `rdCIPLabeler` on all six SMILES gives S, with one stereocentre each. The SMILES formulas are C8H17NOSi to C11H23NOSi. The stereo claim is therefore confirmed.
- The "(continued)" heading and the entry 11 second page are not in this folder (only `rendered.png`, which shows entries 6 to 10). Treat them as unverified.
- The draw-crash and timing claims are not checked here; they are not in the folder.
- Corrected matched count: 5 of 16 rows (variation_color, yield_format and selectivity_format as format strings only, highlight_fill, compound_label_color).
- Tool gaps added: baseline alignment across a row, mixed bold/regular runs in a field, and bond-length/line-width/label-size settings for scope panels.
