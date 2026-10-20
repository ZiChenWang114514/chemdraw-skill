from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image

from cdxml_toolkit.mcp_runtime import mcp_server, official_overrides


def as_dict(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def require_ok(result, operation: str):
    data = as_dict(result)
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"{operation} failed: {data}")
    return data


def render_with_timeout(source: Path, destination: Path):
    outcome = mcp_server._run_worker(
        "render_to_png",
        [str(source)],
        {"output_path": str(destination)},
        timeout_seconds=75,
    )
    if not outcome.get("ok"):
        raise RuntimeError(f"render_to_png failed: {outcome}")
    return require_ok(outcome.get("result"), "render_to_png")


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end ChemDraw smoke test")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cdxml_path = output_dir / "aspirin.cdxml"
    png_path = output_dir / "aspirin.png"

    molecule = {
        "name": "aspirin",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "formula": "C9H8O4",
        "source": "bundled trusted smoke fixture",
    }
    print("smoke: drawing aspirin", file=sys.stderr, flush=True)
    drawing = require_ok(
        official_overrides.draw_molecule(molecule, output_path=str(cdxml_path)),
        "draw_molecule",
    )
    rendered = render_with_timeout(cdxml_path, png_path)
    print("smoke: rendered aspirin", file=sys.stderr, flush=True)

    if not cdxml_path.is_file() or cdxml_path.stat().st_size == 0:
        raise RuntimeError("CDXML output is missing or empty")
    if not png_path.is_file() or png_path.stat().st_size == 0:
        raise RuntimeError("PNG output is missing or empty")

    with Image.open(png_path) as image:
        width, height = image.size
        image.verify()
    if width < 32 or height < 32:
        raise RuntimeError(f"PNG dimensions are implausible: {width}x{height}")

    stereo_smiles = (
        "N[C@@H]1CC[C@H](O)C1",
        "N[C@@H]1CC[C@@H](O)C1",
    )
    stereo_results = []
    for index, smiles in enumerate(stereo_smiles, start=1):
        print(f"smoke: drawing stereoisomer {index}", file=sys.stderr, flush=True)
        stereo_cdxml = output_dir / f"stereoisomer-{index}.cdxml"
        stereo_png = output_dir / f"stereoisomer-{index}.png"
        stereo_drawing = require_ok(
            official_overrides.draw_molecule(
                {"smiles": smiles}, output_path=str(stereo_cdxml)
            ),
            f"draw_stereoisomer_{index}",
        )
        stereo_render = render_with_timeout(stereo_cdxml, stereo_png)
        print(f"smoke: rendered stereoisomer {index}", file=sys.stderr, flush=True)
        validation = stereo_drawing.get("metadata", {}).get(
            "chemistry_validation", {}
        )
        if (
            validation.get("status") != "preserved"
            or validation.get("wedge_bonds", 0) < 1
        ):
            raise RuntimeError(
                f"Stereoisomer {index} has no verified wedge representation"
            )
        with Image.open(stereo_png) as image:
            stereo_dimensions = list(image.size)
            image.verify()
        stereo_results.append(
            {
                "smiles": smiles,
                "cdxml": str(stereo_cdxml),
                "png": str(stereo_png),
                "png_dimensions": stereo_dimensions,
                "chemistry_validation": validation,
                "render_result": stereo_render,
            }
        )

    stereo_cdxml_files = [Path(item["cdxml"]) for item in stereo_results]
    stereo_png_files = [Path(item["png"]) for item in stereo_results]
    if stereo_cdxml_files[0].read_bytes() == stereo_cdxml_files[1].read_bytes():
        raise RuntimeError("Stereoisomer CDXML files are identical")
    if stereo_png_files[0].read_bytes() == stereo_png_files[1].read_bytes():
        raise RuntimeError("Stereoisomer PNG files are identical")

    print(json.dumps({
        "ok": True,
        "resolved_name": molecule.get("name"),
        "formula": molecule.get("formula"),
        "source": molecule.get("source"),
        "cdxml": str(cdxml_path),
        "cdxml_size": cdxml_path.stat().st_size,
        "png": str(png_path),
        "png_size": png_path.stat().st_size,
        "png_dimensions": [width, height],
        "draw_result": drawing,
        "render_result": rendered,
        "stereoisomers": stereo_results,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
