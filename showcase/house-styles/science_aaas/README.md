# Science / Science Advances house style

How reaction schemes are drawn in Science and Science Advances, measured from open-access figures. Machine-readable card: `toolkit/cdxml_toolkit/publication/house_styles/science_aaas.json` (base preset `nature`; the journal uses similar small sans-serif labels).

## Sources (CC BY 4.0)

- Choudhary, Zhang and Lin, Sci. Adv. 2024, 10, eadp7544, DOI 10.1126/sciadv.adp7544: Fig. 3 (`evidence/science_aaas-01.png`) and Fig. 4 (`evidence/science_aaas-02.png`).
- Zhao et al., Sci. Adv. 2024, 10, eadq0028, DOI 10.1126/sciadv.adq0028: Fig. 3 (`evidence/science_aaas-03.png`).

All three crops are substrate-scope figures: a core reaction header above a grid of scope products. The card records them as the `substrate_scope` figure type.

## Measurements

Pixel readings from the crops. Crops 01 and 02 (Choudhary et al.) agree; crop 03 (Zhao et al.) is recorded where it differs.

- Arrow shaft / bond length: 15.4 (crops 01 and 02: 15.3 to 15.5). Crop 03 gives 7.7, a shorter arrow in the Zhao et al. scheme.
- Line width / bond length: 0.043 (crops 01 and 02: 2 px on a 47 px bond). Crop 03 records 3 px on a 43 px bond (0.070).
- Bold (new-bond) width / bond length: 0.115 (crops 01 and 02: 5.4 px on a 47 px bond).
- Bond length / atom-label cap height: 1.935 on the card, not yet reproduced. The TIPS labels measure about 30 px cap height in crops 01 and 02 (ratio about 1.57). Re-measure before relying on it.
- Atom labels: Arial or Helvetica, about 8 pt at print size.

## Conventions

- Compound numbers bold, suffix not italic. Black in Choudhary et al.; blue in Zhao et al. The card uses black.
- Yield as a plain percentage after the number on the same line. Choudhary et al. writes `3a, 88%`; Zhao et al. writes `2a: 89%` with the yield in blue. The card uses `, `.
- Incoming component blue, #0202F4: the amine in Choudhary et al., both in the reagent and in the product. In Zhao et al. the incoming Br is blue in the product only (#0B04CE). The rest is black.
- Newly formed bond red, #F80302, in Choudhary et al. (bold amide C-N bond). Zhao et al. colours its formed C-Br bond blue. The card uses red.
- Kekulé rings (all three crops).
- Reagent text black; plain arrow.
- Abbreviated groups: OMe in all three crops. CF3 appears only in crop 01 and NHBoc only in crop 02, so neither is on the card. TIPS, OEt and O-tBu are drawn as labels in the crops; they have no entry in the toolkit abbreviation table.

## Not settled by the crops

- Solvent placement. Choudhary et al. puts the solvent above the arrow and temperature and time below. Zhao et al. puts reagents above and solvent and conditions below. The card leaves `conditions_split` null.
- Formed-bond colour: red (Choudhary et al.) against blue (Zhao et al.).
- Yield separator: `, ` (Choudhary et al.) against `: ` (Zhao et al.).
- Compound-label colour: black against blue (Zhao et al.).
- Yield colour: blue in Zhao et al. The house-style schema has no yield-colour key.
- Inline A + B layout. Crops 01 and 02 show an inline plus; crop 03 has one substrate. `substrate_layout` and `show_plus_sign` are left null.
