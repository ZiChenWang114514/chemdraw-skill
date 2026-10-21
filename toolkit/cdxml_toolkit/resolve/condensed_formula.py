"""Condensed structural formula parser.

Converts chemist-shorthand condensed formulae (PhB(OH)₂, Et₃N, MeI)
to canonical SMILES by tokenizing against the superatom fragment
vocabulary (~2,850 entries) and assembling via RDKit.

This is a *generative* parser — it handles novel combinations like
PhB(OMe)₂ or PhB(OEt)₂ without needing a dictionary entry for every
whole molecule.

Grammar patterns handled:

  group + atom/group            MeI, BzCl, EtOH
  group_n + central (+ more)    Et₃N, Ph₃P, Me₃SiCl
  left + atom + (group)_n       PhB(OH)₂, PhB(OMe)₂
  elem_n + chain                Cl₂CHOCH₃, PhCH₂Br

Usage::

    >>> from cdxml_toolkit.condensed_formula import resolve_condensed_formula
    >>> resolve_condensed_formula("PhB(OH)2")
    'OB(O)c1ccccc1'
    >>> resolve_condensed_formula("Et3N")
    'CCN(CC)CC'
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Element table (symbols recognised as bare atoms in condensed formulae)
# ---------------------------------------------------------------------------

# Two-letter elements — checked before single-letter to avoid ambiguity.
_TWO_LETTER_ELEMENTS = {
    "He", "Li", "Be", "Ne", "Na", "Mg", "Al", "Si", "Cl", "Ar",
    "Ca", "Sc", "Ti", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Zr", "Nb",
    "Mo", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te",
    "Cs", "Ba", "La", "Ce", "Hf", "Ta", "Re", "Os", "Ir", "Pt",
    "Au", "Hg", "Tl", "Pb", "Bi",
}

# Single-letter elements.
_ONE_LETTER_ELEMENTS = {
    "H", "B", "C", "N", "O", "F", "P", "S", "K", "I", "V", "Y", "W", "U",
}

# Elements that should use bracket notation in SMILES.
_BRACKET_ELEMENTS = {
    "H",  # explicit hydrogen needs brackets
    "Li", "Be", "Na", "Mg", "Al", "Si", "Ca", "Sc", "Ti", "Cr", "Mn",
    "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Rb", "Sr",
    "Zr", "Nb", "Mo", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb",
    "Te", "Cs", "Ba", "La", "Ce", "Hf", "Ta", "Re", "Os", "Ir", "Pt",
    "Au", "Hg", "Tl", "Pb", "Bi", "K", "V", "Y", "W", "U",
}

# Organic-subset elements that don't need brackets in SMILES.
_ORGANIC_SUBSET = {"B", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I"}

# Superatom table keys to EXCLUDE from abbreviation matching because they
# collide with element symbols.  These single/double-letter entries map to
# bare atoms (n→N, o→O) or to wrong molecules (co→CO carbonyl, sn→NS,
# zn→CBz-variant).  They must be handled by element matching instead.
_ELEMENT_COLLISIONS = {
    sym.lower() for sym in (_ONE_LETTER_ELEMENTS | _TWO_LETTER_ELEMENTS)
}


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _get_abbrev_table() -> Dict[str, str]:
    """Return the superatom abbreviation table (lowercase key → SMILES)."""
    from .superatom_table import get_superatom_table
    return get_superatom_table()


def tokenize(formula: str) -> List[Tuple[str, Any]]:
    """Tokenize a condensed structural formula.

    Returns a list of ``(token_type, value)`` tuples where *token_type*
    is one of ``'abbrev'``, ``'element'``, ``'count'``,
    ``'paren_open'``, ``'paren_close'``.

    Uses the superatom table (~2,854 entries) for abbreviation matching
    with greedy longest-match, case-insensitive.  Abbreviations take
    priority over element symbols.

    Returns an empty list if the formula contains unrecognisable tokens.
    """
    table = _get_abbrev_table()
    tokens: List[Tuple[str, Any]] = []
    i = 0
    s = formula

    # Pre-compute max abbreviation length for the search window.
    max_abbrev_len = max((len(k) for k in table), default=0)

    while i < len(s):
        ch = s[i]

        # Skip whitespace
        if ch == " ":
            i += 1
            continue

        # Parentheses
        if ch == "(":
            tokens.append(("paren_open", "("))
            i += 1
            continue
        if ch == ")":
            tokens.append(("paren_close", ")"))
            i += 1
            continue

        # Digit run → count
        if ch.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(("count", int(s[i:j])))
            i = j
            continue

        # Try two-letter element FIRST (exact case: uppercase + lowercase).
        # This prevents superatom entries like "co"→CO (carbonyl) from
        # shadowing the element Co (cobalt).
        if i + 1 < len(s) and s[i:i + 2] in _TWO_LETTER_ELEMENTS:
            tokens.append(("element", s[i:i + 2]))
            i += 2
            continue

        # Try abbreviation (longest match first, case-insensitive).
        # Skip matches whose key collides with an element symbol
        # (single-letter n/o/s/h or two-letter co/sn/zn) — those are
        # handled by element matching above and below.
        matched = False
        hi = min(max_abbrev_len, len(s) - i)
        for length in range(hi, 0, -1):
            candidate = s[i:i + length]
            key = candidate.lower()
            if key in table and key not in _ELEMENT_COLLISIONS:
                tokens.append(("abbrev", candidate))
                i += length
                matched = True
                break
        if matched:
            continue

        # Try single-letter element (uppercase only)
        if ch in _ONE_LETTER_ELEMENTS:
            tokens.append(("element", ch))
            i += 1
            continue

        # Unrecognised character → bail out
        return []

    return tokens


# ---------------------------------------------------------------------------
# SMILES assembler
# ---------------------------------------------------------------------------

def _element_smiles(sym: str) -> str:
    """Return SMILES atom string for an element symbol."""
    if sym in _BRACKET_ELEMENTS:
        return f"[{sym}]"
    return sym


def _mol_from_token(tok_type: str, tok_val: str,
                    table: Dict[str, str]) -> Optional["Chem.Mol"]:
    """Create an RDKit Mol from a single token."""
    from rdkit import Chem

    if tok_type == "abbrev":
        smiles = table.get(tok_val.lower())
        if smiles is None:
            return None
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            # Some superatom entries are SMARTS
            mol = Chem.MolFromSmarts(smiles)
            if mol is not None:
                try:
                    mol = Chem.RWMol(mol)
                    Chem.SanitizeMol(mol)
                    mol = mol.GetMol()
                except Exception:
                    return None
        return mol

    if tok_type == "element":
        smi = _element_smiles(tok_val)
        return Chem.MolFromSmiles(smi)

    return None


def _attachment_idx(mol: "Chem.Mol") -> int:
    """Return the atom index used as the attachment point.

    Superatom SMILES have the first atom in the SMILES string as the
    attachment point.  For RDKit mols created from SMILES, atom index 0
    corresponds to the first atom written.
    """
    return 0


def _combine(mol_a: "Chem.Mol", idx_a: int,
             mol_b: "Chem.Mol", idx_b: int) -> "Chem.Mol":
    """Combine two molecules by adding a single bond between them.

    Returns a new Mol with a bond between atom *idx_a* of *mol_a*
    and atom *idx_b* of *mol_b*.
    """
    from rdkit import Chem

    combo = Chem.CombineMols(mol_a, mol_b)
    offset = mol_a.GetNumAtoms()
    rw = Chem.RWMol(combo)
    rw.AddBond(idx_a, idx_b + offset, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(rw)
    except Exception:
        pass  # Sanitization may fail for organometallics; that's OK
    return rw.GetMol()


def _assemble(tokens: List[Tuple[str, Any]]) -> Optional[str]:
    """Assemble a canonical SMILES from a token list.

    Implements a stack-based state machine that handles:
      - Linear chaining (MeI, BzCl)
      - Multiplied prefix groups (Et₃N, Ph₃P)
      - Parenthesised branches with multiplier (PhB(OH)₂)
      - Element subscripts in linear chains (Cl₂CH…)
    """
    from rdkit import Chem

    table = _get_abbrev_table()

    if not tokens:
        return None

    # --- State ---
    mol = None          # Current molecule being built
    tip = None          # Atom index in mol that is the "current attachment point"
    pending = None      # (mol, attach_idx, count) — fragment waiting for its central atom
    branch_stack = []   # Stack of (mol, tip) for parenthesised groups
    branch_frags = []   # Fragments collected inside current parentheses
    in_branch = 0       # Nesting depth of parentheses

    i = 0
    while i < len(tokens):
        tok_type, tok_val = tokens[i]

        # --- Parenthesis open ---
        if tok_type == "paren_open":
            branch_stack.append((mol, tip, branch_frags[:]))
            branch_frags = []
            in_branch += 1
            i += 1
            continue

        # --- Parenthesis close ---
        if tok_type == "paren_close":
            if not branch_stack:
                return None  # unmatched paren

            # Determine multiplier (peek ahead for count)
            count = 1
            if (i + 1 < len(tokens)
                    and tokens[i + 1][0] == "count"):
                count = tokens[i + 1][1]
                i += 1  # consume the count

            # Build the branch fragment from collected pieces
            branch_mol = None
            branch_tip = None
            for frag_mol, frag_attach in branch_frags:
                if branch_mol is None:
                    branch_mol = frag_mol
                    branch_tip = frag_attach
                else:
                    new_mol = _combine(branch_mol, branch_tip,
                                       frag_mol, frag_attach)
                    branch_tip = branch_mol.GetNumAtoms() + frag_attach
                    branch_mol = new_mol

            # Restore parent state
            parent_mol, parent_tip, parent_branch_frags = branch_stack.pop()
            branch_frags = parent_branch_frags
            in_branch -= 1

            if branch_mol is not None and parent_mol is not None:
                # Attach branch_mol to parent_mol at parent_tip, `count` times
                for _ in range(count):
                    parent_mol = _combine(parent_mol, parent_tip,
                                          branch_mol,
                                          _attachment_idx(branch_mol))
            elif branch_mol is not None:
                # No parent yet — unusual, but handle gracefully
                parent_mol = branch_mol
                parent_tip = _attachment_idx(branch_mol)

            mol = parent_mol
            tip = parent_tip
            i += 1
            continue

        # --- Count (not after paren_close — handled above) ---
        if tok_type == "count":
            # Multiplier after a group/element: sets pending count
            if pending is not None:
                p_mol, p_attach, _ = pending
                pending = (p_mol, p_attach, tok_val)
            i += 1
            continue

        # --- Abbreviation or element ---
        if tok_type in ("abbrev", "element"):
            frag = _mol_from_token(tok_type, tok_val, table)
            if frag is None:
                return None
            frag_attach = _attachment_idx(frag)
            is_hydrogen = (tok_type == "element" and tok_val == "H")

            # If we're inside parentheses, collect fragments
            if in_branch > 0:
                branch_frags.append((frag, frag_attach))
                i += 1
                continue

            # If there's a pending fragment with a count, this token
            # is the central atom.  Attach `count` copies of pending
            # to this fragment.
            if pending is not None:
                p_mol, p_attach, p_count = pending
                # This fragment is the central atom
                central = frag
                central_tip = frag_attach
                for _ in range(p_count):
                    central = _combine(central, central_tip,
                                       p_mol, p_attach)
                if mol is not None:
                    # Also attach central to the existing molecule
                    central = _combine(mol, tip, central, central_tip)
                    tip = tip  # tip stays on the original attachment
                else:
                    tip = central_tip
                mol = central
                pending = None
                i += 1
                continue

            # Peek ahead: is the next token a count?
            if (i + 1 < len(tokens)
                    and tokens[i + 1][0] == "count"):
                count = tokens[i + 1][1]

                # Hydrogen with count: ALWAYS attach to the previous
                # heavy atom (tip).  H is terminal — it can never be a
                # "central" atom in the X_n Y pattern.
                # E.g. CH₂Br → C gets 2H, then Br bonds to C.
                #      NaBH₄ → B gets 4H.
                if is_hydrogen:
                    if mol is not None:
                        for _ in range(count):
                            mol = _combine(mol, tip, frag, frag_attach)
                    i += 2
                    continue

                # Peek further: is there another group/element after?
                if i + 2 < len(tokens) and tokens[i + 2][0] in (
                        "abbrev", "element", "paren_open"):
                    # Pattern: group_n + central → stash as pending
                    pending = (frag, frag_attach, count)
                    i += 2  # skip the group and its count
                    continue
                else:
                    # Count at end: replicate element on tip
                    # e.g., trailing Cl₂ at end → 2 Cl on tip
                    if mol is not None:
                        for _ in range(count):
                            mol = _combine(mol, tip, frag, frag_attach)
                    else:
                        mol = frag
                        tip = frag_attach
                    i += 2
                    continue

            # Simple linear attachment
            if mol is None:
                mol = frag
                tip = frag_attach
            else:
                new_mol = _combine(mol, tip, frag, frag_attach)
                # Advance tip to the new fragment's attachment atom
                tip = mol.GetNumAtoms() + frag_attach
                mol = new_mol

            i += 1
            continue

        # Unknown token type → bail
        return None

    # --- Flush any remaining pending fragment ---
    if pending is not None:
        p_mol, p_attach, p_count = pending
        if mol is not None:
            for _ in range(p_count):
                mol = _combine(mol, tip, p_mol, p_attach)
        elif p_count == 1:
            mol = p_mol
        else:
            return None  # dangling multiplied fragment with no central

    if mol is None:
        return None

    # Validate and canonicalize
    try:
        Chem.SanitizeMol(mol)
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Quick-reject patterns: strings that look like IUPAC names or sentences.
_IUPAC_LIKE = re.compile(
    r"(?:^[a-z].*\s)"   # starts lowercase and has spaces → sentence/name
    r"|(?:amine$|acid$|ether$|oxide$|chloride$|bromide$|iodide$|"
    r"hydride$|phosphine$|carbonate$|aldehyde$|ketone$|alcohol$)",
    re.IGNORECASE,
)

# Quick-reject: too long to be a condensed formula
_MAX_FORMULA_LEN = 40


def resolve_condensed_formula(formula: str) -> Optional[str]:
    """Parse a condensed structural formula to canonical SMILES.

    Tokenizes *formula* against the superatom abbreviation vocabulary
    (~2,854 fragments) and assembles a molecule via RDKit.

    Returns a canonical SMILES string, or ``None`` if parsing fails or
    the input doesn't look like a condensed formula.

    This function is designed as a tier in the reagent resolution chain
    (between the reagent dictionary and OPSIN).  It returns ``None``
    quickly for inputs it can't handle, letting downstream tiers try.
    """
    if not formula or len(formula) > _MAX_FORMULA_LEN:
        return None

    clean = formula.strip()
    if not clean:
        return None

    # Skip things that look like IUPAC names or common names.
    if _IUPAC_LIKE.search(clean):
        return None

    # Skip things with multiple words (IUPAC names, reaction descriptions).
    if " " in clean:
        return None

    # Tokenize
    tokens = tokenize(clean)
    if not tokens:
        return None

    # Need at least 2 tokens to form a compound
    # (single abbreviations are handled by the reagent DB)
    real_tokens = [t for t in tokens if t[0] not in ("count",)]
    if len(real_tokens) < 2:
        return None

    # Assemble
    return _assemble(tokens)
