"""Lossless CDXML document model.

``parse`` / ``load`` keep every element, attribute (in order, with its exact string value),
text run and comment, plus the XML declaration and DOCTYPE. Edits go through ``Document``
methods that validate names and values against the ChemDraw catalog
(``cdxml_toolkit/catalog/data/cdxml_model_22_2.json``), so an attribute the catalog does not
know is refused unless the caller opts in or the element already carries it.
"""

from .document import Document, catalog_index, load, parse

__all__ = ["Document", "catalog_index", "load", "parse"]
