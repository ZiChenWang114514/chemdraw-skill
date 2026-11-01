import json

import pytest

cv2 = pytest.importorskip('cv2')
pymupdf = pytest.importorskip('pymupdf')

from PIL import Image
from rdkit import Chem
from rdkit.Chem import Draw

from cdxml_toolkit.engines import document, env
from cdxml_toolkit.mcp_runtime.engine_tools import extract_structures_from_document

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
CAFFEINE = 'Cn1c(=O)c2c(ncn2C)n(C)c1=O'


@pytest.fixture
def page(tmp_path):
    """A white page with two well separated structures."""
    sheet = Image.new('RGB', (1000, 500), 'white')
    for x, smiles in ((60, ASPIRIN), (560, CAFFEINE)):
        sheet.paste(Draw.MolToImage(Chem.MolFromSmiles(smiles), size=(380, 300)), (x, 100))
    path = tmp_path / 'page.png'
    sheet.save(path)
    return path


@pytest.fixture
def fake_engines(monkeypatch):
    def available():
        from cdxml_toolkit.engines.registry import ENGINES
        return {n: n in {'molscribe'} for n in ENGINES}

    answers = iter([ASPIRIN, CAFFEINE])
    monkeypatch.setattr(env, 'available', available)
    monkeypatch.setattr(env, 'call', lambda name, action, params, timeout=0: [{'smiles': next(answers)}])


def test_an_image_page_is_segmented_read_and_summarised(page, tmp_path, fake_engines):
    out = tmp_path / 'out'
    report = extract_structures_from_document(str(page), str(out), engines='molscribe')
    assert report['segmenter'] == 'opencv' and len(report['segments']) == 2
    assert any('OpenCV segmenter' in w for w in report['warnings'])
    assert [r['engines'][0]['smiles'] for r in report['segments']] == [[ASPIRIN], [CAFFEINE]]
    assert report['needs_review'] == [1, 2]  # one engine alone is never enough to stop looking
    assert (out / 'contact-sheet.png').is_file() and json.loads((out / 'structures.json').read_text())['segments']
    assert Image.open(out / 'contact-sheet.png').size[1] >= 2 * 220


def test_a_pdf_page_is_rendered_first(page, tmp_path, fake_engines):
    pdf = tmp_path / 'paper.pdf'
    with pymupdf.open() as doc:
        sheet = doc.new_page(width=500, height=250)
        sheet.insert_image(sheet.rect, filename=str(page))
        doc.save(pdf)
    report = extract_structures_from_document(str(pdf), str(tmp_path / 'pdf-out'), pages=[1], engines='molscribe')
    assert report['pages'] == [1] and len(report['segments']) == 2
    with pytest.raises(ValueError, match='outside 1..1'):
        extract_structures_from_document(str(pdf), str(tmp_path / 'again'), pages=[3])


def test_existing_output_is_never_overwritten(page, tmp_path, fake_engines):
    out = tmp_path / 'out'
    out.mkdir()
    (out / 'keep.txt').write_text('mine')
    with pytest.raises(ValueError, match='not empty'):
        document.extract(str(page), str(out))
    assert (out / 'keep.txt').read_text() == 'mine'


def test_a_missing_deep_segmenter_is_named_when_asked_for_explicitly(page, tmp_path, fake_engines):
    with pytest.raises(ValueError, match='install-engines decimer-segmentation'):
        extract_structures_from_document(str(page), str(tmp_path / 'o'), segmenter='decimer-segmentation')
