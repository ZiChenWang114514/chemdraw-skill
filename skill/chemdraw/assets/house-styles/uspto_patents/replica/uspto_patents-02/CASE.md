# US 10,519,146 B2: generic formula (I) (uspto_patents, markush)

Source: Lanman et al. (Amgen), US 10,519,146 B2, 2019 (KRAS G12C inhibitors and methods of using the same), column 57, formula (I) and its definitions. Licence: public domain (US patent), as stated on the house-style card.

Drawing style: the `uspto_patents` card (publisher kind, base preset `j_mol_mod`), figure type `markush`, crop `evidence/uspto_patents-02.png`. The card's conventions were not applied to this drawing: a scope panel takes only the base preset, and the tool's own report says house conventions apply to schemes only. Table rows that match on colour, face or Kekule form are therefore matches of the base preset, not of the card (see Audit).

## What is reproduced

The core of the generic formula (I) only: the benzo-fused isothiazole (2,1-benzisothiazole) skeleton with R2 and R3 on the benzo ring and R4 on the isothiazole carbon. The ring positions E1 and E2 are present as ring atoms, and the R groups are drawn as attachment points.

Not reproduced: the definitions text (wherein E1 and E2 ... R4 is ...), the R4 option fragments and the ring-A and L fragments below the formula, and the line numbers and two-column page.

The core was transcribed by eye from the crop, not read by OCSR (the generic formula is not a closed structure). The SMILES is a transcription with dummy atoms for the R positions, checked with RDKit (12 heavy atoms read back with the expected ring connectivity):

- scaffold SMILES: `*c1cc2nsc(*)c2cc1*`; dummy atom 0 is R2 (on the benzo carbon next to E1), atom 7 is R4 (on the isothiazole carbon), atom 11 is R3 (on the benzo carbon next to E2)

Simplifications, forced by the tool: E1 and E2 are drawn as plain ring carbons (CR1 with R1 = H); the paper's claim is N or CR1, so the replica is one of the allowed cases, not the general formula.

Tool: `cdx.py draw` with `kind: "scope"` (one structure, one label), the only brief kind that accepts a single structure with no reaction. The house style is applied only as its base preset, because scope panels take only the base preset (the brief reports this).

Replay: `replay.py` is the jacs-au file with the docstring changed. It has not been run. For `kind: "scope"` the output path is a folder, not a `.cdxml` file, so it needs a change before it is used again; that is a tool-side point, recorded below.

## Attempts

1. Scope brief with title "Formula (I)" (`scope_try1`). The draw wrapper reported `tool_timeout` after 300 s under heavy load on the machine, but the output files were complete; ChemDraw rendering failed (OpenBLAS memory error, then worker exit 143). The title is not in the paper, so it was dropped.
2. Scope brief without a title (`scope_try2`, the one in this folder). Drawn in 251 s with no error; render succeeded (`rendered.png`). The panel still adds a "Substrate scope" heading, which the paper does not have.

## Replica check against the card (markush claims and top-level conventions)

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| formula label (I) plain, flush right above the drawing | (I) flush right at the right margin, level with the top of the structure | (I) plain, under the structure at the left, as a compound label | no (face yes, placement no) |
| R groups as R with superscript numbers (r_group_style superscript_number) | R2, R3, R4 with superscript numbers | plain R on all three positions; no numbers | no |
| ring atoms E1, E2 with subscript numbers | E1, E2 subscripted, ring positions labelled | not drawn; plain carbons | no |
| unspecified ring as open loop or circle with the letter inside (ring A) | ring A circle in the lower fragments | not drawn (not in the core) | no (not reproduced) |
| attachment point as wavy line across the bond | wavy lines on the lower fragments | none drawn (not in the core) | no (not reproduced) |
| variable definitions as running justified text beginning "wherein" | yes, body text | not drawn | no (not a drawing item) |
| table_style none | no table | no table | yes (trivial: a formula has no table either way) |
| black line art, no colour (variation_color null) | black | black pixels only (from base preset, not card) | yes |
| Times serif atom labels | Times | Times-face labels; 8 pt is the replica's own figure, not checked against the card's 7.5 pt estimate; from base preset | yes (face only) |
| Kekule rings (aromatic_rings kekule) | benzo ring in Kekule form | benzo ring in Kekule form (from base preset, not card) | yes |
| bond length about 3.0 cap heights (measured 3.0) | 64 px bond over 21 px cap height, 3.0 | 14.4 pt bond over 8 pt label, cap height about 5.3 pt by estimate, about 2.7 | no (2.7 against 3.0; labels visibly larger relative to the bond) |
| line width 0.047 bond (measured) | 3 px over 64 px, 0.047 | 0.6 pt over 14.4 pt, 0.042; the 0.6 pt value is not in this folder | no (not verified; 0.042 is not 0.047) |
| scheme title centred and underlined | no title on the formula | "Substrate scope" heading added by the tool, not underlined | no |
| general formula label bold or not | plain | plain | yes |
| compound label colour #000000 | black | black | yes |
| bicyclic orientation of the paper drawing | N at the top right, C-R4 at the bottom right | N at the bottom right, C-R4 at the top right (flipped vertically); connectivity read back | no |
| line numbers 5, 10, 15 and justified two-column body text | yes | not drawn | no (not a drawing item) |

Counts for the markush-specific claims (five signature features, r_group_style, table_style): 1 of 7 match (table_style none, which is trivially true). Top-level conventions: black, Times face, Kekule and label colour match, but all four come from the base preset rather than the card; bond and line geometry do not match; title, label placement and orientation do not.

## Differences from the paper

- The formula label (I) is under the structure, left, as a scope compound label. The paper has it flush right above the drawing.
- R2, R3 and R4 all read R. The paper numbers them, so the replica does not show which group is which.
- E1 and E2 are plain carbons. The paper labels them, and the claim is N or CR1, so the replica is one case of the formula.
- The bicyclic is flipped vertically relative to the paper.
- The "Substrate scope" heading is added by the tool; the paper has none.
- The definitions text, the lower R4 fragments, the ring A circle, the wavy attachment bonds and the line numbers are not drawn.
- rendered.png was made with desktop ChemDraw from `scope_try2`; the rendering is the only one checked by eye.

## Tool gaps

- No Markush drawer: `draw_figure` cannot write R groups with superscript numbers (R2, R3, R4) or ring atoms with subscript numbers (E1, E2). A dummy atom becomes a plain `R` label (CDXML GenericNickname) with no number and no subscript.
- No ring-atom labels: variable ring positions (N or CR1) can be written only as a fixed element, not as a labelled placeholder.
- No formula label placement: a scope panel puts its label below the structure at the left; there is no option for a flush-right formula number above the drawing.
- No ring placeholder: an open loop or circle with a letter inside (ring A) cannot be expressed.
- No wavy attachment bond and no bond-crossing marker for an open substituent position.
- No definitions block: the "wherein ..." text is not a drawing object.
- A scope panel adds a "Substrate scope" heading when no title is given, and no switch to remove it was found. A title of "" was not tried, but the code (`figure_scope.py`, `brief.get("title") or "Substrate scope"`) treats "" as missing, so it would give the same heading.
- The scheme kind needs at least one step, so a single generic formula can only go through the scope kind.
- The replay script for a scope brief writes to a folder; `replay.py` as copied from the jacs-au case assumes a single `.cdxml` path and must be adapted before reuse.
- Operational: under the load on this machine `draw_figure` took 250 to 300 s and ChemDraw rendering failed twice on the first CDXML (OpenBLAS allocation error, worker exit 143). The second render succeeded.
- The `markush_compile` tool (spec-driven, with a native PNG) exists in the MCP signatures but is not wired to house styles and was not used here, because the brief specified `draw`. A spec-based replica is the next test for this crop.

## Audit

Checked by eye against `reference.png` and `rendered.png` (both at 3x), by connected-component measurements on both PNGs, by RDKit on the scaffold SMILES, and by reading the toolkit code.

Overclaims corrected in the table and header above:

- The header said the card "was used as it stands". It was not. `figure_scope.py` keeps only the base preset (`j_mol_mod`) for a scope panel, and the brief's own report says "house conventions apply to schemes only". The black, Times face, Kekule and label colour rows match the preset, not the card.
- Bond length was marked "approx". It is not a match. Replica label cap height is about 21 px against a bond of about 57 px (ratio about 2.7). In the reference the cap height is about 17 px and the E1 to E2 distance across the ring (two bonds, para) is about 109 px, which gives a bond of about 55 px and a ratio of about 3.2 to 3.4. The replica labels are visibly larger relative to the bonds.
- Line width was marked "approx". It is not verified. The 0.6 pt value does not appear anywhere in this folder, and 0.042 is not the card's 0.047. Visually the stroke weight is similar to the reference, so this is unverified rather than refuted.
- table_style "none" is trivially true for a formula drawing and says nothing about the card.
- Times size: the replica's 8 pt is the replicator's own figure. The card gives 7.5 pt as an estimate. The face matches; the size was not checked.

Confirmed by image or code, unchanged: (I) sits bottom left and plain, not flush right above the drawing; R groups carry no superscript numbers and E1/E2 are absent; the "Substrate scope" heading is present; the bicyclic is flipped vertically (reference N at top, replica N at bottom); the scaffold SMILES connectivity matches the reference (R2 carbon, then CH, then the N-bearing fused carbon; R3 mirrored), so the flip is the only geometric difference.

Not verifiable from this folder: the `scope_try1` and `scope_try2` directories, their logs, the 251 s and 300 s timings, the OpenBLAS and exit-143 failures, and the statement that `rendered.png` came from `scope_try2`. `replay.py` has not been run.

Corrected count: markush-specific conventions 1 of 7 (unchanged, and the one match is trivial). Top-level conventions 5 of 10 match (black, Times face, plain label, label colour, Kekule), all from the base preset. Bond length and line width do not match.

Tool capabilities the replicator did not test (present in code, untested here):

- `markush_compile` (`markush/spec.py`, `label_runs`): atom labels take `^{...}` and `_{...}` markup, so `R^{2}` and `E_{1}` are expressible. The "no superscript R numbers" gap is specific to `draw_figure`.
- `markush` spec `kind: "variable_ring"` with a circle and a centre letter (`markush/draft_spec.py` header, `cdxml_writer.py` circles): ring A as a circle with the letter inside may be expressible, with an open part by a gap.
- `compose_chemical_figure` (`mcp_runtime/figure_tools.py`): text objects with rich runs (superscript and subscript, around lines 806 to 810), ellipse and rectangle objects, and a flush-right text alignment. Text alignment is only Left, Center or Right, so the "wherein" block can be placed but not justified.
- Bond display `Wavy` through template edits (`figure_tools.py` around line 995, `figure_editing.edit_bond_display`), and `CrossingBonds` through `figure_editing.apply_crossings`. Both suggest the wavy attachment and bond-crossing gaps are narrower than stated.
- Markush style keys `bond_length`, `font_size`, `line_width`, `bond_spacing` can take the card's measured geometry by hand. The house-style card is not wired to the markush path (no house reference in `markush/*.py`).
