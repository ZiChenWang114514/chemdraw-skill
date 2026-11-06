"""Non-destructive bridge to an already-open desktop ChemDraw window.

Unlike headless batch converters, this module attaches only to a running interactive
ChemDraw session and never hides the application window, closes user documents, or
terminates the application process.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterator

from . import artifact_safety


SUPPORTED_ACTIONS = ("status", "read_active", "read_selection", "insert_cdxml")
_LIVE_STAGE_DIR = Path(tempfile.gettempdir()) / "chemdraw-skill-live"


@contextmanager
def _com_context() -> Iterator[None]:
    try:
        import pythoncom
    except ImportError:
        yield
        return
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


def _get_active_com_application() -> Any | None:
    """Attach to an already-running ChemDraw COM instance without launching a new one."""
    if sys.platform != "win32" and "win32com" not in sys.modules and "win32com.client" not in sys.modules:
        return None
    try:
        import win32com.client as win32_client
    except ImportError:
        return None
    get_active = getattr(win32_client, "GetActiveObject", None)
    if get_active is None:
        return None
    try:
        return get_active("ChemDraw.Application")
    except Exception:
        return None


def _active_document(app: Any) -> Any | None:
    try:
        doc = getattr(app, "ActiveDocument", None)
        if doc is not None:
            return doc
    except Exception:
        pass
    try:
        docs = getattr(app, "Documents", None)
        if docs is not None and int(getattr(docs, "Count", 0) or 0) > 0:
            return docs.Item(1)
    except Exception:
        pass
    return None


def _document_name(doc: Any) -> str | None:
    if doc is None:
        return None
    for attr in ("Name", "name", "FullName"):
        try:
            val = getattr(doc, attr, None)
            if isinstance(val, str) and val.strip():
                return val.strip()
        except Exception:
            continue
    return "Untitled"


def _selection_objects(doc: Any) -> Any | None:
    if doc is None:
        return None
    try:
        sel = getattr(doc, "Selection", None)
        if sel is None:
            return None
        return getattr(sel, "Objects", None) or sel
    except Exception:
        return None


def _collection_count(objs: Any) -> int:
    if objs is None:
        return 0
    try:
        return int(getattr(objs, "Count", 0) or 0)
    except Exception:
        return 0


def _has_chemistry(objs: Any) -> bool:
    if objs is None:
        return False
    try:
        atoms = getattr(objs, "Atoms", None)
        if atoms is not None and int(getattr(atoms, "Count", 0) or 0) > 0:
            return True
    except Exception:
        pass
    try:
        formula = getattr(objs, "Formula", None)
        if isinstance(formula, str) and formula.strip():
            return True
    except Exception:
        pass
    return _collection_count(objs) > 0


def _extract_cdxml_from_objects(objs: Any) -> str:
    if objs is None:
        return ""
    data_attr = getattr(objs, "Data", None)
    if callable(data_attr):
        for fmt in ("text/xml", "chemical/x-cdxml", "cdxml"):
            try:
                raw = data_attr(fmt)
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8", errors="replace")
                if isinstance(raw, str) and "<CDXML" in raw:
                    return raw
            except Exception:
                continue
    elif isinstance(data_attr, (str, bytes, bytearray)):
        text = data_attr.decode("utf-8", errors="replace") if isinstance(data_attr, (bytes, bytearray)) else data_attr
        if "<CDXML" in text:
            return text
    try:
        data_obj = getattr(objs, "DataObject", None)
        if data_obj is not None and hasattr(data_obj, "GetData"):
            for fmt in ("text/xml", "chemical/x-cdxml", "cdxml"):
                try:
                    raw = data_obj.GetData(fmt)
                    if isinstance(raw, (bytes, bytearray)):
                        raw = raw.decode("utf-8", errors="replace")
                    if isinstance(raw, str) and "<CDXML" in raw:
                        return raw
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def _extract_smiles_from_objects(objs: Any, cdxml_text: str = "") -> str:
    if objs is not None:
        data_attr = getattr(objs, "Data", None)
        if callable(data_attr):
            for fmt in ("chemical/x-smiles", "smiles"):
                try:
                    raw = data_attr(fmt)
                    if isinstance(raw, (bytes, bytearray)):
                        raw = raw.decode("utf-8", errors="replace")
                    if isinstance(raw, str) and raw.strip() and "<CDXML" not in raw:
                        return raw.strip()
                except Exception:
                    continue
        for attr in ("SMILES", "smiles"):
            try:
                val = getattr(objs, attr, None)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            except Exception:
                continue
    if cdxml_text and "<CDXML" in cdxml_text:
        try:
            from rdkit import Chem

            mols = [m for m in (Chem.MolsFromCDXML(cdxml_text) or []) if m is not None and m.GetNumAtoms() > 0]
            smiles_parts = [Chem.MolToSmiles(m) for m in mols if Chem.MolToSmiles(m)]
            if smiles_parts:
                return ".".join(smiles_parts)
        except Exception:
            pass
    return ""


def _resolve_cdxml_input(cdxml: str, smiles: str) -> str:
    raw = (cdxml or "").strip()
    if raw:
        if "<CDXML" in raw or raw.startswith("<?xml"):
            return raw
        candidate = Path(raw).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"CDXML file not found: {candidate}")
        content = candidate.read_text(encoding="utf-8")
        if "<CDXML" not in content:
            raise ValueError(f"File does not contain valid CDXML: {candidate}")
        return content
    smi = (smiles or "").strip()
    if smi:
        from cdxml_toolkit.naming.mol_builder import draw_molecule as _draw_mol

        drawn = _draw_mol({"smiles": smi})
        if not isinstance(drawn, dict) or not drawn.get("ok") or not drawn.get("cdxml"):
            raise ValueError(f"Could not generate CDXML from SMILES: {smi!r}")
        return str(drawn["cdxml"])
    raise ValueError("insert_cdxml requires a non-empty cdxml (XML string or file path) or smiles")


def _publish_optional_cdxml(cdxml_text: str, output_path: str) -> tuple[str | None, list[dict[str, Any]]]:
    if not (output_path or "").strip():
        return None, []
    destination = artifact_safety.resolve_destination(
        source=None,
        output_path=output_path,
        tag="live-chemdraw",
        suffix=".cdxml",
        base_dir=_LIVE_STAGE_DIR,
    )
    with artifact_safety.staging_file(destination) as staged:
        staged.write_text(cdxml_text, encoding="utf-8")
        artifact_safety.validate_artifact(staged)
        artifact_safety.publish_file(staged, destination)
    return str(destination), artifact_safety.artifact_records([destination])


def _envelope(payload: dict[str, Any], *, artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    outputs = {k: v for k, v in payload.items() if k not in ("ok", "outputs", "warnings", "metadata", "artifacts")}
    metadata: dict[str, Any] = {"network_used": False}
    if artifacts:
        metadata["artifacts"] = artifacts
    return {
        **payload,
        "outputs": outputs,
        "warnings": payload.get("warnings", []),
        "artifacts": artifacts or [],
        "metadata": metadata,
    }


def _macos_session(action: str, *, cdxml: str, smiles: str, output_path: str) -> dict[str, Any]:
    from ..chemdraw import mac_automation

    bundle = mac_automation.find_application()
    if bundle is None:
        return _envelope({
            "ok": action == "status",
            "action": action,
            "active_window": False,
            "document_name": None,
            "selection_has_chemistry": False,
            "reason": "No open ChemDraw window found",
        })
    bundle_id = mac_automation.bundle_identifier(bundle)
    if not mac_automation.is_running(bundle_id):
        return _envelope({
            "ok": action == "status",
            "action": action,
            "active_window": False,
            "document_name": None,
            "selection_has_chemistry": False,
            "reason": "No open ChemDraw window found",
        })

    if action == "status":
        script = (
            f'tell application id "{bundle_id}"\n'
            '  if (count of documents) is 0 then return "0||"\n'
            '  set d to front document\n'
            '  set docName to name of d\n'
            '  set smi to ""\n'
            '  try\n'
            '    set smi to (SMILES of selection of d)\n'
            '  end try\n'
            '  return "1|" & docName & "|" & smi\n'
            'end tell'
        )
        try:
            reply = mac_automation.run_applescript(script, timeout_seconds=15)
        except Exception as exc:
            return _envelope({
                "ok": True,
                "action": action,
                "active_window": False,
                "document_name": None,
                "selection_has_chemistry": False,
                "reason": f"No open ChemDraw window found ({exc})",
            })
        parts = reply.split("|", 2)
        has_doc = parts[0] == "1"
        doc_name = parts[1] if len(parts) > 1 and parts[1] else None
        smi = parts[2].strip() if len(parts) > 2 else ""
        return _envelope({
            "ok": True,
            "action": action,
            "active_window": has_doc,
            "document_name": doc_name,
            "selection_has_chemistry": bool(smi),
            "smiles": smi or None,
            **(
                {}
                if has_doc
                else {"reason": "ChemDraw is running but has no open document"}
            ),
        })

    if action in ("read_active", "read_selection"):
        _LIVE_STAGE_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="live-read-", dir=_LIVE_STAGE_DIR) as tmp_dir:
            snapshot = Path(tmp_dir) / "snapshot.cdxml"
            script = (
                f'tell application id "{bundle_id}"\n'
                '  if (count of documents) is 0 then error "No open document" number 1001\n'
                '  set d to front document\n'
                '  set docName to name of d\n'
                '  set smi to ""\n'
                '  try\n'
                '    set smi to (SMILES of selection of d)\n'
                '  end try\n'
                f'  save d in (POSIX file "{snapshot.as_posix()}") as "ChemDraw XML"\n'
                '  return docName & "|" & smi\n'
                'end tell'
            )
            reply = mac_automation.run_applescript(script, timeout_seconds=30)
            doc_name, _, smi = reply.partition("|")
            cdxml_text = snapshot.read_text(encoding="utf-8") if snapshot.is_file() else ""
        if not smi and cdxml_text:
            smi = _extract_smiles_from_objects(None, cdxml_text)
        saved_path, artifacts = _publish_optional_cdxml(cdxml_text, output_path) if cdxml_text else (None, [])
        return _envelope(
            {
                "ok": bool(cdxml_text),
                "action": action,
                "active_window": True,
                "document_name": doc_name or "Untitled",
                "selection_has_chemistry": bool(smi),
                "cdxml": cdxml_text,
                "smiles": smi,
                "output_path": saved_path,
            },
            artifacts=artifacts,
        )

    # action == "insert_cdxml"
    cdxml_text = _resolve_cdxml_input(cdxml, smiles)
    saved_path, artifacts = _publish_optional_cdxml(cdxml_text, output_path)
    if saved_path:
        open_target = Path(saved_path)
    else:
        _LIVE_STAGE_DIR.mkdir(parents=True, exist_ok=True)
        open_target = artifact_safety._available_path(_LIVE_STAGE_DIR / "live-insert.cdxml")
        open_target.write_text(cdxml_text, encoding="utf-8")
    script = (
        f'tell application id "{bundle_id}"\n'
        f'  open (POSIX file "{open_target.as_posix()}")\n'
        '  activate\n'
        '  return name of front document\n'
        'end tell'
    )
    doc_name = mac_automation.run_applescript(script, timeout_seconds=30)
    return _envelope(
        {
            "ok": True,
            "action": action,
            "active_window": True,
            "document_name": doc_name or open_target.name,
            "cdxml": cdxml_text,
            "smiles": _extract_smiles_from_objects(None, cdxml_text),
            "output_path": saved_path or str(open_target),
        },
        artifacts=artifacts,
    )


def live_chemdraw_session(
    action: str = "status",
    *,
    cdxml: str = "",
    smiles: str = "",
    output_path: str = "",
) -> dict[str, Any]:
    """Interact non-destructively with an already-open user-facing desktop ChemDraw window.

    Connects to a running ChemDraw instance (GetActiveObject on Windows COM or AppleScript on
    macOS) without hiding the window, closing user documents, or exiting the application.

    Args:
        action: One of:
            - "status": Check if ChemDraw is open with an active document and whether the
              current selection (or active canvas) contains chemical structures.
            - "read_active": Read the active document (or selection if active) as CDXML and
              SMILES without modifying the open document, optionally saving a copy to output_path.
            - "read_selection": Read the currently selected objects (falling back to the active
              document if nothing is selected) as CDXML and SMILES.
            - "insert_cdxml": Load cdxml (a CDXML string or file path) or smiles into the user's
              active open ChemDraw window (or open a new visible document tab if none is open).
        cdxml: CDXML string or path to a .cdxml file for action="insert_cdxml".
        smiles: Optional SMILES string to render and insert when cdxml is not provided.
        output_path: Optional file path to save a copy of the read or inserted CDXML.
    """
    normalized_action = (action or "status").strip().lower()
    if normalized_action not in SUPPORTED_ACTIONS:
        raise ValueError(
            f"Unsupported action {action!r}; choose one of: {', '.join(SUPPORTED_ACTIONS)}"
        )

    with _com_context():
        app = _get_active_com_application()
        if app is None and sys.platform == "darwin":
            return _macos_session(
                normalized_action, cdxml=cdxml, smiles=smiles, output_path=output_path
            )
        if app is None:
            return _envelope({
                "ok": normalized_action == "status",
                "action": normalized_action,
                "active_window": False,
                "document_name": None,
                "selection_has_chemistry": False,
                "reason": "No open ChemDraw window found",
                **(
                    {}
                    if normalized_action == "status"
                    else {"error": "No open ChemDraw window found"}
                ),
            })

        doc = _active_document(app)
        if normalized_action == "status":
            if doc is None:
                return _envelope({
                    "ok": True,
                    "action": "status",
                    "active_window": False,
                    "document_name": None,
                    "selection_has_chemistry": False,
                    "reason": "ChemDraw is running but has no open document",
                })
            sel_objs = _selection_objects(doc)
            sel_count = _collection_count(sel_objs)
            doc_objs = getattr(doc, "Objects", None)
            has_chem = _has_chemistry(sel_objs) if sel_count > 0 else _has_chemistry(doc_objs)
            return _envelope({
                "ok": True,
                "action": "status",
                "active_window": True,
                "document_name": _document_name(doc),
                "selection_count": sel_count,
                "selection_has_chemistry": bool(has_chem),
            })

        if normalized_action in ("read_active", "read_selection"):
            if doc is None:
                return _envelope({
                    "ok": False,
                    "action": normalized_action,
                    "active_window": False,
                    "document_name": None,
                    "selection_has_chemistry": False,
                    "reason": "No open ChemDraw document found",
                    "error": "No open ChemDraw document found",
                })
            sel_objs = _selection_objects(doc)
            sel_count = _collection_count(sel_objs)
            doc_objs = getattr(doc, "Objects", None)
            if normalized_action == "read_selection" and sel_count > 0:
                target_objs = sel_objs
                scope = "selection"
            elif sel_count > 0:
                target_objs = sel_objs
                scope = "selection"
            else:
                target_objs = doc_objs
                scope = "document"

            cdxml_text = _extract_cdxml_from_objects(target_objs)
            if not cdxml_text and target_objs is not doc_objs and doc_objs is not None:
                cdxml_text = _extract_cdxml_from_objects(doc_objs)
                if cdxml_text:
                    scope = "document"
            smiles_text = _extract_smiles_from_objects(target_objs, cdxml_text)
            if not smiles_text and doc_objs is not None:
                smiles_text = _extract_smiles_from_objects(doc_objs, cdxml_text)
            saved_path, artifacts = (
                _publish_optional_cdxml(cdxml_text, output_path) if cdxml_text else (None, [])
            )
            return _envelope(
                {
                    "ok": True,
                    "action": normalized_action,
                    "active_window": True,
                    "document_name": _document_name(doc),
                    "scope": scope,
                    "selection_has_chemistry": bool(smiles_text or _has_chemistry(target_objs)),
                    "cdxml": cdxml_text,
                    "smiles": smiles_text,
                    "output_path": saved_path,
                },
                artifacts=artifacts,
            )

        # normalized_action == "insert_cdxml"
        cdxml_text = _resolve_cdxml_input(cdxml, smiles)
        saved_path, artifacts = _publish_optional_cdxml(cdxml_text, output_path)
        inserted = False
        if doc is not None:
            for holder in (getattr(doc, "Objects", None), _selection_objects(doc), getattr(doc, "DataObject", None)):
                if holder is None:
                    continue
                set_data = getattr(holder, "SetData", None)
                if callable(set_data):
                    try:
                        set_data("text/xml", cdxml_text)
                        inserted = True
                        break
                    except Exception:
                        try:
                            set_data(cdxml_text, "text/xml")
                            inserted = True
                            break
                        except Exception:
                            pass
            if not inserted and hasattr(doc, "Objects"):
                try:
                    setattr(doc.Objects, "Data", cdxml_text)
                    inserted = True
                except Exception:
                    pass

        if not inserted:
            docs = getattr(app, "Documents", None)
            if docs is not None and hasattr(docs, "Add"):
                try:
                    new_doc = docs.Add()
                    if new_doc is not None:
                        doc = new_doc
                        objs = getattr(doc, "Objects", None)
                        if objs is not None and callable(getattr(objs, "SetData", None)):
                            objs.SetData("text/xml", cdxml_text)
                            inserted = True
                        elif objs is not None:
                            setattr(objs, "Data", cdxml_text)
                            inserted = True
                except Exception:
                    pass
            if not inserted and docs is not None and hasattr(docs, "Open"):
                if saved_path:
                    open_file = Path(saved_path)
                else:
                    _LIVE_STAGE_DIR.mkdir(parents=True, exist_ok=True)
                    open_file = artifact_safety._available_path(_LIVE_STAGE_DIR / "live-insert.cdxml")
                    open_file.write_text(cdxml_text, encoding="utf-8")
                doc = docs.Open(str(open_file))
                inserted = doc is not None

        if doc is not None and hasattr(doc, "Activate"):
            try:
                doc.Activate()
            except Exception:
                pass

        return _envelope(
            {
                "ok": bool(inserted or doc is not None),
                "action": "insert_cdxml",
                "active_window": True,
                "document_name": _document_name(doc),
                "inserted": bool(inserted or doc is not None),
                "cdxml": cdxml_text,
                "smiles": _extract_smiles_from_objects(getattr(doc, "Objects", None), cdxml_text),
                "output_path": saved_path,
            },
            artifacts=artifacts,
        )


LIVE_CHEMDRAW_TOOLS = {"live_chemdraw_session": live_chemdraw_session}
