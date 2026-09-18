import json
from unittest import mock

import pytest

from compact_tool import run_compact


def test_full_evidence_stays_on_disk_and_summary_is_small(tmp_path):
    args=tmp_path/'args.json';args.write_text('{}')
    result={'ok':True,'result':{'ok':True,'raw_response':'x'*40000,'structures':[{'smiles':'CCO'}],
                              'warnings':['Inspect chirality']}}
    with mock.patch('compact_tool._worker',return_value=result):
        summary=run_compact('extract_structures_via_decimer_api',args,tmp_path/'result.json')
    assert len(json.dumps(summary).encode())<4096
    assert 'raw_response' not in json.dumps(summary) and 'CCO' not in json.dumps(summary)
    assert summary['review_required'] and summary['warning_count']==1
    assert json.loads((tmp_path/'result.json').read_text())==result


def test_nested_failure_and_output_protection(tmp_path):
    args=tmp_path/'args.json';args.write_text('{}');out=tmp_path/'result.json'
    with mock.patch('compact_tool._worker',return_value={'ok':True,'result':{'ok':False,'error':'bad input'}}):
        summary=run_compact('modify_molecule',args,out)
    assert not summary['ok'] and summary['review_required']
    before=out.read_bytes()
    with mock.patch('compact_tool._worker') as worker,pytest.raises(ValueError):
        run_compact('modify_molecule',args,out)
    worker.assert_not_called();assert out.read_bytes()==before


def test_unbounded_warning_text_stays_retrievable(tmp_path):
    args=tmp_path/'args.json';args.write_text('{}')
    with mock.patch('compact_tool._worker',return_value={'ok':True,'result':{'warnings':['x'*12000]*20}}):
        summary=run_compact('render_cdxml_files',args,tmp_path/'result.json')
    assert len(json.dumps(summary).encode())<4096
    assert summary['warning_count']==20 and summary['review_required']
    assert summary['details']['sha256']


def test_unknown_tool_rejected_without_execution(tmp_path):
    args=tmp_path/'args.json';args.write_text('{}')
    with mock.patch('compact_tool._worker') as worker,pytest.raises(ValueError):
        run_compact('execute_arbitrary_code',args,tmp_path/'result.json')
    worker.assert_not_called()
