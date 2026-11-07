# Chem. Eur. J. 2023: Gibbs energy profile, Scheme 3b (energy_profile figure type, crop 08)

Source: Anderson et al., "Gold-catalyzed cyclization of yndiamides with isoxazoles via alpha-imino gold Fischer carbenes", *Chem. Eur. J.* **2023**. DOI: [10.1002/chem.202302821](https://doi.org/10.1002/chem.202302821). Licence: CC BY 4.0. Reference crop: `reference.png` (copy of `skill/chemdraw/assets/house-styles/chemeurj/evidence/chemeurj-08.png`).

House style: `chemeurj` (base preset `wiley`, bond length 17.0 pt in the report). Card: `toolkit/cdxml_toolkit/publication/house_styles/chemeurj.json`, `figure_types.energy_profile`.

## What is reproduced

Only the chemistry that `draw_figure` can express. The energy profile itself is not drawn, because `draw_figure` has no energy-diagram drawer. The manifest tool `compose_chemical_figure` was not used (see Tool gaps).

- The ynediamide (`CN(*)C#CN(C(C)C)*`, shown in the paper as PG-N(Me)-C≡C-N(i-Pr)-PG) and the gold reagent H3P-Au+ give the two regioisomeric gold ketenimine-type intermediates Int1minor (`C[N+](*)=C=C([Au][PH3])N(C(C)C)*`) and Int1major (`CN(*)C([Au][PH3])=C=[N+](C(C)C)*`).
- Drawn as a divergent scheme with two arrows, one per regioisomer, labelled in bold with the paper's names.
- The reproduced structures use `brief.json` (final brief, `style: chemeurj`); `rendered.png` is a 1200 px wide render of that brief. Its source (desktop ChemDraw or offline) is not recorded in this folder.

Not reproduced: the energy axis and levels, all energy values, the S.M. / TS_Interconv box, the 3-methyl-5-phenylisoxazole partner, Int2 and Int3 (isoxazolium and Z-Int3 species), TS1/TS2 structures, the grey starting-material panel, and the coloured pathways.

## Brief iterations

- v1: S.M. and H3P-Au+ as two substrates with two products. Refused: "The steps are not a linear route, a convergent route ... or a set of reactions from one starting material".
- v2: single substrate, Au written as "H3P-Au+ (cat.)" above the arrow. Drawn and read back as matched, but the "(cat.)" wording is not in the paper (the Au is incorporated into the intermediates, not a catalyst), so it was removed.
- v3: same brief without "(cat.)". Final. The first two `--render` attempts exceeded the 300 s tool limit while the shared ChemDraw session was busy; the third reportedly completed (`checks_passed: true`, readback `matched`, no lint issues). No validation output is in this folder, so these results are unverified here.

## Table: conventions and signature features

Claims are the energy_profile card entries plus the top-level conventions visible in crop 08. "Match" counts only "yes".

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `energy_unit` kcal/mol | axis label ΔG_sol / kcal·mol⁻¹ | no energy axis | no |
| `energy_label` delta_G | ΔG_sol (solvation-corrected, subscript "sol") | not drawn | no |
| `level_style` bars_solid_connectors | thick level bars with thin solid slanted connectors, dotted connectors from S.M. | not drawn | no |
| `pathway_colors` (card: null) | minor blue, major maroon | not drawn; the two regioisomer arrows are both plain black | no |
| `ts_marker` none | TS1minor, TS2major etc. without double dagger | no TS drawn | not reproduced |
| signature: thick bars about 3x bond line | bars 15-17 px | not drawn | no |
| signature: bold name and energy value next to each bar | bold name with value beneath it, above the bar | bold name only, no energy value | no |
| signature: vertical axis arrow at left with ΔG label | present | not drawn | no |
| signature: second pathway in contrasting colour | blue #0080BF vs maroon #800000 | black only | no |
| `compound_label_face` bold | bold Int1 with the minor/major suffix set as a subscript | bold, suffix on the baseline | yes (face only) |
| `compound_label_color` #000000 | black | black | yes |
| `highlight_fill` #E6E6E6 (grey box behind S.M. group) | grey box behind the S.M. group | no fill; `draw_figure` shades only the largest ring of the final product, and there is no ring here | no |
| `arrow_style` plain | the two coloured arrows under the profile are single-headed (minor points left, major points right), labelled Minor/Major Regioisomer; crop 08 has no black scheme arrow | plain black single-headed arrows (card value met, but not the paper's colour) | no |
| `show_plus_sign` true | no "+" between the S.M. species in the box | no "+" drawn (one substrate only) | no |
| `abbreviate_groups` Ts, Ph, tBu, OMe | Ph on the isoxazole (not drawn here) | no Ph drawn; PG is generic (see below) | not reproduced |
| `aromatic_rings` kekule | isoxazole in S.M. box drawn Kekule | isoxazole not drawn | not reproduced |
| visible, not claimed for crop 08: Au in orange | Au orange in all structures | Au black | no |
| visible, not claimed: bond length about 2 x cap height (card measured 2.0) | bond about 2 x cap height by eye | in rendered.png the bold label cap height is about 32 px and the bond about 69 px (about 2.1); not measured precisely | approximate |

Matched 2 of 16 claimed conventions.

Conventions for conditions, yields, substrate layout and colours (`conditions_split`, `yield_format`, `substrate_layout`, `substrate_colors`, `reagent_text_color`) are not shown in crop 08 and are not counted.

## Differences from the paper

- No energy profile. The main content of Scheme 3b is the energy diagram; the replica is only the intermediate structures from the S.M. and gold reagent.
- Mechanism simplified. The paper reaches Int1minor from S.M. through a blue dotted connector and Int1major from S.M. through a maroon dotted connector. TS_Interconv (−23.8) lies on the solid path between the two intermediates, so they interconvert through it. The replica draws both Int1 species as parallel products of S.M. plus gold in a divergent scheme, which shows neither the two dotted connectors nor the interconversion.
- Protecting groups. The paper labels nitrogen substituents PG; the tool draws the `*` placeholder as R. The placeholder was used because the identity of PG is not in the crop.
- Gold reagent. The paper shows H3P-Au+ as a starting material in the grey box; the replica shows it as text above the arrow, with no catalyst wording (after v2).
- Isoxazole partner, TS_Interconv box, grey starting-material box and Int2/Int3 species are omitted.
- Orientation. The replica mirrors the paper's Int1major: the N-Me and N-i-Pr groups sit on opposite sides. The connectivity in `brief.json` matches the paper's Int1major.
- Cumulated bonds. The central sp carbon of the N+=C=C unit is drawn linearly and has no label, so the two double bonds read as one N+=C double line to a carbon bearing Au. The paper writes that central carbon as an explicit "C" in both Int1 structures, so this is a difference, not the paper's convention.
- Labels. The paper sets the minor/major suffixes as subscripts (Int1 with a subscript minor or major); the replica writes them on the baseline.
- Abbreviations. The paper writes Me and i-Pr as text; the replica draws Me and i-Pr as bond skeletons. PH3 is text in both.
- Au and N colour. Au is black in the replica (paper: orange); N is black (paper: blue).
- Text. "H3P-Au+" was rendered as H3P⁻Au⁺: the hyphen after P was converted to a superscript minus. This is wrong: the phosphine is neutral.

## Tool gaps

Scope: the gaps below were checked against `draw_figure`, whose brief accepts only kinds scheme, scope and mechanism (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`). The manifest tool `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`, documented in `skill/chemdraw/references/publication-figures.md`) is registered for these figures but was not tried here. Its objects include text with runs, arrows, lines, rectangles, ellipses, brackets and symbols, so several gaps are narrower than stated. Items marked "not tested" are read from code only.

- No energy-profile drawer in `draw_figure`. Missing there: level bars at energy positions, solid and dotted connectors between levels, a vertical ΔG_sol axis with a unit label, per-level name and value labels, and per-branch colouring. In the manifest tool, lines and arrows take a dashed style but no dotted style, and no object has its own line width, so thick level bars would have to be filled rectangles and dotted connectors are not directly available (not tested).
- No background panel in `draw_figure`. `highlight_fill` shades only the largest ring of the final product, and there is no way to put a grey box behind a chosen group of species or to outline a TS label. The manifest tool has rectangle objects with `fill_type` (solid, shaded, faded), a `background` flag that sends them behind the structures, and `round_edge`, which look sufficient for a grey S.M. panel and a rounded TS_Interconv frame (not tested).
- Per-atom and per-species colour. `substrate_colors` colours whole substrates of a step and `new_bond_color` works only by atom mapping; neither can colour Au or heteroatoms in `draw_figure`. Manifest molecules accept `color`, `highlight_atoms` and `highlight_color`; whether these colour the Au label is not tested.
- Named protecting groups. A `*` placeholder is drawn as R in `draw_figure`; there is no way to draw a labelled PG on a nitrogen there, and any species with `*` is skipped by the balance check (report: "generic atoms (R groups, *) cannot be balanced"). A PG label could be placed as a text object near the nitrogen in the manifest tool, but it would not be bonded to N (not tested).
- Scheme arrow colour. `draw_figure` arrows take only the styles solid, dashed, failed, reversible and resonance, with no colour. The manifest tool's arrows and lines take `color`, and its `resonance` style has a full head on both ends, which gives a double-headed arrow (not tested).
- Text formatting. In `draw_figure`, above/below text passes through a tidy step that turned a hyphen after an element symbol into a superscript minus (H3P-Au+ became H3P⁻Au⁺). The manifest tool's text runs take their text verbatim and support subscript, superscript, italic and per-run colour, so the conversion should not occur there (not tested). Species labels in `draw_figure` take plain text only, so the subscript suffixes of Int1minor and Int1major cannot be drawn there.
- Central cumulene carbon label. Neither draw path was tried for an explicit "C" on the sp carbon of N+=C=C; `draw_figure` has no atom-label option for it (not tested in the manifest tool).
- Shared ChemDraw session. `--render` waited for the desktop session and exceeded the 300 s tool limit twice while other draws were running (per the replicator; not verifiable from this folder).

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json` and the chemeurj card. No other file was changed.

Overclaims corrected above:
- Paper arrows: the two coloured arrows under the energy profile are single-headed, not double-headed. The card's energy_profile observation repeats the "double-headed" error; the card was not edited. The `arrow_style` row was "partial" and is now "no".
- Mechanism: Int1major is reached from S.M. by a maroon dotted connector, not through TS_Interconv.
- Central carbon: the paper labels it, so "this is how the paper draws it too" was wrong.
- Tool gaps were checked only against `draw_figure`; several are not gaps in `compose_chemical_figure`.

Unverified in this folder:
- The final-render results (`checks_passed: true`, readback `matched`, no lint issues) and the 300 s timeouts: no validation output or log is present.
- That `rendered.png` is a desktop ChemDraw render: `replay.py` runs offline and writes only a CDXML file.
- The `draw_figure` claims about the largest-ring fill and the `*` balance check were not checked in code.

Match rows re-checked against the images:
- `compound_label_face` bold: holds in both images. The paper's suffixes are subscripted; the replica's are not. Counted as yes for face only.
- `compound_label_color` black: holds in both images.
- Corrected matched count: 2 of 16 (unchanged).

Extra checks, not counted:
- Colours: the paper uses blue N and orange Au (also in the TS_Interconv frame); the replica is all black. Not reproduced.
- Abbreviations: the paper writes Me and i-Pr as text; the replica draws them as skeletons. Not reproduced.
- Proportions: bond/cap ratio about 2.1 against the card's 2.0 by eye. Line weight: strokes look about 3-4 px against a bond of about 69 px, roughly 0.05 against the card's 0.04. This is a rough visual estimate and is not verified.
- Yields and conditions: crop 08 has no yields and no conditions block. The reagent above the arrow comes from the brief, not from the crop. Not applicable.
- Layout: the replica is a divergent scheme; the paper is an energy profile. Not matched.
