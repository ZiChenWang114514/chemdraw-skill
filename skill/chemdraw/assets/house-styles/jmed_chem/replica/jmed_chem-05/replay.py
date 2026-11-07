"""Redraw Figure 1A (inhibitor grid, two rows of four) of Baldwin, Ward et al., J. Med. Chem. 2025, DOI 10.1021/acs.jmedchem.4c02694, from figure-manifest.json; offline."""
from pathlib import Path
import os, subprocess, sys
os.environ.setdefault('CHEMDRAW_OFFLINE', '1')
if len(sys.argv) != 2:
    raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
manifest = Path(__file__).parent / 'figure-manifest.json'
args = out / 'compose_args.json'
args.write_text('{"manifest_path": "%s", "output_path": "%s"}' % (manifest, out / 'figure.cdxml'), encoding='utf-8')
root = Path(__file__).resolve().parents[7]
subprocess.run([sys.executable, str(root / 'skill/chemdraw/scripts/cdx.py'), 'call', 'compose_chemical_figure',
                '--args', str(args), '--out', str(out / 'validation.json')], check=True)
print(out / 'figure.cdxml')
