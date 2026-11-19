"""Redraw the two 2D transition-state panels of Chen, Wipf, Houk et al., Nat. Commun. 2022, 13, Fig. 6 (TS5/TS5* and TS8/TS8*, Rh drawn as text-free fragments with L and Cl) from brief.json with the ACS 1996 build path; offline. The 3D CYLview geometries are not drawn."""
from pathlib import Path
import os,sys
os.environ.setdefault('CHEMDRAW_OFFLINE','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[5]/'scripts'))
from acs_builder import build_from_spec
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
written=build_from_spec(str(Path(__file__).parent/'brief.json'),str(out/'figure.cdxml'))
print(written)
