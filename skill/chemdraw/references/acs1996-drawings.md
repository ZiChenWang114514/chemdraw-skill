# ACS Document 1996 drawings (exams, lectures, papers)

Use `scripts/acs_builder.py` when a figure needs things a plain molecule drawing does not give: abbreviation nodes such as C10H21 or C6H13 with correct subscripts, Chinese annotations, bold compound codes in boxes, reaction arrows with conditions, resonance pairs, charges, radicals and lone pairs. For a single unlabeled molecule `draw_molecule` is enough; for exact reproduction of a paper figure use the [figure manifest](publication-figures.md).

The style is fixed to ACS Document 1996: bond 14.4 pt, line 0.6, bold 2.0, hash spacing 2.5, margin 1.6, Arial 10 pt labels and captions. Coordinates are points, x right, y down.

## From a JSON spec

```bash
cdx.py build spec.json out.cdxml --render
```

```json
{"objects": [
  {"type": "molecule", "smiles": "[*:1]/C=C/C(=O)OCC", "at": [80, 60], "labels": {"1": "C10H21"}},
  {"type": "label_box", "at": [80, 100], "text": "A"},
  {"type": "arrow", "from": [175, 60], "to": [245, 60]},
  {"type": "text", "at": [210, 50], "text": "H{sub:2}, Pd/C"},
  {"type": "text", "at": [210, 76], "text": "EtOH，25 °C"},
  {"type": "molecule", "smiles": "[*:1]CCC(=O)OCC", "at": [325, 60], "labels": {"1": "C10H21"}},
  {"type": "label_box", "at": [325, 100], "text": "B"}
]}
```

This is [assets/acs1996/example.json](../assets/acs1996/example.json); its native render is `assets/acs1996/example.png`.

This build spec is not the figure manifest of [publication figures](publication-figures.md), although both list typed objects: the build spec places objects with `at` and rich text with `{sub:...}` markup, while the manifest uses `position`, `runs` and a `version` field. Do not mix fields between them.

| Object | Fields |
| --- | --- |
| `molecule` | `smiles`; `at` (centre); `labels` map from dummy-atom map number to abbreviation; optional `rotate` (degrees), `flip`, `displays` (bond index → `WedgeBegin`/`WedgedHashBegin`/`Bold`/…), `radicals` (atom indices), `lone_pairs` (`[atom, "left"|"right"|"up"|"down"]`), `hide_charge_label` |
| `text` | `at`, `text` (markup), optional `size`, `align` (`Left`/`Center`/`Right`), `bold` |
| `arrow` | `from`, `to`, optional `kind`: `forward` or `resonance` (double-headed) |
| `box` | `from`, `to` corners, optional `round` |
| `label_box` | `at`, `text`, optional `width`: bold Arial code in a rounded box |

## Rules that matter

- **Abbreviations.** Write the substituent as a dummy atom `[*:n]` and map `n` to the label. The node is saved as a real `GenericNickname`, so the label stays editable chemistry. Digits become subscripts automatically. When the bond leaves to the right, the label is reversed (H21C10) so that the attachment atom touches the bond.
- **Markup.** `{i:x}` italic, `{b:x}` bold, `{bi:x}` bold italic, `{sub:x}`, `{sup:x}`. Use the true minus sign `−` in charges.
- **Chinese text.** CJK characters and full-width punctuation are written in SimSun (font 5); Latin text, digits and symbols in the same string stay in Arial. Without the separate font entry ChemDraw renders boxes. In JSON specs, CJK text may be written directly or as `\uXXXX` escapes.
- **Unknown-species codes.** Exam convention: codes such as A, B, X, L in bold Arial. Use `label_box` or `{b:...}`.
- **Stereo.** Wedges come from the SMILES via RDKit; pass `displays` only to match a required depiction, then check readback.
- **Special bonding.** For ylides or resonance forms that RDKit would normalize, use the library API with explicit `coords` and `label_text`, or write the fragment nodes directly, for example a phosphonium ylide drawn as the P⁺–CH⁻ ↔ P=CH resonance pair.
- **Layout.** Leave at least about 25 pt between a molecule's bounding box and condition text. Long abbreviations widen the box. Check the PNG.

## Library use

```python
import sys; sys.path.insert(0, '<skill>/scripts')
from acs_builder import Fig
fig = Fig()
pts = fig.mol('[*:1]C(=O)[O-]', at=(100, 80), labels={1: 'C17H35'})
fig.text(100, 120, '{b:K} (tetraene)')
fig.write('k.cdxml')
```

Run it with `cdx.py py k_figure.py`, then `cdx.py render k.cdxml`.

## Putting figures into Word

Insert the 300 dpi PNG at its native size (width in cm = pixel width / 300 × 2.54). Every figure then shares the same 14.4 pt bond length and 10 pt font, which reads consistently in a printed paper. Keep the CDXML beside the document as the editable source. Re-export the PDF after replacing images and inspect the pages.
