# Sarpong group: BF3-promoted diazomethane ring expansion (Figure 2B, top band)

Source: Sarpong et al., *Nat. Commun.* **2024** (Late-stage benzenoid-to-troponoid skeletal modification of the cephalotanes: total synthesis of harringtonolide). DOI: [10.1038/s41467-024-48586-6](https://doi.org/10.1038/s41467-024-48586-6). Licence: CC BY 4.0. Reference crop: `evidence/sarpong_group-03.png` (Figure 2B, top band, 900 x 244 px), copied here as `reference.png`.

Figure type: `mechanism` (house style card `sarpong_group`, `figure_types.mechanism`).

## What is reproduced

The mechanism pattern of the desired pathway: a BF3-activated ketone takes up CH2N2 (carbonyl addition), and the alkoxide-diazonium intermediate undergoes a 1,2-shift of a ring bond to the CH2 carbon with loss of N2, giving the ring-expanded ketone.

The paper's substrate 20, the intermediates 21, 22 and 22' and harringtonolide (4) are caged polycycles. The crop is 900 x 244 px, and the cage bonds cannot be read with confidence at that size, so the brief uses a cyclohexanone model: 1 (cyclohexanone) + CH2N2 gives 2 (alkoxide-diazonium), and 2 gives 3 (cycloheptanone) + N2. Labels 1 to 3 are model numbers, not the paper's numbering. Five two-electron curved arrows are drawn in the house colour and weight. The tool reports both steps as atom and charge balanced.

Model SMILES (checked with RDKit: C6H10O + CH2N2 gives C7H12N2O; C7H12N2O gives C7H12O + N2):

- 1: `O=C1CCCCC1`
- CH2N2 (carbanion resonance form): `[CH2-][N+]#N`
- 2: `[O-]C1(C[N+]#N)CCCCC1`
- 3: `O=C1CCCCCC1`
- N2: `N#N`

Step 1 conditions copied from the paper: BF3·OEt2 above, CH2Cl2 below. Step 2 has no conditions in the crop.

## Replay

`python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-03/replay.py NEW_DIR` writes `figure.cdxml` and `validation.json` (checked: `checks_passed` true, readback matched). `rendered.png` is the desktop ChemDraw render of the same brief, downscaled to 1200 px wide. The `cdx.py draw` CLI hung on this brief, so the replay and the render use the runtime call (see Tool gaps).

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| curved_arrow_color #800000 | dark red electron-pushing arrows | #800000 arrows (applied by the card) | yes |
| curved_arrow_weight thin | arrows thinner than bonds | thin arrows (applied by the card) | yes |
| show_lone_pairs false | no lone pairs drawn | none drawn | yes |
| formal_charge_style plain | plain BF3 minus and N2 plus | plain O minus and N plus | yes |
| intermediate_label_style bold_number | bold 20, 21, 22, 22' | plain 1, 2, 3 | no |
| compound_label_face bold | bold numbers | plain (scheme-only convention, skipped for mechanisms) | no |
| compound_label_color #000000 | black | black | yes |
| compound_label_italic_suffix false | no suffix | no suffix | yes |
| reagent_text_color #000000 | black | black | yes |
| conditions_split reagents_above_solvent_below | BF3·OEt2 and CH2N2 above, CH2Cl2 below | BF3·OEt2 above, CH2Cl2 below; CH2N2 drawn as a reactant structure left of the arrow, not above it | no |
| arrow_style plain | dashed shafts on all four arrows in the crop (see the dashed row below) | plain solid shafts | no |
| dashed reaction arrows between intermediates | all four arrows dashed | solid (dashed not allowed for mechanism steps) | no |
| intermediates in square brackets | one bracket pair spanning 21 to 22' | none | no |
| teal dot on the reacting carbon | teal dot on the CH2 carbon of 21 | none | no |
| dashed grey frame with underlined bullet title | present | none | no |
| curved arrows drawn over the cage | over the caged skeleton | over a cyclohexanone model | no |
| bold heavy bonds on the near face of caged polycycles | present on 20, 21, 22' and 4 | plain model bonds | no |
| natural-product name bold italic blue under the target | "harringtonolide (4)" in plain black, only "(4)" bold | none drawn | no |

Abbreviation convention OMe, Boc, tBu: not applicable, since no such group is drawn in the model (the paper writes the ring methoxy as MeO). Not counted.

Matched 7 of 18 conventions after audit (the first draft claimed 9 of 18; see Audit).

## Differences from the paper

- Substrate: the cyclohexanone and cycloheptanone model replaces the caged 20 to harringtonolide (4) sequence. The cage, the bridging ether and lactone, and the methyl groups are absent.
- Labels: plain 1 to 3 instead of bold 20, 21, 22, 22' and harringtonolide (4).
- Arrows: solid in the replica; all four arrows in the crop are dashed.
- Intermediates: no square bracket pair around 21 to 22'.
- Reacting carbon: no teal dot.
- BF3: the paper draws an O-BF3 bond on the alkoxide in 21; the replica has O minus, with BF3·OEt2 as condition text.
- CH2N2: drawn as a substrate structure in the first row, whereas the paper writes it above the arrow.
- Steps 22 to 22' and 22' to 4 (tautomerisation and oxidation-state change of the tropone precursor) are not reproduced.
- No dashed grey frame and no underlined "desired pathway" title.
- The energy-profile labels TS1 (11.7) and TS2-C (10.1) at the bottom edge of the crop are not drawn.

## Tool gaps

- Mechanism steps accept only arrow `solid`, `reversible` or `resonance`, so the dashed reaction arrows of the card cannot be drawn. This is limited to `kind: "mechanism"`: the scheme path of `draw_figure` accepts `dashed`, but it cannot draw curved arrows.
- Mechanism species refuse `ts_bracket` and `atom_halos` (error: unknown keys). Square brackets around intermediates and a coloured dot on a reacting atom are therefore not available for mechanism figures. The scheme path has both keys, so the same limit again applies to mechanisms only.
- `compound_label_face: bold` and `intermediate_label_style: bold_number` are skipped for mechanisms (the style report lists them as scheme-only), so mechanism labels stay plain.
- No frame or titled box around a pathway, and no bond-width setting for heavy bonds on a caged skeleton.
- No way to draw the O-BF3 coordination on the alkoxide in a mechanism species. Dative SMILES on mechanism species were not tried.
- No per-atom or per-bond colour key on a mechanism species (its species keys are `id`, `smiles`, `name`, `label`), so changed atoms or bonds cannot be coloured, as the card's signature feature asks.
- No style key on a mechanism species label, so a bold or bold italic blue name cannot be set.
- `cdx.py draw` (with and without `--render`) returned `worker_crashed` (exit 143 after about 90 s) for this brief and for the documented aldehyde/hydroxide mechanism example. The same brief run through `cdx.py py` calling `draw_figure` finished in about 2.5 s without render and about 5 s with `render=True`, which wrote the PNG.

## Audit

A second reader checked `reference.png`, `rendered.png`, `brief.json`, the house card and the toolkit source (`figure_mechanism.py`, `figure_house.py`, `figure_draw.py`). Nothing in the case folder was regenerated.

Overclaims corrected:

- `conditions_split` was marked yes. The paper stacks CH2N2 with BF3·OEt2 above the arrow, but the replica draws CH2N2 as a reactant structure. The `above` key takes a list (`_text_lines` in `figure_mechanism.py`), so CH2N2 could have been set as text above the arrow. The structure was a choice, not a tool limit.
- `arrow_style` was marked yes. The paper column said plain shafts, but all four reaction arrows in `reference.png` are dashed. The replica's solid shafts do not match.
- The count falls from 9 of 18 to 7 of 18.

Rows kept as matched:

- `curved_arrow_color` and `curved_arrow_weight`: `figure_house.py` sets the colour to #800000 and the width to 0.75 times the line width on curve elements. Fully covered red pixels in `rendered.png` sit near 128 (spread 116 to 135 from downscaling), so the exact hex is not confirmed from the render. The arrow weight was not measured in pixels.
- `show_lone_pairs`, `formal_charge_style`, `compound_label_color`, `compound_label_italic_suffix`, `reagent_text_color`: consistent with `rendered.png` by eye.

Mechanism tool gaps confirmed in source: the arrow list (`MECH_ARROWS`), the species keys, and the scheme-only skip message for label styles.

Not verified:

- `validation.json` and the readback claim in the Replay section: no such file is in the case folder, and the replay was not rerun.
- The `cdx.py draw` `worker_crashed` report: not rerun.
- Yield placement and format: neither image shows a yield, so this is not applicable and not counted.
- Abbreviations: the paper writes MeO and Me, while the card lists OMe. No such group is drawn in the replica, so this is not counted.
- Proportions and line weight against the paper: the card's measurements come from a 2000 px figure, not this 900 px crop, and were not measured here.
- Layout: the paper is a five-structure band with a dashed frame. The replica is a three-structure scheme. This is a clear mismatch but is not one of the table rows.
