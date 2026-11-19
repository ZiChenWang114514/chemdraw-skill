# Royal Society of Chemistry house style

How reaction schemes are drawn in RSC journals (Chemical Science, Chemical Communications, Organic & Biomolecular Chemistry, Green Chemistry), measured from open-access figures. Machine-readable card: `toolkit/cdxml_toolkit/publication/house_styles/rsc_journals.json` (style slug `rsc_journals`, base preset `rsc`).

## Sources (CC BY 3.0)

- Cen et al., Chem. Sci. 2024, DOI 10.1039/d4sc05429f: Table 2 scope of carboxylic acids and alkynes (`evidence/rsc_journals-01.png`).
- Freiberg et al., Chem. Sci. 2023, 14, 3462, DOI 10.1039/d3sc00198a: Scheme 1, formation of DPDTC (`evidence/rsc_journals-02.png`), and Scheme 6, representative drug amides (`evidence/rsc_journals-03.png`).

## Measurements (means of three crops)

- Bond length / atom-label cap height: 1.91. The crops give 2.24, 1.84 and 1.66; two of the three lie within 15 percent of the mean.
- Line width / bond length: 0.046. The crops give 0.053, 0.043 and 0.042 (2 px lines, so this is a rough value).
- Arrow shaft / bond length: 7.7. The crops give 11.9, 4.5 and 6.6, so the crops disagree and the value is rough.
- Atom labels: Arial or Helvetica, about 8 pt at print size.
- Bold bond width: not measured. The bold red bond in Scheme 6 has no reliable bond length to divide by.

## Conventions (top level, set only where two crops agree)

- Compound numbers bold black in Table 2 and Scheme 1; Scheme 6 uses plain numbers. Two of three crops are bold, so bold is the card value.
- Reagents and catalysts above the arrow; solvent and temperature below (all three crops).
- Kekule rings (all three crops).
- Plus sign between substrates: inline in Table 2, stacked in Scheme 1. Scheme 6 has no plus; the amine is added above the second arrow.
- Yield after the product label, in parentheses, on the same line (Table 2 and Scheme 6). Scheme 1 puts its yield on the line under the label.
- Reagent text black; plain arrow.
- Abbreviated groups seen in two crops: OMe (Table 2 and the trimethoxy ring in Scheme 6) and OCF3 (Table 2, and F3CO on sonidegib in Scheme 6, which is OCF3 read from the other side).

## Not settled (null in the card)

- Yield format: Table 2 writes the isolated yield then the GC yield in parentheses (77% (84%)); Scheme 6 writes one yield in parentheses (27 (94%)); Scheme 1 writes 89% yield with the scale.
- Substrate layout: inline with a plus in Table 2, stacked with a plus in Scheme 1, amine above the second arrow in Scheme 6.
- New-bond colour: only Scheme 6 colours a new bond (the amide C-N bond, red, drawn thicker). In Table 2 the naphthalene, including its new ring, is navy.
- Substrate colours: only Table 2 colours whole substrates (acid-derived naphthalene navy, alkyne-derived aryl magenta). Scheme 1 colours only the triphosgene carbonyl blue.
- Abbreviations seen in one crop only: CF3 and CO2Me (Table 2). OPh and SMe are abbreviated in Table 2 but are not in the house abbreviation table.

## Figure types

- Reaction scheme (Scheme 1 and Scheme 6): grey header panel (#F1F5F8) behind the upper reaction in Scheme 6 only, with a black rule beneath it. Other features are listed in the card, including the green drug names under the products in Scheme 6, which have no card field.
- Substrate scope (Table 2): one core drawn in a grid, the varied alkyne-derived aryl in magenta (#9D0A42), catalyst and conditions written once in the header, and the yield written as isolated then GC yield in parentheses.
