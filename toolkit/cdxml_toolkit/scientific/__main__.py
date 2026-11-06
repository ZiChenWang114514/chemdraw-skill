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
        from .spectra import analyze_spectrum, build_nmr_cdxml
        from .plots import plot_xy
        proc = dict(spec.get('processing') or {})
        for key in ('solvent', 'inset_region', 'nucleus', 'frequency_mhz', 'exclude_solvent',
                    'multiplet_max_j_hz', 'baseline_windows', 'baseline_degree', 'prominence',
                    'integration_regions', 'normalization_region', 'normalization_value'):
            if key in spec and key not in proc:
                proc[key] = spec[key]
        if 'spectrometer_frequency_mhz' in spec and 'frequency_mhz' not in proc:
            proc['frequency_mhz'] = spec['spectrometer_frequency_mhz']
        if 'spectrometer_frequency_mhz' in proc and 'frequency_mhz' not in proc:
            proc['frequency_mhz'] = proc.pop('spectrometer_frequency_mhz')
        else:
            proc.pop('spectrometer_frequency_mhz', None)
        result=analyze_spectrum(source(spec['input']),proc)
        spectrum=result.pop('spectrum')
        cdxml_str=result.pop('cdxml',None)
        title=spec.get('title','NMR spectrum')
        nucleus=proc.get('nucleus') or '1H'
        if cdxml_str is None:
            cdxml_str=build_nmr_cdxml(
                spectrum['ppm'],
                spectrum['intensity'],
                peaks=result.get('peaks',[]),
                inset_region=proc.get('inset_region'),
                title=title,
                nucleus=nucleus,
            )
        plot=plot_xy(spectrum['ppm'],spectrum['intensity'],output,title=title,
            xlabel='Chemical shift / ppm',ylabel='Intensity / a.u.',reverse_x=True,
            provenance={'file':result['source'],'sha256':result['sha256']},
            dpi=int(spec.get('dpi',300)))
        out_dir=Path(output)
        (out_dir/'plot.cdxml').write_text(cdxml_str,encoding='utf-8')
        path=out_dir/'analysis.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'analysis_path':str(path.resolve()),**plot}
    if operation=='plot':
        import numpy as np
        from .plots import plot_xy
        dpi=int(spec.get('dpi',300))
        xlabel=spec.get('x_label',spec.get('xlabel','x'))
        ylabel=spec.get('y_label',spec.get('ylabel','y'))
        if spec.get('series'):
            resolved_series=[]
            prov_files=[]
            for item in spec['series']:
                s_item=dict(item)
                if 'input' in s_item or 'path' in s_item:
                    s_path=source(s_item.get('input') or s_item.get('path'))
                    s_data=np.genfromtxt(s_path,delimiter=',',names=True,encoding='utf-8-sig')
                    x_col=s_item.get('x_column',spec.get('x_column','x'))
                    y_col=s_item.get('y_column',spec.get('y_column','y'))
                    s_item['x']=s_data[x_col]
                    s_item['y']=s_data[y_col]
                    prov_files.append({'file':str(s_path.resolve()),'sha256':hashlib.sha256(s_path.read_bytes()).hexdigest()})
                resolved_series.append(s_item)
            return plot_xy(
                None,
                None,
                output,
                title=spec.get('title','Scientific plot'),
                xlabel=xlabel,
                ylabel=ylabel,
                reverse_x=spec.get('reverse_x',False),
                provenance={'series':prov_files} if prov_files else spec.get('provenance'),
                dpi=dpi,
                series=resolved_series,
            )
        path=source(spec['input']);data=np.genfromtxt(path,delimiter=',',names=True,encoding='utf-8-sig')
        return plot_xy(data[spec['x_column']],data[spec['y_column']],output,title=spec.get('title','Scientific plot'),
            xlabel=xlabel,ylabel=ylabel,reverse_x=spec.get('reverse_x',False),
            provenance={'file':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},
            dpi=dpi)
    if operation=='stack_nmr':
        from .spectra import build_stacked_nmr_cdxml
        raw_spectra=spec.get('spectra',[])
        resolved_spectra=[]
        for item in raw_spectra:
            if isinstance(item,str):
                resolved_spectra.append(str(source(item).resolve()))
            elif isinstance(item,dict):
                d_item=dict(item)
                for k in ('path','input','source'):
                    if k in d_item and isinstance(d_item[k],str):
                        d_item[k]=str(source(d_item[k]).resolve())
                resolved_spectra.append(d_item)
            else:
                resolved_spectra.append(item)
        ppm_range=tuple(spec['ppm_range']) if spec.get('ppm_range') is not None else None
        res=build_stacked_nmr_cdxml(
            resolved_spectra,
            output_path=output,
            labels=spec.get('labels'),
            ppm_range=ppm_range,
            title=spec.get('title','Stacked NMR Comparison'),
            normalize=spec.get('normalize','each'),
            show_peaks=spec.get('show_peaks',True),
            match_shifts=spec.get('match_shifts'),
        )
        res.pop('cdxml',None)
        return res
    if operation=='lcms_plate':
        from .plots import build_lcms_plate_cdxml
        plate_spec=dict(spec)
        for k in ('input','source','path'):
            if k in plate_spec and isinstance(plate_spec[k],str):
                plate_spec[k]=str(source(plate_spec[k]).resolve())
        res=build_lcms_plate_cdxml(plate_spec,output_path=output)
        res.pop('cdxml',None)
        return res
    raise ValueError(f'Unsupported scientific workflow: {operation}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['tlc','apparatus','nmr','plot','mechanism','stack_nmr','lcms_plate'])
    parser.add_argument('--spec',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.operation,args.spec,args.output),ensure_ascii=False,indent=2))
