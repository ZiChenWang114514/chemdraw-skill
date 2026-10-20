"""
ELN CSV Parser — Findmolecule ELN export file parser.

Parses semicolon-delimited CSV exports from Findmolecule ELN into structured
dataclasses.  The CSV format uses @TYPE rows to delimit sections (REACTANT,
SOLVENT, PRODUCT, ANALYSIS).

This module is pure stdlib — no external dependencies.

Originally part of procedure_writer.py; extracted into the package so that
eln_enrichment.py and reaction_parser.py can import it without depending on
private root-level scripts.
"""

import csv
import html as html_mod
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ReagentInfo:
    name: str
    mass: str
    mmol: str
    equiv: str
    mw: float
    is_substrate: bool
    supplier: str
    volume: str


@dataclass
class SolventInfo:
    name: str
    volume: str
    concentration: str


@dataclass
class ProductInfo:
    name: str
    mw: float
    theoretical_mass: str
    obtained_mass: str
    yield_pct: str


@dataclass
class LCMSFileInfo:
    path: str
    filename: str
    category: str       # "tracking", "workup", "purification", "final"
    sort_key: float     # numeric key for chronological sorting
    report: Optional[object] = None
    group_prefix: Optional[str] = None     # tracking group prefix
    method_variant: Optional[str] = None   # filename-derived method hint


@dataclass
class ExperimentData:
    experiment_name: str
    labbook_name: str
    procedure_html: str
    procedure_text: str
    reaction_type: str
    start_date: str
    reactants: List[ReagentInfo] = field(default_factory=list)
    solvents: List[SolventInfo] = field(default_factory=list)
    product: Optional[ProductInfo] = None
    lcms_files: List[LCMSFileInfo] = field(default_factory=list)
    nmr_pdfs: List[str] = field(default_factory=list)
    nmr_data: List[str] = field(default_factory=list)
    sm_mass: Optional[float] = None       # CSV-derived MW (fallback)
    product_mass: Optional[float] = None  # CSV-derived MW (fallback)
    cdx_path: Optional[str] = None
    rxn_path: Optional[str] = None


# ---------------------------------------------------------------------------
# HTML / text utilities
# ---------------------------------------------------------------------------

def strip_html(html_str: str) -> str:
    """Strip HTML tags and convert to plain text."""
    text = re.sub(r'<br\s*/?>', '\n', html_str)
    text = re.sub(r'</p>\s*<p[^>]*>', '\n\n', text)
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<img[^>]*>', '', text)
    # Remove all remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities (covers &nbsp; &lt; &gt; &amp; &deg; &#nnn; etc.)
    text = html_mod.unescape(text)
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_procedure_body(full_text: str) -> str:
    """Extract the procedure portion, cutting off literature references."""
    # "Reference:" marks start of literature references
    idx = full_text.find('Reference:')
    if idx > 0:
        body = full_text[:idx].strip()
    else:
        body = full_text.strip()
    # Also cut Chinese text blocks (common in patent references)
    m = re.search(r'[\u4e00-\u9fff]', body)
    if m and m.start() > 50:
        body = body[:m.start()].strip()
    return body


# ---------------------------------------------------------------------------
# CSV parser
# ---------------------------------------------------------------------------

def parse_eln_csv(csv_path: str) -> Optional[ExperimentData]:
    """Parse a Findmolecule ELN CSV export.

    Parameters
    ----------
    csv_path : str
        Path to the semicolon-delimited CSV file.

    Returns
    -------
    ExperimentData or None if the file has fewer than 2 rows.
    """
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';', quotechar='"')
        rows = list(reader)

    if len(rows) < 2:
        return None

    # Row 0: metadata headers, Row 1: metadata values
    meta_headers = rows[0]
    meta_values = rows[1]
    metadata: Dict[str, str] = {}
    for h, v in zip(meta_headers, meta_values):
        metadata[h] = v

    # Parse @TYPE sections
    sections: Dict[str, list] = {
        'REACTANT': [], 'SOLVENT': [], 'PRODUCT': [], 'ANALYSIS': []
    }
    current_headers: List[str] = []

    for row in rows[2:]:
        if not row:
            continue
        if row[0] == '@TYPE':
            current_headers = row[1:]
            continue
        type_name = row[0]
        if type_name in sections:
            data: Dict[str, str] = {}
            for i, h in enumerate(current_headers):
                if i + 1 < len(row):
                    data[h] = row[i + 1]
                else:
                    data[h] = ''
            sections[type_name].append(data)

    # Build ExperimentData
    procedure_html = metadata.get('PROCEDURE', '')
    procedure_text = extract_procedure_body(strip_html(procedure_html))

    exp = ExperimentData(
        experiment_name=metadata.get('EXPERIENCE_NAME', ''),
        labbook_name=metadata.get('LABBOOK_NAME', ''),
        procedure_html=procedure_html,
        procedure_text=procedure_text,
        reaction_type=metadata.get('EXPERIENCE_TYPE_NAME', ''),
        start_date=metadata.get('STARTED_ON', ''),
    )

    # Reactants
    for r in sections['REACTANT']:
        mw_str = r.get('MOL_WEIGHT', '0')
        try:
            mw = float(mw_str) if mw_str else 0.0
        except ValueError:
            mw = 0.0
        reagent = ReagentInfo(
            name=r.get('REACTANT', '').strip(),
            mass=r.get('MASS', ''),
            mmol=r.get('MMOL', ''),
            equiv=r.get('EQUIV', ''),
            mw=mw,
            is_substrate=r.get('SUBSTRATE', '').lower() == 'true',
            supplier=r.get('SOURCE_SUPPLIER', ''),
            volume=r.get('VOLUME', ''),
        )
        exp.reactants.append(reagent)

    # Solvents
    for s in sections['SOLVENT']:
        solvent = SolventInfo(
            name=s.get('SOLVENT', ''),
            volume=s.get('VOLUME', ''),
            concentration=s.get('CONCENTRATION', ''),
        )
        exp.solvents.append(solvent)

    # Product
    for p in sections['PRODUCT']:
        mw_str = p.get('MOL_WEIGHT', '0')
        try:
            mw = float(mw_str) if mw_str else 0.0
        except ValueError:
            mw = 0.0
        exp.product = ProductInfo(
            name=p.get('PRODUCT_NAME', ''),
            mw=mw,
            theoretical_mass=p.get('MASS', ''),
            obtained_mass=p.get('MASS OBTAINED', ''),
            yield_pct=p.get('YIELD', ''),
        )

    # SM mass from substrate row (pick the largest-MW substrate,
    # since small-MW reagents like HCl can also be marked as substrate)
    substrate_mws = [r.mw for r in exp.reactants if r.is_substrate and r.mw > 50]
    if substrate_mws:
        exp.sm_mass = max(substrate_mws)

    # Product mass — use CSV MW directly
    if exp.product and exp.product.mw > 0:
        exp.product_mass = exp.product.mw

    return exp
