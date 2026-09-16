# ChemDraw Skill quick start

This guide supports any agent that can read local instructions and call MCP or Python. Image reconstruction also requires visual inspection. Adapt discovery paths and configuration to the client.

## Setup

Read [generic integration](../skill/chemdraw/references/agent-integration.md) and [Windows setup](guide.md#first-time-windows-setup). No specific agent CLI is required, and the installer does not change client configuration by default.

## First use

Load `skill/chemdraw/SKILL.md`, then ask:

```text
Use the ChemDraw Skill to resolve aspirin and produce editable CDXML. If native ChemDraw is available, render and inspect a PNG. Report structure readback and output paths.
```

For publication images, follow the [reconstruction guide](../skill/chemdraw/references/image-visual-review.md): inspect, crop, recognize with DECIMER API, align orientation, compare, correct, assemble conditions and layout, and validate natively. Assess chemical correctness and visual fidelity separately.

[Record template](../skill/chemdraw/assets/paper-replica/task-template.json) | [Runnable example](../skill/chemdraw/assets/paper-replica/example/CASE.md) | [Workflow router](../skill/chemdraw/references/workflow-router.md)
