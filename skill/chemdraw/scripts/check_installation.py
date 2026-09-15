"""Read-only comparison of an installed Skill with its maintained source."""
from pathlib import Path
import argparse
import hashlib
import json

CACHES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def file_hashes(root):
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()
            and not CACHES.intersection(p.relative_to(root).parts)
            and p.suffix not in {'.pyc', '.pyo'}}


def compare_trees(source, installed):
    expected, actual = file_hashes(source), file_hashes(installed)
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    modified = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    return {'ok': not (missing or extra or modified), 'missing': missing,
            'modified': modified, 'extra': extra, 'source_files': len(expected),
            'installed_files': len(actual), 'algorithm': 'sha256'}


def check_examples(root):
    root = Path(root)
    errors = []
    example = root/'assets/paper-replica/example'
    for name in ('figure.json', 'replay.py'):
        if not (example/name).is_file():
            errors.append(f'paper-replica/example: missing {name}')
    replay = example/'replay.py'
    if replay.is_file() and "'figure.cdxml'" not in replay.read_text(encoding='utf-8'):
        errors.append('paper-replica/example: replay does not declare figure.cdxml output')
    manifest = example/'figure.json'
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        def inspect(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {'file', 'template_path'} and isinstance(child, str):
                        if not (example/child).is_file():
                            errors.append(f'paper-replica/example: missing {child}')
                    else:
                        inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
        inspect(data)
    cases = root/'assets/paper-reconstructions/cases.json'
    if not cases.is_file():
        errors.append('paper-reconstructions: missing cases.json')
    else:
        for case in json.loads(cases.read_text(encoding='utf-8')).values():
            for relative in case['files'].values():
                if not (cases.parent/relative).is_file():
                    errors.append(f'paper-reconstructions: missing {relative}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--installed', required=True, type=Path)
    args = parser.parse_args()
    result = compare_trees(args.source, args.installed)
    result['example_errors'] = check_examples(args.installed)
    result['ok'] = result['ok'] and not result['example_errors']
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
