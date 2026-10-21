"""
constants.py -- Centralized constants for chem-tools v0.3.

All hardcoded magic numbers that were previously scattered across individual
tool scripts are collected here.  Each constant has a comment noting its
purpose and original source file(s).

Sections:
  1. ACS Document 1996 style constants
  2. ACS_STYLE dict and CDXML_HEADER template string
  3. LCMS analysis constants
  4. Mass matching constants
  5. Layout constants (reaction_cleanup gaps)
  6. Image / structure constants
"""

# ============================================================================
# 1. ACS Document 1996 style constants
# ============================================================================

# Bond length -- float for geometry calculations
# Originally in: alignment.py, scheme_polisher_v2.py, coord_normalizer.py,
#   reaction_from_image.py, reaction_cleanup.py (~line 772), scheme_aligner.py (~line 146)
ACS_BOND_LENGTH = 14.40

# Bond length -- string for CDXML XML attributes
# Originally in: cdxml_builder.py, chemscript_bridge.py, eln_enrichment.py,
#   reactant_heuristic.py, reaction_from_image.py (CDXML header)
ACS_BOND_LENGTH_STR = "14.40"

# Chain angle -- float for calculations
# Originally in: cdxml_builder.py, chemscript_bridge.py
ACS_CHAIN_ANGLE = 120

# Chain angle -- string for CDXML XML attributes
# Originally in: cdxml_builder.py, chemscript_bridge.py
ACS_CHAIN_ANGLE_STR = "120"

# Font table ID for Arial (ChemDraw font table index)
# Originally in: cdxml_builder.py, scheme_polisher_v2.py
ACS_LABEL_FONT = "3"

# Label size in points (atom labels)
# Originally in: cdxml_builder.py, scheme_polisher_v2.py
ACS_LABEL_SIZE = "10"

# Label face: 96 = bold (ChemDraw encoding)
# Originally in: cdxml_builder.py, scheme_polisher_v2.py
ACS_LABEL_FACE = "96"

# Caption size in points (reaction conditions text)
# Originally in: cdxml_builder.py
ACS_CAPTION_SIZE = "10"

# Caption face: 0 = plain
# Originally in: cdxml_builder.py, chemscript_bridge.py
ACS_CAPTION_FACE = "0"

# Line width in points
# Originally in: cdxml_builder.py, chemscript_bridge.py
ACS_LINE_WIDTH = "0.60"

# Bold bond width in points
# Originally in: cdxml_builder.py, chemscript_bridge.py, scheme_polisher_v2.py
ACS_BOLD_WIDTH = "2"

# Bond spacing (percentage, ChemDraw internal units)
# Originally in: cdxml_builder.py, scheme_polisher_v2.py
ACS_BOND_SPACING = "18"

# Hash spacing (dashed bond dash gap) in points
# Originally in: cdxml_builder.py, chemscript_bridge.py, scheme_polisher_v2.py
ACS_HASH_SPACING = "2.50"

# Margin width in points
# Originally in: cdxml_builder.py, chemscript_bridge.py, scheme_polisher_v2.py
ACS_MARGIN_WIDTH = "1.60"


# ============================================================================
# 2. ACS_STYLE dict and CDXML_HEADER template
# ============================================================================

# Complete ACS Document 1996 style dict -- all values are strings for direct
# use as XML attributes.  Superset of chemscript_bridge.ACS_STYLE_ATTRS and
# scheme_polisher_v2.ACS_SETTINGS.
# Originally in: chemscript_bridge.py (ACS_STYLE_ATTRS), scheme_polisher_v2.py (ACS_SETTINGS)
ACS_STYLE = {
    "BondLength": ACS_BOND_LENGTH_STR,
    "ChainAngle": ACS_CHAIN_ANGLE_STR,
    "BoldWidth": ACS_BOLD_WIDTH,
    "LineWidth": ACS_LINE_WIDTH,
    "MarginWidth": ACS_MARGIN_WIDTH,
    "HashSpacing": ACS_HASH_SPACING,
    "BondSpacing": ACS_BOND_SPACING,
    "LabelFont": ACS_LABEL_FONT,
    "LabelSize": ACS_LABEL_SIZE,
    "LabelFace": ACS_LABEL_FACE,
    "CaptionFont": ACS_LABEL_FONT,
    "CaptionSize": ACS_CAPTION_SIZE,
    "CaptionFace": ACS_CAPTION_FACE,
}

# Full CDXML document header template with ACS Document 1996 style.
# Contains {bbox} placeholder for the document bounding box.
# Originally in: cdxml_builder.py (_CDXML_HEADER), reaction_from_image.py (_CDXML_HEADER)
CDXML_HEADER = """\
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >
<CDXML
 CreationProgram="ChemDraw 16.0.0.82"
 BoundingBox="{bbox}"
 WindowPosition="-2147483648 -2147483648"
 WindowSize="-2147483648 -2147483648"
 FractionalWidths="yes"
 InterpretChemically="yes"
 ShowAtomQuery="yes"
 ShowAtomStereo="no"
 ShowAtomEnhancedStereo="yes"
 ShowAtomNumber="no"
 ShowResidueID="no"
 ShowBondQuery="yes"
 ShowBondRxn="yes"
 ShowBondStereo="no"
 ShowTerminalCarbonLabels="no"
 ShowNonTerminalCarbonLabels="no"
 HideImplicitHydrogens="no"
 LabelFont="{label_font}"
 LabelSize="{label_size}"
 LabelFace="{label_face}"
 CaptionFont="{label_font}"
 CaptionSize="{caption_size}"
 HashSpacing="{hash_spacing}"
 MarginWidth="{margin_width}"
 LineWidth="{line_width}"
 BoldWidth="{bold_width}"
 BondLength="{bond_length}"
 BondSpacing="{bond_spacing}"
 ChainAngle="{chain_angle}"
 LabelJustification="Auto"
 CaptionJustification="Left"
 AminoAcidTermini="HOH"
 ShowSequenceTermini="yes"
 ShowSequenceBonds="yes"
 ResidueWrapCount="40"
 ResidueBlockCount="10"
 ResidueZigZag="yes"
 NumberResidueBlocks="no"
 PrintMargins="36 36 36 36"
 ChemPropName=""
 ChemPropFormula="Chemical Formula: "
 ChemPropExactMass="Exact Mass: "
 ChemPropMolWt="Molecular Weight: "
 ChemPropMOverZ="m/z: "
 ChemPropAnalysis="Elemental Analysis: "
 ChemPropBoilingPt="Boiling Point: "
 ChemPropMeltingPt="Melting Point: "
 ChemPropCritTemp="Critical Temp: "
 ChemPropCritPres="Critical Pres: "
 ChemPropCritVol="Critical Vol: "
 ChemPropGibbs="Gibbs Energy: "
 ChemPropLogP="Log P: "
 ChemPropMR="MR: "
 ChemPropHenry="Henry&apos;s Law: "
 ChemPropEForm="Heat of Form: "
 ChemProptPSA="tPSA: "
 ChemPropCLogP="CLogP: "
 ChemPropCMR="CMR: "
 ChemPropLogS="LogS: "
 ChemPropPKa="pKa: "
 ChemPropID=""
 color="0"
 bgcolor="1"
 RxnAutonumberStart="1"
 RxnAutonumberConditions="no"
 RxnAutonumberStyle="Roman"
 RxnAutonumberFormat="(#)"
><colortable>
<color r="1" g="1" b="1"/>
<color r="0" g="0" b="0"/>
<color r="1" g="0" b="0"/>
<color r="1" g="1" b="0"/>
<color r="0" g="1" b="0"/>
<color r="0" g="1" b="1"/>
<color r="0" g="0" b="1"/>
<color r="1" g="0" b="1"/>
</colortable><fonttable>
<font id="{label_font}" charset="iso-8859-1" name="Arial"/>
</fonttable>"""

# Minimal CDXML wrapper for single-fragment operations (ChemScript, etc.)
# Originally in: alignment.py (sp_fragment_to_cdxml), eln_enrichment.py, reactant_heuristic.py
CDXML_MINIMAL_HEADER = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n'
    '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
    '<CDXML BondLength="' + ACS_BOND_LENGTH_STR + '">'
)

# CDXML closing tag
# Originally in: cdxml_builder.py, reaction_from_image.py
CDXML_FOOTER = "</CDXML>"


# ============================================================================
# 3. LCMS analysis constants
# ============================================================================

# Default RT matching tolerance in minutes for cross-file peak matching
# Originally in: multi_lcms_analyzer.py (--rt-tolerance default)
LCMS_RT_TOLERANCE = 0.02

# Default m/z clustering tolerance in Da for ion merging
# Originally in: multi_lcms_analyzer.py (--mz-tolerance default)
LCMS_MZ_TOLERANCE = 0.5

# Fraction change threshold for increasing/decreasing trend classification
# Originally in: multi_lcms_analyzer.py (--trend-threshold default)
LCMS_TREND_THRESHOLD = 0.2

# Default minimum area% for a compound to appear in the reaction summary
# Originally in: multi_lcms_analyzer.py (--min-summary-area default)
LCMS_MIN_SUMMARY_AREA = 2.0

# Column boundary x-coordinate (half of 612pt letter page width) for
# two-column MS/UV panel parsing in MassLynx PDF reports.
# Originally in: lcms_analyzer.py (computed as page_width / 2.0)
LCMS_COLUMN_BOUNDARY = 306.0

# MS axis tick values to exclude when extracting m/z labels
# Originally in: lcms_analyzer.py (_MS_AXIS_TICKS)
LCMS_MS_AXIS_TICKS = {500.0, 1000.0}

# UV axis tick values to exclude when extracting wavelength labels
# Originally in: lcms_analyzer.py (_UV_AXIS_TICKS)
LCMS_UV_AXIS_TICKS = {150.0, 200.0, 250.0, 300.0, 350.0, 400.0}

# UV wavelength valid range (nm) for lambda-max extraction
# Originally in: lcms_analyzer.py (_parse_uv_from_words, line ~408)
LCMS_UV_WAVELENGTH_MIN = 150.0
LCMS_UV_WAVELENGTH_MAX = 400.0


# ============================================================================
# 4. Mass matching constants
# ============================================================================

# MW tolerance in Da for matching CSV reagents to scheme fragments
# Originally in: eln_enrichment.py (best_delta threshold, lines ~306 and ~347)
MW_MATCH_TOLERANCE = 2.0

# Loose MW tolerance in Da for matching substrate fragment to CSV row
# Originally in: eln_enrichment.py (substrate MW match, line ~689)
MW_MATCH_TOLERANCE_LOOSE = 5.0

# MW tolerance in Da for matching species to CSV rows in procedure_writer
# Originally in: procedure_writer.py (MASS_TOLERANCE, line ~69)
MASS_TOLERANCE = 1.5

# Minimum area% for a peak to be reported in LCMS characterization/notes
# Originally in: procedure_writer.py (MIN_REPORT_AREA_PCT, line ~70)
MIN_REPORT_AREA_PCT = 20.0

# Minimum area% for an unidentified compound to be counted as "significant"
# Originally in: procedure_writer.py (hardcoded 2.0 in tracking summary, line ~1990)
MIN_SIGNIFICANT_AREA = 2.0


# ============================================================================
# 5. Layout constants (from reaction_cleanup.py)
# ============================================================================

# Gap in points from arrow to bottom of above-arrow objects (base case)
# Originally in: reaction_cleanup.py (ABOVE_GAP in most approaches, line ~457)
LAYOUT_ABOVE_GAP = 8.0

# Gap in points from arrow to top of below-arrow objects
# Originally in: reaction_cleanup.py (BELOW_GAP in all approaches, line ~458)
LAYOUT_BELOW_GAP = 4.0

# Extra gap for fragments with hanging NH/PH labels (N or P at bottom with <=2 bonds)
# Originally in: reaction_cleanup.py (HANGING_GAP, line ~899)
LAYOUT_HANGING_LABEL_GAP = 16.0

# Gap in points between multiple fragments on the same side (arrow_driven approach)
# Originally in: reaction_cleanup.py (INTER_GAP, line ~523)
LAYOUT_INTER_FRAGMENT_GAP = 8.0

# Gap between molecule edge and arrow tip, in multiples of bond length (chemdraw_mimic)
# Originally in: reaction_cleanup.py (FRAG_GAP_BONDS, line ~774)
LAYOUT_FRAG_GAP_BONDS = 1.0

# Gap between multiple reactants, in multiples of bond length (chemdraw_mimic)
# Originally in: reaction_cleanup.py (INTER_GAP_BONDS, line ~775)
LAYOUT_INTER_GAP_BONDS = 0.8


# ============================================================================
# 6. Image / structure constants
# ============================================================================

# Reduced bond length for condition structures rendered above/below the arrow
# (smaller than ACS_BOND_LENGTH so they don't overwhelm the scheme)
# Originally in: reaction_from_image.py (EXPAND_SCALE_BOND, line ~420)
EXPAND_SCALE_BOND = 10.0
