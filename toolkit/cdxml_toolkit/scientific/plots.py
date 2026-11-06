"""Data-backed scientific plots in SVG, PNG, and editable CDXML."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET
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
            d.curve(pts[i:i+251], color=s.get('color'))
        if s.get('label'):
            d.text([right - 95, top + 12 + idx * 12], str(s['label']), 8, color=s.get('color'))
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


build_plot_cdxml = plot_xy


LCMS_PLATE_TIERS = (
    ('high', '>= 70%', '#c8e6c9'),
    ('medium', '30-70%', '#fff9c4'),
    ('low', '>0-30%', '#ffcdd2'),
    ('none', '0% / empty', '#eeeeee'),
    ('no_data', 'no data', '#b0bec5'),
)
LCMS_NO_DATA_COLOR = '#b0bec5'

_WELL_RE = re.compile(r'([A-Ha-h])\s*[-_]?\s*0?([1-9]|1[0-2])')
_WELL_SEARCH_RE = re.compile(r'(?<![A-Za-z0-9])([A-Ha-h])[-_]?0?([1-9]|1[0-2])(?![0-9])')


def _split_well_token(text: str) -> tuple[str | None, str]:
    """Split an OpenLynx "rack:pos" / "row:col" value; return (row letter or None, token)."""
    if ':' in text:
        parts = [p.strip() for p in text.split(':') if p.strip()]
        if len(parts) == 2 and len(parts[0]) == 1 and parts[0].isalpha() and parts[1].isdigit():
            return parts[0].upper(), parts[1]
        if parts:
            return None, parts[-1]
    return None, text


def _parse_well_token(raw_well: Any) -> tuple[str, int] | int | None:
    """Return (row, col) for a lettered well, an int for a 1-based numeric position, or None."""
    if raw_well is None or isinstance(raw_well, bool):
        return None
    if isinstance(raw_well, int):
        return int(raw_well)
    text = str(raw_well).strip()
    if not text:
        return None
    row, token = _split_well_token(text)
    if row is not None:
        return row, int(token)
    m = _WELL_RE.fullmatch(token)
    if m:
        return m.group(1).upper(), int(m.group(2))
    if token.isdigit():
        return int(token)
    raise ValueError(f'Unrecognised well identifier {raw_well!r}')


def _normalize_well_id(raw_well: Any, index: int, n_cols: int = 12, n_rows: int = 8) -> str:
    parsed = _parse_well_token(raw_well)
    if isinstance(parsed, tuple):
        return f'{parsed[0]}{parsed[1]}'
    pos = (parsed - 1) if parsed is not None else index
    if pos < 0 or pos >= n_rows * n_cols:
        raise ValueError(
            f'Well position {raw_well if parsed is not None else index + 1!r} is outside a '
            f'{n_rows}x{n_cols} plate'
        )
    return f"{chr(ord('A') + pos // n_cols)}{pos % n_cols + 1}"


def _peak_area_pct(peak: Any, wavelength: int | str | None) -> float:
    wl_str = str(wavelength or '').strip().lower()
    if '254' in wl_str:
        for attr in ('area_pct_254nm', 'area_pct', 'area_pct_220nm'):
            val = getattr(peak, attr, None)
            if val is not None:
                return float(val)
    elif '220' in wl_str:
        for attr in ('area_pct_220nm', 'area_pct', 'area_pct_254nm'):
            val = getattr(peak, attr, None)
            if val is not None:
                return float(val)
    for attr in ('area_pct', 'area_pct_254nm', 'area_pct_220nm'):
        val = getattr(peak, attr, None)
        if val is not None:
            return float(val)
    return 0.0


def _match_peak_to_mass(peak: Any, target_mass: float, tol_da: float = 1.5) -> str | None:
    from ..analysis.deterministic.mass_resolver import build_adducts
    adducts = build_adducts(float(target_mass))
    for spec in getattr(peak, 'ms_spectra', []) or []:
        mode = getattr(spec, 'mode', 'ES+')
        for mz in getattr(spec, 'top_ions', []) or []:
            for adduct_name, expected_mz in adducts.items():
                is_pos = adduct_name.endswith('+')
                if (mode == 'ES+' and is_pos) or (mode == 'ES-' and not is_pos):
                    if abs(float(mz) - float(expected_mz)) <= tol_da:
                        return f'{adduct_name} ({float(mz):.1f})'
    return None


def _reports_to_well_records(
    reports: Sequence[Any],
    *,
    product_mass: float | None = None,
    sm_mass: float | None = None,
    wavelength: int | str | None = 254,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, rep in enumerate(reports):
        raw_well: Any = str(getattr(rep, 'well', '') or '').strip()
        if not raw_well:
            for candidate in (getattr(rep, 'sample_id', ''), getattr(rep, 'sample_name', ''), getattr(rep, 'filename', '')):
                m = _WELL_SEARCH_RE.search(str(candidate or ''))
                if m:
                    raw_well = f'{m.group(1).upper()}{int(m.group(2))}'
                    break
        s_idx = getattr(rep, 'sample_index', None)
        # Keep the raw identifier; build_lcms_plate_cdxml normalises once against the plate size.
        well_id = raw_well if raw_well else (s_idx if s_idx is not None else None)

        peaks = getattr(rep, 'peaks', []) or []
        best_purity = 0.0
        best_rt = None
        found_ion = None
        sm_pct = 0.0

        if product_mass is not None:
            for pk in peaks:
                matched_ion = _match_peak_to_mass(pk, float(product_mass))
                if matched_ion is not None:
                    pct = _peak_area_pct(pk, wavelength)
                    if pct >= best_purity:
                        best_purity = pct
                        best_rt = float(getattr(pk, 'rt', 0.0))
                        found_ion = matched_ion
        else:
            for pk in peaks:
                pct = _peak_area_pct(pk, wavelength)
                if pct >= best_purity:
                    best_purity = pct
                    best_rt = float(getattr(pk, 'rt', 0.0))
                    found_ion = getattr(pk, 'mass_found', None)

        if sm_mass is not None:
            for pk in peaks:
                if _match_peak_to_mass(pk, float(sm_mass)) is not None:
                    sm_pct = max(sm_pct, _peak_area_pct(pk, wavelength))

        records.append({
            'well': well_id,
            'purity': round(float(best_purity), 2),
            'rt': round(float(best_rt), 2) if best_rt is not None else None,
            'found_ion': found_ion,
            'sm_pct': round(float(sm_pct), 2) if sm_mass is not None else None,
            'sample_name': getattr(rep, 'sample_name', ''),
        })
    return records


def _load_lcms_reports_from_path(path: Path) -> list[Any]:
    from ..analysis.openlynx_rpt import is_openlynx_rpt, parse_rpt
    from ..analysis.lcms_analyzer import LCMS_FORMATS, parse_report

    if path.is_file():
        if path.suffix.lower() == '.rpt' or is_openlynx_rpt(str(path)):
            return parse_rpt(str(path))
        for fmt in LCMS_FORMATS:
            if path.suffix.lower() in fmt.suffixes and fmt.detect(str(path)):
                return list(fmt.parse(str(path)))
        if path.suffix.lower() == '.pdf':
            rep = parse_report(str(path))
            return [rep] if rep is not None else []
        raise ValueError(f'Unsupported LCMS plate input file: {path}')

    if path.is_dir():
        reports: list[Any] = []
        for child in sorted(path.iterdir()):
            if child.suffix.lower() == '.rpt' or (child.is_file() and is_openlynx_rpt(str(child))):
                reports.extend(parse_rpt(str(child)))
            elif child.is_file() and child.suffix.lower() == '.pdf':
                rep = parse_report(str(child))
                if rep is not None:
                    reports.append(rep)
            else:
                for fmt in LCMS_FORMATS:
                    if child.suffix.lower() in fmt.suffixes and fmt.detect(str(child)):
                        reports.extend(fmt.parse(str(child)))
                        break
        if not reports:
            raise ValueError(f'No LCMS reports found in directory: {path}')
        return reports

    raise ValueError(f'LCMS plate source path does not exist: {path}')


def _detect_plate_dimensions(raw_well_ids: Sequence[Any], plate_format: int | str | None) -> tuple[list[str], list[int]]:
    """Pick 24- or 96-well dimensions from raw (un-normalised) well identifiers."""
    rows96, cols96 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], list(range(1, 13))
    rows24, cols24 = ['A', 'B', 'C', 'D'], [1, 2, 3, 4, 5, 6]
    if plate_format is not None:
        pf = str(plate_format).strip().lower()
        if '24' in pf or '4x6' in pf:
            return rows24, cols24
        if '96' in pf or '8x12' in pf:
            return rows96, cols96
        raise ValueError(f'Unsupported plate_format {plate_format!r}; use 24 or 96')

    if len(raw_well_ids) > 24:
        return rows96, cols96
    for raw in raw_well_ids:
        parsed = _parse_well_token(raw)
        if isinstance(parsed, tuple):
            if parsed[0] > 'D' or parsed[1] > 6:
                return rows96, cols96
        elif parsed is not None and parsed > 24:
            return rows96, cols96
    return rows24, cols24


def _purity_tier(purity: float | None) -> tuple[str, str]:
    if purity is None or not np.isfinite(float(purity)):
        return 'no_data', LCMS_NO_DATA_COLOR
    if float(purity) <= 0.0:
        return 'none', '#eeeeee'
    val = float(purity)
    if val >= 70.0:
        return 'high', '#c8e6c9'
    if val >= 30.0:
        return 'medium', '#fff9c4'
    return 'low', '#ffcdd2'


def build_lcms_plate_cdxml(
    source_or_spec: Any,
    output_path: str | Path | None = None,
    *,
    product_mass: float | None = None,
    sm_mass: float | None = None,
    plate_format: int | str | None = None,
    wavelength: int | str = 254,
    title: str = 'LCMS Plate Purity Heatmap',
) -> dict[str, Any]:
    """Build an editable 24-well or 96-well LCMS purity heatmap in CDXML."""
    raw_wells: list[dict[str, Any]] = []

    if isinstance(source_or_spec, Mapping):
        spec = dict(source_or_spec)
        output_path = spec.get('output_path', spec.get('output', output_path))
        product_mass = spec.get('product_mass', product_mass)
        sm_mass = spec.get('sm_mass', sm_mass)
        plate_format = spec.get('plate_format', spec.get('format', plate_format))
        wavelength = spec.get('wavelength', wavelength)
        title = spec.get('title', title)

        if 'wells' in spec and isinstance(spec['wells'], Sequence):
            for idx, item in enumerate(spec['wells']):
                if isinstance(item, Mapping):
                    raw_wells.append(dict(item))
        elif 'input' in spec or 'source' in spec or 'path' in spec:
            src_path = Path(spec.get('input') or spec.get('source') or spec.get('path'))
            if src_path.is_file() and src_path.suffix.lower() == '.json':
                loaded = json.loads(src_path.read_text(encoding='utf-8-sig'))
                return build_lcms_plate_cdxml(
                    loaded,
                    output_path=output_path,
                    product_mass=product_mass,
                    sm_mass=sm_mass,
                    plate_format=plate_format,
                    wavelength=wavelength,
                    title=title,
                )
            reports = _load_lcms_reports_from_path(src_path)
            raw_wells = _reports_to_well_records(
                reports,
                product_mass=product_mass,
                sm_mass=sm_mass,
                wavelength=wavelength,
            )
        else:
            # Allow dict mapping well_id -> purity or dict
            for k, v in spec.items():
                if _WELL_RE.fullmatch(str(k).strip()) or str(k).strip().isdigit():
                    if isinstance(v, (int, float)):
                        raw_wells.append({'well': str(k).strip().upper(), 'purity': float(v)})
                    elif isinstance(v, Mapping):
                        raw_wells.append({'well': str(k).strip().upper(), **dict(v)})
    elif isinstance(source_or_spec, (str, Path)):
        src_path = Path(source_or_spec)
        if src_path.is_file() and src_path.suffix.lower() == '.json':
            loaded = json.loads(src_path.read_text(encoding='utf-8-sig'))
            return build_lcms_plate_cdxml(
                loaded,
                output_path=output_path,
                product_mass=product_mass,
                sm_mass=sm_mass,
                plate_format=plate_format,
                wavelength=wavelength,
                title=title,
            )
        reports = _load_lcms_reports_from_path(src_path)
        raw_wells = _reports_to_well_records(
            reports,
            product_mass=product_mass,
            sm_mass=sm_mass,
            wavelength=wavelength,
        )
    elif isinstance(source_or_spec, Sequence):
        for item in source_or_spec:
            if isinstance(item, Mapping):
                raw_wells.append(dict(item))
            elif hasattr(item, 'peaks') and hasattr(item, 'well'):
                raw_wells.extend(
                    _reports_to_well_records(
                        [item],
                        product_mass=product_mass,
                        sm_mass=sm_mass,
                        wavelength=wavelength,
                    )
                )
    else:
        raise ValueError('Provide a path, spec dict, or list of well dicts for build_lcms_plate_cdxml')

    rows, cols = _detect_plate_dimensions([w.get('well') for w in raw_wells], plate_format)
    n_rows, n_cols = len(rows), len(cols)

    well_map: dict[str, dict[str, Any]] = {}
    for idx, w in enumerate(raw_wells):
        wid = _normalize_well_id(w.get('well'), idx, n_cols=n_cols, n_rows=n_rows)
        if wid[0] not in rows or int(wid[1:]) not in cols:
            raise ValueError(f'Well {wid} is outside the {n_rows}x{n_cols} plate')
        if wid in well_map:
            raise ValueError(f'Duplicate well {wid} in LCMS plate input')
        purity_val = None
        for key in ('purity', 'area_pct', 'product_pct'):
            if w.get(key) is not None:
                purity_val = w[key]
                break
        purity = float(purity_val) if purity_val is not None else None
        rt_val = w.get('rt', w.get('tR', w.get('retention_time')))
        rt = float(rt_val) if rt_val is not None else None
        found_ion = w.get('found_ion', w.get('ion', w.get('adduct', w.get('mass_found'))))
        tier_name, fill_hex = _purity_tier(purity)
        well_map[wid] = {
            'well': wid,
            'purity': round(purity, 1) if purity is not None else None,
            'rt': round(rt, 2) if rt is not None else None,
            'found_ion': str(found_ion) if found_ion else None,
            'tier': tier_name,
            'color': fill_hex,
        }

    cell_w = 54.0 if n_cols == 6 else 44.0
    cell_h = 42.0 if n_rows == 4 else 34.0
    gap = 3.0
    left_margin = 46.0
    top_margin = 56.0
    grid_w = n_cols * cell_w + (n_cols - 1) * gap
    grid_h = n_rows * cell_h + (n_rows - 1) * gap
    canvas_w = int(max(left_margin + grid_w + 40.0, left_margin + 64.0 + 70.0 * len(LCMS_PLATE_TIERS) + 10.0))
    canvas_h = int(top_margin + grid_h + 92.0)

    drawing = Drawing(canvas_w, canvas_h)
    plate_group = drawing.add('group', {'BoundingBox': f'0 0 {canvas_w} {canvas_h}'})

    subtitle = f'({n_rows}x{n_cols}, {wavelength} nm' + (f', M={product_mass}' if product_mass else '') + ')'
    drawing.text((left_margin, 22.0), f'{title} {subtitle}', size=11, parent=plate_group)

    # Column headers
    for c_idx, col_num in enumerate(cols):
        cx = left_margin + c_idx * (cell_w + gap) + cell_w * 0.42
        drawing.text((cx, top_margin - 10.0), str(col_num), size=9, parent=plate_group)

    tier_counts = {'high': 0, 'medium': 0, 'low': 0, 'none': 0, 'no_data': 0}

    # Plate grid cells (draw background fills/borders first, then text overlays on top)
    deferred_cell_texts: list[tuple[tuple[float, float], str, int, str | None]] = []
    for r_idx, row_ch in enumerate(rows):
        ry = top_margin + r_idx * (cell_h + gap)
        drawing.text((18.0, ry + cell_h * 0.58), row_ch, size=9, parent=plate_group)
        for c_idx, col_num in enumerate(cols):
            cx = left_margin + c_idx * (cell_w + gap)
            wid = f'{row_ch}{col_num}'
            info = well_map.get(wid)
            if info is not None:
                tier_name = info['tier']
                fill_hex = info['color']
                purity = info['purity']
                rt = info['rt']
            else:
                tier_name = 'none'
                fill_hex = '#eeeeee'
                purity = 0.0
                rt = None
            tier_counts[tier_name] += 1

            drawing.filled_rect(
                cx,
                ry,
                cx + cell_w,
                ry + cell_h,
                fill_color=fill_hex,
                border_color='#9e9e9e',
                parent=plate_group,
            )
            # Draw crisp cell border
            drawing.curve(
                [(cx, ry), (cx + cell_w, ry), (cx + cell_w, ry + cell_h), (cx, ry + cell_h)],
                parent=plate_group,
                closed=True,
                filled=False,
                color='#9e9e9e',
            )

            if info is not None and purity is None:
                deferred_cell_texts.append(((cx + cell_w * 0.28, ry + cell_h * 0.58), 'n/d', 8, '#37474f'))
            elif info is not None and purity > 0.0:
                p_str = f'{purity:.0f}%' if abs(purity - round(purity)) < 0.05 else f'{purity:.1f}%'
                deferred_cell_texts.append(((cx + 8.0, ry + cell_h * 0.44), p_str, 8, None))
                if rt is not None:
                    deferred_cell_texts.append(((cx + 6.0, ry + cell_h * 0.80), f'tR {rt:.2f}', 6, '#424242'))
            elif info is not None:
                deferred_cell_texts.append(((cx + cell_w * 0.34, ry + cell_h * 0.58), '0%', 8, '#757575'))
            else:
                deferred_cell_texts.append(((cx + cell_w * 0.40, ry + cell_h * 0.58), '-', 8, '#757575'))

    for xy_pt, txt_val, f_sz, col_hex in deferred_cell_texts:
        drawing.text(xy_pt, txt_val, size=f_sz, parent=plate_group, color=col_hex)

    # Legend bar below grid
    legend_y = top_margin + grid_h + 18.0
    lx = left_margin
    drawing.text((lx, legend_y + 10.0), 'Purity Tiers:', size=8, parent=plate_group)
    lx += 64.0
    for _, tier_label, tier_hex in LCMS_PLATE_TIERS:
        drawing.filled_rect(lx, legend_y, lx + 14.0, legend_y + 12.0, fill_color=tier_hex, border_color='#757575', parent=plate_group)
        drawing.text((lx + 18.0, legend_y + 10.0), tier_label, size=8, parent=plate_group)
        lx += 70.0

    # Best Wells summary callout at the bottom
    ranked_wells = sorted(
        (w for w in well_map.values() if w['purity'] is not None and w['purity'] > 0.0),
        key=lambda w: (-w['purity'], w['well']),
    )
    top_wells = ranked_wells[:5]
    if top_wells:
        summary_items = [
            f"{w['well']} ({w['purity']:.1f}%" + (f", tR {w['rt']:.2f} min" if w['rt'] is not None else '') + ')'
            for w in top_wells
        ]
        best_wells_text = 'Best Wells: ' + ', '.join(summary_items)
    else:
        best_wells_text = 'Best Wells: None detected'

    drawing.text((left_margin, legend_y + 32.0), best_wells_text, size=9, parent=plate_group)

    saved_path = drawing.save(output_path) if output_path is not None else None
    xml_str = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
        + ET.tostring(drawing.root, encoding='unicode')
    )

    out: dict[str, Any] = {
        'cdxml': xml_str,
        'plate_format': '96-well' if n_rows == 8 else '24-well',
        'rows': rows,
        'columns': cols,
        'well_count': len(well_map),
        'tier_counts': tier_counts,
        'best_wells': [w['well'] for w in top_wells],
        'best_wells_summary': best_wells_text,
        'wells': [well_map[k] for k in sorted(well_map)],
    }
    if saved_path is not None:
        out['output_path'] = saved_path
    return out
