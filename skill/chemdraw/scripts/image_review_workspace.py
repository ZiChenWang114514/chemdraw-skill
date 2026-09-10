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

def prepare(image_path,regions_path,output_dir,scale=1):
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

def compare(left,right,output_path,height=500):
    left,right,output_path=map(Path,(left,right,output_path))
    if not isinstance(height,int) or not 50<=height<=2000:raise ValueError('height must be 50..2000')
    if output_path.exists() or output_path.with_suffix('.json').exists():raise FileExistsError(output_path)
    panels=[];scales=[]
    for path in (left,right):
        with Image.open(path) as raw:
            rgba=ImageOps.exif_transpose(raw).convert('RGBA')
            bg=Image.new('RGBA',rgba.size,'white');im=Image.alpha_composite(bg,rgba).convert('RGB')
        factor=height/im.height;scales.append(factor)
        panels.append(im.resize((max(1,round(im.width*factor)),height),Image.Resampling.LANCZOS))
    canvas=Image.new('RGB',(sum(p.width for p in panels)+36,height+36),'white');d=ImageDraw.Draw(canvas)
    x=12
    for title,panel in zip(('REFERENCE','CANDIDATE - NATIVE CHEMDRAW'),panels):
        d.text((x,5),title,fill='black');canvas.paste(panel,(x,24));x+=panel.width+12
    output_path.parent.mkdir(parents=True,exist_ok=True);canvas.save(output_path)
    result={'left':str(left.resolve()),'right':str(right.resolve()),'source_sha256':digest(left),
            'candidate_sha256':digest(right),'display_uniform_scale_factors':scales,
            'mirroring':False,'warping':False,'visual_review':'pending_agent_inspection',
            'chemical_acceptance':'not_evaluated','comparison_sha256':digest(output_path)}
    output_path.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='op',required=True)
    a=sub.add_parser('prepare');a.add_argument('image');a.add_argument('regions');a.add_argument('output');a.add_argument('--scale',type=int,default=1)
    b=sub.add_parser('compare');b.add_argument('left');b.add_argument('right');b.add_argument('output');b.add_argument('--height',type=int,default=500)
    args=p.parse_args()
    result=prepare(args.image,args.regions,args.output,args.scale) if args.op=='prepare' else compare(args.left,args.right,args.output,args.height)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
