"""Resolve — turning chemical names, formulae, and abbreviations into SMILES.

The 4-tier resolution chain and all supporting databases:
  Tier 1: curated reagent database (~186 entries)
  Tier 2: generative condensed-formula parser
  Tier 3: OPSIN (via reactant_heuristic)
  Tier 4: PubChem name/CAS lookup
"""

from .reagent_db import get_reagent_db, ReagentDB
from .condensed_formula import resolve_condensed_formula
from .cas_resolver import resolve_name_to_smiles, resolve_cas
from .superatom_table import lookup_smiles, get_superatom_table
