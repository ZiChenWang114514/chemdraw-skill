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

import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..chemdraw.style_presets import STYLE_PRESETS, style_preset, style_preset_slug

DATA_DIR = Path(__file__).with_suffix("")

KINDS = ("journal", "publisher", "group")
REQUIRED_KEYS = ("slug", "kind", "display_name", "base_preset", "measured", "conventions", "evidence")
OPTIONAL_KEYS = ("applies_to", "notes", "figure_types")

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

# Figure types a card can describe beyond the reaction scheme its top-level conventions cover.
# Each entry is {"conventions": {...}, "signature_features": [...], "crops": ["evidence/..."]}.
FIGURE_TYPES = ("reaction_scheme", "substrate_scope", "mechanism", "catalytic_cycle", "energy_profile",
                "total_synthesis", "retrosynthesis", "structure_panel", "sar_table",
                "optimization_table", "concept_panel", "graphical_abstract", "stereo_model", "derivatization",
                "biosynthesis", "biomolecule", "coordination_complex", "polymer", "markush", "process_route",
                "photophysical_diagram", "assignment_panel", "setup_diagram")
FIGURE_TYPE_KEYS = ("conventions", "signature_features", "crops", "notes")
# Figure-type convention -> a tuple of allowed values, or "color", "colors", "bool" or "text".
# None is always allowed.
FIGURE_CONVENTIONS: Mapping[str, Any] = {
    "curved_arrow_color": "color",
    "curved_arrow_weight": ("thin", "bond", "bold"),
    "show_lone_pairs": "bool",
    "formal_charge_style": ("plain", "circled"),
    "intermediate_label_style": ("bold_number", "bold_roman", "plain_roman", "bold_letter", "int_number", "none"),
    "ts_marker": ("double_dagger", "bracket_double_dagger", "none"),
    "cycle_shape": ("circle", "rounded_rectangle", "open_arc", "none"),
    "cycle_arrow_color": "color",
    "catalyst_color": "color",
    "center_label": "bool",
    "step_names": "bool",
    "energy_unit": ("kcal/mol", "kJ/mol", "eV"),
    "energy_label": ("delta_G", "delta_G_double_dagger", "delta_E", "delta_H"),
    "level_style": ("bars_dashed_connectors", "bars_solid_connectors", "smooth_curve"),
    "pathway_colors": "colors",
    "scope_layout": ("grid", "grid_with_core", "table"),
    "variation_color": "color",
    "yield_format": "text",
    "selectivity_format": "text",
    "conditions_position": ("scheme_on_top", "footnote", "both"),
    "step_label_style": ("letter_under_arrow", "letter_above_arrow", "roman", "numbered", "footnote", "none"),
    "retro_arrow": ("open_double", "none"),
    "disconnection_mark": ("wavy_line", "colored_bond", "dashed_line", "none"),
    "disconnection_color": "color",
    "step_count_shown": "bool",
    "highlight_fill": "color",
    "table_style": ("horizontal_rules", "grid", "none"),
    "activity_format": "text",
    "entry_highlight": ("bold_row", "shaded_row", "boxed_row", "none"),
    "footnote_style": ("superscript_letters", "superscript_numbers", "none"),
    "panel_label_style": ("bold_lowercase", "bold_uppercase", "parenthesised_lowercase", "none"),
    "comparison_layout": ("stacked_rows", "side_by_side"),
    "this_work_color": "color",
    "background_fill": "color",
    "model_style": ("chair", "newman", "zimmerman_traxler", "perspective_3d", "fischer", "sawhorse"),
    "derivatization_layout": ("radial", "grid", "linear"),
    "enzyme_label_style": ("italic_above_arrow", "boxed", "plain", "colored"),
    "sugar_projection": ("haworth", "chair", "zigzag"),
    "peptide_style": ("full_structure", "three_letter", "one_letter"),
    "dative_bond_style": ("arrow", "line", "dashed"),
    "metal_color": "color",
    "repeat_bracket": ("square", "round"),
    "r_group_style": ("superscript_number", "subscript_number", "plain_number"),
    "scale_shown": "bool",
    "numbering_style": ("atom_numbers", "ring_locants", "none"),
    "shift_color": "color",
}
# Which convention keys each figure type accepts.
FIGURE_TYPE_CONVENTIONS: Mapping[str, tuple[str, ...]] = {
    "reaction_scheme": ("yield_format", "selectivity_format", "highlight_fill", "variation_color"),
    "substrate_scope": ("scope_layout", "variation_color", "yield_format", "selectivity_format",
                        "conditions_position", "highlight_fill"),
    "mechanism": ("curved_arrow_color", "curved_arrow_weight", "show_lone_pairs", "formal_charge_style",
                  "intermediate_label_style", "ts_marker", "highlight_fill"),
    "catalytic_cycle": ("cycle_shape", "cycle_arrow_color", "catalyst_color", "center_label", "step_names",
                        "intermediate_label_style", "curved_arrow_color", "highlight_fill"),
    "energy_profile": ("energy_unit", "energy_label", "level_style", "pathway_colors", "ts_marker",
                       "intermediate_label_style"),
    "total_synthesis": ("step_label_style", "step_count_shown", "yield_format", "highlight_fill",
                        "variation_color"),
    "retrosynthesis": ("retro_arrow", "disconnection_mark", "disconnection_color", "highlight_fill",
                       "step_count_shown"),
    "structure_panel": ("highlight_fill", "variation_color", "intermediate_label_style"),
    "sar_table": ("table_style", "activity_format", "variation_color", "highlight_fill"),
    "optimization_table": ("table_style", "entry_highlight", "footnote_style", "yield_format",
                           "selectivity_format"),
    "concept_panel": ("panel_label_style", "comparison_layout", "this_work_color", "background_fill",
                      "highlight_fill", "variation_color"),
    "graphical_abstract": ("background_fill", "highlight_fill", "variation_color", "this_work_color"),
    "stereo_model": ("model_style", "ts_marker", "highlight_fill", "variation_color"),
    "derivatization": ("derivatization_layout", "yield_format", "highlight_fill", "variation_color"),
    "biosynthesis": ("enzyme_label_style", "highlight_fill", "variation_color", "intermediate_label_style"),
    "biomolecule": ("sugar_projection", "peptide_style", "highlight_fill", "variation_color"),
    "coordination_complex": ("dative_bond_style", "metal_color", "highlight_fill", "formal_charge_style"),
    "polymer": ("repeat_bracket", "highlight_fill", "variation_color"),
    "markush": ("r_group_style", "variation_color", "table_style"),
    "process_route": ("step_label_style", "step_count_shown", "yield_format", "scale_shown", "highlight_fill"),
    "photophysical_diagram": ("energy_unit", "level_style", "pathway_colors"),
    "assignment_panel": ("numbering_style", "shift_color", "highlight_fill"),
    "setup_diagram": ("background_fill", "highlight_fill"),
}
# Figure-type conventions the drawing tools apply; the rest guide the agent and are listed in reports.
APPLIED_FIGURE_CONVENTIONS: Mapping[str, tuple[str, ...]] = {
    "mechanism": ("curved_arrow_color", "curved_arrow_weight"),
    "catalytic_cycle": ("cycle_arrow_color",),
    "structure_panel": ("highlight_fill", "variation_color", "intermediate_label_style"),
}

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
    "N3": ("[NX2]=[NX2+]=[NX1-]", "N=[N+]=[N-]", "N3", "N3"),
    "OTMS": ("[OX2][Si]([CH3])([CH3])[CH3]", "O[Si](C)(C)C", "OTMS", "TMSO"),
    "OTf": ("[OX2][SX4](=[OX1])(=[OX1])[CX4](F)(F)F", "OS(=O)(=O)C(F)(F)F", "OTf", "TfO"),
    "Tf": ("[SX4](=[OX1])(=[OX1])[CX4](F)(F)F", "S(=O)(=O)C(F)(F)F", "Tf", "Tf"),
    "OTs": ("[OX2][SX4](=[OX1])(=[OX1])c1[cH][cH]c([CH3])[cH][cH]1", "OS(=O)(=O)c1ccc(C)cc1", "OTs", "TsO"),
    "Ms": ("[SX4](=[OX1])(=[OX1])[CH3]", "S(C)(=O)=O", "Ms", "Ms"),
    "OMs": ("[OX2][SX4](=[OX1])(=[OX1])[CH3]", "OS(C)(=O)=O", "OMs", "MsO"),
    "Bpin": ("[BX3]1[OX2][CX4]([CH3])([CH3])[CX4]([CH3])([CH3])[OX2]1", "B1OC(C)(C)C(C)(C)O1", "Bpin", "Bpin"),
    "TIPS": ("[Si]([CH1]([CH3])[CH3])([CH1]([CH3])[CH3])[CH1]([CH3])[CH3]",
             "[Si](C(C)C)(C(C)C)C(C)C", "TIPS", "TIPS"),
    "OTIPS": ("[OX2][Si]([CH1]([CH3])[CH3])([CH1]([CH3])[CH3])[CH1]([CH3])[CH3]",
              "O[Si](C(C)C)(C(C)C)C(C)C", "OTIPS", "TIPSO"),
    "Bz": ("[CX3](=[OX1])c1[cH][cH][cH][cH][cH]1", "C(=O)c1ccccc1", "Bz", "Bz"),
    "OBz": ("[OX2][CX3](=[OX1])c1[cH][cH][cH][cH][cH]1", "OC(=O)c1ccccc1", "OBz", "BzO"),
    "Piv": ("[CX3](=[OX1])[CX4]([CH3])([CH3])[CH3]", "C(=O)C(C)(C)C", "Piv", "Piv"),
    "nBu": ("[CH2][CH2][CH2][CH3]", "CCCC", "nBu", "nBu"),
    "iPr": ("[CH1]([CH3])[CH3]", "C(C)C", "iPr", "iPr"),
    "NMe2": ("[NX3;H0;!$(N[CX3]=[OX1])]([CH3])[CH3]", "N(C)C", "NMe2", "Me2N"),
}

# Other spellings accepted in cards.
GROUP_ALIASES: Mapping[str, str] = {"t-Bu": "tBu", "NPhth": "PhthN", "CO2tBu": "Boc", "n-Bu": "nBu",
                                     "Bu": "nBu", "i-Pr": "iPr", "BPin": "Bpin", "OSiMe3": "OTMS"}


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
    figure_types: dict = field(default_factory=dict)

    def convention(self, key: str, default: Any = None) -> Any:
        value = self.conventions.get(key)
        return default if value is None else value

    def figure_convention(self, figure_type: str, key: str, default: Any = None) -> Any:
        """A convention of one figure type (``mechanism``, ``catalytic_cycle`` ...), or ``default``."""
        section = self.figure_types.get(figure_type) or {}
        value = (section.get("conventions") or {}).get(key)
        return default if value is None else value

    def as_dict(self) -> dict:
        return {
            "slug": self.slug, "kind": self.kind, "display_name": self.display_name,
            "applies_to": list(self.applies_to), "base_preset": self.base_preset,
            "measured": dict(self.measured), "conventions": dict(self.conventions),
            "evidence": [dict(e) for e in self.evidence],
            "figure_types": json.loads(json.dumps(self.figure_types)),
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
    figure_types = card.get("figure_types") or {}
    errors.extend(_figure_type_errors(figure_types, evidence if isinstance(evidence, list) else []))
    if errors:
        raise ValueError(f"{source}: invalid house style: " + "; ".join(errors))
    applies = card.get("applies_to") or []
    return HouseStyle(
        slug=slug, kind=str(card["kind"]), display_name=str(card["display_name"]), base_preset=str(base),
        measured=dict(card.get("measured") or {}), conventions=dict(conventions),
        evidence=[dict(e) for e in evidence], applies_to=list(applies) if isinstance(applies, list) else [applies],
        figure_types=json.loads(json.dumps(figure_types)),
    )


def _figure_type_errors(figure_types: Any, evidence: list) -> list[str]:
    if not isinstance(figure_types, Mapping):
        return ["figure_types must be an object"]
    errors: list[str] = []
    crops = {str(e.get("crop")) for e in evidence if isinstance(e, Mapping) and e.get("crop")}
    for name, section in figure_types.items():
        where = f"figure_types.{name}"
        if name not in FIGURE_TYPES:
            errors.append(f"{where}: unknown figure type; known: {', '.join(FIGURE_TYPES)}")
            continue
        if not isinstance(section, Mapping):
            errors.append(f"{where} must be an object")
            continue
        unknown = sorted(set(section) - set(FIGURE_TYPE_KEYS))
        if unknown:
            errors.append(f"{where}: unknown keys {unknown}")
        section_crops = section.get("crops")
        if not isinstance(section_crops, list) or not section_crops:
            errors.append(f"{where}.crops must list the evidence crops it was read from")
        else:
            missing = [c for c in section_crops if c not in crops]
            if missing:
                errors.append(f"{where}.crops {missing} are not crops of the evidence list")
        features = section.get("signature_features", [])
        if not isinstance(features, list) or not all(isinstance(f, str) for f in features):
            errors.append(f"{where}.signature_features must be a list of texts")
        conventions = section.get("conventions", {})
        if not isinstance(conventions, Mapping):
            errors.append(f"{where}.conventions must be an object")
            continue
        allowed = FIGURE_TYPE_CONVENTIONS[name]
        for key, value in conventions.items():
            if key not in allowed:
                errors.append(f"{where}: convention {key!r} does not apply; allowed: {', '.join(allowed)}")
                continue
            if value is None:
                continue
            kind = FIGURE_CONVENTIONS[key]
            if isinstance(kind, tuple) and value not in kind:
                errors.append(f"{where}.{key} {value!r} must be one of {list(kind)}")
            elif kind == "color" and not (isinstance(value, str) and _HEX.match(value)):
                errors.append(f"{where}.{key} {value!r} must be a #RRGGBB colour")
            elif kind == "colors" and not (isinstance(value, list) and value
                                           and all(isinstance(c, str) and _HEX.match(c) for c in value)):
                errors.append(f"{where}.{key} must be a list of #RRGGBB colours")
            elif kind == "bool" and not isinstance(value, bool):
                errors.append(f"{where}.{key} must be true or false")
            elif kind == "text" and not isinstance(value, str):
                errors.append(f"{where}.{key} must be a text")
    return errors


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


def _style_suggestions(name: str, choices: Iterable[str]) -> str:
    options = [str(c) for c in choices if str(c).strip()]
    needle = str(name or "").strip().lower()
    if not options or not needle:
        return ""
    sub_hits = [c for c in options if needle in c.lower() or c.lower() in needle]
    lower_map: dict[str, str] = {}
    for opt in options:
        lower_map.setdefault(opt.lower(), opt)
    close_hits = [
        lower_map[m]
        for m in difflib.get_close_matches(needle, list(lower_map), n=4, cutoff=0.5)
    ]
    suggestions = list(dict.fromkeys([*sub_hits, *close_hits]))[:5]
    return f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""


def house_style(name: str, directory: str | Path | None = None) -> HouseStyle:
    """One house style by slug or display name (any case)."""
    key = _normalise(name)
    styles = load_house_styles(directory)
    for slug, style in styles.items():
        if key and key in {_normalise(slug), _normalise(style.display_name)}:
            return style
    hint = _style_suggestions(name, styles)
    raise ValueError(f"Unknown house style {name!r}; available: {', '.join(styles) or 'none'}.{hint}")


def resolve_style(name: str, directory: str | Path | None = None) -> tuple[str, Any]:
    """("preset", preset dict) for a measurement preset, ("house", HouseStyle) for a house style."""
    try:
        return "preset", style_preset(name)
    except ValueError:
        pass
    try:
        house_dict = load_house_styles(directory)
        houses = ", ".join(house_dict) or "none"
    except ValueError as exc:  # a broken card must not hide the measurement presets
        hint = _style_suggestions(name, STYLE_PRESETS)
        raise ValueError(
            f"Unknown style {name!r}; measurement presets: {', '.join(STYLE_PRESETS)}; "
            f"house styles could not be loaded ({exc}).{hint}"
        ) from None
    try:
        return "house", house_style(name, directory)
    except ValueError:
        hint = _style_suggestions(name, [*STYLE_PRESETS, *house_dict])
        raise ValueError(
            f"Unknown style {name!r}; measurement presets: {', '.join(STYLE_PRESETS)}; "
            f"house styles: {houses}.{hint}"
        ) from None


def house_style_summary(style: HouseStyle) -> dict:
    """The fields ``cdx.py styles`` lists."""
    return {"slug": style.slug, "kind": style.kind, "base_preset": style.base_preset,
            "display_name": style.display_name, "evidence": len(style.evidence),
            "figure_types": sorted(style.figure_types)}
