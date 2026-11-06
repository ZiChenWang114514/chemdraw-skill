# Scientific Workflows Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../scientific-workflows.md](../scientific-workflows.md).

## `scientific.__main__`

- **function**, line 8: `run(operation, spec_path, output)` - No public docstring in the audited version.

## `scientific.apparatus`

- **function**, line 20: `draw_apparatus(spec, output)` - No public docstring in the audited version.
- **function**, line 9: `template_catalog(path)` - No public docstring in the audited version.

## `scientific.common`

- **class**, line 23: `Drawing` - No public docstring in the audited version.
- **method**, line 75: `Drawing.add(kind, attrs, parent = None)` - No public docstring in the audited version.
- **method**, line 37: `Drawing.color(rgb_hex: str) -> str` - No public docstring in the audited version.
- **method**, line 102: `Drawing.curve(points, parent = None, closed = False, filled = False, color: str | None = None, dashed: bool = False)` - No public docstring in the audited version.
- **method**, line 120: `Drawing.filled_rect(x1, y1, x2, y2, *, fill_color: str, border_color: str | None = None, parent = None) -> ET.Element` - No public docstring in the audited version.
- **method**, line 92: `Drawing.line(a, b, parent = None, color: str | None = None, dashed: bool = False)` - No public docstring in the audited version.
- **method**, line 152: `Drawing.save(output)` - No public docstring in the audited version.
- **method**, line 80: `Drawing.text(xy, value, size = 10, parent = None, color: str | None = None)` - No public docstring in the audited version.
- **function**, line 8: `number(value, name, low = None, high = None)` - No public docstring in the audited version.
- **function**, line 17: `point(value)` - No public docstring in the audited version.

## `scientific.mechanism`

- **function**, line 36: `compile_mechanism(spec, *, checks = None)` - No public docstring in the audited version.
- **function**, line 8: `validate_mechanism_steps(steps, molecules)` - Check fully specified equations; partial illustrations stay explicitly unchecked.

## `scientific.plots`

- **function**, line 350: `build_lcms_plate_cdxml(source_or_spec: Any, output_path: str | Path | None = None, *, product_mass: float | None = None, sm_mass: float | None = None, plate_format: int | str | None = None, wavelength: int | str = 254, title: str = 'LCMS Plate Purity Heatmap') -> dict[str, Any]` - Build an editable 24-well or 96-well LCMS purity heatmap in CDXML.
- **function**, line 13: `envelope_indices(values, limit = 1600)` - No public docstring in the audited version.
- **function**, line 59: `plot_xy(x = None, y = None, output_dir = None, *, title = 'Scientific plot', xlabel = 'x', ylabel = 'y', reverse_x = False, provenance = None, dpi = 300, series = None)` - No public docstring in the audited version.

## `scientific.spectra`

- **function**, line 623: `analyze_spectrum(path, options = None)` - No public docstring in the audited version.
- **function**, line 863: `build_nmr_cdxml(ppm: Any = None, intensity: Any = None, *, peaks: Optional[Sequence[Any]] = None, inset_region: Optional[Union[Tuple[float, float], list[float]]] = None, title: str = '1H NMR Spectrum', nucleus: str = '1H', output_path: Optional[Union[str, Path]] = None, x: Any = None, y: Any = None, spectrum: Any = None) -> str` - Build a ChemDraw CDXML document for an NMR spectrum with optional zoomed ``inset_region``.
- **function**, line 1241: `build_stacked_nmr_cdxml(spectra: Sequence[str | Path | Mapping[str, Any]], output_path: str | Path | None = None, *, labels: Sequence[str] | None = None, ppm_range: tuple[float, float] | None = None, title: str = 'Stacked NMR Comparison', normalize: str = 'each', show_peaks: bool = True, match_shifts: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]` - Build a multi-trace stacked NMR comparison CDXML figure (2 to 8 spectra).
- **function**, line 1017: `nmr_to_cdxml(ppm: Any = None, intensity: Any = None, *, peaks: Optional[Sequence[Any]] = None, inset_region: Optional[Union[Tuple[float, float], list[float]]] = None, title: str = '1H NMR Spectrum', nucleus: str = '1H', output_path: Optional[Union[str, Path]] = None, x: Any = None, y: Any = None, spectrum: Any = None) -> str` - Convert NMR spectrum arrays, peak list, or file path into a CDXML string (with optional ``inset_region``).
- **function**, line 1045: `plot_nmr(ppm: Any = None, intensity: Any = None, *, peaks: Optional[Sequence[Any]] = None, inset_region: Optional[Union[Tuple[float, float], list[float]]] = None, title: str = '1H NMR Spectrum', nucleus: str = '1H', output_path: Optional[Union[str, Path]] = None, output_dir: Optional[Union[str, Path]] = None, x: Any = None, y: Any = None, spectrum: Any = None) -> Union[str, dict[str, Any]]` - Plot an NMR spectrum to CDXML (and optional ``output_dir`` bundle) with ``inset_region`` zoom support.
- **function**, line 522: `read_spectrum(path)` - No public docstring in the audited version.

## `scientific.tlc`

- **function**, line 338: `draw_tlc(spec, output = None)` - No public docstring in the audited version.
- **function**, line 49: `measure_rf(origin, solvent_front, spot)` - Project a measured spot along the calibrated solvent travel direction.
