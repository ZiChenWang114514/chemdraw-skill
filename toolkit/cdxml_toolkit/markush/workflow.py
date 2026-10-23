"""Step-by-step Markush extraction driver for small models.

The driver owns every exact step (geometry, ids, serialization, validation,
files); the model answers one short, closed question at a time::

    init WORKDIR IMAGE [--text claims.txt|.pdf]
    next WORKDIR                  -> one task: what to look at, the question, the answer shape
    submit WORKDIR TASK answer.json
    status WORKDIR

Tasks: ``labels`` (type each numbered text box), ``labels_check`` (second
look at the readback), ``review`` (side-by-side checklist, as edits on the
numbered marks), ``definitions:<name>`` (one variable from the claim text).
Every answer is validated; an invalid answer comes back with what to change,
at most ``MAX_ATTEMPTS`` times, then the task is left for a person
(``needs_review``) and the run continues.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from . import draft_spec, fidelity, layout_detect, text_defs
from .compile import SpecError, build_graph, check_cxsmiles, compile_spec, to_cxsmiles
from .cdxml_writer import write_cdxml
from .spec import plain_label

MAX_ATTEMPTS = 3
MAX_REVIEW_ROUNDS = 3
Renderer = Callable[[Path, Path], bool]
_LABEL_CHARS = re.compile(r"^[A-Za-z0-9()\[\]^_{}'+\-,.= ]+$")


def _sha(data) -> str:
    if isinstance(data, (str, Path)) and Path(data).is_file():
        return hashlib.sha256(Path(data).read_bytes()).hexdigest()[:16]
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')


def parse_answer(text: str):
    """Answers may arrive wrapped in a ```json fence or with prose around them."""
    text = text.strip()
    fence = re.search(r'```(?:json)?\s*(.*?)```', text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except ValueError:
        start = min([i for i in (text.find('{'), text.find('[')) if i >= 0], default=-1)
        if start < 0:
            raise ValueError('The answer is not JSON. Reply with only the JSON object.')
        return json.loads(text[start:text.rfind('}' if text[start] == '{' else ']') + 1])


# ------------------------------------------------------------------ init
def init(workdir, image, text=None, crop=None, reuse=None) -> dict:
    work = Path(workdir)
    if work.exists() and any(work.iterdir()):
        raise FileExistsError(f'{work} is not empty; use a new folder for each run.')
    (work / 'source').mkdir(parents=True)
    src = work / 'source' / ('image' + Path(image).suffix.lower())
    if crop:
        img = cv2.imread(str(image))
        x0, y0, x1, y1 = crop
        cv2.imwrite(str(src.with_suffix('.png')), img[y0:y1, x0:x1])
        src = src.with_suffix('.png')
    else:
        shutil.copyfile(image, src)
    state = {'version': 1, 'image': str(src), 'image_sha': _sha(src), 'text': None, 'stage': 'labels',
             'tasks': {}, 'texts': {}, 'edits': [], 'round': 0, 'notes': [], 'definitions': {}}
    if text:
        tsrc = work / 'source' / ('claims' + Path(text).suffix.lower())
        shutil.copyfile(text, tsrc)
        state['text'] = str(tsrc)
    graph = layout_detect.detect(src)
    _write(work / 'graph.json', graph)
    layout_detect.overlay(src, graph, work / 'marks.png')
    layout_detect.label_sheet(src, graph, work / 'labels.png')
    state['graph_sha'] = _sha({k: v for k, v in graph.items() if k != 'image'})  # path differs per run
    if reuse:
        state['reuse'] = str(Path(reuse) / 'answers')
    _write(work / 'state.json', state)
    return status(work)


def status(workdir) -> dict:
    work = Path(workdir)
    state = _read(work / 'state.json')
    out = {'stage': state['stage'], 'round': state['round'],
           'tasks': {k: v['status'] for k, v in state['tasks'].items()},
           'needs_review': [k for k, v in state['tasks'].items() if v['status'] == 'needs_review'],
           'notes': state['notes']}
    if (work / 'final' / 'report.json').is_file():
        out['report'] = str(work / 'final' / 'report.json')
    return out


# ------------------------------------------------------------------ tasks
def _task_input(state, work, task):
    """What a task depends on; a cached answer is reused only for the same input."""
    if task in ('labels', 'labels_check'):
        return {'graph': state['graph_sha'], 'image': state['image_sha'], 'texts': state['texts'] if task != 'labels' else None}
    if task.startswith('definitions:'):
        return {'chunk': _sha(state['definition_chunks'].get(task.split(':', 1)[1], ''))}
    return {'round': state['round'], 'image': state['image_sha'], 'edits': state['edits']}


def next_task(workdir, renderer: Renderer | None = None) -> dict:
    work = Path(workdir)
    state = _read(work / 'state.json')
    while True:
        task = _advance(state, work, renderer)
        _write(work / 'state.json', state)
        if task is None:
            return {'task': None, 'done': True, **status(work)}
        cached = _cached_answer(state, task)
        if cached is None:
            break
        submit(work, task, cached, renderer=renderer, _state=state)
        state = _read(work / 'state.json')
    info = state['tasks'][task]
    packet = _packet(state, work, task)
    packet.update(task=task, attempt=info['attempts'] + 1, max_attempts=MAX_ATTEMPTS,
                  submit=f'cdx.py markush submit {work} {task} ANSWER.json')
    if info.get('last_errors'):
        packet['fix_these'] = info['last_errors']
    return packet


def _cached_answer(state, task):
    folder = state.get('reuse')
    if not folder or not (Path(folder) / f'{task.replace(":", "_")}.json').is_file():
        return None
    saved = _read(Path(folder) / f'{task.replace(":", "_")}.json')
    if saved.get('input') == state['tasks'][task]['input']:
        return saved['answer']
    return None


def _open(state, work, task):
    if task not in state['tasks']:
        state['tasks'][task] = {'status': 'open', 'attempts': 0, 'input': _task_input(state, work, task)}
    return state['tasks'][task]['status'] == 'open'


def _advance(state, work, renderer):
    """Run automatic steps until a question is needed; return its task id or None."""
    while True:
        st = state['stage']
        if st == 'labels':
            if _open(state, work, 'labels'):
                return 'labels'
            state['stage'] = 'labels_check'
        elif st == 'labels_check':
            if _open(state, work, 'labels_check'):
                _readback(state, work)
                return 'labels_check'
            state['stage'] = 'draft'
        elif st == 'draft':
            state['round'] += 1
            _draft(state, work, renderer)
            state['stage'] = 'review' if state.get('rendered') else 'definitions'
        elif st == 'review':
            task = f'review:{state["round"]}'
            if _open(state, work, task):
                return task
            if state.get('pending_edits') and state['round'] < MAX_REVIEW_ROUNDS:
                state['pending_edits'] = False
                state['stage'] = 'draft'
            else:
                if state.get('pending_edits'):
                    state['notes'].append('Review edits remain after the last round; check the drawing by hand.')
                state['stage'] = 'definitions'
        elif st == 'definitions':
            if 'definition_chunks' not in state:
                state['definition_chunks'] = _chunks(state, work)
            for name in sorted(state['definition_chunks']):
                if _open(state, work, f'definitions:{name}'):
                    return f'definitions:{name}'
            state['stage'] = 'finalize'
        elif st == 'finalize':
            _finalize(state, work, renderer)
            state['stage'] = 'done'
        else:
            return None


def _packet(state, work, task) -> dict:
    graph = _graph(state, work)
    ids = [l['id'] for l in graph['labels']]
    if task == 'labels':
        return {
            'look_at': [str(work / 'labels.png')],
            'question': ('Each row shows one text box from the drawing, with its id on the left. Type the text '
                         'of every box exactly. Write superscripts as ^{...} and subscripts as _{...}; keep '
                         'parentheses. Stacked letters (N over H) are written in reading order: "NH".'),
            'answer_shape': {i: 'text' for i in ids},
            'example': {'T1': '(R^{A})_{n}', 'T2': 'A', 'T3': 'O', 'T7': 'NH', 'T8': 'L^{1}', 'T20': 'N'},
        }
    if task == 'labels_check':
        return {
            'look_at': [str(work / 'readback.png')],
            'question': ('Orange boxes are the text boxes; the blue text under each box is what was typed for '
                         'it. List boxes whose typed text is wrong, with the correct text, and describe any '
                         'text in the drawing that has no orange box. Empty lists mean everything matches.'),
            'answer_shape': {'wrong': {'T#': 'correct text'}, 'unboxed': ['short description and position']},
            'example': {'wrong': {'T12': 'R^{R}'}, 'unboxed': []},
        }
    if task.startswith('review:'):
        rnd = work / 'rounds' / f'{state["round"]:02d}'
        fid = _read(rnd / 'fidelity.json') if (rnd / 'fidelity.json').is_file() else {}
        return {
            'look_at': [str(rnd / 'review.png'), str(rnd / 'diff.png')],
            'question': ('review.png: left is the source with numbered marks (T# text boxes, v# bond ends), '
                         'right is the redrawn structure. diff.png: red = only in the source, blue = only in '
                         'the redrawing. Compare bonds and labels. Report only real differences, using the '
                         'mark ids from the left image. Empty lists mean the redrawing is correct.'),
            'answer_shape': {'missing_bonds': [['id', 'id']], 'extra_bonds': [['id', 'id']],
                             'bond_orders': [['id', 'id', 'order 1-3']], 'text': {'T#': 'correct text'}},
            'example': {'missing_bonds': [['T5', 'T7']], 'extra_bonds': [], 'bond_orders': [['v8', 'v3', 2]],
                        'text': {}},
            'facts': {'match': fid.get('match'), 'draft_notes': state.get('draft_notes', [])},
        }
    if task.startswith('definitions:'):
        name = task.split(':', 1)[1]
        need = state.get('attachments', {}).get(name)
        return {
            'look_at': [],
            'text': state['definition_chunks'][name],
            'question': (f'From the patent text above, give the definition of {name}. "values": concrete '
                         'choices as SMILES fragments, attachment points written [*:1], [*:2] ... ' +
                         (f'({name} has {need} attachment point(s)); ' if need else '') +
                         'for a ring-atom variable (G, X ...) list element symbols. Put the claim wording '
                         'in "text". Leave "values" empty if the text only names a class (e.g. "C1-6 alkyl"). '
                         'Give "count_range" [min, max] only when the label has a repeat count (n, p, q ...); '
                         'otherwise leave it out.'),
            'answer_shape': {'text': 'claim wording', 'values': ['[*:1]F'], 'count_range': [0, 3]},
            'example': {'text': 'RB is halogen or methyl; q is 0, 1 or 2', 'values': ['[*:1]F', '[*:1]Cl',
                        '[*:1]C'], 'count_range': [0, 2]},
        }
    raise KeyError(task)


# ------------------------------------------------------------------ submit
def submit(workdir, task, answer, renderer: Renderer | None = None, _state=None) -> dict:
    work = Path(workdir)
    state = _state or _read(work / 'state.json')
    info = state['tasks'].get(task)
    if not info or info['status'] != 'open':
        raise ValueError(f'Task {task!r} is not waiting for an answer; run `next` to see the current task.')
    if isinstance(answer, (str, Path)) and Path(answer).is_file():
        answer = parse_answer(Path(answer).read_text(encoding='utf-8-sig'))
    elif isinstance(answer, str):
        answer = parse_answer(answer)
    info['attempts'] += 1
    try:
        errors = _apply(state, work, task, answer)
    except (ValueError, KeyError, TypeError) as exc:
        errors = [str(exc)]
    if errors:
        info['last_errors'] = errors
        if info['attempts'] >= MAX_ATTEMPTS:
            info['status'] = 'needs_review'
            state['notes'].append(f'{task}: no valid answer after {MAX_ATTEMPTS} attempts ({errors[0]})')
        _write(work / 'state.json', state)
        return {'accepted': False, 'errors': errors, 'attempts_left': MAX_ATTEMPTS - info['attempts']}
    info['status'] = 'done'
    info.pop('last_errors', None)
    _write(work / 'answers' / f'{task.replace(":", "_")}.json', {'input': info['input'], 'answer': answer})
    _write(work / 'state.json', state)
    return {'accepted': True, 'next': 'run `cdx.py markush next` for the next task'}


def _check_text(tid, text, ids):
    if tid not in ids:
        return f'{tid} is not a text box; boxes are {ids[0]}..{ids[-1]}.'
    if not isinstance(text, str) or not text.strip():
        return f'{tid}: give the text as a non-empty string.'
    if not _LABEL_CHARS.match(text):
        return f'{tid}: {text!r} has characters other than letters, digits, ( ) ^ _ {{ }} and \' + - , .'
    if text.count('{') != text.count('}') or text.count('(') != text.count(')'):
        return f'{tid}: {text!r} has unbalanced braces or parentheses.'
    return None


def _apply(state, work, task, answer):
    graph = _graph(state, work)
    ids = [l['id'] for l in graph['labels']]
    marks = set(ids) | {v['id'] for v in graph['vertices']}
    if task == 'labels':
        if not isinstance(answer, dict):
            return ['Answer with one JSON object: {"T1": "text", ...}.']
        errors = [f'{t} is missing; type the text of every box.' for t in ids if t not in answer]
        errors += [e for t, v in answer.items() if (e := _check_text(t, v, ids))]
        if not errors:
            state['texts'] = {t: answer[t].strip() for t in ids}
        return errors
    if task == 'labels_check':
        if not isinstance(answer, dict) or not isinstance(answer.get('wrong', {}), dict):
            return ['Answer {"wrong": {"T#": "text"}, "unboxed": []}.']
        errors = [e for t, v in answer.get('wrong', {}).items() if (e := _check_text(t, v, ids))]
        if errors:
            return errors
        for t, v in answer.get('wrong', {}).items():
            state['notes'].append(f'{t}: second reading changed {state["texts"][t]!r} to {v!r}.')
            state['texts'][t] = v.strip()
        for item in answer.get('unboxed') or []:
            state['notes'].append(f'Text without a box (not in the drawing yet): {item}')
        return []
    if task.startswith('review:'):
        if not isinstance(answer, dict):
            return ['Answer one JSON object with missing_bonds, extra_bonds, bond_orders and text.']
        errors, edits = [], []
        for key in ('missing_bonds', 'extra_bonds', 'bond_orders'):
            for item in answer.get(key) or []:
                if not isinstance(item, list) or len(item) != (3 if key == 'bond_orders' else 2):
                    errors.append(f'{key}: write each item as ' + ('["v3", "v8", 2]' if key == 'bond_orders'
                                                                    else '["T5", "T7"]') + f'; got {item!r}.')
                    continue
                bad = [x for x in item[:2] if x not in marks]
                if bad:
                    errors.append(f'{key}: {", ".join(map(str, bad))} is not a mark on the left image.')
                    continue
                if key == 'bond_orders' and item[2] not in (1, 2, 3):
                    errors.append(f'bond_orders: order must be 1, 2 or 3; got {item[2]!r}.')
                    continue
                edits.append({'op': key, 'a': item[0], 'b': item[1], **({'order': item[2]} if len(item) == 3 else {})})
        for t, v in (answer.get('text') or {}).items():
            if (e := _check_text(t, v, ids)):
                errors.append(e)
            else:
                edits.append({'op': 'text', 'id': t, 'text': v.strip()})
        if errors:
            return errors
        state['edits'].extend(edits)
        state['pending_edits'] = bool(edits)
        return []
    if task.startswith('definitions:'):
        name = task.split(':', 1)[1]
        return _apply_definition(state, name, answer)
    raise KeyError(task)


def _apply_definition(state, name, answer):
    from rdkit import Chem
    if not isinstance(answer, dict):
        return ['Answer {"text": "...", "values": [...], "count_range": [min, max]}.']
    values = answer.get('values') or []
    need = state.get('attachments', {}).get(name)
    errors = []
    for v in values:
        if not isinstance(v, str):
            errors.append(f'values: {v!r} is not a string.')
            continue
        if re.fullmatch(r'(Cl|Br|Si|[BCNOSPFI])H?', v):
            continue  # ring-atom variable value
        mol = Chem.MolFromSmiles(v)
        if mol is None:
            errors.append(f'values: {v!r} is not valid SMILES; write attachments as [*:1].')
            continue
        maps = sorted(a.GetAtomMapNum() for a in mol.GetAtoms() if a.GetAtomicNum() == 0)
        if need and maps != list(range(1, need + 1)):
            errors.append(f'values: {v!r} has attachment points {maps or "none"}; {name} needs '
                          + ', '.join(f'[*:{i}]' for i in range(1, need + 1)) + '.')
    rng = answer.get('count_range') or None  # [] means no repeat count
    if rng is not None and not (isinstance(rng, list) and len(rng) == 2 and all(isinstance(x, int) for x in rng)
                                and 0 <= rng[0] <= rng[1]):
        errors.append('count_range: give two integers [min, max] with min <= max.')
    if errors:
        return errors
    item = {'text': str(answer.get('text') or ''), 'values': values}
    if rng is not None:
        item['count_range'] = rng
    state['definitions'][name] = item
    return []


# ------------------------------------------------------------------ automatic steps
def _graph(state, work):
    graph = copy.deepcopy(_read(work / 'graph.json'))
    for e in state.get('edits', []):
        if e['op'] == 'text':
            continue
        key = frozenset((e['a'], e['b']))
        graph['edges'] = [x for x in graph['edges'] if frozenset((x['a'], x['b'])) != key]
        if e['op'] == 'missing_bonds':
            graph['edges'].append({'a': e['a'], 'b': e['b'], 'order': 1})
        elif e['op'] == 'bond_orders':
            graph['edges'].append({'a': e['a'], 'b': e['b'], 'order': e['order']})
    return graph


def _texts(state):
    texts = dict(state['texts'])
    for e in state.get('edits', []):
        if e['op'] == 'text':
            texts[e['id']] = e['text']
    return texts


def _readback(state, work):
    graph = _graph(state, work)
    img = cv2.imread(state['image'], cv2.IMREAD_COLOR)
    if graph['upscale'] > 1:
        img = cv2.resize(img, None, fx=graph['upscale'], fy=graph['upscale'], interpolation=cv2.INTER_CUBIC)
    img = cv2.copyMakeBorder(img, 0, 40, 0, 120, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    fs = max(0.4, graph['char_px'] / 50)
    for lab in graph['labels']:
        x0, y0, x1, y1 = lab['box']
        cv2.rectangle(img, (x0 - 2, y0 - 2), (x1 + 2, y1 + 2), (0, 140, 255), 1)
        cv2.putText(img, state['texts'].get(lab['id'], '?'), (x0, y1 + int(18 * fs) + 4), cv2.FONT_HERSHEY_SIMPLEX,
                    fs, (200, 60, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(work / 'readback.png'), img)


def _draft(state, work, renderer):
    rnd = work / 'rounds' / f'{state["round"]:02d}'
    rnd.mkdir(parents=True, exist_ok=False)
    graph = _graph(state, work)
    out = draft_spec.draft(graph, _texts(state))
    state['draft_notes'] = out['notes']
    state['rendered'] = False
    if out['spec'] is None:
        state['notes'].extend(out['notes'])
        return
    spec = out['spec']
    spec['definitions'] = state.get('definitions', {})
    _write(rnd / 'markush.json', spec)
    _write(rnd / 'layout.json', out['layout'])
    try:
        g = build_graph(spec)
    except SpecError as exc:
        state['draft_notes'] = list(out['notes']) + exc.errors
        return
    state['attachments'] = _attachment_counts(spec, g)
    (rnd / 'drawing.cdxml').write_text(write_cdxml(g, out['layout']), encoding='utf-8')
    if renderer is None:
        state['notes'].append('Native rendering unavailable: the drawing is an unrendered draft and was not reviewed.')
        return
    png = rnd / 'drawing.png'
    if not renderer(rnd / 'drawing.cdxml', png) or not png.is_file():
        state['notes'].append(f'Native render failed in round {state["round"]}.')
        return
    state['rendered'] = True
    fid = fidelity.compare(state['image'], png, rnd / 'diff.png')
    _write(rnd / 'fidelity.json', fid)
    _side_by_side(work / 'marks.png', png, rnd / 'review.png')


def _side_by_side(left, right, out, height=760):
    panels = []
    for path in (left, right):
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            a = img[:, :, 3:4].astype(float) / 255
            img = (img[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
        k = height / img.shape[0]
        panels.append(cv2.resize(img, (round(img.shape[1] * k), height), interpolation=cv2.INTER_AREA))
    gap = np.full((height, 16, 3), 255, np.uint8)
    gap[:, 7:9] = 180
    cv2.imwrite(str(out), np.hstack([panels[0], gap, panels[1]]))


def _attachment_counts(spec, g):
    """How many [*:n] points a definition value needs, keyed by plain label."""
    counts = {}
    for i, info in enumerate(g.atoms):
        if info.get('kind') == 'attach' or not info.get('label'):
            continue
        name = info.get('plain') or plain_label(info['label'])
        atom = g.mol.GetAtomWithIdx(i)
        in_ring = atom.IsInRing() and info.get('kind') == 'generic' and atom.GetDegree() >= 2 \
            and not any(r['ref'] == info['ref'] for r in g.rings)
        counts[name] = 1 if info['ref'] in {gr['group'] for gr in g.groups} else \
            (None if in_ring and atom.GetDegree() == 2 else atom.GetDegree())
    return counts


def _chunks(state, work):
    if not state.get('text'):
        return {}
    texts = _texts(state)
    kinds = [draft_spec.classify(t) for t in texts.values()]
    rings = {plain_label(texts[l['id']]) for l in _graph(state, work)['labels'] if l.get('in_circle') is not None}
    names = sorted({plain_label(k[1]) for k in kinds if k[0] in ('generic', 'group')} | rings)
    counts = {plain_label(k[1]): k[2] for k in kinds if k[0] == 'group'}
    found = text_defs.locate(text_defs.load_text(state['text']), names, counts=counts, rings=rings)
    missing = [n for n in names if n not in found]
    if missing:
        state['notes'].append('No definition found in the text for: ' + ', '.join(missing))
    return found


def _finalize(state, work, renderer):
    final = work / 'final'
    final.mkdir(exist_ok=True)
    rounds = sorted((work / 'rounds').glob('[0-9][0-9]')) if (work / 'rounds').is_dir() else []
    report = {'notes': state['notes'], 'needs_review': [k for k, v in state['tasks'].items()
                                                        if v['status'] == 'needs_review'], 'rounds': len(rounds)}
    if not rounds or not (rounds[-1] / 'markush.json').is_file():
        report['error'] = 'No drawable spec was produced.'
        _write(final / 'report.json', report)
        return
    last = rounds[-1]
    spec = _read(last / 'markush.json')
    spec['definitions'] = state.get('definitions', {})
    _write(final / 'markush.json', spec)
    shutil.copyfile(last / 'layout.json', final / 'layout.json')
    try:
        result = compile_spec(spec)
    except SpecError as exc:
        report['error'] = exc.errors
        _write(final / 'report.json', report)
        return
    (final / 'markush.cxsmiles').write_text(result['cxsmiles'] + '\n', encoding='utf-8')
    (final / 'markush.mol').write_text(result['molblock'], encoding='utf-8')
    shutil.copyfile(last / 'drawing.cdxml', final / 'markush.cdxml')
    if (last / 'drawing.png').is_file():
        shutil.copyfile(last / 'drawing.png', final / 'markush.png')
    if (last / 'fidelity.json').is_file():
        report['fidelity'] = _read(last / 'fidelity.json')
    defined = set(spec['definitions'])
    labels = set(state.get('attachments', {}))
    report['cxsmiles'] = result['cxsmiles']
    report['checks'] = result.get('checks', [])
    report['undefined'] = sorted(labels - defined) if state.get('text') else []
    report['unused_definitions'] = sorted(defined - labels)
    _write(final / 'report.json', report)
