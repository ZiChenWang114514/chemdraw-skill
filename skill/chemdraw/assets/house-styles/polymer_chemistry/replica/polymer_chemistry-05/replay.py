"""Redraw the D3 to D3V monomer step of Figure 1 (panel 2) of Kodger et al., Polym. Chem. 2022, 10.1039/d2py00841f, from brief.json; offline. Only this one drawable step is reproduced; the polymer steps (sec-BuLi and styrene, propagation, end functionalisation, coupling, grafting) are not drawn because the species are polymers without a SMILES."""
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
