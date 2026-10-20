"""Editable fixed-layout chemical figures and bounded RDKit analysis tools."""
from __future__ import annotations

import json
import math
import hashlib
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from rdkit import Chem
from rdkit.Chem import AllChem, rdCIPLabeler, rdDepictor

from ..chemistry_semantics import semantic_key, validate_fragment, document_inventory
from . import artifact_safety


def _publish(data, output_path):
    target = artifact_safety.resolve_destination(source=None, output_path=output_path,
        tag='rdkit', suffix='.json')
    with artifact_safety.staging_file(target) as stage:
        stage.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        artifact_safety.publish_file(stage, target)
    return artifact_safety.with_artifacts({'ok': True, 'output_path': str(target),
        'operation': data.get('operation'), 'count': len(data.get('results', []))}, [target])


def _mol(record):
    if record.get('molblock'):
        mol = Chem.MolFromMolBlock(record['molblock'], removeHs=False)
    elif record.get('file'):
        path = Path(record['file']).expanduser().resolve()
        if path.suffix.lower() == '.cdxml':
            from ..chemistry_semantics import read_molecules
            mols = read_molecules(path)
            index = int(record.get('fragment_index', 0))
            mol = mols[index]
        elif path.suffix.lower() in ('.mol', '.sdf'):
            if path.suffix.lower() == '.sdf':
                supplier = Chem.SDMolSupplier(str(path), removeHs=False)
                mol = supplier[int(record.get('fragment_index', 0))]
            else:
                mol = Chem.MolFromMolFile(str(path), removeHs=False)
        else:
            raise ValueError('Supported structure files: CDXML, MOL, SDF')
    else:
        mol = Chem.MolFromSmiles(record.get('smiles', ''))
    if mol is None or not mol.GetNumAtoms():
        raise ValueError('A grounded, nonempty molecule is required')
    if mol.GetNumAtoms() > 1000:
        raise ValueError('Molecule exceeds the 1000 atom drawing limit')
    return mol


def _descriptor(mol):
    from rdkit.Chem import Descriptors, rdMolDescriptors
    mol = Chem.Mol(mol)
    rdCIPLabeler.AssignCIPLabels(mol)
    return {'smiles': Chem.MolToCXSmiles(mol), 'semantic_key': semantic_key(mol),
        'formula': rdMolDescriptors.CalcMolFormula(mol), 'mw': Descriptors.MolWt(mol),
        'exact_mass': Descriptors.ExactMolWt(mol),
        'atoms': [{'index': a.GetIdx(), 'element': a.GetSymbol(),
                   'cip': a.GetProp('_CIPCode') if a.HasProp('_CIPCode') else None,
                   'isotope': a.GetIsotope(), 'charge': a.GetFormalCharge(),
                   'map_number': a.GetAtomMapNum()} for a in mol.GetAtoms()],
        'potential_stereo': [{'type': str(s.type), 'center': s.centeredOn,
                             'specified': str(s.specified)} for s in Chem.FindPotentialStereo(mol)],
        'stereo_groups': [{'type': str(g.GetGroupType()),
                          'atoms': [a.GetIdx() for a in g.GetAtoms()]} for g in mol.GetStereoGroups()]}


def rdkit_workbench(molecules: list[dict], operation: str = 'inspect',
                    options: dict | None = None, output_path: str | None = None) -> dict:
    """Analyze grounded molecules: inspect, stereoisomers, tautomers, mcs, r_groups, set_stereo.

    Input records accept smiles/CXSMILES, molblock, or file (CDXML/MOL/SDF).
    Atom indices are zero-based and refer to each input's atom order. Options:
    max_results (1..128), only_unassigned (stereoisomers, default true),
    include_molblock, timeout (MCS, 1..30 seconds). R-group decomposition uses
    molecules[0] as the explicit core. set_stereo takes configurations={index:
    R/S/unspecified} for one molecule, verifies the achieved CIP labels, and emits
    a connectivity-preserving diff. Enumeration creates candidate structures,
    not predictions of populations, reaction products, or experimental ratios.
    Writes provenance, bounded candidate results and truncation status to JSON.
    """
    if not 1 <= len(molecules) <= 128:
        raise ValueError('Provide 1..128 grounded molecules')
    options = options or {}
    unknown = set(options) - {'max_results', 'only_unassigned', 'include_molblock', 'timeout', 'configurations'}
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')
    limit = int(options.get('max_results', 32))
    if not 1 <= limit <= 128:
        raise ValueError('max_results must be 1..128')
    mols = [_mol(m) for m in molecules]
    results, warnings = [], []
    if operation == 'inspect':
        results = [_descriptor(m) for m in mols]
    elif operation == 'stereoisomers':
        from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions
        for i, mol in enumerate(mols):
            opts = StereoEnumerationOptions(onlyUnassigned=bool(options.get('only_unassigned', True)),
                                           maxIsomers=limit + 1, unique=True, rand=0)
            candidates = list(EnumerateStereoisomers(mol, options=opts))
            results.append({'input_index': i, 'truncated': len(candidates) > limit,
                            'candidates': [_descriptor(m) for m in candidates[:limit]]})
        warnings.append('Enumeration does not establish stereoisomer abundance or accessibility.')
    elif operation == 'tautomers':
        from rdkit.Chem.MolStandardize import rdMolStandardize
        for i, mol in enumerate(mols):
            enumerator = rdMolStandardize.TautomerEnumerator()
            enumerator.SetMaxTautomers(limit + 1)
            enumerator.SetMaxTransforms(1000)
            candidates = enumerator.Enumerate(mol)
            results.append({'input_index': i, 'status': str(candidates.status),
                'truncated': len(candidates) > limit or str(candidates.status) != 'Completed',
                'candidates': [_descriptor(m) for m in list(candidates)[:limit]]})
        warnings.append('Tautomer candidates are not a pH-dependent equilibrium prediction; stereo may change.')
    elif operation == 'mcs':
        from rdkit.Chem import rdFMCS
        if len(mols) < 2:
            raise ValueError('MCS needs at least two molecules')
        timeout = int(options.get('timeout', 10))
        if not 1 <= timeout <= 30:
            raise ValueError('timeout must be 1..30 seconds')
        mcs = rdFMCS.FindMCS(mols, timeout=timeout, ringMatchesRingOnly=True,
                            completeRingsOnly=True, matchChiralTag=True)
        query = Chem.MolFromSmarts(mcs.smartsString)
        results = [{'smarts': mcs.smartsString, 'atoms': mcs.numAtoms, 'bonds': mcs.numBonds,
                    'timed_out': mcs.canceled,
                    'matches': [list(m.GetSubstructMatch(query)) if query else [] for m in mols]}]
    elif operation == 'set_stereo':
        if len(mols)!=1 or not options.get('configurations'):
            raise ValueError('set_stereo requires one molecule and explicit configurations')
        source=mols[0]; changed=Chem.Mol(source)
        # Enhanced groups encode collective semantics and must not be silently altered.
        if source.GetStereoGroups():
            raise ValueError('set_stereo on enhanced stereo groups needs explicit group-aware editing')
        potential_centers={int(info.centeredOn) for info in Chem.FindPotentialStereo(source)
                           if str(info.type)=='Atom_Tetrahedral'}
        diff=[]
        for raw_index,target in options['configurations'].items():
            index=int(raw_index)
            if index not in range(changed.GetNumAtoms()) or target not in ('R','S','unspecified'):
                raise ValueError('Specify a valid zero-based atom index and R, S, or unspecified')
            atom=changed.GetAtomWithIdx(index)
            rdCIPLabeler.AssignCIPLabels(changed)
            old=atom.GetProp('_CIPCode') if atom.HasProp('_CIPCode') else None
            if target=='unspecified':
                atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
                if atom.HasProp('_CIPCode'): atom.ClearProp('_CIPCode')
            else:
                if index not in potential_centers: raise ValueError('Atom is not a potential tetrahedral stereocenter')
                if atom.GetDegree() not in (3,4): raise ValueError('Not a tetrahedral center')
                atom.SetChiralTag(Chem.ChiralType.CHI_TETRAHEDRAL_CW)
                if atom.HasProp('_CIPCode'): atom.ClearProp('_CIPCode')
                rdCIPLabeler.AssignCIPLabels(changed)
                if not atom.HasProp('_CIPCode'): raise ValueError('CIP could not be assigned to this atom')
                if atom.GetProp('_CIPCode')!=target:
                    atom.InvertChirality(); atom.ClearProp('_CIPCode'); rdCIPLabeler.AssignCIPLabels(changed)
                if atom.GetProp('_CIPCode')!=target: raise ValueError('Requested CIP configuration was not achieved')
            diff.append({'atom_index':index,'before':old,'after':target})
        a,b=Chem.Mol(source),Chem.Mol(changed)
        Chem.RemoveStereochemistry(a); Chem.RemoveStereochemistry(b)
        if semantic_key(a)!=semantic_key(b): raise ValueError('Unexpected connectivity change')
        for raw_index,target in options['configurations'].items():
            atom=changed.GetAtomWithIdx(int(raw_index))
            if target!='unspecified' and atom.GetProp('_CIPCode')!=target:
                raise ValueError('A coupled stereocenter changed an earlier CIP assignment')
        results=[{**_descriptor(changed),'diff':diff,'connectivity_preserved':True}]
    elif operation == 'r_groups':
        from rdkit.Chem import rdRGroupDecomposition
        if len(mols) < 2:
            raise ValueError('Provide an explicit core followed by molecules to decompose')
        rows, unmatched = rdRGroupDecomposition.RGroupDecompose([mols[0]], mols[1:], asSmiles=True)
        results = [{'rows': rows, 'unmatched_input_indices': [i + 1 for i in unmatched]}]
    else:
        raise ValueError('operation must be inspect, stereoisomers, tautomers, mcs, r_groups, or set_stereo')
    if options.get('include_molblock') and operation == 'inspect':
        for result, mol in zip(results, mols):
            if mol.GetNumConformers() == 0:
                rdDepictor.Compute2DCoords(mol)
            result['molblock'] = Chem.MolToMolBlock(mol, forceV3000=True)
    data = {'operation': operation, 'input_keys': [semantic_key(m) for m in mols],
            'results': results, 'warnings': warnings, 'index_convention': 'zero_based_input_atom_order'}
    return _publish(data, output_path)


def _point(value):
    if len(value) != 2 or not all(math.isfinite(float(x)) and abs(float(x)) < 1e6 for x in value):
        raise ValueError('Coordinates must be two finite point values')
    return tuple(map(float, value))


def _move(element, dx, dy):
    for node in element.iter():
        for key in ('p', 'BoundingBox', 'Head3D', 'Tail3D', 'Center3D', 'MajorAxisEnd3D', 'MinorAxisEnd3D', 'CurvePoints'):
            if key not in node.attrib:
                continue
            values = list(map(float, node.get(key).split()))
            stride = 3 if key.endswith('3D') else 2
            for i in range(0, len(values), stride):
                values[i] += dx
                values[i + 1] += dy
            node.set(key, ' '.join(f'{v:.4f}' for v in values))


def compose_chemical_figure(manifest_path: str, output_path: str) -> dict:
    """Compose editable CDXML using explicit point coordinates and grounded molecules.

    Read the Skill publication-figures reference for the JSON manifest schema.
    Supports molecules with exact atom coordinates or template alignment, CIP/
    atom labels, highlights, rich text, straight/equilibrium/resonance/retro arrows,
    curved electron arrows, brackets and shapes. A template_path preserves native
    objects and permits translations/text edits without flattening. Outputs final
    CDXML round-trip validation; native rendering and reference comparison are
    separate required steps. Never claims journal identity from export success.
    """
    from ..render.renderer import _IDGen, _build_fragment
    from ..image.structure_from_image import _rdkit_mol_to_atom_bond_dicts
    manifest_file = Path(manifest_path).expanduser().resolve()
    data = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
    allowed = {'version', 'template_path', 'edits', 'style', 'objects', 'steps', 'grid', 'crossings'}
    if set(data) - allowed:
        raise ValueError(f'Unknown manifest fields: {sorted(set(data) - allowed)}')
    if data.get('version', 1) != 1:
        raise ValueError('Unsupported figure manifest version')
    objects = data.get('objects', [])
    if data.get('grid'):
        grid=data['grid']; columns=int(grid.get('columns',3))
        if not 1<=columns<=20: raise ValueError('grid columns must be 1..20')
        cell_width,row_height=float(grid.get('cell_width',160)),float(grid.get('row_height',140))
        if min(cell_width,row_height)<20: raise ValueError('Grid cells must be at least 20 points')
        ox,oy=_point(grid.get('origin',[90,90])); count=0
        objects=[dict(item) for item in objects]
        for item in objects:
            if item.get('type')=='molecule' and 'position' not in item and 'coordinates' not in item:
                item['position']=[ox+(count%columns)*cell_width,oy+(count//columns)*row_height]; count+=1
    if len(objects) > 1000:
        raise ValueError('At most 1000 scene objects')
    def local_path(value):
        path = Path(value).expanduser()
        return path.resolve() if path.is_absolute() else (manifest_file.parent / path).resolve()
    template = local_path(data['template_path']) if data.get('template_path') else None
    if data.get('crossings') and not template:
        raise ValueError('Crossings require a native template')
    if template and not any(data.get(k) for k in ('edits','objects','style','steps','crossings')):
        target=artifact_safety.resolve_destination(source=template,output_path=output_path,tag='figure',suffix='.cdxml')
        with artifact_safety.staging_file(target) as stage:
            stage.write_bytes(template.read_bytes())
            artifact_safety.validate_artifact(stage)
            artifact_safety.publish_file(stage,target)
        return artifact_safety.with_artifacts({'ok':True,'output_path':str(target),
            'metadata':{'native_objects':'byte_identical','chemical_semantics':'unchanged_bytes',
                        'document_chemistry_validation':{'status':'preserved',
                            'method':'byte_identical_copy','scope':'unchanged_bytes',
                            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},
                        'native_render':'not_run','visual_identity':'requires_same_renderer'}},[target])
    # Preserve native trees, including opaque native objects, without redraw.
    if template:
        tree = ET.parse(template)
        root = tree.getroot()
        pages = root.findall('page')
        if len(pages) != 1:
            raise ValueError('Template mode currently requires one page; select/export the target page first')
        page = pages[0]
        before = document_inventory(template)
    else:
        root = ET.Element('CDXML', {'BondLength': '14.4', 'LineWidth': '0.6',
            'BoldWidth': '2', 'HashSpacing': '2.5', 'MarginWidth': '1.6',
            'BondSpacing': '18', 'LabelFont': '3', 'CaptionFont': '3',
            'LabelSize': '10', 'CaptionSize': '10', 'LabelFace': '96'})
        fonts = ET.SubElement(root, 'fonttable')
        ET.SubElement(fonts, 'font', {'id': '3', 'charset': 'iso-8859-1', 'name': 'Arial'})
        page = ET.SubElement(root, 'page', {'id': '1', 'BoundingBox': '0 0 1000 1000'})
        before = None
    expected_inventory = Counter(before or {})
    next_id = max([int(n.get('id')) for n in root.iter() if n.get('id', '').isdigit()] + [1000]) + 1
    def uid():
        nonlocal next_id
        value = str(next_id)
        next_id += 1
        return value
    style = data.get('style', {})
    style_fields = {'font', 'font_size', 'bond_length', 'line_width', 'bold_width', 'hash_spacing', 'margin_width'}
    if set(style) - style_fields:
        raise ValueError('Unknown style field')
    font_size = float(style.get('font_size', root.get('CaptionSize', 10)))
    bond_length = float(style.get('bond_length', root.get('BondLength', 14.4)))
    if not 3 <= font_size <= 72 or not 5 <= bond_length <= 100:
        raise ValueError('font_size 3..72 and bond_length 5..100 points are required')
    for name, attribute in {'font_size':'CaptionSize', 'bond_length':'BondLength',
                           'line_width':'LineWidth', 'bold_width':'BoldWidth',
                           'hash_spacing':'HashSpacing', 'margin_width':'MarginWidth'}.items():
        if name in style:
            value = float(style[name])
            if not math.isfinite(value) or value <= 0:
                raise ValueError('Style measurements must be positive finite numbers')
            root.set(attribute, str(value))
    if 'font_size' in style:
        root.set('LabelSize', str(font_size))
    fonts = root.find('fonttable')
    if fonts is None:
        fonts = ET.SubElement(root, 'fonttable')
    font_id = root.get('CaptionFont', '3')
    if 'font' in style:
        font_id = uid()
        ET.SubElement(fonts, 'font', {'id': font_id, 'charset': 'iso-8859-1', 'name': str(style['font'])})
        root.set('CaptionFont', font_id)
        root.set('LabelFont', font_id)
    colors = root.find('colortable')
    if colors is None:
        colors = ET.SubElement(root, 'colortable')
        ET.SubElement(colors, 'color', {'r':'1','g':'1','b':'1'})
        ET.SubElement(colors, 'color', {'r':'0','g':'0','b':'0'})
    def color(value):
        if not value:
            return '3' if not template else '0'
        v = str(value).lstrip('#')
        if len(v) != 6:
            raise ValueError('Colors must be six-digit RGB hex values')
        rgb = [int(v[i:i+2],16)/255 for i in (0,2,4)]
        ET.SubElement(colors,'color',dict(zip(('r','g','b'),map(str,rgb))))
        return str(len(colors) + 1)
    named, validations, boxes = {}, [], []
    def remember(item, element, bbox=None):
        name = item.get('id')
        if name:
            if name in named:
                raise ValueError(f'Duplicate scene object id: {name}')
            named[name] = element.get('id')
        if bbox:
            boxes.append({'id': name or element.get('id'), 'box': list(bbox)})
    def text(parent, item):
        x,y = _point(item['position'])
        size = float(item.get('size',font_size))
        if not 3 <= size <= 144:
            raise ValueError('Text size must be 3..144 points')
        align = item.get('align','Left')
        if align not in ('Left','Center','Right'):
            raise ValueError('align must be Left, Center, Right')
        node = ET.SubElement(parent,'t',{'id':uid(),'p':f'{x} {y}',
            'Justification':align,'InterpretChemically':'no'})
        runs = item.get('runs',[{'text':item.get('text','')}])
        for run in runs:
            face = sum(bit for key,bit in [('bold',1),('italic',2),('underline',4),('subscript',32),('superscript',64)] if run.get(key))
            if run.get('subscript') and run.get('superscript'):
                raise ValueError('A text run cannot be both subscript and superscript')
            ET.SubElement(node,'s',{'font':font_id,'size':str(size),
                'face':str(face),'color':color(run.get('color',item.get('color')))}).text = str(run.get('text',''))
        full = ''.join(str(r.get('text','')) for r in runs)
        width = max([len(line) for line in full.splitlines()] or [0])*size*.6
        left = x-width/2 if align=='Center' else x-width if align=='Right' else x
        remember(item,node,(left,y-size,left+width,y+size*.3))
        return node
    for edit in data.get('edits',[]):
        if set(edit)-{'id','translate','text','runs','display'}:
            raise ValueError('Template edits support id, translate, text/runs only')
        matches=[n for n in page.iter() if n.get('id')==str(edit['id'])]
        if len(matches)!=1:
            raise ValueError('Template edit needs one exact native object ID')
        node=matches[0]
        if 'display' in edit:
            from .figure_editing import edit_bond_display
            edit_bond_display(node, edit)
            continue
        if node.tag not in ('fragment','group','t','arrow','curve','graphic','bracketedgroup'):
            raise ValueError('Edit whole objects, not individual chemical atoms/bonds')
        if 'translate' in edit:
            _move(node,*_point(edit['translate']))
        if 'text' in edit or 'runs' in edit:
            if node.tag!='t' or any(node is t for atom in page.iter('n') for t in atom.iter('t')):
                raise ValueError('Text edits are restricted to non-atom annotations')
            pos=list(map(float,node.get('p').split()))
            replacement=text(ET.Element('tmp'),{**edit,'position':pos})
            for child in list(node): node.remove(child)
            for child in list(replacement): node.append(child)
    if data.get('crossings'):
        from .figure_editing import apply_crossings
        apply_crossings(page, data['crossings'])
    for item in objects:
        kind=item.get('type')
        fields={
            'molecule':{'smiles','molblock','file','fragment_index','position','coordinates','rotation','label',
                        'preserve_coordinates','align_to','alignment_mode','bond_length','cip_labels','atom_numbers',
                        'annotation_offsets','highlight_atoms','highlight_bonds','highlight_color','color','bond_displays'},
            'text':{'position','text','runs','size','align','color'},
            'arrow':{'start','end','style','color'},'line':{'start','end','style','color'},
            'curve':{'points','color'},'electron_arrow':{'points','color','electrons'},
            'symbol':{'start','end','symbol','color'},
            'rectangle':{'start','end','color'},'ellipse':{'start','end','color'},'bracket':{'start','end','color','label'}}
        unknown=set(item)-fields.get(kind,set())-{'type','id'}
        if unknown: raise ValueError(f'Unknown {kind} object fields: {sorted(unknown)}')
        if kind=='molecule':
            record=dict(item)
            if record.get('file'): record['file']=str(local_path(record['file']))
            mol=_mol(record)
            expected_inventory.update(semantic_key(m) for m in Chem.GetMolFrags(mol, asMols=True))
            source=Chem.MolToCXSmiles(mol)
            if item.get('coordinates') is not None:
                coords=item['coordinates']
                if len(coords)!=mol.GetNumAtoms():
                    raise ValueError('Exact coordinates require one point per input atom')
                conf=Chem.Conformer(mol.GetNumAtoms())
                for i,xy in enumerate(coords):
                    x,y=_point(xy); conf.SetAtomPosition(i,(x,-y,0))
                mol.RemoveAllConformers(); mol.AddConformer(conf)
                absolute=True
            else:
                absolute=False
                if item.get('align_to'):
                    reference_record=dict(item['align_to'])
                    if reference_record.get('file'): reference_record['file']=str(local_path(reference_record['file']))
                    reference=_mol(reference_record)
                    if not reference.GetNumConformers(): rdDepictor.Compute2DCoords(reference)
                    params=rdDepictor.ConstrainedDepictionParams()
                    params.acceptFailure=False
                    params.adjustMolBlockWedging=True
                    if item.get('alignment_mode','substructure')=='mcs':
                        from rdkit.Chem import rdFMCS
                        mcs=rdFMCS.FindMCS([reference,mol],timeout=10,ringMatchesRingOnly=True,completeRingsOnly=True)
                        if mcs.canceled or mcs.numAtoms<3: raise ValueError('No validated MCS alignment core')
                        query=Chem.MolFromSmarts(mcs.smartsString)
                        atom_map=list(zip(reference.GetSubstructMatch(query),mol.GetSubstructMatch(query)))
                        rdDepictor.GenerateDepictionMatching2DStructure(mol,reference,atomMap=atom_map,params=params)
                    else:
                        rdDepictor.GenerateDepictionMatching2DStructure(mol,reference,params=params)
                elif item.get('preserve_coordinates') and mol.GetNumConformers():
                    pass
                else:
                    rdDepictor.Compute2DCoords(mol,useRingTemplates=True)
            Chem.Kekulize(mol,clearAromaticFlags=True)
            atoms,bonds=_rdkit_mol_to_atom_bond_dicts(mol)
            angle=math.radians(float(item.get('rotation',0)))
            cx=sum(a['x'] for a in atoms)/len(atoms); cy=sum(a['y'] for a in atoms)/len(atoms)
            px,py=_point(item.get('position',[100,100]))
            local_bond_length=float(item.get('bond_length',bond_length))
            if not 5 <= local_bond_length <= 100:
                raise ValueError('Molecule bond_length must be 5..100 points')
            scale=local_bond_length/1.5
            for a in atoms:
                if absolute:
                    a['y']=-a['y']
                else:
                    x,y=a['x']-cx,a['y']-cy
                    a['x']=px+scale*(x*math.cos(angle)-y*math.sin(angle))
                    a['y']=py-scale*(x*math.sin(angle)+y*math.cos(angle))
            # Allocate atom/bond IDs from the same document namespace.
            gen=_IDGen(start=next_id)
            fragment_xml,atom_map,fragment_id=_build_fragment(atoms,bonds,gen)
            fragment=ET.fromstring(fragment_xml)
            next_id=max(int(n.get('id')) for n in fragment.iter() if n.get('id'))+1
            for run in fragment.iter('s'):
                run.set('font',font_id); run.set('size',str(font_size))
            for index,display in item.get('bond_displays',{}).items():
                if int(index) not in range(mol.GetNumBonds()): raise ValueError('Invalid bond display index')
                if display not in ('None','WedgeBegin','WedgeEnd','WedgedHashBegin','WedgedHashEnd','Wavy','Bold','Dash'):
                    raise ValueError('Unsupported bond display')
                bond=fragment.findall('b')[int(index)]
                if display=='None': bond.attrib.pop('Display',None)
                else: bond.set('Display',display)
            fragment.set('color', color(item.get('color')))
            for run in fragment.iter('s'):
                run.set('color',color(item.get('color')))
            page.append(fragment)
            validations.append(validate_fragment(source,ET.tostring(fragment,encoding='unicode')))
            xx=[a['x'] for a in atoms]; yy=[a['y'] for a in atoms]
            remember(item,fragment,(min(xx)-font_size/2,min(yy)-font_size,max(xx)+font_size/2,max(yy)+font_size/2))
            highlight=color(item.get('highlight_color','#cc3333')) if item.get('highlight_atoms') else None
            for i in item.get('highlight_atoms',[]):
                if int(i) not in range(len(atoms)): raise ValueError('Invalid highlight atom index')
                atom_node=fragment.find(f"n[@id='{atom_map[int(i)+1]}']")
                atom_node.set('color',highlight)
                for run in atom_node.iter('s'): run.set('color',highlight)
                # Carbon has no visible atom glyph: a halo still shows the selection.
                a=atoms[int(i)]; x,y=a['x'],a['y']; radius=font_size*.7
                ET.SubElement(page,'graphic',{'id':uid(),'GraphicType':'Oval','OvalType':'Circle',
                    'BoundingBox':f'{x-radius} {y-radius} {x+radius} {y+radius}',
                    'Center3D':f'{x} {y} 0','MajorAxisEnd3D':f'{x+radius} {y} 0',
                    'MinorAxisEnd3D':f'{x} {y+radius} 0','color':highlight})
            for i in item.get('highlight_bonds',[]):
                if int(i) not in range(mol.GetNumBonds()): raise ValueError('Invalid highlight bond index')
                fragment.findall('b')[int(i)].set('color',color(item.get('highlight_color','#cc3333')))
            rdCIPLabeler.AssignCIPLabels(mol)
            for i,a in enumerate(atoms):
                labels=[]
                if item.get('atom_numbers'): labels.append(str(i))
                atom=mol.GetAtomWithIdx(i)
                if item.get('cip_labels') and atom.HasProp('_CIPCode'): labels.append(atom.GetProp('_CIPCode'))
                if labels:
                    vx,vy=a['x']-sum(xx)/len(xx),a['y']-sum(yy)/len(yy)
                    norm=math.hypot(vx,vy) or 1
                    ox,oy=vx/norm*13,vy/norm*13
                    override=item.get('annotation_offsets',{}).get(str(i))
                    if override is not None: ox,oy=_point(override)
                    text(page,{'position':[a['x']+ox,a['y']+oy],'text':','.join(labels),
                               'align':'Center','size':max(5,font_size*.7)})
            if item.get('label'):
                text(page,{'position':[(min(xx)+max(xx))/2,max(yy)+font_size+12],
                           'text':item['label'],'align':'Center'})
        elif kind=='text':
            text(page,item)
        elif kind in ('arrow','line'):
            start,end=_point(item['start']),_point(item['end'])
            style_name=item.get('style','forward' if kind=='arrow' else 'line')
            if style_name not in ('forward','line','dashed','failed','resonance','equilibrium','retro'):
                raise ValueError('Unsupported straight arrow style')
            def arrow(a,b,half=False):
                node=ET.SubElement(page,'arrow',{'id':uid(),'Tail3D':f'{a[0]} {a[1]} 0',
                    'Head3D':f'{b[0]} {b[1]} 0','ArrowheadHead':'HalfLeft' if half else 'Full',
                    'ArrowheadType':'Solid','HeadSize':'1000','ArrowheadWidth':'250',
                    'FillType':'None','LineWidth':root.get('LineWidth','0.6'),'color':color(item.get('color'))})
                return node
            node=arrow(start,end,style_name=='equilibrium')
            if style_name=='line': node.set('ArrowheadHead','None')
            if style_name=='dashed': node.set('LineType','Dashed')
            if style_name=='failed': node.set('NoGo','Cross')
            if style_name=='resonance': node.set('ArrowheadTail','Full')
            if style_name=='retro':
                node.set('ArrowShaftSpacing','300')
                node.set('ArrowheadType','Angle')
                node.set('LineType','Double')
            if style_name=='equilibrium':
                dx,dy=end[0]-start[0],end[1]-start[1]; length=math.hypot(dx,dy)
                if length==0: raise ValueError('Arrow length must be nonzero')
                sx,sy=-dy/length*4,dx/length*4
                arrow((end[0]+sx,end[1]+sy),(start[0]+sx,start[1]+sy),True)
            remember(item,node)
        elif kind in ('curve','electron_arrow'):
            points=[_point(x) for x in item['points']]
            if len(points)!=4: raise ValueError('Cubic curves require four Bezier points')
            # ChemDraw stores incoming handle, first anchor, outgoing handle,
            # incoming handle, last anchor, outgoing handle (3 points per anchor).
            native_points=[points[0],*points,points[-1]]
            node=ET.SubElement(page,'curve',{'id':uid(),'CurvePoints':' '.join(f'{x} {y}' for x,y in native_points),
                'FillType':'None','LineWidth':root.get('LineWidth','0.6'),'color':color(item.get('color'))})
            if kind=='electron_arrow':
                node.set('ArrowheadHead','HalfLeft' if item.get('electrons',2)==1 else 'Full')
                node.set('ArrowheadType','Solid')
            remember(item,node)
        elif kind=='symbol':
            symbol=item['symbol']
            if symbol not in ('LonePair','Electron','RadicalCation','RadicalAnion','CirclePlus','CircleMinus','Dagger','DoubleDagger','Plus','Minus'):
                raise ValueError('Unsupported native symbol')
            x1,y1=_point(item['start']);x2,y2=_point(item['end'])
            if x2<=x1 or y2<=y1:raise ValueError('Symbol end must be below/right of start')
            node=ET.SubElement(page,'graphic',{'id':uid(),'GraphicType':'Symbol','SymbolType':symbol,
                'BoundingBox':f'{x1} {y1} {x2} {y2}','color':color(item.get('color'))})
            remember(item,node)
        elif kind in ('rectangle','ellipse','bracket'):
            x1,y1=_point(item['start']); x2,y2=_point(item['end'])
            if x2<=x1 or y2<=y1: raise ValueError('Shape end must be below/right of start')
            if kind=='bracket':
                node=ET.SubElement(page,'group',{'id':uid(),'color':color(item.get('color'))})
                for x,sign in ((x1,1),(x2,-1)):
                    for a,b in [((x,y1),(x,y2)),((x,y1),(x+5*sign,y1)),((x,y2),(x+5*sign,y2))]:
                        ET.SubElement(node,'graphic',{'id':uid(),'GraphicType':'Line',
                            'color':color(item.get('color')),'BoundingBox':f'{a[0]} {a[1]} {b[0]} {b[1]}'})
                if item.get('label'): text(page,{'position':[x2+3,y2],'text':item['label']})
            else:
                node=ET.SubElement(page,'graphic',{'id':uid(),'GraphicType':'Oval' if kind=='ellipse' else 'Rectangle',
                    'BoundingBox':f'{x1} {y1} {x2} {y2}','color':color(item.get('color'))})
                if kind=='ellipse':
                    cx,cy=(x1+x2)/2,(y1+y2)/2
                    node.set('Center3D',f'{cx} {cy} 0')
                    node.set('MajorAxisEnd3D',f'{x2} {cy} 0')
                    node.set('MinorAxisEnd3D',f'{cx} {y2} 0')
            remember(item,node)
        else:
            raise ValueError(f'Unsupported object type: {kind}')
    if data.get('steps'):
        scheme=ET.SubElement(page,'scheme',{'id':uid()})
        for step in data['steps']:
            attrs={'id':uid()}
            for field,attr in [('reactants','ReactionStepReactants'),('products','ReactionStepProducts'),
                ('arrows','ReactionStepArrows'),('above','ReactionStepObjectsAboveArrow'),('below','ReactionStepObjectsBelowArrow')]:
                if step.get(field): attrs[attr]=' '.join(named[n] for n in step[field])
            ET.SubElement(scheme,'step',attrs)
    # Only detect large component overlaps; atom labels intentionally overlap bonds.
    collisions=[]
    for i,a in enumerate(boxes):
        for b in boxes[i+1:]:
            ax,ay,az,aw=a['box']; bx,by,bz,bw=b['box']
            if min(az,bz)-max(ax,bx)>1 and min(aw,bw)-max(ay,by)>1:
                collisions.append([a['id'],b['id']])
    target=artifact_safety.resolve_destination(source=template,output_path=output_path,tag='figure',suffix='.cdxml')
    with artifact_safety.staging_file(target) as stage:
        ET.indent(root)
        ET.ElementTree(root).write(stage,encoding='utf-8',xml_declaration=True)
        artifact_safety.validate_artifact(stage)
        serialized = ET.parse(stage)
        after = document_inventory(stage) if serialized.find('.//fragment') is not None else Counter()
        if after != expected_inventory:
            raise ValueError('chemical_semantics_changed: final document inventory differs from template plus inputs')
        document_validation = {'status':'preserved', 'method':'final_cdxml_roundtrip',
            'scope':'rdkit_readback_consistency', 'molecules':sum(after.values()),
            'sha256':hashlib.sha256(stage.read_bytes()).hexdigest()}
        artifact_safety.publish_file(stage,target)
    return artifact_safety.with_artifacts({'ok':True,'output_path':str(target),
        'metadata':{'chemistry_validation':validations,'document_chemistry_validation':document_validation,'native_render':'not_run',
                    'visual_identity':'not_evaluated','component_overlap_candidates':collisions,
                    'object_ids':named},
        'warnings':['Inspect overlap candidates and native rendering before acceptance.'] if collisions else []},[target])


def compare_figure_images(reference_path: str, candidate_path: str, output_path: str) -> dict:
    """Compare aligned local raster previews without resizing or warping.

    Output JSON contains exact pixel equality, normalized mean absolute error,
    ink intersection-over-union, and dimensions. Different dimensions explicitly
    fail comparison. This evaluates appearance only, never chemical identity.
    """
    import numpy as np
    from PIL import Image
    def pixels(path):
        with Image.open(path) as image:
            rgba=image.convert('RGBA')
            background=Image.new('RGBA',rgba.size,'white')
            return np.asarray(Image.alpha_composite(background,rgba).convert('RGB')).copy()
    a,b=pixels(reference_path),pixels(candidate_path)
    result={'reference_dimensions':[a.shape[1],a.shape[0]],'candidate_dimensions':[b.shape[1],b.shape[0]],
            'same_dimensions':a.shape==b.shape,'chemical_identity':'not_evaluated'}
    if a.shape==b.shape:
        delta=np.abs(a.astype(float)-b.astype(float))
        ia=np.min(a,axis=2)<240; ib=np.min(b,axis=2)<240
        union=np.logical_or(ia,ib).sum()
        result.update(exact_pixels=bool(np.array_equal(a,b)),normalized_mae=float(delta.mean()/255),
            ink_iou=float(np.logical_and(ia,ib).sum()/union) if union else 1.0)
    return _publish({'operation':'compare_images','results':[result]},output_path)


FIGURE_TOOLS={f.__name__:f for f in (rdkit_workbench,compose_chemical_figure,compare_figure_images)}


def main(argv=None):
    import argparse
    from .figure_validation import validate_figure
    cli_tools = {**FIGURE_TOOLS, 'validate_figure': validate_figure}
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool',choices=sorted(cli_tools))
    parser.add_argument('--arguments',type=Path,required=True,help='JSON keyword arguments file')
    args=parser.parse_args(argv)
    try:
        result=cli_tools[args.tool](**json.loads(args.arguments.read_text(encoding='utf-8-sig')))
    except Exception as exc:
        print(json.dumps({'ok':False,'error':{'type':type(exc).__name__,'message':str(exc)}},ensure_ascii=False))
        return 1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
