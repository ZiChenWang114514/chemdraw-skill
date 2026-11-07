"""Redraw the drawable part of JACS Au 2025, 5, 2792-2801 (Steffen et al., DOI 10.1021/jacsau.5c00357), Figure 5 lower part, from brief.json; offline.

The crop is an orbital energy plot (no molecular structures), so brief.json holds no species or steps; on this brief draw_figure hung without output in testing (see CASE.md)."""
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
