"""Native bond presentation edits; chemical inventory is checked by the composer."""


def apply_crossings(page, crossings):
    if not isinstance(crossings, list):
        raise ValueError('crossings must be a list')
    ids = {}
    parents = {child:parent for parent in page.iter() for child in parent}
    for n in page.iter():
        if n.get('id'):
            if n.get('id') in ids:
                raise ValueError('Duplicate native object ID')
            ids[n.get('id')] = n
    edges = {}
    pairs = []
    for item in crossings:
        if set(item) != {'front','back'}:
            raise ValueError('crossings require front and back native bond IDs')
        front,back = str(item['front']),str(item['back'])
        if front == back or any(x not in ids or ids[x].tag != 'b' for x in (front,back)):
            raise ValueError('Crossing requires two distinct existing bonds')
        f,b = ids[front],ids[back]
        if parents[f] is not parents[b] or parents[f].tag != 'fragment':
            raise ValueError('Crossing bonds must belong to the same fragment')
        if {f.get('B'), f.get('E')} & {b.get('B'), b.get('E')}:
            raise ValueError('Crossing bonds cannot share an atom')
        edges.setdefault(back,set()).add(front)
        pairs.append((f,b))
    visiting,done,ordered = set(),set(),[]
    def visit(key):
        if key in visiting: raise ValueError('Crossing depth cycle')
        if key in done: return
        visiting.add(key)
        for nxt in sorted(edges.get(key,())): visit(nxt)
        visiting.remove(key);done.add(key);ordered.append(key)
    for key in sorted(set(edges) | {v for values in edges.values() for v in values}): visit(key)
    for key in reversed(ordered):
        n=ids[key];parent=parents[n];parent.remove(n);parent.append(n)
    for f,b in pairs:
        for n,other in ((f,b),(b,f)):
            refs = n.get('CrossingBonds','').split()
            if other.get('id') not in refs: refs.append(other.get('id'))
            n.set('CrossingBonds',' '.join(refs))
    if pairs:
        for z,n in enumerate(page.iter(),1):
            if n.tag in {'fragment','n','b','t','graphic','curve','arrow','group'}:
                n.set('Z',str(z))


def edit_bond_display(node, edit):
    if node.tag != 'b' or set(edit) != {'id','display'}:
        raise ValueError('Bond display edits require only id and display')
    allowed = {'None','Dash','Hash','Bold','WedgeBegin','WedgeEnd','WedgedHashBegin','WedgedHashEnd','Wavy'}
    if edit['display'] not in allowed:
        raise ValueError('Unsupported bond display')
    if edit['display'] == 'None': node.attrib.pop('Display',None)
    else: node.set('Display',edit['display'])
