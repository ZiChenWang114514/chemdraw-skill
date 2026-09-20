# Lessons and fixes

Read only the relevant entry. These are observed failure modes, not universal restrictions on all ChemDraw versions.

| Symptom | Correction | Verification boundary |
| --- | --- | --- |
| A C-N bridge appears as two segments and is mistaken for a dashed bond | Inspect the crossing crop. Keep a single bond and remove `Display="Dash"` when the gap is occlusion; set native crossing depth separately. Do not add an intersection atom. | Compare plain and isomeric readback. The observed Dash-to-solid correction preserved both; hashed wedge edits may not. |
| One crossing is correct but the matching crossing has no gap | Use explicit front/back bond references and consistent native ordering through the figure composer. Remove obsolete manually overlaid lines before reuse. | Inspect every native-rendered crossing. `Z` alone or a black overlay did not reliably fix the observed case. |
| DECIMER returns parseable but incorrect bridge structures | Check connectivity, carbonyls, N-ethyl, protecting-group abbreviations and formal charges before styling. Retain raw candidates and grounded correction records. | Formula and successful parsing do not prove image identity. |
| MCS is null while change lists are empty | Read the comparison status and reason. Incomplete or ambiguous mapping is not an empty successful difference. | Formula deltas supplement but do not replace mapped atom/bond changes. |
| Native saving adds bridgehead configurations | Compare the saved file, distinguish added/lost/changed assignments, and use direct ChemScript readback when necessary. | Reader agreement does not independently identify the source; do not remove stereo or reverse wedges to force a pass. |
| Native opening fails with no output or `NoneType ... SaveAs` | Check the XML declaration. The observed `utf8` alias failed while standard `UTF-8` worked. Native import normalizes the staged declaration, preserving the source. | This is one cause, not a diagnosis of every native failure. |
| A comparison calls an arbitrary candidate a native ChemDraw image | Supply a matching native render receipt or label the image simply as a candidate. | A matching record is provenance linkage, not cryptographic proof of the renderer or visual acceptance. |
| Repeated styling and full catalog reads increase rework | Resolve structure and depth before typography; read one workflow and the needed signatures, and reuse unchanged crops. | If requested, separate cached input from other token usage and record the cutoff. |

Use [reconstruction](image-visual-review.md), [native figure edits](publication-figures.md), and [saved-file validation](figure-validation.md) for executable workflows. New lessons should record an observed symptom, a tested correction and its limits; avoid machine-specific IDs and paths.

For perspective-bond disagreement, abbreviation hydrogen loss, and version-specific stereo handling, use [stereo reconstruction diagnosis](stereo-reconstruction.md). Test a difficult fragment before propagating templates; revalidate the exact final saved file.
