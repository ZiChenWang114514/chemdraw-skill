"""Native TLC plates and explicitly calibrated spot measurements."""
from __future__ import annotations

from copy import deepcopy
import math
from xml.etree import ElementTree as ET
from .common import Drawing, number, point


TLC_VISUALIZATION_PALETTES = {
    'uv254': {
        'spot': '#1b5e20',
        'plate': '#c8f7c5',
        'label': 'UV 254 nm',
    },
    'uv365': {
        'spot': '#00b0ff',
        'plate': '#1a237e',
        'label': 'UV 365 nm',
    },
    'kmno4': {
        'spot': '#f9a825',
        'plate': '#8e24aa',
        'label': 'KMnO4 stain',
    },
    'pma': {
        'spot': '#1b365d',
        'plate': '#dce775',
        'label': 'PMA stain',
    },
    'ninhydrin': {
        'spot': '#6a1b9a',
        'plate': '#fff8e1',
        'label': 'Ninhydrin stain',
    },
    'anisaldehyde': {
        'spot': '#c2185b',
        'plate': '#fce4ec',
        'label': 'p-Anisaldehyde stain',
    },
    'iodine': {
        'spot': '#8d6e63',
        'plate': '#fffde7',
        'label': 'I2 vapor',
    },
}


def measure_rf(origin, solvent_front, spot):
    """Project a measured spot along the calibrated solvent travel direction."""
    a, b, s = map(point, (origin, solvent_front, spot))
    d = [b[i] - a[i] for i in range(2)]
    length = sum(v * v for v in d)
    if length == 0:
        raise ValueError('Origin and solvent front must differ')
    return number(sum((s[i] - a[i]) * d[i] for i in range(2)) / length, 'Rf', 0, 1)


def _resolve_spot_color_hex(spec: dict, spot: dict | None = None) -> str | None:
    for container in ((spot or {}), spec):
        raw_color = container.get('color')
        if raw_color:
            key = str(raw_color).strip().lower()
            if key in TLC_VISUALIZATION_PALETTES:
                return TLC_VISUALIZATION_PALETTES[key]['spot']
            return str(raw_color).strip()
        for attr in ('stain', 'visualization'):
            val = container.get(attr)
            if val:
                key = str(val).strip().lower().replace(' ', '').replace('-', '').replace('_', '')
                for pal_key, pal_info in TLC_VISUALIZATION_PALETTES.items():
                    if key == pal_key or key.startswith(pal_key):
                        return pal_info['spot']
                if str(val).strip().startswith('#'):
                    return str(val).strip()
    return None


def _merge_spot_lists(spot_lists: list[list[dict]], rf_tol: float = 0.015) -> list[dict]:
    merged: list[dict] = []
    for spots in spot_lists:
        for sp in spots:
            rf_val = number(sp['rf'], 'Rf', 0, 1)
            existing = next((m for m in merged if abs(float(m['rf']) - rf_val) <= rf_tol), None)
            if existing is None:
                merged.append(deepcopy(sp))
            else:
                for dim_key in ('width', 'height', 'tail'):
                    if dim_key in sp:
                        existing[dim_key] = max(float(existing.get(dim_key, 0)), float(sp[dim_key]))
    merged.sort(key=lambda s: float(s['rf']))
    return merged


def _inject_cospot_lanes(lanes: list[dict], rf_tol: float = 0.015) -> list[dict]:
    """Populate explicit `cospot_of` lanes or automatically insert an `SM + Rxn` co-spot lane."""
    out = [deepcopy(lane) for lane in lanes]
    if not out:
        return out

    label_to_idx = {str(lane.get('label', '')).strip().lower(): idx for idx, lane in enumerate(out)}
    has_explicit_cospot = False

    for lane in out:
        cospot_refs = lane.get('cospot_of')
        if cospot_refs and isinstance(cospot_refs, (list, tuple)) and len(cospot_refs) >= 2:
            has_explicit_cospot = True
            source_spot_lists: list[list[dict]] = []
            for ref in cospot_refs:
                if isinstance(ref, int) and 0 <= ref < len(out):
                    source_spot_lists.append(out[ref].get('spots', []))
                elif isinstance(ref, str) and ref.strip().lower() in label_to_idx:
                    source_spot_lists.append(out[label_to_idx[ref.strip().lower()]].get('spots', []))
            if lane.get('spots'):
                source_spot_lists.append(lane['spots'])
            lane['spots'] = _merge_spot_lists(source_spot_lists, rf_tol=rf_tol)
            if not lane.get('label'):
                lane['label'] = 'SM + Rxn'

    if has_explicit_cospot or len(out) < 2:
        return out

    # Check if a co-spot lane is already present by label
    for lane in out:
        lbl_low = str(lane.get('label', '')).strip().lower()
        if 'cospot' in lbl_low or 'co-spot' in lbl_low or 'sm + rxn' in lbl_low or 'sm+rxn' in lbl_low:
            if not lane.get('spots') and len(out) >= 2:
                lane['spots'] = _merge_spot_lists([out[0].get('spots', []), out[-1].get('spots', [])], rf_tol=rf_tol)
            return out

    sm_idx = 0
    rxn_idx = 1
    for idx, lane in enumerate(out):
        lbl = str(lane.get('label', '')).strip().lower()
        if any(k in lbl for k in ('sm', 'starting', 'substrate', 'reactant')):
            sm_idx = idx
            break
    for idx, lane in enumerate(out):
        if idx == sm_idx:
            continue
        lbl = str(lane.get('label', '')).strip().lower()
        if any(k in lbl for k in ('rxn', 'reaction', 'crude', 'mix')):
            rxn_idx = idx
            break
    else:
        rxn_idx = 1 if sm_idx == 0 else 0

    merged_spots = _merge_spot_lists(
        [out[sm_idx].get('spots', []), out[rxn_idx].get('spots', [])],
        rf_tol=rf_tol,
    )
    cospot_lane = {
        'label': 'SM + Rxn',
        'spots': merged_spots,
        'cospot_of': [sm_idx, rxn_idx],
    }
    insert_pos = min(max(sm_idx, rxn_idx), len(out))
    out.insert(insert_pos, cospot_lane)
    return out


def _render_single_1d_plate(d: Drawing, spec: dict, x: float, y: float) -> dict:
    raw_lanes = spec.get('lanes', [])
    if spec.get('auto_cospot') or any(isinstance(l, dict) and l.get('cospot_of') for l in raw_lanes):
        rf_tol = float(spec.get('cospot_rf_tol', 0.015))
        lanes = _inject_cospot_lanes(raw_lanes, rf_tol=rf_tol)
    else:
        lanes = [deepcopy(l) for l in raw_lanes]

    if not 1 <= len(lanes) <= 24:
        raise ValueError('Provide 1..24 TLC lanes')
    width = number(spec.get('width', max(150, 60 * len(lanes))), 'width', 60, 1500)
    height = number(spec.get('height', 210), 'height', 60, 1500)
    origin = number(spec.get('origin_fraction', 0.1), 'origin_fraction', 0, 0.4)
    front = number(spec.get('front_fraction', 0.1), 'front_fraction', 0, 0.4)

    plate = d.add('tlcplate', {
        'TopLeft': f'{x} {y}',
        'TopRight': f'{x + width} {y}',
        'BottomLeft': f'{x} {y + height}',
        'BottomRight': f'{x + width} {y + height}',
        'BoundingBox': f'{x} {y} {x + width} {y + height}',
        'OriginFraction': origin,
        'SolventFrontFraction': front,
        'ShowOrigin': 'yes',
        'ShowSolventFront': 'yes',
        'ShowBorders': 'yes',
    })

    for index, lane in enumerate(lanes):
        node = d.add('tlclane', {}, plate)
        spots = lane.get('spots', [])
        if len(spots) > 100:
            raise ValueError('At most 100 spots per lane')
        for spot in spots:
            spot_attrs = {
                'Rf': number(spot['rf'], 'Rf', 0, 1),
                # TLC dimensions use raw 16.16 integers even in native CDXML.
                'Width': round(65536 * number(spot.get('width', 8), 'spot width', 0.1, width / len(lanes))),
                'Height': round(65536 * number(spot.get('height', 5), 'spot height', 0.1, height)),
                'Tail': round(65536 * number(spot.get('tail', 0), 'tail', 0, height)),
                'CurveType': '128' if spot.get('filled', True) else '0',
                'ShowRf': 'yes' if spec.get('show_rf', True) else 'no',
            }
            spot_hex = _resolve_spot_color_hex(spec, spot)
            if spot_hex is not None:
                spot_attrs['color'] = d.color(spot_hex)
            d.add('tlcspot', spot_attrs, node)
        d.text([x + width * (index + 0.5) / len(lanes) - 10, y + height + 15], lane.get('label', str(index + 1)), 8)

    solvent_label = spec.get('solvent', 'Solvent system not supplied')
    stain_key = str(spec.get('stain') or spec.get('visualization') or '').strip().lower()
    if stain_key in TLC_VISUALIZATION_PALETTES:
        solvent_label = f"{solvent_label} ({TLC_VISUALIZATION_PALETTES[stain_key]['label']})"
    d.text([x, y + height + 35], solvent_label, 9)
    return {'lanes': lanes, 'width': width, 'height': height}


def _draw_2d_tlc(spec: dict, output=None) -> dict:
    size = number(spec.get('width', spec.get('size', 220)), 'width', 80, 1500)
    height = number(spec.get('height', size), 'height', 80, 1500)
    origin = number(spec.get('origin_fraction', 0.12), 'origin_fraction', 0, 0.4)
    front = number(spec.get('front_fraction', 0.10), 'front_fraction', 0, 0.4)

    d = Drawing(int(size + 130), int(height + 120))
    d.text([45, 20], spec.get('title', '2D TLC Plate'), 11)
    x, y = 55.0, 40.0

    plate = d.add('tlcplate', {
        'TopLeft': f'{x} {y}',
        'TopRight': f'{x + size} {y}',
        'BottomLeft': f'{x} {y + height}',
        'BottomRight': f'{x + size} {y + height}',
        'BoundingBox': f'{x} {y} {x + size} {y + height}',
        'OriginFraction': origin,
        'SolventFrontFraction': front,
        'ShowOrigin': 'yes',
        'ShowSolventFront': 'yes',
        'ShowBorders': 'yes',
    })
    lane_node = d.add('tlclane', {}, plate)

    x_orig = x + size * origin
    x_front = x + size * (1.0 - front)
    y_orig = y + height * (1.0 - origin)
    y_front = y + height * front

    # Dashed diagonal reference line (rf1 == rf2) for on-silica stability check
    d.line([x_orig, y_orig], [x_front, y_front], color='#757575', dashed=True)
    d.text([x_orig + 8, y_front + 12], 'rf1 = rf2 (diagonal)', 7, color='#757575')

    # 1st dimension vertical arrow (left margin, bottom -> top)
    solv1 = spec.get('solvent_1') or spec.get('first_dimension') or spec.get('solvent', '1st eluent')
    d.line([x - 16, y_orig], [x - 16, y_front])
    d.add('arrow', {
        'BoundingBox': f'{x - 19} {y_front} {x - 13} {y_orig}',
        'Tail3D': f'{x - 16} {y_orig} 0',
        'Head3D': f'{x - 16} {y_front} 0',
        'ArrowheadType': 'Full',
        'ArrowheadHead': 'Full',
    })
    d.text([8, y + height * 0.5], f'1st: {solv1}', 8)

    # 2nd dimension horizontal arrow (bottom margin, left -> right)
    solv2 = spec.get('solvent_2') or spec.get('second_dimension') or solv1
    d.line([x_orig, y + height + 18], [x_front, y + height + 18])
    d.add('arrow', {
        'BoundingBox': f'{x_orig} {y + height + 15} {x_front} {y + height + 21}',
        'Tail3D': f'{x_orig} {y + height + 18} 0',
        'Head3D': f'{x_front} {y + height + 18} 0',
        'ArrowheadType': 'Full',
        'ArrowheadHead': 'Full',
    })
    d.text([x_orig, y + height + 34], f'2nd: {solv2}', 8)

    raw_spots = list(spec.get('spots', []))
    if not raw_spots:
        for lane in spec.get('lanes', []):
            raw_spots.extend(lane.get('spots', []))

    off_diagonal_count = 0
    for idx, spot in enumerate(raw_spots):
        rf_pair = spot.get('rf')
        if isinstance(rf_pair, (list, tuple)) and len(rf_pair) == 2:
            rf1 = number(rf_pair[0], 'Rf1', 0, 1)
            rf2 = number(rf_pair[1], 'Rf2', 0, 1)
        else:
            rf1 = number(spot.get('rf1', spot.get('rf', 0.5)), 'Rf1', 0, 1)
            rf2 = number(spot.get('rf2', rf1), 'Rf2', 0, 1)

        if abs(rf1 - rf2) > 0.03:
            off_diagonal_count += 1

        sx = x_orig + rf2 * (x_front - x_orig)
        sy = y_orig - rf1 * (y_orig - y_front)
        r_pt = number(spot.get('radius', 4.5), 'spot radius', 0.5, 40)
        spot_hex = _resolve_spot_color_hex(spec, spot) or '#1b5e20'
        color_idx = d.color(spot_hex)

        circle_pts = [
            [sx + r_pt * math.cos(2.0 * math.pi * k / 12), sy + r_pt * math.sin(2.0 * math.pi * k / 12)]
            for k in range(12)
        ]
        d.curve(circle_pts, closed=True, filled=spot.get('filled', True), color=color_idx)

        spot_attrs = {
            'Rf': rf1,
            'Rf2': rf2,
            'Width': round(65536 * number(spot.get('width', 8), 'spot width', 0.1, size)),
            'Height': round(65536 * number(spot.get('height', 5), 'spot height', 0.1, height)),
            'Tail': round(65536 * number(spot.get('tail', 0), 'tail', 0, height)),
            'CurveType': '128' if spot.get('filled', True) else '0',
            'ShowRf': 'yes' if spec.get('show_rf', True) else 'no',
            'color': color_idx,
        }
        d.add('tlcspot', spot_attrs, lane_node)
        lbl = spot.get('label') or f'({rf1:.2f}, {rf2:.2f})'
        d.text([sx + r_pt + 3, sy + 3], str(lbl), 7, color=color_idx)

    xml_str = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
        + ET.tostring(d.root, encoding='unicode')
    )
    saved = d.save(output) if output is not None else None
    return {
        'output_path': saved,
        'cdxml': xml_str,
        'mode': '2d',
        'lane_count': 1,
        'spot_count': len(raw_spots),
        'off_diagonal_spots': off_diagonal_count,
        'measurement_basis': spec.get('measurement_basis', 'provided 2D (Rf1, Rf2) values'),
        'quantitative_purity': 'not inferred from spot size or intensity',
    }


def draw_tlc(spec, output=None):
    mode = str(spec.get('mode', '1d')).strip().lower()
    if mode == '2d' or spec.get('two_dimensional'):
        return _draw_2d_tlc(spec, output)

    plates = spec.get('plates')
    if plates and isinstance(plates, list):
        if not 1 <= len(plates) <= 8:
            raise ValueError('Provide 1..8 TLC plates for multi-eluent comparison')
        plate_widths = []
        max_h = 210.0
        for p_spec in plates:
            p_lanes = p_spec.get('lanes', spec.get('lanes', []))
            n_l = max(len(p_lanes), 1) + (1 if (p_spec.get('auto_cospot') or spec.get('auto_cospot')) else 0)
            pw = number(p_spec.get('width', spec.get('width', max(150, 60 * n_l))), 'width', 60, 1500)
            ph = number(p_spec.get('height', spec.get('height', 210)), 'height', 60, 1500)
            plate_widths.append(pw)
            max_h = max(max_h, ph)
        gap = 50.0
        total_w = sum(plate_widths) + gap * (len(plates) - 1) + 80.0
        d = Drawing(int(total_w), int(max_h + 110))
        d.text([25, 20], spec.get('title', 'Multi-Eluent TLC Comparison'), 11)
        cur_x = 30.0
        total_lanes = 0
        for idx, p_spec in enumerate(plates):
            merged_p = {**spec, **p_spec}
            merged_p.pop('plates', None)
            if p_spec.get('title'):
                d.text([cur_x, 34], str(p_spec['title']), 9)
            info = _render_single_1d_plate(d, merged_p, cur_x, 45.0)
            cur_x += info['width'] + gap
            total_lanes += len(info['lanes'])
        xml_str = (
            '<?xml version="1.0" encoding="UTF-8" ?>\n'
            '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
            + ET.tostring(d.root, encoding='unicode')
        )
        saved = d.save(output) if output is not None else None
        return {
            'output_path': saved,
            'cdxml': xml_str,
            'plate_count': len(plates),
            'lane_count': total_lanes,
            'measurement_basis': spec.get('measurement_basis', 'provided Rf values'),
            'quantitative_purity': 'not inferred from spot size or intensity',
        }

    raw_lanes = spec.get('lanes', [])
    if spec.get('auto_cospot') or any(isinstance(l, dict) and l.get('cospot_of') for l in raw_lanes):
        lanes_preview = _inject_cospot_lanes(raw_lanes, rf_tol=float(spec.get('cospot_rf_tol', 0.015)))
    else:
        lanes_preview = raw_lanes
    if not 1 <= len(lanes_preview) <= 24:
        raise ValueError('Provide 1..24 TLC lanes')
    width = number(spec.get('width', max(150, 60 * len(lanes_preview))), 'width', 60, 1500)
    height = number(spec.get('height', 210), 'height', 60, 1500)
    d = Drawing(width + 80, height + 100)
    d.text([25, 20], spec.get('title', 'TLC plate'))
    info = _render_single_1d_plate(d, {**spec, 'lanes': lanes_preview, 'width': width, 'height': height}, 30, 40)
    xml_str = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
        + ET.tostring(d.root, encoding='unicode')
    )
    saved = d.save(output) if output is not None else None
    return {
        'output_path': saved,
        'cdxml': xml_str,
        'lane_count': len(info['lanes']),
        'measurement_basis': spec.get('measurement_basis', 'provided Rf values'),
        'quantitative_purity': 'not inferred from spot size or intensity',
    }


build_tlc_cdxml = draw_tlc
