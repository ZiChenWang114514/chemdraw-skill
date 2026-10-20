"""
scheme_yaml_writer.py — Generate scheme YAML from reaction_parser JSON.

This is the layout-decision layer between perception (reaction_parser) and
rendering (renderer).  It reads a reaction JSON, decides where each species
goes in the scheme, and writes a YAML file that the renderer can consume.

The three decisions made here:
  1. Structure or text?  (atom-contributing → structure; non-contributing → text)
  2. Position?  (substrate → left; other reactant → above arrow; reagents → below)
  3. Priority ordering of below-arrow text (catalyst > base > solvent > conditions)

Usage:
    python experiments/scheme_dsl/scheme_yaml_writer.py reaction.json -o scheme.yaml

    from scheme_dsl.scheme_yaml_writer import write_scheme_yaml
    yaml_path = write_scheme_yaml("reaction.json", "scheme.yaml")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Role-based priority for below-arrow text ordering
# ---------------------------------------------------------------------------

# Lower number = higher priority (appears first below arrow)
_ROLE_PRIORITY = {
    "catalyst": 10,
    "ligand": 15,
    "base": 20,
    "coupling_reagent": 25,
    "reducing_agent": 30,
    "oxidant": 30,
    "lewis_acid": 30,
    "activating_agent": 30,
    "halogenating_agent": 30,
    "fluorinating_agent": 30,
    "borylating_agent": 30,
    "protecting_group": 35,
    "deprotecting_agent": 35,
    "acid": 35,
    "additive": 40,
    "reductant": 40,
    "reagent": 45,
    "drying_agent": 50,
    "inorganic_salt": 50,
    "solvent": 80,
}

# Roles that should always be shown as text, never as drawn structures
_DEMOTE_ROLES = {
    "base", "catalyst", "ligand", "coupling_reagent", "reducing_agent",
    "oxidant", "protecting_group", "deprotecting_agent", "acid",
    "activating_agent", "lewis_acid", "drying_agent", "halogenating_agent",
    "fluorinating_agent", "borylating_agent", "additive", "reductant",
    "reagent", "solvent", "inorganic_salt",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_scheme_yaml(
    json_path: str,
    output_path: str,
    layout: str = "auto",
    include_run_arrows: bool = True,
    use_eln_labels: bool = False,
) -> str:
    """Read reaction JSON, make layout decisions, write YAML file.

    Parameters
    ----------
    json_path : str
        Path to reaction_parser JSON file.
    output_path : str
        Path where the YAML will be written.
    layout : str
        Layout type: "linear", "sequential", or "auto" (inferred from step count).
    include_run_arrows : bool
        If True and ELN data has SM mass + product yield, include run_arrows.
    use_eln_labels : bool
        If True, label products with ELN experiment names instead of
        sequential numbers.

    Returns
    -------
    str
        The absolute path to the written YAML file.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    species = data.get("species", [])
    eln_data = data.get("eln_data") or {}
    conditions = data.get("conditions", [])

    product_label = None
    if use_eln_labels:
        experiment = data.get("experiment",
                              os.path.splitext(os.path.basename(json_path))[0])
        product_label = experiment

    # Build the YAML dict
    yaml_dict = _build_yaml_dict(species, conditions, eln_data,
                                  layout=layout,
                                  include_run_arrows=include_run_arrows,
                                  product_label=product_label)

    # Write YAML
    _write_yaml_file(yaml_dict, output_path)

    return os.path.abspath(output_path)


def build_scheme_yaml_dict(
    json_path: str,
    layout: str = "auto",
    include_run_arrows: bool = True,
    use_eln_labels: bool = False,
) -> Dict[str, Any]:
    """Read reaction JSON and return the YAML dict (without writing to disk).

    Useful for programmatic access when you want to inspect or modify
    the dict before writing.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    species = data.get("species", [])
    eln_data = data.get("eln_data") or {}
    conditions = data.get("conditions", [])

    product_label = None
    if use_eln_labels:
        experiment = data.get("experiment",
                              os.path.splitext(os.path.basename(json_path))[0])
        product_label = experiment

    return _build_yaml_dict(species, conditions, eln_data,
                            layout=layout,
                            include_run_arrows=include_run_arrows,
                            product_label=product_label)


# ---------------------------------------------------------------------------
# Core layout logic
# ---------------------------------------------------------------------------

def _build_yaml_dict(
    species: List[Dict[str, Any]],
    conditions: List[str],
    eln_data: Dict[str, Any],
    layout: str = "auto",
    include_run_arrows: bool = True,
    product_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the complete YAML dict from reaction data.

    This is where all three layout decisions are made:
      1. Structure or text?  (atom_contributing → draw; else → text)
      2. Position?  (substrate left, other reactant above, reagents below)
      3. Priority ordering of below-arrow text

    Parameters
    ----------
    product_label : str, optional
        When set, only products get this label (ELN mode).
        Substrates and above-arrow structures are unlabelled.
    """
    # --- Classify species into scheme positions ---
    substrates = []        # left of arrow (drawn structures)
    above_structures = []  # above arrow (drawn structures)
    above_text = []        # above arrow (text, e.g. "(1.2 eq)")
    below_text_items = []  # below arrow (text with priority for sorting)
    products = []          # right of arrow (drawn structures)

    # Track species that will be drawn as structures (need StructureRef entries)
    drawn_ids = set()

    for sp in species:
        sp_id = sp.get("id", "")
        role = sp.get("role", "")
        role_detail = (sp.get("role_detail") or "").lower()
        is_sm = sp.get("is_sm", False)
        is_dp = sp.get("is_dp", False)
        is_substrate = sp.get("is_substrate", False)
        is_solvent = sp.get("is_solvent", False)
        atom_contributing = (role == "atom_contributing")
        source = sp.get("source", "")
        # Use raw name for labels (display_text may already have equiv appended)
        name = sp.get("name", "")
        display = sp.get("display_text") or name
        smiles = sp.get("smiles")

        # Check is_dp flag as well as role for product identification
        if role == "product" or is_dp:
            if smiles:
                products.append(sp_id)
                drawn_ids.add(sp_id)

        # Check is_sm/is_substrate flags — but only honor them when the
        # species is atom-contributing or unclassified.  The CSV may mark
        # reagents like n-BuLi as "substrate" even though RXNMapper says
        # they are non-contributing.  Role classification wins.
        elif (is_substrate or is_sm) and (atom_contributing or role in ("", "unclassified")):
            if smiles:
                substrates.append(sp_id)
                drawn_ids.add(sp_id)
            # else: CSV-only SM entry with no structure — skip (the actual
            # structure should be a separate atom_contributing species)

        elif atom_contributing:
            # Atom-contributing species are drawn as structures above arrow
            above_structures.append(sp_id)
            drawn_ids.add(sp_id)
            # Add equiv text below the structure
            equiv = sp.get("csv_equiv")
            if equiv:
                above_text.append(f"({equiv} eq)")

        elif is_solvent:
            # Solvents → below arrow text, low priority
            priority = _ROLE_PRIORITY.get("solvent", 80)
            below_text_items.append((priority, display))

        else:
            # Non-contributing / unclassified species → text below arrow
            # Check if it should be demoted (drawn structure → text)
            should_demote = role_detail in _DEMOTE_ROLES
            has_structure = source in ("fragment", "rxn") and smiles

            if has_structure and not should_demote:
                # Unusual: non-contributing but not a known reagent type.
                # Draw it above the arrow as a structure.
                above_structures.append(sp_id)
                drawn_ids.add(sp_id)
            else:
                # Text label below arrow — use raw name + format equiv here
                priority = _ROLE_PRIORITY.get(role_detail, 50)
                label = _format_label_with_equiv(name, display, sp.get("csv_equiv"))
                if not label:
                    continue
                below_text_items.append((priority, label))

    # If no substrate was identified but there are atom-contributing species
    # above the arrow, promote the most likely one to substrate (left of arrow).
    # Prefer the one with csv_equiv closest to 1.0, else the first one.
    if not substrates and above_structures:
        above_set = set(above_structures)
        best_id = above_structures[0]
        best_diff = float("inf")
        for sp in species:
            sp_id_check = sp.get("id")
            if sp_id_check in above_set:
                eq = sp.get("csv_equiv")
                if eq:
                    try:
                        diff = abs(float(eq) - 1.0)
                        if diff < best_diff:
                            best_diff = diff
                            best_id = sp_id_check
                    except (ValueError, TypeError):
                        pass
        above_structures.remove(best_id)
        substrates.append(best_id)
        # Rebuild above_text from remaining above_structures
        above_text = []
        remaining = set(above_structures)
        for sp in species:
            if sp.get("id") in remaining:
                eq = sp.get("csv_equiv")
                if eq:
                    above_text.append(f"({eq} eq)")

    # Sort below-arrow text by priority
    below_text_items.sort(key=lambda x: x[0])
    below_text = [item[1] for item in below_text_items]

    # Add conditions (temperature, time, atmosphere) at end
    if conditions:
        below_text.extend(_normalize_conditions(conditions))

    # --- Build structures dict ---
    # Assign compound labels to substrates and products.
    # Above-arrow structures (reagents) don't get numbered.
    # When product_label is set (ELN mode), only products get labels.
    label_map: Dict[str, str] = {}
    if product_label is not None:
        # ELN mode: only products get the provided label
        for sid in products:
            label_map[sid] = product_label
    else:
        # Default mode: sequential numbers 1, 2, 3, ...
        label_order: List[str] = []
        for sid in substrates:
            if sid not in label_order:
                label_order.append(sid)
        for sid in products:
            if sid not in label_order:
                label_order.append(sid)
        label_counter = 1
        for sid in label_order:
            label_map[sid] = str(label_counter)
            label_counter += 1

    structures = {}
    for sp in species:
        sp_id = sp.get("id", "")
        if sp_id not in drawn_ids:
            continue
        smiles = sp.get("smiles")
        if not smiles:
            continue
        entry: Dict[str, Any] = {"smiles": smiles}
        # Compound number label below structure (substrates + products only)
        if sp_id in label_map:
            entry["label"] = label_map[sp_id]
        structures[sp_id] = entry

    # --- Build step ---
    step: Dict[str, Any] = {}
    if substrates:
        step["substrates"] = substrates
    if products:
        step["products"] = products

    above: Dict[str, Any] = {}
    if above_structures:
        above["structures"] = above_structures
    if above_text:
        above["text"] = above_text
    if above:
        step["above_arrow"] = above

    if below_text:
        step["below_arrow"] = {"text": below_text}

    # --- Determine layout ---
    if layout == "auto":
        layout = "linear"  # single step for now; multi-step will be "sequential"

    # --- Build top-level YAML dict ---
    yaml_dict: Dict[str, Any] = {
        "structures": structures,
        "steps": [step],
        "layout": layout,
    }

    # --- Run arrows ---
    # Run arrows already display yield in their output label, so only add
    # yield_ to the step when run arrows are NOT present (avoids duplication).
    run_arrows_added = False
    if include_run_arrows and eln_data:
        run_arrows = _build_run_arrows(eln_data)
        if run_arrows:
            yaml_dict["run_arrows"] = run_arrows
            run_arrows_added = True

    if not run_arrows_added:
        yield_pct = eln_data.get("product_yield", "").strip()
        if yield_pct:
            yield_str = yield_pct.rstrip("%").strip()
            step["yield_"] = f"{yield_str}%"

    return yaml_dict


# ---------------------------------------------------------------------------
# Run arrows
# ---------------------------------------------------------------------------

def _build_run_arrows(eln_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Build run_arrows list from ELN data (SM mass → product yield)."""
    sm_mass = eln_data.get("sm_mass", "").strip()
    product_obtained = eln_data.get("product_obtained", "").strip()
    product_yield = eln_data.get("product_yield", "").strip()

    if not sm_mass or not product_obtained:
        return None

    input_label = sm_mass if _has_unit(sm_mass) else f"{sm_mass} g"
    obtained_str = (product_obtained if _has_unit(product_obtained)
                    else f"{product_obtained} g")
    if product_yield:
        yield_clean = product_yield.rstrip("%").strip()
        output_label = f"{obtained_str}, {yield_clean}% yield"
    else:
        output_label = obtained_str

    return [{
        "step": 1,
        "runs": [{"input": input_label, "output": output_label}],
    }]


def _format_label_with_equiv(
    name: str, display: str, csv_equiv: Optional[str],
) -> str:
    """Build a text label, adding equiv only if not already present.

    Uses raw ``name`` as the base label, falling back to ``display``.
    Avoids duplicating "(X eq)" when ``display_text`` already contains it.
    """
    base = name or display
    if not base:
        return ""
    # If equiv data exists and the label doesn't already mention "eq"
    if csv_equiv and "eq" not in base.lower():
        return f"{base} ({csv_equiv} eq)"
    # If display has equiv but name doesn't, use display as-is
    if "eq" in display.lower():
        return display
    return base


def _normalize_conditions(conditions: List[str]) -> List[str]:
    """Normalize condition strings for display.

    Fixes temperature formatting:
      "80 C"  → "80 °C"
      "105C"  → "105 °C"
      "80°C"  → "80 °C"
      "-78 °C" → "-78 °C" (no change)
    """
    result = []
    for cond in conditions:
        # "80 C" or "-78 C" → "80 °C" (missing degree symbol)
        cond = re.sub(r"(-?\d+\.?\d*)\s+C\b", r"\1 °C", cond)
        # "80C" or "105C" → "80 °C" (no space, no degree)
        cond = re.sub(r"(-?\d+\.?\d*)C\b", r"\1 °C", cond)
        # "80°C" → "80 °C" (no space before degree)
        cond = re.sub(r"(-?\d+\.?\d*)°C", r"\1 °C", cond)
        result.append(cond)
    return result


def _has_unit(value: str) -> bool:
    """Check if a mass string already contains a unit (g, mg, mL, etc.)."""
    return bool(re.search(r"\d\s*(g|mg|kg|mL|µL|L)\b", value))


def _merge_eln_labels(experiments: List[str]) -> str:
    """Merge multiple ELN experiment names into a compact label.

    If all share a common prefix (e.g. "KL-7001-"), uses compact form:
    "KL-7001-001/003/004/009".  Otherwise joins with ", ".
    """
    if not experiments:
        return ""
    if len(experiments) == 1:
        return experiments[0]

    # Try to find common prefix up to the last dash
    parts = [exp.rsplit("-", 1) for exp in experiments if "-" in exp]
    if len(parts) == len(experiments):
        prefixes = set(p[0] for p in parts)
        if len(prefixes) == 1:
            prefix = parts[0][0]
            suffixes = [p[1] for p in parts]
            return prefix + "-" + "/".join(suffixes)
    return ", ".join(experiments)


# ---------------------------------------------------------------------------
# Multi-reaction merge — data structures
# ---------------------------------------------------------------------------

@dataclass
class ReactionSummary:
    """Extracted summary of one reaction JSON for merge classification."""
    index: int
    json_path: str
    experiment: str
    sm_smiles: str
    dp_smiles: str
    reagent_smiles: Dict[str, str]    # {species_id: canonical_smiles}
    reagent_names: Dict[str, str]     # {species_id: display_name}
    reagent_equivs: Dict[str, str]    # {species_id: equiv_str}
    all_smiles: set                   # all valid canonical SMILES in this reaction
    species: List[Dict[str, Any]]
    conditions: List[str]
    eln_data: Dict[str, Any]


@dataclass
class MergePlan:
    """How to combine N reaction JSONs into a merged scheme."""
    parallel_groups: List[List[int]]   # groups of reaction indices
    chains: List[List[int]]            # independent sequential chains (each is a topo-sorted list of group indices)
    unrelated_groups: List[int]        # indices into parallel_groups with no chain link

    def describe(self) -> str:
        parts: List[str] = []
        for chain in self.chains:
            descs = []
            for gi in chain:
                grp = self.parallel_groups[gi]
                descs.append("+".join(str(g) for g in grp)
                             if len(grp) > 1 else str(grp[0]))
            parts.append("Chain: " + " -> ".join(descs))
        for gi in self.unrelated_groups:
            grp = self.parallel_groups[gi]
            parts.append("Unrelated: " + "+".join(str(g) for g in grp))
        return "; ".join(parts) if parts else "Single reaction"


# ---------------------------------------------------------------------------
# Multi-reaction merge — SMILES matching
# ---------------------------------------------------------------------------

def _canonicalize(smiles: str) -> str:
    """Return RDKit canonical SMILES, or original string if RDKit fails."""
    if not smiles:
        return ""
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            return Chem.MolToSmiles(mol)
    except Exception:
        pass
    return smiles


def _strip_salts(smiles: str) -> str:
    """Strip small fragments (counterions) from multi-component SMILES.

    Keeps only the largest fragment by heavy atom count.  This handles
    common salt forms (HCl, TFA, Na+, etc.) that differ between ELN
    entries for the same compound.
    """
    if not smiles or "." not in smiles:
        return smiles
    try:
        from rdkit import Chem
        frags = smiles.split(".")
        best = smiles
        best_size = 0
        for frag in frags:
            mol = Chem.MolFromSmiles(frag)
            if mol is not None:
                size = mol.GetNumHeavyAtoms()
                if size > best_size:
                    best_size = size
                    best = Chem.MolToSmiles(mol)
        return best
    except Exception:
        return smiles


def _smiles_match(a: str, b: str) -> bool:
    """Check if two SMILES represent the same molecule, tolerating salt forms."""
    if not a or not b:
        return False
    if a == b:
        return True
    return _strip_salts(a) == _strip_salts(b)


def _extract_reaction_summary(index: int, json_path: str) -> ReactionSummary:
    """Load a reaction JSON and extract the key data for merge classification.

    Solvents are excluded from the reagent set (checked via role_detail or
    is_solvent flag).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    species = data.get("species", [])
    conditions = data.get("conditions", [])
    eln_data = data.get("eln_data") or {}
    experiment = data.get("experiment", os.path.splitext(
        os.path.basename(json_path))[0])

    sm_smiles = ""
    dp_smiles = ""
    reagent_smiles: Dict[str, str] = {}
    reagent_names: Dict[str, str] = {}
    reagent_equivs: Dict[str, str] = {}
    all_smiles: set = set()

    for sp in species:
        smi = _canonicalize(sp.get("smiles", ""))
        sp_id = sp.get("id", "")
        is_solvent = (sp.get("is_solvent", False)
                      or (sp.get("role_detail") or "").lower() == "solvent")

        if smi and smi != "?" and smi != "":
            all_smiles.add(smi)

        if sp.get("is_sm") and smi and not is_solvent:
            sm_smiles = smi
        if (sp.get("is_dp") or sp.get("role") == "product") and smi:
            dp_smiles = smi
        elif not is_solvent and smi and not sp.get("is_sm") and not sp.get("is_dp"):
            reagent_smiles[sp_id] = smi
            reagent_names[sp_id] = (sp.get("name") or sp.get("display_text")
                                    or sp_id)
            equiv = sp.get("csv_equiv")
            if equiv:
                reagent_equivs[sp_id] = str(equiv)

    return ReactionSummary(
        index=index, json_path=json_path, experiment=experiment,
        sm_smiles=sm_smiles, dp_smiles=dp_smiles,
        reagent_smiles=reagent_smiles, reagent_names=reagent_names,
        reagent_equivs=reagent_equivs, all_smiles=all_smiles,
        species=species, conditions=conditions, eln_data=eln_data,
    )


# ---------------------------------------------------------------------------
# Multi-reaction merge — pair classification
# ---------------------------------------------------------------------------

def _classify_pair(a: ReactionSummary, b: ReactionSummary) -> str:
    """Classify the relationship between two reactions.

    Returns "parallel", "sequential_ab", "sequential_ba", or "unrelated".

    Parallel requires: same SM + same DP + at least one shared non-solvent
    reagent.  Same SM+DP with no shared reagent = different chemistry.

    Salt forms are tolerated: free amine and HCl salt are treated as the
    same molecule for SM/DP matching.
    """
    sm_match = _smiles_match(a.sm_smiles, b.sm_smiles)
    dp_match = _smiles_match(a.dp_smiles, b.dp_smiles)

    if sm_match and dp_match:
        a_set = set(a.reagent_smiles.values())
        b_set = set(b.reagent_smiles.values())
        if a_set & b_set:
            return "parallel"
        return "unrelated"

    # Direct DP→SM match (salt-tolerant)
    if _smiles_match(a.dp_smiles, b.sm_smiles):
        return "sequential_ab"
    if _smiles_match(b.dp_smiles, a.sm_smiles):
        return "sequential_ba"

    # Fallback: check if A's product SMILES appears anywhere in B's species
    # (handles cases where SM SMILES is unresolved but the molecule appears
    # as a reagent or is otherwise present in the reaction)
    if a.dp_smiles:
        a_dp_stripped = _strip_salts(a.dp_smiles)
        for smi in b.all_smiles:
            if a.dp_smiles == smi or a_dp_stripped == _strip_salts(smi):
                return "sequential_ab"
    if b.dp_smiles:
        b_dp_stripped = _strip_salts(b.dp_smiles)
        for smi in a.all_smiles:
            if b.dp_smiles == smi or b_dp_stripped == _strip_salts(smi):
                return "sequential_ba"

    return "unrelated"


def _build_merge_plan(summaries: List[ReactionSummary]) -> MergePlan:
    """Analyze N reactions and determine merge strategy.

    Algorithm:
    1. Pairwise classification
    2. Union-Find for parallel clustering
    3. DAG construction for sequential links between clusters
    4. Find connected components in the DAG (independent chains)
    5. Topological sort within each component
    """
    n = len(summaries)
    if n == 1:
        return MergePlan(
            parallel_groups=[[0]], chains=[[0]],
            unrelated_groups=[],
        )

    # Classify all pairs
    classifications: Dict[Tuple[int, int], str] = {}
    for i in range(n):
        for j in range(i + 1, n):
            classifications[(i, j)] = _classify_pair(summaries[i], summaries[j])

    # Union-Find for parallel clusters
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for (i, j), c in classifications.items():
        if c == "parallel":
            union(i, j)

    # Build groups
    groups_map: Dict[int, List[int]] = {}
    for i in range(n):
        root = find(i)
        groups_map.setdefault(root, []).append(i)
    groups = list(groups_map.values())

    reaction_to_group: Dict[int, int] = {}
    for gi, grp in enumerate(groups):
        for ri in grp:
            reaction_to_group[ri] = gi

    # DAG of sequential links between groups
    ng = len(groups)
    seq_edges: set = set()
    for (i, j), c in classifications.items():
        gi, gj = reaction_to_group[i], reaction_to_group[j]
        if gi == gj:
            continue
        if c == "sequential_ab":
            seq_edges.add((gi, gj))
        elif c == "sequential_ba":
            seq_edges.add((gj, gi))

    if not seq_edges:
        # No sequential links at all
        if ng == 1:
            return MergePlan(
                parallel_groups=groups, chains=[[0]],
                unrelated_groups=[],
            )
        return MergePlan(
            parallel_groups=groups, chains=[],
            unrelated_groups=list(range(ng)),
        )

    # Find connected components in the undirected version of the DAG
    adj_undirected: Dict[int, set] = {i: set() for i in range(ng)}
    adj_directed: Dict[int, List[int]] = {i: [] for i in range(ng)}
    in_deg: Dict[int, int] = {i: 0 for i in range(ng)}
    for a, b in seq_edges:
        adj_undirected[a].add(b)
        adj_undirected[b].add(a)
        adj_directed[a].append(b)
        in_deg[b] += 1

    visited: set = set()
    components: List[set] = []
    for start in range(ng):
        if start in visited or not adj_undirected[start]:
            continue
        # BFS to find connected component
        component: set = set()
        bfs_queue = [start]
        while bfs_queue:
            node = bfs_queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for nb in adj_undirected[node]:
                if nb not in visited:
                    bfs_queue.append(nb)
        components.append(component)

    # Topological sort within each component → one chain per component
    chains: List[List[int]] = []
    for component in components:
        # Kahn's algorithm on the subgraph
        local_in: Dict[int, int] = {g: 0 for g in component}
        for g in component:
            for nb in adj_directed[g]:
                if nb in component:
                    local_in[nb] += 1
        queue = [g for g in component if local_in[g] == 0]
        chain: List[int] = []
        while queue:
            node = queue.pop(0)
            chain.append(node)
            for nb in adj_directed[node]:
                if nb in component:
                    local_in[nb] -= 1
                    if local_in[nb] == 0:
                        queue.append(nb)
        if len(chain) != len(component):
            chain = sorted(component)  # cycle fallback
        chains.append(chain)

    # Groups not in any component → unrelated
    connected_groups: set = set()
    for comp in components:
        connected_groups.update(comp)
    unrelated = [gi for gi in range(ng) if gi not in connected_groups]

    return MergePlan(
        parallel_groups=groups,
        chains=chains,
        unrelated_groups=unrelated,
    )


# ---------------------------------------------------------------------------
# Multi-reaction merge — parallel merge helpers
# ---------------------------------------------------------------------------

def _pick_template(
    summaries: List[ReactionSummary],
    group_indices: List[int],
) -> int:
    """Pick the best template reaction for a parallel group.

    Returns the index (into summaries) of the reaction whose reagent
    SMILES set is shared by the most other reactions in the group.
    This minimizes the number of run-arrow notes needed.
    """
    if len(group_indices) <= 1:
        return group_indices[0]

    reagent_sets = {}
    for ri in group_indices:
        s = summaries[ri]
        reagent_sets[ri] = frozenset(s.reagent_smiles.values())

    best_ri = group_indices[0]
    best_count = 0
    for ri in group_indices:
        count = sum(1 for other in group_indices
                    if reagent_sets[other] == reagent_sets[ri])
        if count > best_count:
            best_count = count
            best_ri = ri
    return best_ri


def _diff_reagents(
    summaries: List[ReactionSummary],
    group_indices: List[int],
) -> Tuple[bool, Dict[int, Optional[str]]]:
    """Compare reagents across parallel reactions against the optimal template.

    Each run is compared against the template reaction (first in group).
    Notes only show reagents that are in THIS run but NOT in the template
    (i.e. what's different about this particular run).  Equiv differences
    for shared reagents are handled by range notation on the main arrow.

    Returns (all_identical, {reaction_index: note_string_or_None}).
    """
    if len(group_indices) <= 1:
        return True, {}

    # Build per-reaction fingerprint: {canonical_smiles: (name, equiv)}
    per_reaction: Dict[int, Dict[str, Tuple[str, str]]] = {}
    for ri in group_indices:
        s = summaries[ri]
        fp: Dict[str, Tuple[str, str]] = {}
        for sp_id, smi in s.reagent_smiles.items():
            equiv = s.reagent_equivs.get(sp_id, "")
            name = s.reagent_names.get(sp_id, "")
            fp[smi] = (name, equiv)
        per_reaction[ri] = fp

    template_ri = _pick_template(summaries, group_indices)
    template_smiles = set(per_reaction[template_ri].keys())

    # Check if any run has a different reagent set than the template
    has_differences = False
    notes: Dict[int, Optional[str]] = {}
    for ri in group_indices:
        run_smiles = set(per_reaction[ri].keys())
        # Reagents in this run but NOT in the template
        extra = run_smiles - template_smiles
        if extra:
            has_differences = True
            parts: List[str] = []
            for smi in sorted(extra):
                name, equiv = per_reaction[ri][smi]
                if equiv:
                    parts.append(f"{name} ({equiv} eq)")
                else:
                    parts.append(name)
            notes[ri] = ", ".join(parts)
        else:
            notes[ri] = None

    if not has_differences:
        return True, {}

    return False, notes


def _equiv_range(
    summaries: List[ReactionSummary],
    group_indices: List[int],
    smiles: str,
) -> str:
    """Compute range notation for equivalents of one reagent across parallel runs.

    Returns e.g. "1.1\u20131.5" (en-dash) if they differ, single value if same.
    """
    values: List[float] = []
    for ri in group_indices:
        s = summaries[ri]
        for sp_id, smi in s.reagent_smiles.items():
            if smi == smiles:
                eq = s.reagent_equivs.get(sp_id, "")
                if eq:
                    try:
                        values.append(float(eq))
                    except ValueError:
                        pass
    if not values:
        return ""
    unique = sorted(set(values))
    if len(unique) == 1:
        return f"{unique[0]:g}"
    return f"{unique[0]:g}\u2013{unique[-1]:g}"


# ---------------------------------------------------------------------------
# Multi-reaction merge — combined YAML generation
# ---------------------------------------------------------------------------

def _namespace_species_id(reaction_index: int, sp_id: str) -> str:
    """Prefix a species ID with reaction index to avoid collisions."""
    return f"rxn{reaction_index}_{sp_id}"


def _apply_namespace(
    yaml_dict: Dict[str, Any],
    reaction_index: int,
    remap: Dict[str, str],
) -> Dict[str, Any]:
    """Namespace all structure IDs in a single-reaction YAML dict.

    Returns a new dict with namespaced structure keys and step references.
    Applies the remap table for shared intermediates.
    """
    old_structures = yaml_dict.get("structures", {})
    new_structures: Dict[str, Any] = {}
    id_map: Dict[str, str] = {}  # old_id -> final_id

    for old_id, struct_data in old_structures.items():
        ns_id = _namespace_species_id(reaction_index, old_id)
        final_id = remap.get(ns_id, ns_id)
        id_map[old_id] = final_id
        new_structures[final_id] = struct_data

    def _remap_ids(id_list: List[str]) -> List[str]:
        return [id_map.get(sid, sid) for sid in id_list]

    new_steps = []
    for step in yaml_dict.get("steps", []):
        new_step = dict(step)
        if "substrates" in new_step:
            new_step["substrates"] = _remap_ids(new_step["substrates"])
        if "products" in new_step:
            new_step["products"] = _remap_ids(new_step["products"])
        if "above_arrow" in new_step:
            above = dict(new_step["above_arrow"])
            if "structures" in above:
                above["structures"] = _remap_ids(above["structures"])
            new_step["above_arrow"] = above
        new_steps.append(new_step)

    result = dict(yaml_dict)
    result["structures"] = new_structures
    result["steps"] = new_steps
    return result


def _build_run_entry_from_eln(
    eln_data: Dict[str, Any],
    allow_partial: bool = False,
) -> Optional[Dict[str, Any]]:
    """Build a single run arrow entry dict from ELN data.

    Parameters
    ----------
    allow_partial : bool
        When True, create an entry even if only sm_mass is available
        (output will be empty).  Used for merged schemes where every
        reaction should get a run arrow.
    """
    sm_mass = eln_data.get("sm_mass", "").strip()
    product_obtained = eln_data.get("product_obtained", "").strip()
    product_yield = eln_data.get("product_yield", "").strip()

    if not sm_mass:
        return None
    if not product_obtained and not allow_partial:
        return None

    input_label = sm_mass if _has_unit(sm_mass) else f"{sm_mass} g"

    if product_obtained:
        obtained_str = (product_obtained if _has_unit(product_obtained)
                        else f"{product_obtained} g")
        if product_yield:
            yield_clean = product_yield.rstrip("%").strip()
            output_label = f"{obtained_str}, {yield_clean}% yield"
        else:
            output_label = obtained_str
    else:
        output_label = ""

    return {"input": input_label, "output": output_label}


def _update_below_arrow_with_ranges(
    step_dict: Dict[str, Any],
    summaries: List[ReactionSummary],
    group_indices: List[int],
    template: ReactionSummary,
) -> None:
    """Replace individual equiv values with range notation in below_arrow text.

    For parallel groups, reagents that vary across runs get range notation
    (e.g., "Cs2CO3 (1.5\u20132.0 eq)").
    """
    below = step_dict.get("below_arrow")
    if not below:
        return
    text_lines = below.get("text", [])
    if not text_lines:
        return

    new_lines = []
    for line in text_lines:
        updated = False
        for sp in template.species:
            name = sp.get("name", "")
            if not name or name not in line or "eq" not in line:
                continue
            smi = _canonicalize(sp.get("smiles", ""))
            if not smi:
                continue
            range_str = _equiv_range(summaries, group_indices, smi)
            if range_str and "\u2013" in range_str:
                new_line = re.sub(
                    r"\([^)]*eq\)", f"({range_str} eq)", line)
                new_lines.append(new_line)
                updated = True
                break
        if not updated:
            new_lines.append(line)

    below["text"] = new_lines


def _update_above_arrow_with_ranges(
    step_dict: Dict[str, Any],
    summaries: List[ReactionSummary],
    group_indices: List[int],
    template: ReactionSummary,
) -> None:
    """Replace equiv values in above_arrow text with range notation."""
    above = step_dict.get("above_arrow")
    if not above:
        return
    text_lines = above.get("text", [])
    if not text_lines:
        return

    # Above-arrow text entries are typically "(X eq)" for each above structure.
    # Find the corresponding species by position.
    above_structs = above.get("structures", [])
    new_lines = []
    for i, line in enumerate(text_lines):
        if "eq" not in line:
            new_lines.append(line)
            continue
        # Find the SMILES for the i-th above structure
        if i < len(above_structs):
            sid = above_structs[i]
            sp = next((s for s in template.species if s.get("id") == sid), None)
            if sp:
                smi = _canonicalize(sp.get("smiles", ""))
                if smi:
                    range_str = _equiv_range(summaries, group_indices, smi)
                    if range_str and "\u2013" in range_str:
                        new_lines.append(f"({range_str} eq)")
                        continue
        new_lines.append(line)

    above["text"] = new_lines


def build_merged_scheme_yaml_dict(
    json_paths: List[str],
    layout: str = "auto",
    include_run_arrows: bool = True,
    use_eln_labels: bool = False,
) -> Dict[str, Any]:
    """Build a combined YAML dict from multiple reaction JSONs.

    Detects parallel reactions (same SM + DP + shared reagents) and sequential
    chains (product of A = SM of B), and produces a merged scheme.
    """
    all_summaries = [_extract_reaction_summary(i, p)
                     for i, p in enumerate(json_paths)]

    # Filter out degenerate reactions (SM == DP, e.g. solubility tests,
    # control experiments).  These have no meaningful reaction to display.
    summaries = [s for s in all_summaries
                 if not (s.sm_smiles and s.dp_smiles
                         and s.sm_smiles == s.dp_smiles)]

    if not summaries:
        summaries = all_summaries  # fallback: don't filter everything out

    plan = _build_merge_plan(summaries)

    # --- Determine shared intermediates (per chain) ---
    remap: Dict[str, str] = {}
    for chain in plan.chains:
        for ci in range(len(chain) - 1):
            gi_a = chain[ci]
            gi_b = chain[ci + 1]
            ri_a = plan.parallel_groups[gi_a][0]
            ri_b = plan.parallel_groups[gi_b][0]
            sa, sb = summaries[ri_a], summaries[ri_b]

            # Find the DP species in A that links to B
            dp_id_a = next(
                (sp["id"] for sp in sa.species
                 if (sp.get("is_dp") or sp.get("role") == "product")
                 and _canonicalize(sp.get("smiles", "")) == sa.dp_smiles),
                None,
            )
            # Find the SM species in B that matches A's product.
            # Try direct SM match first; if SM SMILES is unresolved, find any
            # species in B whose SMILES equals A's DP.
            sm_id_b = next(
                (sp["id"] for sp in sb.species
                 if sp.get("is_sm")
                 and _canonicalize(sp.get("smiles", "")) == sa.dp_smiles),
                None,
            )
            if sm_id_b is None:
                # Fallback: any species in B with matching SMILES
                sm_id_b = next(
                    (sp["id"] for sp in sb.species
                     if _canonicalize(sp.get("smiles", "")) == sa.dp_smiles),
                    None,
                )
            if dp_id_a and sm_id_b:
                canonical = _namespace_species_id(ri_a, dp_id_a)
                replaced = _namespace_species_id(ri_b, sm_id_b)
                remap[replaced] = canonical

    # --- Build per-group YAML dicts ---
    def _build_group(
        group_indices: List[int],
        step_number: int,
        label_start: int,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], int]:
        """Build YAML structures + step(s) for one parallel group.

        Returns (structures_dict, [step_dict], next_label).
        """
        template_ri = _pick_template(summaries, group_indices)
        template = summaries[template_ri]

        # ELN label for products (when use_eln_labels is enabled)
        plabel = None
        if use_eln_labels:
            exps = [summaries[ri].experiment for ri in group_indices]
            plabel = _merge_eln_labels(exps)

        # Build single-reaction dict using existing logic
        single = _build_yaml_dict(
            template.species, template.conditions, template.eln_data,
            layout="linear", include_run_arrows=False,
            product_label=plabel,
        )

        # Range notation for parallel groups — apply BEFORE namespacing
        # so that species IDs in above_arrow.structures match template.species
        if len(group_indices) > 1:
            _update_below_arrow_with_ranges(
                single["steps"][0], summaries, group_indices, template)
            _update_above_arrow_with_ranges(
                single["steps"][0], summaries, group_indices, template)

        # Namespace IDs
        ns = _apply_namespace(single, template_ri, remap)
        structures = ns["structures"]
        step = ns["steps"][0]

        # Relabel: skip IDs already in all_structures (shared intermediates
        # get their label from the group that first produced them).
        if use_eln_labels:
            # ELN mode: labels already set by _build_yaml_dict (product_label)
            for _sid in list(structures.keys()):
                if _sid in all_structures:
                    del structures[_sid]
        else:
            # Default mode: relabel with global counter
            label_counter = label_start
            for _sid in list(structures.keys()):
                if _sid in all_structures:
                    del structures[_sid]
                    continue
                entry = structures[_sid]
                if "label" in entry:
                    entry["label"] = str(label_counter)
                    label_counter += 1
            label_start = label_counter

        return structures, [step], label_start

    def _build_group_run_arrows(
        group_indices: List[int],
        step_number: int,
        include: bool,
    ) -> Optional[Dict[str, Any]]:
        """Build run_arrows entry for one parallel group.

        Every reaction in the group gets a run arrow, even if the ELN
        data only has sm_mass (no product_obtained).  This ensures all
        runs are visible, with deviation notes shown where applicable.
        """
        if not include:
            return None

        all_identical, notes = _diff_reagents(summaries, group_indices)
        runs: List[Dict[str, Any]] = []
        for ri in group_indices:
            entry = _build_run_entry_from_eln(
                summaries[ri].eln_data, allow_partial=True)
            if entry:
                if not all_identical and notes.get(ri):
                    entry["note"] = notes[ri]
                runs.append(entry)

        if runs:
            return {"step": step_number, "runs": runs}
        return None

    # --- Determine overall layout ---
    num_chains = len(plan.chains)
    num_unrelated = len(plan.unrelated_groups)
    num_sections = num_chains + num_unrelated

    if layout == "auto":
        if num_sections > 1:
            layout = "stacked-rows"
        elif num_chains == 1 and len(plan.chains[0]) > 1:
            layout = "sequential"
        else:
            layout = "linear"

    # --- Assemble ---
    all_structures: Dict[str, Any] = {}
    run_arrows_list: List[Dict[str, Any]] = []

    if layout == "stacked-rows" or num_sections > 1:
        # Each chain becomes a section; each unrelated group becomes a section
        sections: List[Dict[str, Any]] = []
        label_counter = 1
        global_step = 1

        for chain in plan.chains:
            chain_steps: List[Dict[str, Any]] = []
            for gi in chain:
                grp = plan.parallel_groups[gi]
                structs, steps, label_counter = _build_group(
                    grp, global_step, label_counter)
                valid_steps = [s for s in steps
                           if s.get("substrates") or s.get("products")]
                if not valid_steps:
                    continue
                all_structures.update(structs)
                chain_steps.extend(valid_steps)
                ra = _build_group_run_arrows(grp, global_step, include_run_arrows)
                if ra:
                    run_arrows_list.append(ra)
                global_step += 1
            if chain_steps:
                sec: Dict[str, Any] = {"steps": chain_steps}
                if len(chain_steps) > 1:
                    sec["layout"] = "sequential"
                sections.append(sec)

        # Each unrelated group as its own section
        for gi in plan.unrelated_groups:
            grp = plan.parallel_groups[gi]
            structs, steps, label_counter = _build_group(
                grp, global_step, label_counter)
            valid_steps = [s for s in steps
                           if s.get("substrates") or s.get("products")]
            if not valid_steps:
                continue
            all_structures.update(structs)
            sec = {"steps": valid_steps}
            ra = _build_group_run_arrows(grp, global_step, include_run_arrows)
            if ra:
                run_arrows_list.append(ra)
            global_step += 1
            sections.append(sec)

        # If only 1 section survived, collapse to flat sequential layout
        if len(sections) == 1:
            flat_steps = sections[0].get("steps", [])
            flat_layout = "sequential" if len(flat_steps) > 1 else "linear"
            yaml_dict: Dict[str, Any] = {
                "structures": all_structures,
                "steps": flat_steps,
                "layout": flat_layout,
            }
        else:
            yaml_dict = {
                "structures": all_structures,
                "sections": sections,
                "layout": "stacked-rows",
            }
    else:
        # Linear or sequential: single chain, flat steps list
        all_steps: List[Dict[str, Any]] = []
        label_counter = 1
        step_num = 1
        # Use the single chain if available, otherwise unrelated groups
        group_order = plan.chains[0] if plan.chains else plan.unrelated_groups
        for gi in group_order:
            grp = plan.parallel_groups[gi]
            structs, steps, label_counter = _build_group(
                grp, step_num, label_counter)
            valid_steps = [s for s in steps
                           if s.get("substrates") or s.get("products")]
            if not valid_steps:
                continue
            all_structures.update(structs)
            all_steps.extend(valid_steps)
            ra = _build_group_run_arrows(grp, step_num, include_run_arrows)
            if ra:
                run_arrows_list.append(ra)
            step_num += 1

        yaml_dict = {
            "structures": all_structures,
            "steps": all_steps,
            "layout": layout,
        }

    # Prevent auto-wrapping; merged schemes should render as-is
    if yaml_dict.get("layout") == "sequential":
        yaml_dict["wrap"] = "none"

    if run_arrows_list:
        yaml_dict["run_arrows"] = run_arrows_list

    return yaml_dict


def write_merged_scheme_yaml(
    json_paths: List[str],
    output_path: str,
    layout: str = "auto",
    include_run_arrows: bool = True,
    use_eln_labels: bool = False,
) -> str:
    """Read multiple reaction JSONs, detect relationships, write merged YAML.

    Returns the absolute path to the written YAML file.
    """
    yaml_dict = build_merged_scheme_yaml_dict(
        json_paths, layout=layout, include_run_arrows=include_run_arrows,
        use_eln_labels=use_eln_labels,
    )
    _write_yaml_file(yaml_dict, output_path)
    return os.path.abspath(output_path)


# ---------------------------------------------------------------------------
# YAML output
# ---------------------------------------------------------------------------

def _write_yaml_file(data: Dict[str, Any], path: str) -> None:
    """Write YAML dict to file.

    Uses PyYAML if available, otherwise writes a simple manual format.
    """
    if yaml is not None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                      sort_keys=False)
    else:
        # Fallback: write JSON with .yaml extension (valid YAML superset)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate scheme YAML from one or more reaction_parser JSON files.",
    )
    parser.add_argument("json_paths", nargs="+",
                        help="One or more reaction parser JSON files")
    parser.add_argument("-o", "--output", default=None,
                        help="Output YAML path (default: auto-generated)")
    parser.add_argument("--layout", default="auto",
                        help="Layout: linear, sequential, stacked-rows, auto")
    parser.add_argument("--no-run-arrows", action="store_true",
                        help="Suppress run arrows")
    parser.add_argument("--no-merge", action="store_true",
                        help="Process each JSON individually (skip merge)")
    parser.add_argument("--eln-labels", action="store_true",
                        help="Label products with ELN experiment names "
                        "instead of sequential numbers")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    for jp in args.json_paths:
        if not os.path.exists(jp):
            print(f"Error: {jp} not found", file=sys.stderr)
            sys.exit(1)

    include_run_arrows = not args.no_run_arrows

    if len(args.json_paths) == 1:
        # Single input: existing behavior
        jp = args.json_paths[0]
        output = args.output
        if output is None:
            stem = os.path.splitext(os.path.basename(jp))[0]
            output = os.path.join(
                os.path.dirname(jp) or ".", f"{stem}-scheme.yaml")
        result = write_scheme_yaml(
            jp, output, layout=args.layout,
            include_run_arrows=include_run_arrows,
            use_eln_labels=args.eln_labels,
        )
        if args.verbose:
            print(f"Written: {result}", file=sys.stderr)
        print(result)
    else:
        # Multiple inputs: produce individual YAMLs + merged YAML
        for jp in args.json_paths:
            stem = os.path.splitext(os.path.basename(jp))[0]
            ind_output = os.path.join(
                os.path.dirname(jp) or ".", f"{stem}-scheme.yaml")
            result = write_scheme_yaml(
                jp, ind_output, layout=args.layout,
                include_run_arrows=include_run_arrows,
                use_eln_labels=args.eln_labels,
            )
            if args.verbose:
                print(f"Individual: {result}", file=sys.stderr)

        if not args.no_merge:
            output = args.output
            if output is None:
                output = os.path.join(
                    os.path.dirname(args.json_paths[0]) or ".",
                    "merged-scheme.yaml")
            merged = write_merged_scheme_yaml(
                args.json_paths, output, layout=args.layout,
                include_run_arrows=include_run_arrows,
                use_eln_labels=args.eln_labels,
            )
            if args.verbose:
                print(f"Merged: {merged}", file=sys.stderr)
            print(merged)


if __name__ == "__main__":
    main()
