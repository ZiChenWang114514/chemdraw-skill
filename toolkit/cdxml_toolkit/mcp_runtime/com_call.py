"""chemdraw_com_call: a declarative program over ChemDraw's COM automation objects.

The program is checked against the committed COM catalog before ChemDraw starts: every
member must exist on the type the alias holds, with the access the step needs, and every
result gets the catalog's type, so ``doc.Objects.Atoms`` is known to be a collection of
``IChemDrawAtom`` without asking ChemDraw. Members with side effects outside the document
(printing, the clipboard, menus, preferences, quitting) are blocked, and file access needs
explicit opt-ins, as in the ChemScript SDK tool.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
import json
import logging
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterator, Optional

from . import artifact_safety

logger = logging.getLogger(__name__)

SUPPORTED_OPERATIONS = ("get", "set", "call", "iterate", "release")
MAX_PROGRAM_STEPS = 200
MAX_REQUEST_BYTES = 256 * 1024
MAX_ITERATION_ITEMS = 1000
MAX_TEXT = 20000
ROOT = "app"
_ALIAS = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

BLOCKED_MEMBERS = {
    "Quit": "the tool starts and quits ChemDraw itself",
    "Print": "printing is outside the document",
    "PrintOut": "printing is outside the document",
    "Paste": "it reads the user's clipboard",
    "Copy": "it writes the user's clipboard",
    "Cut": "it writes the user's clipboard",
}
BLOCKED_TYPES = {
    "IChemOfficeMenuBars": "menu commands are run by dedicated tools",
    "IChemOfficeMenuBar": "menu commands are run by dedicated tools",
    "IChemOfficeMenus": "menu commands are run by dedicated tools",
    "IChemOfficeMenu": "menu commands are run by dedicated tools",
    "IChemOfficeMenuItems": "menu commands are run by dedicated tools",
    "IChemOfficeMenuItem": "menu commands are run by dedicated tools",
}
# Setting anything on the preferences changes the user's ChemDraw for good.
READ_ONLY_TYPES = {"IChemDrawPreferences": "preferences belong to the user"}
BLOCKED_PAIRS = {
    ("IChemDrawApplication", "MenuBars"): "menu commands are run by dedicated tools",
    ("IChemDrawDocuments", "Close"): "it would close documents the program did not open",
}
FILE_READ = {("IChemDrawDocuments", "Open"), ("DataObjectFiles", "Add")}
FILE_WRITE = {("IChemDrawDocument", "SaveAs")}
OVERWRITING = {("IChemDrawDocument", "Save")}
EXPORT_SUFFIXES = {
    ".cdxml", ".cdx", ".png", ".svg", ".emf", ".wmf", ".pdf", ".jpg", ".jpeg", ".tif", ".tiff",
    ".gif", ".bmp", ".mol", ".sdf", ".rxn", ".smi", ".cml", ".eps",
}


class ComCallError(RuntimeError):
    """A ChemDraw failure with a stable public code."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.public_message = message


# ---------------------------------------------------------------------------- catalog


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    from cdxml_toolkit.catalog import classify

    library = classify.load_catalog("com")["object_library"]
    types: dict[str, dict[str, Any]] = {}
    constants: dict[str, int] = {}
    for entry in library["types"]:
        if entry["kind"] == "dispatch":
            types[entry["name"]] = {
                "members": {m["name"]: m for m in entry["members"] if not m.get("hidden")},
            }
        elif entry["kind"] == "enum":
            constants.update({m["name"]: m["value"] for m in entry["members"] if m["kind"] == "constant"})
    return {"types": types, "constants": constants}


def _type_of(declared: Optional[str]) -> Optional[str]:
    """The catalog dispatch type a declared type names, or None for scalars and unknowns."""
    name = (declared or "").rstrip("*")
    return name if name in _catalog()["types"] else None


def _is_collection(type_name: str) -> bool:
    members = _catalog()["types"][type_name]["members"]
    return "Count" in members and "Item" in members and members["Item"]["kind"] == "method"


def _element_type(collection: str) -> Optional[str]:
    declared = _type_of(_catalog()["types"][collection]["members"]["Item"].get("returns"))
    if declared:
        return declared
    types = _catalog()["types"]
    for candidate in (collection[:-3] + "y" if collection.endswith("ies") else None, collection[:-1]):
        if candidate and candidate in types:
            return candidate
    return None


# ------------------------------------------------------------------------ validation


def _check_value(index: int, value: Any, aliases: dict[str, Optional[str]], what: str) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"program step {index} {what} must be a finite number")
        return value
    if isinstance(value, dict) and set(value) == {"constant"}:
        constants = _catalog()["constants"]
        if value["constant"] not in constants:
            raise ValueError(f"program step {index} names an unknown constant {value['constant']!r}")
        return constants[value["constant"]]
    if isinstance(value, dict) and set(value) == {"ref"}:
        if value["ref"] not in aliases or aliases[value["ref"]] is None:
            raise ValueError(f"program step {index} refers to {value['ref']!r}, which is not an object alias")
        return value
    raise ValueError(f"program step {index} {what} must be a string, number, boolean, null, "
                     "{\"constant\": name} or {\"ref\": alias}")


def _access(index: int, type_name: str, member: dict[str, Any], operation: str) -> None:
    name = member["name"]
    if name in BLOCKED_MEMBERS or BLOCKED_PAIRS.get((type_name, name)):
        why = BLOCKED_MEMBERS.get(name) or BLOCKED_PAIRS[(type_name, name)]
        raise ValueError(f"program step {index}: {type_name}.{name} is blocked ({why})")
    if type_name in BLOCKED_TYPES:
        raise ValueError(f"program step {index}: {type_name} is blocked ({BLOCKED_TYPES[type_name]})")
    if operation == "set" and type_name in READ_ONLY_TYPES:
        raise ValueError(f"program step {index}: {type_name}.{name} is blocked ({READ_ONLY_TYPES[type_name]})")


def validate_program(
    program: list[dict[str, Any]],
    *,
    allow_file_io: bool = False,
    allow_overwrite: bool = False,
) -> list[dict[str, Any]]:
    """Check the program against the COM catalog and return the steps with their types."""
    if not isinstance(program, list) or not program:
        raise ValueError("program must be a non-empty list")
    if len(program) > MAX_PROGRAM_STEPS:
        raise ValueError(f"program may contain at most {MAX_PROGRAM_STEPS} steps")
    try:
        encoded = json.dumps(program, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("program must contain JSON-compatible values") from exc
    if len(encoded) > MAX_REQUEST_BYTES:
        raise ValueError("program exceeds the configured request limit")

    types = _catalog()["types"]
    aliases: dict[str, Optional[str]] = {ROOT: "IChemDrawApplication"}
    used: set[str] = set()
    steps: list[dict[str, Any]] = []
    for index, original in enumerate(program):
        if not isinstance(original, dict):
            raise ValueError(f"program step {index} must be an object")
        step = dict(original)
        operation = step.get("op")
        if operation not in SUPPORTED_OPERATIONS:
            raise ValueError(f"program step {index} uses an unsupported operation")
        target = step.setdefault("target", ROOT)
        if not isinstance(target, str) or target not in aliases:
            raise ValueError(f"program step {index} uses unknown alias {target!r}")
        if operation == "release":
            if target == ROOT:
                raise ValueError(f"program step {index} cannot release the reserved alias {ROOT}")
            aliases.pop(target)
            steps.append(step)
            continue
        owner = aliases[target]
        if owner is None:
            raise ValueError(f"program step {index}: {target} holds a value, not an object")
        step["owner_type"] = owner

        if operation == "iterate":
            if not _is_collection(owner):
                raise ValueError(f"program step {index}: {owner} is not a collection (it has no Count and Item)")
            element = _element_type(owner)
            members = step.get("members", [])
            if not isinstance(members, list) or not all(isinstance(m, str) for m in members):
                raise ValueError(f"program step {index} members must be a list of names")
            if members and element is None:
                raise ValueError(f"program step {index}: the element type of {owner} is unknown, so its members cannot be read")
            for name in members:
                member = types[element]["members"].get(name)
                if member is None:
                    raise ValueError(f"program step {index}: {element} has no member {name}")
                _access(index, element, member, "get")
                if member["kind"] != "property" or "get" not in member.get("access", []) or member.get("parameters"):
                    raise ValueError(f"program step {index}: {element}.{name} is not a readable property")
            step["element_type"] = element
            step["result_type"] = None
        else:
            name = step.get("member")
            if not isinstance(name, str) or not name:
                raise ValueError(f"program step {index} requires member")
            member = types[owner]["members"].get(name)
            if member is None:
                raise ValueError(f"program step {index}: {owner} has no member {name}")
            _access(index, owner, member, operation)
            if operation in ("get", "set"):
                if member["kind"] == "method":
                    raise ValueError(f"program step {index}: {owner}.{name} is a method; use op call")
                if member.get("parameters"):
                    raise ValueError(f"program step {index}: {owner}.{name} takes parameters, which get and set do not support")
                access = member.get("access", [])
                if operation == "get" and "get" not in access:
                    raise ValueError(f"program step {index}: {owner}.{name} is not readable")
                if operation == "set" and not ({"put", "putref"} & set(access)):
                    raise ValueError(f"program step {index}: {owner}.{name} is not writable")
            else:
                if member["kind"] != "method":
                    raise ValueError(f"program step {index}: {owner}.{name} is a property; use op get or set")
            if operation == "set":
                if "value" not in step:
                    raise ValueError(f"program step {index} requires value")
                step["value"] = _check_value(index, step["value"], aliases, "value")
            if operation == "call":
                arguments = step.get("args", [])
                if not isinstance(arguments, list):
                    raise ValueError(f"program step {index} args must be a list")
                parameters = member.get("parameters", [])
                required = sum(1 for p in parameters if not p.get("optional"))
                if len(arguments) < required:
                    raise ValueError(f"program step {index}: {owner}.{name} needs at least {required} argument(s)")
                if len(arguments) > len(parameters):
                    raise ValueError(f"program step {index}: {owner}.{name} takes at most {len(parameters)} argument(s)")
                step["args"] = [_check_value(index, item, aliases, "argument") for item in arguments]
                _check_files(index, owner, name, step["args"], allow_file_io, allow_overwrite)
            declared = member.get("type") if member["kind"] == "property" else member.get("returns")
            step["result_type"] = _type_of(declared)
            if step["result_type"] is None and name == "Item" and _is_collection(owner):
                step["result_type"] = _element_type(owner)

        alias = step.get("as")
        if alias is not None:
            if not isinstance(alias, str) or not _ALIAS.fullmatch(alias):
                raise ValueError(f"program step {index} has an invalid result alias")
            if alias == ROOT:
                raise ValueError(f"program step {index}: the alias {ROOT} is reserved")
            if alias in used:
                raise ValueError(f"program step {index}: the alias {alias} is already used")
            used.add(alias)
            aliases[alias] = step["result_type"]
        steps.append(step)
    return steps


def _check_files(index: int, owner: str, name: str, args: list[Any], allow_file_io: bool, allow_overwrite: bool) -> None:
    pair = (owner, name)
    if pair in FILE_READ or pair in FILE_WRITE or pair in OVERWRITING:
        if not allow_file_io:
            raise ValueError(f"program step {index}: {owner}.{name} reads or writes files and needs allow_file_io")
    if pair in OVERWRITING and not allow_overwrite:
        raise ValueError(f"program step {index}: {owner}.{name} replaces the file the document came from; it needs allow_overwrite")
    if pair == ("IChemDrawDocument", "Close"):
        if not (args and args[0] is False) and not allow_overwrite:
            raise ValueError(
                f"program step {index}: Close may save over the document's file; pass false as the first "
                "argument or set allow_overwrite")
    if pair in FILE_WRITE and not (args and isinstance(args[0], str) and args[0]):
        raise ValueError(f"program step {index}: {owner}.{name} needs a file name as its first argument")


# ------------------------------------------------------------------------- execution


def _plain(value: Any, type_name: Optional[str]) -> Any:
    if type_name is not None:
        return {"object": type_name}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "...[truncated]"


def _resolve(value: Any, objects: dict[str, Any]) -> Any:
    if isinstance(value, dict) and "ref" in value:
        return objects[value["ref"]]
    return value


def _guard_file_call(owner: str, name: str, args: list[Any], allow_overwrite: bool, written: list[str]) -> list[Any]:
    pair = (owner, name)
    if pair in FILE_READ and args:
        source = Path(str(args[0])).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Input file does not exist: {source}")
        return [str(source), *args[1:]]
    if pair in FILE_WRITE:
        target = Path(str(args[0])).expanduser().resolve()
        if target.suffix.lower() not in EXPORT_SUFFIXES:
            raise ValueError(f"SaveAs format {target.suffix or '(none)'} is not one ChemDraw exports here; "
                             f"use one of {', '.join(sorted(EXPORT_SUFFIXES))}")
        if target.exists() and not allow_overwrite:
            raise FileExistsError(f"Refusing to overwrite an existing file: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        written.append(str(target))
        return [str(target), *args[1:]]
    return args


def execute_program(
    application: Any,
    steps: list[dict[str, Any]],
    *,
    max_items: int = 100,
    allow_overwrite: bool = False,
    created: Optional[list[Any]] = None,
) -> dict[str, Any]:
    """Run validated steps against ``application``; returns results and written files.

    Documents the program adds or opens are appended to ``created`` as they appear, so the
    caller can close them even when a later step fails.
    """
    objects: dict[str, Any] = {ROOT: application}
    types: dict[str, Optional[str]] = {ROOT: "IChemDrawApplication"}
    created = created if created is not None else []
    written: list[str] = []
    results = []
    for index, step in enumerate(steps):
        operation = step["op"]
        target_alias = step["target"]
        if operation == "release":
            objects.pop(target_alias, None)
            results.append({"step": index, "op": operation, "value": True})
            continue
        target = objects[target_alias]
        owner = types[target_alias]
        value: Any
        if operation == "get":
            value = getattr(target, step["member"])
        elif operation == "set":
            value = _resolve(step["value"], objects)
            setattr(target, step["member"], value)
        elif operation == "call":
            args = [_resolve(item, objects) for item in step["args"]]
            args = _guard_file_call(owner, step["member"], args, allow_overwrite, written)
            value = getattr(target, step["member"])(*args)
            if (owner, step["member"]) in FILE_WRITE and not Path(written[-1]).is_file():
                raise ComCallError("native_saveas_silent_failure",
                                   f"ChemDraw returned from SaveAs without creating {written[-1]}")
            if step["result_type"] == "IChemDrawDocument" and step["member"] in ("Add", "Open"):
                created.append(value)
        else:
            count = int(target.Count)
            shown = min(count, max_items)
            items = []
            for position in range(1, shown + 1):
                element = target.Item(position)
                entry: dict[str, Any] = {"index": position}
                for member_name in step.get("members", []):
                    declared = _catalog()["types"][step["element_type"]]["members"][member_name]
                    entry[member_name] = _plain(getattr(element, member_name), _type_of(declared.get("type")))
                items.append(entry)
            value = {"count": count, "items": items, "truncated": count > shown}
            results.append({"step": index, "op": operation, "value": value})
            continue
        alias = step.get("as")
        if alias is not None:
            objects[alias] = value
            types[alias] = step["result_type"]
        results.append({"step": index, "op": operation, "value": _plain(value, step["result_type"])})
    return {"results": results, "written": written}


@contextmanager
def _open_application() -> Iterator[tuple[Any, bool]]:
    """Start ChemDraw hidden; yield ``(application, owned)`` and quit it afterwards if it was ours."""
    from . import native_renderer

    with native_renderer._com_apartment():
        try:
            application, _ = native_renderer._acquire_application()
            owned = int(application.Documents.Count) == 0
            was_visible = bool(application.Visible)
            if owned:
                application.Visible = False
        except Exception as exc:
            text = str(exc)
            if "not licensed" in text.lower() or getattr(exc, "hresult", None) == -2147221230:
                raise ComCallError("chemdraw_license_unavailable",
                                   "ChemDraw COM reports that the installed product license is unavailable") from exc
            raise ComCallError("chemdraw_unavailable", f"ChemDraw could not be started through COM: {text}") from exc
        try:
            yield application, owned
        finally:
            try:
                if owned:
                    application.Quit()
                else:
                    application.Visible = was_visible
            except Exception as exc:
                # Only the exception type: COM messages can quote paths or document content.
                logger.warning("ChemDraw cleanup after a COM call failed (%s)", type(exc).__name__)
            application = None


def _windows() -> bool:
    return sys.platform == "win32"


def chemdraw_com_call(
    program: list[dict[str, Any]],
    allow_file_io: bool = False,
    allow_overwrite: bool = False,
    max_items: int = 100,
) -> dict[str, Any]:
    """Run a declarative program over ChemDraw's COM automation objects (Windows, ChemDraw installed).

    program is a list of steps; the root object is the alias "app" (ChemDraw.Application).
    Each step has op get, set, call, iterate or release, an optional target alias (default
    app), and for get/set/call the member; call takes args, set takes value, and as stores
    the result under a new alias. Arguments and values are strings, numbers, booleans, null,
    {"constant": "kCDFormatPNG"} (any constant of the ChemDraw type library) or
    {"ref": alias}. iterate walks a collection (Count and Item, counted from 1) and reads the
    listed members of each item: {"op": "iterate", "target": "atoms", "members": ["Charge"]}.
    Every member is checked against the committed COM catalog before ChemDraw starts, with
    the result types followed through the program (see the interface-com reference for the
    members). Printing, the clipboard, menus, preference changes and Quit are blocked.
    Opening, saving or exporting files needs allow_file_io; an existing file is never
    replaced unless allow_overwrite is also true (Document.Save and Close with saveChanges
    true need it too). Documents the program opens are closed without saving and ChemDraw
    is quit afterwards if the tool started it. Object results are reported as their type;
    max_items caps the items iterate reads.
    """
    if allow_overwrite and not allow_file_io:
        raise ValueError("allow_overwrite requires allow_file_io")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= MAX_ITERATION_ITEMS:
        raise ValueError(f"max_items must be an integer from 1 through {MAX_ITERATION_ITEMS}")
    steps = validate_program(program, allow_file_io=allow_file_io, allow_overwrite=allow_overwrite)
    if not _windows():
        raise ComCallError(
            "chemdraw_unavailable",
            "ChemDraw COM automation needs Windows with ChemDraw installed; on macOS use the "
            "ChemScript tools or render through ChemDraw for macOS")
    created: list[Any] = []
    closed = 0
    try:
        with _open_application() as (application, _owned):
            try:
                outcome = execute_program(
                    application, steps, max_items=max_items, allow_overwrite=allow_overwrite, created=created)
            finally:
                # Documents the program opened are closed unsaved, even when a step failed.
                for document in reversed(created):
                    try:
                        document.Close(False)
                    except Exception:
                        pass
                closed = len(created)
                # COM proxies must be gone before the apartment is torn down.
                created.clear()
                application = None
    except ComCallError:
        raise
    except (ValueError, FileNotFoundError, FileExistsError):
        raise
    except Exception as exc:
        raise ComCallError("chemdraw_com_failed", f"ChemDraw COM call failed: {exc}") from exc
    warnings = []
    if allow_file_io:
        warnings.append("ChemDraw file access was explicitly enabled for this program")
    if allow_overwrite:
        warnings.append("Replacing existing files was explicitly enabled for this program")
    outputs = {"results": outcome["results"], "written": outcome["written"]}
    payload = {
        "ok": True,
        "outputs": outputs,
        "warnings": warnings,
        "metadata": {"steps": len(steps), "network_used": False, "file_io_enabled": bool(allow_file_io),
                     "overwrite_enabled": bool(allow_overwrite), "documents_closed": closed},
    }
    artifacts = artifact_safety.artifact_records(outcome["written"])
    if artifacts:
        payload["metadata"]["artifacts"] = artifacts
    return payload


COM_TOOLS = {"chemdraw_com_call": chemdraw_com_call}
