# Natural Product Reports: first total synthesis of Rhopaladin D (Scheme 10, total_synthesis)

Source: Tepe et al., "Advances in the total synthesis of bis- and tris-indole alkaloids containing N-heterocyclic linker moieties", *Natural Product Reports* **2024**. DOI: [10.1039/d4np00012a](https://doi.org/10.1039/d4np00012a). Licence: CC BY 3.0. Reference crop: `evidence/natural_product_reports-07.png` (copied as `reference.png`).

Card: `natural_product_reports` (RSC base preset), figure type `total_synthesis`.

## What is reproduced

The whole of Scheme 10: six structures (54, 55, 56, 57 in square brackets, 58, and Rhopaladin D (53d)) and five steps: condensation of aldehyde 54 with ethyl azidoacetate; ester hydrolysis and amidation to 56 (two operations on one arrow); aza-Wittig reaction with PPh2Me to the unisolated iminophosphorane 57; condensation and cyclisation with polymer-bound 23a to 58; SEM removal with TBAF to 53d. Yields as in the scheme: 80%, 90% and 92% (two operations), 56%, 60%.

Structures are written from the crop. Alkene geometry is Z throughout: the Z-azidoacrylate geometry for 55 and 56 and the imine 57 is taken from the Hemetsberger chemistry, not read from the crop. For 58 and 53d the review text states the Z geometry (NOESY). The review also reports 58 as a 6:4 E/Z mixture, which the scheme does not show.

| SMILES | Structure |
| --- | --- |
| `O=Cc1cn(COCC[Si](C)(C)C)c2ccccc12` | 54 |
| `CCOC(=O)/C(=C/c1cn(COCC[Si](C)(C)C)c2ccccc12)N=[N+]=[N-]` | 55 |
| `NC(=O)/C(=C/c1cn(COCC[Si](C)(C)C)c2ccccc12)N=[N+]=[N-]` | 56 |
| `NC(=O)/C(=C/c1cn(COCC[Si](C)(C)C)c2ccccc12)N=P(C)(c1ccccc1)c1ccccc1` | 57 (iminophosphorane, bracketed) |
| `O=C1NC(C(=O)c2c[nH]c3ccccc23)=N/C1=C\c1cn(COCC[Si](C)(C)C)c2ccccc12` | 58 |
| `O=C1NC(C(=O)c2c[nH]c3ccccc23)=N/C1=C\c1c[nH]c2ccccc12` | Rhopaladin D (53d) |

All six SMILES were checked with RDKit. The brief is `brief.json` in this folder; `replay.py` redraws it offline. Reagents are text on the arrows (ethyl azidoacetate, NaOEt, LiOH, CDI, NH3, PPh2Me, 23a, BEMP, TBAF), not species in the brief.

## Result

The first draw used SMILES without alkene stereo and was refused by the read-back (`chemical_semantics_changed`: the saved file added Z double-bond stereo). The second draw with Z stereo succeeded. Two renders were run in total. `rendered.png` is the ChemDraw render (`figure_v2.png`), downscaled to 1000 px wide and quantised to 128 colours to stay under 250 KB.

The tool's `checks_passed` is false because of two label clashes (fragments 1576 and 1743, both around the bracketed 57 and its SEM chain). The read-back reports 10 structures drawn, matched, none missing, none unexpected. The balance warnings name the reagents written as text and the SEM by-product; nothing was added to the drawing.

## Differences from the paper

- Layout: the paper folds the linear route into a U (54 to 55 to 56 on the top row; 56 to 57 runs right to left; then 57 down to 58 and 53d). The tool draws five sequential rows, each arrow pointing right, so the leftward 56 to 57 arrow is not reproduced.
- Bracket: 57 is in a square bracket made with `ts_bracket` and an empty superscript. The bracket spans the whole fragment, including the SEM chain, and its lower edge collides with the SEM methyl labels. The paper's brackets are tighter.
- SEM: the paper labels the indole nitrogen "SEM". The tool draws the full CH2OCH2CH2SiMe3 chain, because only Me and CO2Et are contracted.
- Yields: the paper sets the yields in bold under each arrow. The tool sets them in plain text, and for the two-operation step it writes "90%" and "92%" in parentheses on the reagent lines.
- Numbering: the paper's numbered reagents (1. LiOH, THF, H2O; 2. CDI, NH3, DMF) are typed text in the brief, not generated numbering.
- Compound labels: bold, black, as in the paper. Rhopaladin D (53d) is bold with its number, as in the paper.

## Tool gaps

- No folded or U-shaped route layout; a linear route wraps only into sequential rows.
- No bracket for an unisolated intermediate that is not a transition state. `ts_bracket` adds a double-dagger superscript (blank only with an empty string) and sizes the bracket to the whole fragment.
- One yield field per step; a step with several operations cannot place a bold yield under the arrow for each operation.
- No generated numbered reagent list on the arrow.
- No SEM (or other protecting-group) abbreviation in `abbreviate_groups`.
- No thin rounded-rectangle box around a final target (the card cites it for crop 06).
- Layout lint reports two label clashes and does not relayout, so `checks_passed` is false.

## Verdict

Structures and reagent text are reproduced, with three caveats. The figure draws 55, 56, 57 and 58 twice each (10 structure instances for 6 compounds), which the Result section does not say. The alkene geometry is taken from the literature, not read from the crop. Yields sit under the arrow but are plain, not bold. The U-fold layout, the SEM abbreviation, the bracket size, the bold yields and the label clashes are not reproduced. Matched conventions: 6 of 16 (see Audit).

## Audit

Checked on 2026-11-07 against `reference.png` and `rendered.png`, using the house card `natural_product_reports.json` (`total_synthesis`). This file has no per-convention match table, and the 11 of 16 count and the tool gap list from the replicating agent are not recorded here. The table below is an independent audit of 16 conventions that apply to this figure. Anything not verified at this resolution is counted as not matched.

| # | Convention | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Bold compound numbers centred under each structure | Matched | 54 to 58 and 53d are bold and centred |
| 2 | Compound label colour black, Arial-like face | Matched | Visual check only |
| 3 | Kekule rings, plain black arrows, black reagent text | Matched | Visual check only |
| 4 | Reagent text above or below the arrow (steps 1, 3, 4, 5) | Matched | Same sides as the reference; step 3 direction is wrong (row 16) |
| 5 | Single-operation yield under the arrow, format `{value}%` | Matched | 80%, 56%, 60% in the right place and format |
| 6 | Yields in bold | Not matched | Plain in the rendered figure; bold in the reference |
| 7 | Two-operation yields bold under each operation | Not matched | 90% and 92% are in parentheses on the reagent lines |
| 8 | Numbered reagent lines 1. and 2. on the arrow | Not matched | Numbers are typed literally; the tool does not generate them |
| 9 | CO2Et abbreviation | Matched | Abbreviated in 55 and 56 |
| 10 | SEM abbreviation | Not matched | Full CH2OCH2CH2SiMe3 chain drawn in 54 to 58 |
| 11 | U-fold route; 56 to 57 arrow pointing left | Not matched | Five rows, every arrow rightward |
| 12 | Each intermediate drawn once | Not matched | 55, 56, 57 and 58 each appear twice (product of one row, substrate of the next) |
| 13 | Tight square bracket around unisolated 57 | Not matched | Bracket is oversized and its lower edge runs through the SEM Me labels |
| 14 | No label clashes | Not matched | The P-Me label on 57 runs into the NH2 label; the SEM Me sits on the bracket |
| 15 | Proportions, bond length to cap height, line weight | Not verified | Not measured; not counted as matched |
| 16 | Alkene geometry as drawn in the crop | Not verified | Z is taken from the Hemetsberger chemistry, as the file says |

Corrected count: 6 of 16 matched (rows 1 to 5 and 9).

Overclaims in the earlier text:
- The Verdict said structures were reproduced. The figure has 10 structure instances for 6 compounds, and the Result section says only that 10 structures matched.
- The Verdict said yields were reproduced. They are placed correctly but are not bold, which is the convention.
- The Verdict said the structures were reproduced, but the alkene geometry was never read from the crop.

Tool gaps the replicating agent did not list:
- The layout duplicates intermediates. Each row draws a step's product and the next step's substrate separately, so a linear route cannot show one shared intermediate between two arrows.
- No per-arrow direction control. A single step cannot point left, which the fold requires.
- No bracket fitted to the core fragment. The bracket follows the whole fragment, SEM chain included, instead of a chosen atom set.
- The layout lint detects the P-Me/NH2 and SEM/bracket clashes but does not move anything to clear them.

Card note: `natural_product_reports.json` sets `conditions_split` to null and says synthetic steps have no solvent split. The reference does split step 5 (TBAF above, THF reflux below), and the brief follows the reference. The card does not record that split.
