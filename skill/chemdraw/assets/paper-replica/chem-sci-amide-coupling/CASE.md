# Chemical Science paper replica: DPDTC synthesis

Source: K. M. Freiberg, R. D. Kavthe, R. M. Thomas, D. M. Fialho, P. Dee, M. Scurria and B. H. Lipshutz, Direct formation of amide/peptide bonds from carboxylic acids: no traditional coupling reagents, 1-pot, and green, *Chem. Sci.*, 2023, **14**, 3462-3469. DOI: [10.1039/d3sc00198a](https://doi.org/10.1039/d3sc00198a).

Licence: CC BY 3.0 (as stated), © the authors 2023; reference crop reproduced under that licence.

Drawing style: the `rsc_journals` house style in `brief.json` (bold labels, reagents above and solvent below; base preset RSC (2 Column), 12.2 pt bonds); see `cdx.py styles`.

## What is reproduced

Scheme 1: 2-mercaptopyridine and triphosgene with Et3N (2 equiv) in acetone, 0 °C - rt, 16 h, give di(2-pyridyl) dithiocarbonate (1; DPDTC) in 89% yield on 6.5 g scale.

| Species | SMILES | OCSR (MolScribe, MolNextr, MolVec) |
| --- | --- | --- |
| 2-mercaptopyridine | `Sc1ccccn1` | 3 of 3 agree |
| triphosgene | `O=C(OC(Cl)(Cl)Cl)OC(Cl)(Cl)Cl` | MolScribe and MolNextr agree; MolVec returned nothing |
| 1; DPDTC | `O=C(Sc1ccccn1)Sc1ccccn1` | MolScribe and MolNextr agree; MolVec misread the thiocarbonyl core |

The structures follow the paper's text (DPDTC, triphosgene) and agree with the two consistent engines.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/paper-replica/chem-sci-amide-coupling/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

Compare the PNG with `reference.png` (the published scheme) and `rendered.png` (the expected ChemDraw output).

## Differences from the reference

- The two reactants sit side by side with a plus sign; the paper stacks 2-mercaptopyridine above triphosgene.
- The yield and scale line is placed under the arrow, not under the product label, and has no parentheses.
- Ring orientations differ, and the carbonyl O is black rather than blue.
- The note "(solid; easy to handle)" under triphosgene is omitted; it is commentary, not a condition.
- The step is reported as unbalanced because the drawing does not show the stoichiometry (2 equiv of thiol) or the HCl and CHCl3-derived by-products; the paper draws it the same way.
