# Lessons and fixes

Observed failures and the fix that worked. Read only the relevant row.

## Everyday drawing

| Symptom | Fix |
| --- | --- |
| `No module named cdxml_toolkit.mcp_runtime`, or old toolkit behaviour | A script ran on the wrong interpreter. Start everything through `cdx.py` (it re-launches in the runtime); run other scripts as `cdx.py py SCRIPT`. |
| Re-rendered PNG did not change | The renderer refuses to overwrite. `cdx.py render` renders to a temporary name and replaces the old PNG only on success; other routes must use a new name. |
| Chinese text shows as boxes | The run needs a CJK font entry (SimSun, font 5). `acs_builder` puts CJK characters in SimSun and keeps Latin text in Arial automatically. |
| Abbreviation reads "C10H21" on the wrong side of the bond, or digits not subscripted | Use a `GenericNickname` node with a reversed label (H21C10) when the bond leaves to the right; put digits in subscript runs. `acs_builder` does both. |
| Ylide or resonance form "corrected" by RDKit | Write the nodes explicitly (`coords`/`label_text`, or raw fragment XML) instead of going through SMILES. |
| Condition text collides with a molecule | Leave about 25 pt between the molecule box and the text; long abbreviations widen the box. |
| Figures look inconsistent in a Word document | Insert every 300 dpi PNG at native size (px / 300 × 2.54 cm) so bond length and font size match across figures. |
| A figure "looked fine" in the log but was wrong | Open every rendered PNG and look at it before reporting. |

## Reconstruction

| Symptom | Fix |
| --- | --- |
| A C–N bridge shows as two segments and is taken for a dashed bond | It is occlusion: keep one single bond, remove `Display="Dash"`, set depth with `crossings`. Never add an intersection atom. |
| One crossing has a gap, the matching one does not | Give explicit front/back pairs to the figure composer; remove old hand-drawn cover lines. `Z` alone or a white overlay did not fix it. |
| DECIMER returns a parseable but wrong bridged structure | Check connectivity, carbonyls, N-ethyl, protecting-group abbreviations and charges before any styling. |
| MCS is null but the change lists are empty | Read the comparison status; an incomplete mapping is not "no change". |
| Native save adds bridgehead configurations | Compare the saved file with `cdx.py chemscript-info`; do not delete stereo or reverse wedges to make readers agree. |
| Native open fails with no output or `NoneType ... SaveAs` | The XML declaration said `utf8`; it must be `UTF-8`. |
| Time lost restyling | Settle structure and depth before typography; reuse unchanged crops. |

## Markush

| Symptom | Fix |
| --- | --- |
| Read-back of a Markush CDXML shows carbon for R groups, or loses the variable attachment | Readers turn generic labels into carbon and ignore `MultiAttachment`. Take chemistry from `markush.json` or the CXSMILES, not from the CDXML. |
| `m:` missing from CXSMILES | RDKit drops `m:` on write. Use `markush_compile`, which writes the CXSMILES itself. |
| NH label shows as "HN" or the H lands on the wrong side | Use an `N` atom with `h: 1`; the writer adds the H as its own caption on the side of the drawing. |
| Label flips to the other side of its bond | Set the label display (Left or Right) from the bond direction; the writer does this from the source layout. |
| `(R^C)_p` or `R^B` sits shifted from its bond end | ChemDraw centres the first character (Left) or the last (Right) on a near-horizontal single bond; `_label_node_x` compensates. Steep bonds keep the stored position. |
| A bond drawn hugging a ring circle is lost | The detector reads it as part of the circle. Answer the review task with `missing_bonds` for the two marks. |
| A short double bond between two labels reads as single | Check `bond_orders` in review; short pairs near text are easy to miss. |

For perspective-bond disagreement and abbreviation hydrogen loss, see [stereo diagnosis](stereo-reconstruction.md). Workflows: [image reconstruction](image-visual-review.md), [figure manifest](publication-figures.md), [saved-file validation](figure-validation.md).
