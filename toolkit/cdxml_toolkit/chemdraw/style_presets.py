"""Built-in drawing-style presets taken from ChemDraw's stock style sheets.

Each preset holds the document settings of one style sheet that ChemDraw
installs in its ``ChemDraw Items`` folder (ACS Document 1996, Wiley, RSC,
Nature Research and others), copied here so the toolkit never needs ChemDraw
or the ``.cds`` files at run time.  Values use CDXML attribute names and
units, as returned by :func:`cdxml_toolkit.chemdraw.style_sheet.read_style_sheet`.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

DEFAULT_STYLE_PRESET = "acs1996"


def _preset(name: str, sheet: str, used_by: str, attributes: dict, *, label: tuple, caption: tuple) -> Mapping:
    return MappingProxyType({
        "name": name,
        "sheet": sheet,
        "used_by": used_by,
        "attributes": MappingProxyType(dict(attributes)),
        "fonts": MappingProxyType({"label": tuple(label), "caption": tuple(caption)}),
    })


STYLE_PRESETS: Mapping[str, Mapping] = MappingProxyType({
    'acs1996': _preset(
        'ACS Document 1996', 'ACS Document 1996',
        'ACS journals (J. Am. Chem. Soc., J. Org. Chem., Org. Lett. and others); the toolkit default',
        {'BondLength': '14.4', 'BoldWidth': '2', 'LineWidth': '0.6', 'MarginWidth': '1.6', 'HashSpacing': '2.5', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '10'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'wiley': _preset(
        'Wiley', 'Wiley Document',
        'Wiley-VCH journals such as Angew. Chem. and Chem. Eur. J.',
        {'BondLength': '17', 'BoldWidth': '2.6', 'LineWidth': '0.75', 'MarginWidth': '2', 'HashSpacing': '2.6', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '12', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'adv_synth_catal': _preset(
        'Adv. Synth. Catal.', 'Adv. Synth. Catal. Document',
        'Advanced Synthesis & Catalysis',
        {'BondLength': '17', 'BoldWidth': '2', 'LineWidth': '1', 'MarginWidth': '1.6', 'HashSpacing': '2.5', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Times New Roman', 'iso-8859-1'),
    ),
    'rsc': _preset(
        'RSC (2 column)', 'RSC (2 Column) Document',
        'Royal Society of Chemistry journals, two-column figures',
        {'BondLength': '12.2', 'BoldWidth': '1.6', 'LineWidth': '0.45', 'MarginWidth': '1.25', 'HashSpacing': '1.75', 'ChainAngle': '120', 'BondSpacing': '20', 'LabelFace': '96', 'LabelSize': '7', 'CaptionFace': '0', 'CaptionSize': '7'},
        label=('Helvetica', 'iso-8859-1'), caption=('Helvetica', 'iso-8859-1'),
    ),
    'rsc_1col': _preset(
        'RSC (1 column)', 'RSC (1 Column) Document',
        'Royal Society of Chemistry journals, one-column figures',
        {'BondLength': '12.2', 'BoldWidth': '1.6', 'LineWidth': '0.45', 'MarginWidth': '1.25', 'HashSpacing': '1.75', 'ChainAngle': '120', 'BondSpacing': '20', 'LabelFace': '96', 'LabelSize': '7', 'CaptionFace': '96', 'CaptionSize': '7'},
        label=('Helvetica', 'iso-8859-1'), caption=('Helvetica', 'iso-8859-1'),
    ),
    'nature': _preset(
        'Nature Research', 'Nature Research Document',
        'Nature and Nature Research journals',
        {'BondLength': '10.8', 'BoldWidth': '1.56', 'LineWidth': '0.6', 'MarginWidth': '1.19', 'HashSpacing': '1.7', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '6', 'CaptionFace': '96', 'CaptionSize': '6'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'synthesis': _preset(
        'SYNTHESIS, SYNLETT', 'SYNTHESIS, SYNLETT Document',
        'Thieme Synthesis and Synlett',
        {'BondLength': '17', 'BoldWidth': '2', 'LineWidth': '0.8', 'MarginWidth': '1.3', 'HashSpacing': '2.5', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '10'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'science_of_synthesis': _preset(
        'Science of Synthesis', 'Science of Synthesis',
        'Thieme Science of Synthesis reference work',
        {'BondLength': '17', 'BoldWidth': '2', 'LineWidth': '0.8', 'MarginWidth': '2.25', 'HashSpacing': '2.5', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '10'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'helv_chim_acta': _preset(
        'Helv. Chim. Acta', 'Verlag Helv. Chim. Acta Doc',
        'Helvetica Chimica Acta',
        {'BondLength': '17', 'BoldWidth': '2', 'LineWidth': '0.6', 'MarginWidth': '2', 'HashSpacing': '2', 'ChainAngle': '120', 'BondSpacing': '15', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'j_het_chem': _preset(
        'J. Heterocycl. Chem.', 'J. Het. Chem',
        'Journal of Heterocyclic Chemistry',
        {'BondLength': '10.8', 'BoldWidth': '2.06', 'LineWidth': '0.6', 'MarginWidth': '1.08', 'HashSpacing': '1.3', 'ChainAngle': '120', 'BondSpacing': '16', 'LabelFace': '96', 'LabelSize': '7', 'CaptionFace': '0', 'CaptionSize': '7'},
        label=('Times', 'iso-8859-1'), caption=('Times', 'iso-8859-1'),
    ),
    'j_chin_chem_soc': _preset(
        'J. Chin. Chem. Soc.', 'J. Chin. Chem. Soc. Document',
        'Journal of the Chinese Chemical Society',
        {'BondLength': '18', 'BoldWidth': '2.5', 'LineWidth': '1', 'MarginWidth': '2', 'HashSpacing': '2.5', 'ChainAngle': '120', 'BondSpacing': '20', 'LabelFace': '96', 'LabelSize': '12', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'j_mol_mod': _preset(
        'J. Mol. Model.', 'J. Mol. Mod. (2 Column)',
        'Journal of Molecular Modeling (the one- and two-column sheets are identical)',
        {'BondLength': '14.4', 'BoldWidth': '2', 'LineWidth': '0.6', 'MarginWidth': '1.6', 'HashSpacing': '2.5', 'ChainAngle': '120', 'BondSpacing': '18', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '10'},
        label=('Times New Roman', 'iso-8859-1'), caption=('Times New Roman', 'iso-8859-1'),
    ),
    'phytomedicine': _preset(
        'Phytomedicine', 'Phytomedicine Document',
        'Phytomedicine',
        {'BondLength': '20', 'BoldWidth': '1.33', 'LineWidth': '1', 'MarginWidth': '1.25', 'HashSpacing': '3', 'ChainAngle': '120', 'BondSpacing': '8', 'LabelFace': '97', 'LabelSize': '12', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Arial', 'iso-8859-1'),
    ),
    'chemdraw_default': _preset(
        'ChemDraw new document', 'New Document',
        "ChemDraw's default for a new document (not a journal style)",
        {'BondLength': '30', 'BoldWidth': '4', 'LineWidth': '1', 'MarginWidth': '2', 'HashSpacing': '2.7', 'ChainAngle': '120', 'BondSpacing': '12', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Times New Roman', 'iso-8859-1'),
    ),
    'chemdraw_slide': _preset(
        'ChemDraw new slide', 'New Slide',
        "ChemDraw's default for slides (not a journal style)",
        {'BondLength': '30', 'BoldWidth': '4', 'LineWidth': '1.6', 'MarginWidth': '2', 'HashSpacing': '2.7', 'ChainAngle': '120', 'BondSpacing': '15', 'LabelFace': '96', 'LabelSize': '12', 'CaptionFace': '0', 'CaptionSize': '16'},
        label=('Arial', 'iso-8859-1'), caption=('Times New Roman', 'iso-8859-1'),
    ),
    'chemdraw_a4': _preset(
        'ChemDraw new A4 document', 'New A4 Document',
        "ChemDraw's default for an A4 document (not a journal style)",
        {'BondLength': '30', 'BoldWidth': '4', 'LineWidth': '1', 'MarginWidth': '2', 'HashSpacing': '2.7', 'ChainAngle': '120', 'BondSpacing': '12', 'LabelFace': '96', 'LabelSize': '10', 'CaptionFace': '0', 'CaptionSize': '12'},
        label=('Arial', 'iso-8859-1'), caption=('Times New Roman', 'iso-8859-1'),
    ),
})


# Stock sheets that are numerically identical to a listed preset.
_ALIASES = {"J. Mol. Mod. (1 Column)": "j_mol_mod"}


def _as_dict(slug: str) -> dict:
    preset = STYLE_PRESETS[slug]
    return {
        "slug": slug,
        "name": preset["name"],
        "sheet": preset["sheet"],
        "used_by": preset["used_by"],
        "attributes": dict(preset["attributes"]),
        "fonts": {role: list(font) for role, font in preset["fonts"].items()},
    }


def _normalise(text: str) -> str:
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def style_preset_slug(name: str) -> str:
    """Slug of a preset named by slug, display name or style-sheet name (any case)."""
    key = _normalise(str(name or ""))
    if key:
        for alias, slug in _ALIASES.items():
            if key == _normalise(alias):
                return slug
        for slug, preset in STYLE_PRESETS.items():
            if key in {_normalise(slug), _normalise(preset["name"]), _normalise(preset["sheet"])}:
                return slug
    raise ValueError(f"Unknown style preset {name!r}; available: {', '.join(STYLE_PRESETS)}")


def list_style_presets() -> list[dict]:
    """All presets, default first, as plain dictionaries."""
    return [_as_dict(slug) for slug in STYLE_PRESETS]


def style_preset(name: str) -> dict:
    """One preset by slug, display name or style-sheet name (case-insensitive)."""
    return _as_dict(style_preset_slug(name))


def style_preset_bond_length(name: str) -> float:
    return float(STYLE_PRESETS[style_preset_slug(name)]["attributes"]["BondLength"])


# Attributes holding page coordinates, which scale with the bond length.
_POINT_ATTRIBUTES = (
    "p", "BoundingBox", "Head3D", "Tail3D", "Center3D", "MajorAxisEnd3D", "MinorAxisEnd3D",
    "CurvePoints", "CurvePoints3D",
)


def _scaled(value: str, factor: float) -> str:
    try:
        return " ".join(f"{float(n) * factor:.2f}" for n in value.split())
    except ValueError:
        return value


def apply_style_preset(cdxml_text: str, name: str, *, rescale: bool = True) -> str:
    """Write a preset's settings and fonts onto a CDXML document.

    With ``rescale`` every page coordinate (atoms, text, arrows, curves, boxes) is
    scaled to the preset's bond length, and text runs written in the document's
    label or caption font and size take the preset's font and size.  Without it
    only the document settings change, as with ``ApplySettings`` in ChemDraw.
    """
    import xml.etree.ElementTree as ET

    from .style_sheet import apply_style_sheet

    preset = style_preset(name)
    old = ET.fromstring(cdxml_text)
    old_length = float(old.get("BondLength") or 0) or None
    old_fonts = {old.get("LabelFont"): "Label", old.get("CaptionFont"): "Caption"}
    old_sizes = {old.get("LabelSize") or "10", old.get("CaptionSize") or "10"}
    fonts = {role: tuple(font) for role, font in preset["fonts"].items()}
    styled = apply_style_sheet(cdxml_text, {"attributes": preset["attributes"], "fonts": fonts}, rescale=False)
    if not rescale or not old_length:
        return styled
    root = ET.fromstring(styled)
    factor = float(preset["attributes"]["BondLength"]) / old_length
    for element in root.iter():
        for attribute in _POINT_ATTRIBUTES:
            if attribute in element.attrib:
                element.set(attribute, _scaled(element.get(attribute), factor))
        if element.tag != "s":
            continue
        role = old_fonts.get(element.get("font"))
        if role:
            element.set("font", root.get(f"{role}Font"))
        size = element.get("size")
        if size is not None:
            if size in old_sizes or _scaled(size, 1) in {_scaled(v, 1) for v in old_sizes}:
                element.set("size", root.get(f"{role or 'Label'}Size"))
            else:
                element.set("size", _scaled(size, factor).removesuffix(".00"))
    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")


def style_preset_as_manifest_style(name: str) -> dict:
    """A preset as the ``style`` dictionary of ``compose_chemical_figure``."""
    attributes = style_preset(name)["attributes"]
    return {
        "font": STYLE_PRESETS[style_preset_slug(name)]["fonts"]["label"][0],
        "font_size": float(attributes["LabelSize"]),
        "bond_length": float(attributes["BondLength"]),
        "line_width": float(attributes["LineWidth"]),
        "bold_width": float(attributes["BoldWidth"]),
        "hash_spacing": float(attributes["HashSpacing"]),
        "margin_width": float(attributes["MarginWidth"]),
    }
