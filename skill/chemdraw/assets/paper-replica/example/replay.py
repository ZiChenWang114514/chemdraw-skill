"""Reproduce a self-authored chemical figure; no API upload or session data."""
from pathlib import Path
import json,sys
from cdxml_toolkit.mcp_runtime.figure_tools import compose_chemical_figure
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
result=compose_chemical_figure(str(Path(__file__).parent/'figure.json'),str(out/'figure.cdxml'))
(out/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(out/'figure.cdxml')
