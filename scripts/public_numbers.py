"""Counts that the README, guide and website quote, taken from the repository itself.

    cdx.py py scripts/public_numbers.py            # print the counts
    cdx.py py scripts/public_numbers.py --check    # list every quoted number that is wrong

Each claim is a pattern with one number in it and the count it must equal. A page that
quotes a number in one of these forms is checked; nothing is rewritten.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "showcase" / "house-styles"
PAGES = ("README.md", "README.zh-cn.md", "docs/guide.md", "docs/guide.zh-cn.md", "docs/zh-cn.md",
         "site/index.html", "site/en/index.html", "toolkit/README.md")


def counts() -> dict[str, int]:
    from cdxml_toolkit.chemdraw.style_presets import list_style_presets
    from cdxml_toolkit.mcp_runtime import tool_registry
    from cdxml_toolkit.publication.house_styles import list_house_styles
    from cdxml_toolkit.reaction_calculator import hazards

    return {
        "house_styles": len(list_house_styles()),
        "style_presets": len(list_style_presets()),
        "evidence_figures": sum(1 for _ in SHOWCASE.glob("*/evidence/*.png")),
        "replicas": sum(1 for _ in SHOWCASE.glob("*/replica/*/CASE.md")),
        "safety_entries": len(hazards.entries()),
        "tools_full": len(tool_registry.build_registry("full")),
        "tools_default": len(tool_registry.build_registry(tool_registry.DEFAULT_PROFILE)),
    }


# (pattern with one captured number, count name). Both languages of a claim sit together.
CLAIMS = (
    (r"(\d+) (?:empirical )?(?:journal (?:&amp; |and )?group )?house styles", "house_styles"),
    (r"(\d+) 个(?:实测)?(?:期刊与课题组)?画法风格", "house_styles"),
    # "28 cards + 4 presets" is the gallery's own count of preset renders, a different number.
    (r"(?<!cards \+ )(?<!\d)(\d+) (?:ChemDraw |measurement )?presets\b", "style_presets"),
    (r"(\d+) 个 ChemDraw 预设", "style_presets"),
    (r"(\d+) openly licensed figures", "evidence_figures"),
    (r"(\d+) 张开放许可插图", "evidence_figures"),
    (r"(\d+) (?:literature replicas|published figures|more redrawn figures|redraws)", "replicas"),
    (r"(\d+) (?:个文献复现|张已发表)", "replicas"),
    (r"(\d+)-(?:entry|reagent) (?:GHS |reagent )?safety reminders", "safety_entries"),
    (r"(\d+) common solvents", "safety_entries"),
)


def wrong_claims(numbers: dict[str, int] | None = None, pages=PAGES) -> list[str]:
    numbers = numbers or counts()
    wrong = []
    for name in pages:
        text = (ROOT / name).read_text(encoding="utf-8")
        for pattern, key in CLAIMS:
            for match in re.finditer(pattern, text):
                if int(match.group(1)) != numbers[key]:
                    wrong.append(f"{name}: '{match.group(0)}' but {key} is {numbers[key]}")
    return wrong


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    numbers = counts()
    if not args.check:
        print(json.dumps(numbers, indent=2))
        return 0
    wrong = wrong_claims(numbers)
    print("\n".join(wrong) or "every quoted number matches the repository")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
