"""Real engines on real inputs. Skipped unless CDX_ENGINES_LIVE=1 and the engine is installed.

    CDX_ENGINES_LIVE=1 python -m pytest tests/runtime/test_engines_live.py -m engine_live -q
"""
import os

import pytest

from cdxml_toolkit.engines import document, env, nmr, ocsr, reactions

pytestmark = [pytest.mark.engine_live,
              pytest.mark.skipif(os.environ.get('CDX_ENGINES_LIVE') != '1', reason='set CDX_ENGINES_LIVE=1')]

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'


def need(*names):
    missing = [n for n in names if not env.available().get(n)]
    if missing:
        pytest.skip('not installed: ' + ', '.join(missing))


def drawing(path, smiles=ASPIRIN):
    from rdkit import Chem
    from rdkit.Chem import Draw
    Draw.MolToFile(Chem.MolFromSmiles(smiles), str(path), size=(500, 400))
    return str(path)


def key(smiles):
    from rdkit import Chem
    return Chem.MolToInchiKey(Chem.MolFromSmiles(smiles))


@pytest.mark.parametrize('engine', ['molscribe', 'molnextr', 'molparser', 'molvec'])
def test_each_ocsr_engine_reads_a_clean_drawing(engine, tmp_path):
    need(engine)
    out = ocsr.recognize(drawing(tmp_path / 'a.png'), engines=engine)
    assert out['ok'] and out['engines'][0]['structures'][0]['inchikey'] == key(ASPIRIN)
    assert out['provenance'] == 'model_prediction'


def test_engines_that_agree_are_still_only_candidates(tmp_path):
    need('molscribe', 'molvec')
    out = ocsr.recognize(drawing(tmp_path / 'a.png'), engines='molscribe,molvec')
    assert out['comparison']['agreement'] == 'all' and out['comparison']['selected'] is None


def test_pdf_extraction_keeps_whole_structures(tmp_path):
    need('decimer-segmentation', 'molscribe')
    import fitz
    page = fitz.open()
    sheet = page.new_page()
    sheet.insert_image(fitz.Rect(60, 60, 460, 360), filename=drawing(tmp_path / 'a.png'))
    pdf = tmp_path / 'p.pdf'
    page.save(str(pdf))
    out = document.extract(str(pdf), str(tmp_path / 'out'), engines='molscribe')
    assert out['segmenter'] == 'decimer-segmentation' and len(out['segments']) == 1
    segment = out['segments'][0]
    assert segment['bbox'] and segment['comparison']['groups'][0]['inchikey'] == key(ASPIRIN)


def test_forward_prediction_is_labelled_and_balanced():
    need('reactiont5-forward')
    out = reactions.products('CC(=O)OC(C)=O.OC(=O)c1ccccc1O')
    assert out['provenance'] == 'model_prediction' and out['structures']


def test_multi_step_route_for_aspirin_is_in_stock():
    need('aizynthfinder')
    out = reactions.retrosynthesis(ASPIRIN, engine='aizynthfinder', steps='multi')
    assert out['solved'] and out['routes'][0]['all_in_stock']


def test_nmr_of_ethyl_acetate_has_the_expected_peak_counts():
    need('magnet')
    out = nmr.predict('CCOC(C)=O', nucleus='both')
    assert len(out['peaks']['1H']) == 3 and len(out['peaks']['13C']) == 4
    assert all(p['predicted'] for p in out['peaks']['1H'] + out['peaks']['13C'])
