"""Tools backed by the optional engines (cdxml_toolkit.engines). All answers are model predictions."""

from __future__ import annotations

from typing import Any, Optional

from ..engines import env as engine_env
from ..engines import document, nmr, ocsr, reactions
from ..engines.registry import ENGINES


def list_engines() -> dict[str, Any]:
    """List the optional OCSR, segmentation, reaction, retrosynthesis, condition and NMR engines and which are installed.

    Install with `cdx.py install-engines NAME...` (each engine gets its own environment). Remote engines
    upload data and need the user's consent (see the Skill's upload rule).
    """
    status = engine_env.status()
    status['ok'] = True
    status['provenance'] = 'model_prediction'
    return status


def recognize_structure(
    image_path: str,
    engines: str = "decimer-api",
    hand_drawn: bool = False,
    output_path: Optional[str] = None,
    timeout_seconds: int = 600,
    confirm_upload: bool = False,
    approved_sha256: Optional[str] = None,
    approved_origin: Optional[str] = None,
) -> dict[str, Any]:
    """Read one structure image with one or several OCSR engines and compare the answers.

    `engines` is a name or comma-separated list from decimer-api, decimer-local, molscribe, molnextr,
    molparser, molvec, or `all` (every installed local engine, plus decimer-api only when confirm_upload is
    true). `output_path` is a new JSON file for the raw decimer-api response.
    The default stays the remote DECIMER service. The result lists each engine's structures and a
    `comparison`: engines that agree give `agreed_smiles` as a candidate, any disagreement leaves it null
    and sets `needs_review`. Nothing is picked silently; compare every structure with the image.
    Remote engines follow the same upload rule as extract_structures_via_decimer_api (preflight, consent,
    offline refusal); local engines never upload.
    """
    return ocsr.recognize(image_path, engines, hand_drawn=hand_drawn, output_path=output_path,
                          timeout_seconds=timeout_seconds, confirm_upload=confirm_upload,
                          approved_sha256=approved_sha256, approved_origin=approved_origin)


def predict_products(
    reactants: str,
    reagents: Optional[str] = None,
    engine: Optional[str] = None,
    count: int = 5,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Predict likely products of a reaction from reactant SMILES (dot-separated) with a learned model.

    Engine: reactiont5-forward (local; install with `cdx.py install-engines reactiont5-forward`). Returns up
    to `count` ranked candidates with beam scores and ready `reactions` (A.B>>P). These are predictions,
    not literature facts; the true product may not be among them.
    """
    return reactions.products(reactants, reagents, engine, count, timeout_seconds)


def predict_retrosynthesis(
    product: str,
    engine: Optional[str] = None,
    steps: str = "single",
    count: int = 5,
    time_limit: int = 60,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Suggest precursors (steps="single") or full routes to purchasable stock (steps="multi") for a target.

    Engines: aizynthfinder (local, single and multi-step, USPTO policies and ZINC stock), synplanner
    (local, multi-step only, USPTO rules and MCULE/Molport building blocks; a target that is itself
    purchasable is reported as such without a search), retrochimera (local, single and multi-step, multi-step
    searched with Syntheseus; for research use, read only its first 5 to 10 answers) and reactiont5-retro
    (local, single step). Routes list `reactions` (A.B>>P per step) that render_scheme and route_summary
    accept, `starting_materials` and whether all are in stock. Learned suggestions only: check selectivity,
    conditions and availability before relying on them.
    """
    return reactions.retrosynthesis(product, engine, steps, count, time_limit, timeout_seconds)


def predict_conditions(
    reactants: str,
    products: str,
    engine: Optional[str] = None,
    count: int = 5,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Rank catalyst, solvent and reagent combinations for a reaction (reactants and products as SMILES).

    Engine: reacon (local; install with `cdx.py install-engines reacon`; the authors' repository states no
    licence). The reaction is atom-mapped first (`mapped_reaction` is returned so the map can be checked).
    Options list a catalyst, up to two solvents and up to three reagents with a score, learned from patent
    reactions. They are candidates only: no temperature, time, amounts or yield, and a new reaction type may
    be answered poorly.
    """
    return reactions.conditions(reactants, products, engine, count, timeout_seconds)


def extract_structures_from_document(
    path: str,
    out_dir: str,
    pages: Optional[list[int]] = None,
    engines: str = "molscribe,molvec",
    segmenter: str = "auto",
    dpi: int = 200,
    confirm_upload: bool = False,
    hand_drawn: bool = False,
) -> dict[str, Any]:
    """Find every structure on a PDF (pages are 1-based, up to 50) or an image, read each with several engines.

    Pages are rendered, segmented (DECIMER Segmentation if installed, else the OpenCV segmenter), and each
    segment goes through recognize_structure with `engines` (local engines by default; decimer-api uploads
    each segment only with confirm_upload). Writes crops, `structures.json` and a `contact-sheet.png` that
    puts each crop beside the structures the engines read, into a new `out_dir`. Segments where the engines
    disagree are listed in `needs_review`. Segmentation can miss, merge or split structures: look at the sheet.
    """
    return document.extract(path, out_dir, pages, engines, segmenter, dpi, confirm_upload, hand_drawn)


def predict_nmr(
    smiles: str,
    nucleus: str = "1H",
    solvent: str = "chloroform",
    frequency_mhz: float = 400.0,
    engine: Optional[str] = None,
    output_path: Optional[str] = None,
    timeout_seconds: int = 900,
    experimental_1h: Optional[list[float]] = None,
    experimental_13c: Optional[list[float]] = None,
) -> dict[str, Any]:
    """Predict 1H and/or 13C chemical shifts (`nucleus` "1H", "13C" or "both") of one molecule in a solvent.

    Engines: magnet (local; MagNET, supports H, C, N, O, F, Cl, S) and nmrnet-pp (local; NMRNet++, which takes
    no solvent); install with `cdx.py install-engines NAME`. `engine="magnet,nmrnet-pp"` runs both and adds a
    peak-by-peak `comparison`, never an average; an engine that fails is listed in `failed_engines`. Returns
    peaks grouped by symmetry (shift, proton count, atom indices) marked `predicted: true`. With `output_path`
    (a new file) it also writes a simulated `ppm,intensity` spectrum of singlets that
    scientific_workflow(operation="nmr") can read. Predictions are not measured data: never put them in an
    experimental characterization line.

    With `experimental_1h` and/or `experimental_13c` (lists of measured ppm values) one engine's prediction is
    also matched to them peak by peak (Hungarian assignment): the nuclei you give peaks for are predicted
    whatever `nucleus` says, and `experimental_comparison` lists each predicted group with its closest
    measured peak, the signed and absolute error, the mean and largest error per nucleus and `outliers`
    (over 0.5 ppm for 1H, 5 ppm for 13C). It is a candidate assignment: confirm it with 2D NMR.
    """
    experimental = bool(experimental_1h or experimental_13c)
    if experimental:
        if engine and len([n for n in engine.split(',') if n.strip()]) > 1:
            raise ValueError('compare with experimental peaks using one engine at a time')
        nucleus = 'both' if (experimental_1h and experimental_13c) else ('13C' if experimental_13c else '1H')
    result = nmr.predict(smiles, nucleus, solvent, frequency_mhz, engine, output_path, timeout_seconds)
    if experimental and result.get('ok', True):
        result['experimental_comparison'] = nmr.compare_shifts(
            smiles, experimental_1h, experimental_13c, solvent=solvent, predicted_result=result)
    return result


ENGINE_TOOLS = {
    "list_engines": list_engines,
    "recognize_structure": recognize_structure,
    "extract_structures_from_document": extract_structures_from_document,
    "predict_products": predict_products,
    "predict_retrosynthesis": predict_retrosynthesis,
    "predict_conditions": predict_conditions,
    "predict_nmr": predict_nmr,
}

__all__ = ["ENGINE_TOOLS", "ENGINES"]
