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

For perspective-bond disagreement and abbreviation hydrogen loss, see [stereo diagnosis](stereo-reconstruction.md). Workflows: [image reconstruction](image-visual-review.md), [figure manifest](publication-figures.md), [saved-file validation](figure-validation.md).
