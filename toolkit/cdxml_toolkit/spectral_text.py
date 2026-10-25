"""ACS-style characterization text: parse, format and sanity-check NMR, IR, melting point and rotation data.

Nothing here changes a value the user gave: peaks keep the digits they were written with, and a
check that fails is a warning, never a correction.
"""

from __future__ import annotations

import re

from rdkit import Chem

DASH = '–'
DELTA = 'δ'
DEGREE_C = '°C'
ALPHA = 'α'

# residual solvent signals (ppm): 13C of the deuterated solvent, as in the usual impurity tables
CARBON_SOLVENT = {'cdcl3': (77.16,), 'dmsod6': (39.52,), 'cd3od': (49.00,), 'acetoned6': (29.84, 206.26),
                  'c6d6': (128.06,), 'cd2cl2': (53.84,), 'cd3cn': (1.32, 118.26)}
SOLVENT_TOLERANCE = 0.15

_NUMBER = r'\d+(?:\.\d+)?'
_PEAK = re.compile(rf'^(?P<a>[-+]?{_NUMBER})(?:\s*[{DASH}—-]\s*(?P<b>{_NUMBER}))?\s*(?:\((?P<body>.*)\))?$')
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
