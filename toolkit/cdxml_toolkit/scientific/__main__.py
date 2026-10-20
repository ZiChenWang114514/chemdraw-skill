"""Run scientific workflows: python -m cdxml_toolkit.scientific OP --spec FILE --output PATH."""
import argparse
import hashlib
import json
from pathlib import Path


def run(operation, spec_path, output):
    spec_path=Path(spec_path).resolve();spec=json.loads(spec_path.read_text(encoding='utf-8-sig'))
    def source(value):
        p=Path(value);return p if p.is_absolute() else spec_path.parent/p
    if operation=='tlc':
        from .tlc import draw_tlc
        return draw_tlc(spec,output)
    if operation=='apparatus':
        from .apparatus import draw_apparatus
        spec['template_files']={key:str(source(value).resolve()) for key,value in spec.get('template_files',{}).items()}
        return draw_apparatus(spec,output)
    if operation=='mechanism':
        from .mechanism import compile_mechanism
        from ..mcp_runtime.figure_tools import compose_chemical_figure
        import tempfile
        for obj in spec.get('objects',[]):
            if 'file' in obj:obj['file']=str(source(obj['file']).resolve())
        checks=[]
        compiled=compile_mechanism(spec,checks=checks)
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/'figure.json';manifest.write_text(json.dumps(compiled),encoding='utf-8')
            result=compose_chemical_figure(str(manifest),str(output))
            result['mechanism_checks']=checks
            return result
    if operation=='nmr':
        from .spectra import analyze_spectrum
        from .plots import plot_xy
        result=analyze_spectrum(source(spec['input']),spec.get('processing',{}))
        spectrum=result.pop('spectrum')
        plot=plot_xy(spectrum['ppm'],spectrum['intensity'],output,title=spec.get('title','NMR spectrum'),
            xlabel='Chemical shift / ppm',ylabel='Intensity / a.u.',reverse_x=True,provenance={'file':result['source'],'sha256':result['sha256']})
        path=Path(output)/'analysis.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'analysis_path':str(path.resolve()),**plot}
    if operation=='plot':
        import numpy as np
        from .plots import plot_xy
        path=source(spec['input']);data=np.genfromtxt(path,delimiter=',',names=True,encoding='utf-8-sig')
        return plot_xy(data[spec['x_column']],data[spec['y_column']],output,title=spec.get('title','Scientific plot'),
            xlabel=spec['x_label'],ylabel=spec['y_label'],reverse_x=spec.get('reverse_x',False),
            provenance={'file':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    raise ValueError(f'Unsupported scientific workflow: {operation}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['tlc','apparatus','nmr','plot','mechanism'])
    parser.add_argument('--spec',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.operation,args.spec,args.output),ensure_ascii=False,indent=2))
