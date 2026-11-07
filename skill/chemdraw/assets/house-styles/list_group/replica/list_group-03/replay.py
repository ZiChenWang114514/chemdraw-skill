"""Redraw the substrate-scope panel (ring-expansion products 3b-3f) of List et al., Nature 2024, from brief.json; offline."""
from pathlib import Path
import json,os,sys
os.environ.setdefault('CHEMDRAW_OFFLINE','1')
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
brief=json.loads((Path(__file__).parent/'brief.json').read_text(encoding='utf-8'))
result=draw_figure(brief,str(out/'pages'))
(out/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(out/'pages')
