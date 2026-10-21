"""Native TLC plates and explicitly calibrated spot measurements."""
from .common import Drawing, number, point


def measure_rf(origin, solvent_front, spot):
    """Project a measured spot along the calibrated solvent travel direction."""
    a,b,s=map(point,(origin,solvent_front,spot))
    d=[b[i]-a[i] for i in range(2)]
    length=sum(v*v for v in d)
    if length==0:raise ValueError('Origin and solvent front must differ')
    return number(sum((s[i]-a[i])*d[i] for i in range(2))/length,'Rf',0,1)


def draw_tlc(spec, output):
    lanes=spec.get('lanes',[])
    if not 1<=len(lanes)<=24:raise ValueError('Provide 1..24 TLC lanes')
    width=number(spec.get('width',max(150,60*len(lanes))),'width',60,1500)
    height=number(spec.get('height',210),'height',60,1500)
    origin=number(spec.get('origin_fraction',.1),'origin_fraction',0,.4)
    front=number(spec.get('front_fraction',.1),'front_fraction',0,.4)
    d=Drawing(width+80,height+100)
    d.text([25,20],spec.get('title','TLC plate'))
    x,y=30,40
    plate=d.add('tlcplate',{'TopLeft':f'{x} {y}','TopRight':f'{x+width} {y}',
        'BottomLeft':f'{x} {y+height}','BottomRight':f'{x+width} {y+height}',
        'BoundingBox':f'{x} {y} {x+width} {y+height}', 'OriginFraction':origin,
        'SolventFrontFraction':front,'ShowOrigin':'yes','ShowSolventFront':'yes','ShowBorders':'yes'})
    for index,lane in enumerate(lanes):
        node=d.add('tlclane',{},plate)
        spots=lane.get('spots',[])
        if len(spots)>100:raise ValueError('At most 100 spots per lane')
        for spot in spots:
            d.add('tlcspot',{'Rf':number(spot['rf'],'Rf',0,1),
                # TLC dimensions use raw 16.16 integers even in native CDXML.
                'Width':round(65536*number(spot.get('width',8),'spot width',.1,width/len(lanes))),
                'Height':round(65536*number(spot.get('height',5),'spot height',.1,height)),
                'Tail':round(65536*number(spot.get('tail',0),'tail',0,height)),
                'CurveType':'128' if spot.get('filled',True) else '0',
                'ShowRf':'yes' if spec.get('show_rf',True) else 'no'},node)
        d.text([x+width*(index+.5)/len(lanes)-10,y+height+15],lane.get('label',str(index+1)),8)
    d.text([x,y+height+35],spec.get('solvent','Solvent system not supplied'),9)
    return {'output_path':d.save(output),'lane_count':len(lanes),
        'measurement_basis':spec.get('measurement_basis','provided Rf values'),
        'quantitative_purity':'not inferred from spot size or intensity'}
