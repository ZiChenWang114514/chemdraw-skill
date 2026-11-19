"""Result post-conditions: checks a tool runs on its own output before it reports success.

Every check is a small pure function that returns a :class:`PostconditionResult`.
A tool that gets ``ok=False`` from a check turns it into a failure payload with
:func:`failure_payload` instead of returning the chemically wrong result as a success.

Structures are given as SMILES strings or RDKit molecules; CDXML is read with
:mod:`cdxml_toolkit.chemistry_semantics` and structural differences come from
:func:`cdxml_toolkit.chemistry_diff.structural_diff`.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Union
from xml.etree import ElementTree as ET

from rdkit import Chem

from .chemistry_diff import structural_diff
from .chemistry_semantics import _NONMETALS, read_fragments, semantic_key

Structure = Union[str, "Chem.Mol"]


@dataclass(frozen=True)
class PostconditionResult:
    """Outcome of one check. ``code`` is a stable machine-readable identifier."""

    ok: bool
    code: str
    message: str
    details: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.ok


def _passed(code: str, message: str, **details: Any) -> PostconditionResult:
    return PostconditionResult(True, code, message, details)


def _failed(code: str, message: str, **details: Any) -> PostconditionResult:
    return PostconditionResult(False, code, message, details)


def _mol(value: Structure) -> "Chem.Mol":
    if isinstance(value, Chem.Mol):
        return value
    if isinstance(value, str):
        mol = Chem.MolFromSmiles(value)
        if mol is not None:
            return mol
    raise ValueError(f"not a readable structure: {value!r}")


def _smiles(value: Structure) -> str:
    return Chem.MolToSmiles(_mol(value))


# --- structure-level checks -----------------------------------------------------------------

def check_changed(before: Structure, after: Structure) -> PostconditionResult:
    """An edit must change the structure; a no-op is not a successful edit."""
    old, new = semantic_key(_mol(before)), semantic_key(_mol(after))
    if old == new:
        return _failed("no_change", "The edit left the structure unchanged.", structure=new)
    return _passed("changed", "The structure changed.", before=old, after=new)


def check_preserved(before: Structure, after: Structure, *, targeted_atoms: Iterable[int] = (),
                    timeout: int = 5) -> PostconditionResult:
    """Atoms and bonds outside ``targeted_atoms`` (atom indices of ``before``) are unchanged.

    The comparison is the MCS diff of :func:`structural_diff`; an incomplete or ambiguous
    comparison fails, because preservation could not be shown.
    """
    targeted = set(targeted_atoms)
    diff = structural_diff(_smiles(before), _smiles(after), timeout=timeout)
    if diff["status"] != "completed":
        return _failed("preservation_unverified",
                       f"Preservation could not be verified ({diff.get('reason') or diff['status']}).",
                       diff=diff)
    reverse = {after: before for before, after in diff["atom_mapping"] or []}
    stray = []
    for change in diff["atom_changes"] + diff["bond_changes"] + diff["stereo_changes"]:
        involved = set()
        if "before_atom" in change:
            involved.add(change["before_atom"])
        involved.update(change.get("before_atoms") or [])
        involved.update(reverse[i] for i in change.get("after_atoms") or [] if i in reverse)
        if "after_atom" in change and change["after_atom"] in reverse:
            involved.add(reverse[change["after_atom"]])
        # A change is allowed when it touches a targeted atom; new atoms alone count as the edit.
        if involved and not involved & targeted:
            stray.append(change)
    if stray:
        return _failed("structure_not_preserved",
                       f"{len(stray)} change(s) touch atoms that were not targeted.", changes=stray)
    return _passed("structure_preserved", "Only the targeted atoms changed.", diff=diff)


def unspecified_stereocentres(value: Structure) -> list[int]:
    """Indices of tetrahedral stereocentres without an assigned configuration."""
    mol = _mol(value)
    return [index for index, label in Chem.FindMolChiralCenters(
        mol, includeUnassigned=True, useLegacyImplementation=False) if label == "?"]


def check_stereocentres(value: Structure, *, max_unspecified: int = 0) -> PostconditionResult:
    """At most ``max_unspecified`` stereocentres may lack a configuration."""
    missing = unspecified_stereocentres(value)
    if len(missing) > max_unspecified:
        return _failed("stereo_incomplete",
                       f"{len(missing)} stereocentre(s) have no configuration.",
                       unspecified=missing, count=len(missing))
    return _passed("stereo_complete", "Stereocentres are specified.", unspecified=missing,
                   count=len(missing))


def total_charge(value: Structure) -> int:
    return sum(atom.GetFormalCharge() for atom in _mol(value).GetAtoms())


def check_charge_conserved(before: Structure, after: Structure, *,
                           expected_change: int = 0) -> PostconditionResult:
    """Net charge of ``after`` equals that of ``before`` plus ``expected_change``."""
    old, new = total_charge(before), total_charge(after)
    if new - old != expected_change:
        return _failed("charge_not_conserved",
                       f"Net charge went from {old:+d} to {new:+d}.", before=old, after=new,
                       expected_change=expected_change)
    return _passed("charge_conserved", "Net charge is as expected.", before=old, after=new)


def _is_lone_metal(fragment: "Chem.Mol") -> bool:
    if fragment.GetNumAtoms() != 1:
        return False
    atom = fragment.GetAtomWithIdx(0)
    return atom.GetAtomicNum() not in _NONMETALS and atom.GetFormalCharge() == 0


def check_connected_metal(value: Structure, *, max_ligand_fragments: int = 1) -> PostconditionResult:
    """Flag an organometallic drawn as a neutral lone metal atom beside several ligand pieces.

    ``[Pd].P(c1ccccc1)(c1ccccc1)c1ccccc1.P(...)...`` is a complex whose metal-ligand bonds
    were lost. Charged counter-ions (``[K+].[K+].[O-]C([O-])=O``) are not affected.
    """
    fragments = Chem.GetMolFrags(_mol(value), asMols=True, sanitizeFrags=False)
    metals = [Chem.MolToSmiles(f) for f in fragments if _is_lone_metal(f)]
    ligands = [Chem.MolToSmiles(f) for f in fragments
               if not _is_lone_metal(f) and any(a.GetAtomicNum() == 6 for a in f.GetAtoms())]
    if metals and len(ligands) > max_ligand_fragments:
        return _failed("disconnected_organometallic",
                       f"A lone metal atom ({', '.join(metals)}) sits beside {len(ligands)} separate "
                       "ligand fragments; the metal-ligand bonds are missing.",
                       metals=metals, ligands=ligands)
    return _passed("metal_connectivity_plausible", "No lone metal atom with separate ligands.")


# --- formula ----------------------------------------------------------------------------------

_FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?|\(|\))(\d*)")


def formula_counts(value: Union[str, Mapping[str, int], "Chem.Mol"]) -> Counter:
    """Element counts (hydrogens included) of a molecule, a mapping, or a plain formula
    such as ``C4H9Br`` or ``Ca(OH)2``. A SMILES string is not a formula: pass a Mol."""
    if isinstance(value, Chem.Mol):
        counts = Counter()
        for atom in value.GetAtoms():
            counts[atom.GetSymbol()] += 1
            if atom.GetTotalNumHs():
                counts["H"] += atom.GetTotalNumHs()
        return counts
    if isinstance(value, Mapping):
        return Counter({k: int(v) for k, v in value.items() if v})
    text = str(value).replace(" ", "")
    stack = [Counter()]
    position = 0
    for match in _FORMULA_TOKEN.finditer(text):
        if match.start() != position:
            raise ValueError(f"not a molecular formula: {value!r}")
        position = match.end()
        token, digits = match.group(1), match.group(2)
        count = int(digits) if digits else 1
        if token == "(":
            if digits:
                raise ValueError(f"not a molecular formula: {value!r}")
            stack.append(Counter())
        elif token == ")":
            if len(stack) == 1:
                raise ValueError(f"unbalanced parentheses in {value!r}")
            inner = stack.pop()
            for element, n in inner.items():
                stack[-1][element] += n * count
        else:
            stack[-1][token] += count
    if position != len(text) or len(stack) != 1 or not text:
        raise ValueError(f"not a molecular formula: {value!r}")
    return stack[0]


def hill_formula(counts: Mapping[str, int]) -> str:
    counts = {k: v for k, v in counts.items() if v}
    first = [k for k in ("C", "H") if k in counts] if "C" in counts else []
    order = first + sorted(k for k in counts if k not in first)
    return "".join(f"{k}{counts[k] if counts[k] != 1 else ''}" for k in order)


def check_formula(expected: Union[str, Mapping[str, int]], value: Structure) -> PostconditionResult:
    """The formula computed from the input notation equals the formula of the result."""
    want = formula_counts(expected)
    got = formula_counts(_mol(value))
    if want != got:
        return _failed("formula_mismatch",
                       f"The notation gives {hill_formula(want)} but the structure is {hill_formula(got)}.",
                       expected=hill_formula(want), actual=hill_formula(got))
    return _passed("formula_matches", "Formula matches the notation.", formula=hill_formula(got))


# --- CDXML annotations ----------------------------------------------------------------------

_CHARGE_TEXT = re.compile(r"^\s*(\d*)\s*([+\-−])\s*$|^\s*([+\-−])\s*(\d*)\s*$")
_RADICAL_TEXT = {"•", "·", "●"}


def _text_of(element: ET.Element) -> str:
    return "".join(s.text or "" for s in element.iter("s")) or (element.text or "")


def check_cdxml_annotations(cdxml: Union[str, Path]) -> PostconditionResult:
    """Charges and radicals a reader sees in the drawing agree with the semantic structure.

    Visible signs are node ``Charge``/``Radical`` attributes plus free text objects
    (outside any fragment) that read only as a charge (``+``, ``2-``) or a radical dot.
    A sign drawn as free text carries no chemistry, so it shows up as a disagreement.
    """
    root = ET.parse(str(cdxml)).getroot() if isinstance(cdxml, Path) else ET.fromstring(cdxml)
    parents = {child: parent for parent in root.iter() for child in parent}

    def inside_fragment(element):
        parent = parents.get(element)
        while parent is not None:
            if parent.tag == "fragment":
                return True
            parent = parents.get(parent)
        return False

    visible_charge = visible_radicals = 0
    for node in root.iter("n"):
        if node.get("Charge", "").lstrip("-").isdigit():
            visible_charge += int(node.get("Charge"))
        if node.get("Radical") in ("Doublet", "Triplet", "Singlet", "Diradical"):
            visible_radicals += 1
    loose = []
    for text in root.iter("t"):
        if inside_fragment(text):
            continue
        content = _text_of(text).strip()
        match = _CHARGE_TEXT.match(content) if content else None
        if match:
            digits = match.group(1) or match.group(4) or "1"
            sign = match.group(2) or match.group(3)
            visible_charge += int(digits) * (1 if sign == "+" else -1)
            loose.append(content)
        elif content in _RADICAL_TEXT:
            visible_radicals += 1
            loose.append(content)
    mols = [mol for _, mol in read_fragments(cdxml)]
    semantic_charge = sum(a.GetFormalCharge() for m in mols for a in m.GetAtoms())
    semantic_radicals = sum(1 for m in mols for a in m.GetAtoms()
                            if a.GetNumRadicalElectrons() and not (
                                a.GetDegree() == 0 and a.GetFormalCharge() == 0
                                and a.GetAtomicNum() not in _NONMETALS))
    details = dict(visible_charge=visible_charge, semantic_charge=semantic_charge,
                   visible_radicals=visible_radicals, semantic_radicals=semantic_radicals,
                   loose_text=loose)
    if visible_charge != semantic_charge or visible_radicals != semantic_radicals:
        return _failed("annotation_mismatch",
                       "Charges or radicals drawn in the document do not match its structures "
                       f"(drawn charge {visible_charge:+d}, structure {semantic_charge:+d}; drawn radicals "
                       f"{visible_radicals}, structure {semantic_radicals}).", **details)
    return _passed("annotations_consistent", "Drawn charges and radicals match the structures.", **details)


# --- tool payload ---------------------------------------------------------------------------

def failure_payload(result: PostconditionResult, rejected_result: Any = None, *,
                    hint: str | None = None) -> dict:
    """Tool-level failure for a failed post-condition, keeping the rejected output for inspection."""
    if result.ok:
        raise ValueError("failure_payload needs a failed post-condition")
    return {
        "ok": False,
        "error": {"code": "postcondition_failed", "message": result.message,
                  "hint": hint or f"Post-condition {result.code!r} failed; the output was not accepted.",
                  "postcondition": result.code, "details": result.details},
        "rejected_result": rejected_result,
    }


def first_failure(*results: PostconditionResult) -> PostconditionResult | None:
    """The first failed result, or None when every check passed."""
    return next((r for r in results if not r.ok), None)
