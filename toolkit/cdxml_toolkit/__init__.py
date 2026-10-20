"""cdxml-toolkit: Python toolkit for ChemDraw CDXML reaction scheme processing.

Provides tools for reading, writing, manipulating, and rendering ChemDraw CDXML
files. Includes reaction scheme layout, reagent classification, structure
alignment, and a declarative DSL for building schemes from YAML or text.

Core utilities are available without optional dependencies. RDKit, ChemDraw COM,
and other heavy dependencies are lazy-imported and only required when their
specific features are used.
"""

__version__ = "0.7.0a2"

# Core utilities — always available (stdlib + lxml only)
from .constants import ACS_BOND_LENGTH, ACS_CHAIN_ANGLE, ACS_STYLE
from .cdxml_utils import parse_cdxml, write_cdxml, fragment_bbox
from .text_formatting import build_formatted_s_xml
from .resolve.reagent_db import get_reagent_db
