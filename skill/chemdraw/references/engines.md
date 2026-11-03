# Prediction Engines

Optional engines for reading structure images with more than one model, finding the structures in a PDF, and predicting products, precursors, reaction conditions and NMR shifts. Everything here is a **model prediction**: results carry `provenance: "model_prediction"`, are never merged or picked silently, and must be checked before they reach a figure or a report. Signatures: [mcp-signatures.md](mcp-signatures.md).

```bash
cdx.py engines                              # installed or not, what each is for, disk used
cdx.py engines --recommend ocsr             # what to install for a need, with sizes; downloads nothing
cdx.py install-engines --bundle ocsr-standard   # or engine names, or --task ocsr; --dry-run shows sizes first
cdx.py remove-engines molnextr              # dry run; add --yes to delete
cdx.py ocsr crop.png --engines molscribe,molnextr,molvec
cdx.py predict retro "CC(=O)Oc1ccccc1C(=O)O" --json '{"steps": "multi"}'
cdx.py predict conditions "CCO.CC(=O)O" --products "CCOC(C)=O"
```

Each engine installs into its own folder under `~/.local/share/chemdraw-skill/engines` (`%LOCALAPPDATA%\chemdraw-skill\engines` on Windows; `CHEMDRAW_ENGINE_HOME` moves it), with its own Python, so PyTorch 1.x, TensorFlow 2.14 and the numpy 1.x/2.x stacks never meet. The runtime itself never imports an engine. Weights are downloaded at install time, checked against a pinned sha256 and recorded in a receipt; nothing is stored in the repository. Installation needs a network; running an engine does not (`HF_HUB_OFFLINE` is set for every run) and never uploads anything.

## Engines

| Engine | Task | Where it runs | Licence of code / weights | Size |
| --- | --- | --- | --- | --- |
| `decimer-api` | OCSR | remote (default) | MIT; service by the Steinbeck Lab | none |
| `decimer-local` | OCSR | runtime (extra `decimer`) | MIT | existing |
| `molscribe` | OCSR | own env, Python 3.10 | MIT / MIT | 0.8 GB + 1.1 GB |
| `molnextr` | OCSR | own env, Python 3.10 | Apache-2.0 / Apache-2.0 | 1.5 GB + 1.1 GB |
| `molparser` | OCSR (also Markush) | own env, Python 3.10 to 3.12 | Apache-2.0 / **CC BY-NC-SA 4.0, non-commercial only** | 1.5 GB + 20 MB |
| `molvec` | OCSR | Java jar | Apache-2.0 | 1.3 MB |
| `decimer-segmentation` | find structures on a page | own env, Python 3.10 or 3.11 | MIT | TensorFlow 2.14 env |
| `aizynthfinder` | retrosynthesis, single and multi-step | own env, Python 3.12 | MIT | 1.0 GB + 0.8 GB data |
| `reactiont5-forward` | products | own env, Python 3.12 | MIT / MIT | 0.8 GB + weights |
| `reactiont5-retro` | retrosynthesis, single step | own env, Python 3.12 | MIT / MIT | same environment |
| `magnet` | 1H and 13C shifts | own env, Python 3.12 | MIT / MIT | PyTorch env |
| `nmrnet-pp` | 1H and 13C shifts (a second model) | own env, Python 3.11 | MIT / CC BY 4.0 | 0.8 GB + 1.1 GB |
| `retrochimera` | retrosynthesis, single step and routes (Microsoft Research, with Syntheseus) | own env, Python 3.10 | MIT / MIT | 0.7 GB + 4.7 GB + 0.5 GB stock (about 6 GB installed) |
| `reacon` | reaction conditions | own env, Python 3.10 | **no licence stated by the authors** | 0.8 GB + 0.25 GB |

MolParser's weights may not be used commercially; check this before using it in paid or company work. RetroChimera's authors release it for research and experiments only. Reacon's authors state no licence at all, so it is never bundled: it is downloaded from their repository at a pinned commit, only when the user asks for it. Licences are those stated by each project; the weights of an engine are covered by their own terms, shown in `cdx.py install-engines --dry-run`. The full notices are in `toolkit/NOTICE.md`.

## When to offer an engine, and how to install it

Nothing here is installed or downloaded until the user agrees. The default path (remote DECIMER, the upload rule in [SKILL.md](../SKILL.md)) needs no engine at all.

**Offer an engine when** the request needs something the default cannot do and the matching engine is missing:

| The user wants | Offer | Download |
| --- | --- | --- |
| a second opinion on a structure image, or DECIMER's read failed the visual check | `ocsr-standard` (MolScribe + MolVec); `ocsr-lite` (MolVec alone, 2 MB, needs Java) when disk is tight | about 2 GB |
| hard drawings, Markush structures, the widest coverage | `ocsr-full` | about 5.5 GB |
| every structure from a PDF | `pdf` (segmenter + two OCSR engines) | about 4 GB |
| candidate products | `products` | about 1.6 GB |
| precursors or routes | `retro` | about 1.8 GB |
| predicted 1H/13C shifts | `nmr` | about 1.3 GB |
| a second NMR model to compare, or Br, I, Si, P, B in the molecule | `nmr-pp` | about 1.9 GB |
| the strongest single-step precursors, or routes searched with them (research use) | `retro-chimera` | about 6 GB (4.2 GB download; about 20 minutes of set-up after it) |
| catalyst, solvent and reagent candidates for a drawn reaction | `conditions` (code without a stated licence) | about 1.1 GB, 2 GB download |

Sizes are measured folder sizes of finished installs. A tool that needs a missing engine answers `ok: false` with an `install_hint` (engine, use, size, licence, command): relay it instead of searching the documentation, and install only after the user says yes.

**How to offer:** run `cdx.py engines --recommend NEED`, then say in a sentence or two what it is for, the download size, the licence in one line (MolParser's weights are non-commercial) and that it needs a network to install but not to run. After a yes, run `cdx.py install-engines --bundle NAME` and check `cdx.py engines`.

**Do not offer** when the task is already solved by the default path, when the user asked for offline or no-download work (`CHEMDRAW_OFFLINE=1` also makes installation refuse), in tasks unrelated to these needs, or again after the user declined in this conversation.

## Bundles

| Bundle | Engines | For |
| --- | --- | --- |
| `ocsr-lite` | `molvec` | a tiny rule-based second opinion |
| `ocsr-standard` | `molscribe`, `molvec` | an ordinary comparison |
| `ocsr-full` | `molscribe`, `molnextr`, `molparser`, `molvec` | hard drawings and Markush structures |
| `pdf` | `decimer-segmentation`, `molscribe`, `molvec` | structures from PDF pages |
| `products` | `reactiont5-forward` | candidate products |
| `retro` | `aizynthfinder` | single and multi-step retrosynthesis |
| `nmr` | `magnet` | predicted shifts |
| `nmr-pp` | `nmrnet-pp` | a second NMR model to compare with MagNET |
| `retro-chimera` | `retrochimera` | RetroChimera suggestions and Syntheseus route search (research use) |
| `conditions` | `reacon` | candidate reaction conditions (unlicensed code) |

`SynPlanner`, `ReactionT5` retrosynthesis and the individual OCSR engines are installed by name.

## Removing an engine

`cdx.py remove-engines NAME...` shows what it would delete and how much space that frees; `--yes` deletes. It removes only that engine's own folder under the engines home, and refuses a folder that is a symbolic link, outside the home, or not an installation made by `install-engines`. Downloaded package caches outside the folder are not touched. Reinstalling later downloads again.

## Reading a structure image

`recognize_structure(image_path, engines=...)` runs the named engines and compares them. `engines` is a name, a comma-separated list, or `all` (every installed local engine; the remote `decimer-api` joins only with `confirm_upload`). The default stays `decimer-api`, with the upload rule in [SKILL.md](../SKILL.md).

The `comparison` block groups the engines by the structure they read (full InChIKey):

- `agreement`: `all` (one structure), `split` (different structures) or `single` (fewer than two engines produced one).
- `agreed_smiles` is set only when two or more engines gave the same structure. It is a **candidate**, not a result: look at the image.
- `selected` is always `null`; `needs_review` is true unless the engines agree and none failed.
- A difference only in stereochemistry is named in `notes`.

When engines disagree, show the user the groups, look at the image, and decide per atom or bond; do not take the majority. Use [image visual review](image-visual-review.md) for the rest of the reconstruction.

Real-paper accuracy is low for every open model. A 2026 benchmark of 5,029 structures from recent papers reports about 41% exact match for the best graph models (a self-reported figure on a third-party listing); clean computer-drawn images are much easier. Hand-drawn structures need `hand_drawn` with a DECIMER engine.

Measured here with `scripts/ocsr_benchmark.py` on 10 clean RDKit drawings (full InChIKey match, Apple-silicon CPU): MolScribe 10/10 at about 7 s per image, MolNexTR 10/10 at about 11 s, MolParser 10/10 at about 11 s, MolVec 10/10 at about 2 s. This is an upper bound for clean computer drawings, not an accuracy figure for papers.

## Structures in a PDF

`extract_structures_from_document(path, out_dir, pages=[...], engines=...)` renders the pages (up to 50 per call), finds the structures, reads each one, and writes `structures.json` and `contact-sheet.png` into a new folder. The sheet puts each crop beside a drawing of what each group of engines read, so mismatches are visible at a glance. `needs_review` lists the segments where engines disagree or only one engine ran. The segmenter is DECIMER Segmentation when installed, otherwise the OpenCV segmenter in the toolkit (less reliable at merged or split structures; a warning says so). Segmentation can miss a structure entirely: check the sheet against the page.

## Predictions

| Tool | Engines | What comes back |
| --- | --- | --- |
| `predict_products(reactants, reagents)` | `reactiont5-forward` | ranked candidate products with beam scores, and `reactions` (`A.B>>P`) |
| `predict_retrosynthesis(product, steps)` | `aizynthfinder`; `retrochimera` (single step and routes); `synplanner` (routes); `reactiont5-retro` (single step) | precursor options, or routes with `reactions`, `starting_materials` and `all_in_stock` |
| `predict_nmr(smiles, nucleus, solvent, engine)` | `magnet`, `nmrnet-pp`, or both (`engine="magnet,nmrnet-pp"`) | peaks grouped by symmetry, marked `predicted: true`; with two engines a `comparison` of each peak (never averaged); with `output_path` a simulated `ppm,intensity` CSV |
| `predict_conditions(reactants, products)` | `reacon` | ranked catalyst, solvent and reagent sets; the atom-mapped reaction is returned for checking |

Limits to state when reporting:

- Products and precursors are learned suggestions. The true product can be missing from the list; check atom balance with `check_reaction_balance`, and selectivity and conditions by chemistry.
- `reactiont5-retro` mixes reagents and solvents into its reactant sets and can miss the obvious precursor; prefer `aizynthfinder`.
- AiZynthFinder's building-block check uses the ZINC stock that ships with its public data, not the user's catalogue.
- MagNET supports H, C, N, O, F, Cl and S. The toolkit gives it an RDKit/MMFF conformer, but the model was trained on AIMNet2 geometries, so errors can exceed the published ones. Exchangeable OH/NH shifts are rough. Simulated spectra draw singlets only.
- RetroChimera: the authors release it for research and experiments; an expert must check every suggestion, lower-ranked reactions are more likely to be hallucinated (read the first 5 to 10), and its data end in 2023. Routes use the MCULE/Molport building-block list shared with SynPlanner; "in stock" means listed there, not buyable today. A CPU run takes tens of seconds per target because the model loads on every call.
- NMRNet++ uses fold 0 of the authors' five cross-validation models, not their ensemble. Its models take no solvent, so the `solvent` argument does not change its answer, and the geometry is one RDKit/MMFF conformer. When it and MagNET differ by more than 0.3 ppm (1H) or 5 ppm (13C) the peak is flagged in `comparison`: at least one of them is wrong, and neither is the reference.
- Reacon learned from USPTO patents and returns catalyst, solvent and reagent sets, never temperature, time, amounts or yield. It maps the reaction first (so a wrong map changes the answer); when no template of the library matches, the options combine each classifier's top three and are less reliable (`template_level: "none"`).
- Never put predicted values into an experimental characterization line or an SI table; label them as predicted. `scientific_workflow(operation="nmr")` accepts the simulated CSV for plotting.

Route steps feed `render_scheme`, `route_summary` and `draw_figure` as ordinary reaction SMILES; title such a figure as predicted.

## Not included

Checked and left out, with the reason:

- **Other condition predictors** found with weights depend on commercial reaction-classification software or on data that is not public.
- **NMRNet** (the first, 2025 version): its weights are 38 GB; NMRNet++ is provided instead.
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
