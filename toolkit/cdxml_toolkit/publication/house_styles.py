"""House styles: how a journal, publisher or research group actually draws schemes.

A measurement preset (:mod:`cdxml_toolkit.chemdraw.style_presets`) fixes bond
length, line widths and fonts. A house style is measured from published,
openly licensed figures and adds the drawing conventions on top of one preset:
bold or plain compound numbers, where the yield goes, substrates side by side
or stacked, which groups are written as abbreviations, and colour coding of
substrates and newly formed bonds.

Each style is one JSON card in the ``house_styles`` data folder next to this
module. Cards are validated when they are loaded; an invalid card is an error,
never silently skipped.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..chemdraw.style_presets import STYLE_PRESETS, style_preset, style_preset_slug

DATA_DIR = Path(__file__).with_suffix("")

KINDS = ("journal", "publisher", "group")
REQUIRED_KEYS = ("slug", "kind", "display_name", "base_preset", "measured", "conventions", "evidence")
OPTIONAL_KEYS = ("applies_to", "notes")

# Convention -> allowed values (None is always allowed: "not determined").
CONVENTION_ENUMS: Mapping[str, tuple] = {
    "compound_label_face": ("bold", "plain"),
    "yield_placement": ("under_arrow", "under_product_label", "after_product_label",
                        "after_product_label_parenthesised"),
    "yield_separator": (", ", ": ", " "),
    "conditions_split": ("reagents_above_solvent_below", "all_above", "all_below"),
    "substrate_layout": ("inline_plus", "stacked_plus"),
    "aromatic_rings": ("kekule", "circle"),
    "arrow_style": ("plain", "bold"),
}
CONVENTION_COLORS = ("compound_label_color", "new_bond_color", "highlight_fill", "reagent_text_color")
CONVENTION_BOOLS = ("compound_label_italic_suffix", "show_plus_sign")
CONVENTION_KEYS = (tuple(CONVENTION_ENUMS) + CONVENTION_COLORS + CONVENTION_BOOLS
                   + ("yield_format", "abbreviate_groups", "substrate_colors"))
# Informational entries a card may carry inside conventions; shown, never applied.
CONVENTION_INFO = ("signature_features", "notes")

# Groups that can be contracted to a label: name -> (SMARTS with the attachment atom first,
# expansion SMILES with the attachment atom first, label read left-to-right when the rest of
# the molecule is on the left, label when it is on the right).
ABBREVIATIONS: Mapping[str, tuple[str, str, str, str]] = {
    "NHBoc": ("[NX3;H1][CX3](=[OX1])[OX2][CX4]([CH3])([CH3])[CH3]", "NC(=O)OC(C)(C)C", "NHBoc", "BocHN"),
    "OTBS": ("[OX2][Si]([CH3])([CH3])[CX4]([CH3])([CH3])[CH3]", "O[Si](C)(C)C(C)(C)C", "OTBS", "TBSO"),
    "Ts": ("[SX4](=[OX1])(=[OX1])c1[cH][cH]c([CH3])[cH][cH]1", "S(=O)(=O)c1ccc(C)cc1", "Ts", "Ts"),
    "Boc": ("[CX3](=[OX1])[OX2][CX4]([CH3])([CH3])[CH3]", "C(=O)OC(C)(C)C", "Boc", "Boc"),
    "Bn": ("[CH2]c1[cH][cH][cH][cH][cH]1", "Cc1ccccc1", "Bn", "Bn"),
    "CO2Et": ("[CX3](=[OX1])[OX2][CH2][CH3]", "C(=O)OCC", "CO2Et", "EtO2C"),
    "OAc": ("[OX2][CX3](=[OX1])[CH3]", "OC(C)=O", "OAc", "AcO"),
    "Ph": ("c1[cH][cH][cH][cH][cH]1", "c1ccccc1", "Ph", "Ph"),
    "CO2Me": ("[CX3](=[OX1])[OX2][CH3]", "C(=O)OC", "CO2Me", "MeO2C"),
    "tBu": ("[CX4]([CH3])([CH3])[CH3]", "C(C)(C)C", "tBu", "tBu"),
    "CF3": ("[CX4](F)(F)F", "C(F)(F)F", "CF3", "F3C"),
    "NO2": ("[NX3+](=[OX1])[OX1-]", "[N+](=O)[O-]", "NO2", "O2N"),
    "Ac": ("[CX3](=[OX1])[CH3]", "C(C)=O", "Ac", "Ac"),
    # The ether oxygen only: a methyl ester is CO2Me, never C(=O)-OMe.
    "OMe": ("[OX2;!$([OX2][CX3]=[OX1])][CH3]", "OC", "OMe", "MeO"),
    "OBn": ("[OX2][CH2]c1[cH][cH][cH][cH][cH]1", "OCc1ccccc1", "OBn", "BnO"),
    "Cbz": ("[CX3](=[OX1])[OX2][CH2]c1[cH][cH][cH][cH][cH]1", "C(=O)OCc1ccccc1", "Cbz", "Cbz"),
    "PhthN": ("[NX3]1C(=O)c2[cH][cH][cH][cH]c2C1=O", "N1C(=O)c2ccccc2C1=O", "NPhth", "PhthN"),
    "TMS": ("[Si]([CH3])([CH3])[CH3]", "[Si](C)(C)C", "TMS", "TMS"),
    "Et": ("[CH2][CH3]", "CC", "Et", "Et"),
    "Me": ("[CH3]", "C", "Me", "Me"),
    "OCF3": ("[OX2][CX4](F)(F)F", "OC(F)(F)F", "OCF3", "F3CO"),
    "CN": ("[CX2]#[NX1]", "C#N", "CN", "NC"),
}

# Other spellings accepted in cards.
GROUP_ALIASES: Mapping[str, str] = {"t-Bu": "tBu", "NPhth": "PhthN", "CO2tBu": "Boc"}


def group_name(name: str) -> str:
    """The table name of an abbreviation, resolving accepted spellings."""
    return GROUP_ALIASES.get(name, name)

_SLUG = re.compile(r"^_?[a-z0-9]+(?:_[a-z0-9]+)*$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class HouseStyle:
    slug: str
    kind: str
    display_name: str
    base_preset: str
    measured: dict = field(default_factory=dict)
    conventions: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)
    applies_to: list = field(default_factory=list)

    def convention(self, key: str, default: Any = None) -> Any:
        value = self.conventions.get(key)
        return default if value is None else value

    def as_dict(self) -> dict:
        return {
            "slug": self.slug, "kind": self.kind, "display_name": self.display_name,
            "applies_to": list(self.applies_to), "base_preset": self.base_preset,
            "measured": dict(self.measured), "conventions": dict(self.conventions),
            "evidence": [dict(e) for e in self.evidence],
        }


def validate_card(card: Any, *, source: str = "card") -> HouseStyle:
    """A :class:`HouseStyle` from one card; ValueError listing every problem otherwise."""
    if not isinstance(card, Mapping):
        raise ValueError(f"{source}: a house-style card must be a JSON object")
    errors: list[str] = []
    missing = [key for key in REQUIRED_KEYS if key not in card]
    if missing:
        errors.append(f"missing keys {missing}")
    unknown = sorted(set(card) - set(REQUIRED_KEYS) - set(OPTIONAL_KEYS))
    if unknown:
        errors.append(f"unknown keys {unknown}")
    slug = str(card.get("slug") or "")
    if not _SLUG.match(slug):
        errors.append(f"slug {slug!r} must be snake_case")
    if card.get("kind") not in KINDS:
        errors.append(f"kind {card.get('kind')!r} must be one of {list(KINDS)}")
    if not str(card.get("display_name") or "").strip():
        errors.append("display_name is empty")
    base = None
    try:
        base = style_preset_slug(str(card.get("base_preset") or ""))
    except ValueError:
        errors.append(f"base_preset {card.get('base_preset')!r} is not a measurement preset; "
                      f"available: {', '.join(STYLE_PRESETS)}")
    if not isinstance(card.get("measured", {}), Mapping):
        errors.append("measured must be an object")
    evidence = card.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
    elif not all(isinstance(e, Mapping) and (e.get("doi") or e.get("citation")) for e in evidence):
        errors.append("every evidence entry needs a doi or a citation")
    conventions = card.get("conventions", {})
    if not isinstance(conventions, Mapping):
        errors.append("conventions must be an object")
        conventions = {}
    errors.extend(_convention_errors(conventions))
    if errors:
        raise ValueError(f"{source}: invalid house style: " + "; ".join(errors))
    applies = card.get("applies_to") or []
    return HouseStyle(
        slug=slug, kind=str(card["kind"]), display_name=str(card["display_name"]), base_preset=str(base),
        measured=dict(card.get("measured") or {}), conventions=dict(conventions),
        evidence=[dict(e) for e in evidence], applies_to=list(applies) if isinstance(applies, list) else [applies],
    )


def _convention_errors(conventions: Mapping) -> list[str]:
    errors: list[str] = []
    unknown = sorted(set(conventions) - set(CONVENTION_KEYS) - set(CONVENTION_INFO))
    if unknown:
        errors.append(f"unknown conventions {unknown}")
    for key, allowed in CONVENTION_ENUMS.items():
        value = conventions.get(key)
        if value is not None and value not in allowed:
            errors.append(f"{key} {value!r} must be one of {list(allowed)}")
    for key in CONVENTION_COLORS:
        value = conventions.get(key)
        if value is not None and not (isinstance(value, str) and _HEX.match(value)):
            errors.append(f"{key} {value!r} must be a #RRGGBB colour or null")
    for key in CONVENTION_BOOLS:
        value = conventions.get(key)
        if value is not None and not isinstance(value, bool):
            errors.append(f"{key} must be true, false or null")
    template = conventions.get("yield_format")
    if template is not None and not (isinstance(template, str) and "{value}" in template):
        errors.append("yield_format must be a text containing {value}")
    groups = conventions.get("abbreviate_groups")
    if groups is not None:
        if not isinstance(groups, list):
            errors.append("abbreviate_groups must be a list")
        else:
            bad = [g for g in groups if group_name(g) not in ABBREVIATIONS]
            if bad:
                errors.append(f"abbreviate_groups names unknown groups {bad}; known: {', '.join(ABBREVIATIONS)}")
    colors = conventions.get("substrate_colors")
    if colors is not None and not (isinstance(colors, list) and colors
                                   and all(isinstance(c, str) and _HEX.match(c) for c in colors)):
        errors.append("substrate_colors must be a list of #RRGGBB colours or null")
    return errors


def load_house_styles(directory: str | Path | None = None) -> dict[str, HouseStyle]:
    """Every card in the data folder (or ``directory``), validated, by slug."""
    folder = Path(directory) if directory is not None else DATA_DIR
    styles: dict[str, HouseStyle] = {}
    if not folder.is_dir():
        return styles
    for path in sorted(folder.glob("*.json")):
        try:
            card = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            raise ValueError(f"{path.name}: not valid JSON ({exc})") from exc
        style = validate_card(card, source=path.name)
        if style.slug != path.stem:
            raise ValueError(f"{path.name}: slug {style.slug!r} does not match the file name")
        if style.slug in STYLE_PRESETS:
            raise ValueError(f"{path.name}: slug {style.slug!r} is already a measurement preset")
        styles[style.slug] = style
    return styles


def _normalise(text: str) -> str:
    return "".join(ch for ch in str(text).casefold() if ch.isalnum())


def list_house_styles(directory: str | Path | None = None) -> list[HouseStyle]:
    return list(load_house_styles(directory).values())


def house_style(name: str, directory: str | Path | None = None) -> HouseStyle:
    """One house style by slug or display name (any case)."""
    key = _normalise(name)
    styles = load_house_styles(directory)
    for slug, style in styles.items():
        if key and key in {_normalise(slug), _normalise(style.display_name)}:
            return style
    raise ValueError(f"Unknown house style {name!r}; available: {', '.join(styles) or 'none'}")


def resolve_style(name: str, directory: str | Path | None = None) -> tuple[str, Any]:
    """("preset", preset dict) for a measurement preset, ("house", HouseStyle) for a house style."""
    try:
        return "preset", style_preset(name)
    except ValueError:
        pass
    try:
        houses = ", ".join(load_house_styles(directory)) or "none"
    except ValueError as exc:  # a broken card must not hide the measurement presets
        raise ValueError(f"Unknown style {name!r}; measurement presets: {', '.join(STYLE_PRESETS)}; "
                         f"house styles could not be loaded ({exc})") from None
    try:
        return "house", house_style(name, directory)
    except ValueError:
        raise ValueError(f"Unknown style {name!r}; measurement presets: {', '.join(STYLE_PRESETS)}; "
                         f"house styles: {houses}") from None


def house_style_summary(style: HouseStyle) -> dict:
    """The fields ``cdx.py styles`` lists."""
    return {"slug": style.slug, "kind": style.kind, "base_preset": style.base_preset,
            "display_name": style.display_name, "evidence": len(style.evidence)}
