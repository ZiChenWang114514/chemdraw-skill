# Prediction Engines

Optional engines for reading structure images with more than one model, finding the structures in a PDF, and predicting products, precursors, reaction conditions and NMR shifts. Everything here is a **model prediction**: results carry `provenance: "model_prediction"`, are never merged or picked silently, and must be checked before they reach a figure or a report. Signatures: [mcp-signatures.md](mcp-signatures.md).

```bash
cdx.py engines                              # installed or not, what each is for, disk used (as recorded at install)
cdx.py engines --sizes                      # measure the folders again; slow with many large engines
cdx.py engines --recommend ocsr             # what to install for a need, with sizes; downloads nothing
cdx.py install-engines --bundle ocsr-standard   # or engine names, or --task ocsr; --dry-run shows sizes first
cdx.py remove-engines molnextr              # dry run; add --yes to delete
cdx.py ocsr crop.png --engines molscribe,molnextr,molvec
cdx.py predict retro "CC(=O)Oc1ccccc1C(=O)O" --json '{"steps": "multi"}'
cdx.py predict products "CCO.CC(=O)O" --accel on   # keep the model resident for the next call
cdx.py stop-daemons                         # end the resident workers early
```

Each engine installs into its own folder under `~/.local/share/chemdraw-skill/engines` (`%LOCALAPPDATA%\chemdraw-skill\engines` on Windows; `CHEMDRAW_ENGINE_HOME` moves it to a larger disk and must stay set afterwards, or the engines are not found), with its own Python, so the PyTorch, TensorFlow and numpy stacks never meet. The runtime never imports an engine. Weights are downloaded at install time, checked against a pinned sha256 and recorded in a receipt; nothing is stored in the repository. Installing needs a network; running an engine does not (`HF_HUB_OFFLINE` is set) and never uploads anything.

## Engines

<!-- engines-table:start -->
| Engine | Task | Where it runs | Licence | Size |
| --- | --- | --- | --- | --- |
| `decimer-api` | OCSR | remote (default) | MIT (service by the Steinbeck Lab) | none |
| `decimer-local` | OCSR, the DECIMER model on this computer | own env, Python 3.10 or 3.11 | MIT | 1.7 GB environment (TensorFlow), 0.7 GB weights |
| `molscribe` | OCSR | own env, Python 3.10; NVIDIA GPU when present | MIT | 3.6 GB environment with the CUDA build of PyTorch (about 1.4 GB with the CPU build), 1.1 GB weights |
| `molnextr` | OCSR | own env, Python 3.10; NVIDIA GPU when present | Apache-2.0 | 3.6 GB environment with the CUDA build of PyTorch (about 1.5 GB with the CPU build), 1.1 GB weights |
| `molparser` | OCSR (also Markush) | own env, Python 3.10 to 3.12; NVIDIA GPU when present | **Apache-2.0 (code); CC BY-NC-SA 4.0 (weights), non-commercial only** | 3.4 GB environment with the CUDA build of PyTorch (about 1.5 GB with the CPU build), 20 MB weights |
| `molvec` | OCSR | Java jar | Apache-2.0 | 1.3 MB (needs Java) |
| `decimer-segmentation` | find structures on a page | own env, Python 3.10 or 3.11 | MIT | 1.8 GB environment, 0.3 GB model |
| `aizynthfinder` | retrosynthesis, single and multi-step | own env, Python 3.10 to 3.12 | MIT | 0.9 GB environment, 0.8 GB public data (USPTO policies, ZINC stock) |
| `synplanner` | retrosynthesis, multi-step routes | own env, Python 3.10 to 3.12; NVIDIA GPU when present | MIT | 3.8 GB environment with the CUDA build of PyTorch (about 1.4 GB with the CPU build), 0.9 GB building blocks and rules |
| `reactiont5-forward` | products | own env, Python 3.10 to 3.12; NVIDIA GPU when present | MIT | 3.1 GB environment with the CUDA build of PyTorch (about 1.3 GB with the CPU build), 0.8 GB weights |
| `reactiont5-retro` | retrosynthesis, single step | own env, Python 3.10 to 3.12; NVIDIA GPU when present | MIT | 3.1 GB environment with the CUDA build of PyTorch (about 1.3 GB with the CPU build), 0.8 GB weights |
| `magnet` | 1H and 13C shifts | own env, Python 3.12; NVIDIA GPU when present | MIT | 4.7 GB environment with the CUDA build of PyTorch (about 1.5 GB with the CPU build), 0.6 GB weights |
| `retrochimera` | retrosynthesis, single step and routes (Microsoft Research, with Syntheseus) | own env, Python 3.10; NVIDIA GPU when present | MIT | 3.4 GB environment with the CUDA build of PyTorch (about 1.6 GB with the CPU build), 4.7 GB model (Pistachio ensemble), 0.5 GB building blocks; the model is a 4.2 GB download and building the stock list takes 15 to 70 minutes, depending on the CPU, once; running it needs about 14 GB of free memory, because loading and template localization run on the CPU |
| `nmrnet-pp` | 1H and 13C shifts (a second model) | own env, Python 3.11; NVIDIA GPU when present | MIT (code); CC BY 4.0 (weights) | 1.6 GB environment, 1.1 GB checkpoints |
| `reacon` | reaction conditions | own env, Python 3.10; NVIDIA GPU when present | **not declared by the authors (no LICENSE file in their repository)** | 1.6 GB environment, 0.14 GB repository with trained models, 0.12 GB condition libraries (a 2 GB download from the authors, deleted after the libraries are taken out) |
<!-- engines-table:end -->

MolParser's weights may not be used commercially; check this before using it in paid or company work. RetroChimera's authors release it for research and experiments only. Reacon's authors state no licence at all, so it is never bundled: it is downloaded from their repository at a pinned commit, only when the user asks for it. Licences are those stated by each project; the weights of an engine are covered by their own terms, shown in `cdx.py install-engines --dry-run`. The full notices are in `toolkit/NOTICE.md`.

## When to offer an engine, and how to install it

Nothing here is installed or downloaded until the user agrees. The default path (remote DECIMER, the upload rule in [SKILL.md](../SKILL.md)) needs no engine at all.

**Offer an engine when** the request needs something the default cannot do and the matching engine is missing:

| The user wants | Offer | Download |
| --- | --- | --- |
| a second opinion on a structure image, or DECIMER's read failed the visual check | `ocsr-standard` (MolScribe + MolVec); `ocsr-lite` (MolVec alone, <!--size:ocsr-lite-->2 MB<!--/size-->, needs Java) when disk is tight | <!--size:ocsr-standard-->about 4.7 GB<!--/size--> |
| hard drawings, Markush structures, the widest coverage | `ocsr-full` | <!--size:ocsr-full-->about 12.9 GB<!--/size--> |
| every structure from a PDF | `pdf` (segmenter + two OCSR engines) | <!--size:pdf-->about 6.8 GB<!--/size--> |
| candidate products | `products` | <!--size:products-->about 3.9 GB<!--/size--> |
| precursors or routes | `retro` | <!--size:retro-->about 1.7 GB<!--/size--> |
| predicted 1H/13C shifts | `nmr` | <!--size:nmr-->about 5.4 GB<!--/size--> |
| a second NMR model to compare, or Br, I, Si, P, B in the molecule | `nmr-pp` | <!--size:nmr-pp-->about 2.8 GB<!--/size--> |
| the strongest single-step precursors, or routes searched with them (research use) | `retro-chimera` | <!--size:retro-chimera-->about 8.5 GB<!--/size--> (4.2 GB download, then 15 to 70 minutes, depending on the CPU, to build the stock list once); needs about 14 GB of free memory to run |
| catalyst, solvent and reagent candidates for a drawn reaction | `conditions` (code without a stated licence) | <!--size:conditions-->about 1.9 GB<!--/size--> (a 2 GB download that is partly deleted afterwards) |

Sizes are measured folder sizes of finished Windows installs, which carry the CUDA build of PyTorch (about 2 GB per PyTorch engine); a CPU install is smaller (see the table above). A tool that needs a missing engine answers `ok: false` with an `install_hint` (engine, use, size, licence, command): relay it instead of searching the documentation, and install only after the user says yes.

**How to offer:** run `cdx.py engines --recommend NEED` (`ocsr`, `pdf`, `products`, `retro`, `nmr`, `conditions`), then say in a sentence or two what it is for, the download size, the licence in one line and that it needs a network to install but not to run. After a yes, run `cdx.py install-engines --bundle NAME` and check `cdx.py engines`.

**Do not offer** when the task is already solved by the default path, when the user asked for offline or no-download work (`CHEMDRAW_OFFLINE=1` also makes installation refuse), in tasks unrelated to these needs, or again after the user declined in this conversation.

## Bundles

<!-- bundles-table:start -->
| Bundle | Engines | For |
| --- | --- | --- |
| `ocsr-lite` | `molvec` | a tiny rule-based second opinion (needs Java) |
| `ocsr-standard` | `molscribe`, `molvec` | two engines that err differently, enough for a comparison |
| `ocsr-full` | `molscribe`, `molnextr`, `molparser`, `molvec` | every local OCSR engine, for hard drawings and Markush structures |
| `decimer-local` | `decimer-local` | the DECIMER model on this computer, for images that may not be uploaded (TensorFlow) |
| `pdf` | `decimer-segmentation`, `molscribe`, `molvec` | cut the structures out of PDF pages and read them with two engines |
| `products` | `reactiont5-forward` | candidate products of a reaction |
| `retro` | `aizynthfinder` | single and multi-step retrosynthesis |
| `nmr` | `magnet` | predicted 1H and 13C shifts |
| `nmr-pp` | `nmrnet-pp` | a second NMR model to compare with MagNET |
| `retro-chimera` | `retrochimera` | RetroChimera single-step suggestions and Syntheseus route search (research use) |
| `conditions` | `reacon` | candidate reaction conditions (unlicensed code) |
<!-- bundles-table:end -->

`synplanner`, `reactiont5-retro`, `molscribe`, `molnextr`, `molparser` and `decimer-segmentation` are installed by name: `cdx.py install-engines NAME`.

## GPU, memory and disk

- **GPU.** Every PyTorch engine uses an NVIDIA GPU: when `nvidia-smi` finds one at install time the engine gets a CUDA build of PyTorch (older pins are replaced, because they have no kernels for RTX 50-series GPUs), and every response records `device` (`cuda`, `cpu` or `remote`, plus `device_fallback: true` after a retry). If the GPU fails while an engine runs (a CUDA error, no kernels, out of memory), the call is repeated once on the CPU. `CHEMDRAW_ENGINE_DEVICE=cpu` keeps every engine on the CPU, at install and at run time; Macs always use the CPU. `decimer-segmentation`, `decimer-local` (TensorFlow has no GPU support on native Windows) and the Java and ONNX engines stay on the CPU.
- **Memory.** RetroChimera is the largest engine: it needs about 14 GB of free memory on a GPU machine, because loading the model and localizing templates run on the CPU. It starts one rule process for every further 4 GB free, up to 4 (`CHEMDRAW_ENGINE_PROCESSES` sets the number and skips the check). Close other large programs before a RetroChimera run on a machine with less than 16 GB free.
- **Resident workers (`--accel auto|on|off`, `CHEMDRAW_ACCEL`).** By default (`auto`) each prediction is a clean one-shot process, except that a batch of inputs, a multi-step search or a both-nuclei NMR run keeps the model in a loopback-only, token-authenticated worker for the next call. `on` does this for every call, `off` never. The worker handles one request at a time: a caller that finds it busy runs its own one-shot instead. It ends after `CHEMDRAW_ACCEL_IDLE` idle seconds (default 180) and at most two stay resident. `cdx.py engines` lists them; `cdx.py stop-daemons` ends them. Only engines whose models load in a plain Python process can stay resident (not `retrochimera`, `synplanner`, `nmrnet-pp` or `reacon`).
- **Disk.** Package downloads are cached under `CHEMDRAW_ENGINE_HOME/.cache`, on the same disk as the engines, unless `UV_CACHE_DIR` or `PIP_CACHE_DIR` is set.

## Removing an engine

`cdx.py remove-engines NAME...` shows what it would delete and how much space that frees; `--yes` deletes only that engine's own folder under the engines home (it refuses a symbolic link, a folder outside the home, or one `install-engines` did not make). Reinstalling downloads again.

## Reading a structure image

`recognize_structure(image_path, engines=...)` runs the named engines and compares them. `engines` is a name, a comma-separated list, or `all` (every installed local engine; the remote `decimer-api` joins only with `confirm_upload`). The default stays `decimer-api`, with the upload rule in [SKILL.md](../SKILL.md).

`cdx.py ocsr` reads one image per call. For several crops, `extract_structures_from_document` does the whole page or PDF in one pass; from Python only, `cdxml_toolkit.engines.ocsr.recognize_batch(image_paths, engines, ...)` (run it with `cdx.py py`) calls each local engine once for all the crops and returns one report per image.

The `comparison` block groups the engines by the structure they read (full InChIKey):

- `agreement`: `all` (one structure), `split` (different structures) or `single` (fewer than two engines produced one).
- `agreed_smiles` is set only when two or more engines gave the same structure. It is a **candidate**, not a result: look at the image.
- `selected` is always `null`; `needs_review` is true unless the engines agree and none failed.
- A difference only in stereochemistry is named in `notes`.

When engines disagree, show the user the groups, look at the image, and decide per atom or bond; do not take the majority. Use [image visual review](image-visual-review.md) for the rest of the reconstruction.

Real-paper accuracy is low for every open model (a 2026 benchmark of 5,029 structures from recent papers reports about 41% exact match for the best graph models, a self-reported figure); clean computer-drawn images are much easier. Hand-drawn structures need `hand_drawn` with a DECIMER engine.

`decimer-local` is the DECIMER model on this computer, for images that may not be uploaded. It reads the same weights as the remote service, so it gives the same answer; it runs on the CPU in its own TensorFlow 2.15 environment and loads the model first (30 to 70 s on a laptop). A one-shot call pays that every time; a batch, or `--accel on`, keeps it resident for the next call.

## Structures in a PDF

`extract_structures_from_document(path, out_dir, pages=[...], engines=...)` renders the pages (up to 50 per call), finds the structures, reads each one, and writes `structures.json` and `contact-sheet.png` into a new folder; the sheet puts each crop beside what each group of engines read. `needs_review` lists the segments where engines disagree or only one engine ran. The segmenter is DECIMER Segmentation when installed, otherwise the less reliable OpenCV one in the toolkit (a warning says so). Segmentation can miss, merge or split structures: check the sheet against the page.

## Predictions

| Tool | Engines | What comes back |
| --- | --- | --- |
| `predict_products(reactants, reagents)` | `reactiont5-forward` | ranked candidate products with beam scores, and `reactions` (`A.B>>P`) |
| `predict_retrosynthesis(product, steps)` | `aizynthfinder`; `retrochimera` (single step and routes); `synplanner` (routes); `reactiont5-retro` (single step) | precursor options, or routes with `reactions`, `starting_materials` and `all_in_stock` |
| `predict_nmr(smiles, nucleus, solvent, engine)` | `magnet`, `nmrnet-pp`, or both (`engine="magnet,nmrnet-pp"`) | peaks grouped by symmetry (`predicted: true`) with `j_couplings` and multiplet patterns, `device`; with two engines a `comparison` of each peak (never averaged); with `output_path` a simulated `ppm,intensity` CSV; with `experimental_1h` / `experimental_13c` an `experimental_comparison` |
| `predict_conditions(reactants, products)` | `reacon` | ranked catalyst, solvent and reagent sets; the atom-mapped reaction is returned for checking |

To check a measured spectrum against a prediction, give `predict_nmr` the measured peak lists (`experimental_1h=[...]`, `experimental_13c=[...]`, ppm; one engine). Each predicted group is matched to one measured peak by optimal assignment, and `experimental_comparison` returns `kind: "model_assisted_candidate_assignment"`, `matches_1h` and `matches_13c` (atoms, `predicted_shift`, `experimental_shift`, signed `error`, `abs_error`, `is_outlier`), `mae_1h`, `mae_13c`, `max_error_1h`, `max_error_13c`, `outliers` (over 0.5 ppm for 1H, 5 ppm for 13C) and `prediction_source`. It is a candidate assignment, not a measured one: confirm it with 2D NMR.

Limits to state when reporting:

- Products and precursors are learned suggestions. The true product can be missing from the list; check atom balance with `check_reaction_balance`, and selectivity and conditions by chemistry.
- `reactiont5-retro` mixes reagents and solvents into its reactant sets and can miss the obvious precursor; prefer `aizynthfinder`. AiZynthFinder's building-block check uses the ZINC stock in its public data, not the user's catalogue.
- MagNET supports H, C, N, O, F, Cl and S. Shifts are averaged over a Boltzmann-weighted conformer ensemble and 1H-1H `j_couplings` are estimated from the geometry, so peak tables and simulated spectra show multiplet splitting. Errors can exceed the published ones, and exchangeable OH/NH shifts remain approximate.
- RetroChimera: research use only; an expert must check every suggestion, lower-ranked reactions are more likely to be hallucinated (read the first 5 to 10), and its data end in 2023. "In stock" means listed in the MCULE/Molport building blocks it shares with SynPlanner, not buyable today.
- NMRNet++ uses one of the authors' five cross-validation models and takes no solvent, so `solvent` does not change its answer. When it and MagNET differ by more than 0.3 ppm (1H) or 5 ppm (13C) the peak is flagged in `comparison`: at least one is wrong, and neither is the reference.
- Reacon learned from USPTO patents and returns catalyst, solvent and reagent sets, never temperature, time, amounts or yield. It maps the reaction first, so a wrong map changes the answer; with no matching template the options are less reliable (`template_level: "none"`).
- Never put predicted values into an experimental characterization line or an SI table; label them as predicted. `scientific_workflow(operation="nmr")` accepts the simulated CSV for plotting.

Route steps feed `render_scheme`, `route_summary` and `draw_figure` as ordinary reaction SMILES; title such a figure as predicted.

## Not included

Left out, with the reason: other condition predictors (they need commercial reaction-classification software or non-public data); NMRNet, the first version (38 GB of weights; NMRNet++ is provided instead); IBM RXN (needs an account key); nmrdb.org (no programmatic interface); Molecular Transformer (no licence stated); RetroDFM-R (an 8B model that needs H200 GPUs); OSRA and Imago (GPL; they could only be called as external programs).

## Troubleshooting

- `cdx.py engines` lists what is installed; `cdx.py doctor` shows one `engine_*` line per local engine.
- A failed or half-finished install leaves no receipt and the engine does not count as installed: run `install-engines` again (finished downloads are cached; a dropped connection such as `tls handshake eof` is fixed the same way, after checking the network or proxy). `another install of NAME is running` means one install or removal runs at a time per engine: wait for it.
- On macOS a worker script must guard its entry point with `if __name__ == "__main__":`, because the engines start worker processes that import it again.
