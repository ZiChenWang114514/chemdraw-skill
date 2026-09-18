"""Build immutable local task packets, without dispatching agents or accepting chemistry."""
import argparse
import json
import re
from pathlib import Path
from image_review_workspace import digest


def build_packets(manifest_path, output_dir, config_path=None):
    from cdxml_toolkit.mcp_runtime import artifact_safety as safety
    target = Path(output_dir).resolve()
    if target.exists():
        raise ValueError('Output exists; use a new packet directory')
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    config = json.loads(Path(config_path).read_text(encoding='utf-8-sig')) if config_path else {}
    defaults = dict(parallel=False, max_subagents=4, structures_per_task=1,
                    max_ocsr_requests=2, max_native_workers=1, max_structure_retries=1,
                    host_capacity=1, supports_subagents=False, context={})
    if not isinstance(config, dict) or set(config) - set(defaults):
        raise ValueError('Unknown configuration fields')
    defaults.update(config)
    config = defaults
    for key in ('parallel', 'supports_subagents'):
        if type(config[key]) is not bool:
            raise ValueError(key + ' must be boolean')
    for key in ('max_subagents', 'structures_per_task', 'max_ocsr_requests',
                'max_native_workers', 'max_structure_retries', 'host_capacity'):
        minimum = 0 if key in ('host_capacity', 'max_structure_retries') else 1
        if type(config[key]) is not int or config[key] < minimum:
            raise ValueError(key + ' has invalid integer value')
    if config['max_native_workers'] != 1:
        raise ValueError('Native workers must remain one in this Windows session')
    if not isinstance(config['context'], dict):
        raise ValueError('context must map region IDs to short shared definitions')
    if digest(manifest['source']) != manifest['source_sha256']:
        raise ValueError('Source hash changed; prepare crops again')
    regions = [r for r in manifest['regions'] if r.get('kind', 'structure') == 'structure']
    if not regions:
        raise ValueError('No structure regions')
    names = set()
    for r in regions:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', r['id']) or r['id'] in names:
            raise ValueError('Invalid or duplicate region ID')
        names.add(r['id'])
        if digest(r['path']) != r['sha256']:
            raise ValueError('Crop hash changed: ' + r['id'])
        x1, y1, x2, y2 = r['box']
        w, h = manifest['display_dimensions']
        scale = manifest['scale']
        if not 0 <= x1 < x2 <= w or not 0 <= y1 < y2 <= h or scale <= 0:
            raise ValueError('Invalid region bounds or scale')
        if r['crop_to_source'] != {'scale': 1 / scale, 'offset': [x1, y1]}:
            raise ValueError('Invalid coordinate transform')
    size = config['structures_per_task']
    batches = [list(r['id'] for r in regions[i:i + size]) for i in range(0, len(regions), size)]
    parallel = config['parallel'] and config['supports_subagents']
    count = min(config['max_subagents'], config['host_capacity'], len(batches)) if parallel else 1
    mode = ('parallel' if count else 'blocked') if parallel else 'serial'
    reason = 'Host does not support subagents; execute serially' if config['parallel'] and not parallel else None
    tasks = []
    with safety.staging_directory(target) as stage:
        payload = stage / 'packets'
        payload.mkdir()
        for r in regions:
            folder = payload / r['id']
            folder.mkdir()
            (folder / 'attempt-1').mkdir()
            task = dict(id=r['id'], status='pending',
                        packet_path=str(target / r['id'] / 'packet.json'),
                        output_dir=str(target / r['id'] / 'attempt-1'))
            packet = dict(task, source_sha256=manifest['source_sha256'], crop=r,
                          context=config['context'].get(r['id'], ''),
                          instructions=['Inspect this crop and resolve connectivity, charge and stereo.',
                                        'Write editable CDXML and evidence only in your output directory.',
                                        'Do not edit the dispatch record or another region.',
                                        'Return unresolved issues to the main agent; submission is not acceptance.'],
                          result_fields=['component_path', 'sha256', 'issues', 'native_evidence',
                                         'visual_review', 'status'])
            (folder / 'packet.json').write_text(json.dumps(packet, indent=2), encoding='utf-8')
            tasks.append(task)
        dispatch = dict(mode=mode, effective_agents=count, fallback_reason=reason,
                        config=config, tasks=tasks, batches=batches,
                        execution='proposal_only; caller enforces limits and records state',
                        chemical_acceptance='not_evaluated')
        (payload / 'dispatch.json').write_text(json.dumps(dispatch, indent=2), encoding='utf-8')
        safety.publish_directory(payload, target)
    return dict(mode=mode, effective_agents=count, batch_count=len(batches),
                fallback_reason=reason, dispatch_path=str(target / 'dispatch.json'),
                next_step='Main agent reviews packets and executes the proposed queue')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('output')
    parser.add_argument('--config')
    args = parser.parse_args()
    print(json.dumps(build_packets(args.manifest, args.output, args.config)))


if __name__ == '__main__':
    main()
