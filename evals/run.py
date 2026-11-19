"""Collect answers for the task set from any agent that reads a prompt on stdin.

    python evals/run.py --agent "my-agent --print" --out answers-with-skill.json

The command runs once per task with the prompt on stdin; the last line of its output that
parses as a JSON object is the answer. Run it twice, with and without the Skill installed
in that agent, and compare the two files with `score.py tasks A.json --baseline B.json`.
Only the standard library is used, so any Python runs this.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def last_json_object(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    return None


def collect(tasks: list[dict], command: list[str], timeout: float) -> dict:
    answers = {}
    for task in tasks:
        try:
            done = subprocess.run(command, input=task["prompt"], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout)
            answers[task["id"]] = last_json_object(done.stdout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            answers[task["id"]] = None
            print(f"{task['id']}: {type(exc).__name__}", file=sys.stderr)
    return answers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--agent", required=True, help="command that reads one prompt on stdin")
    parser.add_argument("--out", required=True, type=Path, help="new answers file")
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists; name a new file")
    tasks = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
    answers = collect(tasks, shlex.split(args.agent, posix=sys.platform != "win32"), args.timeout)
    args.out.write_text(json.dumps(answers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    answered = sum(value is not None for value in answers.values())
    print(f"{answered} of {len(tasks)} tasks answered -> {args.out}")
    return 0 if answered else 1


if __name__ == "__main__":
    sys.exit(main())
