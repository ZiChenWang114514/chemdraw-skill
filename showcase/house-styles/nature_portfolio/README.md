# Nature Portfolio house style

How reaction schemes are drawn in Nature Portfolio chemistry journals (Nature, Nature Chemistry, Nature Communications, Nature Synthesis, Nature Catalysis), measured from open-access figures. Machine-readable card: `toolkit/cdxml_toolkit/publication/house_styles/nature_portfolio.json` (base preset `nature`).

## Sources (CC BY 4.0)

- Wang et al., Nat. Commun. 2025, 16, 1108, DOI 10.1038/s41467-025-56377-w: Table 1 scheme (`evidence/nature_portfolio-01.png`), Fig. 2 scope header and first row (`-02`).
- Zhao, Jia and Wang, Nat. Commun. 2024, 15, 2415, DOI 10.1038/s41467-024-46576-2: Fig. 2 scheme with X-ray panels and the top of scope row a (`-03`).

## Measurements (means of the evidence crops, 300 dpi page renders)

- Bond length / atom-label cap height: 2.21 (crops 2.26, 1.60, 2.76).
- Line width / bond length: 0.062 (crops 0.067, 0.075, 0.043).
- Bold wedge width / bond length: 0.24 (crops 0.29 and 0.20; both from one paper, and crop 03 has no wedge).
- Arrow shaft / bond length: 11.1 (crops 9.3, 12.7, 11.3). The spread is wide and no single crop matches the mean, so treat it as approximate.
- Atom labels: Arial or Helvetica, about 7 pt at print size. This is an estimate; the crops carry no print size.

## Conventions

- Compound numbers bold black, suffix not italic (both papers).
- Yield written as a plain percentage after the bold number on the same line, e.g. 3a, 85%, 90% ee (both papers). Enantiomeric excess follows the yield after a comma.
- Catalysts and ligands above the arrow; additives, solvent, temperature and time below (both papers).
- Kekulé rings (both papers).
- The substrate-derived skeleton is teal, #0078B2, in substrate and product (exact in crops 01 and 02; crop 03 sampled at #0073AC).
- Reagent text black; plain arrow. H2O in the conditions is bold teal in crops 02 and 03; the card records the plain reagent text colour.
- Abbreviated groups in the card: CO2Me and Et (each drawn as a label in crops 01 and 02). CN and tBu are drawn as labels in crop 02 only. Ph is a ring in crop 01 and a label in crop 02 only, so it is not listed. OMe and Me occur only as text in the crop 02 table.
- Red new C–C bond (#FF0000) and blue second substrate (#0000FF) appear in crops 01 and 02, both from Wang et al. 2025. The second paper has not confirmed them.
- Inline A + B layout and a plus sign between substrates are seen in crops 01 and 02, both from one paper, so the card leaves both unset. The second paper has a single substrate.

## Figure types

- Reaction scheme: the top-level conventions above. No separate section is needed.
- Substrate scope (crops 02 and 03): compounds in a grid, each with a bold label and its yield on the same line; brown rules and rounded boxes separate scope sections. Selectivity is written as "{value}% ee" (crop 02 only).
