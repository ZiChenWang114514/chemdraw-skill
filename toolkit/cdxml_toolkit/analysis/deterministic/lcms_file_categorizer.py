#!/usr/bin/env python3
"""
LCMS File Categorizer

Categorizes LCMS PDF filenames into experiment phases: tracking, workup,
purification, final, reference.  Two APIs:

  - categorize_lcms_file(filename) — simple per-file categorization
  - categorize_lcms_files_batch(filenames, experiment_id) — context-aware
    batch categorization with prefix-based tracking groups, modifier
    stripping, special file filtering, and hybrid sort key calibration

Pure string-processing engine — no PDF parsing, no external dependencies
beyond stdlib.
"""

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import median
from typing import List, Optional, Dict, Tuple


# ---------------------------------------------------------------------------
# Simple file categorization (per-file, no cross-file context)
# ---------------------------------------------------------------------------

def categorize_lcms_file(filename: str) -> Tuple[str, float]:
    """
    Categorize an LCMS file and return (category, sort_key).

    Categories: "tracking", "workup", "purification", "final", "reference"

    Uses the same pattern-matching engine as the batch categorizer
    (_categorize_suffix) but without cross-file context.  Strips
    analytical modifiers (-re, -AmB, -W9, etc.) and extracts the
    experiment suffix before categorization.
    """
    # Strip modifiers and extract suffix (same pipeline as batch)
    stripped, _mods = _strip_modifiers(filename)
    stripped_base = os.path.splitext(stripped)[0] if '.' in stripped else stripped
    experiment_id = _extract_experiment_id(filename)
    suffix = _extract_suffix(stripped_base, experiment_id)

    # Categorize using the shared engine (assume explicit times exist —
    # conservative: bare tNN treated as purification fractions)
    return _categorize_suffix(suffix, has_explicit_time=True)


# Ambiguous sort keys: files whose position in the timeline can't be
# reliably determined from the filename alone.
_AMBIGUOUS_SORT_KEYS = {500}  # 500 = "beforeadd"


# ---------------------------------------------------------------------------
# Batch file categorization (v2 — prefix-based grouping)
# ---------------------------------------------------------------------------

@dataclass
class FileModifiers:
    """Metadata stripped from a filename before categorization."""
    rerun_count: int = 0                    # -re=1, -rere=2
    duplicate_num: Optional[int] = None     # (2) -> 2
    method_variant: Optional[str] = None    # AmB, AmF, AmBfoc, AmFfoc
    method_program: Optional[str] = None    # W1, W9, W13, W17, W19
    long_method: bool = False               # -long suffix
    concentrated: bool = False              # -conc suffix
    focused: bool = False                   # -focus / -foc suffix


@dataclass
class TrackingGroup:
    """A group of tracking files sharing a common prefix."""
    prefix: str                              # e.g. "", "add50mgDEAD", "70C"
    files: List[Tuple[str, float]]           # (filename, time_in_minutes)
    offset: float = 0.0                      # calibrated offset for sort keys


@dataclass
class FileClassification:
    """Classification result for one LCMS file."""
    category: str                            # tracking, workup, purification, final, reference
    sort_key: float
    modifiers: FileModifiers
    group_prefix: Optional[str] = None       # for tracking files
    temperature: Optional[float] = None      # parsed temperature in Celsius


@dataclass
class BatchResult:
    """Result of batch categorization for one experiment."""
    experiment_id: str
    files: Dict[str, FileClassification]     # filename -> classification
    tracking_groups: List[TrackingGroup]
    filtered_files: List[str]                # special files (MS, LC, etc.)
    has_final: bool = False


# --- Modifier stripping ---

def _strip_modifiers(filename: str) -> Tuple[str, FileModifiers]:
    """Strip analytical modifiers from filename, return cleaned name + metadata."""
    base = os.path.splitext(filename)[0]
    mods = FileModifiers()

    # 1. Duplicate number: " (2)" or "(2)" at end
    m = re.search(r'\s*\((\d+)\)\s*$', base)
    if m:
        mods.duplicate_num = int(m.group(1))
        base = base[:m.start()]

    # 2. Rerun: -rere, -re, -RE at end (check rere first)
    if re.search(r'-[Rr][Ee][Rr][Ee]$', base):
        mods.rerun_count = 2
        base = base[:-5]
    elif re.search(r'-[Rr][Ee]$', base):
        mods.rerun_count = 1
        base = base[:-3]
    # Also handle -rerun / -RERUN
    elif re.search(r'-rerun$', base, re.IGNORECASE):
        mods.rerun_count = 1
        base = base[:-6]

    # 3. -focus / -foc at end
    if re.search(r'-foc(?:us)?$', base, re.IGNORECASE):
        mods.focused = True
        m2 = re.search(r'-foc(?:us)?$', base, re.IGNORECASE)
        base = base[:m2.start()]

    # 4. -conc at end
    if re.search(r'-conc$', base, re.IGNORECASE):
        mods.concentrated = True
        base = base[:-5]

    # 5. -long at end
    if re.search(r'-long$', base, re.IGNORECASE):
        mods.long_method = True
        base = base[:-5]

    # 6. Method program: -W1, -W3, -W4, -W9, -W13, -W17, -W19 at end
    m = re.search(r'-(W\d+)$', base, re.IGNORECASE)
    if m:
        mods.method_program = m.group(1).upper()
        base = base[:m.start()]

    # 7. Buffer method: -AmB, -AmF, -AmBfoc, -AmFfoc at end
    #    Must come after -foc stripping since -AmFfoc = -AmF + -foc
    m = re.search(r'-(Am[BF](?:foc)?)$', base, re.IGNORECASE)
    if m:
        mods.method_variant = m.group(1)
        base = base[:m.start()]

    return base, mods


# --- Special file detection ---

_SPECIAL_SUFFIXES_RE = re.compile(
    r'(?:'
    r'-MS'
    r'|-LC(?:-COPY)?'
    r'|-LCtrace'
    r'|-UV'
    r'|-manint'
    r'|-landscape'
    r'|-int'           # integration screenshot
    r')$',
    re.IGNORECASE
)


def _is_special_file(cleaned_base: str) -> bool:
    """Check if this file is a non-standard LCMS report (MS-only, LC-only, etc.)."""
    return bool(_SPECIAL_SUFFIXES_RE.search(cleaned_base))


# --- Experiment ID / suffix extraction ---

def _extract_experiment_id(filename: str) -> str:
    """Extract KL-XXXX-NNN experiment ID from a filename."""
    base = os.path.splitext(filename)[0]
    # Remove (2) duplicate suffix
    base = re.sub(r'\s*\(\d+\)\s*$', '', base)
    m = re.match(r'(KL-\d+-\d+)', base, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return base.upper()


def _extract_suffix(cleaned_base: str, experiment_id: str) -> str:
    """Extract the suffix after the experiment ID from a cleaned filename."""
    # Case-insensitive prefix match
    prefix_len = len(experiment_id)
    if cleaned_base[:prefix_len].upper() == experiment_id.upper():
        remainder = cleaned_base[prefix_len:]
        # Strip leading dash, space, or underscore
        remainder = remainder.lstrip('-').lstrip(' ').lstrip('_')
        return remainder
    return cleaned_base


# --- Time token extraction ---

def _extract_time_token(suffix: str) -> Optional[Tuple[float, int, int]]:
    """
    Find the best time token in the suffix.

    Returns (time_in_minutes, token_start, token_end) or None.
    token_start/end define the span of the time+temperature cluster
    (for prefix extraction: everything before token_start is the group prefix).
    """
    original = suffix
    candidates = []  # (start, end, time_minutes)

    # --- Combined temperature+time patterns ---
    # For NNC+time patterns, t_start points to the start of the time portion
    # (after the temperature), so the temperature becomes part of the group
    # prefix.  For time+NNC patterns, the time IS at the start so t_start
    # = m.start().

    # NNCON: 40CON, 80CON, 90CON, 100CON, 105CON — temperature + overnight
    # The "ON" begins after the "C" in "NNCON", so we need to find that offset.
    for m in re.finditer(r'(\d{2,3})C(ON)\b', original):
        candidates.append((m.start(2), m.end(), 960.0))

    # NNC-ON: 65C-ON — temperature + dash + overnight
    for m in re.finditer(r'(\d{2,3})C-(ON)\b', original):
        candidates.append((m.start(2), m.end(), 960.0))

    # NNC-OWE / NNC-OWE: 130C-OWE
    for m in re.finditer(r'(\d{2,3})C-?(OWE)\b', original):
        candidates.append((m.start(2), m.end(), 2880.0))

    # NNC + NhNm: 40C1h25min — time starts at group 2
    for m in re.finditer(r'(\d{2,3})C-?(\d+)h(\d+)\s*m(?:in)?', original, re.IGNORECASE):
        t = float(m.group(2)) * 60 + float(m.group(3))
        candidates.append((m.start(2), m.end(), t))

    # NNC + Nh: 80C8h, 80C-2h, 120C-5h, 70C-1hmore — time starts at group 2
    for m in re.finditer(r'(\d{2,3})C-?(\d+)h(?!\d)', original, re.IGNORECASE):
        candidates.append((m.start(2), m.end(), float(m.group(2)) * 60))

    # NNC + Nmin: 100C30min, 50C5min, 50C40min — time starts at group 2
    for m in re.finditer(r'(\d{2,3})C-?(\d+)\s*min', original, re.IGNORECASE):
        candidates.append((m.start(2), m.end(), float(m.group(2))))

    # NNC + Nm: 50C12m (boundary at word end) — time starts at group 2
    for m in re.finditer(r'(\d{2,3})C-?(\d+)m\b', original, re.IGNORECASE):
        candidates.append((m.start(2), m.end(), float(m.group(2))))

    # Time + NNC: 30min80C, 100min80C, 12min70C — time IS at the start
    for m in re.finditer(r'(\d+)\s*min(\d{2,3})C', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), float(m.group(1))))

    # Time(m) + NNC: 90m70C (if it occurs) — time IS at the start
    for m in re.finditer(r'(\d+)m(\d{2,3})C', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), float(m.group(1))))

    # Nh + NNC: 9h125C, 1h50C, 1h70C — time IS at the start
    for m in re.finditer(r'(\d+)h(\d{2,3})C', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), float(m.group(1)) * 60))

    # NhNm + NNC: 1h30m80C (if it occurs)
    for m in re.finditer(r'(\d+)h(\d+)m(\d{2,3})C', original, re.IGNORECASE):
        t = float(m.group(1)) * 60 + float(m.group(2))
        candidates.append((m.start(), m.end(), t))

    # NhNm + NNC or NNC: not commonly observed, skip

    # --- Standalone time patterns ---

    # premix with time: premix10min, premix4min, premix7min
    for m in re.finditer(r'premix-?(\d+)\s*min', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), -float(m.group(1))))
    for m in re.finditer(r'premix-?(\d+)\s*m\b', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), -float(m.group(1))))
    # premix alone (no time)
    if re.search(r'\bpremix\b', original, re.IGNORECASE):
        m = re.search(r'\bpremix\b', original, re.IGNORECASE)
        # Only if not already matched as premixNmin
        if not re.search(r'premix-?\d+', original, re.IGNORECASE):
            candidates.append((m.start(), m.end(), -10.0))

    # NhNmin: 1h30min, 2h45min, 3h20min
    for m in re.finditer(r'(\d+)h(\d+)\s*min', original, re.IGNORECASE):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(),
                               float(m.group(1)) * 60 + float(m.group(2))))

    # NhNm: 1h27m, 4h30m, 2h45m, 1h50mrerun
    # Allow m to be followed by non-digit (not just word boundary)
    for m in re.finditer(r'(\d+)h(\d+)m(?![0-9])', original, re.IGNORECASE):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(),
                               float(m.group(1)) * 60 + float(m.group(2))))

    # ON — case-sensitive (uppercase ON).  Must NOT be followed by uppercase
    # letters (to avoid matching inside "ONCE", "ONLY", etc.).
    # Allowed after lowercase (airdryON, scavON) and before lowercase
    # (ONrecheck = overnight recheck).
    for m in re.finditer(r'ON(?![A-Z])', original):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(), 960.0))

    # OWE — case-sensitive, same relaxed boundary
    for m in re.finditer(r'OWE(?![A-Z])', original):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(), 2880.0))

    # Nh: 1h, 12h, 16h — not preceded by temp, not followed by digit (NhNm)
    for m in re.finditer(r'(\d+)h(?!\d)', original, re.IGNORECASE):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(), float(m.group(1)) * 60))

    # Nmin: 30min, 128min — not preceded by temp
    for m in re.finditer(r'(\d+)\s*min(?:s)?', original, re.IGNORECASE):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(), float(m.group(1))))

    # Nm: 90m, 40m, 30mrt — not preceded by temp.
    # Reject only when followed by "in" (to avoid double-matching Nmin as Nm)
    # or by another "m" (mm, mol); allow other suffixes like rt, sp, p.
    for m in re.finditer(r'(\d+)m(?!in|m|ol)', original, re.IGNORECASE):
        if not _preceded_by_temp(original, m.start()):
            candidates.append((m.start(), m.end(), float(m.group(1))))

    # "onehour" / "overnight" as special text
    for m in re.finditer(r'\bonehour\b', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), 60.0))
    for m in re.finditer(r'\bovernight\b', original, re.IGNORECASE):
        candidates.append((m.start(), m.end(), 960.0))

    if not candidates:
        return None

    # Prefer the most specific (longest span) match; break ties by rightmost
    # De-duplicate overlapping candidates: keep the longest span at each position
    candidates.sort(key=lambda c: (-(c[1] - c[0]), -c[0]))
    best = candidates[0]
    return (best[2], best[0], best[1])


def _preceded_by_temp(suffix: str, pos: int) -> bool:
    """Check if position is immediately preceded by a NNC temperature pattern."""
    before = suffix[:pos]
    return bool(re.search(r'\d{2,3}C-?$', before, re.IGNORECASE))


def _extract_temperature(suffix: str) -> Optional[float]:
    """Extract temperature in Celsius from suffix if present."""
    m = re.search(r'(?<![tT])(\d{2,3})C', suffix)
    if m:
        return float(m.group(1))
    return None


# --- Categorization logic ---

# Final product patterns
_FINAL_RE = re.compile(
    r'(?:'
    r'purified'          # nppurified, rppurified, THFRPpurified, c18purified
    r'|lyo'              # lyo, repurlyo, lyotwice, rerelyo
    r'|verify'           # verify, AmBverify
    r'|prodchk'          # product check
    r'|(?:^|[^a-zA-Z])(?:NMRsample|NMRsamp|QC|NMR)(?:[^a-zA-Z]|$)'
    r')',
    re.IGNORECASE
)
_FINAL_STANDALONE_RE = re.compile(
    r'^(?:NMR|final|finalNMR|finalvial|prod|final\d?)$',
    re.IGNORECASE
)

# Purification tube number: optional prefix + tNN or tNNtoNN
_PURIF_PREFIX_RE = re.compile(
    r'^(?:NP\d?|RP\d?|C18(?:-\d)?|prep\d?|col\d?|I\d|scout|THF(?:RP)?'
    r'|THFrecov|EArecov|recol|scavNP|KADrecov|final\d?|recov(?:NP)?'
    r'|MeCN(?:col)?|actual|firstinj|prevbatch'
    r'|fchk\d?|meohtest'       # fraction check, MeOH test
    r'|p\d|v\d|vial\d'         # p1-, v1-, vial1- column/vial prefixes
    r'|first|second'           # first/second injection
    r'|step\d'                 # step1, step2 purification steps
    r')'
    r'-?',
    re.IGNORECASE
)
_TUBE_NUM_RE = re.compile(r't(\d+)(?:to(\d+))?', re.IGNORECASE)

# Purification keywords (not tube numbers)
_PURIF_KEYWORDS = {
    'comb', 'combed', 'peakcomb', 'colload', 'load', 'loading', 'flush',
    'tflush', 'tload', 'tail', 'tails', 'repur', 'repurified',
    'npcomb', 'npcombed', 'rpcomb', 'rprecomb', 'c18comb', 'c18load',
    'thfcol-comb', 'meccol-i1to4comb',
    'impfrac', 'reload',
    'onetube', 'nptails', 'npminor',
    'tend', 'tblob', 'tlast',  # tube end/last/blob
    'fchk', 'fchk1', 'fchk2',  # fraction check
}

# Workup keywords
_WORKUP_KEYWORDS = {
    'crude', 'cr', 'extract', 'ext', 'wash', 'washed', 'washing',
    'rewash', 'rewashed', 'aq', 'org', 'brine',
    'dried', 'driedonce', 'redried', 'combdried',
    'filter', 'filtered', 'filtrate', 'fil', 'filtersolid',
    'pellet', 'pel', 'super', 'ppt',
    'quench', 'quenched',
    'silfil', 'cefil',
    'rotovap', 'rotatrap', 'rota',
    'slurry', 'recryst', 'workup',
    'nofil', 'or',
}

# Reference patterns (starting material checks, not reaction monitoring)
_REFERENCE_RE = re.compile(
    r'^(?:SM\d?|RAE|RAESM|ArI|ArBr|ArBrSM|ArISM|aniline|chloride|SMchloride'
    r'|TP-SM|Clref|tolref|SMPDref|SMPDCT|DDQSM|chlorideSM|SManiline'
    r'|X\d{3}|E\d{3}|INT\d+|KADDP|SMwith\w+'
    r'|spiking|SMcheck|SMchk|SMconfirm|SMrecov|SM-verify'
    r'|aminopySM|AmPySM|smmix|smix|smrtmix|SMS'
    r'|byprod|ref\d?'
    r')(?:$|-)',
    re.IGNORECASE
)

# Additional reference patterns: NpNF fluorine equivalents (titration experiments)
_FLUORINE_EQUIV_RE = re.compile(
    r'^(?:\d*p?\d+F(?:mol)?|\d+F)$',
    re.IGNORECASE
)


def _categorize_suffix(suffix: str, has_explicit_time: bool) -> Tuple[str, float]:
    """
    Categorize a single file's suffix.

    Args:
        suffix: The cleaned suffix (modifiers stripped, experiment ID removed).
        has_explicit_time: True if other files in the experiment have
            explicit time tokens (Nmin, Nh, ON, OWE — not tNN).

    Returns:
        (category, preliminary_sort_key)
    """
    if not suffix:
        return 'tracking', 100

    lower = suffix.lower()

    # --- Priority 0.5: "final-IN-tNN" purification tube fractions ---
    # Must come before the final product check since "final" is a prefix here
    if re.match(r'final\d?-(?:I\d|i\d)', suffix, re.IGNORECASE):
        return 'purification', 3000

    # --- Priority 1: Final product ---
    if _FINAL_RE.search(suffix) or _FINAL_STANDALONE_RE.match(suffix):
        # Exception: "crude-NMR" or "crude-NMRsample" is workup
        if 'crude' in lower:
            return 'workup', 2000
        # Exception: method-prefix + "purified" = purification, not final
        # NPpurified, RPpurified, C18purified, THFRPpurified, scavNPpurified
        if re.match(r'^(?:NP|RP|C18|THFRP|THF|scavNP|col)\d?-?purified',
                    suffix, re.IGNORECASE):
            return 'purification', 3000
        return 'final', 9000

    # --- Priority 2: Purification ---
    # Check for tube numbers: [prefix]-tNN[toNN]
    # First strip any purification prefix to find the tNN part
    test_suffix = suffix
    purif_prefix_match = _PURIF_PREFIX_RE.match(suffix)
    if purif_prefix_match:
        test_suffix = suffix[purif_prefix_match.end():]

    # Recursively strip purification prefixes (p1-c18-t16, final-I1-t4, etc.)
    for _ in range(3):  # max 3 levels of nesting
        new_match = _PURIF_PREFIX_RE.match(test_suffix)
        if new_match:
            test_suffix = test_suffix[new_match.end():]
        else:
            break

    # Also strip inline injection number: I1-, I2-, I1t, etc.
    inj_match = re.match(r'I\d+-?', test_suffix)
    if inj_match:
        test_suffix = test_suffix[inj_match.end():]

    # Also handle leading dash: -t12 → strip dash
    if test_suffix.startswith('-'):
        test_suffix = test_suffix[1:]

    tube_match = _TUBE_NUM_RE.match(test_suffix)
    # Also try bare numbers after purification prefix (first-17, vial2-24)
    if not tube_match and purif_prefix_match and re.match(r'^\d+(?:to\d+)?$', test_suffix):
        tube_num = int(re.match(r'^(\d+)', test_suffix).group(1))
        return 'purification', 3000 + tube_num

    if tube_match:
        has_purif_prefix = purif_prefix_match is not None and purif_prefix_match.end() > 0
        tube_num = int(tube_match.group(1))

        if has_purif_prefix:
            # NP-t13, RP-t25, C18-t79 — always purification
            return 'purification', 3000 + tube_num
        elif has_explicit_time:
            # Bare tNN in an experiment with explicit time tokens
            # High tube numbers (>30) are almost certainly purification
            # Low numbers are ambiguous but still likely purification if
            # explicit times exist alongside
            return 'purification', 3000 + tube_num
        else:
            # Bare tNN, no explicit time tokens — ambiguous
            # Likely purification (tube numbers rarely used for tracking)
            return 'purification', 3000 + tube_num

    # Purification keywords
    # Split on - and check each part
    parts_lower = set(re.split(r'[-_\s]', lower))
    if parts_lower & _PURIF_KEYWORDS:
        return 'purification', 3000

    # More flexible purification keyword match (substring)
    if any(kw in lower for kw in ['peakcomb', 'peak-comb', 'colload',
                                   'rpload', 'npcomb', 'npcombed',
                                   'rpcomb', 'c18comb', 'c18load',
                                   'tpeakcomb',
                                   'c18repur', 'rprepur',
                                   'meohwash',  # column wash
                                   'impfrac', 'reload',
                                   'loading',
                                   'mecncol', 'mecnrecov',
                                   'purefracs', 'lesspure', 'morepure',
                                   'combed',
                                   ]):
        return 'purification', 3000

    # Any suffix starting with a purification method prefix (C18, NP, RP,
    # etc.) is purification — even if the remainder looks like workup
    # (e.g. C18-DCMext = DCM extraction from C18 eluate, still purification;
    # NP-dried = dried NP fractions, still purification).
    if purif_prefix_match and purif_prefix_match.end() > 0:
        # A known purification method prefix was matched
        return 'purification', 3000

    # RN-tNN patterns (R2t5 = round 2, tube 5)
    if re.match(r'^R\d+t\d+', suffix, re.IGNORECASE):
        return 'purification', 3000

    # Bare tube range: NNtoNN (39to41, 46to49)
    if re.match(r'^\d+to\d+$', suffix, re.IGNORECASE):
        return 'purification', 3000

    # peak1, peak2 — purification peak fractions
    if re.match(r'^peak\d+$', lower):
        return 'purification', 3000

    # --- Priority 3: Workup ---
    if parts_lower & _WORKUP_KEYWORDS:
        return 'workup', 2000

    # More flexible workup match (substring for compound words)
    if any(kw in lower for kw in ['crude', 'washed', 'dried', 'quench',
                                   'silfil', 'cefil', 'rotovap',
                                   'rotatrap', 'workup', 'extraction',
                                   'filtrate', 'pellet', 'super',
                                   'slurry', 'recryst',
                                   'dcmext',       # DCM extraction
                                   'ipawash',      # IPA wash
                                   'hclwash',      # HCl wash
                                   'washing',      # washing steps
                                   'orgph',        # organic phase
                                   'orgwash',      # organic wash
                                   'nahco3wu', 'naohwu', 'waterwu',  # wu = workup
                                   'bicarbwash', 'naohwash',
                                   'syrfilter',    # syringe filter
                                   'eaext',        # EA extraction
                                   'rotaeaext',    # rotavap + EA extraction
                                   'wutest',       # workup test
                                   'mainpeak',     # mainpeakhclwash etc.
                                   'dmsodil',      # DMSO dilution
                                   'b4rota',       # before rotavap
                                   ]):
        return 'workup', 2000

    # Standalone workup: aq1, aq2, org1, Naq, Ncr, Norgwash, etc.
    if re.match(r'^(?:aq|org)\d*$', lower):
        return 'workup', 2000
    # Numbered workup: 1orgwash, 2aq, 3Cr
    if re.match(r'^\d+(?:aq|org|cr|wash|ext)', lower):
        return 'workup', 2000
    # cent (centrifuge)
    if lower == 'cent':
        return 'workup', 2000

    # --- Priority 4: Tracking (files with time tokens) ---
    time_result = _extract_time_token(suffix)
    if time_result:
        time_min, _, _ = time_result
        return 'tracking', time_min

    # --- Priority 5: Reference ---
    if _REFERENCE_RE.match(suffix):
        return 'reference', 50
    # Fluorine equivalents: 1p55F, 2p7F, 0p6F, p28Fmol, p8F, etc.
    if _FLUORINE_EQUIV_RE.match(suffix):
        return 'reference', 50
    # N-ref patterns: 2-ref, 3-ref
    if re.match(r'^\d+-ref', lower):
        return 'reference', 50
    # 4-br — aryl bromide reference
    if re.match(r'^\d+-(?:br|cl|i)\b', lower):
        return 'reference', 50

    # --- Fallback ---
    # Some patterns that are clearly a certain category but didn't match above

    # Purification-related fallbacks
    if 'flush' in lower or 'ipaflush' in lower:
        return 'purification', 3000
    if 'trap' in lower and lower != 'rotatrap':
        return 'purification', 3000
    if 'recov' in lower:
        return 'purification', 3000
    if lower.startswith('rp') and any(x in lower for x in ['peak', 'inj', 'chk', '-i']):
        return 'purification', 3000
    if 'kadmix' in lower or 'fracks' in lower:
        return 'purification', 3000
    if re.match(r'^rp\d?-', lower):  # rp-sm, rp-peak, rp2-...
        # rp-sm is reference, others are purification
        if 'sm' in lower:
            return 'reference', 50
        return 'purification', 3000
    # step1-meoh, step2-X — purification step procedures
    if re.match(r'^step\d+', lower):
        return 'purification', 3000

    # Workup-related fallbacks
    if 'solid' in lower and 'gold' not in lower:
        return 'workup', 2000
    if 'sludge' in lower or 'residue' in lower:
        return 'workup', 2000
    if lower.startswith('or') and len(lower) <= 3:  # "or", "or1"
        return 'workup', 2000
    if lower == 'rext' or lower == 'res':
        return 'workup', 2000
    if lower == 'ea':  # ethyl acetate workup
        return 'workup', 2000
    if 'trit' in lower and lower != 'et3n':  # trituration
        return 'workup', 2000

    # Reference fallbacks
    if 'smmix' in lower or 'smix' in lower or 'smrtmix' in lower:
        return 'reference', 50
    if lower.startswith('imp') and not lower.startswith('impfrac'):
        return 'reference', 50
    if 'arbrsm' in lower or 'arism' in lower:
        return 'reference', 50

    # Tracking qualitative timepoints
    if 'morning' in lower or 'monmorn' in lower or 'beforeleave' in lower:
        return 'tracking', 500  # qualitative timepoint, ambiguous ordering
    if 'beforeadd' in lower or 'beforescav' in lower:
        return 'tracking', 500
    if 'afteradd' in lower:
        return 'tracking', 600
    if 'startmix' in lower or 'start' == lower or 'mix' == lower:
        return 'tracking', 0
    if 'check' in lower or 'chk' in lower:
        return 'tracking', 100
    if lower.startswith('step'):
        return 'tracking', 100
    if 'befvac' in lower or 'aftvac' in lower:
        return 'tracking', 100
    if lower.startswith('add') and not lower.startswith('adduct'):
        return 'tracking', 600  # addDCM, addEt3N, etc. — after main reaction
    if 'insert' in lower or 'lc' in lower.split('-'):
        return 'tracking', 100
    if '1moreh' in lower or 'moreh' in lower:
        return 'tracking', 100
    if 'rxnmix' in lower or 'crmix' in lower:
        return 'tracking', 0
    if 'onemorehour' in lower:
        return 'tracking', 60
    if 'longtime' in lower:
        return 'tracking', 500
    if 'aftersfc' in lower:
        return 'tracking', 600  # after SFC purification (but tracking, not purif)
    if 'moreconc' in lower:
        return 'tracking', 100
    # Volume patterns: NNNul (microliters)
    if re.match(r'.*\d+ul$', lower):
        return 'tracking', 100
    if 'heatint' in lower or 'rtint' in lower:
        return 'tracking', 100
    # beforelyo is tracking (sample taken before lyophilization)
    if 'beforelyo' in lower:
        return 'tracking', 100

    return 'tracking', 100


# --- Batch categorization main entry ---

def categorize_lcms_files_batch(
    filenames: List[str],
    experiment_id: Optional[str] = None,
) -> BatchResult:
    """
    Batch-categorize all LCMS files for one experiment.

    Unlike categorize_lcms_file() (which processes files independently),
    this function uses cross-file context to resolve ambiguities:
    - tNN as purification fraction vs tracking timepoint
    - Multi-phase tracking (add-more, scavenger, temperature changes)
    - Modifier stripping (-re, -AmB, -W9, etc.)
    - Special file filtering (-MS, -LC, etc.)

    Args:
        filenames: All LCMS PDF filenames for the experiment (basenames).
        experiment_id: Experiment ID (e.g. "KL-1001-065"). If None,
            auto-detected from the first filename.

    Returns:
        BatchResult with per-file categories, tracking groups,
        filtered files, and has_final flag.
    """
    if not filenames:
        return BatchResult(experiment_id=experiment_id or "", files={},
                           tracking_groups=[], filtered_files=[])

    if experiment_id is None:
        experiment_id = _extract_experiment_id(filenames[0])

    result = BatchResult(
        experiment_id=experiment_id,
        files={},
        tracking_groups=[],
        filtered_files=[],
    )

    # Phase 1: Strip modifiers, filter special files, extract suffixes
    cleaned = {}  # filename -> (cleaned_base, suffix, modifiers)
    for fn in filenames:
        stripped, mods = _strip_modifiers(fn)
        stripped_base = os.path.splitext(stripped)[0] if '.' in stripped else stripped

        if _is_special_file(stripped_base):
            result.filtered_files.append(fn)
            continue

        suffix = _extract_suffix(stripped_base, experiment_id)
        cleaned[fn] = (stripped_base, suffix, mods)

    # Phase 2: Scan for explicit time tokens (to resolve tNN ambiguity)
    # "Explicit time" = a non-tube time pattern (Nmin, Nh, ON, OWE, premix)
    has_explicit_time = False
    for fn, (_, suffix, _) in cleaned.items():
        tt = _extract_time_token(suffix)
        if tt is not None:
            has_explicit_time = True
            break

    # Phase 3: Categorize each file
    tracking_candidates = []  # (filename, suffix, time_min, group_prefix)

    for fn, (stripped_base, suffix, mods) in cleaned.items():
        cat, sort_key = _categorize_suffix(suffix, has_explicit_time)

        temp = _extract_temperature(suffix)

        fc = FileClassification(
            category=cat,
            sort_key=sort_key,
            modifiers=mods,
            temperature=temp,
        )

        if cat == 'tracking':
            tt = _extract_time_token(suffix)
            if tt is not None:
                time_min, t_start, t_end = tt
                # Group prefix = everything before the time token
                prefix = suffix[:t_start].rstrip('-').rstrip(' ').rstrip('_')
                fc.group_prefix = prefix
                fc.sort_key = time_min
                tracking_candidates.append((fn, suffix, time_min, prefix))
            else:
                fc.group_prefix = "__notime__"

        result.files[fn] = fc

    # Phase 4: Group tracking files by prefix
    groups_dict = defaultdict(list)
    for fn, suffix, time_min, prefix in tracking_candidates:
        groups_dict[prefix].append((fn, time_min))

    # Sort groups by median time value
    sorted_groups = []
    for prefix in sorted(groups_dict.keys(),
                         key=lambda p: median([t for _, t in groups_dict[p]])):
        files_in_group = groups_dict[prefix]
        # Sort files within group by time
        files_in_group.sort(key=lambda x: x[1])
        tg = TrackingGroup(prefix=prefix, files=files_in_group)
        sorted_groups.append(tg)

    # Phase 5: Assign calibrated sort keys for multi-group tracking.
    # At categorization time we don't have PDF timestamps, so use the
    # fallback mode (arbitrary +100 min gap between groups).  After PDFs
    # are parsed, callers can recalibrate groups 2+ with real timestamps
    # via calibrate_sort_keys_hybrid().
    calibrate_sort_keys_hybrid(sorted_groups, result)

    # Record group prefix on each tracking file
    for group in sorted_groups:
        for fn, _ in group.files:
            if fn in result.files:
                result.files[fn].group_prefix = group.prefix

    result.tracking_groups = sorted_groups

    # Phase 6: Check for final files
    result.has_final = any(
        fc.category == 'final' for fc in result.files.values()
    )

    return result


# ---------------------------------------------------------------------------
# Hybrid sort key calibration (filename for group 1, timestamps for group 2+)
# ---------------------------------------------------------------------------

def calibrate_sort_keys_hybrid(
    sorted_groups: List['TrackingGroup'],
    result: 'BatchResult',
    run_datetimes: Optional[Dict[str, str]] = None,
) -> None:
    """
    Assign sort keys to tracking files across multiple tracking groups.

    Group 1 (or single-group reactions): uses ONLY filename-derived time
    tokens.  The chemist often prepares samples ahead and may submit them
    out of order on the instrument queue — filename order reflects the
    intended chronology.

    Groups 2+: uses actual PDF acquisition timestamps when available.
    At this stage the chemist is adding reagent or changing temperature
    and runs are overwhelmingly in chronological order.  The real time
    gap between the last sample of group N-1 and the first sample of
    group N is used as the inter-group offset.  Within-group ordering
    also follows acquisition timestamps.

    Args:
        sorted_groups:  TrackingGroup list sorted by median time.
        result:         BatchResult whose files dict will be updated.
        run_datetimes:  Optional mapping of filename → "YYYY-MM-DD HH:MM:SS".
                        When None, falls back to arbitrary +100 min gap
                        (suitable for categorization-time before PDFs are parsed).
    """
    from datetime import datetime as _dt

    if not sorted_groups:
        return

    prev_max_sk = 0.0
    prev_max_fn = None     # filename of file with highest sort_key in prev group

    for i, group in enumerate(sorted_groups):
        if i == 0:
            # Group 1: ONLY filename-derived time tokens
            group.offset = 0.0
            for fn, time_min in group.files:
                result.files[fn].sort_key = time_min
            if group.files:
                prev_max_sk = max(t for _, t in group.files)
                prev_max_fn = max(group.files, key=lambda x: x[1])[0]
        else:
            # Groups 2+: use real PDF timestamps if available
            real_gap_used = False

            if run_datetimes and prev_max_fn:
                prev_dt_str = run_datetimes.get(prev_max_fn)

                # Sort THIS group by acquisition time (not filename tokens)
                group_with_dt = [(fn, t, run_datetimes.get(fn))
                                 for fn, t in group.files]
                has_all_dt = (prev_dt_str is not None and
                              all(dt is not None for _, _, dt in group_with_dt))

                if has_all_dt:
                    try:
                        prev_dt = _dt.strptime(prev_dt_str,
                                               "%Y-%m-%d %H:%M:%S")
                        # Re-sort group files by acquisition time
                        group_with_dt.sort(key=lambda x: x[2])
                        group.files = [(fn, t) for fn, t, _ in group_with_dt]

                        # Assign sort keys: offset from prev group's last file
                        for fn, _orig_t, dt_str in group_with_dt:
                            curr_dt = _dt.strptime(dt_str,
                                                   "%Y-%m-%d %H:%M:%S")
                            offset_min = (curr_dt - prev_dt).total_seconds() / 60
                            if offset_min < 0:
                                offset_min = 0  # safety: clock skew
                            result.files[fn].sort_key = (prev_max_sk
                                                         + offset_min)

                        group.offset = prev_max_sk
                        prev_max_sk = max(result.files[fn].sort_key
                                          for fn, _ in group.files)
                        prev_max_fn = max(group.files,
                                          key=lambda x: result.files[x[0]].sort_key)[0]
                        real_gap_used = True
                    except (ValueError, TypeError):
                        pass  # fall through to fallback

            if not real_gap_used:
                # Fallback: arbitrary +100 min gap
                group.offset = prev_max_sk + 100
                for fn, time_min in group.files:
                    result.files[fn].sort_key = group.offset + time_min
                prev_max_sk = max(result.files[fn].sort_key
                                  for fn, _ in group.files)
                prev_max_fn = max(group.files, key=lambda x: x[1])[0]
