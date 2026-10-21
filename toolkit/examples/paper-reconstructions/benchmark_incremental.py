"""Controlled native-save replay, not an end-to-end recognition or agent benchmark."""
import argparse
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET
from collections import Counter

from cdxml_toolkit.mcp_runtime import reconstruction as r, figure_validation as fv


def run(cdxml, source_image, output):
    output=Path(output).resolve()
    if output.exists(): raise ValueError('Use a new output directory')
    output.mkdir(parents=True)
    expected=Counter(m['semantic_key'] for m in fv.inspect_document(cdxml)['molecules'])
    results={}
    for strategy in ('full_each_edit','incremental'):
        folder=output/strategy;folder.mkdir()
        started=time.perf_counter();calls=[]
        worker=fv._worker
        def observed(name,kwargs):
            calls.append(name)
            return worker(name,kwargs)
        fv._worker=observed
        try:
            previous=r._capture(cdxml,source_image)
            tree=ET.parse(cdxml)
            snapshot=previous
            text_ids=[key[3:] for key,node in previous['scene'].items()
                      if key.startswith('id:') and node['tag']=='t' and node['owner'] is None]
            if not text_ids: raise ValueError('Fixture needs non-atom text')
            node=next(n for n in tree.iter('t') if n.get('id')==text_ids[0])
            run=node.find('s')
            if run is None: raise ValueError('Fixture needs a text run')
            original=run.get('size','10')
            for i,size in enumerate((str(float(original)+1),str(float(original)+2),original)):
                run.set('size',size)
                candidate=folder/f'edit-{i}.cdxml'
                tree.write(candidate,encoding='UTF-8',xml_declaration=True)
                snapshot=r._capture(str(candidate),source_image)
                plan=r._plan(previous,snapshot)
                if strategy=='full_each_edit':
                    fv.validate_figure(str(candidate),str(folder/f'check-{i}'),native=True)
                    report=r._read(folder/f'check-{i}/report.json')
                    assert report['native']['comparison']['semantic_inventory_preserved']
                else:
                    r._local(snapshot,plan,str(folder/f'check-{i}'))
                previous=snapshot
            final=folder/'final-check'
            fv.validate_figure(str(candidate),str(final),native=True)
            final_report=r._read(final/'report.json')
            assert final_report['native']['comparison']['semantic_inventory_preserved']
            assert Counter(m['semantic_key'] for m in final_report['native']['saved']['molecules'])==expected
            results[strategy]=dict(fixture_sha256=r._hash(cdxml),model='none: deterministic Python replay',
                versions={'rdkit':r.rdBase.rdkitVersion,'native_host':'same_host_same_run'},
                acceptance_contract='known-target multiset plus final native save; no image-recognition accuracy claim',
                accepted=True,elapsed_seconds=time.perf_counter()-started,
                native_calls=len(calls),native_operations=dict(Counter(calls)),recognition_calls=0,
                edits=3,agent_tokens=None,source_image_sha256=r._hash(source_image))
        finally:
            fv._worker=worker
    comparison=r._benchmark(results['full_each_edit'],results['incremental'])
    comparison['scope']='Three caption-size edits; native-save scheduling only. Not end-to-end agent speed or accuracy.'
    r._write(output/'benchmark.json',comparison)
    return comparison


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cdxml');parser.add_argument('source_image');parser.add_argument('output')
    args=parser.parse_args()
    print(json.dumps(run(args.cdxml,args.source_image,args.output),indent=2))
