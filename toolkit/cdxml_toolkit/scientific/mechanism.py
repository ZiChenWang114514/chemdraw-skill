"""Compile explicit electron-flow annotations anchored to grounded structures."""
from copy import deepcopy
from collections import Counter
from rdkit import Chem
from .common import point


def validate_mechanism_steps(steps, molecules):
    """Check fully specified equations; partial illustrations stay explicitly unchecked."""
    reports=[]
    def inventory(names):
        atoms=Counter();charge=0
        if not isinstance(names,list) or not names:raise ValueError('A complete step needs nonempty species lists')
        for name in names:
            if name not in molecules:raise ValueError(f'Unknown step molecule: {name}')
            mol=Chem.AddHs(molecules[name])
            if any(a.GetAtomicNum()==0 for a in mol.GetAtoms()):raise ValueError('Expand variable groups before checking a complete step')
            atoms.update((a.GetAtomicNum(),a.GetIsotope()) for a in mol.GetAtoms())
            charge+=sum(a.GetFormalCharge() for a in mol.GetAtoms())
        return atoms,charge
    for index,step in enumerate(steps):
        complete=step.get('complete',False)
        if type(complete) is not bool:raise ValueError('Step completeness must be true or false')
        if not complete:
            reports.append({'step':index,'status':'not_checked_incomplete_step'});continue
        left,lcharge=inventory(step.get('reactants'));right,rcharge=inventory(step.get('products'))
        delta={f'{Chem.GetPeriodicTable().GetElementSymbol(z)}:{isotope}':right[z,isotope]-left[z,isotope]
               for z,isotope in sorted(left.keys()|right.keys()) if right[z,isotope]!=left[z,isotope]}
        if delta or rcharge!=lcharge:
            raise ValueError(f'Complete step {index} is not balanced: isotope/element delta {delta}; charge delta {rcharge-lcharge}')
        reports.append({'step':index,'status':'balanced','atom_count':sum(left.values()),'formal_charge':lcharge,
                        'scope':'Element, isotope and charge conservation only; not mechanistic proof'})
    return reports


def compile_mechanism(spec, *, checks=None):
    objects=deepcopy(spec.get('objects',[]))
    molecules={}
    for obj in objects:
        if obj.get('type')!='molecule':continue
        ident=obj['id']
        if ident in molecules:raise ValueError('Molecule IDs must be unique')
        if obj.get('file'):
            from ..mcp_runtime.figure_tools import _mol
            mol=_mol(obj)
        else:mol=Chem.MolFromSmiles(obj.get('smiles',''))
        if mol is None or not mol.GetNumAtoms():raise ValueError('Grounded molecule required')
        coordinates=[point(p) for p in obj.get('coordinates',[])]
        if len(coordinates)!=mol.GetNumAtoms():raise ValueError('Mechanism anchors require one explicit coordinate per atom')
        molecules[ident]=(mol,coordinates)
    reports=validate_mechanism_steps(spec.get('steps',[]),{name:entry[0] for name,entry in molecules.items()})
    if checks is not None:checks.extend(reports)
    def anchor(record):
        ident=record['molecule']
        if ident not in molecules:raise ValueError(f'Unknown molecule: {ident}')
        mol,coords=molecules[ident]
        if ('atom' in record)==('bond' in record):raise ValueError('Anchor needs exactly one atom or bond')
        indices=[record['atom']] if 'atom' in record else record['bond']
        if len(indices) not in (1,2) or any(not isinstance(i,int) or isinstance(i,bool) or not 0<=i<len(coords) for i in indices):
            raise ValueError('Invalid anchor atom indices')
        if 'bond' in record and (len(indices)!=2 or mol.GetBondBetweenAtoms(*indices) is None):
            raise ValueError('Anchor bond does not exist in the source molecule')
        offset=point(record.get('offset',[0,0]))
        return [sum(coords[i][axis] for i in indices)/len(indices)+offset[axis] for axis in range(2)]
    arrows=spec.get('electron_arrows',[])
    if len(arrows)>200:raise ValueError('At most 200 electron arrows')
    for idx,arrow in enumerate(arrows):
        electrons=arrow.get('electrons',2)
        if type(electrons) is not int or electrons not in (1,2):raise ValueError('Electron count must be 1 or 2')
        controls=[point(p) for p in arrow['controls']]
        if len(controls)!=2:raise ValueError('Supply exactly two Bezier control points')
        objects.append({'type':'electron_arrow','id':f'electron-flow-{idx}',
            'points':[anchor(arrow['source']),*map(list,controls),anchor(arrow['target'])],'electrons':electrons})
    result={'version':1,'objects':objects}
    for key in ('style','steps'):
        if key in spec:result[key]=deepcopy(spec[key])
    for step in result.get('steps',[]):step.pop('complete',None)
    return result
