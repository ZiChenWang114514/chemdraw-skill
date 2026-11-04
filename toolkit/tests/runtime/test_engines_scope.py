"""On-demand installation: what to recommend, what a missing engine reports, and safe removal."""
import json
import os

import pytest

from cdxml_toolkit.engines import env, envelope, ocsr
from cdxml_toolkit.engines.registry import BUNDLES, ENGINES, GUIDE, RECOMMEND, disk_mb


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    monkeypatch.setattr(env, '_nvidia_gpu', lambda: None)  # the tests that want a GPU say so
    return tmp_path


def fake_install(home, name, megabytes=1):
    folder = home / name
    folder.mkdir()
    (folder / env.RECEIPT).write_text('{}')
    (folder / 'weights.bin').write_bytes(b'x' * megabytes * 1000)
    return folder


# --- the data ------------------------------------------------------------------------------------

def test_every_installable_engine_says_when_to_install_it_and_what_it_costs():
    for name, spec in ENGINES.items():
        if spec['kind'] != 'remote':
            guide = GUIDE[name]
            assert guide['use_when'] and guide['skip_when'] and guide['disk_mb'] > 0, name


def test_bundles_name_real_engines_and_every_need_has_a_bundle():
    for name, bundle in BUNDLES.items():
        assert bundle['engines'] and all(e in ENGINES for e in bundle['engines']), name
        assert all(ENGINES[e]['kind'] != 'remote' for e in bundle['engines']), name
    assert any('decimer-local' in BUNDLES[b]['engines'] for b in RECOMMEND['ocsr'])
    assert all(b in BUNDLES for options in RECOMMEND.values() for b in options)
    assert disk_mb(BUNDLES['ocsr-lite']['engines']) < disk_mb(BUNDLES['ocsr-standard']['engines']) < \
        disk_mb(BUNDLES['ocsr-full']['engines'])


# --- recommending --------------------------------------------------------------------------------

def test_recommend_lists_the_smallest_useful_set_first_and_downloads_nothing(home):
    out = env.recommend('ocsr')
    assert out['suggested'] == 'ocsr-standard' and not out['already_installed']
    first = out['options'][0]
    assert first['missing'] == ['molscribe', 'molvec'] and first['download_mb'] == GUIDE['molscribe']['disk_mb'] + GUIDE['molvec']['disk_mb']
    assert first['command'] == 'cdx.py install-engines --bundle ocsr-standard'
    assert list(home.iterdir()) == []  # reading only


def test_recommend_marks_what_is_already_there(home, monkeypatch):
    monkeypatch.setattr(env, 'available', lambda: {n: n in ('molscribe', 'molvec') or ENGINES[n]['kind'] == 'remote'
                                                   for n in ENGINES})
    out = env.recommend('ocsr')
    assert out['already_installed'] and out['options'][0]['command'] is None
    assert out['options'][2]['missing'] == ['molnextr', 'molparser']


def test_recommend_rejects_an_unknown_need():
    with pytest.raises(ValueError, match='unknown need') as caught:
        env.recommend('weather')
    assert 'retrosynthesis' in str(caught.value)  # the task names are offered too


def test_every_engine_task_name_is_accepted_as_a_need(home):
    from cdxml_toolkit.engines.registry import RECOMMEND
    for task in {spec['task'] for spec in ENGINES.values()}:
        out = env.recommend(task)
        assert out['task'] == task and out['need'] in RECOMMEND, task
    assert env.recommend('retrosynthesis')['options'] == env.recommend('retro')['options']
    assert env.recommend('segmentation')['need'] == 'pdf'


# --- a missing engine explains itself ------------------------------------------------------------

def test_a_missing_engine_carries_what_the_user_needs_to_decide(home):
    with pytest.raises(env.EngineMissing) as caught:
        env.call('magnet', 'predict', {})
    hint = caught.value.hint
    assert hint['engine'] == 'magnet' and hint['size_mb'] == GUIDE['magnet']['disk_mb']
    assert hint['license'] and hint['command'] == 'cdx.py install-engines magnet' and hint['use_when']


def test_the_failure_envelope_keeps_the_hint(home):
    result = envelope.failure('nmr', 'magnet', ENGINES['magnet'],
                                                           env.EngineMissing('magnet', 'MagNET is not installed'))
    assert result['ok'] is False and result['install_hint']['engine'] == 'magnet'
    assert 'install_hint' not in envelope.failure('nmr', 'magnet', ENGINES['magnet'], 'plain failure')


def test_an_ocsr_run_reports_the_hint_for_the_engine_that_is_missing(home):
    result = ocsr.recognize(__file__, engines='molscribe')
    assert result['engines'][0]['install_hint']['engine'] == 'molscribe'


# --- installing is refused offline, and costs are shown up front ----------------------------------

def test_installing_is_refused_offline_but_a_dry_run_still_works(home, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_OFFLINE', '1')
    refused = env.install('molscribe')
    assert refused['ok'] is False and 'CHEMDRAW_OFFLINE' in refused['error'] and list(home.iterdir()) == []
    assert env.install('molscribe', dry_run=True)['disk_mb'] == GUIDE['molscribe']['disk_mb']


def test_status_shows_each_engines_disk_use(home):
    fake_install(home, 'magnet', megabytes=2000)
    out = env.status()
    assert out['engines']['magnet']['disk_used_mb'] == 2.0 and out['disk_used_mb'] == 2.0
    assert out['engines']['molscribe']['disk_used_mb'] == 0 and out['engines']['molscribe']['use_when']


def test_status_reports_configured_device_per_engine(home, monkeypatch):
    for name, dev in (('molscribe', 'cuda'), ('decimer-local', 'cpu'), ('aizynthfinder', 'cpu')):
        folder = home / name
        (folder / 'bin').mkdir(parents=True)
        (folder / 'bin' / 'python3').write_text('')
        (folder / env.RECEIPT).write_text(json.dumps({'device': dev}))
    (home / 'molvec').mkdir()
    (home / 'molvec' / ENGINES['molvec']['jar']['name']).write_bytes(b'jar')
    (home / 'molvec' / env.RECEIPT).write_text('{}')
    monkeypatch.setattr(env, 'java', lambda: 'java')
    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE', raising=False)

    engines = env.status()['engines']
    assert engines['decimer-api']['device'] == 'remote'
    assert engines['molscribe']['device'] == 'cuda'
    assert engines['decimer-local']['device'] == 'cpu'
    assert engines['aizynthfinder']['device'] == 'cpu'
    assert engines['molvec']['device'] == 'cpu'
    assert engines['magnet']['device'] is None  # not installed

    monkeypatch.setenv('CHEMDRAW_ENGINE_DEVICE', 'cpu')
    assert env.status()['engines']['molscribe']['device'] == 'cpu'

    # Legacy receipts written before 'device' was recorded infer CUDA from an installed +cu torch wheel
    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE')
    monkeypatch.setattr(env.sys, 'platform', 'win32')
    legacy = home / 'magnet'
    (legacy / 'bin').mkdir(parents=True)
    (legacy / 'bin' / 'python3').write_text('')
    (legacy / env.RECEIPT).write_text(json.dumps({'disk_mb': 10.0}))
    assert env.status()['engines']['magnet']['device'] == 'cpu'
    (legacy / 'Lib' / 'site-packages' / 'torch-2.10.0+cu128.dist-info').mkdir(parents=True)
    assert env.status()['engines']['magnet']['device'] == 'cuda'


# --- removal -------------------------------------------------------------------------------------

def test_removal_is_a_dry_run_until_confirmed(home):
    folder = fake_install(home, 'magnet')
    preview = env.remove('magnet')
    assert preview['dry_run'] and preview['removed'] is False and folder.exists()
    done = env.remove('magnet', dry_run=False)
    assert done['removed'] and not folder.exists()
    assert env.remove('magnet', dry_run=False)['note'] == 'not installed'


def test_a_folder_that_is_not_an_installed_engine_is_never_deleted(home):
    stray = home / 'magnet'
    stray.mkdir()
    (stray / 'my-notes.txt').write_text('keep me')
    refused = env.remove('magnet', dry_run=False)
    assert refused['ok'] is False and 'refused' in refused['error'] and (stray / 'my-notes.txt').exists()


@pytest.mark.skipif(os.name == 'nt', reason='symbolic links need privileges on Windows')
def test_a_symlinked_engine_folder_is_refused_and_its_target_survives(home, tmp_path_factory):
    target = tmp_path_factory.mktemp('precious')
    (target / env.RECEIPT).write_text('{}')
    (target / 'data.txt').write_text('keep me')
    (home / 'magnet').symlink_to(target, target_is_directory=True)
    refused = env.remove('magnet', dry_run=False)
    assert refused['ok'] is False and (target / 'data.txt').exists()


def test_engines_without_a_folder_of_their_own_cannot_be_removed(home):
    assert env.remove('decimer-api', dry_run=False)['ok'] is False


def test_the_install_command_reads_bundles_and_estimates_the_download(home, monkeypatch, capsys):
    from cdxml_toolkit.engines import __main__ as cli
    assert cli.main(['--bundle', 'ocsr-lite', '--dry-run']) == 0
    out = json.loads(capsys.readouterr().out)
    assert [r['engine'] for r in out['reports']] == ['molvec'] and out['download_mb_estimate'] == 2


def _refused(capsys, *argv):
    from cdxml_toolkit.engines import __main__ as cli
    with pytest.raises(SystemExit) as stopped:
        cli.main(list(argv))
    assert stopped.value.code == 2
    return capsys.readouterr().err


def test_each_command_speaks_with_its_own_name(home, capsys):
    assert 'cdx.py engines' in _refused(capsys, '--recommend', 'lava').splitlines()[0]
    assert 'cdx.py remove-engines' in _refused(capsys, '--remove', 'lava').splitlines()[0]
    assert 'cdx.py install-engines' in _refused(capsys, 'lava').splitlines()[0]


def test_a_mistaken_command_gets_one_line_not_the_whole_usage(home, capsys):
    assert 'usage:' not in _refused(capsys, 'lava')
    assert 'usage:' not in _refused(capsys, '--recommend', 'lava')


def test_installing_nothing_points_to_the_recommendation(home, capsys):
    assert 'cdx.py engines --recommend' in _refused(capsys)


def test_removing_nothing_says_how_to_remove(home, capsys):
    message = _refused(capsys, '--remove')
    assert 'cdx.py remove-engines' in message and 'NAME' in message


def test_an_unknown_task_lists_the_tasks(home, capsys):
    message = _refused(capsys, '--task', 'lava')
    assert "'lava'" in message and 'retrosynthesis' in message


def test_the_help_lists_every_need(capsys):
    from cdxml_toolkit.engines import __main__ as cli
    from cdxml_toolkit.engines.registry import RECOMMEND
    with pytest.raises(SystemExit):
        cli.main(['--help'])
    text = ' '.join(capsys.readouterr().out.split())
    offered = text.split('--recommend NEED')[-1].split('--remove')[0]
    assert all(need in offered for need in RECOMMEND)


def test_the_new_needs_are_recommended_with_their_limits_and_nothing_is_downloaded():
    assert [o['bundle'] for o in env.recommend('retro')['options']] == ['retro', 'retro-chimera']
    assert [o['bundle'] for o in env.recommend('nmr')['options']] == ['nmr', 'nmr-pp']
    conditions = env.recommend('conditions')['options'][0]
    assert conditions['missing'] == ['reacon'] and conditions['command'] == 'cdx.py install-engines --bundle conditions'
    assert env.hint('reacon')['license'].startswith('not declared')
    assert env.hint('retrochimera')['size_mb'] >= 5000


def test_a_download_cut_short_is_retried_instead_of_accepted(tmp_path):
    """A host that closes the connection early (and ignores Range) must not leave a truncated file behind."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from cdxml_toolkit.engines import worker

    body = bytes(range(256)) * 4096  # 1 MiB
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.headers.get('Range'))
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body[:300_000] if len(calls) == 1 else body)  # the first answer stops early

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        target = tmp_path / 'file.bin'
        worker._download(f'http://127.0.0.1:{server.server_port}/f', str(target), attempts=5)
    finally:
        server.shutdown()
    assert target.read_bytes() == body and len(calls) == 2


def test_a_bundle_without_downloads_in_its_spec_still_fetches(tmp_path):
    """The installer sends None for every spec key an engine lacks; the worker must treat that as empty."""
    from cdxml_toolkit.engines import worker

    spec = {'data': 'retrochimera-pistachio', 'downloads': None, 'zip_members': None, 'archive_members': None, 'stock': None}
    assert worker._fetch_bundle(str(tmp_path), spec) == {'data': {}}


def _blocks(path, smiles):
    import gzip
    import json
    with gzip.open(path, 'wt', encoding='utf-8') as handle:
        json.dump({str(i): {'smiles': s} for i, s in enumerate(smiles)}, handle)


def test_building_blocks_are_not_rebuilt_when_the_source_hash_matches(tmp_path, monkeypatch):
    from cdxml_toolkit.engines import worker

    source, target = tmp_path / 'blocks.json.gz', tmp_path / 'blocks.smi'
    _blocks(source, ['OCC', 'CCO', 'c1ccccc1'])
    worker._ensure_smiles(str(source), str(target))
    assert target.read_text(encoding='utf-8').split() == sorted({'CCO', 'c1ccccc1'})
    built = []
    monkeypatch.setattr(worker, '_blocks_to_smiles', lambda *a: built.append(a))
    worker._ensure_smiles(str(source), str(target))
    assert built == []


def test_changed_source_hash_rebuilds(tmp_path):
    from cdxml_toolkit.engines import worker

    source, target = tmp_path / 'blocks.json.gz', tmp_path / 'blocks.smi'
    _blocks(source, ['CCO'])
    worker._ensure_smiles(str(source), str(target))
    _blocks(source, ['CCN'])
    worker._ensure_smiles(str(source), str(target))
    assert target.read_text(encoding='utf-8').split() == ['CCN']


def test_aizynthfinder_fetch_rejects_missing_or_unpinned_files(tmp_path, monkeypatch):
    from cdxml_toolkit.engines import worker

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        (tmp_path / 'config.yml').write_text('expansion:\n  uspto:\n    - uspto_model.onnx\n    - uspto_templates.csv.gz\n'
                                             'stock:\n  zinc: zinc_stock.hdf5\n', encoding='utf-8')
        (tmp_path / 'uspto_model.onnx').write_bytes(b'model')
        return worker.subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setattr(worker.subprocess, 'run', fake_run)
    monkeypatch.setattr(worker.time, 'sleep', lambda s: None)
    spec = {'data': 'aizynthfinder-public-data', 'sha256': {'uspto_model.onnx': worker.hashlib.sha256(b'model').hexdigest()}}
    with pytest.raises(RuntimeError, match='uspto_templates.csv.gz'):
        worker.fetch('aizynthfinder', {}, str(tmp_path), spec)
    assert len(calls) == 3  # retried before giving up
    (tmp_path / 'uspto_templates.csv.gz').write_bytes(b'templates')
    (tmp_path / 'zinc_stock.hdf5').write_bytes(b'stock')
    with pytest.raises(RuntimeError, match='pinned sha256'):  # a file in config.yml without a pin is refused
        worker.fetch('aizynthfinder', {}, str(tmp_path), spec)
    spec['sha256'].update({'uspto_templates.csv.gz': worker.hashlib.sha256(b'templates').hexdigest(),
                           'zinc_stock.hdf5': worker.hashlib.sha256(b'stock').hexdigest()})
    receipt = worker.fetch('aizynthfinder', {}, str(tmp_path), spec)
    assert sorted(receipt['data']) == ['uspto_model.onnx', 'uspto_templates.csv.gz', 'zinc_stock.hdf5']


def _worker():
    from cdxml_toolkit.engines import worker
    return worker


def _serve(handler):
    import threading
    from http.server import HTTPServer

    server = HTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_a_permanent_http_error_is_not_retried_for_an_hour(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler
    from urllib.error import HTTPError

    worker = _worker()
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def log_message(self, *args):
            pass

    monkeypatch.setattr('time.sleep', lambda s: pytest.fail('a missing file must not be retried'))
    server = _serve(Handler)
    url = f'http://127.0.0.1:{server.server_port}/gone'
    try:
        with pytest.raises(HTTPError):
            worker._download(url, str(tmp_path / 'a.part'))
        with pytest.raises(HTTPError):
            worker._download_range(url, 0, 9, str(tmp_path / 'b.part'))
    finally:
        server.shutdown()
    assert len(calls) == 2


def test_a_busy_host_is_still_retried(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler

    worker = _worker()
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            first = len(calls) == 1
            self.send_response(429 if first else 200)
            self.send_header('Content-Length', '0' if first else '2')
            self.end_headers()
            if not first:
                self.wfile.write(b'ok')

        def log_message(self, *args):
            pass

    monkeypatch.setattr('time.sleep', lambda s: None)
    server = _serve(Handler)
    target = tmp_path / 'a.part'
    try:
        worker._download(f'http://127.0.0.1:{server.server_port}/f', str(target))
    finally:
        server.shutdown()
    assert target.read_bytes() == b'ok' and len(calls) == 2


def _forbidden_then(body, forbidden):
    """A Range-serving handler that answers the first ``forbidden`` requests with 403."""
    from http.server import BaseHTTPRequestHandler
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.headers.get('Range'))
            if len(calls) <= forbidden:
                self.send_response(403)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            first, last = (int(x) for x in self.headers['Range'].split('=')[1].split('-'))
            chunk = body[first:last + 1]
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {first}-{last}/{len(body)}')
            self.send_header('Content-Length', str(len(chunk)))
            self.end_headers()
            self.wfile.write(chunk)

        def log_message(self, *args):
            pass
    return Handler, calls


def test_a_sporadic_403_from_a_signed_url_host_is_retried_in_range_reads(tmp_path, monkeypatch):
    # figshare redirects every request to a freshly signed URL, and that host sometimes answers 403
    worker = _worker()
    monkeypatch.setattr('time.sleep', lambda s: None)
    body = bytes(range(100))
    for read in (lambda url: worker._RangeFile(url).read(),
                 lambda url: worker.remote_range(url, 10, 19),
                 lambda url: (worker._download_range(url, 10, 19, str(tmp_path / 'r.part')),
                              (tmp_path / 'r.part').read_bytes())[1]):
        handler, calls = _forbidden_then(body, forbidden=2)
        server = _serve(handler)
        try:
            data = read(f'http://127.0.0.1:{server.server_port}/f')
        finally:
            server.shutdown()
        (tmp_path / 'r.part').unlink(missing_ok=True)
        assert data in (body, body[10:20]) and len(calls) >= 3


def test_a_lasting_403_still_ends_the_range_read(tmp_path, monkeypatch):
    from urllib.error import HTTPError
    worker = _worker()
    monkeypatch.setattr('time.sleep', lambda s: None)
    handler, calls = _forbidden_then(b'x' * 10, forbidden=10 ** 6)
    server = _serve(handler)
    try:
        with pytest.raises(HTTPError):
            worker.remote_range(f'http://127.0.0.1:{server.server_port}/f', 0, 9)
    finally:
        server.shutdown()
    assert len(calls) == worker.FORBIDDEN_RETRIES + 1


def test_a_garbled_answer_during_a_range_download_is_retried(tmp_path, monkeypatch):
    import http.client
    import io
    import urllib.request

    worker = _worker()
    answers = [http.client.BadStatusLine('garbage'), io.BytesIO(b'0123456789')]

    def urlopen(request, timeout=0):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr('time.sleep', lambda s: None)
    target = tmp_path / 'a.part'
    worker._download_range('http://host/f', 0, 9, str(target))
    assert target.read_bytes() == b'0123456789'


def test_a_file_already_verified_is_not_downloaded_again(tmp_path, monkeypatch):
    import hashlib

    worker = _worker()
    (tmp_path / 'stock').mkdir()
    (tmp_path / 'stock' / 'blocks.gz').write_bytes(b'blocks')
    digest = hashlib.sha256(b'blocks').hexdigest()
    monkeypatch.setattr(worker, '_download', lambda *a, **k: pytest.fail('nothing to download'))
    answer = worker._fetch_file(str(tmp_path), {'url': 'http://host/f', 'path': 'stock/blocks.gz', 'sha256': digest})
    assert answer == {'data': {'stock/blocks.gz': digest}}


def test_the_scratch_folder_of_a_run_is_gone_when_the_worker_exits():
    import subprocess
    import sys
    from pathlib import Path

    worker = _worker()
    code = (f'import sys; sys.path.insert(0, {str(Path(worker.__file__).parent)!r}); import os, worker; '
            "work = worker._scratch('t-'); os.chdir(work); print(work)")
    done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout.strip() and not Path(done.stdout.strip()).exists()
    assert Path(worker.__file__).read_text(encoding='utf-8').count('mkdtemp') == 1  # every engine goes through it


def _ready_to_install(home, monkeypatch, name='magnet'):
    python = home / name / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text('')
    (home / name / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    monkeypatch.setattr(env, '_pip', lambda *a, **k: None)


def _gpu_install(home, monkeypatch, gpu, name='molparser', has_vision=True):
    _ready_to_install(home, monkeypatch, name)
    calls = []
    monkeypatch.setattr(env, '_pip', lambda python, reqs, log, *a, **k: calls.append((list(reqs), k.get('index_url'))))
    monkeypatch.setattr(env, '_nvidia_gpu', lambda: gpu)
    monkeypatch.setattr(env, '_has_package', lambda python, package: has_vision)
    monkeypatch.setattr(env, '_torch_probe', lambda python: ('2.5.0', True))  # a CPU torch before the swap; CUDA works after it
    monkeypatch.setattr(env, 'call', lambda *a, **k: {})
    return env.install(name), calls


def test_an_nvidia_gpu_gets_a_cuda_build_of_torch_for_an_engine_that_can_use_it(home, monkeypatch):
    from cdxml_toolkit.engines.registry import CUDA_TORCH
    report, calls = _gpu_install(home, monkeypatch, 'NVIDIA GeForce RTX 5090 Laptop GPU')
    reqs, index = calls[-1]
    assert index == CUDA_TORCH['index']
    assert reqs == [f'torch=={CUDA_TORCH["torch"]}+{CUDA_TORCH["tag"]}',
                    f'torchvision=={CUDA_TORCH["torchvision"]}+{CUDA_TORCH["tag"]}']
    assert report['ok'] and report['device'] == 'cuda'
    receipt = json.loads((home / 'molparser' / env.RECEIPT).read_text())
    assert receipt['device'] == 'cuda'


def test_no_gpu_or_an_engine_without_torch_keeps_the_cpu_build(home, monkeypatch):
    report, calls = _gpu_install(home, monkeypatch, None)
    assert all(index is None for _, index in calls) and report['device'] == 'cpu'
    report, calls = _gpu_install(home, monkeypatch, 'RTX', name='decimer-segmentation')  # TensorFlow, CPU on Windows
    assert all(index is None for _, index in calls) and report['device'] == 'cpu'


def test_every_torch_engine_can_take_the_cuda_build():
    # torch 1.13 to 2.5 has no kernels for current GPUs (an RTX 50xx is sm_120), so every torch engine is moved
    # to a CUDA build that has them; their outputs on the GPU matched the CPU builds when this was set
    torch_engines = {name for name, spec in ENGINES.items()
                     if any(r.split('=')[0].split('<')[0].strip() == 'torch' or r.startswith('torch==')
                            for r in spec.get('requirements', [])) or name in ('molscribe', 'molnextr')}
    assert torch_engines and all(ENGINES[name].get('gpu') for name in torch_engines), torch_engines


def test_an_engine_with_compiled_torch_extensions_gets_a_matching_cuda_build(home, monkeypatch):
    # torch_scatter / torch_cluster wheels exist only for some torch builds, so MagNET takes its own build
    cuda = ENGINES['magnet']['cuda']
    report, calls = _gpu_install(home, monkeypatch, 'RTX', name='magnet', has_vision=False)
    torch_call = next(c for c in calls if c[1] == cuda['index'])
    assert torch_call[0] == [f'torch=={cuda["torch"]}+{cuda["tag"]}']
    assert calls[-1][0] == cuda['requirements'] and all(cuda['tag'] in r for r in cuda['requirements'])
    assert report['device'] == 'cuda' and report['torch'] == f'{cuda["torch"]}+{cuda["tag"]}'


def test_engine_downloads_are_cached_under_the_engine_home(home, monkeypatch):
    import subprocess
    seen = {}
    monkeypatch.delenv('UV_CACHE_DIR', raising=False)
    monkeypatch.delenv('PIP_CACHE_DIR', raising=False)
    monkeypatch.setattr(env, '_uv', lambda: 'uv')
    monkeypatch.setattr(env, '_step', lambda cmd, log, environment: seen.update(environment))
    env._pip('python', ['x'], None)
    assert seen['UV_CACHE_DIR'] == str(home / '.cache' / 'uv') and seen['PIP_CACHE_DIR'] == str(home / '.cache' / 'pip')
    monkeypatch.setenv('UV_CACHE_DIR', 'elsewhere')
    env._pip('python', ['x'], None)
    assert seen['UV_CACHE_DIR'] == 'elsewhere'  # a cache the user chose is kept


def test_a_folder_with_an_interpreter_but_no_pyvenv_cfg_is_made_a_venv_again(home, monkeypatch):
    """Without pyvenv.cfg the launcher runs the base Python: packages would land there and the engine never works."""
    folder = home / 'magnet'
    (folder / 'bin').mkdir(parents=True)
    (folder / 'bin' / 'python3').write_text('')
    created = []
    monkeypatch.setattr(env, '_create', lambda name, where, log: created.append(name) or where / 'bin' / 'python3')
    monkeypatch.setattr(env, '_pip', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('stop after the venv step')))
    env.install('magnet')
    assert created == ['magnet']
    (folder / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    created.clear()
    env.install('magnet')
    assert created == []


def test_an_install_stopped_during_its_download_does_not_count_as_installed(home, monkeypatch):
    _ready_to_install(home, monkeypatch)
    started = []

    def run(command, **kwargs):
        started.append(command[0])
        raise KeyboardInterrupt  # the terminal closed, the machine slept: no handler gets to clean up

    monkeypatch.setattr(env, '_run', run)
    with pytest.raises(KeyboardInterrupt):
        env.install('magnet')
    assert started == [str(home / 'magnet' / 'bin' / 'python3')]  # the download ran in the engine's own interpreter
    assert env.available()['magnet'] is False


def test_installing_again_withdraws_the_old_receipt_until_the_download_ends(home, monkeypatch):
    _ready_to_install(home, monkeypatch)
    (home / 'magnet' / env.RECEIPT).write_text('{}')
    seen = []

    class Done:
        stdout = env.MARKER + '{"ok": true, "result": {"weights": {}}}'
        stderr = ''

    def run(command, **kwargs):
        seen.append(env.available()['magnet'])
        return Done()

    monkeypatch.setattr(env, '_run', run)
    assert env.install('magnet')['ok'] is True
    assert seen == [False] and env.available()['magnet'] is True


def test_java_is_found_the_way_the_rest_of_the_toolkit_finds_it(monkeypatch):
    """The macOS /usr/bin/java stub is not Java, and an extracted runtime is not on PATH."""
    from cdxml_toolkit.resolve import jre_manager

    asked = {}

    def get_java(download=True):
        asked['download'] = download
        return '/opt/jre/bin/java'

    monkeypatch.setattr(jre_manager, 'get_java', get_java)
    assert env.java() == '/opt/jre/bin/java' and asked == {'download': False}  # looking never downloads


@pytest.mark.skipif(os.name == 'nt', reason='the stand-in interpreter is a shell script')
def test_bytes_that_are_not_utf8_cannot_lose_the_answer(home):
    python = home / 'molnextr' / 'bin' / 'python3'
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\ncat > /dev/null\nprintf '\\377\\n" + env.MARKER + '{"ok": true, "result": [1]}' + "\\n'\n")
    python.chmod(0o755)
    (home / 'molnextr' / env.RECEIPT).write_text('{}')
    assert env.call('molnextr', 'predict', {}) == [1]


def test_the_engines_tables_come_from_the_registry_and_need_their_markers():
    from cdxml_toolkit.engines import table
    with pytest.raises(ValueError, match='engines-table'):
        table.render('no markers here')
    text = table.render('\n'.join(table.MARKERS['engines'] + table.MARKERS['bundles']))
    assert text == table.render(text)  # rendering twice changes nothing
    for name, spec in ENGINES.items():
        row = next(line for line in text.splitlines() if line.startswith(f'| `{name}` |'))
        assert (f'**{spec["license"]}**' in row) == bool(spec.get('restricted'))
    assert all(f'| `{name}` |' in text for name in BUNDLES)


def test_a_size_marker_in_the_offer_table_shows_the_registry_sum_of_its_bundle():
    from cdxml_toolkit.engines import table
    blocks = '\n'.join(table.MARKERS['engines'] + table.MARKERS['bundles'])
    stale = '<!--size:ocsr-standard-->about 2 GB<!--/size--> and <!--size:ocsr-lite-->1 GB<!--/size--> and <!--size:retro-chimera-->x<!--/size-->'
    text = table.render(stale + '\n' + blocks)
    first = text.splitlines()[0]
    assert f'about {disk_mb(BUNDLES["ocsr-standard"]["engines"]) / 1000:.1f} GB' in first
    assert f'{disk_mb(BUNDLES["ocsr-lite"]["engines"])} MB' in first  # under a gigabyte it stays in megabytes
    assert f'about {disk_mb(BUNDLES["retro-chimera"]["engines"]) / 1000:.1f} GB' in first
    assert text == table.render(text)
    with pytest.raises(ValueError, match='no-such-bundle'):
        table.render('<!--size:no-such-bundle-->x<!--/size-->\n' + blocks)


def test_recognize_batch_calls_each_worker_engine_once_and_aligns_results(tmp_path, monkeypatch):
    from cdxml_toolkit.engines import consensus, document

    img1 = tmp_path / 'a.png'
    img2 = tmp_path / 'b.png'
    img1.write_bytes(b'img1')
    img2.write_bytes(b'img2')

    assert ocsr.recognize_batch([]) == []

    calls = []

    def fake_call(name, action, params, timeout=0):
        calls.append((name, action, list(params.get('images', []))))
        return [{'smiles': 'c1ccccc1'}, {'smiles': 'CCO'}]

    monkeypatch.setattr(env, 'call', fake_call)
    monkeypatch.setattr(env, 'last_call_meta', lambda name: {'device': 'cuda', 'device_fallback': False})

    reports = ocsr.recognize_batch([str(img1), str(img2)], engines='molscribe,molnextr', expected_formula='C6H6')
    assert len(reports) == 2
    assert len(calls) == 2
    assert calls[0] == ('molscribe', 'predict', [str(img1.resolve()), str(img2.resolve())])
    assert calls[1] == ('molnextr', 'predict', [str(img1.resolve()), str(img2.resolve())])
    assert reports[0]['comparison']['agreed_smiles'] == 'c1ccccc1'
    assert reports[0]['comparison']['groups'][0]['matches_expected_formula'] is True
    assert reports[1]['comparison']['agreed_smiles'] == 'CCO'
    assert reports[1]['comparison']['groups'][0]['matches_expected_formula'] is False

    # document.extract delegates all segments in a single recognize_batch call
    batch_calls = []
    monkeypatch.setattr(document, '_render_pages', lambda *a, **k: [(1, str(img1))])
    monkeypatch.setattr(document, '_segment', lambda *a, **k: ([{'page': 1, 'bbox': [0, 0, 10, 10], 'path': str(img1.resolve())},
                                                                {'page': 1, 'bbox': [10, 10, 20, 20], 'path': str(img2.resolve())}], 'opencv'))
    monkeypatch.setattr(document, '_sheet', lambda *a, **k: None)
    monkeypatch.setattr(ocsr, 'recognize_batch', lambda paths, *a, **k: batch_calls.append(list(paths)) or reports)
    out = document.extract(str(img1), str(tmp_path / 'out'), engines='molscribe,molnextr')
    assert batch_calls == [[str(img1.resolve()), str(img2.resolve())]]
    assert len(out['segments']) == 2


def test_consensus_distinguishes_omitted_vs_inverted_stereo_tautomers_and_expected_formula():
    from cdxml_toolkit.engines import consensus

    # Omitted vs specified stereochemistry (same connectivity)
    omitted = consensus.compare([
        {'engine': 'molscribe', 'ok': True, 'smiles': 'CC(O)C(=O)O'},
        {'engine': 'molnextr', 'ok': True, 'smiles': 'C[C@H](O)C(=O)O'},
    ])
    assert omitted['connectivity_match'] is True
    assert any('omitted stereochemistry' in n for n in omitted['notes'])

    # Inverted stereochemistry (both specify opposite stereocenters)
    inverted = consensus.compare([
        {'engine': 'molscribe', 'ok': True, 'smiles': 'C[C@H](O)C(=O)O'},
        {'engine': 'molnextr', 'ok': True, 'smiles': 'C[C@@H](O)C(=O)O'},
    ])
    assert inverted['connectivity_match'] is True
    assert any('inverted stereochemistry' in n for n in inverted['notes'])

    # Canonical tautomers (different connectivity blocks in InChIKey, same canonical tautomer)
    taut = consensus.compare([
        {'engine': 'molscribe', 'ok': True, 'smiles': 'CC(=O)CC(=O)C'},
        {'engine': 'molnextr', 'ok': True, 'smiles': 'CC(=O)/C=C(/O)C'},
    ], expected_formula='C5H8O2')
    assert any('tautomer' in n for n in taut['notes'])
    assert all(g.get('matches_expected_formula') is True for g in taut['groups'])

