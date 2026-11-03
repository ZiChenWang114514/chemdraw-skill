"""Run one engine action: JSON request on stdin, JSON result on stdout.

Request ``{"engine", "action": "fetch" | "predict", "params", "data_dir", "spec"}``; result
``{"ok": true, "result": ...}`` or ``{"ok": false, "error": ...}``. Started by ``env.call`` with the
interpreter of the engine's own environment, so it imports nothing from this package and uses the
standard library plus the engine only. Engines run on the CPU, except that an engine whose environment
was given a CUDA build of torch (an NVIDIA GPU was found at install time) runs on the GPU; Macs always use
the CPU, because the engines' own device probing fails on some Apple Silicon setups.
"""

import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.error


def _scratch(prefix):
    """A private folder for this run (it holds the user's molecule), removed when the worker exits."""
    import atexit
    import shutil
    import tempfile
    work = tempfile.mkdtemp(prefix=prefix)

    def remove():
        os.chdir(os.path.dirname(work))  # Windows cannot delete the current folder
        shutil.rmtree(work, ignore_errors=True)

    atexit.register(remove)
    return work


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


_CONFIG_FILE = re.compile(r'(?:^\s*-\s+|:\s+)(\S.*\.(?:onnx|gz|hdf5|csv|zip))\s*$')


def _config_files(config):
    """Base names of the data files a ``config.yml`` points at (the paths in it are absolute)."""
    with open(config, encoding='utf-8') as handle:
        return sorted({re.split(r'[\\/]', m.group(1))[-1] for line in handle if (m := _CONFIG_FILE.search(line))})


def _fetch_aizynthfinder(data_dir, spec, attempts=3):
    """Run AiZynthFinder's downloader until every file its config names exists, then check them against the pins."""
    config, missing, message = os.path.join(data_dir, 'config.yml'), None, ''
    for attempt in range(attempts):
        done = subprocess.run([sys.executable, '-m', 'aizynthfinder.tools.download_public_data', data_dir],
                              capture_output=True, text=True)
        message = (done.stderr or done.stdout or '')[-300:]
        if os.path.isfile(config):
            missing = [name for name in _config_files(config) if not os.path.isfile(os.path.join(data_dir, name))]
            if done.returncode == 0 and not missing:
                break
        time.sleep(min(5 * (attempt + 1), 30))
    else:
        raise RuntimeError(f'download_public_data did not finish after {attempts} attempts'
                           + (f'; missing {", ".join(missing)}' if missing else '') + (f': {message}' if message else ''))
    pins, receipt = spec.get('sha256') or {}, {}
    for name in _config_files(config):
        digest = _sha256(os.path.join(data_dir, name))
        if pins.get(name) != digest:
            raise RuntimeError(f'{name} does not match the pinned sha256 (got {digest})')
        receipt[name] = digest
    return {'data': receipt}


def fetch(engine, params, data_dir, spec):
    """Download weights or data into ``data_dir`` and return a receipt (hashes, revisions)."""
    os.makedirs(data_dir, exist_ok=True)
    if spec.get('data') == 'aizynthfinder-public-data':
        return _fetch_aizynthfinder(data_dir, spec)
    if spec.get('data') == 'decimer-segmentation-model':
        return _fetch_file(data_dir, spec['download'])
    if spec.get('data') == 'synplanner-preset':
        return _fetch_synplanner(data_dir, spec)
    if spec.get('data') in ('retrochimera-pistachio', 'nmrnet-pp', 'reacon'):
        return _fetch_bundle(data_dir, spec)
    weights = spec['weights']
    from huggingface_hub import hf_hub_download, snapshot_download
    if weights.get('snapshot'):
        path = snapshot_download(weights['repo'], repo_type=weights['type'], local_dir=data_dir,
                                 revision=weights.get('revision'),
                                 allow_patterns=[weights['include']] if weights.get('include') else None)
        return {'weights': {'repo': weights['repo'], 'revision': weights.get('revision'), 'path': path}}
    receipt = {}
    for name in weights['files']:
        path = hf_hub_download(weights['repo'], name, repo_type=weights['type'], local_dir=data_dir,
                               revision=weights.get('revision'))
        digest = _sha256(path)
        expected = weights['sha256'][name]
        if digest != expected:
            os.remove(path)
            raise RuntimeError(f'{name} does not match the pinned sha256 (got {digest}); nothing was kept')
        receipt[name] = digest
    return {'weights': receipt}


class _Progress:
    """A line on stderr for every 5 % of a long step, or every 30 s; the installer shows stderr while it fetches."""

    def __init__(self, label, total, unit='MB', scale=1e6):
        self.label, self.total, self.unit, self.scale = label, total, unit, scale
        self.shown, self.when = None, 0.0

    def update(self, done):
        share = min(1.0, done / self.total) if self.total else 0.0
        now = time.monotonic()
        if self.shown is not None and share < 1 and share - self.shown < 0.05 and now - self.when < 30:
            return
        if self.shown == 1.0:
            return
        self.shown, self.when = share, now
        sys.stderr.write(f'{self.label}: {done / self.scale:,.0f} of {self.total / self.scale:,.0f} {self.unit} '
                         f'({share:.0%})\n')
        sys.stderr.flush()


FORBIDDEN_RETRIES = 8  # figshare redirects each request to a freshly signed URL whose host sometimes answers 403


def _permanent(exc):
    """A 4xx answer stays the same however often it is asked; 408, 425 and 429 mean try again later."""
    return 400 <= exc.code < 500 and exc.code not in (408, 425, 429)


def _give_up(exc, attempt, attempts):
    """Whether a failed request ends the download: the last attempt, or a 4xx that will not change.

    A 403 is asked again a few times before it counts as permanent.
    """
    if attempt >= attempts - 1:
        return True
    if not isinstance(exc, urllib.error.HTTPError) or not _permanent(exc):
        return False
    return exc.code != 403 or attempt >= FORBIDDEN_RETRIES


def _range_bytes(url, first, last, attempts=20):
    """Bytes ``first``..``last`` of ``url`` in one Range request, repeated after a transient failure."""
    import urllib.request
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={'Range': f'bytes={first}-{last}'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.headers, response.read()
        except (OSError, http.client.HTTPException) as exc:
            if _give_up(exc, attempt, attempts):
                raise
            time.sleep(min(3 * (attempt + 1), 30))


def _download(url, partial, attempts=80, headers=None):
    """Download ``url`` into ``partial``, resuming with a Range request after a dropped connection.

    A transfer that ends before the announced length is retried (resumed when the host supports Range, otherwise
    started again), so a connection closed early is never taken for a finished file.
    """
    import urllib.request
    label = os.path.basename(partial).removesuffix('.part')
    for attempt in range(attempts):  # model hosts sometimes drop a connection mid-transfer
        have = os.path.getsize(partial) if os.path.exists(partial) else 0
        request = urllib.request.Request(url, headers=dict(headers or {}, **({'Range': f'bytes={have}-'} if have else {})))
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                resumed = bool(have) and getattr(response, 'status', 200) == 206
                length = response.headers.get('Content-Length')
                expected = (have if resumed else 0) + int(length) if length and length.isdigit() else None
                progress = _Progress(label, expected) if expected else None
                written = have if resumed else 0
                with open(partial, 'ab' if resumed else 'wb') as out:
                    while True:
                        block = response.read(1 << 20)
                        if not block:
                            break
                        out.write(block)
                        written += len(block)
                        if progress:
                            progress.update(written)
            if expected is None or os.path.getsize(partial) >= expected:
                return
        except urllib.error.HTTPError as exc:
            if exc.code == 416:  # nothing left to ask for: the file is complete
                return
            if _give_up(exc, attempt, attempts):
                raise
        except (OSError, http.client.HTTPException):
            if attempt == attempts - 1:
                raise
        time.sleep(min(3 * (attempt + 1), 30))
    raise RuntimeError(f'{url} could not be downloaded completely')


def _extract(archive, kind, destination):
    """Unpack a .tar.gz (dropping the single top folder GitHub adds) or a .zip, refusing paths that escape."""
    import tarfile
    import zipfile
    root = os.path.realpath(destination)
    os.makedirs(root, exist_ok=True)

    def safe(name):
        target = os.path.realpath(os.path.join(root, name))
        if target != root and not target.startswith(root + os.sep):
            raise RuntimeError(f'archive member {name!r} points outside the target folder')
        return target
    if kind == 'tar.gz':
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                parts = member.name.split('/', 1)
                if len(parts) < 2 or not parts[1] or not (member.isfile() or member.isdir()):
                    continue  # the top folder itself, links, devices
                target = safe(parts[1])
                if member.isdir():
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with tar.extractfile(member) as source, open(target, 'wb') as out:
                        out.write(source.read())
    elif kind == 'zip':
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                safe(name)
            bundle.extractall(root)
    else:
        raise RuntimeError(f'unknown archive type {kind!r}')


def _fetch_file(data_dir, download):
    """One file by URL, resumable, checked against its pinned hash (pystow looks for it under PYSTOW_HOME).

    ``extract`` ('tar.gz' or 'zip') unpacks it into ``into`` (default: ``data_dir``) and removes the archive.
    """
    target = os.path.join(data_dir, download['path'])
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.isfile(target) and _sha256(target) == download['sha256']:  # an earlier install got this far
        return {'data': {download['path']: download['sha256']}}
    partial = target + '.part'
    _download(download['url'], partial)
    digest = _sha256(partial)
    if digest != download['sha256']:
        os.remove(partial)
        raise RuntimeError(f'{download["path"]} does not match the pinned sha256 (got {digest}); nothing was kept')
    os.replace(partial, target)
    if download.get('extract'):
        _extract(target, download['extract'], os.path.join(data_dir, download.get('into', '')))
        os.remove(target)
    return {'data': {download['path']: digest}}


class _RangeFile:
    """A read-only seekable view of a remote file, fetched with Range requests (enough for zipfile)."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        headers, _ = _range_bytes(url, 0, 0)
        self.size = int(headers['Content-Range'].rsplit('/', 1)[1])

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, count=-1):
        end = self.size if count is None or count < 0 else min(self.size, self.pos + count)
        if self.pos >= end:
            return b''
        _, data = _range_bytes(self.url, self.pos, end - 1)
        self.pos += len(data)
        return data


def _fetch_zip_members(data_dir, source):
    """Take only the named members out of a large remote zip (Range requests), checking each result's hash.

    ``source``: ``{'url', 'members': [{'match': name suffix or contains-all list, 'path': where, 'sha256'}]}``.
    """
    import struct
    import zipfile
    import zlib
    remote = _RangeFile(source['url'])
    with zipfile.ZipFile(remote) as bundle:
        infos = bundle.infolist()
    receipt = {}
    for want in source['members']:
        found = [i for i in infos if all(part in i.filename for part in want['match'])]
        if len(found) != 1:
            raise RuntimeError(f'expected one member matching {want["match"]}, found {len(found)}')
        info = found[0]
        target = os.path.join(data_dir, want['path'])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.exists(target) and _sha256(target) == want['sha256']:
            receipt[want['path']] = want['sha256']
            continue
        head = remote_range(source['url'], info.header_offset, info.header_offset + 29 + 4096)
        name_len, extra_len = struct.unpack('<HH', head[26:30])
        start = info.header_offset + 30 + name_len + extra_len
        partial = target + '.part'
        _download_range(source['url'], start, start + info.compress_size - 1, partial)
        inflater = zlib.decompressobj(-15) if info.compress_type == 8 else None
        crc, written = 0, 0
        with open(partial, 'rb') as raw, open(target + '.tmp', 'wb') as out:
            for block in iter(lambda: raw.read(1 << 22), b''):
                block = inflater.decompress(block) if inflater else block
                crc, written = zlib.crc32(block, crc), written + len(block)
                out.write(block)
            if inflater:
                block = inflater.flush()
                crc, written = zlib.crc32(block, crc), written + len(block)
                out.write(block)
        os.remove(partial)
        if crc != info.CRC or written != info.file_size:
            os.remove(target + '.tmp')
            raise RuntimeError(f'{want["path"]} is damaged (CRC mismatch); nothing was kept')
        digest = _sha256(target + '.tmp')
        if digest != want['sha256']:
            os.remove(target + '.tmp')
            raise RuntimeError(f'{want["path"]} does not match the pinned sha256 (got {digest}); nothing was kept')
        os.replace(target + '.tmp', target)
        receipt[want['path']] = digest
    return receipt


def remote_range(url, first, last):
    return _range_bytes(url, first, last)[1]


def _download_range(url, first, last, partial, attempts=200):
    """Fetch bytes ``first``..``last`` of ``url`` into ``partial``, resuming after a dropped connection."""
    import urllib.request
    total = last - first + 1
    progress = _Progress(os.path.basename(partial).removesuffix('.part'), total)
    for attempt in range(attempts):
        have = os.path.getsize(partial) if os.path.exists(partial) else 0
        if have >= total:
            return
        request = urllib.request.Request(url, headers={'Range': f'bytes={first + have}-{last}'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, open(partial, 'ab') as out:
                for block in iter(lambda: response.read(1 << 20), b''):
                    out.write(block)
                    have += len(block)
                    progress.update(have)
        except (OSError, http.client.HTTPException) as exc:
            if _give_up(exc, attempt, attempts):
                raise
            time.sleep(min(3 * (attempt + 1), 30))


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


def _canonical_chunk(chunk):
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog('rdApp.*')
    out = set()
    for smiles in chunk:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            out.add(Chem.MolToSmiles(mol))
    return out


def _blocks_to_smiles(json_gz, smiles_path):
    """Write the building blocks as RDKit-canonical, de-duplicated SMILES (Syntheseus matches exact strings)."""
    import gzip
    import multiprocessing
    with gzip.open(json_gz, 'rt', encoding='utf-8') as handle:
        blocks = json.load(handle)
    raw = [item['smiles'] for value in blocks.values() for item in (value if isinstance(value, list) else [value])]
    del blocks
    chunks = [raw[i:i + 20000] for i in range(0, len(raw), 20000)]
    seen = set()
    progress = _Progress('building blocks', len(chunks), unit='chunks', scale=1)
    with multiprocessing.Pool(max(1, min(8, (os.cpu_count() or 2) - 1))) as pool:
        for done, part in enumerate(pool.imap_unordered(_canonical_chunk, chunks), 1):
            seen |= part
            progress.update(done)
    with open(smiles_path + '.tmp', 'w', encoding='utf-8') as out:
        out.writelines(smiles + '\n' for smiles in sorted(seen))
    os.replace(smiles_path + '.tmp', smiles_path)


def _ensure_smiles(json_gz, smiles_path):
    """Build the SMILES list unless one built from the same source with the same RDKit is already there."""
    import rdkit
    stamp = {'sha256': _sha256(json_gz), 'rdkit': rdkit.__version__}
    sidecar = smiles_path + '.source.json'
    try:
        with open(sidecar, encoding='utf-8') as handle:
            if json.load(handle) == stamp and os.path.isfile(smiles_path):
                return
    except (OSError, ValueError):
        pass
    _blocks_to_smiles(json_gz, smiles_path)
    with open(sidecar, 'w', encoding='utf-8') as handle:
        json.dump(stamp, handle)


def _fetch_archive_members(data_dir, source):
    """Members of a zip that a host builds on the fly (no Range support): download it, keep only the named members.

    The zip itself is not stable, so only the members are pinned (by sha256). The archive is deleted afterwards.
    """
    import zipfile
    partial = os.path.join(data_dir, '_archive.zip.part')
    receipt = {}
    pending = [m for m in source['members']
               if not (os.path.exists(os.path.join(data_dir, m['path'])) and _sha256(os.path.join(data_dir, m['path'])) == m['sha256'])]
    if pending:
        _download(source['url'], partial)
        with zipfile.ZipFile(partial) as bundle:
            for want in pending:
                target = os.path.join(data_dir, want['path'])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                digest = hashlib.sha256()
                with bundle.open(want['name']) as src, open(target + '.tmp', 'wb') as out:
                    for block in iter(lambda: src.read(1 << 20), b''):
                        digest.update(block)
                        out.write(block)
                if digest.hexdigest() != want['sha256']:
                    os.remove(target + '.tmp')
                    raise RuntimeError(f'{want["path"]} does not match the pinned sha256 (got {digest.hexdigest()}); nothing was kept')
                os.replace(target + '.tmp', target)
        os.remove(partial)
    for want in source['members']:
        receipt[want['path']] = want['sha256']
    return receipt


def _fetch_bundle(data_dir, spec):
    """Pinned archives, members of a large remote zip, and a building-block list, as the engine's spec names them."""
    receipt = {}
    for download in spec.get('downloads') or []:
        receipt.update(_fetch_file(data_dir, download)['data'])
    sources = spec.get('zip_members') or []
    for source in ([sources] if isinstance(sources, dict) else sources):
        receipt.update(_fetch_zip_members(data_dir, source))
    if spec.get('archive_members'):
        receipt.update(_fetch_archive_members(data_dir, spec['archive_members']))
    if spec.get('stock'):
        stock = _fetch_file(data_dir, spec['stock'])
        receipt.update(stock['data'])
        _ensure_smiles(os.path.join(data_dir, spec['stock']['path']),
                       os.path.join(data_dir, 'building_blocks', 'building_blocks.smi'))
    return {'data': receipt}


# --- OCSR -----------------------------------------------------------------------------------------

def _device():
    """'cuda' when this environment's torch can use an NVIDIA GPU, else 'cpu'; CHEMDRAW_ENGINE_DEVICE=cpu forces
    the CPU. Engines whose torch was installed without CUDA, and every Mac, stay on the CPU."""
    if os.environ.get('CHEMDRAW_ENGINE_DEVICE', '').lower() == 'cpu' or sys.platform == 'darwin':
        return 'cpu'
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except Exception:  # an engine without torch, or a broken CUDA install
        return 'cpu'


class _OneThreadPool:
    """Stands in for ``multiprocessing.Pool`` in an engine's post-processing: a pool of one thread."""

    def __new__(cls, *args, **kwargs):
        from multiprocessing.pool import ThreadPool
        return ThreadPool(1)


def _serial_pools(*modules):
    """Engines that open ``multiprocessing.Pool(16)`` for every image start 16 fresh Pythons on Windows, each
    importing torch again (several GB per image); the work they do is light, so one thread does it."""
    import types
    for module in modules:
        module.multiprocessing = types.SimpleNamespace(**{**vars(module.multiprocessing), 'Pool': _OneThreadPool})


def _molscribe(params, data_dir, spec):
    import torch
    from molscribe import MolScribe, chemistry
    _serial_pools(chemistry)
    model = MolScribe(os.path.join(data_dir, 'swin_base_char_aux_1m.pth'), device=torch.device(_device()))
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
    from MolNexTR import chemical
    from MolNexTR.model import molnextr
    _serial_pools(chemical)
    model = molnextr(os.path.join(data_dir, 'molnextr_best.pth'), torch.device(_device()))
    out = []
    for path in params['images']:
        try:
            result = model.predict_final_results(path, return_atoms_bonds=False)
            out.append({'smiles': result['predicted_smiles']})
        except Exception as exc:
            out.append({'error': f'{type(exc).__name__}: {exc}'})
    return out


def _molparser(params, data_dir, spec):
    from molparser import MolParser
    model = MolParser(molparser_model_path=data_dir, device=_device())
    out = []
    for path in params['images']:
        try:
            results = model.parse(path, rec_only=True)
            out.append({'smiles': results[0].smi or None} if results else {'error': 'no result'})
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
    """Find structures with the mask network, then cut each one from the page with a margin.

    The network's own crops are masked and can clip labels and bond ends, so only its boxes are used.
    """
    import cv2
    from decimer_segmentation import segment_chemical_structures
    os.makedirs(params['out_dir'], exist_ok=True)
    out = []
    for page_index, path in enumerate(params['images']):
        image = cv2.imread(path)
        if image is None:
            out.append({'source': path, 'segments': [], 'bboxes': []})
            continue
        _, boxes = segment_chemical_structures(image, expand=True, visualization=False, return_bboxes=True)
        height, width = image.shape[:2]
        files, found = [], []
        for number, (y0, x0, y1, x1) in enumerate(boxes, 1):
            if y1 <= y0 or x1 <= x0:
                continue
            margin = max(16, int(0.08 * max(y1 - y0, x1 - x0)))
            left, top = max(0, x0 - margin), max(0, y0 - margin)
            right, bottom = min(width, x1 + margin), min(height, y1 + margin)
            crop = cv2.copyMakeBorder(image[top:bottom, left:right], 12, 12, 12, 12, cv2.BORDER_CONSTANT,
                                      value=(255, 255, 255))
            target = os.path.join(params['out_dir'], f'{params["stem"]}-p{page_index + 1}-s{number}.png')
            cv2.imwrite(target, crop)
            files.append(target)
            found.append([int(left), int(top), int(right), int(bottom)])
        out.append({'source': path, 'segments': files, 'bboxes': found})
    return out


# --- reactions, retrosynthesis -----------------------------------------------------------------------

def _reactiont5(params, data_dir, spec):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(data_dir)
    device = _device()
    model = AutoModelForSeq2SeqLM.from_pretrained(data_dir).eval().to(device)
    count = max(1, int(params.get('count', 5)))
    out = []
    for text in params['inputs']:
        inputs = tokenizer(text, return_tensors='pt').to(device)
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


def _disconnections(ranked, count):
    """The first ``count`` different precursor sets from (template, prior) pairs, best template first.

    The policy ranks templates without applying them: many do not match the target at all and some give
    several outcomes, so what counts is the outcomes, not the templates.
    """
    options, seen = [], set()
    for action, prior in ranked:
        for group in action.reactants:
            reactants = [m.smiles for m in group]
            key = tuple(sorted(reactants))
            if not reactants or key in seen:
                continue
            seen.add(key)
            options.append({'reactants': [reactants], 'template': action.metadata.get('template'),
                            'probability': float(prior)})
            if len(options) == count:
                return options
    return options


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
        return {'steps': 'single', 'target': smiles,
                'options': _disconnections(zip(actions, priors), int(params.get('count', 10)))}
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
    work = _scratch('synplan-')
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


def _syntheseus_tree(graph, node, chosen):
    """A solved route (the AND/OR nodes a search kept) as the tree shape the other planners return."""
    item = {'smiles': node.mol.smiles, 'in_stock': bool(node.mol.metadata.get('is_purchasable'))}
    for step in graph.successors(node):
        if step in chosen:
            item['reaction'] = {'metadata': {'policy_probability': (step.reaction.metadata or {}).get('probability')},
                                'reactants': [_syntheseus_tree(graph, child, chosen) for child in graph.successors(step)]}
    return item


def _available_gb():
    """Memory the system can still hand out, in GB, or None when it cannot be read."""
    try:
        if os.name == 'nt':
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + \
                           [(name, ctypes.c_ulonglong) for name in ('total', 'avail', 'total_page', 'avail_page',
                                                                     'total_virtual', 'avail_virtual', 'extended')]
            status = Status(length=ctypes.sizeof(Status))
            return status.avail / 1e9 if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None
        with open('/proc/meminfo', encoding='ascii') as handle:
            return next(int(line.split()[1]) / 1e6 for line in handle if line.startswith('MemAvailable:'))
    except Exception:
        return None


# RetroChimera starts one rule process per CPU by default; under spawn (Windows, macOS) each one holds its own
# rulebase, so the count follows the free memory: the model takes RULE_MODEL_GB, each process RULE_PROCESS_GB.
RULE_MODEL_GB, RULE_PROCESS_GB = 12, 3  # measured: 12 GB peak with one process (Windows, CPU)


def _rule_processes():
    if os.environ.get('CHEMDRAW_ENGINE_PROCESSES', '').isdigit():
        return max(1, int(os.environ['CHEMDRAW_ENGINE_PROCESSES']))
    ceiling = min(os.cpu_count() or 1, 4)
    free = _available_gb()
    if free is None:
        return ceiling
    return max(1, min(ceiling, int((free - RULE_MODEL_GB) // RULE_PROCESS_GB)))


def _retrochimera(params, data_dir, spec):
    from syntheseus.interface.molecule import Molecule
    smiles = params['smiles']
    count = int(params.get('count', 5))
    single = params.get('steps') == 'single'
    inventory = None
    if not single:  # a target that can be bought needs no model at all
        from syntheseus.search.mol_inventory import SmilesListInventory
        with open(os.path.join(data_dir, 'building_blocks', 'building_blocks.smi'), encoding='utf-8') as handle:
            inventory = SmilesListInventory([line.strip() for line in handle if line.strip()], canonicalize=False)
        if inventory.is_purchasable(Molecule(smiles)):
            return {'steps': 'multi', 'target': smiles, 'solved': True, 'target_in_stock': True, 'top_score': None,
                    'routes': []}
    from retrochimera import RetroChimeraModel
    model = RetroChimeraModel(model_dir=data_dir, device='cpu', template_localization={'num_processes': _rule_processes()})
    if single:
        reactions = model([Molecule(smiles)], num_results=count)[0]
        return {'steps': 'single', 'target': smiles, 'options': [{
            'reactants': [[m.smiles for m in r.reactants]],
            'probability': (r.metadata or {}).get('probability'), 'score': (r.metadata or {}).get('score'),
            'individual_ranks': (r.metadata or {}).get('individual_ranks')} for r in reactions]}
    from syntheseus.search.algorithms.best_first.retro_star import RetroStarSearch
    from syntheseus.search.analysis.route_extraction import iter_routes_time_order
    from syntheseus.search.node_evaluation.common import ConstantNodeEvaluator, ReactionModelLogProbCost
    search = RetroStarSearch(
        reaction_model=model, mol_inventory=inventory, time_limit_s=float(params.get('time_limit', 60)),
        limit_iterations=int(params.get('iterations', 1000)), limit_reaction_model_calls=int(params.get('iterations', 1000)),
        prevent_repeat_mol_in_trees=True, stop_on_first_solution=False,
        value_function=ConstantNodeEvaluator(0.0), and_node_cost_fn=ReactionModelLogProbCost())
    graph, _ = search.run_from_mol(Molecule(smiles))
    routes = [_syntheseus_tree(graph, graph.root_node, set(nodes))
              for nodes in iter_routes_time_order(graph, max_routes=count)]
    return {'steps': 'multi', 'target': smiles, 'solved': bool(graph.root_node.has_solution), 'top_score': None,
            'routes': routes}


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


def _nmrnet_command(data_dir, data, results, element):
    """The authors' inference command. infer.py names its output after ``--path`` split on "/", so that path is
    written with forward slashes (Windows accepts them)."""
    folder = os.path.join(data_dir, element)
    checkpoint = os.path.join(folder, 'cv_seed_42_fold_0', 'checkpoint_last.pt').replace('\\', '/')
    return [sys.executable, 'uninmr/infer.py', '--user-dir', 'uninmr', data, '--valid-subset', 'valid',
            '--results-path', results, '--saved-dir', folder, '--num-workers', '0', '--ddp-backend=c10d',
            '--batch-size', '4', '--task', 'uninmr', '--loss', 'atom_regloss_mae', '--arch', 'unimol_large',
            '--dict-name', os.path.join(data_dir, 'weight', 'dict.txt'),
            '--path', checkpoint, '--cpu', '--log-interval', '50',
            '--log-format', 'simple', '--required-batch-size-multiple', '1', '--selected-atom', element,
            '--gaussian-kernel', '--atom-descriptor', '0', '--split-mode', 'infer']


def _nmrnet_pp(params, data_dir, spec):
    """1H and 13C shifts with NMRNet++ (fold 0 of the authors' five cross-validation models), run by their own infer.py."""
    import pickle
    import lmdb
    import numpy as np
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.AddHs(Chem.MolFromSmiles(params['smiles']))
    if AllChem.EmbedMolecule(mol, randomSeed=42) != 0:
        raise ValueError('no 3D conformer could be generated for this structure')
    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:
        pass  # the authors fall back to the embedded geometry too
    atoms = [a.GetSymbol() for a in mol.GetAtoms()]
    coordinates = mol.GetConformer().GetPositions().astype(np.float32)
    work = _scratch('nmrnetpp-')
    shifts = {}
    for nucleus in params.get('nuclei') or ['1H', '13C']:
        element = {'1H': 'H', '13C': 'C'}[nucleus]
        data = os.path.join(work, 'data-' + element)
        os.makedirs(data)
        record = {'smiles': params['smiles'], 'atoms': atoms, 'coordinates': coordinates,
                  'atoms_target_mask': np.array([1 if a == element else 0 for a in atoms], dtype=np.int32),
                  'atoms_target': np.zeros(len(atoms), dtype=np.float32), 'nmr_frequency': 400, 'nmr_solvent': 'CDCl3'}
        database = lmdb.open(os.path.join(data, 'valid.lmdb'), subdir=False, readonly=False, lock=False,
                             readahead=False, meminit=False, map_size=int(1e9))
        with database.begin(write=True) as transaction:
            transaction.put(b'0', pickle.dumps(record))
        database.close()
        results = os.path.join(work, 'results-' + element)
        command = _nmrnet_command(data_dir, data, results, element)
        done = subprocess.run(command, cwd=os.path.join(data_dir, 'code'), capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError('NMRNet++ inference failed: ' + (done.stderr or done.stdout)[-300:])
        with open(os.path.join(results, 'cv_seed_42_fold_0_valid.out.pkl'), 'rb') as handle:
            output = pickle.load(handle)[0]
        selected = output['select_atom'].view(-1).numpy()[1:len(atoms) + 1]  # drop the start token
        indices = [i for i, flag in enumerate(selected) if flag == 1]
        values = np.asarray(output['predict']).reshape(-1)
        if len(indices) != len(values):
            raise RuntimeError('NMRNet++ returned a different number of shifts than selected atoms')
        shifts.update({i: float(v) for i, v in zip(indices, values)})
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
    return {'atoms': [{'index': a.GetIdx(), 'element': a.GetSymbol(), 'shift': shifts.get(a.GetIdx()),
                       'class': ranks[a.GetIdx()], 'neighbors': [n.GetIdx() for n in a.GetNeighbors()]}
                      for a in mol.GetAtoms()],
            'geometry': 'RDKit ETKDG (seed 42) + MMFF94, one conformer, as in the authors\' data preparation',
            'warnings': ['NMRNet++ is a single cross-validation model (fold 0), not the published five-model average; '
                         'its models take no solvent, so the solvent argument does not change its answer']}


def _reacon(params, data_dir, spec):
    """Ranked catalyst / solvent / reagent sets for a mapped reaction, with the authors' own code and models."""
    import gzip
    import types
    code = os.path.join(data_dir, 'code')
    sys.path.insert(0, code)
    import ast
    tempfile_dir = _scratch('reacon-')
    os.chdir(tempfile_dir)
    import prediction
    import template_extractor
    from chemprop.args import PredictArgs
    from chemprop.train.make_predictions import make_predictions
    from GetMpnnData.get_data import remove_reagent
    from rdkit.Chem import rdChemReactions
    from rdkit.Chem.rdChemReactions import RemoveMappingNumbersFromReactions
    mapped = params['mapped_reaction']
    reactants, products = mapped.split('>>')
    record = {'_id': 0, 'reactants': reactants, 'products': products}
    r0 = template_extractor.extract_from_reaction(record, 0).get('reaction_smarts', '')
    r1 = template_extractor.extract_from_reaction(record, 1).get('reaction_smarts', '')
    r0_star = ''
    if r0:
        reaction = rdChemReactions.ReactionFromSmarts(r0)
        RemoveMappingNumbersFromReactions(reaction)
        r0_star = rdChemReactions.ReactionToSmiles(reaction)
    model_input = remove_reagent(mapped)
    dummy = os.path.join(tempfile_dir, 'input.csv')
    with open(dummy, 'w', encoding='utf-8') as handle:
        handle.write('reaction\n' + model_input + '\n')
    scores = []
    for target in ('cat', 'solv0', 'solv1', 'reag0', 'reag1', 'reag2'):
        arguments = PredictArgs().parse_args(['--test_path', dummy, '--checkpoint_dir', os.path.join(code, 'models', 'MPNN_' + target),
                                              '--preds_path', os.path.join(tempfile_dir, 'p.csv'), '--num_workers', '0'])
        scores.append(list(make_predictions(arguments, [[model_input]])[0][0]))
    prediction.condition_key = prediction.get_condition_labels(os.path.join(code, 'data', 'labels'))
    libraries = os.path.join(data_dir, 'condition_library')

    def load(name):
        with gzip.open(os.path.join(libraries, name), 'rt', encoding='utf-8') as handle:
            return json.load(handle)

    ranked, level = [], 'none'
    for level_name, template, library_file in (('r1', r1, 'condition_library_r1.json.gz'), ('r0', r0, 'condition_library_r0.json.gz'),
                                               ('r0*', r0_star, 'condition_library_r0_1.json.gz')):
        if not template:
            continue
        library = load(library_file)
        if template in library:
            ranked = prediction.condition_selector(types.SimpleNamespace(), template, scores, library)
            level = level_name
            break
    if not ranked:
        ranked = prediction.Nu_condition_selector(scores, [3, 3, 3, 3, 3])
        level = 'none'
    candidates = []
    for text, score in ranked[:int(params.get('count', 5))]:
        catalyst, solvent0, solvent1, reagent0, reagent1, reagent2 = ast.literal_eval(text)
        candidates.append({'catalyst': None if catalyst == 'None' else catalyst, 'solvents': [x for x in (solvent0, solvent1) if x != 'None'],
                           'reagents': [x for x in (reagent0, reagent1, reagent2) if x != 'None'], 'score': float(score)})
    return {'template_level': level, 'templates': {'r1': r1, 'r0': r0}, 'candidates': candidates}


def spec_elements(params):
    return ('H', 'C', 'N', 'O', 'F', 'Cl', 'S')


ENGINES = {'molscribe': _molscribe, 'molnextr': _molnextr, 'molparser': _molparser, 'decimer-local': _decimer_local,
           'decimer-segmentation': _segment, 'reactiont5-forward': _reactiont5, 'reactiont5-retro': _reactiont5,
           'aizynthfinder': _aizynthfinder, 'synplanner': _synplanner, 'magnet': _magnet,
           'retrochimera': _retrochimera, 'nmrnet-pp': _nmrnet_pp, 'reacon': _reacon}


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
