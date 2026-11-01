"""Run one engine action: JSON request on stdin, JSON result on stdout.

Request ``{"engine", "action": "fetch" | "predict", "params", "data_dir", "spec"}``; result
``{"ok": true, "result": ...}`` or ``{"ok": false, "error": ...}``. Started by ``env.call`` with the
interpreter of the engine's own environment, so it imports nothing from this package and uses the
standard library plus the engine only. Everything runs on the CPU: the engines' own device probing
fails on some Apple Silicon setups.
"""

import hashlib
import json
import os
import subprocess
import sys


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(engine, params, data_dir, spec):
    """Download weights or data into ``data_dir`` and return a receipt (hashes, revisions)."""
    os.makedirs(data_dir, exist_ok=True)
    if spec.get('data') == 'aizynthfinder-public-data':
        done = subprocess.run([sys.executable, '-m', 'aizynthfinder.tools.download_public_data', data_dir],
                              capture_output=True, text=True)
        if done.returncode != 0 or not os.path.isfile(os.path.join(data_dir, 'config.yml')):
            raise RuntimeError('download_public_data failed: ' + (done.stderr or done.stdout)[-300:])
        return {'data': {name: _sha256(os.path.join(data_dir, name)) for name in sorted(os.listdir(data_dir))
                         if os.path.isfile(os.path.join(data_dir, name)) and name.endswith(('.onnx', '.hdf5', '.yml'))}}
    if spec.get('data') == 'decimer-segmentation-model':
        return _fetch_file(data_dir, spec['download'])
    if spec.get('data') == 'synplanner-preset':
        return _fetch_synplanner(data_dir, spec)
    weights = spec['weights']
    from huggingface_hub import hf_hub_download, snapshot_download
    if weights.get('snapshot'):
        path = snapshot_download(weights['repo'], repo_type=weights['type'], local_dir=data_dir,
                                 allow_patterns=[weights['include']] if weights.get('include') else None)
        return {'weights': {'repo': weights['repo'], 'path': path}}
    receipt = {}
    for name in weights['files']:
        path = hf_hub_download(weights['repo'], name, repo_type=weights['type'], local_dir=data_dir)
        digest = _sha256(path)
        expected = weights['sha256'][name]
        if digest != expected:
            os.remove(path)
            raise RuntimeError(f'{name} does not match the pinned sha256 (got {digest}); nothing was kept')
        receipt[name] = digest
    return {'weights': receipt}


def _fetch_file(data_dir, download):
    """One file by URL, with retries, checked against its pinned hash (pystow looks for it under PYSTOW_HOME)."""
    import shutil
    import time
    import urllib.request
    target = os.path.join(data_dir, download['path'])
    os.makedirs(os.path.dirname(target), exist_ok=True)
    partial = target + '.part'
    for attempt in range(5):  # model hosts sometimes drop a TLS connection mid-handshake
        try:
            with urllib.request.urlopen(download['url'], timeout=120) as response, open(partial, 'wb') as out:
                shutil.copyfileobj(response, out)
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))
    digest = _sha256(partial)
    if digest != download['sha256']:
        os.remove(partial)
        raise RuntimeError(f'{download["path"]} does not match the pinned sha256 (got {digest}); nothing was kept')
    os.replace(partial, target)
    return {'data': {download['path']: digest}}


def _synplan_cli():
    return os.path.join(os.path.dirname(sys.executable), 'synplan')


BLOCKS_JSON = 'building_blocks/mcule-molport-2026-08/building_blocks.json.gz'
BLOCKS_SMILES = 'building_blocks/mcule-molport-2026-08/building_blocks.smi'


def _fetch_synplanner(data_dir, spec):
    """Download the preset, check every file against its pinned hash, and write the building blocks as SMILES."""
    done = subprocess.run([_synplan_cli(), 'download_preset', '--preset', 'synplanner-gps-mcule-molport',
                           '--save_to', data_dir], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError('synplan download_preset failed: ' + (done.stderr or done.stdout)[-300:])
    receipt = {}
    for relative, expected in spec['sha256'].items():
        path = os.path.join(data_dir, relative)
        digest = _sha256(path) if os.path.isfile(path) else None
        if digest != expected:
            raise RuntimeError(f'{relative} does not match the pinned sha256 (got {digest}); nothing was kept')
        receipt[relative] = digest
    import gzip
    with gzip.open(os.path.join(data_dir, BLOCKS_JSON), 'rt', encoding='utf-8') as handle:
        blocks = json.load(handle)
    with open(os.path.join(data_dir, BLOCKS_SMILES), 'w', encoding='utf-8') as out:  # the planner reads .smi files
        for value in blocks.values():
            for item in (value if isinstance(value, list) else [value]):
                out.write(item['smiles'] + '\n')
    return {'data': receipt}


# --- OCSR -----------------------------------------------------------------------------------------

def _molscribe(params, data_dir, spec):
    import torch
    from molscribe import MolScribe
    model = MolScribe(os.path.join(data_dir, 'swin_base_char_aux_1m.pth'), device=torch.device('cpu'))
    out = []
    for path in params['images']:
        try:
            result = model.predict_image_file(path, return_confidence=True)
            out.append({'smiles': result['smiles'], 'score': float(result['confidence'])})
        except Exception as exc:  # one unreadable crop must not lose the others
            out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


def _molnextr(params, data_dir, spec):
    import functools
    import torch
    torch.load = functools.partial(torch.load, weights_only=True)  # the checkpoint holds tensors only
    from MolNexTR.model import molnextr
    model = molnextr(os.path.join(data_dir, 'molnextr_best.pth'), torch.device('cpu'))
    out = []
    for path in params['images']:
        try:
            result = model.predict_final_results(path, return_atoms_bonds=False)
            out.append({'smiles': result['predicted_smiles']})
        except Exception as exc:
            out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


def _decimer_local(params, data_dir, spec):
    import tensorflow  # noqa: F401  (imported first: the model loads about 4x slower otherwise)
    from cdxml_toolkit.image.structure_from_image import _load_decimer
    predict = _load_decimer(hand_drawn=bool(params.get('hand_drawn')))
    out = []
    for path in params['images']:
        try:
            smiles, confidence = predict(path, confidence=True, hand_drawn=bool(params.get('hand_drawn')))
            values = [float(c) for _, c in confidence]
            out.append({'smiles': smiles, 'score': (sum(values) / len(values)) if values else None})
        except Exception as exc:
            out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


def _segment(params, data_dir, spec):
    import cv2
    from decimer_segmentation import segment_chemical_structures
    os.makedirs(params['out_dir'], exist_ok=True)
    out = []
    for page_index, path in enumerate(params['images']):
        image = cv2.imread(path)
        segments = segment_chemical_structures(image, expand=True, visualization=False) if image is not None else []
        files = []
        for number, segment in enumerate(segments, 1):
            target = os.path.join(params['out_dir'], f'{params["stem"]}-p{page_index + 1}-s{number}.png')
            cv2.imwrite(target, segment)
            files.append(target)
        out.append({'source': path, 'segments': files})
    return out


# --- reactions, retrosynthesis -----------------------------------------------------------------------

def _reactiont5(params, data_dir, spec):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(data_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(data_dir).eval()
    count = max(1, int(params.get('count', 5)))
    out = []
    for text in params['inputs']:
        inputs = tokenizer(text, return_tensors='pt')
        with torch.no_grad():
            result = model.generate(**inputs, max_length=int(params.get('max_length', 150)), num_beams=max(count, 5),
                                    num_return_sequences=count, return_dict_in_generate=True, output_scores=True)
        out.append([{'smiles': tokenizer.decode(seq, skip_special_tokens=True).replace(' ', '').rstrip('.'),
                     'score': float(score)} for seq, score in zip(result.sequences, result.sequences_scores)])
    return out


def _tree(node):
    """Reduce an AiZynthFinder route dictionary to the molecules and reactions that matter."""
    if node.get('type') == 'mol':
        reaction = next((child for child in node.get('children', []) if child.get('type') == 'reaction'), None)
        return {'smiles': node['smiles'], 'in_stock': bool(node.get('in_stock')),
                'reaction': None if reaction is None else {
                    'template': (reaction.get('metadata') or {}).get('template'),
                    'policy_probability': (reaction.get('metadata') or {}).get('policy_probability'),
                    'reactants': [_tree(child) for child in reaction.get('children', [])]}}
    return {'smiles': node.get('smiles')}


def _aizynthfinder(params, data_dir, spec):
    from aizynthfinder.aizynthfinder import AiZynthFinder
    finder = AiZynthFinder(configfile=os.path.join(data_dir, 'config.yml'))
    finder.stock.select(params.get('stock', 'zinc'))
    finder.expansion_policy.select('uspto')
    finder.filter_policy.select('uspto')
    smiles = params['smiles']
    if params.get('steps') == 'single':
        from aizynthfinder.chem import TreeMolecule
        actions, priors = finder.expansion_policy.get_actions([TreeMolecule(parent=None, smiles=smiles)])
        return {'steps': 'single', 'target': smiles, 'options': [{
            'reactants': [[m.smiles for m in group] for group in action.reactants],
            'template': action.metadata.get('template'), 'probability': float(prior)}
            for action, prior in list(zip(actions, priors))[:int(params.get('count', 10))]]}
    finder.config.search.time_limit = int(params.get('time_limit', 60))
    finder.config.search.iteration_limit = int(params.get('iterations', 100))
    finder.target_smiles = smiles
    finder.tree_search()
    finder.build_routes()
    stats = finder.extract_statistics()
    routes = finder.routes.dicts[:int(params.get('count', 5))]
    return {'steps': 'multi', 'target': smiles, 'solved': bool(stats.get('is_solved')),
            'top_score': stats.get('top_score'), 'routes': [_tree(route) for route in routes]}


def _synplanner(params, data_dir, spec):
    import csv
    import tempfile
    work = tempfile.mkdtemp(prefix='synplan-')
    target = os.path.join(work, 'target.smi')
    with open(target, 'w', encoding='utf-8') as handle:
        handle.write(params['smiles'] + '\n')
    config = os.path.join(work, 'planning.yaml')
    with open(config, 'w', encoding='utf-8') as handle:  # the project's standard planning settings
        handle.write('tree:\n  max_iterations: %d\n  max_tree_size: 1000000\n  max_time: %d\n  max_depth: %d\n'
                     '  search_strategy: expansion_first\n  ucb_type: uct\n  c_ucb: 0.1\n  backprop_type: muzero\n'
                     '  evaluation_agg: max\n  exclude_small: True\n  init_node_value: 0.5\n  min_mol_size: 6\n'
                     '  epsilon: 0.0\n  silent: True\nnode_expansion:\n  top_rules: 50\n  rule_prob_threshold: 0.0\n'
                     '  priority_rules_fraction: 0.5\n' % (int(params.get('iterations', 100)),
                                                           int(params.get('time_limit', 60)),
                                                           int(params.get('max_depth', 6))))
    results = os.path.join(work, 'results')
    done = subprocess.run([
        _synplan_cli(), 'planning', '--config', config, '--targets', target,
        '--reaction_rules', os.path.join(data_dir, 'policy/supervised_gps/v1/reaction_rules.tsv'),
        '--building_blocks', os.path.join(data_dir, BLOCKS_SMILES),
        '--policy_network', os.path.join(data_dir, 'policy/supervised_gps/v1/v1/ranking_policy.ckpt'),
        '--results_dir', results, '--export_routes'], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError('synplan planning failed: ' + (done.stderr or done.stdout)[-300:])
    with open(os.path.join(results, 'tree_search_stats.csv'), encoding='utf-8') as handle:
        stats = next(csv.DictReader(handle))
    routes = []
    routes_file = os.path.join(results, 'extracted_routes.json')
    if os.path.isfile(routes_file):
        with open(routes_file, encoding='utf-8') as handle:
            found = json.load(handle)
        routes = found[0] if found else []
    score = stats.get('best_route_score')
    return {'steps': 'multi', 'target': params['smiles'], 'solved': stats.get('solved') == 'True',
            'target_in_stock': stats.get('target_in_stock') == 'True', 'routes_found': int(stats.get('num_routes') or 0),
            'top_score': float(score) if score else None,
            'routes': [_tree(route) for route in routes[:int(params.get('count', 5))]]}


def _magnet(params, data_dir, spec):
    """1H and 13C shifts from an RDKit conformer (MMFF) with MagNET-Zero and MagNET-PCM."""
    import numpy as np
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from magnet import predict_shifts
    mol = Chem.AddHs(Chem.MolFromSmiles(params['smiles']))
    allowed = set(spec_elements(params))
    bad = sorted({a.GetSymbol() for a in mol.GetAtoms()} - allowed)
    if bad:
        raise ValueError('MagNET supports H, C, N, O, F, Cl and S only; found ' + ', '.join(bad))
    ids = AllChem.EmbedMultipleConfs(mol, numConfs=int(params.get('conformers', 10)), randomSeed=7)
    if not len(ids):
        raise ValueError('no 3D conformer could be generated for this structure')
    energies = AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=2000)
    best = min(range(len(energies)), key=lambda i: energies[i][1] if energies[i][1] == energies[i][1] else 1e9)
    xyz = mol.GetConformer(ids[best]).GetPositions()
    numbers = np.array([a.GetAtomicNum() for a in mol.GetAtoms()])
    shifts = predict_shifts(numbers, xyz, solvent=params.get('solvent', 'chloroform'),
                            n_passes=int(params.get('passes', 2)), checkpoints_dir=data_dir, device='cpu')
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
    return {'atoms': [{'index': a.GetIdx(), 'element': a.GetSymbol(), 'shift': None if shifts[a.GetIdx()] != shifts[a.GetIdx()]
                       else float(shifts[a.GetIdx()]), 'class': ranks[a.GetIdx()],
                       'neighbors': [n.GetIdx() for n in a.GetNeighbors()]} for a in mol.GetAtoms()],
            'conformer_energy_kcal': float(energies[best][1]), 'geometry': 'RDKit ETKDG + MMFF94 (lowest of the conformers)'}


def spec_elements(params):
    return ('H', 'C', 'N', 'O', 'F', 'Cl', 'S')


ENGINES = {'molscribe': _molscribe, 'molnextr': _molnextr, 'decimer-local': _decimer_local,
           'decimer-segmentation': _segment, 'reactiont5-forward': _reactiont5, 'reactiont5-retro': _reactiont5,
           'aizynthfinder': _aizynthfinder, 'synplanner': _synplanner, 'magnet': _magnet}


def main():
    answer = sys.stdout
    sys.stdout = sys.stderr  # the engines print progress lines; stdout stays pure JSON
    try:
        request = json.loads(sys.stdin.read())
        engine, action = request['engine'], request['action']
        if action == 'fetch':
            result = fetch(engine, request.get('params') or {}, request['data_dir'], request.get('spec') or {})
        elif action == 'predict' and engine in ENGINES:
            result = ENGINES[engine](request.get('params') or {}, request['data_dir'], request.get('spec') or {})
        else:
            raise ValueError(f'unknown engine action {engine!r} {action!r}')
        payload = {'ok': True, 'result': result}
    except BaseException as exc:
        payload = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
    answer.write('\n@@ENGINE-RESULT@@' + json.dumps(payload) + '\n')  # env.MARKER; engines may print around it
    answer.flush()


if __name__ == '__main__':  # required: the engines start worker processes that re-import this file on macOS
    main()
