"""The engine cases in the READMEs: every file they show exists, stays small and carries no personal path,
and the table of engines agrees with the registry."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "assets" / "readme" / "engines"
READMES = {"en": ROOT / "README.md", "zh": ROOT / "README.zh-cn.md"}
SECTION = {"en": "## Prediction and analysis engines", "zh": "## 预测与分析引擎"}
NEXT_SECTION = {"en": "## Reproduce a paper figure", "zh": "## 复刻论文反应图"}
CASE_LIMIT = 1_000_000  # bytes per case folder (one folder per molecule for the NMR cases)


def section(language: str) -> str:
    text = READMES[language].read_text(encoding="utf-8")
    start = text.index(SECTION[language])
    return text[start:text.index(NEXT_SECTION[language], start)]


class EngineCaseAssetTests(unittest.TestCase):
    def test_every_file_the_section_shows_exists(self) -> None:
        for language in READMES:
            with self.subTest(language=language):
                targets = re.findall(r'(?:src="|\]\()(assets/readme/engines/[^"#)\s]+)', section(language))
                self.assertGreater(len(targets), 10)
                self.assertEqual([t for t in targets if not (ROOT / t).exists()], [])

    def test_both_languages_show_the_same_files(self) -> None:
        shown = {language: re.findall(r'(?:src="|\]\()(assets/readme/engines/[^"#)\s]+)', section(language)) for language in READMES}
        self.assertEqual(shown["en"], shown["zh"])

    def test_each_case_folder_stays_small(self) -> None:
        folders = [CASES / "ocsr", CASES / "pdf", CASES / "retro", CASES / "forward", CASES / "lcms",
                   *sorted(p for p in (CASES / "nmr").iterdir() if p.is_dir())]
        for folder in folders:
            with self.subTest(folder=folder.name):
                size = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
                self.assertLessEqual(size, CASE_LIMIT)

    def test_results_are_json_without_personal_paths(self) -> None:
        pattern = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!<|you|user|USERNAME|example)")
        files = sorted(CASES.rglob("*.json"))
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            with self.subTest(path=path.relative_to(CASES).as_posix()):
                text = path.read_text(encoding="utf-8")
                json.loads(text)
                self.assertIsNone(pattern.search(text))

    def test_provenance_names_the_source_of_every_measured_input(self) -> None:
        provenance = json.loads((CASES / "provenance.json").read_text(encoding="utf-8"))
        for molecule, record in provenance["nmr"].items():
            with self.subTest(molecule=molecule):
                self.assertTrue(record["url"].startswith("https://bmrb.io/"))
                self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", h) for h in record["files_sha256"].values()))
        self.assertEqual(len(provenance["lcms"]["files_sha256"]), 3)

    def test_misses_are_kept_in_the_results(self) -> None:
        # The cases are only honest if the wrong answers stay in the record.
        ocsr = json.loads((CASES / "ocsr" / "results.json").read_text(encoding="utf-8"))["rows"]
        self.assertTrue(any(not row["constitution_match"] for row in ocsr))
        retro = json.loads((CASES / "retro" / "results.json").read_text(encoding="utf-8"))["jobs"]
        self.assertTrue(any(job["exact_rank"] is None for job in retro.values()))
        lcms = json.loads((CASES / "lcms" / "results.json").read_text(encoding="utf-8"))["wells"]
        self.assertTrue(any(not well["agrees_with_pyparse"] for well in lcms))


class EngineTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(ROOT / "toolkit"))
        try:
            from cdxml_toolkit.engines.registry import ENGINES, disk_mb
        except ImportError as exc:  # pragma: no cover - the registry has no heavy imports
            raise unittest.SkipTest(f"registry not importable: {exc}")
        finally:
            sys.path.remove(str(ROOT / "toolkit"))
        cls.engines, cls.disk_mb = ENGINES, staticmethod(disk_mb)

    def test_the_compact_table_lists_every_engine_with_its_registry_size(self) -> None:
        for language in READMES:
            text = section(language)
            for name in self.engines:
                with self.subTest(language=language, engine=name):
                    row = re.search(rf"^\| `{re.escape(name)}` \|.*$", text, re.M)
                    self.assertIsNotNone(row)
                    megabytes = self.disk_mb([name])
                    shown = "none" if megabytes == 0 else f"{megabytes} MB" if megabytes < 100 else f"{megabytes / 1000:.1f} GB"
                    if megabytes == 0:
                        shown = "none" if language == "en" else "无"
                    self.assertIn(f"| {shown} |", row.group(0))


if __name__ == "__main__":
    unittest.main()
