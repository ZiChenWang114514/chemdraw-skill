#!/usr/bin/env python3
"""
ELN CDX Reaction Cleanup Tool

Cleans up reaction schemes exported from Findmolecule ELN (.cdx files):
  - Converts CDX to CDXML
  - Scales coordinates to match ACS Document 1996 style
  - Applies ACS Document 1996 document settings
  - Cleans up individual structures (bond lengths, angles)
  - Sets all text labels to Arial 10pt Bold
  - Cleans up reaction layout (arrow alignment, reagent/condition placement)

Uses a two-pass ChemDraw COM approach:
  Pass 1: Convert CDX -> CDXML, scale coordinates, apply style, clean structures, fix fonts
  Pass 2: Reopen and clean reaction layout (requires fresh document load)

ChemDraw must be CLOSED before running this tool.
ChemDraw is launched minimized, restored to normal before quitting
(so toolbar state is preserved), and closed automatically when done.

Usage:
    python eln_cdx_cleanup.py input.cdx [-o output.cdxml] [--scale 0.5]
    python eln_cdx_cleanup.py input1.cdx input2.cdx input3.cdx
    python eln_cdx_cleanup.py *.cdx --output-dir cleaned/

Python API:
    from .eln_cdx_cleanup import cleanup_eln_cdx
    cleanup_eln_cdx("KL-CC-001.cdx", "KL-CC-001-cleaned.cdxml", scale_factor=0.5)
"""

import argparse
import json
import os
import re
import sys
import time
import tempfile
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# XML-based coordinate scaling
# ---------------------------------------------------------------------------

def _parse_point(s):
    """Parse space-separated coordinate string into list of floats."""
    return [float(v) for v in s.split()]


def _format_point(vals):
    """Format list of floats to space-separated string (2 decimal places)."""
    return ' '.join('{:.2f}'.format(v) for v in vals)


def _scale_point(x, y, cx, cy, factor):
    """Scale point (x,y) toward centroid (cx,cy) by factor."""
    return cx + (x - cx) * factor, cy + (y - cy) * factor


def _sanitize_cdxml(filepath):
    """
    Sanitize a CDXML file by removing invalid XML characters.

    ChemDraw COM exports may include binary data in objecttag Value
    attributes (e.g. Findmolecule ELN metadata). These contain bytes
    that are not valid in XML 1.0 and cause parsing failures.

    Replaces invalid characters with empty string in-place.
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    # XML 1.0 valid characters:
    # #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # Decode as UTF-8 (with replacement for truly broken bytes),
    # then strip invalid XML chars.
    text = raw.decode('utf-8', errors='replace')
    # Remove control chars except tab, newline, carriage return
    cleaned = re.sub(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]', '', text)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned)


def scale_cdxml_coordinates(input_path, output_path, factor=0.5):
    """
    Scale all coordinates in a CDXML file by the given factor,
    centered on the centroid of all node/text positions.

    This shrinks structures while preserving text sizes, preparing
    them for ChemDraw's Clean Up Structure to normalize to the
    target bond length.
    """
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Collect centroid from node and text positions
    positions = []
    for elem in root.iter():
        if elem.tag in ('n', 't') and 'p' in elem.attrib:
            pt = _parse_point(elem.attrib['p'])
            positions.append((pt[0], pt[1]))

    if not positions:
        # Nothing to scale — just copy
        tree.write(output_path, xml_declaration=True, encoding='UTF-8')
        return

    cx = sum(p[0] for p in positions) / len(positions)
    cy = sum(p[1] for p in positions) / len(positions)

    # Scale all coordinate attributes
    for elem in root.iter():
        # p="x y" — node and text positions
        if 'p' in elem.attrib:
            pt = _parse_point(elem.attrib['p'])
            nx, ny = _scale_point(pt[0], pt[1], cx, cy, factor)
            elem.attrib['p'] = _format_point([nx, ny])

        # BoundingBox="x1 y1 x2 y2"
        if 'BoundingBox' in elem.attrib:
            pt = _parse_point(elem.attrib['BoundingBox'])
            if len(pt) >= 4:
                nx1, ny1 = _scale_point(pt[0], pt[1], cx, cy, factor)
                nx2, ny2 = _scale_point(pt[2], pt[3], cx, cy, factor)
                elem.attrib['BoundingBox'] = _format_point([nx1, ny1, nx2, ny2])

        # 3D points on arrows: Head3D, Tail3D, Center3D, etc.
        for attr in ['Head3D', 'Tail3D', 'Center3D',
                     'MajorAxisEnd3D', 'MinorAxisEnd3D']:
            if attr in elem.attrib:
                pt = _parse_point(elem.attrib[attr])
                nx, ny = _scale_point(pt[0], pt[1], cx, cy, factor)
                if len(pt) >= 3:
                    elem.attrib[attr] = _format_point([nx, ny, pt[2]])
                else:
                    elem.attrib[attr] = _format_point([nx, ny])

    tree.write(output_path, xml_declaration=True, encoding='UTF-8')


# ---------------------------------------------------------------------------
# ChemDraw COM helpers
# ---------------------------------------------------------------------------

def _find_chemdraw_windows():
    """Find all ChemDraw window handles."""
    import win32gui

    def callback(hwnd, results):
        try:
            title = win32gui.GetWindowText(hwnd)
            if 'ChemDraw' in title:
                results.append(hwnd)
        except:
            pass
    results = []
    win32gui.EnumWindows(callback, results)
    return results


def _minimize_chemdraw():
    """Minimize all ChemDraw windows to avoid disrupting the user."""
    import win32gui
    import win32con
    hwnds = _find_chemdraw_windows()
    for hwnd in hwnds:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return hwnds


def _restore_chemdraw_window():
    """
    Restore (un-minimize) ChemDraw windows before quitting.

    ChemDraw saves toolbar/window state to the registry on Quit().
    If we quit while minimized, it saves a 'no toolbars' state.
    Restoring the window first ensures proper state is saved.
    """
    import win32gui
    import win32con
    hwnds = _find_chemdraw_windows()
    for hwnd in hwnds:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.5)


def _get_chemdraw():
    """
    Get or launch ChemDraw COM instance.
    Returns (cdApp, launched_new).
    If an existing instance is found, it is reused.
    """
    import win32com.client
    try:
        cdApp = win32com.client.GetActiveObject('ChemDraw.Application')
        return cdApp, False
    except:
        cdApp = win32com.client.Dispatch('ChemDraw.Application')
        return cdApp, True


def _chemdraw_open(cdApp, filepath):
    """Open a file in ChemDraw (minimized), activate the document."""
    cdApp.Visible = True
    time.sleep(1)
    _minimize_chemdraw()
    doc = cdApp.Documents.Open(filepath)
    time.sleep(1)
    _minimize_chemdraw()
    doc.Activate()
    time.sleep(0.5)
    return doc


# ---------------------------------------------------------------------------
# CDX to CDXML conversion via COM
# ---------------------------------------------------------------------------

def _cdx_to_cdxml_com(cdx_path, cdxml_path):
    """Convert CDX to CDXML using ChemDraw COM."""
    import win32com.client
    cdApp, launched = _get_chemdraw()
    doc = _chemdraw_open(cdApp, cdx_path)
    doc.SaveAs(cdxml_path)
    time.sleep(0.5)
    doc.Close(False)
    if launched:
        _restore_chemdraw_window()
        cdApp.Quit()
    return cdxml_path


# ---------------------------------------------------------------------------
# Main cleanup workflow
# ---------------------------------------------------------------------------

# Default ACS Document 1996 style sheet path
ACS_STYLE_PATH = os.path.join(
    r'C:\ProgramData\PerkinElmerInformatics\ChemOffice2016',
    r'ChemDraw\ChemDraw Items\ACS Document 1996.cds'
)


def cleanup_eln_cdx(input_path, output_path=None, scale_factor=0.5,
                    style_path=None):
    """
    Clean up a reaction scheme exported from Findmolecule ELN.

    Parameters
    ----------
    input_path : str
        Path to input .cdx or .cdxml file.
    output_path : str, optional
        Path for output .cdxml file. Defaults to input stem + '-cleaned.cdxml'.
    scale_factor : float, optional
        Factor to scale coordinates before cleanup (default 0.5).
        Set to 1.0 to skip scaling.
    style_path : str, optional
        Path to .cds style sheet (default: ACS Document 1996).

    Returns
    -------
    str
        Path to the cleaned output file.
    """
    import win32com.client

    if style_path is None:
        style_path = ACS_STYLE_PATH

    if not os.path.exists(style_path):
        print("WARNING: Style sheet not found: {}".format(style_path))
        print("         Skipping style application.")
        style_path = None

    input_path = os.path.abspath(input_path)
    input_ext = os.path.splitext(input_path)[1].lower()
    input_stem = os.path.splitext(input_path)[0]

    if output_path is None:
        output_path = input_stem + '-cleaned.cdxml'
    output_path = os.path.abspath(output_path)

    # Create temp directory for intermediate files
    tmpdir = tempfile.mkdtemp(prefix='eln_cleanup_')

    try:
        # --- Step 0: Convert CDX to CDXML if needed ---
        if input_ext == '.cdx':
            cdxml_path = os.path.join(tmpdir, 'converted.cdxml')
            print("  Converting CDX to CDXML...")
            _cdx_to_cdxml_com(input_path, cdxml_path)
            # Sanitize: remove invalid XML chars from ELN metadata
            _sanitize_cdxml(cdxml_path)
        elif input_ext == '.cdxml':
            cdxml_path = input_path
        else:
            raise ValueError("Unsupported file format: {}".format(input_ext))

        # --- Step 1: Scale coordinates in XML ---
        scaled_path = os.path.join(tmpdir, 'scaled.cdxml')
        if scale_factor != 1.0:
            print("  Scaling coordinates by {}...".format(scale_factor))
            scale_cdxml_coordinates(cdxml_path, scaled_path, factor=scale_factor)
        else:
            scaled_path = cdxml_path

        # --- Pass 1: Apply style + Clean Structure + Change fonts ---
        print("  Pass 1: Style + Clean Structure + Fonts...")
        cdApp, launched = _get_chemdraw()
        doc = _chemdraw_open(cdApp, scaled_path)

        # Apply style
        if style_path:
            doc.Settings.ApplySettings(style_path, style_path)
            time.sleep(0.5)

        # Clean Up Structure
        doc.Objects.Select()
        time.sleep(0.5)
        cdApp.MenuBars(1).Menus(5).MenuItems(6).Execute()
        time.sleep(1)

        # Change all caption text to Arial 10pt Bold
        captions = doc.Objects.Captions
        for i in range(1, captions.Count + 1):
            cap = captions.Item(i)
            cap.Family = "Arial"
            cap.Size = 10.0
            cap.Face = 96  # Bold

        # Also set document-level label defaults
        doc.Settings.LabelFont = "Arial"
        doc.Settings.LabelSize = 10.0
        doc.Settings.LabelFace = 96

        # Save pass 1 result
        pass1_path = os.path.join(tmpdir, 'pass1.cdxml')
        doc.SaveAs(pass1_path)
        time.sleep(0.5)
        doc.Close(False)

        # Close ChemDraw between passes if we launched it
        if launched:
            _restore_chemdraw_window()
            cdApp.Quit()
            time.sleep(1)

        # --- Pass 2: Reopen fresh + Clean Up Reaction ---
        print("  Pass 2: Clean Up Reaction...")
        cdApp, launched = _get_chemdraw()
        doc = _chemdraw_open(cdApp, pass1_path)

        doc.Objects.Select()
        time.sleep(1)
        cdApp.MenuBars(1).Menus(5).MenuItems(7).Execute()
        time.sleep(1)

        # Save final output
        doc.SaveAs(output_path)
        time.sleep(0.5)
        doc.Close(False)

        if launched:
            _restore_chemdraw_window()
            cdApp.Quit()

    finally:
        # Cleanup temp files
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except:
            pass

    return output_path


def cleanup_multiple(input_paths, output_dir=None, scale_factor=0.5,
                     style_path=None):
    """
    Clean up multiple CDX/CDXML files.

    Parameters
    ----------
    input_paths : list of str
        Paths to input files.
    output_dir : str, optional
        Directory for output files. Defaults to same directory as each input.
    scale_factor : float
        Coordinate scale factor (default 0.5).
    style_path : str, optional
        Path to .cds style sheet.

    Returns
    -------
    list of str
        Paths to cleaned output files.
    """
    results = []
    for path in input_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            out = os.path.join(output_dir, name + '-cleaned.cdxml')
        else:
            out = os.path.join(os.path.dirname(path), name + '-cleaned.cdxml')

        print("Processing: {}".format(os.path.basename(path)))
        try:
            result = cleanup_eln_cdx(path, out, scale_factor=scale_factor,
                                     style_path=style_path)
            print("  -> {}\n".format(result))
            results.append(result)
        except Exception as e:
            print("  ERROR: {}\n".format(e))
            results.append(None)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Clean up ELN-exported CDX reaction schemes to ACS 1996 style.',
        epilog='Examples:\n'
               '  python eln_cdx_cleanup.py KL-CC-001.cdx\n'
               '  python eln_cdx_cleanup.py *.cdx --output-dir cleaned/\n'
               '  python eln_cdx_cleanup.py input.cdx -o output.cdxml --scale 0.5\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input', nargs='+',
                        help='Input .cdx or .cdxml file(s)')
    parser.add_argument('-o', '--output',
                        help='Output file path (single file mode only)')
    parser.add_argument('--output-dir',
                        help='Output directory (batch mode)')
    parser.add_argument('--scale', type=float, default=0.5,
                        help='Coordinate scale factor (default: 0.5)')
    parser.add_argument('--style',
                        help='Path to .cds style sheet '
                             '(default: ACS Document 1996)')
    parser.add_argument('--json', action='store_true',
                        help='Output result as JSON to stdout')

    args = parser.parse_args(argv)

    # When --json, redirect status prints to stderr and capture warnings
    if args.json:
        import io
        _real_stdout = sys.stdout
        _capture = io.StringIO()
        sys.stdout = _capture

    try:
        if len(args.input) == 1 and args.output:
            # Single file mode
            result_path = cleanup_eln_cdx(args.input[0], args.output,
                            scale_factor=args.scale, style_path=args.style)
            if args.json:
                sys.stdout = _real_stdout
                captured = _capture.getvalue()
                warnings = [l.strip() for l in captured.splitlines()
                            if 'WARNING' in l.upper()]
                # Dump captured status to stderr
                if captured.strip():
                    print(captured, file=sys.stderr, end='')
                result = {
                    "input": os.path.abspath(args.input[0]),
                    "output": os.path.abspath(result_path),
                    "warnings": warnings,
                }
                print(json.dumps(result, indent=2))
        elif args.json:
            # Batch mode with --json
            results = cleanup_multiple(args.input, output_dir=args.output_dir,
                                       scale_factor=args.scale,
                                       style_path=args.style)
            sys.stdout = _real_stdout
            captured = _capture.getvalue()
            warnings = [l.strip() for l in captured.splitlines()
                        if 'WARNING' in l.upper()]
            if captured.strip():
                print(captured, file=sys.stderr, end='')
            json_results = []
            for inp, out in zip(args.input, results):
                json_results.append({
                    "input": os.path.abspath(inp),
                    "output": os.path.abspath(out) if out else None,
                    "warnings": warnings,
                })
            print(json.dumps(json_results, indent=2))
        else:
            # Batch mode
            cleanup_multiple(args.input, output_dir=args.output_dir,
                             scale_factor=args.scale, style_path=args.style)
    except Exception:
        if args.json:
            sys.stdout = _real_stdout
        raise

    return 0


if __name__ == '__main__':
    sys.exit(main())
