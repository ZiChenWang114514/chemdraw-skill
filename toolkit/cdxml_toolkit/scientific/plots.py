"""Data-backed scientific plots in SVG, PNG, and editable CDXML."""
import json
from pathlib import Path
import numpy as np
from .common import Drawing


def envelope_indices(values, limit=1600):
    values=np.asarray(values)
    if limit<6:raise ValueError('Envelope limit must be at least six')
    if len(values)<=limit:return np.arange(len(values))
    # Preserve extrema instead of silently discarding narrow spectral peaks.
    keep={0,len(values)-1}
    for chunk in np.array_split(np.arange(1,len(values)-1),(limit-2)//2):
        if len(chunk):keep.update([int(chunk[np.argmin(values[chunk])]),int(chunk[np.argmax(values[chunk])])])
    return np.array(sorted(keep))


def plot_xy(x,y,output_dir,*,title='Scientific plot',xlabel='x',ylabel='y',reverse_x=False,provenance=None):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or len(x)<2 or len(x)>2000000 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Plot requires equal-length finite one-dimensional arrays')
    if x.max()==x.min():raise ValueError('X axis must have a nonzero range')
    target=Path(output_dir).resolve();target.mkdir(parents=True,exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig,ax=plt.subplots(figsize=(8,3.8),layout='constrained')
    ax.plot(x,y,color='#185f72',linewidth=.9)
    ax.set(xlabel=xlabel,ylabel=ylabel,title=title)
    if reverse_x:ax.invert_xaxis()
    ax.spines[['top','right']].set_visible(False)
    xmin,xmax=sorted(ax.get_xlim());ymin,ymax=sorted(ax.get_ylim())
    xticks=[float(v) for v in ax.get_xticks() if xmin<=v<=xmax]
    yticks=[float(v) for v in ax.get_yticks() if ymin<=v<=ymax]
    for extension in ('svg','png'):fig.savefig(target/f'plot.{extension}',dpi=180)
    plt.close(fig)
    np.savetxt(target/'data.csv',np.c_[x,y],delimiter=',',header='x,y',comments='')
    d=Drawing(600,300);d.text([65,25],title,12)
    left,right,top,bottom=65,565,45,245
    def xx(v):return left+(right-left)*((xmax-v) if reverse_x else (v-xmin))/(xmax-xmin)
    def yy(v):return bottom-(bottom-top)*(v-ymin)/(ymax-ymin)
    d.line([left,top],[left,bottom]);d.line([left,bottom],[right,bottom])
    for v in xticks:
        p=xx(v);d.line([p,bottom],[p,bottom+4]);d.text([p-8,bottom+17],f'{v:.3g}',8)
    for v in yticks:
        p=yy(v);d.line([left-4,p],[left,p]);d.text([5,p+3],f'{v:.3g}',8)
    d.text([270,285],xlabel,10);d.text([5,40],ylabel,8)
    keep=envelope_indices(y)
    # Separate curves avoid native per-object control-point limits.
    pts=[[xx(x[i]),yy(y[i])] for i in keep]
    for i in range(0,len(pts)-1,250):d.curve(pts[i:i+251])
    d.save(target/'plot.cdxml')
    result={'source':provenance,'sample_count':len(x),'cdxml_display_samples':len(keep),
        'display_reduction':'min/max envelope; analysis and CSV retain every sample',
        'xlabel':xlabel,'ylabel':ylabel,'reverse_x':reverse_x,
        'axes':{'x_limits':[xmin,xmax],'y_limits':[ymin,ymax],'x_ticks':xticks,'y_ticks':yticks},
        'outputs':{ext:str(target/f'plot.{ext}') for ext in ('svg','png','cdxml')}}
    (target/'plot.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
