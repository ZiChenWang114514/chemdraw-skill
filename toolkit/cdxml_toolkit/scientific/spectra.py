"""Auditable 1D spectral peak picking and integration without guessed assignments."""
import contextlib
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple, Union
import numpy as np
from scipy.signal import find_peaks
from .common import Drawing, number


# Known residual solvent peaks in 1H and 13C NMR (ppm).
SOLVENT_ALIASES = {
    'cdcl3': 'CDCl3',
    'chloroform': 'CDCl3',
    'chloroformd': 'CDCl3',
    'trichloromethane': 'CDCl3',
    'dmsod6': 'DMSO-d6',
    'dmso': 'DMSO-d6',
    'dimethylsulfoxide': 'DMSO-d6',
    'dimethylsulfoxided6': 'DMSO-d6',
    'cd3od': 'CD3OD',
    'meod': 'CD3OD',
    'methanold4': 'CD3OD',
    'methanol': 'CD3OD',
    'cd3cn': 'CD3CN',
    'acnd3': 'CD3CN',
    'acetonitriled3': 'CD3CN',
    'acetonitrile': 'CD3CN',
    'c6d6': 'C6D6',
    'benzened6': 'C6D6',
    'benzene': 'C6D6',
    'acetoned6': 'Acetone-d6',
    'acetone': 'Acetone-d6',
    'cd3cocd3': 'Acetone-d6',
    'd2o': 'D2O',
    'water': 'D2O',
    'deuteriumoxide': 'D2O',
    'cd2cl2': 'CD2Cl2',
    'dcmd2': 'CD2Cl2',
    'dichloromethaned2': 'CD2Cl2',
    'dichloromethane': 'CD2Cl2',
    'thfd8': 'THF-d8',
    'thf': 'THF-d8',
    'tetrahydrofurand8': 'THF-d8',
    'tetrahydrofuran': 'THF-d8',
    'toluened8': 'Toluene-d8',
    'toluene': 'Toluene-d8',
}

RESIDUAL_SOLVENT_PEAKS = {
    '1H': {
        'CDCl3': [7.26],
        'DMSO-d6': [2.50],
        'CD3OD': [3.31],
        'CD3CN': [1.94],
        'C6D6': [7.16],
        'Acetone-d6': [2.05],
        'D2O': [4.79],
        'CD2Cl2': [5.32],
        'THF-d8': [3.58, 1.72],
        'Toluene-d8': [2.08, 6.97, 7.01, 7.09],
    },
    '13C': {
        'CDCl3': [77.16],
        'DMSO-d6': [39.52],
        'CD3OD': [49.00],
        'CD3CN': [1.32, 118.26],
        'C6D6': [128.06],
        'Acetone-d6': [29.84, 206.26],
        'CD2Cl2': [53.84],
        'THF-d8': [67.21, 25.31],
        'Toluene-d8': [20.43, 125.13, 127.96, 128.87, 137.48],
    },
}


def _clean_tag(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if value is None:
        return None
    text = str(value).strip().strip('<>').replace('^', '').strip()
    return text or None


def _normalize_solvent(solvent):
    tag = _clean_tag(solvent)
    if not tag:
        return None
    key = re.sub(r'[^a-z0-9]+', '', tag.lower())
    return SOLVENT_ALIASES.get(key, tag)


def _normalize_nucleus(nucleus, ppm_axis=None):
    tag = _clean_tag(nucleus)
    if tag:
        upper = tag.upper()
        if '13C' in upper or upper == 'C13' or upper == 'C':
            return '13C'
        if '1H' in upper or upper in ('H1', 'H', 'PROTON'):
            return '1H'
        return tag
    if ppm_axis is not None and len(ppm_axis) > 0:
        span_max = float(np.nanmax(ppm_axis))
        if span_max > 35.0:
            return '13C'
    return '1H'


def _hash_source(path: Path) -> str:
    path = Path(path)
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        digest = hashlib.sha256()
        files = sorted(p for p in path.rglob('*') if p.is_file())
        for f in files[:64]:
            digest.update(f.name.encode('utf-8', errors='replace'))
            digest.update(f.read_bytes())
        return digest.hexdigest()
    raise ValueError(f'Spectrum path does not exist: {path}')


def _process_raw_fid(data, sw_hz, nucleus='1H', digital_filter_removed=False, source_format='bruker_fid'):
    import nmrglue as ng
    data = np.asarray(data)
    if not np.iscomplexobj(data):
        data = data.astype(np.complex128)
    nuc = _normalize_nucleus(nucleus)
    lb_hz = 1.0 if nuc == '13C' else 0.3
    sw = float(sw_hz) if sw_hz and float(sw_hz) > 0 else 4000.0
    data = ng.proc_base.em(data, lb=lb_hz / sw)
    next_pow2 = 1 << max(int(np.ceil(np.log2(max(len(data), 16)))), 1)
    target_size = next_pow2 * 2 if next_pow2 == len(data) else next_pow2
    target_size = min(max(target_size, len(data)), 262144)
    if target_size > len(data):
        data = ng.proc_base.zf_size(data, target_size)
    else:
        data = ng.proc_base.zf_auto(data)
    data = ng.proc_base.fft(data)
    ps0, ps1 = 0.0, 0.0
    autophase_method = 'acme'
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                phased, phases = ng.proc_autophase.autops(data, 'acme', return_phases=True, disp=False)
            except TypeError:
                phased, phases = ng.proc_autophase.autops(data, 'acme', return_phases=True)
        phased = np.asarray(phased)
        if phased.shape == data.shape and np.isfinite(phased).all():
            data = phased
            ps0, ps1 = float(phases[0]), float(phases[1])
        else:
            autophase_method = 'fallback_zero'
    except Exception:
        autophase_method = 'fallback_zero'
    real_spec = np.real(data).astype(float)
    if len(real_spec) > 0 and abs(float(np.min(real_spec))) > 1.2 * abs(float(np.max(real_spec))):
        real_spec = -real_spec
        ps0 = (ps0 + 180.0) % 360.0
    proc_meta = {
        'source_format': source_format,
        'digital_filter_removed': bool(digital_filter_removed),
        'line_broadening_hz': float(lb_hz),
        'zero_fill_size': int(len(real_spec)),
        'fft': True,
        'autophase_method': autophase_method,
        'ps0': round(ps0, 3),
        'ps1': round(ps1, 3),
    }
    return real_spec, proc_meta


def _find_bruker_pdata_dir(path: Path):
    if path.is_file() and path.name == '1r':
        return path.parent
    if path.is_dir():
        if (path / '1r').is_file():
            return path
        pdata = path / 'pdata'
        if pdata.is_dir():
            if (pdata / '1' / '1r').is_file():
                return pdata / '1'
            candidates = sorted(
                (d for d in pdata.iterdir() if d.is_dir() and (d / '1r').is_file()),
                key=lambda d: (0, int(d.name)) if d.name.isdigit() else (1, d.name),
            )
            if candidates:
                return candidates[0]
    return None


def _find_bruker_fid_dir(path: Path):
    if path.is_file() and path.name in ('fid', 'ser'):
        parent = path.parent
        if (parent / 'acqus').is_file() or (parent / 'acqu').is_file():
            return parent
    if path.is_dir():
        has_fid = (path / 'fid').is_file() or (path / 'ser').is_file()
        has_acq = (path / 'acqus').is_file() or (path / 'acqu').is_file()
        if has_fid and has_acq:
            return path
    return None


def _find_varian_dir(path: Path):
    if path.is_file() and path.name == 'fid' and (path.parent / 'procpar').is_file():
        return path.parent
    if path.is_dir():
        if (path / 'fid').is_file() and (path / 'procpar').is_file():
            return path
    return None


def _bruker_ppm_scale(ng, dic, size):
    dummy = np.zeros(int(size), dtype=float)
    udic = ng.bruker.guess_udic(dic, dummy, strip_fake=True)
    udic[0]['size'] = int(size)
    acqus = dic.get('acqus') or {}
    procs = dic.get('procs') or {}
    if udic[0].get('sw', 999.99) == 999.99:
        if 'SW_p' in procs:
            udic[0]['sw'] = float(procs['SW_p'])
        elif 'SW_h' in acqus:
            udic[0]['sw'] = float(acqus['SW_h'])
    if udic[0].get('obs', 100.0) == 100.0:
        if 'SF' in procs and float(procs['SF']) > 0:
            udic[0]['obs'] = float(procs['SF'])
        elif 'SFO1' in acqus and float(acqus['SFO1']) > 0:
            udic[0]['obs'] = float(acqus['SFO1'])
    if udic[0].get('car', 999.99) == 999.99:
        obs = float(udic[0].get('obs') or 400.0)
        sw = float(udic[0].get('sw') or 4000.0)
        if 'OFFSET' in procs:
            udic[0]['car'] = float(procs['OFFSET']) * obs - sw / 2.0
        elif 'O1' in acqus:
            udic[0]['car'] = float(acqus['O1'])
        else:
            udic[0]['car'] = 0.0
    uc = ng.fileiobase.uc_from_udic(udic)
    return uc.ppm_scale().astype(float), udic


def _read_spectrum_with_meta(path):
    path = Path(path)
    suffix = path.suffix.lower()

    if path.is_file() and suffix == '.csv':
        values = np.genfromtxt(path, delimiter=',', names=True, encoding='utf-8-sig')
        if not {'ppm', 'intensity'} <= set(values.dtype.names or ()):
            raise ValueError('CSV requires ppm,intensity columns')
        x = np.atleast_1d(values['ppm']).astype(float)
        y = np.atleast_1d(values['intensity']).astype(float)
        return x, y, {'format': 'csv'}

    if path.is_file() and suffix in ('.ft', '.ft1', '.ft2'):
        import nmrglue as ng
        dic, data = ng.pipe.read(str(path))
        if data.ndim != 1 or np.iscomplexobj(data):
            raise ValueError('Provide a processed real 1D spectrum')
        x = ng.pipe.make_uc(dic, data).ppm_scale().astype(float)
        y = data.astype(float)
        udic = ng.pipe.guess_udic(dic, data)
        obs = udic[0].get('obs')
        label = _clean_tag(udic[0].get('label'))
        meta = {'format': 'nmrpipe'}
        if obs and float(obs) > 0 and float(obs) != 100.0:
            meta['frequency_mhz'] = float(obs)
        if label:
            meta['nucleus'] = _normalize_nucleus(label, x)
        return x, y, meta

    if path.is_file() and suffix in ('.jdx', '.dx'):
        import nmrglue as ng
        dic, data = ng.jcampdx.read(str(path))
        udic = ng.jcampdx.guess_udic(dic, data)
        obs = udic[0].get('obs')
        if (obs is None or float(obs) == 100.0) and '.OBSERVEFREQUENCY' in dic:
            try:
                obs = float(dic['.OBSERVEFREQUENCY'][0])
            except Exception:
                pass
        if (obs is None or float(obs) == 100.0) and '$SFO1' in dic:
            try:
                obs = float(dic['$SFO1'][0])
            except Exception:
                pass
        obs_mhz = float(obs) if obs and float(obs) > 0 else None
        nucleus = _clean_tag(
            dic.get('.OBSERVENUCLEUS') or dic.get('$NUC1') or udic[0].get('label')
        )
        solvent = _normalize_solvent(
            dic.get('.SOLVENTNAME') or dic.get('.SOLVENTREFERENCE') or dic.get('$SOLVENT') or dic.get('SOLVENT')
        )
        dtype_vals = dic.get('DATATYPE') or dic.get('DATA TYPE') or []
        dtype_str = ' '.join(str(v) for v in (dtype_vals if isinstance(dtype_vals, list) else [dtype_vals])).upper()
        xunits_vals = dic.get('XUNITS') or []
        xunits_str = ' '.join(str(v) for v in (xunits_vals if isinstance(xunits_vals, list) else [xunits_vals])).upper()
        raw_proc = None
        if isinstance(data, list):
            if len(data) >= 2 and ('FID' in dtype_str or 'SEC' in xunits_str or 'TIME' in dtype_str):
                complex_fid = np.asarray(data[0], dtype=float) + 1j * np.asarray(data[1], dtype=float)
                sw_hz = float(udic[0].get('sw') or 4000.0)
                y, raw_proc = _process_raw_fid(
                    complex_fid, sw_hz, nucleus=nucleus or '1H',
                    digital_filter_removed=False, source_format='jcampdx_fid'
                )
            else:
                y = np.asarray(data[0], dtype=float)
        else:
            arr = np.asarray(data)
            if arr.ndim == 2 and arr.shape[0] in (1, 2):
                arr = arr[0]
            if arr.ndim != 1:
                raise ValueError('Provide a 1D JCAMP-DX spectrum')
            if np.iscomplexobj(arr):
                if 'FID' in dtype_str or 'SEC' in xunits_str:
                    sw_hz = float(udic[0].get('sw') or 4000.0)
                    y, raw_proc = _process_raw_fid(
                        arr, sw_hz, nucleus=nucleus or '1H',
                        digital_filter_removed=False, source_format='jcampdx_fid'
                    )
                else:
                    y = np.real(arr).astype(float)
            else:
                y = arr.astype(float)

        firstx, lastx, isppm = ng.jcampdx._find_firstx_lastx(dic)
        if firstx is not None and lastx is None and 'DELTAX' in dic:
            try:
                lastx = float(firstx) + float(dic['DELTAX'][0]) * (len(y) - 1)
            except Exception:
                pass
        if firstx is not None and lastx is not None:
            fx, lx = float(firstx), float(lastx)
            if isppm:
                first_ppm, last_ppm = fx, lx
            elif ('HZ' in xunits_str or '1/S' in xunits_str or abs(fx) > 250.0) and obs_mhz:
                first_ppm, last_ppm = fx / obs_mhz, lx / obs_mhz
            else:
                first_ppm, last_ppm = fx, lx
            x = np.linspace(first_ppm, last_ppm, len(y), dtype=float)
        elif udic[0].get('sw') and obs_mhz:
            sw_ppm = float(udic[0]['sw']) / obs_mhz
            car_ppm = float(udic[0].get('car', 0.0)) / obs_mhz
            x = np.linspace(car_ppm + sw_ppm / 2.0, car_ppm - sw_ppm / 2.0, len(y), dtype=float)
        else:
            raise ValueError('JCAMP-DX file lacks calibrated X-axis metadata (FIRSTX/LASTX)')

        meta = {'format': 'jcampdx'}
        if obs_mhz:
            meta['frequency_mhz'] = obs_mhz
        if nucleus:
            meta['nucleus'] = _normalize_nucleus(nucleus, x)
        if solvent:
            meta['solvent'] = solvent
        if raw_proc:
            meta['raw_processing'] = raw_proc
        return x, y, meta

    if path.is_file() and suffix == '.jdf':
        import nmrglue as ng
        dic, data = ng.jeol.read(str(path))
        data = np.squeeze(np.asarray(data))
        if data.ndim != 1:
            raise ValueError('Provide a 1D JEOL spectrum')
        udic = ng.jeol.guess_udic(dic, data)
        obs = udic[0].get('obs')
        obs_mhz = float(obs) if obs and float(obs) > 0 and float(obs) != 100.0 else 400.0
        sw_hz = float(udic[0].get('sw') or 4000.0)
        nucleus = _clean_tag(udic[0].get('label'))
        solvent = _normalize_solvent((dic.get('param') or {}).get('solvent'))
        raw_proc = None
        if np.iscomplexobj(data) and udic[0].get('time', True):
            y, raw_proc = _process_raw_fid(
                data, sw_hz, nucleus=nucleus or '1H',
                digital_filter_removed=False, source_format='jeol_jdf'
            )
        else:
            y = np.real(data).astype(float)
        udic[0]['size'] = len(y)
        udic[0].setdefault('complex', True)
        udic[0].setdefault('car', 0.0)
        if udic[0].get('obs', 100.0) == 100.0:
            udic[0]['obs'] = obs_mhz
        if udic[0].get('sw', 999.99) == 999.99:
            udic[0]['sw'] = sw_hz
        x = ng.fileiobase.uc_from_udic(udic).ppm_scale().astype(float)
        meta = {'format': 'jeol', 'frequency_mhz': obs_mhz}
        if nucleus:
            meta['nucleus'] = _normalize_nucleus(nucleus, x)
        if solvent:
            meta['solvent'] = solvent
        if raw_proc:
            meta['raw_processing'] = raw_proc
        return x, y, meta

    # Varian / Agilent (.fid directory or fid + procpar)
    varian_dir = _find_varian_dir(path)
    if varian_dir is not None:
        import nmrglue as ng
        dic, data = ng.varian.read(str(varian_dir))
        data = np.squeeze(np.asarray(data))
        if data.ndim != 1:
            raise ValueError('Provide a 1D Varian FID')
        udic = ng.varian.guess_udic(dic, data)
        procpar = dic.get('procpar') or {}
        def _pval(k):
            vals = (procpar.get(k) or {}).get('values')
            return vals[0] if vals else None
        sfrq = _pval('sfrq')
        sw_val = _pval('sw')
        tn = _pval('tn')
        solv = _normalize_solvent(_pval('solvent'))
        obs_mhz = float(sfrq) if sfrq is not None else float(udic[0].get('obs') or 400.0)
        sw_hz = float(sw_val) if sw_val is not None else float(udic[0].get('sw') or 4000.0)
        nucleus = _clean_tag(tn or udic[0].get('label')) or '1H'
        y, raw_proc = _process_raw_fid(
            data, sw_hz, nucleus=nucleus,
            digital_filter_removed=False, source_format='varian_fid'
        )
        udic[0]['size'] = len(y)
        udic[0].setdefault('complex', True)
        udic[0]['obs'] = obs_mhz
        udic[0]['sw'] = sw_hz
        if udic[0].get('car', 999.99) == 999.99:
            rfp = _pval('rfp')
            rfl = _pval('rfl')
            if rfp is not None and rfl is not None:
                udic[0]['car'] = sw_hz / 2.0 - (float(rfl) - float(rfp))
            else:
                udic[0]['car'] = obs_mhz * 4.5 if _normalize_nucleus(nucleus) == '1H' else obs_mhz * 100.0
        x = ng.fileiobase.uc_from_udic(udic).ppm_scale().astype(float)
        meta = {
            'format': 'varian_fid',
            'frequency_mhz': obs_mhz,
            'nucleus': _normalize_nucleus(nucleus, x),
            'raw_processing': raw_proc,
        }
        if solv:
            meta['solvent'] = solv
        return x, y, meta

    # Bruker: check if caller pointed directly at an 'fid' file first, otherwise processed pdata/1r, then dataset raw fid
    if path.is_file() and path.name in ('fid', 'ser'):
        pdata_dir = None
        bruker_fid_dir = _find_bruker_fid_dir(path)
    else:
        pdata_dir = _find_bruker_pdata_dir(path)
        bruker_fid_dir = None if pdata_dir is not None else _find_bruker_fid_dir(path)

    if pdata_dir is not None:
        import nmrglue as ng
        dic, data = ng.bruker.read_pdata(str(pdata_dir))
        data = np.squeeze(np.asarray(data, dtype=float))
        if data.ndim != 1:
            raise ValueError('Provide a 1D Bruker processed spectrum')
        x, udic = _bruker_ppm_scale(ng, dic, len(data))
        acqus = dic.get('acqus') or {}
        procs = dic.get('procs') or {}
        obs = procs.get('SF') or acqus.get('SFO1') or acqus.get('BF1') or udic[0].get('obs')
        obs_mhz = float(obs) if obs and float(obs) > 0 and float(obs) != 100.0 else None
        nucleus = _clean_tag(acqus.get('NUC1') or procs.get('AXNUC') or udic[0].get('label'))
        solvent = _normalize_solvent(acqus.get('SOLVENT'))
        meta = {'format': 'bruker_pdata'}
        if obs_mhz:
            meta['frequency_mhz'] = obs_mhz
        if nucleus:
            meta['nucleus'] = _normalize_nucleus(nucleus, x)
        if solvent:
            meta['solvent'] = solvent
        return x, data, meta

    if bruker_fid_dir is not None:
        import nmrglue as ng
        dic, data = ng.bruker.read(str(bruker_fid_dir))
        data = np.squeeze(np.asarray(data))
        if data.ndim != 1:
            raise ValueError('Provide a 1D Bruker FID')
        acqus = dic.get('acqus') or {}
        udic = ng.bruker.guess_udic(dic, data)
        obs = acqus.get('SFO1') or acqus.get('BF1') or udic[0].get('obs')
        obs_mhz = float(obs) if obs and float(obs) > 0 and float(obs) != 100.0 else 400.0
        sw_hz = float(acqus.get('SW_h') or udic[0].get('sw') or (float(acqus.get('SW', 10.0)) * obs_mhz))
        nucleus = _clean_tag(acqus.get('NUC1') or udic[0].get('label')) or '1H'
        solvent = _normalize_solvent(acqus.get('SOLVENT'))
        df_removed = False
        if any(k in acqus for k in ('DSPFVS', 'DECIM', 'GRPDLY')) and (
            float(acqus.get('GRPDLY', 0) or 0) > 0 or int(acqus.get('DECIM', 0) or 0) > 1
        ):
            try:
                data = ng.bruker.remove_digital_filter(dic, data)
                df_removed = True
            except Exception:
                df_removed = False
        y, raw_proc = _process_raw_fid(
            data, sw_hz, nucleus=nucleus,
            digital_filter_removed=df_removed, source_format='bruker_fid'
        )
        x, _ = _bruker_ppm_scale(ng, dic, len(y))
        meta = {
            'format': 'bruker_fid',
            'frequency_mhz': obs_mhz,
            'nucleus': _normalize_nucleus(nucleus, x),
            'raw_processing': raw_proc,
        }
        if solvent:
            meta['solvent'] = solvent
        return x, y, meta

    raise ValueError(
        'Supported spectra: CSV, 1D NMRPipe (.ft/.ft1/.ft2), JCAMP-DX (.jdx/.dx), '
        'Bruker 1D (1r/pdata or raw fid), JEOL (.jdf), and Varian (.fid)'
    )


def read_spectrum(path):
    x, y, _ = _read_spectrum_with_meta(path)
    return x, y


load_nmr_spectrum = read_spectrum


def _flag_solvent_peaks(peaks, solvent, nucleus):
    norm_solvent = _normalize_solvent(solvent)
    if not norm_solvent:
        return [], []
    nuc = '13C' if nucleus == '13C' else '1H'
    refs = RESIDUAL_SOLVENT_PEAKS.get(nuc, {}).get(norm_solvent, [])
    if not refs:
        return [], []
    tol = 0.6 if nuc == '13C' else 0.06
    flagged = []
    flagged_indices = []
    for idx, pk in enumerate(peaks):
        ppm = pk['ppm']
        matched_ref = min(refs, key=lambda r: abs(ppm - r))
        if abs(ppm - matched_ref) <= tol:
            flagged.append({
                'ppm': pk['ppm'],
                'intensity': pk['intensity'],
                'prominence': pk['prominence'],
                'solvent': norm_solvent,
                'reference_ppm': matched_ref,
                'nucleus': nuc,
            })
            flagged_indices.append(idx)
    return flagged, flagged_indices


def _group_multiplets(peaks, frequency_mhz, max_j_hz=20.0):
    if not frequency_mhz or float(frequency_mhz) <= 0 or not peaks:
        return []
    freq = float(frequency_mhz)
    ordered = sorted(peaks, key=lambda p: p['ppm'])
    clusters = [[ordered[0]]]
    for pk in ordered[1:]:
        sep_hz = abs(pk['ppm'] - clusters[-1][-1]['ppm']) * freq
        if sep_hz <= max_j_hz:
            clusters[-1].append(pk)
        else:
            clusters.append([pk])

    multiplets = []
    for cluster in clusters:
        n = len(cluster)
        ppms = np.array([p['ppm'] for p in cluster], dtype=float)
        intensities = np.array([max(float(p['intensity']), 0.0) for p in cluster], dtype=float)
        if intensities.sum() > 0:
            center_ppm = float(np.sum(ppms * intensities) / intensities.sum())
        else:
            center_ppm = float(np.mean(ppms))

        if n == 1:
            mult = 's'
            j_hz = []
        else:
            spacings = [round(float((ppms[i + 1] - ppms[i]) * freq), 2) for i in range(n - 1)]
            mean_j = float(np.mean(spacings))
            j_tol = max(1.5, 0.25 * mean_j)
            uniform_j = all(abs(s - mean_j) <= j_tol for s in spacings)
            if n == 2:
                ratio = float(min(intensities) / max(intensities)) if max(intensities) > 0 else 1.0
                mult = 'd' if ratio >= 0.35 else 'm'
                j_hz = [round(spacings[0], 2)]
            elif n == 3:
                if uniform_j and intensities[1] >= intensities[0] and intensities[1] >= intensities[2]:
                    mult = 't'
                    j_hz = [round(mean_j, 2)]
                else:
                    mult = 'm'
                    j_hz = spacings
            elif n == 4:
                if (
                    uniform_j
                    and min(intensities[1], intensities[2]) >= max(intensities[0], intensities[3])
                ):
                    mult = 'q'
                    j_hz = [round(mean_j, 2)]
                else:
                    mult = 'm'
                    j_hz = spacings
            else:
                mult = 'm'
                j_hz = spacings

        multiplets.append({
            'center_ppm': round(center_ppm, 4),
            'multiplicity': mult,
            'j_hz': j_hz,
            'peak_count': n,
            'peaks': [round(float(p['ppm']), 4) for p in cluster],
        })
    return multiplets


def analyze_spectrum(path, options=None):
    if isinstance(path, dict) and options is None:
        spec_dict = dict(path)
        raw_path = spec_dict.get('path') or spec_dict.get('input') or spec_dict.get('source')
        if raw_path is None:
            raise ValueError('Spectrum dictionary requires a path, input, or source key')
        options = dict(spec_dict.get('processing') or {})
        for k in ('solvent', 'nucleus', 'frequency_mhz', 'exclude_solvent', 'multiplet_max_j_hz',
                  'baseline_windows', 'baseline_degree', 'prominence', 'integration_regions',
                  'normalization_region', 'normalization_value', 'inset_region'):
            if k in spec_dict and k not in options:
                options[k] = spec_dict[k]
        path = raw_path
    elif options is None:
        options = {}

    allowed = {
        'baseline_windows', 'baseline_degree', 'prominence', 'integration_regions',
        'normalization_region', 'normalization_value', 'solvent', 'nucleus',
        'frequency_mhz', 'exclude_solvent', 'multiplet_max_j_hz', 'inset_region',
    }
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError('Unknown spectrum processing options')
    if 'normalization_value' in options and 'normalization_region' not in options:
        raise ValueError('Normalization value requires a reference region')
    path = Path(path).resolve()
    x, y, meta = _read_spectrum_with_meta(path)
    if len(x) < 3 or len(x) > 2000000 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Provide 3..2,000,000 finite spectrum points')
    if len(np.unique(x)) != len(x):
        raise ValueError('Chemical shift values must be unique')
    if not (np.all(np.diff(x) > 0) or np.all(np.diff(x) < 0)):
        raise ValueError('Chemical shift axis must be monotonic')
    order = np.argsort(x)
    x, y = x[order], y[order]

    def bounds(limits):
        if not isinstance(limits, (list, tuple)) or len(limits) != 2:
            raise ValueError('A spectral window needs two boundaries')
        a, b = sorted(number(v, 'window boundary') for v in limits)
        if a < x[0] or b > x[-1] or a == b:
            raise ValueError('Window bounds must lie within the spectrum')
        return a, b

    baseline = np.zeros_like(y)
    windows = options.get('baseline_windows', [])
    if windows:
        if len(windows) > 1000:
            raise ValueError('At most 1000 baseline windows')
        mask = np.zeros(len(x), dtype=bool)
        for limits in windows:
            a, b = bounds(limits)
            mask |= (x >= a) & (x <= b)
        degree = number(options.get('baseline_degree', 1), 'baseline degree', 0, 3)
        if not degree.is_integer():
            raise ValueError('Baseline degree must be an integer')
        degree = int(degree)
        if mask.sum() < max(10, degree + 2):
            raise ValueError('Baseline windows contain too few samples')
        baseline = np.polynomial.Polynomial.fit(x[mask], y[mask], degree)(x)
        y = y - baseline
    prominence = number(options.get('prominence', max(float(np.ptp(y)) * .05, 1e-12)), 'prominence', 1e-15)
    peaks, props = find_peaks(y, prominence=prominence)
    if len(peaks) > 10000:
        raise ValueError('Too many peaks; increase prominence')
    integrals = []
    regions = options.get('integration_regions', [])
    if len(regions) > 1000:
        raise ValueError('At most 1000 integration regions')
    for limits in regions:
        a, b = bounds(limits)
        sel = (x > a) & (x < b)
        xx = np.r_[a, x[sel], b]
        yy = np.interp(xx, x, y)
        area = float(np.trapezoid(yy, xx)) if hasattr(np, 'trapezoid') else float(np.trapz(yy, xx))
        integrals.append({'limits_ppm': [a, b], 'area': area})
    normalization = None
    if 'normalization_region' in options:
        index = options['normalization_region']
        if type(index) is not int or not 0 <= index < len(integrals):
            raise ValueError('Invalid normalization region')
        denominator = integrals[index]['area']
        value = number(options.get('normalization_value', 1), 'normalization value', 1e-15)
        if denominator <= 0:
            raise ValueError('Normalization integral must be positive')
        normalization = {'region': index, 'value': value, 'denominator_area': denominator}
        for integral in integrals:
            integral['normalized'] = integral['area'] / denominator * value

    peak_list = [
        {'ppm': float(x[i]), 'intensity': float(y[i]), 'prominence': float(p)}
        for i, p in zip(peaks, props['prominences'])
    ]

    solvent = options.get('solvent') or meta.get('solvent')
    freq_mhz = options.get('frequency_mhz') or meta.get('frequency_mhz')
    if freq_mhz is not None:
        freq_mhz = number(freq_mhz, 'frequency_mhz', 1.0, 2000.0)
    nucleus = _normalize_nucleus(options.get('nucleus') or meta.get('nucleus'), x)

    solvent_peaks, solvent_indices = _flag_solvent_peaks(peak_list, solvent, nucleus)
    exclude_solvent = bool(options.get('exclude_solvent', False))
    solvent_idx_set = set(solvent_indices)
    non_solvent_peaks = [pk for idx, pk in enumerate(peak_list) if idx not in solvent_idx_set]
    reported_peaks = non_solvent_peaks if exclude_solvent else peak_list

    max_j_hz = number(options.get('multiplet_max_j_hz', 20.0), 'multiplet_max_j_hz', 0.5, 200.0)
    multiplet_input = non_solvent_peaks if non_solvent_peaks else reported_peaks
    multiplets = _group_multiplets(multiplet_input, freq_mhz, max_j_hz=max_j_hz)

    processing_info = {
        'baseline_windows': windows,
        'baseline_degree': options.get('baseline_degree', 1) if windows else None,
        'peak_prominence': prominence,
        'normalization': normalization,
    }
    if meta.get('raw_processing'):
        processing_info.update(meta['raw_processing'])

    out_result = {
        'source': str(path),
        'sha256': _hash_source(path),
        'sample_count': len(x),
        'axis_unit': 'ppm',
        'intensity_unit': 'arbitrary',
        'processing': processing_info,
        'peaks': reported_peaks,
        'solvent_peaks': solvent_peaks,
        'multiplets': multiplets,
        'integrals': integrals,
        'assignments': 'not_performed',
        'warnings': (
            ['Peak positions are not automatic atom assignments; integration alone does not establish purity.']
            + (['Negative integrals are present.'] if any(i['area'] < 0 for i in integrals) else [])
        ),
        'spectrum': {'ppm': x.tolist(), 'intensity': y.tolist()},
    }
    if options.get('inset_region') is not None:
        ir = options['inset_region']
        out_result['inset_region'] = [float(min(ir)), float(max(ir))]
        out_result['cdxml'] = build_nmr_cdxml(
            x, y, peaks=reported_peaks, inset_region=ir, nucleus=nucleus
        )
    return out_result


def _extract_nmr_arrays_and_peaks(
    ppm: Any = None,
    intensity: Any = None,
    *,
    peaks: Optional[Sequence[Any]] = None,
    x: Any = None,
    y: Any = None,
    spectrum: Any = None,
) -> Tuple[np.ndarray, np.ndarray, list[dict[str, float]]]:
    """Normalize flexible NMR inputs into (ppm_array, intensity_array, peak_dicts)."""
    if isinstance(ppm, (str, Path)):
        rx, ry = read_spectrum(ppm)
        ppm, intensity = rx, ry
    elif isinstance(ppm, dict):
        d = ppm
        if peaks is None and 'peaks' in d:
            peaks = d['peaks']
        spec_sub = d.get('spectrum') if isinstance(d.get('spectrum'), dict) else d
        ppm = spec_sub.get('ppm') if 'ppm' in spec_sub else spec_sub.get('x')
        intensity = spec_sub.get('intensity') if 'intensity' in spec_sub else spec_sub.get('y')
    elif spectrum is not None and isinstance(spectrum, dict):
        ppm = spectrum.get('ppm') if 'ppm' in spectrum else spectrum.get('x')
        intensity = spectrum.get('intensity') if 'intensity' in spectrum else spectrum.get('y')

    if ppm is None and x is not None:
        ppm = x
    if intensity is None and y is not None:
        intensity = y

    norm_peaks: list[dict[str, float]] = []
    if peaks:
        for pk in peaks:
            if isinstance(pk, (int, float)):
                norm_peaks.append({'ppm': float(pk), 'intensity': 1.0})
            elif isinstance(pk, dict):
                pv = pk.get('ppm', pk.get('shift', pk.get('center')))
                iv = pk.get('intensity', pk.get('height', 1.0))
                if pv is not None:
                    norm_peaks.append({'ppm': float(pv), 'intensity': float(iv if iv is not None else 1.0)})
            else:
                pv = getattr(pk, 'ppm', getattr(pk, 'shift', None))
                iv = getattr(pk, 'intensity', getattr(pk, 'height', 1.0))
                if pv is not None:
                    norm_peaks.append({'ppm': float(pv), 'intensity': float(iv if iv is not None else 1.0)})

    if ppm is None or intensity is None:
        if norm_peaks:
            p_vals = [p['ppm'] for p in norm_peaks]
            p_min = min(min(p_vals) - 0.5, 0.0)
            p_max = max(max(p_vals) + 0.5, 10.0)
            x_arr = np.linspace(p_min, p_max, 2048, dtype=float)
            y_arr = np.zeros_like(x_arr)
            gamma = max((p_max - p_min) * 0.002, 0.003)
            for p in norm_peaks:
                y_arr += p['intensity'] * (gamma ** 2) / ((x_arr - p['ppm']) ** 2 + gamma ** 2)
        else:
            x_arr = np.linspace(0.0, 10.0, 512, dtype=float)
            y_arr = np.zeros_like(x_arr)
    else:
        x_arr = np.asarray(ppm, dtype=float).reshape(-1)
        y_arr = np.asarray(intensity, dtype=float).reshape(-1)
        if len(x_arr) != len(y_arr) or len(x_arr) < 2:
            raise ValueError('ppm and intensity arrays must have matching length >= 2')

    order = np.argsort(x_arr)
    x_arr = x_arr[order]
    y_arr = y_arr[order]

    if not norm_peaks and len(x_arr) >= 3:
        ptp = float(np.ptp(y_arr))
        if ptp > 0:
            pk_idx, _ = find_peaks(y_arr, prominence=max(ptp * 0.08, 1e-12))
            for i in pk_idx[:50]:
                norm_peaks.append({'ppm': float(x_arr[i]), 'intensity': float(y_arr[i])})

    return x_arr, y_arr, norm_peaks


def _downsample_indices(values: np.ndarray, max_points: int = 800) -> list[int]:
    """Select min/max envelope indices to keep CDXML curve compact while preserving sharp peaks."""
    n = len(values)
    if n <= max_points:
        return list(range(n))
    buckets = max(2, max_points // 2)
    edges = np.linspace(0, n, buckets + 1, dtype=int)
    chosen = {0, n - 1}
    for a, b in zip(edges[:-1], edges[1:]):
        if b > a:
            seg = values[a:b]
            chosen.add(int(a + np.argmin(seg)))
            chosen.add(int(a + np.argmax(seg)))
    return sorted(chosen)


def build_nmr_cdxml(
    ppm: Any = None,
    intensity: Any = None,
    *,
    peaks: Optional[Sequence[Any]] = None,
    inset_region: Optional[Union[Tuple[float, float], list[float]]] = None,
    title: str = '1H NMR Spectrum',
    nucleus: str = '1H',
    output_path: Optional[Union[str, Path]] = None,
    x: Any = None,
    y: Any = None,
    spectrum: Any = None,
) -> str:
    """Build a ChemDraw CDXML document for an NMR spectrum with optional zoomed ``inset_region``.

    When ``inset_region=(ppm_low, ppm_high)`` is passed, renders a secondary
    magnified inset box in the upper area of the spectrum showing the zoomed-in
    curve, peak ticks, and its own mini ppm axis for ``[min(inset_region), max(inset_region)]``.
    """
    if isinstance(ppm, dict) and inset_region is None and ppm.get('inset_region') is not None:
        inset_region = ppm['inset_region']

    x_arr, y_arr, norm_peaks = _extract_nmr_arrays_and_peaks(
        ppm, intensity, peaks=peaks, x=x, y=y, spectrum=spectrum
    )

    drawing = Drawing(540, 320)
    x0, y0, w, h = 60.0, 50.0, 420.0, 220.0
    x_min, x_max = float(x_arr[0]), float(x_arr[-1])
    if x_max <= x_min:
        x_max = x_min + 1.0
    y_min, y_max = float(np.min(y_arr)), float(np.max(y_arr))
    y_span = (y_max - y_min) if y_max > y_min else 1.0

    # Reversed x-axis for NMR (high ppm on left, low ppm on right)
    def sx_main(val: float) -> float:
        return x0 + (x_max - float(val)) / (x_max - x_min) * w

    def sy_main(val: float) -> float:
        return y0 + h - 18.0 - ((float(val) - y_min) / y_span) * (h - 42.0)

    main_group = drawing.add('group', {'BoundingBox': f'{x0:.2f} {y0:.2f} {x0 + w:.2f} {y0 + h:.2f}'})
    # Main frame and baseline axis
    drawing.line((x0, y0), (x0, y0 + h), main_group)
    drawing.line((x0, y0 + h), (x0 + w, y0 + h), main_group)
    drawing.line((x0 + w, y0), (x0 + w, y0 + h), main_group)
    drawing.line((x0, y0), (x0 + w, y0), main_group)
    drawing.text((x0 + w * 0.38, y0 - 10.0), title, size=10, parent=main_group)
    drawing.text((x0 + w * 0.40, y0 + h + 28.0), f'{nucleus} Chemical Shift (ppm)', size=9, parent=main_group)

    # Main ppm axis ticks
    for tick_ppm in np.linspace(x_max, x_min, 6):
        tx = sx_main(float(tick_ppm))
        drawing.line((tx, y0 + h), (tx, y0 + h + 5.0), main_group)
        drawing.text((tx - 8.0, y0 + h + 15.0), f'{tick_ppm:.2f}', size=8, parent=main_group)

    # Main spectrum trace
    idx_main = _downsample_indices(y_arr, max_points=800)
    pts_main = [(sx_main(float(x_arr[i])), sy_main(float(y_arr[i]))) for i in idx_main]
    if len(pts_main) >= 2:
        drawing.curve(pts_main, parent=main_group)

    # Main peak ticks
    for pk in norm_peaks:
        p_ppm = pk['ppm']
        if x_min <= p_ppm <= x_max:
            px = sx_main(p_ppm)
            py = sy_main(pk['intensity'])
            drawing.line((px, max(y0 + 4.0, py - 8.0)), (px, max(y0 + 2.0, py - 2.0)), main_group)

    # Secondary magnified inset box when inset_region is provided
    if inset_region is not None:
        if not isinstance(inset_region, (tuple, list)) or len(inset_region) != 2:
            raise ValueError('inset_region must be a 2-element (ppm_low, ppm_high) tuple or list')
        ppm_low = float(min(inset_region[0], inset_region[1]))
        ppm_high = float(max(inset_region[0], inset_region[1]))
        if ppm_high <= ppm_low:
            raise ValueError('inset_region bounds must have ppm_low < ppm_high')

        ix0 = x0 + 24.0
        iy0 = y0 + 12.0
        iw = 185.0
        ih = 82.0

        inset_group = drawing.add(
            'group',
            {
                'BoundingBox': f'{ix0:.2f} {iy0:.2f} {ix0 + iw:.2f} {iy0 + ih:.2f}',
            },
        )
        # Inset bounding box lines
        drawing.line((ix0, iy0), (ix0 + iw, iy0), inset_group)
        drawing.line((ix0 + iw, iy0), (ix0 + iw, iy0 + ih), inset_group)
        drawing.line((ix0, iy0 + ih), (ix0 + iw, iy0 + ih), inset_group)
        drawing.line((ix0, iy0), (ix0, iy0 + ih), inset_group)
        drawing.text(
            (ix0 + 6.0, iy0 + 10.0),
            f'Inset zoom: {ppm_high:.2f}-{ppm_low:.2f} ppm',
            size=7,
            parent=inset_group,
        )

        # Extract or interpolate curve slice in [ppm_low, ppm_high]
        mask = (x_arr >= ppm_low) & (x_arr <= ppm_high)
        if int(np.sum(mask)) >= 2:
            ix_arr = np.r_[ppm_low, x_arr[mask], ppm_high]
            iy_arr = np.interp(ix_arr, x_arr, y_arr)
        else:
            ix_arr = np.linspace(ppm_low, ppm_high, 128, dtype=float)
            iy_arr = np.interp(ix_arr, x_arr, y_arr)

        iy_min = float(np.min(iy_arr))
        iy_max = float(np.max(iy_arr))
        iy_span = (iy_max - iy_min) if iy_max > iy_min else 1.0

        def sx_inset(val: float) -> float:
            return ix0 + 8.0 + (ppm_high - float(val)) / (ppm_high - ppm_low) * (iw - 16.0)

        def sy_inset(val: float) -> float:
            return iy0 + ih - 10.0 - ((float(val) - iy_min) / iy_span) * (ih - 28.0)

        idx_inset = _downsample_indices(iy_arr, max_points=300)
        pts_inset = [(sx_inset(float(ix_arr[i])), sy_inset(float(iy_arr[i]))) for i in idx_inset]
        if len(pts_inset) >= 2:
            drawing.curve(pts_inset, parent=inset_group)

        # Peak ticks & ppm labels inside inset
        inset_peaks = [pk for pk in norm_peaks if ppm_low <= pk['ppm'] <= ppm_high]
        for pk in inset_peaks:
            px = sx_inset(pk['ppm'])
            p_int = float(np.interp(pk['ppm'], ix_arr, iy_arr))
            py = sy_inset(p_int)
            tick_top = max(iy0 + 12.0, py - 7.0)
            tick_bot = max(iy0 + 14.0, py - 2.0)
            drawing.line((px, tick_top), (px, tick_bot), inset_group)
            drawing.text((px - 6.0, max(iy0 + 10.0, tick_top - 2.0)), f"{pk['ppm']:.2f}", size=6, parent=inset_group)

        # Mini ppm axis ticks at bottom of inset box
        for tick_ppm in (ppm_high, 0.5 * (ppm_high + ppm_low), ppm_low):
            tx = sx_inset(tick_ppm)
            drawing.line((tx, iy0 + ih), (tx, iy0 + ih + 3.5), inset_group)
            drawing.text((tx - 7.0, iy0 + ih + 11.0), f'{tick_ppm:.2f}', size=7, parent=inset_group)

    if output_path is not None:
        drawing.save(output_path)

    xml_body = ET.tostring(drawing.root, encoding='unicode')
    return (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
        + xml_body
    )


def nmr_to_cdxml(
    ppm: Any = None,
    intensity: Any = None,
    *,
    peaks: Optional[Sequence[Any]] = None,
    inset_region: Optional[Union[Tuple[float, float], list[float]]] = None,
    title: str = '1H NMR Spectrum',
    nucleus: str = '1H',
    output_path: Optional[Union[str, Path]] = None,
    x: Any = None,
    y: Any = None,
    spectrum: Any = None,
) -> str:
    """Convert NMR spectrum arrays, peak list, or file path into a CDXML string (with optional ``inset_region``)."""
    return build_nmr_cdxml(
        ppm,
        intensity,
        peaks=peaks,
        inset_region=inset_region,
        title=title,
        nucleus=nucleus,
        output_path=output_path,
        x=x,
        y=y,
        spectrum=spectrum,
    )


def plot_nmr(
    ppm: Any = None,
    intensity: Any = None,
    *,
    peaks: Optional[Sequence[Any]] = None,
    inset_region: Optional[Union[Tuple[float, float], list[float]]] = None,
    title: str = '1H NMR Spectrum',
    nucleus: str = '1H',
    output_path: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    x: Any = None,
    y: Any = None,
    spectrum: Any = None,
) -> Union[str, dict[str, Any]]:
    """Plot an NMR spectrum to CDXML (and optional ``output_dir`` bundle) with ``inset_region`` zoom support."""
    target_cdxml = Path(output_path) if output_path is not None else (
        Path(output_dir) / 'spectrum.cdxml' if output_dir is not None else None
    )
    if target_cdxml is not None:
        target_cdxml.parent.mkdir(parents=True, exist_ok=True)

    cdxml_str = build_nmr_cdxml(
        ppm,
        intensity,
        peaks=peaks,
        inset_region=inset_region,
        title=title,
        nucleus=nucleus,
        output_path=target_cdxml,
        x=x,
        y=y,
        spectrum=spectrum,
    )
    if output_dir is not None:
        return {
            'cdxml': cdxml_str,
            'cdxml_path': str(target_cdxml),
            'inset_region': [float(min(inset_region)), float(max(inset_region))] if inset_region is not None else None,
        }
    return cdxml_str


STACKED_NMR_PALETTE = (
    '#000000',
    '#007c83',
    '#1565c0',
    '#c62828',
    '#6a1b9a',
    '#ef6c00',
    '#2e7d32',
    '#455a64',
)


def _coerce_single_trace(item: str | Path | Mapping[str, Any], index: int) -> dict[str, Any]:
    """Load or simulate one NMR trace into {'x', 'y', 'peaks', 'label', 'nucleus'}."""
    default_label = f'Trace {index + 1}'
    nucleus = '1H'
    if isinstance(item, (str, Path)):
        p = Path(item)
        rx, ry = load_nmr_spectrum(p)
        x_arr, y_arr, norm_peaks = _extract_nmr_arrays_and_peaks(rx, ry)
        return {
            'x': x_arr,
            'y': y_arr,
            'peaks': norm_peaks,
            'label': p.stem or p.name or default_label,
            'nucleus': _normalize_nucleus(None, x_arr),
        }

    if not isinstance(item, Mapping):
        raise ValueError(f'Unsupported spectrum entry at index {index}: {type(item)!r}')

    d = dict(item)
    lbl = d.get('label') or d.get('title') or d.get('name')
    if not lbl and isinstance(d.get('source'), (str, Path)):
        lbl = Path(d['source']).stem or Path(d['source']).name
    if not lbl and isinstance(d.get('path') or d.get('input'), (str, Path)):
        p_raw = Path(d.get('path') or d.get('input'))
        lbl = p_raw.stem or p_raw.name

    has_xy_arrays = (
        isinstance(d.get('spectrum'), Mapping)
        or ('ppm' in d and d.get('ppm') is not None)
        or ('x' in d and d.get('x') is not None)
    )
    if not has_xy_arrays and any(k in d for k in ('path', 'input', 'source')):
        raw_p = d.get('path') or d.get('input') or d.get('source')
        if raw_p is not None and Path(str(raw_p)).exists():
            rx, ry = load_nmr_spectrum(raw_p)
            x_arr, y_arr, norm_peaks = _extract_nmr_arrays_and_peaks(rx, ry, peaks=d.get('peaks'))
            return {
                'x': x_arr,
                'y': y_arr,
                'peaks': norm_peaks,
                'label': str(lbl or default_label),
                'nucleus': _normalize_nucleus(d.get('nucleus'), x_arr),
            }

    # Check if this is a predicted shift dict from engines.nmr
    peaks_field = d.get('peaks') if 'peaks' in d else d.get('shifts')
    if not has_xy_arrays and peaks_field is not None:
        raw_peak_list: list[Any] = []
        if isinstance(peaks_field, Mapping):
            if d.get('nucleus') in ('1H', '13C') and peaks_field.get(d['nucleus']):
                nucleus = str(d['nucleus'])
                raw_peak_list = list(peaks_field[nucleus])
            elif peaks_field.get('1H'):
                nucleus = '1H'
                raw_peak_list = list(peaks_field['1H'])
            elif peaks_field.get('13C'):
                nucleus = '13C'
                raw_peak_list = list(peaks_field['13C'])
            else:
                for k_nuc, v_list in peaks_field.items():
                    if isinstance(v_list, Sequence) and not isinstance(v_list, (str, bytes)) and v_list:
                        nucleus = _normalize_nucleus(k_nuc)
                        raw_peak_list = list(v_list)
                        break
        elif isinstance(peaks_field, Sequence) and not isinstance(peaks_field, (str, bytes)):
            raw_peak_list = list(peaks_field)
            if d.get('nucleus'):
                nucleus = _normalize_nucleus(d.get('nucleus'))

        sim_peaks: list[dict[str, Any]] = []
        for pk in raw_peak_list:
            if isinstance(pk, (int, float)):
                sim_peaks.append({'shift_ppm': float(pk), 'count': 1})
            elif isinstance(pk, Mapping):
                s_val = pk.get('shift_ppm', pk.get('ppm', pk.get('shift', pk.get('center'))))
                if s_val is not None:
                    cnt = pk.get('count', pk.get('intensity', pk.get('height', 1)))
                    sim_peaks.append({'shift_ppm': float(s_val), 'count': float(cnt if cnt is not None else 1.0)})
                    if pk.get('nucleus') and not d.get('nucleus'):
                        nucleus = _normalize_nucleus(pk.get('nucleus'))

        from ..engines import nmr as nmr_engine
        freq = float(d.get('frequency_mhz') or 400.0)
        rows = nmr_engine.simulate(sim_peaks, nucleus, freq, points=4096)
        x_arr = np.array([r[0] for r in rows], dtype=float)
        y_arr = np.array([r[1] for r in rows], dtype=float)
        order = np.argsort(x_arr)
        x_arr = x_arr[order]
        y_arr = y_arr[order]
        norm_peaks = [
            {
                'ppm': float(p['shift_ppm']),
                'intensity': float(np.interp(float(p['shift_ppm']), x_arr, y_arr)),
            }
            for p in sim_peaks
        ]
        if not lbl:
            lbl = f"Predicted ({d.get('engine', nucleus)})" if d.get('predicted') or 'peaks' in d else default_label
        return {
            'x': x_arr,
            'y': y_arr,
            'peaks': norm_peaks,
            'label': str(lbl),
            'nucleus': nucleus,
        }

    x_arr, y_arr, norm_peaks = _extract_nmr_arrays_and_peaks(d)
    return {
        'x': x_arr,
        'y': y_arr,
        'peaks': norm_peaks,
        'label': str(lbl or default_label),
        'nucleus': _normalize_nucleus(d.get('nucleus'), x_arr),
    }


def _extract_match_pairs(match_shifts: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None) -> list[dict[str, float]]:
    if match_shifts is None:
        return []
    raw_items: Sequence[Any]
    if isinstance(match_shifts, Mapping):
        raw_items = list(match_shifts.get('matches_1h') or []) + list(match_shifts.get('matches_13c') or [])
        if not raw_items and 'matches' in match_shifts:
            raw_items = list(match_shifts.get('matches') or [])
    else:
        raw_items = list(match_shifts)

    pairs: list[dict[str, float]] = []
    for item in raw_items:
        if not isinstance(item, Mapping):
            continue
        p0 = item.get('predicted_shift', item.get('predicted_ppm', item.get('from_ppm', item.get('ppm_1', item.get('pred')))))
        p1 = item.get('experimental_shift', item.get('experimental_ppm', item.get('to_ppm', item.get('ppm_2', item.get('exp')))))
        if p0 is not None and p1 is not None:
            f0, f1 = float(p0), float(p1)
            err = item.get('error')
            delta = float(err) if err is not None else (f1 - f0)
            pairs.append({'ppm_0': f0, 'ppm_1': f1, 'delta': delta})
    return pairs


def build_stacked_nmr_cdxml(
    spectra: Sequence[str | Path | Mapping[str, Any]],
    output_path: str | Path | None = None,
    *,
    labels: Sequence[str] | None = None,
    ppm_range: tuple[float, float] | None = None,
    title: str = 'Stacked NMR Comparison',
    normalize: str = 'each',
    show_peaks: bool = True,
    match_shifts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a multi-trace stacked NMR comparison CDXML figure (2 to 8 spectra)."""
    if not isinstance(spectra, Sequence) or not (2 <= len(spectra) <= 8):
        raise ValueError('Provide 2 to 8 spectra for stacked NMR comparison')
    if normalize not in ('each', 'global', 'max', 'none'):
        raise ValueError("normalize must be 'each', 'global', 'max', or 'none'")

    traces = [_coerce_single_trace(item, idx) for idx, item in enumerate(spectra)]
    if labels is not None:
        if len(labels) != len(traces):
            raise ValueError('labels length must match spectra length')
        resolved_labels = [str(lbl) for lbl in labels]
    else:
        resolved_labels = [t['label'] for t in traces]

    if ppm_range is not None:
        if len(ppm_range) != 2:
            raise ValueError('ppm_range must be a 2-element (ppm_high, ppm_low) tuple or list')
        ppm_lo = float(min(ppm_range[0], ppm_range[1]))
        ppm_hi = float(max(ppm_range[0], ppm_range[1]))
        if ppm_hi <= ppm_lo:
            raise ValueError('ppm_range bounds must differ')
    else:
        ppm_lo = min(float(np.min(t['x'])) for t in traces)
        ppm_hi = max(float(np.max(t['x'])) for t in traces)
        if ppm_hi <= ppm_lo:
            ppm_hi = ppm_lo + 10.0

    # Slice or interpolate each trace onto [ppm_lo, ppm_hi]
    sliced_traces = []
    global_span = 1e-12
    for t in traces:
        x_full, y_full = t['x'], t['y']
        mask = (x_full >= ppm_lo) & (x_full <= ppm_hi)
        if int(np.sum(mask)) >= 2:
            xs = np.r_[ppm_lo, x_full[mask], ppm_hi]
            ys = np.interp(xs, x_full, y_full)
        else:
            xs = np.linspace(ppm_lo, ppm_hi, 512, dtype=float)
            ys = np.interp(xs, x_full, y_full)
        y_min = float(np.min(ys))
        y_max = float(np.max(ys))
        span = max(y_max - y_min, 1e-12)
        global_span = max(global_span, span)
        pks = [pk for pk in t['peaks'] if ppm_lo <= pk['ppm'] <= ppm_hi]
        sliced_traces.append({
            'x': xs,
            'y': ys,
            'y_min': y_min,
            'span': span,
            'peaks': pks,
            'nucleus': t['nucleus'],
        })

    n_traces = len(sliced_traces)
    lane_h = 82.0
    top_margin = 46.0
    bottom_margin = 54.0
    width = 620.0
    height = top_margin + n_traces * lane_h + bottom_margin
    x0 = 115.0
    plot_w = 470.0

    drawing = Drawing(int(width), int(height))
    main_group = drawing.add('group', {'BoundingBox': f'0 0 {width:.2f} {height:.2f}'})
    drawing.text((x0 + plot_w * 0.30, 22.0), title, size=11, parent=main_group)

    def sx(ppm_val: float) -> float:
        return x0 + (ppm_hi - float(ppm_val)) / (ppm_hi - ppm_lo) * plot_w

    trace_baselines: list[float] = []
    trace_sy_funcs = []

    for idx, st in enumerate(sliced_traces):
        color_hex = STACKED_NMR_PALETTE[idx % len(STACKED_NMR_PALETTE)]
        y_top = top_margin + idx * lane_h
        y_base = y_top + lane_h - 12.0
        amp_h = lane_h - 24.0
        denom = st['span'] if normalize == 'each' else global_span
        y_min = st['y_min']

        def make_sy(yb: float, ym: float, dn: float, ah: float):
            return lambda val: yb - ((float(val) - ym) / dn) * ah

        sy_fn = make_sy(y_base, y_min, denom, amp_h)
        trace_baselines.append(y_base)
        trace_sy_funcs.append(sy_fn)

        # Left-margin trace label
        drawing.text((14.0, y_base - 14.0), resolved_labels[idx], size=9, parent=main_group, color=color_hex)
        # Subtle baseline reference
        drawing.line((x0, y_base), (x0 + plot_w, y_base), parent=main_group, color='#cccccc')

        # Downsampled trace polyline
        keep = _downsample_indices(st['y'], max_points=700)
        pts = [(sx(float(st['x'][i])), sy_fn(float(st['y'][i]))) for i in keep]
        if len(pts) >= 2:
            drawing.curve(pts, parent=main_group, color=color_hex)

        # Peak ticks
        if show_peaks:
            for pk in st['peaks'][:25]:
                px = sx(pk['ppm'])
                p_int = float(np.interp(pk['ppm'], st['x'], st['y']))
                py = sy_fn(p_int)
                tick_top = max(y_top + 2.0, py - 7.0)
                tick_bot = max(y_top + 4.0, py - 2.0)
                drawing.line((px, tick_top), (px, tick_bot), parent=main_group, color=color_hex)

    # Dashed connectors when match_shifts is provided for >= 2 traces
    pairs = _extract_match_pairs(match_shifts)
    if pairs and n_traces >= 2:
        t_idx_a = n_traces - 2
        t_idx_b = n_traces - 1
        st0, st1 = sliced_traces[t_idx_a], sliced_traces[t_idx_b]
        sy0, sy1 = trace_sy_funcs[t_idx_a], trace_sy_funcs[t_idx_b]
        sorted_pairs = sorted(pairs, key=lambda p: -p['ppm_0'])
        for p_i, pair in enumerate(sorted_pairs):
            p0, p1, delta = pair['ppm_0'], pair['ppm_1'], pair['delta']
            if ppm_lo <= p0 <= ppm_hi and ppm_lo <= p1 <= ppm_hi:
                x_a = sx(p0)
                y_a = trace_baselines[t_idx_a] + 2.0
                x_b = sx(p1)
                y_b = sy1(float(np.interp(p1, st1['x'], st1['y']))) - 4.0
                drawing.line((x_a, y_a), (x_b, y_b), parent=main_group, color='#616161', dashed=True)
                mid_x = 0.5 * (x_a + x_b)
                mid_y = 0.5 * (y_a + y_b) + ((-5.0 if p_i % 2 == 0 else 5.0) if len(sorted_pairs) > 1 else 0.0)
                drawing.text(
                    (mid_x - 14.0, mid_y),
                    f'\u0394\u03b4 {delta:+.2f} ppm',
                    size=7,
                    parent=main_group,
                    color='#616161',
                )

    # Shared bottom ppm axis
    y_axis = top_margin + n_traces * lane_h
    drawing.line((x0, y_axis), (x0 + plot_w, y_axis), parent=main_group)
    for tick_ppm in np.linspace(ppm_hi, ppm_lo, 7):
        tx = sx(float(tick_ppm))
        drawing.line((tx, y_axis), (tx, y_axis + 5.0), parent=main_group)
        drawing.text((tx - 8.0, y_axis + 15.0), f'{tick_ppm:.2f}', size=8, parent=main_group)

    axis_nuc = sliced_traces[0]['nucleus']
    drawing.text((x0 + plot_w * 0.36, y_axis + 32.0), f'{axis_nuc} Chemical Shift (ppm)', size=9, parent=main_group)

    saved_path = None
    if output_path is not None:
        saved_path = drawing.save(output_path)

    xml_body = ET.tostring(drawing.root, encoding='unicode')
    xml_str = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
        + xml_body
    )
    out: dict[str, Any] = {
        'cdxml': xml_str,
        'trace_count': len(sliced_traces),
        'ppm_range': [round(float(ppm_hi), 4), round(float(ppm_lo), 4)],
        'labels': resolved_labels,
    }
    if saved_path is not None:
        out['output_path'] = saved_path
    return out


stack_spectra = build_stacked_nmr_cdxml
