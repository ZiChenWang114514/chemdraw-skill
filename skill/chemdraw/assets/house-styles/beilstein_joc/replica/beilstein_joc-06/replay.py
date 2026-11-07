"""Probe for the energy-profile replica of Figure 2 (top) of Chusov et al., Beilstein J. Org. Chem. 2025, 21, 130 (crop beilstein_joc-06, house style beilstein_joc); offline.

Runs draw_figure on brief.json, which asks for kind "energy_profile". The tool has no such drawer and refuses it, so this script
writes the refusal to validation.json and draws nothing. Usage: replay.py NEW_OUTPUT_DIRECTORY
"""
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
print(json.dumps(result,ensure_ascii=False,default=str)[:800])
