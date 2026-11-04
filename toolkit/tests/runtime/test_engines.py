import json
import subprocess
import sys

import pytest

from cdxml_toolkit.engines import consensus, env, envelope, ocsr
from cdxml_toolkit.engines.registry import ENGINES, TASKS, by_task

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
CAFFEINE = 'Cn1c(=O)c2c(ncn2C)n(C)c1=O'


def entry(engine, smiles, ok=True):
    if not ok:
        return envelope.failure('ocsr', engine, ENGINES[engine], 'boom')
    return envelope.result('ocsr', engine, ENGINES[engine], [envelope.describe(smiles)])


# --- registry ------------------------------------------------------------------------------------

def test_every_engine_is_complete_and_licensed():
    for name, spec in ENGINES.items():
        assert spec['task'] in TASKS and spec['kind'] in {'remote', 'runtime', 'local', 'jar'}, name
        assert spec.get('license'), name
        assert 'GPL' not in spec['license'].replace('LGPL', ''), f'{name}: GPL engines are never bundled'
        if spec['kind'] == 'local':
            low, high = spec['python']
            assert 8 <= low <= high <= 13 and spec['requirements'], name
    assert by_task('ocsr') == ['decimer-api', 'decimer-local', 'molscribe', 'molnextr', 'molparser', 'molvec']


def test_downloaded_files_are_pinned_by_hash():
    for name, spec in ENGINES.items():
        weights = spec.get('weights') or {}
        for file in weights.get('files', []):
            assert len(weights['sha256'][file]) == 64, (name, file)
    assert ENGINES['molvec']['jar']['sha256'] and len(ENGINES['molvec']['jar']['sha256']) == 64
    assert any('@' in r and len(r.split('@')[-1]) == 40 for r in ENGINES['molnextr']['requirements']), \
        'MolNexTR is installed from a full commit, not a branch'


# --- environments --------------------------------------------------------------------------------

def test_nothing_is_installed_in_an_empty_home(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    found = env.available()
    assert found['decimer-api'] is True
    assert not any(found[n] for n in ('molscribe', 'molnextr', 'molvec', 'aizynthfinder', 'magnet'))
    with pytest.raises(env.EngineError, match='install-engines molscribe'):
        env.call('molscribe', 'predict', {})


def test_an_environment_without_a_receipt_does_not_count_as_installed(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    python = tmp_path / 'molscribe' / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text('')
    assert env.python_for('molscribe') is None  # a half-finished install must not look usable
    (tmp_path / 'molscribe' / env.RECEIPT).write_text('{}')
    assert env.python_for('molscribe') == python


def test_dry_run_installs_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    report = env.install('molscribe', dry_run=True)
    assert report['python_needed'] == '3.10 to 3.10' and report['license'] == 'MIT'
    assert list(tmp_path.iterdir()) == []


def test_worker_speaks_json_and_never_leaks_a_traceback_to_stdout():
    request = {'engine': 'nothing', 'action': 'predict', 'params': {}, 'data_dir': '.', 'spec': {}}
    done = subprocess.run([sys.executable, str(env.WORKER)], input=json.dumps(request), capture_output=True, text=True)
    payload = json.loads(done.stdout.splitlines()[-1][len(env.MARKER):])
    assert payload['ok'] is False and 'unknown engine action' in payload['error']


# --- comparison ----------------------------------------------------------------------------------

def test_agreement_is_a_candidate_not_a_result():
    outcome = consensus.compare([entry('molscribe', ASPIRIN), entry('molnextr', 'O=C(O)c1ccccc1OC(C)=O')])
    assert outcome['agreement'] == 'all' and outcome['agreed_smiles'] and outcome['needs_review'] is False
    assert outcome['selected'] is None and 'compare every structure with the image' in outcome['rule']


def test_disagreement_selects_nothing():
    outcome = consensus.compare([entry('molscribe', ASPIRIN), entry('molnextr', CAFFEINE), entry('molvec', ASPIRIN)])
    assert outcome['agreement'] == 'split' and outcome['agreed_smiles'] is None and outcome['needs_review']
    assert [g['engines'] for g in outcome['groups']] == [['molscribe', 'molvec'], ['molnextr']]
    assert any('different structures' in n for n in outcome['notes'])


def test_stereo_only_difference_is_named():
    outcome = consensus.compare([entry('molscribe', 'C[C@H](N)C(=O)O'), entry('molnextr', 'C[C@@H](N)C(=O)O')])
    assert outcome['agreed_smiles'] is None and any('stereochemistry' in n for n in outcome['notes'])


def test_a_failed_or_empty_engine_is_reported_and_forces_review():
    outcome = consensus.compare([entry('molscribe', ASPIRIN), entry('molnextr', ASPIRIN),
                                 entry('molvec', None, ok=False)])
    assert outcome['agreed_smiles'] and outcome['needs_review'] is True
    assert outcome['no_result'] == [{'engine': 'molvec', 'reason': 'boom'}]
    single = consensus.compare([entry('molscribe', ASPIRIN)])
    assert single['agreement'] == 'single' and single['agreed_smiles'] is None and single['needs_review']


def test_invalid_smiles_is_flagged_not_accepted():
    bad = envelope.result('ocsr', 'molscribe', ENGINES['molscribe'], [envelope.describe('C(C)(C)(C)(C)C')])
    assert bad['structures'][0]['valid'] is False and bad['warnings']


# --- recognize -----------------------------------------------------------------------------------

@pytest.fixture
def image(tmp_path):
    from PIL import Image
    path = tmp_path / 'structure.png'
    Image.new('RGB', (40, 40), 'white').save(path)
    return str(path)


def test_recognize_runs_each_chosen_engine_and_isolates_failures(image, monkeypatch):
    seen = []

    def call(name, action, params, timeout=0):
        seen.append(name)
        if name == 'molnextr':
            raise env.EngineError('MolNexTR is not installed')
        return [{'smiles': ASPIRIN, 'score': 0.9}]

    monkeypatch.setattr(env, 'call', call)
    answer = ocsr.recognize(image, 'molscribe,molnextr')
    assert seen == ['molscribe', 'molnextr'] and answer['ok'] is True
    assert [e['ok'] for e in answer['engines']] == [True, False]
    assert answer['provenance'] == 'model_prediction' and answer['comparison']['agreement'] == 'single'


def test_recognize_all_never_uploads_without_confirmation(image, monkeypatch):
    monkeypatch.setattr(env, 'available', lambda: {n: n in {'molscribe', 'decimer-api'} for n in ENGINES})
    monkeypatch.setattr(env, 'call', lambda *a, **k: [{'smiles': ASPIRIN}])
    answer = ocsr.recognize(image, 'all')
    assert [e['engine'] for e in answer['engines']] == ['molscribe']


def test_recognize_remote_without_confirmation_is_refused_with_preflight(image):
    answer = ocsr.recognize(image, 'decimer-api')
    assert answer['ok'] is False
    entry_ = answer['engines'][0]
    assert entry_['engine'] == 'decimer-api' and 'confirm_upload' in entry_['error']
    assert len(entry_['preflight']['sha256']) == 64  # the user sees exactly what would be sent


def test_recognize_rejects_unknown_engines_and_missing_files(image):
    with pytest.raises(ValueError, match='unknown OCSR engine'):
        ocsr.recognize(image, 'magic')
    with pytest.raises(ValueError, match='image not found'):
        ocsr.recognize(image + '.missing', 'molscribe')


# --- MolVec output ---------------------------------------------------------------------------------

MOLVEC_ETHANOL = """
   Molvec0111012622342D

  3  2  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.0000    0.5000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  2  3  1  0  0  0  0
M  END
"""


def test_molvec_output_keeps_its_blank_title_line(image, monkeypatch):
    import subprocess
    monkeypatch.setattr(env, 'run_jar', lambda *a, **k: subprocess.CompletedProcess(a, 0, MOLVEC_ETHANOL, ''))
    answer = ocsr.recognize(image, 'molvec')
    assert answer['engines'][0]['structures'][0]['canonical'] == 'CCO'  # a stripped title line shifts the whole header


def test_molvec_that_finds_nothing_is_not_a_structure(image, monkeypatch):
    import subprocess
    monkeypatch.setattr(env, 'run_jar', lambda *a, **k: subprocess.CompletedProcess(a, 0, '', ''))
    entry_ = ocsr.recognize(image, 'molvec')['engines'][0]
    assert entry_['ok'] and entry_['structures'] == [] and entry_['warnings'] == []


def test_every_engine_that_downloads_data_has_a_pinned_hash():
    for name, spec in ENGINES.items():
        if spec.get('data') == 'decimer-segmentation-model':
            assert len(spec['download']['sha256']) == 64 and spec['download']['url'].startswith('https://'), name
        if spec.get('data') == 'synplanner-preset':
            assert spec['sha256'] and all(len(h) == 64 for h in spec['sha256'].values()), name


def test_figshare_files_use_the_api_download_endpoint():
    # ndownloader.figshare.com answers some public files with 403; the API endpoint serves them with Range support
    urls = json.dumps(ENGINES)
    assert 'ndownloader.figshare.com' not in urls
    assert ENGINES['retrochimera']['zip_members']['url'] == 'https://api.figshare.com/v2/file/download/59468882'


def test_the_worker_receives_what_it_needs_to_verify_downloads(monkeypatch, tmp_path):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    captured = {}

    class Done:
        stdout = env.MARKER + json.dumps({'ok': True, 'result': {}})
        stderr = ''

    def run(command, **kwargs):
        captured['request'] = json.loads(kwargs['input'])
        captured['env'] = kwargs['env']
        return Done()

    python = tmp_path / 'synplanner' / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text('')
    (tmp_path / 'synplanner' / env.RECEIPT).write_text('{}')
    monkeypatch.setattr(env, '_run', run)
    env.call('synplanner', 'predict', {'smiles': 'CCO'})
    assert captured['request']['spec']['sha256'] and captured['request']['data_dir'].replace(chr(92), '/').endswith('synplanner/data')
    assert captured['env']['PYSTOW_HOME'] == captured['request']['data_dir']  # model caches stay inside the engine
    assert captured['env']['HF_HUB_OFFLINE'] == '1'  # running an engine never reaches the network


def test_the_nmrnet_checkpoint_path_names_its_fold_after_a_split_on_slashes():
    """infer.py takes path.split('/')[-2] as the output name; a Windows path with backslashes raised IndexError."""
    from cdxml_toolkit.engines import worker

    command = worker._nmrnet_command('D:\\engines\\nmrnet-pp\\data', 'D:\\w\\data-H', 'D:\\w\\results-H', 'H')
    path = command[command.index('--path') + 1]
    assert path.split('/')[-2] == 'cv_seed_42_fold_0' and path.endswith('/checkpoint_last.pt')
    assert '--cpu' in command  # the CPU unless the GPU is asked for
    assert '--cpu' not in worker._nmrnet_command('d', 'data', 'results', 'H', 'cuda')


def test_engine_post_processing_pools_stay_in_one_process():
    """MolScribe and MolNexTR open Pool(16) per image: on Windows that is 16 new Pythons importing torch."""
    import multiprocessing
    import types
    from cdxml_toolkit.engines import worker

    module = types.SimpleNamespace(multiprocessing=multiprocessing)
    worker._serial_pools(module)
    with module.multiprocessing.Pool(16) as pool:
        assert pool.map(abs, [-1, -2]) == [1, 2]
        assert type(pool).__module__.startswith('multiprocessing.pool')  # a thread pool, no child process
        assert pool._processes == 1
    assert multiprocessing.Pool is not module.multiprocessing.Pool  # the real module is left alone


def test_an_engine_uses_the_gpu_only_when_cuda_works_and_cpu_is_not_forced(monkeypatch):
    import sys
    import types
    from cdxml_toolkit.engines import worker

    cuda = types.SimpleNamespace(is_available=lambda: True)
    monkeypatch.setitem(sys.modules, 'torch', types.SimpleNamespace(cuda=cuda))
    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE', raising=False)
    monkeypatch.setattr(worker.sys, 'platform', 'darwin')
    assert worker._device() == 'cpu'  # a Mac stays on the CPU even when torch claims CUDA
    monkeypatch.setattr(worker.sys, 'platform', 'linux')  # the rest holds on Windows and Linux, whatever runs the test
    assert worker._device() == 'cuda'
    monkeypatch.setenv('CHEMDRAW_ENGINE_DEVICE', 'cpu')
    assert worker._device() == 'cpu'
    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE')
    cuda.is_available = lambda: False
    assert worker._device() == 'cpu'


def test_a_download_shows_its_progress_while_a_prediction_keeps_its_output(monkeypatch, tmp_path):
    # a multi-GB fetch otherwise runs for an hour without a line on the terminal
    import subprocess
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    python = tmp_path / 'synplanner' / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text('')
    (tmp_path / 'synplanner' / env.RECEIPT).write_text('{}')
    seen = {}

    class Done:
        stdout = env.MARKER + json.dumps({'ok': True, 'result': {}})
        stderr = None

    def run(command, **kwargs):
        seen[json.loads(kwargs['input'])['action']] = kwargs
        return Done()

    monkeypatch.setattr(env, '_run', run)
    env.call('synplanner', 'fetch', {})
    env.call('synplanner', 'predict', {})
    assert seen['fetch']['capture'] is False  # stderr stays on the terminal
    assert seen['predict']['capture'] is True


def test_progress_lines_are_few_and_end_at_the_total(capsys, monkeypatch):
    from cdxml_toolkit.engines import worker
    monkeypatch.setattr(worker.time, 'monotonic', lambda: 0.0)
    progress = worker._Progress('weights.bin', 1000, unit='MB', scale=10)
    for done in range(0, 1001):
        progress.update(done)
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 21 and lines[-1] == 'weights.bin: 100 of 100 MB (100%)'  # one line per 5 %


def test_chatty_engines_cannot_break_the_result(monkeypatch, tmp_path):
    """Engines print progress and debug lines to stdout; only the marked line is the answer."""
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    python = tmp_path / 'molnextr' / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text('')
    (tmp_path / 'molnextr' / env.RECEIPT).write_text('{}')

    class Done:
        stdout = 'chiral_center_ids (from symbols): []\n' + env.MARKER + json.dumps({'ok': True, 'result': [1]}) + '\nbye\n'
        stderr = ''

    monkeypatch.setattr(env, '_run', lambda *a, **k: Done())
    assert env.call('molnextr', 'predict', {}) == [1]
    Done.stdout = 'only noise\n'
    with pytest.raises(env.EngineError, match='failed to start: only noise'):
        env.call('molnextr', 'predict', {})


def test_decimer_local_has_an_environment_of_its_own_with_pinned_packages_and_weights():
    """It used to install TensorFlow into the shared runtime; its Keras 2 era stack must stay away from the runtime."""
    spec = ENGINES['decimer-local']
    assert spec['kind'] == 'local' and spec['module'] == 'DECIMER' and spec['license'] == 'MIT'
    assert spec['python'] == (10, 11)  # TensorFlow 2.15 has no wheels for Python 3.12
    pinned = {r.split('==')[0] for r in spec['requirements'] if '==' in r}
    assert {'decimer', 'tensorflow'} <= pinned and any(r.startswith('numpy<2') for r in spec['requirements'])
    downloads = spec['downloads']
    assert {d['into'] for d in downloads} == {'DECIMER-V2'}  # where the package looks under PYSTOW_HOME
    assert {d['marker'] for d in downloads} == {'DECIMER_model/saved_model.pb', 'DECIMER_HandDrawn_model/saved_model.pb'}
    assert all(len(d['sha256']) == 64 and d['extract'] == 'zip' and d['url'].startswith('https://zenodo.org/') for d in downloads)


def test_decimer_local_counts_as_installed_only_with_its_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    python = tmp_path / 'decimer-local' / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text('')
    assert env.python_for('decimer-local') is None
    (tmp_path / 'decimer-local' / env.RECEIPT).write_text('{}')
    assert env.python_for('decimer-local') == python
    assert env.data_dir('decimer-local') == tmp_path / 'decimer-local' / 'data'  # the weights stay beside the engine


def _fake_decimer(monkeypatch, answers):
    """A DECIMER package that returns ``answers`` per image, and a TensorFlow that only has to import."""
    import types
    module = types.ModuleType('DECIMER')
    seen = []

    def predict_SMILES(path, confidence=False, hand_drawn=False):
        seen.append((path, confidence, hand_drawn))
        answer = answers[path]
        if isinstance(answer, Exception):
            raise answer
        return answer

    module.predict_SMILES = predict_SMILES
    monkeypatch.setitem(sys.modules, 'DECIMER', module)
    monkeypatch.setitem(sys.modules, 'tensorflow', types.ModuleType('tensorflow'))
    return seen


def _weights(data_dir, *models):
    for model in models:
        (data_dir / 'DECIMER-V2' / model).mkdir(parents=True)
        (data_dir / 'DECIMER-V2' / model / 'saved_model.pb').write_bytes(b'x')


def test_decimer_local_worker_reads_each_image_and_scores_by_mean_token_confidence(tmp_path, monkeypatch):
    from cdxml_toolkit.engines import worker
    seen = _fake_decimer(monkeypatch, {'a.png': ('CCO', [('C', 0.9), ('C', 0.7), ('O', 0.8)]), 'b.png': ValueError('bad image')})
    _weights(tmp_path, 'DECIMER_model')
    out = worker._decimer_local({'images': ['a.png', 'b.png']}, str(tmp_path), {})
    assert out[0]['smiles'] == 'CCO' and out[0]['score'] == pytest.approx(0.8)
    assert out[1] == {'error': 'ValueError: bad image'}  # one bad image does not stop the others
    assert seen == [('a.png', True, False), ('b.png', True, False)]


def test_decimer_local_worker_never_lets_the_package_download_weights(tmp_path, monkeypatch):
    """The package fetches missing models on first use; an engine that is running must not touch the network."""
    from cdxml_toolkit.engines import worker
    _fake_decimer(monkeypatch, {'a.png': ('CCO', [])})
    with pytest.raises(RuntimeError, match='install-engines decimer-local'):
        worker._decimer_local({'images': ['a.png']}, str(tmp_path), {})
    _weights(tmp_path, 'DECIMER_model')
    with pytest.raises(RuntimeError, match='DECIMER_HandDrawn_model'):
        worker._decimer_local({'images': ['a.png'], 'hand_drawn': True}, str(tmp_path), {})
    _weights(tmp_path, 'DECIMER_HandDrawn_model')
    assert worker._decimer_local({'images': ['a.png'], 'hand_drawn': True}, str(tmp_path), {})[0]['smiles'] == 'CCO'


def test_decimer_local_fetch_unpacks_both_model_archives_under_the_package_folder(tmp_path, monkeypatch):
    import hashlib
    import io
    import zipfile
    from cdxml_toolkit.engines import worker

    def archive(root):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as bundle:
            bundle.writestr(f'{root}/saved_model.pb', b'model')
            bundle.writestr(f'{root}/assets/tokenizer.pkl', b'tokens')
        return buffer.getvalue()

    payloads = {'http://host/models.zip': archive('DECIMER_model'), 'http://host/hand.zip': archive('DECIMER_HandDrawn_model')}
    downloaded = []

    def download(url, partial, attempts=80, headers=None):
        downloaded.append(url)
        with open(partial, 'wb') as out:
            out.write(payloads[url])

    monkeypatch.setattr(worker, '_download', download)
    spec = {'data': 'decimer-models', 'downloads': [
        {'url': url, 'path': f'DECIMER-V2/{name}.zip', 'sha256': hashlib.sha256(data).hexdigest(), 'extract': 'zip',
         'into': 'DECIMER-V2', 'marker': f'{root}/saved_model.pb'}
        for (url, data), name, root in zip(payloads.items(), ('models', 'hand'), ('DECIMER_model', 'DECIMER_HandDrawn_model'))]}
    receipt = worker.fetch('decimer-local', {}, str(tmp_path), spec)
    assert (tmp_path / 'DECIMER-V2' / 'DECIMER_model' / 'saved_model.pb').read_bytes() == b'model'
    assert (tmp_path / 'DECIMER-V2' / 'DECIMER_HandDrawn_model' / 'assets' / 'tokenizer.pkl').is_file()
    assert not list((tmp_path / 'DECIMER-V2').glob('*.zip'))  # the archives are not kept
    assert set(receipt['data']) == {'DECIMER-V2/models.zip', 'DECIMER-V2/hand.zip'}
    assert len(downloaded) == 2
    # a second run (after a failure later in the install) does not fetch 300 MB again
    monkeypatch.setattr(worker, '_download', lambda *a, **k: pytest.fail('already unpacked'))
    assert worker.fetch('decimer-local', {}, str(tmp_path), spec) == receipt


def test_structures_inchi_cannot_express_are_not_taken_for_each_other():
    """R groups and `*` have no InChIKey: two different Markush readings must stay two readings."""
    split = consensus.compare([entry('molscribe', '*c1ccccc1'), entry('molvec', '*CCCCO')])
    assert split['agreement'] == 'split' and split['agreed_smiles'] is None and split['needs_review'] is True
    assert len(split['groups']) == 2 and 'different structures' in split['notes'][0]
    same = consensus.compare([entry('molscribe', '*c1ccccc1'), entry('molvec', 'c1ccc(*)cc1')])
    assert same['agreement'] == 'all' and same['agreed_smiles'] == '*c1ccccc1'
    charged = consensus.compare([entry('molscribe', '*[N-]C'), entry('molvec', '*[N-]O')])
    assert 'different structures' in charged['notes'][0]  # a charge sign in the SMILES is not an InChIKey separator
    assert envelope.describe('*c1ccccc1')['inchikey'] is None


def test_a_snapshot_download_is_held_to_its_commit(monkeypatch, tmp_path):
    import types

    from cdxml_toolkit.engines import worker

    seen = {}

    def snapshot_download(repo, **kwargs):
        seen.update(kwargs, repo=repo)
        return str(tmp_path)

    hub = types.ModuleType('huggingface_hub')
    hub.snapshot_download, hub.hf_hub_download = snapshot_download, None
    monkeypatch.setitem(sys.modules, 'huggingface_hub', hub)
    spec = ENGINES['magnet']
    assert worker.fetch('magnet', {}, str(tmp_path), spec)['weights']['revision'] == spec['weights']['revision']
    assert seen['revision'] == spec['weights']['revision'] and seen['allow_patterns'] == ['model_checkpoints/*']


def test_nothing_is_downloaded_from_a_moving_branch_or_an_open_version():
    for name, spec in ENGINES.items():
        weights = spec.get('weights') or {}
        if weights.get('snapshot'):
            assert len(weights['revision']) == 40, name
    assert 'aizynthfinder==4.4.1' in ENGINES['aizynthfinder']['requirements']
    assert 'magnet-nmr==0.2.1' in ENGINES['magnet']['requirements']


def test_the_remote_engine_keeps_its_raw_response_where_asked(image, tmp_path, monkeypatch):
    from cdxml_toolkit.mcp_runtime import decimer_api

    target = str(tmp_path / 'raw.json')
    seen = {}

    def recognize_image(path, **kwargs):
        seen.update(kwargs)
        return {'structures': [{'smiles': 'CCO'}], 'output_path': kwargs['output_path'], 'warnings': []}

    monkeypatch.setattr(decimer_api, 'recognize_image', recognize_image)
    answer = ocsr.recognize(image, 'decimer-api', output_path=target, confirm_upload=True)
    assert seen['output_path'] == target and answer['engines'][0]['output_path'] == target


def test_output_path_without_the_remote_engine_says_nothing_was_written(image, tmp_path, monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: [{'smiles': 'CCO'}])
    answer = ocsr.recognize(image, 'molscribe', output_path=str(tmp_path / 'raw.json'))
    assert any('output_path' in w and 'decimer-api' in w for w in answer['warnings'])
