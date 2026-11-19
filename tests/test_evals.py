"""The evaluation sets are well formed and their scorer cannot be passed by an empty answer."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
sys.path.insert(0, str(EVALS))

import run  # noqa: E402
import score  # noqa: E402

TASKS = json.loads((EVALS / "tasks.json").read_text(encoding="utf-8"))
TRIGGERS = json.loads((EVALS / "triggers.json").read_text(encoding="utf-8"))


class ScorerTests(unittest.TestCase):
    def test_structures_are_compared_as_compounds(self):
        self.assertTrue(score.same_structure("OC(=O)c1ccccc1OC(C)=O", "CC(=O)Oc1ccccc1C(=O)O"))
        self.assertFalse(score.same_structure("CC(=O)Oc1ccccc1C(=O)OC", "CC(=O)Oc1ccccc1C(=O)O"))
        self.assertFalse(score.same_structure("N[C@H](CS)C(=O)O", "N[C@@H](CS)C(=O)O"))  # the enantiomer
        self.assertFalse(score.same_structure("NC(CS)C(=O)O", "N[C@@H](CS)C(=O)O"))  # stereo left out
        self.assertFalse(score.same_structure("CCN(CC)CC", "CCN(CC)CC.Cl"))  # a component left out
        for empty in (None, "", "not a smiles", 7):
            self.assertFalse(score.same_structure(empty, "CCO"))
        with self.assertRaises(ValueError):
            score.same_structure("CCO", "not a smiles")

    def test_numbers_and_safety_answers_need_positive_evidence(self):
        self.assertTrue(score.close_number(91.7, 91.8, 0.3))
        self.assertFalse(score.close_number(73.4, 91.8, 0.3))
        self.assertFalse(score.close_number(True, 1, 0.3))
        self.assertFalse(score.close_number("91.8", 91.8, 0.3))
        points = [["HCN", "hydrogen cyanide"], ["toxic", "lethal"]]
        self.assertTrue(score.names_every_point("Acid liberates hydrogen cyanide, a lethal gas.", points))
        self.assertFalse(score.names_every_point("Be careful, this is toxic.", points))
        self.assertFalse(score.names_every_point("", points))
        self.assertFalse(score.names_every_point(None, points))

    def test_an_empty_run_scores_zero_and_the_reference_answers_score_full(self):
        self.assertEqual(score.score_tasks(TASKS, {})["passed"], 0)
        perfect = {}
        for task in TASKS:
            reference = task["reference"]
            perfect[task["id"]] = {
                "structure": {"smiles": reference.get("smiles")},
                "number": {"value": reference.get("value")},
                "safety": {"text": " ".join(group[0] for group in reference.get("must_mention", []))},
            }[task["kind"]]
        report = score.score_tasks(TASKS, perfect)
        self.assertEqual(report["passed"], report["total"])

    def test_the_command_line_exits_nonzero_when_nothing_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            answers = Path(folder) / "answers.json"
            answers.write_text("{}", encoding="utf-8")
            done = subprocess.run([sys.executable, str(EVALS / "score.py"), "tasks", str(answers)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 1, done.stderr)
            self.assertEqual(json.loads(done.stdout)["passed"], 0)

    def test_trigger_scoring_counts_both_directions_and_reports_gaps(self):
        every = {p: True for p in TRIGGERS["should_trigger"]} | {p: False for p in TRIGGERS["should_not_trigger"]}
        report = score.score_triggers(TRIGGERS, every)
        self.assertEqual((report["trigger_rate"], report["false_trigger_rate"], report["wrong"]), (1.0, 0.0, []))
        always = score.score_triggers(TRIGGERS, {p: True for p in every})
        self.assertEqual(always["false_trigger_rate"], 1.0)
        self.assertEqual(len(always["wrong"]), len(TRIGGERS["should_not_trigger"]))
        self.assertEqual(len(score.score_triggers(TRIGGERS, {})["missing"]), len(every))


class SetTests(unittest.TestCase):
    def test_sets_are_well_formed(self):
        self.assertEqual(len({task["id"] for task in TASKS}), len(TASKS))
        self.assertEqual({task["kind"] for task in TASKS}, {"structure", "number", "safety"})
        self.assertGreaterEqual(len(TRIGGERS["should_trigger"]), 10)
        self.assertGreaterEqual(len(TRIGGERS["should_not_trigger"]), 10)
        self.assertFalse(set(TRIGGERS["should_trigger"]) & set(TRIGGERS["should_not_trigger"]))

    def test_every_structure_reference_is_what_the_offline_resolver_returns(self):
        from cdxml_toolkit.naming.mol_builder import resolve_to_smiles

        for task in TASKS:
            if task["kind"] != "structure":
                continue
            with self.subTest(task=task["id"]):
                resolved = resolve_to_smiles(task["reference"]["resolves_from"], use_network=False)
                if not resolved.get("ok"):  # this host has no offline name parser for it
                    self.skipTest(f"{task['reference']['resolves_from']} does not resolve offline here")
                self.assertTrue(score.same_structure(resolved["smiles"], task["reference"]["smiles"]), resolved)


class RunnerTests(unittest.TestCase):
    def test_the_last_json_object_in_the_output_is_the_answer(self):
        self.assertEqual(run.last_json_object('thinking {"a": 1}\n{"smiles": "CCO"}\n'), {"smiles": "CCO"})
        self.assertIsNone(run.last_json_object("no answer\n[1, 2]\n{broken}"))

    def test_an_agent_command_is_run_once_per_task_with_the_prompt_on_stdin(self):
        echo = [sys.executable, "-c",
                "import sys, json; print(json.dumps({'text': sys.stdin.read()[:12]}))"]
        answers = run.collect(TASKS[:2], echo, timeout=60)
        self.assertEqual(answers[TASKS[0]["id"]], {"text": TASKS[0]["prompt"][:12]})
        self.assertIsNone(run.collect(TASKS[:1], ["no-such-agent-command"], timeout=5)[TASKS[0]["id"]])


if __name__ == "__main__":
    unittest.main()
