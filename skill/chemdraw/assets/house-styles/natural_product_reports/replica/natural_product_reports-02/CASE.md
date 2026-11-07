# Natural Product Reports: maleidride core structures (Fig. 1a, structure panel)

Source: Williams et al., *Nat. Prod. Rep.* 2022, "Maleidride biosynthesis: construction of dimeric anhydrides", DOI [10.1039/d2np00041e](https://doi.org/10.1039/d2np00041e). Licence CC BY 3.0 (from the card). The reference crop is `evidence/natural_product_reports-02.png`; the full-size figure from the paper's open-access copy was checked for the structures.

Drawing style: the `natural_product_reports` house style (`cdx.py styles natural_product_reports`), base preset `rsc`.

Figure type: `structure_panel`.

## What is reproduced

Three of the five structures in the panel, as a `kind: "scope"` panel with one group heading per family:

| family (paper heading, as relabelled in brief.json) | SMILES in brief.json | ring sizes (RDKit) |
| --- | --- | --- |
| head-to-head maleidride (right-hand drawing) | `C1(CC)C(CC)C2=C(C(=O)OC2=O)CCC3=C1C(=O)OC3=O` | 5, 5, 8 |
| head-to-tail nonadride | `O=C1OC(=O)C2=C1CC(CC)CC3=C(C(=O)OC3=O)C(CC)C2` | 5, 5, 9 |
| octadride | `O=C1OC(=O)C2=C1CC(CC)C3=C(C(=O)OC3=O)CC2CC` | 5, 5, 8 |

Each core is a cyclic bis-anhydride: two maleic-anhydride C=C units fused to the carbocycle, with alkyl substituents on sp3 ring carbons. The SMILES were checked with RDKit (valid, two anhydride rings per core). Their connectivity comes from my reading of the drawings, not from source structure data.

Not reproduced: the left-hand head-to-head maleidride (its quaternary methyl carbon and the fusion to the left anhydride could not be read with confidence) and the heptadride (head-to-side) core (lactone, hemiketal OH and fused seven-membered ring not read with confidence).

Build: `python skill/chemdraw/scripts/cdx.py draw brief.json NEW.cdxml`. The replay script `replay.py` redraws the panel offline into a new folder.

## Render status

Not rendered. `--render` (desktop ChemDraw) timed out at the 300 s tool limit on two tries while other drawing jobs held the native ChemDraw lock. Non-rendered draws of the same three structures passed their checks: readback `matched` for 3 structures, data binding and RDKit consistency passed, lint clean, all three cores on one page at the default page size. That check was run with a scope title added ("Maleidride core structures"). The title is not in the paper and must be removed, but `brief.json` still contains `"title": "Maleidride core structures"`, so the brief as stored is not the title-free brief. The final title-free draw did not complete (worker stopped after about 290 s under lock contention), so the title-free brief itself has not been drawn. No `rendered.png` is saved, so proportions, line weight and label face are not checked against the paper.

## Convention check

Rows are the conventions the card claims for `structure_panel` (figure-type section) and the top-level conventions visible in crop 02. "n/a" marks a convention that crop 02 does not show.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `highlight_fill` #C9C9FD: lavender panel joins the related families | lavender area behind the maleidride and nonadride boxes; octadride and heptadride boxes on white | none; scope panels take only the base preset (`style.skipped`: "house conventions apply to schemes only") | no |
| families in thin black rounded rectangles | yes, one box per family | group headings are text only, no frames | no |
| bold family heading with italic sub-class line | "maleidrides" and "nonadrides" bold, sub-class lines italic; "octadrides" and "heptadrides" regular weight | group headings in one plain style; no heading style option | no |
| building block drawn with bold bonds over the plain ring | monomer-derived bonds bold (anhydride C=C and the adjacent ring bonds) | plain bonds only | no |
| `intermediate_label_style` bold_number | no numbered intermediates in crop 02 | n/a | n/a |
| `compound_label_face` bold | no compound labels in crop 02 | n/a | n/a |
| aromatic rings kekule | anhydride C=C shown as Kekule double bonds | Kekule SMILES input only; no drawn output in the case folder and no render | no (not verified) |
| thin plain lines (line width 0.05 of bond length) | thin plain lines | `rsc` base preset applied; line width not measured | no (not checked) |
| Arial-like sans-serif labels | yes | `rsc` preset label font not checked | no (not checked) |

Matched 0 of 7 claimed conventions (rows that apply to crop 02). The kekule row rests on the input SMILES, not on a drawn output; the thin-line and label-font rows were never checked because there is no render.

## Differences from the paper

- No panel: the lavender fill, the black rounded boxes and the bold/italic family headings are not drawn.
- Bold monomer-derived bonds are drawn plain.
- Two of the five structures are missing (left-hand head-to-head and heptadride).
- The alkyl chains carry a repeat bracket with *n* in the paper. The replica uses ethyl groups with no bracket.
- The left-hand head-to-head core is not drawn at all, so its quaternary methyl is also missing.
- The panel label "a)" is not drawn; the replica draws only the structures and their group headings.

## Tool gaps

- `draw_figure` has no panel kind. Only `scheme`, `scope` and `mechanism` exist; a family panel with boxes and fills has to be made by hand, with `cdx.py build` or a figure manifest.
- `scope` panels take only the base preset. The house-style conventions (`style.skipped`) are not applied to them, so no bold bonds, label face or group style can come from the card.
- Group headings take no style options (weight, italic sub-class line, placement above a frame).
- No frame or fill: no rounded rectangle around a group and no pastel fill behind a set of structures. (`highlight_fill` applies only to the largest ring of a scheme product.)
- No bold or coloured single-bond option for species in a scope or panel brief.
- No polymer repeat bracket (`n`) on a species chain.
- Native render unavailable in this run: `--render` timed out twice on the ChemDraw lock; there was no visual check.
- Scope page size: at the default page size the three cores fit one page; at 120 x 120 mm each structure went to its own page.

## Structure issues

- Left-hand head-to-head maleidride not transcribed (quaternary methyl carbon and its fusion to the left anhydride).
- Heptadride (head-to-side) not transcribed.
- The three transcribed cores were read from the figure; their connectivity (which ring positions carry the anhydride pairs and the alkyl groups) is my reading and has not been checked against source data.
- Alkyl chains are simplified to ethyl groups.

## Audit

Checked against `reference.png`. No `rendered.png`, `figure.cdxml` or `validation.json` is in this folder, so nothing drawn could be inspected.

- Corrected matched count: 0 of 7 (was 1 of 7). The kekule match rested on the input SMILES, not on a drawing; the thin-line and label-font rows were never checked.
- Not verified: the readback, data-binding, lint and one-page results. No output in this folder supports them, so they are the replicator's report only, as is the 120 x 120 mm page-split result.
- Corrected: the title is still in `brief.json`, contrary to the earlier text; the panel has five structures, not four cores; the left-hand head-to-head core is missing entirely, not only its methyl.
- Corrected: the group labels in `brief.json` (for example "Maleidrides (head-to-head)") are the replicator's wording. The paper uses bold "maleidrides" and "nonadrides" with italic sub-class lines, and plain "octadrides" and "heptadrides".
- Confirmed in code: `draw_figure` rejects any kind other than scheme, scope and mechanism (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`), and scope panels report that house conventions apply to schemes only (`figure_scope.py`). The listed gaps are accurate.
- Missed gaps: `draw_figure` has no panel-letter key (the bold "a)"); scope species accept only id, smiles, name, label, group and values, so there is no placement, per-structure label face, colour or bold-bond option; `group` is a single string per species, so the nested grouping in the reference (two maleidride structures inside one heading, a nonadride box overlapping the lavender panel) cannot be expressed.
- Connectivity and ring sizes of the three cores were not independently confirmed against the reference; the topology looks plausible but is unchecked.
