"""
schema.py — Dataclasses for the scheme DSL descriptor.

Represents the parsed content of a YAML scheme file. The LLM specifies
chemistry content and topology; the renderer handles all spatial layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StructureRef:
    """Reference to a chemical structure — resolved later by the renderer."""
    id: str                          # user-assigned key (e.g. "ArBr")
    smiles: Optional[str] = None     # SMILES string
    name: Optional[str] = None       # compound name (for resolution)
    file: Optional[str] = None       # path to CDXML file
    cdxml_id: Optional[int] = None   # existing fragment ID
    label: Optional[str] = None      # compound number displayed below (e.g. "1")


@dataclass
class ArrowContent:
    """Content placed above or below an arrow."""
    structures: list[str] = field(default_factory=list)  # refs to StructureRef ids
    text: list[str] = field(default_factory=list)        # condition text lines


@dataclass
class StepDescriptor:
    """A single reaction step."""
    substrates: list[str]            # refs to StructureRef ids
    products: list[str]              # refs to StructureRef ids
    above_arrow: Optional[ArrowContent] = None
    below_arrow: Optional[ArrowContent] = None
    yield_: Optional[str] = None
    number: Optional[int] = None     # for numbered steps
    id: Optional[str] = None
    arrow_style: str = "solid"       # "solid", "dashed", "failed" (X on arrow)


@dataclass
class RunArrowEntry:
    """A single run (one scale) of a reaction step."""
    input_label: str         # e.g. "2.15 g"
    output_label: str        # e.g. "1.60 g, 72% yield"
    note: Optional[str] = None  # per-run annotation, e.g. "HATU (1.2 eq)"


@dataclass
class StepRunArrows:
    """Run arrows for a specific step (may have multiple scales)."""
    step: int                # 1-indexed step number
    runs: list[RunArrowEntry] = field(default_factory=list)


VALID_LAYOUTS = frozenset({
    "linear", "sequential", "divergent", "stacked-rows",
    "numbered-parallel", "convergent",
})

VALID_WRAPS = frozenset({"repeat", "serpentine", "none"})

VALID_ARROW_STYLES = frozenset({"solid", "dashed", "failed"})


@dataclass
class SectionDescriptor:
    """A section in a stacked-rows layout."""
    label: Optional[str] = None          # "(i)", "(a)", etc.
    steps: list[StepDescriptor] = field(default_factory=list)
    layout: str = "linear"               # each section's internal layout


@dataclass
class SchemeDescriptor:
    """Complete scheme description."""
    source: Optional[str] = None     # path to reaction_parser JSON file
    structures: dict[str, StructureRef] = field(default_factory=dict)
    steps: list[StepDescriptor] = field(default_factory=list)
    layout: str = "linear"           # layout pattern keyword
    wrap: str = "repeat"             # "repeat", "serpentine", "none"
    steps_per_row: Optional[int] = None  # auto-computed if omitted
    title: Optional[str] = None
    run_arrows: list[StepRunArrows] = field(default_factory=list)
    condition_key: Optional[dict[str, str]] = None  # letter conditions: {"a": "..."}
    sections: list[SectionDescriptor] = field(default_factory=list)
