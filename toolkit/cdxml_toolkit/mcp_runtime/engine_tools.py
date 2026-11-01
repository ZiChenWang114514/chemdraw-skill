"""Tools backed by the optional engines (cdxml_toolkit.engines). All answers are model predictions."""

from __future__ import annotations

from typing import Any, Optional

from ..engines import env as engine_env
from ..engines import document, nmr, ocsr, reactions
from ..engines.registry import ENGINES


def list_engines() -> dict[str, Any]:
    """List the optional OCSR, segmentation, reaction, retrosynthesis and NMR engines and which are installed.

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
    molvec, or `all` (every installed local engine, plus decimer-api only when confirm_upload is true).
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
    purchasable is reported as such without a search) and reactiont5-retro (local, single step). Routes list `reactions` (A.B>>P per step) that render_scheme and
    route_summary accept, `starting_materials` and whether all are in stock. Learned-template suggestions
    only: check selectivity, conditions and availability before relying on them.
    """
    return reactions.retrosynthesis(product, engine, steps, count, time_limit, timeout_seconds)


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
) -> dict[str, Any]:
    """Predict 1H and/or 13C chemical shifts (`nucleus` "1H", "13C" or "both") of one molecule in a solvent.

    Engine: magnet (local; MagNET, supports H, C, N, O, F, Cl, S; install with
    `cdx.py install-engines magnet`). Returns peaks grouped by symmetry (shift, proton count, atom indices)
    marked `predicted: true`. With `output_path` (a new file) it also writes a simulated `ppm,intensity`
    spectrum of singlets that scientific_workflow(operation="nmr") can read. Predictions are not measured data:
    never put them in an experimental characterization line.
    """
    return nmr.predict(smiles, nucleus, solvent, frequency_mhz, engine, output_path, timeout_seconds)


ENGINE_TOOLS = {
    "list_engines": list_engines,
    "recognize_structure": recognize_structure,
    "extract_structures_from_document": extract_structures_from_document,
    "predict_products": predict_products,
    "predict_retrosynthesis": predict_retrosynthesis,
    "predict_nmr": predict_nmr,
}

__all__ = ["ENGINE_TOOLS", "ENGINES"]
