# natural_product_reports-08: lipopeptide structure panel (Fig. 14)

## Source

Wang, Tang et al., *Nat. Prod. Rep.* 2023 (Dehydroamino acid residues in bioactive natural products). DOI [10.1039/d3np00041a](https://doi.org/10.1039/d3np00041a). Licence CC BY 3.0, as recorded in the house-style card. Reference crop: `reference.png` (Fig. 14).

Figure type: `structure_panel`. House style: `natural_product_reports` (base preset `rsc`). Drawn with `draw_figure`, `kind: "scope"`, through `brief.json`.

## What is reproduced

One of the four structures in the crop: herbicolin A (60), *Erwinia herbicola*, antifungal activity. It is drawn as a fragment only:

- the N-terminal acyl chain with the glucose on the chain carbon, the CH2 and the amide carbonyl;
- the dehydrobutyryl residue (the red unit in the paper) as `C/C=C(\NC...)C(=O)N`, Z double bond;
- the rest of the peptide is left out and the fragment ends in an N-methyl amide cap, which is a placeholder and not part of the natural product.

The name, organism and activity are given as three values beside the structure, as in the paper's name, italic organism and plain activity lines.

| ID | SMILES (in brief.json) | Read from the crop |
| --- | --- | --- |
| 60 | `C/C=C(\NC(=O)CC(CCCCCCCCCCC)OC1OC(CO)C(O)C(O)C1O)C(=O)NC` | Chain length (11 carbons after the CH), glucose and the Z-dehydrobutyryl unit are read from the image; stereo is shown in the crop (hashed and wedged bonds at the CH that carries the glucose ether O, on the glucose ring and at the Thr and Leu centres) but is omitted from the SMILES, so the species has six unassigned stereocentres (checked in RDKit). The Z geometry is the one the crop shows (NH and methyl on the same side of the C=C) and the brief encodes it. Parses in RDKit with the molecular formula C25H46N2O8 (no stereo in that check, same atoms). |

Structures 61 (stenothricin D), 62 (stendomycin I) and 63 (FR900359) are not reproduced. Their full peptide sequences, macrocycle connectivity and stereocentres cannot be read reliably from this crop, so no SMILES was written for them.

## Rendering status

The draw did not finish. The first brief, with the alkene given without stereo, failed the ChemDraw round trip with `chemical_semantics_changed`: the source lost the E/Z descriptor and the round trip added one. The brief with the Z descriptor was then run with `--render` twice and each run stopped at the 300 s tool timeout. The cause of the timeouts was not established; a heavy process load on the machine was suspected but not checked. The retry rule was then used up, so no `rendered.png` was saved and no visual comparison with the paper is available. The results below are therefore the card-to-crop comparison plus the tool behaviour recorded above, not a rendered match.

Attempts (output folders in the scratch folder, none kept): try1 and try2 without the alkene stereo failed the round trip; try3 and try4 with the Z descriptor stopped at the 300 s timeout.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/natural_product_reports/replica/natural_product_reports-08/replay.py NEW_DIR
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `validation.json` into the new folder. Because the kind is scope, `figure.cdxml` is created as a folder holding `page-001.cdxml` and so on, not as one file. It has not been run to completion.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound number bold, centred under the structure (top-level and structure_panel) | `60` bold on the name line, centred under the structure | label `60`; scope labels take only the base preset, so bold is not applied; not rendered | no |
| natural product name, plain face (structure_panel: "bold name or number") | `Herbicolin A` plain, number bold | name is a plain value in a column; the brief gives this name to the truncated fragment, so the label names a compound that is not drawn (see Audit); not rendered | no |
| organism in italic under the name (structure_panel) | *Erwinia herbicola* italic | plain value; the brief has no italic field | no |
| activity in plain text below the organism (structure_panel) | `antifungal activity` plain, on its own line below | plain value in a column, not a centred block under the structure; not rendered | no |
| dehydro residue coloured red #FC332F (card: biomolecule variation colour, same crop) | the whole dehydrobutyryl unit in red: the NH, the C=O, the alkene and its methyl | no per-atom or per-bond colour in a species; not rendered | no |
| thin plain lines, bond width 0.05 of bond length, Kekule/Arial-like labels (top-level) | thin lines, sans-serif labels | `rsc` base preset applied by the scope path; not rendered | no |
| highlight fill #C9C9FD behind the product (structure_panel claim) | no fill in this crop; the card says the fill rests on crop 02 only | none drawn; the claim does not apply to this crop | n/a (not in this figure; not counted) |
| families in thin rounded rectangles with bold heading and italic sub-class line (structure_panel claim) | absent in this crop (seen in crop 02) | not drawn | n/a (not in this figure; not counted) |

Matched: 0 of 6 applicable rows. Nothing was rendered, so no row can be marked matched. Two rows (highlight fill, rounded rectangles) are card claims from crop 02 that this crop does not show; they are not applicable here and are not counted.

## Differences from the paper

- Only one of four structures is drawn, and that one is a fragment: the peptide chain beyond the dehydro residue is replaced by an N-methyl amide cap, so the molecule drawn is not herbicolin A. The brief still names it Herbicolin A; the name should be dropped until the full structure is drawn.
- Structure 60's chain length, sugar connectivity and the Z geometry of the dehydro double bond are read from the crop and agree with it (11 carbons after the CH; the crop shows the NH and methyl on the same side of the C=C, and the brief encodes Z). The stereo at the CH bearing the sugar and on the glucose ring is shown in the crop and omitted from the brief.
- The paper's layout is a four-structure grid with the name, italic organism and activity stacked and centred under each structure. The scope layout places them in columns to the right of the structure.
- Compound number is not bold and the name is not in the paper's style.
- The red colour of the dehydro residue is not drawn.
- No render exists, so no check of bond length against the label cap height, line weight or label font was possible.

## Tool gaps

- `draw_figure` `kind: "scope"` fails the ChemDraw round trip for a species whose double-bond geometry is not given: the source loses the E/Z descriptor and the round trip adds one, so the check refuses the brief with `chemical_semantics_changed`. A scope species with a stereo double bond given explicitly did not finish within 300 s in two attempts, so the stereo path is not verified.
- Scope panels take only the base preset (`cdx.py styles` and the draw docs say so). The house-style conventions for compound labels, italic organism lines and activity lines are not applied to a scope panel.
- A species has no per-atom or per-bond colour, so a coloured residue such as the red dehydro unit cannot be drawn in a structure panel. `substrate_colors` applies to scheme substrates only, and `atom_halos` draws a halo, not a coloured bond.
- No free-text block for a name, organism and activity stacked and centred under a structure; scope values are columns.
- No way to write a long peptide or macrocycle from residue codes; a structure is given as SMILES or a name (curated table, or PubChem when the network is allowed), and the full lipopeptides cannot be typed reliably from this crop.
- No drawn break or truncation symbol for a fragment; the cap has to be a real group, so a fragment always shows an invented end.

## Audit

Checked on 2026-11-07 against `reference.png` (enlarged), `brief.json`, the house card, and the toolkit code (`mcp_runtime/figure_scope.py`, `mcp_runtime/figure_draw.py`, `chemistry_semantics.py`). RDKit was used for the SMILES. The drawing tools were not run again.

Overclaims corrected above:

- The stereo at the CH and the sugar was described as not visible at this resolution. It is visible in the crop; omitting it is a choice, and the species has six unassigned stereocentres.
- The Z geometry was described as an assumption. The crop shows it.
- The brief names the truncated fragment Herbicolin A. The output would present an N-methyl-capped fragment as the natural product.
- The table counted two card claims that this crop does not show as "no". They are not applicable, so the count is 0 of 6.
- The cause of the timeouts (machine load) was not established.
- The replay writes a folder for `figure.cdxml`, not a file.
- The tool-gap line "structures must be given as SMILES" is too broad. Names are resolved through the curated table or PubChem. The real gap is that there is no residue-code or peptide builder.

Confirmed: the formula C25H46N2O8 and the Z descriptor (RDKit), the 11 carbons after the CH, and the base-preset-only scope path (its style report says so). The species keys allow no colour, halo or text-run formatting, and labels and values are plain text.

Corrected matched count: 0 of 6 applicable rows. No row can be marked matched without a render.

Tool gaps the replicator did not list:

- No mixed formatting within one line: the paper's name line is plain text with a bold number, and a scope value cannot hold runs of different face.
- No visual check without ChemDraw: without a native render the report says `native: not_run`, so proportions, line weight and label face cannot be checked.
- No name-to-structure check: a name is accepted with any SMILES, and the tool does not flag a fragment that is not the named compound.
- No warning for undefined stereocentres in a species SMILES: the six unassigned centres pass without a note.
