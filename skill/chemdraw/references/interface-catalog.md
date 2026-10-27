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
| ChemScript SDK types and members | [interface-chemscript.md](interface-chemscript.md), then one `inventory/chemscript-N.md` shard |
| ChemDraw COM objects (`Application`, `Document`, `Objects`, ...) | [interface-com.md](interface-com.md), then one `inventory/com-N.md` shard |
| CDXML elements, attributes and their evidence | [interface-cdxml-model.md](interface-cdxml-model.md), then `inventory/cdxml-attributes-N.md` |
| ChemDraw menu commands and their command ids | [interface-menu.md](interface-menu.md) |
| A working program for a generic tool, already run and checked | [recipes-chemdraw.md](recipes-chemdraw.md) |

The four `interface-*` pages and the recipes are generated (`cdx.py regen-catalog`) from what the installed ChemDraw reports about itself. Every row carries a tier: T1 has a dedicated tool, T2 has a recipe that was run, T3 is documented only. Do not call a T3 member as if it were verified; state that it is untested.

Classify interfaces as MCP-direct, CLI-direct, Python-direct, supporting, developer, legacy, or restricted. Expose only cohesive operations with validation, non-overwriting outputs, bounded execution, and a verifiable result.
