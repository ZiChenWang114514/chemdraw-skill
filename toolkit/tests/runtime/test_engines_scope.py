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
        env.recommend('conditions')


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
