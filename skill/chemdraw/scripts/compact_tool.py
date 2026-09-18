"""Keep existing worker evidence on disk and return a small review summary."""
import argparse
import hashlib
import json
from pathlib import Path

TOOLS = {'extract_structures_via_decimer_api', 'modify_molecule',
         'compose_chemical_figure', 'render_cdxml_files', 'get_toolkit_capabilities'}


def _worker(tool, arguments):
    from cdxml_toolkit.mcp_runtime.mcp_server import _run_worker
    return _run_worker(tool, [], arguments)


def run_compact(tool, arguments_path, output_path):
    from cdxml_toolkit.mcp_runtime import artifact_safety as safety
    if tool not in TOOLS:
        raise ValueError('Unsupported tool; use an existing reconstruction tool')
    target = Path(output_path).resolve()
    if target.exists():
        raise ValueError('Output exists; choose a new evidence file')
    arguments = json.loads(Path(arguments_path).read_text(encoding='utf-8-sig'))
    if not isinstance(arguments, dict):
        raise ValueError('Arguments must be a JSON object')
    result = _worker(tool, arguments)
    encoded = json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
    with safety.staging_file(target) as stage:
        stage.write_bytes(encoded)
        safety.publish_file(stage, target)
    layers = []
    current = result
    for _ in range(8):
        if isinstance(current, str):
            try:
                current = json.loads(current)
            except ValueError:
                break
        if not isinstance(current, dict):
            break
        layers.append(current)
        current = current.get('result')
    failed = any(item.get('ok') is False or item.get('error') for item in layers)
    warnings = sum(len(item['warnings']) if isinstance(item.get('warnings'), list)
                   else int(bool(item.get('warnings'))) for item in layers)
    ok = bool(layers) and layers[0].get('ok') is True and not failed
    return {'ok': ok, 'tool': tool, 'status': 'produced' if ok else 'needs_review',
            'review_required': True, 'warning_count': warnings,
            'chemical_acceptance': 'not_evaluated',
            'details': {'path': str(target), 'sha256': hashlib.sha256(encoded).hexdigest()},
            'next_step': 'Read evidence errors and warnings before retrying' if failed else
                         'Inspect relevant evidence and the artifact; record acceptance separately'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool', choices=sorted(TOOLS))
    parser.add_argument('--arguments', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(run_compact(args.tool, args.arguments, args.output)))


if __name__ == '__main__':
    main()
