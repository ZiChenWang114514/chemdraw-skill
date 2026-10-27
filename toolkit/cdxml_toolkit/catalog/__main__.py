"""Regenerate a committed catalog from the installed ChemDraw: ``python -m cdxml_toolkit.catalog``."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import cdxml, chemscript, com, menu

DATA = Path(__file__).with_name("data")
LAYERS = (
    ("chemscript", "chemscript_22_2.json", "reflect the installed ChemScript SDK and join its XML docs"),
    ("com", "com_22_2.json", "read the ChemDraw COM type libraries (ChemDraw is not started)"),
    ("menu", "menu_22_2.json", "start a private ChemDraw and read its menu commands"),
    ("cdxml", "cdxml_model_22_2.json", "scan the CDXML ChemDraw installs and writes, and its binaries"),
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="layer", required=True)
    for name, default, text in LAYERS:
        layer = sub.add_parser(name, help=text)
        layer.add_argument("--output", type=Path, default=DATA / default)
        layer.add_argument("--verified-on", required=True, help='for example "22.2.0/win"')
        layer.add_argument("--replace", action="store_true", help="replace an existing catalog file")
    args = parser.parse_args(argv)

    if args.output.exists() and not args.replace:
        print(f"{args.output} exists; pass --replace to regenerate it", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix=f"{args.layer}-catalog-") as scratch:
        if args.layer == "chemscript":
            module = chemscript
            catalog = chemscript.extract_live(Path(scratch) / "reflection.json", verified_on=args.verified_on)
        elif args.layer == "cdxml":
            module = cdxml
            catalog = cdxml.extract_live(scratch, verified_on=args.verified_on)
        else:
            module = {"com": com, "menu": menu}[args.layer]
            catalog = module.extract_live(verified_on=args.verified_on)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(module.dump(catalog), encoding="utf-8", newline="\n")
    print(f"wrote {args.output}: {catalog['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
