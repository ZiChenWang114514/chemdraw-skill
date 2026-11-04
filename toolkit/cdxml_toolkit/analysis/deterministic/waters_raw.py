"""Waters MassLynx ``.raw`` directory parser and ``_HEADER.TXT`` metadata extractor.

Extracts acquisition metadata (``Acquired Date``, ``Acquired Time``,
``Sample Description``, ``Instrument``, ``Conditions``, ``Inlet Method``)
from ``_HEADER.TXT`` (or ``_header.txt``) inside a Waters ``.raw`` directory
and populates ``LCMSAnalysis``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from .mzml_parser import (
    Chromatogram,
    LCMSAnalysis,
    LCMSPeak,
    MassSpectrum,
    SampleInfoDict,
    parse_mzml,
)

_CANONICAL_HEADER_KEYS: Dict[str, str] = {
    "acquired date": "Acquired Date",
    "acquired time": "Acquired Time",
    "sample description": "Sample Description",
    "sample id": "Sample ID",
    "sample name": "Sample Name",
    "instrument": "Instrument",
    "conditions": "Conditions",
    "inlet method": "Inlet Method",
    "ms method": "MS Method",
    "tune method": "Tune Method",
    "job code": "Job Code",
    "task code": "Task Code",
    "user name": "User Name",
    "vial": "Vial",
    "bottle": "Bottle",
    "solvent delay": "Solvent Delay",
}


def _find_header_file(raw_dir: Union[str, Path]) -> Optional[Path]:
    """Locate ``_HEADER.TXT`` (case-insensitive) inside *raw_dir*."""
    p = Path(raw_dir)
    if p.is_file():
        return p
    if not p.is_dir():
        return None
    for candidate in ("_HEADER.TXT", "_header.txt", "HEADER.TXT", "header.txt"):
        target = p / candidate
        if target.is_file():
            return target
    try:
        for child in p.iterdir():
            if child.is_file() and child.name.upper() in ("_HEADER.TXT", "HEADER.TXT"):
                return child
    except OSError:
        pass
    return None


def parse_waters_header(raw_dir: Union[str, Path]) -> Dict[str, str]:
    """Read ``_HEADER.TXT`` (or ``_header.txt``) inside a Waters ``.raw`` directory.

    Extracts ``Acquired Date``, ``Acquired Time``, ``Sample Description``,
    ``Instrument``, ``Conditions`` / ``Inlet Method``, and any other ``$$ Key: Value``
    entries into a dictionary.
    """
    p = Path(raw_dir)
    if not p.exists():
        raise FileNotFoundError(f"Waters .raw directory not found: {p}")

    header_path = _find_header_file(p)
    result: SampleInfoDict = SampleInfoDict()
    if header_path is None:
        return result

    raw_bytes = header_path.read_bytes()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="replace")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("$$"):
            line = line[2:].strip()
        if ":" in line:
            key_part, val_part = line.split(":", 1)
        elif "=" in line:
            key_part, val_part = line.split("=", 1)
        else:
            continue

        key_clean = key_part.strip()
        val_clean = val_part.strip()
        if not key_clean:
            continue

        lower_key = key_clean.lower()
        canonical_key = _CANONICAL_HEADER_KEYS.get(lower_key, key_clean)
        result[canonical_key] = val_clean
        snake_key = re.sub(r"[^a-z0-9]+", "_", lower_key).strip("_")
        if snake_key:
            result[snake_key] = val_clean

    acq_date = result.get("Acquired Date", "")
    acq_time = result.get("Acquired Time", "")
    if acq_date and acq_time:
        result["acquisition_date"] = f"{acq_date} {acq_time}"
    elif acq_date:
        result["acquisition_date"] = acq_date
    elif acq_time:
        result["acquisition_date"] = acq_time

    if "Sample Description" not in result and "Sample Name" in result:
        result["Sample Description"] = result["Sample Name"]
        result["sample_description"] = result["Sample Name"]

    method_val = result.get("Inlet Method") or result.get("Conditions") or result.get("MS Method") or ""
    if method_val:
        result.setdefault("method", method_val)

    return result


def parse_waters_raw(raw_dir: Union[str, Path]) -> LCMSAnalysis:
    """Parse a Waters ``.raw`` directory and attach ``_HEADER.TXT`` metadata onto ``LCMSAnalysis``."""
    p = Path(raw_dir)
    if not p.exists():
        raise FileNotFoundError(f"Waters .raw directory not found: {p}")

    header = parse_waters_header(p)
    chromatograms: List[Chromatogram] = []
    peaks: List[LCMSPeak] = []
    spectra: List[MassSpectrum] = []

    # If a companion or converted .mzML / .mzXML exists inside the .raw folder, parse its traces
    if p.is_dir():
        for child in sorted(p.iterdir()):
            if child.is_file() and child.suffix.lower() in (".mzml", ".mzxml"):
                try:
                    sub = parse_mzml(child)
                    chromatograms.extend(sub.chromatograms)
                    peaks.extend(sub.peaks)
                    spectra.extend(sub.spectra)
                    break
                except Exception:
                    pass

    acq_date = header.get("acquisition_date") or header.get("Acquired Date") or ""
    instrument = header.get("Instrument") or header.get("instrument") or "Unknown"
    sample_desc = (
        header.get("Sample Description")
        or header.get("sample_description")
        or header.get("Sample Name")
        or p.stem
    )
    method = (
        header.get("Inlet Method")
        or header.get("Conditions")
        or header.get("inlet_method")
        or header.get("conditions")
        or ""
    )

    sample_info = SampleInfoDict(header)
    if sample_desc:
        sample_info.setdefault("Sample Description", sample_desc)
        sample_info.setdefault("sample_description", sample_desc)

    return LCMSAnalysis(
        filename=p.name,
        file_path=str(p.resolve()),
        format="Waters .raw",
        chromatograms=chromatograms,
        peaks=peaks,
        spectra=spectra,
        sample_info=sample_info,
        instrument=instrument,
        acquisition_date=acq_date,
        method=method,
        method_path=method,
        method_short=method,
        sample_name=sample_desc,
        date=header.get("Acquired Date", ""),
        time=header.get("Acquired Time", ""),
        detector="MS TIC",
    )
