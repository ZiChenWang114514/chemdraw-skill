#!/usr/bin/env python3
"""
scheme_reader_verify.py — Visual verification report for scheme_reader output.

Generates an HTML report that shows each CDXML scheme as a rendered image
alongside scheme_reader's parsed narrative, species list, and step graph.
This lets a chemist visually confirm that the parser understood the scheme
correctly.

Two modes:
  1. Directory mode:  point at a folder of .cdxml files
  2. Document mode:   point at a .pptx or .docx; objects are extracted first

CLI:
    python -m cdxml_toolkit.scheme_reader_verify dir_of_cdxml/ -o report.html
    python -m cdxml_toolkit.scheme_reader_verify slides.pptx  -o report.html
    python -m cdxml_toolkit.scheme_reader_verify slides.pptx thesis.docx -o report.html
    python -m cdxml_toolkit.scheme_reader_verify dir/ --render   # also renders images via ChemDraw
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

from cdxml_toolkit.perception.scheme_reader import read_scheme, SchemeDescription
from cdxml_toolkit.perception.scheme_refine import (
    apply_corrections, generate_llm_narrative, _build_reaction_smiles,
    enrich_aligned_names,
)

# ---------------------------------------------------------------------------
# ML enrichment (optional — requires chem-pipeline's experiments modules)
# ---------------------------------------------------------------------------
_ML_AVAILABLE = False

def _try_load_ml():
    """Try to import RXNMapper + RXN Insight from chem-pipeline experiments."""
    global _ML_AVAILABLE
    if _ML_AVAILABLE:
        return True
    # chem-pipeline experiments/ is not a proper package — add path
    _pipeline_root = os.path.normpath(
        os.path.join(os.path.expanduser("~"), "chem-pipeline"))
    if os.path.isdir(_pipeline_root) and _pipeline_root not in sys.path:
        sys.path.insert(0, _pipeline_root)
    try:
        from experiments.role_classification.rxn_role_classifier import (  # noqa: F401
            classify_roles_enriched,
        )
        _ML_AVAILABLE = True
        return True
    except ImportError:
        return False


def _enrich_step(rxn_smiles: str, timeout: int = 120) -> Optional[dict]:
    """Run RXNMapper + RXN Insight on a single reaction SMILES."""
    try:
        from experiments.role_classification.rxn_role_classifier import (
            classify_roles_enriched,
        )
        return classify_roles_enriched(rxn_smiles, timeout=timeout)
    except Exception:
        return None


def enrich_scheme(desc: SchemeDescription,
                  verbose: bool = False) -> dict:
    """Generate ML enrichment for all steps in a scheme.

    Returns dict keyed by step_index with RXNMapper/RXN Insight results.
    """
    enrichment = {}
    if not _try_load_ml():
        if verbose:
            print("  ML enrichment unavailable (chem-pipeline not found)",
                  file=sys.stderr)
        return enrichment

    for step in desc.steps:
        rxn_smi = _build_reaction_smiles(step, desc.species)
        if not rxn_smi:
            if verbose:
                print(f"  Step {step.step_index}: no SMILES for rxn SMILES",
                      file=sys.stderr)
            continue
        if verbose:
            print(f"  Step {step.step_index}: {rxn_smi[:80]}...",
                  file=sys.stderr)
        result = _enrich_step(rxn_smi)
        if result:
            enrichment[step.step_index] = result
        elif verbose:
            print(f"  Step {step.step_index}: ML enrichment failed",
                  file=sys.stderr)
    return enrichment


def batch_enrich_schemes(descs: list, verbose: bool = False) -> list:
    """Batch ML enrichment for multiple SchemeDescriptions.

    Uses RXNMapper batch API to send all reaction SMILES in a single
    subprocess call (one model load), then calls RXN Insight per-step
    for reaction classification.

    Args:
        descs: List of (index, SchemeDescription) tuples.

    Returns:
        List of (index, enrichment_dict) tuples.
    """
    if not _try_load_ml():
        if verbose:
            print("ML enrichment unavailable", file=sys.stderr)
        return [(i, {}) for i, _ in descs]

    from experiments.atom_mapping.rxn_atom_mapper import (
        map_reactions_batch, classify_roles_from_mapping,
    )

    # Phase 1: Collect all reaction SMILES (filter out R-group/invalid)
    def _valid_rxn_smiles(rxn_smi: str) -> bool:
        """Check that both sides of reaction contain valid SMILES."""
        try:
            from rdkit import Chem
        except ImportError:
            return True  # can't validate, let RXNMapper try
        parts = rxn_smi.split(">>")
        if len(parts) != 2:
            return False
        for side in parts:
            for frag in side.split("."):
                if not frag:
                    continue
                mol = Chem.MolFromSmiles(frag)
                if mol is None:
                    return False
        return True

    all_rxns = []      # (desc_idx, step_idx, rxn_smiles)
    n_skipped = 0
    for desc_idx, desc in descs:
        for step in desc.steps:
            rxn_smi = _build_reaction_smiles(step, desc.species)
            if rxn_smi:
                if _valid_rxn_smiles(rxn_smi):
                    all_rxns.append((desc_idx, step.step_index, rxn_smi))
                else:
                    n_skipped += 1

    if not all_rxns:
        return [(i, {}) for i, _ in descs]

    if verbose:
        msg = f"Batch mapping {len(all_rxns)} reactions via RXNMapper..."
        if n_skipped:
            msg += f" ({n_skipped} skipped: invalid/R-group SMILES)"
        print(msg, file=sys.stderr)

    # Phase 2: Batch atom mapping (single subprocess)
    rxn_smiles_list = [r[2] for r in all_rxns]
    batch_results = map_reactions_batch(rxn_smiles_list, timeout=600)

    if verbose:
        n_ok = sum(1 for r in batch_results if r is not None)
        print(f"  {n_ok}/{len(batch_results)} reactions mapped",
              file=sys.stderr)

    # Phase 3: Role classification from atom maps + RXN Insight enrichment
    enrichments = {i: {} for i, _ in descs}

    for (desc_idx, step_idx, rxn_smi), map_result in zip(all_rxns, batch_results):
        if map_result is None:
            continue

        # Classify roles from atom maps
        role_result = classify_roles_from_mapping(
            original_rxn=rxn_smi,
            mapped_rxn=map_result["mapped_rxn"],
            confidence=map_result["confidence"],
        )

        # Try RXN Insight for reaction class/name (still per-step subprocess)
        try:
            from experiments.role_classification.rxn_role_classifier import (
                _run_rxn_insight,
            )
            insight = _run_rxn_insight(rxn_smi, timeout=60)
            if insight:
                role_result["reaction_class"] = insight.get("reaction_class", "")
                role_result["reaction_name"] = insight.get("reaction_name", "")
                role_result["byproducts"] = insight.get("byproducts", [])
                role_result["functional_groups_reactants"] = insight.get(
                    "functional_groups_reactants", [])
            else:
                role_result["reaction_class"] = ""
                role_result["reaction_name"] = ""
                role_result["byproducts"] = []
        except ImportError:
            role_result["reaction_class"] = ""
            role_result["reaction_name"] = ""
            role_result["byproducts"] = []

        enrichments[desc_idx][step_idx] = role_result

        if verbose and (step_idx == 0 or desc_idx % 10 == 0):
            rc = role_result.get("reaction_class", "?")
            print(f"  [{desc_idx}] step {step_idx}: {rc}",
                  file=sys.stderr)

    return [(i, enrichments[i]) for i, _ in descs]


# ---------------------------------------------------------------------------
# SMILES -> structure image (RDKit SVG)
# ---------------------------------------------------------------------------

# Cache: smiles -> base64 data-URI SVG
_smiles_svg_cache: dict = {}


def _smiles_to_svg_b64(smiles: str, width: int = 200, height: int = 120) -> str:
    """Render a SMILES string to an inline SVG data-URI via RDKit.

    Returns a data:image/svg+xml;base64,... string, or "" on failure.
    Results are cached so duplicate SMILES are rendered only once.
    """
    if not smiles:
        return ""
    if smiles in _smiles_svg_cache:
        return _smiles_svg_cache[smiles]

    try:
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D

        mol = Chem.MolFromSmiles(smiles, sanitize=False)
        if mol is None:
            _smiles_svg_cache[smiles] = ""
            return ""

        # Partial sanitisation — tolerate dummy atoms / R-groups
        try:
            Chem.SanitizeMol(mol, Chem.SanitizeFlags.SANITIZE_ALL
                             ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES)
        except Exception:
            pass

        try:
            Chem.rdDepictor.Compute2DCoords(mol)
        except Exception:
            pass

        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        opts = drawer.drawOptions()
        opts.clearBackground = True
        opts.bondLineWidth = 1.2
        opts.padding = 0.15
        # Make dummy atoms (R-groups) visible
        opts.dummyIsotopeLabels = False
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg_text = drawer.GetDrawingText()

        b64 = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
        uri = f"data:image/svg+xml;base64,{b64}"
        _smiles_svg_cache[smiles] = uri
        return uri

    except Exception:
        _smiles_svg_cache[smiles] = ""
        return ""


# ---------------------------------------------------------------------------
# Image rendering (optional, requires ChemDraw COM)
# ---------------------------------------------------------------------------

def _render_cdxml_to_png(cdxml_path: str, output_path: str) -> bool:
    """Render a CDXML file to PNG via cdxml_to_image. Returns True on success."""
    try:
        from cdxml_toolkit.chemdraw.cdxml_to_image import cdxml_to_png
        cdxml_to_png(cdxml_path, output_path)
        return True
    except Exception:
        # Fall back to subprocess call
        try:
            import subprocess
            python = sys.executable
            result = subprocess.run(
                [python, "-m", "cdxml_toolkit.cdxml_to_image",
                 cdxml_path, "-o", output_path],
                capture_output=True, timeout=30,
            )
            return result.returncode == 0 and os.path.exists(output_path)
        except Exception:
            return False


def _embed_image_b64(img_path: str) -> str:
    """Read image file and return base64 data-URI string."""
    if not os.path.exists(img_path):
        return ""
    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    ext = os.path.splitext(img_path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "gif": "image/gif", "svg": "image/svg+xml"}.get(ext.lstrip("."), "image/png")
    return f"data:{mime};base64,{data}"


# ---------------------------------------------------------------------------
# OLE extraction helpers
# ---------------------------------------------------------------------------

def _extract_from_document(doc_path: str, out_dir: str) -> List[str]:
    """Extract ChemDraw objects from PPTX/DOCX, return list of CDXML paths."""
    from cdxml_toolkit.office.ole_extractor import extract_from_office
    results = extract_from_office(doc_path, out_dir,
                                  output_format="cdxml", convert_method="auto")
    paths = []
    for r in results:
        if r.cdxml_output and os.path.exists(r.cdxml_output):
            paths.append(r.cdxml_output)
        elif r.error:
            print(f"  Warning: {r.source_path}: {r.error}", file=sys.stderr)
    return paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_species_summary(desc) -> list:
    """Build a species summary list from a SchemeDescription."""
    summary = []
    for sid, sp in desc.species.items():
        entry = {"id": sid, "element_type": sp.element_type}
        if sp.label:
            entry["label"] = sp.label
        if sp.name:
            entry["name"] = sp.name[:80]
        if sp.smiles:
            entry["smiles"] = sp.smiles[:120]
        if sp.formula:
            entry["formula"] = sp.formula
        if sp.mw is not None:
            entry["mw"] = round(sp.mw, 1)
        if sp.text_category:
            entry["text_category"] = sp.text_category
        if getattr(sp, "iupac_name", None):
            entry["iupac_name"] = sp.iupac_name
        summary.append(entry)
    return summary


# ---------------------------------------------------------------------------
# Parse one CDXML and return structured result
# ---------------------------------------------------------------------------

def _parse_one(cdxml_path: str, render: bool = False,
               img_dir: Optional[str] = None,
               use_chemscript: bool = False,
               enrich: bool = False,
               segment: bool = False) -> dict:
    """Parse a single CDXML file and return a result dict for the report."""
    result = {
        "file": os.path.basename(cdxml_path),
        "path": cdxml_path,
        "error": None,
        "narrative": "",
        "topology": "",
        "num_steps": 0,
        "species_summary": [],
        "steps_summary": [],
        "warnings": [],
        "image_b64": "",
        "json_full": None,
    }

    # Parse
    try:
        desc = read_scheme(cdxml_path, use_network=False,
                           use_chemscript=use_chemscript, verbose=False,
                           segment=segment)
        result["narrative"] = desc.narrative
        result["topology"] = desc.topology
        result["content_type"] = desc.content_type or "unknown"
        result["num_steps"] = desc.num_steps
        result["warnings"] = desc.warnings
        result["_desc"] = desc  # keep for Tier 2 corrections

        # Species summary
        result["species_summary"] = _build_species_summary(desc)

        # Steps summary
        for step in desc.steps:
            s = {
                "idx": step.step_index,
                "reactants": step.reactant_ids,
                "products": step.product_ids,
                "reagents": step.reagent_ids,
                "arrow": step.arrow_style,
            }
            if step.conditions:
                s["conditions"] = step.conditions[:5]  # cap for display
            if step.yield_text:
                s["yield"] = step.yield_text
            result["steps_summary"].append(s)

        result["json_full"] = desc.to_dict()

        # Sub-scheme data (when segmentation is active)
        if desc.sub_schemes:
            result["sub_schemes"] = []
            for sub in desc.sub_schemes:
                sub_info = {
                    "num_steps": sub.num_steps,
                    "topology": sub.topology,
                    "content_type": sub.content_type or "unknown",
                    "num_species": len(sub.species),
                    "narrative": sub.narrative,
                    "species_summary": _build_species_summary(sub),
                    "steps_summary": [],
                }
                for step in sub.steps:
                    s = {
                        "idx": step.step_index,
                        "reactants": step.reactant_ids,
                        "products": step.product_ids,
                        "reagents": step.reagent_ids,
                        "arrow": step.arrow_style,
                    }
                    if step.conditions:
                        s["conditions"] = step.conditions[:5]
                    if step.yield_text:
                        s["yield"] = step.yield_text
                    sub_info["steps_summary"].append(s)
                result["sub_schemes"].append(sub_info)

        # ML enrichment (optional)
        ml_enrichment = {}
        if enrich and desc.steps:
            try:
                ml_enrichment = enrich_scheme(desc, verbose=True)
                result["ml_enrichment"] = ml_enrichment
            except Exception as exc:
                print(f"  ML enrichment error: {exc}", file=sys.stderr)

        # LLM-quality narrative (with ML grounding when available)
        try:
            result["llm_narrative"] = generate_llm_narrative(
                desc, ml_enrichment=ml_enrichment)
        except Exception:
            result["llm_narrative"] = ""

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)

    # Render image
    if render and img_dir:
        png_path = os.path.join(img_dir, Path(cdxml_path).stem + ".png")
        if _render_cdxml_to_png(cdxml_path, png_path):
            result["image_b64"] = _embed_image_b64(png_path)

    return result


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------

_CSS = """
:root { --bg: #f8f9fa; --card: #fff; --border: #dee2e6; --accent: #0d6efd;
        --green: #198754; --red: #dc3545; --muted: #6c757d; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       background: var(--bg); color: #212529; line-height: 1.5; padding: 24px; }
h1 { font-size: 1.6rem; margin-bottom: 8px; }
.subtitle { color: var(--muted); margin-bottom: 24px; }
.stats { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.stat { background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 12px 20px; min-width: 140px; }
.stat-value { font-size: 1.5rem; font-weight: 700; }
.stat-label { font-size: 0.85rem; color: var(--muted); }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; margin-bottom: 20px; overflow: hidden; }
.card-header { padding: 12px 16px; border-bottom: 1px solid var(--border);
               display: flex; align-items: center; gap: 12px;
               cursor: pointer; user-select: none; }
.card-header:hover { background: #f1f3f5; }
.card-header h2 { font-size: 1rem; flex: 1; }
.badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem;
         font-weight: 600; }
.badge-topo { background: #e7f1ff; color: var(--accent); }
.badge-content { background: #f3e8ff; color: #6f42c1; }
.badge-steps { background: #d1e7dd; color: var(--green); }
.badge-error { background: #f8d7da; color: var(--red); }
.badge-warn { background: #fff3cd; color: #856404; }
.badge-cat { background: #e2e3e5; color: #41464b; font-size: 0.7rem; padding: 1px 6px; }
.badge-cat-cond { background: #cff4fc; color: #055160; }
.badge-cat-cite { background: #e2d9f3; color: #432874; }
.badge-cat-bio { background: #f8d7da; color: var(--red); }
.card-body { padding: 16px; display: none; }
.card.open .card-body { display: block; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
.img-box { text-align: center; }
.img-box img { max-width: 100%; border: 1px solid var(--border); border-radius: 4px; }
.no-img { padding: 40px; text-align: center; color: var(--muted);
          background: #f1f3f5; border-radius: 4px; }
.narrative { background: #f8f9fa; padding: 12px; border-radius: 4px;
             white-space: pre-wrap; font-size: 0.9rem; line-height: 1.6; }
.section-title { font-weight: 600; font-size: 0.9rem; margin: 12px 0 6px;
                 color: var(--muted); text-transform: uppercase;
                 letter-spacing: 0.5px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 4px; }
th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--border); }
th { background: #f1f3f5; font-weight: 600; position: sticky; top: 0; }
.smiles { font-family: "Courier New", monospace; font-size: 0.75rem;
          word-break: break-all; max-width: 280px; color: var(--muted); }
.struct-cell { padding: 2px 4px; }
.struct-img { width: 160px; height: 96px; object-fit: contain;
              border: 1px solid #e9ecef; border-radius: 3px; background: #fff;
              vertical-align: middle; }
.no-struct { color: #ccc; }
.json-toggle { color: var(--accent); cursor: pointer; font-size: 0.85rem;
               text-decoration: underline; margin-top: 8px; display: inline-block; }
.json-block { display: none; background: #f1f3f5; padding: 12px;
              border-radius: 4px; font-family: monospace; font-size: 0.8rem;
              white-space: pre-wrap; max-height: 400px; overflow: auto;
              margin-top: 6px; }
.chevron { transition: transform 0.2s; display: inline-block; }
.card.open .chevron { transform: rotate(90deg); }
.verdict { padding: 3px 10px; border-radius: 4px; font-size: 0.8rem;
           font-weight: 600; display: inline-block; }
.verdict-ok { background: #d1e7dd; color: var(--green); }
.verdict-warn { background: #fff3cd; color: #856404; }
.verdict-fail { background: #f8d7da; color: var(--red); }
.tier-label { font-weight: 700; font-size: 0.8rem; text-transform: uppercase;
              letter-spacing: 0.5px; margin-bottom: 4px; }
.tier-1 .tier-label { color: var(--accent); }
.tier-2 .tier-label { color: #198754; }
.tier-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
            margin-top: 8px; }
.tier-col { padding: 10px; border-radius: 6px; }
.tier-1 { background: #f8f9fa; border: 1px solid #dee2e6; }
.tier-2 { background: #f0faf4; border: 1px solid #a3cfbb; }
.correction-note { font-size: 0.8rem; color: #495057; font-style: italic;
                   margin-top: 6px; padding: 6px 10px; background: #fff3cd;
                   border-radius: 4px; }
.diff-highlight { background: #fff3cd; padding: 1px 4px; border-radius: 2px; }
.badge-t2 { background: #d1e7dd; color: var(--green); }
"""

_JS = """
document.querySelectorAll('.card-header').forEach(h => {
  h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
});
document.querySelectorAll('.json-toggle').forEach(t => {
  t.addEventListener('click', e => {
    e.stopPropagation();
    const block = t.nextElementSibling;
    block.style.display = block.style.display === 'block' ? 'none' : 'block';
  });
});
function expandAll() {
  document.querySelectorAll('.card').forEach(c => c.classList.add('open'));
}
function collapseAll() {
  document.querySelectorAll('.card').forEach(c => c.classList.remove('open'));
}
"""


def _species_table_html(species: list) -> str:
    if not species:
        return '<p style="color:var(--muted)">No species detected</p>'
    rows = []
    for sp in species:
        label = sp.get("label", "")
        name = sp.get("name", "")
        smiles = sp.get("smiles", "")
        formula = sp.get("formula", "")
        mw = sp.get("mw", "")
        etype = sp.get("element_type", "")
        tcat = sp.get("text_category", "")

        # Type/category badge
        if etype == "text":
            cat_css = {"condition_ref": "badge-cat-cond",
                       "citation": "badge-cat-cite",
                       "bioactivity": "badge-cat-bio"}.get(tcat, "badge-cat")
            type_html = f'<span class="badge {cat_css}">{tcat or "text"}</span>'
        else:
            type_html = f'<span class="badge badge-cat">{etype or "?"}</span>'

        # Render SMILES to SVG structure image
        svg_uri = _smiles_to_svg_b64(smiles) if smiles else ""
        if svg_uri:
            struct_html = f'<img src="{svg_uri}" class="struct-img" alt="{smiles}">'
        else:
            struct_html = '<span class="no-struct">-</span>'

        iupac = sp.get("iupac_name", "")
        iupac_html = (f'<span style="color:#0d6efd;font-size:0.85em">{iupac}</span>'
                      if iupac else "")

        rows.append(f"""<tr>
            <td>{sp['id']}</td>
            <td>{type_html}</td>
            <td><b>{label}</b></td>
            <td>{name}{('<br>' + iupac_html) if iupac_html else ''}</td>
            <td class="struct-cell">{struct_html}</td>
            <td class="smiles">{smiles}</td>
            <td>{formula}</td>
            <td>{mw}</td>
        </tr>""")
    return f"""<table>
        <tr><th>ID</th><th>Type</th><th>Label</th><th>Name / IUPAC</th><th>Structure</th><th>SMILES</th><th>Formula</th><th>MW</th></tr>
        {''.join(rows)}
    </table>"""


def _steps_table_html(steps: list) -> str:
    if not steps:
        return '<p style="color:var(--muted)">No steps detected</p>'
    rows = []
    for s in steps:
        r_ids = ", ".join(s.get("reactants", []))
        p_ids = ", ".join(s.get("products", []))
        rg_ids = ", ".join(s.get("reagents", []))
        conds = "; ".join(s.get("conditions", [])[:3])
        yld = s.get("yield", "")
        arrow = s.get("arrow", "solid")
        arrow_icon = {"solid": "->", "dashed": "-->", "failed": "X->"}.get(arrow, "->")
        rows.append(f"""<tr>
            <td>{s['idx'] + 1}</td>
            <td>{r_ids}</td>
            <td>{arrow_icon}</td>
            <td>{p_ids}</td>
            <td>{rg_ids}</td>
            <td>{conds}</td>
            <td>{yld}</td>
        </tr>""")
    return f"""<table>
        <tr><th>#</th><th>Reactants</th><th></th><th>Products</th>
            <th>Reagents</th><th>Conditions</th><th>Yield</th></tr>
        {''.join(rows)}
    </table>"""


def _sub_schemes_html(sub_schemes: list) -> str:
    """Generate HTML for sub-scheme display (collapsible sections)."""
    if not sub_schemes:
        return ""
    parts = [f'<div class="section-title" style="color:#6f42c1">'
             f'Composite Scheme: {len(sub_schemes)} independent sub-schemes'
             f'</div>']
    for i, sub in enumerate(sub_schemes):
        topo = sub.get("topology", "?")
        ctype = sub.get("content_type", "unknown")
        n_steps = sub.get("num_steps", 0)
        n_species = sub.get("num_species", 0)
        narrative = sub.get("narrative", "")
        species_summary = sub.get("species_summary", [])
        steps_summary = sub.get("steps_summary", [])
        parts.append(f"""
        <details style="margin:8px 0;border:1px solid #ddd;border-radius:4px;padding:8px">
            <summary style="cursor:pointer;font-weight:600">
                Sub-scheme {i + 1}
                <span class="badge badge-topo">{topo}</span>
                <span class="badge badge-content">{ctype}</span>
                <span class="badge badge-steps">{n_steps} steps, {n_species} species</span>
            </summary>
            <div style="margin-top:8px">
                <div class="narrative">{narrative}</div>
                <div class="section-title" style="font-size:0.85rem">
                    Species ({len(species_summary)})
                </div>
                {_species_table_html(species_summary)}
                <div class="section-title" style="font-size:0.85rem">
                    Steps
                </div>
                {_steps_table_html(steps_summary)}
            </div>
        </details>
        """)
    return "\n".join(parts)


def _verdict(result: dict) -> Tuple[str, str]:
    """Return (css_class, text) for the verdict badge."""
    if result["error"]:
        return "verdict-fail", "PARSE ERROR"
    if result["num_steps"] == 0:
        return "verdict-warn", "NO STEPS"
    if result["warnings"]:
        return "verdict-warn", f"OK ({len(result['warnings'])} warnings)"
    return "verdict-ok", "OK"


def _tier2_summary_html(t1: dict, t2_corrections: dict, t2_desc) -> str:
    """Generate Tier 2 correction summary HTML."""
    if not t2_corrections:
        return ""

    changes = []
    if "content_type" in t2_corrections:
        old = t1.get("content_type", "unknown")
        new = t2_corrections["content_type"]
        if old != new:
            changes.append(
                f'<b>Content type</b>: '
                f'<span class="diff-highlight">{old} &rarr; {new}</span>')
    if "topology" in t2_corrections:
        old = t1.get("topology", "?")
        new = t2_corrections["topology"]
        if old != new:
            changes.append(
                f'<b>Topology</b>: '
                f'<span class="diff-highlight">{old} &rarr; {new}</span>')
    sp_corr = t2_corrections.get("species_corrections", {})
    for sp_id, fixes in sp_corr.items():
        for field, val in fixes.items():
            changes.append(
                f'<b>{sp_id}.{field}</b>: '
                f'<span class="diff-highlight">&rarr; {val}</span>')

    notes = t2_corrections.get("notes", "")

    # Tier 2 narrative
    t2_narrative = t2_desc.narrative if t2_desc else ""

    changes_html = "<br>".join(changes) if changes else "No field changes"
    note_html = (f'<div class="correction-note">{notes}</div>'
                 if notes else "")

    return f"""
    <div class="tier-row">
        <div class="tier-col tier-1">
            <div class="tier-label">Tier 1 (Deterministic)</div>
            <div class="narrative">{t1.get('narrative', '')}</div>
        </div>
        <div class="tier-col tier-2">
            <div class="tier-label">Tier 2 (LLM-Refined)</div>
            <div class="narrative">{t2_narrative}</div>
        </div>
    </div>
    <div style="margin-top:8px">
        <b style="font-size:0.85rem">LLM Corrections:</b><br>
        <span style="font-size:0.85rem">{changes_html}</span>
        {note_html}
    </div>
    """


def _card_html(idx: int, result: dict) -> str:
    """Generate HTML for one scheme card."""
    v_class, v_text = _verdict(result)
    has_t2 = result.get("_t2_corrections") is not None

    # Image section
    if result["image_b64"]:
        img_html = f'<img src="{result["image_b64"]}" alt="Rendered scheme">'
    else:
        img_html = '<div class="no-img">No rendered image<br>(use --render to enable ChemDraw rendering)</div>'

    # Error display
    if result["error"]:
        body_html = f'<div class="narrative" style="color:var(--red)">{result["error"]}</div>'
    elif has_t2:
        # Dual-tier display with LLM narrative
        t2_desc = result.get("_t2_desc")
        body_html = _tier2_summary_html(result, result["_t2_corrections"], t2_desc)
        # Add LLM narrative if available
        llm_nar = result.get("llm_narrative", "")
        if llm_nar:
            body_html += f"""
            <div style="margin-top:10px">
                <div class="tier-col tier-2" style="margin-bottom:8px">
                    <div class="tier-label">LLM Narrative</div>
                    <div class="narrative">{llm_nar}</div>
                </div>
            </div>
            """
        body_html += f"""
        <div class="section-title">Species Registry ({len(result['species_summary'])} species)</div>
        {_species_table_html(result['species_summary'])}

        <div class="section-title">Reaction Steps</div>
        {_steps_table_html(result['steps_summary'])}

        {"".join(f'<div class="badge badge-warn" style="margin-top:4px">{w}</div>' for w in result.get('warnings', []))}
        """
    else:
        llm_nar = result.get("llm_narrative", "")
        llm_html = ""
        if llm_nar:
            llm_html = f"""
            <div class="tier-row">
                <div class="tier-col tier-1">
                    <div class="tier-label">Parser Output</div>
                    <div class="narrative">{result['narrative']}</div>
                </div>
                <div class="tier-col tier-2">
                    <div class="tier-label">LLM Narrative</div>
                    <div class="narrative">{llm_nar}</div>
                </div>
            </div>
            """
        else:
            llm_html = f"""
            <div class="section-title">Narrative</div>
            <div class="narrative">{result['narrative']}</div>
            """

        body_html = f"""
        {llm_html}

        <div class="section-title">Species Registry ({len(result['species_summary'])} species)</div>
        {_species_table_html(result['species_summary'])}

        <div class="section-title">Reaction Steps</div>
        {_steps_table_html(result['steps_summary'])}

        {"".join(f'<div class="badge badge-warn" style="margin-top:4px">{w}</div>' for w in result.get('warnings', []))}
        """

    # Sub-schemes display (when segmentation is active)
    sub_html = _sub_schemes_html(result.get("sub_schemes", []))
    if sub_html:
        body_html += sub_html

    # JSON toggle
    json_html = ""
    if result.get("json_full"):
        json_str = json.dumps(result["json_full"], indent=2, ensure_ascii=False)
        # Escape HTML
        json_str = json_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        json_html = f"""
        <span class="json-toggle">Show full JSON</span>
        <div class="json-block">{json_str}</div>
        """

    # Header badges — show Tier 2 values if corrected
    t2_corr = result.get("_t2_corrections", {}) or {}
    topo_display = t2_corr.get("topology", result.get("topology", "?"))
    ctype_display = t2_corr.get("content_type", result.get("content_type", "unknown"))
    t2_badge = ' <span class="badge badge-t2">T2</span>' if has_t2 else ""
    ml_badge = (' <span class="badge" style="background:#cce5ff;color:#004085">ML</span>'
                if result.get("ml_enrichment") else "")
    n_sub = len(result.get("sub_schemes", []))
    seg_badge = (f' <span class="badge" style="background:#e8daef;color:#6f42c1">'
                 f'{n_sub} sub-schemes</span>' if n_sub > 0 else "")

    return f"""
    <div class="card" id="card-{idx}">
        <div class="card-header">
            <span class="chevron">&#9654;</span>
            <h2>{result['file']}</h2>
            <span class="badge badge-topo">{topo_display}</span>
            <span class="badge badge-content">{ctype_display}</span>
            <span class="badge badge-steps">{result['num_steps']} steps</span>
            <span class="verdict {v_class}">{v_text}</span>{t2_badge}{ml_badge}{seg_badge}
        </div>
        <div class="card-body">
            <div class="two-col">
                <div class="img-box">{img_html}</div>
                <div>{body_html}</div>
            </div>
            {json_html}
        </div>
    </div>
    """


def generate_report(results: List[dict], output_path: str,
                    title: str = "Scheme Reader Verification Report") -> None:
    """Generate the HTML report from a list of result dicts."""
    n_total = len(results)
    n_ok = sum(1 for r in results if not r["error"] and r["num_steps"] > 0)
    n_warn = sum(1 for r in results if not r["error"] and r["warnings"])
    n_err = sum(1 for r in results if r["error"])
    n_empty = sum(1 for r in results if not r["error"] and r["num_steps"] == 0)
    n_t2 = sum(1 for r in results if r.get("_t2_corrections"))
    n_ml = sum(1 for r in results if r.get("ml_enrichment"))

    # Sort: errors first, then by filename
    results_sorted = sorted(results,
                            key=lambda r: (0 if r["error"] else 1, r["file"]))

    cards = "\n".join(_card_html(i, r) for i, r in enumerate(results_sorted))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{title}</h1>
<p class="subtitle">Visual verification of scheme_reader output.
   Click a card to expand. Compare the rendered image with the parsed narrative.</p>

<div class="stats">
    <div class="stat">
        <div class="stat-value">{n_total}</div>
        <div class="stat-label">Total schemes</div>
    </div>
    <div class="stat">
        <div class="stat-value" style="color:var(--green)">{n_ok}</div>
        <div class="stat-label">Parsed OK</div>
    </div>
    <div class="stat">
        <div class="stat-value" style="color:#856404">{n_warn}</div>
        <div class="stat-label">With warnings</div>
    </div>
    <div class="stat">
        <div class="stat-value" style="color:var(--muted)">{n_empty}</div>
        <div class="stat-label">No steps found</div>
    </div>
    <div class="stat">
        <div class="stat-value" style="color:var(--red)">{n_err}</div>
        <div class="stat-label">Parse errors</div>
    </div>
    <div class="stat">
        <div class="stat-value" style="color:#198754">{n_t2}</div>
        <div class="stat-label">LLM-refined</div>
    </div>
    <div class="stat">
        <div class="stat-value" style="color:#0d6efd">{n_ml}</div>
        <div class="stat-label">ML-enriched</div>
    </div>
</div>

<div style="margin-bottom: 16px;">
    <button onclick="expandAll()" style="padding:6px 14px;cursor:pointer;border:1px solid var(--border);border-radius:4px;background:var(--card)">Expand All</button>
    <button onclick="collapseAll()" style="padding:6px 14px;cursor:pointer;border:1px solid var(--border);border-radius:4px;background:var(--card);margin-left:6px">Collapse All</button>
</div>

{cards}

<script>{_JS}</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report written to {output_path} ({n_total} schemes)")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a visual verification report for scheme_reader")
    parser.add_argument("inputs", nargs="+",
                        help="CDXML files, directories of CDXML files, "
                             "or PPTX/DOCX documents")
    parser.add_argument("-o", "--output", default="scheme_reader_report.html",
                        help="Output HTML file (default: scheme_reader_report.html)")
    parser.add_argument("--render", action="store_true",
                        help="Render CDXML to PNG via ChemDraw COM "
                             "(requires ChemDraw to be closed)")
    parser.add_argument("--chemscript", action="store_true",
                        help="Use ChemScript for SMILES (best abbreviation "
                             "resolution, requires ChemDraw 16+ on Windows)")
    parser.add_argument("--corrections",
                        help="Tier 2 corrections JSON file "
                             "(maps source_key to correction dict)")
    parser.add_argument("--enrich", action="store_true",
                        help="Run RXNMapper + RXN Insight ML enrichment "
                             "per step (requires chem-pipeline rxn-experiments)")
    parser.add_argument("--segment", action="store_true",
                        help="Auto-segment multi-panel CDXML files into "
                             "independent sub-schemes")
    parser.add_argument("--title", default="Scheme Reader Verification Report",
                        help="Report title")
    args = parser.parse_args()

    # Collect all CDXML paths
    cdxml_paths: List[str] = []
    tmp_dirs = []

    for inp in args.inputs:
        inp = os.path.abspath(inp)
        ext = os.path.splitext(inp)[1].lower()

        if ext in (".pptx", ".docx"):
            # Extract from document
            doc_name = Path(inp).stem
            tmp = tempfile.mkdtemp(prefix=f"sr_verify_{doc_name}_")
            tmp_dirs.append(tmp)
            print(f"Extracting from {os.path.basename(inp)}...", file=sys.stderr)
            extracted = _extract_from_document(inp, tmp)
            # Tag with source document
            for p in extracted:
                cdxml_paths.append((p, os.path.basename(inp)))
            print(f"  -> {len(extracted)} ChemDraw objects", file=sys.stderr)

        elif ext == ".cdxml":
            cdxml_paths.append((inp, None))

        elif os.path.isdir(inp):
            for fn in sorted(os.listdir(inp)):
                if fn.lower().endswith(".cdxml"):
                    cdxml_paths.append((os.path.join(inp, fn), os.path.basename(inp)))
        else:
            print(f"Skipping unknown input: {inp}", file=sys.stderr)

    if not cdxml_paths:
        print("No CDXML files found.", file=sys.stderr)
        sys.exit(1)

    # Optional image rendering directory
    img_dir = None
    if args.render:
        img_dir = tempfile.mkdtemp(prefix="sr_verify_img_")
        tmp_dirs.append(img_dir)

    # Load Tier 2 corrections if provided
    corrections_map = {}
    if args.corrections:
        with open(args.corrections, "r", encoding="utf-8") as f:
            corrections_map = json.load(f)
        print(f"Loaded {len(corrections_map)} Tier 2 corrections",
              file=sys.stderr)

    # Parse all (Phase 1: deterministic parsing, no ML enrichment yet)
    results = []
    for i, (cdxml_path, source_doc) in enumerate(cdxml_paths):
        name = os.path.basename(cdxml_path)
        if source_doc:
            display_name = f"[{source_doc}] {name}"
        else:
            display_name = name
        print(f"  [{i+1}/{len(cdxml_paths)}] {display_name}", file=sys.stderr)
        result = _parse_one(cdxml_path, render=args.render, img_dir=img_dir,
                            use_chemscript=args.chemscript,
                            enrich=False,  # ML enrichment handled in batch below
                            segment=args.segment)
        if source_doc:
            result["file"] = display_name

        # Apply Tier 2 corrections if available
        corr_key = None
        for candidate in [
            f"{source_doc or 'standalone'}/{name}" if source_doc else name,
            name,
            f"docx/{name}" if source_doc and "docx" in source_doc.lower() else None,
            f"pptx/{name}" if source_doc and "pptx" in source_doc.lower() else None,
            f"showcase/{name}" if source_doc and "showcase" in source_doc.lower() else None,
        ]:
            if candidate and candidate in corrections_map:
                corr_key = candidate
                break

        if corr_key and result.get("_desc"):
            corr = corrections_map[corr_key]
            try:
                t2_desc = apply_corrections(result["_desc"], corr)
                result["_t2_corrections"] = corr
                result["_t2_desc"] = t2_desc
            except Exception as e:
                print(f"  Warning: Tier 2 correction failed for {name}: {e}",
                      file=sys.stderr)

        results.append(result)

    # Regenerate LLM narrative from corrected desc (Tier 2) where available
    # This ensures content_type/topology corrections flow into the narrative
    for r in results:
        t2 = r.get("_t2_desc")
        if t2:
            try:
                r["llm_narrative"] = generate_llm_narrative(t2)
            except Exception:
                pass

    # Phase 1.5: Aligned IUPAC name enrichment (requires ChemScript)
    if args.chemscript:
        n_aligned_total = 0
        for r in results:
            desc = r.get("_t2_desc") or r.get("_desc")
            if desc and desc.steps:
                try:
                    n = enrich_aligned_names(desc)
                    if n:
                        n_aligned_total += n
                        r["llm_narrative"] = generate_llm_narrative(desc)
                        # Rebuild species summary to include updated names
                        r["species_summary"] = _build_species_summary(desc)
                except Exception:
                    pass
        if n_aligned_total:
            print(f"  Aligned IUPAC names: {n_aligned_total} species updated",
                  file=sys.stderr)

    # Phase 2: Batch ML enrichment (single RXNMapper subprocess for all reactions)
    if args.enrich:
        # Collect schemes with steps for enrichment
        descs_for_enrich = []
        for i, r in enumerate(results):
            desc = r.get("_desc")
            if desc and desc.steps:
                descs_for_enrich.append((i, desc))

        if descs_for_enrich:
            print(f"\nBatch ML enrichment for {len(descs_for_enrich)} schemes...",
                  file=sys.stderr)
            batch_results = batch_enrich_schemes(descs_for_enrich, verbose=True)

            # Apply enrichment and regenerate narratives
            # Use corrected T2 desc when available so corrections flow into narrative
            for desc_idx, enrichment in batch_results:
                if enrichment:
                    results[desc_idx]["ml_enrichment"] = enrichment
                    desc = (results[desc_idx].get("_t2_desc")
                            or results[desc_idx].get("_desc"))
                    if desc:
                        try:
                            results[desc_idx]["llm_narrative"] = (
                                generate_llm_narrative(desc,
                                                       ml_enrichment=enrichment))
                        except Exception:
                            pass
            n_enriched = sum(1 for _, e in batch_results if e)
            print(f"  {n_enriched} schemes enriched", file=sys.stderr)

    # Clean up internal fields before report
    for r in results:
        r.pop("_desc", None)

    # Generate report
    generate_report(results, args.output, title=args.title)

    # Cleanup temp dirs only if no images needed (they're embedded as b64)
    for d in tmp_dirs:
        try:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
