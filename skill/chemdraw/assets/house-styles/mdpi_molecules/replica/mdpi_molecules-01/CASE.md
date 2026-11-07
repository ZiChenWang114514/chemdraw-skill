# Molecules (MDPI): reductive cyanation with BrCN, Scheme 1 part (c)

Source: Wu et al., "Nickel-Catalyzed Reductive Cyanation of Aryl Halides and Epoxides with Cyanogen Bromide", *Molecules* **2024**, *29*(24), 6016. DOI: [10.3390/molecules29246016](https://doi.org/10.3390/molecules29246016).

Licence: CC BY 4.0. The reference crop is reproduced under that licence.

Drawing style: the `mdpi_molecules` house style (card `toolkit/cdxml_toolkit/publication/house_styles/mdpi_molecules.json`, figure type `reaction_scheme`), applied through `draw_figure` with `style: "mdpi_molecules"`. The base preset is ACS Document 1996.

## What is reproduced

Part (c) of Scheme 1, "Reductive cyanation with cyanogen bromide (this work)", aryl-halide branch only: an aryl iodide and BrCN give the aryl nitrile under Ni with Zn or Mn. The Ni catalyst is written above the arrow and the reductant below it (in the paper the Ni sits in a circle on the arrow; the replica does not draw that). The reagent and product are drawn in one row with a plus sign between the two reactants.

Replica structures (checked with RDKit):

| ID | Role | SMILES in brief.json | Source in the crop |
| --- | --- | --- | --- |
| ArI | aryl iodide | `Cc1ccc(I)cc1` | Ar-X with X = I; Ar and X are generic in the paper, see Differences |
| BrCN | cyanogen bromide | `BrC#N` | read directly; no OCSR run |
| ArCN | aryl nitrile | `Cc1ccc(C#N)cc1` | Ar-CN with the new C-CN bond |

The brief was drawn three times. Try 1 used iodobenzene and benzonitrile. The tool then abbreviated phenyl to Ph, which the crop does not show, so try 2 used p-tolyl (`brief.json`, final). Try 2 hit the 300 s tool timeout in the render step, so the same brief was drawn once more (try 3); that render is `rendered.png`. Try 1 is kept only in the scratch folder and is not part of this case.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/mdpi_molecules/replica/mdpi_molecules-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. The replay was syntax-checked but not re-run for this case.

## Report of the final draw

- `layout`: linear; one step, one row.
- `readback`: matched, 3 structures drawn, 0 missing, 0 unexpected; `checks_passed`: true; `lint`: no issues.
- `style.applied`: bold compound label face, `new_bond_color`, `show_plus_sign`, reagent text colour, inline-plus substrate layout, and abbreviation (0 contracted, since no Ph is present).
- `style.skipped`: `conditions_split` (the brief's own above and below lines are kept), yield placement and separator (not in the card for this figure type), highlight fill and substrate colours (not in the card for this figure type).
- `warnings`: step 1 does not balance as drawn; BrI (named as the missing by-product) is not drawn. The paper draws no by-product either, and the Zn or Mn reductant is not part of the atom balance, so this is the expected result for a reductive coupling and not a drawing error.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| new C-CN bond red `#FF0000` (`new_bond_color`) | the aryl-C to CN bond formed in the coupling is red and bold | the aryl-C to CN bond is red (applied by the tool) but not bold: it is the same weight as the ring bonds | yes for colour only; bold weight not matched |
| arrow style plain | plain solid arrow | plain solid arrow | yes |
| plus sign between reactants (`show_plus_sign`) | plus between the aryl halide and BrCN | plus between the two reactants | yes |
| aromatic rings kekule (`aromatic_rings`) | Kekule rings | Kekule rings | yes |
| conditions split: catalyst above, reductant below | Ni in a circle on the arrow, Zn or Mn below | Ni as plain text above and Zn or Mn as plain text below, typed into the brief by hand (the card key is not applied and no circle symbol is drawn) | no |
| introduced group CN bold blue `#0000FF` (reaction_scheme signature) | BrCN CN and the product CN are bold blue | CN is plain black; no convention key colours or bolds a group | no |
| thin grey `#BDBDBD` frame (reaction_scheme signature) | scheme inside a grey frame | no frame | no |
| reagent text colour `#000000` (top-level) | Ni black; Zn and Mn look dark maroon at this resolution (read by eye) | all black | no |
| substrate layout inline plus (`substrate_layout`) | aryl halide stacked above the epoxide with "or", then plus BrCN | one inline pair; the epoxide branch is not drawn | partly, counted as no |
| abbreviate groups Ph, CO2Et (top-level) | aryl drawn as a ring with generic Ar; no Ph label | p-tolyl drawn as a ring; no abbreviation applied | no (the Ph abbreviation was applied to phenyl in try 1, which the crop does not show) |
| variation colour `#0000FF` (reaction_scheme) | no variation in this panel | not applicable | n/a |
| yield and selectivity formats, highlight fill null (reaction_scheme) | no yield and no highlight in this panel; teal bars are section titles outside this panel | nothing drawn | n/a |
| compound label face bold (top-level) | no compound numbers in this panel | not applicable | n/a |

Claimed rows (applicable to this panel): 10. Claimed matched: 5. Matched after audit: 4 (the conditions row is not a match, see Audit).

Proportions (bond length against label size, line weight, arrow length): these were not measured in pixels. The card records `measured` values as null for crop 01, so there is no card value to test against. Rough pixel check made in the audit (4x crops of the product region, so accurate to about 10 to 15 percent): the label cap height is about half the bond length in both images (ratio about 2.0, matching the card's bond_length_over_cap_height of 2.0); the black line width is about 0.04 of the bond length in both (card 0.042); the replica arrow is about 5 bond lengths and the crop arrow about 8, so the replica arrow is shorter, as stated above. The bold new bond is the exception: about 0.11 of the bond length in the crop (card bold 0.13) against about 0.04 in the replica.

## Differences from the paper

- Only part (c), aryl-halide branch, is drawn. The epoxide branch (R on an oxirane giving R-CH(CN)-CH2-NCO) and the "or" between the two reactant alternatives are not drawn.
- Ar is generic in the paper and X is I or Br. The replica uses p-tolyl and iodide only. p-Tolyl was chosen over phenyl so that the ring is drawn without the Ph abbreviation; the chemistry of the aryl group is not claimed.
- Ni is plain text above the arrow. In the paper it sits in a circle on the reaction arrow.
- The CN groups are plain black in BrCN and in the product; the paper writes them bold blue.
- The new C-CN bond is red but thin; the paper's is bold, about three times the weight of the ring bonds. The card's bold new bond feature is not reproduced.
- No grey frame and no teal section bar with the bold title "(c) Reductive cyanation with cyanogen bromide (this work)".
- No partial charges (delta plus and minus) over the C-X bond or the Br-CN bond.
- The paper writes the reductant "Zn or Mn" in a dark maroon colour and in bold type. The replica draws it in plain black (see the convention check).
- The missing by-product (IBr) is named in the report but not drawn; the paper does not draw it either.

## Tool gaps

- A group written on a structure cannot be coloured or bolded (for example the CN label). A species label styles only the compound label, and `variation_color` applies to variation labels only.
- No frame around a scheme and no filled section-title bar (the paper's teal bars).
- No catalyst-in-a-circle symbol on a reaction arrow. `catalytic_cycle` covers only a closed loop of steps.
- No partial-charge (delta plus and minus) annotation on bonds.
- No generic group placeholder. Each species needs a SMILES, so an "Ar" label inside a ring and a variable halogen X cannot be drawn.
- No stacking of alternative reactants on one arrow with "or". The epoxide branch cannot sit in the same figure.
- The card's `conditions_split` key is not applied by `draw_figure` (the report says the brief's above and below lines are kept).
- The brief has no arrow-length key. The arrow length follows the layout, which is what the card's `arrow_length_over_bond_length: null` leaves open.
- No weight key for a single bond: the card's bold new bond cannot be set; `new_bond_color` sets colour only.
- Reagent text takes one colour and one weight for the whole above or below line, so the maroon bold "Zn or Mn" cannot be drawn while Ni stays black.
- Free text under a species (the "X = I, Br", "aryl halides and epoxides" and "nitriles" captions in the crop) has no key in the brief keys used in this case (species, steps, above, below, arrow, style, max_width). Not tested beyond those keys.

## Audit

Checked on 2026-11-07 by reading reference.png, rendered.png, CASE.md, brief.json, replay.py and the card `mdpi_molecules.json`, with a rough pixel measurement of the product region in both images.

- The conditions row is not a match. The replica's catalyst is plain text where the paper has a circle on the arrow, and the card key is not applied, so the placement depended on lines typed into the brief by hand.
- The new-bond row counts colour only. The replica's red bond is the same weight as the ring bonds; the paper's is bold.
- The matched count is 4 of 10, not 5 as claimed.
- The proportion statements are now backed by a rough measurement and agree with the card within about 15 percent, except for the bold bond.
- Not verified here: the readback, checks_passed, lint, style.applied and RDKit results are not in this folder (there is no figure.cdxml or validation.json next to replay.py). They are the replicator's report and were not re-run. The replay was not run.
- Tool gaps added to the list: the single-bond weight, the reagent word-level colour and weight, and the free-text caption gap.
