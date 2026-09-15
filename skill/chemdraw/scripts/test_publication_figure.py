"""Smoke tests for the data-driven Skill route."""
import csv
import json
from pathlib import Path
import tempfile
import unittest


class PublicationFigureTests(unittest.TestCase):
    def test_full_profile_exposes_workflow(self):
        from cdxml_toolkit.mcp_runtime.tool_registry import build_registry
        self.assertIn('publication_figure',build_registry())
        self.assertNotIn('publication_figure',build_registry('core'))

    def test_create_retains_blank_measurement_and_stable_id(self):
        from cdxml_toolkit.mcp_runtime.publication_figure import publication_figure
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with (root/'data.csv').open('w',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream);writer.writerow(['compound_id','smiles','yield'])
                # Aspirin is the existing Skill smoke-test fixture.
                writer.writerow(['aspirin','CC(=O)Oc1ccccc1C(=O)O',''])
            (root/'spec.json').write_text(json.dumps({'table':'data.csv','fields':[{'column':'yield'}],'native_render':False}))
            result=publication_figure('create',str(root/'spec.json'),str(root/'output'))
            self.assertTrue(result['ok'])
            project=json.loads((root/'output/project.json').read_text())
            self.assertEqual(project['compounds']['aspirin']['input']['values']['yield'],'')
