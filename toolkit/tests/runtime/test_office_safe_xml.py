"""Office package parts are parsed without entity expansion."""

from __future__ import annotations

from pathlib import Path

from cdxml_toolkit.office import safe_xml

OFFICE = Path(__file__).resolve().parents[2] / "cdxml_toolkit" / "office"


def test_entities_are_not_expanded():
    root = safe_xml.fromstring(b'<!DOCTYPE r [<!ENTITY e "expanded">]><r>&e;</r>')
    assert "expanded" not in (root.text or "")


def test_office_modules_parse_through_the_safe_helper():
    offenders = [
        path.name
        for path in OFFICE.glob("*.py")
        if "etree.fromstring(" in path.read_text(encoding="utf-8") and path.name != "safe_xml.py"
    ]
    assert offenders == []
