# Prediction Engines

Optional engines for reading structure images with more than one model, finding the structures in a PDF, and predicting products, precursors and NMR shifts. Everything here is a **model prediction**: results carry `provenance: "model_prediction"`, are never merged or picked silently, and must be checked before they reach a figure or a report. Signatures: [mcp-signatures.md](mcp-signatures.md).

```bash
cdx.py engines                              # which engines are installed
cdx.py install-engines molscribe molvec     # or --task ocsr; --dry-run shows size and Python needs first
cdx.py ocsr crop.png --engines molscribe,molnextr,molvec
cdx.py predict retro "CC(=O)Oc1ccccc1C(=O)O" --json '{"steps": "multi"}'
```

Each engine installs into its own folder under `~/.local/share/chemdraw-skill/engines` (`%LOCALAPPDATA%\chemdraw-skill\engines` on Windows; `CHEMDRAW_ENGINE_HOME` moves it), with its own Python, so PyTorch 1.x, TensorFlow 2.14 and the numpy 1.x/2.x stacks never meet. The runtime itself never imports an engine. Weights are downloaded at install time, checked against a pinned sha256 and recorded in a receipt; nothing is stored in the repository. Installation needs a network; running an engine does not (`HF_HUB_OFFLINE` is set for every run) and never uploads anything.

## Engines

| Engine | Task | Where it runs | Licence of code / weights | Size |
| --- | --- | --- | --- | --- |
| `decimer-api` | OCSR | remote (default) | MIT; service by the Steinbeck Lab | none |
| `decimer-local` | OCSR | runtime (extra `decimer`) | MIT | existing |
| `molscribe` | OCSR | own env, Python 3.10 | MIT / MIT | 0.8 GB + 1.1 GB |
| `molnextr` | OCSR | own env, Python 3.10 | Apache-2.0 / Apache-2.0 | 1.5 GB + 1.1 GB |
| `molvec` | OCSR | Java jar | Apache-2.0 | 1.3 MB |
| `decimer-segmentation` | find structures on a page | own env, Python 3.10 or 3.11 | MIT | TensorFlow 2.14 env |
| `aizynthfinder` | retrosynthesis, single and multi-step | own env, Python 3.12 | MIT | 1.0 GB + 0.8 GB data |
| `reactiont5-forward` | products | own env, Python 3.12 | MIT / MIT | 0.8 GB + weights |
| `reactiont5-retro` | retrosynthesis, single step | own env, Python 3.12 | MIT / MIT | same environment |
| `magnet` | 1H and 13C shifts | own env, Python 3.12 | MIT / MIT | PyTorch env |

Licences are those stated by each project; the weights of an engine are covered by their own terms, shown in `cdx.py install-engines --dry-run`. The full notices are in `toolkit/NOTICE.md`.

## Reading a structure image

`recognize_structure(image_path, engines=...)` runs the named engines and compares them. `engines` is a name, a comma-separated list, or `all` (every installed local engine; the remote `decimer-api` joins only with `confirm_upload`). The default stays `decimer-api`, with the upload rule in [SKILL.md](../SKILL.md).

The `comparison` block groups the engines by the structure they read (full InChIKey):

- `agreement`: `all` (one structure), `split` (different structures) or `single` (fewer than two engines produced one).
- `agreed_smiles` is set only when two or more engines gave the same structure. It is a **candidate**, not a result: look at the image.
- `selected` is always `null`; `needs_review` is true unless the engines agree and none failed.
- A difference only in stereochemistry is named in `notes`.

When engines disagree, show the user the groups, look at the image, and decide per atom or bond; do not take the majority. Use [image visual review](image-visual-review.md) for the rest of the reconstruction.

Real-paper accuracy is low for every open model. A 2026 benchmark of 5,029 structures from recent papers reports about 41% exact match for the best graph models (a self-reported figure on a third-party listing); clean computer-drawn images are much easier. Hand-drawn structures need `hand_drawn` with a DECIMER engine.

Measured here with `scripts/ocsr_benchmark.py` on 10 clean RDKit drawings (full InChIKey match, Apple-silicon CPU): MolScribe 10/10 at about 7 s per image, MolNexTR 10/10 at about 11 s, MolVec 10/10 at about 2 s. This is an upper bound for clean computer drawings, not an accuracy figure for papers.

## Structures in a PDF

`extract_structures_from_document(path, out_dir, pages=[...], engines=...)` renders the pages (up to 50 per call), finds the structures, reads each one, and writes `structures.json` and `contact-sheet.png` into a new folder. The sheet puts each crop beside a drawing of what each group of engines read, so mismatches are visible at a glance. `needs_review` lists the segments where engines disagree or only one engine ran. The segmenter is DECIMER Segmentation when installed, otherwise the OpenCV segmenter in the toolkit (less reliable at merged or split structures; a warning says so). Segmentation can miss a structure entirely: check the sheet against the page.

## Predictions

| Tool | Engines | What comes back |
| --- | --- | --- |
| `predict_products(reactants, reagents)` | `reactiont5-forward` | ranked candidate products with beam scores, and `reactions` (`A.B>>P`) |
| `predict_retrosynthesis(product, steps)` | `aizynthfinder`; `reactiont5-retro` (single step) | precursor options, or routes with `reactions`, `starting_materials` and `all_in_stock` |
| `predict_nmr(smiles, nucleus, solvent)` | `magnet` | peaks grouped by symmetry, marked `predicted: true`; with `output_path` a simulated `ppm,intensity` CSV |

Limits to state when reporting:

- Products and precursors are learned suggestions. The true product can be missing from the list; check atom balance with `check_reaction_balance`, and selectivity and conditions by chemistry.
- `reactiont5-retro` mixes reagents and solvents into its reactant sets and can miss the obvious precursor; prefer `aizynthfinder`.
- AiZynthFinder's building-block check uses the ZINC stock that ships with its public data, not the user's catalogue.
- MagNET supports H, C, N, O, F, Cl and S. The toolkit gives it an RDKit/MMFF conformer, but the model was trained on AIMNet2 geometries, so errors can exceed the published ones. Exchangeable OH/NH shifts are rough. Simulated spectra draw singlets only.
- Never put predicted values into an experimental characterization line or an SI table; label them as predicted. `scientific_workflow(operation="nmr")` accepts the simulated CSV for plotting.

Route steps feed `render_scheme`, `route_summary` and `draw_figure` as ordinary reaction SMILES; title such a figure as predicted.

## Not included

Checked and left out, with the reason:

- **Reacon** (reaction conditions): the paper is published, but no code or weights could be found.
- **Other condition predictors** found with weights depend on commercial reaction-classification software or on data that is not public, so `predict_conditions` is not provided.
- **IBM RXN**: needs an account key and its API contract could not be verified without one.
- **nmrdb.org**: a browser page without a programmatic interface.
- **Molecular Transformer**: no licence is stated in its repository.
- **RetroDFM-R**: an 8B language model trained on H200 GPUs; not practical on a laptop CPU.
- **OSRA, Imago**: GPL; would only ever be called as external programs, not bundled.

## Troubleshooting

- `cdx.py engines` lists what is installed; `cdx.py doctor` shows one `engine_*` line per local engine.
- A failed or half-finished install leaves no receipt and the engine does not count as installed. Run `install-engines` again; finished downloads are cached.
- Package index or model hosts can drop connections during a large download (`tls handshake eof`); run the same command again.
- On macOS a worker script must guard its entry point with `if __name__ == "__main__":`, because the engines start worker processes that import it again.
