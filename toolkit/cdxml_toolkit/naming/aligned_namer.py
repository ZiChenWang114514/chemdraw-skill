"""
aligned_namer.py — Aligned IUPAC Name Generation

Pairwise alignment (SM→product pairs) and multi-step sequence alignment
for synthetic routes.

Uses name_decomposer to exhaustively generate alternative names for each
molecule, then picks names that share the same naming parent, making the
transformation obvious from the names alone.

Multi-step sequences use parent-aware dynamic programming (Viterbi) to
minimise parent-ring switches first, then chemistry-aware token diff as
tiebreaker.

Usage:
    python aligned_namer.py --sm "BrC1=CC=CC=C1" --product "C1=CC=C(C2=CC=NC=C2)C=C1"
    python aligned_namer.py --showcase  # run on all showcase reactions
    python aligned_namer.py --showcase --report alignment_report.txt
"""
import argparse
import difflib
import html as html_mod
import re
import sys
import os
import glob
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from rdkit import Chem, RDLogger
from rdkit.Chem import rdFMCS
RDLogger.logger().setLevel(RDLogger.ERROR)

from cdxml_toolkit.naming.name_decomposer import (
    decompose_name, DecompositionResult, name_fragment_as_substituent,
    _validate_name, _canonical, _name_to_smiles,
)

try:
    from rdkit.Chem.inchi import MolToInchi
except ImportError:
    MolToInchi = None  # type: ignore[assignment]


def _validate_variant(name: str, expected_canonical: str) -> bool:
    """Validate a variant name resolves to the same molecule.

    First tries canonical SMILES comparison (fast).  Falls back to
    InChI comparison to handle tautomers (e.g. quinazolinone NH position).
    """
    if _validate_name(name, expected_canonical):
        return True
    # Canonical SMILES didn't match — try InChI (tautomer-tolerant)
    if MolToInchi is None:
        return False
    smi = _name_to_smiles(name)
    if smi is None:
        return False
    try:
        mol_variant = Chem.MolFromSmiles(smi)
        mol_expected = Chem.MolFromSmiles(expected_canonical)
        if mol_variant is None or mol_expected is None:
            return False
        return MolToInchi(mol_variant) == MolToInchi(mol_expected)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Levenshtein distance
# ---------------------------------------------------------------------------

def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            # insertion, deletion, substitution
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if c1 == c2 else 1)
            ))
        prev = curr
    return prev[-1]


def name_similarity(name1: str, name2: str) -> float:
    """Compute similarity between two names as 1 - normalized Levenshtein.

    Returns a float in [0, 1] where 1.0 means identical.
    """
    if not name1 or not name2:
        return 0.0
    dist = _levenshtein(name1.lower(), name2.lower())
    max_len = max(len(name1), len(name2))
    return 1.0 - (dist / max_len) if max_len > 0 else 0.0


# ---------------------------------------------------------------------------
# Chemistry-aware tokeniser
# ---------------------------------------------------------------------------

# Ring system names (ordered longest-first for greedy matching)
_RING_SYSTEMS = sorted([
    "quinoline", "isoquinoline", "quinoxaline", "quinazoline",
    "pyridine", "pyrimidine", "pyrazine", "pyridazine",
    "benzene", "naphthalene", "anthracene",
    "indole", "benzimidazole", "benzothiazole", "benzofuran", "benzoxazole",
    "thiophene", "furan", "pyrrole", "imidazole", "oxazole",
    "thiazole", "triazine", "tetrazole", "triazole", "oxadiazole",
    "morpholine", "piperidine", "piperazine", "pyrrolidine",
    "carbazole", "acridine", "phenanthroline",
    "thienopyrimidine", "isoindoline", "isoindole",
    "carbamate", "benzamide", "acetamide",
    # Additional heterocycles common in drug synthesis
    "pyrazole", "isoxazole", "isothiazole",
    "oxazolidine", "oxazolidinone", "thiazolidine",
    "tetrahydronaphthalene", "dihydronaphthalene",
    "phthalazine", "cinnoline",
    "purine", "xanthine",
    "azetidine", "aziridine", "oxetane", "thietane",
    "diazepine", "oxazepine",
    # Retained names (for tokenizer splitting: "dimethylaniline" → "dimethyl"+"aniline")
    "aniline", "phenol", "benzenol",
    "anisole", "benzaldehyde", "acetophenone", "styrene",
], key=len, reverse=True)

_SUBSTITUENT_PREFIXES = sorted([
    "amino", "bromo", "chloro", "fluoro", "iodo", "nitro",
    "methyl", "ethyl", "propyl", "butyl", "phenyl", "benzyl",
    "methoxy", "ethoxy", "hydroxy", "oxo", "formyl",
    "methoxycarbonyl", "ethoxycarbonyl", "carbamoyl", "carboxy", "cyano",
    "morpholino", "morpholin", "piperidin", "pyrrolidin", "piperazin",
    "benzamido", "acetamido", "acetyl",
    "tert", "sec", "iso", "cyclo",
], key=len, reverse=True)

_MULTIPLIERS = {"di", "tri", "tetra", "penta", "hexa", "bis", "tris"}
_STEREO = {"r", "s", "e", "z", "cis", "trans", "rac", "dl", "meso"}


_LINKERS = frozenset({
    'yl', 'oxy', 'oyl', 'amido', 'amino', 'thio', 'sulfonyl',
    'amine', 'ol', 'one', 'thiol',
})
_FG_SUFFIXES = ('amine', 'amide', 'thiol', 'aldehyde', 'nitrile')


def _classify_token(tok: str, out: list) -> None:
    """Recursively classify and split a single IUPAC token.

    Appends (token, category) tuples to *out*.
    """
    if not tok:
        return

    # 1. Locant
    if re.match(r'^\d+(?:,\d+)*$', tok):
        out.append((tok, 'locant'))
        return

    # 2. Ring match (longest ring first — _RING_SYSTEMS is pre-sorted)
    for ring in _RING_SYSTEMS:
        if tok == ring or tok.endswith(ring):
            prefix = tok[:len(tok) - len(ring)]
            if prefix:
                _classify_token(prefix, out)  # recurse on prefix
            out.append((ring, 'ring'))
            return

    # 3. Exact multiplier / stereo / linker
    if tok in _MULTIPLIERS:
        out.append((tok, 'multiplier'))
        return
    if tok in _STEREO:
        out.append((tok, 'stereo'))
        return
    if tok in _LINKERS:
        out.append((tok, 'linker'))
        return

    # 4. Exact substituent prefix
    for sub in _SUBSTITUENT_PREFIXES:
        if tok == sub:
            out.append((sub, 'substituent'))
            return

    # 5. Split on substituent suffix (longest match first)
    #    E.g. "dimethylphenyl" → "dimethyl" + "phenyl"
    for sub in _SUBSTITUENT_PREFIXES:
        if tok.endswith(sub) and len(tok) > len(sub):
            _classify_token(tok[:-len(sub)], out)  # recurse on prefix
            out.append((sub, 'substituent'))
            return

    # 6. Split on functional group suffix
    #    E.g. "phenylamine" → "phenyl" + "amine"
    for fg in _FG_SUFFIXES:
        if tok.endswith(fg) and len(tok) > len(fg):
            _classify_token(tok[:-len(fg)], out)  # recurse on prefix
            out.append((fg, 'linker'))
            return

    # 7. Fallback
    out.append((tok, 'other'))


def _tokenize_name_chem(name: str) -> List[Tuple[str, str]]:
    """Chemistry-aware IUPAC name tokeniser.

    Returns list of (token, category) tuples where category is one of:
    locant, ring, substituent, multiplier, stereo, linker, other.
    """
    result: List[Tuple[str, str]] = []
    s = name.lower().strip()
    raw = re.findall(r'\d+(?:,\d+)*|[a-z]+|\S', s)

    for tok in raw:
        if not tok or tok in ('(', ')', '-', ',', '[', ']', ' '):
            continue
        _classify_token(tok, result)

    return result


def _chem_tokens_flat(name: str) -> List[str]:
    """Get just the token strings from chemistry-aware tokeniser."""
    return [tok for tok, _ in _tokenize_name_chem(name)]


def chem_token_diff_count(a: str, b: str) -> float:
    """Token diff count using chemistry-aware tokeniser with soft equivalences.

    Exact token mismatches cost 1.0 each.  Tokens that are chemically
    related (e.g. "phenyl"/"benzene", "aniline"/"phenylamine") contribute
    a reduced cost (0.3) instead of the full 1.0 per token.
    """
    ta = Counter(_chem_tokens_flat(a))
    tb = Counter(_chem_tokens_flat(b))
    # Work on copies so we can consume matching equivalences
    ra = dict(ta)   # residual counts for a
    rb = dict(tb)   # residual counts for b

    cost = 0.0

    # First pass: consume exact matches (cost = 0)
    for k in set(ra) & set(rb):
        matched = min(ra[k], rb[k])
        ra[k] -= matched
        rb[k] -= matched

    # Second pass: try soft equivalences on remaining tokens
    # Build residual sets (only tokens with count > 0)
    ra = {k: v for k, v in ra.items() if v > 0}
    rb = {k: v for k, v in rb.items() if v > 0}

    for tok_a, tok_b, n_consumed_a, n_consumed_b in _soft_equivalence_pairs(ra, rb):
        matched = min(ra.get(tok_a, 0) // n_consumed_a,
                      rb.get(tok_b, 0) // n_consumed_b)
        if matched > 0:
            ra[tok_a] = ra.get(tok_a, 0) - matched * n_consumed_a
            rb[tok_b] = rb.get(tok_b, 0) - matched * n_consumed_b
            if ra[tok_a] <= 0:
                ra.pop(tok_a, None)
            if rb[tok_b] <= 0:
                rb.pop(tok_b, None)
            cost += matched * _SOFT_EQUIV_COST

    # Remaining unmatched tokens cost 1.0 each
    cost += sum(v for v in ra.values())
    cost += sum(v for v in rb.values())

    return cost


# Soft equivalence: related tokens that should have reduced mismatch cost.
# Each entry: (token_a, token_b, count_a, count_b)
# Meaning: 1 of token_a ≈ 1 of token_b (consuming count_a and count_b respectively)
_SOFT_EQUIV_TABLE = [
    # Ring/substituent forms of the same moiety
    ("benzene", "phenyl", 1, 1),
    ("naphthalene", "naphthyl", 1, 1),
    # Retained → systematic (only entries where BOTH sides are single tokens
    # after _chem_tokens_flat; multi-token targets like "phenylamine" and
    # "methoxybenzene" are handled by _retained_systematic_variants instead)
    ("phenol", "benzenol", 1, 1),
    # Functional group name equivalences
    ("amine", "amino", 1, 1),
    ("ol", "hydroxy", 1, 1),
    ("one", "oxo", 1, 1),
    ("thiol", "sulfanyl", 1, 1),
    # Ester naming equivalences
    ("carboxylate", "carboxylic", 1, 1),
]
_SOFT_EQUIV_COST = 0.3  # cost per soft-equivalent pair (vs 1.0 for hard mismatch)


def _soft_equivalence_pairs(ra: dict, rb: dict):
    """Yield applicable (tok_a, tok_b, n_a, n_b) from the equivalence table.

    Only yields pairs where tok_a is in *ra* and tok_b is in *rb*,
    or vice versa (bidirectional).
    """
    for tok_a, tok_b, n_a, n_b in _SOFT_EQUIV_TABLE:
        if ra.get(tok_a, 0) >= n_a and rb.get(tok_b, 0) >= n_b:
            yield tok_a, tok_b, n_a, n_b
        elif ra.get(tok_b, 0) >= n_b and rb.get(tok_a, 0) >= n_a:
            yield tok_b, tok_a, n_b, n_a


# ---------------------------------------------------------------------------
# Parent ring extraction
# ---------------------------------------------------------------------------

# Known ring systems for parent classification.
# Fused names like "thieno[2,3-d]pyrimidine" are intentionally omitted —
# they contain "pyrimidine" as substring, so the simpler ring name matches.
# This avoids false switches when the decomposer reports different levels
# of specificity for the same scaffold.
_KNOWN_RINGS = {
    # 6-membered N-heterocycles
    "pyridine", "pyrimidine", "pyrazine", "pyridazine", "triazine",
    "pyran", "thiopyran",
    # 5-membered heterocycles
    "thiophene", "furan", "pyrrole", "imidazole", "oxazole",
    "thiazole", "tetrazole", "pyrazole", "isoxazole", "isothiazole",
    "triazole", "oxadiazole", "thiadiazole",
    "selenophene",
    # Saturated 5-membered
    "pyrrolidine", "oxazolidine", "thiazolidine", "dioxolane",
    # Saturated 6-membered
    "piperidine", "piperazine", "morpholine",
    "dioxane", "dithiane",
    # 3- and 4-membered
    "oxirane", "aziridine", "thiirane",
    "azetidine", "oxetane", "thietane",
    # 7-membered
    "diazepine", "oxazepine", "azepane", "azepine", "oxepane",
    # Benzo-fused N-heterocycles
    "quinoline", "isoquinoline", "quinoxaline", "quinazoline",
    "phthalazine", "cinnoline",
    "indole", "isoindole", "indazole", "indoline", "isoindoline",
    "benzimidazole", "benzotriazole",
    # Benzo-fused O/S heterocycles
    "benzofuran", "benzothiophene", "benzoxazole",
    "benzothiazole", "benzisoxazole", "benzisothiazole",
    "chromene", "chromone", "coumarin", "chroman",
    "benzodioxole", "benzodioxane",
    # Larger fused heterocycles
    "carbazole", "acridine", "phenanthroline",
    "phenothiazine", "phenoxazine", "phenazine", "phenanthridine",
    "purine", "xanthine", "xanthene", "pteridine",
    "naphthyridine", "benzodiazepine",
    # Fused N-rich (common in kinase inhibitors)
    "pyrrolopyrimidine", "pyrazolopyrimidine", "imidazopyridine",
    "pyrrolizine", "indolizine",
    "thienopyridine", "thienopyrimidine",
    # Drug-relevant lactams/imides
    "hydantoin",
    # Saturated fused / partial
    "tetrahydroisoquinoline", "tetrahydroquinoline",
    # Carbocycles — simple
    "benzene", "toluene", "naphthalene", "anthracene",
    "cyclopropane", "cyclobutane",
    "cyclopentane", "cyclopentene", "cyclopentadiene",
    "cyclohexane", "cyclohexene", "cyclohexadiene",
    "cycloheptane", "cyclooctane",
    # Carbocycles — polycyclic
    "indene", "indane", "fluorene", "phenanthrene", "azulene",
    "decalin", "tetralin",
    "adamantane", "norbornane",
    "biphenyl",
}


# Retained IUPAC names that map to a base ring system.
# These are trivially-substituted rings whose retained name doesn't
# contain the base ring string as a substring.
_RETAINED_TO_BASE = {
    # Benzene retained names
    "aniline": "benzene", "phenol": "benzene", "anisole": "benzene",
    "acetophenone": "benzene", "benzaldehyde": "benzene",
    "benzoic acid": "benzene", "styrene": "benzene",
    "catechol": "benzene", "resorcinol": "benzene",
    "hydroquinone": "benzene", "cresol": "benzene",
    "xylene": "benzene", "toluene": "benzene",
    "cumene": "benzene", "mesitylene": "benzene",
    # Naphthalene retained names
    "naphthol": "naphthalene",
    # Saturated/partial naphthalene
    "tetralin": "naphthalene", "decalin": "naphthalene",
    # Indene/indane family
    "indane": "indene",
}

# Pre-compute elided stems: "quinazoline" → "quinazolin", etc.
# IUPAC drops terminal 'e' before vowel-starting suffixes (-ol, -one, -amine).
_KNOWN_RING_STEMS = {}
for _ring in _KNOWN_RINGS:
    if _ring.endswith('e'):
        _KNOWN_RING_STEMS[_ring[:-1]] = _ring
    _KNOWN_RING_STEMS[_ring] = _ring

# Pre-sorted versions for hot-path functions (extract_parent_ring, etc.)
# Avoids re-sorting on every call inside the DP inner loop.
_KNOWN_RINGS_BY_LEN = sorted(_KNOWN_RINGS, key=len, reverse=True)
_KNOWN_RING_STEMS_BY_LEN = sorted(_KNOWN_RING_STEMS, key=len, reverse=True)


def _strip_locants(s: str) -> str:
    """Remove IUPAC locant insertions so ring substrings become contiguous.

    E.g. "cyclohex-1-ene-1-carboxylate" → "cyclohexenecarboxylate"
    """
    return re.sub(r'-[\d,()H]+-', '', s)


def extract_parent_ring(parent: str) -> str:
    """Extract core ring system from a parent name string.

    Checks (in order):
    1. Known ring names as substrings, longest first
    2. Elided stems (e.g. "quinazolin" for "quinazoline")
    3. Locant-stripped matching (handles "cyclohex-1-ene" → "cyclohexene")
    4. Retained name → base ring mapping
    5. "phenyl" in name → benzene (chain compounds with phenyl substituent)
    6. Suffix patterns (e.g. "-phenone" → benzene)
    7. Fallback: lowered parent string
    """
    p = parent.lower().strip()
    # 1. Direct ring match (longest first)
    for ring in _KNOWN_RINGS_BY_LEN:
        if ring in p:
            return _RETAINED_TO_BASE.get(ring, ring)
    # 2. Elided stem match (longest first) — handles vowel elision
    #    e.g. "quinazolin-4-one" matches stem "quinazolin" → "quinazoline"
    for stem in _KNOWN_RING_STEMS_BY_LEN:
        if stem in p:
            ring = _KNOWN_RING_STEMS[stem]
            return _RETAINED_TO_BASE.get(ring, ring)
    # 3. Locant-stripped matching — handles "cyclohex-1-ene" → "cyclohexene"
    p_stripped = _strip_locants(p)
    if p_stripped != p:
        for ring in _KNOWN_RINGS_BY_LEN:
            if ring in p_stripped:
                return _RETAINED_TO_BASE.get(ring, ring)
        for stem in _KNOWN_RING_STEMS_BY_LEN:
            if stem in p_stripped:
                ring = _KNOWN_RING_STEMS[stem]
                return _RETAINED_TO_BASE.get(ring, ring)
    # 4. Retained names
    for retained, base in _RETAINED_TO_BASE.items():
        if retained in p:
            return base
    # 5. "phenyl" in name → benzene (chain compounds like "1-phenylpropan-1-ol")
    if "phenyl" in p:
        return "benzene"
    # 6. Suffix patterns
    if p.endswith("phenone") or p.endswith("phenol"):
        return "benzene"
    # 7. Names starting with "benz"
    if p.startswith("benz"):
        return "benzene"
    return p


# ---------------------------------------------------------------------------
# Post-hoc alignment variant generator
# ---------------------------------------------------------------------------
# Expands the candidate name set with IUPAC-equivalent alternatives that
# the decomposer may not have produced, specifically:
#   1. Ester naming: "alkyl X-ate" ↔ "X-ic acid alkyl ester"
#   2. Retained→systematic: "aniline" → "phenylamine", etc.
#   3. Indicated-H lactam suffix→prefix: "-4(3H)-one" → "4-oxo-"

_COMMON_ALKYL_ESTERS = {
    "methyl", "ethyl", "propyl", "isopropyl", "butyl", "tert-butyl",
    "isobutyl", "sec-butyl", "benzyl", "allyl", "phenyl", "vinyl",
    "neopentyl", "cyclopentyl", "cyclohexyl",
}

# Alkyl → alkoxy mapping for ester suffix→prefix conversion.
# "methyl X-carboxylate" → "(methoxycarbonyl)X"
_ALKYL_TO_ALKOXY = {
    "methyl": "methoxy", "ethyl": "ethoxy", "propyl": "propoxy",
    "isopropyl": "isopropoxy", "butyl": "butoxy",
    "tert-butyl": "tert-butoxy", "isobutyl": "isobutoxy",
    "sec-butyl": "sec-butoxy", "benzyl": "benzyloxy",
    "allyl": "allyloxy", "phenyl": "phenoxy", "vinyl": "vinyloxy",
    "neopentyl": "neopentyloxy", "cyclopentyl": "cyclopentyloxy",
    "cyclohexyl": "cyclohexyloxy",
}
_ALKOXY_TO_ALKYL = {v: k for k, v in _ALKYL_TO_ALKOXY.items()}


def _ester_variants(name: str, parent: str) -> List[Tuple[str, str]]:
    """Generate ester naming alternatives.

    "ethyl X-carboxylate"  →  "X-carboxylic acid ethyl ester"
    "X-ic acid alkyl ester"  →  "alkyl X-ate"
    """
    variants: List[Tuple[str, str]] = []

    # Direction 1: "alkyl ...ate" → "...ic acid alkyl ester"
    parts = name.split(None, 1)
    if len(parts) == 2:
        first = parts[0]
        rest = parts[1]
        if first.lower() in _COMMON_ALKYL_ESTERS and rest.endswith("ate"):
            acid_form = rest[:-3] + "ic acid"
            variant = acid_form + " " + first + " ester"
            # Parent: use the acid form as parent (same ring)
            acid_parent = parent
            if parent and parent.endswith("ate"):
                acid_parent = parent[:-3] + "ic acid"
            variants.append((variant, acid_parent))

    # Direction 2: "...ic acid alkyl ester" → "alkyl ...ate"
    m = re.match(r'^(.+ic acid)\s+(\S+)\s+ester$', name, re.IGNORECASE)
    if m:
        acid_part = m.group(1)
        alkyl = m.group(2)
        # "Xic acid" → "Xate"  (strip "ic acid" = 7 chars, append "ate")
        ester_form = alkyl + " " + acid_part[:-7] + "ate"
        variants.append((ester_form, parent))

    return variants


# Retained IUPAC name → systematic alternative(s).
# Includes both the base retained name and common derivatives.
_RETAINED_TO_SYSTEMATIC = {
    # Benzene derivatives
    "aniline": "phenylamine",
    "phenol": "benzenol",
    "anisole": "methoxybenzene",
    "benzaldehyde": "benzenecarbaldehyde",
    "acetophenone": "1-phenylethanone",
    "styrene": "ethenylbenzene",
    "catechol": "benzene-1,2-diol",
    "resorcinol": "benzene-1,3-diol",
    "hydroquinone": "benzene-1,4-diol",
    "cresol": "methylphenol",
    "toluene": "methylbenzene",
    "xylene": "dimethylbenzene",
    "cumene": "isopropylbenzene",
    # Naphthalene derivatives
    "naphthol": "naphthalenol",
    # Common heterocycle retained names
    "nicotinamide": "pyridine-3-carboxamide",
    "nicotinic acid": "pyridine-3-carboxylic acid",
    "salicylaldehyde": "2-hydroxybenzaldehyde",
    "salicylic acid": "2-hydroxybenzoic acid",
}


def _retained_systematic_variants(
    name: str, parent: str,
) -> List[Tuple[str, str]]:
    """Generate systematic IUPAC alternatives for retained names.

    E.g. "2,6-dimethylaniline" → "2,6-dimethylphenylamine"
    """
    variants: List[Tuple[str, str]] = []
    name_lower = name.lower()

    for retained, systematic in _RETAINED_TO_SYSTEMATIC.items():
        if retained in name_lower:
            idx = name_lower.index(retained)
            # Preserve original case of prefix
            variant = name[:idx] + systematic + name[idx + len(retained):]
            # Parent: replace retained name in parent too
            if parent:
                parent_lower = parent.lower()
                if retained in parent_lower:
                    pidx = parent_lower.index(retained)
                    new_parent = parent[:pidx] + systematic + parent[pidx + len(retained):]
                else:
                    new_parent = parent
            else:
                new_parent = variant
            variants.append((variant, new_parent))

    # Also generate reverse: systematic → retained
    for retained, systematic in _RETAINED_TO_SYSTEMATIC.items():
        if systematic in name_lower and retained not in name_lower:
            idx = name_lower.index(systematic)
            variant = name[:idx] + retained + name[idx + len(systematic):]
            if parent:
                parent_lower = parent.lower()
                if systematic in parent_lower:
                    pidx = parent_lower.index(systematic)
                    new_parent = parent[:pidx] + retained + parent[pidx + len(systematic):]
                else:
                    new_parent = parent
            else:
                new_parent = variant
            variants.append((variant, new_parent))

    return variants


def _indicated_h_variants(name: str, parent: str) -> List[Tuple[str, str]]:
    """Generate suffix→prefix variants for indicated-H lactam names.

    E.g. "6,7-dimethoxyquinazolin-4(3H)-one" → "4-oxo-6,7-dimethoxyquinazoline"

    The decomposer's suffix→prefix sometimes fails for names with
    indicated-hydrogen notation like (3H), (1H), etc.
    """
    variants: List[Tuple[str, str]] = []

    suffix_map = {
        "one": "oxo",
        "ol": "hydroxy",
        "amine": "amino",
        "thione": "thioxo",
    }

    name_lower = name.lower()

    for suffix, prefix in suffix_map.items():
        # Look for "STEM-LOCANT(IH)-SUFFIX" where STEM is a known ring stem
        tail_pattern = r'-(\d+)\(\d+[hH]\)-' + re.escape(suffix) + r'$'
        tail_m = re.search(tail_pattern, name_lower)
        if not tail_m:
            continue

        locant = tail_m.group(1)
        before_locant = name[:tail_m.start()]  # everything before "-LOCANT(IH)-SUFFIX"

        # Find the longest known ring stem at the END of before_locant
        best_stem = None
        best_ring = None
        for stem, ring in _KNOWN_RING_STEMS.items():
            if before_locant.lower().endswith(stem):
                if best_stem is None or len(stem) > len(best_stem):
                    best_stem = stem
                    best_ring = ring

        if best_stem:
            # Split: leading substituents + ring
            leading = before_locant[:len(before_locant) - len(best_stem)]

            # Build variant: "LOCANT-PREFIX-LEADING-RING_FULL"
            # E.g. "4-oxo-6,7-dimethoxyquinazoline"
            if leading:
                variant = locant + "-" + prefix + "-" + leading + best_ring
            else:
                variant = locant + "-" + prefix + best_ring
            variant = re.sub(r'-{2,}', '-', variant)
            variant = variant.strip('-')

            new_parent = variant
            variants.append((variant, new_parent))

    return variants


def _general_suffix_prefix_variants(name: str, parent: str) -> List[Tuple[str, str]]:
    """Generate suffix→prefix variants for standard IUPAC names.

    Handles names WITHOUT indicated-H, e.g.:
      "pyridin-2-amine"  → "2-aminopyridine"
      "naphthalen-1-ol"  → "1-hydroxynapthalene"

    Complements _indicated_h_variants which handles (NH) notation.
    """
    variants: List[Tuple[str, str]] = []
    name_lower = name.lower()

    suffix_map = {
        "amine": "amino",
        "ol": "hydroxy",
        "one": "oxo",
        "thiol": "sulfanyl",
    }

    for suffix, prefix in suffix_map.items():
        # Pattern: "ring-LOCANT-SUFFIX" at the end
        # E.g. "pyridin-2-amine", "naphthalen-1-ol"
        # Must NOT have indicated-H (handled by _indicated_h_variants)
        pattern = r'-(\d+(?:,\d+)*)-' + re.escape(suffix) + r'$'
        m = re.search(pattern, name_lower)
        if not m:
            continue

        # Skip if there's an indicated-H right before the suffix
        if re.search(r'\(\d+[hH]\)-' + re.escape(suffix) + r'$', name_lower):
            continue

        locants = m.group(1)
        before = name[:m.start()]  # everything before "-LOCANT-SUFFIX"

        # Find longest known ring stem at the end of 'before'
        best_stem = None
        best_ring = None
        for stem, ring in _KNOWN_RING_STEMS.items():
            if before.lower().endswith(stem):
                if best_stem is None or len(stem) > len(best_stem):
                    best_stem = stem
                    best_ring = ring

        if best_stem:
            leading = before[:len(before) - len(best_stem)]
            if leading:
                # E.g. "6,7-dimethoxypyridin-2-amine" →
                #      "2-amino-6,7-dimethoxypyridine"
                variant = locants + "-" + prefix + "-" + leading + best_ring
            else:
                # E.g. "pyridin-2-amine" → "2-aminopyridine"
                variant = locants + "-" + prefix + best_ring
            variant = re.sub(r'-{2,}', '-', variant)
            variant = variant.strip('-')
            variants.append((variant, variant))

    return variants


# ---------------------------------------------------------------------------
# Extended suffix→prefix for principal characteristic groups
# ---------------------------------------------------------------------------
# Suffixes that extend beyond the parent ring stem (carboxylate,
# carbaldehyde, carboxamide, carbonitrile, carboxylic acid).
# These follow the same ring_stem-LOCANT-SUFFIX pattern as the simple
# suffixes handled by _general_suffix_prefix_variants, but the suffix
# words themselves are longer and sometimes require an alkyl ester prefix.

# (suffix, prefix_or_None, needs_alkyl_prefix, wrap_in_parens)
# When needs_alkyl_prefix is True, the prefix is built from the
# space-separated first word of the name (e.g. "methyl" → "methoxycarbonyl").
_EXTENDED_SUFFIX_TABLE: List[Tuple[str, Optional[str], bool, bool]] = [
    ("carboxylic acid", "carboxy",   False, False),
    ("carboxamide",     "carbamoyl", False, True),
    ("carbaldehyde",    "formyl",    False, False),
    ("carbonitrile",    "cyano",     False, False),
    ("carboxylate",     None,        True,  True),   # prefix from alkyl
]


def _extended_suffix_prefix_variants(
    name: str, parent: str,
) -> List[Tuple[str, str]]:
    """Generate suffix→prefix variants for principal characteristic groups.

    Handles suffixes that extend beyond the parent ring stem:
      "methyl 2-(methylthio)thieno[2,3-d]pyrimidine-4-carboxylate"
        → "2-(methylthio)-4-(methoxycarbonyl)thieno[2,3-d]pyrimidine"
      "2-(methylthio)thieno[2,3-d]pyrimidine-4-carbaldehyde"
        → "2-(methylthio)-4-formylthieno[2,3-d]pyrimidine"

    Algorithm mirrors _general_suffix_prefix_variants: find the suffix at
    the end of the name, locate the ring stem before it, and reconstruct
    with the prefix form prepended.
    """
    variants: List[Tuple[str, str]] = []

    for suffix, prefix, needs_alkyl, wrap in _EXTENDED_SUFFIX_TABLE:
        # Work on a potentially trimmed name (alkyl stripped for esters)
        work_name = name
        alkyl = None

        if needs_alkyl:
            parts = name.split(None, 1)
            if len(parts) != 2:
                continue
            if parts[0].lower() not in _ALKYL_TO_ALKOXY:
                continue
            alkyl = parts[0]
            work_name = parts[1]

        work_lower = work_name.lower()

        # Match "-LOCANT-SUFFIX" (or " SUFFIX" for multi-word) at the end
        if " " in suffix:
            # Multi-word suffix like "carboxylic acid"
            pattern = r'-(\d+(?:,\d+)*)-' + re.escape(suffix) + r'$'
        else:
            pattern = r'-(\d+(?:,\d+)*)-' + re.escape(suffix) + r'$'

        m = re.search(pattern, work_lower)
        if not m:
            continue

        locants = m.group(1)
        before = work_name[:m.start()]    # everything before "-LOCANT-SUFFIX"

        # Find longest known ring stem at the end of 'before'
        before_lower = before.lower()
        best_stem = None
        best_ring = None
        for stem, ring in _KNOWN_RING_STEMS.items():
            if before_lower.endswith(stem):
                if best_stem is None or len(stem) > len(best_stem):
                    best_stem = stem
                    best_ring = ring

        if best_stem is None:
            continue

        leading = before[:len(before) - len(best_stem)]

        # Build the prefix
        if needs_alkyl and alkyl is not None:
            alkoxy = _ALKYL_TO_ALKOXY[alkyl.lower()]
            prefix = f"{alkoxy}carbonyl"
            wrap = True

        if prefix is None:
            continue

        pref = f"({prefix})" if wrap else prefix

        # Reconstruct: LOCANT-PREFIX-LEADING-RING
        if leading:
            variant = locants + "-" + pref + "-" + leading + best_ring
        else:
            variant = locants + "-" + pref + best_ring
        variant = re.sub(r'-{2,}', '-', variant)
        variant = variant.strip('-')

        new_parent = best_ring
        variants.append((variant, new_parent))

    return variants


def _extended_prefix_to_suffix_variants(
    name: str, parent: str,
) -> List[Tuple[str, str]]:
    """Generate prefix→suffix variants for principal characteristic groups.

    Reverse of _extended_suffix_prefix_variants:
      "2-(methylthio)-4-(methoxycarbonyl)thieno[2,3-d]pyrimidine"
        → "methyl 2-(methylthio)thieno[2,3-d]pyrimidine-4-carboxylate"
      "4-formyl-2-(methylthio)thieno[2,3-d]pyrimidine"
        → "2-(methylthio)thieno[2,3-d]pyrimidine-4-carbaldehyde"

    Detects known prefix patterns in the name's substituent chain and
    converts them to suffix form appended after the ring stem.
    """
    variants: List[Tuple[str, str]] = []
    name_lower = name.lower()

    # Table: (prefix_to_detect, suffix, produces_alkyl)
    # For alkoxycarbonyl, we iterate over _ALKOXY_TO_ALKYL entries.
    simple_prefix_map = [
        ("carboxy",   "carboxylic acid", False),
        ("carbamoyl", "carboxamide",     False),
        ("formyl",    "carbaldehyde",    False),
        ("cyano",     "carbonitrile",    False),
    ]

    # --- Simple prefixes (no alkyl) ---
    for prefix, suffix, _ in simple_prefix_map:
        # Match "LOCANT-PREFIX" or "LOCANT-(PREFIX)" in the name
        # Try with parentheses first
        for pfx_pat in [re.escape(f"({prefix})"), re.escape(prefix)]:
            pat = r'(\d+(?:,\d+)*)-' + pfx_pat + r'[-]?'
            m_pref = re.search(pat, name_lower)
            if m_pref:
                break
        else:
            continue

        locants = m_pref.group(1)

        # Remove the matched prefix group from the name
        before_match = name[:m_pref.start()]
        after_match = name[m_pref.end():]
        core = before_match + after_match
        core = re.sub(r'-{2,}', '-', core)
        core = core.strip('-')

        # Find ring stem in core to build suffix form
        core_lower = core.lower()
        best_stem = None
        best_ring = None
        for stem, ring in _KNOWN_RING_STEMS.items():
            if stem in core_lower:
                if best_stem is None or len(stem) > len(best_stem):
                    best_stem = stem
                    best_ring = ring

        if best_stem is None:
            continue

        # Find where the stem ends in core, insert "-LOCANT-SUFFIX" there
        stem_idx = core_lower.rfind(best_stem)
        stem_end = stem_idx + len(best_stem)

        # Include trailing 'e' if present (elided stem → full ring)
        if (stem_end < len(core) and core[stem_end].lower() == 'e'
                and best_ring.endswith('e') and not best_stem.endswith('e')):
            stem_end += 1

        variant = core[:stem_end] + "-" + locants + "-" + suffix + core[stem_end:]
        variant = re.sub(r'-{2,}', '-', variant)
        variant = variant.strip('-')
        variants.append((variant, parent))

    # --- Ester prefixes: (alkoxycarbonyl) → alkyl ... carboxylate ---
    for alkoxy, alkyl in _ALKOXY_TO_ALKYL.items():
        target = f"({alkoxy}carbonyl)"
        target_lower = target.lower()
        idx = name_lower.find(target_lower)
        if idx < 0:
            continue

        # Find locant before the prefix
        before_target = name[:idx]
        m_loc = re.search(r'(\d+(?:,\d+)*)-$', before_target)
        if not m_loc:
            continue

        locants = m_loc.group(1)

        # Remove the matched "LOCANT-(alkoxycarbonyl)" from the name
        before_loc = name[:m_loc.start()].rstrip('-')
        after_target = name[idx + len(target):].lstrip('-')
        core = before_loc + after_target
        core = re.sub(r'-{2,}', '-', core)
        core = core.strip('-')

        # Find ring stem to append suffix
        core_lower = core.lower()
        best_stem = None
        best_ring = None
        for stem, ring in _KNOWN_RING_STEMS.items():
            if stem in core_lower:
                if best_stem is None or len(stem) > len(best_stem):
                    best_stem = stem
                    best_ring = ring

        if best_stem is None:
            continue

        stem_idx = core_lower.rfind(best_stem)
        stem_end = stem_idx + len(best_stem)
        if (stem_end < len(core) and core[stem_end].lower() == 'e'
                and best_ring.endswith('e') and not best_stem.endswith('e')):
            stem_end += 1

        suffix_part = core[:stem_end] + "-" + locants + "-carboxylate" + core[stem_end:]
        variant = alkyl + " " + suffix_part
        variant = re.sub(r'-{2,}', '-', variant)
        variants.append((variant, parent))

    return variants


def _find_locant_group_starts(text: str) -> List[int]:
    """Find starting positions of top-level locant-prefix groups in *text*.

    A locant group starts with ``\\d+(,\\d+)*-`` at bracket depth 0.
    """
    starts: List[int] = []
    i = 0
    depth = 0
    while i < len(text):
        c = text[i]
        if c in '([':
            depth += 1
            i += 1
        elif c in ')]':
            depth -= 1
            i += 1
        elif c.isdigit() and depth == 0:
            j = i
            while j < len(text) and (
                    text[j].isdigit() or text[j] == ','):
                j += 1
            if j < len(text) and text[j] == '-':
                starts.append(i)
            i = max(i + 1, j)
        else:
            i += 1
    return starts


def _reorder_locant_prefixes(name: str, parent: str) -> Optional[str]:
    """Reorder top-level locant-prefix groups to ascending locant order.

    IUPAC convention requires substituent prefixes to appear in ascending
    locant order.  E.g.:

        "5-(chlorosulfonyl)-2-ethoxybenzoic acid"   (parent "benzoic acid")
      → "2-ethoxy-5-(chlorosulfonyl)benzoic acid"

    *parent* is needed to locate the boundary between the prefix section
    and the parent stem.  Returns the reordered name, or ``None`` if the
    name is already in ascending order or cannot be parsed.
    """
    if not parent:
        return None

    name_lower = name.lower()
    parent_lower = parent.lower().strip()

    # --- Collect candidate parent-stem positions -------------------------
    # Multiple strategies are needed because the decomposer's parent may
    # include substituent prefixes (e.g. "2-ethoxybenzoic acid" instead
    # of "benzoic acid").  We try all strategies and pick the first
    # candidate that yields ≥ 2 non-ascending locant groups.
    candidates: List[int] = []

    # Strategy 1: Literal parent match
    idx = name_lower.rfind(parent_lower)
    if idx > 0:
        candidates.append(idx)

    # Strategy 2: Elided form ("quinazoline" → "quinazolin")
    if parent_lower.endswith('e'):
        idx = name_lower.rfind(parent_lower[:-1])
        if idx > 0:
            candidates.append(idx)

    ring = extract_parent_ring(parent_lower)

    # Strategy 3: Known ring stems derived from the parent ring
    if ring and ring != parent_lower:
        for stem in _KNOWN_RING_STEMS_BY_LEN:
            if _KNOWN_RING_STEMS[stem].lower() == ring:
                idx = name_lower.rfind(stem)
                if idx > 0:
                    candidates.append(idx)
                    break

    # Strategy 4: Ring-name marker for retained acid names
    # E.g. "benzoic acid" → ring "benzene" → marker "benz" finds the
    # parent position even though "benzene"/"benzen" aren't in "benzoic".
    if ring and len(ring) >= 3:
        for end in range(len(ring), 2, -1):
            marker = ring[:end]
            idx = name_lower.rfind(marker)
            if idx > 0:
                candidates.append(idx)
                break

    if not candidates:
        return None

    # --- Try each candidate, use the first that yields a reordering ------
    # Sort candidates ascending so smaller (= longer prefix section) first.
    for parent_pos in sorted(set(candidates)):
        prefix_section = name[:parent_pos]
        parent_section = name[parent_pos:]

        group_starts = _find_locant_group_starts(prefix_section)
        if len(group_starts) <= 1:
            continue  # try next candidate

        # Extract (first_locant_value, group_text) for each group
        groups: List[Tuple[int, str]] = []
        for idx_g, start in enumerate(group_starts):
            end = (group_starts[idx_g + 1]
                   if idx_g + 1 < len(group_starts)
                   else len(prefix_section))
            group_text = prefix_section[start:end]
            m = re.match(r'(\d+)', group_text)
            first_loc = int(m.group(1)) if m else 0
            groups.append((first_loc, group_text))

        # Already in ascending order?
        locs = [g[0] for g in groups]
        if locs == sorted(locs):
            continue  # no reordering needed at this split point

        before = prefix_section[:group_starts[0]]
        sorted_groups = sorted(groups, key=lambda g: g[0])

        # Reassemble: strip trailing '-' from each part, join with '-'
        parts = [g[1].rstrip('-') for g in sorted_groups]
        new_prefix = '-'.join(parts)

        result = before + new_prefix + parent_section
        result = re.sub(r'-{2,}', '-', result)
        return result

    return None


# ---------------------------------------------------------------------------
# Retained name → substitutive prefix + ring decomposition
# ---------------------------------------------------------------------------
# Retained names like "aniline" are systematically "aminobenzene" (prefix
# + ring).  When the retained name appears as a parent with numbered
# substituent prefixes (e.g. "4-fluoroaniline"), we can generate the
# fully substitutive form "4-fluoro-1-aminobenzene" where the retained
# name's defining substituent gets its own locant.  This often yields a
# closer text match in aligned sequences.

# (retained_name, substituent_prefix, ring_name, default_locant)
# default_locant: position of the defining substituent in the standard
# numbering.  None means the retained name is used for multiple isomers
# (e.g. naphthol can be 1- or 2-).
_RETAINED_SUBSTITUTIVE = [
    ("aniline", "amino", "benzene", "1"),
    ("phenol", "hydroxy", "benzene", "1"),
    ("anisole", "methoxy", "benzene", "1"),
    ("thiophenol", "sulfanyl", "benzene", "1"),
    ("naphthol", "hydroxy", "naphthalene", None),
]


def _retained_to_substitutive_variants(
    name: str, parent: str,
) -> List[Tuple[str, str]]:
    """Generate fully substitutive variants from retained parent names.

    "4-fluoroaniline" → "4-fluoro-1-aminobenzene" (parent: benzene)
    "2,6-dichlorophenol" → "2,6-dichloro-1-hydroxybenzene" (parent: benzene)

    The locant reorder pass later normalises to ascending order:
    "4-fluoro-1-aminobenzene" → "1-amino-4-fluorobenzene"
    """
    variants: List[Tuple[str, str]] = []
    name_lower = name.lower()

    for retained, prefix, ring, locant in _RETAINED_SUBSTITUTIVE:
        if retained not in name_lower:
            continue
        if locant is None:
            continue  # skip ambiguous retained names

        idx = name_lower.index(retained)
        leading = name[:idx]          # e.g. "4-fluoro" from "4-fluoroaniline"
        trailing = name[idx + len(retained):]  # e.g. "" (usually empty)

        # Build substitutive form: "leading-LOCANT-PREFIX-ring-trailing"
        if leading:
            # Ensure proper hyphenation
            lead = leading.rstrip('-')
            variant = f"{lead}-{locant}-{prefix}{ring}{trailing}"
        else:
            variant = f"{locant}-{prefix}{ring}{trailing}"

        variant = re.sub(r'-{2,}', '-', variant)
        new_parent = ring
        variants.append((variant, new_parent))

    return variants


def _generate_alignment_variants(
    name: str, parent: str,
) -> List[Tuple[str, str]]:
    """Generate all alignment variant alternatives for a name.

    Returns list of (variant_name, variant_parent) tuples.
    These supplement the decomposer's alternatives with IUPAC-equivalent
    forms that reduce text distance between consecutive names.
    """
    variants: List[Tuple[str, str]] = []
    # Locant reordering — always try ascending locant normalization
    reordered = _reorder_locant_prefixes(name, parent)
    if reordered and reordered != name:
        variants.append((reordered, parent))
    variants.extend(_ester_variants(name, parent))
    variants.extend(_extended_suffix_prefix_variants(name, parent))
    variants.extend(_extended_prefix_to_suffix_variants(name, parent))
    variants.extend(_retained_systematic_variants(name, parent))
    variants.extend(_retained_to_substitutive_variants(name, parent))
    variants.extend(_indicated_h_variants(name, parent))
    variants.extend(_general_suffix_prefix_variants(name, parent))
    return variants


# ---------------------------------------------------------------------------
# Two-pass contextual variant generation
# ---------------------------------------------------------------------------

def _contextual_variants(
    name: str, parent: str, neighbor_name: str,
) -> List[Tuple[str, str]]:
    """Generate variants of *name* targeted to match *neighbor_name* better.

    Analyses the neighbor's naming style and generates matching variants.
    Returns list of (variant_name, variant_parent) tuples.
    """
    variants: List[Tuple[str, str]] = []
    n_lower = neighbor_name.lower()
    name_lower = name.lower()

    # 1. If neighbor uses "acid" form, try converting our ester to acid form
    #    (and vice versa)
    if "carboxylic acid" in n_lower or "acid" in n_lower:
        variants.extend(_ester_variants(name, parent))
    if "carboxylate" in n_lower or "ester" in n_lower:
        variants.extend(_ester_variants(name, parent))

    # 2. If neighbor uses systematic names, try our retained→systematic
    #    If neighbor uses retained names, try systematic→retained
    for retained, systematic in _RETAINED_TO_SYSTEMATIC.items():
        if systematic.lower() in n_lower and retained in name_lower:
            # Neighbor uses systematic form, we have the retained form
            variants.extend(_retained_systematic_variants(name, parent))
            break
        if retained in n_lower and systematic.lower() in name_lower:
            # Neighbor uses retained form, we have the systematic form
            variants.extend(_retained_systematic_variants(name, parent))
            break

    # 3. Style matching: suffix vs prefix naming
    #    If neighbor uses prefix style (e.g., "4-chloro-..."), generate prefix
    #    variants for our names that use suffix style (e.g., "...-4-one")
    n_tokens = set(_chem_tokens_flat(neighbor_name))
    our_tokens = set(_chem_tokens_flat(name))

    # Check if neighbor uses prefix-style substituents
    prefix_subs = {"amino", "hydroxy", "oxo", "sulfanyl"}
    neighbor_has_prefix = bool(n_tokens & prefix_subs)
    suffix_subs = {"amine", "ol", "one", "thiol"}
    we_have_suffix = bool(our_tokens & suffix_subs)

    if neighbor_has_prefix and we_have_suffix:
        variants.extend(_general_suffix_prefix_variants(name, parent))
        variants.extend(_indicated_h_variants(name, parent))

    # 4. Reverse: if neighbor uses suffix style, try converting our prefix style
    #    E.g., neighbor has "pyridin-2-amine", we have "2-aminopyridine"
    neighbor_has_suffix = bool(n_tokens & suffix_subs)
    we_have_prefix = bool(our_tokens & prefix_subs)

    if neighbor_has_suffix and we_have_prefix:
        # Try to generate suffix form from our prefix form
        # This is the reverse of _general_suffix_prefix_variants
        variants.extend(_prefix_to_suffix_variants(name, parent))

    # 5. Extended principal characteristic group suffix/prefix matching.
    #    If neighbor uses prefix-style naming for extended groups (formyl,
    #    carboxy, carbamoyl, cyano, alkoxycarbonyl), try our suffix→prefix;
    #    and vice versa.
    ext_prefix_tokens = {"formyl", "carboxy", "carbamoyl", "cyano", "carbonyl"}
    ext_suffix_tokens = {"carboxylate", "carbaldehyde", "carboxamide",
                         "carbonitrile", "carboxylic"}
    if n_tokens & ext_prefix_tokens and our_tokens & ext_suffix_tokens:
        variants.extend(_extended_suffix_prefix_variants(name, parent))
    if n_tokens & ext_suffix_tokens and our_tokens & ext_prefix_tokens:
        variants.extend(_extended_prefix_to_suffix_variants(name, parent))

    return variants


def _prefix_to_suffix_variants(
    name: str, parent: str,
) -> List[Tuple[str, str]]:
    """Generate prefix→suffix variants (reverse of _general_suffix_prefix_variants).

    E.g., "2-aminopyridine" → "pyridin-2-amine"
          "4-oxoquinazoline" → "quinazolin-4-one"
    """
    variants: List[Tuple[str, str]] = []
    name_lower = name.lower()

    prefix_map = {
        "amino": "amine",
        "hydroxy": "ol",
        "oxo": "one",
        "sulfanyl": "thiol",
    }

    for prefix, suffix in prefix_map.items():
        # Pattern: LOCANT-PREFIX-RING at end (or LOCANT-PREFIX-substitutents-RING)
        # E.g. "2-amino-pyridine", "2-aminopyridine"
        # We need to find the prefix and ring
        pat = r'(\d+(?:,\d+)*)-' + re.escape(prefix) + r'[-]?'
        m = re.search(pat, name_lower)
        if not m:
            continue

        locants = m.group(1)
        after_prefix = name_lower[m.end():]  # everything after "N-prefix-"

        # Find a known ring in the remaining part
        for ring in _KNOWN_RINGS_BY_LEN:
            if after_prefix == ring or after_prefix.endswith(ring):
                # Get the elided stem form for the ring (e.g.
                # "pyridine" → "pyridin").  Prefer the shortest
                # stem that maps to this ring, which is the elided
                # form needed for suffix attachment.
                stem = ring
                for s in _KNOWN_RING_STEMS_BY_LEN:
                    if _KNOWN_RING_STEMS[s] == ring and len(s) < len(stem):
                        stem = s
                # Build suffix form: leading-STEM-LOCANT-SUFFIX
                leading = after_prefix[:len(after_prefix) - len(ring)]
                variant = leading + stem + "-" + locants + "-" + suffix
                variant = re.sub(r'-{2,}', '-', variant)
                variant = variant.strip('-')
                variants.append((variant, variant))
                break

    return variants


# ---------------------------------------------------------------------------
# DP Viterbi for multi-step sequence alignment
# ---------------------------------------------------------------------------

def _dp_viterbi(
    names_per_compound: List[List[str]],
    metric_fn,
    minimize: bool = True,
) -> Tuple[List[str], float]:
    """Dynamic programming (Viterbi-style) optimal path.

    O(N * M^2) where N = num compounds, M = max names per compound.
    Picks one name per compound to optimise the sum of consecutive
    pairwise metric values.
    """
    N = len(names_per_compound)
    if N == 0:
        return [], 0.0

    dp = [{} for _ in range(N)]
    backptr = [{} for _ in range(N)]

    for j, name in enumerate(names_per_compound[0]):
        dp[0][j] = 0.0
        backptr[0][j] = -1

    for i in range(1, N):
        for j, name_j in enumerate(names_per_compound[i]):
            best_prev_score = float("inf") if minimize else float("-inf")
            best_prev_idx = 0
            for k, name_k in enumerate(names_per_compound[i - 1]):
                edge = metric_fn(name_k, name_j)
                cumulative = dp[i - 1][k] + edge
                if (minimize and cumulative < best_prev_score) or \
                   (not minimize and cumulative > best_prev_score):
                    best_prev_score = cumulative
                    best_prev_idx = k
            dp[i][j] = best_prev_score
            backptr[i][j] = best_prev_idx

    if minimize:
        last_idx = min(dp[N - 1], key=dp[N - 1].get)
    else:
        last_idx = max(dp[N - 1], key=dp[N - 1].get)

    total_score = dp[N - 1][last_idx]
    path = [last_idx]
    for i in range(N - 1, 0, -1):
        path.append(backptr[i][path[-1]])
    path.reverse()

    chosen = [names_per_compound[i][path[i]] for i in range(N)]
    return chosen, total_score


def _make_parent_penalised_metric(base_metric_fn, name_to_parent: dict,
                                   penalty: float = 100.0):
    """Create a metric that adds a penalty when parent rings differ.

    The penalty is large enough that the DP will always minimise parent
    switches first, then optimise the base metric as a tiebreaker.
    """
    def metric(a: str, b: str) -> float:
        base = base_metric_fn(a, b)
        pa = extract_parent_ring(name_to_parent.get(a, ""))
        pb = extract_parent_ring(name_to_parent.get(b, ""))
        return base + (penalty if pa != pb else 0.0)
    return metric


# ---------------------------------------------------------------------------
# Name diff
# ---------------------------------------------------------------------------

def _tokenize_iupac(name: str) -> List[str]:
    """Split an IUPAC name into tokens at dashes, parens, spaces, commas.

    Delimiters are kept as separate tokens so that the reconstructed
    string ``''.join(tokens)`` equals the original name.
    """
    tokens: List[str] = []
    buf: List[str] = []
    for ch in name:
        if ch in '-() ,':
            if buf:
                tokens.append(''.join(buf))
                buf = []
            tokens.append(ch)
        else:
            buf.append(ch)
    if buf:
        tokens.append(''.join(buf))
    return tokens


def _refine_replace(t1: str, t2: str,
                    min_affix: int = 3) -> List[Tuple[str, str, str]]:
    """Refine a 'replace' op by stripping the shared prefix/suffix.

    IUPAC substituents are often concatenated without a delimiter
    (e.g. "bromoquinolin"), so the token-level diff may lump a
    substituent and its parent into one replace op.  Stripping the
    common head/tail recovers the clean diff.

    Only strips a prefix/suffix if it is at least *min_affix* characters
    long, to avoid noisy single-character splits (e.g. the shared "e"
    in "carbamate" / "amine").

    Returns a list of (tag, text1, text2) ops.
    """
    # Common prefix
    i = 0
    while i < min(len(t1), len(t2)) and t1[i] == t2[i]:
        i += 1
    if i < min_affix:
        i = 0  # too short — don't split

    # Common suffix (not overlapping prefix)
    j = 0
    while (j < min(len(t1), len(t2)) - i
           and t1[-(j + 1)] == t2[-(j + 1)]):
        j += 1
    if j < min_affix:
        j = 0  # too short — don't split

    prefix = t1[:i]
    suffix = t1[len(t1) - j:] if j else ""
    mid1 = t1[i:len(t1) - j] if j else t1[i:]
    mid2 = t2[i:len(t2) - j] if j else t2[i:]

    ops: List[Tuple[str, str, str]] = []
    if prefix:
        ops.append(('equal', prefix, prefix))
    if mid1 and mid2:
        ops.append(('replace', mid1, mid2))
    elif mid1:
        ops.append(('delete', mid1, ''))
    elif mid2:
        ops.append(('insert', '', mid2))
    if suffix:
        ops.append(('equal', suffix, suffix))
    return ops


def name_diff(name1: str, name2: str) -> List[Tuple[str, str, str]]:
    """Token-level diff between two IUPAC names.

    Tokenises both names at IUPAC delimiters (``- ( ) , space``), then
    runs ``SequenceMatcher`` on the token lists.  Replace ops are further
    refined by stripping shared prefix/suffix within the replaced text,
    so that concatenated tokens like ``bromoquinolin`` are split into
    ``bromo`` (changed) + ``quinolin`` (equal).

    Returns list of ``(tag, from_text, to_text)`` tuples where *tag* is
    ``'equal'``, ``'replace'``, ``'delete'``, or ``'insert'``, and
    *from_text* / *to_text* are the joined token strings.

    Example::

        >>> name_diff('4-fluoropyridine', '4-(piperidin-1-yl)pyridine')
        [('equal', '4-', '4-'),
         ('replace', 'fluoro', '(piperidin-1-yl)'),
         ('equal', 'pyridine', 'pyridine')]
    """
    tok1 = _tokenize_iupac(name1)
    tok2 = _tokenize_iupac(name2)
    sm = difflib.SequenceMatcher(None, tok1, tok2, autojunk=False)

    result: List[Tuple[str, str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        t1 = ''.join(tok1[i1:i2])
        t2 = ''.join(tok2[j1:j2])
        if tag == 'replace':
            result.extend(_refine_replace(t1, t2))
        else:
            result.append((tag, t1, t2))
    return result


def format_name_diff(name1: str, name2: str) -> str:
    """Plain-text summary of changes between two aligned names.

    Returns a string like ``fluoro -> (piperidin-1-yl)``.
    Multiple changes are separated by `` ; ``.
    """
    ops = name_diff(name1, name2)
    changes = []
    for tag, t1, t2 in ops:
        if tag == 'replace':
            changes.append(f"{t1} -> {t2}")
        elif tag == 'delete':
            changes.append(f"(-{t1})")
        elif tag == 'insert':
            changes.append(f"(+{t2})")
    return " ; ".join(changes) if changes else "(identical)"


def format_name_diff_html(name1: str, name2: str) -> str:
    """Inline HTML showing the diff between two aligned names.

    Equal parts are plain text; changed parts are highlighted with
    red strikethrough (deleted/old) and green (inserted/new) spans.

    Returns an HTML fragment (no surrounding tags).
    """
    ops = name_diff(name1, name2)
    parts = []
    for tag, t1, t2 in ops:
        if tag == 'equal':
            parts.append(html_mod.escape(t1))
        elif tag == 'replace':
            parts.append(
                f'<span class="diff-del">{html_mod.escape(t1)}</span>'
                f'<span class="diff-arrow">\u2192</span>'
                f'<span class="diff-ins">{html_mod.escape(t2)}</span>')
        elif tag == 'delete':
            parts.append(
                f'<span class="diff-del">{html_mod.escape(t1)}</span>')
        elif tag == 'insert':
            parts.append(
                f'<span class="diff-ins">{html_mod.escape(t2)}</span>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Alignment result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AlignmentResult:
    """Result of aligning names for an SM→product pair."""
    sm_smiles: str
    prod_smiles: str
    sm_result: Optional[DecompositionResult] = None
    prod_result: Optional[DecompositionResult] = None

    # Exact parent matches: (sm_name, prod_name, shared_parent)
    aligned_pairs: List[Tuple[str, str, str]] = field(default_factory=list)

    # Best similarity pair (may or may not be an exact match)
    best_sm_name: str = ""
    best_prod_name: str = ""
    best_similarity: float = 0.0

    @property
    def is_aligned(self) -> bool:
        return len(self.aligned_pairs) > 0

    @property
    def alignment_quality(self) -> str:
        """Classify alignment: ALIGNED / SEMI-ALIGNED / UNALIGNED."""
        if self.aligned_pairs:
            return "ALIGNED"
        elif self.best_similarity >= 0.5:
            return "SEMI-ALIGNED"
        else:
            return "UNALIGNED"


# ---------------------------------------------------------------------------
# Core alignment function
# ---------------------------------------------------------------------------

def find_aligned_names(sm_smiles: str, prod_smiles: str,
                       verbose: bool = False,
                       preferred_parent: Optional[str] = None,
                       ) -> AlignmentResult:
    """Find aligned name pairs for SM→product that share a naming parent.

    Parameters
    ----------
    sm_smiles, prod_smiles : str
        Canonical SMILES for starting material and product.
    verbose : bool
        Print debug info.
    preferred_parent : str, optional
        Substring to match against available naming parents.  When set,
        aligned pairs whose shared parent contains this string receive a
        similarity bonus, biasing selection toward a consistent naming
        parent across a multi-step scheme.  Example: ``"quinoline"``
        would prefer quinoline-rooted names over morpholine-rooted ones.

    Returns an AlignmentResult with exact matches and similarity ranking.
    """
    result = AlignmentResult(sm_smiles=sm_smiles, prod_smiles=prod_smiles)

    sm_result = decompose_name(sm_smiles, verbose=verbose)
    prod_result = decompose_name(prod_smiles, verbose=verbose)
    result.sm_result = sm_result
    result.prod_result = prod_result

    if sm_result.errors or prod_result.errors:
        return result

    # Collect all valid names + their naming parent for each
    sm_names = [(sm_result.canonical_name,
                 sm_result.canonical_parent or "(unknown)")]
    for alt in sm_result.alternatives:
        if alt.valid:
            sm_names.append((alt.name, alt.parent_name))

    prod_names = [(prod_result.canonical_name,
                   prod_result.canonical_parent or "(unknown)")]
    for alt in prod_result.alternatives:
        if alt.valid:
            prod_names.append((alt.name, alt.parent_name))

    # Find pairs sharing the same parent name
    sm_by_parent = defaultdict(list)
    prod_by_parent = defaultdict(list)

    for name, parent in sm_names:
        sm_by_parent[parent.lower()].append(name)
    for name, parent in prod_names:
        prod_by_parent[parent.lower()].append(name)

    # Direct parent match
    for parent_key in sm_by_parent:
        if parent_key in prod_by_parent:
            for sm_name in sm_by_parent[parent_key]:
                for prod_name in prod_by_parent[parent_key]:
                    result.aligned_pairs.append(
                        (sm_name, prod_name, parent_key))

    # Remove trivial "(canonical)" matches
    result.aligned_pairs = [(s, p, par) for s, p, par in result.aligned_pairs
                            if par != "(canonical)"]

    # When a preferred_parent is specified, first try to find the best
    # pair where BOTH parents contain the preferred substring.  This keeps
    # naming consistent across a multi-step scheme.  Only fall back to
    # unrestricted similarity if no preferred-parent pair exists.
    pref_key = preferred_parent.lower().strip() if preferred_parent else ""
    # Also match the truncated form (e.g. "quinolin" for "quinoline")
    # because -yl suffixed names drop the final 'e'.
    pref_keys = []
    if pref_key:
        pref_keys.append(pref_key)
        if pref_key.endswith('e'):
            pref_keys.append(pref_key[:-1])

    def _has_pref(text: str) -> bool:
        """Check if text contains the preferred parent (or its stem)."""
        t = text.lower()
        return any(pk in t for pk in pref_keys)

    best_sim = 0.0
    best_pair = ("", "")
    best_pref_sim = 0.0
    best_pref_pair = ("", "")

    for sm_name, sm_par in sm_names:
        for prod_name, prod_par in prod_names:
            sim = name_similarity(sm_name, prod_name)
            if sim > best_sim:
                best_sim = sim
                best_pair = (sm_name, prod_name)
            # Track best pair matching preferred parent separately.
            # Check the parent string — use stem matching because -yl
            # suffixed parents drop the final 'e' (e.g. "quinolin-2-yl"
            # inside "4-(4-phenylquinolin-2-yl)morpholine").
            if (pref_keys
                    and _has_pref(sm_par)
                    and _has_pref(prod_par)
                    and sim > best_pref_sim):
                best_pref_sim = sim
                best_pref_pair = (sm_name, prod_name)

    # Use preferred-parent pair if it exists and has reasonable similarity
    # (at least 30% — just enough to filter out nonsense).
    if best_pref_pair[0] and best_pref_sim >= 0.30:
        result.best_sm_name = best_pref_pair[0]
        result.best_prod_name = best_pref_pair[1]
        result.best_similarity = best_pref_sim
    else:
        result.best_sm_name = best_pair[0]
        result.best_prod_name = best_pair[1]
        result.best_similarity = best_sim

    return result


# ---------------------------------------------------------------------------
# Multi-step sequence alignment
# ---------------------------------------------------------------------------

@dataclass
class SequenceAlignmentResult:
    """Result of aligning names across a multi-step synthetic route."""
    smiles_list: List[str]
    chosen_names: List[str]
    parent_names: List[str]
    parent_rings: List[str]
    parent_switches: int
    base_score: float
    decomposition_results: List[Optional[DecompositionResult]] = field(
        default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_fully_aligned(self) -> bool:
        return self.parent_switches == 0


def find_aligned_name_sequence(
    smiles_list: List[str],
    verbose: bool = False,
    parent_penalty: float = 100.0,
    timeout: float = 30.0,
) -> SequenceAlignmentResult:
    """Pick one IUPAC name per intermediate to minimise parent-ring switches.

    Uses parent-aware Viterbi DP: the objective is to minimise parent
    switches first (penalty >> base metric), then minimise chemistry-aware
    token diff as tiebreaker.

    Parameters
    ----------
    smiles_list : list of str
        SMILES for each intermediate in synthesis order.
    verbose : bool
        Print debug info during decomposition.
    parent_penalty : float
        Penalty added when consecutive names have different parent rings.
        Must be >> max possible base metric value.
    timeout : float
        Per-compound decomposition timeout in seconds.

    Returns
    -------
    SequenceAlignmentResult
    """
    names_per_compound: List[List[str]] = []
    name_to_parent: Dict[str, str] = {}
    decomp_results: List[Optional[DecompositionResult]] = []
    errors: List[str] = []
    canonical_smiles: List[Optional[str]] = []  # for variant validation

    for smi in smiles_list:
        try:
            r = decompose_name(smi, verbose=verbose, timeout=timeout)
            decomp_results.append(r)

            all_names = [(r.canonical_name, r.canonical_parent or "")]
            for alt in r.alternatives:
                if alt.valid:
                    all_names.append((alt.name, alt.parent_name))

            # Generate alignment variants for each name.
            # Variants are round-trip validated: name → SMILES → canonical
            # must match the original compound's canonical SMILES.
            expected_canon = _canonical(smi)
            canonical_smiles.append(expected_canon)
            extra = []
            seen_names = {n for n, _ in all_names}
            for n, p in all_names:
                for vn, vp in _generate_alignment_variants(n, p):
                    if vn not in seen_names:
                        if expected_canon and _validate_variant(vn, expected_canon):
                            extra.append((vn, vp))
                        seen_names.add(vn)
            all_names.extend(extra)

            valid_names = [n for n, _ in all_names]
            names_per_compound.append(valid_names)
            for n, p in all_names:
                if p:
                    # Check if parent gives a recognized ring; if not,
                    # the name itself may contain the ring (decomposer bug
                    # where prefix-stripping eats part of the ring name)
                    ring = extract_parent_ring(p)
                    if ring == p.lower().strip():
                        name_ring = extract_parent_ring(n)
                        if name_ring != n.lower().strip():
                            p = n
                else:
                    # Empty parent (retained names, single decompositions)
                    p = n
                name_to_parent[n] = p

            if r.errors:
                errors.append(f"{smi[:40]}: {'; '.join(r.errors)}")
        except Exception as e:
            decomp_results.append(None)
            canonical_smiles.append(None)
            fallback = f"[{smi[:30]}]"
            names_per_compound.append([fallback])
            name_to_parent[fallback] = ""
            errors.append(f"{smi[:40]}: {e}")

    # --- Pass 1: Run parent-aware DP with chem_token_diff_count as base metric
    penalised_fn = _make_parent_penalised_metric(
        chem_token_diff_count, name_to_parent, parent_penalty)
    pass1_chosen, _total = _dp_viterbi(
        names_per_compound, penalised_fn, minimize=True)

    # --- Pass 2: Generate contextual variants based on Pass 1 choices,
    #     then re-run DP with the expanded candidate lists.
    #     Each compound looks at what its neighbors chose in Pass 1 and
    #     generates targeted variants to match that naming style.
    names_per_compound_p2 = [list(names) for names in names_per_compound]
    added_any = False
    for i in range(len(pass1_chosen)):
        existing = set(names_per_compound_p2[i])
        ctx_variants: List[Tuple[str, str]] = []

        # Get parent for this compound's current names (use first name)
        comp_parent = name_to_parent.get(
            names_per_compound[i][0], "") if names_per_compound[i] else ""

        # Generate variants targeted at each neighbor's chosen name
        if i > 0:
            for n in names_per_compound_p2[i]:
                ctx_variants.extend(
                    _contextual_variants(n, name_to_parent.get(n, comp_parent),
                                         pass1_chosen[i - 1]))
        if i < len(pass1_chosen) - 1:
            for n in names_per_compound_p2[i]:
                ctx_variants.extend(
                    _contextual_variants(n, name_to_parent.get(n, comp_parent),
                                         pass1_chosen[i + 1]))

        # Add new unique variants (validated against canonical SMILES)
        exp_canon = canonical_smiles[i] if i < len(canonical_smiles) else None
        for vn, vp in ctx_variants:
            if vn not in existing:
                if exp_canon and not _validate_variant(vn, exp_canon):
                    existing.add(vn)  # skip invalid, but don't try again
                    continue
                names_per_compound_p2[i].append(vn)
                existing.add(vn)
                added_any = True
                # Register parent for the new variant
                if vp:
                    ring = extract_parent_ring(vp)
                    if ring == vp.lower().strip():
                        name_ring = extract_parent_ring(vn)
                        if name_ring != vn.lower().strip():
                            vp = vn
                else:
                    vp = vn
                name_to_parent[vn] = vp

    # Re-run DP only if we actually added new variants
    if added_any:
        penalised_fn_p2 = _make_parent_penalised_metric(
            chem_token_diff_count, name_to_parent, parent_penalty)
        chosen, _total = _dp_viterbi(
            names_per_compound_p2, penalised_fn_p2, minimize=True)
    else:
        chosen = pass1_chosen

    # --- Post-DP: normalise locant order to ascending ----------------------
    # chem_token_diff_count is order-agnostic (multiset), so the DP cannot
    # distinguish "5-X-2-Y-ring" from "2-Y-5-X-ring".  IUPAC convention
    # demands ascending locants, so we normalise here.
    for i, name in enumerate(chosen):
        parent = name_to_parent.get(name, "")
        reordered = _reorder_locant_prefixes(name, parent)
        if reordered and reordered != name:
            exp_canon = (canonical_smiles[i]
                         if i < len(canonical_smiles) else None)
            if exp_canon is None or _validate_variant(reordered, exp_canon):
                chosen[i] = reordered
                name_to_parent[reordered] = parent

    # Compute actual stats
    base_score = 0.0
    switches = 0
    parent_names = [name_to_parent.get(n, "") for n in chosen]
    parent_rings = [extract_parent_ring(p) for p in parent_names]

    for i in range(len(chosen) - 1):
        base_score += chem_token_diff_count(chosen[i], chosen[i + 1])
        if parent_rings[i] != parent_rings[i + 1]:
            switches += 1

    return SequenceAlignmentResult(
        smiles_list=smiles_list,
        chosen_names=chosen,
        parent_names=parent_names,
        parent_rings=parent_rings,
        parent_switches=switches,
        base_score=base_score,
        decomposition_results=decomp_results,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Molecular diff (MCS-based)
# ---------------------------------------------------------------------------

@dataclass
class FragmentChange:
    """One changed fragment in a molecular diff."""
    sm_frag_smiles: str   # [*]-bearing SMILES from SM side ("" for additions)
    prod_frag_smiles: str # [*]-bearing SMILES from product side ("" for removals)
    sm_name: str          # substituent name ("fluoro", "H", etc.)
    prod_name: str        # substituent name ("phenyl", etc.)
    change_type: str      # "replace" | "addition" | "removal"


@dataclass
class MolecularDiffResult:
    """Result of MCS-based molecular diff between SM and product."""
    sm_smiles: str
    prod_smiles: str
    changes: List[FragmentChange]
    mcs_num_atoms: int
    fallback_used: bool = False
    fallback_text: str = ""
    stereo_only: bool = False


def _get_connected_components(mol: Chem.Mol,
                               atom_indices: set) -> List[set]:
    """Group atom indices into connected components within the molecule."""
    visited: set = set()
    components: List[set] = []
    for start in atom_indices:
        if start in visited:
            continue
        comp: set = set()
        queue = [start]
        while queue:
            idx = queue.pop()
            if idx in visited:
                continue
            visited.add(idx)
            comp.add(idx)
            atom = mol.GetAtomWithIdx(idx)
            for nbr in atom.GetNeighbors():
                nidx = nbr.GetIdx()
                if nidx in atom_indices and nidx not in visited:
                    queue.append(nidx)
        components.append(comp)
    return components


def _extract_fragment_smiles(mol: Chem.Mol, frag_atoms: set,
                              attachments: List[Tuple[int, int]]
                              ) -> str:
    """Extract a fragment as SMILES with [*] at each attachment point.

    Args:
        mol: Source molecule.
        frag_atoms: Set of atom indices belonging to this fragment.
        attachments: List of (frag_atom_idx, core_atom_idx) pairs
                     representing bonds crossing from fragment to MCS core.

    Returns:
        SMILES like "[*]c1ccccc1" for a phenyl fragment.
    """
    frag = Chem.RWMol()
    old_to_new: dict = {}

    # Add fragment atoms
    for old_idx in sorted(frag_atoms):
        src = mol.GetAtomWithIdx(old_idx)
        new_atom = Chem.Atom(src.GetAtomicNum())
        new_atom.SetFormalCharge(src.GetFormalCharge())
        new_atom.SetNumExplicitHs(src.GetNumExplicitHs())
        new_atom.SetIsAromatic(src.GetIsAromatic())
        new_idx = frag.AddAtom(new_atom)
        old_to_new[old_idx] = new_idx

    # Add [*] dummy atoms for each attachment point
    attach_dummies: dict = {}   # core_atom_idx -> new_dummy_idx
    for frag_idx, core_idx in attachments:
        if core_idx not in attach_dummies:
            dummy_idx = frag.AddAtom(Chem.Atom(0))  # [*]
            attach_dummies[core_idx] = dummy_idx
        bond = mol.GetBondBetweenAtoms(frag_idx, core_idx)
        btype = bond.GetBondType() if bond else Chem.BondType.SINGLE
        frag.AddBond(old_to_new[frag_idx], attach_dummies[core_idx], btype)

    # Add intra-fragment bonds
    for old_idx in frag_atoms:
        atom = mol.GetAtomWithIdx(old_idx)
        for bond in atom.GetBonds():
            other = bond.GetOtherAtomIdx(old_idx)
            if other in frag_atoms and old_idx < other:
                frag.AddBond(old_to_new[old_idx], old_to_new[other],
                             bond.GetBondType())

    try:
        Chem.SanitizeMol(frag)
        return Chem.MolToSmiles(frag)
    except Exception:
        # If sanitization fails, try without aromaticity perception
        try:
            Chem.SanitizeMol(frag, Chem.SanitizeFlags.SANITIZE_ALL
                             ^ Chem.SanitizeFlags.SANITIZE_SETAROMATICITY)
            return Chem.MolToSmiles(frag)
        except Exception:
            return ""


def _name_fragment(frag_smiles: str) -> str:
    """Name a fragment, returning substituent prefix or raw SMILES fallback."""
    if not frag_smiles:
        return "H"
    # Normalise [*][H] variants
    mol = Chem.MolFromSmiles(frag_smiles)
    if mol is None:
        return frag_smiles
    heavy = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
    if heavy == 0:
        return "H"

    # Detect =O (oxo/carbonyl) vs -OH (hydroxy) — the generic substituent
    # namer may not distinguish bond order.
    if heavy == 1:
        atom = next(a for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
        if atom.GetAtomicNum() == 8:  # oxygen
            # Check if any bond to a dummy atom is a double bond
            for bond in atom.GetBonds():
                if bond.GetOtherAtom(atom).GetAtomicNum() == 0:  # [*]
                    if bond.GetBondTypeAsDouble() == 2.0:
                        return "oxo"
            return "hydroxy"
        if atom.GetAtomicNum() == 16:  # sulfur
            for bond in atom.GetBonds():
                if bond.GetOtherAtom(atom).GetAtomicNum() == 0:
                    if bond.GetBondTypeAsDouble() == 2.0:
                        return "thioxo"
            return "sulfanyl"

    result = name_fragment_as_substituent(frag_smiles, verbose=False)
    return result if result else frag_smiles


def molecular_diff(sm_smiles: str, prod_smiles: str,
                   min_mcs_ratio: float = 0.4,
                   verbose: bool = False) -> MolecularDiffResult:
    """Compute molecular-level diff between SM and product using MCS.

    Finds the Maximum Common Substructure (invariant core), extracts
    changed fragments from each side, names them as IUPAC substituents,
    and returns structured diff results.

    Falls back to text diff when MCS is too small.

    Args:
        sm_smiles: Starting material SMILES.
        prod_smiles: Product SMILES.
        min_mcs_ratio: Minimum fraction of smaller molecule covered by MCS.
                       Below this, falls back to text diff.
        verbose: Print debug info.

    Returns:
        MolecularDiffResult with list of FragmentChange entries.
    """
    empty = MolecularDiffResult(sm_smiles=sm_smiles, prod_smiles=prod_smiles,
                                changes=[], mcs_num_atoms=0)

    sm_mol = Chem.MolFromSmiles(sm_smiles)
    prod_mol = Chem.MolFromSmiles(prod_smiles)
    if sm_mol is None or prod_mol is None:
        empty.fallback_used = True
        empty.fallback_text = "(invalid SMILES)"
        return empty

    sm_n = sm_mol.GetNumAtoms()
    prod_n = prod_mol.GetNumAtoms()

    # --- MCS computation ---
    try:
        mcs = rdFMCS.FindMCS(
            [sm_mol, prod_mol],
            threshold=1.0,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
            timeout=5,
        )
    except Exception:
        empty.fallback_used = True
        return empty

    if mcs.canceled or mcs.numAtoms < 3:
        empty.fallback_used = True
        return empty

    # --- Quality gate ---
    smaller = min(sm_n, prod_n)
    if mcs.numAtoms < min_mcs_ratio * smaller:
        if verbose:
            print(f"  MCS too small: {mcs.numAtoms}/{smaller} "
                  f"({mcs.numAtoms/smaller:.0%})", file=sys.stderr)
        empty.fallback_used = True
        return empty

    # --- Atom mappings ---
    core = Chem.MolFromSmarts(mcs.smartsString)
    if core is None:
        empty.fallback_used = True
        return empty

    sm_match = sm_mol.GetSubstructMatch(core)
    prod_match = prod_mol.GetSubstructMatch(core)
    if not sm_match or not prod_match:
        empty.fallback_used = True
        return empty

    sm_core = set(sm_match)
    prod_core = set(prod_match)

    # --- Stereo-only check ---
    if mcs.numAtoms == sm_n == prod_n:
        return MolecularDiffResult(
            sm_smiles=sm_smiles, prod_smiles=prod_smiles,
            changes=[], mcs_num_atoms=mcs.numAtoms, stereo_only=True)

    # --- Extract non-MCS atoms ---
    sm_non_mcs = set(range(sm_n)) - sm_core
    prod_non_mcs = set(range(prod_n)) - prod_core

    # --- Group into connected components ---
    sm_comps = _get_connected_components(sm_mol, sm_non_mcs)
    prod_comps = _get_connected_components(prod_mol, prod_non_mcs)

    if verbose:
        print(f"  MCS: {mcs.numAtoms} atoms.  SM changed: {len(sm_non_mcs)} "
              f"in {len(sm_comps)} frag(s).  Prod changed: {len(prod_non_mcs)} "
              f"in {len(prod_comps)} frag(s).", file=sys.stderr)

    # --- Find attachment points ---
    # For each component, find bonds from non-MCS to MCS atoms.
    # Key: MCS core position (index in sm_match/prod_match tuple)
    # Multiple fragments can attach to the same core atom (e.g. Grignard
    # addition: C=O → C(OH)(R) produces two product fragments on one atom).
    def _find_attachments(mol, components, core_set, match_tuple):
        """Return {mcs_pos: [(component, [(frag_idx, core_idx), ...]), ...]}."""
        attach_map: dict = {}  # mcs_pos -> list of (comp, atts)
        for comp in components:
            atts: List[Tuple[int, int]] = []
            for atom_idx in comp:
                for nbr in mol.GetAtomWithIdx(atom_idx).GetNeighbors():
                    nidx = nbr.GetIdx()
                    if nidx in core_set:
                        atts.append((atom_idx, nidx))
            # Key by MCS core position (to enable pairing)
            # A component may attach to multiple core atoms; use the first.
            mcs_positions_seen: set = set()
            for _, core_idx in atts:
                mcs_pos = match_tuple.index(core_idx)
                if mcs_pos not in mcs_positions_seen:
                    mcs_positions_seen.add(mcs_pos)
                    attach_map.setdefault(mcs_pos, []).append((comp, atts))
        return attach_map

    sm_attach = _find_attachments(sm_mol, sm_comps, sm_core, sm_match)
    prod_attach = _find_attachments(prod_mol, prod_comps, prod_core, prod_match)

    # --- Pair fragments by shared MCS attachment point ---
    all_mcs_positions = set(sm_attach.keys()) | set(prod_attach.keys())
    changes: List[FragmentChange] = []

    for mcs_pos in sorted(all_mcs_positions):
        sm_list = sm_attach.get(mcs_pos, [])
        prod_list = prod_attach.get(mcs_pos, [])

        # Extract all fragment SMILES and names for each side
        sm_frags = []
        for comp, atts in sm_list:
            smi = _extract_fragment_smiles(sm_mol, comp, atts)
            sm_frags.append((smi, _name_fragment(smi) if smi else "H"))
        prod_frags = []
        for comp, atts in prod_list:
            smi = _extract_fragment_smiles(prod_mol, comp, atts)
            prod_frags.append((smi, _name_fragment(smi) if smi else "H"))

        if sm_frags and prod_frags:
            # Replacement at this position.  Multiple fragments on one
            # side are part of the same transformation (e.g. Grignard
            # C=O → C(OH)(R)), so combine all names with " + ".
            sm_names = " + ".join(n for _, n in sm_frags)
            prod_names = " + ".join(n for _, n in prod_frags)
            changes.append(FragmentChange(
                sm_frag_smiles=sm_frags[0][0],
                prod_frag_smiles=prod_frags[0][0],
                sm_name=sm_names, prod_name=prod_names,
                change_type="replace",
            ))
        elif sm_frags:
            # Pure removals (nothing on product side at this position)
            for smi, name in sm_frags:
                changes.append(FragmentChange(
                    sm_frag_smiles=smi, prod_frag_smiles="",
                    sm_name=name, prod_name="H",
                    change_type="removal",
                ))
        elif prod_frags:
            # Pure additions (nothing on SM side at this position)
            for smi, name in prod_frags:
                changes.append(FragmentChange(
                    sm_frag_smiles="", prod_frag_smiles=smi,
                    sm_name="H", prod_name=name,
                    change_type="addition",
                ))

    # --- Post-processing: merge unpaired removals + additions ---
    # Symmetric molecules (e.g. benzene) can cause the MCS to map
    # substituted carbons to different positions, so a true substitution
    # appears as a removal + addition.  Merge them into replacements.
    removals = [c for c in changes if c.change_type == "removal"]
    additions = [c for c in changes if c.change_type == "addition"]

    if removals and additions:
        paired_changes = [c for c in changes if c.change_type == "replace"]
        # Pair removals with additions (1:1, in order)
        n_pairs = min(len(removals), len(additions))
        for i in range(n_pairs):
            paired_changes.append(FragmentChange(
                sm_frag_smiles=removals[i].sm_frag_smiles,
                prod_frag_smiles=additions[i].prod_frag_smiles,
                sm_name=removals[i].sm_name,
                prod_name=additions[i].prod_name,
                change_type="replace",
            ))
        # Keep any leftover unpaired removals/additions
        for r in removals[n_pairs:]:
            paired_changes.append(r)
        for a in additions[n_pairs:]:
            paired_changes.append(a)
        changes = paired_changes

    return MolecularDiffResult(
        sm_smiles=sm_smiles, prod_smiles=prod_smiles,
        changes=changes, mcs_num_atoms=mcs.numAtoms)


# ---------------------------------------------------------------------------
# Molecular diff formatting
# ---------------------------------------------------------------------------

def format_molecular_diff(sm_smiles: str, prod_smiles: str,
                          alignment_result: Optional['AlignmentResult'] = None
                          ) -> str:
    """Plain-text molecular diff: ``fluoro → phenyl``.

    Uses MCS to identify changed fragments, names them as substituents.
    Falls back to text diff (``format_name_diff``) when MCS is too small.

    Multiple changes separated by `` ; ``.
    """
    result = molecular_diff(sm_smiles, prod_smiles)

    if result.fallback_used:
        # Fall back to text diff using best available names
        if alignment_result:
            n1 = alignment_result.best_sm_name or ""
            n2 = alignment_result.best_prod_name or ""
        else:
            n1 = _quick_name(sm_smiles)
            n2 = _quick_name(prod_smiles)
        if n1 and n2:
            return format_name_diff(n1, n2)
        return result.fallback_text or "(no diff available)"

    if result.stereo_only:
        return "(stereo change)"
    if not result.changes:
        return "(identical)"

    parts = []
    for ch in result.changes:
        if ch.change_type == "replace":
            parts.append(f"{ch.sm_name} \u2192 {ch.prod_name}")
        elif ch.change_type == "removal":
            parts.append(f"{ch.sm_name} \u2192 H")
        elif ch.change_type == "addition":
            parts.append(f"H \u2192 {ch.prod_name}")
    return " ; ".join(parts) if parts else "(identical)"


def format_molecular_diff_html(sm_smiles: str, prod_smiles: str,
                                alignment_result: Optional['AlignmentResult'] = None
                                ) -> str:
    """HTML molecular diff with coloured spans.

    Uses same CSS classes as ``format_name_diff_html`` for consistency:
    ``.diff-del`` (red strikethrough), ``.diff-ins`` (green), ``.diff-arrow``.
    """
    result = molecular_diff(sm_smiles, prod_smiles)

    if result.fallback_used:
        if alignment_result:
            n1 = alignment_result.best_sm_name or ""
            n2 = alignment_result.best_prod_name or ""
        else:
            n1 = _quick_name(sm_smiles)
            n2 = _quick_name(prod_smiles)
        if n1 and n2:
            return format_name_diff_html(n1, n2)
        return html_mod.escape(result.fallback_text or "(no diff available)")

    if result.stereo_only:
        return '<span class="diff-ins">(stereo change)</span>'
    if not result.changes:
        return "(identical)"

    parts = []
    for ch in result.changes:
        if ch.change_type == "replace":
            parts.append(
                f'<span class="diff-del">{html_mod.escape(ch.sm_name)}</span>'
                f'<span class="diff-arrow">\u2192</span>'
                f'<span class="diff-ins">{html_mod.escape(ch.prod_name)}</span>'
            )
        elif ch.change_type == "removal":
            parts.append(
                f'<span class="diff-del">{html_mod.escape(ch.sm_name)}</span>'
                f'<span class="diff-arrow">\u2192</span>'
                f'<span class="diff-ins">H</span>'
            )
        elif ch.change_type == "addition":
            parts.append(
                f'<span class="diff-del">H</span>'
                f'<span class="diff-arrow">\u2192</span>'
                f'<span class="diff-ins">{html_mod.escape(ch.prod_name)}</span>'
            )
    return " ; ".join(parts) if parts else "(identical)"


def _quick_name(smiles: str) -> str:
    """Get IUPAC name for a SMILES without full decomposition."""
    try:
        from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
        cs = ChemScriptBridge.get_instance()
        return cs.get_name(smiles)
    except Exception:
        return ""


# Showcase runner and CLI entry points live in chem-pipeline/aligned_namer.py
