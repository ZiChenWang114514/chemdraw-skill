"""The executable Skill proxy must discover its own client-independent folder."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


class AgentDiscoveryTests(unittest.TestCase):
    def test_proxy_discovers_itself_without_a_client_home(self):
        script = Path(__file__).with_name("runtime_discovery.py")
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            for key in ("CHEMDRAW_SKILL_ROOT", "CODEX_HOME", "CHEMDRAW_MCP_PYTHON"):
                env.pop(key, None)
            env.update(HOME=tmp, USERPROFILE=tmp)
            result = subprocess.run(
                [sys.executable, str(script), "--python", sys.executable, "--json"],
                env=env, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)["skill_root"]["path"]), script.parent.parent)


if __name__ == "__main__":
    unittest.main()
