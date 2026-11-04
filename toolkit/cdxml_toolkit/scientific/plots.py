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


DEFAULT_SERIES_COLORS = ('#185f72', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02')


def _normalize_series(x, y, series):
    normalized = []
    raw_series = list(series) if series is not None else [{'x': x, 'y': y}]
    if not raw_series:
        raise ValueError('At least one data series is required')
    for idx, item in enumerate(raw_series):
        if not isinstance(item, dict) or 'x' not in item or 'y' not in item:
            raise ValueError('Each series must provide x and y arrays')
        sx = np.asarray(item['x'], dtype=float)
        sy = np.asarray(item['y'], dtype=float)
        if (
            sx.ndim != 1
            or sy.shape != sx.shape
            or len(sx) < 2
            or len(sx) > 2000000
            or not np.isfinite(sx).all()
            or not np.isfinite(sy).all()
        ):
            raise ValueError('Plot requires equal-length finite one-dimensional arrays')
        normalized.append({
            'x': sx,
            'y': sy,
            'label': item.get('label'),
            'color': item.get('color') or DEFAULT_SERIES_COLORS[idx % len(DEFAULT_SERIES_COLORS)],
            'style': item.get('style') or '-',
        })
    all_x = np.concatenate([s['x'] for s in normalized])
    if all_x.max() == all_x.min():
        raise ValueError('X axis must have a nonzero range')
    return normalized


def plot_xy(
    x=None,
    y=None,
    output_dir=None,
    *,
    title='Scientific plot',
    xlabel='x',
    ylabel='y',
    reverse_x=False,
    provenance=None,
    dpi=300,
    series=None,
):
    if isinstance(x, dict):
        spec = x
        if output_dir is None and y is not None:
            output_dir = y
            y = None
        output_dir = spec.get('output_dir', output_dir)
        title = spec.get('title', title)
        xlabel = spec.get('xlabel', xlabel)
        ylabel = spec.get('ylabel', ylabel)
        reverse_x = spec.get('reverse_x', reverse_x)
        provenance = spec.get('provenance', provenance)
        dpi = int(spec.get('dpi', dpi))
        series = spec.get('series', series)
        x = spec.get('x')
        y = spec.get('y')
    dpi = int(dpi)
    if dpi <= 0:
        raise ValueError('dpi must be positive')
    if output_dir is None:
        raise ValueError('output_dir is required')
    series_list = _normalize_series(x, y, series)
    primary_x = series_list[0]['x']
    primary_y = series_list[0]['y']
    target=Path(output_dir).resolve();target.mkdir(parents=True,exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig,ax=plt.subplots(figsize=(8,3.8),layout='constrained')
    has_labels = False
    for s in series_list:
        lbl = s.get('label')
        if lbl:
            has_labels = True
        ax.plot(s['x'], s['y'], color=s['color'], linestyle=s['style'], linewidth=.9, label=lbl)
    if has_labels:
        ax.legend(frameon=False, fontsize=8)
    ax.set(xlabel=xlabel,ylabel=ylabel,title=title)
    if reverse_x:ax.invert_xaxis()
    ax.spines[['top','right']].set_visible(False)
    xmin,xmax=sorted(ax.get_xlim());ymin,ymax=sorted(ax.get_ylim())
    xticks=[float(v) for v in ax.get_xticks() if xmin<=v<=xmax]
    yticks=[float(v) for v in ax.get_yticks() if ymin<=v<=ymax]
    for extension in ('svg','png'):fig.savefig(target/f'plot.{extension}',dpi=dpi)
    plt.close(fig)
    np.savetxt(target/'data.csv',np.c_[primary_x,primary_y],delimiter=',',header='x,y',comments='')
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
    total_display_samples = 0
    for idx, s in enumerate(series_list):
        keep = envelope_indices(s['y'])
        total_display_samples += int(len(keep))
        # Separate curves avoid native per-object control-point limits.
        pts = [[xx(s['x'][i]), yy(s['y'][i])] for i in keep]
        for i in range(0, len(pts) - 1, 250):
            d.curve(pts[i:i+251])
        if s.get('label'):
            d.text([right - 95, top + 12 + idx * 12], str(s['label']), 8)
    d.save(target/'plot.cdxml')
    result={'source':provenance,'sample_count':int(sum(len(s['x']) for s in series_list)),
        'cdxml_display_samples':total_display_samples,
        'series_count':len(series_list),
        'dpi':dpi,
        'display_reduction':'min/max envelope; analysis and CSV retain every sample',
        'xlabel':xlabel,'ylabel':ylabel,'reverse_x':reverse_x,
        'axes':{'x_limits':[xmin,xmax],'y_limits':[ymin,ymax],'x_ticks':xticks,'y_ticks':yticks},
        'outputs':{ext:str(target/f'plot.{ext}') for ext in ('svg','png','cdxml')}}
    (target/'plot.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
