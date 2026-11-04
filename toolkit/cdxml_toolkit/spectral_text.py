"""ACS-style characterization text: parse, format and sanity-check NMR, IR, melting point and rotation data.

Nothing here changes a value the user gave: peaks keep the digits they were written with, and a
check that fails is a warning, never a correction.
"""

from __future__ import annotations

import re

from rdkit import Chem

DASH = '\u2013'
DELTA = '\u03b4'
DEGREE_C = '\u00b0C'
ALPHA = '\u03b1'

# residual solvent signals (ppm): 13C of the deuterated solvent, as in the usual impurity tables
CARBON_SOLVENT = {'cdcl3': (77.16,), 'dmsod6': (39.52,), 'cd3od': (49.00,), 'acetoned6': (29.84, 206.26),
                  'c6d6': (128.06,), 'cd2cl2': (53.84,), 'cd3cn': (1.32, 118.26), 'thfd8': (25.31, 67.21)}
SOLVENT_PEAKS_13C: dict[str, list[dict[str, object]]] = {
    'CDCl3': [{'ppm': 77.16, 'shift': 77.16, 'label': 'CDCl3', 'species': 'CDCl3', 'kind': 'solvent', 'multiplicity': 't'}],
    'DMSO-d6': [{'ppm': 39.52, 'shift': 39.52, 'label': 'DMSO-d6', 'species': 'DMSO-d6', 'kind': 'solvent', 'multiplicity': 'septet'}],
    'CD3OD': [{'ppm': 49.00, 'shift': 49.00, 'label': 'CD3OD', 'species': 'CD3OD', 'kind': 'solvent', 'multiplicity': 'septet'}],
    'Acetone-d6': [
        {'ppm': 29.84, 'shift': 29.84, 'label': 'Acetone-d6 (CH3)', 'species': 'Acetone-d6', 'kind': 'solvent', 'multiplicity': 'septet'},
        {'ppm': 206.26, 'shift': 206.26, 'label': 'Acetone-d6 (C=O)', 'species': 'Acetone-d6', 'kind': 'solvent', 'multiplicity': 'm'},
    ],
    'CD3CN': [
        {'ppm': 1.32, 'shift': 1.32, 'label': 'CD3CN (CD3)', 'species': 'CD3CN', 'kind': 'solvent', 'multiplicity': 'septet'},
        {'ppm': 118.26, 'shift': 118.26, 'label': 'CD3CN (CN)', 'species': 'CD3CN', 'kind': 'solvent', 'multiplicity': 's'},
    ],
    'C6D6': [{'ppm': 128.06, 'shift': 128.06, 'label': 'C6D6', 'species': 'C6D6', 'kind': 'solvent', 'multiplicity': 't'}],
    'THF-d8': [
        {'ppm': 25.31, 'shift': 25.31, 'label': 'THF-d8 (beta)', 'species': 'THF-d8', 'kind': 'solvent', 'multiplicity': 'quintet'},
        {'ppm': 67.21, 'shift': 67.21, 'label': 'THF-d8 (alpha)', 'species': 'THF-d8', 'kind': 'solvent', 'multiplicity': 'quintet'},
    ],
    'CD2Cl2': [{'ppm': 53.84, 'shift': 53.84, 'label': 'CD2Cl2', 'species': 'CD2Cl2', 'kind': 'solvent', 'multiplicity': 'quintet'}],
}
SOLVENT_PEAKS_1H: dict[str, list[dict[str, object]]] = {
    'CDCl3': [
        {'ppm': 7.26, 'shift': 7.26, 'label': 'CHCl3', 'species': 'CHCl3', 'kind': 'residual_solvent', 'multiplicity': 's', 'solvent': 'CDCl3'},
        {'ppm': 1.56, 'shift': 1.56, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'CDCl3'},
    ],
    'DMSO-d6': [
        {'ppm': 2.50, 'shift': 2.50, 'label': 'DMSO-d5', 'species': 'DMSO-d5', 'kind': 'residual_solvent', 'multiplicity': 'quintet', 'solvent': 'DMSO-d6'},
        {'ppm': 3.33, 'shift': 3.33, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'DMSO-d6'},
    ],
    'CD3OD': [
        {'ppm': 3.31, 'shift': 3.31, 'label': 'CHD2OD', 'species': 'CHD2OD', 'kind': 'residual_solvent', 'multiplicity': 'quintet', 'solvent': 'CD3OD'},
        {'ppm': 4.87, 'shift': 4.87, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'CD3OD'},
    ],
    'D2O': [
        {'ppm': 4.79, 'shift': 4.79, 'label': 'HDO', 'species': 'HDO', 'kind': 'residual_solvent', 'multiplicity': 's', 'solvent': 'D2O'},
    ],
    'Acetone-d6': [
        {'ppm': 2.05, 'shift': 2.05, 'label': 'acetone-d5', 'species': 'acetone-d5', 'kind': 'residual_solvent', 'multiplicity': 'quintet', 'solvent': 'Acetone-d6'},
        {'ppm': 2.84, 'shift': 2.84, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'Acetone-d6'},
    ],
    'CD3CN': [
        {'ppm': 1.94, 'shift': 1.94, 'label': 'CHD2CN', 'species': 'CHD2CN', 'kind': 'residual_solvent', 'multiplicity': 'quintet', 'solvent': 'CD3CN'},
        {'ppm': 2.13, 'shift': 2.13, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'CD3CN'},
    ],
    'C6D6': [
        {'ppm': 7.16, 'shift': 7.16, 'label': 'C6HD5', 'species': 'C6HD5', 'kind': 'residual_solvent', 'multiplicity': 's', 'solvent': 'C6D6'},
        {'ppm': 0.40, 'shift': 0.40, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'C6D6'},
    ],
    'THF-d8': [
        {'ppm': 3.58, 'shift': 3.58, 'label': 'THF-d7 (alpha)', 'species': 'THF-d7', 'kind': 'residual_solvent', 'multiplicity': 'm', 'solvent': 'THF-d8'},
        {'ppm': 1.72, 'shift': 1.72, 'label': 'THF-d7 (beta)', 'species': 'THF-d7', 'kind': 'residual_solvent', 'multiplicity': 'm', 'solvent': 'THF-d8'},
    ],
    'CD2Cl2': [
        {'ppm': 5.32, 'shift': 5.32, 'label': 'CHDCl2', 'species': 'CHDCl2', 'kind': 'residual_solvent', 'multiplicity': 't', 'solvent': 'CD2Cl2'},
        {'ppm': 1.52, 'shift': 1.52, 'label': 'HDO', 'species': 'HDO', 'kind': 'water', 'multiplicity': 's', 'solvent': 'CD2Cl2'},
    ],
}
_SOLVENT_1H_ALIASES: dict[str, str] = {
    'cdcl3': 'CDCl3',
    'chloroform': 'CDCl3',
    'chloroformd': 'CDCl3',
    'trichloromethane': 'CDCl3',
    'dmsod6': 'DMSO-d6',
    'd6dmso': 'DMSO-d6',
    'dmso': 'DMSO-d6',
    'cd3od': 'CD3OD',
    'meod': 'CD3OD',
    'methanold4': 'CD3OD',
    'd4methanol': 'CD3OD',
    'd2o': 'D2O',
    'water': 'D2O',
    'heavywater': 'D2O',
    'acetoned6': 'Acetone-d6',
    'd6acetone': 'Acetone-d6',
    'acetone': 'Acetone-d6',
    'cd3cn': 'CD3CN',
    'mecnd3': 'CD3CN',
    'acetonitriled3': 'CD3CN',
    'acetonitrile': 'CD3CN',
    'c6d6': 'C6D6',
    'benzened6': 'C6D6',
    'benzene': 'C6D6',
    'thfd8': 'THF-d8',
    'd8thf': 'THF-d8',
    'thf': 'THF-d8',
    'cd2cl2': 'CD2Cl2',
    'dcmd2': 'CD2Cl2',
    'dichloromethaned2': 'CD2Cl2',
}
SOLVENT_TOLERANCE = 0.15

_NUMBER = r'\d+(?:\.\d+)?'
_PEAK = re.compile(rf'^(?P<a>[-+]?{_NUMBER})(?:\s*[{DASH}\u2014-]\s*(?P<b>{_NUMBER}))?\s*(?:\((?P<body>.*)\))?$')
_COUPLING = re.compile(rf'J\s*=\s*(?P<j>{_NUMBER}(?:\s*,\s*{_NUMBER})*)\s*Hz')
_PROTONS = re.compile(r'(\d+)\s*H')
_WORDS = re.compile(r'[A-Za-z][A-Za-z ]*')
_SIMPLE = {'s', 'd', 't', 'q', 'p', 'quint', 'quin', 'sext', 'sept', 'hept', 'm', 'br'}


def _split_top_level(text):
    pieces, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            pieces.append(text[start:index])
            start = index + 1
    pieces.append(text[start:])
    return [piece.strip() for piece in pieces if piece.strip()]


def _read_body(body, piece):
    """'d, J = 8.0, 2.0 Hz, 2H' -> (multiplicity, [J], protons)."""
    couplings, rest = [], body
    found = _COUPLING.search(body)
    if found:
        couplings = [value.strip() for value in found.group('j').split(',')]
        rest = body[:found.start()] + body[found.end():]
    elif re.search(r'\bJ\b', body):
        raise ValueError(f'Cannot read the peak {piece!r}')
    mult = protons = None
    for part in (p.strip() for p in rest.split(',') if p.strip()):
        count = _PROTONS.fullmatch(part)
        if count and protons is None:
            protons = int(count.group(1))
        elif _WORDS.fullmatch(part) and mult is None:
            mult = part
        else:
            raise ValueError(f'Cannot read the peak {piece!r}')
    return mult, couplings, protons


def parse_peaks(text: str) -> list[dict]:
    """Peaks of an NMR list such as ``7.40-7.30 (m, 5H), 5.11 (s, 2H)`` as dicts.

    Every number stays the string it was written as, so ``2.10`` is not turned into ``2.1``.
    """
    text = str(text).strip().lstrip(DELTA).strip().rstrip('.;').strip()
    peaks = []
    for piece in _split_top_level(text):
        found = _PEAK.match(piece)
        if not found:
            raise ValueError(f'Cannot read the peak {piece!r}')
        mult, couplings, protons = _read_body(found.group('body') or '', piece) if found.group('body') else (None, [], None)
        peaks.append({'shift': found.group('a') if not found.group('b') else None,
                      'range': (found.group('a'), found.group('b')) if found.group('b') else None,
                      'mult': mult, 'J': couplings, 'n': protons})
    if not peaks:
        raise ValueError('The peak list is empty')
    return peaks


def _number(value, decimals):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f'A shift or coupling must be a number or text, not {value!r}')
    return value if isinstance(value, str) else f'{value:.{decimals}f}'


def normalize_peaks(items, decimals: int) -> list[dict]:
    """Peaks given as text, numbers or dicts -> the dicts :func:`parse_peaks` returns."""
    peaks = []
    for item in items:
        if isinstance(item, str):
            peaks += parse_peaks(item)
        elif isinstance(item, dict):
            unknown = set(item) - {'shift', 'range', 'mult', 'J', 'n'}
            if unknown or not (item.get('shift') is not None) ^ (item.get('range') is not None):
                raise ValueError(f'A peak needs shift or range, and may carry mult, J and n: {item!r}')
            coupling = item.get('J') or []
            coupling = [coupling] if not isinstance(coupling, (list, tuple)) else coupling
            peaks.append({'shift': _number(item['shift'], decimals) if item.get('shift') is not None else None,
                          'range': tuple(_number(v, decimals) for v in item['range']) if item.get('range') else None,
                          'mult': item.get('mult'), 'J': [_number(v, 1) for v in coupling],
                          'n': int(item['n']) if item.get('n') is not None else None})
        else:
            peaks.append({'shift': _number(item, decimals), 'range': None, 'mult': None, 'J': [], 'n': None})
    if not peaks:
        raise ValueError('The peak list is empty')
    return peaks


def format_peak(peak: dict) -> str:
    head = peak['shift'] if peak['range'] is None else f'{peak["range"][0]}{DASH}{peak["range"][1]}'
    inner = ', '.join(part for part in (
        peak['mult'], f'J = {", ".join(peak["J"])} Hz' if peak['J'] else None,
        f'{peak["n"]}H' if peak['n'] is not None else None) if part)
    return f'{head} ({inner})' if inner else head


def format_peaks(peaks) -> str:
    return ', '.join(format_peak(peak) for peak in peaks)


def known_multiplicity(mult: str) -> bool:
    base = re.sub(r'^(br|app|apparent)\s+', '', mult.strip().lower())
    return base in _SIMPLE or bool(re.fullmatch(r'[dtq]{2,4}', base))


def nucleus_ok(name: str) -> bool:
    found = re.fullmatch(r'(\d{1,3})([A-Z][a-z]?)', name)
    if not found:
        return False
    try:
        Chem.GetPeriodicTable().GetAtomicNumber(found.group(2))
    except (RuntimeError, ValueError):
        return False
    return True


def formula_hydrogens(mol) -> int:
    return sum(atom.GetTotalNumHs() for atom in mol.GetAtoms())


def distinct_carbons(mol) -> int:
    """Carbons that differ by symmetry (what a decoupled 13C spectrum can show at most)."""
    mol = Chem.RemoveHs(mol)
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
    return len({ranks[a.GetIdx()] for a in mol.GetAtoms() if a.GetAtomicNum() == 6})


def _solvent_key(name) -> str:
    return re.sub(r'[\s_\-]', '', str(name or '')).lower()


def _resolve_solvent_1h(solvent: str) -> str | None:
    if not solvent:
        return None
    if solvent in SOLVENT_PEAKS_1H:
        return solvent
    key = _solvent_key(solvent)
    return _SOLVENT_1H_ALIASES.get(key)


def is_solvent_peak_1h(ppm: float, solvent: str, tolerance: float = 0.05) -> dict | None:
    """Return the matched 1H residual solvent peak dict if ``ppm`` is within ``tolerance``, else ``None``."""
    canonical = _resolve_solvent_1h(solvent)
    if canonical is None:
        return None
    val = float(ppm)
    tol = float(tolerance)
    best_entry: dict[str, object] | None = None
    best_delta = tol + 1.0
    for entry in SOLVENT_PEAKS_1H.get(canonical, ()):
        ref_ppm = float(entry['ppm'])  # type: ignore[arg-type]
        delta = abs(val - ref_ppm)
        if delta <= tol and delta < best_delta:
            best_delta = delta
            best_entry = entry
    if best_entry is None:
        return None
    matched = dict(best_entry)
    matched['observed_ppm'] = val
    matched['delta_ppm'] = round(best_delta, 4)
    return matched


def filter_solvent_peaks_1h(peaks: list, solvent: str, tolerance: float = 0.05) -> list:
    """Filter out 1H residual solvent and HDO peaks from ``peaks`` (numbers, dicts, or peak objects)."""
    if not peaks:
        return []
    canonical = _resolve_solvent_1h(solvent)
    if canonical is None:
        return list(peaks)

    filtered = []
    for item in peaks:
        ppm_val: float | None = None
        if isinstance(item, (int, float)):
            ppm_val = float(item)
        elif isinstance(item, dict):
            raw = item.get('ppm')
            if raw is None:
                raw = item.get('shift')
            if raw is None:
                raw = item.get('center')
            if raw is not None:
                try:
                    ppm_val = float(raw)
                except (TypeError, ValueError):
                    ppm_val = None
        else:
            raw = getattr(item, 'ppm', getattr(item, 'shift', None))
            if raw is not None:
                try:
                    ppm_val = float(raw)
                except (TypeError, ValueError):
                    ppm_val = None

        if ppm_val is not None and is_solvent_peak_1h(ppm_val, canonical, tolerance=tolerance) is not None:
            continue
        filtered.append(item)
    return filtered


def _text(value) -> str:
    return str(value)


def _signed(value) -> str:
    text = _text(value)
    return text if text[:1] in '+-' else f'+{text}'


def _nmr(nucleus, config, mol, label, warnings, checks):
    if not nucleus_ok(nucleus):
        raise ValueError(f'{label}: {nucleus!r} is not an NMR nucleus such as 1H, 13C, 19F or 31P')
    config = dict(config or {})
    unknown = set(config) - {'frequency', 'solvent', 'text', 'peaks'}
    if unknown:
        raise ValueError(f'{label}: unknown NMR field(s) {sorted(unknown)}')
    if ('text' in config) == ('peaks' in config):
        raise ValueError(f'{label}: give {nucleus} NMR peaks as either text or peaks')
    decimals = 2 if nucleus == '1H' else 1
    peaks = parse_peaks(config['text']) if 'text' in config else normalize_peaks(config['peaks'], decimals)
    for peak in peaks:
        if peak['mult'] and not known_multiplicity(peak['mult']):
            warnings.append(f"{label}: {nucleus} multiplicity {peak['mult']!r} is not a usual multiplicity code (s, d, t, q, m, br ...).")
    details = ', '.join(part for part in (f"{_text(config['frequency'])} MHz" if config.get('frequency') else None,
                                          config.get('solvent')) if part)
    if nucleus == '1H':
        _check_protons(peaks, mol, label, warnings, checks)
    elif nucleus == '13C':
        _check_carbons(peaks, mol, config.get('solvent'), label, warnings, checks)
    return f'{nucleus} NMR{f" ({details})" if details else ""} {DELTA} {format_peaks(peaks)}'


def _check_protons(peaks, mol, label, warnings, checks):
    expected = formula_hydrogens(mol)
    if any(peak['n'] is None for peak in peaks):
        warnings.append(f'{label}: some 1H signals have no integral, so the proton count was not checked.')
        return
    total = sum(peak['n'] for peak in peaks)
    checks['1H'] = {'integral': total, 'formula_h': expected}
    if total < expected:
        warnings.append(f'{label}: the 1H integral accounts for {total} of {expected} H (exchangeable OH/NH protons '
                        'are often not seen; otherwise check the list).')
    elif total > expected:
        warnings.append(f'{label}: the 1H integral is {total} H, more than the {expected} H of the formula '
                        '(a solvent or impurity signal may be included).')


def _check_carbons(peaks, mol, solvent, label, warnings, checks):
    classes = distinct_carbons(mol)
    checks['13C'] = {'signals': len(peaks), 'distinct_carbons': classes}
    if len(peaks) < classes:
        warnings.append(f'{label}: {len(peaks)} signals for {classes} distinct carbons: quaternary or overlapping '
                        'carbons may be missing; say so if they are, or check the list.')
    elif len(peaks) > classes:
        warnings.append(f'{label}: {len(peaks)} signals for {classes} distinct carbons: C-F or C-P coupling, rotamers '
                        'or an impurity can add signals.')
    for value in CARBON_SOLVENT.get(_solvent_key(solvent), ()):
        for peak in peaks:
            if peak['shift'] is not None and abs(float(peak['shift']) - value) <= SOLVENT_TOLERANCE:
                warnings.append(f"{label}: {peak['shift']} matches the {solvent} solvent signal ({value}); check that it "
                                'is a product signal.')


def _melting_point(value, label, warnings):
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError(f'{label}: mp is a number, "low-high" or [low, high]')
        text = f'{_text(value[0])}{DASH}{_text(value[1])}'
    else:
        text = re.sub(rf'(?<=\d)\s*[{DASH}-]\s*(?=\d)', DASH, _text(value).strip())
    numbers = re.findall(_NUMBER, text)
    if len(numbers) == 2 and float(numbers[1]) - float(numbers[0]) > 5:
        warnings.append(f'{label}: a melting range of {float(numbers[1]) - float(numbers[0]):g} {DEGREE_C} is wide; '
                        'the sample may be impure or the range mistyped.')
    if len(numbers) == 2 and float(numbers[1]) < float(numbers[0]):
        warnings.append(f'{label}: the melting range runs downwards ({text}).')
    return f'mp {text} {DEGREE_C}'


def _rotation(config, label, warnings):
    unknown = set(config) - {'value', 'c', 'solvent', 'temperature', 'wavelength'}
    if unknown or config.get('value') is None:
        raise ValueError(f'{label}: optical_rotation needs value and may carry c, solvent, temperature, wavelength')
    sign = f'[{ALPHA}]{_text(config["temperature"]) if config.get("temperature") is not None else ""}{config.get("wavelength", "D")}'
    conditions = ', '.join(part for part in ((f'c {_text(config["c"])}' if config.get('c') is not None else None),
                                             config.get('solvent')) if part)
    if config.get('c') is None or not config.get('solvent'):
        warnings.append(f'{label}: a specific rotation is only reportable with its concentration (c, g/100 mL) and solvent.')
    return f'{sign} {_signed(config["value"])}{f" ({conditions})" if conditions else ""}'


def _infrared(config, label):
    values = config.get('values') if isinstance(config, dict) else config
    medium = config.get('medium') if isinstance(config, dict) else None
    if not values:
        raise ValueError(f'{label}: ir needs a list of wavenumbers')
    shown = ', '.join(f'{v:g}' if isinstance(v, (int, float)) else _text(v) for v in values)
    return f'IR{f" ({medium})" if medium else ""} {shown} cm-1'


def describe(record: dict, mol, label: str) -> dict:
    """The paragraph (without HRMS) of one compound, with the checks that were run and their warnings.

    Order follows the ACS Style Guide: appearance, Rf, melting point, rotation, IR, then the NMR
    spectra (1H, 13C, other nuclei).
    """
    warnings, checks, parts = [], {}, []
    if record.get('appearance'):
        parts.append(_text(record['appearance']))
    if record.get('rf') is not None:
        rf = record['rf']
        if isinstance(rf, dict):
            parts.append(f'Rf = {_text(rf["value"])}' + (f' ({rf["eluent"]})' if rf.get('eluent') else ''))
        else:
            parts.append(f'Rf = {_text(rf)}')
    if record.get('mp') is not None:
        parts.append(_melting_point(record['mp'], label, warnings))
    if record.get('optical_rotation') is not None:
        parts.append(_rotation(dict(record['optical_rotation']), label, warnings))
    if record.get('ir') is not None:
        parts.append(_infrared(record['ir'], label))
    nmr = dict(record.get('nmr') or {})
    for nucleus in sorted(nmr, key=lambda n: (n != '1H', n != '13C', n)):
        parts.append(_nmr(nucleus, nmr[nucleus], mol, label, warnings, checks))
    return {'parts': parts, 'checks': checks, 'warnings': warnings}
