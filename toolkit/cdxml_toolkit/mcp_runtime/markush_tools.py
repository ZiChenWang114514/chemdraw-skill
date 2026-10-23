"""Markush (generic structure) tools: validate, compile, enumerate and detect.

A Markush structure is kept as a ``markush.json`` spec.  It compiles to
CXSMILES (``$`` labels, ``m:`` variable attachment), a V3000 molfile and an
editable CDXML drawing.  Readers turn generic labels into carbon, so chemistry
is taken from the spec or CXSMILES, never from reading the CDXML back.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import artifact_safety


def _new_dir(output_dir):
    target = Path(output_dir).resolve()
    if target.exists():
        raise artifact_safety.OutputExistsError(f'Refusing to overwrite an existing directory: {target}')
    return target


def markush_validate(spec_path: str) -> dict:
    """Check a markush.json spec; every error says what to change."""
    from ..markush.spec import validate_spec
    errors = validate_spec(spec_path)
    return {'ok': not errors, 'errors': errors}


def markush_compile(spec_path: str, output_dir: str, layout_path: str | None = None,
                    render: bool = True) -> dict:
    """Compile a spec into markush.cxsmiles, markush.mol (V3000), markush.cdxml and a native PNG.

    ``layout_path`` holds coordinates (for example from the image workflow) so the
    drawing follows the source figure; without it RDKit coordinates are used.
    ``output_dir`` must not exist yet.
    """
    from ..markush.cdxml_writer import write_cdxml
    from ..markush.compile import SpecError, compile_spec
    target = _new_dir(output_dir)
    try:
        result = compile_spec(spec_path)
    except SpecError as exc:
        return {'ok': False, 'errors': exc.errors}
    layout = json.loads(Path(layout_path).read_text(encoding='utf-8')) if layout_path else None
    with artifact_safety.staging_directory(target) as stage:
        (stage / 'markush.cxsmiles').write_text(result['cxsmiles'] + '\n', encoding='utf-8')
        (stage / 'markush.mol').write_text(result['molblock'], encoding='utf-8')
        (stage / 'markush.cdxml').write_text(write_cdxml(result['graph'], layout), encoding='utf-8')
        artifact_safety.publish_directory(stage, target)
    out = {'ok': not result['checks'], 'cxsmiles': result['cxsmiles'], 'checks': result['checks'],
           'files': sorted(str(p) for p in target.iterdir()), 'native_render': 'not_run'}
    if render:
        from .official_overrides import render_to_png
        png = render_to_png(str(target / 'markush.cdxml'), str(target / 'markush.png'))
        out['native_render'] = 'ok' if png.get('ok') else png.get('error', 'failed')
        if png.get('ok'):
            out['files'].append(str(target / 'markush.png'))
    return artifact_safety.with_artifacts(out, out['files'])


def markush_enumerate(spec_path: str, count: int = 5, seed: int = 0) -> dict:
    """Sample concrete members from the definition values of a spec (SMILES)."""
    from ..markush.compile import SpecError, enumerate_members
    if not 1 <= int(count) <= 200:
        return {'ok': False, 'error': 'count must be 1..200'}
    try:
        return {'ok': True, **enumerate_members(spec_path, int(count), int(seed))}
    except SpecError as exc:
        return {'ok': False, 'errors': exc.errors}


def markush_detect(image_path: str, output_dir: str) -> dict:
    """Find text boxes, bonds and ring circles in a clean Markush drawing.

    Writes graph.json (pixel geometry with T# text-box and v# bond-end ids),
    marks.png (the ids drawn on the image) and labels.png (one enlarged row per
    text box, for transcription).  No chemistry is guessed here.
    """
    from ..markush import layout_detect
    target = _new_dir(output_dir)
    graph = layout_detect.detect(image_path)
    with artifact_safety.staging_directory(target) as stage:
        (stage / 'graph.json').write_text(json.dumps(graph, indent=1), encoding='utf-8')
        layout_detect.overlay(image_path, graph, stage / 'marks.png')
        layout_detect.label_sheet(image_path, graph, stage / 'labels.png')
        artifact_safety.publish_directory(stage, target)
    files = sorted(str(p) for p in target.iterdir())
    return artifact_safety.with_artifacts(
        {'ok': True, 'labels': len(graph['labels']), 'vertices': len(graph['vertices']),
         'bonds': len(graph['edges']), 'circles': len(graph['circles']), 'files': files}, files)


MARKUSH_TOOLS = {f.__name__: f for f in (markush_validate, markush_compile, markush_enumerate, markush_detect)}
