"""Run py2opsin with an input file private to the call.

py2opsin stages the name in ``tmp_fpath``; a fixed path in the shared temp folder lets
parallel workers read or delete each other's input.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Callable
import warnings


def py2opsin_private(py2opsin: Callable[..., Any], name: str) -> Any:
    with tempfile.TemporaryDirectory(prefix="cdxml-opsin-") as folder:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return py2opsin(name, tmp_fpath=os.path.join(folder, "input.txt"))
