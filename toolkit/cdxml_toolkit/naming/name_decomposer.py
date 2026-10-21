"""
Name-driven IUPAC decomposition.

Parse the bracket hierarchy of an IUPAC name to find substituent
boundaries, then generate alternative valid names by swapping
parent ↔ substituent roles.  Uses ChemDraw (via ChemScript) as
the naming oracle — we never try to parse IUPAC grammar ourselves.

Usage:
    python name_decomposer.py <SMILES> [-v] [--json] [--max-depth N]
"""
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import List, Optional, Tuple

from rdkit import Chem, RDLogger
from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge

RDLogger.logger().setLevel(RDLogger.ERROR)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BracketNode:
    """A parenthesised group in an IUPAC name."""
    text: str            # content inside the parens (excluding the parens)
    start: int           # index of '(' in the full name
    end: int             # index of ')' in the full name (inclusive)
    children: List["BracketNode"] = field(default_factory=list)
    depth: int = 0       # nesting depth (0 = top-level group)
    kind: str = ""       # "stereo" | "multiplier" | "substituent" | "unknown"


@dataclass
class Alternative:
    """One alternative IUPAC name for the molecule."""
    name: str
    parent_name: str     # name of the fragment used as parent
    sub_name: str        # name of the fragment used as substituent
    locant: str          # locant on the new parent
    valid: bool          # round-trip validated?
    strategy: str = ""   # how the name was assembled
    notes: str = ""


@dataclass
class DecompositionResult:
    original_smiles: str
    canonical_smiles: str
    canonical_name: str
    bracket_tree: Optional[BracketNode]
    alternatives: List[Alternative] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    canonical_parent: str = ""  # parent name in the canonical naming


# ---------------------------------------------------------------------------
# Bracket tree parser
# ---------------------------------------------------------------------------

def parse_bracket_tree(name: str) -> BracketNode:
    """Parse parenthesised groups in an IUPAC name into a tree.

    Skips square brackets [...] (stereo descriptors, ring-fusion).
    Returns a root node whose children are the top-level (...) groups.
    """
    root = BracketNode(text=name, start=0, end=len(name) - 1, depth=-1)
    stack: List[Tuple[int, int]] = []   # (start_pos, depth)
    nodes_by_depth: dict[int, List[BracketNode]] = {}
    i = 0
    while i < len(name):
        ch = name[i]
        if ch == '[':
            # skip entire [...] block
            j = name.find(']', i + 1)
            if j == -1:
                i += 1
            else:
                i = j + 1
            continue
        if ch == '(':
            depth = len(stack)
            stack.append((i, depth))
        elif ch == ')' and stack:
            start_pos, depth = stack.pop()
            text = name[start_pos + 1:i]
            node = BracketNode(
                text=text, start=start_pos, end=i, depth=depth
            )
            nodes_by_depth.setdefault(depth, []).append(node)
        i += 1

    # Build tree: depth-0 nodes are children of root; depth-N nodes are
    # children of the nearest enclosing depth-(N-1) node.
    all_depths = sorted(nodes_by_depth.keys())
    for d in all_depths:
        if d == 0:
            root.children = nodes_by_depth[d]
        else:
            parent_nodes = nodes_by_depth.get(d - 1, [])
            for node in nodes_by_depth[d]:
                # Find the parent that encloses this node
                for pn in parent_nodes:
                    if pn.start < node.start and node.end < pn.end:
                        pn.children.append(node)
                        break

    return root


# ---------------------------------------------------------------------------
# Bracket group classification
# ---------------------------------------------------------------------------

# Patterns that are NOT substituents
_STEREO_RE = re.compile(
    r'^[RSEZ±]$|^rac$|^rel$|^[RSrs],[RSrs]$|^[0-9]+[RSEZ]$'
    r'|^[0-9]+[a-z]*[RSEZ](,[0-9]+[a-z]*[RSEZ])*$',
    re.IGNORECASE
)
_MULTIPLIER_RE = re.compile(
    r'^di$|^tri$|^tetra$|^penta$|^hexa$|^bis$|^tris$', re.IGNORECASE
)
_NUMBERSONLY_RE = re.compile(r'^[\d,\' ]+$')


def classify_node(node: BracketNode) -> str:
    """Quick regex classification of a bracket group.

    Returns "stereo", "multiplier", "skip", or "candidate".
    """
    t = node.text.strip()
    if not t:
        return "skip"
    if _STEREO_RE.match(t):
        return "stereo"
    if _MULTIPLIER_RE.match(t):
        return "multiplier"
    if _NUMBERSONLY_RE.match(t):
        return "skip"  # ring assembly numbering
    # Very short texts are unlikely to be substituents
    if len(t) <= 2 and not t.endswith("yl"):
        return "skip"
    return "candidate"


# ---------------------------------------------------------------------------
# ChemDraw interaction helpers
# ---------------------------------------------------------------------------

_cs: Optional[ChemScriptBridge] = None


def _get_cs() -> ChemScriptBridge:
    global _cs
    if _cs is None:
        _cs = ChemScriptBridge()
    return _cs


def _name_to_smiles(name: str) -> Optional[str]:
    """Try to resolve an IUPAC name to SMILES via ChemDraw."""
    try:
        smi = _get_cs().write_data(name, "smiles", source_format="name")
        if smi and Chem.MolFromSmiles(smi) is not None:
            return smi
    except Exception:
        pass
    return None


def _smiles_to_name(smiles: str) -> Optional[str]:
    """Get IUPAC name for a SMILES string."""
    try:
        return _get_cs().get_name(smiles)
    except Exception:
        return None


def _canonical(smiles: str) -> Optional[str]:
    """RDKit canonical SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def _add_at(mol: Chem.Mol, atom_idx: int) -> Optional[Tuple[Chem.Mol, str]]:
    """Add astatine (At, Z=85) at a specific atom. Return (mol, smiles).

    For ring NH atoms, At replaces the H (removes one explicit H).
    """
    edit = Chem.RWMol(mol)
    target = edit.GetAtomWithIdx(atom_idx)
    # If target is ring N/O with explicit H, At replaces H
    if (target.IsInRing() and target.GetAtomicNum() != 6
            and target.GetTotalNumHs() > 0):
        explicit_h = target.GetNumExplicitHs()
        if explicit_h > 0:
            target.SetNumExplicitHs(explicit_h - 1)
    at_idx = edit.AddAtom(Chem.Atom(85))
    edit.AddBond(atom_idx, at_idx, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(edit)
        result = edit.GetMol()
        return result, Chem.MolToSmiles(result)
    except Exception:
        return None


def _get_yl_via_acid_probe(mol: Chem.Mol, attach_idx: int,
                           verbose: bool = False) -> Optional[str]:
    """Get the -yl substituent form of a fragment using icosanoic acid probe.

    Attaches the fragment to icosanoic acid (C20, COOH), names the result via
    ChemDraw, and extracts the -yl name from "20-(SUBSTITUENT)icosanoic acid".

    Uses C20 acid because:
    - COOH is a PCG → always forces the chain as naming parent
    - No drug molecule has a C20 chain → zero confusion
    - Locant 20 and "icosanoic acid" suffix are unambiguous to parse
    """
    acid = Chem.MolFromSmiles("CCCCCCCCCCCCCCCCCCCC(=O)O")
    if acid is None:
        return None

    combo = Chem.RWMol(Chem.CombineMols(mol, acid))
    # The acid's first carbon (C20, terminal) is at offset = mol.GetNumAtoms()
    acid_c_idx = mol.GetNumAtoms()
    combo.AddBond(attach_idx, acid_c_idx, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(combo)
    except Exception:
        return None

    acid_smi = Chem.MolToSmiles(combo.GetMol())
    acid_name = _smiles_to_name(acid_smi)
    if acid_name is None:
        return None

    if verbose:
        print(f"    Icosanoic acid probe: '{acid_name}'", file=sys.stderr)

    # Extract -yl form from "20-(substituent)icosanoic acid"
    m = re.match(r'20-\((.+)\)icosanoic acid$', acid_name)
    if m:
        return m.group(1)
    # Try without parentheses: "20-substitutenticosanoic acid"
    m = re.match(r'20-(.+)icosanoic acid$', acid_name)
    if m:
        return m.group(1)
    return None


_ACID_SMILES = "CCCCCCCCCCCCCCCCCCCC(=O)O"


def _get_yl_via_selenyl_probe(mol: Chem.Mol, attach_idx: int,
                               verbose: bool = False) -> Optional[str]:
    """Get the -yl substituent form via a Se-linked icosanoic acid probe.

    Builds: fragment—Se—CH₂(C₁₈)—COOH, names via ChemDraw, extracts
    the substituent name from ``20-({sub}selanyl)icosanoic acid``.

    The Se linker isolates the fragment from the acid chain, which avoids
    the ambiguity that breaks the direct acid probe for carbonyl and
    hydroxyl fragments (formyl, acetyl, Boc, phenylmethanol, etc.).
    """
    acid = Chem.MolFromSmiles(_ACID_SMILES)
    if acid is None:
        return None

    combo = Chem.RWMol(Chem.CombineMols(mol, acid))
    se_idx = combo.AddAtom(Chem.Atom(34))           # Se
    combo.AddBond(attach_idx, se_idx, Chem.BondType.SINGLE)
    acid_c_start = mol.GetNumAtoms()                 # C-20 of the acid
    combo.AddBond(se_idx, acid_c_start, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(combo)
    except Exception:
        return None

    probe_smi = Chem.MolToSmiles(combo.GetMol())
    probe_name = _smiles_to_name(probe_smi)
    if probe_name is None:
        return None

    if verbose:
        print(f"    Se-probe: '{probe_name}'", file=sys.stderr)

    # Extract from "20-({sub}selanyl)icosanoic acid"
    m = re.match(r'20-\((.+?)selanyl\)icosanoic acid$', probe_name)
    if m:
        return m.group(1)
    # Without outer parens: "20-{sub}selanylicosanoic acid"
    m = re.match(r'20-(.+?)selanylicosanoic acid$', probe_name)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Public fragment-naming API
# ---------------------------------------------------------------------------

# Simple single-atom substituent lookup (avoids ChemScript calls)
_SIMPLE_SUB_MAP = {
    9: "fluoro",     # F
    17: "chloro",    # Cl
    35: "bromo",     # Br
    53: "iodo",      # I
}


def _name_via_naphthalene_probe(mol: Chem.Mol, attach_idx: int,
                                verbose: bool = False) -> Optional[str]:
    """Fallback naming: attach fragment to naphthalene, extract substituent.

    Used when the icosanoic acid probe fails (e.g. for simple alkyl groups
    that merge into the acid chain).  Naphthalene is a named bicyclic ring
    system that takes IUPAC parent priority over most drug-like fragments.

    Extracts from "2-(SUBSTITUENT)naphthalene" or "2-SUBSTITUENTnaphthalene".
    """
    naph = Chem.MolFromSmiles("c1ccc2ccccc2c1")
    if naph is None:
        return None

    combo = Chem.RWMol(Chem.CombineMols(mol, naph))
    # Naphthalene position 2 = first atom after offset in canonical SMILES.
    # In 'c1ccc2ccccc2c1' the atoms are ordered 0-9; position 2 corresponds
    # to atom index 1 in canonical ordering.  We use index 1 (the second
    # carbon of the first ring — bonded to C1 and C3).
    naph_c2_idx = mol.GetNumAtoms() + 1  # offset + 1
    combo.AddBond(attach_idx, naph_c2_idx, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(combo)
    except Exception:
        return None

    combo_smi = Chem.MolToSmiles(combo.GetMol())
    combo_name = _smiles_to_name(combo_smi)
    if combo_name is None:
        return None

    if verbose:
        print(f"    Naphthalene probe: '{combo_name}'", file=sys.stderr)

    # Try bracketed form first: "2-(substituent)naphthalene"
    m = re.match(r'\d+-\((.+)\)naphthalene$', combo_name)
    if m:
        return m.group(1)
    # Unbracketed: "2-substituentnaphthalene"
    m = re.match(r'\d+-(.+)naphthalene$', combo_name)
    if m:
        return m.group(1)
    return None


@lru_cache(maxsize=256)
def _name_fragment_cached(canonical_frag_smiles: str,
                          verbose: bool = False) -> Optional[str]:
    """Cache-friendly inner function keyed on canonical SMILES."""
    mol = Chem.MolFromSmiles(canonical_frag_smiles)
    if mol is None:
        return None

    # Find dummy atom
    dummy_idx = None
    attach_idx = None
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0:
            dummy_idx = atom.GetIdx()
            break
    if dummy_idx is None:
        return None

    # Find the neighbor (attachment atom in the fragment)
    dummy_atom = mol.GetAtomWithIdx(dummy_idx)
    neighbors = list(dummy_atom.GetNeighbors())
    if not neighbors:
        return None
    attach_idx = neighbors[0].GetIdx()

    # --- Simple single-atom check ---
    # If the fragment is just [*]-X where X is a single heavy atom with no
    # other heavy-atom neighbors, use the lookup table.
    attach_atom = mol.GetAtomWithIdx(attach_idx)
    heavy_neighbors_of_attach = [
        n for n in attach_atom.GetNeighbors() if n.GetAtomicNum() != 0
    ]
    if (mol.GetNumHeavyAtoms() == 2   # [*] + one heavy atom
            and attach_atom.GetAtomicNum() in _SIMPLE_SUB_MAP
            and not heavy_neighbors_of_attach):
        return _SIMPLE_SUB_MAP[attach_atom.GetAtomicNum()]

    # Check for heteroatom directly bonded to dummy with further structure:
    # [*]O (hydroxy), [*]N (amino), [*]S (sulfanyl) — only when no other
    # heavy neighbors of the heteroatom (otherwise it's part of a bigger fragment)
    if (mol.GetNumHeavyAtoms() == 2
            and not heavy_neighbors_of_attach):
        z = attach_atom.GetAtomicNum()
        if z == 8:
            return "hydroxy"
        if z == 7:
            return "amino"
        if z == 16:
            return "sulfanyl"

    # --- General case: use icosanoic acid probe ---
    # Remove the dummy atom and prepare clean fragment mol
    edit = Chem.RWMol(mol)
    edit.RemoveAtom(dummy_idx)
    # Adjust attach_idx for the removal
    adjusted_idx = attach_idx if attach_idx < dummy_idx else attach_idx - 1
    try:
        Chem.SanitizeMol(edit)
    except Exception:
        return None

    frag_clean = edit.GetMol()

    # Try acid probe first (works for ring-based and hetero-chain fragments)
    result = _get_yl_via_acid_probe(frag_clean, adjusted_idx, verbose=verbose)
    if result is not None:
        return result

    # Acid probe fails for simple alkyls (they extend the C20 chain).
    # Fallback: attach to naphthalene and extract from "2-(X)naphthalene".
    naph_result = _name_via_naphthalene_probe(frag_clean, adjusted_idx,
                                              verbose=verbose)
    if naph_result is not None:
        return naph_result

    # Both probes failed — try acyl fragment detection.
    # Acyl groups ([*]-C(=O)-R) cause probe parents to flip because C=O
    # becomes the principal characteristic group.
    # Strategy: detect C=O at attachment, cap with OH → carboxylic acid form,
    # name the acid, derive the acyl prefix.
    attach_a = frag_clean.GetAtomWithIdx(adjusted_idx)
    if attach_a.GetAtomicNum() == 6:
        # Check for C=O double bond on attachment carbon
        carbonyl_o_idx = None
        for bond in attach_a.GetBonds():
            other = frag_clean.GetAtomWithIdx(bond.GetOtherAtomIdx(adjusted_idx))
            if (other.GetAtomicNum() == 8
                    and bond.GetBondType() == Chem.BondType.DOUBLE):
                carbonyl_o_idx = other.GetIdx()
                break
        if carbonyl_o_idx is not None:
            # Build the carboxylic acid: add OH at the attachment point
            acid_edit = Chem.RWMol(frag_clean)
            oh_idx = acid_edit.AddAtom(Chem.Atom(8))
            acid_edit.AddBond(adjusted_idx, oh_idx, Chem.BondType.SINGLE)
            try:
                Chem.SanitizeMol(acid_edit)
                acid_smi = Chem.MolToSmiles(acid_edit.GetMol())
                acid_name = _smiles_to_name(acid_smi)
                if verbose:
                    print(f"    Acyl acid form: '{acid_name}'",
                          file=sys.stderr)
                if acid_name:
                    # Convert acid name → acyl prefix:
                    #   "formic acid" → "formyl"
                    #   "acetic acid" → "acetyl"
                    #   "benzoic acid" → "benzoyl"
                    #   "X-ic acid" → "X-yl" (general rule)
                    if acid_name.endswith("ic acid"):
                        base = acid_name[:-len("ic acid")]
                        if base.endswith("carboxyl"):
                            return base + "yl"
                        return base + "yl"
            except Exception:
                pass

            # Acyl-ester pattern: [*]-C(=O)-O-R → "(R-oxy)carbonyl"
            # Detect: attachment C has C=O and also single-bonded O
            ester_o_idx = None
            for bond in attach_a.GetBonds():
                other_idx = bond.GetOtherAtomIdx(adjusted_idx)
                other = frag_clean.GetAtomWithIdx(other_idx)
                if (other.GetAtomicNum() == 8
                        and bond.GetBondType() == Chem.BondType.SINGLE
                        and other_idx != carbonyl_o_idx):
                    ester_o_idx = other_idx
                    break

            if ester_o_idx is not None:
                # Build the R-OH fragment (the ester's alcohol)
                # Break bond at carbonyl C → ester O, replace with [*]
                r_edit = Chem.RWMol(frag_clean)
                r_edit.RemoveBond(adjusted_idx, ester_o_idx)
                # Remove the C=O + attachment side, keep the O-R side
                # Simpler: build [*]-O-R directly
                r_frag = Chem.RWMol()
                # BFS from ester_o_idx to collect all atoms on that side
                visited_r = set()
                queue_r = [ester_o_idx]
                while queue_r:
                    ai = queue_r.pop()
                    if ai in visited_r or ai == adjusted_idx:
                        continue
                    visited_r.add(ai)
                    for nbr in frag_clean.GetAtomWithIdx(ai).GetNeighbors():
                        ni = nbr.GetIdx()
                        if ni != adjusted_idx and ni not in visited_r:
                            queue_r.append(ni)

                old_to_new_r = {}
                for old_i in sorted(visited_r):
                    src = frag_clean.GetAtomWithIdx(old_i)
                    na = Chem.Atom(src.GetAtomicNum())
                    na.SetFormalCharge(src.GetFormalCharge())
                    na.SetIsAromatic(src.GetIsAromatic())
                    new_i = r_frag.AddAtom(na)
                    old_to_new_r[old_i] = new_i

                # Add dummy at where the C(=O) was
                dummy_new = r_frag.AddAtom(Chem.Atom(0))
                r_frag.AddBond(old_to_new_r[ester_o_idx], dummy_new,
                               Chem.BondType.SINGLE)

                # Add bonds within R-O fragment
                for old_i in visited_r:
                    for bond in frag_clean.GetAtomWithIdx(old_i).GetBonds():
                        other_i = bond.GetOtherAtomIdx(old_i)
                        if other_i in visited_r and old_i < other_i:
                            r_frag.AddBond(old_to_new_r[old_i],
                                           old_to_new_r[other_i],
                                           bond.GetBondType())
                try:
                    Chem.SanitizeMol(r_frag)
                    r_smi = Chem.MolToSmiles(r_frag)
                    # Name the [*]-O-R fragment → should give "R-oxy"
                    r_name = name_fragment_as_substituent(r_smi, verbose=verbose)
                    if r_name:
                        return f"({r_name})carbonyl"
                except Exception:
                    pass

    return None


def name_fragment_as_substituent(frag_smiles: str,
                                  verbose: bool = False) -> Optional[str]:
    """Convert a [*]-bearing fragment SMILES to its IUPAC substituent prefix.

    Uses the icosanoic acid probe (C20 acid): attaches the fragment at [*]
    to the acid's terminal carbon, names the whole molecule via ChemScript,
    and extracts the substituent from "20-(SUBSTITUENT)icosanoic acid".

    For simple single-atom fragments (F, Cl, Br, I, O, N, S) a direct
    lookup table is used to avoid a ChemScript call.

    Args:
        frag_smiles: SMILES with [*] marking the attachment point.
                     E.g. "[*]c1ccccc1" for phenyl, "[*]F" for fluoro.
        verbose: Print debug info to stderr.

    Returns:
        Substituent prefix name (e.g. "phenyl", "fluoro", "morpholino",
        "(piperidin-1-yl)") or None on failure.

    Examples::

        >>> name_fragment_as_substituent("[*]F")
        'fluoro'
        >>> name_fragment_as_substituent("[*]c1ccccc1")
        'phenyl'
    """
    # Canonicalise the fragment SMILES for cache lookup
    mol = Chem.MolFromSmiles(frag_smiles)
    if mol is None:
        return None
    canon = Chem.MolToSmiles(mol)
    return _name_fragment_cached(canon, verbose=verbose)


def _get_yl_suffix_via_acid(parent_mol: Chem.Mol, parent_attach_idx: int,
                            heteroatom_num: int,
                            verbose: bool = False) -> Optional[str]:
    """Get the -yl+suffix form by building parent + heteroatom + icosanoic acid.

    For heteroatom linkages (O, N, S), the substituent name includes the
    heteroatom suffix (e.g., "pyridin-4-yloxy" for O, "phenylamino" for N).
    We build: parent-[heteroatom]-icosanoic_acid, name it, and extract
    the substituent from "20-(SUBSTITUENT)icosanoic acid".
    """
    acid = Chem.MolFromSmiles("CCCCCCCCCCCCCCCCCCCC(=O)O")
    if acid is None:
        return None
    het_atom = Chem.Atom(heteroatom_num)
    combo = Chem.RWMol(Chem.CombineMols(parent_mol, acid))
    het_idx = combo.AddAtom(het_atom)
    combo.AddBond(parent_attach_idx, het_idx, Chem.BondType.SINGLE)
    acid_c_start = parent_mol.GetNumAtoms()
    combo.AddBond(het_idx, acid_c_start, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(combo)
    except Exception:
        return None
    acid_name = _smiles_to_name(Chem.MolToSmiles(combo.GetMol()))
    if acid_name is None:
        return None
    if verbose:
        print(f"    Acid+heteroatom probe: '{acid_name}'", file=sys.stderr)
    m = re.match(r'20-\((.+)\)icosanoic acid$', acid_name)
    if m:
        return m.group(1)
    m = re.match(r'20-(.+)icosanoic acid$', acid_name)
    if m:
        return m.group(1)
    return None


def _get_locant_replace_heteroatom(sub_mol: Chem.Mol, sub_attach_idx: int,
                                   verbose: bool = False
                                   ) -> Optional[Tuple[str, Optional[str]]]:
    """Remove heteroatom from sub fragment, add At to its C neighbor, name.

    Returns (at_probe_name, locant) or None.
    The At-probe name serves as the assembly template: replace "astato" with
    the yl+suffix form to get the swapped name.
    """
    het_atom = sub_mol.GetAtomWithIdx(sub_attach_idx)
    # Find carbon neighbor of the heteroatom within the fragment
    c_neighbor_idx = None
    for n in het_atom.GetNeighbors():
        if n.GetAtomicNum() == 6:
            c_neighbor_idx = n.GetIdx()
            break
    if c_neighbor_idx is None:
        return None

    edit = Chem.RWMol(sub_mol)
    edit.RemoveAtom(sub_attach_idx)
    try:
        Chem.SanitizeMol(edit)
    except Exception:
        return None

    # Adjust index after atom removal
    new_c_idx = (c_neighbor_idx - 1
                 if sub_attach_idx < c_neighbor_idx else c_neighbor_idx)
    at_i = edit.AddAtom(Chem.Atom(85))
    edit.AddBond(new_c_idx, at_i, Chem.BondType.SINGLE)
    try:
        Chem.SanitizeMol(edit)
    except Exception:
        return None

    at_name = _smiles_to_name(Chem.MolToSmiles(edit.GetMol()))
    if at_name is None:
        return None

    if verbose:
        print(f"    Het->At probe: '{at_name}'", file=sys.stderr)

    locant = None
    m = re.search(r'(\d+)-astato', at_name, re.IGNORECASE)
    if m:
        locant = m.group(1)
    elif 'astato' in at_name.lower():
        locant = ""
    return at_name, locant


# ---------------------------------------------------------------------------
# Core decomposition logic
# ---------------------------------------------------------------------------

def validate_as_substituent(full_name: str, node: BracketNode,
                            verbose: bool = False) -> bool:
    """Check if replacing a bracket group with 'astato' gives a valid name.

    This tells us ChemDraw treats that position as a real substituent slot.
    """
    # Build modified name: replace (content) with astato
    before = full_name[:node.start]
    after = full_name[node.end + 1:]
    modified = before + "astato" + after
    if verbose:
        print(f"    At-probe name: {modified}", file=sys.stderr)
    return _name_to_smiles(modified) is not None


def _find_at_atom(mol: Chem.Mol) -> Optional[int]:
    """Find the atom index of At in a molecule."""
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 85:
            return atom.GetIdx()
    return None


def _split_at_at(smiles: str) -> Optional[Tuple[str, str, int]]:
    """Given SMILES containing At, return (parent_smiles, At_neighbor_idx_in_parent).

    Removes At and returns the molecule with At removed, plus the atom index
    where At was attached (for later probe attachment).
    Returns (smiles_without_at, original_smiles, neighbor_idx_in_clean_mol).
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    at_idx = _find_at_atom(mol)
    if at_idx is None:
        return None

    at_atom = mol.GetAtomWithIdx(at_idx)
    neighbors = at_atom.GetNeighbors()
    if not neighbors:
        return None
    neighbor_idx = neighbors[0].GetIdx()

    # Remove At.  Try sanitization first; if it fails (e.g. ring N losing
    # a bond needs H compensation), try again with explicit H.
    edit = Chem.RWMol(mol)
    edit.RemoveAtom(at_idx)
    try:
        Chem.SanitizeMol(edit)
    except Exception:
        # Retry with explicit H on the neighbor (now shifted by At removal)
        edit = Chem.RWMol(mol)
        edit.RemoveAtom(at_idx)
        adj_idx = neighbor_idx - 1 if at_idx < neighbor_idx else neighbor_idx
        atom = edit.GetAtomWithIdx(adj_idx)
        atom.SetNumExplicitHs(atom.GetNumExplicitHs() + 1)
        try:
            Chem.SanitizeMol(edit)
        except Exception:
            return None
    clean_mol = edit.GetMol()
    clean_smi = Chem.MolToSmiles(clean_mol)

    # The neighbor index may have shifted if at_idx < neighbor_idx
    if at_idx < neighbor_idx:
        new_neighbor_idx = neighbor_idx - 1
    else:
        new_neighbor_idx = neighbor_idx

    return clean_smi, smiles, new_neighbor_idx


def get_parent_smiles_from_at_probe(full_name: str,
                                     node: BracketNode) -> Optional[Tuple[str, int]]:
    """Replace bracket group with 'astato', resolve to SMILES,
    remove the At to get the parent fragment + attachment index.

    Returns (parent_smiles, attach_idx_in_parent) or None.
    """
    before = full_name[:node.start]
    after = full_name[node.end + 1:]
    modified = before + "astato" + after
    at_smiles = _name_to_smiles(modified)
    if at_smiles is None:
        return None
    result = _split_at_at(at_smiles)
    if result is None:
        return None
    parent_smi, _, attach_idx = result
    return parent_smi, attach_idx


def get_sub_smiles_from_bracket(node: BracketNode) -> Optional[str]:
    """Try to resolve the bracket content as a standalone chemical name.

    The bracket content is the substituent in -yl form. We try several
    strategies to resolve it to SMILES:
    1. Direct: try the text as-is (works for e.g. "phenyl")
    2. Strip trailing -yl and add -e (e.g. "pyridin-4-yl" → "pyridine")
    """
    text = node.text.strip()
    if not text:
        return None

    # Try as-is (e.g., "phenyl", "morpholino")
    smi = _name_to_smiles(text)
    if smi:
        return smi

    # Try removing trailing "-yl" variants and restoring parent form
    for suffix in ["-yl", "yl"]:
        if text.endswith(suffix):
            stem = text[:-len(suffix)]
            # Try adding 'e' back (pyridin → pyridine)
            for restore in [stem + "e", stem + "ene", stem]:
                smi = _name_to_smiles(restore)
                if smi:
                    return smi

    return None


# ---------------------------------------------------------------------------
# -yl form construction
# ---------------------------------------------------------------------------

# Well-known parent → substituent name mappings
_YL_SPECIALS = {
    "benzene": ["phenyl"],
    "naphthalene": ["naphthyl"],
    "toluene": ["tolyl"],
}


def construct_yl_form(parent_name: str, locant: str) -> List[str]:
    """Construct candidate '-yl' substituent forms from a parent name.

    Returns a list of candidates to try (most likely first).
    ChemDraw round-trip validation will pick the correct one.
    """
    lower = parent_name.lower().strip()

    # Check specials
    if lower in _YL_SPECIALS:
        candidates = list(_YL_SPECIALS[lower])
        # Also add the locant variant if applicable
        if locant:
            for c in list(candidates):
                candidates.append(f"{c.replace('yl', f'-{locant}-yl')}")
        return candidates

    # General rule: drop trailing 'e' (if present), insert locant, add '-yl'
    name = parent_name.strip()
    if name.endswith('e') and not name.endswith('ene'):
        stem = name[:-1]
    else:
        stem = name

    candidates = []
    if locant:
        candidates.append(f"{stem}-{locant}-yl")
        # Also try without locant (some names omit it)
        candidates.append(f"{stem}-yl")
    else:
        candidates.append(f"{stem}-yl")

    return candidates


def get_locant_via_at_probe(fragment_smiles: str,
                            attach_idx: int) -> Optional[str]:
    """Add At at attachment point, name via ChemDraw, extract locant.

    Returns the locant string (e.g., "4") or None.
    """
    mol = Chem.MolFromSmiles(fragment_smiles)
    if mol is None:
        return None

    result = _add_at(mol, attach_idx)
    if result is None:
        return None
    _, at_smi = result

    at_name = _smiles_to_name(at_smi)
    if at_name is None:
        return None

    # Extract locant from "X-astato..." pattern
    m = re.search(r'(\d+)-astato', at_name, re.IGNORECASE)
    if m:
        return m.group(1)

    # Check for "astato" without a numeric locant (position 1 implied)
    if 'astato' in at_name.lower():
        return ""

    return None


# ---------------------------------------------------------------------------
# Prefix substituent detection (for bracketless names)
# ---------------------------------------------------------------------------

def find_prefix_substituents(name: str,
                             verbose: bool = False,
                             skip_single_prefix: bool = False,
                             ) -> List[BracketNode]:
    """Detect non-bracketed substituent prefixes in a name.

    For names like "4-phenylpyridine", bracket parsing finds nothing.
    This function scans for the parent name at the end and identifies
    substituent prefixes before it.

    Strategy: try suffixes of increasing length as potential parent names
    via ChemDraw. The longest valid suffix (that isn't the whole name)
    is the parent; everything before it is substituent prefix(es).

    Returns synthetic BracketNode(s) representing the prefix substituents,
    with positions set so that the At-probe approach works.
    """
    # Skip names that already have bracket groups (handled elsewhere)
    if '(' in name:
        return []

    # Try suffixes from longest to shortest
    # The parent name is at the END of the IUPAC name
    words = name.split()
    # For multi-word names like "benzoic acid", "butanoic acid",
    # work with the last word first, then try multi-word suffixes
    candidates = []

    # Try each position as a split point
    for i in range(1, len(name)):
        suffix = name[i:]
        prefix = name[:i]

        # The suffix should start with a letter (parent name)
        # Also allow "1H-" prefix (hydrogen designation in heterocycles)
        # Also allow locant-prefixed parents like "1,3,4-oxadiazole"
        if not suffix or (not suffix[0].isalpha()
                          and not re.match(r'\d+H-', suffix)
                          and not re.match(r'[\d,]+-[a-zA-Z]', suffix)):
            continue

        # The prefix should end with a substituent-like pattern
        # (ends with a letter, typically 'yl', 'o', 'oxy', etc.)
        if not prefix:
            continue

        # Quick filter: skip if suffix is too short to be a real parent name
        if len(suffix) < 4:
            continue

        # Check if suffix is a valid parent name
        smi = _name_to_smiles(suffix)
        if smi is not None:
            candidates.append((i, suffix, prefix, smi))

    if not candidates:
        return []

    # Find the best candidate: the one where the prefix looks most like
    # a substituent.  Prefer splits where the prefix ends with a common
    # substituent suffix (-yl, -o, -amino, etc.)
    # and the parent name is a real ring/chain system.
    best = None
    for i, suffix, prefix, smi in candidates:
        # Strip leading locant+dash from prefix (numeric or N-locants)
        stripped = re.sub(r'^(?:N(?:,N)*[,-]|\d+[,-])+', '', prefix).rstrip('-')
        if not stripped:
            continue

        # Check if the stripped prefix resolves as a substituent (name)
        # by trying to resolve it.
        # But skip if it contains internal or trailing locants
        # (e.g. "chloro-4-phenyl" or "cyclohexyl-2" — really multi-prefix)
        if re.search(r'.\d+[,-]|[a-z]-\d+$', stripped):
            continue  # multi-prefix, handled in fallback
        sub_smi = _name_to_smiles(stripped)
        if sub_smi is not None:
            if best is None or len(suffix) > len(best[1]):
                best = (i, suffix, prefix, smi, stripped, sub_smi)
            continue

        # Also try common -yl to parent conversions
        if stripped.endswith('yl'):
            for restore_suffix in ['e', 'ene', '']:
                parent_form = stripped.rstrip('yl').rstrip('-') + restore_suffix
                if parent_form:
                    sub_smi = _name_to_smiles(parent_form)
                    if sub_smi is not None:
                        if best is None or len(suffix) > len(best[1]):
                            best = (i, suffix, prefix, smi, stripped, sub_smi)
                        break

    if best is not None and not skip_single_prefix:
        split_pos, suffix, prefix, parent_smi, sub_text, sub_smi = best

        if verbose:
            print(f"  Prefix scan: '{prefix}' + '{suffix}'", file=sys.stderr)
            print(f"    Substituent text: '{sub_text}' -> {sub_smi}",
                  file=sys.stderr)
            print(f"    Parent: '{suffix}' -> {parent_smi}", file=sys.stderr)

        # Create a synthetic BracketNode for the prefix substituent
        # Position it so that replacing name[start:end+1] with "astato"
        # gives a valid At-probe name.
        sub_start = prefix.find(sub_text)
        if sub_start == -1:
            sub_start = 0
        sub_end = sub_start + len(sub_text) - 1

        node = BracketNode(
            text=sub_text,
            start=sub_start,
            end=sub_end,
            depth=0,
            kind="prefix_substituent",
        )
        return [node]

    # Fallback: multi-prefix scan.
    # For "2-chloro-4-phenylquinoline", the whole prefix doesn't resolve
    # as one substituent.  Split on locant boundaries and try each piece.
    # Try candidates sorted by suffix length ascending (shortest parent first
    # = longest prefix = most substituents to decompose).
    sorted_candidates = sorted(candidates, key=lambda c: len(c[1]))

    for _, suffix, prefix, parent_smi in sorted_candidates:
        # Split prefix into individual substituents on locant boundaries
        # e.g. "2-chloro-4-phenyl" → ["2-chloro-", "4-phenyl"]
        parts = re.split(r'(?=(?:N(?:,N)*|\d+)[,-])', prefix)
        parts = [p for p in parts if p]

        if verbose:
            print(f"  Multi-prefix scan: prefix='{prefix}' parent='{suffix}'",
                  file=sys.stderr)
            print(f"    Parts: {parts}", file=sys.stderr)

        nodes = []
        for part in parts:
            # Strip locant prefix
            stripped = re.sub(r'^(?:N(?:,N)*[,-]|\d+[,-])+', '',
                              part).rstrip('-')
            if not stripped or len(stripped) < 3:
                continue

            # Try to resolve as a substituent name
            sub_smi = _name_to_smiles(stripped)
            if sub_smi is None and stripped.endswith('yl'):
                for restore_suffix in ['e', 'ene', '']:
                    parent_form = (stripped.rstrip('yl').rstrip('-')
                                   + restore_suffix)
                    if parent_form:
                        sub_smi = _name_to_smiles(parent_form)
                        if sub_smi is not None:
                            break

            if sub_smi is None:
                continue

            # Find position of substituent text in the full name
            sub_start = name.find(stripped)
            if sub_start == -1:
                continue
            sub_end = sub_start + len(stripped) - 1

            if verbose:
                print(f"    Multi-prefix sub: '{stripped}' -> {sub_smi} "
                      f"(pos {sub_start}-{sub_end})", file=sys.stderr)

            nodes.append(BracketNode(
                text=stripped,
                start=sub_start,
                end=sub_end,
                depth=0,
                kind="prefix_substituent",
            ))

        if nodes:
            return nodes

    # Fallback: multiplied prefix scan.
    # For "2,3-diphenylquinoline": locants=2,3, multiplier=di, sub=phenyl.
    # Construct At-probe for each locant: "3-phenyl-2-astatoquinoline".
    _MULTIPLIER_RE = re.compile(
        r'^([\d,]+)-'                    # locant list: "2,3-"
        r'(di|tri|tetra|penta|hexa)'     # multiplier
        r'(.+)$'                         # base substituent: "phenyl"
    )
    for _, suffix, prefix, parent_smi in sorted_candidates:
        m = _MULTIPLIER_RE.match(prefix)
        if not m:
            continue
        locant_str, multiplier, base_sub = m.groups()
        locants = locant_str.split(',')

        # Verify the base substituent resolves
        sub_smi = _name_to_smiles(base_sub.rstrip('-'))
        if sub_smi is None:
            continue

        if verbose:
            print(f"  Multiplied prefix: locants={locants} "
                  f"mult={multiplier} sub='{base_sub}' "
                  f"parent='{suffix}'", file=sys.stderr)

        # For each locant, create a node whose At-probe replaces ONE
        # instance.  The At-probe name is constructed manually:
        # "locants_minus_one-sub-locant-astato-parent"
        nodes = []
        clean_sub = base_sub.rstrip('-')
        # Ensure suffix starts with dash if it starts with a digit (locants)
        dash_suffix = suffix if suffix[0].isalpha() else f"-{suffix}"
        for loc in locants:
            other_locs = [l for l in locants if l != loc]
            if other_locs:
                # Build: "other_loc-sub-loc-astato-parent"
                other_prefix = ','.join(other_locs) + f'-{clean_sub}'
                probe_name = f"{other_prefix}-{loc}-astato{dash_suffix}"
            else:
                probe_name = f"{loc}-astato{dash_suffix}"

            # Verify the probe resolves
            probe_smi = _name_to_smiles(probe_name)
            if probe_smi is None:
                if verbose:
                    print(f"    Mult At-probe FAIL: '{probe_name}'",
                          file=sys.stderr)
                continue

            if verbose:
                print(f"    Mult At-probe OK: '{probe_name}'",
                      file=sys.stderr)

            # Create a special node that stores the full probe name
            # (can't use simple text replacement for multiplied prefixes)
            node = BracketNode(
                text=base_sub.rstrip('-'),
                start=-1,   # sentinel: not a simple text position
                end=-1,
                depth=0,
                kind="multiplied_prefix",
            )
            # Store probe name + locant in the node text for later use
            node._probe_name = probe_name
            node._locant = loc
            node._parent_suffix = suffix
            nodes.append(node)

        if nodes:
            return nodes

    return []


def _at_probe_for_prefix(full_name: str, node: BracketNode,
                          verbose: bool = False) -> bool:
    """Validate a prefix substituent by replacing it with 'astato'.

    For prefix substituents, we replace the text directly (no parens to remove).
    For multiplied prefixes, the probe name is pre-computed.
    """
    if node.kind == "multiplied_prefix" and hasattr(node, '_probe_name'):
        modified = node._probe_name
    else:
        before = full_name[:node.start]
        after = full_name[node.end + 1:]
        modified = before + "astato" + after
    if verbose:
        print(f"    Prefix At-probe: '{modified}'", file=sys.stderr)
    return _name_to_smiles(modified) is not None


@dataclass
class FragmentResult:
    """Result of splitting a molecule into parent and substituent."""
    parent_smi: str
    parent_mol: Chem.Mol
    parent_attach_idx: int
    sub_smi: str
    sub_mol: Chem.Mol
    sub_attach_idx: int


def _get_fragments_via_at_probe(canonical_smiles: str, at_probe_smiles: str,
                                verbose: bool = False
                                ) -> Optional[FragmentResult]:
    """From the At-probe SMILES, extract parent and substituent fragments.

    The At-probe SMILES has At replacing the substituent.  We:
    1. Find the At atom and its neighbor in the At-probe molecule
    2. Remove At to get parent SMILES + attachment index
    3. Use substructure matching to find which atoms in the full molecule
       belong to the parent, then the rest is the substituent

    Returns FragmentResult with mol objects (preserving atom indices) or None.
    """
    result = _split_at_at(at_probe_smiles)
    if result is None:
        return None
    parent_smi, _, parent_attach_idx = result

    # Match parent in full molecule to find substituent atoms
    full_mol = Chem.MolFromSmiles(canonical_smiles)
    parent_mol = Chem.MolFromSmiles(parent_smi)
    if full_mol is None or parent_mol is None:
        return None

    parent_match = full_mol.GetSubstructMatch(parent_mol)
    if not parent_match:
        return None

    parent_set = set(parent_match)
    sub_atoms = [i for i in range(full_mol.GetNumAtoms()) if i not in parent_set]

    if not sub_atoms:
        return None

    # Find attachment bond: parent atom → sub atom
    sub_attach_full = None
    parent_attach_full = None
    for bond in full_mol.GetBonds():
        a1, a2 = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        if a1 in parent_set and a2 not in parent_set:
            parent_attach_full = a1
            sub_attach_full = a2
            break
        if a2 in parent_set and a1 not in parent_set:
            parent_attach_full = a2
            sub_attach_full = a1
            break

    if sub_attach_full is None:
        return None

    # Extract substituent as a separate molecule
    # Use RWMol: remove the bond, get fragments.
    # Clear aromaticity before bond removal to avoid kekulization issues,
    # then let SanitizeMol recalculate properly for each fragment.
    edit = Chem.RWMol(full_mol)
    Chem.Kekulize(edit, clearAromaticFlags=True)
    edit.RemoveBond(parent_attach_full, sub_attach_full)
    try:
        Chem.SanitizeMol(edit)
    except Exception:
        return None

    frag_atom_lists = Chem.GetMolFrags(edit, asMols=False)
    frag_mols = Chem.GetMolFrags(edit, asMols=True, sanitizeFrags=True)

    # Identify which fragment is the substituent and parent
    sub_frag_idx = None
    parent_frag_idx = None
    for fi, atom_list in enumerate(frag_atom_lists):
        if sub_attach_full in atom_list:
            sub_frag_idx = fi
        if parent_attach_full in atom_list:
            parent_frag_idx = fi

    if sub_frag_idx is None or parent_frag_idx is None:
        return None

    sub_frag_mol = frag_mols[sub_frag_idx]
    parent_frag_mol = frag_mols[parent_frag_idx]
    sub_smi = Chem.MolToSmiles(sub_frag_mol)
    parent_frag_smi = Chem.MolToSmiles(parent_frag_mol)

    # Map attachment atom indices from full molecule to fragment indices
    sub_mapping = {old: new for new, old in enumerate(frag_atom_lists[sub_frag_idx])}
    parent_frag_mapping = {old: new for new, old in enumerate(frag_atom_lists[parent_frag_idx])}
    sub_attach_in_frag = sub_mapping.get(sub_attach_full)
    parent_attach_in_frag = parent_frag_mapping.get(parent_attach_full)

    if sub_attach_in_frag is None or parent_attach_in_frag is None:
        return None

    return FragmentResult(
        parent_smi=parent_frag_smi,
        parent_mol=parent_frag_mol,
        parent_attach_idx=parent_attach_in_frag,
        sub_smi=sub_smi,
        sub_mol=sub_frag_mol,
        sub_attach_idx=sub_attach_in_frag,
    )


def generate_alternative_from_prefix(full_name: str, canonical_smiles: str,
                                      node: BracketNode,
                                      verbose: bool = False,
                                      max_depth: int = 0,
                                      _deadline: Optional[float] = None,
                                      ) -> List[Alternative]:
    """Generate alternatives for a prefix substituent (no brackets).

    Uses the At-probe to identify parent/substituent fragments from the
    molecular graph, avoiding the need to resolve substituent names
    (like "phenyl") which can give radical SMILES.
    """
    alternatives = []

    # Get parent and substituent fragments via At-probe
    if node.kind == "multiplied_prefix" and hasattr(node, '_probe_name'):
        at_name = node._probe_name
    else:
        before = full_name[:node.start]
        after = full_name[node.end + 1:]
        at_name = before + "astato" + after
    at_smi = _name_to_smiles(at_name)
    if at_smi is None:
        if verbose:
            print(f"    Prefix At-probe failed: '{at_name}'", file=sys.stderr)
        return alternatives

    frags = _get_fragments_via_at_probe(canonical_smiles, at_smi,
                                         verbose=verbose)
    if frags is None:
        if verbose:
            print(f"    Fragment extraction failed", file=sys.stderr)
        return alternatives

    return _assemble_alternatives(frags, canonical_smiles, verbose=verbose,
                                   max_depth=max_depth, _deadline=_deadline)


# ---------------------------------------------------------------------------
# Helpers for recursive assembly
# ---------------------------------------------------------------------------

def _parent_name_from_bracket_yl(yl_text: str) -> Optional[str]:
    """Derive a parent name from a bracket-group -yl text.

    E.g., '2-morpholino-4-phenylquinolin-3-yl'
        → strip '-3-yl' → '2-morpholino-4-phenylquinolin'
        → add 'e'       → '2-morpholino-4-phenylquinoline'

    Returns the parent name if it resolves via ChemDraw, else None.
    """
    m = re.search(r'-(\d+)-yl$', yl_text)
    if not m:
        return None
    base = yl_text[:m.start()]
    # Most IUPAC ring names drop a trailing 'e' to form -yl
    # (quinoline → quinolin-yl, pyridine → pyridin-yl)
    for suffix in ('e', ''):
        candidate = base + suffix
        if _name_to_smiles(candidate) is not None:
            return candidate
    return None


def _insert_prefix_by_locant(name: str, locant: str,
                              prefix_text: str) -> str:
    """Insert '{locant}-{prefix_text}-' at the correct numerical position.

    Scans top-level locants (skipping bracketed content) and inserts
    before the first locant that is numerically greater than *locant*.

    >>> _insert_prefix_by_locant('2-morpholino-4-phenylquinoline',
    ...                          '3', '(phenylmethanol-yl)')
    '2-morpholino-3-(phenylmethanol-yl)-4-phenylquinoline'
    """
    target = int(locant)
    depth = 0
    i = 0
    while i < len(name):
        c = name[i]
        if c in '([':
            depth += 1
            i += 1
        elif c in ')]':
            depth -= 1
            i += 1
        elif c.isdigit() and depth == 0:
            j = i
            while j < len(name) and name[j].isdigit():
                j += 1
            if j < len(name) and name[j] == '-':
                num = int(name[i:j])
                if num > target:
                    return (name[:i] + f"{locant}-{prefix_text}-"
                            + name[i:])
            i = j
        else:
            i += 1
    # Fallback: no locant greater than target was found.  The new prefix
    # should go AFTER all existing locant-prefix groups (before the parent
    # stem), not at the very start.
    #
    # If the last prefix is bracketed, we can find its closing bracket and
    # insert right after it.  For unbracketed prefixes we fall back to
    # prepending (may give non-ascending locant order, but ChemDraw's
    # resolver is lenient).
    #
    # Find the last locant-dash at depth 0:
    last_ld_end = None  # position right after the last locant's '-'
    d2 = 0
    k = 0
    while k < len(name):
        ch = name[k]
        if ch in '([':
            d2 += 1; k += 1
        elif ch in ')]':
            d2 -= 1; k += 1
        elif ch.isdigit() and d2 == 0:
            kj = k
            while kj < len(name) and name[kj].isdigit():
                kj += 1
            if kj < len(name) and name[kj] == '-':
                last_ld_end = kj + 1
            k = kj
        else:
            k += 1

    if last_ld_end is not None and last_ld_end < len(name) and name[last_ld_end] == '(':
        # Last prefix is bracketed — find the matching ')'.
        bd = 1
        bp = last_ld_end + 1
        while bp < len(name) and bd > 0:
            if name[bp] in '([':
                bd += 1
            elif name[bp] in ')]':
                bd -= 1
            bp += 1
        # bp is right after the closing bracket.
        # Insert: {existing}-{locant}-{prefix}{rest}
        rest = name[bp:]
        sep = "" if not rest or not rest[0].isdigit() else "-"
        return name[:bp] + f"-{locant}-{prefix_text}{sep}" + rest

    # Ultimate fallback: prepend.  No trailing hyphen when *name* starts
    # with a letter (the parent stem).
    sep = "-" if name and name[0].isdigit() else ""
    return f"{locant}-{prefix_text}{sep}" + name


# ---------------------------------------------------------------------------
# Alternative name generation
# ---------------------------------------------------------------------------

def generate_alternative(full_name: str, canonical_smiles: str,
                         node: BracketNode,
                         verbose: bool = False,
                         max_depth: int = 0,
                         _deadline: Optional[float] = None,
                         ) -> List[Alternative]:
    """Generate alternative names by swapping parent ↔ substituent at one bracket.

    Uses At-probe + molecular graph fragmentation to extract parent/sub
    fragments with correct atom indices.
    """
    # Get At-probe SMILES (replace bracket with astato)
    before = full_name[:node.start]
    after = full_name[node.end + 1:]
    at_name = before + "astato" + after
    at_smi = _name_to_smiles(at_name)
    if at_smi is None:
        if verbose:
            print(f"    At-probe failed: '{at_name}'", file=sys.stderr)
        return []

    # Extract parent and substituent fragments from the molecular graph
    frags = _get_fragments_via_at_probe(canonical_smiles, at_smi,
                                         verbose=verbose)
    if frags is None:
        if verbose:
            print(f"    Fragment extraction failed", file=sys.stderr)
        return []

    return _assemble_alternatives(frags, canonical_smiles, verbose=verbose,
                                   max_depth=max_depth, _deadline=_deadline,
                                   _bracket_yl_text=node.text)


def _assemble_alternatives(frags: FragmentResult, canonical_smiles: str,
                           verbose: bool = False,
                           max_depth: int = 0,
                           _deadline: Optional[float] = None,
                           _bracket_yl_text: str = "",
                           ) -> List[Alternative]:
    """Shared assembly logic for both bracket and prefix substituents.

    Given parent/sub fragments (with correct mol objects and attachment indices),
    construct -yl form of parent, get locant on new parent, assemble via
    replace-hal, and validate.
    """
    alternatives = []

    # Name both fragments
    parent_name = _smiles_to_name(frags.parent_smi)
    sub_parent_name = _smiles_to_name(frags.sub_smi)
    if parent_name is None or sub_parent_name is None:
        if verbose:
            print(f"    Could not name fragments: parent={frags.parent_smi} "
                  f"sub={frags.sub_smi}", file=sys.stderr)
        return alternatives

    # Get locant on current parent
    # Use the mol object directly to preserve atom indices
    parent_locant_result = _add_at(frags.parent_mol, frags.parent_attach_idx)
    parent_locant = None
    if parent_locant_result:
        _, parent_at_smi = parent_locant_result
        parent_at_name = _smiles_to_name(parent_at_smi)
        if parent_at_name:
            m = re.search(r'(\d+)-astato', parent_at_name, re.IGNORECASE)
            if m:
                parent_locant = m.group(1)
            elif 'astato' in parent_at_name.lower():
                parent_locant = ""

    # Construct -yl form candidates for the old parent
    yl_candidates = construct_yl_form(parent_name, parent_locant or "")

    # Se-probe: often gives superior -yl forms (e.g. formyl, acetyl,
    # hydroxy(phenyl)methyl) that construct_yl_form cannot derive.
    se_yl = _get_yl_via_selenyl_probe(
        frags.parent_mol, frags.parent_attach_idx, verbose=verbose)
    if se_yl and se_yl not in yl_candidates:
        yl_candidates.insert(0, se_yl)

    if verbose:
        print(f"    Sub fragment: {frags.sub_smi} → '{sub_parent_name}'",
              file=sys.stderr)
        print(f"    Parent: {frags.parent_smi} → '{parent_name}' "
              f"(locant={parent_locant})", file=sys.stderr)
        print(f"    -yl candidates: {yl_candidates}", file=sys.stderr)

    # Get locant on new parent (the old substituent) using mol object
    # Check if attachment is on a heteroatom (O, N, S) — needs special handling
    # BUT: ring heteroatoms (like N in morpholine) work fine with At-probe,
    # only exocyclic heteroatoms (O in ethers, N in amines) need special path
    sub_attach_atom = frags.sub_mol.GetAtomWithIdx(frags.sub_attach_idx)
    is_heteroatom = (sub_attach_atom.GetAtomicNum() in (7, 8, 16)
                     and not sub_attach_atom.IsInRing())  # exocyclic only

    new_parent_at_name = None
    new_parent_locant = None
    heteroatom_yl_suffix = None  # e.g., "pyridin-4-yloxy"

    if is_heteroatom:
        # Heteroatom pathway: can't add At to O/N/S directly
        het_num = sub_attach_atom.GetAtomicNum()
        if verbose:
            print(f"    Heteroatom attachment: {sub_attach_atom.GetSymbol()} "
                  f"(Z={het_num})", file=sys.stderr)

        # Step A: Get yl+suffix via acid probe through heteroatom
        heteroatom_yl_suffix = _get_yl_suffix_via_acid(
            frags.parent_mol, frags.parent_attach_idx, het_num,
            verbose=verbose)

        # Step B: Get locant by replacing heteroatom with At
        loc_result = _get_locant_replace_heteroatom(
            frags.sub_mol, frags.sub_attach_idx, verbose=verbose)
        if loc_result is not None:
            new_parent_at_name, new_parent_locant = loc_result

        if new_parent_at_name is None or heteroatom_yl_suffix is None:
            if verbose:
                print(f"    Heteroatom pathway failed: at_name={new_parent_at_name} "
                      f"yl_suffix={heteroatom_yl_suffix}", file=sys.stderr)
            return alternatives
    else:
        # Normal pathway: At directly on carbon
        at_result = _add_at(frags.sub_mol, frags.sub_attach_idx)
        if at_result is None:
            if verbose:
                print(f"    At addition to sub failed at "
                      f"{sub_attach_atom.GetSymbol()}"
                      f"(idx={frags.sub_attach_idx})", file=sys.stderr)
            return alternatives
        _, new_parent_at_smi = at_result
        new_parent_at_name = _smiles_to_name(new_parent_at_smi)
        if new_parent_at_name is None:
            if verbose:
                print(f"    ChemScript can't name At-probe: "
                      f"{new_parent_at_smi}", file=sys.stderr)
            return alternatives

        m = re.search(r'(\d+)-astato', new_parent_at_name, re.IGNORECASE)
        if m:
            new_parent_locant = m.group(1)
        elif 'astato' in new_parent_at_name.lower():
            new_parent_locant = ""

    if verbose:
        print(f"    New parent At-probe: '{new_parent_at_name}' "
              f"(locant={new_parent_locant})", file=sys.stderr)
        if heteroatom_yl_suffix:
            print(f"    Heteroatom yl+suffix: '{heteroatom_yl_suffix}'",
                  file=sys.stderr)

    # Assemble alternatives via replace-hal
    # For heteroatom cases, use the acid-derived yl+suffix form instead
    if is_heteroatom and heteroatom_yl_suffix:
        all_yl_forms = [heteroatom_yl_suffix]
    else:
        all_yl_forms = list(yl_candidates)

    for yl_form in all_yl_forms:
        if new_parent_locant:
            # Derive locanted sub-parent from the At-probe name by stripping
            # the astatine prefix.  E.g. "1-astato-4-fluorobenzene" → "4-fluorobenzene".
            # This preserves locant info that the canonical sub_parent_name
            # (e.g. "fluorobenzene") lacks, enabling correct prefix ordering.
            at_prefix = f"{new_parent_locant}-astato"
            if new_parent_at_name.lower().startswith(at_prefix.lower()):
                locanted_parent = new_parent_at_name[len(at_prefix):]
                if locanted_parent.startswith("-"):
                    locanted_parent = locanted_parent[1:]
            else:
                locanted_parent = sub_parent_name
            for strat, assembled in [
                ("replace-hal-noparens",
                 _insert_prefix_by_locant(
                     locanted_parent, new_parent_locant, yl_form)),
                ("replace-hal-parens",
                 _insert_prefix_by_locant(
                     locanted_parent, new_parent_locant,
                     f"({yl_form})")),
            ]:
                valid = _validate_name(assembled, canonical_smiles)
                if verbose:
                    tag = "VALID" if valid else "INVALID"
                    print(f"    Assembled ({strat}): '{assembled}' [{tag}]",
                          file=sys.stderr)
                alternatives.append(Alternative(
                    name=assembled,
                    parent_name=sub_parent_name,
                    sub_name=yl_form,
                    locant=new_parent_locant or "",
                    valid=valid,
                    strategy=strat,
                ))
                if valid:
                    break  # skip more-bracketed variants
            continue

        if "astato" in new_parent_at_name.lower():
            # Try noparens first; skip parens if noparens validates
            for strat, repl in [("replace-hal-noparens", yl_form),
                                 ("replace-hal-parens", f"({yl_form})")]:
                assembled = re.sub(
                    r'\d*-?astato', repl, new_parent_at_name,
                    flags=re.IGNORECASE
                )
                valid = _validate_name(assembled, canonical_smiles)
                if verbose:
                    tag = "VALID" if valid else "INVALID"
                    print(f"    Assembled ({strat}): '{assembled}' [{tag}]",
                          file=sys.stderr)
                alternatives.append(Alternative(
                    name=assembled,
                    parent_name=sub_parent_name,
                    sub_name=yl_form,
                    locant=new_parent_locant or "",
                    valid=valid,
                    strategy=strat,
                ))
                if valid:
                    break  # skip more-bracketed variants

    # Fallback: if no valid alternatives from construct_yl_form, try acid probe
    has_valid = any(a.valid for a in alternatives)
    if not has_valid:
        acid_yl = _get_yl_via_acid_probe(
            frags.parent_mol, frags.parent_attach_idx, verbose=verbose
        )
        if acid_yl and acid_yl not in yl_candidates:
            if verbose:
                print(f"    Acid probe -yl: '{acid_yl}'", file=sys.stderr)
            # Try assembly with acid-probe -yl form
            # Try noparens first; skip parens if noparens validates
            if new_parent_locant:
                pattern = f"{new_parent_locant}-astato"
                if pattern in new_parent_at_name:
                    for strat, assembled in [
                        ("acid-probe-noparens",
                         new_parent_at_name.replace(
                             pattern, f"{new_parent_locant}-{acid_yl}")),
                        ("acid-probe-parens",
                         new_parent_at_name.replace(
                             pattern, f"{new_parent_locant}-({acid_yl})")),
                    ]:
                        valid = _validate_name(assembled, canonical_smiles)
                        if verbose:
                            tag = "VALID" if valid else "INVALID"
                            print(f"    Assembled ({strat}): '{assembled}' "
                                  f"[{tag}]", file=sys.stderr)
                        alternatives.append(Alternative(
                            name=assembled,
                            parent_name=sub_parent_name,
                            sub_name=acid_yl,
                            locant=new_parent_locant or "",
                            valid=valid,
                            strategy=strat,
                        ))
                        if valid:
                            break  # skip more-bracketed variants
            elif "astato" in new_parent_at_name.lower():
                for strat, repl in [("acid-probe-noparens", acid_yl),
                                     ("acid-probe-parens", f"({acid_yl})")]:
                    assembled = re.sub(
                        r'\d*-?astato', repl, new_parent_at_name,
                        flags=re.IGNORECASE
                    )
                    valid = _validate_name(assembled, canonical_smiles)
                    if verbose:
                        tag = "VALID" if valid else "INVALID"
                        print(f"    Assembled ({strat}): '{assembled}' "
                              f"[{tag}]", file=sys.stderr)
                    alternatives.append(Alternative(
                        name=assembled,
                        parent_name=sub_parent_name,
                        sub_name=acid_yl,
                        locant=new_parent_locant or "",
                        valid=valid,
                        strategy=strat,
                    ))
                    if valid:
                        break  # skip more-bracketed variants

    # Recursive decomposition: try alternative parent names for sub-fragment
    # max_depth: -1 = unlimited (until timeout), 0 = disabled, >0 = N levels
    if max_depth != 0 and new_parent_locant:
        if _deadline is not None and time.monotonic() > _deadline:
            if verbose:
                print(f"    Skipping recursive decomposition (timeout)",
                      file=sys.stderr)
        else:
            if verbose:
                print(f"    Recursive decomposition of sub-fragment "
                      f"(max_depth={max_depth})...", file=sys.stderr)
            next_depth = max_depth - 1 if max_depth > 0 else max_depth
            sub_decomp = decompose_name(frags.sub_smi, max_depth=next_depth,
                                        verbose=verbose, _deadline=_deadline)

            # Collect recursive alt parent names (deduplicated)
            recursive_parents = []
            seen_parents = set()
            sub_canon = _canonical(frags.sub_smi)
            for sub_alt in sub_decomp.alternatives:
                if sub_alt.valid and sub_alt.name not in seen_parents:
                    if sub_alt.name != sub_parent_name:
                        seen_parents.add(sub_alt.name)
                        recursive_parents.append(sub_alt.name)

            # Bracket-text shortcut: the bracket content may encode a
            # flat-prefix parent name unreachable by recursive decomp
            # (e.g. "2-morpholino-4-phenylquinolin-3-yl"
            #  → "2-morpholino-4-phenylquinoline")
            if _bracket_yl_text:
                bt_parent = _parent_name_from_bracket_yl(_bracket_yl_text)
                if bt_parent and bt_parent not in seen_parents:
                    bt_smi = _name_to_smiles(bt_parent)
                    if (bt_smi and sub_canon
                            and _canonical(bt_smi) == sub_canon):
                        if verbose:
                            print(f"    Bracket-text parent: '{bt_parent}'",
                                  file=sys.stderr)
                        seen_parents.add(bt_parent)
                        recursive_parents.append(bt_parent)

            for alt_parent in recursive_parents:
                if verbose:
                    print(f"    Recursive alt: '{alt_parent}'",
                          file=sys.stderr)
                for yl_form in all_yl_forms:
                    # Try noparens first; skip more-bracketed if valid
                    for strat, assembled in [
                        ("recursive-noparens",
                         _insert_prefix_by_locant(
                             alt_parent, new_parent_locant,
                             yl_form)),
                        ("recursive-parens",
                         _insert_prefix_by_locant(
                             alt_parent, new_parent_locant,
                             f"({yl_form})")),
                        ("recursive-brackets",
                         _insert_prefix_by_locant(
                             alt_parent, new_parent_locant,
                             f"[{yl_form}]")),
                    ]:
                        valid = _validate_name(assembled, canonical_smiles)
                        if verbose:
                            tag = "VALID" if valid else "INVALID"
                            print(f"    Recursive ({strat}): "
                                  f"'{assembled}' [{tag}]",
                                  file=sys.stderr)
                        alternatives.append(Alternative(
                            name=assembled,
                            parent_name=alt_parent,
                            sub_name=yl_form,
                            locant=new_parent_locant,
                            valid=valid,
                            strategy=strat,
                        ))
                        if valid:
                            break  # skip more-bracketed variants

    # Se-probe reverse assembly: the Se-probe yl of the old parent may
    # encode a suffix→prefix conversion (e.g. "-3-carbaldehyde" becomes
    # "3-formyl-" inside the yl text).  Extract the converted parent name
    # and insert the sub-fragment's prefix form at the attachment locant.
    if se_yl and max_depth != 0:
        yl_text = se_yl.strip('()[]')
        se_parent = _parent_name_from_bracket_yl(yl_text)
        if (se_parent and se_parent != sub_parent_name
                and se_parent != parent_name):
            # Verify the extracted parent resolves to the same molecule
            se_parent_smi = _name_to_smiles(se_parent)
            parent_canon = _canonical(frags.parent_smi)
            if (se_parent_smi and parent_canon
                    and _canonical(se_parent_smi) == parent_canon):
                # Get the attachment locant from the yl text
                m_loc = re.search(r'-(\d+)-yl$', yl_text)
                if m_loc:
                    se_locant = m_loc.group(1)
                    # Compute sub-fragment prefix/yl forms
                    sub_yl_candidates = construct_yl_form(
                        sub_parent_name, new_parent_locant or "")
                    sub_se_yl = _get_yl_via_selenyl_probe(
                        frags.sub_mol, frags.sub_attach_idx,
                        verbose=verbose)
                    if sub_se_yl and sub_se_yl not in sub_yl_candidates:
                        sub_yl_candidates.insert(0, sub_se_yl)

                    if verbose:
                        print(f"    Se-reverse parent: '{se_parent}' "
                              f"(locant={se_locant})",
                              file=sys.stderr)
                        print(f"    Sub-fragment yl candidates: "
                              f"{sub_yl_candidates}", file=sys.stderr)

                    for sub_yl in sub_yl_candidates:
                        # Try noparens first; skip parens if valid
                        for strat, assembled in [
                            ("se-reverse-noparens",
                             _insert_prefix_by_locant(
                                 se_parent, se_locant, sub_yl)),
                            ("se-reverse-parens",
                             _insert_prefix_by_locant(
                                 se_parent, se_locant,
                                 f"({sub_yl})")),
                        ]:
                            valid = _validate_name(
                                assembled, canonical_smiles)
                            if verbose:
                                tag = "VALID" if valid else "INVALID"
                                print(f"    Se-reverse ({strat}): "
                                      f"'{assembled}' [{tag}]",
                                      file=sys.stderr)
                            alternatives.append(Alternative(
                                name=assembled,
                                parent_name=se_parent,
                                sub_name=sub_yl,
                                locant=se_locant,
                                valid=valid,
                                strategy=strat,
                            ))
                            if valid:
                                break  # skip more-bracketed variants

    return alternatives


def _validate_name(name: str, expected_canonical: str) -> bool:
    """Round-trip validate: name → SMILES → canonical, compare."""
    smi = _name_to_smiles(name)
    if smi is None:
        return False
    canon = _canonical(smi)
    if canon is None:
        return False
    return canon == expected_canonical


# ---------------------------------------------------------------------------
# Suffix → prefix conversion
# ---------------------------------------------------------------------------

# (suffix, prefix_form, terminal_e_elided_before_suffix)
# Longest suffix first to avoid partial matches.
_SUFFIX_PREFIX_MAP = [
    # Longest suffix first to avoid partial matches.
    ("carboxylic acid", "carboxy", False),
    ("sulfonic acid", "sulfo", False),
    ("sulfonamide", "sulfamoyl", False),
    ("carbonitrile", "cyano", False),
    ("carbaldehyde", "formyl", False),
    ("carboxamide", "carbamoyl", False),
    ("amine", "amino", True),
    ("ol", "hydroxy", True),
    ("one", "oxo", True),
    ("thiol", "sulfanyl", False),
]


def _suffix_to_prefix_alternatives(canonical_name: str,
                                    canonical_smiles: str,
                                    verbose: bool = False,
                                    ) -> List[Alternative]:
    """Convert IUPAC suffix to prefix form.

    E.g. pyridin-4-amine → 4-aminopyridine,
         cyclohexan-1-ol → 1-hydroxycyclohexane.

    Only handles single-locant suffixes (not multiplied like 1,4-diamine).
    """
    alternatives: List[Alternative] = []

    for suffix, prefix, e_elided in _SUFFIX_PREFIX_MAP:
        if not canonical_name.endswith(suffix):
            continue

        before = canonical_name[:-len(suffix)]
        # Expect: {stem}-{locant(s)}-
        m = re.match(r'^(.+)-(\d+(?:,\d+)*)-$', before)
        if not m:
            continue

        stem = m.group(1)
        locants_str = m.group(2)

        # Skip multiplied locants for now (e.g. benzene-1,4-diamine)
        if ',' in locants_str:
            continue

        # Restore terminal 'e' if elided before vowel-starting suffix
        parent = stem + 'e' if e_elided else stem

        # Assemble prefix form via locant-ordered insertion
        assembled = _insert_prefix_by_locant(parent, locants_str, prefix)

        valid = _validate_name(assembled, canonical_smiles)
        if verbose:
            tag = "VALID" if valid else "INVALID"
            print(f"    Suffix→prefix ({suffix}→{prefix}): "
                  f"'{assembled}' [{tag}]", file=sys.stderr)

        alternatives.append(Alternative(
            name=assembled,
            parent_name=parent,
            sub_name=prefix,
            locant=locants_str,
            valid=valid,
            strategy="suffix-to-prefix",
        ))

        # Only one principal characteristic group per name
        break

    return alternatives


def _deduplicate_alternatives(alternatives: List[Alternative],
                               verbose: bool = False) -> List[Alternative]:
    """Remove redundant alternatives: bracket-only variants and
    single-position synonym variants.

    **Step 1 — bracket-stripped dedup.**  Group validated names by their
    bracket-stripped form (all ``()``, ``[]`` removed).  Within each group
    keep only the name with the fewest bracket characters (ties broken by
    shortest total length).

    **Step 2 — single-segment synonym collapse.**  For any two surviving
    names that differ at exactly one contiguous segment where one segment
    has outer brackets and the other does not, discard the bracketed
    variant.  Since both names round-trip to the same canonical SMILES,
    the segments must be synonymous (e.g. ``morpholino`` vs
    ``(morpholin-4-yl)``).
    """
    valid = [a for a in alternatives if a.valid]
    invalid = [a for a in alternatives if not a.valid]

    if len(valid) <= 1:
        return alternatives

    # --- Step 1: bracket-stripped dedup ---
    def _strip_brackets(name: str) -> str:
        return name.replace('(', '').replace(')', '').replace('[', '').replace(']', '')

    def _bracket_count(name: str) -> int:
        return sum(1 for c in name if c in '()[]')

    groups: dict = {}
    for alt in valid:
        key = _strip_brackets(alt.name)
        groups.setdefault(key, []).append(alt)

    step1: List[Alternative] = []
    for group in groups.values():
        best = min(group, key=lambda a: (_bracket_count(a.name), len(a.name)))
        step1.append(best)
        if verbose and len(group) > 1:
            removed = [a.name for a in group if a is not best]
            print(f"  Dedup (bracket-strip): kept '{best.name}', "
                  f"removed {removed}", file=sys.stderr)

    # --- Step 2: single-segment synonym collapse ---
    # Sort shortest-first so shorter names are preferred as "keepers".
    step1.sort(key=lambda a: (len(a.name), a.name))

    to_remove: set = set()
    for i in range(len(step1)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(step1)):
            if j in to_remove:
                continue
            name_i = step1[i].name
            name_j = step1[j].name

            # Find longest common prefix
            pfx = 0
            for k in range(min(len(name_i), len(name_j))):
                if name_i[k] == name_j[k]:
                    pfx = k + 1
                else:
                    break

            # Find longest common suffix (not overlapping with prefix)
            sfx = 0
            max_sfx = min(len(name_i), len(name_j)) - pfx
            for k in range(1, max_sfx + 1):
                if name_i[-k] == name_j[-k]:
                    sfx = k
                else:
                    break

            end_i = len(name_i) - sfx if sfx else len(name_i)
            end_j = len(name_j) - sfx if sfx else len(name_j)
            mid_i = name_i[pfx:end_i]
            mid_j = name_j[pfx:end_j]

            if not mid_i or not mid_j:
                continue

            # Check: does exactly one segment have outer brackets?
            def _has_outer_brackets(s: str) -> bool:
                return (len(s) >= 2
                        and ((s[0] == '(' and s[-1] == ')')
                             or (s[0] == '[' and s[-1] == ']')))

            i_outer = _has_outer_brackets(mid_i)
            j_outer = _has_outer_brackets(mid_j)

            if i_outer != j_outer:
                # One has outer brackets, one doesn't.
                # Only collapse if the inner text shares a common stem
                # (≥ 4 chars) with the non-bracketed form — this avoids
                # collapsing genuinely different yl-forms (e.g.
                # "hydroxy(phenyl)methyl" vs "phenylmethanol-yl").
                if i_outer:
                    inner = mid_i[1:-1]
                    other = mid_j
                else:
                    inner = mid_j[1:-1]
                    other = mid_i

                common_prefix_len = 0
                for k in range(min(len(inner), len(other))):
                    if inner[k] == other[k]:
                        common_prefix_len = k + 1
                    else:
                        break

                if common_prefix_len >= 4:
                    if i_outer:
                        to_remove.add(i)
                        if verbose:
                            print(f"  Dedup (synonym): removed '{name_i}' "
                                  f"(kept shorter '{name_j}')",
                                  file=sys.stderr)
                        break  # i is removed, skip remaining j
                    else:
                        to_remove.add(j)
                        if verbose:
                            print(f"  Dedup (synonym): removed '{name_j}' "
                                  f"(kept shorter '{name_i}')",
                                  file=sys.stderr)

    step2 = [alt for idx, alt in enumerate(step1) if idx not in to_remove]

    return step2 + invalid


# ---------------------------------------------------------------------------
# Space-separated yl-group alternatives
# ---------------------------------------------------------------------------

# Ring stems that appear in "ring-N-yl" patterns (e.g. pyridin-4-yl)
_YL_RING_STEMS = [
    "quinolin", "isoquinolin", "quinoxalin", "quinazolin",
    "pyridin", "pyrimidin", "pyrazin", "pyridazin",
    "morpholin", "piperidin", "piperazin", "pyrrolidin",
    "indol", "benzimidazol", "benzothiazol", "benzofuran", "benzoxazol",
    "naphthal", "acridin", "carbazol", "phenanthrol",
    "thien", "furan", "pyrrol", "imidazol", "oxazol", "thiazol",
    "triazin", "tetrazol", "triazol", "oxadiazol",
    "phenyl",  # for phenylbenzoate etc.
]


def _space_sep_yl_alternatives(
    canonical_name: str,
    canonical_smiles: str,
    verbose: bool = False,
    max_depth: int = 0,
    _deadline: Optional[float] = None,
) -> List[Alternative]:
    """Generate alternatives for space-separated names with embedded yl-groups.

    Handles names like "tert-butyl pyridin-4-ylcarbamate" where a ring-yl
    pattern is fused into the name without brackets.  Creates a synthetic
    BracketNode and delegates to the standard generate_alternative() path.

    Produces alternatives like "4-((tert-butoxycarbonyl)amino)pyridine"
    where the ring becomes the parent.
    """
    if ' ' not in canonical_name:
        return []

    alternatives: List[Alternative] = []

    # Build regex matching ring-N-yl patterns
    stem_pattern = '|'.join(re.escape(s) for s in
                            sorted(_YL_RING_STEMS, key=len, reverse=True))
    # Match ring stem + optional fused annotation + locant + yl
    # E.g.: pyridin-4-yl, quinolin-7-yl, thieno[2,3-d]pyrimidin-4-yl
    yl_re = re.compile(
        r'((?:' + stem_pattern + r')'
        r'(?:\[[^\]]+\])?'      # optional fused ring annotation [2,3-d]
        r'(?:[a-z]*)'           # optional stem continuation (e.g. "oline" in morpholine)
        r'(?:-\d+(?:,\d+)*)?'  # optional locant(s)
        r'-yl)',
        re.IGNORECASE,
    )

    for m in yl_re.finditer(canonical_name):
        yl_text = m.group(1)   # e.g. "pyridin-4-yl"
        yl_start = m.start()
        yl_end = m.end() - 1   # inclusive

        # The yl-group should appear after a space (space-separated name)
        # and be followed by more text (the functional group suffix)
        if yl_start == 0:
            continue
        # Check there's a space somewhere before this yl-group
        before_text = canonical_name[:yl_start]
        if ' ' not in before_text:
            continue
        # Check there's a suffix after the yl-group (not end-of-name)
        after_text = canonical_name[yl_end + 1:]
        if not after_text or after_text.startswith(' '):
            continue  # yl at end of name or before space — not embedded

        if verbose:
            print(f"  Space-sep yl: '{yl_text}' in '{canonical_name}'",
                  file=sys.stderr)
            print(f"    before='{before_text}' after='{after_text}'",
                  file=sys.stderr)

        # Create synthetic BracketNode
        # The At-probe: replace yl-text with "astato"
        node = BracketNode(
            text=yl_text,
            start=yl_start,
            end=yl_end,
            depth=0,
            kind="candidate",
        )

        # Try At-probe (replace yl-text with "astato")
        at_name = canonical_name[:yl_start] + "astato" + canonical_name[yl_end + 1:]
        if verbose:
            print(f"    At-probe name: '{at_name}'", file=sys.stderr)

        at_smi = _name_to_smiles(at_name)
        if at_smi is None:
            if verbose:
                print(f"    At-probe failed", file=sys.stderr)
            continue

        # Extract fragments
        frags = _get_fragments_via_at_probe(canonical_smiles, at_smi,
                                             verbose=verbose)
        if frags is None:
            if verbose:
                print(f"    Fragment extraction failed", file=sys.stderr)
            continue

        # Assemble alternatives
        alts = _assemble_alternatives(
            frags, canonical_smiles, verbose=verbose,
            max_depth=max_depth, _deadline=_deadline,
            _bracket_yl_text=yl_text,
        )
        alternatives.extend(alts)

        if verbose:
            print(f"    Generated {len(alts)} alternatives from space-sep yl",
                  file=sys.stderr)

    return alternatives


# ---------------------------------------------------------------------------
# Main decomposition
# ---------------------------------------------------------------------------

def decompose_name(smiles: str, max_depth: int = -1,
                   verbose: bool = False,
                   timeout: Optional[float] = 30.0,
                   _deadline: Optional[float] = None,
                   ) -> DecompositionResult:
    """Main entry point: decompose an IUPAC name into alternatives.

    1. Get canonical name from ChemDraw
    2. Parse bracket tree
    3. Classify bracket groups
    4. For each substituent group, generate alternative names

    Args:
        max_depth: Recursion depth limit.  ``-1`` (default) = unlimited
            (recurse until timeout or convergence).  ``0`` = no recursion.
            Positive integer = that many levels.
        timeout: Wall-clock seconds before recursive decomposition is
            skipped.  Set to ``None`` to disable.  Only used on the
            outermost call; recursive calls inherit the computed deadline
            via ``_deadline``.
    """
    # Compute deadline on the outermost call; inner calls inherit it.
    if _deadline is None and timeout is not None:
        _deadline = time.monotonic() + timeout
    canon_smi = _canonical(smiles)
    if canon_smi is None:
        return DecompositionResult(
            original_smiles=smiles, canonical_smiles="",
            canonical_name="", bracket_tree=None,
            errors=["Invalid SMILES"]
        )

    canonical_name = _smiles_to_name(smiles)
    if canonical_name is None:
        return DecompositionResult(
            original_smiles=smiles, canonical_smiles=canon_smi,
            canonical_name="", bracket_tree=None,
            errors=["ChemDraw could not name this structure"]
        )

    if verbose:
        print(f"\nCanonical name: {canonical_name}", file=sys.stderr)

    tree = parse_bracket_tree(canonical_name)

    if verbose:
        print(f"Top-level bracket groups: {len(tree.children)}",
              file=sys.stderr)
        for i, child in enumerate(tree.children):
            print(f"  [{i}] depth={child.depth} "
                  f"pos={child.start}-{child.end} "
                  f"text='{child.text}'", file=sys.stderr)

    result = DecompositionResult(
        original_smiles=smiles,
        canonical_smiles=canon_smi,
        canonical_name=canonical_name,
        bracket_tree=tree,
    )

    # Collect ALL bracket nodes at all depths (breadth-first)
    def _collect_nodes(node):
        nodes = []
        for child in node.children:
            nodes.append(child)
            nodes.extend(_collect_nodes(child))
        return nodes

    all_nodes = _collect_nodes(tree)
    if verbose:
        print(f"Total bracket nodes (all depths): {len(all_nodes)}",
              file=sys.stderr)

    # Process all bracket groups at all depths
    for node in all_nodes:
        kind = classify_node(node)
        node.kind = kind
        if verbose:
            print(f"\n  Bracket '({node.text})' depth={node.depth} → {kind}",
                  file=sys.stderr)

        if kind != "candidate":
            continue

        # Validate as substituent via At-probe
        if not validate_as_substituent(canonical_name, node,
                                        verbose=verbose):
            node.kind = "invalid_sub"
            if verbose:
                print(f"    At-probe validation failed", file=sys.stderr)
            continue

        node.kind = "substituent"

        # Generate alternatives
        alts = generate_alternative(
            canonical_name, canon_smi, node, verbose=verbose,
            max_depth=max_depth, _deadline=_deadline,
        )
        result.alternatives.extend(alts)

    # Fallback: if no bracket groups found substituents, try prefix scanning
    if not result.alternatives:
        prefix_nodes = find_prefix_substituents(
            canonical_name, verbose=verbose
        )
        for pnode in prefix_nodes:
            if _at_probe_for_prefix(canonical_name, pnode, verbose=verbose):
                if pnode.kind not in ("multiplied_prefix",):
                    pnode.kind = "prefix_substituent"
                alts = generate_alternative_from_prefix(
                    canonical_name, canon_smi, pnode, verbose=verbose,
                    max_depth=max_depth, _deadline=_deadline,
                )
                result.alternatives.extend(alts)

        # Retry: if single-prefix nodes produced no valid alternatives,
        # try again with multi-prefix fallback (skip_single_prefix=True).
        # This handles cases like "2-chloro-4-phenylquinoline" where "chloro"
        # is found first as a single-prefix but can't produce useful alts.
        valid_alts = [a for a in result.alternatives if a.valid]
        if not valid_alts and prefix_nodes:
            if verbose:
                print("  Retrying with multi-prefix fallback...",
                      file=sys.stderr)
            prefix_nodes2 = find_prefix_substituents(
                canonical_name, verbose=verbose,
                skip_single_prefix=True
            )
            for pnode in prefix_nodes2:
                if _at_probe_for_prefix(canonical_name, pnode,
                                         verbose=verbose):
                    if pnode.kind not in ("multiplied_prefix",):
                        pnode.kind = "prefix_substituent"
                    alts = generate_alternative_from_prefix(
                        canonical_name, canon_smi, pnode, verbose=verbose,
                        max_depth=max_depth, _deadline=_deadline,
                    )
                    result.alternatives.extend(alts)

    # Suffix→prefix conversion (e.g. pyridin-4-amine → 4-aminopyridine)
    suffix_alts = _suffix_to_prefix_alternatives(
        canonical_name, canon_smi, verbose=verbose)
    result.alternatives.extend(suffix_alts)

    # Space-separated names with embedded yl-groups
    # (e.g. "tert-butyl pyridin-4-ylcarbamate" — no brackets, no prefix match)
    if ' ' in canonical_name:
        yl_alts = _space_sep_yl_alternatives(
            canonical_name, canon_smi, verbose=verbose,
            max_depth=max_depth, _deadline=_deadline,
        )
        result.alternatives.extend(yl_alts)

    # Deduplicate alternatives:
    # 1. Remove exact-name duplicates and names identical to canonical
    seen: set = {canonical_name}  # canonical is already listed separately
    unique: list = []
    for alt in result.alternatives:
        if alt.name not in seen:
            seen.add(alt.name)
            unique.append(alt)
    # 2. Remove bracket-only variants and single-position synonyms
    result.alternatives = _deduplicate_alternatives(unique, verbose=verbose)

    # Infer canonical parent: for the canonical name, the parent is the
    # fragment that remains when the first substituent is removed.
    # We can extract this from the At-probe of the first substituent node.
    if result.alternatives:
        # The first alternative's parent_name is the OLD substituent that
        # became new parent — so the OLD parent is what the canonical name
        # uses.  We can extract it from the At-probe: replace substituent
        # with At, resolve, remove At → parent fragment → name it.
        for alt in result.alternatives:
            if alt.valid:
                # The sub_name (in -yl form) tells us what the canonical
                # parent is.  But it's simpler to just check the At-probe.
                # For now, use a heuristic: look for the longest suffix of
                # canonical_name that resolves as a valid compound.
                break

    # Try to determine canonical parent from prefix scan or bracket analysis
    if not result.canonical_parent:
        # For bracket names: parent is name minus bracket group text
        # For prefix names: parent is the suffix
        # Simplest heuristic: try removing first valid bracket group
        for node in all_nodes:
            if node.kind == "substituent":
                # At-probe: replace bracket with At → SMILES → remove At → name
                before = canonical_name[:node.start]
                after = canonical_name[node.end + 1:]
                probe = before + "astato" + after
                at_smi = _name_to_smiles(probe)
                if at_smi:
                    split = _split_at_at(at_smi)
                    if split:
                        parent_smi, _, _ = split
                        parent_name = _smiles_to_name(parent_smi)
                        if parent_name:
                            result.canonical_parent = parent_name
                            break

    # Fallback: try the prefix scan parent
    if not result.canonical_parent and '(' not in canonical_name:
        for i in range(len(canonical_name) - 4, 0, -1):
            suffix = canonical_name[i:]
            if suffix[0].isalpha():
                smi = _name_to_smiles(suffix)
                if smi:
                    result.canonical_parent = suffix
                    break

    return result


# ---------------------------------------------------------------------------
# R-group / placeholder handling
# ---------------------------------------------------------------------------

# Two probe sets for dual-probe consensus.  We run the decomposition with
# each set, replace probe names with R-labels, and only keep names that
# agree across both runs.  This cleanly handles molecules that contain
# real halogens — if probe A collides with a real halogen, probe B won't,
# and the intersection filters out the bad names.
#
# Each entry: (atomic_number, IUPAC_prefix, IUPAC_stem)
_PROBE_SET_A = [
    (9,  'fluoro',  'fluor'),   # F  — first label
    (17, 'chloro',  'chlor'),   # Cl — second label (multi-R-group)
]
_PROBE_SET_B = [
    (53, 'iodo',    'iod'),     # I  — first label
    (35, 'bromo',   'brom'),    # Br — second label (multi-R-group)
]


def _replace_probe_in_name(name: str, label: str,
                           probe_prefix: str = 'bromo',
                           probe_stem: str = 'brom') -> str:
    """Replace probe-atom name fragments with the R-group label.

    Tries several patterns; replaces only the FIRST match to avoid
    clobbering legitimate atoms in the rest of the molecule.
    """
    # Try exact prefix replacement first (most common case)
    # e.g. "4-fluoropyridine" -> '4-"R"-pyridine'
    m = re.search(r'(\d+-)?' + re.escape(probe_prefix), name, re.IGNORECASE)
    if m:
        locant = m.group(1) or ""
        after = name[m.end():]
        # Add dash before suffix if it starts with a letter
        sep = "-" if after and after[0].isalpha() else ""
        return name[:m.start()] + locant + '"' + label + '"' + sep + after

    # Bracket form: "(fluoro)" -> '("R")'
    pat_bracket = re.compile(r'\(' + re.escape(probe_prefix) + r'\)',
                             re.IGNORECASE)
    m = pat_bracket.search(name)
    if m:
        return name[:m.start()] + '("' + label + '")' + name[m.end():]

    # Any remaining probe stem substring
    pat_stem = re.compile(re.escape(probe_stem) + r'\w*', re.IGNORECASE)
    m = pat_stem.search(name)
    if m:
        after = name[m.end():]
        sep = "-" if after and after[0].isalpha() else ""
        return name[:m.start()] + '"' + label + '"' + sep + after

    return name


@dataclass
class RGroupMapping:
    """Tracks an R-group label and its position in the molecule."""
    label: str          # Text label: "R", "R1", "X", "Ar", etc.
    atom_idx: int       # Atom index in the original SMILES (dummy atom)
    probe_atom_idx: int # Atom index in the probed SMILES (halogen atom)


def _build_label_map(dummy_indices: List[int],
                     labels) -> dict:
    """Build {atom_idx: label_str} from various label formats."""
    if labels is None:
        if len(dummy_indices) == 1:
            return {dummy_indices[0]: "R"}
        else:
            return {idx: f"R{i}" for i, idx in enumerate(dummy_indices, 1)}
    elif isinstance(labels, (list, tuple)):
        label_map = {}
        for i, idx in enumerate(dummy_indices):
            label_map[idx] = labels[i] if i < len(labels) else f"R{i+1}"
        return label_map
    else:
        return dict(labels)


def prepare_rgroup_smiles(smiles: str,
                          labels=None,
                          probe_set=None,
                          label_probe_map=None,
                          ) -> Tuple[Optional[str], List[RGroupMapping]]:
    """Replace dummy atoms (*) with halogen probe atoms.

    Args:
        smiles: SMILES string, possibly containing [*] dummy atoms.
        labels: Optional. Can be:
                - dict mapping atom index -> label string
                - list of label strings (matched to dummy atoms in order)
                - None: auto-generate as R, R1, R2...
        probe_set: List of (atomic_num, prefix, stem) tuples.
                   Defaults to _PROBE_SET_A.  Ignored if label_probe_map
                   is provided.
        label_probe_map: Explicit {label: (atomic_num, prefix, stem)} dict.
                         Overrides probe_set if given.

    Returns:
        (probed_smiles, mappings) where probed_smiles has halogens
        instead of *, and mappings tracks which atoms were replaced.
        Returns (None, []) if no dummy atoms found or on error.
    """
    if probe_set is None and label_probe_map is None:
        probe_set = _PROBE_SET_A

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, []

    # Find dummy atoms (atomic number 0)
    dummy_indices = []
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0:
            dummy_indices.append(atom.GetIdx())

    if not dummy_indices:
        return None, []  # No R-groups

    label_map = _build_label_map(dummy_indices, labels)

    # Build label → probe assignment
    if label_probe_map:
        label_to_probe = {}
        for idx in dummy_indices:
            label = label_map.get(idx, f"R{idx}")
            if label in label_probe_map:
                label_to_probe[label] = label_probe_map[label]
            elif probe_set:
                label_to_probe[label] = probe_set[0]
            else:
                label_to_probe[label] = _PROBE_SET_A[0]
    else:
        label_to_probe = {}
        probe_idx = 0
        for idx in dummy_indices:
            label = label_map.get(idx, f"R{idx}")
            if label not in label_to_probe:
                if probe_idx < len(probe_set):
                    label_to_probe[label] = probe_set[probe_idx]
                    probe_idx += 1
                else:
                    label_to_probe[label] = probe_set[0]

    # Replace dummy atoms with their assigned probe atom
    edit = Chem.RWMol(mol)
    mappings = []
    for idx in dummy_indices:
        atom = edit.GetAtomWithIdx(idx)
        label = label_map.get(idx, f"R{idx}")
        probe_z, _prefix, _stem = label_to_probe[label]
        atom.SetAtomicNum(probe_z)
        atom.SetFormalCharge(0)
        atom.SetNoImplicit(False)
        mappings.append(RGroupMapping(
            label=label, atom_idx=idx, probe_atom_idx=idx
        ))

    try:
        Chem.SanitizeMol(edit)
        probed_smi = Chem.MolToSmiles(edit)
        return probed_smi, mappings
    except Exception:
        return None, []


def _probe_label_mapping(mappings: List[RGroupMapping],
                         probe_set: list) -> dict:
    """Build {label: (prefix, stem)} from mappings and probe_set."""
    result = {}
    probe_idx = 0
    for m in mappings:
        if m.label not in result:
            if probe_idx < len(probe_set):
                _z, prefix, stem = probe_set[probe_idx]
                result[m.label] = (prefix, stem)
                probe_idx += 1
            else:
                _z, prefix, stem = probe_set[0]
                result[m.label] = (prefix, stem)
    return result


def _replace_all_probes(name: str, label_to_probe: dict) -> str:
    """Replace all probe-atom names in a string with R-group labels."""
    result = name
    for label, (prefix, stem) in label_to_probe.items():
        result = _replace_probe_in_name(result, label,
                                        probe_prefix=prefix,
                                        probe_stem=stem)
    return result


def decompose_name_with_rgroups(smiles: str,
                                 labels=None,
                                 verbose: bool = False
                                 ) -> DecompositionResult:
    """Decompose a molecule with R-group placeholders using dual-probe consensus.

    Strategy: run decomposition twice with different probe halogen sets
    (A: F/Cl, B: I/Br), replace probe names with R-group labels, and
    INTERSECT — only keep names that both sets agree on.

    The two probe sets are designed with matching alphabetical orderings:
      Set A: fluoro (1st label), chloro (2nd label) → chloro < fluoro
      Set B: iodo   (1st label), bromo  (2nd label) → bromo  < iodo
    This ensures that IUPAC alphabetical prefix ordering is consistent
    between sets, so name strings match after probe→label replacement.

    If the molecule already contains one of the probe halogens, the
    collision is detected via the intersection (colliding set produces
    wrong names) and a single-probe fallback is used.

    If the SMILES has no dummy atoms, falls through to regular decompose_name.

    Args:
        smiles: SMILES string, may contain [*] dummy atoms for R-groups.
        labels: Optional labels for R-groups. Can be:
                - None: auto-generate R, R1, R2...
                - list: ['R', 'X'] matched to dummies in order
                - dict: {atom_idx: label}
        verbose: Print debug info to stderr.
    """
    # Prepare both probe sets
    probed_a, mappings_a = prepare_rgroup_smiles(
        smiles, labels, probe_set=_PROBE_SET_A)
    probed_b, mappings_b = prepare_rgroup_smiles(
        smiles, labels, probe_set=_PROBE_SET_B)

    if probed_a is None:
        # No R-groups found — regular decomposition
        return decompose_name(smiles, verbose=verbose)

    # Build label→(prefix, stem) for each probe set
    ltp_a = _probe_label_mapping(mappings_a, _PROBE_SET_A)
    ltp_b = _probe_label_mapping(mappings_b, _PROBE_SET_B)

    if verbose:
        print(f"  R-group dual-probe consensus:", file=sys.stderr)
        print(f"    Set A ({probed_a}): "
              + ", ".join(f"{l}={p}" for l, (p, _) in ltp_a.items()),
              file=sys.stderr)
        print(f"    Set B ({probed_b}): "
              + ", ".join(f"{l}={p}" for l, (p, _) in ltp_b.items()),
              file=sys.stderr)

    # Run decomposition with each probe set
    result_a = decompose_name(probed_a, verbose=verbose)
    result_b = decompose_name(probed_b, verbose=verbose)

    # Replace probes with labels in canonical names
    canon_a = _replace_all_probes(result_a.canonical_name, ltp_a)
    canon_b = _replace_all_probes(result_b.canonical_name, ltp_b)

    # Determine canonical name: prefer consensus, fall back to non-colliding
    mol = Chem.MolFromSmiles(smiles)
    real_elements = {a.GetAtomicNum() for a in mol.GetAtoms()
                     if a.GetAtomicNum() != 0}
    a_collides = any(z in real_elements for z, _, _ in _PROBE_SET_A)
    b_collides = any(z in real_elements for z, _, _ in _PROBE_SET_B)

    if canon_a == canon_b:
        canonical = canon_a
        if verbose:
            print(f"    Canonical consensus: {canonical}", file=sys.stderr)
    else:
        if a_collides and not b_collides:
            canonical = canon_b
        elif b_collides and not a_collides:
            canonical = canon_a
        else:
            canonical = canon_a  # No collision — names just differ slightly
        if verbose:
            print(f"    Canonical disagree: A={canon_a}, B={canon_b}",
                  file=sys.stderr)
            print(f"    Using: {canonical}", file=sys.stderr)

    # Collect alternatives from each set, keyed by name-after-replacement
    def _alts_by_name(result, ltp):
        by_name = {}
        for alt in result.alternatives:
            if alt.valid:
                replaced = _replace_all_probes(alt.name, ltp)
                if replaced not in by_name:
                    by_name[replaced] = alt
        return by_name

    alts_a = _alts_by_name(result_a, ltp_a)
    alts_b = _alts_by_name(result_b, ltp_b)

    # Intersect: only keep names that both sets agree on
    common_names = set(alts_a.keys()) & set(alts_b.keys())

    if verbose:
        print(f"    Set A alts: {len(alts_a)}, Set B alts: {len(alts_b)}, "
              f"consensus: {len(common_names)}", file=sys.stderr)
        for name in sorted(common_names):
            print(f"      [OK] {name}", file=sys.stderr)
        only_a = set(alts_a.keys()) - common_names
        only_b = set(alts_b.keys()) - common_names
        for name in sorted(only_a):
            print(f"      [A only] {name}", file=sys.stderr)
        for name in sorted(only_b):
            print(f"      [B only] {name}", file=sys.stderr)

    # --- Build final result ---
    canon_smi = Chem.MolToSmiles(mol) if mol else ""
    result = DecompositionResult(
        original_smiles=smiles,
        canonical_smiles=canon_smi,
        canonical_name=canonical,
        canonical_parent=_replace_all_probes(
            result_a.canonical_parent or "", ltp_a) or None,
        bracket_tree=None,
    )

    for name in sorted(common_names):
        alt_a = alts_a[name]
        result.alternatives.append(Alternative(
            name=name,
            parent_name=_replace_all_probes(alt_a.parent_name, ltp_a),
            sub_name=_replace_all_probes(alt_a.sub_name, ltp_a),
            locant=alt_a.locant,
            valid=True,
            strategy=alt_a.strategy,
        ))

    # Fallback: if consensus is empty, use the non-colliding set
    if not common_names:
        if a_collides and not b_collides and alts_b:
            fallback_alts, fallback_ltp = alts_b, ltp_b
        elif b_collides and not a_collides and alts_a:
            fallback_alts, fallback_ltp = alts_a, ltp_a
        elif alts_a:
            fallback_alts, fallback_ltp = alts_a, ltp_a
        else:
            fallback_alts, fallback_ltp = alts_b, ltp_b

        for name, alt in fallback_alts.items():
            result.alternatives.append(Alternative(
                name=name,
                parent_name=_replace_all_probes(alt.parent_name, fallback_ltp),
                sub_name=_replace_all_probes(alt.sub_name, fallback_ltp),
                locant=alt.locant,
                valid=True,
                strategy=alt.strategy + " (single-probe fallback)",
            ))
        if verbose and fallback_alts:
            print(f"    Fallback to single probe: {len(fallback_alts)} alts",
                  file=sys.stderr)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_text(result: DecompositionResult) -> str:
    """Format result as human-readable text."""
    lines = []
    lines.append(f"Input SMILES:    {result.original_smiles}")
    lines.append(f"Canonical SMILES: {result.canonical_smiles}")
    lines.append(f"Canonical name:  {result.canonical_name}")

    if result.errors:
        for e in result.errors:
            lines.append(f"  ERROR: {e}")
        return "\n".join(lines)

    if result.bracket_tree:
        lines.append(f"\nBracket groups ({len(result.bracket_tree.children)}):")
        for child in result.bracket_tree.children:
            lines.append(f"  ({child.text})  [{child.kind}]")

    valid_alts = [a for a in result.alternatives if a.valid]
    invalid_alts = [a for a in result.alternatives if not a.valid]

    lines.append(f"\nAlternatives ({len(valid_alts)} valid, "
                 f"{len(invalid_alts)} invalid):")

    lines.append(f"  1. {result.canonical_name}  [canonical]")
    for i, alt in enumerate(valid_alts, 2):
        lines.append(f"  {i}. {alt.name}  [VALID, parent: {alt.parent_name}]")

    if invalid_alts:
        lines.append(f"\n  Invalid attempts:")
        for alt in invalid_alts:
            lines.append(f"  - {alt.name}  [{alt.strategy}]")

    return "\n".join(lines)


def _format_json(result: DecompositionResult) -> str:
    """Format result as JSON."""
    d = {
        "original_smiles": result.original_smiles,
        "canonical_smiles": result.canonical_smiles,
        "canonical_name": result.canonical_name,
        "errors": result.errors,
        "alternatives": [asdict(a) for a in result.alternatives],
    }
    return json.dumps(d, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Name-driven IUPAC decomposition"
    )
    parser.add_argument("smiles", help="SMILES string to decompose")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print detailed progress to stderr")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--max-depth", type=int, default=-1,
                        help="Maximum recursion depth (default: -1, "
                        "unlimited until timeout). 0 = no recursion.")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="Timeout in seconds (default: 30). "
                             "Use 0 to disable.")
    args = parser.parse_args()

    timeout = args.timeout if args.timeout > 0 else None
    result = decompose_name(args.smiles, max_depth=args.max_depth,
                            verbose=args.verbose, timeout=timeout)

    if args.json:
        print(_format_json(result))
    else:
        print(_format_text(result))


if __name__ == "__main__":
    main()
