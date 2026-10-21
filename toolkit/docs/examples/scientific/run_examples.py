"""Generate editable scientific examples; native rendering is a separate check."""
import argparse
import csv
import json
import math
from pathlib import Path
from cdxml_toolkit.scientific.__main__ import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--nmr-input',type=Path,help='Processed real 1D NMRPipe or ppm,intensity CSV')
    parser.add_argument('--glassware',type=Path,help='Converted native Clipware part 1 CDXML')
    parser.add_argument('--condensers',type=Path,help='Converted native Clipware part 2 CDXML')
    args=parser.parse_args()
    if bool(args.glassware)!=bool(args.condensers):parser.error('Supply both apparatus libraries')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    here=Path(__file__).resolve().parent;results={}
    for operation in ('tlc','mechanism'):
        results[operation]=run(operation,here/f'{operation}.json',out/f'{operation}.cdxml')
    # Explicitly simulated data, not measured reaction progress.
    data=out/'simulated-first-order.csv'
    with data.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle);writer.writerow(['time_min','fraction_remaining'])
        writer.writerows((t,math.exp(-.06*t)) for t in range(61))
    spec={'input':data.name,'x_column':'time_min','y_column':'fraction_remaining',
          'x_label':'Time / min','y_label':'Fraction remaining',
          'title':'Simulated first-order decay: k = 0.06 per min'}
    plot_spec=out/'plot.json';plot_spec.write_text(json.dumps(spec,indent=2))
    results['plot']=run('plot',plot_spec,out/'plot')
    if args.nmr_input:
        spec=json.loads((here/'nmr.json').read_text());spec['input']=str(args.nmr_input.resolve())
        # The bundled integration windows belong only to the documented example.
        spec['processing']={}
        path=out/'nmr.json';path.write_text(json.dumps(spec,indent=2))
        results['nmr']=run('nmr',path,out/'nmr')
    if args.glassware:
        spec=json.loads((here/'apparatus.json').read_text())
        spec['template_files']={'glassware':str(args.glassware.resolve()),'condensers':str(args.condensers.resolve())}
        path=out/'apparatus.json';path.write_text(json.dumps(spec,indent=2))
        results['apparatus']=run('apparatus',path,out/'apparatus.cdxml')
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(out/'results.json')


if __name__=='__main__':main()
