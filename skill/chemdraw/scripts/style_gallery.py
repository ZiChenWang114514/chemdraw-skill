"""Draw one demo reaction in every measurement preset and every house style.

Run with ``cdx.py py <skill>/scripts/style_gallery.py --output-dir NEW_DIR``. The demo is a
Suzuki coupling of methyl 4-bromobenzoate with 4-methoxyphenylboronic acid, with conditions
and a yield. Each style gives one editable CDXML file; ``index.md`` lists them. Nothing is
rendered: open or render the files natively to compare the styles.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEMO = {
    "species": [
        {"id": "ArBr", "smiles": "COC(=O)c1ccc(Br)cc1", "label": "1"},
        {"id": "ArB", "smiles": "COc1ccc(B(O)O)cc1", "label": "2"},
        {"id": "P", "smiles": "COC(=O)c1ccc(-c2ccc(OC)cc2)cc1", "label": "3"},
    ],
    "steps": [{"substrates": ["ArBr", "ArB"], "products": ["P"],
               "above": ["Pd(PPh3)4 (5 mol%)", "K2CO3 (2 equiv)"], "below": ["dioxane/H2O, 90 °C, 12 h"],
               "yield": "85%"}],
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", required=True, help="a new or empty folder")
    args = parser.parse_args(argv)

    from cdxml_toolkit.chemdraw.style_presets import list_style_presets
    from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
    from cdxml_toolkit.publication.house_styles import list_house_styles

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; give a new folder")
    styles = [("preset", p["slug"], p["name"]) for p in list_style_presets()]
    styles += [("house", h.slug, h.display_name) for h in list_house_styles()]
    lines = ["# Style gallery", "", "One Suzuki coupling drawn in each style.", "",
             "| Kind | Style | Name | File | Notes |", "| --- | --- | --- | --- | --- |"]
    failed = 0
    for kind, slug, name in styles:
        target = out / f"{kind}-{slug}.cdxml"
        report = draw_figure({**json.loads(json.dumps(DEMO)), "style": slug}, str(target))
        if not report.get("ok"):
            failed += 1
            lines.append(f"| {kind} | {slug} | {name} | (failed) | {'; '.join(report.get('errors', []))} |")
            continue
        applied = ", ".join(report["style"].get("applied", [])) or "preset only"
        lines.append(f"| {kind} | {slug} | {name} | {target.name} | {applied} |")
    (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not failed, "output_dir": str(out), "drawn": len(styles) - failed,
                      "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
