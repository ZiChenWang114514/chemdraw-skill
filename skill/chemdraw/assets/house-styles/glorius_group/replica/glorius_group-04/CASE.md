# Glorius group, Figure 3 (DFT energy profile): isoxazolone ring contraction and azirine olefin insertion

Source: Glorius et al., *J. Am. Chem. Soc.* 2025, DOI [10.1021/jacs.4c18080](https://doi.org/10.1021/jacs.4c18080) (cyclic bifunctional reagents enabling a strain-release-driven formal [3+2] cycloaddition), Figure 3, panel "DFT Studies". Licence: CC BY 4.0 (from the house-style card `glorius_group`). The reference crop is `evidence/glorius_group-04.png`, copied here as `reference.png`.

Figure type: `energy_profile` (the card has no drawer for this type).

Drawing style: the `glorius_group` house style (base preset `acs1996`), applied with `cdx.py draw --render`.

## What is reproduced

The chemistry on the main path of the figure, as a two-step reaction scheme, because the tools have no energy-profile drawer:

- Step 1: `1a` (4,4-dimethyl-3-phenylisoxazol-5(4H)-one, `CC1(C)C(=O)ON=C1c1ccccc1`) gives `4a` (2,2-dimethyl-3-phenyl-2H-azirine, `CC1(C)N=C1c1ccccc1`) and CO2, with EnT written on the arrow.
- Step 2: `4a` and acrylonitrile (`C=CC#N`) give `3a` (`CC1(C)N=C(c2ccccc2)CC1C#N`), the 1-pyrroline from olefin insertion into the azirine C-C bond, drawn as the final product. The figure's singlet superscript is not reproduced; the label is the compound number only.

Both steps balance (C11H11NO2 = C10H11N + CO2; C10H11N + C3H3N = C13H14N2), checked with RDKit. The structures were read from the crop, not taken from OCSR. The azirine and the isoxazolone are unambiguous; the 1-pyrroline connectivity (C(Ph)=N, CH2 next to C(Ph), CH(CN) next to CMe2, N bonded to CMe2) was read from a 3x zoom.

The energies, the energy axis, all transition states and intermediates, the MECP points, the second EnT excitation of the azirine and the competing pathways are not drawn. Their absence is described under "Differences" and "Tool gaps".

## Files

- `brief.json`: the brief (style `glorius_group`, two steps, five species). The rendered figure was drawn from this brief.
- `rendered.png`: ChemDraw rendering of the brief, downscaled to 1200 px wide.
- `replay.py`: offline redraw of `brief.json`. Checked: it writes `figure.cdxml` and `validation.json` without ChemDraw.

## Card conventions against the crop

The first ten rows are the energy-profile conventions and signature features the card claims for this figure type. The remaining rows are the top-level scheme conventions that are visible in the crop.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_unit `kcal/mol` (energy_profile) | kcal/mol on the axis label, values as dG (dE) | no energies drawn | no |
| energy_label `delta_G` (energy_profile) | dG and (dE) on each level | not drawn | no |
| level_style `bars_solid_connectors` (energy_profile) | black level bars joined by solid connectors | not drawn | no |
| pathway_colors `#000000`, `#859795` (energy_profile) | black main path, grey dashed competing path | not drawn | no |
| ts_marker `none` (energy_profile) | TS named in the label (3TS-1), no double dagger | no TS drawn | no |
| bold species name with superscript multiplicity above dG (dE) (signature) | yes | compound labels bold, no multiplicity, no values | no |
| bare upward energy axis labelled dG (dE) in kcal/mol (signature) | yes | no axis | no |
| stage brackets under the x axis with italic names (signature) | "Isoxazolone ring contraction", "Olefin insertion into azirine" | none | no |
| thin grey frames for competing TS insets (signature) | two framed insets | none | no |
| spin densities on pink circles (signature) | 0.76, 0.46, 0.11 on 1a | none | no |
| compound_label_face `bold` | bold 1a, 4a, 3a | bold | yes |
| compound_label_color `#000000` | black | black | yes |
| substrate_colors, first `#2C0001` | the isoxazolone ring bonds and C=O of 1a are dark red-brown (`#260303` in the crop); the Ph and Me bonds and the N and O letters are black; the spin-density numbers are dark red-brown | whole 1a drawn in `#2C0001`, including the Ph and Me bonds and the labels | no |
| substrate_colors, second `#0203FE` | acrylonitrile drawn grey-teal, not blue | acrylonitrile drawn in `#0203FE` | no |
| reagent_text_color `#000000` | EnT in black, inside a grey circle icon rather than as text above an arrow | EnT in black text above the arrow | yes (colour only) |
| arrow_style `plain` | the crop has no reaction arrow; the only arrows are the vertical EnT arrow and the energy axis arrow | plain reaction arrows with solid heads | not verifiable, not counted |
| new_bond_color `null` | the forming bonds of the TS structures 3TS-2, 3TS-4a and 3TS-4b carry short pink marks (about `#EB659D`) | no coloured bonds | no |
| abbreviate_groups includes `Me` | gem-dimethyl drawn as bare bonds, no Me label | Me labels drawn | no |
| abbreviate_groups `Ph`, `CN` | Ph and CN labelled | Ph and CN labelled | yes |
| conditions_split `reagents_above_solvent_below` | one reagent above the arrow (EnT), nothing below | EnT above; the tool skipped the split (listed under skipped) | not applied |
| show_plus_sign `true` | no plus sign in the crop (no multi-component reagent set) | plus signs drawn between species | not visible in crop |
| substrate_layout `inline_plus` | no inline substrate set in the crop | inline plus drawn for 4a and acrylonitrile | not visible in crop |
| aromatic_rings `kekule` | Ph abbreviated, ring not drawn | Ph abbreviated | not verifiable |
| single horizontal row | one horizontal energy profile | two rows (see differences) | no |

Count for the JSON: of the 10 energy-profile claims (the first ten rows), 0 match.

## Differences from the paper

- The figure is an energy profile; the replica is a reaction scheme of its chemistry. Levels, values, pathways, transition states, MECP points, stage brackets, insets and spin densities are absent.
- The route is shortened to two steps. The triplet steps (3IM-1', 3IM-1, the second EnT that excites the singlet azirine to the triplet, 3IM-3a) are not drawn, so the replica does not show the second energy-transfer step. Step 2 has no conditions in the brief, because the paper gives none for that step.
- The route wraps into two rows (step 1 on the first row, step 2 below), with 4a drawn twice. The paper is one horizontal profile.
- CO2 is drawn as an O=C=O structure with a plus sign. The paper writes CO2 as bold text on a curved arrow.
- Substrate colours: the card's second colour (`#0203FE`) is applied to acrylonitrile, which the paper does not colour blue (its acrylonitrile is grey-teal in the crop; the exact value was not confirmed by pixel sampling). The first colour covers the whole of 1a, including its Ph and Me bonds. In the paper the isoxazolone ring bonds and C=O are dark red-brown, while the Ph and Me bonds and the N and O letters are black.
- Ring fills: the paper fills the isoxazolone ring of 1a and the pyrroline ring of 13a with pale grey (`#DEE2E5`), and draws the 13a ring bonds in dark green (about `#244E41`). The replica has neither.
- Forming bonds: the TS structures carry short pink marks (about `#EB659D`) on the bonds being formed. Not drawn.
- Compound labels: the paper also carries a superscript singlet on 1a and 4a (labelled 11a and 14a in the paper), not only on the product. The replica labels them 1a, 4a and 3a.
- The energy-profile connector to 13a carries a break mark (two slashes) at the MECP-2 level. Not drawn.
- Me groups are labelled, while the paper draws the gem-dimethyl groups as bonds.
- The EnT symbol is the tool's plain text on the arrow; the paper uses a grey circular EnT icon with a circular arrow, not a cyan lamp.
- Product 3a carries the compound number only; the paper's superscript singlet (13a) is not reproduced, and whether the species label can carry it was not tested.

## Tool gaps

- No energy-profile drawer: no way to give level values (dG and dE in parentheses), level bars, solid or dashed connectors per pathway, a bare kcal/mol axis, multiplicity superscripts on species names, stage brackets with italic names, or framed insets. Spin-density circles are reachable with `atom_halos` (see Audit).
- Layout: a step with two products (1a to 4a plus CO2) does not continue the row, so step 2 starts a new row. The brief only continues a row for one-substrate, one-product steps, so a two-step route with a shared intermediate cannot be kept on one line.
- By-products: CO2 can only be drawn as a structure. There is no way to annotate an arrow with a small by-product (for example "-CO2") or to write a by-product as text.
- Conditions split: the card's `conditions_split` is listed under skipped, so above and below lines are kept as given with no split rule.
- Substrate colours colour the whole molecule. There is no option to colour only heteroatom labels or a chosen set of atoms, which the paper does here.
- Abbreviation control: `abbreviate_groups` cannot exclude Me for one figure while keeping Ph and CN labelled.
- EnT symbol: no icon for energy transfer (a circled EnT with a circular arrow, or the cyan lamp of the card's signature features) is available for step arrows.
- Render reliability: a render of the 720 pt row-budget variant (try 3) failed on the shared machine with "OpenBLAS error: Memory allocation still failed after 10 retries, giving up." The one retry did not return in the time available and was stopped. The 504 pt brief (try 2) rendered. The first render attempt (try 1) was stopped early by mistake, when a background task was stopped; it was rerun as try 2.

## Result

`rendered.png` is the ChemDraw rendering of the 504 pt brief. The report: `native.status` rendered, `readback` matched (6 of 6 structures, none missing or unexpected), `checks_passed` true, no lint issues, one note (step 2 has no conditions, none drawn).

## Audit

Checked against `reference.png` (900 px wide, the paper crop) and `rendered.png` (1200 px wide), using colour sampling of the crop and enlarged crops of the 1a, 3TS-2, 3TS-4a, 13a and EnT regions, and the toolkit code in `toolkit/cdxml_toolkit/mcp_runtime/` (`figure_draw.py`, `figure_house.py`).

Overclaims corrected in the table:

- `substrate_colors, first`: was "partial". The paper does not colour the whole molecule. Its ring bonds and C=O are dark red-brown, while the Ph and Me bonds are black. The replica colours all of 1a. Now not matched.
- `new_bond_color`: was "yes" with "no coloured bonds in the crop". The crop has short pink marks on the forming bonds of 3TS-2, 3TS-4a and 3TS-4b. The replica has none. Now not matched. The match was for the wrong reason.
- `arrow_style`: was "yes". The crop has no reaction arrow, only the vertical EnT arrow and the energy axis arrow. Not verifiable, not counted.
- `reagent_text_color`: the colour matches (EnT is black), but the paper sets EnT inside a grey circle icon. Kept as yes for colour only.
- `substrate_colors, second` (`#0203FE`, acrylonitrile): "no" stands, because the paper's acrylonitrile is not blue. The replicator's `#859795` value for it was not confirmed by pixel sampling.
- The Differences bullet on substrate colours said the paper colours only the heteroatom labels. That was wrong and is corrected above.

Corrected matched count: 4 of the 24 table rows. That is 0 of the 10 energy-profile rows, and 4 of the 14 top-level rows (compound label face, compound label colour, EnT colour, Ph and CN abbreviations). The earlier table had 6 yes and 1 partial among the top-level rows.

Not claimed in the table and not refuted here: proportions (bond length to cap height), line weight, yield placement and format (no yields in the crop) and conditions placement (no split conditions in the crop). Proportions and line weight were not measured.

Tool gaps the replicator missed:

- Ring fills are available. `ring_fills` in `figure_draw.py` takes a ring index and a colour (hex accepted), so the pale grey ring fill is reachable through the species decorations. `highlight_fill` only fills the largest ring of each final product, and this card sets it to null. This is a card and brief omission, not a missing tool.
- Spin-density circles are reachable with `atom_halos` (`atoms`, `color`, `radius`). The spin-density numbers (0.76, 0.46, 0.11) are not drawn and have no decoration in the brief, so they remain a gap.
- Pink marks on forming bonds of TS structures cannot be drawn. The TS structures are not in the brief, and `new_bond_color` only colours bonds that an atom mapping finds between a step's reagents and products.
- Connector break marks (the two slashes before 13a): I found no break-mark option in the toolkit's `figure_draw.py` decorations, so this stands as a gap for the energy-profile route.
- Superscript singlet on the compound numbers (11a, 14a, 13a in the paper): the replica labels are plain text and this was not tested, so it is an untested gap, not a confirmed one.

Not checked: the render failures (try 1 and try 3). The folder has no logs, so those claims are unverified.
