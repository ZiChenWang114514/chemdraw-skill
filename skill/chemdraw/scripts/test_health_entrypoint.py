from pathlib import Path


def test_health_check_runs_pytest_suite():
    script = Path(__file__).with_name('health_check.ps1').read_text(encoding='utf-8-sig')
    assert "@('-m', 'pytest', $PSScriptRoot, '-q')" in script
