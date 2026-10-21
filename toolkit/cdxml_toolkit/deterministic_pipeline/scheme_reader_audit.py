"""Audit scheme_reader Mode A (deterministic) quality on showcase CDXMLs.

Runs ``read_scheme()`` against every showcase file and checks:
  - Parse success (steps, species, narrative present)
  - Step completeness (each step has reactants AND products)
  - Species coverage (fraction of species used in steps)
  - Topology correctness (matches filename convention)
  - Conditions extraction (non-empty conditions per step)
  - Arrow style accuracy (dashed/failed detected)
  - Narrative quality (no leftover ``[SMILES: ...]`` fragments)

Usage::

    python -m cdxml_toolkit.scheme_reader_audit [showcase_dir]
    python -m cdxml_toolkit.scheme_reader_audit --html report.html --render
    python -m cdxml_toolkit.scheme_reader_audit --json -o audit_results.json
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field, asdict
from html import escape as html_escape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..perception.scheme_reader import read_scheme, SchemeDescription


# ---------------------------------------------------------------------------
# Expected topology from filename conventions
# ---------------------------------------------------------------------------

_TOPOLOGY_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"divergent|_sar", re.I), "divergent"),
    (re.compile(r"stacked|parallel|comparison|different_routes", re.I), "parallel"),
    # serpentine/wrap are LAYOUTS, topology is still linear
    (re.compile(r"serpentine|wrap|linear|sequential|letter|compact|"
                r"name_resolution|reductive|mitsunobu|grignard|"
                r"two_step|three_step|run_arrows|failed|above_structures", re.I),
     "linear"),
]


def _expected_topology(filename: str) -> Optional[str]:
    """Infer expected topology from filename convention.  Returns None if ambiguous."""
    base = os.path.splitext(os.path.basename(filename))[0]
    for pattern, topo in _TOPOLOGY_RULES:
        if pattern.search(base):
            return topo
    return None


def _expected_step_count(filename: str) -> Optional[int]:
    """Infer expected step count from filename if it contains a number hint."""
    base = os.path.splitext(os.path.basename(filename))[0]
    # Patterns like "4step", "5step", "7step", "3step"
    m = re.search(r"(\d+)\s*step", base, re.I)
    if m:
        return int(m.group(1))
    # "two_step", "three_step"
    word_map = {"two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8}
    for word, n in word_map.items():
        if f"{word}_step" in base.lower():
            return n
    # Divergent: count from filename e.g. "4products"
    m2 = re.search(r"(\d+)\s*product", base, re.I)
    if m2:
        return int(m2.group(1))
    # Divergent/SAR schemes — step count equals number of products, skip
    # single-step heuristic for these
    if re.search(r"divergent|_sar", base, re.I):
        return None  # can't infer from filename alone
    # Single-step schemes (buchwald, suzuki, snar, etc.) that are linear with no step count
    if re.search(r"buchwald|suzuki|snar|amide_coupling|boc_deprotection|"
                 r"reductive_amination|mitsunobu|grignard|name_resolution|"
                 r"failed_arrow", base, re.I):
        return 1
    return None


# ---------------------------------------------------------------------------
# Per-file audit result
# ---------------------------------------------------------------------------

@dataclass
class FileAuditResult:
    """Quality audit result for one CDXML file."""
    filename: str
    cdxml_path: str = ""
    status: str = "PASS"  # "PASS", "WARN", "FAIL", "ERROR"
    num_steps: int = 0
    num_species: int = 0
    topology: str = ""
    content_type: str = ""
    expected_topology: Optional[str] = None
    expected_steps: Optional[int] = None
    topology_match: bool = True
    step_count_match: bool = True
    all_steps_complete: bool = True     # every step has >=1 reactant AND product
    species_coverage: float = 1.0       # fraction in steps
    orphan_species: List[str] = field(default_factory=list)
    conditions_coverage: float = 1.0    # fraction of steps with conditions
    steps_missing_conditions: List[int] = field(default_factory=list)
    arrow_styles: List[str] = field(default_factory=list)
    smiles_in_narrative: int = 0        # count of [SMILES: ...] in narrative
    warnings: List[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    error: Optional[str] = None
    # Rich data (stored for HTML, not serialised to JSON)
    _desc: Optional[SchemeDescription] = field(default=None, repr=False)
    _image_b64: str = field(default="", repr=False)

    @property
    def detail_line(self) -> str:
        """One-line summary for terminal output."""
        parts = [f"{self.num_steps} step{'s' if self.num_steps != 1 else ''}"]
        parts.append(f"{self.num_species} species")
        parts.append(f"{self.topology}")
        if self.expected_topology and self.topology_match:
            parts[-1] += " OK"
        elif self.expected_topology and not self.topology_match:
            parts[-1] += f" MISMATCH (expected {self.expected_topology})"
        if self.expected_steps is not None and not self.step_count_match:
            parts.append(f"steps: {self.num_steps}/{self.expected_steps}")
        if not self.all_steps_complete:
            parts.append("incomplete steps")
        if self.species_coverage < 1.0:
            parts.append(f"coverage {self.species_coverage:.0%}")
        if self.smiles_in_narrative > 0:
            parts.append(f"{self.smiles_in_narrative} SMILES in narrative")
        return ", ".join(parts)


# ---------------------------------------------------------------------------
# Aggregate report
# ---------------------------------------------------------------------------

@dataclass
class AuditReport:
    """Aggregate quality report across all audited files."""
    showcase_dir: str = ""
    total_files: int = 0
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    results: List[FileAuditResult] = field(default_factory=list)
    total_time_ms: float = 0.0

    def to_dict(self) -> dict:
        d = {
            "showcase_dir": self.showcase_dir,
            "total_files": self.total_files,
            "pass": self.pass_count,
            "warn": self.warn_count,
            "fail": self.fail_count,
            "error": self.error_count,
            "total_time_ms": round(self.total_time_ms, 1),
            "results": [],
        }
        for r in self.results:
            rd = {k: v for k, v in asdict(r).items()
                  if not k.startswith("_")}
            d["results"].append(rd)
        return d


# ---------------------------------------------------------------------------
# Image rendering helpers
# ---------------------------------------------------------------------------

def _render_cdxml_to_png(cdxml_path: str, output_path: str) -> bool:
    """Render a CDXML file to PNG via cdxml_to_image.  Returns True on success."""
    try:
        from ..chemdraw.cdxml_to_image import cdxml_to_png
        cdxml_to_png(cdxml_path, output_path)
        return True
    except Exception:
        try:
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
    ext = os.path.splitext(img_path)[1].lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg",
            "jpeg": "image/jpeg"}.get(ext, "image/png")
    return f"data:{mime};base64,{data}"


# ---------------------------------------------------------------------------
# Core audit logic
# ---------------------------------------------------------------------------

def _audit_one(cdxml_path: str,
               use_chemscript: bool = False,
               verbose: bool = False,
               render: bool = False,
               img_dir: Optional[str] = None) -> FileAuditResult:
    """Run quality audit on a single CDXML file."""
    filename = os.path.basename(cdxml_path)
    result = FileAuditResult(filename=filename, cdxml_path=cdxml_path)
    result.expected_topology = _expected_topology(filename)
    result.expected_steps = _expected_step_count(filename)

    t0 = time.perf_counter()
    try:
        desc = read_scheme(cdxml_path,
                           use_network=False,
                           use_chemscript=use_chemscript,
                           verbose=verbose)
    except Exception as exc:
        result.status = "ERROR"
        result.error = f"{type(exc).__name__}: {exc}"
        result.parse_time_ms = (time.perf_counter() - t0) * 1000
        return result
    result.parse_time_ms = (time.perf_counter() - t0) * 1000
    result._desc = desc

    # Render image
    if render and img_dir:
        png_path = os.path.join(img_dir, Path(cdxml_path).stem + ".png")
        if _render_cdxml_to_png(cdxml_path, png_path):
            result._image_b64 = _embed_image_b64(png_path)

    # Basic parse success
    result.num_steps = desc.num_steps
    result.num_species = len(desc.species)
    result.topology = desc.topology
    result.content_type = desc.content_type or "unknown"

    if desc.num_steps < 1:
        result.status = "FAIL"
        result.warnings.append("No steps parsed")
        return result
    if not desc.species:
        result.status = "FAIL"
        result.warnings.append("No species found")
        return result
    if not desc.narrative:
        result.warnings.append("Empty narrative")

    # Topology correctness
    if result.expected_topology:
        result.topology_match = (desc.topology == result.expected_topology)
        if not result.topology_match:
            result.warnings.append(
                f"Topology mismatch: got '{desc.topology}', "
                f"expected '{result.expected_topology}'"
            )

    # Step count correctness
    if result.expected_steps is not None:
        result.step_count_match = (desc.num_steps == result.expected_steps)
        if not result.step_count_match:
            result.warnings.append(
                f"Step count mismatch: got {desc.num_steps}, "
                f"expected {result.expected_steps}"
            )

    # Step completeness
    for step in desc.steps:
        if not step.reactant_ids or not step.product_ids:
            result.all_steps_complete = False
            result.warnings.append(
                f"Step {step.step_index}: missing "
                f"{'reactants' if not step.reactant_ids else 'products'}"
            )

    # Species coverage
    referenced_ids = set()
    for step in desc.steps:
        referenced_ids.update(step.reactant_ids)
        referenced_ids.update(step.product_ids)
        referenced_ids.update(step.reagent_ids)

    fragment_species = {sid: sp for sid, sp in desc.species.items()
                        if sp.element_type == "fragment"}
    if fragment_species:
        covered = sum(1 for sid in fragment_species if sid in referenced_ids)
        result.species_coverage = covered / len(fragment_species)
        result.orphan_species = [
            sid for sid in fragment_species if sid not in referenced_ids
        ]
        if result.species_coverage < 0.8:
            result.warnings.append(
                f"Low species coverage: {result.species_coverage:.0%} "
                f"({len(result.orphan_species)} orphans)"
            )

    # Conditions coverage
    steps_with_conds = 0
    for step in desc.steps:
        if step.conditions or step.condition_text_raw:
            steps_with_conds += 1
        else:
            result.steps_missing_conditions.append(step.step_index)
    if desc.num_steps > 0:
        result.conditions_coverage = steps_with_conds / desc.num_steps

    # Arrow styles
    result.arrow_styles = [s.arrow_style for s in desc.steps]

    # Narrative quality
    result.smiles_in_narrative = len(re.findall(r"\[SMILES:", desc.narrative))
    if result.smiles_in_narrative > 0:
        result.warnings.append(
            f"{result.smiles_in_narrative} raw SMILES in narrative"
        )

    # Scheme warnings
    if desc.warnings:
        for w in desc.warnings:
            result.warnings.append(f"scheme warning: {w}")

    # Determine overall status
    has_fail = False
    has_warn = False

    if not result.topology_match:
        has_fail = True
    if not result.step_count_match:
        if result.expected_steps and result.num_steps <= result.expected_steps // 2:
            has_fail = True
        else:
            has_warn = True
    if not result.all_steps_complete:
        has_warn = True
    if result.species_coverage < 0.5:
        has_fail = True
    elif result.species_coverage < 0.8:
        has_warn = True
    if result.smiles_in_narrative > 0:
        has_warn = True

    if has_fail:
        result.status = "FAIL"
    elif has_warn:
        result.status = "WARN"
    else:
        result.status = "PASS"

    return result


def audit_showcase(showcase_dir: str,
                   use_chemscript: bool = False,
                   verbose: bool = False,
                   render: bool = False) -> AuditReport:
    """Run quality audit on all showcase CDXMLs in a directory.

    Parameters
    ----------
    showcase_dir : str
        Directory containing ``*.cdxml`` showcase files.
    use_chemscript : bool
        Use ChemScript for SMILES extraction.
    verbose : bool
        Print debug info during parsing.
    render : bool
        Render CDXMLs to PNG via ChemDraw COM (requires ChemDraw closed).

    Returns
    -------
    AuditReport
        Aggregate quality report.
    """
    report = AuditReport(showcase_dir=showcase_dir)

    cdxml_files = sorted(
        f for f in os.listdir(showcase_dir) if f.endswith(".cdxml")
    )
    report.total_files = len(cdxml_files)

    # Set up image directory if rendering
    img_dir = None
    if render:
        img_dir = tempfile.mkdtemp(prefix="audit_imgs_")
        print(f"  Rendering to {img_dir}", file=sys.stderr)

    t_total = time.perf_counter()
    for i, fname in enumerate(cdxml_files):
        path = os.path.join(showcase_dir, fname)
        if render:
            print(f"  [{i+1}/{len(cdxml_files)}] {fname}", file=sys.stderr)
        result = _audit_one(path, use_chemscript=use_chemscript,
                            verbose=verbose, render=render, img_dir=img_dir)
        report.results.append(result)

        if result.status == "PASS":
            report.pass_count += 1
        elif result.status == "WARN":
            report.warn_count += 1
        elif result.status == "FAIL":
            report.fail_count += 1
        else:
            report.error_count += 1

    report.total_time_ms = (time.perf_counter() - t_total) * 1000
    return report


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "PASS": "\033[92m",   # green
    "WARN": "\033[93m",   # yellow
    "FAIL": "\033[91m",   # red
    "ERROR": "\033[91m",  # red
}
_RESET = "\033[0m"


def _print_report(report: AuditReport, color: bool = True) -> None:
    """Print human-readable audit report to stdout."""
    print()
    print("=" * 70)
    print("  Scheme Reader Audit: Mode A (Deterministic)")
    print(f"  {report.total_files} showcase files evaluated")
    print("=" * 70)
    print()

    max_name_len = max((len(r.filename) for r in report.results), default=30)

    for r in report.results:
        if color:
            c = _STATUS_COLORS.get(r.status, "")
            tag = f"{c}{r.status:5s}{_RESET}"
        else:
            tag = f"{r.status:5s}"

        name = r.filename.ljust(max_name_len)
        if r.error:
            detail = f"ERROR: {r.error}"
        else:
            detail = r.detail_line
        print(f"  {tag}  {name}  {detail}")

        # Print warnings indented
        for w in r.warnings:
            if color:
                print(f"         {_STATUS_COLORS.get('WARN', '')}-> {w}{_RESET}")
            else:
                print(f"         -> {w}")

    print()
    print("-" * 70)
    summary_parts = []
    if report.pass_count:
        summary_parts.append(f"{report.pass_count} PASS")
    if report.warn_count:
        summary_parts.append(f"{report.warn_count} WARN")
    if report.fail_count:
        summary_parts.append(f"{report.fail_count} FAIL")
    if report.error_count:
        summary_parts.append(f"{report.error_count} ERROR")
    print(f"  Summary: {', '.join(summary_parts)}")
    print(f"  Total parse time: {report.total_time_ms:.0f} ms")
    print()


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

_STATUS_BG = {
    "PASS": "#d4edda", "WARN": "#fff3cd",
    "FAIL": "#f8d7da", "ERROR": "#f8d7da",
}
_STATUS_FG = {
    "PASS": "#155724", "WARN": "#856404",
    "FAIL": "#721c24", "ERROR": "#721c24",
}
_STATUS_BORDER = {
    "PASS": "#c3e6cb", "WARN": "#ffeeba",
    "FAIL": "#f5c6cb", "ERROR": "#f5c6cb",
}


def _species_table_html(desc: SchemeDescription) -> str:
    """Build an HTML table for the species registry."""
    if not desc.species:
        return '<p style="color:#6c757d;font-size:0.85rem">No species</p>'
    rows = []
    for sid, sp in desc.species.items():
        label = html_escape(sp.label or "")
        name = html_escape(sp.name or "")
        iupac = html_escape(getattr(sp, "iupac_name", "") or "")
        smiles = html_escape(sp.smiles or "")
        formula = html_escape(sp.formula or "")
        mw_str = f"{sp.mw:.1f}" if sp.mw else ""
        etype = sp.element_type or ""
        tcat = html_escape(sp.text_category or "")
        # Choose display name
        display = iupac or name or formula or ""
        # Truncate long SMILES for display
        smiles_short = smiles[:60] + ("..." if len(smiles) > 60 else "")
        rows.append(f"""<tr>
            <td class="mono">{html_escape(sid)}</td>
            <td>{label}</td>
            <td>{display}</td>
            <td class="mono" title="{smiles}">{smiles_short}</td>
            <td>{formula}</td>
            <td style="text-align:right">{mw_str}</td>
            <td>{etype}{(' / ' + tcat) if tcat else ''}</td>
        </tr>""")
    return f"""<table class="inner-table">
        <tr><th>ID</th><th>Label</th><th>Name</th><th>SMILES</th>
            <th>Formula</th><th>MW</th><th>Type</th></tr>
        {''.join(rows)}
    </table>"""


def _steps_table_html(desc: SchemeDescription) -> str:
    """Build an HTML table for the reaction steps."""
    if not desc.steps:
        return '<p style="color:#6c757d;font-size:0.85rem">No steps</p>'
    rows = []
    for step in desc.steps:
        r_ids = ", ".join(step.reactant_ids)
        p_ids = ", ".join(step.product_ids)
        rg_ids = ", ".join(step.reagent_ids)
        conds = "; ".join(step.conditions[:3])
        yld = step.yield_text or ""
        arrow_icon = {"solid": "&#8594;", "dashed": "&#8669;",
                      "failed": "&#10007;&#8594;"}.get(step.arrow_style, "&#8594;")
        rows.append(f"""<tr>
            <td style="text-align:center">{step.step_index + 1}</td>
            <td class="mono">{html_escape(r_ids)}</td>
            <td style="text-align:center;font-size:1.1rem">{arrow_icon}</td>
            <td class="mono">{html_escape(p_ids)}</td>
            <td class="mono">{html_escape(rg_ids)}</td>
            <td>{html_escape(conds)}</td>
            <td>{html_escape(yld)}</td>
        </tr>""")
    return f"""<table class="inner-table">
        <tr><th>#</th><th>Reactants</th><th></th><th>Products</th>
            <th>Reagents</th><th>Conditions</th><th>Yield</th></tr>
        {''.join(rows)}
    </table>"""


def _card_html(idx: int, r: FileAuditResult) -> str:
    """Generate one expandable card for a scheme file."""
    bg = _STATUS_BG.get(r.status, "#fff")
    fg = _STATUS_FG.get(r.status, "#000")
    border = _STATUS_BORDER.get(r.status, "#dee2e6")

    # Status badge
    status_badge = (f'<span class="badge" style="background:{bg};color:{fg}">'
                    f'{r.status}</span>')

    # Topology badge
    if r.expected_topology and not r.topology_match:
        topo_badge = (f'<span class="badge badge-fail">{r.topology}'
                      f' (expected {r.expected_topology})</span>')
    else:
        topo_badge = f'<span class="badge badge-info">{r.topology}</span>'

    ctype_badge = (f'<span class="badge badge-muted">{r.content_type}</span>'
                   if r.content_type else "")
    steps_badge = (f'<span class="badge badge-info">'
                   f'{r.num_steps} step{"s" if r.num_steps != 1 else ""}</span>')

    # Image section
    if r._image_b64:
        img_html = f'<img src="{r._image_b64}" alt="Rendered scheme">'
    else:
        img_html = ('<div class="no-img">No rendered image<br>'
                    '<small>(use --render)</small></div>')

    # Body content
    if r.error:
        body_html = (f'<div class="narrative" style="color:#721c24">'
                     f'{html_escape(r.error)}</div>')
    else:
        desc = r._desc
        narrative = html_escape(desc.narrative) if desc else ""
        # Quality checklist
        checks = []
        checks.append(_check_item("Steps parsed", r.num_steps >= 1,
                                   f"{r.num_steps} steps"))
        checks.append(_check_item("Species found", r.num_species >= 1,
                                   f"{r.num_species} species"))
        if r.expected_topology:
            checks.append(_check_item("Topology correct", r.topology_match,
                                       f"{r.topology}"
                                       + (f" (expected {r.expected_topology})"
                                          if not r.topology_match else "")))
        if r.expected_steps is not None:
            checks.append(_check_item("Step count correct", r.step_count_match,
                                       f"{r.num_steps}"
                                       + (f"/{r.expected_steps}"
                                          if not r.step_count_match else "")))
        checks.append(_check_item("All steps complete", r.all_steps_complete))
        checks.append(_check_item("Species coverage",
                                   r.species_coverage >= 0.8,
                                   f"{r.species_coverage:.0%}"))
        checks.append(_check_item("Conditions extracted",
                                   r.conditions_coverage >= 0.5,
                                   f"{r.conditions_coverage:.0%}"))
        checks.append(_check_item("No raw SMILES in narrative",
                                   r.smiles_in_narrative == 0,
                                   f"{r.smiles_in_narrative} found"
                                   if r.smiles_in_narrative else ""))

        checklist_html = '<div class="checklist">' + ''.join(checks) + '</div>'

        # Warnings
        warn_html = ""
        if r.warnings:
            warn_items = "".join(
                f'<div class="warn-item">{html_escape(w)}</div>'
                for w in r.warnings
            )
            warn_html = f'<div class="warn-box">{warn_items}</div>'

        # Narrative
        nar_html = ""
        if narrative:
            nar_html = (f'<div class="section-title">Narrative</div>'
                        f'<div class="narrative">{narrative}</div>')

        # Species table
        sp_html = ""
        if desc and desc.species:
            sp_html = (f'<div class="section-title">'
                       f'Species Registry ({len(desc.species)})</div>'
                       + _species_table_html(desc))

        # Steps table
        st_html = ""
        if desc and desc.steps:
            st_html = (f'<div class="section-title">'
                       f'Reaction Steps ({len(desc.steps)})</div>'
                       + _steps_table_html(desc))

        body_html = f"""
        {checklist_html}
        {warn_html}
        {nar_html}
        {sp_html}
        {st_html}
        """

    # Parse time
    time_str = f"{r.parse_time_ms:.0f} ms"

    return f"""
    <div class="card" style="border-left:4px solid {border}">
        <div class="card-header" onclick="this.parentElement.classList.toggle('open')">
            <span class="chevron">&#9654;</span>
            {status_badge}
            <span class="card-title">{html_escape(r.filename)}</span>
            {topo_badge} {ctype_badge} {steps_badge}
            <span class="badge badge-muted">{time_str}</span>
        </div>
        <div class="card-body">
            <div class="two-col">
                <div class="img-box">{img_html}</div>
                <div class="detail-box">{body_html}</div>
            </div>
        </div>
    </div>
    """


def _check_item(label: str, ok: bool, detail: str = "") -> str:
    """Render one quality check item."""
    icon = "&#10003;" if ok else "&#10007;"
    color = "#155724" if ok else "#dc3545"
    detail_span = f' <span class="check-detail">{html_escape(detail)}</span>' if detail else ""
    return (f'<div class="check-item">'
            f'<span style="color:{color};font-weight:700">{icon}</span> '
            f'{html_escape(label)}{detail_span}</div>')


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _html_report(report: AuditReport) -> str:
    """Generate a self-contained HTML audit report with scheme cards."""
    pass_pct = (report.pass_count / report.total_files * 100
                if report.total_files else 0)
    warn_pct = (report.warn_count / report.total_files * 100
                if report.total_files else 0)
    fail_pct = ((report.fail_count + report.error_count)
                / report.total_files * 100
                if report.total_files else 0)

    cards_html = "\n".join(
        _card_html(i, r) for i, r in enumerate(report.results)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Mode A Audit Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
         Helvetica, Arial, sans-serif; background: #f8f9fa; color: #212529;
         padding: 24px; max-width: 1440px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .subtitle {{ color: #6c757d; font-size: 0.9rem; margin-bottom: 20px; }}

  /* Summary */
  .summary-bar {{ display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
  .summary-card {{ background: #fff; border-radius: 8px; padding: 14px 20px;
                   box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                   min-width: 110px; text-align: center; }}
  .summary-card .num {{ font-size: 2rem; font-weight: 700; }}
  .summary-card .label {{ font-size: 0.75rem; color: #6c757d;
                          text-transform: uppercase; letter-spacing: 0.5px; }}
  .progress-bar {{ height: 10px; border-radius: 5px; overflow: hidden;
                   display: flex; margin-bottom: 24px; background: #e9ecef; }}
  .progress-bar .seg {{ height: 100%; }}

  /* Badges */
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 0.78rem; font-weight: 600; margin: 0 2px;
            vertical-align: middle; }}
  .badge-info {{ background: #d1ecf1; color: #0c5460; }}
  .badge-muted {{ background: #e9ecef; color: #6c757d; }}
  .badge-fail {{ background: #f8d7da; color: #721c24; }}

  /* Cards */
  .card {{ background: #fff; border-radius: 8px; margin-bottom: 10px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.06); overflow: hidden; }}
  .card-header {{ padding: 10px 16px; cursor: pointer; display: flex;
                  align-items: center; gap: 8px; user-select: none; }}
  .card-header:hover {{ background: #f1f3f5; }}
  .card-title {{ font-weight: 600; font-size: 0.92rem; font-family: monospace; }}
  .chevron {{ font-size: 0.7rem; color: #6c757d; transition: transform 0.15s;
              display: inline-block; width: 14px; }}
  .card.open .chevron {{ transform: rotate(90deg); }}
  .card-body {{ display: none; padding: 0 16px 16px 16px; }}
  .card.open .card-body {{ display: block; }}

  /* Two-column layout */
  .two-col {{ display: grid; grid-template-columns: minmax(250px,420px) 1fr;
              gap: 16px; margin-top: 8px; }}
  @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
  .img-box {{ text-align: center; }}
  .img-box img {{ max-width: 100%; border: 1px solid #dee2e6; border-radius: 4px; }}
  .no-img {{ background: #f8f9fa; border: 1px dashed #dee2e6; border-radius: 4px;
             padding: 40px 20px; color: #adb5bd; text-align: center;
             font-size: 0.85rem; }}

  /* Quality checklist */
  .checklist {{ display: flex; flex-wrap: wrap; gap: 2px 16px;
                margin-bottom: 10px; }}
  .check-item {{ font-size: 0.84rem; white-space: nowrap; }}
  .check-detail {{ color: #6c757d; }}

  /* Warnings */
  .warn-box {{ background: #fff3cd; border-radius: 4px; padding: 6px 10px;
               margin-bottom: 10px; }}
  .warn-item {{ font-size: 0.82rem; color: #856404; padding: 1px 0; }}
  .warn-item::before {{ content: "\\26A0 "; }}

  /* Sections */
  .section-title {{ font-size: 0.82rem; font-weight: 700; color: #495057;
                    text-transform: uppercase; letter-spacing: 0.4px;
                    margin: 12px 0 4px 0; }}
  .narrative {{ background: #f8f9fa; border-radius: 4px; padding: 10px;
                font-size: 0.85rem; line-height: 1.5; white-space: pre-wrap;
                max-height: 300px; overflow-y: auto; margin-bottom: 8px; }}

  /* Inner tables */
  .inner-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  .inner-table th {{ background: #495057; color: #fff; padding: 5px 8px;
                     font-size: 0.74rem; text-transform: uppercase;
                     letter-spacing: 0.3px; text-align: left; }}
  .inner-table td {{ padding: 4px 8px; border-bottom: 1px solid #e9ecef;
                     vertical-align: top; }}
  .inner-table tr:hover td {{ background: #f8f9fa; }}
  .mono {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.8rem; }}

  .footer {{ margin-top: 20px; font-size: 0.8rem; color: #6c757d; }}
</style>
</head>
<body>
<h1>Scheme Reader Audit: Mode A (Deterministic)</h1>
<p class="subtitle">{report.total_files} showcase files &middot;
   {report.total_time_ms:.0f} ms total parse time &middot;
   {os.path.basename(report.showcase_dir)}/</p>

<div class="summary-bar">
    <div class="summary-card">
        <div class="num" style="color:#155724">{report.pass_count}</div>
        <div class="label">Pass</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#856404">{report.warn_count}</div>
        <div class="label">Warn</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#721c24">{report.fail_count}</div>
        <div class="label">Fail</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#721c24">{report.error_count}</div>
        <div class="label">Error</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#004085">{pass_pct:.0f}%</div>
        <div class="label">Pass Rate</div>
    </div>
</div>

<div class="progress-bar">
    <div class="seg" style="width:{pass_pct}%;background:#28a745"></div>
    <div class="seg" style="width:{warn_pct}%;background:#ffc107"></div>
    <div class="seg" style="width:{fail_pct}%;background:#dc3545"></div>
</div>

{cards_html}

<div class="footer">
    <p><b>Quality checks:</b> Steps parsed, species found, topology correct,
    step count correct, all steps have reactants+products, species coverage
    &ge;80%, conditions extracted, no raw [SMILES:...] in narrative.</p>
</div>

<script>
// Expand all FAIL/WARN cards by default
document.querySelectorAll('.card').forEach(function(c) {{
    var hdr = c.querySelector('.card-header');
    if (hdr && (hdr.innerHTML.indexOf('FAIL') >= 0 ||
                hdr.innerHTML.indexOf('WARN') >= 0)) {{
        c.classList.add('open');
    }}
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit scheme_reader Mode A quality on showcase CDXMLs"
    )
    parser.add_argument(
        "showcase_dir", nargs="?",
        default=os.path.join(os.path.dirname(__file__),
                             "..", "experiments", "scheme_dsl", "showcase"),
        help="Directory of showcase CDXML files (default: experiments/scheme_dsl/showcase)"
    )
    parser.add_argument("--chemscript", action="store_true",
                        help="Use ChemScript for SMILES extraction")
    parser.add_argument("--render", action="store_true",
                        help="Render CDXMLs to PNG via ChemDraw COM "
                             "(requires ChemDraw closed)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of terminal report")
    parser.add_argument("--html",
                        help="Write HTML report to file")
    parser.add_argument("-o", "--output",
                        help="Write JSON output to file (implies --json)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print debug info during parsing")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable terminal colors")

    args = parser.parse_args()

    # Resolve path
    showcase_dir = os.path.abspath(args.showcase_dir)
    if not os.path.isdir(showcase_dir):
        print(f"Error: not a directory: {showcase_dir}", file=sys.stderr)
        sys.exit(1)

    report = audit_showcase(showcase_dir,
                            use_chemscript=args.chemscript,
                            verbose=args.verbose,
                            render=args.render)

    if args.html:
        html = _html_report(report)
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML audit report written to {args.html}")
    elif args.json or args.output:
        data = report.to_dict()
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Audit results written to {args.output}")
        else:
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
            print()
    else:
        _print_report(report, color=not args.no_color)

    # Exit code: 0 if all PASS/WARN, 1 if any FAIL/ERROR
    if report.fail_count + report.error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
