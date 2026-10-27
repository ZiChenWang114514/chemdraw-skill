from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from cdxml_toolkit.mcp_runtime import artifact_safety
from cdxml_toolkit.mcp_runtime.scientific_tool import scientific_workflow
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

EXAMPLES = Path(__file__).resolve().parents[2] / 'docs' / 'examples' / 'scientific'


def _plot_spec(folder: Path) -> Path:
    data = folder / 'decay.csv'
    with data.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['time_min', 'fraction_remaining'])
        writer.writerows((t, math.exp(-0.06 * t)) for t in range(21))
    spec = folder / 'plot.json'
    spec.write_text(json.dumps({'input': data.name, 'x_column': 'time_min', 'y_column': 'fraction_remaining',
                                'x_label': 'Time / min', 'y_label': 'Fraction remaining',
                                'title': 'Simulated decay'}), encoding='utf-8')
    return spec


def test_a_file_workflow_publishes_one_cdxml_and_reports_its_path(tmp_path):
    target = tmp_path / 'plate.cdxml'

    result = scientific_workflow('tlc', str(EXAMPLES / 'tlc.json'), str(target))

    assert result['ok'] and result['outputs']['operation'] == 'tlc'
    assert target.is_file() and target.read_text(encoding='utf-8').lstrip().startswith('<?xml')
    assert result['outputs']['result']['output_path'] == str(target)
    assert [a['path'] for a in result['metadata']['artifacts']] == [str(target)]
    assert not [p for p in tmp_path.iterdir() if p != target]  # no staging leftovers


def test_a_directory_workflow_publishes_its_files_under_the_new_directory(tmp_path):
    spec = _plot_spec(tmp_path)
    target = tmp_path / 'plot-results'

    result = scientific_workflow('plot', str(spec), str(target))

    names = {a['path'] for a in result['metadata']['artifacts']}
    assert names and all(Path(p).parent == target for p in names)
    assert {p.suffix for p in map(Path, names)} >= {'.svg', '.csv'}


def test_existing_outputs_are_never_replaced(tmp_path):
    target = tmp_path / 'plate.cdxml'
    target.write_text('keep me', encoding='utf-8')

    with pytest.raises(artifact_safety.OutputExistsError):
        scientific_workflow('tlc', str(EXAMPLES / 'tlc.json'), str(target))

    assert target.read_text(encoding='utf-8') == 'keep me'
    folder = tmp_path / 'there'
    folder.mkdir()
    with pytest.raises(artifact_safety.OutputExistsError):
        scientific_workflow('plot', str(_plot_spec(tmp_path)), str(folder))


def test_inputs_are_checked_before_anything_is_written(tmp_path):
    with pytest.raises(ValueError, match='operation'):
        scientific_workflow('summon', str(EXAMPLES / 'tlc.json'), str(tmp_path / 'a.cdxml'))
    with pytest.raises(ValueError, match='spec'):
        scientific_workflow('tlc', str(tmp_path / 'missing.json'), str(tmp_path / 'a.cdxml'))
    with pytest.raises(ValueError, match=r'\.cdxml'):
        scientific_workflow('tlc', str(EXAMPLES / 'tlc.json'), str(tmp_path / 'a.png'))
    assert list(tmp_path.iterdir()) == []


def test_a_failing_workflow_leaves_no_output(tmp_path):
    spec = tmp_path / 'bad.json'
    spec.write_text('{"unexpected": true}', encoding='utf-8')
    target = tmp_path / 'plate.cdxml'

    with pytest.raises(Exception):
        scientific_workflow('tlc', str(spec), str(target))

    assert not target.exists()
    assert [p.name for p in tmp_path.iterdir()] == ['bad.json']


def test_tool_is_in_the_analysis_profile_and_the_full_set():
    assert 'scientific_workflow' in build_registry('analysis')
    assert 'scientific_workflow' in build_registry()
    assert 'scientific_workflow' not in build_registry('core')
