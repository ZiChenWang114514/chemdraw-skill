# Scientific Workflows Public Symbols

> Generated from cdxml-toolkit 0.7.0a1. Curated guidance: [../scientific-workflows.md](../scientific-workflows.md).

## `scientific.__main__`

- **function**, line 8: `run(operation, spec_path, output)` - No public docstring in the audited version.

## `scientific.apparatus`

- **function**, line 20: `draw_apparatus(spec, output)` - No public docstring in the audited version.
- **function**, line 9: `template_catalog(path)` - No public docstring in the audited version.

## `scientific.common`

- **class**, line 23: `Drawing` - No public docstring in the audited version.
- **method**, line 36: `Drawing.add(kind, attrs, parent = None)` - No public docstring in the audited version.
- **method**, line 51: `Drawing.curve(points, parent = None, closed = False, filled = False)` - No public docstring in the audited version.
- **method**, line 47: `Drawing.line(a, b, parent = None)` - No public docstring in the audited version.
- **method**, line 60: `Drawing.save(output)` - No public docstring in the audited version.
- **method**, line 41: `Drawing.text(xy, value, size = 10, parent = None)` - No public docstring in the audited version.
- **function**, line 8: `number(value, name, low = None, high = None)` - No public docstring in the audited version.
- **function**, line 17: `point(value)` - No public docstring in the audited version.

## `scientific.mechanism`

- **function**, line 36: `compile_mechanism(spec, *, checks = None)` - No public docstring in the audited version.
- **function**, line 8: `validate_mechanism_steps(steps, molecules)` - Check fully specified equations; partial illustrations stay explicitly unchecked.

## `scientific.plots`

- **function**, line 8: `envelope_indices(values, limit = 1600)` - No public docstring in the audited version.
- **function**, line 19: `plot_xy(x, y, output_dir, *, title = 'Scientific plot', xlabel = 'x', ylabel = 'y', reverse_x = False, provenance = None)` - No public docstring in the audited version.

## `scientific.spectra`

- **function**, line 24: `analyze_spectrum(path, options)` - No public docstring in the audited version.
- **function**, line 9: `read_spectrum(path)` - No public docstring in the audited version.

## `scientific.tlc`

- **function**, line 14: `draw_tlc(spec, output)` - No public docstring in the audited version.
- **function**, line 5: `measure_rf(origin, solvent_front, spot)` - Project a measured spot along the calibrated solvent travel direction.
