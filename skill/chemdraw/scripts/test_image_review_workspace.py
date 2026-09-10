import json
from pathlib import Path
import pytest
from PIL import Image
from image_review_workspace import prepare,compare,digest

def fixture(tmp_path,regions):
    im=tmp_path/'source.png';Image.new('RGB',(100,60),'white').save(im)
    reg=tmp_path/'regions.json';reg.write_text(json.dumps(regions))
    return im,reg

def test_prepare_tracks_original_and_crop(tmp_path):
    im,r=fixture(tmp_path,[{'id':'A','box':[10,10,50,40]}])
    result=prepare(im,r,tmp_path/'out',2)
    assert result['source_sha256']==digest(im)
    assert result['regions'][0]['crop_dimensions']==[80,60]
    assert result['chemical_acceptance']=='not_evaluated'

@pytest.mark.parametrize('regions',[[{'id':'../A','box':[0,0,5,5]}],
    [{'id':'A','box':[-1,0,5,5]}],[{'id':'A','box':[0,0,101,5]}],
    [{'id':'A','box':[0,0,5,5]}]*2,[]])
def test_invalid_regions_leave_no_directory(tmp_path,regions):
    im,r=fixture(tmp_path,regions)
    with pytest.raises(ValueError):prepare(im,r,tmp_path/'out')
    assert not (tmp_path/'out').exists()

def test_comparison_is_pending_and_protects_existing_files(tmp_path):
    im,r=fixture(tmp_path,[{'id':'A','box':[0,0,5,5]}])
    output=tmp_path/'pair.png';receipt=compare(im,im,output,100)
    assert receipt['visual_review']=='pending_agent_inspection'
    assert receipt['display_uniform_scale_factors']==[100/60]*2
    assert not receipt['mirroring'] and not receipt['warping']
    with pytest.raises(FileExistsError):compare(im,im,output,100)

def test_exclusion_and_coordinate_mapping_preserve_source(tmp_path):
    im,r=fixture(tmp_path,[{'id':'A','box':[10,10,50,40],'exclude_boxes':[[12,12,15,16]]}])
    Image.new('RGB',(100,60),'black').save(im)
    original=digest(im)
    result=prepare(im,r,tmp_path/'out',1)
    with Image.open(tmp_path/'out/A.png') as crop:
        assert crop.getpixel((2,2))==(255,255,255)
        assert crop.getpixel((5,2))==(0,0,0)
    assert result['regions'][0]['crop_to_source']=={'scale':1,'offset':[10,10]}
    assert digest(im)==original

def test_outside_exclusion_rejected_before_writing(tmp_path):
    im,r=fixture(tmp_path,[{'id':'A','box':[10,10,50,40],'exclude_boxes':[[0,0,15,16]]}])
    with pytest.raises(ValueError,match='inside'):prepare(im,r,tmp_path/'out')
    assert not (tmp_path/'out').exists()
