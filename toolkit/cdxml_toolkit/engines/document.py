"""Find the structures on a page or in a PDF, read each one, and build a sheet for visual review."""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import env, envelope, ocsr
from .registry import ENGINES

PAGE_LIMIT = 50
SEGMENT_LIMIT = 200


def _render_pages(source: Path, pages, out_dir: Path, dpi: int) -> list:
    """PNG files for the requested pages (1-based) of a PDF; an image file is its own single page."""
    if source.suffix.lower() != '.pdf':
        return [(1, str(source))]
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError as exc:
            raise ValueError('reading a PDF needs PyMuPDF (extra: analysis)') from exc
    out = []
    with pymupdf.open(str(source)) as document:
        wanted = sorted(set(pages)) if pages else range(1, min(document.page_count, PAGE_LIMIT) + 1)
        for number in wanted:
            if not 1 <= number <= document.page_count:
                raise ValueError(f'page {number} is outside 1..{document.page_count}')
            target = out_dir / 'pages' / f'page-{number:03d}.png'
            target.parent.mkdir(parents=True, exist_ok=True)
            document[number - 1].get_pixmap(dpi=dpi).save(str(target))
            out.append((number, str(target)))
    if len(out) > PAGE_LIMIT:
        raise ValueError(f'at most {PAGE_LIMIT} pages per call')
    return out


def _segment_opencv(pages, out_dir: Path) -> list:
    import cv2
    from ..image.structure_from_image import segment_structures
    segments = []
    for number, path in pages:
        image = cv2.imread(path)
        if image is None:
            continue
        for index, (crop, box) in enumerate(segment_structures(image), 1):
            target = out_dir / 'segments' / f'p{number:03d}-s{index:02d}.png'
            target.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(target), crop)
            segments.append({'page': number, 'path': str(target), 'bbox': list(map(int, box))})
    return segments


def _segment(pages, out_dir: Path, segmenter: str, warnings: list) -> tuple:
    use_deep = segmenter in ('auto', 'decimer-segmentation') and env.available()['decimer-segmentation']
    if segmenter == 'decimer-segmentation' and not use_deep:
        raise ValueError('decimer-segmentation is not installed: run `cdx.py install-engines decimer-segmentation`')
    if use_deep:
        answers = env.call('decimer-segmentation', 'predict', {
            'images': [p for _, p in pages], 'out_dir': str(out_dir / 'segments'), 'stem': 'seg'})
        segments = []
        for (number, _), answer in zip(pages, answers):
            segments += [{'page': number, 'path': path, 'bbox': box}
                         for path, box in zip(answer['segments'], answer.get('bboxes') or [None] * len(answer['segments']))]
        return segments, 'decimer-segmentation'
    if segmenter == 'auto':
        warnings.append('DECIMER Segmentation is not installed: used the OpenCV segmenter, which merges and '
                        'splits structures less reliably')
    return _segment_opencv(pages, out_dir), 'opencv'


def _sheet(rows, path: Path):
    """One PNG: for each segment its crop, then the structure each distinct answer corresponds to."""
    from PIL import Image, ImageDraw
    from rdkit import Chem
    from rdkit.Chem import Draw
    cell = 220
    columns = 4  # crop + up to three candidate drawings
    sheet = Image.new('RGB', (columns * cell, max(1, len(rows)) * (cell + 24)), 'white')
    draw = ImageDraw.Draw(sheet)
    for row, item in enumerate(rows):
        top = row * (cell + 24)
        draw.text((4, top + 4), f'#{item["index"]}  page {item["page"]}', fill='black')
        try:
            crop = Image.open(item['path']).convert('RGB')
            crop.thumbnail((cell - 8, cell - 8))
            sheet.paste(crop, (4, top + 20))
        except OSError:
            draw.text((4, top + 30), 'unreadable crop', fill='red')
        for column, group in enumerate(item['comparison']['groups'][:columns - 1], 1):
            mol = Chem.MolFromSmiles(group['canonical'])
            if mol is not None:
                sheet.paste(Draw.MolToImage(mol, size=(cell - 8, cell - 8)), (column * cell + 4, top + 20))
            draw.text((column * cell + 4, top + 4), ', '.join(group['engines'])[:34], fill='black')
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def extract(path: str, out_dir: str, pages=None, engines: str = 'molscribe,molvec', segmenter: str = 'auto',
            dpi: int = 200, confirm_upload: bool = False, hand_drawn: bool = False) -> dict:
    """Segment, recognize and compare. ``out_dir`` must be new or empty; nothing existing is overwritten."""
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f'file not found: {path}')
    target = Path(out_dir).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError(f'out_dir {target} is not empty: choose a new folder')
    target.mkdir(parents=True, exist_ok=True)
    started = time.time()
    warnings: list = []
    page_files = _render_pages(source, pages, target, dpi)
    segments, method = _segment(page_files, target, segmenter, warnings)
    if len(segments) > SEGMENT_LIMIT:
        warnings.append(f'{len(segments)} segments found; only the first {SEGMENT_LIMIT} were read')
        segments = segments[:SEGMENT_LIMIT]
    rows = []
    for index, segment in enumerate(segments, 1):
        answer = ocsr.recognize(segment['path'], engines, hand_drawn=hand_drawn, confirm_upload=confirm_upload)
        rows.append({'index': index, **segment, 'comparison': answer['comparison'],
                     'engines': [{'engine': e['engine'], 'ok': e['ok'], 'error': e.get('error'),
                                  'smiles': [s['smiles'] for s in e['structures']]} for e in answer['engines']]})
    sheet = target / 'contact-sheet.png'
    if rows:
        _sheet(rows, sheet)
    review = [r['index'] for r in rows if r['comparison']['needs_review']]
    report = {'ok': True, 'task': 'document_ocsr', 'provenance': envelope.PROVENANCE, 'source': str(source),
              'segmenter': method, 'pages': [n for n, _ in page_files], 'segments': rows,
              'contact_sheet': str(sheet) if rows else None, 'needs_review': review,
              'elapsed_s': round(time.time() - started, 1),
              'warnings': warnings + ['predicted structures: compare every segment with the sheet and the page; '
                                      'segmentation can miss, merge or split structures']}
    (target / 'structures.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    report['output_dir'] = str(target)
    return report
