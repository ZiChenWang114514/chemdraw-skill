"""Redraw the stand-in brief for Figure 2 (More O-Ferrall-Jencks square) of Deufel, van Gemmeren et al., J. Chem. Educ. 2024, 10.1021/acs.jchemed.4c00270, from brief.json; offline. Only the H-Ar / [M]-Ar stand-in is drawn; the square itself is not expressible."""
from pathlib import Path
import json,os,sys
os.environ.setdefault('CHEMDRAW_OFFLINE','1')
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
brief=json.loads((Path(__file__).parent/'brief.json').read_text(encoding='utf-8'))
result=draw_figure(brief,str(out/'figure.cdxml'))
(out/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(out/'figure.cdxml')
