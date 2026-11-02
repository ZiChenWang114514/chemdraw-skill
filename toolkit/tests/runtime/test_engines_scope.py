"""On-demand installation: what to recommend, what a missing engine reports, and safe removal."""
import json
import os

import pytest

from cdxml_toolkit.engines import env, envelope, ocsr
from cdxml_toolkit.engines.registry import BUNDLES, ENGINES, GUIDE, RECOMMEND, disk_mb


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    return tmp_path


def fake_install(home, name, megabytes=1):
    folder = home / name
    folder.mkdir()
    (folder / env.RECEIPT).write_text('{}')
    (folder / 'weights.bin').write_bytes(b'x' * megabytes * 1000)
    return folder


# --- the data ------------------------------------------------------------------------------------

def test_every_local_engine_says_when_to_install_it_and_what_it_costs():
    for name, spec in ENGINES.items():
        if spec['kind'] in ('local', 'jar'):
            guide = GUIDE[name]
            assert guide['use_when'] and guide['skip_when'] and guide['disk_mb'] > 0, name


def test_bundles_name_real_engines_and_every_need_has_a_bundle():
    for name, bundle in BUNDLES.items():
        assert bundle['engines'] and all(e in ENGINES for e in bundle['engines']), name
        assert all(ENGINES[e]['kind'] in ('local', 'jar') for e in bundle['engines']), name
    assert all(b in BUNDLES for options in RECOMMEND.values() for b in options)
    assert disk_mb(BUNDLES['ocsr-lite']['engines']) < disk_mb(BUNDLES['ocsr-standard']['engines']) < \
        disk_mb(BUNDLES['ocsr-full']['engines'])


# --- recommending --------------------------------------------------------------------------------

def test_recommend_lists_the_smallest_useful_set_first_and_downloads_nothing(home):
    out = env.recommend('ocsr')
    assert out['suggested'] == 'ocsr-standard' and not out['already_installed']
    first = out['options'][0]
    assert first['missing'] == ['molscribe', 'molvec'] and first['download_mb'] == 2002
    assert first['command'] == 'cdx.py install-engines --bundle ocsr-standard'
    assert list(home.iterdir()) == []  # reading only


def test_recommend_marks_what_is_already_there(home, monkeypatch):
    monkeypatch.setattr(env, 'available', lambda: {n: n in ('molscribe', 'molvec') or ENGINES[n]['kind'] == 'remote'
                                                   for n in ENGINES})
    out = env.recommend('ocsr')
    assert out['already_installed'] and out['options'][0]['command'] is None
    assert out['options'][2]['missing'] == ['molnextr', 'molparser']


def test_recommend_rejects_an_unknown_need():
    with pytest.raises(ValueError, match='unknown need'):
        env.recommend('weather')


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
    monkeypatch.setattr(env, '_pip', lambda *a, **k: None)


def test_an_install_stopped_during_its_download_does_not_count_as_installed(home, monkeypatch):
    _ready_to_install(home, monkeypatch)
    started = []

    def run(command, **kwargs):
        started.append(command[0])
        raise KeyboardInterrupt  # the terminal closed, the machine slept: no handler gets to clean up

    monkeypatch.setattr(env.subprocess, 'run', run)
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

    monkeypatch.setattr(env.subprocess, 'run', run)
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
