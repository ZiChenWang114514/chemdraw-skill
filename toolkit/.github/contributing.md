# Contributing

Thank you for helping maintain `cdxml-toolkit-community`. Keep changes focused,
preserve chemistry semantics, and retain compatibility unless a release clearly
documents a change.

## Development setup

Use 64-bit Windows and Python 3.10-3.13. Native ChemDraw, ChemScript, and Office
tests require separately licensed desktop software.

```powershell
git clone https://github.com/ZiChenWang114514/cdxml-toolkit-community.git
Set-Location .\cdxml-toolkit-community
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,windows,office,analysis,image]"
python -m pytest -m "not network" -q
```

## Change requirements

- Add or update tests for behavioral changes.
- Preserve stereochemistry, isotopes, formal charges, atom mapping, and CDXML
  document validity.
- Keep network tests explicitly marked with `@pytest.mark.network`.
- Do not commit ChemDraw, Office, ChemScript, DECIMER model files, credentials,
  private experiments, or proprietary fixtures.
- Keep native tests separate from portable tests and report skipped applications.
- Update both `pyproject.toml` and `cdxml_toolkit/__init__.py` when changing the
  version.

Run `python -m build` and `python -m twine check dist/*` before a release-related
pull request. See [the maintenance guide](../docs/maintenance.md) for upstream
synchronization and release procedures.

