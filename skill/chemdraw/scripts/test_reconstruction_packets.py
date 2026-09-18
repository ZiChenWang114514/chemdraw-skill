import json
from pathlib import Path

import pytest
from PIL import Image

from image_review_workspace import prepare
from reconstruction_packets import build_packets


def crops(tmp_path):
    image=tmp_path/'source.png';Image.new('RGB',(1200,100),'white').save(image)
    regions=tmp_path/'regions.json'
    regions.write_text(json.dumps([{'id':f's{i}','box':[i*100,0,(i+1)*100,100]} for i in range(12)]))
    prepare(image,regions,tmp_path/'crops')
    return tmp_path/'crops/manifest.json'


def test_default_serial_and_twelve_isolated_packets(tmp_path):
    manifest=crops(tmp_path)
    out=tmp_path/'packets';summary=build_packets(manifest,out)
    assert summary['effective_agents']==1 and summary['mode']=='serial'
    plan=json.loads((out/'dispatch.json').read_text())
    assert len(plan['tasks'])==12
    assert len({t['output_dir'] for t in plan['tasks']})==12
    assert all(Path(t['packet_path']).is_file() for t in plan['tasks'])
    assert all(not t['status']=='accepted' for t in plan['tasks'])


def test_explicit_parallel_grouping_capacity_and_fallback(tmp_path):
    manifest=crops(tmp_path)
    config=tmp_path/'config.json'
    config.write_text(json.dumps({'parallel':True,'max_subagents':4,'structures_per_task':2,
        'host_capacity':3,'supports_subagents':True}))
    summary=build_packets(manifest,tmp_path/'packets',config)
    assert summary['effective_agents']==3 and summary['batch_count']==6
    data=json.loads(config.read_text());data['supports_subagents']=False;config.write_text(json.dumps(data))
    assert build_packets(manifest,tmp_path/'fallback',config)['mode']=='serial'


def test_changed_crop_and_invalid_options_are_rejected(tmp_path):
    manifest=crops(tmp_path)
    Image.new('RGB',(100,100),'black').save(tmp_path/'crops/s0.png')
    with pytest.raises(ValueError,match='hash'):
        build_packets(manifest,tmp_path/'packets')
    assert not (tmp_path/'packets').exists()


def test_existing_output_preserved(tmp_path):
    manifest=crops(tmp_path);out=tmp_path/'packets';build_packets(manifest,out)
    before=(out/'dispatch.json').read_bytes()
    with pytest.raises(ValueError):build_packets(manifest,out)
    assert before==(out/'dispatch.json').read_bytes()


@pytest.mark.parametrize('config', [
    {'parallel': 'true'}, {'max_native_workers': 2}, {'structures_per_task': 0},
    {'unexpected': 1}, {'context': []}, {'max_subagents': True}])
def test_invalid_config_preserves_destination(tmp_path, config):
    manifest = crops(tmp_path)
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        build_packets(manifest, tmp_path / 'packets', path)
    assert not (tmp_path / 'packets').exists()


def test_enabled_host_without_capacity_blocks(tmp_path):
    manifest = crops(tmp_path)
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'parallel': True, 'supports_subagents': True, 'host_capacity': 0}))
    result = build_packets(manifest, tmp_path / 'packets', config)
    assert result['mode'] == 'blocked' and result['effective_agents'] == 0


def test_invalid_transform_rejected(tmp_path):
    manifest = crops(tmp_path)
    record = json.loads(manifest.read_text())
    record['regions'][0]['crop_to_source']['scale'] = -1
    manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='transform'):
        build_packets(manifest, tmp_path / 'packets')
