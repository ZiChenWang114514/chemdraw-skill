# Sarpong group, Nat. Commun. 2024: cephalotane structure panel (Figure 1A, left part)

Source: Sarpong et al., "Late-stage benzenoid-to-troponoid skeletal modification of the cephalotanes exemplified by the total synthesis of harringtonolide", *Nat. Commun.* **2024**, *15*, 4125. DOI: [10.1038/s41467-024-48586-6](https://doi.org/10.1038/s41467-024-48586-6).

Licence: CC BY 4.0 (as recorded in the `sarpong_group` house-style card); the reference crop is reproduced under that licence.

Figure type: `structure_panel` (house style `sarpong_group`, base preset `nature`). The drawing is made with `kind: "scope"` because no structure-panel drawer exists (see Tool gaps).

## What is reproduced

Of the crop (Figure 1A, left part of the figure), three items:

- the boxed C18 and C19 benzenoid core, drawn as `C18 & C19-benzenoids` (the dashed top methyl is drawn as a plain methyl);
- cephanolide A (1), with its phenol OH and ether bridge;
- ceforalide H (2), with the dearomatised ring A (ketone and ring-fusion OH) and the same ether bridge.

Not reproduced: the family structure (cephanolides A-D and ceforalides A-G, with red variable substituents), the grey block arrow and "previous work" text, the grey "common intermediate" box at the right edge of the crop, the bold front bonds of the cage, the grey ring letters A-E, the grey frame, the bold teal step counts, and the bold compound numbers.

## Structures

The SMILES in `brief.json` were read by eye from the high-resolution Figure 1 of the paper (2000 px wide, PMC open-access image in the chemdraw-papers folder) and built atom by atom from a bond list with RDKit, so the connectivity is the one that was read, not a copied structure. OCSR (`cdx.py ocsr`, decimer-api only, one engine) returned no usable structure for this crop: its outputs contained Hg atoms and a fragment that does not match the figure. Checks: RDKit valence and formula only (C19H22O2 for the core, C18H18O4 for cephanolide A, C18H18O5 for ceforalide H). Constitution only: the relative configuration shown by bold and hashed bonds and the H orientations are not encoded, so the cage is not stereo-correct in the replica.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-01/replay.py NEW_DIR
```

`replay.py` calls `draw_figure` on `brief.json` offline. Because the brief is a scope panel, its output is a folder (`panel/page-001.cdxml`), not one `.cdxml` file. `rendered.png` is the ChemDraw render of that page (drawn with `cdx.py draw` and `cdx.py render`; draw about 3 min, render about 4.7 min on this machine).

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| family members side by side | family panel, cephanolide A (1), ceforalide H (2) and box in a 2 x 2 arrangement | three structures in one row, family not drawn | no |
| differing atoms in dark red #800000 | red substituents on the family, OH, ether O and bonds in 1 and 2 | no colour on any atom or bond | no |
| name with bold number in parentheses | "cephanolide A (1)", bold number | "cephanolide A (1)", plain | no |
| step count below in bold italic teal #0C5C61 | "(total 10 steps)", "(total 11 steps)" | not drawn | no |
| core skeleton in thin grey frame | grey box around the C18 and C19 core | no frame | no |
| grey ring letters A-E | grey A, B, C, D, E on the core | no ring letters | no |
| highlight_fill null | grey filled box (#CCCCCC) behind the "common intermediate" structure at the right edge of the crop | no filled highlight | no |
| compound label colour #000000 | black | black | yes |
| compound label face bold (top level) | bold numbers, plain names | all plain | no |
| aromatic rings kekule | boxed core ring A drawn with dashed inner lines; the cephanolide A ring uses solid inner lines | kekule double bonds in ring A | no |
| abbreviate groups (Me) | "Me" labels on every methyl | bare line methyls | no |
| bold heavy bonds (about 3x line width) on the near face of the cage | heavy front bonds in 1 and 2 | plain bonds throughout | no |

Matched 1 of 12 items after audit (the replica first claimed 3; see Audit). The card's claim about blue natural-product names is not counted here: the names in crop 01 are plain black type.

## Differences from the paper

- Family structure (cephanolides A-D and ceforalides A-G) not drawn; only 1 and 2 and the core box.
- No bold front bonds, no hashed bonds, no stereo, so the cage is flat; the paper's 3D depiction is lost.
- Compound labels plain, not bold; the step counts are missing.
- Methyls drawn as bond lines rather than "Me".
- Red colour for changed atoms and bonds is missing; the core and both targets are black.
- Grey frame, grey ring letters and the grey block arrow are missing.
- The default "Substrate scope" heading is printed above the panel even though the brief title is empty.
- Ceforalide H: the cross-conjugated ring A with the ring-fusion OH is drawn with the C=O and OH labels overlapping a bond (see the rendered PNG). The lint step reported no issue.

## Tool gaps

- No `structure_panel` drawer: `draw_figure` has scheme, scope and mechanism kinds only. A panel with no arrows must be faked as a scope grid.
- House-style conventions are not applied to scope panels ("house conventions apply to schemes only"), so bold labels, abbreviations and colours cannot be set for this figure type.
- No per-atom or per-bond colour for a structure in any kind (needed for the dark red changed atoms and the red substituents of a family).
- No bold (heavy) bond or wedge option for a flat drawing of a caged skeleton; the 3D front-bond look needs stereo that the brief cannot express for these structures.
- No grey frame, grey ring letters or teal caption under a structure.
- No option to suppress the automatic "Substrate scope" title.
- Scope panels do not abbreviate methyl to "Me" under the house style.
- The lint step did not catch an overlap between a C=O/OH label and a bond in the dearomatised ring.
- OCSR on this crop returned invalid or wrong structures from one engine and nothing to compare against.
- `cdx.py draw ... --render` on a scope panel exceeded the 300 s draw_figure timeout; draw and render had to be run separately.

## Audit

Checked by eye on zoomed crops of `reference.png` and `rendered.png`, and against the toolkit code (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`, `figure_scope.py`, `figure_house.py`). No draw or render was repeated.

Table corrections:

- `highlight_fill`: the crop has a filled grey box (sampled RGB 204,204,204) behind the "common intermediate" molecule at the right edge. The replica omits it. Not matched.
- `aromatic rings kekule`: the boxed core ring A is drawn with dashed inner lines, not kekule double bonds. Only the cephanolide A ring uses solid inner lines. Not matched.
- `compound label colour`: kept as matched (black in both, sampled RGB 0,0,0).
- `heavy front bonds`: the core box shows no heavier bonds, so the paper cell now lists only 1 and 2.
- Count: 1 of 12, not 3.
- Card error: the card's "natural-product names in bold italic blue" is not what crop 01 shows (plain black names).
- Missing from this folder: no `panel/` output and no `validation.json`, so `rendered.png` cannot be traced to a replay here. There is no `card_errors` field in any result.
- The SMILES formulas match the stated values (RDKit: C19H22O2, C18H18O4, C18H18O5). The drawn connectivity was not checked atom by atom against the reference.

Tool gap statements that the code contradicts or that need narrowing:

- "No per-atom or per-bond colour in any kind" is overstated. Scheme drawings accept house-style `substrate_colors` (paints a substrate's atoms and bonds) and `new_bond_color` (colours bonds formed in a step, via atom mapping), and species accept `atom_halos` and `ring_fills`. The real gap is that scope panels take none of these, and that changed atoms or rings cannot be named in a structure panel.
- "The 3D front-bond look needs stereo" is the wrong reason. A bold bond is a display property, not stereo. No drawing path exposes it, and the card's `bold_width` is not applied anywhere.
- "No option to suppress the 'Substrate scope' title" holds for an empty title (`figure_scope.py` line 140: `brief.get("title") or "Substrate scope"`). A whitespace title was not tested.
- "House conventions apply to schemes only" is confirmed: `apply_house_conventions` is called only from the scheme path.
- "No structure_panel drawer" is confirmed: the kinds are scheme, scope and mechanism.

Tool gaps the replicator missed:

- No dashed inner aromatic ring style. `aromatic_rings` accepts only `circle`, which the scheme path skips.
- No font face, colour, or bold or italic runs for scope labels or free annotations (step counts, "previous work"). Scope labels bind to a table with no style fields.
- No grey or teal text colour, and no free-text annotation kind.
- No outlined box or grey filled rounded rectangle behind a molecule. `ring_fills` fills one ring only.
- The lint step missed the C=O/OH overlap on ceforalide H. Confirmed by eye: the OH label sits on ring and bridge bonds, and the C=O label runs into a bond at the top right.
