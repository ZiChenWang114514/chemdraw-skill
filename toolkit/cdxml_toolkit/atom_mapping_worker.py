"""Run one learned atom-mapping backend: JSON request on stdin, JSON result on stdout.

Request ``{"method": "rxnmapper" | "localmapper", "reactions": ["A.B>>C", ...]}``; result
``{"ok": true, "results": [{"mapped_rxn": ..., "confidence" / "confident": ...} | {"error": ...}]}``.
Started by ``mapping_backends.run`` with the interpreter of the backend's own environment, so it
imports nothing from this package and uses the standard library plus the backend only.
"""

import json
import sys


def _rxnmapper(reactions):
    from rxnmapper import RXNMapper
    engine = RXNMapper()
    out = []
    for reaction in reactions:
        try:
            result = engine.get_attention_guided_atom_maps([reaction])[0]
            out.append({'mapped_rxn': result['mapped_rxn'], 'confidence': float(result['confidence'])})
        except Exception as exc:  # one oversized or odd reaction must not lose the others
            out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


def _localmapper(reactions):
    from localmapper import localmapper
    engine = localmapper('cpu')
    out = []
    for reaction in reactions:
        try:
            result = engine.get_atom_map(reaction, return_dict=True)
            out.append({'mapped_rxn': result['mapped_rxn'], 'confident': bool(result.get('confident')),
                        'template': result.get('template')})
        except Exception as exc:
            out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


METHODS = {'rxnmapper': _rxnmapper, 'localmapper': _localmapper}


def main():
    answer = sys.stdout
    sys.stdout = sys.stderr  # the backends print progress lines; stdout stays pure JSON
    try:
        request = json.loads(sys.stdin.read())
        if request.get('method') not in METHODS:
            raise ValueError(f'unknown method {request.get("method")!r}')
        payload = {'ok': True, 'results': METHODS[request['method']](request['reactions'])}
    except BaseException as exc:
        payload = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
    answer.write(json.dumps(payload))
    answer.flush()


if __name__ == '__main__':
    main()
