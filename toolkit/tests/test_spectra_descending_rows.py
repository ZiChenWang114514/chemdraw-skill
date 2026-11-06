"""Predicted-shift traces whose simulated rows run high-to-low ppm are interpolated correctly."""

from __future__ import annotations

import numpy as np
import pytest

from cdxml_toolkit.engines import nmr as nmr_engine
from cdxml_toolkit.scientific import spectra


def test_descending_rows_give_peak_intensity_at_the_peak(monkeypatch):
    xs = np.linspace(10.0, 0.0, 1001)  # NMR order: high to low ppm
    ys = 1.0 / (1.0 + ((xs - 7.26) / 0.01) ** 2)
    monkeypatch.setattr(nmr_engine, "simulate", lambda *a, **k: list(zip(xs, ys)))
    trace = spectra._coerce_single_trace({"peaks": [7.26], "nucleus": "1H"}, 0)
    assert np.all(np.diff(trace["x"]) > 0)
    assert trace["peaks"][0]["intensity"] == pytest.approx(1.0, rel=1e-3)


def test_equal_ppm_range_bounds_must_differ():
    with pytest.raises(ValueError, match="must differ"):
        spectra.build_stacked_nmr_cdxml([{"ppm": [1, 2, 3], "intensity": [0, 1, 0]}] * 2, ppm_range=(2.0, 2.0))
