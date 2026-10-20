"""Render — declarative text-based reaction scheme renderer.

Build publication-ready CDXML reaction schemes from YAML or compact text.
The LLM specifies semantic content (structures, roles, conditions);
the deterministic renderer handles all spatial layout.

Supported layouts: linear, sequential, serpentine, divergent, stacked-rows.
Supported annotations: run arrows, dashed/failed arrows, compound labels,
letter conditions.

No ChemDraw COM needed — uses RDKit for 2D coordinate generation.
"""

from .schema import SchemeDescriptor, StepDescriptor, StructureRef, ArrowContent
from .renderer import render, render_to_file
from .parser import parse_yaml
from .compact_parser import parse_compact_file
