"""Auditable 1D spectral peak picking and integration without guessed assignments."""
import hashlib
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from .common import number


def read_spectrum(path):
    path=Path(path)
    if path.suffix.lower()=='.csv':
        values=np.genfromtxt(path,delimiter=',',names=True,encoding='utf-8-sig')
        if not {'ppm','intensity'}<=set(values.dtype.names or ()):
            raise ValueError('CSV requires ppm,intensity columns')
        return np.atleast_1d(values['ppm']),np.atleast_1d(values['intensity'])
    if path.suffix.lower() in ('.ft','.ft1','.ft2'):
        import nmrglue as ng
        dic,data=ng.pipe.read(str(path))
        if data.ndim!=1 or np.iscomplexobj(data):raise ValueError('Provide a processed real 1D spectrum')
        return ng.pipe.make_uc(dic,data).ppm_scale(),data.astype(float)
    raise ValueError('Supported processed spectra: CSV and real 1D NMRPipe')


def analyze_spectrum(path, options):
    allowed={'baseline_windows','baseline_degree','prominence','integration_regions','normalization_region','normalization_value'}
    if not isinstance(options,dict) or set(options)-allowed:raise ValueError('Unknown spectrum processing options')
    if 'normalization_value' in options and 'normalization_region' not in options:
        raise ValueError('Normalization value requires a reference region')
    path=Path(path).resolve();x,y=read_spectrum(path)
    if len(x)<3 or len(x)>2000000 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Provide 3..2,000,000 finite spectrum points')
    if len(np.unique(x))!=len(x):raise ValueError('Chemical shift values must be unique')
    if not (np.all(np.diff(x)>0) or np.all(np.diff(x)<0)):raise ValueError('Chemical shift axis must be monotonic')
    order=np.argsort(x);x,y=x[order],y[order]
    def bounds(limits):
        if not isinstance(limits,(list,tuple)) or len(limits)!=2:raise ValueError('A spectral window needs two boundaries')
        a,b=sorted(number(v,'window boundary') for v in limits)
        if a<x[0] or b>x[-1] or a==b:raise ValueError('Window bounds must lie within the spectrum')
        return a,b
    baseline=np.zeros_like(y)
    windows=options.get('baseline_windows',[])
    if windows:
        if len(windows)>1000:raise ValueError('At most 1000 baseline windows')
        mask=np.zeros(len(x),dtype=bool)
        for limits in windows:
            a,b=bounds(limits);mask|=(x>=a)&(x<=b)
        degree=number(options.get('baseline_degree',1),'baseline degree',0,3)
        if not degree.is_integer():raise ValueError('Baseline degree must be an integer')
        degree=int(degree)
        if mask.sum()<max(10,degree+2):raise ValueError('Baseline windows contain too few samples')
        baseline=np.polynomial.Polynomial.fit(x[mask],y[mask],degree)(x)
        y=y-baseline
    prominence=number(options.get('prominence',max(float(np.ptp(y))*.05,1e-12)),'prominence',1e-15)
    peaks,props=find_peaks(y,prominence=prominence)
    if len(peaks)>10000:raise ValueError('Too many peaks; increase prominence')
    integrals=[]
    regions=options.get('integration_regions',[])
    if len(regions)>1000:raise ValueError('At most 1000 integration regions')
    for limits in regions:
        a,b=bounds(limits)
        sel=(x>a)&(x<b);xx=np.r_[a,x[sel],b];yy=np.interp(xx,x,y)
        area=float(np.trapezoid(yy,xx)) if hasattr(np,'trapezoid') else float(np.trapz(yy,xx))
        integrals.append({'limits_ppm':[a,b],'area':area})
    normalization=None
    if 'normalization_region' in options:
        index=options['normalization_region']
        if type(index) is not int or not 0<=index<len(integrals):raise ValueError('Invalid normalization region')
        denominator=integrals[index]['area'];value=number(options.get('normalization_value',1),'normalization value',1e-15)
        if denominator<=0:raise ValueError('Normalization integral must be positive')
        normalization={'region':index,'value':value,'denominator_area':denominator}
        for integral in integrals:integral['normalized']=integral['area']/denominator*value
    return {'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'sample_count':len(x),'axis_unit':'ppm','intensity_unit':'arbitrary',
        'processing':{'baseline_windows':windows,'baseline_degree':options.get('baseline_degree',1) if windows else None,'peak_prominence':prominence,'normalization':normalization},
        'peaks':[{'ppm':float(x[i]),'intensity':float(y[i]),'prominence':float(p)} for i,p in zip(peaks,props['prominences'])],
        'integrals':integrals,'assignments':'not_performed',
        'warnings':['Peak positions are not automatic atom assignments; integration alone does not establish purity.']+(['Negative integrals are present.'] if any(i['area']<0 for i in integrals) else []),
        'spectrum':{'ppm':x.tolist(),'intensity':y.tolist()}}
