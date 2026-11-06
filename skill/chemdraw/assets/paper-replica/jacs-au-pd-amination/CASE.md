# JACS Au: Pd-catalyzed amination in water (Scheme 5, recycling reaction)

Source: K. S. Iyer, R. D. Kavthe, R. M. Lammert, J. R. Yirak, B. H. Lipshutz, "Ligated Pd-Catalyzed Aminations of Aryl/Heteroaryl Halides with Aliphatic Amines under Sustainable Aqueous Micellar Conditions", *JACS Au* **2024**, *4*, 680-689. DOI: [10.1021/jacsau.3c00742](https://doi.org/10.1021/jacsau.3c00742).

Licence: CC BY 4.0, © the authors 2024; reference crop reproduced under that licence.

Drawing style: the `acs1996` preset in `brief.json` (ChemDraw's ACS Document 1996 style sheet, the default); see `cdx.py styles`.

## What is reproduced

The reaction at the top of Scheme 5 (recycling studies): 1-[bis(4-fluorophenyl)methyl]piperazine (25b) and 1-bromo-3-nitrobenzene (25a) give 1-[bis(4-fluorophenyl)methyl]-4-(3-nitrophenyl)piperazine (25). Conditions are copied from the scheme; the yield is the cycle 0 value (99%) from the table under the scheme. The recycling table and the grey "initial reaction + 3 recycles" box are not drawn.

| ID | Structure (SMILES in brief.json) | OCSR (MolScribe / MolNexTR / MolVec) |
| --- | --- | --- |
| 25b | 1-[bis(4-fluorophenyl)methyl]piperazine | MolScribe and MolNexTR match, plus a stray one-atom fragment from the crop edge; MolVec reads one F as CH3. Used the name from the paper. |
| 25a | 1-bromo-3-nitrobenzene | all three match |
| 25 | 1-[bis(4-fluorophenyl)methyl]-4-(3-nitrophenyl)piperazine | all three match |

The structures follow the compound names and the drawing in the paper; 25 is the C-N coupling product of 25a and 25b.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/paper-replica/jacs-au-pd-amination/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` without network access and writes `figure.cdxml` and `validation.json`. Compare the PNG with `reference.png`; `rendered.png` is the expected ChemDraw rendering.

## Differences from the paper

- Layout: the paper stacks 25b above 25a with a "+" between them; the brief draws the two substrates side by side on one row.
- Nitro groups are drawn as charged N+/O- bonds, where the paper uses an NO2 label.
- Compound labels are plain, not bold, and the C-N bond formed is not highlighted in purple.
- "KOtBu" is plain text; the paper uses the same plain form in this scheme.
- The paper's coloured note "(aqueous layer is recycled)" is drawn in black; the yield (99%) is placed under the conditions instead of in the table.
- The recycling table (cycles 1-3: 97, 98, 90%) is omitted.
