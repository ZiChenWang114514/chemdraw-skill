"""Preserve explicit compound label offsets when a cleanup moves fragments."""
from pathlib import Path
from xml.etree import ElementTree as ET


def preserve_label_anchors(source, output):
    original, revised = ET.parse(source), ET.parse(output)
    def fragments(tree):
        found={}
        for f in tree.iter('fragment'):
            points=[tuple(map(float,n.get('p').split())) for n in f.findall('n') if n.get('p')]
            if points:
                xs,ys=zip(*points)
                found[f.get('id')]=((min(xs)+max(xs))/2,max(ys),min(xs),max(xs))
        return found
    before,after=fragments(original),fragments(revised)
    excluded=set()
    for step in original.iter('step'):
        for key in ('ReactionStepObjectsAboveArrow','ReactionStepObjectsBelowArrow'):
            excluded.update(step.get(key,'').split())
    target={t.get('id'):t for page in revised.findall('.//page') for t in page.findall('t')}
    changed=False
    labels_by_fragment={}
    for page in original.findall('.//page'):
        for text in page.findall('t'):
            tid=text.get('id')
            if tid in excluded or tid not in target or not text.get('p'):
                continue
            if ''.join(text.itertext()).strip() in ('+',''):
                continue
            x,y=map(float,text.get('p').split())
            candidates=[(abs(x-cx)+abs(y-bottom-14),fid,cx,bottom) for fid,(cx,bottom,left,right) in before.items()
                        if 5<=y-bottom<=25 and abs(x-cx)<=max(8,(right-left)/2)]
            if not candidates:
                continue
            _,fid,cx,bottom=min(candidates)
            if fid not in after:
                continue
            new_x=after[fid][0]+x-cx; new_y=after[fid][1]+y-bottom
            node=target[tid]; old_x,old_y=map(float,node.get('p').split())
            labels_by_fragment.setdefault(fid,[]).append(node)
            dx,dy=new_x-old_x,new_y-old_y
            node.set('p',f'{new_x:.4f} {new_y:.4f}')
            if node.get('BoundingBox'):
                box=list(map(float,node.get('BoundingBox').split()))
                node.set('BoundingBox',' '.join(f'{v+(dx if i%2==0 else dy):.4f}' for i,v in enumerate(box)))
            changed=True
    nodes={n.get('id'):n for n in revised.iter() if n.get('id')}
    def shift(node,dy):
        for child in node.iter():
            for key in ('p','BoundingBox'):
                if child.get(key):
                    values=list(map(float,child.get(key).split()))
                    child.set(key,' '.join(f'{v+(dy if i%2 else 0):.4f}' for i,v in enumerate(values)))
    for step in revised.iter('step'):
        arrows=[nodes.get(a) for a in step.get('ReactionStepArrows','').split()]
        arrows=[a for a in arrows if a is not None and a.get('Head3D')]
        if not arrows:
            continue
        arrow_y=min(float(a.get('Head3D').split()[1]) for a in arrows)
        for fid in step.get('ReactionStepObjectsAboveArrow','').split():
            fragment=nodes.get(fid)
            if fragment is None or fragment.tag!='fragment' or fid not in labels_by_fragment:
                continue
            labels=labels_by_fragment[fid]
            visible_bottom=max(float(t.get('p').split()[1])+3 for t in labels)
            dy=min(0,arrow_y-8-visible_bottom)
            if dy:
                shift(fragment,dy)
                for label in labels: shift(label,dy)
                changed=True
    if changed:
        revised.write(output,encoding='utf-8',xml_declaration=True)
