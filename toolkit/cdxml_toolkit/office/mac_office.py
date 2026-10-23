"""Word and PowerPoint for macOS automation (AppleScript).

The macOS counterpart of the Office COM calls in ``office_objects``: export a
.docx or .pptx to PDF. Word and PowerPoint for macOS are sandboxed, so the
document is staged in the shared Office group container, which both
applications may read and write without a "Grant File Access" prompt.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from cdxml_toolkit.chemdraw import mac_automation

BUNDLE_IDS = {
    ".docx": "com.microsoft.Word",
    ".pptx": "com.microsoft.Powerpoint",
}
OFFICE_GROUP_CONTAINER = Path("~/Library/Group Containers/UBF8T346G9.Office").expanduser()
PDF_TIMEOUT_SECONDS = 120
DOCUMENT_OPEN_SECONDS = 60

# Both scripts wait for the document by name (``open`` returns before the
# document exists), export it, close it, and quit when asked (argument 4 is
# "quit" when this module launched the application).
_WAIT_FOR = '''
		set doc to missing value
		repeat {attempts} times
			try
				set doc to {collection} docName
				get name of doc
				exit repeat
			on error
				set doc to missing value
			end try
			delay 0.1
		end repeat
		if doc is missing value then error "Office did not open the document" number 1001
'''

_WORD_SCRIPT = '''on run argv
	set src to item 1 of argv
	set dst to item 2 of argv
	set docName to item 3 of argv
	set srcFile to POSIX file src
	tell application id "com.microsoft.Word"
		open srcFile
''' + _WAIT_FOR.format(attempts=DOCUMENT_OPEN_SECONDS * 10, collection="document") + '''
		save as doc file name dst file format format PDF
		close doc saving no
		if item 4 of argv is "quit" then quit saving no
	end tell
end run
'''

_POWERPOINT_SCRIPT = '''on run argv
	set src to item 1 of argv
	set dst to item 2 of argv
	set docName to item 3 of argv
	set srcFile to POSIX file src
	set dstFile to POSIX file dst
	tell application id "com.microsoft.Powerpoint"
		open srcFile
''' + _WAIT_FOR.format(attempts=DOCUMENT_OPEN_SECONDS * 10, collection="presentation") + '''
		save doc in dstFile as save as PDF
		close doc
		if item 4 of argv is "quit" then quit
	end tell
end run
'''

_SCRIPTS = {".docx": _WORD_SCRIPT, ".pptx": _POWERPOINT_SCRIPT}


class OfficeAutomationError(RuntimeError):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


def application_path(suffix: str) -> Path | None:
    """The installed Word (.docx) or PowerPoint (.pptx) for macOS, if any."""
    name = {".docx": "Microsoft Word.app", ".pptx": "Microsoft PowerPoint.app"}[suffix]
    for root in (Path("/Applications"), Path("~/Applications").expanduser()):
        if (root / name).is_dir():
            return root / name
    return None


def export_pdf(
    source: str | Path, destination: str | Path, *, timeout_seconds: float = PDF_TIMEOUT_SECONDS
) -> Path:
    """Export a .docx (Word) or .pptx (PowerPoint) to PDF with Office for macOS."""
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()
    suffix = source_path.suffix.lower()
    if suffix not in _SCRIPTS:
        raise ValueError(f"Office PDF export supports .docx and .pptx, not {suffix or source_path.name}")
    bundle_id = BUNDLE_IDS[suffix]
    owner = "Word" if suffix == ".docx" else "PowerPoint"
    if not OFFICE_GROUP_CONTAINER.is_dir():
        raise OfficeAutomationError(
            "office_not_installed", f"Microsoft {owner} for macOS has never been started on this Mac"
        )

    staging = OFFICE_GROUP_CONTAINER / "chemdraw-skill" / uuid.uuid4().hex
    staging.mkdir(parents=True)
    launched_pid = None
    try:
        staged_source = staging / f"document{suffix}"
        staged_pdf = staging / "document.pdf"
        shutil.copyfile(source_path, staged_source)
        try:
            mac_automation.reap_orphans()
            launched = mac_automation.application_pid(bundle_id) is None
            if launched:
                launched_pid = mac_automation.launch_hidden(bundle_id)
            mac_automation.run_applescript(
                _SCRIPTS[suffix],
                [str(staged_source), str(staged_pdf), staged_source.name,
                 "quit" if launched else "keep"],
                timeout_seconds=timeout_seconds,
            )
        except mac_automation.MacAutomationError as exc:
            if launched_pid:
                # A sign-in or activation dialog blocks ``quit``; stop the instance we started.
                mac_automation.terminate_process(launched_pid)
            raise _office_error(owner, exc) from exc
        finally:
            mac_automation.unregister_launch(launched_pid)
        if not staged_pdf.is_file() or staged_pdf.stat().st_size == 0:
            raise OfficeAutomationError("office_export_failed", f"Microsoft {owner} wrote no PDF")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staged_pdf, destination_path)
        return destination_path
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _office_error(owner: str, exc: mac_automation.MacAutomationError) -> OfficeAutomationError:
    message = str(exc)
    if exc.error_code == "chemdraw_automation_not_authorized":
        return OfficeAutomationError(
            "office_automation_not_authorized",
            f"macOS blocked automation of Microsoft {owner}; allow it in System Settings > "
            "Privacy & Security > Automation",
        )
    if exc.error_code == "native_timeout" or "(1001)" in message or "(-128)" in message:
        return OfficeAutomationError(
            "office_not_ready",
            f"Microsoft {owner} did not open the document. Start {owner} once, sign in and "
            "activate Microsoft 365, and close any open dialog, then retry",
        )
    return OfficeAutomationError("office_export_failed", f"Microsoft {owner} PDF export failed: {message}")
