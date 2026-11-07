# Dalton Transactions, Chart 1, panel A: one copper(I) NHC entry (replica of 1 of 6 entries)

Source: Martins et al., Dalton Trans. 2025, "Borane-functionalized heteroscorpionate copper complexes as catalysts for azide-alkyne cycloaddition", DOI 10.1039/d5dt01595b. Licence CC BY 3.0 (from the house-style card). The reference crop is `reference.png` (copy of `evidence/dalton_transactions-01.png`, 748 x 1353 px, panels A and B of Chart 1).

Figure type: `structure_panel` (with the `coordination_complex` conventions of the card). Style slug: `dalton_transactions`.

## What is reproduced

Only the first entry of panel A: the imidazol-2-ylidene copper(I) chloride with TOF 950 h-1 (Refs. 16-18). The NHC N-substituents are drawn as methyl (the paper's R is a variable group, not read from the crop); X is drawn as Cl. The SMILES in `brief.json` is `CN1C=C[N+](C)=C1[Cu-]Cl` (checked with RDKit: C5H8ClCuN2). It is charge-separated, see below.

Not reproduced: the other five entries of panel A (diimine Cu cation 1920 h-1, phosphine Cu cage 313 h-1, bridged Si-Cu dimer 28 h-1) and all of panel B (Drover Cp*Fe phosphine, Szymczak Cu, "Our work" Zn and "This work" Cu with borane-tethered pyrazolyl ligands). I did not run OCSR, and I did not write SMILES for the multi-donor complexes (metal-donor bonds, bridging halides, borane chains), because I could not check them with confidence. The panel is therefore one entry, not the figure.

## Replay

```
python skill/chemdraw/scripts/cdx.py py -I skill/chemdraw/assets/house-styles/dalton_transactions/replica/dalton_transactions-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/panel/page-001.cdxml
```

`replay.py` calls `draw_figure` on `brief.json` offline. The template from the JACS Au replica writes `figure.cdxml`; that fails for `kind: "scope"`, which takes a new folder, so the replay here writes `NEW_DIR/panel/page-001.cdxml`. `rendered.png` is the native render of that page.

Run history: the first draw (heading added as a group, plus a title) gave native `not_run` (`resource_busy`, 175 s). The second draw, without the title, also gave `not_run`; one `cdx.py render` retry succeeded and produced `rendered.png`. A third draw with `"title": ""` produced a byte-identical CDXML (sha256 5c3b7a...), so an empty title is treated as absent.

## Convention table

Rows marked n/a concern elements that are not in the drawn entry (boron, Cp*, tBu, the "Our work" and "This work" labels). They are neither matches nor misses for this replica. Seven rows apply; two match, and both come from the base preset defaults, not from the card (the scope drawer applies no card convention).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| coordination_complex: metal-ligand bond is a plain line, not an arrow | plain line from the carbene C to Cu | plain line from C to Cu | yes (bond style only; default bond, not the card) |
| coordination_complex: formal_charge_style plain | no charges on the NHC (neutral carbene drawn with a ring line) | N+ and Cu- drawn, because the SMILES is charge-separated | no |
| coordination_complex: metal colour null (black in crop 01) | Cu black | Cu black | yes (black is the default colour; the card is not applied) |
| coordination_complex: boron pink (crops 01-03) | B only in panel B | not drawn | n/a |
| coordination_complex: arene or Cp bonded by one line to the ring (crops 01, 06) | Cp* in the Drover entry | not drawn | n/a |
| coordination_complex: Cp* drawn with an inner circle (crop 01) | Drover entry only | not drawn | n/a |
| structure_panel: "A:" and "B:" bold letters with italic titles, dashed rule between panels | bold "A:", italic title, dashed rule above panel B | title and group heading in regular type, no rule, no panel B; the drawer adds a default heading "Substrate scope" when no title is given | no |
| structure_panel: TOF in italics under each structure, "(Ref.)" in italics | "950 h-1" and "(Refs. 16-18)" in italics | "TOF: 950 h⁻¹" and "Ref.: Refs. 16-18" in regular type with the field names as prefixes | no |
| structure_panel: "Our work" and "This work" in italics | panel B only | not drawn | n/a |
| top level: label_font Arial | sans-serif, Arial-like | the rsc base preset names Helvetica as its label face (chemdraw/style_presets.py), and the scope path takes that face only; the card's Arial is not applied. The glyphs look alike on screen, but the face is not Arial | no (by face name; visually near-identical) |
| top level: aromatic_rings kekule | NHC ring drawn with a dashed (delocalised) bond | Kekule-type C=C plus N+=C | no (the card's kekule setting also contradicts the dashed bond in crop 01, and the card's vocabulary has no dashed option) |
| top level: abbreviate_groups tBu | tBu in the Si-Cu entry only | not drawn | n/a |

Count: 12 rows, 5 n/a, 7 applicable, 2 matched. The earlier note "Claimed: 11. Matched: 2." did not match the table, which had 12 rows and three "yes" entries; the label_font "yes" was wrong.

Scope note: the report says style.applied is empty and skipped reads "house conventions apply to schemes only; the base preset was applied". The draw_figure docstring confirms that scope panels take only the house style's base preset, so no coordination_complex or structure_panel convention reaches a scope panel. The 2 matches above therefore come from the base preset and default black, not from the card.

## Differences from the paper

- Only one of six entries is drawn; the panel layout (two lettered panels, dashed rule) is not reproduced.
- The NHC is drawn charge-separated (N+, Cu-); the paper shows a neutral carbene with the dashed ring bond and no charges.
- The chloride is drawn to the left of Cu; in the paper the halide sits directly below Cu.
- The R groups are methyl; the paper uses an unnamed variable R.
- The compound identifier `nhc` is printed under the structure (the drawer uses the species id when no label is given); the paper has no compound label here.
- Field names are printed ("TOF:", "Ref.:") in regular type; the paper shows the values alone in italics with no labels.
- The default heading "Substrate scope" is printed above the panel; the paper has none.
- Bond length, line width and text sizes were not measured against the crop; the comparison is visual.

## Tool gaps

Gaps the replicator named:

- `kind: "scope"` takes only the base preset (figure_scope.py takes the preset's font and geometry and nothing else; the draw_figure docstring says scope panels take only the house style's base preset). House conventions (label face, metal and donor colours, italic annotations, panel headers) cannot reach a structure panel. The card's label_font Arial also cannot be set for a scope panel.
- No compound-label suppression: a species without a label shows its id, and `label: ""` is replaced by the id. Not traced in publication_figure.py; the replica output shows "nhc".
- No field-label suppression: an omitted field label is the key (figure_scope.py `_fields`: `item.get("label", key)`), so it prints in lower case ("tof:"). An empty label is passed through as "" to the spec. The claim that an empty label is replaced by a default ("TOF", "Ref.") was not traced in publication_figure.py and is not verified here.
- No empty-title option: `brief.get("title") or "Substrate scope"` (figure_scope.py), so an omitted or empty title gives the default heading. Confirmed.
- No mixed text styling in scope panels: labels, values and group headings are plain text (figure_scope.py `_text`). The run-level bold, italic, subscript and superscript code in figure_tools.py is not reachable from a scope brief.
- No panel separator (dashed rule or lettered panel object) in kind scope: SCOPE_KEYS has no such key.
- Dative metal-ligand bonds: there is no `dative_bonds` key. SPECIES_KEYS is {id, smiles, name, label, group, values}, so a species record with `dative_bonds` is refused as an unknown key. The "not tested" item is therefore a refusal, not an untested option. A neutral two-bonded NHC donor cannot be written from SMILES (C->[Cu] gives [C] with two radicals or CH2); only the charge-separated form draws plain lines, and it adds N+ and Cu-.
- Native render: resource_busy after 175 s on the first two draws, and one cdx.py render retry succeeded. rendered.png exists in this folder; the timing and the retry are not verifiable from the folder (see Audit).
- Replay template: replay.py writes page-001.cdxml into a new folder for kind scope, and its docstring says so. Confirmed.

Gaps the replicator missed:

- No delocalised (dashed) ring bond. The house style accepts only aromatic_rings "kekule" or "circle" (publication/house_styles.py line 38), and figure_house.py maps "circle" to Kekule drawing. The dashed NHC ring of the paper cannot be written.
- No subscript or superscript runs in scope values or labels. The replica writes "h⁻¹" with Unicode superscript characters, which is a workaround and not a superscript run. Formulae such as Cy2B, (TMS)2N, PF6 and CuLn cannot be written with true subscripts.
- No bracket around a cationic complex and no counterion placement. Brackets exist only for ts_bracket in schemes (figure_draw.py around lines 497-540), and ts_bracket is not a scope key.
- No coordinate or anchor control. The drawer lays out structures and their labels automatically, so the chloride cannot be placed directly below Cu as in the paper.
- No bond-style option in a scope brief (no hashed, wedge or dashed bonds for metal-donor contacts). None of the bond styles needed for the other entries of panel A can be written.
- No bond length, line width or other geometry override in a scope brief. SCOPE_KEYS and SPECIES_KEYS allow only width_mm, height_mm and a preset, so the card's measured proportions (bond length 2.3 times cap height, line width 0.07 times bond length) cannot be requested.
- No element colours in scope panels (house colours are scheme-only). This did not change this entry, whose N and Cl are black in the paper.

## Audit

Checked against reference.png and rendered.png (zoomed crops), the card publication/house_styles/dalton_transactions.json, and the toolkit code: figure_scope.py, figure_draw.py (draw_figure docstring), chemdraw/style_presets.py, publication/house_styles.py and figure_house.py.

Corrections made to this file:

- The count was wrong. The table had 12 rows and three "yes" entries, not "11 claimed, 2 matched". Five rows concern elements absent from the drawn entry and are now n/a. Of the seven applicable rows, two match, and both come from base defaults.
- The label_font row said the rsc base preset gives Arial. The rsc preset names Helvetica, and the scope path takes that face, so the row is now "no".
- The scope note implied the matches came from Arial labels and plain lines. They come from the default bond and default black; no card convention reaches the panel.
- The dative_bonds item was described as untested. The key is not supported (SPECIES_KEYS rejects unknown keys), so it is a refusal.
- Tool gaps added: dashed ring bond, sub- and superscript runs, bracket and counterion placement, coordinate control, bond-style options, geometry overrides, element colours in scope.

Corrected matched count: 2 of 7 applicable rows (bond style and black Cu, both default). The card's conventions are not applied to this panel, so the replica does not match the card at the convention level.

Not verifiable from this folder: there is no panel/ folder, no validation.json and no CDXML here. The sha256 5c3b7a... of the blank-title draw, the style.skipped text, the resource_busy history and the CDXML font names could not be checked. They are not counted as evidence.

Not measured: line width, bond length and cap height were not measured in either image. No proportion match is claimed, and the card's 2.3 ratio cannot be requested for a scope panel anyway.
