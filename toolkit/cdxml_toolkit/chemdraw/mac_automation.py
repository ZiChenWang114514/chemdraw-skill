"""ChemDraw for macOS automation through AppleScript.

ChemDraw for Windows is driven through COM (``ChemDraw.Application``).  ChemDraw
for macOS has no COM server, but it ships an AppleScript dictionary
(``ChemDraw.sdef``) with ``open``, ``save ... in ... as``, ``close``, ``quit``
and selection properties such as ``SMILES``.  This module wraps those commands
behind the same open -> save as -> close -> quit sequence the COM code uses, so
native renders and format conversions come from ChemDraw itself on macOS too.

Every call goes through ``osascript`` in a subprocess with a timeout.  The first
call asks macOS for Automation permission (System Settings > Privacy & Security
> Automation); a denied permission is reported with a stable error code.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from functools import lru_cache
import html
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Iterable, Optional


BUNDLE_IDS = (
    "com.revvity.ChemDraw",
    "com.perkinelmer.ChemDraw",
    "com.cambridgesoft.ChemDraw",
)

# AppleScript ``save ... as`` type names (CFBundleTypeName in ChemDraw's
# Info.plist), keyed by output extension.
SAVE_TYPES = {
    ".cdx": "ChemDraw",
    ".cdxml": "ChemDraw XML",
    ".png": "PNG",
    ".svg": "Scalable Vector Graphics (SVG)",
    ".pdf": "PDF",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".gif": "GIF",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".bmp": "BMP",
    ".eps": "Encapsulated PostScript",
    ".mol": "MDL Molfile V2000",
    ".sdf": "MDL SDfile V2000",
    ".rxn": "Reaction Molfile V2000 (RXN)",
    ".cml": "Chemical Markup Language (CML)",
    ".skc": "ISIS/Sketch (SKC)",
    ".tgf": "Transportable Graphics (TGF)",
}

# Native PNG export resolution of ChemDraw for macOS.
NATIVE_PNG_DPI = 300

_NOT_AUTHORIZED = (-1743, -10004)
_NOT_RUNNING = (-600, -609)
_TIMED_OUT = (-1712,)

# Windows fonts common in ChemDraw documents, with installed macOS equivalents in
# order of preference.  ChemDraw for macOS shows a blocking "font is not
# available" alert when a document names a missing font, which stalls
# automation, so staged copies name an installed font instead.
FONT_EQUIVALENTS = {
    "simsun": ("Songti SC", "STSong", "PingFang SC"),
    "nsimsun": ("Songti SC", "STSong", "PingFang SC"),
    "\u5b8b\u4f53": ("Songti SC", "STSong", "PingFang SC"),
    "\u65b0\u5b8b\u4f53": ("Songti SC", "STSong", "PingFang SC"),
    "simhei": ("Heiti SC", "STHeiti", "PingFang SC"),
    "\u9ed1\u4f53": ("Heiti SC", "STHeiti", "PingFang SC"),
    "microsoft yahei": ("PingFang SC", "Heiti SC"),
    "microsoft yahei ui": ("PingFang SC", "Heiti SC"),
    "\u5fae\u8f6f\u96c5\u9ed1": ("PingFang SC", "Heiti SC"),
    "dengxian": ("PingFang SC", "Heiti SC"),
    "\u7b49\u7ebf": ("PingFang SC", "Heiti SC"),
    "kaiti": ("Kaiti SC", "STKaiti"),
    "kaiti_gb2312": ("Kaiti SC", "STKaiti"),
    "\u6977\u4f53": ("Kaiti SC", "STKaiti"),
    "fangsong": ("STFangsong", "Songti SC"),
    "fangsong_gb2312": ("STFangsong", "Songti SC"),
    "\u4eff\u5b8b": ("STFangsong", "Songti SC"),
    "mingliu": ("LiSong Pro", "Songti TC"),
    "pmingliu": ("LiSong Pro", "Songti TC"),
    "\u7d30\u660e\u9ad4": ("LiSong Pro", "Songti TC"),
    "\u65b0\u7d30\u660e\u9ad4": ("LiSong Pro", "Songti TC"),
    "microsoft jhenghei": ("PingFang TC", "Heiti TC"),
    "ms gothic": ("Hiragino Sans", "Osaka"),
    "ms mincho": ("Hiragino Mincho ProN", "Osaka"),
    "malgun gothic": ("Apple SD Gothic Neo", "AppleGothic"),
    "times new roman": ("Times New Roman", "Times"),
    "arial": ("Arial", "Helvetica"),
    "calibri": ("Helvetica Neue", "Helvetica"),
    "segoe ui": ("Helvetica Neue", "Helvetica"),
    "tahoma": ("Tahoma", "Helvetica Neue", "Helvetica"),
    "verdana": ("Verdana", "Helvetica"),
    "cambria": ("Times New Roman", "Times"),
    "cambria math": ("STIX Two Math", "Times New Roman", "Times"),
    "courier new": ("Courier New", "Courier"),
    "consolas": ("Menlo", "Courier"),
    "symbol": ("Symbol",),
}
_CJK_FALLBACKS = ("PingFang SC", "Songti SC", "Heiti SC", "Arial Unicode MS")
_LATIN_FALLBACKS = ("Helvetica", "Arial")
_LATIN_CHARSETS = {"iso-8859-1", "x-mac-roman", "windows-1252", "ascii", "us-ascii", ""}
_FONT_ELEMENT = re.compile(r"<font\b[^>]*>", re.I)
_ATTRIBUTE = re.compile(r'(\b[\w:-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')

_OPEN_DOCUMENT = '''
on posixFile(p)
  return POSIX file p
end posixFile

on findDocument(srcPath)
  tell application id "@BUNDLE_ID@"
    repeat 200 times
      repeat with d in documents
        try
          set f to file of d
          if f is not missing value and (POSIX path of f) is srcPath then return contents of d
        end try
      end repeat
      delay 0.05
    end repeat
  end tell
  error "ChemDraw did not open the document" number 1001
end findDocument
'''

# One generic script runs a list of steps on a document.  Paths and menu names
# are passed as data (argv), never as script source.  The bundle identifier is
# compiled in as a literal (validated by ``_steps_script``) because ChemDraw's
# own terms such as ``menu item`` only compile inside a literal application tell.
#   select-all                    Edit > Select All
#   menu <menu> <item>            run a ChemDraw menu command on the document
#   save <path> <type>            save a copy in the given format
#   query                         append SMILES, formula, weights of the selection
_STEPS_SCRIPT = _OPEN_DOCUMENT + '''
on run argv
  set srcPath to item 1 of argv
  set srcFile to POSIX file srcPath
  set answers to {}
  tell application id "@BUNDLE_ID@"
    open srcFile
    set doc to my findDocument(srcPath)
    try
      set i to 2
      repeat while i is less than or equal to (count of argv)
        set step to item i of argv
        if step is "select-all" then
          do menu item "Select All" of menu "Edit"
          set i to i + 1
        else if step is "menu" then
          do menu item (item (i + 2) of argv) of menu (item (i + 1) of argv)
          set i to i + 3
        else if step is "save" then
          set outFile to my posixFile(item (i + 1) of argv)
          save doc in outFile as (item (i + 2) of argv)
          set i to i + 3
        else if step is "query" then
          set end of answers to (SMILES of selection of doc)
          set end of answers to (Molecular Formula of selection of doc)
          set end of answers to ((Molecular Weight of selection of doc) as text)
          set end of answers to ((Exact Mass of selection of doc) as text)
          set i to i + 1
        else
          error "Unknown step " & step number 1002
        end if
      end repeat
    on error errorMessage number errorNumber
      close doc saving no
      error errorMessage number errorNumber
    end try
    close doc saving no
  end tell
  set AppleScript's text item delimiters to (character id 31)
  return answers as text
end run
'''


class MacAutomationError(RuntimeError):
    """ChemDraw for macOS automation failure with a stable public error code."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.public_message = message


def is_macos() -> bool:
    return sys.platform == "darwin"


def _bundle_from_executable(path: Path) -> Optional[Path]:
    for parent in (path, *path.parents):
        if parent.suffix == ".app":
            return parent
    return None


def find_application() -> Optional[Path]:
    """Return the ChemDraw ``.app`` bundle, honouring ``CHEMDRAW_EXE``."""
    configured = os.environ.get("CHEMDRAW_EXE")
    if configured:
        bundle = _bundle_from_executable(Path(configured).expanduser())
        if bundle is not None and bundle.is_dir():
            return bundle
    roots = [Path("/Applications"), Path.home() / "Applications"]
    for root in roots:
        try:
            candidates = sorted(root.glob("ChemDraw*.app"), reverse=True)
        except OSError:
            continue
        for candidate in candidates:
            if (candidate / "Contents" / "Info.plist").is_file():
                return candidate
    for bundle_id in BUNDLE_IDS:
        try:
            found = subprocess.run(
                ["mdfind", f"kMDItemCFBundleIdentifier == '{bundle_id}'"],
                capture_output=True, text=True, timeout=10, check=False,
            ).stdout.split("\n")
        except (OSError, subprocess.SubprocessError):
            continue
        for line in found:
            if line.endswith(".app") and Path(line).is_dir():
                return Path(line)
    return None


def find_executable() -> Optional[Path]:
    bundle = find_application()
    if bundle is None:
        return None
    info = application_info(bundle)
    executable = bundle / "Contents" / "MacOS" / info.get("CFBundleExecutable", "ChemDraw")
    return executable if executable.is_file() else None


def application_info(bundle: Path) -> dict:
    try:
        with (bundle / "Contents" / "Info.plist").open("rb") as handle:
            return plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return {}


def bundle_identifier(bundle: Optional[Path] = None) -> str:
    bundle = bundle or find_application()
    if bundle is None:
        raise MacAutomationError("chemdraw_not_found", "ChemDraw for macOS was not found")
    identifier = application_info(bundle).get("CFBundleIdentifier")
    return identifier or BUNDLE_IDS[0]


def _classify(returncode: int, stderr: str) -> MacAutomationError:
    message = stderr.strip() or f"osascript exited with status {returncode}"
    for code in _NOT_AUTHORIZED:
        if f"({code})" in message:
            return MacAutomationError(
                "chemdraw_automation_not_authorized",
                "macOS blocked automation of ChemDraw; allow it in System Settings > "
                "Privacy & Security > Automation",
            )
    for code in _TIMED_OUT:
        if f"({code})" in message:
            return MacAutomationError(
                "native_timeout",
                "ChemDraw did not answer in time; a dialog may be open in ChemDraw",
            )
    for code in _NOT_RUNNING:
        if f"({code})" in message:
            return MacAutomationError(
                "chemdraw_not_running", f"ChemDraw stopped responding: {message}"
            )
    lowered = message.lower()
    if "licen" in lowered or "activation" in lowered:
        return MacAutomationError(
            "chemdraw_license_unavailable",
            "ChemDraw reports that the installed product license is unavailable",
        )
    return MacAutomationError("native_automation_failed", f"ChemDraw automation failed: {message}")


@lru_cache(maxsize=1)
def installed_font_families() -> frozenset:
    """Font family names installed on this Mac, read through CoreText."""
    if not is_macos():
        return frozenset()
    try:
        core_text = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreText"))
        core_foundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    except (OSError, TypeError):
        return frozenset()
    core_text.CTFontManagerCopyAvailableFontFamilyNames.restype = ctypes.c_void_p
    core_foundation.CFArrayGetCount.restype = ctypes.c_long
    core_foundation.CFArrayGetCount.argtypes = [ctypes.c_void_p]
    core_foundation.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
    core_foundation.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
    core_foundation.CFStringGetCString.restype = ctypes.c_bool
    core_foundation.CFStringGetCString.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32,
    ]
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    names = core_text.CTFontManagerCopyAvailableFontFamilyNames()
    if not names:
        return frozenset()
    families = set()
    try:
        buffer = ctypes.create_string_buffer(1024)
        for index in range(core_foundation.CFArrayGetCount(names)):
            value = core_foundation.CFArrayGetValueAtIndex(names, index)
            if core_foundation.CFStringGetCString(value, buffer, len(buffer), 0x08000100):
                families.add(buffer.value.decode("utf-8"))
    finally:
        core_foundation.CFRelease(names)
    return frozenset(families)


def _replacement_font(name: str, charset: str, available: frozenset) -> Optional[str]:
    lowered = {family.lower(): family for family in available}
    if name.lower() in lowered:
        return None
    candidates = FONT_EQUIVALENTS.get(name.strip().lower(), ())
    fallbacks = _LATIN_FALLBACKS if charset.strip().lower() in _LATIN_CHARSETS else _CJK_FALLBACKS
    for candidate in (*candidates, *fallbacks):
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def substitute_missing_fonts(path: str | Path, available: Optional[frozenset] = None) -> dict:
    """Rename fonts in a CDXML font table that are not installed on this Mac.

    Only the ``name`` attribute of ``<font>`` elements in ``<fonttable>`` changes;
    the font ids, and therefore every styled text run, stay the same.  Returns
    ``{original name: installed name}`` for the fonts that were renamed.
    """
    target = Path(path)
    available = installed_font_families() if available is None else frozenset(available)
    if not available:
        return {}
    text = target.read_text(encoding="utf-8")
    start = text.find("<fonttable")
    end = text.find("</fonttable>", start)
    if start < 0 or end < 0:
        return {}
    changes: dict = {}

    def rename(match: re.Match) -> str:
        element = match.group(0)
        attributes = {
            key.lower(): html.unescape(double if double is not None else single)
            for key, _quoted, double, single in _ATTRIBUTE.findall(element)
        }
        name = attributes.get("name")
        if not name:
            return element
        replacement = _replacement_font(name, attributes.get("charset", ""), available)
        if replacement is None:
            return element
        changes[name] = replacement
        return _ATTRIBUTE.sub(
            lambda attribute: (
                f'{attribute.group(1)}="{html.escape(replacement, quote=True)}"'
                if attribute.group(1).lower() == "name" else attribute.group(0)
            ),
            element,
        )

    table = _FONT_ELEMENT.sub(rename, text[start:end])
    if changes:
        target.write_text(text[:start] + table + text[end:], encoding="utf-8")
    return changes


def run_applescript(script: str, args: Iterable[str] = (), *, timeout_seconds: float = 60) -> str:
    """Run an AppleScript through ``osascript`` and return its stdout."""
    try:
        completed = subprocess.run(
            ["osascript", "-", *args],
            input=script, capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MacAutomationError(
            "native_timeout", f"ChemDraw did not finish within {timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise MacAutomationError("native_automation_failed", f"osascript is unavailable: {exc}") from exc
    if completed.returncode != 0:
        raise _classify(completed.returncode, completed.stderr)
    return completed.stdout.strip()


def is_running(bundle_id: str) -> bool:
    script = f'return application id "{bundle_id}" is running'
    try:
        return run_applescript(script, timeout_seconds=15) == "true"
    except MacAutomationError:
        return False


_BUNDLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,254}$")


def _steps_script(bundle_id: str) -> str:
    if not _BUNDLE_ID_PATTERN.match(bundle_id):
        raise MacAutomationError("chemdraw_not_found", "ChemDraw has an invalid bundle identifier")
    return _STEPS_SCRIPT.replace("@BUNDLE_ID@", bundle_id)


def save_type_for(path: Path) -> str:
    try:
        return SAVE_TYPES[path.suffix.lower()]
    except KeyError:
        raise MacAutomationError(
            "native_format_unsupported",
            f"ChemDraw for macOS cannot save {path.suffix or 'files without an extension'}",
        ) from None


class MacChemDrawSession:
    """Launch ChemDraw once (hidden, in the background) and reuse it for exports.

    ChemDraw is quit on exit only when this session launched it, matching the
    COM sessions on Windows.
    """

    def __init__(self, *, timeout_seconds: int = 60, bundle: Optional[Path] = None):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.bundle = bundle
        self.bundle_id: Optional[str] = None
        self.launched = False

    def __enter__(self):
        return self

    def start(self) -> None:
        if self.bundle_id is not None:
            return
        bundle = self.bundle or find_application()
        if bundle is None:
            raise MacAutomationError("chemdraw_not_found", "ChemDraw for macOS was not found")
        self.bundle = bundle
        bundle_id = bundle_identifier(bundle)
        if not is_running(bundle_id):
            subprocess.run(["open", "-g", "-b", bundle_id], check=False, timeout=30)
            deadline = time.monotonic() + self.timeout_seconds
            while not is_running(bundle_id):
                if time.monotonic() > deadline:
                    raise MacAutomationError(
                        "native_timeout", "ChemDraw did not start in time"
                    )
                time.sleep(0.25)
            self.launched = True
        self.bundle_id = bundle_id

    def _openable(self, source: str | Path, workspace: Path) -> Path:
        """Return a copy of ``source`` that ChemDraw opens without a font alert."""
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"ChemDraw input not found: {source_path}")
        staged = workspace / f"input{source_path.suffix.lower()}"
        shutil.copy2(source_path, staged)
        if staged.suffix == ".cdxml":
            substitute_missing_fonts(staged)
        return staged.resolve()

    def run_steps(self, source: str | Path, steps: Iterable[str]) -> list[str]:
        """Open ``source`` and run ChemDraw steps on it (see ``_STEPS_SCRIPT``)."""
        steps = [str(step) for step in steps]
        self.start()
        with tempfile.TemporaryDirectory(prefix="cdx-mac-") as workspace:
            staged = self._openable(source, Path(workspace))
            output = run_applescript(
                _steps_script(self.bundle_id), [str(staged), *steps],
                timeout_seconds=self.timeout_seconds,
            )
        return output.split("\x1f") if output else []

    def export(self, source: str | Path, *destinations: str | Path) -> list[str]:
        """Open ``source`` and save it to every destination (format from extension)."""
        if not destinations:
            raise ValueError("at least one destination is required")
        steps, outputs = [], []
        for destination in destinations:
            destination_path = Path(destination).expanduser().resolve()
            steps += ["save", str(destination_path), save_type_for(destination_path)]
            outputs.append(str(destination_path))
        self.run_steps(source, steps)
        return outputs

    def analyze(self, source: str | Path) -> dict:
        """ChemDraw's own reading of every structure in ``source``.

        Returns ``smiles`` (reactions as ``reactants>>products``),
        ``formula``, ``molecular_weight`` and ``exact_mass``.
        """
        answers = self.run_steps(source, ["select-all", "query"])
        if len(answers) != 4:
            raise MacAutomationError("native_automation_failed", "ChemDraw returned no structure data")
        smiles, formula, weight, exact = answers

        def number(text: str) -> Optional[float]:
            try:
                return float(text.replace(",", "."))
            except ValueError:
                return None

        return {
            "smiles": smiles,
            "formula": formula,
            "molecular_weight": number(weight),
            "exact_mass": number(exact),
        }

    def smiles(self, source: str | Path) -> str:
        """Return ChemDraw's own SMILES for every structure in ``source``."""
        return self.analyze(source)["smiles"]

    def apply_menu(
        self, source: str | Path, destination: str | Path, *commands: tuple[str, str],
        select_all: bool = True,
    ) -> str:
        """Run ChemDraw menu ``commands`` (``(menu, item)`` pairs) and save the result."""
        destination_path = Path(destination).expanduser().resolve()
        steps: list[str] = ["select-all"] if select_all else []
        for menu, item in commands:
            steps += ["menu", menu, item]
        steps += ["save", str(destination_path), save_type_for(destination_path)]
        self.run_steps(source, steps)
        return str(destination_path)

    def clean(self, source: str | Path, destination: str | Path, *, reaction: bool = False) -> str:
        """ChemDraw Structure > Clean Up Structure (or Clean Up Reaction)."""
        item = "Clean Up Reaction" if reaction else "Clean Up Structure"
        return self.apply_menu(source, destination, ("Structure", item))

    def structure_names(self, source: str | Path) -> list[str]:
        """Names from ChemDraw Structure > Convert Structure to Name, in document order."""
        before = _caption_texts(Path(source))
        with tempfile.TemporaryDirectory(prefix="cdx-mac-") as workspace:
            named = Path(workspace) / "named.cdxml"
            self.apply_menu(source, named, ("Structure", "Convert Structure to Name"))
            after = _caption_texts(named)
        remaining = list(before)
        names = []
        for text in after:
            if text in remaining:
                remaining.remove(text)
            else:
                names.append(text)
        return names

    def name_to_structure(self, name: str, destination: str | Path) -> str:
        """ChemDraw Structure > Convert Name to Structure for one chemical name."""
        with tempfile.TemporaryDirectory(prefix="cdx-mac-") as workspace:
            source = Path(workspace) / "name.cdxml"
            source.write_text(_caption_document(name), encoding="utf-8")
            return self.apply_menu(source, destination, ("Structure", "Convert Name to Structure"))

    def close(self) -> None:
        if self.launched and self.bundle_id:
            try:
                run_applescript(
                    f'tell application id "{self.bundle_id}" to quit saving no',
                    timeout_seconds=30,
                )
            except MacAutomationError:
                pass
        self.launched = False
        self.bundle_id = None

    def __exit__(self, exc_type, exc, traceback):
        self.close()


def _caption_texts(path: Path) -> list[str]:
    """Plain text of every free caption (``<t>`` outside fragments) in a CDXML file."""
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    texts = []

    def walk(element, inside_fragment: bool) -> None:
        for child in element:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "t" and not inside_fragment:
                text = "".join(child.itertext()).strip()
                if text:
                    texts.append(text)
            walk(child, inside_fragment or tag == "fragment")

    walk(root, False)
    return texts


def _caption_document(text: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
        '<CDXML><fonttable><font id="3" charset="iso-8859-1" name="Arial"/></fonttable>'
        '<page id="1"><t id="2" p="100 100"><s font="3" size="10">'
        f"{html.escape(text, quote=False)}</s></t></page></CDXML>"
    )


def convert_file(source: str | Path, destination: str | Path, *, timeout_seconds: int = 60) -> str:
    """Convert one file with ChemDraw for macOS (format from the destination extension)."""
    with MacChemDrawSession(timeout_seconds=timeout_seconds) as session:
        return session.export(source, destination)[0]


def flatten_png(path: str | Path, dpi: int = NATIVE_PNG_DPI) -> None:
    """Composite a transparent native PNG onto white and apply the requested DPI.

    ChemDraw for Windows renders with ``TransparentPNGs = False``; ChemDraw for
    macOS always exports transparent PNGs at 300 dpi.  This keeps both outputs
    identical in appearance and resolution.
    """
    from PIL import Image

    target = Path(path)
    with Image.open(target) as image:
        image.load()
        rgba = image.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, "white")
    flattened.paste(rgba, mask=rgba.getchannel("A"))
    if dpi != NATIVE_PNG_DPI and dpi > 0:
        scale = dpi / NATIVE_PNG_DPI
        size = (max(1, round(flattened.width * scale)), max(1, round(flattened.height * scale)))
        flattened = flattened.resize(size, Image.LANCZOS)
    flattened.save(target, dpi=(dpi, dpi))
