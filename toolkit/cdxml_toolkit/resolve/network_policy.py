"""Process-wide switch that keeps remote lookups and downloads on the machine.

Set ``CHEMDRAW_OFFLINE=1`` (or true/yes/on) for confidential or offline work: PubChem
lookups return nothing, the Java runtime is not downloaded and DECIMER uploads are
refused. Tool workers inherit the variable (``CHEMDRAW_*`` is forwarded).
"""

from __future__ import annotations

import os

OFFLINE_ENV = "CHEMDRAW_OFFLINE"


def network_allowed() -> bool:
    return os.environ.get(OFFLINE_ENV, "").strip().lower() not in ("1", "true", "yes", "on")


def offline_reason(what: str) -> str:
    return f"{what} skipped: {OFFLINE_ENV} is set, so nothing leaves this machine"
