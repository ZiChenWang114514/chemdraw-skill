"""Reflection catalog and controlled ChemScript SDK program runtime."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


MAX_PROGRAM_STEPS = 256
MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_ITERATION_ITEMS = 1000
SUPPORTED_OPERATIONS = {
    "construct",
    "call_static",
    "call",
    "get",
    "set",
    "get_index",
    "set_index",
    "iterate",
    "dispose",
    "release",
}
_ALIAS = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
_FILE_MEMBERS = re.compile(r"(?:Load|Read|Write|Open|Save|Append)File\Z", re.IGNORECASE)
_INTEROP_MEMBER = re.compile(
    r"(?:getCPtr|swigRelease|swigCMemOwn|HandleRef|IntPtr|new_|delete_)",
    re.IGNORECASE,
)
_INTEROP_TYPE_PARTS = (
    "System.Runtime.InteropServices.HandleRef",
    "System.IntPtr",
    "SWIGTYPE_",
    ".ChemScriptPINVOKE",
    ".ChemScriptBase",
    ".CppWrapper",
    "SWIGPendingException",
)


def _is_file_member(name: Any) -> bool:
    return isinstance(name, str) and bool(_FILE_MEMBERS.search(name))


def _is_file_type(name: Any) -> bool:
    return isinstance(name, str) and str(name).rsplit(".", 1)[-1].endswith(
        ("FileReader", "FileWriter")
    )


def _is_interop_name(type_name: str = "", member: str = "") -> bool:
    return any(part in type_name for part in _INTEROP_TYPE_PARTS) or bool(
        _INTEROP_MEMBER.search(member)
    )


def validate_program(
    program: list[dict[str, Any]],
    *,
    allow_file_io: bool = True,
    allow_unsafe_interop: bool = False,
) -> list[dict[str, Any]]:
    """Validate the declarative SDK program without loading Python.NET."""
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

    aliases: set[str] = set()
    normalized = []
    for index, original in enumerate(program):
        if not isinstance(original, dict):
            raise ValueError(f"program step {index} must be an object")
        step = dict(original)
        operation = step.get("op")
        if operation not in SUPPORTED_OPERATIONS:
            raise ValueError(f"program step {index} uses an unsupported operation")
        if operation in {"construct", "call_static"}:
            if not isinstance(step.get("type"), str) or not step["type"].strip():
                raise ValueError(f"program step {index} requires type")
        if operation in {"call", "get", "set", "get_index", "set_index", "iterate", "dispose", "release"}:
            if not isinstance(step.get("target"), str) or not _ALIAS.fullmatch(step["target"]):
                raise ValueError(f"program step {index} requires a valid target alias")
        if operation in {"call", "call_static", "get", "set"}:
            if not isinstance(step.get("member"), str) or not step["member"].strip():
                raise ValueError(f"program step {index} requires member")
        if operation in {"construct", "call", "call_static"}:
            arguments = step.get("args", [])
            if not isinstance(arguments, list):
                raise ValueError(f"program step {index} args must be a list")
            step["args"] = arguments
        if operation == "set" and "value" not in step:
            raise ValueError(f"program step {index} requires value")
        if operation in {"get_index", "set_index"} and "index" not in step:
            raise ValueError(f"program step {index} requires index")
        if operation == "set_index" and "value" not in step:
            raise ValueError(f"program step {index} requires value")
        alias = step.get("as")
        if alias is not None:
            if not isinstance(alias, str) or not _ALIAS.fullmatch(alias):
                raise ValueError(f"program step {index} has an invalid result alias")
            if alias in aliases:
                raise ValueError(f"program step {index} reuses result alias {alias}")
            aliases.add(alias)
        if (
            _is_file_member(step.get("member"))
            or (operation == "construct" and _is_file_type(step.get("type")))
        ) and not allow_file_io:
            raise ValueError(f"program step {index} requests file I/O without allow_file_io")
        if _is_interop_name(step.get("type", ""), step.get("member", "")) and not allow_unsafe_interop:
            raise ValueError(f"program step {index} requests unsafe interop without allow_unsafe_interop")
        normalized.append(step)
    return normalized


def _load_configuration() -> dict[str, Any]:
    config_path = Path(
        os.environ.get("CHEMSCRIPT_CONFIG_PATH") or (Path.home() / ".chemscript_config.json")
    ).expanduser()
    config: dict[str, Any] = {}
    if config_path.is_file():
        try:
            decoded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(decoded, dict):
                config.update(decoded)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("ChemScript configuration is not valid JSON") from exc
    if os.environ.get("CHEMSCRIPT_DLL_DIR"):
        config["dll_dir"] = os.environ["CHEMSCRIPT_DLL_DIR"]
    if os.environ.get("CHEMSCRIPT_ASSEMBLY"):
        config["assembly"] = os.environ["CHEMSCRIPT_ASSEMBLY"]
    return config


class ChemScriptRuntime:
    """One direct Python.NET session for cataloging and executing an SDK program."""

    def __init__(self):
        config = _load_configuration()
        dll_dir = Path(str(config.get("dll_dir") or "")).expanduser()
        assembly_name = str(config.get("assembly") or "CambridgeSoft.ChemScript")
        if not dll_dir.is_dir():
            raise RuntimeError("ChemScript DLL directory is not configured or does not exist")
        assembly_file = dll_dir / f"{assembly_name}.dll"
        if not assembly_file.is_file():
            raise RuntimeError("Configured ChemScript managed assembly does not exist")

        dll_parent = dll_dir.parent
        os.environ["PATH"] = os.pathsep.join(
            [str(dll_dir), str(dll_parent), os.environ.get("PATH", "")]
        )
        sys.path.insert(0, str(dll_dir))
        if hasattr(os, "add_dll_directory"):
            self._dll_handle = os.add_dll_directory(str(dll_dir))
        else:
            self._dll_handle = None

        from pythonnet import load

        load("netfx")
        import clr

        clr.AddReference(assembly_name)
        from System.Reflection import Assembly, BindingFlags

        self.BindingFlags = BindingFlags
        self.assembly = Assembly.LoadFrom(str(assembly_file.resolve()))
        self.module = __import__(assembly_name, fromlist=["StructureData"])
        self.types = {item.FullName: item for item in self.assembly.GetExportedTypes()}
        self.short_types: dict[str, list[Any]] = {}
        for item in self.types.values():
            self.short_types.setdefault(item.Name, []).append(item)
        self.namespace = assembly_name

    def reflection_type(self, name: str):
        candidate = str(name).strip()
        if candidate in self.types:
            return self.types[candidate]
        qualified = f"{self.namespace}.{candidate}"
        if qualified in self.types:
            return self.types[qualified]
        matches = self.short_types.get(candidate, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"ChemScript type name is ambiguous: {candidate}")
        raise ValueError(f"Unknown public ChemScript type: {candidate}")

    def python_type(self, name: str):
        reflection_type = self.reflection_type(name)
        relative = reflection_type.FullName
        prefix = self.namespace + "."
        if relative.startswith(prefix):
            relative = relative[len(prefix) :]
        parts = relative.split("+")
        value = getattr(self.module, parts[0])
        for part in parts[1:]:
            value = getattr(value, part)
        return value

    def system_python_type(self, name: str):
        import System

        candidate = str(name).strip()
        if candidate.startswith("System."):
            value: Any = System
            for part in candidate.split(".")[1:]:
                value = getattr(value, part)
            return value
        return self.python_type(candidate)

    def resolve_argument(self, value: Any, aliases: dict[str, Any], *, unsafe: bool):
        if isinstance(value, list):
            return [self.resolve_argument(item, aliases, unsafe=unsafe) for item in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"$ref"}:
            alias = value["$ref"]
            if alias not in aliases:
                raise ValueError(f"Unknown object alias: {alias}")
            return aliases[alias]
        if set(value) == {"$bytes_base64"}:
            try:
                return base64.b64decode(value["$bytes_base64"], validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid base64 byte argument") from exc
        if set(value) == {"$enum"}:
            spec = value["$enum"]
            if not isinstance(spec, dict) or not isinstance(spec.get("type"), str):
                raise ValueError("Enum arguments require type and name or value")
            enum_type = self.python_type(spec["type"])
            if isinstance(spec.get("name"), str):
                return getattr(enum_type, spec["name"])
            if "value" in spec:
                return enum_type(int(spec["value"]))
            raise ValueError("Enum arguments require name or value")
        if set(value) == {"$array"}:
            spec = value["$array"]
            if not isinstance(spec, dict) or not isinstance(spec.get("items"), list):
                raise ValueError("Array arguments require type and items")
            import System

            element_type = self.system_python_type(spec["type"])
            items = [
                self.resolve_argument(item, aliases, unsafe=unsafe)
                for item in spec["items"]
            ]
            return System.Array[element_type](items)
        if set(value) == {"$default"}:
            import System

            type_name = value["$default"]
            if type_name == "System.String":
                return None
            return System.Activator.CreateInstance(self.reflection_type(type_name))
        if set(value) == {"$intptr"}:
            if not unsafe:
                raise ValueError("IntPtr arguments require allow_unsafe_interop")
            import System

            return System.IntPtr(int(value["$intptr"]))
        if set(value) == {"$handleref"}:
            if not unsafe:
                raise ValueError("HandleRef arguments require allow_unsafe_interop")
            import System

            spec = value["$handleref"]
            wrapper = self.resolve_argument(spec.get("wrapper"), aliases, unsafe=unsafe)
            return System.Runtime.InteropServices.HandleRef(
                wrapper, System.IntPtr(int(spec["handle"]))
            )
        return {
            key: self.resolve_argument(item, aliases, unsafe=unsafe)
            for key, item in value.items()
        }

    def member_is_interop(self, reflection_type, member: str) -> bool:
        flags = (
            self.BindingFlags.Public
            | self.BindingFlags.Instance
            | self.BindingFlags.Static
            | self.BindingFlags.DeclaredOnly
        )
        candidates = [
            method
            for method in reflection_type.GetMethods(flags)
            if method.Name == member and not method.IsSpecialName
        ]
        if not candidates:
            return _is_interop_name(reflection_type.FullName, member)
        return all(_member_interop_reason(reflection_type.FullName, method) for method in candidates)


def _type_name(value: Any) -> str:
    if value is None:
        return "System.Void"
    return str(getattr(value, "FullName", None) or value)


def _parameter(parameter) -> dict[str, Any]:
    parameter_type = parameter.ParameterType
    return {
        "name": parameter.Name,
        "type": _type_name(parameter_type),
        "by_ref": bool(parameter_type.IsByRef),
        "optional": bool(parameter.IsOptional),
    }


def _member_interop_reason(type_name: str, member) -> str | None:
    member_name = str(getattr(member, "Name", ""))
    names = [type_name, member_name]
    return_type = getattr(member, "ReturnType", None)
    if return_type is not None:
        names.append(_type_name(return_type))
    get_parameters = getattr(member, "GetParameters", None)
    if callable(get_parameters):
        names.extend(_type_name(item.ParameterType) for item in get_parameters())
    if any(_is_interop_name(name, member_name) for name in names):
        return "Native SWIG pointer or handle plumbing"
    return None


def _catalog(runtime: ChemScriptRuntime) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flags = (
        runtime.BindingFlags.Public
        | runtime.BindingFlags.Instance
        | runtime.BindingFlags.Static
        | runtime.BindingFlags.DeclaredOnly
    )
    type_records = []
    members = []
    for sdk_type in sorted(runtime.types.values(), key=lambda item: item.FullName):
        type_records.append(
            {
                "name": sdk_type.FullName,
                "kind": "enum" if sdk_type.IsEnum else ("value_type" if sdk_type.IsValueType else "class"),
            }
        )
        for constructor in sdk_type.GetConstructors(flags):
            reason = _member_interop_reason(sdk_type.FullName, constructor)
            members.append(
                {
                    "type": sdk_type.FullName,
                    "kind": "constructor",
                    "name": ".ctor",
                    "signature": constructor.ToString(),
                    "parameters": [_parameter(item) for item in constructor.GetParameters()],
                    "static": False,
                    "classification": "interop_infrastructure" if reason else "sdk_api",
                    "execution_op": "construct" if not reason else "construct_with_allow_unsafe_interop",
                    "reason": reason,
                }
            )
        for method in sdk_type.GetMethods(flags):
            if method.IsSpecialName:
                continue
            reason = _member_interop_reason(sdk_type.FullName, method)
            members.append(
                {
                    "type": sdk_type.FullName,
                    "kind": "method",
                    "name": method.Name,
                    "signature": method.ToString(),
                    "parameters": [_parameter(item) for item in method.GetParameters()],
                    "return_type": _type_name(method.ReturnType),
                    "static": bool(method.IsStatic),
                    "classification": "interop_infrastructure" if reason else "sdk_api",
                    "execution_op": (
                        "call_static" if method.IsStatic else "call"
                    ) if not reason else "call_with_allow_unsafe_interop",
                    "reason": reason,
                }
            )
        for prop in sdk_type.GetProperties(flags):
            accessor = prop.GetMethod or prop.SetMethod
            reason = _member_interop_reason(sdk_type.FullName, accessor) if accessor else None
            operations = []
            if prop.CanRead:
                operations.append("get")
            if prop.CanWrite:
                operations.append("set")
            members.append(
                {
                    "type": sdk_type.FullName,
                    "kind": "property",
                    "name": prop.Name,
                    "signature": f"{_type_name(prop.PropertyType)} {prop.Name}",
                    "property_type": _type_name(prop.PropertyType),
                    "static": bool(accessor and accessor.IsStatic),
                    "readable": bool(prop.CanRead),
                    "writable": bool(prop.CanWrite),
                    "classification": "interop_infrastructure" if reason else "sdk_api",
                    "execution_op": operations if not reason else ["get/set with allow_unsafe_interop"],
                    "reason": reason,
                }
            )
        for field in sdk_type.GetFields(flags):
            reason = (
                "Native SWIG pointer or handle plumbing"
                if _is_interop_name(sdk_type.FullName, field.Name)
                or _is_interop_name(_type_name(field.FieldType), field.Name)
                else None
            )
            members.append(
                {
                    "type": sdk_type.FullName,
                    "kind": "field",
                    "name": field.Name,
                    "signature": f"{_type_name(field.FieldType)} {field.Name}",
                    "field_type": _type_name(field.FieldType),
                    "static": bool(field.IsStatic),
                    "readable": True,
                    "writable": not bool(field.IsInitOnly or field.IsLiteral),
                    "classification": "interop_infrastructure" if reason else "sdk_api",
                    "execution_op": ["get", "set"] if not reason else ["get/set with allow_unsafe_interop"],
                    "reason": reason,
                }
            )
        for event in sdk_type.GetEvents(flags):
            members.append(
                {
                    "type": sdk_type.FullName,
                    "kind": "event",
                    "name": event.Name,
                    "signature": f"{_type_name(event.EventHandlerType)} {event.Name}",
                    "classification": "interop_infrastructure",
                    "execution_op": None,
                    "reason": "Event callbacks are process-local interop infrastructure",
                }
            )
    return type_records, members


def catalog_sdk(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]:
    types, members = _catalog(runtime)
    eligible = [item for item in members if item["classification"] == "sdk_api"]
    infrastructure = len(members) - len(eligible)
    coverage = {
        "public_types_discovered": len(types),
        "public_types_catalogued": len(types),
        "public_members_discovered": len(members),
        "public_members_catalogued": len(members),
        "catalog_percent": 100.0,
        "eligible_members": len(eligible),
        "eligible_members_with_execution_path": sum(bool(item["execution_op"]) for item in eligible),
        "execution_path_percent": round(
            100.0 * sum(bool(item["execution_op"]) for item in eligible) / max(1, len(eligible)), 3
        ),
        "interop_infrastructure_members": infrastructure,
    }
    query = str(request.get("query") or "").strip().casefold()
    type_name = str(request.get("type_name") or "").strip().casefold()
    include_infrastructure = bool(request.get("include_infrastructure", False))
    filtered = []
    for item in members:
        if not include_infrastructure and item["classification"] == "interop_infrastructure":
            continue
        if type_name and type_name not in item["type"].casefold():
            continue
        searchable = " ".join(
            str(item.get(key) or "") for key in ("type", "kind", "name", "signature")
        ).casefold()
        if query and query not in searchable:
            continue
        filtered.append(item)
    offset = request.get("offset", 0)
    limit = request.get("limit", 100)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 500:
        raise ValueError("limit must be an integer from 0 through 500")
    page = filtered[offset:] if limit == 0 else filtered[offset : offset + limit]
    return {
        "ok": True,
        "assembly": runtime.assembly.FullName,
        "coverage": coverage,
        "types": types,
        "members": page,
        "page": {
            "offset": offset,
            "limit": limit,
            "returned": len(page),
            "matched": len(filtered),
        },
    }


def _dotnet_type_name(value: Any) -> str:
    try:
        return str(value.GetType().FullName)
    except Exception:
        return f"{type(value).__module__}.{type(value).__name__}"


def _serialize(value: Any, *, alias: str | None = None, max_items: int = 100, depth: int = 0):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes_base64": base64.b64encode(bytes(value)).decode("ascii")}
    value_type = None
    try:
        value_type = value.GetType()
        if value_type.IsEnum:
            return {
                "$enum": {
                    "type": str(value_type.FullName),
                    "name": str(value),
                    "value": int(value),
                }
            }
    except Exception:
        value_type = None
    if alias is not None and value_type is not None:
        return {"$ref": alias, "$type": str(value_type.FullName)}
    if depth < 3 and isinstance(value, (list, tuple)):
        return [
            _serialize(item, max_items=max_items, depth=depth + 1)
            for item in value[:max_items]
        ]
    if depth < 3 and value_type is not None:
        interfaces = {str(item.FullName) for item in value_type.GetInterfaces()}
        if "System.Collections.IDictionary" in interfaces:
            result = []
            for index, key in enumerate(value.Keys):
                if index >= max_items:
                    break
                result.append(
                    {
                        "key": _serialize(key, max_items=max_items, depth=depth + 1),
                        "value": _serialize(value[key], max_items=max_items, depth=depth + 1),
                    }
                )
            return result
        if "System.Collections.IEnumerable" in interfaces:
            result = []
            for index, item in enumerate(value):
                if index >= max_items:
                    break
                result.append(_serialize(item, max_items=max_items, depth=depth + 1))
            return result
    return {"$type": _dotnet_type_name(value), "display": str(value)[:500]}


def _check_file_call(member: str, args: list[Any], *, allow_overwrite: bool) -> None:
    if not _is_file_member(member) or not args or not isinstance(args[0], str):
        return
    path = Path(args[0]).expanduser()
    if re.match(r"(?:Write|Save|Append)File\Z", member, re.IGNORECASE):
        if path.exists() and not allow_overwrite:
            raise ValueError("ChemScript file output already exists; set allow_overwrite to replace it")


def _check_file_constructor(type_name: str, args: list[Any], *, allow_overwrite: bool) -> None:
    if not _is_file_type(type_name) or not args or not isinstance(args[0], str):
        return
    if str(type_name).rsplit(".", 1)[-1].endswith("FileWriter"):
        path = Path(args[0]).expanduser()
        if path.exists() and not allow_overwrite:
            raise ValueError("ChemScript file output already exists; set allow_overwrite to replace it")


def execute_program(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]:
    allow_file_io = bool(request.get("allow_file_io", False))
    allow_overwrite = bool(request.get("allow_overwrite", False))
    allow_unsafe = bool(request.get("allow_unsafe_interop", False))
    max_items = request.get("max_items", 100)
    if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= MAX_ITERATION_ITEMS:
        raise ValueError(f"max_items must be an integer from 1 through {MAX_ITERATION_ITEMS}")
    program = validate_program(
        request.get("program"),
        allow_file_io=allow_file_io,
        allow_unsafe_interop=allow_unsafe,
    )
    aliases: dict[str, Any] = {}
    disposed: set[int] = set()
    results = []
    try:
        for index, step in enumerate(program):
            operation = step["op"]
            alias = step.get("as")
            value: Any = None
            if operation == "construct":
                reflection_type = runtime.reflection_type(step["type"])
                if _is_interop_name(reflection_type.FullName) and not allow_unsafe:
                    raise ValueError("The requested constructor is native interop infrastructure")
                args = [runtime.resolve_argument(item, aliases, unsafe=allow_unsafe) for item in step["args"]]
                _check_file_constructor(
                    step["type"], args, allow_overwrite=allow_overwrite
                )
                value = runtime.python_type(step["type"])(*args)
            elif operation == "call_static":
                reflection_type = runtime.reflection_type(step["type"])
                if runtime.member_is_interop(reflection_type, step["member"]) and not allow_unsafe:
                    raise ValueError("The requested member is native interop infrastructure")
                args = [runtime.resolve_argument(item, aliases, unsafe=allow_unsafe) for item in step["args"]]
                _check_file_call(step["member"], args, allow_overwrite=allow_overwrite)
                value = getattr(runtime.python_type(step["type"]), step["member"])(*args)
            elif operation == "call":
                target = aliases[step["target"]]
                reflection_type = target.GetType()
                if runtime.member_is_interop(reflection_type, step["member"]) and not allow_unsafe:
                    raise ValueError("The requested member is native interop infrastructure")
                args = [runtime.resolve_argument(item, aliases, unsafe=allow_unsafe) for item in step["args"]]
                _check_file_call(step["member"], args, allow_overwrite=allow_overwrite)
                value = getattr(target, step["member"])(*args)
            elif operation == "get":
                value = getattr(aliases[step["target"]], step["member"])
            elif operation == "set":
                target = aliases[step["target"]]
                resolved = runtime.resolve_argument(step["value"], aliases, unsafe=allow_unsafe)
                setattr(target, step["member"], resolved)
                value = resolved
            elif operation == "get_index":
                target = aliases[step["target"]]
                index_value = runtime.resolve_argument(step["index"], aliases, unsafe=allow_unsafe)
                value = target[tuple(index_value) if isinstance(index_value, list) else index_value]
            elif operation == "set_index":
                target = aliases[step["target"]]
                index_value = runtime.resolve_argument(step["index"], aliases, unsafe=allow_unsafe)
                resolved = runtime.resolve_argument(step["value"], aliases, unsafe=allow_unsafe)
                target[tuple(index_value) if isinstance(index_value, list) else index_value] = resolved
                value = resolved
            elif operation == "iterate":
                target = aliases[step["target"]]
                value = []
                for item_index, item in enumerate(target):
                    if item_index >= max_items:
                        break
                    value.append(item)
            elif operation == "dispose":
                target = aliases[step["target"]]
                if hasattr(target, "Dispose"):
                    target.Dispose()
                    disposed.add(id(target))
                value = True
            elif operation == "release":
                value = aliases.pop(step["target"])
            if alias is not None:
                aliases[alias] = value
            results.append(
                {
                    "step": index,
                    "op": operation,
                    "value": _serialize(value, alias=alias, max_items=max_items),
                }
            )
    finally:
        disposed_count = len(disposed)
        for value in reversed(list(aliases.values())):
            if id(value) in disposed or not hasattr(value, "Dispose"):
                continue
            try:
                value.Dispose()
                disposed.add(id(value))
                disposed_count += 1
            except Exception:
                pass
    return {
        "ok": True,
        "assembly": runtime.assembly.FullName,
        "results": results,
        "disposed": disposed_count,
    }


def _read_request(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("ChemScript SDK request exceeds the configured limit")
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("ChemScript SDK request must be an object")
    return request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--response-file", type=Path)
    args = parser.parse_args()
    try:
        request = _read_request(args.request_file)
        runtime = ChemScriptRuntime()
        action = request.get("action")
        if action == "catalog":
            response = catalog_sdk(runtime, request)
        elif action == "execute":
            response = execute_program(runtime, request)
        else:
            raise ValueError("Unknown ChemScript SDK action")
        return_code = 0
    except ValueError as exc:
        response = {
            "ok": False,
            "error": {"code": "invalid_sdk_request", "message": str(exc)[:1000]},
        }
        return_code = 2
    except Exception:
        response = {
            "ok": False,
            "error": {
                "code": "chemscript_sdk_failed",
                "message": "ChemScript SDK execution failed in the isolated runtime",
            },
        }
        return_code = 1
    encoded = json.dumps(response, separators=(",", ":"), default=str)
    if args.response_file:
        args.response_file.write_text(encoded, encoding="utf-8")
    else:
        print(encoded)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
