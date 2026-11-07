# Dalton Transactions: Mn(III)/Mn(V) alcohol oxidation cycle (Scheme 4)

Source: Albrecht et al., *Dalton Trans.* 2023 (Manganese(III) complexes stabilized with N-heterocyclic carbene ligands for alcohol oxidation catalysis). DOI: [10.1039/d3dt01013a](https://doi.org/10.1039/d3dt01013a).

Licence: CC BY 3.0 (from the house-style card). The reference crop is reproduced under that licence.

Drawing style: the `dalton_transactions` house style (`brief.json` sets `"style": "dalton_transactions"`; base preset `rsc`). Figure type: `catalytic_cycle`. The tool applies only `cycle_arrow_color` for this figure type; the `coordination_complex` conventions (`dative_bond_style`, `metal_color`) are not applied by any code path, so the metal styling is not from the card.

## What is reproduced

The catalytic cycle of Scheme 4: Mn(III) complex **2** reacts with tBuOOH to give the Mn(V)=O species **C** (tBuOH released). **C** reacts with the alcohol (R, R' generic) to give the hydrogen-bonded intermediate **D** in square brackets. **D** releases the ketone and H2O and returns to **2**. Labels 2, C and D are bold. Reagents and by-products are text on the arrows, except the ketone and the alcohol, which the paper draws as structures (see Differences).

Not reproduced: the resonance partner **B** (Mn(IV)-O•), which the cycle layout drops (see Tool gaps).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/dalton_transactions/replica/dalton_transactions-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw rendering of the same brief (the first render attempt exceeded the 300 s tool limit; the single retry rendered). The readback claim (`matched` for the three species) could not be checked: this folder holds no `figure.cdxml` or `validation.json`. The step-1 atom-balance warning is explained under Differences.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| cycle_shape: circle | black arcs on an implied circle, intermediates on the circle | three straight arrows between 2, C and D, forming a triangle | no |
| cycle_arrow_color #000000 | black | black | yes |
| center_label: none | no centre label | none | yes |
| step_names: none | no step names | none | yes |
| dative_bond_style: line | metal-donor bonds are single lines | single lines, but Mn=C (carbene) and Mn=O are drawn as double bonds | no |
| cycle arcs black on implied circle, intermediates on it | yes | no (straight arrows) | no |
| reagents and by-products on short curved side arrows | curved arrows | text on straight arrows | no |
| metal-ligand bonds plain lines, never arrows | plain lines (the chelate Mn-O bonds look hashed at this resolution, unconfirmed) | plain Mn-O lines, but Mn=C and Mn=O are double bonds | no |
| metal symbol coloured by oxidation state (Mn orange, red, magenta, olive) | yes | black | no |
| bold compound numbers with bold letters | 2, B, C, D bold | 2, C, D (B omitted); bold weight not verifiable from this folder | no |
| compound_label_color #000000 | black | black | yes |
| arrow_style plain | plain arrows | plain arrows | yes |
| reagent_text_color #000000 | black | black | yes |
| heteroatoms coloured by element | O, N and Mn coloured in the paper | all atoms black | no |
| conditions_split: reagents above, solvent below | tBuOOH above; the alcohol enters from below | tBuOOH above; R-CH(OH)-R' label sits above the C-to-D arrow in rendered.png (brief.json says below); tBuOH left of and below the arrow (paper: right of the arc) | no |

Claimed: 15. Matched: 8 (replicator). Matched after audit: 6 (see Audit).

Bond length, line width and arrow length were not compared. The card's measured values are not null (`bond_length_over_cap_height` 2.3, `line_width_over_bond_length` 0.07, `arrow_length_over_bond_length` 6.9), and crop 05 records a 2 px line width; no code path reads these keys, so they could not be enforced either. The `abbreviate_groups` tBu rule is not tested, because the replica writes tBuOOH and tBuOH as text and draws no tBu structure.

## Differences from the paper

- **Ligand.** The paper's donor is drawn as a bare C with curved backbone arcs to two O atoms. The replica uses a 1,3-disubstituted imidazol-2-ylidene with two CH2-aryl-O arms: N atoms and benzene rings are drawn, and the paper shows neither. The ligand identity was inferred from the arcs in the crop; it was not checked against the paper's full text or SI.
- **Carbene bond.** The NHC-Mn bond is drawn as a double bond (the carbene resonance form); the paper draws a single line.
- **Acetylacetonate.** The paper shows a chelating O,O-acac ring. The replica draws a monodentate Z-enolate on one O, which places the enol over the aryl ring of the ligand.
- **Oxo and metal labels.** In C the oxo O sits on the Mn label; ChemDraw flags the label clash, and the automatic re-layout does not clear it.
- **Mn(III)/Mn(V)/Mn(IV) states.** The paper gives superscript roman numerals and colours each Mn by oxidation state. The replica has neither.
- **B.** The paper draws C and B side by side with a double-headed resonance arrow. The replica omits B; the cycle layout does not draw it.
- **Reagent and by-product structures.** The paper draws the ketone (R2C=O), H2O and the alcohol as structures. The replica writes them as text (R2C=O + H2O; R-CH(OH)-R'). The catalytic-cycle layout did not draw them as structures.
- **Intermediate D.** The paper shows an H-bond from the carbinol O-H to the Mn-OH with dotted lines, and the carbinol C-H as a partial bond. The replica places the alkyl radical fragment `R-C(•)(OH)-R` as a separate molecule above the Mn complex inside the square bracket. The bracket matches the paper's square bracket with no dagger.
- **Generic groups.** R and R' are drawn as `*` atoms in the SMILES; ChemDraw shows them as R. Because of them, steps 2 and 3 cannot be atom-balanced, and step 1 is flagged as unbalanced because the text-only tBuOOH supplies no O. This is a true warning: the oxo O comes from tBuOOH, which is not a structure in this layout.
- **Arrows.** The paper's cycle and side arrows are curved; the replica's are straight.

## Tool gaps

- The `catalytic-cycle` layout draws only cycle intermediates. Reagents, by-products and products given as species are dropped (the readback lists them as `missing`), so the entering and leaving substrates have to be text lines. Text does not count toward atom balance.
- The cycle layout draws straight arrows between nodes; the `catalytic_cycle.cycle_shape: circle` convention and curved side arrows are not produced.
- A resonance step inside a catalytic cycle does not draw its partner (B was missing and the layout duplicated C), so C and B cannot be shown as the paper's resonance pair.
- SMILES cannot express the bidentate O,O-enolate of acetylacetonate with two single Mn-O bonds: a valid SMILES needs a charge or an extra bond order. A dative or chelate bond option is missing from the brief.
- An acyclic enol C=C with no E/Z specified makes the layout fail with `chemical_semantics_changed`; the stereo had to be written as Z.
- No per-atom colour: the metal and donor colours from the card (Mn by oxidation state, O and N colours) cannot be given in the brief, and the house style applies no element colours in this layout.
- No superscript or oxidation-state annotation on species labels.
- Dotted or partial bonds (H-bonds, the C-H bond being broken in D) cannot be drawn; D's alkyl fragment is a separate molecule.
- Generic R groups (`*`) cannot be atom-balanced, so steps that contain them are reported as unchecked.
- Label-clash lint (oxo O against Mn) is reported but not fixed by the automatic re-layout.

## Audit

Second-pass review of reference.png, rendered.png, brief.json, the card (`dalton_transactions.json`) and the toolkit's figure code. No re-render was made. Matched count: 6 of 15 (not 8). The six are cycle arrow colour, centre label none, step names none, compound label colour, arrow style plain, reagent text colour. Five of these hold by default or by absence (the tool lists `center_label` and `step_names` as skipped guidance, the colour steps are no-ops at #000000, and arrow style plain is the default); only `cycle_arrow_color` is set by a drawing step.

Overclaims corrected above:
- Bold compound labels were marked matched although B is missing and the label weight cannot be checked here.
- Plain metal-ligand bonds: the replica's Mn=C and Mn=O are double bonds, and the paper's chelate Mn-O bonds look hashed (unconfirmed).
- Conditions: the alcohol label sits above the C-to-D arrow in rendered.png, not below.
- The coordination_complex conventions were not applied by the tool.
- The paper draws the ketone and the alcohol as structures, not text.
- The measured geometry was not null; the card and crop 05 have values, and no code reads them.
- The readback claim cannot be checked: no figure.cdxml or validation.json is in this folder.

Not matched on inspection (not in the table): the canvas aspect ratio differs (reference 748x535, about 1.40:1; rendered 1086x968, about 1.12:1); no element or metal colour (rendered has no saturated pixels; reference has orange, red, magenta and olive); tBuOOH and tBuOH carry an italic t in the reference and upright in the replica; the oxo O collides with the Mn label in C, and the acac enolate crosses the aryl ring in 2.

Tool gaps the replicator missed:
- The card's measured geometry keys (`bond_length_over_cap_height`, `line_width_over_bond_length`, `arrow_length_over_bond_length`) are read by no code, so bond length, line width and arrow length cannot be set from the card.
- For catalytic_cycle only `cycle_arrow_color` is applied. `center_label`, `step_names`, `intermediate_label_style`, `curved_arrow_color` and `cycle_shape` are accepted but reported as skipped guidance, so lettered intermediates cannot be styled beyond the compound-label face.
- `conditions_split: reagents_above_solvent_below` is not enforced; above and below lines are kept as given.
- The coordination_complex keys (`dative_bond_style`, including the value `dashed`, `metal_color`, `formal_charge_style`) are never applied for any figure.
- I found no brief key for run formatting on text lines, so italic t, italic R and R', and oxidation-state superscripts cannot be written on text reagents. The only superscript is the ts_bracket marker.

Tool-gap claims checked and accurate: no circle cycle shape, no curved side arrows, no resonance partner drawn, no chelate or dative option (a neutral O,O-acac chelate with two single Mn-O bonds needs a charge on the carbonyl O), no per-atom label colour, no dotted or partial bonds, no superscript on species labels, and generic atoms left unbalanced. The `chemical_semantics_changed` error for an unspecified enol C=C is not checked here.
