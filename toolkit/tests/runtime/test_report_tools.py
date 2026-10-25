import csv
import json
from pathlib import Path

import pytest

from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.report_tools import (
    check_reaction_balance, export_structures, molecule_report,
)
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
CAFFEINE = 'Cn1cnc2c1c(=O)n(C)c(=O)n2C'
ESTER = 'CC(=O)O.OCC>>CC(=O)OCC.O'


# --- molecule_report -------------------------------------------------------

def test_report_matches_published_values_for_aspirin_and_caffeine():
    result = molecule_report([{'smiles': ASPIRIN, 'label': 'aspirin'}, {'smiles': CAFFEINE}])
    assert result['ok'] and result['operation'] == 'molecule_report'
    aspirin, caffeine = result['results']
    assert aspirin['label'] == 'aspirin'
    assert aspirin['formula'] == 'C9H8O4'
    assert aspirin['mw'] == pytest.approx(180.159, abs=1e-3)
    assert aspirin['exact_mass'] == pytest.approx(180.04226, abs=1e-5)
    assert aspirin['inchikey'] == 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N'
    assert caffeine['inchikey'] == 'RYYVLZVUVIJVGH-UHFFFAOYSA-N'
    assert caffeine['tpsa'] == pytest.approx(61.82, abs=0.01)
    assert caffeine['logp'] == pytest.approx(-1.029, abs=0.005)
    assert (aspirin['hbd'], aspirin['hba'], aspirin['rotatable_bonds']) == (1, 3, 2)


def test_report_rules_and_flags():
    big = 'C' * 40  # 40-carbon alkane: breaks the molecular weight and logP limits
    result = molecule_report([{'smiles': ASPIRIN}, {'smiles': big}])
    aspirin, alkane = result['results']
    assert aspirin['lipinski']['violations'] == 0 and aspirin['veber']['pass']
    assert alkane['lipinski']['violations'] == 2
    assert alkane['lipinski']['rules']['logp_le_5'] is False


def test_adducts_use_electron_corrected_masses():
    adducts = {a['name']: a for a in molecule_report([{'smiles': ASPIRIN}])['results'][0]['adducts']}
    assert adducts['[M+H]+']['mz'] == pytest.approx(181.04954, abs=1e-4)
    assert adducts['[M+Na]+']['mz'] == pytest.approx(203.03151, abs=1e-4)
    assert adducts['[M-H]-']['mz'] == pytest.approx(179.03498, abs=1e-4)
    assert adducts['[M+2H]2+']['mz'] == pytest.approx((180.04226 + 2 * 1.007276) / 2, abs=1e-4)
    assert adducts['[M-H]-']['mode'] == 'negative'


def test_bromine_isotope_pattern_is_the_one_to_one_doublet():
    pattern = molecule_report([{'smiles': 'Brc1ccccc1'}])['results'][0]['isotope_pattern']
    # Peaks are scaled to the tallest one. 79Br is slightly more abundant than 81Br, so M leads
    # and M+2 is just under it; 13C adds a few percent at M+1.
    assert [p['offset'] for p in pattern] == [0, 1, 2, 3, 4]
    assert pattern[0]['relative_percent'] == pytest.approx(100.0)
    assert pattern[2]['relative_percent'] == pytest.approx(97.4, abs=1.0)
    assert pattern[1]['relative_percent'] == pytest.approx(6.5, abs=0.5)


def test_report_markdown_table_and_csv_file(tmp_path):
    out = tmp_path / 'props.csv'
    result = molecule_report([{'smiles': ASPIRIN, 'label': 'aspirin'}], output_path=str(out))
    assert '| aspirin |' in result['markdown']
    rows = list(csv.DictReader(out.open(encoding='utf-8')))
    assert rows[0]['formula'] == 'C9H8O4' and rows[0]['inchikey'].startswith('BSYNRYMUTX')
    with pytest.raises(Exception):
        molecule_report([{'smiles': ASPIRIN}], output_path=str(out))  # never overwrites


def test_report_reads_every_fragment_of_a_cdxml_file(tmp_path):
    scheme = tmp_path / 'ester.cdxml'
    api.render_scheme(yaml_text=_ester_yaml(), output_path=str(scheme))
    result = molecule_report([{'file': str(scheme), 'all_fragments': True}])
    assert [r['formula'] for r in result['results']] == ['C2H4O2', 'C2H6O', 'C4H8O2']
    assert all(r['source']['fragment_id'] for r in result['results'])


def test_report_rejects_generic_and_empty_input():
    with pytest.raises(ValueError):
        molecule_report([])
    with pytest.raises(ValueError, match='generic'):
        molecule_report([{'smiles': 'C[*]'}])


# --- check_reaction_balance ------------------------------------------------

def test_esterification_is_balanced_with_water():
    result = check_reaction_balance(ESTER)
    reaction = result['reactions'][0]
    assert result['balanced'] and reaction['balanced']
    assert reaction['charge'] == {'reactants': 0, 'products': 0}
    assert reaction['atom_economy_percent'] == pytest.approx(88.106 / (60.052 + 46.069) * 100, abs=0.01)
    assert reaction['mass_balance']['difference'] == pytest.approx(0, abs=0.01)


def test_missing_byproduct_is_named():
    reaction = check_reaction_balance('CC(=O)O.OCC>>CC(=O)OCC')['reactions'][0]
    assert not reaction['balanced']
    assert reaction['missing_from_products'] == {'formula': 'H2O', 'common_name': 'water'}
    assert 'missing_from_reactants' not in reaction


def test_missing_reactant_atoms_are_named_on_the_other_side():
    reaction = check_reaction_balance('CC(=O)OCC>>CC(=O)O')['reactions'][0]
    assert reaction['missing_from_products']['formula'] == 'C2H4'
    reaction = check_reaction_balance('CC(=O)O>>CC(=O)OCC')['reactions'][0]
    assert reaction['missing_from_reactants']['formula'] == 'C2H4'


def test_integer_coefficients_are_suggested_for_combustion():
    reaction = check_reaction_balance('C.O=O>>O=C=O.O')['reactions'][0]
    assert not reaction['balanced']
    assert reaction['suggested_coefficients'] == {'reactants': [1, 2], 'products': [1, 2]}
    given = check_reaction_balance({'reactants': [{'smiles': 'C'}, {'smiles': 'O=O', 'coefficient': 2}],
                                    'products': [{'smiles': 'O=C=O'}, {'smiles': 'O', 'coefficient': 2}]})
    assert given['balanced']


def test_charge_participates_in_the_balance():
    reaction = check_reaction_balance('[Fe+3].[Fe]>>[Fe+2]')['reactions'][0]
    assert not reaction['balanced']
    assert reaction['charge'] == {'reactants': 3, 'products': 2}
    assert reaction['suggested_coefficients'] == {'reactants': [2, 1], 'products': [3]}  # 2 Fe3+ + Fe -> 3 Fe2+


def test_isotope_labels_are_balanced_separately():
    reaction = check_reaction_balance('CC(=O)O>>[2H]C(=O)O')['reactions'][0]
    assert not reaction['balanced']
    assert 'composition' in reaction


def test_agents_are_listed_but_not_counted():
    result = check_reaction_balance('CC(=O)O.OCC>OS(=O)(=O)O>CC(=O)OCC.O')
    reaction = result['reactions'][0]
    assert reaction['balanced'] and reaction['agents'][0]['formula'] == 'H2O4S'


def test_records_with_labels_and_stoichiometry():
    result = check_reaction_balance(
        {'reactants': [{'smiles': 'CC(=O)O', 'label': 'acetic acid'},
                       {'smiles': 'OCC', 'label': 'ethanol', 'equiv': 3, 'density_g_ml': 0.789}],
         'products': [{'smiles': 'CC(=O)OCC', 'label': 'ethyl acetate', 'isolated_mg': 150},
                      {'smiles': 'O'}]},
        options={'scale_mmol': 2.0})
    rows = result['reactions'][0]['stoichiometry']
    assert by_name_label(rows, 'acetic acid')['mass_mg'] == pytest.approx(120.10, abs=0.05)
    ethanol = by_name_label(rows, 'ethanol')
    assert ethanol['mmol'] == pytest.approx(6.0) and ethanol['equiv'] == 3
    assert ethanol['volume_ml'] == pytest.approx(6.0 * 46.069 / 789.0, abs=1e-3)
    product = by_name_label(rows, 'ethyl acetate')
    assert product['theoretical_mg'] == pytest.approx(176.21, abs=0.05)
    assert product['yield_percent'] == pytest.approx(150 / 176.21 * 100, abs=0.1)


def by_name_label(rows, label):
    return next(row for row in rows if row['label'] == label)


def test_limiting_reagent_can_be_chosen():
    options = {'scale_mmol': 1.0, 'limiting': 1}
    rows = check_reaction_balance(ESTER, options=options)['reactions'][0]['stoichiometry']
    assert [row['equiv'] for row in rows if row['role'] == 'reactant'] == [1.0, 1.0]
    with pytest.raises(ValueError, match='limiting'):
        check_reaction_balance(ESTER, options={'scale_mmol': 1.0, 'limiting': 5})


def test_balance_reads_steps_from_a_cdxml_scheme(tmp_path):
    scheme = tmp_path / 'ester.cdxml'
    api.render_scheme(yaml_text=_ester_yaml(), output_path=str(scheme))
    result = check_reaction_balance({'cdxml': str(scheme)})
    reaction = result['reactions'][0]
    assert reaction['step_id'] and not result['balanced']
    assert reaction['missing_from_products']['formula'] == 'H2O'
    assert [s['formula'] for s in reaction['reactants']] == ['C2H4O2', 'C2H6O']
    assert [s['formula'] for s in reaction['agents']] == []  # text above the arrow is not a structure


def test_balance_rejects_unusable_input(tmp_path):
    for bad in ('C', 'CC>>', '>>CC', 'not a reaction'):
        with pytest.raises(ValueError):
            check_reaction_balance(bad)
    bare = tmp_path / 'bare.cdxml'
    api.draw_molecule({'smiles': 'CCO'}, str(bare))
    with pytest.raises(ValueError, match='reaction step'):
        check_reaction_balance({'cdxml': str(bare)})
    with pytest.raises(ValueError, match='generic'):
        check_reaction_balance('C[*]>>C')


# --- export_structures -----------------------------------------------------

def test_export_lists_every_cdxml_fragment_with_its_id(tmp_path):
    scheme = tmp_path / 'ester.cdxml'
    api.render_scheme(yaml_text=_ester_yaml(), output_path=str(scheme))
    result = export_structures(str(scheme))
    rows = result['structures']
    assert [r['smiles'] for r in rows] == ['CC(=O)O', 'CCO', 'CCOC(C)=O']
    assert rows[1]['inchikey'] == 'LFQSCWFLJHTTHZ-UHFFFAOYSA-N'
    assert all(r['fragment_id'] for r in rows) and result['count'] == 3


def test_export_files_in_each_format(tmp_path):
    scheme = tmp_path / 'ester.cdxml'
    api.render_scheme(yaml_text=_ester_yaml(), output_path=str(scheme))
    for suffix, check in (
        ('.csv', lambda text: 'inchikey' in text.splitlines()[0] and 'CCO' in text),
        ('.json', lambda text: len(json.loads(text)['structures']) == 3),
        ('.smi', lambda text: text.splitlines()[1].split()[0] == 'CCO'),
        ('.sdf', lambda text: text.count('$$$$') == 3 and '> <InChIKey>' in text),
        ('.md', lambda text: text.startswith('| #')),
    ):
        out = tmp_path / f'out{suffix}'
        export_structures(str(scheme), output_path=str(out))
        assert check(out.read_text(encoding='utf-8')), suffix


def test_export_round_trips_sdf_and_smiles_records(tmp_path):
    sdf = tmp_path / 'two.sdf'
    export_structures([{'smiles': ASPIRIN, 'label': 'aspirin'}, {'smiles': CAFFEINE, 'label': 'caffeine'}],
                      output_path=str(sdf))
    again = export_structures(str(sdf))
    assert [r['formula'] for r in again['structures']] == ['C9H8O4', 'C8H10N4O2']
    assert [r['label'] for r in again['structures']] == ['aspirin', 'caffeine']


def test_export_can_include_molblocks_and_flags_generic_atoms(tmp_path):
    result = export_structures([{'smiles': ASPIRIN}, {'smiles': 'C[*]'}], options={'include_molblock': True})
    good, generic = result['structures']
    assert 'V2000' in good['molblock'] or 'V3000' in good['molblock']
    assert generic['inchi'] is None and generic['smiles'] == '*C'
    assert any('InChI' in w for w in result['warnings'])


def test_export_refuses_binary_and_unknown_files(tmp_path):
    binary = tmp_path / 'figure.cdx'
    binary.write_bytes(b'VjCD0100')
    with pytest.raises(ValueError, match='convert_cdx_cdxml'):
        export_structures(str(binary))
    with pytest.raises(ValueError):
        export_structures(str(tmp_path / 'missing.cdxml'))
    with pytest.raises(ValueError):
        export_structures([])


# --- registration ----------------------------------------------------------

def test_tools_are_registered_in_the_full_profile_only():
    names = {'molecule_report', 'check_reaction_balance', 'export_structures'}
    assert names <= set(build_registry())
    assert not names & set(build_registry('core'))
    assert all(build_registry()[n].resource_class is None for n in names)


def _ester_yaml():
    return ('layout: linear\nstructures:\n  A: {smiles: "CC(=O)O"}\n  B: {smiles: "OCC"}\n'
            '  P: {smiles: "CC(=O)OCC"}\nsteps:\n  - substrates: [A, B]\n    products: [P]\n'
            '    above_arrow:\n      text: ["H2SO4"]\n')
