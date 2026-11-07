# JACS Au, Figure 5D: computed mechanism of the Co-mediated bromoalkylation (chemistry steps only)

Source: Gilmour et al., "Chloroalkylation of unactivated alkenes via a cobalt-mediated radical ligand transfer", *JACS Au* **2025**. DOI: [10.1021/jacsau.5c01211](https://doi.org/10.1021/jacsau.5c01211).

Licence: CC BY 4.0. `reference.png` is the house-style evidence crop `evidence/jacs_au-07.png` (Figure 5D), reproduced under that licence.

Drawing style: the `jacs_au` house style in `brief.json` (base preset ACS Document 1996; bold compound labels, abbreviated Me and NO2, plain reaction arrows); see `cdx.py styles jacs_au`.

Figure type: `energy_profile`.

## What is reproduced

Only the structures of the pathway, drawn as a two-step scheme with `draw_figure`:

1. `[CH2][N+](=O)[O-]` (nitromethyl radical) + `CC=C` (propene) gives `C[CH]CC[N+](=O)[O-]` (Int-III, bold label, radical doublet). This is the radical addition at the terminal alkene carbon.
2. Int-III + `BrC[N+](=O)[O-]` (bromonitromethane) gives `CC(Br)CC[N+](=O)[O-]`, the Br-transfer product at -39.5 kcal/mol. The by-product CH2NO2 radical is named as missing by the tool and not drawn.

Not reproduced: the free-energy curve, the stationary-point values, the ΔG axis arrow, the transition-state brackets, the barrierless branch to the Cl product, the photoexcitation arrow, the Ir, Co, Ag and Li species with MeCN ligands, the Cl product, and the blue ω annotations. The `draw_figure` tool has no energy-profile kind.

Structures were read from the 900 px crop by eye; OCSR was not run. Connectivity is Me-CH(•)-CH2-CH2-NO2 for Int-III and Me-CHBr-CH2-CH2-NO2 for the Br product. The SMILES were checked with RDKit (they parse and canonicalise).

## Replay

```
python skill/chemdraw/scripts/cdx.py py -I skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw rendering of the first brief (downscaled from 1425 px to 1200 px wide).

## Brief iterations

- Try 1 (`brief.json`): as above. Rendered with `--render`; `readback` matched 6 structures, `checks_passed` false because step 2 does not balance (CH2NO2 by-product named, not drawn).
- Try 2: added `[CH2][N+](=O)[O-]` as a second product of step 2 to balance it. The tool refused it: "The steps form a cycle: a product feeds back into its own route." Try 1 is kept.

No third brief was tried: the remaining gaps are in the tools and the card, not in the brief.

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_unit kcal/mol | ΔG values in kcal·mol-1 | no energy values | no |
| energy_label delta_G on an up arrow | italic ΔG (kcal·mol-1) on an up arrow, top right | no arrow | no |
| no y axis | no axis | no axis, but no energy profile is drawn, so there is no axis to compare | no |
| level_style smooth_curve | one smooth thick grey curve through all stationary points | no curve; rows of structures | no |
| pathway_colors #889897 | grey #889897 pathway | black bonds, no pathway colour | no |
| ts_marker bracket_double_dagger | TS in square brackets with double dagger | no TS drawn | no |
| stationary points as black dots with plain values, "complex" in grey italics | yes | none | no |
| branch as second grey curve labelled barrierless | yes | none | no |
| species along the curve; halogens as pink and blue discs | Br pink #CC6AE5, Cl blue #4F8EDB | Br as black text; no Cl | no |
| photoexcitation as dashed vertical arrow from navy bulb | yes | none | no |
| compound label face bold | Int-III bold | Int-III bold | yes |
| compound label colour #000000 | black | black | yes |
| label font Arial (checked by eye, not measured) | sans-serif labels | sans-serif labels; font not measured and the CDXML font not checked | no |
| abbreviate_groups Me, NO2 | Me, NO2 | Me, NO2 | yes |
| arrow_style plain | straight black reaction arrow in the Co box | plain solid arrows | yes |
| radical dot on radical centres | radical dot on TS brackets | radical doublet stored in the CDXML, no dot visible in the PNG | no |

Claimed 16, matched 6. After audit, 4 of 16 hold (see Audit).

## Differences from the paper

- The paper's figure is a single energy profile; the replica is two rows of structures. Energies, the curve, the TS brackets and the photoexcitation step are absent.
- Step 2 does not balance as drawn; the CH2NO2 radical that the chain regenerates is not drawn (the tool refuses the cycle).
- The Br atom is black text, not the paper's pink disc. The Cl product and the Cl transfer from CoIII-5 are not drawn.
- A "+" is drawn between the radical and propene in step 1. The paper's crop shows no plus sign for this part.
- The two starting materials of step 1 (nitromethyl radical and propene) are read from the -23.3 kcal/mol species and are an inference, not labelled as such in the paper.
- No conditions are drawn; the crop gives none for these steps.
- The lint check flagged a crowded plus and widened the gaps once; the two steps are on separate rows.
- Proportions (bond length against label cap height) were not measured; the comparison is by eye against the `jacs_au` preset (bond length 14.4 pt).

## Tool gaps

- No energy-profile drawer: no smooth pathway curve, no stationary-point dots with values, no ΔG up arrow, no per-pathway colour, no second branch curve.
- A transition-state bracket needs a valid SMILES species. The Br-transfer TS, with Br bridging the chain carbon and CH2NO2, is a three-centre bond that a normal SMILES cannot hold, so `ts_bracket` cannot express it; partial-bond radical-addition TSs have the same problem.
- Radical dots are not shown: the CDXML stores `Radical="Doublet"` on the radical nodes, but the ChemDraw render of Int-III and of the CH2NO2 starting material has no dot.
- Chain propagation (a product that feeds step 1) is refused as a cycle, so the radical chain cannot be drawn.
- No option to draw halogens as coloured discs (the card's Br pink and Cl blue convention).
- Organometallic and photocatalyst species (Ir photocatalyst, CoIII-4(Ag)+, CoIII-5, CoII-6, AgCl, AgBr, LiCl(MeCN)3, MeCN ligands) cannot be drawn by name, since the curated table and PubChem do not hold them; no SMILES was invented for them.
- No way to place energy values or ω annotations beside a species; step text is limited to `above` and `below` lines.
- No dashed arrow from a light-source disc (photoexcitation step).
- The crowded-plus lint check still fires after the one automatic re-layout (2.5 pt clearance).

## Structure issues

- Int-III (Me-C•H-CH2-CH2-NO2) and the Br product (Me-CHBr-CH2-CH2-NO2) are read from a 900 px crop; the chain length and radical position were not checked at higher resolution.
- The -23.3 kcal/mol species is read as propene plus a nitromethyl radical; the crop shows the alkene with a radical dot and a separate CH2NO2 fragment, so the pairing is an inference.
- The [BrCH2NO2]•- radical anion at -15.4 kcal/mol, the Ag and Li salts and the Co complexes were not drawn.

## Audit

Audited against `reference.png`, `rendered.png` and the `jacs_au` card (`toolkit/cdxml_toolkit/publication/house_styles/jacs_au.json`, `energy_profile` type).

- Overclaims corrected: "no y axis" was marked as a match, but no energy profile is drawn, so the row is vacuous. "label font Arial" was marked as a match without a measured font. The replicator's own note says it was checked by eye only, and the CDXML font was not checked.
- Holds: the bold "Int-III" label, black label colour, the Me and NO2 abbreviations, and a plain arrow style. The arrow is solid, unbarbed and not curved.
- Not matched, proportion: the arrow in `rendered.png` is 253 px long and the bond is about 35 px by eye at 2x zoom, a ratio near 7. The card gives 3.2 (crop 01) and the reference crop 07 gives 330/66 = 5.0. The "comparison by eye" in the Proportions section does not hold for arrow length. Bond-to-cap-height (about 1.9 against the card's 2.06) is close but not measured precisely. Line weight is not measured.
- The card itself is inconsistent: `measured.label_font` lists Arial as measured, while this case says it was not. The card's `arrow_length_over_bond_length` of 3.2 comes from crop 01 only; crop 07 gives 5.0.
- Radical dot: confirmed absent in both rows of `rendered.png`. The CDXML `Radical` flag was not inspected, so the cause is unverified.
- Tool gaps the replicator missed: (a) free-text colour, italic and superscript runs, needed for blue ω values, grey italic "complex", italic ΔG and Ir/Co oxidation-state superscripts; (b) square brackets around a non-TS species with a charge or radical mark, such as [BrCH2NO2]•−; (c) curved or angled reaction arrows, including arrows from a species to a leaving group and the curved AgCl/AgBr arrows; (d) free 2D placement of species at arbitrary x,y, since `draw_figure` only lays out rows; (e) framed or dashed boxes and embedded images, such as the 3D model inset; (f) a loop-back arrow for a closed radical chain, since the cycle refusal blocks the chain as drawn.
- Corrected count: 4 of 16 conventions match.

