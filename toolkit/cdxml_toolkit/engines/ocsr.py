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
    spec = ENGINES[name]
    if name == 'molvec':
        done = env.run_jar(name, ['gov.nih.ncats.molvec.Main', '-f', image], timeout=timeout)
        molfile = done.stdout  # the first line of a mol file is a blank title: keep it
        if done.returncode != 0 or 'V2000' not in molfile and 'V3000' not in molfile:
            return []
        return [envelope.describe(envelope.molfile_to_smiles(molfile))]
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
    return envelope.result('ocsr', 'decimer-api', spec, structures, sha256=answer.get('sha256'),
                           api_origin=answer.get('api_origin'), network_used=True,
                           upstream_warnings=answer.get('warnings', []))


def recognize(image_path: str, engines='decimer-api', hand_drawn: bool = False, output_path: str | None = None,
              timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: str | None = None,
              approved_origin: str | None = None) -> dict:
    """Run the chosen engines on one image. ``all`` means every installed local engine, plus the remote
    DECIMER only when ``confirm_upload`` is true. One engine failing never stops the others."""
    names = resolve(engines)
    if 'all' in names:
        wanted = [n for n in by_task('ocsr') if ENGINES[n]['kind'] != 'remote' and env.available()[n]]
        if confirm_upload:
            wanted.append('decimer-api')
        names = wanted + [n for n in names if n not in ('all', *wanted)]
    image = str(Path(image_path).expanduser().resolve())
    if not Path(image).is_file():
        raise ValueError(f'image not found: {image_path}')
    entries = []
    for name in dict.fromkeys(names):
        started = time.time()
        spec = ENGINES[name]
        if name == 'decimer-api':
            entry = _remote(image, hand_drawn, timeout_seconds, None, confirm_upload, approved_sha256, approved_origin)
        else:
            try:
                entry = envelope.result('ocsr', name, spec, _local(name, image, hand_drawn, timeout_seconds))
            except (env.EngineError, ValueError, OSError) as exc:
                entry = envelope.failure('ocsr', name, spec, str(exc))
        entry['elapsed_s'] = round(time.time() - started, 2)
        entries.append(entry)
    return {'ok': any(e['ok'] for e in entries), 'task': 'ocsr', 'provenance': envelope.PROVENANCE, 'image': image,
            'engines': entries, 'comparison': consensus.compare(entries),
            'warnings': ['predicted structures: compare each with the image before use']}
