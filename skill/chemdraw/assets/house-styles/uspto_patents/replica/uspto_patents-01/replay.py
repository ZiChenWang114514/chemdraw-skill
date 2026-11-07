"""Redraw the generic formula I and the Ar1 definition of US 9,732,080 B2 (col. 6), from brief.json; offline.

Replica of the uspto_patents house-style figure type markush (crop evidence/uspto_patents-01.png).
Adapted from the jacs-au replay: the brief is kind "scope", so the output is a folder (page-001.cdxml).
"""
from pathlib import Path
import json,os,sys
os.environ.setdefault('CHEMDRAW_OFFLINE','1')
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
brief=json.loads((Path(__file__).parent/'brief.json').read_text(encoding='utf-8'))
result=draw_figure(brief,str(out/'panel'))
(out/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(out/'panel')
