#!/usr/bin/env python3
"""Build a self-contained OpenVSX / VS Code Marketplace .vsix package for ChemDraw Studio,
syncing the live 2D Reaxys/SciFinder editor & 3D Mol* templates directly from toolkit/ui_apps.py,
and optionally installing it across all VS Code-family IDEs on the host.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
VSCODE_DIR = ROOT / "vscode"
TOOLKIT_DIR = ROOT / "toolkit"
MEDIA_DIR = VSCODE_DIR / "media"
GEN_DIR = MEDIA_DIR / "generated"
DIST_DIR = VSCODE_DIR / "dist"


ACTIVITY_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="12,2.5 20.2,7.25 20.2,16.75 12,21.5 3.8,16.75 3.8,7.25"/>
  <line x1="12" y1="5.6" x2="17.5" y2="8.8"/>
  <line x1="17.5" y1="15.2" x2="12" y2="18.4"/>
  <line x1="6.5" y1="15.2" x2="6.5" y2="8.8"/>
  <circle cx="20.2" cy="7.25" r="1.6" fill="currentColor" stroke="none"/>
</svg>
"""


def _make_icon_png(width: int = 256, height: int = 256) -> bytes:
    """Render a crisp 256x256 anti-aliased benzene-hexagon badge PNG using stdlib only."""
    bg = (13, 23, 42)
    accent = (56, 189, 248)
    white = (248, 250, 252)
    cx, cy = width * 0.5, height * 0.5
    outer_r = width * 0.34
    inner_r = width * 0.245

    verts = [
        (cx + math.cos(-math.pi / 2 + k * math.pi / 3) * outer_r,
         cy + math.sin(-math.pi / 2 + k * math.pi / 3) * outer_r)
        for k in range(6)
    ]
    in_verts = [
        (cx + math.cos(-math.pi / 2 + k * math.pi / 3) * inner_r,
         cy + math.sin(-math.pi / 2 + k * math.pi / 3) * inner_r)
        for k in range(6)
    ]

    def seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy or 1.0
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    rows = bytearray()
    corner_r = 46.0
    for y in range(height):
        rows.append(0)
        for x in range(width):
            # Rounded-square mask
            qx = max(0.0, abs(x - cx) - (width * 0.5 - corner_r))
            qy = max(0.0, abs(y - cy) - (height * 0.5 - corner_r))
            mask_d = math.hypot(qx, qy) - corner_r
            if mask_d > 1.0:
                rows.extend((0, 0, 0, 0))
                continue
            alpha = 255 if mask_d < -0.5 else int(255 * (1.0 - (mask_d + 0.5) / 1.5))

            # Distance to hexagon edges + 3 Kekule double bonds + heteroatom dot
            d_hex = min(seg_dist(x, y, verts[k][0], verts[k][1], verts[(k + 1) % 6][0], verts[(k + 1) % 6][1]) for k in range(6))
            d_dbl = min(seg_dist(x, y, in_verts[k][0], in_verts[k][1], in_verts[(k + 1) % 6][0], in_verts[(k + 1) % 6][1]) for k in (0, 2, 4))
            d_dot = abs(math.hypot(x - verts[1][0], y - verts[1][1])) - 13.5

            r, g, b = bg
            # Subtle radial glow
            glow = max(0.0, 1.0 - math.hypot(x - cx, y - cy) / (width * 0.48))
            r = int(r + 14 * glow)
            g = int(g + 28 * glow)
            b = int(b + 48 * glow)

            for dist, thick, col in ((d_hex, 5.2, white), (d_dbl, 4.0, accent)):
                cov = max(0.0, min(1.0, (thick + 0.8 - dist) / 1.6))
                if cov > 0 and not (col is white and math.hypot(x - verts[1][0], y - verts[1][1]) < 18.0):
                    r = int(r * (1 - cov) + col[0] * cov)
                    g = int(g * (1 - cov) + col[1] * cov)
                    b = int(b * (1 - cov) + col[2] * cov)

            cov_dot = max(0.0, min(1.0, (1.0 - d_dot) / 1.6))
            if cov_dot > 0:
                r = int(r * (1 - cov_dot) + accent[0] * cov_dot)
                g = int(g * (1 - cov_dot) + accent[1] * cov_dot)
                b = int(b * (1 - cov_dot) + accent[2] * cov_dot)

            rows.extend((r, g, b, alpha))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")


def _vsix_manifest(pkg: dict) -> str:
    cats = ",".join(pkg.get("categories", ["Other"]))
    tags = ",".join(pkg.get("keywords", []))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{pkg['name']}" Version="{pkg['version']}" Publisher="{pkg['publisher']}" />
    <DisplayName>{pkg['displayName'].replace('&', '&amp;')}</DisplayName>
    <Description xml:space="preserve">{pkg['description'].replace('&', '&amp;')}</Description>
    <Tags>{tags}</Tags>
    <Categories>{cats}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{pkg['engines']['vscode']}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
    </Properties>
    <License>extension/LICENSE.txt</License>
    <Icon>extension/media/icon.png</Icon>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Changelog" Path="extension/CHANGELOG.md" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="extension/LICENSE.txt" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/media/icon.png" Addressable="true" />
  </Assets>
</PackageManifest>
"""


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json" />
  <Default Extension=".js" ContentType="application/javascript" />
  <Default Extension=".html" ContentType="text/html" />
  <Default Extension=".svg" ContentType="image/svg+xml" />
  <Default Extension=".png" ContentType="image/png" />
  <Default Extension=".md" ContentType="text/markdown" />
  <Default Extension=".txt" ContentType="text/plain" />
  <Default Extension=".vsixmanifest" ContentType="text/xml" />
</Types>
"""


def build_vsix(output_path: Path | None = None) -> Path:
    sys.path.insert(0, str(TOOLKIT_DIR))
    from cdxml_toolkit.mcp_runtime import ui_apps  # noqa: WPS433

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    (MEDIA_DIR / "activity-icon.svg").write_text(ACTIVITY_ICON_SVG, encoding="utf-8", newline="\n")
    (MEDIA_DIR / "icon.png").write_bytes(_make_icon_png(256, 256))

    # Sync live 2D Reaxys/SciFinder Studio fragment & 3D Mol* HTML directly from toolkit/ui_apps.py
    (GEN_DIR / "studio-fragment.html").write_text(
        ui_apps.render_drawing_studio_fragment(),
        encoding="utf-8",
        newline="\n",
    )
    (GEN_DIR / "molstar-app.html").write_text(
        ui_apps.render_molstar_app_html(),
        encoding="utf-8",
        newline="\n",
    )

    # Syntax-check extension JS with Node if Node is present
    node = shutil.which("node")
    if node:
        for js_file in (VSCODE_DIR / "src" / "extension.js", VSCODE_DIR / "src" / "webview-bridge.js"):
            subprocess.run([node, "--check", str(js_file)], check=True)

    pkg = json.loads((VSCODE_DIR / "package.json").read_text(encoding="utf-8"))
    vsix_file = output_path or (DIST_DIR / f"{pkg['name']}-{pkg['version']}.vsix")
    vsix_file.parent.mkdir(parents=True, exist_ok=True)

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    with zipfile.ZipFile(vsix_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("extension.vsixmanifest", _vsix_manifest(pkg))
        zf.writestr("extension/LICENSE.txt", license_text)

        files_to_pack = [
            VSCODE_DIR / "package.json",
            VSCODE_DIR / "README.md",
            VSCODE_DIR / "CHANGELOG.md",
            VSCODE_DIR / "src" / "extension.js",
            VSCODE_DIR / "src" / "webview-bridge.js",
            MEDIA_DIR / "activity-icon.svg",
            MEDIA_DIR / "icon.png",
            GEN_DIR / "studio-fragment.html",
            GEN_DIR / "molstar-app.html",
        ]
        for fp in files_to_pack:
            arcname = "extension/" + fp.relative_to(VSCODE_DIR).as_posix()
            zf.write(fp, arcname=arcname)

    return vsix_file


def discover_vscode_family_clis() -> list[tuple[str, str]]:
    """Discover installed VS Code-compatible editor CLIs (never touching Claude Code)."""
    found: list[tuple[str, str]] = []
    seen_paths: set[str] = set()

    def add(label: str, exe: str | None) -> None:
        if not exe or not os.path.isfile(exe):
            return
        norm = os.path.normcase(os.path.abspath(exe))
        if norm in seen_paths:
            return
        seen_paths.add(norm)
        found.append((label, exe))

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        prog = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        win_candidates = [
            ("VS Code", os.path.join(prog, "Microsoft VS Code", "bin", "code.cmd")),
            ("VS Code", r"D:\Program Files\Microsoft VS Code\bin\code.cmd"),
            ("VS Code", os.path.join(local, "Programs", "Microsoft VS Code", "bin", "code.cmd")),
            ("Cursor", os.path.join(local, "Programs", "cursor", "resources", "app", "bin", "cursor.cmd")),
            ("Windsurf", os.path.join(local, "Programs", "Windsurf", "bin", "windsurf.cmd")),
            ("Trae", os.path.join(local, "Programs", "Trae", "bin", "trae.cmd")),
            ("Trae", r"D:\Programs\Trae\bin\trae.cmd"),
            ("Kiro", os.path.join(local, "Programs", "Kiro", "bin", "kiro.cmd")),
            ("Kiro", os.path.join(prog86, "Kiro", "bin", "kiro.cmd")),
            ("Kiro", r"D:\Program Files (x86)\Kiro\bin\kiro.cmd"),
            ("Qoder", r"D:\Program Files\Qoder CN IDE\bin\code.cmd"),
        ]
        for label, cand in win_candidates:
            add(label, cand)

    for label, cmd in (
        ("VS Code", "code"),
        ("Cursor", "cursor"),
        ("Windsurf", "windsurf"),
        ("Trae", "trae"),
        ("Kiro", "kiro"),
        ("VSCodium", "codium"),
    ):
        add(label, shutil.which(cmd))

    return found


def _install_into_extensions_dir(vsix_path: Path, ext_root: Path, pkg: dict) -> str:
    """Direct VSIX unpack + extensions.json registration when an IDE CLI is mid-update or absent."""
    import time

    ext_id = f"{pkg['publisher']}.{pkg['name']}"
    rel_dir = f"{ext_id}-{pkg['version']}"
    target_dir = ext_root / rel_dir
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(vsix_path, "r") as zf:
        for member in zf.namelist():
            if not member.startswith("extension/"):
                continue
            rel = member[len("extension/"):]
            if not rel:
                continue
            dest = target_dir / rel
            if member.endswith("/"):
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member))

    reg_file = ext_root / "extensions.json"
    entries = []
    if reg_file.is_file():
        try:
            entries = json.loads(reg_file.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    entries = [e for e in entries if (e.get("identifier") or {}).get("id", "").lower() != ext_id.lower()]
    fs_path = str(target_dir.resolve())
    posix_path = target_dir.resolve().as_posix()
    if sys.platform == "win32" and len(posix_path) >= 2 and posix_path[1] == ":":
        drive = posix_path[0].lower()
        uri_path = f"/{drive}:{posix_path[2:]}"
        external = f"file:///{drive}%3A{posix_path[2:]}"
        fs_path = drive + fs_path[1:]
    else:
        uri_path = posix_path
        external = f"file://{posix_path}"

    entries.append({
        "identifier": {"id": ext_id},
        "version": pkg["version"],
        "location": {
            "$mid": 1,
            "fsPath": fs_path,
            "_sep": 1 if sys.platform == "win32" else 0,
            "external": external,
            "path": uri_path,
            "scheme": "file",
        },
        "relativeLocation": rel_dir,
        "metadata": {
            "installedTimestamp": int(time.time() * 1000),
            "pinned": True,
            "source": "vsix",
        },
    })
    reg_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return str(target_dir)


def install_into_ides(vsix_path: Path) -> list[dict]:
    pkg = json.loads((VSCODE_DIR / "package.json").read_text(encoding="utf-8"))
    results = []
    succeeded_labels: set[str] = set()
    for label, cli in discover_vscode_family_clis():
        try:
            proc = subprocess.run(
                [cli, "--install-extension", str(vsix_path), "--force"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            ok = proc.returncode == 0
            if ok:
                succeeded_labels.add(label)
            results.append({
                "ide": label,
                "cli": cli,
                "ok": ok,
                "output": (proc.stdout + "\n" + proc.stderr).strip()[:260],
            })
        except Exception as exc:
            results.append({"ide": label, "cli": cli, "ok": False, "output": str(exc)})

    home = Path.home()
    for label, dot_folder in (
        ("VS Code", ".vscode"),
        ("Antigravity", ".antigravity"),
        ("Cursor", ".cursor"),
        ("Windsurf", ".windsurf"),
        ("Qoder", ".qoder"),
        ("Qoder CN", ".qoder-cn"),
        ("Trae", ".trae"),
        ("Trae CN", ".trae-cn"),
    ):
        ext_root = home / dot_folder / "extensions"
        if label not in succeeded_labels and (ext_root / "extensions.json").is_file():
            installed_dir = _install_into_extensions_dir(vsix_path, ext_root, pkg)
            results.append({
                "ide": label,
                "method": "extensions_dir",
                "ok": True,
                "output": f"Installed directly into {installed_dir}",
            })
            succeeded_labels.add(label)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Explicit output path for .vsix")
    parser.add_argument("--install-all", action="store_true", help="Install the built .vsix into all detected VS Code-family IDEs")
    args = parser.parse_args(argv)

    vsix_path = build_vsix(args.output)
    summary: dict = {
        "ok": True,
        "vsix_path": str(vsix_path),
        "size_bytes": vsix_path.stat().st_size,
    }
    if args.install_all:
        summary["installations"] = install_into_ides(vsix_path)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
