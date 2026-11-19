# Wiley chemistry journals house style (`wiley_angew`)

How reaction schemes are drawn in Angewandte Chemie, Chemistry - A European Journal and related Wiley-VCH journals, measured from open-access figures. It adds drawing conventions on top of the Wiley style sheet (`wiley`).

## Sources (all CC BY 4.0)

1. Rowett, Sweeting, Heard and Lennox, Angew. Chem. Int. Ed. 2024, 63, e202400570, DOI 10.1002/anie.202400570 (crops 01, 02)
2. Zobernig et al., Chem. Eur. J. 2024, 30, e202302455, DOI 10.1002/chem.202302455 (crop 03)

## Conventions

Set on the card because the crops agree:

- Compound numbers bold and black: 01, 02, 03
- Catalyst and reagents above the arrow, solvent and temperature below: 01, 02 (crop 03 puts the base below the arrow)
- Substrates side by side with a plus sign: 01, 02
- Aromatic rings as Kekule structures: 01, 02, 03
- Plain arrow (grey or black; thin black in 03): 01, 02, 03
- Sans-serif labels: 01, 02, 03
- Heavier lines than ACS (about 0.09 of the bond); bond about 2.1 times the capital height: 01, 02, 03

Reaction schemes are listed as the `reaction_scheme` figure type with all three crops. It adds no figure-type-only convention.

Not set, because the crops disagree (the reasons are in the card's `conventions.notes`):

- Yield: placement differs (after the product label in 01, under it in 03); only 01 prints a percent sign.
- Arrow length: 6 to 12 bond lengths across the crops (01 8.4, 02 6.2, 03 12.2). The card keeps the median, 8.4.
- Colour: 01 and 02 colour whole substrates red and blue and print reagent names in purple; 03 keeps substrates black, colours only the new bonds red, and prints reagent text in black. No colour rule is set.
- Abbreviations: Me is a label in 01 and 02 but drawn as lines in 03; NO2 and OMe appear only in 01. No group is set.
