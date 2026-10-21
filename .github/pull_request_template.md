## Summary

## Validation

- [ ] `python scripts/validate_distribution.py` passes
- [ ] Skill tests pass: `python skill/chemdraw/scripts/cdx.py py -m pytest skill/chemdraw/tests -q`
- [ ] Toolkit tests pass when `toolkit/` changed: `python -m pytest -m "not network" -q` in `toolkit/`
- [ ] New or changed behavior has focused tests
- [ ] Chemistry semantics were checked
- [ ] Native ChemDraw, ChemScript or Office checks are reported when applicable (skipped checks are listed as skipped)
- [ ] No credentials, private chemistry, licensed binaries or generated caches are included
