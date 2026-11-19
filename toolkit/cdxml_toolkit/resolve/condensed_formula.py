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
# Recursive-descent parser
# ---------------------------------------------------------------------------
#
# A condensed formula is read left to right as a chain.  Each item is an
# element, a named group or a bracketed sub-formula, optionally followed by a
# multiplier.  Hydrogens attach to the current chain atom; a multiplied item
# either fills the current atom ("CH2Cl2", "PhB(OH)2") or, when it cannot,
# waits for the next centre ("Et3N", "(CH3)3CBr", "PhMe2SiCl").  A bracketed
# unit with two open ends repeats along the chain ("CH3(CH2)4CH3").  Bond
# orders follow from the remaining valences ("CH3CN", "(CH3)2CO").  The
# formula counted from the notation must equal that of the molecule.

class _ParseError(ValueError):
    pass


# Named groups, case-sensitive; "*" marks each attachment point.  One "*" is a
# terminal group; two make a linker continued at the second attachment.
_GROUPS: Dict[str, str] = {
    "Ph": "*c1ccccc1", "Me": "*C", "Et": "*CC", "Pr": "*CCC", "nPr": "*CCC",
    "iPr": "*C(C)C", "Bu": "*CCCC", "nBu": "*CCCC", "iBu": "*CC(C)C",
    "sBu": "*C(C)CC", "tBu": "*C(C)(C)C", "Bn": "*Cc1ccccc1",
    "Bz": "*C(=O)c1ccccc1", "Ac": "*C(C)=O", "Piv": "*C(=O)C(C)(C)C",
    "Ts": "*S(=O)(=O)c1ccc(C)cc1", "Ms": "*S(C)(=O)=O", "Tf": "*S(=O)(=O)C(F)(F)F",
    "Cy": "*C1CCCCC1", "Tol": "*c1ccc(C)cc1", "Mes": "*c1c(C)cc(C)cc1C",
    "Boc": "*C(=O)OC(C)(C)C", "Cbz": "*C(=O)OCc1ccccc1",
    "TMS": "*[Si](C)(C)C", "TBS": "*[Si](C)(C)C(C)(C)C", "TBDMS": "*[Si](C)(C)C(C)(C)C",
    "TIPS": "*[Si](C(C)C)(C(C)C)C(C)C",
    "NO2": "*[N+](=O)[O-]", "SO3H": "*S(=O)(=O)O", "COOH": "*C(=O)O", "CO2H": "*C(=O)O",
    "COO": "*C(=O)O*", "CO2": "*C(=O)O*", "SO2": "*S(=O)(=O)*",
}
_MAX_GROUP_LEN = max(len(k) for k in _GROUPS)

# Allowed valences of elements whose bonding the parser checks; other
# elements (metals) are accepted with whatever they are bonded to.
_VALENCES: Dict[str, Tuple[int, ...]] = {
    "H": (1,), "B": (3,), "C": (4,), "N": (3,), "O": (2,), "F": (1,),
    "Cl": (1,), "Br": (1,), "I": (1,), "Si": (4,), "P": (3, 5),
    "S": (2, 4, 6), "Se": (2,),
}

# Ionic salts: cation + anion written as one formula (K2CO3, NaOtBu, Ca(OH)2).
_CATIONS: Dict[str, str] = {
    "Li": "[Li+]", "Na": "[Na+]", "K": "[K+]", "Rb": "[Rb+]", "Cs": "[Cs+]",
    "Mg": "[Mg+2]", "Ca": "[Ca+2]", "Sr": "[Sr+2]", "Ba": "[Ba+2]", "NH4": "[NH4+]",
}
_ANIONS: Dict[str, str] = {
    "H": "[H-]", "F": "[F-]", "Cl": "[Cl-]", "Br": "[Br-]", "I": "[I-]",
    "OH": "[OH-]", "CN": "[C-]#N", "N3": "[N-]=[N+]=[N-]", "O": "[O-2]", "S": "[S-2]",
    "OMe": "C[O-]", "OEt": "CC[O-]", "OtBu": "CC(C)(C)[O-]", "OAc": "CC(=O)[O-]",
    "CO3": "[O-]C([O-])=O", "HCO3": "OC(=O)[O-]", "SO4": "[O-]S(=O)(=O)[O-]",
    "HSO4": "OS(=O)(=O)[O-]", "SO3": "[O-]S([O-])=O", "HSO3": "OS([O-])=O",
    "S2O3": "[O-]S(=O)(=S)[O-]", "PO4": "[O-]P(=O)([O-])[O-]",
    "HPO4": "OP(=O)([O-])[O-]", "H2PO4": "OP(=O)(O)[O-]", "NO3": "[O-][N+](=O)[O-]",
    "NO2": "[O-]N=O", "BH4": "[BH4-]", "AlH4": "[AlH4-]", "ClO": "[O-]Cl",
    "ClO4": "[O-]Cl(=O)(=O)=O", "MnO4": "[O-][Mn](=O)(=O)=O",
}
_SALT = re.compile(r"^(NH4|Li|Na|Rb|Cs|Mg|Ca|Sr|Ba|K)(\d*)(?:\(([A-Za-z0-9]+)\)(\d+)|([A-Za-z0-9]+))$")


class _Unit:
    """A piece of the molecule with open attachment points (``slots``)."""

    def __init__(self, mol, head, out, slots, tracked, kind):
        self.mol, self.head, self.out = mol, head, out
        self.slots, self.tracked, self.kind = slots, tracked, kind


def _fixed_hydrogens(mol) -> None:
    for atom in mol.GetAtoms():
        atom.SetNumExplicitHs(atom.GetTotalNumHs())
        atom.SetNoImplicit(True)


def _group_unit(smiles: str) -> _Unit:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise _ParseError(smiles)
    _fixed_hydrogens(mol)
    dummies = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
    if not dummies or any(mol.GetAtomWithIdx(d).GetDegree() != 1 for d in dummies):
        raise _ParseError(smiles)
    ends = [mol.GetAtomWithIdx(d).GetNeighbors()[0].GetIdx() for d in dummies]
    rw = Chem.RWMol(mol)
    for d in sorted(dummies, reverse=True):
        rw.RemoveAtom(d)

    def shifted(i):
        return i - sum(1 for d in dummies if d < i)

    slots: Dict[int, int] = {}
    for end in ends:
        slots[shifted(end)] = slots.get(shifted(end), 0) + 1
    return _Unit(rw.GetMol(), shifted(ends[0]), shifted(ends[-1]), slots, {}, "group")


def _element_unit(symbol: str) -> _Unit:
    from rdkit import Chem

    mol = Chem.RWMol()
    atom = Chem.Atom(symbol)
    atom.SetNoImplicit(True)
    mol.AddAtom(atom)
    tracked = {0: _VALENCES[symbol]} if symbol in _VALENCES else {}
    return _Unit(mol.GetMol(), 0, 0, {}, tracked, "hydrogen" if symbol == "H" else "element")


def _lex(text: str) -> List[Tuple[str, Any]]:
    """Tokens ``("(",)``, ``(")",)``, ``("count", n)``, ``("group", key)``,
    ``("element", symbol)`` or ``("superatom", text)``; raises on anything else."""
    table = None
    tokens: List[Tuple[str, Any]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "()":
            tokens.append((ch, ch))
            i += 1
            continue
        if ch.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            tokens.append(("count", int(text[i:j])))
            i = j
            continue
        for length in range(min(_MAX_GROUP_LEN, len(text) - i), 0, -1):
            if text[i:i + length] in _GROUPS:
                tokens.append(("group", text[i:i + length]))
                i += length
                break
        else:
            if text[i:i + 2] in _TWO_LETTER_ELEMENTS:
                tokens.append(("element", text[i:i + 2]))
                i += 2
            elif ch in _ONE_LETTER_ELEMENTS:
                tokens.append(("element", ch))
                i += 1
            else:
                # Other abbreviations come from the superatom vocabulary.
                table = table if table is not None else _get_abbrev_table()
                longest = max((len(k) for k in table), default=0)
                for length in range(min(longest, len(text) - i), 0, -1):
                    key = text[i:i + length].lower()
                    if key in table and key not in _ELEMENT_COLLISIONS:
                        tokens.append(("superatom", table[key]))
                        i += length
                        break
                else:
                    raise _ParseError(f"unrecognised text at {text[i:]!r}")
    return tokens


class _Chain:
    """The molecule being built, with its current attachment atom."""

    def __init__(self):
        from rdkit import Chem

        self.mol = Chem.RWMol()
        self.tracked: Dict[int, Tuple[int, ...]] = {}
        self.slots: Dict[int, int] = {}
        self.head: Optional[int] = None
        self.current: Optional[int] = None
        self.pending: List[Tuple[_Unit, int]] = []
        self.bonds: List[Tuple[int, int]] = []

    # -- valence bookkeeping --
    def _used(self, i: int) -> int:
        atom = self.mol.GetAtomWithIdx(i)
        return int(sum(b.GetBondTypeAsDouble() for b in atom.GetBonds())) + atom.GetNumExplicitHs()

    def free(self, i: int) -> int:
        if i in self.tracked:
            return max(self.tracked[i]) - self._used(i)
        if i in self.slots:
            return self.slots[i]
        return 99

    def _consume(self, i: int, n: int) -> None:
        if self.free(i) < n:
            raise _ParseError("valence exceeded")
        if i in self.slots:
            self.slots[i] -= n

    # -- building --
    def merge(self, unit: _Unit) -> Tuple[int, int]:
        from rdkit import Chem

        offset = self.mol.GetNumAtoms()
        self.mol = Chem.RWMol(Chem.CombineMols(self.mol, unit.mol))
        for i, n in unit.slots.items():
            self.slots[i + offset] = n
        for i, v in unit.tracked.items():
            self.tracked[i + offset] = v
        for b in unit.mol.GetBonds():
            self.bonds.append((b.GetBeginAtomIdx() + offset, b.GetEndAtomIdx() + offset))
        return unit.head + offset, unit.out + offset

    def bond(self, i: int, j: int, order: int = 1) -> None:
        from rdkit import Chem

        self._consume(i, order)
        self._consume(j, order)
        kind = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE}[order]
        self.mol.AddBond(i, j, kind)
        self.bonds.append((i, j))

    def add_h(self, i: int, n: int) -> None:
        self._consume(i, n)
        atom = self.mol.GetAtomWithIdx(i)
        atom.SetNumExplicitHs(atom.GetNumExplicitHs() + n)

    def attach(self, i: int, unit: _Unit, n: int) -> None:
        """Hang ``n`` copies of ``unit`` on atom ``i``."""
        for _ in range(n):
            if unit.kind == "hydrogen":
                self.add_h(i, 1)
            else:
                head, _ = self.merge(unit)
                self.bond(i, head)

    def place(self, unit: _Unit) -> int:
        """Add the next chain unit; pending prefixes attach to it first."""
        head, out = self.merge(unit)
        for prefix, n in self.pending:
            self.attach(head, prefix, n)
        self.pending = []
        if self.current is None:
            if self.head is not None:
                raise _ParseError("the chain has no open end")
            self.head = head
        else:
            self.bond(self.current, head)
        self.current = out
        return head

    def open_ends(self) -> bool:
        """True when the chain could continue at both ends (a repeat unit like CH2)."""
        if self.head is None or self.current is None:
            return False
        if self.head == self.current:
            return self.free(self.head) >= 2
        return self.free(self.head) >= 1 and self.free(self.current) >= 1

    def finish(self) -> None:
        from rdkit import Chem

        if self.pending:
            total = sum(n for _, n in self.pending)
            if self.current is None or self.free(self.current) < total:
                raise _ParseError("multiplied group without a centre")
            for prefix, n in self.pending:
                self.attach(self.current, prefix, n)
            self.pending = []
        if self.head is None:
            raise _ParseError("empty formula")

    def saturate(self) -> None:
        """Raise bond orders where both ends still have valence (C=O, C#N)."""
        from rdkit import Chem

        orders = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}
        for i, j in self.bonds:
            if i not in self.tracked or j not in self.tracked:
                continue
            bond = self.mol.GetBondBetweenAtoms(i, j)
            while self.free(i) > 0 and self.free(j) > 0 and bond.GetBondTypeAsDouble() < 3:
                bond.SetBondType(orders[int(bond.GetBondTypeAsDouble()) + 1])
        for i, valences in self.tracked.items():
            if self._used(i) not in valences:
                raise _ParseError("unfilled or overfilled valence")
        if any(self.slots.values()):
            raise _ParseError("group with an open attachment point")


def _parse_items(tokens: List[Tuple[str, Any]], pos: int, nested: bool):
    """Read ``item count?`` pairs up to a closing bracket (when nested) or the end."""
    items: List[Tuple[Tuple[str, Any], int]] = []
    while pos < len(tokens):
        kind, value = tokens[pos]
        if kind == ")":
            if not nested:
                raise _ParseError("unmatched )")
            return items, pos + 1
        if kind == "count":
            raise _ParseError("count without a group")
        if kind == "(":
            inner, pos = _parse_items(tokens, pos + 1, True)
            if not inner:
                raise _ParseError("empty brackets")
            item: Tuple[str, Any] = ("bracket", inner)
        else:
            item = (kind, value)
            pos += 1
        count = 1
        if pos < len(tokens) and tokens[pos][0] == "count":
            count = tokens[pos][1]
            pos += 1
        if count < 1:
            raise _ParseError("zero multiplier")
        items.append((item, count))
    if nested:
        raise _ParseError("unclosed (")
    return items, pos


def _unit_for(item: Tuple[str, Any]) -> _Unit:
    kind, value = item
    if kind == "element":
        return _element_unit(value)
    if kind == "group":
        return _group_unit(_GROUPS[value])
    if kind == "superatom":
        return _group_unit("*" + value)
    chain = _build(value)
    chain.finish()
    repeat = chain.open_ends()
    unit = _Unit(chain.mol.GetMol(), chain.head, chain.current, dict(chain.slots),
                 dict(chain.tracked), "repeat" if repeat else "branch")
    return unit


def _build(items) -> _Chain:
    chain = _Chain()
    for k, (item, count) in enumerate(items):
        unit = _unit_for(item)
        following = items[k + 1][0] if k + 1 < len(items) else None
        if unit.kind == "hydrogen":
            if chain.current is None:
                chain.pending.append((unit, count))
            else:
                chain.add_h(chain.current, count)
            continue
        if unit.kind == "repeat":
            for _ in range(count):
                chain.place(_unit_for(item))
            continue
        if count > 1 or unit.kind == "branch":
            if chain.current is not None and chain.free(chain.current) >= count:
                chain.attach(chain.current, unit, count)
            else:
                chain.pending.append((unit, count))
            continue
        current = chain.current
        if (unit.kind == "element" and item[1] in ("O", "S") and current is not None
                and chain.tracked.get(current) == (4,) and chain.free(current) >= 3
                and following is not None and following != ("element", "H")):
            # C-O inside a chain with C still short of bonds: a carbonyl (CH3COCH3).
            head, _ = chain.merge(unit)
            chain.bond(current, head, order=2)
            continue
        chain.place(unit)
    return chain


def _salt(text: str) -> Optional[str]:
    """Charge-separated SMILES for an ionic salt such as K2CO3 or Ca(OH)2."""
    from rdkit import Chem

    match = _SALT.match(text)
    if not match:
        return None
    cation, n_cation, bracketed, n_bracketed, plain = match.groups()
    if bracketed:
        anion, n_anion = bracketed, int(n_bracketed)
    elif plain in _ANIONS:
        anion, n_anion = plain, 1
    else:
        split = re.match(r"^(.*?)(\d+)$", plain)
        if not split or split.group(1) not in _ANIONS:
            return None
        anion, n_anion = split.group(1), int(split.group(2))
    if anion not in _ANIONS:
        return None
    n_cation = int(n_cation) if n_cation else 1
    parts = [_CATIONS[cation]] * n_cation + [_ANIONS[anion]] * n_anion
    mol = Chem.MolFromSmiles(".".join(parts))
    if mol is None or sum(a.GetFormalCharge() for a in mol.GetAtoms()) != 0:
        return None
    return Chem.MolToSmiles(mol)


def _notation_counts(items) -> Dict[str, int]:
    """Element counts read directly from the notation, independent of bonding."""
    from collections import Counter

    from ..postconditions import formula_counts

    total: Counter = Counter()
    for item, count in items:
        kind, value = item
        if kind == "bracket":
            part = Counter(_notation_counts(value))
        elif kind == "element":
            part = Counter({value: 1})
        else:
            part = formula_counts(_unit_for(item).mol)
        for element, n in part.items():
            total[element] += n * count
    return total


def _parse(text: str) -> Optional[str]:
    """Parse a condensed formula; None when it cannot be read with full confidence."""
    from rdkit import Chem, RDLogger

    from ..postconditions import check_formula

    salt = _salt(text)
    if salt is not None:
        return salt
    RDLogger.DisableLog("rdApp.*")
    try:
        tokens = _lex(text)
        if sum(1 for t in tokens if t[0] not in ("count", "(", ")")) < 2:
            return None
        items, _ = _parse_items(tokens, 0, False)
        chain = _build(items)
        chain.finish()
        chain.saturate()
        mol = chain.mol.GetMol()
        Chem.SanitizeMol(mol)
        if not check_formula(_notation_counts(items), mol).ok:
            return None
        return Chem.MolToSmiles(mol)
    except (_ParseError, ValueError, KeyError, RuntimeError):
        return None
    finally:
        RDLogger.EnableLog("rdApp.*")


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

    Reads named groups (Ph, Et, tBu, NO2, CO2H, ...), the superatom
    abbreviation vocabulary, elements, hydrogens and bracketed groups with
    leading or trailing multipliers, and writes ionic salts (K2CO3, NaOtBu)
    as separate ions.

    Returns a canonical SMILES string, or ``None`` if parsing fails, the
    input doesn't look like a condensed formula, or the formula counted from
    the notation differs from that of the molecule built from it.

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

    return _parse(clean)
