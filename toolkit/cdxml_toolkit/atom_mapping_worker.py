"""Run one learned atom-mapping backend: JSON request on stdin, JSON result on stdout.

Request ``{"method": "rxnmapper" | "localmapper", "reactions": ["A.B>>C", ...]}``; result
``{"ok": true, "results": [{"mapped_rxn": ..., "confidence" / "confident": ...} | {"error": ...}]}``.
Started by ``mapping_backends.run`` with the interpreter of the backend's own environment, so it
imports nothing from this package and uses the standard library plus the backend only.
"""

import json
import os
import sys

RXNMAPPER_CHUNK_SIZE = 16


def _rxnmapper(reactions):
    from rxnmapper import RXNMapper
    engine = RXNMapper()
    out = []
    for start in range(0, len(reactions), RXNMAPPER_CHUNK_SIZE):
        chunk = list(reactions[start:start + RXNMAPPER_CHUNK_SIZE])
        try:
            results = engine.get_attention_guided_atom_maps(chunk)
            if not isinstance(results, list) or len(results) != len(chunk):
                raise RuntimeError(f'expected {len(chunk)} results, got {len(results) if isinstance(results, list) else type(results).__name__}')
            for result in results:
                out.append({'mapped_rxn': result['mapped_rxn'], 'confidence': float(result['confidence'])})
        except Exception:  # one oversized or odd reaction must not lose the others
            for reaction in chunk:
                try:
                    result = engine.get_attention_guided_atom_maps([reaction])[0]
                    out.append({'mapped_rxn': result['mapped_rxn'], 'confidence': float(result['confidence'])})
                except Exception as exc:
                    out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


def _localmapper_device() -> str:
    if os.environ.get('CHEMDRAW_ENGINE_DEVICE', '').strip().lower() == 'cpu':
        return 'cpu'
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except Exception:
        return 'cpu'


def _localmapper(reactions):
    from localmapper import localmapper
    device = _localmapper_device()
    engine = None
    cpu_engine = None
    if device == 'cuda':
        try:
            engine = localmapper('cuda')
        except Exception:
            device = 'cpu'
    if engine is None:
        engine = localmapper('cpu')
        cpu_engine = engine
    out = []
    for reaction in reactions:
        try:
            result = engine.get_atom_map(reaction, return_dict=True)
            out.append({'mapped_rxn': result['mapped_rxn'], 'confident': bool(result.get('confident')),
                        'template': result.get('template')})
        except Exception as exc:
            if device == 'cuda':
                try:
                    if cpu_engine is None:
                        cpu_engine = localmapper('cpu')
                    result = cpu_engine.get_atom_map(reaction, return_dict=True)
                    engine = cpu_engine
                    device = 'cpu'
                    out.append({'mapped_rxn': result['mapped_rxn'], 'confident': bool(result.get('confident')),
                                'template': result.get('template')})
                    continue
                except Exception:
                    if 'cuda' in str(exc).lower():
                        engine = cpu_engine
                        device = 'cpu'
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
