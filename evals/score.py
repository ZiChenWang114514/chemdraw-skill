"""Score agent answers against the evaluation sets in this folder.

Run inside the toolkit runtime (structures are compared with RDKit):

    cdx.py py evals/score.py tasks ANSWERS.json [--baseline OTHER.json]
    cdx.py py evals/score.py triggers DECISIONS.json

ANSWERS maps a task id to the JSON object the agent replied with; DECISIONS maps each
trigger prompt to true (the agent loaded the Skill) or false. A missing answer fails.
The exit code is 1 when no task passes or when the trigger set is not fully answered.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def same_structure(answer: object, reference: str) -> bool:
    """Whether two SMILES are the same compound: connectivity, charge, isotopes and stereo."""
    from rdkit import Chem

    from cdxml_toolkit.chemistry_semantics import semantic_key

    if not isinstance(answer, str) or not answer.strip():
        return False
    mine, theirs = Chem.MolFromSmiles(answer), Chem.MolFromSmiles(reference)
    if theirs is None:
        raise ValueError(f"reference SMILES does not parse: {reference}")
    return mine is not None and semantic_key(mine) == semantic_key(theirs)


def close_number(answer: object, value: float, tolerance: float) -> bool:
    return isinstance(answer, (int, float)) and not isinstance(answer, bool) and abs(answer - value) <= tolerance


def names_every_point(answer: object, must_mention: list[list[str]]) -> bool:
    """A safety answer passes only on positive evidence: one term from every group is present."""
    if not isinstance(answer, str) or not answer.strip():
        return False
    text = answer.lower()
    return all(any(term.lower() in text for term in group) for group in must_mention)


def score_task(task: dict, answer: object) -> bool:
    reference = task["reference"]
    answer = answer if isinstance(answer, dict) else {}
    if task["kind"] == "structure":
        return same_structure(answer.get("smiles"), reference["smiles"])
    if task["kind"] == "number":
        return close_number(answer.get("value"), reference["value"], reference["tolerance"])
    if task["kind"] == "safety":
        return names_every_point(answer.get("text"), reference["must_mention"])
    raise ValueError(f"unknown task kind {task['kind']!r}")


def score_tasks(tasks: list[dict], answers: dict) -> dict:
    results = {task["id"]: score_task(task, answers.get(task["id"])) for task in tasks}
    return {"passed": sum(results.values()), "total": len(results), "results": results}


def score_triggers(triggers: dict, decisions: dict) -> dict:
    wanted = {prompt: True for prompt in triggers["should_trigger"]}
    wanted.update({prompt: False for prompt in triggers["should_not_trigger"]})
    missing = [prompt for prompt in wanted if not isinstance(decisions.get(prompt), bool)]
    hit = sum(decisions.get(p) is True for p in triggers["should_trigger"])
    quiet = sum(decisions.get(p) is False for p in triggers["should_not_trigger"])
    return {
        "trigger_rate": hit / len(triggers["should_trigger"]),
        "false_trigger_rate": 1 - quiet / len(triggers["should_not_trigger"]) if not missing else None,
        "missing": missing,
        "wrong": [p for p, want in wanted.items() if isinstance(decisions.get(p), bool) and decisions[p] is not want],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="suite", required=True)
    tasks = sub.add_parser("tasks")
    tasks.add_argument("answers", type=Path)
    tasks.add_argument("--baseline", type=Path, help="answers from the same agent without the Skill")
    triggers = sub.add_parser("triggers")
    triggers.add_argument("decisions", type=Path)
    args = parser.parse_args(argv)

    def load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    if args.suite == "triggers":
        report = score_triggers(load(HERE / "triggers.json"), load(args.decisions))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report["missing"] else 0
    task_set = load(HERE / "tasks.json")
    report = score_tasks(task_set, load(args.answers))
    if args.baseline:
        baseline = score_tasks(task_set, load(args.baseline))
        report["baseline"] = {"passed": baseline["passed"], "total": baseline["total"]}
        report["gained"] = sorted(k for k, ok in report["results"].items() if ok and not baseline["results"][k])
        report["lost"] = sorted(k for k, ok in report["results"].items() if not ok and baseline["results"][k])
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
