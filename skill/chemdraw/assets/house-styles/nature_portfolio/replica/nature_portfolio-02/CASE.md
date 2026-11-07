# Nature Portfolio house style: Fig. 2 header scheme (nature_portfolio-02)

Source: Wang et al., *Nat. Commun.* **2025**, *16*, 1108. DOI: [10.1038/s41467-025-56377-w](https://doi.org/10.1038/s41467-025-56377-w). Licence: CC BY 4.0 (from the card).

Figure type: `reaction_scheme`, as assigned for this crop. The card has no `figure_types` section, so only its top-level conventions apply. The crop itself is a scheme plus a scope panel (dashed rules, six scope rows, grey ligand box).

## What is reproduced

The top reaction scheme only: the Ni-catalysed electroreductive cross-coupling of a benzylic chloride (1) with an aryl bromide (2) giving 3a. Concrete compounds stand in for the generic Ar1, Ar2 and R placeholders: 1 is (1-chloropropyl)benzene, 2 is methyl 4-bromobenzoate, and 3a is methyl 4-(1-phenylpropyl)benzoate, with the 85% yield and 90% ee from the scope row. Conditions are copied from the crop. The scope rows (3a-3f, X = Br/Cl/OTf) and the grey L1 box are not drawn.

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| 1 | `CCC(Cl)c1ccccc1` | RDKit canonical SMILES matches; C9H11Cl |
| 2 | `COC(=O)c1ccc(Br)cc1` | RDKit canonical SMILES matches; C8H7BrO2 |
| 3a | `CCC(c1ccccc1)c1ccc(cc1)C(=O)OC` | Same molecule as RDKit's canonical `CCC(c1ccccc1)c1ccc(C(=O)OC)cc1`; the string differs, so it is not the canonical form. C17H18O2. Racemic: the crop shows a wedge at the stereocentre but gives no absolute configuration, so none is assigned. |

No OCSR was run; the structures were read from the crop and checked in RDKit.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/nature_portfolio/replica/nature_portfolio-02/replay.py NEW_DIR
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Re-run during the audit into a scratch folder: `checks_passed: true`, readback `matched`, `native.status: not_run`, and the BrCl balance warning. The original run's output and any `brief_try2` file are not in this folder, so the provenance of `rendered.png` (a desktop ChemDraw render) is not verified here.

## Tries

1. `yield: "85%"`: the output read `3a, 85%`. The scope row reads `X = Br, 3a, 85%, 90% ee`; the top band of the crop has no yield.
2. `yield: "85%, 90% ee"` (final): the output reads `3a, 85%, 90% ee`, matching the scope row, not the top band. This is the brief kept here.

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold 1, 2, 3 in the top band (`3a` appears only in the scope rows) | bold 1, 2 and 3a in the render (2 checked in an upscaled crop); the product is numbered 3a, not 3 | yes (face only; product number differs) |
| compound_label_color #000000 | black | black | yes |
| compound_label_italic_suffix false | `a` upright | `a` upright | yes |
| yield_placement after_product_label | no yield in the top band; `X = Br, 3a, 85%, 90% ee` appears only in the scope rows below the dashed rule | `3a, 85%, 90% ee` on one line under the product, copied from the scope row | no |
| yield_format `{value}%` | `85%` and `90% ee` in the scope rows; the `ee` is not in the `{value}%` format | yield string typed as one free-text value; the template fills only a bare number, so `85%, 90% ee` passes through unformatted | no (not exercised) |
| conditions_split reagents_above_solvent_below | electrode and catalyst/ligand above; electrolyte, base, solvent, current below | same split; the tool skipped this convention and the split comes from the brief | yes (brief-supplied) |
| substrate_layout null (inline A + B) | `1 + 2` inline | `1 + 2` inline | yes |
| abbreviate_groups (OMe, Ph, Me, Et, tBu, CN) | Ph, Et, Me in the scope rows; ester drawn as CO2Me (also CO2Et, SO2Me) | Ph, Et, Me abbreviated; ester drawn as C(=O)OMe (CO2Me is not on the card list) | no |
| aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| new_bond_color null | new C-C bond red (#FF0000) in evidence | new bond black | no |
| substrate_colors #0078B2 | substrate 1 teal, substrate 2 blue (#0000FF) | substrate 1 teal; substrate 2 black | no (one of two colours) |
| highlight_fill null | none | none | yes |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain | plain | yes |
| show_plus_sign null | `+` drawn | `+` drawn | yes |
| yield_separator `, ` | `, ` | `, ` | yes |
| measured bond length / cap height (2.21 card; 1.6 on this crop) | bond 40 px; cap 25 px (1.6). The crop also records a compound-label cap of 18 px, which gives 2.2 | bond 10.8 pt; a 6 pt Arial cap is about 4.3 pt, giving about 2.5 (10.8 / 6 = 1.8 if the font size is used instead) | no |
| measured line width / bond (0.062 card; 0.075 on this crop) | 3 px / 40 px (0.075) | 0.6 / 10.8 (0.056) | approximately, not matched |
| measured arrow length / bond (11.1 card; 12.7 on this crop) | 507 px / 40 px (12.7) | 141.5 / 10.8 (13.1) | no (18% above the card value; within 3% of the crop only) |

Matched: 11 of 19 rows after the audit below (16 top-level conventions plus three measured proportions; the first draft said 14).

## Differences from the paper

- Product colouring: the paper colours the product fragments by origin (teal Ar1 part, blue Ar2 part) and the new C-C bond red. The replica draws the product in black.
- Second substrate: the paper's aryl bromide is blue; the replica's is black. The card lists only one substrate colour.
- Ester: the paper labels the ester CO2Me. The replica draws it as a full C(=O)OMe group.
- Label size: the paper's atom labels are proportionally larger (bond/label about 1.6 on this crop). The nature preset's label size gives about 2.5, so the labels look small against the rings.
- Stereochemistry: the paper shows a bold wedge at the stereocentre. The replica is racemic and has no wedge, because the crop gives no absolute configuration.
- Ligand L1: the paper shows the structure in a grey rounded box. The replica gives it as text only.
- Placeholders: the paper uses generic R, Ar1 and Ar2 (Ar sits inside the ring, not in a circle); the replica uses concrete compounds.
- Product number: the top band labels the product 3; the replica uses 3a from the scope row.
- Scope rows, dashed rules and the scope-panel layout are not drawn.
- Yield: the top band has no yield. The paper's `85%, 90% ee` sits in the scope row (`X = Br, 3a, 85%, 90% ee`), and the replica copies that line under its product. The ee is only free text; the tool has no selectivity field for this step.

## Tool gaps

- No per-fragment or per-atom colouring of the product by substrate origin; `substrate_colors` applies only to the first substrate, and `new_bond_color` needs atom mapping that a brief cannot give.
- No grey rounded panel or boxed structure for a ligand in the conditions; a ligand can only be given as text.
- No way to draw a bold wedge at a stereocentre from a brief without an absolute-configuration SMILES.
- No generic R or Ar placeholders in a scheme; circled Ar rings are not supported.
- The `conditions_split` convention is listed on the card but skipped by the tool (reported as "kept as given"), so the split depends on the brief author.
- Atom balance: the reductive coupling loses Br and Cl (BrCl), which the tool flags as unbalanced and does not draw. There is no way to show the two-electron reduction (electrode input) as a by-product, so the warning stays.
- Label size: the nature preset draws labels at 6 pt; the card's measured 7.3 pt estimate is not applied.
- Bold wedge width: the card's `bold_width_over_bond_length` 0.244 is not applied; the nature preset gives 1.56/10.8 = 0.144. No wedge is drawn here, so this is not visible in this replica.
- Scope rows: `draw_figure` scope panels take only the base preset, so the card's conventions would not apply to them. This comes from the documentation and was not tested.
- `yield_format` fills the template only when the whole yield is a bare number (`format_yield` matches `_YIELD_VALUE` in full). `85%, 90% ee` passes through unformatted, and the validation report lists `yield_format` only on the under-arrow branch, not for `after_product_label`.
- The card's measured proportions (bond/cap, line width, arrow length) are not applied: the report's applied list has no entry for them, and the bond length is the preset's 10.8 pt.
- Card-list gap, not a tool gap: `CO2Me` and `CO2Et` are in the tool's abbreviation table, but the card's `abbreviate_groups` omits them. `SO2Me` is not in the table at all.

## Audit

Checked against `reference.png` (the scope crop, with the top band at its left), `rendered.png`, the house card at `toolkit/cdxml_toolkit/publication/house_styles/nature_portfolio.json`, the toolkit source, and a re-run of `replay.py` into a scratch folder.

Confirmed on inspection: the three compounds are the scope-row structures (C9H11Cl, C8H7BrO2, C17H18O2); substrate 1 is teal and substrate 2 black; reagent text is black; the arrow is plain; reagent subscripts render; `1`, `2` and `3a` are bold; `3a` has an upright `a`; the new C-C bond is black, not red; L1 is text only; the replay reports `checks_passed: true`, readback `matched`, and the BrCl warning.

Overclaims corrected in the table and text above:
- The top band of the reference has no yield and labels the product `3`. The `3a, 85%, 90% ee` line comes from the scope row. Yield placement is now a no, and the claim that the crop reads that line is withdrawn.
- `yield_format` is not exercised. The template fills only a bare number, so the ee string passes through. Now a no.
- The ester is drawn as C(=O)OMe, not CO2Me. Now a no, not partial. The RDKit check for 3a was also wrong: the string is the same molecule but not RDKit's canonical string.
- Substrate colour matches one of the two colours. Now a no.
- Bond/cap: 10.8 / 6 is 1.8, not 2.5. The 2.5 figure needs the 4.3 pt cap height. The crop records two cap heights (25 px and 18 px); the 1.6 figure uses 25 px. Against the card's 2.209 the replica is off, so the row stays a no.
- Arrow: the row compared against the crop (12.7) and passed it. Against the card's 11.1 the replica is 18% high. Now a no.
- Count: 11 of 19, not 14.

Not verified: the provenance of `rendered.png` as a desktop ChemDraw render of `brief_try2`. The folder holds no `brief_try2`, and the offline re-run reports `native.status: not_run`.

Tool gaps the replicator did not list: the `yield_format` template fills only bare numbers; the card's measured proportions are not applied; the card's `abbreviate_groups` omits CO2Me and CO2Et, a card-list gap. The seven gaps the replicator did list were accepted, except that the wedge and substrate-colour code paths were not read.
