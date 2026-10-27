"""Keep temp folders usable inside restricted Windows sandboxes.

Python 3.12+ on Windows gives ``tempfile.mkdtemp`` folders an owner-only ACL. A sandbox that runs the
agent's commands under a restricted token can create such a folder yet not write into it, so every
worker launch and every staged output fails with "Permission denied". When a probe shows that, temp
folders are created with the parent's inherited permissions instead. Ordinary hosts are untouched.
"""

from __future__ import annotations

import os
import secrets
import shutil
import sys
import tempfile
from typing import Callable, Optional


def mkdtemp_is_usable() -> bool:
    """Whether a folder made by ``tempfile.mkdtemp`` accepts a file."""
    folder = None
    try:
        folder = tempfile.mkdtemp(prefix="cdx-probe-")
        with open(os.path.join(folder, "write-test"), "wb") as handle:
            handle.write(b"0")
        return True
    except OSError:
        return False
    finally:
        if folder:
            shutil.rmtree(folder, ignore_errors=True)


def _inheriting_mkdtemp(suffix: Optional[str] = None, prefix: Optional[str] = None, dir=None) -> str:
    prefix = tempfile.gettempprefix() if prefix is None else prefix
    base = os.path.abspath(os.fspath(dir)) if dir is not None else tempfile.gettempdir()
    for _ in range(100):
        path = os.path.join(base, f"{prefix}{secrets.token_hex(4)}{suffix or ''}")
        try:
            os.mkdir(path)
        except FileExistsError:
            continue
        return path
    raise FileExistsError(f"no unused temp folder name under {base}")


def ensure_usable_mkdtemp(is_usable: Optional[Callable[[], bool]] = None) -> bool:
    """Replace ``tempfile.mkdtemp`` when its folders are unusable. Returns True when it was replaced."""
    if is_usable is None:
        if not (sys.platform == "win32" and sys.version_info >= (3, 12)):
            return False
        is_usable = mkdtemp_is_usable
    if is_usable():
        return False
    tempfile.mkdtemp = _inheriting_mkdtemp
    return True
