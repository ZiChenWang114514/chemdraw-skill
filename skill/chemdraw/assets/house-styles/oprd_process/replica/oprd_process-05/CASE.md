# oprd_process crop 05: two literature routes to pretomanid (Scheme 2)

Source: K. Lucas, T. Opatz et al., *Org. Process Res. Dev.* 2023, DOI [10.1021/acs.oprd.3c00187](https://doi.org/10.1021/acs.oprd.3c00187) (Short and efficient synthesis of the antituberculosis agent pretomanid from (R)-glycidol), Scheme 2 (literature routes to pretomanid).

Licence: CC BY 4.0, from the house-style card (`oprd_process.json`, evidence entry `oprd_process-05`). Reference crop reproduced under that licence.

Figure type: `total_synthesis` (card section). Style: `oprd_process` (base preset `acs1996`).

## What is reproduced

Both literature routes in the crop, drawn as two separate linear routes:

- Read & Fairlamb route: `7` + TBS glycidyl ether, then `8`, `9`, `10`, then `1`, with reagents above and yields under each arrow (31%, 51%, 84%, 73%).
- Zhai et al. route: `11` + epichlorohydrin, then `12`, `13`, `14`, `15`, then `1`, with reagents above and yields under each arrow (73%, 92%, 71%, 66%, 85%).

The two routes are drawn with one brief each, not one brief. `draw_figure` refuses a single brief whose steps form two unconnected routes (see Tool gaps), so `rendered.png` stacks the two ChemDraw renders (`routeA.png` and `routeB.png` in the scratch folder) vertically. The stacked PNG is an image, not an editable CDXML.

Structures were written by hand from the crop, not from OCSR. Each SMILES was checked with RDKit (formula and CIP labels). Compound `1` is pretomanid, C14H12F3N3O5.

## Stereochemistry (assumed, not read)

The crop is too small to read the wedge and hash bonds with confidence. The stereocentre is carried through every step unchanged (epoxide opening at the terminal CH2, benzylation and cyclisation at the oxygen, no bond to the stereocentre is broken), and its CIP priority pattern (O > CH2O/CH2Cl > CH2N > H) is the same in every intermediate. So all stereocentres were written as (S), the configuration of pretomanid. The epoxide and epichlorohydrin reagents were drawn without stereo.

## Layout of the two briefs

- `brief_read_fairlamb.json` (also copied to `brief.json`): steps 1-4, species `7`, `Ep1`, `8`, `9`, `10`, `1a`.
- `brief_zhai.json`: steps 5-9, species `11`, `Ep2`, `12`, `13`, `14`, `15`, `1b`.

`replay.py` reads `brief.json` only, so it reproduces the Read & Fairlamb route. To reproduce the Zhai route, point the script at `brief_zhai.json` (a one-line change in the copied script, not made here).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/oprd_process/replica/oprd_process-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| Literature routes headed by authors in bold (Read & Fairlamb, Zhai et al.) | yes, bold headings above each route | no heading text in the brief or output | no |
| Yield alone under each arrow | yes (31%, 51%, 84%, 73%, 73%, 92%, 71%, 66%, 85%) | yes, under each arrow | yes |
| Reagents above the arrow | yes | yes for the text reagents; the epoxide and epichlorohydrin are drawn as reactants (see the epoxide row) | yes |
| Yield format `{value}%` | `31%` | `31%` | yes |
| No step labels (`step_label_style: none`) | no step labels | none drawn | yes |
| Rows wrap with downward arrows at the right edge | Read & Fairlamb row turns down from 9 to 10; Zhai row turns down from 13 to 14 | each step on its own row, no wrap connector | no |
| Compound labels bold, black | bold numbers under each structure | bold numbers, black | yes |
| OTBS abbreviation | `OTBS` | `OTBS` | yes |
| Aromatic rings in Kekule form | Kekule | Kekule | yes |
| No highlight fill, no colours | black only | black only | yes |
| Plus sign between two reactants | no plus sign; the epoxide and epichlorohydrin sit above the arrow | plus drawn between each pair of reactants | no |
| Plain arrow, reagents over the arrow | plain arrows | plain arrows | yes |
| Epoxide drawn above the arrow (not as a reactant) | epoxide structure above the arrow | epoxide drawn as a second reactant beside the substrate | no |
| `OCF3` and `Ar` written as text | `OCF3`, `Ar` | `OCF3` expanded to F3C-O, benzyl expanded to ring and CH2 | no |
| `NO2` written as text | `NO2` | drawn as N(+)(=O)O(-) | no |
| Multi-line conditions (`1. ... 2. ...`) | two numbered lines above the arrow | `1. TBAF, THF` / `2. NaH` above the arrow | yes |
| Arrow length about eight bond lengths | long arrows | similar length; not measured | not checked |
| Stereo wedges and hashes at the stereocentres | wedge and hash bonds | wedge and hash drawn, assigned (S) | unverified |

Card claims for this figure type: 9 (does not reconcile with `oprd_process.json`; see Audit). Matches claimed: 7 (yield under arrow, reagents above, yield format, no step labels, bold labels, OTBS, colours). Mismatches claimed: author headings and wrap arrows. The plus sign row is also a mismatch and was not claimed.

## Differences from the paper

- Two routes stacked as two images, not one composed CDXML. The paper has the two routes as one figure with headings.
- Each step sits on its own row. The paper packs two or three steps per row and turns the route down at the right edge (9 to 10 and 13 to 14); the continuation row runs right to left.
- The epoxide reagent is a reactant beside the substrate, not a structure above the arrow.
- `OCF3` and the benzyl `Ar` are expanded in full; the paper uses the text abbreviations.
- `NO2` is drawn as N(+)(=O)O(-); the paper uses the text `NO2`.
- Product `1` appears twice, once per route (`1a` and `1b`). The paper draws it once per route too, so this matches the figure, but it is a duplicate in the brief.
- Stereo was assumed, not read (see above).
- Mass balance: `draw_figure` reports that several steps do not balance (step 2 and later in both routes), because the reagents are text and their by-products (for example HBr, NaCl, TBS-F) are not drawn. Nothing was added to the drawing.

## Tool gaps

- `draw_figure` refuses one brief containing two unconnected linear routes (error text confirmed in `toolkit/cdxml_toolkit/render/route_graph.py`). Each route needs its own brief, so the stacking is done outside the tools.
- The `draw_figure` brief accepts only `kind`, `species`, `steps`, `max_width`, `title`, `style` and `layout` (`BRIEF_KEYS` in `toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`). The scheme-level renderer (`render/parser.py`, `render/renderer.py`) does support `wrap: serpentine` (zigzag rows with vertical arrows), `stacked-rows` sections with labels, `above_arrow.structures` (a structure above the arrow) and `steps_per_row` / `max_row_width`. None of these is reachable from `draw_figure`, so the wrap, two-route and structure-above-arrow gaps are gaps of the brief surface, not of the renderer. Not run here.
- No bold heading above a route. The brief's `title` is a single heading for the whole figure; the renderer parses it, but its drawing was not verified here. Section labels such as `(i)` and `(a)` are the only per-section text in the scheme format.
- No `Ar` abbreviation. The card's `abbreviate_groups` lists only `Boc` and `OTBS`, so `Ar`, `OCF3` and `NO2` as text needs a card change, not a drawing-tool change.
- Reagent text cannot be tied to numbered steps beyond writing the `1.` / `2.` lines as plain text.
- Not a drawing capability gap: `--render` runs of about three minutes, and a stall under ChemDraw contention, are operational.

## Audit

Checked by viewing `reference.png` and `rendered.png`, reading `brief.json`, `oprd_process.json` and the toolkit sources named above. Nothing was rendered again.

Overclaims found:

- The plus sign row was marked matched. The reference has no plus sign on either route; the epoxide and epichlorohydrin are drawn above the arrows. The paper column (`7 + epoxide`, `11 + epichlorohydrin`) was wrong.
- The multi-line conditions row described the paper's lines as under the arrow. In the reference both numbered lines are above the arrow. The match holds only for placement above.
- The Differences section said the paper packs four steps per row. The reference has two or three.
- The headline "9 card claims, 7 matched" does not reconcile. The `total_synthesis` block in `oprd_process.json` has five convention keys and three signature features (eight items). The table itself has eleven "yes" rows, which the summary does not match.
- Bold compound labels: the replica labels look bold, but their size and position against the reference were not measured (the card records a compound-label cap height of 45 px for this crop). Kept as matched on face only.
- Reagents above: holds for the text reagents only. The epoxide and epichlorohydrin are reactants in the replica (covered by the epoxide row).
- Yield under arrow and yield format hold: nine yields in the reference, nine in the replica.
- Stereo wedges and hashes: unverified at this resolution.
- Arrow length: not measured.
- Mass balance and the RDKit checks: no `validation.json` or RDKit output is in this folder, so these are unverified.

Card issues (`oprd_process.json`, not edited here):

- `show_plus_sign: true` is contradicted by this crop.
- The `conditions_split` note says solvent and temperature go below the arrow in crop 05. In the reference all conditions are above the arrow and only the yield is below.
- `abbreviate_groups` lacks `Ar`, `OCF3` and `NO2`, so the expansions in the replica follow from the card, not from the tools.

Corrected matched count: 10 of the 18 table rows (rows 2, 3, 4, 5, 7, 8, 9, 10, 12, 16). Not matched: author headings, row wrap, plus sign, epoxide above the arrow, `OCF3`/`Ar` text, `NO2` text. Not checked or unverified: arrow length, stereo.

Tool gaps the replicator missed or misattributed: the wrap, structure-above-arrow and two-route gaps exist at the `draw_figure` brief level only; the renderer already has serpentine wrap, stacked-rows sections and above-arrow structures. The `title` key was not mentioned. Italic runs inside reagent text (the italic `p` in `p-OCF3-BnBr` in the reference) were not checked in the replica and are unverified.
