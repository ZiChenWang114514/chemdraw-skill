# Science / Sci. Adv. house style: arene bromination (Fig. 3, Zhao et al.)

Source: Zhao et al., *Sci. Adv.* **2024**, *10*, eadq0028, DOI [10.1126/sciadv.adq0028](https://doi.org/10.1126/sciadv.adq0028). Licence: CC BY 4.0. The reference image `reference.png` shows the header box and the two scope rows (2a to 2l) of Fig. 3, reproduced under that licence.

Card: `toolkit/cdxml_toolkit/publication/house_styles/science_aaas.json` (base preset `nature`), evidence entry `science_aaas-03`. The card has no `figure_types` section, so the checks below use its top-level conventions and the observations recorded for this crop.

Figure type: `reaction_scheme` (one boxed general reaction over a scope grid).

## What is reproduced

- The main reaction in the header box, as one step: a model arene to its para-bromo product **2a**, with the header conditions (Fe(TPY10)Br3 10 mol %; H2O2 6 equiv, NH4Br 6 equiv; EtOH/H2O, RT, 2.5 h) above and below the arrow, and the yield 89%. The paper says "2.5 hours"; the render shows "rt, 2.5 h" where the brief says "RT, 2.5 h" (see Audit).
- The substrate is acetanilide, the parent arene of 2a. The paper's header shows a generic `Ar-H`. The replicator tried no generic placeholder (for example a dummy-atom SMILES), so the claim that none can be drawn is untested. This is an instance of the general reaction, not the paper's header.
- The 2a structure is read from the crop (AcHN-C6H4-Br, Br para to the amide nitrogen): `CC(=O)Nc1ccc(Br)cc1`.

Not reproduced: the boxed header and its drop shadow, the `Ar` circle, the `RS (p/o) > 20/1` note, the red FeBr3 side results (28%, 23%), and the scope grid apart from one compound. A five-entry scope panel (2a, 2b, 2c, 2d, 2e) was drawn as an unrendered `kind: "scope"` draft (see Operational notes). Compounds 2b to 2l, the footnotes and the `b` / `a` superscripts are not drawn.

## Files

- `brief.json`: the single-step brief used for the rendered replica (`"style": "science_aaas"`).
- `rendered.png`: desktop ChemDraw render of that brief (1110 x 196 px, 23 KB).
- `replay.py`: runs `draw_figure` on `brief.json` offline; tested with `cdx.py py` and writes `figure.cdxml` and `validation.json`.

## Convention check

Columns: convention (card value or observation for this crop), paper (crop 03), replica, match. Counts for the result cover the 16 top-level card conventions (`compound_label_italic_suffix` included).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face: bold | **2a** bold | **2a** bold (applied by house code; weak at 1110 px) | yes |
| compound_label_color: #000000 (card) | 2a and its yield are blue | label black (matches the card, contradicts the crop) | no |
| compound_label_italic_suffix: false | no suffix | no suffix | yes |
| yield_placement: after_product_label | yield on the label's line under the product | `2a, 89%` on one line | yes |
| yield_format: {value}% | 89% | 89% | yes |
| yield_separator: ", " (card) | colon, `2a: 89%` (the crop's own entry says "after a colon") | comma | no |
| yield colour (not in card; crop observation) | blue | black; no yield colour option | no |
| reagent_text_color: #000000 | black | black | yes |
| arrow_style: plain | plain arrow | plain arrow | yes |
| aromatic_rings: kekule | Kekule rings | inner double bonds not resolvable at 1110 px | not confirmed |
| abbreviate_groups: OMe, CF3 (card) | no OMe or CF3 in 2a; the paper's scope abbreviates 2a as `AcHN-` | full acetamido drawn, not abbreviated; AcHN is not in the toolkit's abbreviation table | no |
| substrate_colors: #000000, #0B0AED (card) | the incoming Br is blue, but only in the product; the reaction has one drawn substrate | no blue atom | no |
| new_bond_color: null (card) | the new C-Br bond is blue in the crop | C-Br bond black | no |
| highlight_fill: null | none | none | yes |
| conditions_split: null (card) | reagents above the arrow, solvent and conditions below | same split (the brief's own above/below); the card sets no split, so this checks the crop only | yes |
| substrate_layout: null | one substrate | one substrate | not tested |
| show_plus_sign: null | no plus sign | no plus sign | yes |
| label font Arial, about 8 pt (card) | label looks Arial-like | not measured | not checked |
| bond length / label cap height (card 1.935) | 43 / 21 px = 2.05 in crop 03 | not measured | no (unverified) |
| line width / bond length (card 0.052) | 3 px / 43 px = 0.070 in crop 03; the card value is about 25 percent thinner than this crop | not measured; the replica follows the card value | no |
| arrow length / bond length (card 12.82, mean of three crops) | 329 / 43 px = 7.7 in crop 03; the amine crops give about 15 | not measured; with the card value the arrow is about 1.7 times the crop ratio (12.82 / 7.7), not "about twice" | no |
| side results in red parentheses | 28% and 23% for FeBr3 | not drawn | no |
| header box with drop shadow | yes | no | no |
| Ar circle placeholder | yes | acetanilide instead | no |
| Br of the product blue | yes | black | no |

Card conventions: 9 matched of 16 (label bold, label italic suffix off, yield placement, yield format, reagent text, plain arrow, null highlight, null conditions split, null plus sign). Not matched: label colour, yield separator, substrate colours, new-bond colour. Not tested or not confirmed: aromatic rings, abbreviated groups, substrate layout.

The first draft claimed 10 of 15. It counted the null new-bond colour as a match while its own row says "no", and it left out `compound_label_italic_suffix`. Its "yes" rows in the table number 9, and the corrected list above is also 9.

## Differences from the paper

- Substrate: acetanilide stands in for the generic `Ar-H` of the header. The header's red `H` and the `Ar` circle are not drawn.
- Reagent: the bromine source (NH4Br) is written as text above the arrow, so the atom balance check reports that step 1 lacks Br. The warning stays because the reagent text cannot be counted as a source. Nothing was added to the drawing.
- Colour: the introduced Br, the product yield and the compound labels are black. The paper uses blue for all three.
- Yield: `2a, 89%` uses a comma, the paper uses `2a: 89%`.
- Abbreviation: the paper's scope draws 2a with `AcHN-`; the replica draws the full acetamido group.
- Conditions text: "RT" and "2.5 hours" in the paper; the render reads "rt" and "2.5 h".
- Arrow: the replica arrow is long relative to the structures; the crop's arrow is about 7.7 bond lengths, and the card value applied to the replica is 12.82.
- Scope: one compound instead of twelve, and no footnotes.

## Tool gaps

- No generic `Ar` placeholder or boxed header with drop shadow. A dummy-atom SMILES or a `title` box was not tried, so only the drop shadow is confirmed missing.
- A reagent-only halogen source (NH4Br) listed in `above` text is not counted in the atom balance, so every bromination step will carry a missing-Br warning. The brief has no reagent role, so there is no way to mark a text reagent as the source.
- No per-figure colour for the formed C-Br bond, the Br atom, the compound labels or the yields. The toolkit does colour formed bonds (`_color_new_bonds`) and substrates, but only when the card sets `new_bond_color` or `substrate_colors`; this card leaves `new_bond_color` null, and no brief field sets a colour. The first draft's wording ("the tool does not colour it") was too broad.
- No yield colour option.
- A scheme cannot place steps with different substrates in one row: `draw_figure` refused four independent 2a, 2b, 2d, 2e steps, as its docstring says it does for steps that fit no linear, convergent, divergent or cycle layout. Scope rows of different arenes must use `kind: "scope"`.
- `kind: "scope"` applies only the base preset (nature); house conventions are skipped (`house conventions apply to schemes only`), so the scope panel cannot carry the bold-label and yield-colour conventions of this card.
- The style report is inconsistent about `yield_separator`. The code applies the card's separator silently (no `applied` entry) and records nothing for `compound_label_color` when it is black, so the report does not show either one. The label colour omission is by design for black; the yield separator omission is a reporting gap.
- The card holds one `yield_separator` for the publisher. Crop 01 and crop 02 use a comma and crop 03 uses a colon, and the code accepts `": "`, but there is no per-figure override.
- Arrow length and the bond/cap ratios are card-wide values (12.82 is the mean of three crops, two of them amine crops with an arrow about twice as long). A single figure cannot use its own crop's geometry.
- No coloured or annotation text runs: the red side results, the red `RS (p/o)` note, the red `H` and the red FeBr3 yields cannot be drawn, because `above`, `below` and scope `values` take plain text only.
- The abbreviation table has no `AcHN` (acetamido), `NH2` or `NMe2`, although the paper's scope uses all three. A card that abbreviates them would still fail on this figure.
- A scheme has no footnote field (`BRIEF_KEYS` lacks it), so the `a` and `b` footnote markers cannot be drawn; only `kind: "scope"` takes footnotes.

## Operational notes

- `draw_figure` with `--render` took about 280 s for the single-step brief.
- The first scope render exceeded the 300 s tool limit; the retry rendered no PNG because ChemDraw stayed busy (`resource_busy`, 175 s). The scope draft (`scope-try3c`, two pages: 4 compounds and 1 compound at 180 x 80 mm) is unrendered and is kept outside this case folder.

## Attempts

1. Single step 2a, rendered: matched structures, native render ok, balance warning (Br source). Used as the replica.
2. Four independent steps (2a, 2b, 2d, 2e): refused as not laid out.
3. Scope panel of five compounds (2a to 2e), height 80 mm: two pages, not rendered (resource busy after one retry).

## Audit

- Overclaimed: "10 of 15" (now 9 of 16). The new-bond colour row is "no" but was counted as a match; the italic-suffix convention was omitted; conditions split and the plus sign are null card values, so their matches check only the crop.
- Overclaimed: "approx." for bond length, cap height and line width. Line width on this crop is 0.070 against the card's 0.052, so the replica is thinner than the crop if it follows the card.
- Overclaimed: arrow "about twice" the crop ratio. With the card value 12.82 the ratio is about 1.7. The replica arrow was not measured.
- Overclaimed: "the tool does not colour" the new bond. The toolkit colours formed bonds when the card sets `new_bond_color`; the real gap is that no brief field sets a colour.
- Mis-described reference: the image is the header and two scope rows (2a to 2l), not the "top box and first row". The 2a in it is drawn with `AcHN-`, which the replica does not reproduce.
- Not explained: the render reads "rt, 2.5 h" while the brief says "RT, 2.5 h". No case-folding was found in the toolkit's figure code; the cause needs a check of the ChemDraw output.
- Not checked: label font and size, bond length, and line and arrow geometry on the replica itself. The pixel measurements were not run.
