"""Redraw the copper(I) NHC entry of panel A (Chart 1) of Martins et al., Dalton Trans. 2025 (DOI 10.1039/d5dt01595b), from brief.json; offline. Only one of the six panel entries is drawn; see CASE.md."""
from pathlib import Path
import json,os,sys
os.environ.setdefault('CHEMDRAW_OFFLINE','1')
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
if len(sys.argv)!=2:raise SystemExit('Usage: replay.py NEW_OUTPUT_DIRECTORY')
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=False)
brief=json.loads((Path(__file__).parent/'brief.json').read_text(encoding='utf-8'))
# kind "scope" takes a new folder (page-001.cdxml, ...), not a single .cdxml file
result=draw_figure(brief,str(out/'panel'))
(out/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(out/'panel'/'page-001.cdxml')
