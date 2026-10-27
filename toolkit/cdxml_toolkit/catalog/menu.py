"""Catalog of ChemDraw's menu commands, read from the running application's own menu tree.

``IChemDrawApplication.MenuBars`` exposes every menu with a caption and a numeric
``CommandID``. ``IChemOfficeMenuItem.Execute`` runs a command on the current selection, so
this list is the map from a menu feature (Clean Up Structure, Predict 1H-NMR Shifts, ...)
to the identifier the COM layer accepts. Items with no command id are sub-menus or
dialog-only entries; they are recorded as popups.
"""

from __future__ import annotations

import gc
import json
import os
from typing import Any, Optional

NATIVE_LOCK_SECONDS = 120


def _plain(caption: str) -> str:
    return caption.replace("&", "")


def build_catalog(raw: list[dict[str, Any]], *, verified_on: str = "unverified") -> dict[str, Any]:
    """Turn the raw ``[{menu, items: [{caption, command_id}]}]`` walk into the committed shape."""
    menus = []
    commands = popups = separators = 0
    for entry in raw:
        items = []
        for item in entry["items"]:
            caption = item["caption"].strip()
            if not caption:
                separators += 1
            elif item.get("command_id"):
                commands += 1
                items.append({"caption": caption, "command_id": item["command_id"]})
            else:
                popups += 1
                items.append({"caption": caption, "popup": True})
        menus.append({"caption": _plain(entry["menu"]), "items": items})
    return {
        "schema": 1,
        "layer": "menu",
        "verified_on": verified_on,
        "sources": ["com"],
        "counts": {
            "menus": len(menus),
            "items": commands + popups,
            "commands": commands,
            "popups": popups,
            "separators": separators,
        },
        "menus": menus,
    }


def find_command(catalog: dict[str, Any], caption: str) -> Optional[tuple[str, int]]:
    """Return ``(menu caption, command id)`` for a menu item caption, ignoring case."""
    wanted = caption.strip().lower()
    for entry in catalog["menus"]:
        for item in entry["items"]:
            if item["caption"].lower() == wanted and "command_id" in item:
                return entry["caption"], item["command_id"]
    return None


def _walk(application) -> list[dict[str, Any]]:
    raw = []
    bar = application.MenuBars.Item(1)
    menus = bar.Menus
    for menu_index in range(1, menus.Count + 1):
        menu = menus.Item(menu_index)
        items = menu.MenuItems
        entry: dict[str, Any] = {"menu": menu.caption, "items": []}
        for item_index in range(1, items.Count + 1):
            item = items.Item(item_index)
            entry["items"].append({"caption": item.caption, "command_id": item.CommandID})
        raw.append(entry)
    return raw


def extract_live(*, verified_on: Optional[str] = None) -> dict[str, Any]:
    """Start a private ChemDraw (Windows), read its menus and quit it."""
    import pythoncom
    import win32com.client as win32

    from ..mcp_runtime.resource_lock import native_resource_lock

    with native_resource_lock("chemdraw_com", NATIVE_LOCK_SECONDS):
        pythoncom.CoInitialize()
        try:
            application = win32.DispatchEx("ChemDraw.Application")
            try:
                raw = _walk(application)
            finally:
                try:
                    application.Quit()
                except Exception:
                    pass
                # Drop every proxy of the exited server before the apartment is torn down.
                application = None
                gc.collect()
        finally:
            pythoncom.CoUninitialize()
    return build_catalog(raw, verified_on=verified_on or os.environ.get("CDX_VERIFIED_ON", "unverified"))


def dump(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=1) + "\n"
