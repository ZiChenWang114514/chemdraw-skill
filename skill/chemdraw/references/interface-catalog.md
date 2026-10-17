# Interface Catalog

Use this page only when the workflow router does not identify an entry point.

| Need | Authority |
| --- | --- |
| Exact live tool names and parameters | [mcp-signatures.md](mcp-signatures.md) or `cdx.py sig NAME` |
| Tool selection, privacy, and failures | [toolkit-tools.md](toolkit-tools.md) |
| End-to-end task order | [workflow-router.md](workflow-router.md) |
| Python interfaces by domain | One `toolkit-*-interfaces.md` file |
| Installed console commands | [toolkit-cli-interfaces.md](toolkit-cli-interfaces.md) |
| Runtime and installation | [operations.md](operations.md) |
| Every audited public symbol | [toolkit-public-inventory.md](toolkit-public-inventory.md), then one shard |
| Reasons not to expose an API | [toolkit-reviewed-exclusions.md](toolkit-reviewed-exclusions.md) |

Classify interfaces as MCP-direct, CLI-direct, Python-direct, supporting, developer, legacy, or restricted. Expose only cohesive operations with validation, non-overwriting outputs, bounded execution, and a verifiable result.
