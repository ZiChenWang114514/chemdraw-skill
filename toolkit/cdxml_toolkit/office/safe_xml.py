"""Open Office packages and parse their XML without trusting them.

Office files come from users and mail. A part with an entity declaration must not
expand into a large tree or reach the network, and a package must not unpack into
more data than a document can plausibly hold.
"""

from __future__ import annotations

import zipfile

# A real document with embedded media stays far below these; an archive built to
# exhaust memory or disk does not.
MAX_PACKAGE_BYTES = 2 * 1024 ** 3      # everything unpacked
MAX_PACKAGE_MEMBERS = 20_000
MAX_MEMBER_RATIO = 200                 # unpacked / packed, checked on large parts only
RATIO_CHECK_FROM_BYTES = 32 * 1024 ** 2


class UnsafePackage(ValueError):
    """The archive is not a plausible Office document and was not read."""


def open_package(path) -> zipfile.ZipFile:
    """Open a package for reading after checking what it would unpack to."""
    package = zipfile.ZipFile(path, "r")
    try:
        members = package.infolist()
        if len(members) > MAX_PACKAGE_MEMBERS:
            raise UnsafePackage(f"{path}: {len(members)} parts (limit {MAX_PACKAGE_MEMBERS}).")
        total = 0
        for member in members:
            total += member.file_size
            if (member.file_size >= RATIO_CHECK_FROM_BYTES
                    and member.file_size > MAX_MEMBER_RATIO * max(member.compress_size, 1)):
                raise UnsafePackage(
                    f"{path}: part {member.filename} unpacks to {member.file_size} bytes from "
                    f"{member.compress_size} (more than {MAX_MEMBER_RATIO} to 1)."
                )
        if total > MAX_PACKAGE_BYTES:
            raise UnsafePackage(f"{path}: unpacks to {total} bytes (limit {MAX_PACKAGE_BYTES}).")
    except Exception:
        package.close()
        raise
    return package


def fromstring(data):
    from lxml import etree

    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    return etree.fromstring(data, parser)
