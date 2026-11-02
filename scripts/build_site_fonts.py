#!/usr/bin/env python3
"""Build the website's two heading fonts from their pinned upstream releases.

Run it after adding a Chinese heading whose characters the trimmed font lacks (tests/test_site.py says
when):

    python -m pip install "fonttools[woff]==4.68.0"
    python scripts/build_site_fonts.py

Trimming a font makes it a Modified Version under the SIL Open Font License. Source Serif reserves the name
"Source", so its trimmed copy is named Skill Serif, in the file, in its name table and in the stylesheet.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import tempfile
import urllib.request
import zipfile
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

LATIN_FILE = "skill-serif-latin.woff2"
CHINESE_FILE = "noto-serif-sc-heading.woff2"

LATIN_SOURCE = {
    "url": "https://github.com/adobe-fonts/source-serif/releases/download/4.005R/source-serif-4.005_Desktop.zip",
    "sha256": "549fdb8f9a682bd06944298621404969f6de77c2e422ff3b8244a1dcd6a0c425",
    "member": "source-serif-4.005_Desktop/VAR/SourceSerif4Variable-Roman.ttf",
}
CHINESE_SOURCE = {
    "url": "https://raw.githubusercontent.com/google/fonts/2e61f4355afd22b801791b0df176065082423b87/"
           "ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
    "sha256": "050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9",
}

# Matches the unicode-range of Skill Serif in site/styles.css.
LATIN_UNICODES = [
    *range(0x00, 0x100), 0x131, 0x152, 0x153, 0x2BB, 0x2BC, 0x2C6, 0x2DA, 0x2DC, 0x304, 0x308, 0x329,
    *range(0x3B1, 0x3B5),  # alpha to delta: the Greek of compound names
    *range(0x2000, 0x2070), 0x20AC, 0x2122, 0x2191, 0x2193, 0x2212, 0x2215, 0xFEFF, 0xFFFD,
]
PUNCTUATION = "—‘’“”…　、。〈〉《》「」『』【】！％（）＋，－：；＝？～"

PAGES = {"zh": ("index.html", "lab/index.html", "404.html"), "en": ("en/index.html", "en/lab/index.html")}


def heading_text(language: str, site: Path = SITE) -> str:
    """Every string the pages set in the heading face: the static h1 and h2, the brand, and what the game fills in."""
    parts = []
    for page in PAGES[language]:
        html = (site / page).read_text(encoding="utf-8")
        parts += re.findall(r"<(?:h1|h2)\b[^>]*>(.*?)</(?:h1|h2)>", html, re.S)
        parts += re.findall(r'class="brand"[^>]*>(.*?)</a>', html, re.S)
    for name in (f"words.{language}.js", f"daily.{language}.js"):
        script = (site / name).read_text(encoding="utf-8")
        parts += re.findall(r'^\s*"(?:name|title|badgesTitle|lockedName)": "(.*)",?$', script, re.M)
        for block in re.findall(r'^\s*"(?:names|modes)": \{(.*?)^\s*\}', script, re.M | re.S):
            parts += re.findall(r'": "(.*)",?$', block, re.M)
    text = unescape(re.sub(r"<[^>]+>|\{\w+\}", "", " ".join(parts)))
    return "".join(sorted(set(text) - set(" \n\t")))


def is_chinese(char: str) -> bool:
    return "㐀" <= char <= "鿿"


def _download(source: dict) -> bytes:
    with urllib.request.urlopen(source["url"], timeout=120) as response:  # noqa: S310 - pinned https URL
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != source["sha256"]:
        raise SystemExit(f'{source["url"]} does not match its pinned sha256 (got {digest})')
    return data


def _rename(font, family: str, postscript: str) -> None:
    """Replace every name a reader or a system sees; the copyright (ID 0) and the licence stay."""
    version = font["name"].getDebugName(5) or ""
    names = {1: family, 2: "Regular", 3: f"{postscript};{version.split(';')[0]}", 4: family, 6: postscript}
    table = font["name"]
    table.names = [record for record in table.names if record.nameID not in (*names, 16, 17, 21, 22, 25)]
    for number, value in names.items():
        table.setName(value, number, 3, 1, 0x409)
    for record in table.names:  # the named instances of a variable font
        if record.nameID >= 256 and "SourceSerif4Variable" in record.toUnicode():
            record.string = record.toUnicode().replace("SourceSerif4Variable", "SkillSerif")


def _instance(source: Path, axes: dict):
    """Fix the weight; the result is saved and read back because the subsetter needs complete tables."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    buffer = io.BytesIO()
    instancer.instantiateVariableFont(TTFont(source), axes).save(buffer)
    buffer.seek(0)
    return TTFont(buffer)


def _subset(font, unicodes: list, features: list) -> None:
    from fontTools import subset

    options = subset.Options(layout_features=features, name_IDs=["*"], name_languages=["*"], hinting=False,
                             notdef_outline=True, glyph_names=False)
    options.drop_tables += ["vhea", "vmtx", "VORG", "DSIG"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)


def _save(font, path: Path) -> None:
    font.flavor = "woff2"
    font.save(path)
    print(f"{path.name}: {path.stat().st_size} bytes, {len(font.getBestCmap())} characters")


def build_latin(source: Path) -> None:
    font = _instance(source, {"wght": 600, "opsz": (24, 24, 60)})
    _subset(font, LATIN_UNICODES, ["case", "ccmp", "kern", "liga", "locl", "mark", "mkmk", "pnum", "tnum"])
    _rename(font, "Skill Serif", "SkillSerif-Semibold")
    _save(font, SITE / "fonts" / LATIN_FILE)


def build_chinese(source: Path) -> None:
    font = _instance(source, {"wght": 600})
    text = "".join(c for c in heading_text("zh") if is_chinese(c)) + PUNCTUATION + " "
    _subset(font, [ord(c) for c in text], ["kern", "locl"])
    _rename(font, "Noto Serif SC Heading", "NotoSerifSC-Heading")
    font["OS/2"].usWeightClass = 600
    _save(font, SITE / "fonts" / CHINESE_FILE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--latin", type=Path, help="SourceSerif4Variable-Roman.ttf, already downloaded")
    parser.add_argument("--chinese", type=Path, help="NotoSerifSC[wght].ttf, already downloaded")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        latin = args.latin
        if latin is None:
            latin = Path(folder) / "latin.ttf"
            with zipfile.ZipFile(io.BytesIO(_download(LATIN_SOURCE))) as bundle:
                latin.write_bytes(bundle.read(LATIN_SOURCE["member"]))
        chinese = args.chinese
        if chinese is None:
            chinese = Path(folder) / "chinese.ttf"
            chinese.write_bytes(_download(CHINESE_SOURCE))
        build_latin(latin)
        build_chinese(chinese)


if __name__ == "__main__":
    main()
