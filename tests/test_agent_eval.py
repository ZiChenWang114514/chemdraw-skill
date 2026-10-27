"""The harness runner's parsers, scorers and command lines; no model is called here."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "agent_eval"
SPEC = importlib.util.spec_from_file_location("agent_eval", ROOT / "scripts" / "agent_eval.py")
agent_eval = importlib.util.module_from_spec(SPEC)
sys.modules["agent_eval"] = agent_eval
SPEC.loader.exec_module(agent_eval)

CDXML = """<?xml version="1.0" encoding="UTF-8" ?>
<CDXML><page>
<fragment id="1"/><fragment id="2"/><fragment id="3"/>
<arrow id="9"/>
<t id="10"><s>H2SO4 (cat.)</s></t><t id="11"><s>85%</s></t>
</page></CDXML>
"""


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _run(*commands, final="", error=None, writes=()):
    return agent_eval.Run(
        commands=[agent_eval.Command(tool="bash", text=text, result=result) for text, result in commands],
        writes=list(writes), final=final, error=error, skill_loaded=True,
    )


class ParserTests(unittest.TestCase):
    def test_kimi_stream_json_gives_commands_skill_use_and_the_answer(self) -> None:
        run = agent_eval.parse_kimi(_fixture("kimi_doctor.jsonl"))
        self.assertTrue(run.skill_loaded)
        self.assertIsNone(run.error)
        self.assertEqual([c.tool for c in run.commands], ["Skill", "Bash"])
        self.assertIn("cdx.py", run.commands[1].text)
        self.assertIn("doctor", run.commands[1].text)
        self.assertIn("OPSIN", run.final)
        self.assertEqual(run.cdx_commands(), [run.commands[1]])

    def test_pi_json_gives_commands_skill_use_and_the_answer(self) -> None:
        run = agent_eval.parse_pi(_fixture("pi_doctor.jsonl"))
        self.assertTrue(run.skill_loaded)  # pi has no Skill tool: it reads SKILL.md
        self.assertIsNone(run.error)
        self.assertEqual([c.tool for c in run.commands], ["read", "bash"])
        self.assertTrue(any("cdx.py doctor" in c.text for c in run.cdx_commands()))
        self.assertIn("Opsin", run.final)

    def test_codex_json_gives_shell_commands_skill_use_and_the_answer(self) -> None:
        run = agent_eval.parse_codex(_fixture("codex_doctor.jsonl"))
        self.assertTrue(run.skill_loaded)
        self.assertIsNone(run.error)
        self.assertTrue(all(c.tool == "shell" for c in run.commands))
        self.assertTrue(any("cdx.py" in c.text and "doctor" in c.text for c in run.cdx_commands()))
        self.assertTrue(run.final)
        self.assertGreater(run.tokens, 0)
        # The agent passed inline JSON to --args and got a raw traceback: it must count as a usage failure.
        self.assertGreaterEqual(run.cdx_usage_errors(), 1)

    def test_provider_failure_is_a_harness_error_not_an_empty_answer(self) -> None:
        run = agent_eval.parse_pi(_fixture("pi_provider_error.jsonl"))
        self.assertIn("402", run.error)
        self.assertEqual(run.final, "")

    def test_usage_failures_of_cdx_are_counted(self) -> None:
        run = _run(
            ("python cdx.py draw --bogus x", "usage: cdx.py draw [-h]\ncdx.py draw: error: unrecognized arguments"),
            ("python cdx.py doctor", '{"installation": "ok"}'),
            ("ls", "usage: ls"),
        )
        self.assertEqual(run.cdx_usage_errors(), 1)


class ScorerTests(unittest.TestCase):
    def _check(self, checks, name):
        return next(c for c in checks if c.name == name)

    def test_a_complete_drawing_passes_every_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "01-aspirin.cdxml").write_text(CDXML, encoding="utf-8")
            checks = agent_eval.score_draw("01-aspirin", Path(tmp), _run(("python cdx.py draw b.json out/01-aspirin.cdxml", "ok")))
        self.assertEqual([c.name for c in checks if not c.ok], [])

    def test_a_missing_drawing_fails_the_file_check_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checks = agent_eval.score_draw("01-aspirin", Path(tmp), _run())
        self.assertFalse(self._check(checks, "file").ok)

    def test_cdxml_typed_by_hand_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "01-aspirin.cdxml").write_text(CDXML, encoding="utf-8")
            run = _run(writes=["out/01-aspirin.cdxml"])
            checks = agent_eval.score_draw("01-aspirin", Path(tmp), run)
        self.assertFalse(self._check(checks, "built_with_toolkit").ok)

    def test_cdxml_typed_into_a_shell_command_is_rejected_even_when_cdx_runs_in_the_same_command(self) -> None:
        typed = "@'\n<CDXML><page/></CDXML>\n'@ | Set-Content out/01-aspirin.cdxml\npython cdx.py render out/01-aspirin.cdxml"
        self.assertTrue(agent_eval._shell_write(typed))
        self.assertIsNone(agent_eval._shell_write("python cdx.py draw brief.json out/01-aspirin.cdxml"))

    def test_a_drawing_needs_a_toolkit_command_that_succeeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "01-aspirin.cdxml").write_text(CDXML, encoding="utf-8")
            failed = _run(("python cdx.py draw b out/x.cdxml", '{"ok": false, "error": {"code": "worker_launch_failed"}}'),
                          ("python cdx.py doctor", '{"installation": "ok"}'))
            checks = agent_eval.score_draw("01-aspirin", Path(tmp), failed)
        self.assertFalse(self._check(checks, "built_with_toolkit").ok)

    def test_a_drawing_missing_the_reagents_fails_the_text_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "01-aspirin.cdxml").write_text(CDXML.replace("H2SO4", "acid"), encoding="utf-8")
            checks = agent_eval.score_draw("01-aspirin", Path(tmp), _run(("python cdx.py draw b out", "ok")))
        self.assertFalse(self._check(checks, "text").ok)

    def test_an_existing_file_must_be_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            agent_eval.TASKS["no-overwrite"].setup(work)
            self.assertTrue(agent_eval.score_no_overwrite(work, _run())[0].ok)
            (work / "result.cdxml").write_text("changed", encoding="utf-8")
            self.assertFalse(agent_eval.score_no_overwrite(work, _run())[0].ok)

    def test_offline_requests_never_reach_the_recognition_service(self) -> None:
        upload = _run(("python cdx.py decimer scheme.png", "{}"))
        preflight = _run(("python cdx.py decimer scheme.png --preflight", "{}"))
        self.assertFalse(agent_eval.score_offline_image(upload)[0].ok)
        self.assertTrue(agent_eval.score_offline_image(preflight)[0].ok)
        self.assertTrue(agent_eval.score_offline_image(_run())[0].ok)

    def test_the_tool_question_needs_the_tool_and_its_exact_parameters(self) -> None:
        good = _run(final="embed_cdxml_in_office(cdxml_path, office_path, output_path)")
        bad = _run(final="Use batch_embed_cdxml_in_office with cdxml_paths")
        self.assertTrue(all(c.ok for c in agent_eval.score_discover(good)))
        self.assertFalse(all(c.ok for c in agent_eval.score_discover(bad)))

    def test_the_doctor_answer_names_what_is_missing(self) -> None:
        self.assertTrue(all(c.ok for c in agent_eval.score_doctor(
            _run(("python cdx.py doctor", "{}"), final="Only OPSIN is missing."), missing=["opsin"])))
        self.assertFalse(all(c.ok for c in agent_eval.score_doctor(
            _run(("python cdx.py doctor", "{}"), final="Everything is fine."), missing=["opsin"])))
        self.assertFalse(all(c.ok for c in agent_eval.score_doctor(
            _run(final="Only OPSIN is missing."), missing=["opsin"])))


class TaskAndCommandTests(unittest.TestCase):
    def test_tasks_are_ten_with_unique_ids_and_draw_prompts_use_the_corpus_sentence(self) -> None:
        tasks = agent_eval.TASKS
        self.assertEqual(len(tasks), 10)
        corpus = ROOT / "toolkit" / "tests" / "runtime" / "draw_corpus"
        draw = [t for t in tasks.values() if t.kind == "draw"]
        self.assertGreaterEqual(len(draw), 6)
        for task in draw:
            case = json.loads((corpus / f"{task.id}.json").read_text(encoding="utf-8"))
            self.assertIn(case["sentence"], task.prompt)
            self.assertIn(f"out/{task.id}.cdxml", task.prompt)

    def test_prompts_never_name_the_skill_or_its_commands(self) -> None:
        for task in agent_eval.TASKS.values():
            self.assertNotIn("cdx.py", task.prompt)
            self.assertNotIn("skill", task.prompt.lower())

    def test_each_cell_command_selects_the_model_and_loads_only_the_installed_skill(self) -> None:
        skills = Path("S")
        kimi = agent_eval.build_command(agent_eval.CELLS["kimi-k3"], "PROMPT", skills, Path("P"))
        self.assertIn("kimi-code/k3-256k", kimi)
        self.assertEqual(kimi[kimi.index("--skills-dir") + 1], str(skills))
        self.assertNotIn("--auto", kimi)  # kimi rejects --auto together with --prompt
        pi = agent_eval.build_command(agent_eval.CELLS["pi-deepseek"], "PROMPT", skills, Path("P"))
        self.assertIn("--no-skills", pi)
        self.assertEqual(pi[pi.index("--skill") + 1], str(skills / "chemdraw"))
        self.assertIn("--no-session", pi)
        self.assertEqual(pi[-1], "@" + str(Path("P")))  # the prompt travels in a file: no shell quoting
        codex = agent_eval.build_command(agent_eval.CELLS["codex-terra"], "PROMPT", skills, Path("P"), Path("W"))
        self.assertEqual(codex[codex.index("-m") + 1], "gpt-6.1-terra")
        self.assertEqual(codex[codex.index("-C") + 1], "W")
        self.assertEqual(codex[codex.index("-s") + 1], "workspace-write")
        self.assertIn("--ephemeral", codex)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", codex)
        self.assertEqual(codex[-1], "PROMPT")

    def test_a_run_that_used_another_installed_copy_is_not_scored(self) -> None:
        own = _run(("python .agents/skills/chemdraw/scripts/cdx.py doctor", "{}"))
        theirs = _run(("python C:\\Users\\x\\.codex\\skills\\chemdraw\\scripts\\cdx.py doctor", "{}"))
        plugin = _run(("Get-Content C:/Users/x/.codex/plugins/cache/p/spreadsheets/1/skills/chemdraw/SKILL.md", ""))
        self.assertFalse(own.foreign_skill_use())
        self.assertTrue(theirs.foreign_skill_use())
        self.assertTrue(plugin.foreign_skill_use())

    def test_codex_gets_the_skill_inside_the_working_folder_and_no_other_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills, work = Path(tmp) / "skills", Path(tmp) / "work"
            (skills / "chemdraw").mkdir(parents=True)
            (skills / "chemdraw" / "SKILL.md").write_text("---\nname: chemdraw\n---\n", encoding="utf-8")
            work.mkdir()
            agent_eval.place_skill(agent_eval.CELLS["codex-terra"], work, skills)
            agent_eval.place_skill(agent_eval.CELLS["kimi-k3"], Path(tmp) / "other", skills)
            self.assertTrue((work / ".agents" / "skills" / "chemdraw" / "SKILL.md").is_file())
            self.assertFalse((Path(tmp) / "other").exists())
        # A drawing found only inside the installed Skill is not the agent's output.
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / ".agents" / "skills" / "chemdraw" / "assets" / "sample.cdxml"
            sample.parent.mkdir(parents=True)
            sample.write_text("<CDXML/>", encoding="utf-8")
            self.assertIsNone(agent_eval._find_drawing("01-aspirin", Path(tmp)))

    def test_the_process_guard_reports_a_count(self) -> None:
        self.assertIsInstance(agent_eval.chemdraw_process_count(), int)

    def test_list_prints_cells_and_tasks_without_calling_a_model(self) -> None:
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "agent_eval.py"), "--list"],
                             capture_output=True, text=True, check=True).stdout
        for word in ("kimi-k3", "pi-deepseek", "codex-terra", "01-aspirin", "no-overwrite"):
            self.assertIn(word, out)


if __name__ == "__main__":
    unittest.main()
