"""Call every toolkit tool once, the way `cdx.py call` does, and report which ones work on this machine.

Run it in the toolkit runtime:  python cdx.py py <skill>/scripts/smoke_all_tools.py --output-dir NEW_DIR

The inputs are the Skill's bundled assets and the files earlier cases write, so the cases run in order.
Work stays offline (CHEMDRAW_OFFLINE=1) unless --network is given; a case that needs ChemDraw, ChemScript,
an optional engine or the network is skipped, with the reason, when this machine lacks it. Tools that read
an LCMS report run only with --lcms-pdf. Results go to NEW_DIR/report.json; the exit code is 1 when any
case failed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets'
ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
SALICYLIC = 'OC(=O)c1ccccc1O'
ESTER = 'CC(=O)O.OCC>>CC(=O)OCC.O'
AMIDE = ('CC(=O)Cl.Nc1ccccc1', 'CC(=O)Nc1ccccc1')
OCSR = ('decimer-local', 'molscribe', 'molnextr', 'molparser', 'molvec')


def _ocsr(ctx):
    return ','.join(name for name in OCSR if ctx.engines.get(name))


def _rdf(ctx):
    """A one-reaction SciFinder-style RDF (V3000 blocks), written with RDKit from the esterification."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    def block(smiles, name):
        mol = Chem.MolFromSmiles(smiles)
        AllChem.Compute2DCoords(mol)
        mol.SetProp('_Name', name)
        return Chem.MolToMolBlock(mol, forceV3000=True)

    parts = ['$RDFILE 1', '$DATM    11/03/2026 12:00', '$RFMT $RIREG 1', '$RXN', '', '  SMOKE', '', '  2  1']
    for smiles, name in (('CC(=O)O', 'acetic acid'), ('OCC', 'ethanol'), ('CC(=O)OCC', 'ethyl acetate')):
        parts += ['$MOL', block(smiles, name).rstrip('\n')]
    parts += ['$DTYPE RXN:VARIATION(1):STEPNO', '$DATUM 1']
    path = ctx.out / 'reaction.rdf'
    path.write_text('\n'.join(parts) + '\n', encoding='utf-8')
    return {'input_path': str(path)}


def _template(ctx):
    """A one-slide PPTX with a text placeholder and a ChemDraw placeholder, and the manifest that fills it."""
    from pptx import Presentation
    from pptx.util import Inches
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    for text, top in (('{{TITLE}}', 0.5), ('{{MOL}}', 2.0)):
        slide.shapes.add_textbox(Inches(1), Inches(top), Inches(4), Inches(1)).text_frame.text = text
    template = ctx.out / 'template.pptx'
    deck.save(template)
    manifest = ctx.out / 'template-manifest.json'
    manifest.write_text(json.dumps({'slots': [{'placeholder': '{{TITLE}}', 'value': 'Smoke test'},
                                              {'placeholder': '{{MOL}}', 'type': 'cdxml', 'file': 'aspirin.cdxml'}]}),
                        encoding='utf-8')
    return {'template_path': str(template), 'manifest_path': str(manifest), 'output_path': str(ctx.out / 'filled.pptx')}


def _replacement(ctx):
    inspected = json.loads((ctx.out / 'inspect' / 'manifest.json').read_text(encoding='utf-8'))
    objects = inspected.get('objects') or []
    manifest = ctx.out / 'replace-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'source_sha256': inspected['source_sha256'],
                                    'replacements': [{'object_id': objects[0]['object_id'],
                                                      'replacement_cdxml': 'figure.cdxml'}]}), encoding='utf-8')
    return {'input_path': str(ctx.out / 'one.pptx'), 'replacements_manifest': str(manifest),
            'output_path': str(ctx.out / 'replaced.pptx'), 'render_pdf_preview': False}


def _experiment(ctx):
    folder = ctx.out / 'experiment'
    folder.mkdir(exist_ok=True)
    shutil.copy2(ctx.out / 'figure.cdxml', folder / 'SMOKE-001.cdxml')
    return folder


def _experiments(ctx):
    folder = ctx.out / 'experiments'
    folder.mkdir(exist_ok=True)
    shutil.copy2(ctx.out / 'reaction.json', folder / 'SMOKE-001.json')
    return {'smiles': 'CC(=O)OCC', 'experiment_dir': str(folder)}


def _brief():
    return {'species': [{'id': 'acid', 'smiles': 'CC(=O)O'}, {'id': 'alcohol', 'smiles': 'OCC'},
                        {'id': 'ester', 'smiles': 'CC(=O)OCC'}, {'id': 'water', 'smiles': 'O'}],
            'steps': [{'substrates': ['acid', 'alcohol'], 'products': ['ester', 'water'],
                       'above': ['H2SO4 (cat.)'], 'below': ['reflux, 2 h'], 'yield': '85%'}]}


def _p(ctx, name):
    return str(ctx.out / name)


# Each case: tool, what it needs from the machine, and its arguments (a dict, or a function of the context).
# needs: chemdraw (native ChemDraw automation), chemscript (ChemDraw's ChemScript SDK), network,
# lcms (a report PDF from --lcms-pdf), engine:NAME (an installed optional engine), ocsr (any local OCSR engine).
CASES = [
    {'tool': 'get_toolkit_capabilities', 'args': {'detail': 'summary'}},
    {'tool': 'diagnose_runtime', 'args': {}},
    {'tool': 'list_engines', 'args': {}},
    {'tool': 'chemdraw_inventory', 'args': {'layer': 'com', 'limit': 3}},
    {'tool': 'resolve_name', 'args': lambda c: {'query': 'Et3N', 'use_network': c.network}},
    {'tool': 'draw_molecule', 'args': lambda c: {'mol_json': {'smiles': ASPIRIN, 'name': 'aspirin'},
                                                 'output_path': _p(c, 'aspirin.cdxml')}},
    {'tool': 'modify_molecule', 'args': {'mol_json': {'smiles': ASPIRIN}, 'operation': 'analyze'}},
    {'tool': 'draw_figure', 'args': lambda c: {'brief': _brief(), 'output_path': _p(c, 'figure.cdxml')}},
    {'tool': 'chemdraw_object', 'args': lambda c: {'op': 'list', 'input_path': _p(c, 'aspirin.cdxml')}},
    {'tool': 'convert_cdx_cdxml', 'args': lambda c: {'input_path': _p(c, 'aspirin.cdxml'),
                                                     'output_path': _p(c, 'aspirin.cdx')}},
    {'tool': 'render_to_png', 'needs': ['chemdraw'],
     'args': lambda c: {'cdxml_path': _p(c, 'aspirin.cdxml'), 'output_path': _p(c, 'aspirin.png')}},
    {'tool': 'render_cdxml_files', 'needs': ['chemdraw'],
     'args': lambda c: {'input_paths': [_p(c, 'figure.cdxml')], 'output_dir': _p(c, 'rendered')}},
    {'tool': 'parse_scheme', 'args': lambda c: {'cdxml_path': _p(c, 'figure.cdxml'),
                                                'output_path': _p(c, 'scheme.json')}},
    {'tool': 'parse_reaction', 'args': lambda c: {'cdxml': _p(c, 'figure.cdxml'),
                                                  'output_path': _p(c, 'reaction.json')}},
    {'tool': 'summarize_reaction', 'args': lambda c: {'json_path': _p(c, 'reaction.json')}},
    {'tool': 'render_scheme', 'args': lambda c: {'json_path': _p(c, 'reaction.json'),
                                                 'output_path': _p(c, 'from-json.cdxml')}},
    {'tool': 'search_compound', 'args': _experiments},
    {'tool': 'clean_scheme_layout', 'args': lambda c: {'input_path': _p(c, 'figure.cdxml'),
                                                       'output_path': _p(c, 'figure-clean.cdxml'),
                                                       'render_preview': False}},
    {'tool': 'polish_reaction_scheme', 'args': lambda c: {'input_path': _p(c, 'figure.cdxml'),
                                                          'output_path': _p(c, 'figure-polished.cdxml'),
                                                          'render_preview': False}},
    {'tool': 'merge_reaction_schemes', 'args': lambda c: {'input_paths': [_p(c, 'figure.cdxml'),
                                                                          _p(c, 'figure-clean.cdxml')],
                                                          'output_path': _p(c, 'merged.cdxml'),
                                                          'render_preview': False}},
    {'tool': 'segment_large_scheme', 'args': lambda c: {'cdxml_path': _p(c, 'figure.cdxml'),
                                                        'output_path': _p(c, 'segments.json')}},
    {'tool': 'discover_experiment_files', 'args': lambda c: {'input_dir': str(_experiment(c)),
                                                             'experiment': 'SMOKE-001'}},
    {'tool': 'assemble_lab_book', 'args': lambda c: {'input_dir': str(_experiment(c)), 'experiment': 'SMOKE-001',
                                                     'output_path': _p(c, 'lab-book.txt')}},
    {'tool': 'format_lab_entry', 'args': lambda c: {
        'entries_json': [{'type': 'text', 'content': 'Acetic acid and ethanol were heated at reflux.'},
                         {'type': 'nmr', 'content': '1H NMR (400 MHz, CDCl3) δ 4.12 (q, 2H), 2.05 (s, 3H), 1.26 (t, 3H).'}],
        'output_path': _p(c, 'entry.txt')}},
    {'tool': 'parse_scifinder_rdf', 'args': _rdf},
    {'tool': 'export_structures', 'args': lambda c: {'source': _p(c, 'figure.cdxml'),
                                                     'output_path': _p(c, 'structures.csv')}},
    {'tool': 'molecule_report', 'args': {'molecules': [{'smiles': ASPIRIN, 'label': 'aspirin'}]}},
    {'tool': 'rdkit_workbench', 'args': {'molecules': [{'smiles': 'CC(O)CC'}], 'operation': 'stereoisomers'}},
    {'tool': 'hrms_line', 'args': {'molecules': [{'smiles': ASPIRIN, 'adduct': '[M+Na]+', 'found_mz': 203.0315}]}},
    {'tool': 'characterization_text', 'args': {'compounds': [{'smiles': ASPIRIN, 'appearance': 'white solid',
                                                               'mp': '134-136'}]}},
    {'tool': 'check_reaction_balance', 'args': {'reaction': ESTER, 'options': {'scale_mmol': 1}}},
    {'tool': 'map_reaction_atoms', 'args': {'reaction': ESTER, 'options': {'method': 'mcs'}}},
    {'tool': 'si_materials_tables', 'args': {'reactions': [ESTER]}},
    {'tool': 'route_summary', 'args': {'steps': [
        {'label': '1', 'yield_percent': 80, 'input_mg': 1000, 'product_mg': 500, 'used_mg': 400},
        {'label': '2', 'yield_percent': 70, 'input_mg': 800, 'product_mg': 300}]}},
    {'tool': 'compose_chemical_figure', 'args': lambda c: {'manifest_path': str(ASSETS / 'paper-replica' / 'example' / 'figure.json'),
                                                           'output_path': _p(c, 'composed.cdxml')}},
    {'tool': 'compare_figure_images', 'args': lambda c: {
        'reference_path': str(ASSETS / 'acs1996' / 'example.png'),
        'candidate_path': str(ASSETS / 'acs1996' / 'example.png'), 'output_path': _p(c, 'image-compare.json')}},
    {'tool': 'scientific_workflow', 'args': lambda c: {'operation': 'tlc', 'spec_path': str(ASSETS / 'scientific' / 'tlc.json'),
                                                       'output_path': _p(c, 'tlc.cdxml')}},
    {'tool': 'publication_figure', 'needs': ['chemdraw'],
     'args': lambda c: {'operation': 'create', 'spec_path': str(ASSETS / 'publication' / 'sar.json'),
                        'output_dir': _p(c, 'sar')}},
    {'tool': 'markush_validate', 'args': {'spec_path': str(ASSETS / 'markush' / 'indole-macrocycle.json')}},
    {'tool': 'markush_enumerate', 'args': {'spec_path': str(ASSETS / 'markush' / 'indole-macrocycle.json'), 'count': 2}},
    {'tool': 'markush_compile', 'args': lambda c: {
        'spec_path': str(ASSETS / 'markush' / 'indole-macrocycle.json'), 'output_dir': _p(c, 'markush'),
        'layout_path': str(ASSETS / 'markush' / 'indole-macrocycle.layout.json'), 'render': c.has('chemdraw')}},
    {'tool': 'markush_detect', 'args': lambda c: {'image_path': str(ASSETS / 'acs1996' / 'example.png'),
                                                  'output_dir': _p(c, 'markush-detect')}},
    {'tool': 'embed_cdxml_in_office', 'needs': ['chemdraw'],
     'args': lambda c: {'cdxml_path': _p(c, 'aspirin.cdxml'), 'office_path': _p(c, 'one.pptx')}},
    {'tool': 'batch_embed_cdxml_in_office', 'needs': ['chemdraw'],
     'args': lambda c: {'cdxml_paths': [_p(c, 'aspirin.cdxml'), _p(c, 'figure.cdxml')],
                        'output_path': _p(c, 'batch.docx')}},
    {'tool': 'inspect_chemdraw_objects_in_office', 'needs': ['chemdraw'],
     'args': lambda c: {'input_path': _p(c, 'one.pptx'), 'output_dir': _p(c, 'inspect')}},
    {'tool': 'extract_cdxml_from_office', 'needs': ['chemdraw'],
     'args': lambda c: {'file_path': _p(c, 'batch.docx'), 'output_dir': _p(c, 'extracted')}},
    {'tool': 'replace_chemdraw_objects_in_office', 'needs': ['chemdraw'], 'args': _replacement},
    {'tool': 'fill_office_template', 'needs': ['chemdraw'], 'args': _template},
    {'tool': 'stoichiometry_grid', 'needs': ['chemdraw'],
     'args': lambda c: {'source': ESTER, 'mode': 'analyze', 'output_path': _p(c, 'stoichiometry.cdxml')}},
    {'tool': 'stoichiometry_grid', 'needs': ['chemdraw'],
     'args': lambda c: {'source': _p(c, 'stoichiometry.cdxml'), 'mode': 'read'}},
    {'tool': 'chemdraw_com_call', 'needs': ['chemdraw'], 'args': lambda c: {'allow_file_io': True, 'program': [
        {'op': 'get', 'member': 'name'},
        {'op': 'get', 'member': 'Documents', 'as': 'docs'},
        {'op': 'call', 'target': 'docs', 'member': 'Open', 'args': [_p(c, 'aspirin.cdxml')], 'as': 'doc'},
        {'op': 'get', 'target': 'doc', 'member': 'Saved'}]}},
    {'tool': 'compare_molecules', 'needs': ['chemscript'], 'args': {'molecule_a': ASPIRIN, 'molecule_b': SALICYLIC}},
    {'tool': 'batch_compare_molecules', 'needs': ['chemscript'],
     'args': {'pairs': [{'mol1': ASPIRIN, 'mol2': SALICYLIC, 'pair_id': 'a'}, {'mol1': ASPIRIN, 'mol2': ASPIRIN,
                                                                               'pair_id': 'b'}]}},
    {'tool': 'structure_to_name', 'needs': ['chemscript'], 'args': {'molecules': [{'smiles': ASPIRIN}]}},
    {'tool': 'chemdraw_chemical_properties', 'needs': ['chemscript'], 'args': {'molecules': [{'smiles': ASPIRIN}]}},
    {'tool': 'inspect_chemscript_sdk', 'needs': ['chemscript'], 'args': {'query': 'StructureData', 'limit': 5}},
    {'tool': 'execute_chemscript_sdk', 'needs': ['chemscript'], 'args': {'program': [
        {'op': 'call_static', 'type': 'StructureData', 'member': 'LoadData', 'args': [ASPIRIN, 'chemical/x-smiles'],
         'as': 'mol'},
        {'op': 'get', 'target': 'mol', 'member': 'Weight'}]}},
    {'tool': 'parse_analysis_file', 'needs': ['lcms'], 'args': lambda c: {'pdf_path': c.lcms[0]}},
    {'tool': 'analyze_lcms_series', 'needs': ['lcms2'],
     'args': lambda c: {'files': c.lcms, 'output_path': _p(c, 'lcms-series.json')}},
    {'tool': 'extract_structures_via_decimer_api', 'note': 'offline: the no-upload preflight, which must refuse',
     'refusal': lambda c: None if c.network else 'Remote upload refused',
     'args': lambda c: {'image_path': str(ASSETS / 'acs1996' / 'example.png'), 'confirm_upload': c.network}},
    {'tool': 'extract_structures_from_image', 'needs': ['engine:decimer-local'],
     'args': {'image_path': str(ASSETS / 'acs1996' / 'example.png'), 'detect_labels': False}},
    {'tool': 'recognize_structure', 'needs': ['ocsr'],
     'args': lambda c: {'image_path': str(ASSETS / 'acs1996' / 'example.png'), 'engines': _ocsr(c)}},
    {'tool': 'extract_structures_from_document', 'needs': ['ocsr'],
     'args': lambda c: {'path': str(ASSETS / 'acs1996' / 'example.png'), 'out_dir': _p(c, 'document'),
                        'engines': _ocsr(c)}},
    {'tool': 'predict_retrosynthesis', 'needs': ['engine:aizynthfinder'],
     'args': {'product': 'CC(=O)Nc1ccc(O)cc1', 'engine': 'aizynthfinder', 'count': 3}},
    {'tool': 'predict_retrosynthesis', 'needs': ['engine:retrochimera'],
     'args': {'product': 'CC(=O)Nc1ccc(O)cc1', 'engine': 'retrochimera', 'count': 3}},
    {'tool': 'predict_retrosynthesis', 'needs': ['engine:reactiont5-retro'],
     'args': {'product': 'CC(=O)Nc1ccc(O)cc1', 'engine': 'reactiont5-retro', 'count': 3}},
    {'tool': 'predict_retrosynthesis', 'needs': ['engine:synplanner'],
     'args': {'product': 'CC(=O)Nc1ccc(O)cc1', 'engine': 'synplanner', 'steps': 'multi', 'time_limit': 30}},
    {'tool': 'predict_products', 'needs': ['engine:reactiont5-forward'],
     'args': {'reactants': AMIDE[0], 'engine': 'reactiont5-forward', 'count': 2}},
    {'tool': 'predict_conditions', 'needs': ['engine:reacon'],
     'args': {'reactants': AMIDE[0], 'products': AMIDE[1], 'engine': 'reacon', 'count': 2}},
    {'tool': 'predict_nmr', 'needs': ['engine:magnet'], 'args': {'smiles': 'CCOC(C)=O', 'engine': 'magnet'}},
    {'tool': 'predict_nmr', 'needs': ['engine:nmrnet-pp'], 'args': {'smiles': 'CCOC(C)=O', 'engine': 'nmrnet-pp'}},
]


class Context:
    def __init__(self, out, network, lcms, machine, engines):
        self.out, self.network, self.lcms, self.machine, self.engines = out, network, lcms, machine, engines

    def has(self, need):
        if need.startswith('engine:'):
            return bool(self.engines.get(need.split(':', 1)[1]))
        if need == 'ocsr':
            return bool(_ocsr(self))
        if need == 'network':
            return self.network
        if need == 'lcms':
            return bool(self.lcms)
        if need == 'lcms2':
            return len(self.lcms) >= 2
        return bool(self.machine.get(need))


def machine():
    """What this computer offers: ChemDraw automation and ChemScript (present with desktop ChemDraw on Windows)."""
    from cdxml_toolkit.mcp_runtime.extended_tools import diagnose_runtime
    capabilities = diagnose_runtime().get('outputs', {}).get('capabilities', {})
    status = {name: (value or {}).get('status') for name, value in capabilities.items()}
    native = status.get('chemdraw_com') == 'available' or (sys.platform == 'darwin' and status.get('chemdraw') == 'available')
    return {'chemdraw': native, 'chemscript': native}


def run(ctx, cases, only=None):
    sys.path.insert(0, str(HERE))
    import cdx
    rows = []
    for index, case in enumerate(cases, 1):
        tool = case['tool']
        if only and tool not in only:
            continue
        row = {'case': index, 'tool': tool}
        if case.get('note'):
            row['note'] = case['note']
        missing = [need for need in case.get('needs', []) if not ctx.has(need)]
        if missing:
            rows.append({**row, 'status': 'skipped', 'reason': 'needs ' + ', '.join(missing)})
            continue
        started = time.monotonic()
        try:
            args = case['args'](ctx) if callable(case['args']) else case['args']
            summary = cdx._summary(tool, cdx._worker(tool, args))
        except Exception as exc:  # a broken case input is a failure of this run, not of the harness
            summary = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
        refusal = case['refusal'](ctx) if case.get('refusal') else None
        if refusal:  # the call must be refused with this message, and nothing else counts
            passed = not summary['ok'] and refusal in str(summary.get('error'))
        else:
            passed = summary['ok']
        row.update(status='pass' if passed else 'fail', seconds=round(time.monotonic() - started, 1))
        if not passed:
            row['error'] = summary.get('error') or 'the call succeeded but was expected to be refused'
        rows.append(row)
        print(f"{row['status']:7s} {tool}" + (f"  {str(row.get('error'))[:160]}" if row.get('error') else ''),
              file=sys.stderr, flush=True)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output-dir', required=True, help='a new folder for the outputs and report.json')
    parser.add_argument('--network', action='store_true', help='allow network lookups and the DECIMER upload')
    parser.add_argument('--lcms-pdf', nargs='+', default=[], help='LCMS report PDFs for the analysis tools')
    parser.add_argument('--only', help='comma-separated tool names to run')
    ns = parser.parse_args(argv)
    out = Path(ns.output_dir).resolve()
    if out.exists():
        parser.error(f'{out} exists; give a new folder')
    out.mkdir(parents=True)
    if not ns.network:
        os.environ['CHEMDRAW_OFFLINE'] = '1'
    from cdxml_toolkit.engines.env import available
    ctx = Context(out, ns.network, [str(Path(p).resolve()) for p in ns.lcms_pdf], machine(), available())
    rows = run(ctx, CASES, set(ns.only.split(',')) if ns.only else None)
    counts = {status: sum(r['status'] == status for r in rows) for status in ('pass', 'fail', 'skipped')}
    report = {'counts': counts, 'network': ns.network, 'machine': ctx.machine,
              'engines': sorted(name for name, ok in ctx.engines.items() if ok), 'cases': rows}
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'counts': counts, 'report': str(out / 'report.json')}, indent=2))
    return 1 if counts['fail'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
