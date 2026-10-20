# Reaction scheme examples

Thirty editable reaction schemes demonstrate the supported layouts and notation. Each example includes a YAML or compact-text description, CDXML, and a ChemDraw PNG preview.

## Linear Layouts (single step)

| # | File | Feature shown |
|---|------|---------------|
| 01 | `01_buchwald_linear` | Buchwald coupling, above-arrow structure + equiv text |
| 02 | `02_suzuki_linear` | Suzuki coupling, above-arrow boronic acid |
| 03 | `03_snar_linear` | SNAr, text-only conditions (no above structure) |
| 04 | `04_amide_coupling_linear` | Amide coupling, above-arrow amine |
| 05 | `05_boc_deprotection_linear` | Boc removal, simple 2-line conditions |
| 22 | `22_reductive_amination` | Reductive amination, above-arrow aldehyde |
| 23 | `23_mitsunobu` | Mitsunobu, above-arrow alcohol |
| 24 | `24_grignard_addition` | Grignard, text-only conditions |
| 21 | `21_name_resolution` | Name resolution: `name: "morpholine"` using the reagent database |

## Sequential Layouts (multi-step, single row)

| # | File | Feature shown |
|---|------|---------------|
| 06 | `06_two_step_sequential` | 2 steps, SNAr + Boc removal |
| 07 | `07_three_step_sequential` | 3 steps, Buchwald + NBS + Suzuki |
| 25 | `25_two_step_with_above_structures` | 2 steps, above-arrow structures on BOTH steps |
| 27 | `27_sequential_run_arrows_no_wrap` | 2 steps + run arrows (mass/yield below scheme) |

## Wrap:Repeat (multi-row L→R, most common pattern)

| # | File | Feature shown |
|---|------|---------------|
| 08 | `08_wrap_repeat_4step` | 4 steps in 2 rows (2+2), above-arrow structure |
| 09 | `09_wrap_repeat_5step` | 5 steps in 2 rows (3+2) |
| 10 | `10_wrap_repeat_with_run_arrows` | 3 steps in 2 rows (2+1) + run arrows per step |
| 11 | `11_wrap_repeat_with_dashed` | 3 steps in 2 rows, last step is dashed (planned) |

## Wrap:Serpentine (zigzag L→R / R→L, thesis/paper style)

| # | File | Feature shown |
|---|------|---------------|
| 12 | `12_serpentine_5step` | 5 steps: Row 1 L→R (3), vert arrow, Row 2 R→L (1) |
| 13 | `13_serpentine_7step` | 7 steps: Row 1 L→R, vert, Row 2 R→L, vert, Row 3 L→R |

## Letter Conditions (thesis-style a, b, c keys)

| # | File | Feature shown |
|---|------|---------------|
| 14 | `14_letter_conditions_3step` | 3-step sequential + condition key block below |
| 15 | `15_letter_conditions_serpentine` | 5-step serpentine + letter conditions + key block |

## Arrow Styles

| # | File | Feature shown |
|---|------|---------------|
| 11 | `11_wrap_repeat_with_dashed` | Dashed arrow (planned step) |
| 16 | `16_failed_arrow` | Failed arrow (bold X overlay) |

## Divergent (one starting material → multiple products)

| # | File | Feature shown |
|---|------|---------------|
| 17 | `17_divergent_buchwald_sar` | 3 products (morpholine, piperidine, aniline), last one failed |
| 18 | `18_divergent_4products` | 4 Suzuki products from same bromide |
| 26 | `26_divergent_success_vs_failure` | 2 products: SNAr success + Buchwald failure |

## Stacked Rows (independent sub-schemes with section labels)

| # | File | Feature shown |
|---|------|---------------|
| 19 | `19_stacked_rows_comparison` | 3 sections: same reaction, different conditions |
| 20 | `20_stacked_rows_different_routes` | 3 sections: different scaffolds, section (iii) is 2-step |
| 28 | `28_stacked_multi_step_sections` | 2 sections with 2 steps each |

## Compact Syntax

| # | File | Feature shown |
|---|------|---------------|
| 29 | `29_compact_syntax_linear` | Single-step via compact .txt format |
| 30 | `30_compact_syntax_multistep` | 3-step sequential via compact .txt format |

## What to look for during visual inspection

- [ ] Structure orientations — do rings look normal or rotated oddly?
- [ ] Spacing — is there enough gap between structures, arrows, and text?
- [ ] Arrow lengths — do they accommodate the conditions text?
- [ ] Above-arrow structures — properly centered, equiv text visible?
- [ ] Text readability — font sizes, subscripts rendered?
- [ ] Multi-row alignment — rows lined up at left margin?
- [ ] Serpentine — R→L rows correctly mirrored?
- [ ] Vertical arrows — positioned at correct edge with conditions beside?
- [ ] Run arrows — aligned with parent step arrows?
- [ ] Dashed arrows — clearly distinguishable from solid?
- [ ] Failed X — visible and centered on arrow?
- [ ] Letter conditions — small italic letters visible on arrows?
- [ ] Condition key — legible text block below the scheme?
- [ ] Section labels — "(i)", "(ii)" visible at left margin?
- [ ] Compound labels — bold numbers below structures?
- [ ] Divergent branching — products vertically separated with clear arrows?
