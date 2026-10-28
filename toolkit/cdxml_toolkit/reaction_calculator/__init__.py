"""Stoichiometry behind the materials tables and route summaries: amounts, yield and safety notes.

ChemDraw's own interactive grid (Structure > Analyze Stoichiometry) is driven by
``cdxml_toolkit.chemdraw.stoichiometry_grid``.
"""

from .engine import compute
from .state import build_state

__all__ = ['build_state', 'compute']
