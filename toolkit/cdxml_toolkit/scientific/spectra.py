"""Auditable 1D spectral peak picking and integration without guessed assignments."""
import contextlib
import hashlib
import io
import re
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from .common import number


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
                  'normalization_region', 'normalization_value'):
            if k in spec_dict and k not in options:
                options[k] = spec_dict[k]
        path = raw_path
    elif options is None:
        options = {}

    allowed = {
        'baseline_windows', 'baseline_degree', 'prominence', 'integration_regions',
        'normalization_region', 'normalization_value', 'solvent', 'nucleus',
        'frequency_mhz', 'exclude_solvent', 'multiplet_max_j_hz',
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

    return {
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
