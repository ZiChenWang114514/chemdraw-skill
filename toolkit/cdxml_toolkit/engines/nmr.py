"""NMR shift prediction. Output is a prediction and is never written into a measured-data field."""

from __future__ import annotations

import time
from pathlib import Path

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
        host = by_index[members[0]['neighbors'][0]]['element'] if nucleus == '1H' and members[0]['neighbors'] else None
        peaks.append({'nucleus': nucleus, 'shift_ppm': round(shift, 2), 'count': len(members),
                      'atoms': sorted(a['index'] for a in members), 'predicted': True,
                      'exchangeable': host in ('O', 'N', 'S')})
    return sorted(peaks, key=lambda p: -p['shift_ppm'])


def simulate(peaks: list, nucleus: str, frequency_mhz: float, width_hz: float = 1.5, points: int = 16384) -> list:
    """Lorentzian singlets on a ppm axis (no coupling): a picture of where the lines fall, not a multiplet pattern."""
    low, high = (-1.0, 12.0) if nucleus == '1H' else (-10.0, 230.0)
    half = width_hz / frequency_mhz / 2  # half width in ppm (1H axis; 13C uses the same Hz-to-ppm rule)
    if nucleus == '13C':
        half = width_hz / (frequency_mhz * 0.2515) / 2
    step = (high - low) / (points - 1)
    axis = [low + i * step for i in range(points)]
    out = []
    for x in axis:
        total = 0.0
        for peak in peaks:
            total += peak['count'] * half * half / ((x - peak['shift_ppm']) ** 2 + half * half)
        out.append((x, total))
    return out[::-1]  # NMR convention: high ppm first


def predict(smiles: str, nucleus: str = '1H', solvent: str = 'chloroform', frequency_mhz: float = 400.0,
            engine: str | None = None, output_path: str | None = None, timeout_seconds: int = 900) -> dict:
    name = engine or 'magnet'
    if name not in ENGINES or ENGINES[name]['task'] != 'nmr':
        raise ValueError(f'unknown nmr engine {name!r} (choose from {", ".join(by_task("nmr"))})')
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
    unsupported = sorted({a.GetSymbol() for a in mol.GetAtoms()} - set(ENGINES[name]['elements']))
    if unsupported:
        raise ValueError(f'{ENGINES[name]["title"]} supports {", ".join(ENGINES[name]["elements"])} only; found '
                         + ", ".join(unsupported))
    canonical = Chem.MolToSmiles(mol)
    started = time.time()
    try:
        raw = env.call(name, 'predict', {'smiles': canonical, 'solvent': key}, timeout=timeout_seconds)
    except env.EngineError as exc:
        return envelope.failure('nmr', name, ENGINES[name], str(exc))
    nuclei = ['1H', '13C'] if nucleus == 'both' else [nucleus]
    spectra = {}
    peaks = {n: _peaks(raw['atoms'], n) for n in nuclei}
    if output_path:
        base = Path(output_path).expanduser().resolve()
        for n in nuclei:
            target = base if len(nuclei) == 1 else base.with_name(f'{base.stem}-{n}{base.suffix}')
            if target.exists():
                raise ValueError(f'{target} exists: choose a new file name')
            target.parent.mkdir(parents=True, exist_ok=True)
            rows = simulate(peaks[n], n, float(frequency_mhz))
            with open(target, 'x', encoding='utf-8') as handle:
                handle.write('ppm,intensity\n')
                handle.writelines(f'{x:.5f},{y:.6f}\n' for x, y in rows)
            spectra[n] = str(target)
    return envelope.result('nmr', name, ENGINES[name], [], smiles=canonical, solvent=key, frequency_mhz=float(frequency_mhz),
                           peaks=peaks, simulated_spectra=spectra, geometry=raw.get('geometry'),
                           elapsed_s=round(time.time() - started, 2), predicted=True,
                           warnings=['predicted shifts, not measured data: do not report them as experimental values',
                                     'the geometry is an RDKit/MMFF conformer; MagNET-Zero was trained on AIMNet2 '
                                     'geometries, so errors can be larger than the published ones',
                                     'simulated spectra draw singlets only (no coupling or multiplets)'] +
                           (['OH/NH/SH proton shifts depend on concentration and exchange; treat them as rough'] if any(
                               p['exchangeable'] for n in nuclei for p in peaks[n]) else []))
