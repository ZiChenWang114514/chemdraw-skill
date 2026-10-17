"""Installation integrity for the ChemDraw skill.

The skill folder is its own maintained source: `--write-manifest` records a
SHA-256 for every file in manifest.json, and the default mode verifies the
folder against it. Text files are hashed after CRLF -> LF normalization, so a
git checkout with autocrlf does not produce false "modified" reports.
"""
from pathlib import Path
import argparse
import hashlib
import json

CACHES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
TEXT = {'.md', '.py', '.json', '.ps1', '.cdxml', '.csv', '.yaml', '.yml', '.txt', '.svg', '.toml'}
MANIFEST = 'manifest.json'


def file_digest(path):
    data = Path(path).read_bytes()
    if Path(path).suffix.lower() in TEXT:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def file_hashes(root):
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    return {p.relative_to(root).as_posix(): file_digest(p)
            for p in root.rglob('*') if p.is_file()
            and not CACHES.intersection(p.relative_to(root).parts)
            and p.suffix not in {'.pyc', '.pyo'} and p.relative_to(root).as_posix() != MANIFEST}


def _diff(expected, actual):
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    modified = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    return {'ok': not (missing or extra or modified), 'missing': missing, 'modified': modified,
            'extra': extra, 'source_files': len(expected), 'installed_files': len(actual),
            'algorithm': 'sha256, text files LF-normalized'}


def compare_trees(source, installed):
    return _diff(file_hashes(source), file_hashes(installed))


def write_manifest(root):
    root = Path(root)
    text = json.dumps(file_hashes(root), indent=1, sort_keys=True) + '\n'
    (root / MANIFEST).write_text(text, encoding='utf-8')
    return root / MANIFEST


def check_manifest(root):
    root = Path(root)
    path = root / MANIFEST
    if not path.is_file():
        return {'ok': False, 'missing': [MANIFEST], 'modified': [], 'extra': []}
    return _diff(json.loads(path.read_text(encoding='utf-8')), file_hashes(root))


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
    parser.add_argument('--installed', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source', type=Path, help='optional second tree to compare instead of manifest.json')
    parser.add_argument('--write-manifest', action='store_true')
    args = parser.parse_args()
    if args.write_manifest:
        print(write_manifest(args.installed))
        return 0
    result = compare_trees(args.source, args.installed) if args.source else check_manifest(args.installed)
    result['example_errors'] = check_examples(args.installed)
    result['ok'] = result['ok'] and not result['example_errors']
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
