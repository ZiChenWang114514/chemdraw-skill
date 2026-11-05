"""NMR shift prediction. Output is a prediction and is never written into a measured-data field."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable

from . import env, envelope
from .registry import ENGINES, by_task

SOLVENTS = ('chloroform', 'dimethylsulfoxide', 'methanol', 'water', 'acetone', 'benzene', 'acetonitrile',
            'dichloromethane', 'tetrahydrofuran', 'toluene', 'chlorobenzene', 'trifluoroethanol')
ALIASES = {'cdcl3': 'chloroform', 'dmso': 'dimethylsulfoxide', 'dmso-d6': 'dimethylsulfoxide',
           'cd3od': 'methanol', 'd2o': 'water', 'acetone-d6': 'acetone', 'c6d6': 'benzene', 'cd3cn': 'acetonitrile',
           'cd2cl2': 'dichloromethane', 'thf-d8': 'tetrahydrofuran'}
ELEMENT = {'1H': 'H', '13C': 'C'}


def _peaks(atoms: list, nucleus: str) -> list:
    """One peak per set of symmetry-equivalent atoms (their shifts are averaged)."""
    element = ELEMENT[nucleus]
    by_index = {a['index']: a for a in atoms}
    groups: dict = {}
    for atom in atoms:
        if atom['element'] == element and atom['shift'] is not None:
            groups.setdefault(atom['class'], []).append(atom)
    peaks = []
    for members in groups.values():
        shift = sum(a['shift'] for a in members) / len(members)
        host = by_index[members[0]['neighbors'][0]]['element'] if nucleus == '1H' and members[0].get('neighbors') else None
        entry = {'nucleus': nucleus, 'shift_ppm': round(shift, 2), 'count': len(members),
                 'atoms': sorted(a['index'] for a in members), 'predicted': True,
                 'exchangeable': host in ('O', 'N', 'S')}
        if 'j_couplings' in members[0]:
            entry['j_couplings'] = members[0]['j_couplings']
        if 'multiplicity_hint' in members[0]:
            entry['multiplicity_hint'] = members[0]['multiplicity_hint']
        if 'shift_std' in members[0]:
            stds = [a['shift_std'] for a in members if a.get('shift_std') is not None]
            entry['shift_std'] = round(sum(stds) / len(stds), 3) if stds else None
        peaks.append(entry)
    return sorted(peaks, key=lambda p: -p['shift_ppm'])


def simulate(peaks: list, nucleus: str, frequency_mhz: float, width_hz: float = 1.5, points: int = 16384) -> list:
    """Lorentzian singlets on a ppm axis (no coupling): a picture of where the lines fall, not a multiplet pattern."""
    low, high, margin = (-1.0, 12.0, 1.0) if nucleus == '1H' else (-10.0, 230.0, 10.0)
    shifts = [peak['shift_ppm'] for peak in peaks]
    low, high = min([low, *(s - margin for s in shifts)]), max([high, *(s + margin for s in shifts)])
    step = (high - low) / (points - 1)
    half = width_hz / (frequency_mhz * (1.0 if nucleus == '1H' else 0.2515)) / 2  # half width in ppm
    half = max(half, 2 * step)  # narrower lines fall between grid points and lose height at random
    try:
        import numpy as np
        axis = low + np.arange(points, dtype=float) * step
        if peaks:
            s_arr = np.array([float(p['shift_ppm']) for p in peaks], dtype=float)[:, None]
            c_arr = np.array([float(p['count']) for p in peaks], dtype=float)[:, None]
            h2 = half * half
            totals = np.sum(c_arr * h2 / ((axis[None, :] - s_arr) ** 2 + h2), axis=0)
        else:
            totals = np.zeros(points, dtype=float)
        return list(zip(axis[::-1].tolist(), totals[::-1].tolist()))
    except ImportError:
        axis = [low + i * step for i in range(points)]
        out = []
        for x in axis:
            total = 0.0
            for peak in peaks:
                total += peak['count'] * half * half / ((x - peak['shift_ppm']) ** 2 + half * half)
            out.append((x, total))
        return out[::-1]  # NMR convention: high ppm first


def _compare(by_engine: dict, nuclei: list) -> dict:
    """Pair each engine's peaks with the nearest peak of the first engine; large gaps are listed for review."""
    names = list(by_engine)
    first = names[0]
    out = {}
    for nucleus in nuclei:
        limit = 0.3 if nucleus == '1H' else 5.0
        rows = []
        for peak in by_engine[first][nucleus]:
            row = {'atoms': peak['atoms'], 'count': peak['count'], 'shift_ppm': {first: peak['shift_ppm']}}
            for other in names[1:]:
                match = next((q for q in by_engine[other][nucleus] if q['atoms'] == peak['atoms']), None)
                if match is None:
                    match = next((q for q in by_engine[other][nucleus] if set(q['atoms']) & set(peak['atoms'])), None)
                row['shift_ppm'][other] = match['shift_ppm'] if match else None
            values = [v for v in row['shift_ppm'].values() if v is not None]
            row['spread_ppm'] = round(max(values) - min(values), 2) if len(values) > 1 else None
            row['needs_review'] = len(values) < len(names) or (row['spread_ppm'] or 0) > limit
            rows.append(row)
        out[nucleus] = rows
    return {'peaks': out, 'needs_review': any(r['needs_review'] for rows in out.values() for r in rows),
            'review_threshold_ppm': {'1H': 0.3, '13C': 5.0},
            'note': 'engines are compared, never averaged: a gap means at least one of them is wrong for this molecule'}


def _targets(output_path: str | None, nuclei: list) -> dict:
    """Where each simulated spectrum goes; an existing file is refused before any engine runs."""
    if not output_path:
        return {}
    base = Path(output_path).expanduser().resolve()
    targets = {n: base if len(nuclei) == 1 else base.with_name(f'{base.stem}-{n}{base.suffix}') for n in nuclei}
    for target in targets.values():
        if target.exists():
            raise ValueError(f'{target} exists: choose a new file name')
    return targets


def _run_one(engine: str, smiles: str, solvent: str, nuclei: list, timeout: int) -> dict:
    env._LAST_CALL_META.set(None)
    raw = env.call(engine, 'predict', {'smiles': smiles, 'solvent': solvent, 'nuclei': nuclei}, timeout=timeout)
    meta = env.last_call_meta(engine)
    return {'engine': engine, 'raw': raw, 'device': meta['device'],
            **({'device_fallback': True} if meta.get('device_fallback') else {})}


def predict(smiles: str, nucleus: str = '1H', solvent: str = 'chloroform', frequency_mhz: float = 400.0,
            engine: str | None = None, output_path: str | None = None, timeout_seconds: int = 900) -> dict:
    """``engine`` may name several, comma separated: each runs and the peaks are compared, never merged.
    An engine that fails is listed in ``failed_engines`` and the others still answer."""
    names = [n.strip() for n in (engine or 'magnet').split(',') if n.strip()]
    for name in names:
        if name not in ENGINES or ENGINES[name]['task'] != 'nmr':
            raise ValueError(f'unknown nmr engine {name!r} (choose from {", ".join(by_task("nmr"))})')
    if len(set(names)) != len(names):
        raise ValueError('name each engine once')
    if nucleus not in ('1H', '13C', 'both'):
        raise ValueError("nucleus must be '1H', '13C' or 'both'")
    key = ALIASES.get(solvent.strip().lower(), solvent.strip().lower())
    if key not in SOLVENTS:
        raise ValueError(f'unknown solvent {solvent!r}; choose one of: {", ".join(SOLVENTS)}')
    if not 60 <= float(frequency_mhz) <= 1200:
        raise ValueError('frequency_mhz must be between 60 and 1200')
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog('rdApp.*')
    mol = Chem.MolFromSmiles((smiles or '').strip())
    if mol is None:
        raise ValueError(f'smiles is not valid: {smiles!r}')
    if '.' in Chem.MolToSmiles(mol):
        raise ValueError('give one molecule (no salts or mixtures)')
    present = {a.GetSymbol() for a in mol.GetAtoms()}
    for name in names:
        unsupported = sorted(present - set(ENGINES[name]['elements']))
        if unsupported:
            raise ValueError(f'{ENGINES[name]["title"]} supports {", ".join(ENGINES[name]["elements"])} only; found '
                             + ", ".join(unsupported))
    canonical = Chem.MolToSmiles(mol)
    nuclei = ['1H', '13C'] if nucleus == 'both' else [nucleus]
    targets = _targets(output_path, nuclei)
    started = time.time()
    runs, failed = [], []
    for name in names:
        try:
            runs.append(_run_one(name, canonical, key, nuclei, timeout_seconds))
        except env.EngineError as exc:
            failed.append(envelope.failure('nmr', name, ENGINES[name], exc))
    if not runs:
        return {**failed[0], 'failed_engines': failed} if len(failed) > 1 else failed[0]
    raws = {r['engine']: r['raw'] for r in runs}
    names = list(raws)
    by_engine = {name: {n: _peaks(raw['atoms'], n) for n in nuclei} for name, raw in raws.items()}
    spectra = {}
    for n, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = simulate(by_engine[names[0]][n], n, float(frequency_mhz))
        with open(target, 'x', encoding='utf-8') as handle:
            handle.write('ppm,intensity\n')
            handle.writelines(f'{x:.5f},{y:.6f}\n' for x, y in rows)
        spectra[n] = str(target)
    warnings = ['predicted shifts, not measured data: do not report them as experimental values']
    for r in runs:
        if r.get('device_fallback'):
            warnings.append(f'{r["engine"]}: CUDA failed at runtime; fell back to CPU.')
    if failed:
        warnings.append('did not run, so there is nothing to compare with: ' + ', '.join(f['engine'] for f in failed)
                        + ' (see `failed_engines`)')
    for name in names:
        warnings += [w for w in raws[name].get('warnings', []) if w not in warnings]
    if 'magnet' in names:
        warnings.append('the geometry is an RDKit/MMFF conformer; MagNET-Zero was trained on AIMNet2 '
                        'geometries, so errors can be larger than the published ones')
    warnings.append('simulated spectra draw singlets only (no coupling or multiplets)')
    if any(p['exchangeable'] for name in names for n in nuclei for p in by_engine[name][n]):
        warnings.append('OH/NH/SH proton shifts depend on concentration and exchange; treat them as rough')
    first = names[0]
    common = dict(smiles=canonical, solvent=key, frequency_mhz=float(frequency_mhz), simulated_spectra=spectra,
                  elapsed_s=round(time.time() - started, 2), predicted=True, warnings=warnings,
                  **({'failed_engines': failed} if failed else {}))
    if len(runs) == 1:
        one = runs[0]
        return envelope.result('nmr', first, ENGINES[first], [], peaks=by_engine[first],
                               atoms=raws[first].get('atoms', []),
                               geometry=raws[first].get('geometry'), device=one['device'],
                               **({'device_fallback': True} if one.get('device_fallback') else {}), **common)
    devs = list(dict.fromkeys(r['device'] for r in runs if r.get('device')))
    any_fallback = any(r.get('device_fallback') for r in runs)
    out = envelope.result('nmr', ','.join(names), {'kind': 'local', 'license': 'see each engine'}, [],
                          device=devs[0] if len(devs) == 1 else 'mixed',
                          **({'device_fallback': True} if any_fallback else {}),
                          engines=[{'engine': r['engine'], 'license': ENGINES[r['engine']].get('license'),
                                    'device': r['device'],
                                    **({'device_fallback': True} if r.get('device_fallback') else {}),
                                    'peaks': by_engine[r['engine']],
                                    'atoms': raws[r['engine']].get('atoms', []),
                                    'geometry': raws[r['engine']].get('geometry')} for r in runs],
                          peaks=by_engine[first], atoms=raws[first].get('atoms', []),
                          comparison=_compare(by_engine, nuclei), **common)
    out['note'] = f'`peaks` repeats the first engine ({first}); see `engines` and `comparison` for all of them'
    return out


predict_shifts = predict


def _heuristic_topological_groups(smiles: str) -> dict[str, list[dict[str, Any]]]:
    """Topological group fallback using RDKit symmetry classes when ML engines are unavailable."""
    from rdkit import Chem

    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
    atoms = []
    for a in mol.GetAtoms():
        idx = a.GetIdx()
        sym = a.GetSymbol()
        shift: float | None = None
        if sym == 'C':
            hyb = str(a.GetHybridization())
            het_neighbors = sum(1 for n in a.GetNeighbors() if n.GetAtomicNum() not in (1, 6))
            if a.GetIsAromatic():
                shift = 128.0 + 8.0 * het_neighbors
            elif 'SP2' in hyb:
                shift = 170.0 if het_neighbors >= 2 else (135.0 + 15.0 * het_neighbors)
            elif 'SP' == hyb:
                shift = 80.0 + 10.0 * het_neighbors
            else:
                shift = 20.0 + 25.0 * het_neighbors
        elif sym == 'H':
            nbr = a.GetNeighbors()[0] if a.GetNeighbors() else None
            if nbr is None:
                shift = 1.0
            elif nbr.GetAtomicNum() != 6:
                shift = 4.5
            elif nbr.GetIsAromatic():
                shift = 7.3
            elif 'SP2' in str(nbr.GetHybridization()):
                shift = 5.8
            else:
                het = sum(1 for n in nbr.GetNeighbors() if n.GetAtomicNum() not in (1, 6))
                shift = 1.2 + 2.2 * het
        atoms.append({
            'index': idx,
            'element': sym,
            'shift': shift,
            'class': ranks[idx],
            'neighbors': [n.GetIdx() for n in a.GetNeighbors()],
        })
    return {'1H': _peaks(atoms, '1H'), '13C': _peaks(atoms, '13C')}


def _normalize_predicted_groups(
    smiles: str,
    predicted_result: dict[str, Any] | None,
    need_1h: bool,
    need_13c: bool,
    solvent: str,
    engines: Iterable[str],
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    """Peak groups ``{'1H': [...], '13C': [...]}`` and where they came from: ``'supplied'`` (predicted_result),
    ``'engine'`` (a prediction run here) or ``'heuristic'`` (no engine answered: a crude topology estimate)."""
    if predicted_result is not None:
        if 'atoms' in predicted_result and isinstance(predicted_result['atoms'], list) and 'peaks' not in predicted_result:
            atoms = predicted_result['atoms']
            return {'1H': _peaks(atoms, '1H'), '13C': _peaks(atoms, '13C')}, 'supplied'
        peaks_container = predicted_result.get('peaks', predicted_result)
        if isinstance(peaks_container, dict):
            out: dict[str, list[dict[str, Any]]] = {'1H': [], '13C': []}
            for nuc in ('1H', '13C'):
                raw_list = peaks_container.get(nuc) or peaks_container.get(nuc.lower()) or []
                if isinstance(raw_list, dict) and 'peaks' in raw_list:
                    raw_list = raw_list['peaks']
                for idx, item in enumerate(raw_list):
                    if isinstance(item, (int, float)):
                        out[nuc].append({
                            'nucleus': nuc,
                            'shift_ppm': float(item),
                            'count': 1,
                            'atoms': [idx],
                        })
                    elif isinstance(item, dict):
                        s_val = item.get('shift_ppm', item.get('shift', item.get('ppm')))
                        if s_val is not None:
                            atoms_idx = item.get('atoms', item.get('atom_indices', [idx]))
                            out[nuc].append({
                                'nucleus': nuc,
                                'shift_ppm': float(s_val),
                                'count': int(item.get('count', len(atoms_idx) or 1)),
                                'atoms': list(atoms_idx),
                                **({'multiplicity_hint': item['multiplicity_hint']} if 'multiplicity_hint' in item else {}),
                                **({'j_couplings': item['j_couplings']} if 'j_couplings' in item else {}),
                                **({'shift_std': item['shift_std']} if 'shift_std' in item else {}),
                            })
            if out['1H'] or out['13C']:
                return out, 'supplied'

    nuc_arg = 'both' if (need_1h and need_13c) else ('13C' if need_13c and not need_1h else '1H')
    eng_str = ','.join(engines) if not isinstance(engines, str) else engines
    try:
        res = predict(smiles, nucleus=nuc_arg, solvent=solvent, engine=eng_str)
        if res.get('ok') and isinstance(res.get('peaks'), dict):
            return {
                '1H': list(res['peaks'].get('1H', [])),
                '13C': list(res['peaks'].get('13C', [])),
            }, 'engine'
    except Exception:
        pass
    return _heuristic_topological_groups(smiles), 'heuristic'


def _match_nucleus_hungarian(
    nucleus: str,
    pred_groups: list[dict[str, Any]],
    exp_peaks: list[Any] | None,
    outlier_threshold: float,
) -> tuple[list[dict[str, Any]], float | None, float | None, list[dict[str, Any]]]:
    """Use scipy.optimize.linear_sum_assignment to match predicted topological groups to experimental peaks."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    if not exp_peaks or not pred_groups:
        return [], None, None, []

    exp_vals: list[float] = []
    for item in exp_peaks:
        if isinstance(item, (int, float)):
            exp_vals.append(float(item))
        elif isinstance(item, dict):
            v = item.get('ppm', item.get('shift', item.get('shift_ppm')))
            if v is not None:
                exp_vals.append(float(v))
    if not exp_vals:
        return [], None, None, []

    cost = np.zeros((len(pred_groups), len(exp_vals)), dtype=float)
    for i, pg in enumerate(pred_groups):
        p_shift = float(pg['shift_ppm'])
        for j, e_shift in enumerate(exp_vals):
            cost[i, j] = abs(p_shift - e_shift)

    row_ind, col_ind = linear_sum_assignment(cost)
    matches: list[dict[str, Any]] = []
    outliers: list[dict[str, Any]] = []

    for r, c in zip(row_ind, col_ind):
        pg = pred_groups[int(r)]
        pred_ppm = round(float(pg['shift_ppm']), 4)
        exp_ppm = round(float(exp_vals[int(c)]), 4)
        abs_err = round(abs(pred_ppm - exp_ppm), 4)
        signed_err = round(exp_ppm - pred_ppm, 4)
        is_outlier = bool(abs_err > outlier_threshold)
        entry: dict[str, Any] = {
            'nucleus': nucleus,
            'atoms': list(pg.get('atoms', [])),
            'atom_indices': list(pg.get('atoms', [])),
            'count': int(pg.get('count', len(pg.get('atoms', [])) or 1)),
            'predicted_shift': pred_ppm,
            'experimental_shift': exp_ppm,
            'predicted_ppm': pred_ppm,
            'experimental_ppm': exp_ppm,
            'error': signed_err,
            'abs_error': abs_err,
            'is_outlier': is_outlier,
        }
        if 'multiplicity_hint' in pg:
            entry['multiplicity_hint'] = pg['multiplicity_hint']
        if 'j_couplings' in pg:
            entry['j_couplings'] = pg['j_couplings']
        if 'shift_std' in pg:
            entry['shift_std'] = pg['shift_std']
        matches.append(entry)
        if is_outlier:
            outliers.append(entry)

    matches.sort(key=lambda m: -m['predicted_shift'])
    abs_errors = [m['abs_error'] for m in matches]
    mae = round(float(sum(abs_errors) / len(abs_errors)), 4) if abs_errors else None
    max_err = round(float(max(abs_errors)), 4) if abs_errors else None
    return matches, mae, max_err, outliers


def compare_shifts(
    smiles: str,
    experimental_1h: list[float] | None = None,
    experimental_13c: list[float] | None = None,
    *,
    solvent: str = 'CDCl3',
    engines: Iterable[str] = ('magnet',),
    predicted_result: dict[str, Any] | None = None,
    outlier_threshold_1h: float = 0.5,
    outlier_threshold_13c: float = 5.0,
) -> dict[str, Any]:
    """Compare predicted NMR shifts against experimental 1H/13C peak lists using Hungarian matching."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog('rdApp.*')
    mol = Chem.MolFromSmiles((smiles or '').strip())
    if mol is None:
        raise ValueError(f'smiles is not valid: {smiles!r}')
    canonical = Chem.MolToSmiles(mol)

    groups, source = _normalize_predicted_groups(
        canonical,
        predicted_result,
        need_1h=bool(experimental_1h),
        need_13c=bool(experimental_13c),
        solvent=solvent,
        engines=engines,
    )

    matches_1h, mae_1h, max_err_1h, out_1h = _match_nucleus_hungarian(
        '1H', groups.get('1H', []), experimental_1h, outlier_threshold_1h
    )
    matches_13c, mae_13c, max_err_13c, out_13c = _match_nucleus_hungarian(
        '13C', groups.get('13C', []), experimental_13c, outlier_threshold_13c
    )

    return {
        'kind': 'model_assisted_candidate_assignment',
        'prediction_source': source,
        'smiles': canonical,
        'solvent': solvent,
        'matches_1h': matches_1h,
        'matches_13c': matches_13c,
        'mae_1h': mae_1h,
        'mae_13c': mae_13c,
        'max_error_1h': max_err_1h,
        'max_error_13c': max_err_13c,
        'outliers': out_1h + out_13c,
        'warning': 'Model-assisted candidate assignment only; verify with 2D NMR (COSY/HSQC/HMBC).'
                   + ('' if source != 'heuristic' else ' No prediction engine answered: the shifts are a crude '
                      'topology estimate, not a model prediction (install one with `cdx.py install-engines magnet`).'),
    }
