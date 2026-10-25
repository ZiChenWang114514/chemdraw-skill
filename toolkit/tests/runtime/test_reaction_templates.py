import re
from xml.etree import ElementTree as ET

import pytest
from rdkit import Chem
from rdkit.Chem import rdChemReactions

from cdxml_toolkit import reaction_templates as rt
from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.report_tools import map_reaction_atoms


def parts(side):
    return [(s, Chem.MolFromSmiles(s)) for s in side.split('.') if s]


def classify(reaction):
    left, agents, right = reaction.split('>')
    return rt.classify(parts(left), parts(agents), parts(right))


def flat(mol):
    mol = Chem.Mol(mol)
    Chem.RemoveStereochemistry(mol)
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol)


@pytest.mark.parametrize('reaction, name', [
    ('CC(=O)Cl.CCN>>CC(=O)NCC', 'Amide formation'),
    ('CC(=O)O.CCN>>CC(=O)NCC', 'Amide coupling'),
    ('CC(=O)O.CCN>CCN(CC)CC>CC(=O)NCC', 'Amide coupling'),
    ('CS(=O)(=O)Cl.CCN>>CCNS(C)(=O)=O', 'Sulfonamide'),
    ('CC(=O)Cl.OCc1ccccc1>>CC(=O)OCc1ccccc1', 'Ester formation'),
    ('CC(=O)O.OCc1ccccc1>>CC(=O)OCc1ccccc1', 'Esterification'),
    ('CC(C)(C)OC(=O)OC(=O)OC(C)(C)C.NCc1ccccc1>>CC(C)(C)OC(=O)NCc1ccccc1', 'anhydride'),
    ('Brc1ccccc1.OB(O)c1ccccc1>>c1ccc(-c2ccccc2)cc1', 'Suzuki'),
    ('Fc1ccc([N+](=O)[O-])cc1.C1CCNCC1>>O=[N+]([O-])c1ccc(N2CCCCC2)cc1', 'Aryl amination'),
    ('BrCc1ccccc1.C1CCNCC1>>c1ccc(CN2CCCCC2)cc1', 'N-Alkylation'),
    ('BrCC.Oc1ccccc1>>CCOc1ccccc1', 'Williamson'),
    ('O=Cc1ccccc1.CCN>>CCNCc1ccccc1', 'Reductive amination'),
    ('CC(=O)c1ccccc1>>CC(O)c1ccccc1', 'Carbonyl reduction'),
    ('OCc1ccccc1>>O=Cc1ccccc1', 'Alcohol oxidation'),
    ('COC(=O)c1ccccc1>>OC(=O)c1ccccc1', 'Ester hydrolysis'),
    ('CC(C)(C)OC(=O)NCc1ccccc1>>NCc1ccccc1', 'Boc deprotection'),
    ('O=[N+]([O-])c1ccccc1>>Nc1ccccc1', 'Nitro reduction'),
    ('CC=CC>>CCCC', 'Hydrogenation'),
    ('C#Cc1ccccc1.[N-]=[N+]=NCc1ccccc1>>c1ccc(Cn2cc(-c3ccccc3)nn2)cc1', 'click'),
    ('C=CC=C.C=C>>C1=CCCCC1', 'Diels'),
])
def test_common_reaction_types_are_named_from_the_structures(reaction, name):
    result = classify(reaction)
    assert result['name'] and name in result['name'], result
    assert result['matches'][0]['name'] == result['name']
    assert result['basis'] == 'reaction centre'


def test_a_reaction_without_a_template_is_unclassified_not_guessed():
    result = classify('C1CCCCC1.Cl>>ClC1CCCCC1')
    assert result['name'] is None and result['matches'] == []
    assert 'unclassified' in result['note']


def test_the_evidence_names_the_species_that_took_part_and_leaves_spectators_out():
    result = classify('CC(=O)O.CCN.O>CCN(CC)CC>CC(=O)NCC')
    assert result['matches'][0]['species'] == ['CC(=O)O', 'CCN']
    assert 'CCN(CC)CC' not in result['matches'][0]['species']


def test_a_second_site_in_the_same_molecule_does_not_change_the_class():
    result = classify('OC(=O)c1ccc(Br)cc1.CCN>>CCNC(=O)c1ccc(Br)cc1')
    assert 'Amide coupling' in result['name']


def test_a_product_that_differs_from_the_template_result_does_not_match():
    assert classify('CC(=O)Cl.CCN>>CC(=O)NC')['name'] is None


MAPPED = {
    'amide': 'CC(=O)Cl.CCN>>CC(=O)NCC',
    'suzuki': 'Brc1ccccc1.OB(O)c1ccccc1>>c1ccc(-c2ccccc2)cc1',
}


def test_the_reaction_centre_is_a_smarts_that_reproduces_the_reaction():
    result = map_reaction_atoms(MAPPED['amide'], {'template': True})
    template = result['template']
    assert template['smarts'].count('>>') == 1
    rxn = rdChemReactions.ReactionFromSmarts(template['smarts'])
    assert rxn.GetNumReactantTemplates() == 2
    products = {flat(p[0]) for p in rxn.RunReactants((Chem.MolFromSmiles('CC(=O)Cl'), Chem.MolFromSmiles('CCN')))}
    assert products == {'CCNC(C)=O'}
    assert template['reproduces'] is True
    assert template['changed_atoms'] == 2


def test_the_template_generalises_to_other_substituents_but_not_to_other_chemistry():
    template = map_reaction_atoms(MAPPED['amide'], {'template': True})['template']
    rxn = rdChemReactions.ReactionFromSmarts(template['smarts'])
    products = {flat(p[0]) for p in rxn.RunReactants((Chem.MolFromSmiles('O=C(Cl)c1ccccc1'),
                                                       Chem.MolFromSmiles('CCCN')))}
    assert products == {flat(Chem.MolFromSmiles('CCCNC(=O)c1ccccc1'))}
    assert not rxn.RunReactants((Chem.MolFromSmiles('CCO'), Chem.MolFromSmiles('CCN')))


def test_the_template_keeps_leaving_atoms_and_renumbers_the_maps_from_one():
    template = map_reaction_atoms(MAPPED['suzuki'], {'template': True})['template']
    left, right = template['smarts'].split('>>')
    numbers = lambda text: sorted(int(n) for n in re.findall(r':(\d+)\]', text))
    assert numbers(left) == numbers(right) == list(range(1, len(numbers(left)) + 1))
    assert 'Br' in left or '#35' in left
    rxn = rdChemReactions.ReactionFromSmarts(template['smarts'])
    out = {flat(p[0]) for p in rxn.RunReactants((Chem.MolFromSmiles('Brc1ccccc1C'), Chem.MolFromSmiles('OB(O)c1ccccn1')))}
    assert out == {flat(Chem.MolFromSmiles('Cc1ccccc1-c1ccccn1'))}


def test_an_ambiguous_mapping_has_no_template_until_the_tie_is_resolved():
    result = map_reaction_atoms('CC(=O)O.OCC>>CC(=O)OCC', {'template': True})
    assert result['status'] == 'ambiguous'
    assert result['template']['smarts'] is None and 'ambiguous' in result['template']['note']
    forced = map_reaction_atoms('CC(=O)O.OCC>>CC(=O)OCC', {'template': True, 'resolve_ambiguity': True})
    assert forced['template']['smarts'] and forced['template']['reproduces'] is True


def test_classification_and_template_are_options_of_the_mapping_tool():
    plain = map_reaction_atoms(MAPPED['amide'])
    assert 'template' not in plain and 'reaction_class' not in plain
    result = map_reaction_atoms(MAPPED['amide'], {'classify': True})
    assert 'Amide formation' in result['reaction_class']['name'] and 'template' not in result
    with pytest.raises(ValueError, match='Unknown options'):
        map_reaction_atoms(MAPPED['amide'], {'templates': True})


def test_a_list_of_reactions_gets_one_class_and_template_each():
    out = map_reaction_atoms([{'label': 'a', 'reaction': MAPPED['amide']},
                              {'label': 'b', 'reaction': MAPPED['suzuki']}], {'template': True, 'classify': True})
    names = [entry['reaction_class']['name'] for entry in out['reactions']]
    assert 'Amide' in names[0] and 'Suzuki' in names[1]
    assert all(entry['template']['smarts'] for entry in out['reactions'])


# --- map numbers written into a drawn scheme --------------------------------

SCHEME = """layout: linear
structures:
  S1: {smiles: "CC(=O)Cl"}
  S2: {smiles: "CCN"}
  S3: {smiles: "CC(=O)NCC"}
steps:
  - substrates: [S1, S2]
    products: [S3]
"""


@pytest.fixture
def scheme(tmp_path):
    path = tmp_path / 'scheme.cdxml'
    api.render_scheme(yaml_text=SCHEME, output_path=str(path))
    return path


def number_labels(text):
    root = ET.fromstring(text.encode('utf-8'))
    out = []
    for t in root.find('page').iter('t'):
        value = ''.join(s.text or '' for s in t.iter('s')).strip()
        if t.get('id', '').isdigit() and value.isdigit() and t.get('MapNumber') == 'true':
            x, y = (float(v) for v in t.get('p').split()[:2])
            out.append((int(value), x, y))
    return out


def node_positions(text):
    root = ET.fromstring(text.encode('utf-8'))
    return [tuple(float(v) for v in n.get('p').split()[:2]) for n in root.find('page').iter('n') if n.get('p')]


def test_map_numbers_are_written_beside_the_mapped_atoms_of_the_drawing(scheme, tmp_path):
    out = tmp_path / 'numbered.cdxml'
    result = map_reaction_atoms({'cdxml': str(scheme)}, {'map_numbers_into_scheme': str(out)})
    assert result['scheme_path'] == str(out) and out.is_file()
    original, text = scheme.read_text(encoding='utf-8'), out.read_text(encoding='utf-8')
    labels = number_labels(text)
    mapped = len(result['map'])
    assert mapped == 6 and len(labels) == 2 * mapped
    assert sorted(n for n, _, _ in labels) == sorted(list(range(1, mapped + 1)) * 2)
    nodes = node_positions(original)
    for _, x, y in labels:
        nearest = min(((x - a) ** 2 + (y - b) ** 2) ** 0.5 for a, b in nodes)
        assert 4 < nearest < 22
    for line in original.splitlines():
        if line.strip():
            assert line in text


def test_the_numbered_scheme_is_still_a_valid_reaction_drawing(scheme, tmp_path):
    out = tmp_path / 'numbered.cdxml'
    map_reaction_atoms({'cdxml': str(scheme)}, {'map_numbers_into_scheme': str(out)})
    again = map_reaction_atoms({'cdxml': str(out)})
    assert again['status'] == 'complete'
    ids = re.findall(r'\bid="(\d+)"', out.read_text(encoding='utf-8'))
    assert len(ids) == len(set(ids))


def test_a_scheme_output_is_never_overwritten_and_needs_a_drawing(scheme, tmp_path):
    out = tmp_path / 'taken.cdxml'
    out.write_text('keep', encoding='utf-8')
    with pytest.raises(Exception):
        map_reaction_atoms({'cdxml': str(scheme)}, {'map_numbers_into_scheme': str(out)})
    assert out.read_text(encoding='utf-8') == 'keep'
    with pytest.raises(ValueError, match='drawn'):
        map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC', {'map_numbers_into_scheme': str(tmp_path / 'x.cdxml')})
    with pytest.raises(ValueError, match='cdxml'):
        map_reaction_atoms({'cdxml': str(scheme)}, {'map_numbers_into_scheme': str(tmp_path / 'x.txt')})
    with pytest.raises(ValueError, match='one drawn reaction'):
        map_reaction_atoms([{'cdxml': str(scheme)}], {'map_numbers_into_scheme': str(tmp_path / 'y.cdxml')})
