# Patent Markush structures

A Markush (generic) structure has variable labels (R^1, X, L^2), variable attachment points (a group drawn into a ring, `(R^B)_q`), variable rings (a circle labelled "A") and repeat counts. A plain SMILES cannot hold these, so a Markush is kept as a **`markush.json` spec**. The spec compiles to:

- `markush.cxsmiles`: CXSMILES with `$...$` atom labels, `m:` variable attachment and `LN:` repeat counts. Code writes this text itself, because RDKit drops `m:` when it writes CXSMILES.
- `markush.mol`: a V3000 molfile with `ENDPTS` bonds.
- `markush.cdxml`: an editable ChemDraw drawing with GenericNickname labels, `MultiAttachment` bonds and ring circles. It is for display only.
- `markush.png`: the native render.

Take the chemistry from the spec or the CXSMILES, never from reading the CDXML back. Readers turn generic labels into carbon and ignore `MultiAttachment`.

## Tools

| Tool | Use |
| --- | --- |
| `markush_validate(spec_path)` | Every error names the fix, for example `unknown atom 'ind:C9'; indole has N1, C2, C3, C3a, ...`. |
| `markush_compile(spec_path, output_dir, layout_path=None, render=True)` | Writes all four files into a new folder. `layout_path` makes the drawing follow the source figure. |
| `markush_enumerate(spec_path, count=5, seed=0)` | Samples concrete members from the definition values, as a sanity check. |
| `markush_detect(image_path, output_dir)` | Writes the image geometry (`graph.json`), the numbered marks (`marks.png`) and one row per text box (`labels.png`). |

## Spec format

The worked example is `examples/markush/indole-macrocycle.json` in the repository.

```json
{"version": 1,
 "fragments": [{"id": "ind", "template": "indole", "double": [["C2","C3"], ["C3a","C7a"], ["C4","C5"], ["C6","C7"]]}],
 "atoms": [{"id": "Z", "label": "Z"}, {"id": "nh", "element": "N", "h": 1},
           {"id": "ringA", "label": "A", "kind": "variable_ring"}],
 "bonds": [["ind:N1", "Z"], ["ind:C3", "nh"], {"a": "ca", "b": "nh", "display": "arc"}],
 "variable_position": [{"group": "RB", "label": "(R^{B})_{q}", "count": "q", "on": ["ind:C4", "ind:C6", "ind:C7"]}],
 "definitions": {"Z": {"text": "C1-3 alkyl", "values": ["[*:1]C", "[*:1]CC"]}}}
```

- Fragment atoms are addressed by locant (`ind:C3`), never by index. Plain atoms have `element`, or else a `label`, never both.
- Labels use `^{...}` for superscripts and `_{...}` for subscripts.
- A definition value has one `[*:n]` for each bond of its label. The `[*:1]`, `[*:2]` order follows the order of that label's bonds in `bonds`. Check the order for linkers such as L^1 and L^2, because a drafted spec cannot know which end the claim means.

## Image + claims workflow (built for small models)

A small, low-cost model can run the whole workflow, because code does everything that has to be exact: geometry, ids, the CXSMILES, the XML and validation. The model only reads text and answers small checklists. Each answer is JSON on a fixed schema, and code validates it.

```bash
cdx.py markush init WORK --image figure.png --text claims.pdf   # --crop X0 Y0 X1 Y1 for a full page
cdx.py markush next WORK                                        # prints one task
cdx.py markush submit WORK TASK answer.json                     # validates, then advances
cdx.py markush status WORK
```

Run `next`, answer, `submit` in a loop until `next` reports `done`. Each task prints `look_at` (images to open), `question`, `answer_shape` and an `example`. Answer with exactly that shape; a fenced JSON block is accepted.

| Task | What the model does |
| --- | --- |
| `labels` | Types the text of each numbered box in `labels.png`, for example `(R^{A})_{n}` or `NH`. |
| `labels_check` | Looks at the read-back image and lists wrong or unboxed text. |
| `review:N` | Compares the source with marks against the native redraw (and `diff.png`), and reports `missing_bonds`, `extra_bonds`, `bond_orders` and `text` by mark id. Empty lists accept. At most 3 rounds. |
| `definitions:NAME` | Turns one claim clause (already cut out by code) into `values` and `count_range`. |

Between tasks the tool drafts the spec from the image graph and the typed labels. It compiles the spec, renders it natively in the source layout and scores the ink overlap with the source (`fidelity.match`). A rejected answer comes back with `fix_these`. After 3 failed attempts the task becomes `needs_review` and the run continues. Never switch to a larger model automatically. Rerun with `init NEW --reuse OLD` to keep the answers whose input has not changed.

`WORK/final/` holds `markush.json`, `layout.json`, the CXSMILES, the molfile, the CDXML, the PNG and `report.json`. Report `needs_review`, `undefined` and the fidelity score with the result.

### Rules for the answering model

- Type labels exactly. Do not expand abbreviations or guess hidden text.
- Cite only mark ids that appear in the image (`T#`, `v#`). Never give coordinates or atom indices.
- In review, a bond drawn as a curve along a ring circle is still a bond. Check short dashes between labels.
- Leave `values` empty when the claim only names a class (for example "C1-6 alkyl"), and keep the wording in `text`.

## Layout fidelity

The drawing follows the source: bond length, font size and line width come from the image, ring circles keep their centre and radius, and labels keep their side. ChemDraw places a one-bond label by its bond angle:

- Left display, bond within about 45 degrees of horizontal: ChemDraw centres the first character on the node. For `(R^C)_p` that character is the parenthesis.
- Right display, bond under about 25 degrees: ChemDraw centres the last character on the node.
- Steeper bonds, and labels with several bonds: ChemDraw keeps the stored text position.

The writer corrects for these rules. Without a layout the tool uses RDKit coordinates, which give a correct structure but look nothing like the source.

Common failures are in [lessons](lessons.md#markush).
