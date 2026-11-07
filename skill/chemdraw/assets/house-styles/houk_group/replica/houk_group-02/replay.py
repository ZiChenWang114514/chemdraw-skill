"""Redraw the S3 C-H oxygenation step (S3 + dioxirane to P3-OH2 + ketone) from the energy profile in Fig. 5 of Galeotti, Houk, Bietti et al., J. Am. Chem. Soc. 2023, DOI 10.1021/jacs.3c07163, from brief.json; offline."""
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
