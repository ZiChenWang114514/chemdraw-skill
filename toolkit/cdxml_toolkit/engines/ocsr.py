"""Recognize a chemical structure image with one or several engines and compare the answers."""

from __future__ import annotations

import time
from pathlib import Path

from . import consensus, env, envelope
from .registry import ENGINES, by_task


def resolve(engines) -> list:
    """Engine names from ``"decimer-api"``, ``"molscribe,molvec"``, a list, or ``"all"`` (see ``recognize``)."""
    if isinstance(engines, str):
        engines = [part.strip() for part in engines.split(',') if part.strip()]
    names = list(engines or ['decimer-api'])
    unknown = [n for n in names if n != 'all' and (n not in ENGINES or ENGINES[n]['task'] != 'ocsr')]
    if unknown:
        raise ValueError(f'unknown OCSR engine {unknown[0]!r} (choose from {", ".join(by_task("ocsr"))}, or all)')
    return names


def _local(name: str, image: str, hand_drawn: bool, timeout: int) -> list:
    if name == 'molvec':
        done = env.run_jar(name, ['gov.nih.ncats.molvec.Main', '-f', image], timeout=timeout)
        molfile = done.stdout  # the first line of a mol file is a blank title: keep it
        if done.returncode != 0 or 'V2000' not in molfile and 'V3000' not in molfile:
            return []
        return [envelope.describe(envelope.molfile_to_smiles(molfile))]
    env._LAST_CALL_META.set(None)
    answers = env.call(name, 'predict', {'images': [image], 'hand_drawn': hand_drawn}, timeout=timeout)
    first = answers[0]
    if 'error' in first:
        raise env.EngineError(first['error'])
    return [envelope.describe(first['smiles'], first.get('score'))]


def _remote(image: str, hand_drawn: bool, timeout: int, output_path, confirm_upload, approved_sha256, approved_origin) -> dict:
    from ..mcp_runtime.decimer_api import DecimerAPIError, recognize_image
    spec = ENGINES['decimer-api']
    try:
        answer = recognize_image(image, hand_drawn=hand_drawn, timeout_seconds=timeout, output_path=output_path,
                                 confirm_upload=confirm_upload, approved_sha256=approved_sha256,
                                 approved_origin=approved_origin)
    except DecimerAPIError as exc:
        refused = exc.as_result()
        return envelope.failure('ocsr', 'decimer-api', spec, refused.get('error', str(exc)),
                                **({'preflight': refused['preflight']} if 'preflight' in refused else {}))
    structures = [envelope.describe(s.get('smiles')) for s in answer.get('structures', [])]
    return envelope.result('ocsr', 'decimer-api', spec, structures, device='remote', sha256=answer.get('sha256'),
                           api_origin=answer.get('api_origin'), network_used=True,
                           upstream_warnings=answer.get('warnings', []),
                           **({'output_path': answer['output_path']} if answer.get('output_path') else {}))


def _resolve_engine_names(engines, confirm_upload: bool) -> list[str]:
    names = resolve(engines)
    if 'all' in names:
        wanted = [n for n in by_task('ocsr') if ENGINES[n]['kind'] != 'remote' and env.available()[n]]
        if confirm_upload:
            wanted.append('decimer-api')
        names = wanted + [n for n in names if n not in ('all', *wanted)]
    return list(dict.fromkeys(names))


def _assemble_report(image: str, entries: list[dict], names: list[str], *,
                     output_path: str | None = None, expected_formula: str | None = None) -> dict:
    warnings = ['predicted structures: compare each with the image before use']
    for entry in entries:
        if entry.get('device_fallback'):
            warnings.append(f'{entry["engine"]}: CUDA failed at runtime; fell back to CPU.')
    if output_path and 'decimer-api' not in names:
        warnings.append('output_path holds the raw decimer-api response; that engine did not run, so nothing was written')
    devs = list(dict.fromkeys(e['device'] for e in entries if e.get('ok') and e.get('device')))
    top_extra = {}
    if devs:
        top_extra['device'] = devs[0] if len(devs) == 1 else 'mixed'
    if any(e.get('device_fallback') for e in entries):
        top_extra['device_fallback'] = True
    accels = [e['accel'] for e in entries if isinstance(e.get('accel'), dict)]
    if accels:
        top_extra['accel'] = accels[0]
    return {'ok': any(e['ok'] for e in entries), 'task': 'ocsr', 'provenance': envelope.PROVENANCE, 'image': image,
            **top_extra, 'engines': entries, 'comparison': consensus.compare(entries, expected_formula=expected_formula),
            'warnings': warnings}


def recognize(image_path: str, engines='decimer-api', hand_drawn: bool = False, output_path: str | None = None,
              timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: str | None = None,
              approved_origin: str | None = None, expected_formula: str | None = None) -> dict:
    """Run the chosen engines on one image. ``all`` means every installed local engine, plus the remote
    DECIMER only when ``confirm_upload`` is true. One engine failing never stops the others. ``output_path``
    is a new JSON file for the raw response of the remote DECIMER; the local engines have none."""
    names = _resolve_engine_names(engines, confirm_upload)
    image = str(Path(image_path).expanduser().resolve())
    if not Path(image).is_file():
        raise ValueError(f'image not found: {image_path}')
    entries = []
    for name in names:
        started = time.time()
        spec = ENGINES[name]
        if name == 'decimer-api':
            entry = _remote(image, hand_drawn, timeout_seconds, output_path, confirm_upload, approved_sha256, approved_origin)
        else:
            try:
                structures = _local(name, image, hand_drawn, timeout_seconds)
                meta = {'device': 'cpu', 'device_fallback': False} if name == 'molvec' else env.last_call_meta(name)
                accel_meta = None if name == 'molvec' else env.last_accel_meta(name)
                extra = {'device': meta['device']}
                if accel_meta:
                    extra['accel'] = accel_meta
                if meta.get('device_fallback'):
                    extra['device_fallback'] = True
                    extra['warnings'] = [f'{name}: CUDA failed at runtime; fell back to CPU.']
                entry = envelope.result('ocsr', name, spec, structures, **extra)
            except (env.EngineError, ValueError, OSError, RuntimeError) as exc:
                entry = envelope.failure('ocsr', name, spec, exc)
        entry['elapsed_s'] = round(time.time() - started, 2)
        entries.append(entry)
    return _assemble_report(image, entries, names, output_path=output_path, expected_formula=expected_formula)


def recognize_batch(image_paths: list[str], engines: str = 'molscribe,molvec', *, hand_drawn: bool = False,
                    timeout_seconds: int = 600, confirm_upload: bool = False, approved_origin: str | None = None,
                    expected_formula: str | None = None) -> list[dict]:
    """Run the chosen engines on a batch of images, calling each worker-backed engine once for the whole batch."""
    if not image_paths:
        return []
    names = _resolve_engine_names(engines, confirm_upload)
    images = []
    for image_path in image_paths:
        image = str(Path(image_path).expanduser().resolve())
        if not Path(image).is_file():
            raise ValueError(f'image not found: {image_path}')
        images.append(image)
    per_image_entries: list[list[dict]] = [[] for _ in images]
    for name in names:
        spec = ENGINES[name]
        if name == 'decimer-api':
            for idx, image in enumerate(images):
                started = time.time()
                entry = _remote(image, bool(hand_drawn), timeout_seconds, None, confirm_upload, None, approved_origin)
                entry['elapsed_s'] = round(time.time() - started, 2)
                per_image_entries[idx].append(entry)
        elif name == 'molvec':
            for idx, image in enumerate(images):
                started = time.time()
                try:
                    structures = _local('molvec', image, bool(hand_drawn), timeout_seconds)
                    entry = envelope.result('ocsr', 'molvec', spec, structures, device='cpu')
                except (env.EngineError, ValueError, OSError, RuntimeError) as exc:
                    entry = envelope.failure('ocsr', 'molvec', spec, exc)
                entry['elapsed_s'] = round(time.time() - started, 2)
                per_image_entries[idx].append(entry)
        else:
            started = time.time()
            env._LAST_CALL_META.set(None)
            try:
                raw = env.call(name, 'predict', {'images': images, 'hand_drawn': bool(hand_drawn)},
                               timeout=timeout_seconds)
                if isinstance(raw, list) and len(raw) == 1 and len(images) > 1:
                    for rest in images[1:]:
                        raw.extend(env.call(name, 'predict', {'images': [rest], 'hand_drawn': bool(hand_drawn)},
                                            timeout=timeout_seconds))
                if not isinstance(raw, list) or len(raw) != len(images):
                    raise env.EngineError(f'{name} returned {len(raw) if isinstance(raw, list) else type(raw).__name__} '
                                          f'answers for {len(images)} images')
                elapsed = round(time.time() - started, 2)
                meta = env.last_call_meta(name)
                accel_meta = env.last_accel_meta(name)
                for idx, item in enumerate(raw):
                    if isinstance(item, dict) and 'error' in item:
                        entry = envelope.failure('ocsr', name, spec, env.EngineError(item['error']))
                    else:
                        try:
                            structures = [envelope.describe(item['smiles'], item.get('score'))]
                            extra = {'device': meta['device']}
                            if accel_meta:
                                extra['accel'] = accel_meta
                            if meta.get('device_fallback'):
                                extra['device_fallback'] = True
                                extra['warnings'] = [f'{name}: CUDA failed at runtime; fell back to CPU.']
                            entry = envelope.result('ocsr', name, spec, structures, **extra)
                        except (env.EngineError, ValueError, OSError, KeyError, TypeError) as exc:
                            entry = envelope.failure('ocsr', name, spec, exc)
                    entry['elapsed_s'] = elapsed
                    per_image_entries[idx].append(entry)
            except (env.EngineError, ValueError, OSError, RuntimeError) as exc:
                elapsed = round(time.time() - started, 2)
                for idx in range(len(images)):
                    entry = envelope.failure('ocsr', name, spec, exc)
                    entry['elapsed_s'] = elapsed
                    per_image_entries[idx].append(entry)
    return [_assemble_report(image, entries, names, expected_formula=expected_formula)
            for image, entries in zip(images, per_image_entries)]
