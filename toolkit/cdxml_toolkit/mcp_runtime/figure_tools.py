"""Editable fixed-layout chemical figures and bounded RDKit analysis tools."""
from __future__ import annotations

import json
import math
import hashlib
from collections import Counter
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

from rdkit import Chem
from rdkit.Chem import AllChem, rdCIPLabeler, rdDepictor

from ..chemistry_semantics import semantic_key, validate_fragment, document_inventory, read_molecules
from ..vision import stereo_audit
from . import artifact_safety


JACS_PALETTE = {
    'pastel_blue': '#D6EAF8',
    'pastel_red': '#FADBD8',
    'pastel_green': '#D5F5E3',
    'pastel_yellow': '#FCF3CF',
    'pastel_purple': '#E8DAEF',
    'pastel_orange': '#FDEBD0',
    'pastel_teal': '#D1F2EB',
    'jacs_blue': '#005AB5',
    'jacs_red': '#DC3220',
    'jacs_green': '#008060',
    'jacs_purple': '#6A3D9A',
    'white': '#FFFFFF',
    'black': '#000000',
    'red': '#DC3220',
    'blue': '#005AB5',
    'green': '#008060',
    'purple': '#6A3D9A',
    'yellow': '#FCF3CF',
    'orange': '#FDEBD0',
    'teal': '#D1F2EB',
    'gray': '#808080',
    'grey': '#808080',
}


def _publish(data, output_path):
    target = artifact_safety.resolve_destination(
        source=None, output_path=output_path, tag='rdkit', suffix='.json'
    )
    with artifact_safety.staging_file(target) as stage:
        stage.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        artifact_safety.publish_file(stage, target)
    out = {
        'ok': data.get('ok', True),
        'output_path': str(target),
        'operation': data.get('operation'),
        'count': len(data.get('results', [])),
        'results': data.get('results', []),
        'warnings': data.get('warnings', []),
        'checkpoints': data.get('checkpoints', []),
    }
    for extra_key in ('smiles', 'canonical_smiles', 'cip_labels', 'products', 'diagnosis', 'error'):
        if extra_key in data:
            out[extra_key] = data[extra_key]
    return artifact_safety.with_artifacts(out, [target])


def _mol(record):
    if record.get('molblock'):
        mol = Chem.MolFromMolBlock(record['molblock'], removeHs=False)
    elif record.get('file'):
        path = Path(record['file']).expanduser().resolve()
        if path.suffix.lower() == '.cdxml':
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
    canon_smi = Chem.MolToSmiles(mol)
    return {
        'smiles': Chem.MolToCXSmiles(mol),
        'canonical_smiles': canon_smi,
        'semantic_key': semantic_key(mol),
        'formula': rdMolDescriptors.CalcMolFormula(mol),
        'mw': Descriptors.MolWt(mol),
        'exact_mass': Descriptors.ExactMolWt(mol),
        'atoms': [
            {
                'index': a.GetIdx(),
                'element': a.GetSymbol(),
                'cip': a.GetProp('_CIPCode') if a.HasProp('_CIPCode') else None,
                'isotope': a.GetIsotope(),
                'charge': a.GetFormalCharge(),
                'map_number': a.GetAtomMapNum(),
            }
            for a in mol.GetAtoms()
        ],
        'potential_stereo': [
            {
                'type': str(s.type),
                'center': s.centeredOn,
                'specified': str(s.specified),
            }
            for s in Chem.FindPotentialStereo(mol)
        ],
        'stereo_groups': [
            {
                'type': str(g.GetGroupType()),
                'atoms': [a.GetIdx() for a in g.GetAtoms()],
            }
            for g in mol.GetStereoGroups()
        ],
        'checkpoints': stereo_audit.visual_checkpoints(canon_smi),
    }


def _curve_points_for_ring(ring_pts: list[tuple[float, float]], style: str = 'polygon', inset: float = 0.0) -> str:
    n = len(ring_pts)
    if n == 0:
        return ''
    rcx = sum(p[0] for p in ring_pts) / n
    rcy = sum(p[1] for p in ring_pts) / n
    adjusted: list[tuple[float, float]] = []
    for px, py in ring_pts:
        dx, dy = rcx - px, rcy - py
        dist = math.hypot(dx, dy)
        if inset and dist > 1e-6:
            step = min(float(inset), dist * 0.45)
            px += (dx / dist) * step
            py += (dy / dist) * step
        adjusted.append((px, py))
    if style == 'spline' and n >= 3:
        ctrl: list[tuple[float, float]] = []
        for i in range(n):
            p_prev = adjusted[(i - 1) % n]
            p_curr = adjusted[i]
            p_next = adjusted[(i + 1) % n]
            tx = (p_next[0] - p_prev[0]) * 0.16
            ty = (p_next[1] - p_prev[1]) * 0.16
            ctrl.extend([(p_curr[0] - tx, p_curr[1] - ty), p_curr, (p_curr[0] + tx, p_curr[1] + ty)])
        return ' '.join(f'{x:.2f} {y:.2f}' for x, y in ctrl)
    poly = [q for p in adjusted for q in (p, p, p)]
    return ' '.join(f'{x:.2f} {y:.2f}' for x, y in poly)


def rdkit_workbench(
    molecules: list[dict] | str | None = None,
    operation: str = 'inspect',
    options: dict | None = None,
    output_path: str | None = None,
    **kwargs,
) -> dict:
    """Analyze and edit grounded molecules: inspect, stereoisomers, tautomers, mcs,
    r_groups, set_stereo, edit_structure, edit_smarts, read_wedges, depict_like,
    enumerate_markush.
    """
    allowed_option_keys = {
        'max_results',
        'only_unassigned',
        'include_molblock',
        'timeout',
        'configurations',
        'set_atom',
        'set_bond',
        'add_group',
        'remove_atoms',
        'set_ez',
        'set_stereo',
        'ops',
        'edit_smarts',
        'smarts',
        'wedges',
        'positions',
        'reference_image',
        'reference_image_path',
        'annotate_indices',
        'size',
        'image_output_path',
        'r_groups',
        'r_groups_by_label',
        'core_smiles',
    }
    unknown_kwargs = set(kwargs) - allowed_option_keys - {'smiles'}
    if unknown_kwargs:
        raise ValueError(f'Unknown arguments: {sorted(unknown_kwargs)}')

    options = dict(options or {})
    for k, v in kwargs.items():
        if k in allowed_option_keys and k not in options:
            options[k] = v

    if molecules is None:
        raw_smi = kwargs.get('smiles') or options.get('core_smiles')
        if raw_smi is not None:
            molecules = [{'smiles': raw_smi}]
        else:
            raise ValueError('Provide 1..128 grounded molecules')
    elif isinstance(molecules, str):
        molecules = [{'smiles': molecules}]
    elif isinstance(molecules, dict):
        molecules = [molecules]
    elif isinstance(molecules, list):
        molecules = [{'smiles': m} if isinstance(m, str) else dict(m) for m in molecules]

    if not 1 <= len(molecules) <= 128:
        raise ValueError('Provide 1..128 grounded molecules')

    for rec in molecules:
        for k in allowed_option_keys:
            if k in rec and k not in options:
                options[k] = rec[k]

    unknown = set(options) - allowed_option_keys
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')

    limit = int(options.get('max_results', 32))
    if not 1 <= limit <= 128:
        raise ValueError('max_results must be 1..128')

    edit_keys = ('set_atom', 'set_bond', 'add_group', 'remove_atoms', 'set_ez', 'ops')
    if operation == 'inspect':
        if any(options.get(k) is not None for k in edit_keys):
            operation = 'edit_structure'
        elif options.get('edit_smarts') or options.get('smarts'):
            operation = 'edit_smarts'
        elif options.get('wedges') is not None:
            operation = 'read_wedges'
        elif options.get('reference_image') or options.get('reference_image_path'):
            operation = 'depict_like'
        elif options.get('r_groups') is not None or options.get('r_groups_by_label') is not None:
            operation = 'enumerate_markush'

    # Check SMILES validity upfront and return diagnose_smiles_error on invalid SMILES
    for rec in molecules:
        if not rec.get('molblock') and not rec.get('file') and 'smiles' in rec:
            raw_smiles = str(rec.get('smiles') or '')
            parsed = Chem.MolFromSmiles(raw_smiles) if raw_smiles else None
            if parsed is None or parsed.GetNumAtoms() == 0:
                diag = stereo_audit.diagnose_smiles_error(raw_smiles)
                err_data = {
                    'ok': False,
                    'valid': False,
                    'operation': operation,
                    'diagnosis': str(diag),
                    'error': {
                        'type': 'SmilesParseError',
                        'message': str(diag),
                        'diagnosis': diag.to_dict(),
                    },
                    'results': [
                        {
                            'valid': False,
                            'smiles': raw_smiles,
                            'error': str(diag),
                            'diagnosis': diag.to_dict(),
                            'checkpoints': [],
                        }
                    ],
                    'warnings': [str(diag)],
                    'checkpoints': [],
                }
                if output_path is not None:
                    return _publish(err_data, output_path)
                return err_data

    mols = [_mol(m) for m in molecules]
    results, warnings = [], []
    extra_top: dict = {}

    if operation == 'inspect':
        results = [_descriptor(m) for m in mols]
    elif operation == 'stereoisomers':
        from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions
        for i, mol in enumerate(mols):
            opts = StereoEnumerationOptions(
                onlyUnassigned=bool(options.get('only_unassigned', True)),
                maxIsomers=limit + 1,
                unique=True,
                rand=0,
            )
            candidates = list(EnumerateStereoisomers(mol, options=opts))
            results.append({
                'input_index': i,
                'truncated': len(candidates) > limit,
                'candidates': [_descriptor(m) for m in candidates[:limit]],
            })
        warnings.append('Enumeration does not establish stereoisomer abundance or accessibility.')
    elif operation == 'tautomers':
        from rdkit.Chem.MolStandardize import rdMolStandardize
        for i, mol in enumerate(mols):
            enumerator = rdMolStandardize.TautomerEnumerator()
            enumerator.SetMaxTautomers(limit + 1)
            enumerator.SetMaxTransforms(1000)
            candidates = enumerator.Enumerate(mol)
            results.append({
                'input_index': i,
                'status': str(candidates.status),
                'truncated': len(candidates) > limit or str(candidates.status) != 'Completed',
                'candidates': [_descriptor(m) for m in list(candidates)[:limit]],
            })
        warnings.append('Tautomer candidates are not a pH-dependent equilibrium prediction; stereo may change.')
    elif operation == 'mcs':
        from rdkit.Chem import rdFMCS
        if len(mols) < 2:
            raise ValueError('MCS needs at least two molecules')
        timeout = int(options.get('timeout', 10))
        if not 1 <= timeout <= 30:
            raise ValueError('timeout must be 1..30 seconds')
        mcs = rdFMCS.FindMCS(
            mols,
            timeout=timeout,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            matchChiralTag=True,
        )
        query = Chem.MolFromSmarts(mcs.smartsString)
        results = [{
            'smarts': mcs.smartsString,
            'atoms': mcs.numAtoms,
            'bonds': mcs.numBonds,
            'timed_out': mcs.canceled,
            'matches': [list(m.GetSubstructMatch(query)) if query else [] for m in mols],
        }]
    elif operation == 'set_stereo' and options.get('configurations') and not any(options.get(k) for k in edit_keys):
        if len(mols) != 1 or not options.get('configurations'):
            raise ValueError('set_stereo requires one molecule and explicit configurations')
        source = mols[0]
        changed = Chem.Mol(source)
        if source.GetStereoGroups():
            raise ValueError('set_stereo on enhanced stereo groups needs explicit group-aware editing')
        potential_centers = {
            int(info.centeredOn)
            for info in Chem.FindPotentialStereo(source)
            if str(info.type) == 'Atom_Tetrahedral'
        }
        diff = []
        for raw_index, target in options['configurations'].items():
            index = int(raw_index)
            if index not in range(changed.GetNumAtoms()) or target not in ('R', 'S', 'unspecified'):
                raise ValueError('Specify a valid zero-based atom index and R, S, or unspecified')
            atom = changed.GetAtomWithIdx(index)
            rdCIPLabeler.AssignCIPLabels(changed)
            old = atom.GetProp('_CIPCode') if atom.HasProp('_CIPCode') else None
            if target == 'unspecified':
                atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
                if atom.HasProp('_CIPCode'):
                    atom.ClearProp('_CIPCode')
            else:
                if index not in potential_centers:
                    raise ValueError('Atom is not a potential tetrahedral stereocenter')
                if atom.GetDegree() not in (3, 4):
                    raise ValueError('Not a tetrahedral center')
                atom.SetChiralTag(Chem.ChiralType.CHI_TETRAHEDRAL_CW)
                if atom.HasProp('_CIPCode'):
                    atom.ClearProp('_CIPCode')
                rdCIPLabeler.AssignCIPLabels(changed)
                if not atom.HasProp('_CIPCode'):
                    raise ValueError('CIP could not be assigned to this atom')
                if atom.GetProp('_CIPCode') != target:
                    atom.InvertChirality()
                    atom.ClearProp('_CIPCode')
                    rdCIPLabeler.AssignCIPLabels(changed)
                if atom.GetProp('_CIPCode') != target:
                    raise ValueError('Requested CIP configuration was not achieved')
            diff.append({'atom_index': index, 'before': old, 'after': target})
        a, b = Chem.Mol(source), Chem.Mol(changed)
        Chem.RemoveStereochemistry(a)
        Chem.RemoveStereochemistry(b)
        if semantic_key(a) != semantic_key(b):
            raise ValueError('Unexpected connectivity change')
        for raw_index, target in options['configurations'].items():
            atom = changed.GetAtomWithIdx(int(raw_index))
            if target != 'unspecified' and atom.GetProp('_CIPCode') != target:
                raise ValueError('A coupled stereocenter changed an earlier CIP assignment')
        results = [{**_descriptor(changed), 'diff': diff, 'connectivity_preserved': True}]
    elif operation in ('edit_structure', 'set_stereo'):
        if len(mols) != 1:
            raise ValueError('edit_structure requires one molecule')
        raw_smi = molecules[0].get('smiles') or Chem.MolToSmiles(mols[0])
        if options.get('edit_smarts') or options.get('smarts'):
            rxn_smarts = str(options.get('edit_smarts') or options.get('smarts'))
            rxn = AllChem.ReactionFromSmarts(rxn_smarts)
            if rxn is None:
                raise ValueError(f'Invalid reaction SMARTS: {rxn_smarts}')
            prods = rxn.RunReactants((mols[0],))
            if not prods or not prods[0]:
                raise ValueError('edit_smarts did not match the input molecule')
            edited_mol = Chem.Mol(prods[0][0])
            Chem.SanitizeMol(edited_mol)
            raw_smi = Chem.MolToSmiles(edited_mol)
        has_struct_ops = any(
            options.get(k) is not None
            for k in ('ops', 'set_atom', 'set_bond', 'add_group', 'remove_atoms', 'set_ez', 'set_stereo', 'configurations')
        )
        if has_struct_ops:
            stereo_arg = options.get('set_stereo')
            if stereo_arg is None and options.get('configurations'):
                stereo_arg = options['configurations']
            edited_smi = stereo_audit.edit_structure(
                raw_smi,
                ops=options.get('ops'),
                set_atom=options.get('set_atom'),
                set_bond=options.get('set_bond'),
                add_group=options.get('add_group'),
                remove_atoms=options.get('remove_atoms'),
                set_ez=options.get('set_ez'),
                set_stereo=stereo_arg,
            )
            raw_smi = str(edited_smi)
        edited_mol = Chem.MolFromSmiles(raw_smi)
        desc = _descriptor(edited_mol)
        desc['smiles'] = str(raw_smi)
        desc['canonical_smiles'] = str(raw_smi)
        results = [desc]
        extra_top['smiles'] = str(raw_smi)
        extra_top['canonical_smiles'] = str(raw_smi)
    elif operation == 'edit_smarts':
        if len(mols) != 1:
            raise ValueError('edit_smarts requires one molecule')
        rxn_smarts = str(options.get('edit_smarts') or options.get('smarts') or '')
        if not rxn_smarts:
            raise ValueError('edit_smarts requires a reaction SMARTS string')
        rxn = AllChem.ReactionFromSmarts(rxn_smarts)
        if rxn is None:
            raise ValueError(f'Invalid reaction SMARTS: {rxn_smarts}')
        prods = rxn.RunReactants((mols[0],))
        if not prods or not prods[0]:
            raise ValueError('edit_smarts did not match the input molecule')
        edited_mol = Chem.Mol(prods[0][0])
        Chem.SanitizeMol(edited_mol)
        canon = Chem.MolToSmiles(edited_mol)
        desc = _descriptor(edited_mol)
        desc['smiles'] = canon
        results = [desc]
        extra_top['smiles'] = canon
    elif operation == 'read_wedges':
        if len(mols) != 1:
            raise ValueError('read_wedges requires one molecule')
        raw_smi = molecules[0].get('smiles') or Chem.MolToSmiles(mols[0])
        wedges = options.get('wedges')
        if not wedges:
            raise ValueError('read_wedges requires a non-empty wedges list')
        rw_res = stereo_audit.read_wedges(raw_smi, wedges, positions=options.get('positions'))
        new_mol = Chem.MolFromSmiles(rw_res['smiles'])
        desc = _descriptor(new_mol)
        desc.update({
            'smiles': rw_res['smiles'],
            'canonical_smiles': rw_res['canonical_smiles'],
            'cip_labels': rw_res['cip_labels'],
            'notes': rw_res['notes'],
        })
        results = [desc]
        extra_top['smiles'] = rw_res['smiles']
        extra_top['canonical_smiles'] = rw_res['canonical_smiles']
        extra_top['cip_labels'] = rw_res['cip_labels']
    elif operation == 'depict_like':
        if len(mols) != 1:
            raise ValueError('depict_like requires one molecule')
        ref_img = options.get('reference_image') or options.get('reference_image_path')
        if not ref_img:
            raise ValueError('depict_like requires reference_image')
        raw_smi = molecules[0].get('smiles') or Chem.MolToSmiles(mols[0])
        img_out = options.get('image_output_path')
        if img_out is None and output_path and str(output_path).lower().endswith(('.png', '.jpg', '.jpeg')):
            img_out = output_path
            output_path = None
        dep_res = stereo_audit.depict_like(
            raw_smi,
            ref_img,
            output_path=img_out,
            annotate_indices=bool(options.get('annotate_indices', True)),
            size=int(options.get('size', 500)),
        )
        serializable_dep = {k: v for k, v in dep_res.items() if k != 'image'}
        serializable_dep['checkpoints'] = stereo_audit.visual_checkpoints(raw_smi)
        results = [serializable_dep]
    elif operation == 'enumerate_markush':
        core_smi = options.get('core_smiles') or molecules[0].get('smiles') or Chem.MolToSmiles(mols[0])
        r_groups = options.get('r_groups_by_label') or options.get('r_groups')
        if r_groups is None:
            raise ValueError('enumerate_markush requires r_groups or r_groups_by_label')
        enum_res = stereo_audit.enumerate_markush_r_groups(core_smi, r_groups)
        if isinstance(enum_res, dict):
            products_plain = {k: str(v) for k, v in enum_res.items()}
            results = enum_res.get('results', [{'label': k, 'smiles': str(v)} for k, v in enum_res.items()])
            extra_top['products'] = products_plain
        else:
            results = [{'smiles': enum_res, 'checkpoints': stereo_audit.visual_checkpoints(enum_res or '')}]
            extra_top['smiles'] = enum_res
    elif operation == 'r_groups':
        from rdkit.Chem import rdRGroupDecomposition
        if len(mols) < 2:
            raise ValueError('Provide an explicit core followed by molecules to decompose')
        rows, unmatched = rdRGroupDecomposition.RGroupDecompose([mols[0]], mols[1:], asSmiles=True)
        results = [{'rows': rows, 'unmatched_input_indices': [i + 1 for i in unmatched]}]
    else:
        raise ValueError(
            'operation must be inspect, stereoisomers, tautomers, mcs, r_groups, '
            'set_stereo, edit_structure, edit_smarts, read_wedges, depict_like, or enumerate_markush'
        )
    if options.get('include_molblock') and operation == 'inspect':
        for result, mol in zip(results, mols):
            if mol.GetNumConformers() == 0:
                rdDepictor.Compute2DCoords(mol)
            result['molblock'] = Chem.MolToMolBlock(mol, forceV3000=True)
    all_checkpoints = []
    for r in results:
        if isinstance(r, dict) and r.get('checkpoints'):
            all_checkpoints.extend(r['checkpoints'])
    if not all_checkpoints and mols:
        all_checkpoints = stereo_audit.visual_checkpoints(Chem.MolToSmiles(mols[0]))
    data = {
        'ok': True,
        'operation': operation,
        'input_keys': [semantic_key(m) for m in mols],
        'results': results,
        'warnings': warnings,
        'checkpoints': all_checkpoints,
        'index_convention': 'zero_based_input_atom_order',
        **extra_top,
    }
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


def _resolve_crossing_bond_id(ref, fragment, atom_map):
    """Resolve a bond reference (native bond ID str, bond index int, or [a1, a2] atom index pair) to a <b> id."""
    if isinstance(ref, (list, tuple)) and len(ref) == 2:
        a1, a2 = int(ref[0]), int(ref[1])
        if (a1 + 1) not in atom_map or (a2 + 1) not in atom_map:
            raise ValueError(f'Crossing atom indices {[a1, a2]} out of range')
        n1, n2 = str(atom_map[a1 + 1]), str(atom_map[a2 + 1])
        target_ends = {n1, n2}
        for b in fragment.findall('b'):
            if {b.get('B'), b.get('E')} == target_ends:
                return b.get('id')
        raise ValueError(f'No bond found between atom indices {a1} and {a2}')
    if isinstance(ref, int):
        bonds = fragment.findall('b')
        if 0 <= ref < len(bonds):
            return bonds[ref].get('id')
        raise ValueError(f'Bond index {ref} out of range')
    ref_str = str(ref)
    for b in fragment.findall('b'):
        if b.get('id') == ref_str:
            return ref_str
    return ref_str


def _strip_multi_attachments_for_inventory(root_el: ET.Element) -> ET.Element:
    """Return a deep copy of root_el with MultiAttachment nodes and their coordination bonds removed."""
    cleaned = deepcopy(root_el)
    for frag in cleaned.iter('fragment'):
        ma_ids = {
            n.get('id')
            for n in list(frag.findall('n'))
            if n.get('NodeType') == 'MultiAttachment'
        }
        if not ma_ids:
            continue
        for n in list(frag.findall('n')):
            if n.get('id') in ma_ids:
                frag.remove(n)
        for b in list(frag.findall('b')):
            if b.get('B') in ma_ids or b.get('E') in ma_ids:
                frag.remove(b)
    return cleaned


def compose_chemical_figure(manifest_path: str, output_path: str) -> dict:
    """Compose editable CDXML using explicit point coordinates and grounded molecules.

    Read the Skill publication-figures reference for the JSON manifest schema.
    Supports molecules with exact atom coordinates or template alignment, CIP/
    atom labels, highlights, ring fills, multi-attachments, crossings, rich text,
    straight/equilibrium/resonance/retro arrows, curved electron arrows,
    transition-state brackets, orbitals, interactions, and shapes.
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
        grid = data['grid']
        columns = int(grid.get('columns', 3))
        if not 1 <= columns <= 20:
            raise ValueError('grid columns must be 1..20')
        cell_width, row_height = float(grid.get('cell_width', 160)), float(grid.get('row_height', 140))
        if min(cell_width, row_height) < 20:
            raise ValueError('Grid cells must be at least 20 points')
        ox, oy = _point(grid.get('origin', [90, 90]))
        count = 0
        objects = [dict(item) for item in objects]
        for item in objects:
            if item.get('type') == 'molecule' and 'position' not in item and 'coordinates' not in item:
                item['position'] = [ox + (count % columns) * cell_width, oy + (count // columns) * row_height]
                count += 1
    if len(objects) > 1000:
        raise ValueError('At most 1000 scene objects')

    def local_path(value):
        path = Path(value).expanduser()
        return path.resolve() if path.is_absolute() else (manifest_file.parent / path).resolve()

    template = local_path(data['template_path']) if data.get('template_path') else None
    if template and not any(data.get(k) for k in ('edits', 'objects', 'style', 'steps', 'crossings')):
        target = artifact_safety.resolve_destination(source=template, output_path=output_path, tag='figure', suffix='.cdxml')
        with artifact_safety.staging_file(target) as stage:
            stage.write_bytes(template.read_bytes())
            artifact_safety.validate_artifact(stage)
            artifact_safety.publish_file(stage, target)
        return artifact_safety.with_artifacts({
            'ok': True,
            'output_path': str(target),
            'metadata': {
                'native_objects': 'byte_identical',
                'chemical_semantics': 'unchanged_bytes',
                'document_chemistry_validation': {
                    'status': 'preserved',
                    'method': 'byte_identical_copy',
                    'scope': 'unchanged_bytes',
                    'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                },
                'native_render': 'not_run',
                'visual_identity': 'requires_same_renderer',
            },
        }, [target])

    if template:
        tree = ET.parse(template)
        root = tree.getroot()
        pages = root.findall('page')
        if len(pages) != 1:
            raise ValueError('Template mode currently requires one page; select/export the target page first')
        page = pages[0]
        before = document_inventory(template)
    else:
        root = ET.Element('CDXML', {
            'BondLength': '14.4',
            'LineWidth': '0.6',
            'BoldWidth': '2',
            'HashSpacing': '2.5',
            'MarginWidth': '1.6',
            'BondSpacing': '18',
            'LabelFont': '3',
            'CaptionFont': '3',
            'LabelSize': '10',
            'CaptionSize': '10',
            'LabelFace': '96',
        })
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
    for name, attribute in {
        'font_size': 'CaptionSize',
        'bond_length': 'BondLength',
        'line_width': 'LineWidth',
        'bold_width': 'BoldWidth',
        'hash_spacing': 'HashSpacing',
        'margin_width': 'MarginWidth',
    }.items():
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
        ET.SubElement(colors, 'color', {'r': '1', 'g': '1', 'b': '1'})
        ET.SubElement(colors, 'color', {'r': '0', 'g': '0', 'b': '0'})

    def color(value):
        if not value:
            return '3' if not template else '0'
        raw = str(value).strip()
        if raw.lower() in JACS_PALETTE:
            raw = JACS_PALETTE[raw.lower()]
        v = raw.lstrip('#')
        if len(v) == 3 and all(c in '0123456789abcdefABCDEF' for c in v):
            v = ''.join(ch * 2 for ch in v)
        if len(v) != 6:
            raise ValueError('Colors must be six-digit RGB hex values')
        rgb = [int(v[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        ET.SubElement(colors, 'color', dict(zip(('r', 'g', 'b'), map(str, rgb))))
        return str(len(colors) + 1)

    named, validations, boxes = {}, [], []
    frag_meta = []
    bg_z_elements = []
    pending_crossings = []

    def remember(item, element, bbox=None):
        name = item.get('id')
        if name:
            if name in named:
                raise ValueError(f'Duplicate scene object id: {name}')
            named[name] = element.get('id')
        if bbox:
            boxes.append({'id': name or element.get('id'), 'box': list(bbox)})

    def text(parent, item):
        x, y = _point(item['position'])
        size = float(item.get('size', font_size))
        if not 3 <= size <= 144:
            raise ValueError('Text size must be 3..144 points')
        align = item.get('align', 'Left')
        if align not in ('Left', 'Center', 'Right'):
            raise ValueError('align must be Left, Center, Right')
        node = ET.SubElement(parent, 't', {
            'id': uid(),
            'p': f'{x} {y}',
            'Justification': align,
            'InterpretChemically': 'no',
        })
        runs = item.get('runs', [{'text': item.get('text', '')}])
        for run in runs:
            face = sum(
                bit
                for key, bit in [('bold', 1), ('italic', 2), ('underline', 4), ('subscript', 32), ('superscript', 64)]
                if run.get(key)
            )
            if run.get('subscript') and run.get('superscript'):
                raise ValueError('A text run cannot be both subscript and superscript')
            ET.SubElement(node, 's', {
                'font': font_id,
                'size': str(size),
                'face': str(face),
                'color': color(run.get('color', item.get('color'))),
            }).text = str(run.get('text', ''))
        full = ''.join(str(r.get('text', '')) for r in runs)
        width = max([len(line) for line in full.splitlines()] or [0]) * size * .6
        left = x - width / 2 if align == 'Center' else x - width if align == 'Right' else x
        remember(item, node, (left, y - size, left + width, y + size * .3))
        return node

    def emit_ts_bracket(box_coords, spec_dict, bracketed_ids=None):
        bx1, by1, bx2, by2 = map(float, box_coords)
        if bx2 < bx1:
            bx1, bx2 = bx2, bx1
        if by2 < by1:
            by1, by2 = by2, by1
        lip = float(spec_dict.get('lip_size', 5.0))
        bracket_type = str(spec_dict.get('bracket_type', 'Square'))
        superscript = str(spec_dict.get('superscript', spec_dict.get('label', '\u2021')))
        c_idx = color(spec_dict.get('color'))
        left_id = uid()
        right_id = uid()
        bg_id = uid()
        att1_id = uid()
        att2_id = uid()
        ET.SubElement(page, 'graphic', {
            'id': left_id,
            'BoundingBox': f'{bx1:.2f} {by1:.2f} {bx1 + lip:.2f} {by2:.2f}',
            'GraphicType': 'Bracket',
            'BracketType': bracket_type,
            'LipSize': f'{lip:g}',
            'color': c_idx,
        })
        ET.SubElement(page, 'graphic', {
            'id': right_id,
            'BoundingBox': f'{bx2:.2f} {by1:.2f} {bx2 - lip:.2f} {by2:.2f}',
            'GraphicType': 'Bracket',
            'BracketType': bracket_type,
            'LipSize': f'{lip:g}',
            'color': c_idx,
        })
        bg_attrs = {'id': bg_id, 'BracketType': bracket_type}
        obj_ids = bracketed_ids or spec_dict.get('object_ids')
        if obj_ids:
            bg_attrs['BracketedObjectIDs'] = ' '.join(str(named.get(i, i)) for i in obj_ids)
        bg_node = ET.SubElement(page, 'bracketedgroup', bg_attrs)
        ET.SubElement(bg_node, 'bracketattachment', {'id': att1_id, 'GraphicID': left_id})
        ET.SubElement(bg_node, 'bracketattachment', {'id': att2_id, 'GraphicID': right_id})
        if superscript:
            text(page, {
                'position': [bx2 + 3.5, by1 + 4.0],
                'text': superscript,
                'align': 'Left',
                'size': font_size,
                'color': spec_dict.get('color'),
            })
        return bg_node

    for edit in data.get('edits', []):
        if set(edit) - {'id', 'translate', 'text', 'runs', 'display'}:
            raise ValueError('Template edits support id, translate, text/runs only')
        matches = [n for n in page.iter() if n.get('id') == str(edit['id'])]
        if len(matches) != 1:
            raise ValueError('Template edit needs one exact native object ID')
        node = matches[0]
        if 'display' in edit:
            from .figure_editing import edit_bond_display
            edit_bond_display(node, edit)
            continue
        if node.tag not in ('fragment', 'group', 't', 'arrow', 'curve', 'graphic', 'bracketedgroup'):
            raise ValueError('Edit whole objects, not individual chemical atoms/bonds')
        if 'translate' in edit:
            _move(node, *_point(edit['translate']))
        if 'text' in edit or 'runs' in edit:
            if node.tag != 't' or any(node is t for atom in page.iter('n') for t in atom.iter('t')):
                raise ValueError('Text edits are restricted to non-atom annotations')
            pos = list(map(float, node.get('p').split()))
            replacement = text(ET.Element('tmp'), {**edit, 'position': pos})
            for child in list(node):
                node.remove(child)
            for child in list(replacement):
                node.append(child)

    for item in objects:
        kind = item.get('type')
        fields = {
            'molecule': {
                'smiles', 'molblock', 'file', 'fragment_index', 'position', 'coordinates', 'rotation', 'label',
                'preserve_coordinates', 'align_to', 'alignment_mode', 'bond_length', 'cip_labels', 'atom_numbers',
                'annotation_offsets', 'highlight_atoms', 'highlight_bonds', 'highlight_color', 'color', 'bond_displays',
                'ring_fills', 'atom_halos', 'multi_attachments', 'crossings', 'ts_bracket',
            },
            'text': {'position', 'text', 'runs', 'size', 'align', 'color'},
            'arrow': {'start', 'end', 'style', 'color'},
            'line': {'start', 'end', 'style', 'color'},
            'curve': {'points', 'color'},
            'electron_arrow': {'points', 'color', 'electrons'},
            'symbol': {'start', 'end', 'symbol', 'color'},
            'rectangle': {'start', 'end', 'color', 'fill_type', 'round_edge', 'dashed', 'background'},
            'ellipse': {'start', 'end', 'color', 'fill_type', 'round_edge', 'dashed', 'background'},
            'bracket': {'start', 'end', 'color', 'label'},
            'ts_bracket': {'start', 'end', 'from', 'to', 'box', 'color', 'label', 'superscript', 'bracket_type', 'lip_size', 'object_ids'},
            'orbital': {'center', 'at', 'position', 'cx', 'cy', 'start', 'end', 'orbital_type', 'angle_deg', 'angle', 'length', 'width', 'color'},
            'interaction': {'start', 'end', 'from', 'to', 'p1', 'p2', 'style', 'color', 'label', 'clip_margin'},
        }
        unknown = set(item) - fields.get(kind, set()) - {'type', 'id'}
        if unknown:
            raise ValueError(f'Unknown {kind} object fields: {sorted(unknown)}')
        if kind == 'molecule':
            record = dict(item)
            if record.get('file'):
                record['file'] = str(local_path(record['file']))
            mol = _mol(record)
            if item.get('multi_attachments'):
                expected_inventory.update([semantic_key(mol)])
            else:
                expected_inventory.update(semantic_key(m) for m in Chem.GetMolFrags(mol, asMols=True))
            source = Chem.MolToCXSmiles(mol)
            if item.get('coordinates') is not None:
                coords = item['coordinates']
                if len(coords) != mol.GetNumAtoms():
                    raise ValueError('Exact coordinates require one point per input atom')
                conf = Chem.Conformer(mol.GetNumAtoms())
                for i, xy in enumerate(coords):
                    x, y = _point(xy)
                    conf.SetAtomPosition(i, (x, -y, 0))
                mol.RemoveAllConformers()
                mol.AddConformer(conf)
                absolute = True
            else:
                absolute = False
                if item.get('align_to'):
                    reference_record = dict(item['align_to'])
                    if reference_record.get('file'):
                        reference_record['file'] = str(local_path(reference_record['file']))
                    reference = _mol(reference_record)
                    if not reference.GetNumConformers():
                        rdDepictor.Compute2DCoords(reference)
                    params = rdDepictor.ConstrainedDepictionParams()
                    params.acceptFailure = False
                    params.adjustMolBlockWedging = True
                    if item.get('alignment_mode', 'substructure') == 'mcs':
                        from rdkit.Chem import rdFMCS
                        mcs = rdFMCS.FindMCS([reference, mol], timeout=10, ringMatchesRingOnly=True, completeRingsOnly=True)
                        if mcs.canceled or mcs.numAtoms < 3:
                            raise ValueError('No validated MCS alignment core')
                        query = Chem.MolFromSmarts(mcs.smartsString)
                        atom_map_mcs = list(zip(reference.GetSubstructMatch(query), mol.GetSubstructMatch(query)))
                        rdDepictor.GenerateDepictionMatching2DStructure(mol, reference, atomMap=atom_map_mcs, params=params)
                    else:
                        rdDepictor.GenerateDepictionMatching2DStructure(mol, reference, params=params)
                elif item.get('preserve_coordinates') and mol.GetNumConformers():
                    pass
                else:
                    rdDepictor.Compute2DCoords(mol, useRingTemplates=True)
            Chem.Kekulize(mol, clearAromaticFlags=True)
            atoms, bonds = _rdkit_mol_to_atom_bond_dicts(mol)
            angle = math.radians(float(item.get('rotation', 0)))
            cx = sum(a['x'] for a in atoms) / len(atoms)
            cy = sum(a['y'] for a in atoms) / len(atoms)
            px, py = _point(item.get('position', [100, 100]))
            local_bond_length = float(item.get('bond_length', bond_length))
            if not 5 <= local_bond_length <= 100:
                raise ValueError('Molecule bond_length must be 5..100 points')
            scale = local_bond_length / 1.5
            for a in atoms:
                if absolute:
                    a['y'] = -a['y']
                else:
                    x, y = a['x'] - cx, a['y'] - cy
                    a['x'] = px + scale * (x * math.cos(angle) - y * math.sin(angle))
                    a['y'] = py - scale * (x * math.sin(angle) + y * math.cos(angle))
            gen = _IDGen(start=next_id)
            fragment_xml, atom_map, fragment_id = _build_fragment(atoms, bonds, gen)
            fragment = ET.fromstring(fragment_xml)
            next_id = max(int(n.get('id')) for n in fragment.iter() if n.get('id')) + 1
            for run in fragment.iter('s'):
                run.set('font', font_id)
                run.set('size', str(font_size))
            for index, display in item.get('bond_displays', {}).items():
                if int(index) not in range(mol.GetNumBonds()):
                    raise ValueError('Invalid bond display index')
                if display not in ('None', 'WedgeBegin', 'WedgeEnd', 'WedgedHashBegin', 'WedgedHashEnd', 'Wavy', 'Bold', 'Dash'):
                    raise ValueError('Unsupported bond display')
                bond = fragment.findall('b')[int(index)]
                if display == 'None':
                    bond.attrib.pop('Display', None)
                else:
                    bond.set('Display', display)
            fragment.set('color', color(item.get('color')))
            for run in fragment.iter('s'):
                run.set('color', color(item.get('color')))

            # Validate fragment BEFORE appending MultiAttachment nodes and coordination bonds
            validations.append(validate_fragment(source, ET.tostring(fragment, encoding='unicode')))

            for ma in item.get('multi_attachments', []):
                metal_idx = int(ma['metal_atom'])
                ligand_indices = [int(k) for k in ma['ligand_atoms']]
                if metal_idx not in range(len(atoms)) or any(k not in range(len(atoms)) for k in ligand_indices) or not ligand_indices:
                    raise ValueError('Invalid multi_attachments atom indices')
                mcx = sum(atoms[k]['x'] for k in ligand_indices) / len(ligand_indices)
                mcy = sum(atoms[k]['y'] for k in ligand_indices) / len(ligand_indices)
                ma_id = uid()
                att_str = ' '.join(str(atom_map[k + 1]) for k in ligand_indices)
                ET.SubElement(fragment, 'n', {
                    'id': ma_id,
                    'p': f'{mcx:.2f} {mcy:.2f}',
                    'NodeType': 'MultiAttachment',
                    'Attachments': att_str,
                })
                b_disp = str(ma.get('bond_display', 'Dash'))
                b_order = str(ma.get('bond_order', 'dative'))
                b_attrs = {'id': uid(), 'B': str(atom_map[metal_idx + 1]), 'E': ma_id}
                if b_disp and b_disp != 'None':
                    b_attrs['Display'] = b_disp
                if b_order and b_order != 'None':
                    b_attrs['Order'] = b_order
                ET.SubElement(fragment, 'b', b_attrs)

            page.append(fragment)
            frag_meta.append({'id': item.get('id'), 'fragment': fragment, 'atom_map': atom_map})

            for cr in item.get('crossings', []):
                if isinstance(cr, (list, tuple)) and len(cr) == 2:
                    f_ref, b_ref = cr[0], cr[1]
                else:
                    f_ref = cr.get('front', cr.get('front_bond'))
                    b_ref = cr.get('back', cr.get('back_bond'))
                pending_crossings.append({
                    'front': _resolve_crossing_bond_id(f_ref, fragment, atom_map),
                    'back': _resolve_crossing_bond_id(b_ref, fragment, atom_map),
                })

            xx = [a['x'] for a in atoms]
            yy = [a['y'] for a in atoms]
            remember(item, fragment, (min(xx) - font_size / 2, min(yy) - font_size, max(xx) + font_size / 2, max(yy) + font_size / 2))

            if item.get('ring_fills'):
                atom_rings = list(mol.GetRingInfo().AtomRings())
                for rf in item['ring_fills']:
                    if 'atoms' in rf:
                        r_atoms = [int(x) for x in rf['atoms']]
                    else:
                        r_idx = int(rf.get('ring_index', 0))
                        if not 0 <= r_idx < len(atom_rings):
                            raise ValueError(f'Invalid ring_index: {r_idx}')
                        r_atoms = list(atom_rings[r_idx])
                    r_pts = [(atoms[k]['x'], atoms[k]['y']) for k in r_atoms]
                    c_idx = color(rf.get('color', '#D6EAF8'))
                    c_pts = _curve_points_for_ring(
                        r_pts,
                        style=str(rf.get('style', 'polygon')).lower(),
                        inset=float(rf.get('inset', 0.0)),
                    )
                    rx1, ry1 = min(p[0] for p in r_pts), min(p[1] for p in r_pts)
                    rx2, ry2 = max(p[0] for p in r_pts), max(p[1] for p in r_pts)
                    rf_el = ET.Element('curve', {
                        'id': uid(),
                        'Closed': 'yes',
                        'FillType': 'Solid',
                        'LineType': 'None',
                        'color': c_idx,
                        'Z': '1',
                        'BoundingBox': f'{rx1:.2f} {ry1:.2f} {rx2:.2f} {ry2:.2f}',
                        'CurvePoints': c_pts,
                    })
                    page.insert(0, rf_el)
                    bg_z_elements.append(rf_el)

            highlight = color(item.get('highlight_color', '#cc3333')) if item.get('highlight_atoms') else None
            for i in item.get('highlight_atoms', []):
                if int(i) not in range(len(atoms)):
                    raise ValueError('Invalid highlight atom index')
                atom_node = fragment.find(f"n[@id='{atom_map[int(i) + 1]}']")
                atom_node.set('color', highlight)
                for run in atom_node.iter('s'):
                    run.set('color', highlight)
                a = atoms[int(i)]
                x, y = a['x'], a['y']
                radius = font_size * .7
                halo_el = ET.Element('graphic', {
                    'id': uid(),
                    'GraphicType': 'Oval',
                    'OvalType': 'Circle Filled',
                    'BoundingBox': f'{x - radius} {y - radius} {x + radius} {y + radius}',
                    'Center3D': f'{x} {y} 0',
                    'MajorAxisEnd3D': f'{x + radius} {y} 0',
                    'MinorAxisEnd3D': f'{x} {y + radius} 0',
                    'color': highlight,
                    'Z': '1',
                })
                page.insert(0, halo_el)
                bg_z_elements.append(halo_el)

            for halo in item.get('atom_halos', []):
                h_atoms = halo.get('atoms', [halo['atom']] if 'atom' in halo else [])
                h_col = color(halo.get('color', '#FCF3CF'))
                h_rad = float(halo.get('radius', font_size * .7))
                for i in h_atoms:
                    if int(i) not in range(len(atoms)):
                        raise ValueError('Invalid atom_halos atom index')
                    a = atoms[int(i)]
                    x, y = a['x'], a['y']
                    halo_el = ET.Element('graphic', {
                        'id': uid(),
                        'GraphicType': 'Oval',
                        'OvalType': 'Circle Filled',
                        'BoundingBox': f'{x - h_rad} {y - h_rad} {x + h_rad} {y + h_rad}',
                        'Center3D': f'{x} {y} 0',
                        'MajorAxisEnd3D': f'{x + h_rad} {y} 0',
                        'MinorAxisEnd3D': f'{x} {y + h_rad} 0',
                        'color': h_col,
                        'Z': '1',
                    })
                    page.insert(0, halo_el)
                    bg_z_elements.append(halo_el)

            for i in item.get('highlight_bonds', []):
                if int(i) not in range(mol.GetNumBonds()):
                    raise ValueError('Invalid highlight bond index')
                fragment.findall('b')[int(i)].set('color', color(item.get('highlight_color', '#cc3333')))
            rdCIPLabeler.AssignCIPLabels(mol)
            for i, a in enumerate(atoms):
                labels = []
                if item.get('atom_numbers'):
                    labels.append(str(i))
                atom = mol.GetAtomWithIdx(i)
                if item.get('cip_labels') and atom.HasProp('_CIPCode'):
                    labels.append(atom.GetProp('_CIPCode'))
                if labels:
                    vx, vy = a['x'] - sum(xx) / len(xx), a['y'] - sum(yy) / len(yy)
                    norm = math.hypot(vx, vy) or 1
                    ox, oy = vx / norm * 13, vy / norm * 13
                    override = item.get('annotation_offsets', {}).get(str(i))
                    if override is not None:
                        ox, oy = _point(override)
                    text(page, {
                        'position': [a['x'] + ox, a['y'] + oy],
                        'text': ','.join(labels),
                        'align': 'Center',
                        'size': max(5, font_size * .7),
                    })
            if item.get('label'):
                text(page, {
                    'position': [(min(xx) + max(xx)) / 2, max(yy) + font_size + 12],
                    'text': item['label'],
                    'align': 'Center',
                })
            if item.get('ts_bracket'):
                ts_cfg = item['ts_bracket'] if isinstance(item['ts_bracket'], dict) else {}
                emit_ts_bracket(
                    (min(xx) - 5.0, min(yy) - 4.0, max(xx) + 5.0, max(yy) + 4.0),
                    ts_cfg,
                    bracketed_ids=[fragment.get('id')],
                )
        elif kind == 'text':
            text(page, item)
        elif kind in ('arrow', 'line'):
            start, end = _point(item['start']), _point(item['end'])
            style_name = item.get('style', 'forward' if kind == 'arrow' else 'line')
            if style_name not in ('forward', 'line', 'dashed', 'failed', 'resonance', 'equilibrium', 'retro'):
                raise ValueError('Unsupported straight arrow style')

            def arrow(a, b, half=False):
                node = ET.SubElement(page, 'arrow', {
                    'id': uid(),
                    'Tail3D': f'{a[0]} {a[1]} 0',
                    'Head3D': f'{b[0]} {b[1]} 0',
                    'ArrowheadHead': 'HalfLeft' if half else 'Full',
                    'ArrowheadType': 'Solid',
                    'HeadSize': '1000',
                    'ArrowheadWidth': '250',
                    'FillType': 'None',
                    'LineWidth': root.get('LineWidth', '0.6'),
                    'color': color(item.get('color')),
                })
                return node

            node = arrow(start, end, style_name == 'equilibrium')
            if style_name == 'line':
                node.set('ArrowheadHead', 'None')
            if style_name == 'dashed':
                node.set('LineType', 'Dashed')
            if style_name == 'failed':
                node.set('NoGo', 'Cross')
            if style_name == 'resonance':
                node.set('ArrowheadTail', 'Full')
            if style_name == 'retro':
                node.set('ArrowShaftSpacing', '300')
                node.set('ArrowheadType', 'Angle')
                node.set('LineType', 'Double')
            if style_name == 'equilibrium':
                dx, dy = end[0] - start[0], end[1] - start[1]
                length = math.hypot(dx, dy)
                if length == 0:
                    raise ValueError('Arrow length must be nonzero')
                sx, sy = -dy / length * 4, dx / length * 4
                arrow((end[0] + sx, end[1] + sy), (start[0] + sx, start[1] + sy), True)
            remember(item, node)
        elif kind in ('curve', 'electron_arrow'):
            points = [_point(x) for x in item['points']]
            if len(points) != 4:
                raise ValueError('Cubic curves require four Bezier points')
            native_points = [points[0], *points, points[-1]]
            node = ET.SubElement(page, 'curve', {
                'id': uid(),
                'CurvePoints': ' '.join(f'{x} {y}' for x, y in native_points),
                'FillType': 'None',
                'LineWidth': root.get('LineWidth', '0.6'),
                'color': color(item.get('color')),
            })
            if kind == 'electron_arrow':
                node.set('ArrowheadHead', 'HalfLeft' if item.get('electrons', 2) == 1 else 'Full')
                node.set('ArrowheadType', 'Solid')
            remember(item, node)
        elif kind == 'symbol':
            symbol = item['symbol']
            if symbol not in ('LonePair', 'Electron', 'RadicalCation', 'RadicalAnion', 'CirclePlus', 'CircleMinus', 'Dagger', 'DoubleDagger', 'Plus', 'Minus'):
                raise ValueError('Unsupported native symbol')
            x1, y1 = _point(item['start'])
            x2, y2 = _point(item['end'])
            if x2 <= x1 or y2 <= y1:
                raise ValueError('Symbol end must be below/right of start')
            node = ET.SubElement(page, 'graphic', {
                'id': uid(),
                'GraphicType': 'Symbol',
                'SymbolType': symbol,
                'BoundingBox': f'{x1} {y1} {x2} {y2}',
                'color': color(item.get('color')),
            })
            remember(item, node)
        elif kind in ('rectangle', 'ellipse', 'bracket'):
            x1, y1 = _point(item['start'])
            x2, y2 = _point(item['end'])
            if x2 <= x1 or y2 <= y1:
                raise ValueError('Shape end must be below/right of start')
            if kind == 'bracket':
                node = ET.SubElement(page, 'group', {'id': uid(), 'color': color(item.get('color'))})
                for x, sign in ((x1, 1), (x2, -1)):
                    for a, b in [((x, y1), (x, y2)), ((x, y1), (x + 5 * sign, y1)), ((x, y2), (x + 5 * sign, y2))]:
                        ET.SubElement(node, 'graphic', {
                            'id': uid(),
                            'GraphicType': 'Line',
                            'color': color(item.get('color')),
                            'BoundingBox': f'{a[0]} {a[1]} {b[0]} {b[1]}',
                        })
                if item.get('label'):
                    text(page, {'position': [x2 + 3, y2], 'text': item['label']})
            else:
                node = ET.Element('graphic', {
                    'id': uid(),
                    'GraphicType': 'Oval' if kind == 'ellipse' else 'Rectangle',
                    'BoundingBox': f'{x1} {y1} {x2} {y2}',
                    'color': color(item.get('color')),
                })
                if kind == 'ellipse':
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    node.set('Center3D', f'{cx} {cy} 0')
                    node.set('MajorAxisEnd3D', f'{x2} {cy} 0')
                    node.set('MinorAxisEnd3D', f'{cx} {y2} 0')
                if 'fill_type' in item and item['fill_type'] is not None:
                    ft = str(item['fill_type']).strip().lower()
                    fill_map = {'solid': 'Solid', 'shaded': 'Shaded', 'faded': 'Faded', 'none': 'None'}
                    if ft not in fill_map:
                        raise ValueError(f'Unsupported fill_type: {item["fill_type"]}')
                    node.set('FillType', fill_map[ft])
                    if kind == 'ellipse' and ft == 'solid':
                        node.set('OvalType', 'Circle Filled')
                if item.get('round_edge'):
                    if kind == 'rectangle':
                        node.set('RectangleType', 'RoundEdge')
                if item.get('dashed'):
                    node.set('LineType', 'Dashed')
                if item.get('background'):
                    node.set('Z', '1')
                    page.insert(0, node)
                    bg_z_elements.append(node)
                else:
                    page.append(node)
            remember(item, node)
        elif kind == 'ts_bracket':
            if item.get('box'):
                b_coords = item['box']
                if len(b_coords) != 4:
                    raise ValueError('ts_bracket box requires 4 coordinates [x1, y1, x2, y2]')
                x1, y1 = _point(b_coords[:2])
                x2, y2 = _point(b_coords[2:])
            else:
                s_pt = item.get('start') or item.get('from')
                e_pt = item.get('end') or item.get('to')
                if not s_pt or not e_pt:
                    raise ValueError('ts_bracket requires box or start/end coordinates')
                x1, y1 = _point(s_pt)
                x2, y2 = _point(e_pt)
            node = emit_ts_bracket((x1, y1, x2, y2), item)
            remember(item, node)
        elif kind == 'orbital':
            center_pt = item.get('center') or item.get('at') or item.get('position') or item.get('start')
            if center_pt is not None:
                ocx, ocy = _point(center_pt)
            elif 'cx' in item and 'cy' in item:
                ocx, ocy = _point([item['cx'], item['cy']])
            else:
                raise ValueError('orbital requires center/at/position or cx/cy')
            orb_type = str(item.get('orbital_type', 'pShaded'))
            ang_deg = float(item.get('angle_deg', item.get('angle', -90.0)))
            length = float(item.get('length', 18.0))
            width = float(item.get('width', 7.5))
            rad = math.radians(ang_deg)
            tip_x = ocx + length * math.cos(rad)
            tip_y = ocy + length * math.sin(rad)
            perp_rad = rad + math.pi / 2.0
            side_x = ocx + width * math.cos(perp_rad)
            side_y = ocy + width * math.sin(perp_rad)
            node = ET.SubElement(page, 'graphic', {
                'id': uid(),
                'GraphicType': 'Orbital',
                'OrbitalType': orb_type,
                'BoundingBox': f'{ocx:.2f} {ocy:.2f} {tip_x:.2f} {tip_y:.2f}',
                'Center3D': f'{ocx:.2f} {ocy:.2f} 0',
                'MajorAxisEnd3D': f'{tip_x:.2f} {tip_y:.2f} 0',
                'MinorAxisEnd3D': f'{side_x:.2f} {side_y:.2f} 0',
                'color': color(item.get('color', 'jacs_blue')),
            })
            remember(item, node)
        elif kind == 'interaction':
            p1 = _point(item.get('start') or item.get('from') or item['p1'])
            p2 = _point(item.get('end') or item.get('to') or item['p2'])
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            clip_margin = float(item.get('clip_margin', 3.5))
            if dist > 1e-6:
                ux, uy = (p2[0] - p1[0]) / dist, (p2[1] - p1[1]) / dist
                clip = min(clip_margin, dist * 0.4)
            else:
                ux, uy, clip = 1.0, 0.0, 0.0
            cx1, cy1 = p1[0] + ux * clip, p1[1] + uy * clip
            cx2, cy2 = p2[0] - ux * clip, p2[1] - uy * clip
            line_type = 'Solid' if str(item.get('style', 'dashed')).lower() == 'solid' else 'Dashed'
            node = ET.SubElement(page, 'graphic', {
                'id': uid(),
                'GraphicType': 'Line',
                'LineType': line_type,
                'BoundingBox': f'{min(cx1, cx2):.2f} {min(cy1, cy2):.2f} {max(cx1, cx2):.2f} {max(cy1, cy2):.2f}',
                'Head3D': f'{cx2:.2f} {cy2:.2f} 0',
                'Tail3D': f'{cx1:.2f} {cy1:.2f} 0',
                'color': color(item.get('color', 'jacs_blue')),
            })
            if item.get('label'):
                mx = (cx1 + cx2) / 2.0 - uy * 6.0
                my = (cy1 + cy2) / 2.0 + ux * 6.0 + 3.0
                text(page, {'position': [mx, my], 'text': str(item['label']), 'size': max(5, font_size * 0.9), 'align': 'Center', 'color': item.get('color', 'jacs_blue')})
            remember(item, node)
        else:
            raise ValueError(f'Unsupported object type: {kind}')

    if data.get('crossings'):
        if not isinstance(data['crossings'], list):
            raise ValueError('crossings must be a list')
        for cr in data['crossings']:
            if isinstance(cr, (list, tuple)) and len(cr) == 2:
                f_ref, b_ref = cr[0], cr[1]
                mol_id = None
            elif isinstance(cr, dict):
                if not ({'front', 'back'} <= set(cr) or {'front_bond', 'back_bond'} <= set(cr)):
                    raise ValueError('crossings require front and back native bond IDs or atom index pairs')
                f_ref = cr.get('front', cr.get('front_bond'))
                b_ref = cr.get('back', cr.get('back_bond'))
                mol_id = cr.get('molecule', cr.get('object_id'))
            else:
                raise ValueError('Invalid crossing item')
            if isinstance(f_ref, (list, tuple)) or isinstance(b_ref, (list, tuple)):
                target_fm = None
                if mol_id is not None:
                    target_fm = next((fm for fm in frag_meta if fm['id'] == mol_id), None)
                elif len(frag_meta) == 1:
                    target_fm = frag_meta[0]
                elif frag_meta:
                    target_fm = frag_meta[-1]
                if target_fm is None:
                    raise ValueError('Cannot resolve atom-pair crossing without a molecule object')
                pending_crossings.append({
                    'front': _resolve_crossing_bond_id(f_ref, target_fm['fragment'], target_fm['atom_map']),
                    'back': _resolve_crossing_bond_id(b_ref, target_fm['fragment'], target_fm['atom_map']),
                })
            else:
                pending_crossings.append({'front': str(f_ref), 'back': str(b_ref)})

    if pending_crossings:
        from .figure_editing import apply_crossings
        apply_crossings(page, pending_crossings)
        for bg_el in bg_z_elements:
            bg_el.set('Z', '1')

    if data.get('steps'):
        scheme = ET.SubElement(page, 'scheme', {'id': uid()})
        for step in data['steps']:
            attrs = {'id': uid()}
            for field, attr in [
                ('reactants', 'ReactionStepReactants'),
                ('products', 'ReactionStepProducts'),
                ('arrows', 'ReactionStepArrows'),
                ('above', 'ReactionStepObjectsAboveArrow'),
                ('below', 'ReactionStepObjectsBelowArrow'),
            ]:
                if step.get(field):
                    attrs[attr] = ' '.join(named[n] for n in step[field])
            ET.SubElement(scheme, 'step', attrs)
    collisions = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            ax, ay, az, aw = a['box']
            bx, by, bz, bw = b['box']
            if min(az, bz) - max(ax, bx) > 1 and min(aw, bw) - max(ay, by) > 1:
                collisions.append([a['id'], b['id']])
    target = artifact_safety.resolve_destination(source=template, output_path=output_path, tag='figure', suffix='.cdxml')
    with artifact_safety.staging_file(target) as stage:
        ET.indent(root)
        ET.ElementTree(root).write(stage, encoding='utf-8', xml_declaration=True)
        artifact_safety.validate_artifact(stage)
        serialized = ET.parse(stage)
        if serialized.find('.//fragment') is not None:
            if serialized.find('.//*[@NodeType="MultiAttachment"]') is not None:
                cleaned_root = _strip_multi_attachments_for_inventory(serialized.getroot())
                cleaned_xml = ET.tostring(cleaned_root, encoding='unicode')
                after = Counter(semantic_key(m) for m in read_molecules(cleaned_xml))
            else:
                after = document_inventory(stage)
        else:
            after = Counter()
        if after != expected_inventory:
            raise ValueError('chemical_semantics_changed: final document inventory differs from template plus inputs')
        document_validation = {
            'status': 'preserved',
            'method': 'final_cdxml_roundtrip',
            'scope': 'rdkit_readback_consistency',
            'molecules': sum(after.values()),
            'sha256': hashlib.sha256(stage.read_bytes()).hexdigest(),
        }
        artifact_safety.publish_file(stage, target)
    return artifact_safety.with_artifacts({
        'ok': True,
        'output_path': str(target),
        'metadata': {
            'chemistry_validation': validations,
            'document_chemistry_validation': document_validation,
            'native_render': 'not_run',
            'visual_identity': 'not_evaluated',
            'component_overlap_candidates': collisions,
            'object_ids': named,
        },
        'warnings': ['Inspect overlap candidates and native rendering before acceptance.'] if collisions else [],
    }, [target])


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
            rgba = image.convert('RGBA')
            background = Image.new('RGBA', rgba.size, 'white')
            return np.asarray(Image.alpha_composite(background, rgba).convert('RGB')).copy()

    a, b = pixels(reference_path), pixels(candidate_path)
    result = {
        'reference_dimensions': [a.shape[1], a.shape[0]],
        'candidate_dimensions': [b.shape[1], b.shape[0]],
        'same_dimensions': a.shape == b.shape,
        'chemical_identity': 'not_evaluated',
    }
    if a.shape == b.shape:
        delta = np.abs(a.astype(float) - b.astype(float))
        ia = np.min(a, axis=2) < 240
        ib = np.min(b, axis=2) < 240
        union = np.logical_or(ia, ib).sum()
        result.update(
            exact_pixels=bool(np.array_equal(a, b)),
            normalized_mae=float(delta.mean() / 255),
            ink_iou=float(np.logical_and(ia, ib).sum() / union) if union else 1.0,
        )
    return _publish({'operation': 'compare_images', 'results': [result]}, output_path)


FIGURE_TOOLS = {f.__name__: f for f in (rdkit_workbench, compose_chemical_figure, compare_figure_images)}


def main(argv=None):
    import argparse
    from .figure_validation import validate_figure
    cli_tools = {**FIGURE_TOOLS, 'validate_figure': validate_figure}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool', choices=sorted(cli_tools))
    parser.add_argument('--arguments', type=Path, required=True, help='JSON keyword arguments file')
    args = parser.parse_args(argv)
    try:
        result = cli_tools[args.tool](**json.loads(args.arguments.read_text(encoding='utf-8-sig')))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': {'type': type(exc).__name__, 'message': str(exc)}}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
