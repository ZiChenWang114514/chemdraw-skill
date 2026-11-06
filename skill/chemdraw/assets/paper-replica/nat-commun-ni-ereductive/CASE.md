# Nat. Commun. replica: enantioselective electroreductive benzylic arylation

Source: Y.-Z. Wang, B. Sun, J.-F. Guo, X.-Y. Zhu, Y.-C. Gu, Y.-P. Han, C. Ma, T.-S. Mei, Enantioselective reductive cross-couplings to forge C(sp2)–C(sp3) bonds by merging electrochemistry with nickel catalysis, *Nat. Commun.* **2025**, *16*, 1108. DOI: [10.1038/s41467-025-56377-w](https://doi.org/10.1038/s41467-025-56377-w).

Licence: CC BY 4.0, © the authors 2025; reference crop reproduced under that licence.

Drawing style: the `nature_portfolio` house style in `brief.json` (bold labels, yield on the label line, substrate skeleton in teal; base preset Nature Research, 10.8 pt bonds); see `cdx.py styles`.

## What is reproduced

The scheme at the head of Table 1 (reaction optimization): 1-chloropropylbenzene **1a** and methyl 4-bromobenzoate **2a** give (R)-methyl 4-(1-phenylpropyl)benzoate **3a** under nickel-catalysed electroreductive conditions. Conditions are copied from the paper; the yield line uses entry 1 (isolated yield 85%, 90% ee).

| Id | SMILES | Basis |
| --- | --- | --- |
| 1a | `CCC(Cl)c1ccccc1` | drawing; MolNexTR and MolScribe (first fragment) agree, MolVec misreads C as B |
| 2a | `COC(=O)c1ccc(Br)cc1` | name in the text; MolNexTR and MolVec agree |
| 3a | (R)-isomer, stereo SMILES in `brief.json` | drawing; MolScribe returns the same stereo SMILES, MolNexTR drops the methyl, MolVec misreads C as B |

The wedge in the paper puts Et toward the viewer with phenyl on the left and the aryl ester on the right, which is the R centre.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/paper-replica/nat-commun-ni-ereductive/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` without network access and writes `figure.cdxml` and `validation.json`. Compare the render with `reference.png`; `rendered.png` is the expected ChemDraw output.

## Differences from the paper

- CO2Me is drawn as the full ester rather than the abbreviation.
- In **3a** the ethyl group points down on a hashed bond instead of up on a wedge; the configuration is the same.
- The yield and ee are printed under the conditions; the paper gives them in the table rows.
- The paper's colour highlights (blue substrates, red new bond), bold compound numbers and the shaded table background are not reproduced.
