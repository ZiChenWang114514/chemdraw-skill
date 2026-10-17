# ChemDraw Skill quick start

This guide supports any agent that can read local instructions and run shell commands; Claude Code discovers the Skill automatically. Image reconstruction also requires visual inspection.

## Setup

Follow [Windows setup](guide.md#first-time-windows-setup): `scripts/install.ps1 -Runtime -Apply` installs the Skill and its runtime. Then run `python ~/.claude/skills/chemdraw/scripts/cdx.py doctor`. [Agent integration](../skill/chemdraw/references/agent-integration.md) explains the layout and every command.

## First use

Ask your agent:

```text
Use the ChemDraw Skill to resolve aspirin and produce editable CDXML. If native ChemDraw is available, render and inspect a PNG. Report structure readback and output paths.
```

For exam or lecture figures (abbreviations such as C10H21, compound codes, Chinese notes), the Skill uses the [ACS 1996 drawing builder](../skill/chemdraw/references/acs1996-drawings.md). For publication images, it follows the [reconstruction guide](../skill/chemdraw/references/image-visual-review.md): inspect, crop, recognize with the DECIMER API, align orientation, compare, correct, assemble conditions and layout, and render natively.

[Record template](../skill/chemdraw/assets/paper-replica/task-template.json) | [Runnable example](../skill/chemdraw/assets/paper-replica/example/CASE.md) | [Workflow router](../skill/chemdraw/references/workflow-router.md)
