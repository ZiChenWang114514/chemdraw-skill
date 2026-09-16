"""Local visual-review helpers. No OCSR, upload, or automatic chemical acceptance.

prepare IMAGE REGIONS_JSON NEW_DIRECTORY [--scale N]
compare LEFT RIGHT NEW_PNG [--height N]
Regions: [{"id":"13a","box":[left,top,right,bottom],"kind":"structure",
           "exclude_boxes": [[left,top,right,bottom]]}]. Exclusions use source pixels.
The agent must inspect crops and native redraws before recording a verdict.
"""
from pathlib import Path
import argparse,hashlib,json,re
from PIL import Image,ImageDraw,ImageOps

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _prepare(image_path,regions_path,output_dir,scale=1):
    if not isinstance(scale,int) or not 1<=scale<=8:
        raise ValueError('scale must be an integer in 1..8; upsampling adds no information')
    image_path,regions_path,output_dir=map(Path,(image_path,regions_path,output_dir))
    regions=json.loads(regions_path.read_text(encoding='utf-8-sig'))
    if not isinstance(regions,list) or not regions:
        raise ValueError('regions must be a nonempty list')
    with Image.open(image_path) as raw:
        image=ImageOps.exif_transpose(raw).convert('RGB')
    names=set()
    for region in regions:
        name=region['id'];box=region['box']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',name) or name in names:
            raise ValueError('region IDs must be unique safe filenames')
        names.add(name)
        if len(box)!=4 or any(type(v) is not int for v in box):
            raise ValueError('boxes need four integer pixel coordinates')
        x1,y1,x2,y2=box
        if not 0<=x1<x2<=image.width or not 0<=y1<y2<=image.height:
            raise ValueError('region extends outside the image or is empty')
        if region.get('kind','structure') not in ('structure','conditions','annotation'):
            raise ValueError('unknown region kind')
        for excluded in region.get('exclude_boxes',[]):
            if len(excluded)!=4 or any(type(v) is not int for v in excluded):
                raise ValueError('exclude_boxes need four integer coordinates')
            a,b,c,d=excluded
            if not x1<=a<c<=x2 or not y1<=b<d<=y2:
                raise ValueError('exclude_boxes must lie inside their region')
    output_dir.mkdir(parents=True,exist_ok=False)
    records=[]
    for region in regions:
        path=output_dir/(region['id']+'.png');crop=image.crop(region['box'])
        x0,y0=region['box'][:2]
        for a,b,c,d in region.get('exclude_boxes',[]):
            ImageDraw.Draw(crop).rectangle((a-x0,b-y0,c-x0-1,d-y0-1),fill='white')
        if scale!=1:crop=crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.LANCZOS)
        crop.save(path)
        records.append({**region,'path':str(path.resolve()),'sha256':digest(path),
                        'crop_dimensions':list(crop.size),
                        'crop_to_source':{'scale':1/scale,'offset':[x0,y0]},
                        'status':'awaiting_agent_review'})
    result={'source':str(image_path.resolve()),'source_sha256':digest(image_path),
            'display_dimensions':list(image.size),'exif_orientation_applied':True,
            'scale':scale,'regions':records,'chemical_acceptance':'not_evaluated'}
    (output_dir/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def prepare(image_path,regions_path,output_dir,scale=1):
    from cdxml_toolkit.mcp_runtime import artifact_safety as safety
    target=Path(output_dir).resolve()
    if target.exists():raise FileExistsError(target)
    with safety.staging_directory(target) as stage:
        payload=stage/'crops'
        result=_prepare(image_path,regions_path,payload,scale)
        result=safety.rewrite_paths(result,payload,target)
        (payload/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        safety.publish_directory(payload,target)
    return result


def compare(left,right,output_path,height=500,*,native_receipt=None,mode='display',offset=(0,0),region=None):
    from cdxml_toolkit.mcp_runtime import artifact_safety as safety
    left,right,output_path=map(Path,(left,right,output_path))
    if not isinstance(height,int) or not 50<=height<=2000:raise ValueError('height must be 50..2000')
    if output_path.exists() or output_path.with_suffix('.json').exists():raise FileExistsError(output_path)
    if mode not in ('display','aligned'):raise ValueError('mode must be display or aligned')
    if len(offset)!=2 or any(type(x) is not int for x in offset):raise ValueError('offset needs two integer pixels')
    if mode=='display' and tuple(offset)!=(0,0):raise ValueError('offset requires aligned mode')
    provenance='unverified'
    if native_receipt:
        proof=json.loads(Path(native_receipt).read_text(encoding='utf-8-sig'))
        proof=proof.get('result',proof)
        meta=proof.get('metadata',{})
        artifacts=meta.get('artifacts',[])
        rendered=proof.get('outputs',{}).get('rendered',[])
        valid=proof.get('ok') is True and meta.get('renderer')=='ChemDraw COM'
        valid=valid and str(right.resolve()) in [str(Path(p).resolve()) for p in rendered]
        valid=valid and any(Path(a.get('path','')).resolve()==right.resolve() and a.get('sha256')==digest(right) for a in artifacts)
        if not valid:raise ValueError('Native receipt does not match candidate path, hash, or renderer')
        provenance='native_receipt_matched'
    panels=[];scales=[];images=[]
    for path in (left,right):
        with Image.open(path) as raw:
            rgba=ImageOps.exif_transpose(raw).convert('RGBA')
            bg=Image.new('RGBA',rgba.size,'white');im=Image.alpha_composite(bg,rgba).convert('RGB')
        images.append(im)
    if mode=='aligned':
        a,b=images;dx,dy=offset
        if dx<0 or dy<0 or dx+b.width>a.width or dy+b.height>a.height:
            raise ValueError('Alignment would clip candidate pixels')
        padded=Image.new('RGB',a.size,'white');padded.paste(b,(dx,dy));images=[a,padded]
    if region is not None:
        if len(region)!=4 or any(type(v) is not int for v in region):raise ValueError('region needs four integer pixels')
        x1,y1,x2,y2=region
        if any(not (0<=x1<x2<=im.width and 0<=y1<y2<=im.height) for im in images):raise ValueError('region outside image')
        images=[im.crop(region) for im in images]
    for im in images:
        factor=height/im.height if mode=='display' or region else 1
        scales.append(factor)
        panels.append(im.resize((max(1,round(im.width*factor)),height),Image.Resampling.LANCZOS))
        if factor==1:panels[-1]=im.copy()
    canvas=Image.new('RGB',(sum(p.width for p in panels)+36,max(p.height for p in panels)+36),'white');d=ImageDraw.Draw(canvas)
    x=12
    candidate_title='CANDIDATE - NATIVE RECEIPT MATCHED' if provenance=='native_receipt_matched' else 'CANDIDATE'
    for title,panel in zip(('REFERENCE',candidate_title),panels):
        d.text((x,5),title,fill='black');canvas.paste(panel,(x,24));x+=panel.width+12
    result={'left':str(left.resolve()),'right':str(right.resolve()),'source_sha256':digest(left),
            'candidate_sha256':digest(right),'display_uniform_scale_factors':scales,
            'mirroring':False,'warping':False,'visual_review':'pending_agent_inspection',
            'chemical_acceptance':'not_evaluated','candidate_provenance':provenance,
            'comparison_mode':mode,'translation_pixels':list(offset),'region':region,
            'strict_pixel_comparison':False}
    if mode=='aligned' and region is None:
        import numpy as np
        a,b=(np.asarray(im).astype(float) for im in images)
        ia,ib=a.min(axis=2)<240,b.min(axis=2)<240
        union=(ia|ib).sum()
        result.update(strict_pixel_comparison=True,exact_pixels=bool(np.array_equal(a,b)),
                      normalized_mae=float(abs(a-b).mean()/255),ink_iou=float((ia&ib).sum()/union) if union else 1.0)
    with safety.staging_directory(output_path.parent/'comparison-stage') as stage:
        png=stage/'comparison.png';record=stage/'comparison.json'
        canvas.save(png);result['comparison_sha256']=digest(png)
        record.write_text(json.dumps(result,indent=2),encoding='utf-8')
        safety.publish_files([(png,output_path),(record,output_path.with_suffix('.json'))])
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='op',required=True)
    a=sub.add_parser('prepare');a.add_argument('image');a.add_argument('regions');a.add_argument('output');a.add_argument('--scale',type=int,default=1)
    b=sub.add_parser('compare');b.add_argument('left');b.add_argument('right');b.add_argument('output');b.add_argument('--height',type=int,default=500)
    b.add_argument('--native-receipt');b.add_argument('--mode',choices=['display','aligned'],default='display')
    b.add_argument('--offset',type=int,nargs=2,default=[0,0]);b.add_argument('--region',type=int,nargs=4)
    args=p.parse_args()
    result=prepare(args.image,args.regions,args.output,args.scale) if args.op=='prepare' else compare(args.left,args.right,args.output,args.height,native_receipt=args.native_receipt,mode=args.mode,offset=args.offset,region=args.region)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
