# Dalton Transactions: CuAAC catalytic cycle (Scheme 4, crop 03)

Source: Martins et al., "Borane-functionalized heteroscorpionate copper complexes as catalysts for azide-alkyne cycloaddition", *Dalton Trans.* **2025**. DOI: [10.1039/d5dt01595b](https://doi.org/10.1039/d5dt01595b).

Licence: CC BY 3.0, as recorded in the house-style card. The reference crop is reproduced under that licence.

Drawing style: the `dalton_transactions` house style in `brief.json` (base preset RSC; bold compound labels, black reagent text, black cycle arrows); see `cdx.py styles dalton_transactions`.

Figure type: `coordination_complex` and `catalytic_cycle` (the card lists crop 03 under both).

## What is reproduced

The main copper cycle of Scheme 4: copper(I) alkyne complex **4** plus benzyl azide gives the azide-bound intermediate **I+**; base gives copper acetylide **II**; cycloaddition gives the copper triazolide **III**; protonolysis by phenylacetylene releases 1-benzyl-4-phenyl-1,2,3-triazole and regenerates the alkyne complex. The cycle is drawn with `draw_figure`, `layout: "catalytic-cycle"`, and the card's cycle arrow colour.

Not reproduced: the precursor **2b** and the "- 2 MeCN" step above **4**, the product box, the blue "directing effect" lines, and the curved reagent arrows.

## Structures used

| ID | Structure in brief.json | Note |
| --- | --- | --- |
| 4 | Cu(I) bound to a simplified bis(3,5-dimethylpyrazol-1-yl)methane donor and to phenylacetylene | ligand simplified, see Differences |
| I+ | 4 plus the benzyl azide bound to Cu | azide coordinated by a dative bond |
| II | Cu(I) with the ligand, the acetylide and the azide | neutral in the drawing |
| III | Cu bonded to C5 of 1-benzyl-4-phenyl-1,2,3-triazole | Cu on the carbon next to N-benzyl, as in the paper |
| IV+ | Cu complex with phenylacetylene, plus the free triazole as a second fragment | label falls under the triazole, see Differences |
| R'N3 | written as benzyl azide | R' is not given in the crop |

Ligand and azide SMILES are in `brief.json`. Nothing was taken from OCSR: the paper's ligand (a borane-tethered heteroscorpionate with R2B and R groups) was not read reliably from the crop, so it was replaced by a simpler donor rather than guessed.

## Replay

```
python skill/chemdraw/scripts/cdx.py py -I skill/chemdraw/assets/house-styles/dalton_transactions/replica/dalton_transactions-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the PNG with `reference.png`; `rendered.png` is not produced by `replay.py`. The audit rerun wrote `validation.json` with `native.status: not_run`, so the claim that `rendered.png` is a ChemDraw render of this brief is unverified.

The draw report has `checks_passed: false`: `readback` reports `mismatch` because ALK, AZ and PROD are used in steps but not drawn as their own structures, and two steps are flagged as unbalanced (missing H). See the notes below.

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| Compound labels bold | bold 4, I+, II, III, IV+ | bold labels | yes |
| Compound label colour black | black | black | yes |
| Reagents above arrow, solvent below | R'N3 and DIPEA above; no solvent given for the cycle | reagent text above arrows; nothing below | yes |
| Arrow style plain | plain | plain | yes |
| Aromatic rings Kekule | Kekule | Kekule | yes |
| Reagent text colour black | black | black | yes |
| Metal-ligand bonds as plain lines or hashed wedges, never arrows | Cu-N as hashed or plain lines | Cu-N and Cu-alkyne drawn as dative arrows with arrowheads (all 15 metal-ligand bonds, one style) | no |
| Formal charge as plain superscript on the metal | Cu+ plain | Cu+ plain | yes |
| Cationic complex with plain + on the metal | plain + on Cu in 4, I+, IV+ | plain + on Cu in 4, I+, IV+ | yes |
| Cu coloured brown (#804000) | brown | black | no |
| Donor N coloured blue | blue | black | no |
| Alkyne bonded to Cu by a single line | single line | dative arrow from the alkyne terminus | no |
| Cycle arrows black | black | black | yes |
| Cycle drawn as arcs on an implied circle | black arcs | straight chords between intermediates | no |
| Intermediates sit on the circle | yes | roughly on a circle | partial, counted as no |
| No centre label | none | none | yes |
| No step names | none | none | yes |
| Intermediate labels bold roman | I+, II, III, IV+ bold | I+, II, III, IV+ bold | yes |
| Reagents and by-products enter and leave on short curved side arrows | curved side arrows; [DIPEA]HX leaves | straight arrows with text labels; no by-product drawn | no |
| Product in a rounded grey frame with shadow | triazole boxed | not drawn | no |
| Secondary interactions as blue dashed lines (#0000F8) with blue label | "directing effect" lines | not drawn | no |
| Precursor 2b and "- 2 MeCN" step before 4 | present | not drawn | no |
| Label font Arial (card `label_font`) | Arial | Helvetica (font id 4, RSC preset); card font not applied | no |
| Line width about 0.07 of bond length (card `line_width_over_bond_length`) | about 0.07 (2.5 px on a 38 px bond, crop 02) | 0.60 pt on a 12.2 pt bond, about 0.049 | no |
| Arrow length about 6.9 bond lengths (card `arrow_length_over_bond_length`) | about 6.9 (crops 02, 04) | 2.3 to 4.8 bond lengths (measured in `figure.cdxml`) | no |
| IV+ label on the Cu complex that carries the triazole | IV+ under the Cu complex | IV+ under the free triazole fragment | no |

Matched 12 of 26 convention rows in the table. The earlier count said 12 of 21, but the table had 22 rows; the four rows added in the audit are all unmatched.

Not measured: bond length over cap height (label cap height was not measured on the replica). The replica is at the RSC preset bond length (12.2 pt). Arrow length and line width were measured from `figure.cdxml` (rows above). No pixel measurement of the paper crop was taken for this comparison.

## Differences from the paper

- Ligand: the paper's heteroscorpionate (borane tether, R2B and R groups) is replaced by bis(3,5-dimethylpyrazol-1-yl)methane. The boron pendant is omitted.
- R' is drawn as benzyl; the paper does not give R' in the crop.
- The pi-bound alkyne of 4 and I+ is written as a dative bond from the alkyne terminus. Whether a two-bond eta2 SMILES draws was not tested in the audit; the one-bond dative stand-in is the replica's choice.
- Charges: the paper's 4, I+ and IV+ are cations with counter-ions. Here 4 and I+ carry a Cu+ charge, II and III are drawn neutral, and the counter-ion and the [DIPEA]HX by-product are not drawn. A BF4- counter-ion can be written as a dot-separated fragment (tested in the audit: it draws, and only the balance warning follows), so leaving it out is a choice. The balance warnings for steps 2 and 4 are the result.
- IV+ is a two-fragment species (Cu complex plus free triazole). The IV+ label therefore sits under the triazole rather than under the Cu complex.
- Precursor 2b and its arrow are not drawn; the cycle starts at 4.
- Arrows between intermediates are straight segments, not arcs on a circle, and the reagents are text, not structures.
- Overlap: in III the methyl of the pyrazole C3 points down onto the phenyl ring of the triazolide. The lint check reported no issue (the issues list is empty in the audit rerun), so the overlap was not confirmed at render resolution.
- Colour: the Cu, donor N and the dative bonds are all black in the replica; the paper's Cu brown and N blue are absent.

## Tool gaps

- Dative bonds (`Order="dative"`) render as arrows with arrowheads. `house_styles.py` lists `dative_bond_style` with the values `arrow`, `line` and `dashed`, but no code reads it, so the card's `dative_bond_style: line` cannot be met from a brief.
- Metal colour, donor-atom colour, `formal_charge_style` and the other `coordination_complex` conventions are dropped without a skipped entry. The house-style code applies only the section for the brief's own figure type, so a `catalytic_cycle` brief never reads the `coordination_complex` section. The replay's skipped list confirms the silence.
- Catalytic-cycle layout draws straight chords. There is no circular arc arrow and no option to place intermediates on an implied circle with arcs.
- Reagent and by-product side arrows are straight with text labels. There is no curved short side arrow and no by-product drawn on the arrow.
- No rounded grey frame with shadow for a cycle product. `highlight_fill` is listed for `catalytic_cycle` in `house_styles.py` but is not applied; the card's own value for it is null.
- No blue dashed secondary-interaction line with a coloured text label in the `draw_figure` brief.
- Counter-ions: the earlier claim that BF4- cannot be written was wrong. A dot-separated BF4- fragment is accepted and drawn (tested in the audit), and the step-balance check then warns. The real limit is the eta2 alkyne, which was not tested as a two-bond SMILES.
- Overlap lint misses a pyrazole methyl that runs into the phenyl ring of the triazolide in III (the issues list is empty in the rerun).
- Readback compares only drawn structures. ALK, AZ and PROD are reported missing (confirmed in the rerun), so `checks_passed` is false. This is partly a brief choice: these species are listed in `species` but used only as reagent text or free fragments.
- Gaps the replica did not list: the card's label font (Arial) is not applied and is not in the skipped list; the card's line width (0.07 of bond length) is not applied; there is no arrow-length control for the catalytic-cycle layout (drawn arrows are 2.3 to 4.8 bond lengths against the card's 6.9).
- A compound label cannot be tied to one fragment of a dot-separated species, so IV+ falls under the free triazole.
- `draw_figure` does not render natively by default (`native.status: not_run` in the rerun), so the drawing gate needs a separate render step.
- Not tool gaps: the 2b precursor and the MeCN ligands can be written as SMILES, and "- 2 MeCN" as above-arrow text. They were left out by choice.

## Notes on the brief

Three brief versions were drawn (`brief_try1` to `brief_try3` in the scratch folder). The third is the one kept as `brief.json`. It still has two unbalanced steps (step 2, base to II; step 4, III plus alkyne to IV+), because the by-products were not written as species.

## Audit

Audit date 2026-11-07. Checked against reference.png, rendered.png, brief.json, the `dalton_transactions` card, and a rerun of `replay.py` into a temporary folder (its `figure.cdxml` and `validation.json` are not in this folder).

- Confirmed from the rerun: bold compound labels (bold face on 4, I+, II, III, IV+); black labels and reagent text; Cu+ as a plain superscript; Kekule bonds (no order 1.5); black cycle arrows; 15 dative bonds; `checks_passed` false; readback missing ALK, AZ and PROD; steps 2 and 4 unbalanced; lint issues empty.
- Corrected: the count (12 of 21 became 12 of 26); the claim that replay gives `native.status: rendered` (it gives `not_run`); the counter-ion tool gap; the "styles mixed" wording (all metal bonds are one dative style); the arrow length, which is measured now and does not match; the missing label-font and line-width rows.
- Not verified: `brief_try1` to `brief_try3` (not in this folder); the provenance of `rendered.png`; the III overlap at render resolution; the Kekule row for the paper, which rests on the pyrazole and triazole rings because the crop draws no benzene ring.
- Yield and condition-placement rows do not apply: crop 03 draws no yield, and the card's `yield_placement` is null.
