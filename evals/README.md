# Evaluations

Two small sets measure what the Skill adds to an agent. Neither calls a model by itself: you
run your agent and hand the answers to the scorer.

| File | What it measures |
| --- | --- |
| `triggers.json` | Prompts that should and should not load the Skill, for tuning the `description` in `SKILL.md` |
| `tasks.json` | Chemistry tasks with a reference answer: structures, one stoichiometry number, two safety questions |
| `run.py` | Collects task answers from any agent command that reads a prompt on stdin |
| `score.py` | Scores an answers file; structures are compared as compounds, not as strings |

## Task evaluation, with and without the Skill

```text
python evals/run.py --agent "AGENT COMMAND" --out with-skill.json      # Skill installed
python evals/run.py --agent "AGENT COMMAND" --out without-skill.json   # Skill removed
python skill/chemdraw/scripts/cdx.py py evals/score.py tasks with-skill.json --baseline without-skill.json
```

A structure passes when it is the same compound as the reference (connectivity, charge,
isotopes, stereo), whatever the SMILES spelling. A safety answer passes only when it names
every required point; an empty or vague answer fails. The scorer exits with 1 when no task
passes.

## Trigger evaluation

Record, for every prompt in `triggers.json`, whether your agent loaded the Skill, as a JSON
object of prompt to `true` or `false`, then:

```text
python skill/chemdraw/scripts/cdx.py py evals/score.py triggers decisions.json
```

## Reference answers

Each structure reference names the query it `resolves_from`; the repository tests check that
the toolkit's offline resolver returns that compound, so a reference never comes from memory.
No results are committed here: none have been measured for this release.
