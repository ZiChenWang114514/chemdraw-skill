# Maintenance Guide

This document defines how the bundled toolkit in `toolkit/` tracks upstream, tests
changes, and prepares releases.

## Repository model

- The toolkit lives in the `toolkit/` folder of `ZiChenWang114514/chemdraw-skill`.
  It was imported with `git subtree`, so its complete history is part of this
  repository. The former `cdxml-toolkit-community` repository is no longer the
  source of truth.
- Upstream is `leehiufung911/cdxml-toolkit`.
- `main` contains reviewed changes; feature and repair work uses short-lived branches.
- The compatible import package remains `cdxml_toolkit` and the distribution name
  remains `cdxml-toolkit-community`.

The project starts from the complete upstream Git history. Upstream version
`0.5.17` was introduced by commit
`0ae1a94275f2c91e2c45a832c33744c22447d24b`; the PyPI source distribution must
still be compared before that commit is declared an exact release snapshot.

## Upstream synchronization

Review upstream commits, then merge them into `toolkit/` on a dedicated branch:

```powershell
git fetch https://github.com/leehiufung911/cdxml-toolkit.git main
git log --oneline FETCH_HEAD
git switch -c sync/upstream-YYYYMMDD
git subtree pull --prefix=toolkit https://github.com/leehiufung911/cdxml-toolkit.git main
```

Resolve changes deliberately, run the complete portable suite, and add native
checks when affected modules use ChemDraw, ChemScript, or Office. Merge the
sync branch through a pull request with a merge commit, not a squash, so the
pinned commit in `skill/chemdraw/runtime.json` stays reachable. Do not force-push `main`.

## Re-pinning the runtime

An installed Skill copy outside a checkout builds its runtime from the `commit`
recorded in `skill/chemdraw/runtime.json`, and the checkout detects a stale runtime
through `toolkit_fingerprint` in the same file. After any change under
`toolkit/cdxml_toolkit`:

1. Commit the toolkit change.
2. Run `python skill/chemdraw/scripts/cdx.py regen-signatures`; it refreshes the
   generated references and writes the new `toolkit_fingerprint`.
3. Set `commit` to the commit from step 1 and commit `runtime.json` separately.

`tests/test_runtime_baseline.py` fails when the fingerprint is stale or when the
pinned commit's toolkit differs from `toolkit/`; it needs full history, so CI checks
out with `fetch-depth: 0`. Merge such pull requests with a merge commit. After a
squash merge the pinned commit is not on `main`: repeat step 3 on `main` with the
squashed commit.

## Supported environments

| Capability | Maintained environment |
| --- | --- |
| Portable CDXML and RDKit behavior | Windows, Python 3.10-3.13 |
| MCP server | MCP Python SDK 1.x and 2.x; core and community profiles |
| ChemDraw COM and ChemScript | Licensed Windows workstation |
| Editable Office objects | Desktop Word and PowerPoint on Windows |
| DECIMER recognition | Optional `decimer` dependency group and local weights |

Hosted CI validates portable behavior. Native software checks must run on a
licensed local or self-hosted Windows machine and must identify skipped
applications explicitly.

### Live check on macOS

The test suite never starts ChemDraw on macOS, so the AppleScript path
(`open -a ChemDraw`, `osascript`) is checked by hand on a Mac with ChemDraw
activated. Run from the repository root, in a scratch folder, and report each
step as passed, failed or skipped:

```sh
python scripts/install.py --runtime-only --apply
python skill/chemdraw/scripts/cdx.py doctor --native          # opens ChemDraw, renders a probe
python skill/chemdraw/scripts/cdx.py call render_scheme --json '{"yaml_text": "layout: sequential\nstructures:\n  A: {smiles: \"CC(=O)Cl\", label: \"1\"}\n  B: {smiles: \"CCN\", label: \"2\"}\n  P: {smiles: \"CC(=O)NCC\", label: \"3\"}\nsteps:\n  - substrates: [A, B]\n    products: [P]\n", "output_path": "/tmp/amide.cdxml"}'
python skill/chemdraw/scripts/cdx.py call reaction_calculator --json '{"reaction": {"cdxml": "/tmp/amide.cdxml"}, "options": {"scheme_output": "/tmp/amide_amounts.cdxml"}, "output_path": "/tmp/amide_calc.html"}'
python skill/chemdraw/scripts/cdx.py call render_cdxml_files --json '{"input_paths": ["/tmp/amide_amounts.cdxml"], "output_dir": "/tmp/render"}'
python skill/chemdraw/scripts/cdx.py install-mappers --status
```

Open `/tmp/render/amide_amounts.png` and check that the amounts sit below the
compound numbers without touching them.

## Compatibility policy

- Patch releases repair compatible behavior.
- Minor releases may add APIs and deprecate old behavior.
- Breaking changes require a major release or a clearly marked prerelease.
- MCP tool names and result fields remain compatible throughout a minor series.
- Deprecated public members remain available for at least one minor release.

## Release procedure

1. Update the version in `pyproject.toml`, `cdxml_toolkit/__init__.py` and
   `skill/chemdraw/runtime.json` (`toolkit_version`), then pin `commit` there.
2. Run `python -m pytest -m "not network" -q` on Python 3.10-3.13.
3. Run applicable native ChemDraw, ChemScript, and Office checks.
4. Run `python -m build` and `python -m twine check dist/*` in a clean tree.
5. Confirm wheels and source archives do not contain a bundled JRE.
6. Create an annotated `vX.Y.Z` tag and a GitHub Release with compatibility notes.
7. Publish to TestPyPI before any production package index.

The GitHub build workflow creates inspectable wheel and source artifacts. PyPI
publishing remains disabled until the community distribution name is reserved
and Trusted Publishing is configured with an approved GitHub environment.

## Initial maintenance priorities

1. Verify the PyPI `0.5.17` source archive against upstream history.
2. Reserve the community distribution on PyPI and configure Trusted Publishing.
3. Keep the 15 core tool names compatible and review result changes during prereleases.
4. Run the manually triggered native workflow on an activated, self-hosted Windows runner.
5. Regenerate MCP Markdown and JSON references whenever the registry changes.

## MCP runtime maintenance

- `cdxml_toolkit.mcp_server` retains the 15 compatible core tools.
- `cdxml_toolkit.mcp_runtime` owns worker isolation, native resource coordination,
  artifact validation, HTTP security, metrics, and the complete tool registry.
- The `full` profile (default) holds the whole registry; `codex` is a compatibility alias.
  Profile sizes are listed in the README table, and `toolkit/tests/runtime/test_capabilities.py` and the Skill's
  `test_doc_consistency.py` check them against the registry.
- The runtime is client-neutral: no agent-specific configuration writers or
  defaults. The ChemDraw COM mutex keeps its historical name so that older and
  newer runtimes still exclude each other.
- `docs/mcp-tools.md` and `docs/mcp-schema.json` are generated files. CI rejects drift.
  After a registry change also run `cdx.py regen-signatures` for the Skill.
- The native workflow requires a self-hosted runner carrying the `chemdraw` label,
  a current GitHub Actions runner, an activated desktop ChemDraw installation,
  and desktop Word and PowerPoint.
