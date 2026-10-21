#!/usr/bin/env python3
"""
scheme_refine.py — Tier 2 LLM-based refinement of scheme_reader output.

Takes a SchemeDescription (Tier 1 deterministic output) and produces a refined
version with corrections from an LLM.  The module:

1. Generates a structured prompt with the Tier 1 JSON + context.
2. Accepts a correction dict (from any LLM — Claude API, local model, etc.).
3. Applies corrections to produce a refined SchemeDescription.

The correction format is designed to be simple and LLM-friendly:

    {
        "content_type": "synthesis",       # override content type
        "topology": "linear",             # override topology
        "species_corrections": {
            "species_5": {"text_category": "condition_ref"},
            "species_8": {"text_category": "citation"},
        },
        "narrative_override": "...",       # replace narrative entirely
        "notes": "..."                     # free-form LLM reasoning
    }

CLI:
    # Generate prompt for LLM review
    python -m cdxml_toolkit.scheme_refine prompt scheme.json

    # Apply corrections
    python -m cdxml_toolkit.scheme_refine apply scheme.json corrections.json -o refined.json

Python API:
    from cdxml_toolkit.perception.scheme_refine import generate_prompt, apply_corrections
    prompt = generate_prompt(desc)
    refined = apply_corrections(desc, corrections_dict)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from .scheme_reader import SchemeDescription, SpeciesRecord, ScopeEntry


# ---------------------------------------------------------------------------
# Aligned IUPAC name enrichment
# ---------------------------------------------------------------------------

def enrich_aligned_names(desc: SchemeDescription, verbose: bool = False) -> int:
    """Replace canonical IUPAC names with aligned alternatives per step.

    For each step, finds reactant→product SMILES pairs, calls
    ``find_aligned_names()``, and overwrites ``iupac_name`` with the
    best enumerated name regardless of alignment quality.  ALIGNED and
    SEMI-ALIGNED pairs naturally outrank UNALIGNED (via higher
    similarity score), but even UNALIGNED names are always used —
    any IUPAC name is better than showing raw SMILES.

    Also stores transformation diffs in ``desc._alignment_diffs`` for
    display in the narrative.

    Requires ``cdxml_toolkit.aligned_namer`` (which in turn requires
    ChemScript).  Returns 0 silently if the module is unavailable.

    Parameters
    ----------
    desc : SchemeDescription
        Parsed scheme with species SMILES populated.
    verbose : bool
        Print alignment progress to stderr.

    Returns
    -------
    int
        Number of species whose ``iupac_name`` was updated.
    """
    try:
        from ..naming.aligned_namer import find_aligned_names, format_name_diff
    except Exception:
        return 0

    updated: Dict[str, float] = {}   # species_id → best_similarity so far
    n_updated = 0

    # Store transformation diffs: (reactant_id, product_id) → diff string
    if not hasattr(desc, '_alignment_diffs'):
        desc._alignment_diffs = {}

    for step in desc.steps:
        # Collect reactant and product species with SMILES
        reactants = []
        for rid in step.reactant_ids:
            sp = desc.species.get(rid)
            if sp and sp.smiles and sp.element_type == "fragment":
                reactants.append(sp)
        products = []
        for pid in step.product_ids:
            sp = desc.species.get(pid)
            if sp and sp.smiles and sp.element_type == "fragment":
                products.append(sp)

        if not reactants or not products:
            continue

        # Pair each reactant with each product
        for r_sp in reactants:
            for p_sp in products:
                try:
                    result = find_aligned_names(r_sp.smiles, p_sp.smiles,
                                                verbose=verbose)
                except Exception:
                    continue

                quality = result.alignment_quality

                # Use best_similarity as priority — ALIGNED/SEMI-ALIGNED
                # (sim >= 0.5) naturally outranks UNALIGNED (sim < 0.5),
                # but UNALIGNED names are still always better than SMILES.
                sim = result.best_similarity
                # Update reactant name if this alignment is better
                if (result.best_sm_name
                        and sim > updated.get(r_sp.id, -1)):
                    r_sp.iupac_name = result.best_sm_name
                    updated[r_sp.id] = sim
                    n_updated += 1

                # Update product name if this alignment is better
                if (result.best_prod_name
                        and sim > updated.get(p_sp.id, -1)):
                    p_sp.iupac_name = result.best_prod_name
                    updated[p_sp.id] = sim
                    n_updated += 1

                # Store the transformation diff for this aligned pair
                if result.best_sm_name and result.best_prod_name:
                    try:
                        diff_str = format_name_diff(
                            result.best_sm_name, result.best_prod_name)
                        if diff_str and diff_str != "(identical)":
                            desc._alignment_diffs[
                                (r_sp.id, p_sp.id)] = diff_str
                    except Exception:
                        pass

                if verbose:
                    print(f"  Aligned [{quality}] {r_sp.id} \u2194 {p_sp.id}: "
                          f"sim={sim:.2f}", file=sys.stderr)
                    print(f"    SM:   {result.best_sm_name}",
                          file=sys.stderr)
                    print(f"    Prod: {result.best_prod_name}",
                          file=sys.stderr)

    # Second pass: name R-group species by replacing * with H and naming
    # the "core" structure.  Any IUPAC name is better than a raw formula
    # or SMILES in the narrative.
    n_updated += _name_rgroup_cores(desc, verbose=verbose)

    return n_updated


# Regex matching R-group tokens in SMILES: [R], [R'], [R3], [OR'], [Het],
# [COOR''], [F,Cl,Br,I], compound-label brackets like [2.21], [(R,S,S)-5.2]
_RGROUP_TOKEN_RE = re.compile(
    r'\[R\d*\'*\]'          # [R], [R'], [R3], [R'']
    r'|\[OR\'*\]'           # [OR'], [OR'']
    r'|\[Het\]'             # [Het]
    r'|\[COOR\'*\]'         # [COOR''], [COOR']
    r'|\[F,Cl,Br,I\]'      # halide variable
)

# ChemDraw generic group abbreviations that prevent SMILES parsing.
# When a SMILES contains these, the species is a generic methodology scheme
# (protecting groups, leaving groups, etc.) and cannot be named.
_CHEMDRAW_ABBREV_RE = re.compile(
    r'\[G\]'                # generic group
    r'|\[LG\]'              # leaving group
    r'|\[P\d*\'*\]'         # protecting group [P], [P1'], [P']
    r'|\[EWG\]'             # electron-withdrawing group
    r'|\[EDG\]'             # electron-donating group
    r'|\[Nu\]'              # nucleophile
    r'|\[E\+?\]'            # electrophile
    r'|\[Base\]'            # base
)

# Tokens that are just bare R-group labels (entire SMILES is the token)
_BARE_RGROUP_RE = re.compile(
    r'^\[R\d*\'*\]$'
    r'|^\[OR\'*\]$'
    r'|^\[Het\]$'
    r'|^\[COOR\'*\]$'
    r'|^\[F,Cl,Br,I\]$'
    r'|^\*$'
)


def _name_rgroup_cores(desc: SchemeDescription,
                       verbose: bool = False) -> int:
    """Name species that contain R-group atoms by naming the H-core.

    Handles both RDKit notation (``*``) and ChemScript notation
    (``[R]``, ``[R']``, ``[R3]``, ``[OR']``, ``[Het]``, etc.).

    Replaces R-group tokens with ``[H]``, canonicalises with RDKit,
    then calls ChemScript ``get_name()`` on the resulting real molecule.
    The IUPAC name is stored as ``"<core name> derivative"`` (for 2+ R)
    or ``"R-substituted <core name>"`` (for 1 R).

    Returns the number of species updated.
    """
    try:
        from rdkit import Chem
        from ..chemdraw.chemscript_bridge import ChemScriptBridge
        bridge = ChemScriptBridge()
    except Exception:
        return 0

    n = 0
    for sid, sp in desc.species.items():
        if getattr(sp, 'iupac_name', None):
            continue  # already named
        smiles = sp.smiles
        if not smiles:
            continue

        # Check for R-group tokens (both * and [R]-style) and
        # ChemDraw generic abbreviations ([P], [G], [LG], etc.)
        has_star = '*' in smiles
        rgroup_matches = _RGROUP_TOKEN_RE.findall(smiles)
        abbrev_matches = _CHEMDRAW_ABBREV_RE.findall(smiles)
        if not has_star and not rgroup_matches and not abbrev_matches:
            continue

        try:
            # Bare R-group atom: just show the label directly
            stripped = smiles.strip()
            if _BARE_RGROUP_RE.match(stripped):
                # Show as-is but cleaned up: [R] -> R, [R3] -> R3, etc.
                label = stripped.strip('[]')
                if label == '*':
                    label = 'R'
                sp.iupac_name = label
                n += 1
                continue

            # Replace all R-group and abbreviation tokens with [H]
            core_smiles = smiles
            for token in rgroup_matches:
                core_smiles = core_smiles.replace(token, '[H]')
            for token in abbrev_matches:
                core_smiles = core_smiles.replace(token, '[H]')
            if has_star:
                core_smiles = core_smiles.replace('*', '[H]')

            mol = Chem.MolFromSmiles(core_smiles)
            if mol is None:
                # Can't parse even after stripping — label as generic
                sp.iupac_name = "generic intermediate"
                n += 1
                if verbose:
                    print(f"  R-group core: {sid} -> generic intermediate "
                          f"(unparseable: {smiles[:50]})", file=sys.stderr)
                continue

            core_canon = Chem.MolToSmiles(mol)
            core_name = bridge.get_name(core_canon)
            if not core_name:
                # Named core failed — still better than raw SMILES
                sp.iupac_name = "generic intermediate"
                n += 1
                continue

            n_rgroups = (len(rgroup_matches) + len(abbrev_matches)
                         + smiles.count('*'))
            if n_rgroups == 1:
                sp.iupac_name = f"R-substituted {core_name}"
            else:
                sp.iupac_name = f"{core_name} derivative"
            n += 1

            if verbose:
                print(f"  R-group core: {sid} -> {sp.iupac_name}",
                      file=sys.stderr)
        except Exception:
            continue

    return n


# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------

def generate_prompt(desc: SchemeDescription,
                    image_path: Optional[str] = None) -> str:
    """Generate a structured prompt for LLM refinement.

    Parameters
    ----------
    desc : SchemeDescription
        Tier 1 deterministic output.
    image_path : str, optional
        Path to rendered scheme image (for vision models).

    Returns
    -------
    str
        Structured prompt text.
    """
    parts = []

    parts.append("# Scheme Refinement Task\n")
    parts.append("You are reviewing the output of a deterministic chemical "
                 "scheme parser. Your job is to identify and correct any "
                 "misclassifications in the structured output.\n")

    if image_path:
        parts.append(f"**Rendered image**: {image_path}\n")

    parts.append("## Tier 1 Parser Output\n")
    parts.append(f"- **Topology**: {desc.topology}")
    parts.append(f"- **Content type**: {desc.content_type or 'unknown'}")
    parts.append(f"- **Steps**: {desc.num_steps}")
    parts.append(f"- **Species**: {len(desc.species)}\n")

    # Species summary table
    parts.append("### Species Registry\n")
    parts.append("| ID | Type | Category | Label | Name (first 60 chars) | "
                 "SMILES (first 40 chars) | MW |")
    parts.append("|" + "|".join(["---"] * 7) + "|")
    for sp_id, sp in desc.species.items():
        name_short = (sp.name or "")[:60].replace("\n", " / ")
        smi_short = (sp.smiles or "")[:40]
        parts.append(
            f"| {sp_id} | {sp.element_type} | {sp.text_category or '-'} | "
            f"{sp.label or '-'} | {name_short} | {smi_short} | "
            f"{sp.mw or '-'} |"
        )

    # Steps summary
    parts.append("\n### Reaction Steps\n")
    for step in desc.steps:
        r_ids = ", ".join(step.reactant_ids) or "(none)"
        p_ids = ", ".join(step.product_ids) or "(none)"
        rg_ids = ", ".join(step.reagent_ids) or "(none)"
        parts.append(
            f"- **Step {step.step_index}**: "
            f"R=[{r_ids}] → P=[{p_ids}] | "
            f"reagents=[{rg_ids}] | "
            f"conditions={step.conditions} | "
            f"yield={step.yield_text or '-'} | "
            f"arrow={step.arrow_style}"
        )

    # Narrative
    parts.append(f"\n### Current Narrative\n{desc.narrative}\n")

    # Instructions
    parts.append("## Your Task\n")
    parts.append("Review the above and return a JSON correction object with "
                 "any needed fixes. Only include fields that need changing.\n")
    parts.append("Correction format:\n```json")
    parts.append(json.dumps({
        "content_type": "<correct type: synthesis | sar_design | "
                        "biological_pathway | target_array | "
                        "literature_comparison | composite | investigation>",
        "topology": "<correct topology if wrong>",
        "species_corrections": {
            "<species_id>": {
                "text_category": "<condition_ref | citation | bioactivity | "
                                 "chemical | conditions_block>"
            }
        },
        "narrative_override": "<better narrative if the current one is wrong>",
        "notes": "<your reasoning>"
    }, indent=2))
    parts.append("```\n")
    parts.append("If the Tier 1 output is correct, return: `{}`\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Apply corrections
# ---------------------------------------------------------------------------

def apply_corrections(desc: SchemeDescription,
                      corrections: Dict[str, Any]) -> SchemeDescription:
    """Apply LLM corrections to a SchemeDescription.

    Returns a new SchemeDescription with corrections applied.
    The original is not modified.

    Parameters
    ----------
    desc : SchemeDescription
        Tier 1 deterministic output.
    corrections : dict
        LLM correction dict (see module docstring for format).

    Returns
    -------
    SchemeDescription
        Refined description.
    """
    # Deep copy via JSON round-trip
    d = desc.to_dict()
    refined = SchemeDescription.from_dict(d)

    if not corrections:
        return refined

    # Apply content type override
    if "content_type" in corrections:
        refined.content_type = corrections["content_type"]

    # Apply topology override
    if "topology" in corrections:
        refined.topology = corrections["topology"]

    # Apply species corrections
    sp_corr = corrections.get("species_corrections", {})
    for sp_id, fixes in sp_corr.items():
        sp = refined.species.get(sp_id)
        if sp is None:
            continue
        if "text_category" in fixes:
            sp.text_category = fixes["text_category"]
        if "name" in fixes:
            sp.name = fixes["name"]
        if "smiles" in fixes:
            sp.smiles = fixes["smiles"]
        if "label" in fixes:
            sp.label = fixes["label"]

    # Apply narrative override
    if "narrative_override" in corrections:
        refined.narrative = corrections["narrative_override"]
    else:
        # Regenerate narrative with corrected data
        from .scheme_reader import _generate_narrative
        refined.narrative = _generate_narrative(refined)

    return refined


# ---------------------------------------------------------------------------
# Batch refinement: apply a corrections file to multiple schemes
# ---------------------------------------------------------------------------

def load_corrections_file(path: str) -> Dict[str, Dict[str, Any]]:
    """Load a corrections file mapping source filenames to corrections.

    Format:
        {
            "oleObject1.cdxml": { ... corrections ... },
            "oleObject2.cdxml": { ... corrections ... },
        }
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def refine_scheme(desc: SchemeDescription,
                  corrections: Optional[Dict[str, Any]] = None) -> SchemeDescription:
    """Refine a scheme description.

    If corrections are provided, applies them.
    Otherwise returns the description unchanged.
    """
    if corrections:
        return apply_corrections(desc, corrections)
    return desc


# ---------------------------------------------------------------------------
# LLM-quality narrative generation
# ---------------------------------------------------------------------------

# Reagent -> reaction type mapping (pattern, reaction_name, notes)
_REACTION_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # Pd-catalysed cross-couplings
    (re.compile(r"Pd.*(?:dba|PPh3|dppf|dppp|OAc|Cl2)", re.I),
     None, "Pd-catalysed"),  # refined below
    # Buchwald-Hartwig: Pd + amine + base
    (re.compile(r"(?:BINAP|XPhos|SPhos|DavePhos|RuPhos|BrettPhos|JohnPhos"
                r"|XantPhos|t-?Bu[23]?P)", re.I),
     "Buchwald-Hartwig amination", "Pd/ligand system"),
    # Suzuki: boronic acid
    (re.compile(r"B\(OH\)2|boronic|Bpin|BF3K|potassium trifluoroborate", re.I),
     "Suzuki coupling", "boronic acid coupling partner"),
    # Sonogashira: alkyne + Pd/Cu
    (re.compile(r"(?:Sonogashira|CuI.*Pd|PdCl2.*CuI)", re.I),
     "Sonogashira coupling", ""),
    # Heck
    (re.compile(r"(?:Heck|acrylate.*Pd|Pd.*vinyl)", re.I),
     "Heck reaction", ""),
    # NBS bromination
    (re.compile(r"\bNBS\b", re.I),
     "NBS bromination", "electrophilic aromatic bromination"),
    # Boc deprotection
    (re.compile(r"\bTFA\b.*(?:DCM|CH2Cl2)|HCl.*(?:dioxane|Et2O|MeOH)|"
                r"Boc.*(?:deprot|remov)", re.I),
     "Boc deprotection", "acidic removal of tert-butoxycarbonyl"),
    # Cbz deprotection / hydrogenolysis
    (re.compile(r"H2.*Pd/?C|Pd/?C.*H2|hydrogenolysis|Cbz.*deprot", re.I),
     "hydrogenolysis", "Pd/C-catalysed H2 reduction"),
    # Amide coupling
    (re.compile(r"\b(?:HATU|HBTU|EDCI|EDC|DCC|T3P|COMU|PyBOP|TBTU|HOBt"
                r"|HOAt|TFFH|SOCl2.*amine|CDI)\b", re.I),
     "amide coupling", "peptide bond formation"),
    # Reductive amination
    (re.compile(r"NaBH(?:3CN|OAc|\(OAc\)3)|reductive amin", re.I),
     "reductive amination", "imine formation + reduction"),
    # Mitsunobu
    (re.compile(r"(?:DIAD|DEAD|DMAP).*PPh3|Mitsunobu", re.I),
     "Mitsunobu reaction", "stereoinversion of alcohol"),
    # Grignard
    (re.compile(r"\bMgBr\b|\bMgCl\b|Grignard", re.I),
     "Grignard addition", "organomagnesium addition"),
    # Wittig / HWE
    (re.compile(r"(?:Wittig|ylide|PPh3.*CHO|HWE|Horner)", re.I),
     "Wittig/HWE olefination", ""),
    # SNAr
    (re.compile(r"(?:SNAr|nucleophilic aromatic|K2CO3.*DMF|Cs2CO3.*DMF"
                r"|NaH.*DMF)", re.I),
     None, ""),  # needs context to distinguish from Buchwald
    # Reduction (general)
    (re.compile(r"\bLiAlH4\b|LiAlH\(OtBu\)3|NaBH4|DIBAL", re.I),
     "reduction", "hydride reduction"),
    # Oxidation
    (re.compile(r"\b(?:mCPBA|Dess.?Martin|Swern|TEMPO|PDC|PCC|Jones)\b", re.I),
     "oxidation", ""),
    # Halogenation
    (re.compile(r"\bNCS\b", re.I),
     "NCS chlorination", "electrophilic aromatic chlorination"),
    # Alkylation
    (re.compile(r"\b(?:NaH|K2CO3|Cs2CO3)\b.*(?:alkyl|benzyl|methyl|BnBr"
                r"|MeI|allyl)", re.I),
     "alkylation", "base-mediated alkylation"),
    # Ring closure / cyclisation
    (re.compile(r"(?:exo-trig|exo-dig|endo-trig|endo-dig|cycliz|ring.?clos"
                r"|lacton)", re.I),
     "cyclisation", "intramolecular ring closure"),
]


def _build_reaction_smiles(step, species: Dict[str, SpeciesRecord]) -> Optional[str]:
    """Build reaction SMILES from a step's species references.

    Constructs ``R1.R2.reagent1>>P1`` from the step's reactant, reagent,
    and product species.  Only species with SMILES are included.

    Returns None if either side has no SMILES.
    """
    lhs = []
    for sid in list(step.reactant_ids) + list(step.reagent_ids):
        sp = species.get(sid)
        if sp and sp.smiles:
            lhs.append(sp.smiles)
    rhs = []
    for sid in step.product_ids:
        sp = species.get(sid)
        if sp and sp.smiles:
            rhs.append(sp.smiles)
    if not lhs or not rhs:
        return None
    return ".".join(lhs) + ">>" + ".".join(rhs)


def _classify_reaction(condition_text_raw: List[str],
                       reagent_species: List[SpeciesRecord],
                       desc: SchemeDescription,
                       ml_data: Optional[Dict] = None) -> Optional[str]:
    """Try to classify a reaction step from its conditions/reagents.

    When *ml_data* is supplied (from RXN Insight via ``enrich_steps``), its
    ``reaction_name`` is preferred.  The regex heuristic still runs as a
    cross-check and fallback.
    """
    # --- ML classification (preferred when available) ---
    ml_name = None
    if ml_data:
        ml_name = ml_data.get("reaction_name") or None
        # rxn-insight sometimes returns generic class as name; ignore those
        if ml_name and ml_name.lower() in ("unrecognized", "", "other"):
            ml_name = None

    # Combine all text for pattern matching
    all_text = " ".join(condition_text_raw)
    for sp in reagent_species:
        if sp.name:
            all_text += " " + sp.name
        if sp.smiles:
            all_text += " " + sp.smiles

    # Check for Pd + specific ligand patterns first (Buchwald vs Suzuki)
    has_pd = bool(re.search(r"Pd", all_text))
    has_boronic = bool(re.search(r"B\(OH\)2|boronic|Bpin", all_text, re.I))
    has_amine = any(
        (sp.smiles and re.search(r"N[^a-z]|NH", sp.smiles or ""))
        or (sp.name and re.search(
            r"morpholin|piperid|pyrrolid|piperazin|amine|aniline|indol",
            sp.name or "", re.I))
        for sp in reagent_species
    )
    has_coupling_ligand = bool(re.search(
        r"BINAP|XPhos|SPhos|DavePhos|RuPhos|BrettPhos|dppf|dppp", all_text, re.I))

    regex_name = None
    if has_pd and has_boronic:
        regex_name = "Suzuki coupling"
    elif has_pd and has_coupling_ligand and has_amine:
        regex_name = "Buchwald-Hartwig amination"
    elif has_pd and has_coupling_ligand:
        regex_name = "Pd-catalysed cross-coupling"
    else:
        # Pattern-based classification
        for pat, name, _notes in _REACTION_PATTERNS:
            if pat.search(all_text) and name:
                regex_name = name
                break
        # Fallback: check if it's a coupling with base
        if regex_name is None and has_pd:
            regex_name = "Pd-catalysed transformation"

    # Prefer ML name when available; regex serves as cross-check
    if ml_name and regex_name:
        return regex_name  # trust regex for medchem-specific names
    if regex_name:
        return regex_name
    if ml_name:
        return ml_name
    return None


# Compound label that ended up as SMILES (e.g. [2.21], [(R,S,S)-5.2], [5.1])
_COMPOUND_LABEL_RE = re.compile(
    r'^\[[\d(][\w.,\-()/ ]*\]$'
)


def _species_display(sp: SpeciesRecord) -> str:
    """Format a species for narrative display.

    Priority: label > IUPAC name > common name > formula > SMILES.
    SMILES is only shown as a fallback when no readable name is available.
    Compound labels disguised as SMILES (e.g. ``[2.21]``) are shown as
    ``compound 2.21`` instead of ``[SMILES: ...]``.
    """
    parts = []
    if sp.label:
        parts.append(f"compound {sp.label}")
        # Add IUPAC name as parenthetical when available
        iupac = getattr(sp, "iupac_name", None)
        if iupac:
            parts.append(f"({iupac})")
    elif getattr(sp, "iupac_name", None):
        parts.append(sp.iupac_name)
    elif sp.name and len(sp.name) < 40:
        parts.append(sp.name)
    elif sp.formula:
        parts.append(sp.formula)
    # Only show SMILES as last-resort identification when no readable name
    has_readable_name = bool(parts)
    if sp.smiles and not has_readable_name:
        # Detect compound labels disguised as SMILES
        if _COMPOUND_LABEL_RE.match(sp.smiles):
            label_text = sp.smiles.strip('[]')
            parts.append(f"compound {label_text}")
        else:
            parts.append(f"[SMILES: {sp.smiles}]")
    if sp.mw and not sp.label:
        parts.append(f"[MW {sp.mw:.1f}]")
    return " ".join(parts) if parts else sp.id


def _parse_step_reagents(step, species: Dict[str, SpeciesRecord]) -> Dict[str, list]:
    """Decompose all reagent and condition information into categorised bins.

    Collects data from:
      1. Fragment reagent species (drawn structures above/below arrow)
      2. Text reagent species (multi-line text blocks with reagent names,
         solvents, conditions, and workup instructions)
      3. Parsed ``step.conditions`` (extracted physical conditions)

    Returns a dict with keys:
        ``catalysts``   – [(display_name, equiv_or_loading), ...]
        ``ligands``     – [(display_name, equiv_or_loading), ...]
        ``bases``       – [(display_name, equiv_or_loading), ...]
        ``reagents``    – [(display_name, equiv_or_loading), ...]  (catch-all)
        ``solvents``    – [display_name, ...]
        ``conditions``  – [str, ...]  (temperature, time, atmosphere, ...)
        ``workup``      – [str, ...]  (quench/workup instructions)
    """
    from ..resolve.reagent_db import get_reagent_db
    from .reaction_parser import _is_condition_token
    db = get_reagent_db()

    cats: Dict[str, list] = {
        "catalysts": [], "ligands": [], "bases": [], "reagents": [],
        "solvents": [], "conditions": [], "workup": [],
    }
    # Role → bin mapping
    _ROLE_BIN = {
        "catalyst": "catalysts",
        "ligand": "ligands",
        "base": "bases",
        "lewis_acid": "catalysts",
        "solvent": "solvents",
        "coupling_reagent": "reagents",
        "reducing_agent": "reagents",
        "reductant": "reagents",
        "oxidant": "reagents",
        "halogenating_agent": "reagents",
        "fluorinating_agent": "reagents",
        "borylating_agent": "reagents",
        "activating_agent": "reagents",
        "deprotecting_agent": "reagents",
        "protecting_group": "reagents",
        "drying_agent": "reagents",
        "acid": "reagents",
        "additive": "reagents",
        "reagent": "reagents",
    }

    # Track names we've already added (avoid duplicates)
    _seen_names: set = set()

    def _add_token(raw_token: str) -> None:
        """Classify a single token and add to the right bin."""
        token = raw_token.strip()
        if not token:
            return

        # Skip yield tokens (e.g. "72%", "quant.", "95% yield")
        if re.match(r"^\d+\.?\d*\s*%", token) or \
           re.match(r"^quant\.?$", token, re.IGNORECASE):
            return

        # Skip reaction name labels (e.g. "Rieche formylation", "Mitsunobu")
        _rxn_name_patterns = re.compile(
            r"^(?:Rieche|Mitsunobu|Swern|Wittig|Grignard|Heck|Suzuki|"
            r"Buchwald|Sonogashira|Negishi|Stille|Kumada|Chan.Lam|"
            r"Ullmann|Goldberg|Appel|Gabriel|Finkelstein|"
            r"Curtius|Arndt.Eistert|Barton|Dess.Martin|"
            r"Williamson|Fischer|Mannich|Strecker|Reformatsky)\b",
            re.IGNORECASE)
        if _rxn_name_patterns.search(token):
            return

        # Strip equiv/loading annotations for lookup, but preserve for display
        equiv_str = ""
        m = re.match(r"^(.+?)\s*\((\d+\.?\d*\s*(?:eq\.?|equiv\.?|mol\s*%|cat\.))\)\s*$",
                     token, re.IGNORECASE)
        if m:
            token_clean = m.group(1).strip()
            equiv_str = m.group(2).strip()
        else:
            token_clean = token

        # Normalise key for lookup
        lookup_key = token_clean.lower().strip()
        if lookup_key in _seen_names:
            return
        _seen_names.add(lookup_key)

        # Check if it's a physical condition
        if _is_condition_token(token_clean):
            cats["conditions"].append(token_clean)
            return

        # Temperature range patterns not caught by _is_condition_token:
        #   "-78 to RT", "0 C to RT", "-78 C to rt", "-78°C to RT"
        if re.match(
            r"^-?\d+\s*[°\u00b0]?\s*C?\s+to\s+(?:r\.?t\.?|-?\d+\s*[°\u00b0]?\s*C?)\s*$",
            token_clean, re.IGNORECASE
        ):
            cats["conditions"].append(token_clean)
            return

        # Workup detection
        if re.match(r"^then\b", token_clean, re.IGNORECASE):
            cats["workup"].append(token)
            return

        # Reagent DB lookup
        role = db.role_for_name(lookup_key)
        entry = db.entry_for_name(lookup_key)
        display = entry.get("display", token_clean) if entry else token_clean

        if role:
            bin_name = _ROLE_BIN.get(role, "reagents")
            if bin_name == "solvents":
                cats["solvents"].append(display)
            else:
                cats[bin_name].append((display, equiv_str))
        else:
            # Unknown — check if it looks like a solvent ratio ("dioxane/H2O (3:1)")
            if re.match(r"^[A-Za-z0-9,\-]+(/[A-Za-z0-9,\-]+)+(\s*\(\d+:\d+\))?$",
                        token_clean):
                cats["solvents"].append(token_clean)
            # "cat." usually means catalytic amount
            elif equiv_str and "cat" in equiv_str.lower():
                cats["reagents"].append((display, equiv_str))
            # Has a loading → likely a reagent
            elif equiv_str:
                cats["reagents"].append((display, equiv_str))
            else:
                # Genuinely unknown — treat as reagent
                cats["reagents"].append((display, ""))

    # 1. Fragment reagent species (drawn structures)
    for rid in step.reagent_ids:
        sp = species.get(rid)
        if not sp:
            continue
        if sp.element_type == "fragment":
            # Build best display name: label > IUPAC > reagent_db display > name > SMILES
            display_name = None
            role = None

            # Try reagent_db by name first
            if sp.name:
                role = db.role_for_name(sp.name.lower())
                entry = db.entry_for_name(sp.name.lower())
                if entry:
                    display_name = entry.get("display", sp.name)

            # Try reagent_db by SMILES
            if not role and sp.smiles:
                role = db.role_for_smiles(sp.smiles)
                sr = db.smiles_role_display(sp.smiles)
                if sr:
                    if not display_name:
                        display_name = sr[1]
                    if not role:
                        role = sr[0]

            # Fallback display: IUPAC > name > SMILES
            if not display_name:
                display_name = (
                    getattr(sp, "iupac_name", None)
                    or sp.name
                    or (sp.smiles if sp.smiles and len(sp.smiles) <= 40 else None)
                    or sp.id
                )

            lookup_key = display_name.lower().strip()
            if lookup_key in _seen_names:
                continue
            _seen_names.add(lookup_key)

            if role:
                bin_name = _ROLE_BIN.get(role, "reagents")
                if bin_name == "solvents":
                    cats["solvents"].append(display_name)
                else:
                    cats[bin_name].append((display_name, ""))
            else:
                cats["reagents"].append((display_name, ""))

    # 2. Text reagent species (multi-line text blocks)
    for rid in step.reagent_ids:
        sp = species.get(rid)
        if not sp or sp.element_type != "text":
            continue
        if not sp.name:
            continue
        # Split multi-line block into individual tokens
        for line in sp.name.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Split on comma/semicolon (but protect names like "1,4-dioxane")
            # Strategy: if whole line is a known name, keep it; else try splitting
            if db.entry_for_name(line.strip().lower()):
                _add_token(line)
                continue
            # Try splitting on commas
            parts = re.split(r"[;,]\s*", line)
            if len(parts) > 1:
                for part in parts:
                    _add_token(part)
            else:
                _add_token(line)

    # 3. Physical conditions from parsed step.conditions
    for cond in step.conditions:
        cond_lower = cond.lower().strip()
        if cond_lower not in _seen_names:
            _seen_names.add(cond_lower)
            cats["conditions"].append(cond)

    return cats


def _format_conditions(step, species: Dict[str, SpeciesRecord]) -> str:
    """Format step conditions as readable text.

    Delegates to ``_parse_step_reagents`` for structured decomposition,
    then formats into a single-line summary for backward compatibility.
    """
    cats = _parse_step_reagents(step, species)
    parts = []
    for name, equiv in cats["catalysts"]:
        parts.append(f"{name} ({equiv})" if equiv else name)
    for name, equiv in cats["ligands"]:
        parts.append(f"{name} ({equiv})" if equiv else name)
    for name, equiv in cats["bases"]:
        parts.append(f"{name} ({equiv})" if equiv else name)
    for name, equiv in cats["reagents"]:
        parts.append(f"{name} ({equiv})" if equiv else name)
    parts.extend(cats["solvents"])
    parts.extend(cats["conditions"])
    if step.yield_text:
        parts.append(f"{step.yield_text} yield")
    return ", ".join(parts) if parts else "(conditions not specified)"


def analyze_bond_changes(mapped_rxn: str) -> Dict[str, list]:
    """Analyze bond changes from an atom-mapped reaction SMILES.

    Uses RDKit to compare bonds between mapped atoms in reactants vs products.

    Returns
    -------
    dict
        ``formed`` : list of (sym1, map1, sym2, map2, bond_order)
        ``broken`` : list of (sym1, map1, sym2, map2, bond_order)
        ``changed_order`` : list of (sym1, map1, sym2, map2, old_order, new_order)
        ``leaving`` : list of (group_symbol, nbr_symbol, nbr_map)
    """
    try:
        from rdkit import Chem
    except ImportError:
        return {}

    parts = mapped_rxn.split(">>")
    if len(parts) != 2:
        return {}

    reactants = Chem.MolFromSmiles(parts[0])
    products = Chem.MolFromSmiles(parts[1])
    if not reactants or not products:
        return {}

    def _map_to_idx(mol):
        return {a.GetAtomMapNum(): a.GetIdx()
                for a in mol.GetAtoms() if a.GetAtomMapNum()}

    def _bonds_by_map(mol):
        idx_to_map = {a.GetIdx(): a.GetAtomMapNum() for a in mol.GetAtoms()}
        bonds = {}
        for bond in mol.GetBonds():
            m1 = idx_to_map.get(bond.GetBeginAtomIdx(), 0)
            m2 = idx_to_map.get(bond.GetEndAtomIdx(), 0)
            if m1 and m2:
                bonds[(min(m1, m2), max(m1, m2))] = bond.GetBondTypeAsDouble()
        return bonds

    def _atom_sym(mol, mapnum):
        m = _map_to_idx(mol)
        idx = m.get(mapnum)
        if idx is None:
            return "?"
        return mol.GetAtomWithIdx(idx).GetSymbol()

    r_bonds = _bonds_by_map(reactants)
    p_bonds = _bonds_by_map(products)

    formed = [
        (_atom_sym(products, k[0]), k[0],
         _atom_sym(products, k[1]), k[1], p_bonds[k])
        for k in sorted(set(p_bonds) - set(r_bonds))
    ]
    broken = [
        (_atom_sym(reactants, k[0]), k[0],
         _atom_sym(reactants, k[1]), k[1], r_bonds[k])
        for k in sorted(set(r_bonds) - set(p_bonds))
    ]
    changed = [
        (_atom_sym(products, k[0]), k[0],
         _atom_sym(products, k[1]), k[1], r_bonds[k], p_bonds[k])
        for k in sorted(set(r_bonds) & set(p_bonds))
        if r_bonds[k] != p_bonds[k]
    ]

    # Leaving groups: unmapped atoms bonded to mapped atoms in reactants
    leaving = []
    seen = set()
    for atom in reactants.GetAtoms():
        if atom.GetAtomMapNum() == 0 and atom.GetIdx() not in seen:
            for nbr in atom.GetNeighbors():
                mn = nbr.GetAtomMapNum()
                if mn:
                    leaving.append((atom.GetSymbol(), nbr.GetSymbol(), mn))
                    seen.add(atom.GetIdx())
                    break

    return {
        "formed": formed,
        "broken": broken,
        "changed_order": changed,
        "leaving": leaving,
    }


def describe_transformation(changes: Dict[str, list],
                            max_changes: int = 5) -> str:
    """Generate a chemical English description from bond-change analysis.

    Produces a concise, human-readable description of what bonds formed,
    broke, or changed order, and what groups were displaced.

    When the atom mapping is incomplete (reagents not drawn as structures),
    the mapper may shuffle atoms producing many spurious bond changes.
    If total changes exceed *max_changes*, only leaving groups and key
    single-bond formations are reported.

    Example: "C-N bond formed; Br displaced from C"
    """
    if not changes:
        return ""

    formed = changes.get("formed", [])
    broken = changes.get("broken", [])
    changed = changes.get("changed_order", [])
    leaving = changes.get("leaving", [])

    total = len(formed) + len(broken) + len(changed)

    _ORDER_NAME = {
        1.0: "single", 1.5: "aromatic", 2.0: "double", 3.0: "triple",
    }
    parts = []

    if total > max_changes:
        # Too many changes — mapping likely incomplete (reagent not drawn).
        # Report only the most informative: single-bond formations (coupling)
        # and leaving groups.
        key_formed = [f for f in formed if f[4] == 1.0]
        for sym1, _m1, sym2, _m2, _bt in key_formed[:2]:
            parts.append(f"{sym1}-{sym2} bond formed")
        for lg_sym, nbr_sym, _mn in leaving[:2]:
            parts.append(f"{lg_sym} displaced from {nbr_sym}")
        if not parts:
            parts.append(f"complex rearrangement ({total} bond changes)")
    else:
        for sym1, _m1, sym2, _m2, bt in formed:
            bname = _ORDER_NAME.get(bt, f"order-{bt}")
            parts.append(f"{sym1}-{sym2} {bname} bond formed")

        for sym1, _m1, sym2, _m2, bt in broken:
            bname = _ORDER_NAME.get(bt, f"order-{bt}")
            parts.append(f"{sym1}-{sym2} {bname} bond broken")

        for sym1, _m1, sym2, _m2, old_bt, new_bt in changed:
            old_n = _ORDER_NAME.get(old_bt, str(old_bt))
            new_n = _ORDER_NAME.get(new_bt, str(new_bt))
            parts.append(f"{sym1}-{sym2} bond changed {old_n} -> {new_n}")

        for lg_sym, nbr_sym, _mn in leaving:
            parts.append(f"{lg_sym} displaced from {nbr_sym}")

    return "; ".join(parts) if parts else ""


def generate_llm_narrative(desc: SchemeDescription,
                           ml_enrichment: Optional[Dict[int, Dict]] = None,
                           ) -> str:
    """Generate a chemist-quality natural language narrative.

    This function produces Layer 3 output: readable text that an LLM can
    consume for chemical reasoning, grounded in SMILES from the species
    registry.

    Parameters
    ----------
    desc : SchemeDescription
        Parsed scheme (Tier 1 or Tier 2).
    ml_enrichment : dict, optional
        Per-step ML grounding data keyed by step_index.  Each entry is
        the dict returned by ``classify_roles_enriched()`` (RXNMapper +
        rxn-insight).  Keys include ``reaction_class``, ``reaction_name``,
        ``confidence``, ``byproducts``, ``components``.

    Returns
    -------
    str
        Natural language narrative with embedded SMILES for grounding.
    """
    ml_enrichment = ml_enrichment or {}
    if not desc.steps:
        # No-step schemes (target arrays, etc.)
        n_frag = sum(1 for sp in desc.species.values()
                     if sp.element_type == "fragment")
        n_text = sum(1 for sp in desc.species.values()
                     if sp.element_type == "text")
        if n_frag == 0 and n_text == 0:
            return "Empty scheme with no chemical content detected."

        ctype_label = {
            "target_array": "Target structure array",
            "sar_design": "SAR design diagram",
            "synthesis": "Structure collection",
        }.get(desc.content_type or "", "Non-reaction scheme")

        parts = [f"{ctype_label} containing {n_frag} structure(s)."]

        for sp in desc.species.values():
            if sp.element_type != "fragment":
                continue
            display = _species_display(sp)
            # Flag generic scaffolds (contain [*] dummy atoms from R-groups)
            is_generic = sp.smiles and "[*]" in sp.smiles
            if is_generic:
                # Check if variable position info is in the name
                if sp.name and "variable:" in sp.name:
                    parts.append(f"  - {display} [generic scaffold — {sp.name}]")
                else:
                    parts.append(f"  - {display} [generic scaffold]")
            else:
                parts.append(f"  - {display}")

        # Include text annotations if present
        text_sps = [sp for sp in desc.species.values()
                    if sp.element_type == "text" and sp.name]
        if text_sps:
            parts.append("")
            parts.append("Annotations:")
            for sp in text_sps:
                first_line = sp.name.split("\n")[0].strip()
                parts.append(f"  - {first_line}")

        return "\n".join(parts)

    # Build narrative
    ctype_label = {
        "synthesis": "Synthetic route",
        "sar_design": "SAR exploration",
        "biological_pathway": "Biological pathway",
        "literature_comparison": "Literature method comparison",
        "composite": "Composite methodology overview",
        "investigation": "Methodology investigation",
    }.get(desc.content_type or "", "Reaction scheme")

    # Opening line
    topo_adj = {
        "linear": "sequential",
        "divergent": "divergent",
        "convergent": "convergent",
        "parallel": "parallel",
        "mixed": "multi-pathway",
    }.get(desc.topology, "")

    # Identify final product(s) for the opening
    final_products = []
    if desc.steps:
        last_step = desc.steps[-1]
        for pid in last_step.product_ids:
            sp = desc.species.get(pid)
            if sp:
                final_products.append(_species_display(sp))

    opening = f"{ctype_label}"
    if desc.num_steps > 0:
        opening += f" ({desc.num_steps} step{'s' if desc.num_steps > 1 else ''}"
        if topo_adj:
            opening += f", {topo_adj}"
        opening += ")"
    if final_products and desc.content_type in ("synthesis", "", None):
        opening += f" toward {final_products[0]}"
    opening += "."

    parts = [opening, ""]

    # Step-by-step description
    for step in desc.steps:
        ml_data = ml_enrichment.get(step.step_index)

        # Classify reaction (regex + optional ML)
        reagent_sps = [desc.species[rid] for rid in step.reagent_ids
                       if rid in desc.species]
        # Also check text species in reactants for amine detection
        all_step_sps = reagent_sps + [
            desc.species[rid] for rid in step.reactant_ids
            if rid in desc.species]
        rxn_type = _classify_reaction(
            step.condition_text_raw, all_step_sps, desc,
            ml_data=ml_data)

        # Reactant display
        r_names = []
        for rid in step.reactant_ids:
            sp = desc.species.get(rid)
            if sp:
                r_names.append(_species_display(sp))
        r_str = " + ".join(r_names) if r_names else ""

        # Product display
        p_names = []
        for pid in step.product_ids:
            sp = desc.species.get(pid)
            if sp:
                p_names.append(_species_display(sp))
        p_str = " + ".join(p_names) if p_names else ""

        # Detect protocol-only steps (no substrate/product drawn)
        _is_protocol_step = (
            not step.reactant_ids and not step.product_ids
            and desc.content_type in (
                "composite", "literature_comparison", "investigation"))

        # Step header
        step_num = step.step_index + 1
        if rxn_type:
            step_line = f"Step {step_num} -- {rxn_type}:"
        elif _is_protocol_step:
            step_line = f"Method {step_num}:"
        else:
            step_line = f"Step {step_num}:"

        # Arrow annotation
        if step.arrow_style == "failed":
            step_line += " [FAILED]"
        elif step.arrow_style == "dashed":
            step_line += " [tentative/planned]"

        parts.append(step_line)

        # Transformation description with structured conditions
        cats = _parse_step_reagents(step, desc.species)

        # Reactant → product line (or protocol description for method-only steps)
        if _is_protocol_step:
            # No substrate/product drawn — describe the protocol directly
            desc_line = "  Protocol:"
        elif r_str and p_str:
            desc_line = f"  {r_str} -> {p_str}"
        elif r_str:
            desc_line = f"  {r_str} -> (product)"
        elif p_str:
            desc_line = f"  (starting material) -> {p_str}"
        else:
            desc_line = f"  (starting material) -> (product)"
        parts.append(desc_line)

        # Transformation diff (when aligned names show what changed)
        _diffs = getattr(desc, '_alignment_diffs', {})
        if _diffs:
            for rid in step.reactant_ids:
                for pid in step.product_ids:
                    diff_str = _diffs.get((rid, pid))
                    if diff_str:
                        # Replace " -> " with " → " for readability
                        diff_display = diff_str.replace(" -> ", " \u2192 ")
                        parts.append(f"  Transformation: {diff_display}")

        # Reagents line (catalysts, ligands, bases, coupling/reducing agents)
        reagent_parts = []
        for name, equiv in cats["catalysts"]:
            reagent_parts.append(f"{name} ({equiv})" if equiv else name)
        for name, equiv in cats["ligands"]:
            reagent_parts.append(f"{name} ({equiv})" if equiv else name)
        for name, equiv in cats["bases"]:
            reagent_parts.append(f"{name} ({equiv})" if equiv else name)
        for name, equiv in cats["reagents"]:
            reagent_parts.append(f"{name} ({equiv})" if equiv else name)
        if reagent_parts:
            parts.append(f"  Reagents: {', '.join(reagent_parts)}")

        # Solvent line
        if cats["solvents"]:
            parts.append(f"  Solvent: {', '.join(cats['solvents'])}")

        # Physical conditions line (temp, time, atmosphere)
        cond_parts = list(cats["conditions"])
        if step.yield_text:
            cond_parts.append(f"{step.yield_text} yield")
        if cond_parts:
            parts.append(f"  Conditions: {', '.join(cond_parts)}")
        elif not reagent_parts and not cats["solvents"]:
            parts.append("  Conditions: (not specified)")

        # Workup line
        if cats["workup"]:
            parts.append(f"  Workup: {'; '.join(cats['workup'])}")

        # ML grounding block (when enrichment available)
        if ml_data:
            ml_parts = []
            rc = ml_data.get("reaction_class")
            rn = ml_data.get("reaction_name")
            conf = ml_data.get("confidence", 0)
            if rc or rn:
                label = rn or rc
                ml_parts.append(f'rxn-insight="{label}"')
            if conf:
                ml_parts.append(f"atom-map confidence={conf:.2f}")
            bp = ml_data.get("byproducts", [])
            if bp:
                ml_parts.append(f"byproducts=[{', '.join(bp)}]")
            if ml_parts:
                parts.append(f"  [ML: {'; '.join(ml_parts)}]")

            # Tier B: bond-change description from atom maps
            mapped_rxn = ml_data.get("mapped_rxn", "")
            if mapped_rxn:
                changes = analyze_bond_changes(mapped_rxn)
                xform_desc = describe_transformation(changes)
                if xform_desc:
                    parts.append(f"  Bond changes: {xform_desc}")

        parts.append("")

    # Substrate scope table section (when scope entries detected)
    if hasattr(desc, 'scope_entries') and desc.scope_entries:
        parts.append("Substrate scope:")
        for entry in desc.scope_entries:
            sp = desc.species.get(entry.species_id) if entry.species_id else None
            display = _species_display(sp) if sp else None

            line_parts = []
            if entry.label:
                line_parts.append(entry.label)
            elif display:
                line_parts.append(display)
            else:
                line_parts.append(entry.entry_id)

            if entry.conditions_variant:
                line_parts.append(f"({entry.conditions_variant})")
            if entry.yield_text:
                line_parts.append(f"— {entry.yield_text}")
            if entry.mass_text:
                line_parts.append(f"({entry.mass_text})")
            if entry.notes:
                line_parts.append(f"[{entry.notes}]")

            parts.append(f"  - {' '.join(line_parts)}")
        parts.append("")

    return "\n".join(parts).rstrip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scheme_refine",
        description="LLM refinement of scheme_reader output.",
    )
    sub = parser.add_subparsers(dest="command")

    # prompt subcommand
    p_prompt = sub.add_parser("prompt",
                              help="Generate refinement prompt for LLM")
    p_prompt.add_argument("input", help="Tier 1 JSON file")
    p_prompt.add_argument("--image", help="Path to rendered scheme image")

    # apply subcommand
    p_apply = sub.add_parser("apply",
                             help="Apply corrections to Tier 1 output")
    p_apply.add_argument("input", help="Tier 1 JSON file")
    p_apply.add_argument("corrections", help="Corrections JSON file")
    p_apply.add_argument("-o", "--output", help="Output refined JSON")

    args = parser.parse_args(argv)

    if args.command == "prompt":
        desc = SchemeDescription.from_json(args.input)
        prompt = generate_prompt(desc, image_path=args.image)
        print(prompt)
        return 0

    elif args.command == "apply":
        desc = SchemeDescription.from_json(args.input)
        with open(args.corrections, "r", encoding="utf-8") as f:
            corrections = json.load(f)
        refined = apply_corrections(desc, corrections)
        if args.output:
            refined.to_json(args.output)
            print(f"Written to {args.output}", file=sys.stderr)
        else:
            out = json.dumps(refined.to_dict(), indent=2,
                             ensure_ascii=False)
            sys.stdout.buffer.write(out.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
