"""Build the Claude Code plugin from the Skill folder.

    python scripts/build_plugin.py --out NEW_DIR

NEW_DIR receives `.claude-plugin/plugin.json`, `skills/chemdraw/` (the Skill as the installer
copies it, without tests) and `MANIFEST.json` with a SHA-256 for every file. The plugin is
generated: nothing in it is edited by hand or committed. Only the standard library is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "chemdraw"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from install import IGNORED  # noqa: E402  (the same exclusions as an installed Skill)


def toolkit_version() -> str:
    text = (ROOT / "toolkit" / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"$', text, re.M).group(1)


def skill_description() -> str:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    return re.search(r"^description: (.+)$", text, re.M).group(1).strip()


def build(out: Path) -> Path:
    """Write the plugin into the new folder ``out`` and return it."""
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"{out} exists; name a new folder")
    shutil.copytree(SKILL, out / "skills" / "chemdraw", ignore=shutil.ignore_patterns(*IGNORED))
    baseline = json.loads((SKILL / "runtime.json").read_text(encoding="utf-8"))
    repository = baseline["repository"].removesuffix(".git")
    (out / ".claude-plugin").mkdir()
    (out / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "chemdraw-skill",
        "version": toolkit_version(),
        "description": skill_description(),
        "homepage": repository,
        "repository": repository,
        "license": "LicenseRef-PolyForm-Strict-1.0.0 AND CC-BY-NC-ND-4.0",
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    files = {
        path.relative_to(out).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(out.rglob("*")) if path.is_file()
    }
    (out / "MANIFEST.json").write_text(json.dumps(
        {"version": toolkit_version(), "toolkit_commit": baseline["commit"], "files": files}, indent=2,
    ) + "\n", encoding="utf-8", newline="\n")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="new folder for the plugin")
    args = parser.parse_args(argv)
    try:
        plugin = build(args.out)
    except FileExistsError as exc:
        parser.error(str(exc))
    print(plugin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
