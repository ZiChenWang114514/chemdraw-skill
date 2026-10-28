"""ChemDraw's own stoichiometry grid: Structure > Analyze Stoichiometry, and reading it back.

ChemDraw draws the grid under a reaction and recomputes it as amounts are typed into it.
``analyze`` runs the command on a copy of a reaction (Windows through COM, macOS through the
application menu) and saves the result as a new CDXML file; ``read_grid`` reads every grid of a
saved file, so the numbers someone typed in ChemDraw come back without ChemDraw.

ChemDraw enables the command only in a visible window, so the toolkit shows its own private
ChemDraw for a moment, saves, closes the document unsaved and quits. ChemDraw windows the user
already has open are not touched; ``open_result`` then opens the saved file in the user's
ChemDraw.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any
import xml.etree.ElementTree as ET

from ..mcp_runtime.artifact_safety import _available_path
from ..mcp_runtime.resource_lock import native_resource_lock

logger = logging.getLogger(__name__)

MENU_CAPTION = "Analyze Stoichiometry"
MENU_NAME = "Structure"
COMMAND_ID = 367  # ChemDraw 22.2, from the committed menu catalog
LOCK_SECONDS = 300
GRID_WAIT_SECONDS = 10.0
GRID_TAG = "stoichiometrygrid"

_STEP_ROLES = (
    ("ReactionStepReactants", "reactant"),
    ("ReactionStepObjectsAboveArrow", "agent"),
    ("ReactionStepObjectsBelowArrow", "agent"),
    ("ReactionStepProducts", "product"),
)


class StoichiometryGridError(RuntimeError):
    """A failure with a stable public error code."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.public_message = message


# --- reading a saved grid --------------------------------------------------------------

def _cell_value(datum: ET.Element) -> Any:
    raw = datum.get("SGDataValue")
    kind = datum.get("SGDataType")
    if raw is None or raw == "":
        return None
    if kind == "1":
        return raw not in ("0", "no", "false")
    if kind == "3":
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def _cell_text(datum: ET.Element) -> str:
    return "".join("".join(s.itertext()) for s in datum.iter("s"))


def _roles(root: ET.Element) -> dict[str, str]:
    roles: dict[str, str] = {}
    for step in root.iter("step"):
        for attribute, role in _STEP_ROLES:
            for object_id in (step.get(attribute) or "").split():
                roles.setdefault(object_id, role)
    return roles


def _read_one(grid: ET.Element, roles: dict[str, str]) -> dict:
    components = grid.findall("sgcomponent")
    labels: dict[bool, dict[str, str]] = {True: {}, False: {}}
    for component in components:
        if component.get("ComponentIsHeader") == "yes":
            side = component.get("ComponentIsReactant") == "yes"
            for datum in component.findall("sgdatum"):
                labels[side][datum.get("SGPropertyType", "")] = datum.get("SGDataValue") or _cell_text(datum)
    rows = []
    for component in components:
        if component.get("ComponentIsHeader") == "yes":
            continue
        side = component.get("ComponentIsReactant") == "yes"
        object_id = component.get("ComponentReferenceID")
        cells: dict[str, dict] = {}
        for datum in component.findall("sgdatum"):
            if datum.get("IsHidden") == "yes":
                continue
            prop = datum.get("SGPropertyType", "")
            cell: dict[str, Any] = {"value": _cell_value(datum), "text": _cell_text(datum)}
            if datum.get("IsEdited") == "yes":
                cell["edited"] = True
            cells[labels[side].get(prop) or f"property {prop}"] = cell
        role = roles.get(object_id or "") or ("reactant side" if side else "product")
        rows.append({"object_id": object_id, "role": role, "cells": cells})
    return {"id": grid.get("id"), "rows": rows}


def read_grid(path: str | Path) -> dict:
    """Every stoichiometry grid in a saved CDXML file, as ChemDraw wrote it.

    Each row is one component, with its role in the reaction step (reactant, agent or
    product) and one cell per visible column, keyed by ChemDraw's own column caption:
    ``value`` is the stored number (masses in g, amounts in mol, fractions for percentages)
    and ``text`` is what the grid shows, with units.
    """
    source = Path(path).expanduser()
    if source.suffix.lower() != ".cdxml":
        raise ValueError("The stoichiometry grid is read from a CDXML file; save the drawing as .cdxml")
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    root = ET.parse(source).getroot()
    grids = [_read_one(grid, _roles(root)) for grid in root.iter(GRID_TAG)]
    if not grids:
        raise StoichiometryGridError(
            "no_grid",
            f"The file holds no stoichiometry grid. Select the reaction in ChemDraw and choose "
            f"{MENU_NAME} > {MENU_CAPTION}, or run the analysis on this file first.")
    warnings = []
    if len(grids) > 1:
        warnings.append(f"The file holds {len(grids)} stoichiometry grids; each is listed in document order.")
    return {"ok": True, "operation": "stoichiometry_grid", "mode": "read", "path": str(source.resolve()),
            "grids": grids, "warnings": warnings}


# --- a reaction to analyze ---------------------------------------------------------------

def reaction_document(reaction: str, destination: Path) -> Path:
    """Draw a reaction SMILES "reactants>agents>products" as CDXML, agents above the arrow."""
    parts = reaction.strip().split(">")
    if len(parts) != 3 or not parts[0] or not parts[2]:
        raise ValueError('Give a reaction SMILES "reactants>agents>products" or a .cdxml/.cdx file')
    sides = [[smiles for smiles in part.split(".") if smiles] for part in parts]
    structures: list[str] = []
    keys: list[list[str]] = []
    for side in sides:
        keys.append([])
        for smiles in side:
            structures.append(smiles)
            keys[-1].append(f"S{len(structures)}")
    lines = ["layout: linear", "structures:"]
    for index, smiles in enumerate(structures, 1):
        lines += [f"  S{index}:", f"    smiles: {json.dumps(smiles)}"]
    lines += ["steps:", f"  - substrates: [{', '.join(keys[0])}]", f"    products: [{', '.join(keys[2])}]"]
    if keys[1]:
        lines += ["    above_arrow:", f"      structures: [{', '.join(keys[1])}]"]
    from ..mcp_runtime import official_overrides as api
    api.render_scheme(yaml_text="\n".join(lines) + "\n", output_path=str(destination))
    if not destination.is_file():
        raise StoichiometryGridError("scheme_failed", "The reaction could not be drawn")
    return destination


# --- running ChemDraw ------------------------------------------------------------------

def _dispatch():
    """A private ChemDraw (never the user's running one)."""
    from ..mcp_runtime import native_renderer
    application, _ = native_renderer._acquire_application()
    return application


def _apartment():
    from ..mcp_runtime import native_renderer
    return native_renderer._com_apartment()


def _settle(seconds: float) -> None:
    time.sleep(seconds)


def _menu_item(application) -> Any:
    bar = application.MenuBars.Item(1)
    by_caption = None
    for menu_index in range(1, bar.Menus.Count + 1):
        items = bar.Menus.Item(menu_index).MenuItems
        for item_index in range(1, items.Count + 1):
            item = items.Item(item_index)
            try:
                if int(item.CommandID) == COMMAND_ID:
                    return item
                if str(item.caption).replace("&", "") == MENU_CAPTION:
                    by_caption = item
            except Exception:
                continue
    return by_caption


def _cleanup(step: str, action) -> None:
    try:
        action()
    except Exception as exc:
        # Only the exception type: COM messages can quote paths or document content.
        logger.warning("ChemDraw cleanup step %s failed (%s)", step, type(exc).__name__)


def _analyze_windows(work: Path, output: Path) -> None:
    with native_resource_lock("chemdraw_com", LOCK_SECONDS), _apartment():
        application = _dispatch()
        document = None
        try:
            application.Visible = True  # ChemDraw enables the command only in a visible window
            document = application.Documents.Open(str(work))
            _settle(1.0)
            _cleanup("activate", document.Activate)
            document.Objects.Select()
            _settle(0.5)
            before = int(document.StoichiometryGrids.Count)
            item = _menu_item(application)
            if item is None:
                raise StoichiometryGridError(
                    "chemdraw_command_missing", f"This ChemDraw has no {MENU_NAME} > {MENU_CAPTION} command")
            if not item.Enabled:
                raise StoichiometryGridError(
                    "no_reaction", f"ChemDraw did not enable {MENU_CAPTION}: the drawing needs a reaction "
                                   "with an arrow, reactants and products")
            item.Execute()
            waited = 0.0
            while int(document.StoichiometryGrids.Count) <= before and waited < GRID_WAIT_SECONDS:
                _settle(0.25)
                waited += 0.25
            if int(document.StoichiometryGrids.Count) <= before:
                raise StoichiometryGridError("no_grid", f"ChemDraw ran {MENU_CAPTION} but drew no grid")
            document.SaveAs(str(output))
        finally:
            # Close unsaved before quitting: ChemDraw would otherwise save the open copy.
            if document is not None:
                _cleanup("close", lambda: document.Close(False))
            _cleanup("quit", application.Quit)
            document = application = None


def _analyze_macos(work: Path, output: Path) -> None:
    from . import mac_automation
    with mac_automation.MacChemDrawSession() as session:
        session.apply_menu(work, output, (MENU_NAME, MENU_CAPTION))


def open_in_chemdraw(path: Path) -> bool:
    """Show a saved file in the user's ChemDraw."""
    try:
        if sys.platform == "darwin":
            return subprocess.run(["open", "-a", "ChemDraw", str(path)], capture_output=True,
                                  timeout=60).returncode == 0
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606 - ChemDraw is the .cdxml handler
            return True
    except (OSError, subprocess.TimeoutExpired):
        return False
    return False


def _has_grid(path: Path) -> bool:
    return path.suffix.lower() == ".cdxml" and f"<{GRID_TAG}" in path.read_text(encoding="utf-8", errors="replace")


def analyze(source: str, output_path: str | None = None, *, open_result: bool = False) -> dict:
    """Run ChemDraw's Analyze Stoichiometry on a reaction and read the grid it draws.

    source is a reaction SMILES "reactants>agents>products" (agents are drawn above the
    arrow) or a .cdxml/.cdx file holding a reaction. The source is never changed: ChemDraw
    works on a copy and the result is saved to output_path (.cdxml; default
    "<name>-stoichiometry.cdxml" beside the file, or "reaction-stoichiometry.cdxml" in the
    current folder), and an existing file is never replaced. open_result opens the result in
    the user's ChemDraw, where amounts typed into the grid recompute the rest; read the
    saved file again with read_grid.
    """
    if sys.platform == "win32":
        runner = _analyze_windows
    elif sys.platform == "darwin":
        runner = _analyze_macos
    else:
        raise StoichiometryGridError(
            "chemdraw_unavailable", f"{MENU_CAPTION} needs desktop ChemDraw on Windows or macOS")
    candidate = Path(source).expanduser() if len(source) < 1024 and "\n" not in source else None
    is_file = candidate is not None and candidate.suffix.lower() in (".cdxml", ".cdx")
    if is_file:
        if not candidate.is_file():
            raise FileNotFoundError(f"Input file does not exist: {candidate}")
        if _has_grid(candidate):
            raise ValueError(f"{candidate.name} already holds a stoichiometry grid; read it instead, "
                             "or delete the grid in ChemDraw before analyzing again")
        default = candidate.resolve().with_name(f"{candidate.stem}-stoichiometry.cdxml")
    else:
        default = Path.cwd() / "reaction-stoichiometry.cdxml"
    target = Path(output_path).expanduser().resolve() if output_path else default
    if target.suffix.lower() != ".cdxml":
        raise ValueError("output_path must end in .cdxml")
    target = _available_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cdx-stoich-") as folder:
        if is_file:
            work = Path(folder) / f"reaction{candidate.suffix.lower()}"
            shutil.copyfile(candidate, work)
        else:
            work = reaction_document(source, Path(folder) / "reaction.cdxml")
        runner(work, target)
    if not target.is_file():
        raise StoichiometryGridError("no_grid", f"ChemDraw did not save the result of {MENU_CAPTION}")
    result = read_grid(target)
    result.update(mode="analyze", opened=open_in_chemdraw(target) if open_result else False)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cdx.py calc",
        description=f"ChemDraw's own stoichiometry grid ({MENU_NAME} > {MENU_CAPTION}).")
    parser.add_argument("source", nargs="?", help='reaction SMILES "reactants>agents>products" or a .cdxml/.cdx file')
    parser.add_argument("--read", metavar="CDXML", help="only read the grid of a saved file")
    parser.add_argument("--output", help="where to save the result (.cdxml; never replaces a file)")
    parser.add_argument("--no-open", action="store_true", help="do not open the result in ChemDraw")
    args = parser.parse_args(argv)
    if bool(args.read) == bool(args.source):
        parser.error("give a reaction or file to analyze, or --read FILE")
    try:
        if args.read:
            result = read_grid(args.read)
        else:
            result = analyze(args.source, args.output, open_result=not args.no_open)
    except (StoichiometryGridError, ValueError, FileNotFoundError) as exc:
        code = getattr(exc, "error_code", "invalid_input")
        print(json.dumps({"ok": False, "error": {"code": code, "message": str(exc)}}, indent=2))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
