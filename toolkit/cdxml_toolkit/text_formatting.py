"""text_formatting.py — Shared chemical text formatting for ChemDraw CDXML.

Provides functions for building properly formatted <s> (styled text run)
elements in CDXML, handling two chemistry-specific typographic conventions:

1. **Subscript digits in chemical formulas.**
   In chemical notation, digits that follow letters are molecular counts and
   must be rendered as subscripts: "CH3OH" → "CH₃OH", "Pd2(dba)3" → "Pd₂(dba)₃".
   Plain numbers (temperatures "80 °C", durations "2 h", percentages "95%")
   are left as normal text.

2. **Italic prefixes in IUPAC / organic nomenclature.**
   Stereochemical descriptors, positional locants, and heteroatom locants at
   the start of a reagent name are italicised per IUPAC convention:
   "n-BuLi" → "*n*-BuLi", "tert-BuOH" → "*tert*-BuOH", "N-Boc" → "*N*-Boc".

ChemDraw CDXML face codes used:
  - face="96"  (0x60 = Formula)   — normal reagent text
  - face="32"  (0x20 = Subscript) — subscript digits
  - face="2"   (0x02 = Italic)    — italic prefix runs

Previously duplicated across scheme_polisher.py and reaction_from_image.py.
Consolidated here for v0.3.
"""

from __future__ import annotations

import re
from typing import Tuple
from xml.sax.saxutils import escape as xml_escape

# ---------------------------------------------------------------------------
# Regex: letter (or closing paren) followed by one or more digits.
# Matches subscriptable digit groups in chemical formulas.
# Examples:  CH3 → ("H", "3"),  Pd2 → ("d", "2"),  (dba)3 → (")", "3")
# ---------------------------------------------------------------------------
SUBSCRIPT_RE = re.compile(r'([A-Za-z)])(\d+)')

# Keep underscore-prefixed alias for backward compatibility with callers that
# import the private name directly.
_SUBSCRIPT_RE = SUBSCRIPT_RE

# ---------------------------------------------------------------------------
# Italic prefixes recognised in organic chemistry nomenclature.
# Matched at the start of the display name, case-sensitive.
# Longer forms come first so "tert-" is tried before "t-".
# ---------------------------------------------------------------------------
ITALIC_PREFIXES: list[str] = [
    "tert-", "sec-", "iso-",          # long forms first
    "n-", "t-", "s-", "i-",           # single-letter alkyl descriptors
    "o-", "m-", "p-",                 # arene positional (ortho/meta/para)
    "cis-", "trans-",
    "rac-", "meso-",
    "R-", "S-",
    "syn-", "anti-",
    "exo-", "endo-",
    "E-", "Z-",
    "D-", "L-",
    "N-", "O-", "S-", "C-", "P-",    # heteroatom locants (N-Boc, O-alkyl …)
]

_ITALIC_PREFIXES = ITALIC_PREFIXES  # backward-compat alias


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def needs_subscript(text: str) -> bool:
    """Determine whether *text* contains chemical-formula digits that should
    be rendered as subscripts in ChemDraw.

    Returns ``True`` for reagent formulas like ``"CH3OH"``, ``"Cs2CO3"``,
    ``"Pd2(dba)3"`` where trailing digits represent atom counts.

    Returns ``False`` for non-formula text that happens to contain digits:

    * Temperatures — ``"80 °C"``
    * Durations — ``"2 h"``, ``"30 min"``
    * Percentages — ``"95%"``
    * Pure-numeric / unit-only strings — ``"120 °C, 2 h"``

    Examples::

        >>> needs_subscript("Et3N")
        True
        >>> needs_subscript("DMF")
        False
        >>> needs_subscript("80 °C")
        False
    """
    # Temperature (digits before °)
    if re.search(r'\d+\s*°', text):
        return False
    # Duration (digits before h/m at word boundary)
    if re.search(r'\d+\s*[hm](?:\s|$|,)', text):
        return False
    # Percentage
    if re.search(r'\d+\s*%', text):
        return False
    # Pure numeric / unit strings like "reflux", "rt", "120 °C, 2 h"
    if re.fullmatch(r'[\d\s.,°ChmsMinHr/]+', text, re.IGNORECASE):
        return False
    return bool(SUBSCRIPT_RE.search(text))


# Private-name alias for callers that import ``_needs_subscript``.
_needs_subscript = needs_subscript


def split_italic_prefix(text: str) -> Tuple[str, str]:
    """Split *text* into ``(italic_prefix, remainder)`` if it starts with a
    recognised chemistry italic prefix (see :data:`ITALIC_PREFIXES`).

    Returns ``("", text)`` when no prefix matches.

    Examples::

        >>> split_italic_prefix("n-BuLi")
        ('n-', 'BuLi')
        >>> split_italic_prefix("tert-BuOH")
        ('tert-', 'BuOH')
        >>> split_italic_prefix("Cs2CO3")
        ('', 'Cs2CO3')
    """
    for prefix in ITALIC_PREFIXES:
        if text.startswith(prefix):
            return prefix, text[len(prefix):]
    return "", text


_split_italic_prefix = split_italic_prefix  # backward-compat alias


def build_formatted_s_xml(
    text: str,
    font: str = "3",
    size: str = "10",
    color: str = "0",
    italic_font: str | None = None,
) -> str:
    """Build one or more CDXML ``<s>`` elements with correct chemical styling.

    This is the primary text-formatting entry point. It handles:

    1. **Italic prefix** (``n-``, ``tert-``, ``sec-``, ``N-``, …) rendered
       with ``face="2"`` (Italic).
    2. **Subscript digits** after letters/closing-parens rendered with
       ``face="32"`` (Subscript).
    3. **Normal formula text** rendered with ``face="96"`` (Formula).

    Parameters
    ----------
    text : str
        The display text for a reagent or chemical name (e.g. ``"n-BuLi"``,
        ``"Cs2CO3"``, ``"Pd2(dba)3"``).
    font : str
        CDXML font id for normal + subscript runs (default ``"3"`` = Arial).
    size : str
        Font size in points (default ``"10"``).
    color : str
        CDXML color id (default ``"0"`` = black).
    italic_font : str or None
        If given, use this font id for the italic prefix run instead of
        *font*. Useful when the italic style lives in a separate font entry.

    Returns
    -------
    str
        Raw XML string of ``<s>`` elements ready to embed inside a ``<t>``
        element.  Example for ``"n-BuLi"``::

            <s font="3" size="10" color="0" face="2">n-</s>
            <s font="3" size="10" color="0" face="96">BuLi</s>

    Notes
    -----
    The function is XML-safe: all text content is escaped via
    ``xml.sax.saxutils.escape``.
    """
    italic_prefix, rest = split_italic_prefix(text)
    ifont = italic_font if italic_font is not None else font

    parts: list[str] = []

    # ---- italic prefix ----
    if italic_prefix:
        parts.append(
            f'<s font="{ifont}" size="{size}" color="{color}" '
            f'face="2">{xml_escape(italic_prefix)}</s>'
        )

    # ---- remainder with subscript handling ----
    if rest:
        if needs_subscript(rest):
            pos = 0
            for m in SUBSCRIPT_RE.finditer(rest):
                normal_end = m.start(2)
                if pos < normal_end:
                    chunk = xml_escape(rest[pos:normal_end])
                    parts.append(
                        f'<s font="{font}" size="{size}" color="{color}" '
                        f'face="96">{chunk}</s>'
                    )
                digits = xml_escape(m.group(2))
                parts.append(
                    f'<s font="{font}" size="{size}" color="{color}" '
                    f'face="32">{digits}</s>'
                )
                pos = m.end()

            if pos < len(rest):
                chunk = xml_escape(rest[pos:])
                parts.append(
                    f'<s font="{font}" size="{size}" color="{color}" '
                    f'face="96">{chunk}</s>'
                )
        else:
            parts.append(
                f'<s font="{font}" size="{size}" color="{color}" '
                f'face="96">{xml_escape(rest)}</s>'
            )

    return "".join(parts)


# Backward-compatible aliases (used by scheme_polisher and reaction_from_image).
_build_formatted_s_xml = build_formatted_s_xml
build_subscripted_s_xml = build_formatted_s_xml
_build_subscripted_s_xml = build_formatted_s_xml


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    passed = 0
    failed = 0

    def check(label: str, got, expected):
        global passed, failed
        if got == expected:
            print(f"  PASS  {label}")
            passed += 1
        else:
            print(f"  FAIL  {label}")
            print(f"        expected: {expected!r}")
            print(f"        got:      {got!r}")
            failed += 1

    print("text_formatting.py self-test")
    print("=" * 50)

    # --- needs_subscript ---
    check("needs_subscript('CH3OH')", needs_subscript("CH3OH"), True)
    check("needs_subscript('DMF')", needs_subscript("DMF"), False)
    check("needs_subscript('Et3N')", needs_subscript("Et3N"), True)
    check("needs_subscript('Cs2CO3')", needs_subscript("Cs2CO3"), True)
    check("needs_subscript('80 °C')", needs_subscript("80 °C"), False)
    check("needs_subscript('2 h')", needs_subscript("2 h"), False)
    check("needs_subscript('95%')", needs_subscript("95%"), False)

    # --- split_italic_prefix ---
    check("split_italic_prefix('n-BuLi')", split_italic_prefix("n-BuLi"), ("n-", "BuLi"))
    check("split_italic_prefix('Cs2CO3')", split_italic_prefix("Cs2CO3"), ("", "Cs2CO3"))
    check("split_italic_prefix('tert-BuOH')", split_italic_prefix("tert-BuOH"), ("tert-", "BuOH"))
    check("split_italic_prefix('N-Boc')", split_italic_prefix("N-Boc"), ("N-", "Boc"))

    # --- build_formatted_s_xml ---
    xml_et3n = build_formatted_s_xml("Et3N")
    check("build_formatted_s_xml('Et3N') contains <s>",
          "<s " in xml_et3n, True)
    check("build_formatted_s_xml('Et3N') has subscript face",
          'face="32"' in xml_et3n, True)
    check("build_formatted_s_xml('Et3N') has formula face",
          'face="96"' in xml_et3n, True)

    xml_nbuli = build_formatted_s_xml("n-BuLi")
    check("build_formatted_s_xml('n-BuLi') has italic face",
          'face="2"' in xml_nbuli, True)
    check("build_formatted_s_xml('n-BuLi') italic run contains 'n-'",
          'face="2">n-</s>' in xml_nbuli, True)

    xml_dmf = build_formatted_s_xml("DMF")
    check("build_formatted_s_xml('DMF') — no subscript for plain text",
          'face="32"' in xml_dmf, False)

    # --- aliases ---
    check("build_subscripted_s_xml is build_formatted_s_xml",
          build_subscripted_s_xml is build_formatted_s_xml, True)
    check("_build_formatted_s_xml is build_formatted_s_xml",
          _build_formatted_s_xml is build_formatted_s_xml, True)

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)
    print("All tests passed.")
