"""Perception — reading and understanding reaction schemes.

Everything about extracting semantic meaning from CDXML: which fragments are
reactants vs products vs reagents, what the arrows connect, what the text
labels mean.
"""

from .scheme_reader import read_scheme, SchemeDescription
from .reaction_parser import parse_reaction, ReactionDescriptor, reaction_summary
from .scheme_segmenter import segment_scheme, classify_scheme_complexity
