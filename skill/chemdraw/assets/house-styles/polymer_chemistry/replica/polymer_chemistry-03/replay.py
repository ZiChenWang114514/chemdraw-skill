"""Redraw Scheme 1 (rows A to C) of Konkolewicz et al., Polym. Chem. 2026, DOI 10.1039/d5py00767d, offline.

draw_figure refuses the five steps as one brief, so each row is drawn from its own brief
(brief_rowA.json, brief_rowB.json, brief_rowC.json) and the three CDXML files are written side by side.
"""
from pathlib import Path
import json,os,sys
os.environ.setdefault('CHEMDRAW_OFFLINE','1')
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).parent
reports={}
for row in ('A','B','C'):
    brief=json.loads((here/f'brief_row{row}.json').read_text(encoding='utf-8'))
    reports[row]=draw_figure(brief,str(out/f'row_{row}.cdxml'))
(out/'validation.json').write_text(json.dumps(reports,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
print(out)
