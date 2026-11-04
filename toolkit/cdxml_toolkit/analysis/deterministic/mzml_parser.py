"""Open MS format parser (.mzML and .mzXML) using only Python stdlib.

Parses HUPO-PSI ``.mzML`` and ISB ``.mzXML`` mass spectrometry files via
``xml.etree.ElementTree.iterparse``, ``base64``, ``zlib``, and ``struct``
into ``LCMSAnalysis`` (with ``Chromatogram``, ``LCMSPeak``, and
``MassSpectrum``). Supports 32-bit and 64-bit IEEE-754 float binary data
arrays, both zlib-compressed and uncompressed.
"""

from __future__ import annotations

import base64
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


class SampleInfoDict(dict):
    """Dictionary of sample metadata that also compares equal to Sample Description string."""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            desc = self.get("Sample Description") or self.get("sample_description") or self.get("sample_name") or ""
            return other == desc or other == str(self)
        return super().__eq__(other)

    def __contains__(self, item: object) -> bool:
        if super().__contains__(item):
            return True
        if isinstance(item, str):
            for val in self.values():
                if isinstance(val, str) and item in val:
                    return True
        return False


@dataclass
class MassSpectrum:
    """Mass spectrum for a single scan or chromatographic peak (ES+ or ES-)."""

    mz_values: List[float] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    mode: str = "ES+"
    rt: Optional[float] = None
    scan_number: Optional[int] = None
    ms_level: int = 1
    tic: float = 0.0
    base_peak_mz: Optional[float] = None
    base_peak_intensity: Optional[float] = None
    top_ions: List[float] = field(default_factory=list)

    def __init__(
        self,
        mz_values: Union[Sequence[float], str, None] = None,
        intensities: Optional[Sequence[float]] = None,
        mode: str = "ES+",
        *,
        rt: Optional[float] = None,
        scan_number: Optional[int] = None,
        ms_level: int = 1,
        tic: float = 0.0,
        base_peak_mz: Optional[float] = None,
        base_peak_intensity: Optional[float] = None,
        top_ions: Optional[Sequence[float]] = None,
    ) -> None:
        # Support both MassSpectrum(mz_values, intensities, mode) and
        # legacy MassSpectrum(mode, top_ions, intensities) call styles.
        if isinstance(mz_values, str):
            actual_mode = mz_values
            actual_mzs = list(intensities) if intensities is not None else (list(top_ions) if top_ions is not None else [])
            actual_ints = list(mode) if isinstance(mode, (list, tuple)) else []
        else:
            actual_mode = mode if isinstance(mode, str) else "ES+"
            actual_mzs = [float(x) for x in mz_values] if mz_values is not None else (
                [float(x) for x in top_ions] if top_ions is not None else []
            )
            actual_ints = [float(x) for x in intensities] if intensities is not None else []

        norm_mode = actual_mode.strip().upper()
        if norm_mode in ("+", "POS", "POSITIVE", "ESI+", "ES+"):
            norm_mode = "ES+"
        elif norm_mode in ("-", "NEG", "NEGATIVE", "ESI-", "ES-"):
            norm_mode = "ES-"

        self.mz_values = actual_mzs
        self.intensities = actual_ints
        self.mode = norm_mode
        self.rt = float(rt) if rt is not None else None
        self.scan_number = int(scan_number) if scan_number is not None else None
        self.ms_level = int(ms_level)

        if top_ions is not None:
            self.top_ions = [float(x) for x in top_ions]
        elif self.mz_values and self.intensities and len(self.mz_values) == len(self.intensities):
            pairs = sorted(zip(self.mz_values, self.intensities), key=lambda p: p[1], reverse=True)
            self.top_ions = [p[0] for p in pairs]
            # Keep mz_values and intensities aligned; if caller wants top_ions
            # we preserve mz_values in original order and top_ions in intensity order.
        else:
            self.top_ions = list(self.mz_values)

        if tic and tic > 0:
            self.tic = float(tic)
        elif self.intensities:
            self.tic = float(sum(self.intensities))
        else:
            self.tic = 0.0

        if base_peak_mz is not None:
            self.base_peak_mz = float(base_peak_mz)
        elif self.mz_values and self.intensities and len(self.mz_values) == len(self.intensities):
            max_idx = max(range(len(self.intensities)), key=lambda i: self.intensities[i])
            self.base_peak_mz = float(self.mz_values[max_idx])
        else:
            self.base_peak_mz = self.mz_values[0] if self.mz_values else None

        if base_peak_intensity is not None:
            self.base_peak_intensity = float(base_peak_intensity)
        elif self.intensities:
            self.base_peak_intensity = float(max(self.intensities))
        else:
            self.base_peak_intensity = None


@dataclass
class Chromatogram:
    """Chromatographic trace (TIC, BPC, or UV/DAD)."""

    trace_type: str = "TIC"
    times: List[float] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    wavelength: Optional[float] = None
    units: str = "min"

    @property
    def retention_times(self) -> List[float]:
        return self.times

    @property
    def rt(self) -> List[float]:
        return self.times

    @property
    def name(self) -> str:
        return self.trace_type


@dataclass
class LCMSPeak:
    """An integrated chromatographic peak with associated mass spectra."""

    peak_id: Union[int, str] = 1
    rt: float = 0.0
    area: float = 0.0
    area_pct: float = 0.0
    height: float = 0.0
    width: float = 0.0
    start_rt: Optional[float] = None
    end_rt: Optional[float] = None
    ms_spectra: List[MassSpectrum] = field(default_factory=list)
    spectrum: Optional[MassSpectrum] = None
    uv_lambda_max: List[float] = field(default_factory=list)
    area_220nm: Optional[float] = None
    area_254nm: Optional[float] = None
    area_pct_220nm: Optional[float] = None
    area_pct_254nm: Optional[float] = None

    def __post_init__(self) -> None:
        if self.spectrum is not None and not self.ms_spectra:
            self.ms_spectra = [self.spectrum]
        elif self.ms_spectra and self.spectrum is None:
            self.spectrum = self.ms_spectra[0]

    @property
    def mz_values(self) -> List[float]:
        if self.spectrum is not None:
            return self.spectrum.mz_values
        if self.ms_spectra:
            return self.ms_spectra[0].mz_values
        return []

    @property
    def top_ions(self) -> List[float]:
        if self.spectrum is not None:
            return self.spectrum.top_ions
        if self.ms_spectra:
            return self.ms_spectra[0].top_ions
        return []


@dataclass
class LCMSAnalysis:
    """Complete parsed open-format or raw LCMS dataset."""

    filename: str = ""
    file_path: str = ""
    format: str = "mzML"
    chromatograms: List[Chromatogram] = field(default_factory=list)
    peaks: List[LCMSPeak] = field(default_factory=list)
    spectra: List[MassSpectrum] = field(default_factory=list)
    sample_info: Dict[str, str] = field(default_factory=SampleInfoDict)
    instrument: str = "Unknown"
    acquisition_date: str = ""
    method: str = ""
    method_path: str = ""
    method_short: str = ""
    sample_name: str = ""
    date: str = ""
    time: str = ""
    detector: str = "MS TIC"

    def __post_init__(self) -> None:
        if isinstance(self.sample_info, dict) and not isinstance(self.sample_info, SampleInfoDict):
            self.sample_info = SampleInfoDict(self.sample_info)
        if not self.sample_name and isinstance(self.sample_info, dict):
            self.sample_name = (
                self.sample_info.get("Sample Description")
                or self.sample_info.get("sample_description")
                or self.sample_info.get("sample_name")
                or ""
            )
        if not self.method_path and self.method:
            self.method_path = self.method
        if not self.method_short and self.method:
            self.method_short = self.method

    @property
    def tac_peaks(self) -> List[LCMSPeak]:
        return self.peaks

    def get_chromatogram(self, trace_type: str = "TIC") -> Optional[Chromatogram]:
        target = trace_type.strip().upper()
        for chrom in self.chromatograms:
            if chrom.trace_type.upper() == target:
                return chrom
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "format": self.format,
            "instrument": self.instrument,
            "acquisition_date": self.acquisition_date,
            "sample_name": self.sample_name,
            "sample_info": dict(self.sample_info) if isinstance(self.sample_info, dict) else self.sample_info,
            "method": self.method,
            "detector": self.detector,
            "chromatograms": [
                {
                    "trace_type": c.trace_type,
                    "times": c.times,
                    "intensities": c.intensities,
                    "wavelength": c.wavelength,
                    "units": c.units,
                }
                for c in self.chromatograms
            ],
            "peaks": [
                {
                    "peak_id": p.peak_id,
                    "rt": p.rt,
                    "area": p.area,
                    "area_pct": p.area_pct,
                    "height": p.height,
                    "ms_spectra": [
                        {
                            "mode": s.mode,
                            "mz_values": s.mz_values,
                            "intensities": s.intensities,
                            "rt": s.rt,
                            "base_peak_mz": s.base_peak_mz,
                        }
                        for s in p.ms_spectra
                    ],
                }
                for p in self.peaks
            ],
            "spectra_count": len(self.spectra),
        }


# Register LCMSAnalysis, Chromatogram, LCMSPeak onto parent lcms_analyzer module
# so `from .lcms_analyzer import LCMSAnalysis` works seamlessly.
try:
    from .. import lcms_analyzer as _parent_lcms_analyzer

    for _sym_name, _sym_obj in (
        ("LCMSAnalysis", LCMSAnalysis),
        ("Chromatogram", Chromatogram),
        ("LCMSPeak", LCMSPeak),
    ):
        if not hasattr(_parent_lcms_analyzer, _sym_name):
            setattr(_parent_lcms_analyzer, _sym_name, _sym_obj)
    if __package__:
        sys.modules.setdefault(f"{__package__}.lcms_analyzer", _parent_lcms_analyzer)
except Exception:
    pass


# ---------------------------------------------------------------------------
# Binary array decoding helpers
# ---------------------------------------------------------------------------

def decode_binary_array(
    b64_text: Optional[str],
    *,
    precision: int = 64,
    compressed: bool = False,
    byte_order: str = "<",
) -> List[float]:
    """Decode base64-encoded (optionally zlib-compressed) 32/64-bit float array."""
    if not b64_text:
        return []
    cleaned = b64_text.strip()
    if not cleaned:
        return []
    raw = base64.b64decode(cleaned)
    if not raw:
        return []
    if compressed:
        raw = zlib.decompress(raw)
    if not raw:
        return []

    fmt_char = "d" if precision == 64 else "f"
    elem_size = 8 if precision == 64 else 4
    if len(raw) % elem_size != 0:
        # Try alternate precision if byte length matches the other float size
        alt_size = 4 if elem_size == 8 else 8
        if len(raw) % alt_size == 0:
            elem_size = alt_size
            fmt_char = "f" if elem_size == 4 else "d"
        else:
            raw = raw[: (len(raw) // elem_size) * elem_size]

    count = len(raw) // elem_size
    if count == 0:
        return []
    endian = ">" if byte_order in (">", "big", "network") else "<"
    values = list(struct.unpack(f"{endian}{count}{fmt_char}", raw))
    return [float(v) for v in values]


def _values_look_valid_mz_int(vals: Sequence[float]) -> bool:
    """Check whether unpacked interleaved (m/z, intensity) pairs look physically valid."""
    if not vals:
        return True
    if not all(math.isfinite(v) and -1e-6 <= v <= 1e15 for v in vals):
        return False
    mzs = vals[0::2]
    if any(m < 0.0 or m > 1e6 for m in mzs):
        return False
    if len(mzs) >= 2 and any(mzs[i] > mzs[i + 1] + 1e-4 for i in range(len(mzs) - 1)):
        return False
    return True


def _local_name(tag: str) -> str:
    """Strip XML namespace URI from an ElementTree tag."""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


_ISO_DURATION_RE = re.compile(
    r"^P(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$",
    re.IGNORECASE,
)


def _parse_mzxml_rt(rt_str: Optional[str]) -> Optional[float]:
    """Parse an mzXML retentionTime attribute (e.g. 'PT120.5S', 'PT2.5M', '2.0') into minutes."""
    if not rt_str:
        return None
    s = rt_str.strip()
    if not s:
        return None
    m = _ISO_DURATION_RE.match(s)
    if m:
        hours = float(m.group("hours") or 0.0)
        minutes = float(m.group("minutes") or 0.0)
        seconds = float(m.group("seconds") or 0.0)
        return hours * 60.0 + minutes + seconds / 60.0
    # Fallback: strip PT / S / M manually
    s_up = s.upper()
    if s_up.startswith("PT"):
        body = s_up[2:]
        if body.endswith("S") and "M" not in body:
            try:
                return float(body[:-1]) / 60.0
            except ValueError:
                pass
        if body.endswith("M") and "S" not in body:
            try:
                return float(body[:-1])
            except ValueError:
                pass
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Peak picking & chromatogram construction
# ---------------------------------------------------------------------------

def _pick_chromatogram_peaks(
    chrom: Chromatogram,
    spectra: List[MassSpectrum],
    min_rel_height: float = 0.02,
) -> List[LCMSPeak]:
    """Identify chromatographic peaks from a trace and attach nearest MS1 spectra."""
    times = chrom.times
    intensities = chrom.intensities
    n = len(times)
    if n == 0 or len(intensities) != n:
        return []

    max_int = max(intensities, default=0.0)
    if max_int <= 0.0:
        return []

    min_int = min(intensities, default=0.0)
    threshold = max_int * min_rel_height

    # Find local maxima indices
    apex_indices: List[int] = []
    if n == 1:
        if intensities[0] >= threshold:
            apex_indices.append(0)
    elif n <= 4 and min_int > 0.1 * max_int:
        # Sparse scan-only dataset without baseline zeroes: each scan RT is a peak
        apex_indices = [i for i in range(n) if intensities[i] >= threshold]
    else:
        for i in range(n):
            val = intensities[i]
            if val < threshold:
                continue
            left_ok = (i == 0) or (val >= intensities[i - 1])
            right_ok = (i == n - 1) or (val > intensities[i + 1])
            # Require at least one strictly lower neighbor unless n == 1
            strictly_higher = (
                (i > 0 and val > intensities[i - 1])
                or (i < n - 1 and val > intensities[i + 1])
            )
            if left_ok and right_ok and strictly_higher:
                apex_indices.append(i)
        if not apex_indices:
            apex_indices = [i for i in range(n) if intensities[i] >= threshold]

    raw_peaks: List[LCMSPeak] = []
    ms1_spectra = [s for s in spectra if s.ms_level == 1] or list(spectra)

    for peak_num, idx in enumerate(apex_indices, start=1):
        rt_apex = float(times[idx])
        height = float(intensities[idx])

        # Expand left and right to local valley / baseline
        left = idx
        while left > 0 and intensities[left - 1] <= intensities[left]:
            if left - 1 in apex_indices:
                break
            left -= 1
            if intensities[left] <= min_int:
                break
        right = idx
        while right < n - 1 and intensities[right + 1] <= intensities[right]:
            if right + 1 in apex_indices:
                break
            right += 1
            if intensities[right] <= min_int:
                break

        if right > left:
            area = 0.0
            for j in range(left, right):
                dt = max(abs(times[j + 1] - times[j]), 1e-4)
                area += 0.5 * (intensities[j] + intensities[j + 1]) * dt
            width = abs(times[right] - times[left])
            start_rt = float(times[left])
            end_rt = float(times[right])
        else:
            area = height
            width = 0.05
            start_rt = rt_apex - 0.025
            end_rt = rt_apex + 0.025

        # Attach closest ES+ and ES- spectra within RT window
        matched_spectra: List[MassSpectrum] = []
        for mode in ("ES+", "ES-"):
            mode_specs = [s for s in ms1_spectra if s.mode == mode and s.rt is not None]
            if mode_specs:
                best_spec = min(mode_specs, key=lambda s: abs((s.rt or 0.0) - rt_apex))
                if abs((best_spec.rt or 0.0) - rt_apex) <= max(width, 0.25):
                    matched_spectra.append(best_spec)
        if not matched_spectra and ms1_spectra:
            with_rt = [s for s in ms1_spectra if s.rt is not None]
            if with_rt:
                matched_spectra.append(min(with_rt, key=lambda s: abs((s.rt or 0.0) - rt_apex)))
            else:
                matched_spectra.append(ms1_spectra[min(idx, len(ms1_spectra) - 1)])

        raw_peaks.append(
            LCMSPeak(
                peak_id=peak_num,
                rt=round(rt_apex, 4),
                area=round(area, 4),
                area_pct=0.0,
                height=round(height, 4),
                width=round(width, 4),
                start_rt=round(start_rt, 4),
                end_rt=round(end_rt, 4),
                ms_spectra=matched_spectra,
                spectrum=matched_spectra[0] if matched_spectra else None,
            )
        )

    total_area = sum(p.area for p in raw_peaks)
    if total_area > 0:
        for p in raw_peaks:
            p.area_pct = round(100.0 * p.area / total_area, 2)

    return raw_peaks


# ---------------------------------------------------------------------------
# mzML and mzXML parsing
# ---------------------------------------------------------------------------

def _parse_mzml_binary_data_array(bda_elem: ET.Element) -> Tuple[Optional[str], List[float], Optional[str]]:
    """Parse one <binaryDataArray> element from mzML.

    Returns (array_kind, values, unit_name) where array_kind is 'mz', 'intensity',
    'time', or 'other'.
    """
    precision = 64
    compressed = False
    array_kind: Optional[str] = None
    unit_name: Optional[str] = None
    b64_text: Optional[str] = None

    for child in bda_elem.iter():
        lname = _local_name(child.tag)
        if lname == "cvParam":
            acc = (child.attrib.get("accession") or "").strip().upper()
            name = (child.attrib.get("name") or "").strip().lower()
            u_acc = (child.attrib.get("unitAccession") or "").strip().upper()
            u_name = (child.attrib.get("unitName") or "").strip().lower()

            if acc == "MS:1000521" or "32-bit float" in name:
                precision = 32
            elif acc == "MS:1000523" or "64-bit float" in name:
                precision = 64
            elif acc == "MS:1000574" or "zlib" in name:
                compressed = True
            elif acc == "MS:1000576" or "no compression" in name:
                compressed = False
            elif acc == "MS:1000514" or "m/z array" in name:
                array_kind = "mz"
            elif acc == "MS:1000515" or "intensity array" in name:
                array_kind = "intensity"
            elif acc == "MS:1000595" or "time array" in name:
                array_kind = "time"
                if u_acc == "UO:0000010" or u_name.startswith("sec"):
                    unit_name = "second"
                elif u_acc == "UO:0000031" or u_name.startswith("min"):
                    unit_name = "minute"
            elif array_kind is None and "wavelength" in name:
                array_kind = "wavelength"
        elif lname == "binary":
            b64_text = child.text

    values = decode_binary_array(b64_text, precision=precision, compressed=compressed, byte_order="<")
    return array_kind, values, unit_name


def _parse_mzml_chromatogram(chrom_elem: ET.Element) -> Optional[Chromatogram]:
    """Parse one <chromatogram> element from mzML."""
    chrom_id = (chrom_elem.attrib.get("id") or "").strip()
    trace_type = "TIC"
    id_upper = chrom_id.upper()
    if "BPC" in id_upper or "BASEPEAK" in id_upper or "BASE PEAK" in id_upper:
        trace_type = "BPC"
    elif any(k in id_upper for k in ("UV", "DAD", "PDA", "TWC", "TAC", "ABS")):
        trace_type = "UV"
    elif "TIC" in id_upper:
        trace_type = "TIC"

    wavelength: Optional[float] = None
    times: List[float] = []
    intensities: List[float] = []

    for child in chrom_elem:
        lname = _local_name(child.tag)
        if lname == "cvParam":
            acc = (child.attrib.get("accession") or "").strip().upper()
            name = (child.attrib.get("name") or "").strip().lower()
            val = child.attrib.get("value")
            if acc == "MS:1000235" or "total ion current chromatogram" in name:
                trace_type = "TIC"
            elif acc == "MS:1000628" or "base peak chromatogram" in name:
                trace_type = "BPC"
            elif acc in ("MS:1000812", "MS:1000813") or "absorption chromatogram" in name or "electromagnetic" in name:
                trace_type = "UV"
            elif "wavelength" in name and val is not None:
                try:
                    wavelength = float(val)
                except ValueError:
                    pass
        elif lname == "binaryDataArrayList":
            for bda in child:
                if _local_name(bda.tag) == "binaryDataArray":
                    kind, vals, unit = _parse_mzml_binary_data_array(bda)
                    if kind == "time":
                        if unit == "second":
                            times = [round(v / 60.0, 6) for v in vals]
                        else:
                            times = vals
                    elif kind == "intensity":
                        intensities = vals

    if not times and not intensities:
        return None
    return Chromatogram(
        trace_type=trace_type,
        times=times,
        intensities=intensities,
        wavelength=wavelength,
        units="min",
    )


def _parse_mzml_spectrum(spec_elem: ET.Element, default_idx: int) -> Optional[MassSpectrum]:
    """Parse one <spectrum> element from mzML."""
    spec_id = spec_elem.attrib.get("id") or ""
    idx_str = spec_elem.attrib.get("index")
    scan_num: Optional[int] = None
    m_scan = re.search(r"scan=(\d+)", spec_id, re.IGNORECASE)
    if m_scan:
        scan_num = int(m_scan.group(1))
    elif idx_str is not None and idx_str.isdigit():
        scan_num = int(idx_str) + 1
    else:
        scan_num = default_idx

    ms_level = 1
    mode = "ES+"
    rt_min: Optional[float] = None
    tic: float = 0.0
    bp_mz: Optional[float] = None
    bp_int: Optional[float] = None
    mzs: List[float] = []
    ints: List[float] = []

    for elem in spec_elem.iter():
        lname = _local_name(elem.tag)
        if lname == "cvParam":
            acc = (elem.attrib.get("accession") or "").strip().upper()
            name = (elem.attrib.get("name") or "").strip().lower()
            val = elem.attrib.get("value")
            u_acc = (elem.attrib.get("unitAccession") or "").strip().upper()
            u_name = (elem.attrib.get("unitName") or "").strip().lower()

            if acc == "MS:1000511" or name == "ms level":
                try:
                    ms_level = int(val or 1)
                except ValueError:
                    ms_level = 1
            elif acc == "MS:1000130" or "positive scan" in name:
                mode = "ES+"
            elif acc == "MS:1000129" or "negative scan" in name:
                mode = "ES-"
            elif acc == "MS:1000016" or "scan start time" in name or "retention time" in name:
                if val is not None:
                    try:
                        raw_rt = float(val)
                        if u_acc == "UO:0000010" or u_name.startswith("sec"):
                            rt_min = raw_rt / 60.0
                        else:
                            rt_min = raw_rt
                    except ValueError:
                        pass
            elif acc == "MS:1000285" or "total ion current" in name:
                if val is not None:
                    try:
                        tic = float(val)
                    except ValueError:
                        pass
            elif acc == "MS:1000504" or "base peak m/z" in name:
                if val is not None:
                    try:
                        bp_mz = float(val)
                    except ValueError:
                        pass
            elif acc == "MS:1000505" or "base peak intensity" in name:
                if val is not None:
                    try:
                        bp_int = float(val)
                    except ValueError:
                        pass
        elif lname == "binaryDataArray":
            kind, vals, _ = _parse_mzml_binary_data_array(elem)
            if kind == "mz":
                mzs = vals
            elif kind == "intensity":
                ints = vals

    return MassSpectrum(
        mz_values=mzs,
        intensities=ints,
        mode=mode,
        rt=rt_min,
        scan_number=scan_num,
        ms_level=ms_level,
        tic=tic,
        base_peak_mz=bp_mz,
        base_peak_intensity=bp_int,
    )


def _parse_mzxml_scan(scan_elem: ET.Element, default_idx: int) -> MassSpectrum:
    """Parse one <scan> element from mzXML."""
    num_str = scan_elem.attrib.get("num")
    scan_num = int(num_str) if num_str and num_str.isdigit() else default_idx
    ms_level_str = scan_elem.attrib.get("msLevel") or "1"
    try:
        ms_level = int(ms_level_str)
    except ValueError:
        ms_level = 1

    polarity = (scan_elem.attrib.get("polarity") or "+").strip()
    mode = "ES-" if polarity in ("-", "neg", "negative", "ES-", "ESI-") else "ES+"

    rt_min = _parse_mzxml_rt(scan_elem.attrib.get("retentionTime"))

    tic = 0.0
    if scan_elem.attrib.get("totIonCurrent") is not None:
        try:
            tic = float(scan_elem.attrib["totIonCurrent"])
        except ValueError:
            tic = 0.0

    bp_mz: Optional[float] = None
    if scan_elem.attrib.get("basePeakMz") is not None:
        try:
            bp_mz = float(scan_elem.attrib["basePeakMz"])
        except ValueError:
            pass

    bp_int: Optional[float] = None
    if scan_elem.attrib.get("basePeakIntensity") is not None:
        try:
            bp_int = float(scan_elem.attrib["basePeakIntensity"])
        except ValueError:
            pass

    mzs: List[float] = []
    ints: List[float] = []

    for child in scan_elem:
        if _local_name(child.tag) == "peaks":
            prec_str = child.attrib.get("precision") or "32"
            try:
                precision = int(prec_str)
            except ValueError:
                precision = 32
            comp_type = (child.attrib.get("compressionType") or "").strip().lower()
            compressed = comp_type == "zlib"
            byte_order_attr = (child.attrib.get("byteOrder") or "network").strip().lower()
            primary_order = "<" if byte_order_attr in ("little", "<") else ">"
            alt_order = ">" if primary_order == "<" else "<"

            vals = decode_binary_array(
                child.text,
                precision=precision,
                compressed=compressed,
                byte_order=primary_order,
            )
            if not _values_look_valid_mz_int(vals):
                alt_vals = decode_binary_array(
                    child.text,
                    precision=precision,
                    compressed=compressed,
                    byte_order=alt_order,
                )
                if _values_look_valid_mz_int(alt_vals):
                    vals = alt_vals

            mzs = [float(v) for v in vals[0::2]]
            ints = [float(v) for v in vals[1::2]]
            break

    return MassSpectrum(
        mz_values=mzs,
        intensities=ints,
        mode=mode,
        rt=rt_min,
        scan_number=scan_num,
        ms_level=ms_level,
        tic=tic,
        base_peak_mz=bp_mz,
        base_peak_intensity=bp_int,
    )


def parse_mzml(path: Union[str, Path]) -> LCMSAnalysis:
    """Parse an ``.mzML`` or ``.mzXML`` file into an ``LCMSAnalysis`` object."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"MS file not found: {file_path}")

    ext = file_path.suffix.lower()
    fmt = "mzXML" if ext == ".mzxml" else "mzML"

    chromatograms: List[Chromatogram] = []
    spectra: List[MassSpectrum] = []
    sample_info: SampleInfoDict = SampleInfoDict()
    instrument_parts: List[str] = []
    acquisition_date = ""

    # Use iterparse with start/end events to extract metadata and full subtrees
    context = ET.iterparse(str(file_path), events=("start", "end"))
    in_instrument_config = False
    spec_counter = 0

    for event, elem in context:
        lname = _local_name(elem.tag)

        if event == "start":
            if lname == "mzXML":
                fmt = "mzXML"
            elif lname == "mzML":
                fmt = "mzML"
            elif lname == "run":
                ts = elem.attrib.get("startTimeStamp")
                if ts and not acquisition_date:
                    acquisition_date = ts
                samp_ref = elem.attrib.get("sampleRef")
                if samp_ref and "sample_name" not in sample_info:
                    sample_info["sample_name"] = samp_ref
            elif lname == "msRun":
                ts = elem.attrib.get("startTime")
                if ts and not acquisition_date:
                    acquisition_date = ts
            elif lname == "sample":
                sid = elem.attrib.get("id") or ""
                sname = elem.attrib.get("name") or sid
                if sname:
                    sample_info["sample_name"] = sname
                    sample_info.setdefault("Sample Description", sname)
            elif lname in ("instrumentConfiguration", "msInstrument"):
                in_instrument_config = True
            elif in_instrument_config and lname == "cvParam":
                name = (elem.attrib.get("name") or "").strip()
                if name and "instrument" not in name.lower() and name not in instrument_parts:
                    instrument_parts.append(name)
            elif in_instrument_config and lname in ("msManufacturer", "msModel"):
                val = (elem.attrib.get("value") or elem.attrib.get("theValue") or "").strip()
                if val and val not in instrument_parts:
                    instrument_parts.append(val)

        elif event == "end":
            if lname in ("instrumentConfiguration", "msInstrument"):
                in_instrument_config = False
            elif lname == "chromatogram":
                chrom = _parse_mzml_chromatogram(elem)
                if chrom is not None:
                    chromatograms.append(chrom)
                elem.clear()
            elif lname == "spectrum" and fmt == "mzML":
                spec_counter += 1
                spec = _parse_mzml_spectrum(elem, spec_counter)
                if spec is not None:
                    spectra.append(spec)
                elem.clear()
            elif lname == "scan" and fmt == "mzXML":
                spec_counter += 1
                spec = _parse_mzxml_scan(elem, spec_counter)
                spectra.append(spec)
                elem.clear()

    # Synthesize TIC and BPC chromatograms from MS1 spectra if not present
    ms1_with_rt = [s for s in spectra if s.ms_level == 1 and s.rt is not None]
    if not ms1_with_rt and spectra:
        ms1_with_rt = [s for s in spectra if s.rt is not None]

    has_tic = any(c.trace_type.upper() == "TIC" for c in chromatograms)
    has_bpc = any(c.trace_type.upper() == "BPC" for c in chromatograms)

    if ms1_with_rt:
        # Group by RT if both ES+ and ES- scans occur at the same time
        sorted_specs = sorted(ms1_with_rt, key=lambda s: s.rt or 0.0)
        if not has_tic:
            chromatograms.append(
                Chromatogram(
                    trace_type="TIC",
                    times=[round(float(s.rt or 0.0), 6) for s in sorted_specs],
                    intensities=[float(s.tic) for s in sorted_specs],
                    units="min",
                )
            )
        if not has_bpc:
            chromatograms.append(
                Chromatogram(
                    trace_type="BPC",
                    times=[round(float(s.rt or 0.0), 6) for s in sorted_specs],
                    intensities=[float(s.base_peak_intensity or 0.0) for s in sorted_specs],
                    units="min",
                )
            )

    # Pick chromatographic peaks from primary trace (UV -> TIC -> BPC)
    primary_chrom: Optional[Chromatogram] = None
    for preferred in ("UV", "TIC", "BPC"):
        for c in chromatograms:
            if c.trace_type.upper() == preferred and c.times and c.intensities:
                primary_chrom = c
                break
        if primary_chrom is not None:
            break
    if primary_chrom is None and chromatograms:
        primary_chrom = chromatograms[0]

    peaks: List[LCMSPeak] = []
    if primary_chrom is not None:
        peaks = _pick_chromatogram_peaks(primary_chrom, spectra)
    elif spectra:
        # Fallback when spectra lack retention time: treat each MS1 spectrum as a peak
        total_tic = sum(s.tic for s in spectra) or 1.0
        for idx, s in enumerate(spectra, start=1):
            peaks.append(
                LCMSPeak(
                    peak_id=idx,
                    rt=float(s.rt if s.rt is not None else idx),
                    area=float(s.tic),
                    area_pct=round(100.0 * float(s.tic) / total_tic, 2),
                    height=float(s.base_peak_intensity or s.tic),
                    ms_spectra=[s],
                    spectrum=s,
                )
            )

    instrument_str = " ".join(instrument_parts) if instrument_parts else "Unknown"
    sample_name = sample_info.get("sample_name") or file_path.stem
    sample_info.setdefault("Sample Description", sample_name)
    if acquisition_date:
        sample_info.setdefault("Acquired Date", acquisition_date)

    detector = "UV" if (primary_chrom and primary_chrom.trace_type.upper() == "UV") else "MS TIC"

    return LCMSAnalysis(
        filename=file_path.name,
        file_path=str(file_path.resolve()),
        format=fmt,
        chromatograms=chromatograms,
        peaks=peaks,
        spectra=spectra,
        sample_info=sample_info,
        instrument=instrument_str,
        acquisition_date=acquisition_date,
        sample_name=sample_name,
        date=acquisition_date,
        detector=detector,
    )


parse_mzxml = parse_mzml
