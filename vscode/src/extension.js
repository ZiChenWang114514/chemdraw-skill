"use strict";

const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const os = require("os");
const cp = require("child_process");

const Z_TO_SYM = {
  1: "H", 3: "Li", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F", 11: "Na", 12: "Mg",
  13: "Al", 14: "Si", 15: "P", 16: "S", 17: "Cl", 19: "K", 20: "Ca", 26: "Fe",
  27: "Co", 28: "Ni", 29: "Cu", 30: "Zn", 34: "Se", 35: "Br", 44: "Ru", 45: "Rh",
  46: "Pd", 47: "Ag", 50: "Sn", 53: "I", 78: "Pt", 79: "Au"
};

/** Locate the shared chemdraw-skill Python runtime if installed on this machine. */
function findToolkitPython() {
  const cfg = vscode.workspace.getConfiguration("chemdraw").get("pythonPath", "").trim();
  if (cfg && fs.existsSync(cfg)) return cfg;

  const candidates = [];
  if (process.platform === "win32") {
    const lad = process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
    candidates.push(path.join(lad, "chemdraw-skill", "venv", "Scripts", "python.exe"));
  } else if (process.platform === "darwin") {
    candidates.push(path.join(os.homedir(), "Library", "Application Support", "chemdraw-skill", "venv", "bin", "python"));
  } else {
    const xdg = process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
    candidates.push(path.join(xdg, "chemdraw-skill", "venv", "bin", "python"));
  }
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

/** Locate installed cdx.py CLI entry point if present. */
function findCdxScript() {
  const home = os.homedir();
  const rels = [
    [".agents", "skills", "chemdraw", "scripts", "cdx.py"],
    [".cursor", "skills", "chemdraw", "scripts", "cdx.py"],
    [".copilot", "skills", "chemdraw", "scripts", "cdx.py"],
    [".codeium", "windsurf", "skills", "chemdraw", "scripts", "cdx.py"],
    [".cline", "skills", "chemdraw", "scripts", "cdx.py"],
    [".roo", "skills", "chemdraw", "scripts", "cdx.py"],
    [".gemini", "antigravity", "skills", "chemdraw", "scripts", "cdx.py"]
  ];
  for (const r of rels) {
    const p = path.join(home, ...r);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

/** Fast, dependency-free CDXML -> Studio Graph parser so .cdxml CustomEditors open in < 10 ms. */
function parseCdxmlToGraph(xmlText, title) {
  const atoms = [];
  const bonds = [];
  const arrows = [];
  const idToIdx = new Map();

  const nodeRe = /<n\b([^>]*?)(?:\/>|>([\s\S]*?)<\/n>)/g;
  let m;
  while ((m = nodeRe.exec(xmlText)) !== null) {
    const attrs = m[1] || "";
    const inner = m[2] || "";
    if (/NodeType="ExternalConnectionPoint"/.test(attrs)) continue;
    const idM = attrs.match(/\bid="([^"]+)"/);
    const pM = attrs.match(/\bp="([-\d.]+)\s+([-\d.]+)"/);
    if (!idM || !pM) continue;
    let sym = "C";
    const elM = attrs.match(/\bElement="(\d+)"/);
    if (elM) sym = Z_TO_SYM[parseInt(elM[1], 10)] || "C";
    const sM = inner.match(/<s\b[^>]*>([^<]+)<\/s>/);
    if (sM && /NodeType="(?:Nickname|Fragment|GenericNickname|Unspecified)"/.test(attrs)) {
      sym = sM[1].trim().slice(0, 10) || sym;
    }
    const atom = { s: sym, x: parseFloat(pM[1]), y: parseFloat(pM[2]) };
    const chgM = attrs.match(/\bCharge="([-\d]+)"/);
    if (chgM) atom.chg = parseInt(chgM[1], 10);
    const isoM = attrs.match(/\bIsotope="(\d+)"/);
    if (isoM) atom.iso = parseInt(isoM[1], 10);
    idToIdx.set(idM[1], atoms.length);
    atoms.push(atom);
  }

  const bondRe = /<b\b([^>]*?)\/?>/g;
  while ((m = bondRe.exec(xmlText)) !== null) {
    const attrs = m[1] || "";
    const bM = attrs.match(/\bB="([^"]+)"/);
    const eM = attrs.match(/\bE="([^"]+)"/);
    if (!bM || !eM || !idToIdx.has(bM[1]) || !idToIdx.has(eM[1])) continue;
    const ordM = attrs.match(/\bOrder="(\d+)"/);
    let order = ordM ? parseInt(ordM[1], 10) : 1;
    const dispM = attrs.match(/\bDisplay="([^"]+)"/i);
    if (dispM) {
      const d = dispM[1].toLowerCase();
      if (d.includes("wedgebegin") || d === "wedgedbegin") order = 4;
      else if (d.includes("hash")) order = 5;
      else if (d.includes("wavy")) order = 6;
      else if (d === "bold") order = 7;
    }
    bonds.push({ a: idToIdx.get(bM[1]), b: idToIdx.get(eM[1]), o: order });
  }

  const arrowRe = /<arrow\b([^>]*?)\/?>/g;
  while ((m = arrowRe.exec(xmlText)) !== null) {
    const attrs = m[1] || "";
    const hd = attrs.match(/\bHead3D="([-\d.]+)\s+([-\d.]+)/);
    const tl = attrs.match(/\bTail3D="([-\d.]+)\s+([-\d.]+)/);
    if (hd && tl) {
      arrows.push({
        x1: parseFloat(tl[1]), y1: parseFloat(tl[2]),
        x2: parseFloat(hd[1]), y2: parseFloat(hd[2]),
        style: "solid", above: "", below: ""
      });
    }
  }

  // Normalize coordinate scale to 34px bond length centered around (340, 178)
  if (atoms.length > 0) {
    let lenSum = 0, lenCnt = 0;
    for (const b of bonds) {
      const dx = atoms[b.b].x - atoms[b.a].x;
      const dy = atoms[b.b].y - atoms[b.a].y;
      const d = Math.hypot(dx, dy);
      if (d > 0.5) { lenSum += d; lenCnt++; }
    }
    const avg = lenCnt > 0 ? lenSum / lenCnt : 14.4;
    const scale = Math.abs(avg - 34) < 3 ? 1.0 : 34.0 / avg;
    const xs = atoms.map((a) => a.x), ys = atoms.map((a) => a.y);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    for (const a of atoms) {
      a.x = +(340 + (a.x - cx) * scale).toFixed(2);
      a.y = +(178 + (a.y - cy) * scale).toFixed(2);
    }
    for (const ar of arrows) {
      ar.x1 = +(340 + (ar.x1 - cx) * scale).toFixed(2);
      ar.y1 = +(178 + (ar.y1 - cy) * scale).toFixed(2);
      ar.x2 = +(340 + (ar.x2 - cx) * scale).toFixed(2);
      ar.y2 = +(178 + (ar.y2 - cy) * scale).toFixed(2);
    }
  }

  return { name: title || "CDXML Document", template_key: "cdxml", atoms, bonds, arrows };
}

/** Fast V2000 Molfile -> Studio Graph parser. */
function parseMolfileToGraph(molText, title) {
  const lines = molText.replace(/\r/g, "").split("\n");
  const vIdx = lines.findIndex((l) => l.includes("V2000"));
  if (vIdx < 0) return { name: title || "Blank", atoms: [], bonds: [] };
  const na = parseInt(lines[vIdx].slice(0, 3), 10) || 0;
  const nb = parseInt(lines[vIdx].slice(3, 6), 10) || 0;
  const atoms = [];
  const bonds = [];
  for (let i = 0; i < na; i++) {
    const l = lines[vIdx + 1 + i] || "";
    const x = parseFloat(l.slice(0, 10)) || 0;
    const y = parseFloat(l.slice(10, 20)) || 0;
    const s = l.slice(31, 34).trim() || "C";
    atoms.push({ s, x, y: -y });
  }
  for (let i = 0; i < nb; i++) {
    const l = lines[vIdx + 1 + na + i] || "";
    const a = parseInt(l.slice(0, 3), 10) - 1;
    const b = parseInt(l.slice(3, 6), 10) - 1;
    const bt = parseInt(l.slice(6, 9), 10) || 1;
    const st = parseInt(l.slice(9, 12), 10) || 0;
    let o = bt <= 3 ? bt : 1;
    if (st === 1) o = 4;
    else if (st === 6) o = 5;
    else if (st === 4) o = 6;
    if (a >= 0 && b >= 0 && a < na && b < na) {
      const entry = { a, b, o };
      if (bt === 4) entry.q = "arom";
      else if (bt === 8) entry.q = "any";
      bonds.push(entry);
    }
  }
  if (atoms.length > 0) {
    const cx = atoms.reduce((s, a) => s + a.x, 0) / atoms.length;
    const cy = atoms.reduce((s, a) => s + a.y, 0) / atoms.length;
    const scale = 34.0 / 1.54;
    for (const a of atoms) {
      a.x = +(340 + (a.x - cx) * scale).toFixed(2);
      a.y = +(178 + (a.y - cy) * scale).toFixed(2);
    }
  }
  return { name: title || lines[0].trim() || "Molfile", template_key: "mol", atoms, bonds };
}

/** Fast 3D scene parser for PDB / XYZ files when toolkit Python is absent. */
function parse3DTextScene(text, ext) {
  const atoms = [];
  const bonds = [];
  if (ext === ".xyz") {
    const lines = text.trim().split(/\r?\n/);
    for (const line of lines.slice(2)) {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 4) {
        const [s, x, y, z] = parts;
        atoms.push({ idx: atoms.length, s, x: +parseFloat(x) || 0, y: +parseFloat(y) || 0, z: +parseFloat(z) || 0 });
      }
    }
  } else {
    for (const line of text.split(/\r?\n/)) {
      const rec = line.slice(0, 6).trim();
      if ((rec === "ATOM" || rec === "HETATM") && line.length >= 54 && atoms.length < 2500) {
        const atomName = line.slice(12, 16).trim();
        const x = parseFloat(line.slice(30, 38)) || 0;
        const y = parseFloat(line.slice(38, 46)) || 0;
        const z = parseFloat(line.slice(46, 54)) || 0;
        const elRaw = (line.length >= 78 ? line.slice(76, 78).trim() : "") || atomName.replace(/[^A-Za-z]/g, "").slice(0, 1) || "C";
        const s = elRaw[0].toUpperCase() + (elRaw.length > 1 ? elRaw.slice(1).toLowerCase() : "");
        atoms.push({ idx: atoms.length, s, x, y, z });
      }
    }
  }
  for (let i = 0; i < Math.min(atoms.length, 400); i++) {
    for (let j = i + 1; j < Math.min(atoms.length, 400); j++) {
      const d = Math.hypot(atoms[i].x - atoms[j].x, atoms[i].y - atoms[j].y, atoms[i].z - atoms[j].z);
      if (d > 0.4 && d < 1.92) bonds.push({ a: i, b: j, o: 1 });
    }
  }
  return { atoms, bonds };
}

function getNonce() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let out = "";
  for (let i = 0; i < 24; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

/** Build the complete HTML for any 2D Studio Webview (Panel, Sidebar, or CustomEditor). */
function buildStudioWebviewHtml(context, webview, initialGraph, bootOpts = {}) {
  const fragPath = path.join(context.extensionPath, "media", "generated", "studio-fragment.html");
  const bridgePath = path.join(context.extensionPath, "src", "webview-bridge.js");
  let frag = fs.readFileSync(fragPath, "utf8");
  const bridgeJs = fs.readFileSync(bridgePath, "utf8");

  const defaultStyle = vscode.workspace.getConfiguration("chemdraw").get("defaultStyle", "acs1996");
  if (initialGraph) {
    // Replace INITIAL graph & style cleanly inside the generated fragment
    frag = frag.replace(
      /const INITIAL = \{.*?\};\n/,
      () => "const INITIAL = " + JSON.stringify({
        graph: initialGraph,
        style: defaultStyle,
        styles: {
          acs1996: { label: "ACS 1996 / JACS", bondLength: 14.4, lineWidth: 0.6 },
          jacs: { label: "JACS Publication", bondLength: 14.4, lineWidth: 0.6 },
          angew: { label: "Angewandte", bondLength: 14.2, lineWidth: 0.68 },
          nature: { label: "Nature Chem.", bondLength: 14.0, lineWidth: 0.6 },
          science: { label: "Science", bondLength: 13.8, lineWidth: 0.58 },
          rsc: { label: "RSC Chem. Sci.", bondLength: 14.4, lineWidth: 0.6 },
          wiley: { label: "Wiley Adv.", bondLength: 14.5, lineWidth: 0.66 }
        }
      }).replace(/<\//g, "<\\/") + ";\n"
    );
  }

  const nonce = getNonce();
  const csp = [
    "default-src 'none'",
    `img-src ${webview.cspSource} data: blob:`,
    `style-src ${webview.cspSource} 'unsafe-inline'`,
    `script-src 'nonce-${nonce}' 'unsafe-inline'`
  ].join("; ");

  // Add nonce to inline script inside studio-fragment.html
  frag = frag.replace("<script>", `<script nonce="${nonce}">`);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="${csp}">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ChemDraw 2D Studio</title>
</head>
<body>
  <script nonce="${nonce}">window.__CHEMDRAW_VSCODE_BOOT__ = ${JSON.stringify(bootOpts)};</script>
  ${frag}
  <script nonce="${nonce}">${bridgeJs}</script>
</body>
</html>`;
}

/** Build the complete HTML for the 3D Mol* Conformer / Macromolecule Viewer Webview. */
function build3DViewerHtml(context, payload) {
  const tmplPath = path.join(context.extensionPath, "media", "generated", "molstar-app.html");
  let html = fs.readFileSync(tmplPath, "utf8");
  if (payload) {
    html = html.replace(
      /const INITIAL = \{.*?\};\n/,
      () => "const INITIAL = " + JSON.stringify(payload).replace(/<\//g, "<\\/") + ";\n"
    );
  }
  return html;
}

/** Universal Multi-Harness 'Transfer to Agent' Dispatcher. */
async function dispatchStructureToAgent(msg) {
  const wsFolder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  const syncDir = wsFolder
    ? path.join(wsFolder.uri.fsPath, ".chemdraw")
    : path.join(os.homedir(), ".chemdraw");
  fs.mkdirSync(syncDir, { recursive: true });

  const cdxmlPath = path.join(syncDir, "studio-live.cdxml");
  const molPath = path.join(syncDir, "studio-live.mol");
  const jsonPath = path.join(syncDir, "studio-live.json");

  if (msg.cdxml) fs.writeFileSync(cdxmlPath, msg.cdxml, "utf8");
  if (msg.molfile) fs.writeFileSync(molPath, msg.molfile, "utf8");
  fs.writeFileSync(
    jsonPath,
    JSON.stringify(
      {
        smiles: msg.smiles || "",
        smarts: msg.smarts || "",
        formula: msg.formula || "",
        mw: msg.mw || "",
        exactMass: msg.exactMass || "",
        queryMode: msg.queryMode || "exact",
        style: msg.style || "acs1996",
        cdxmlPath,
        molPath,
        updatedAt: new Date().toISOString()
      },
      null,
      2
    ),
    "utf8"
  );

  const relCdxml = wsFolder ? path.relative(wsFolder.uri.fsPath, cdxmlPath).replace(/\\/g, "/") : cdxmlPath;
  const structuredPrompt = [
    `[ChemDraw 2D Studio · ${msg.queryMode || "exact"} mode]`,
    msg.smiles ? `SMILES: ${msg.smiles}` : null,
    msg.smarts && msg.queryMode === "substructure" ? `SMARTS: ${msg.smarts}` : null,
    msg.formula && msg.formula !== "—" ? `Formula: ${msg.formula} (MW ${msg.mw})` : null,
    `Editable CDXML: ${relCdxml}`
  ].filter(Boolean).join(" | ");

  await vscode.env.clipboard.writeText(structuredPrompt);

  const pref = vscode.workspace.getConfiguration("chemdraw").get("preferredChatTarget", "auto");
  const allCommands = new Set(await vscode.commands.getCommands(true));
  let focusedTarget = "Clipboard";

  const tryFocus = async (cmd, arg, label) => {
    if (!allCommands.has(cmd)) return false;
    try {
      if (arg !== undefined) await vscode.commands.executeCommand(cmd, arg);
      else await vscode.commands.executeCommand(cmd);
      focusedTarget = label;
      return true;
    } catch (_e) {
      return false;
    }
  };

  if (pref !== "clipboardOnly") {
    if (pref === "cline") {
      await tryFocus("claude-dev.SidebarProvider.focus", undefined, "Cline");
    } else if (pref === "roo") {
      await tryFocus("roo-cline.SidebarProvider.focus", undefined, "Roo Code");
    } else if (pref === "continue") {
      await tryFocus("continue.focusContinueInput", undefined, "Continue");
    } else {
      // Auto-detect native IDE chat (VS Code Copilot / Cursor / Windsurf / Trae / Kiro / Antigravity), then extensions
      const okNative = await tryFocus(
        "workbench.action.chat.open",
        { query: structuredPrompt, isPartialQuery: true },
        "IDE Chat"
      );
      if (!okNative) {
        (await tryFocus("roo-cline.SidebarProvider.focus", undefined, "Roo Code")) ||
          (await tryFocus("claude-dev.SidebarProvider.focus", undefined, "Cline")) ||
          (await tryFocus("continue.focusContinueInput", undefined, "Continue"));
      }
    }
  }

  const pick = await vscode.window.showInformationMessage(
    `Transferred ${msg.formula || "structure"} to ${focusedTarget} (copied prompt & saved ${relCdxml}).`,
    "Open .cdxml",
    "Render 300 DPI PNG",
    "3D Mol*"
  );
  if (pick === "Open .cdxml") {
    await vscode.commands.executeCommand("vscode.openWith", vscode.Uri.file(cdxmlPath), "chemdraw.cdxmlEditor");
  } else if (pick === "Render 300 DPI PNG") {
    await renderNativeChemDrawPng(vscode.Uri.file(cdxmlPath));
  } else if (pick === "3D Mol*" && msg.smiles) {
    await vscode.commands.executeCommand("chemdraw.openSmilesIn3D", msg.smiles);
  }
}

/** Run native ChemDraw 300 DPI PNG rendering via cdx.py if available. */
async function renderNativeChemDrawPng(uri) {
  const targetUri = uri || (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri);
  if (!targetUri || !targetUri.fsPath.toLowerCase().endsWith(".cdxml")) {
    vscode.window.showWarningMessage("Select or save a .cdxml file first to render a native ChemDraw PNG.");
    return;
  }
  const py = findToolkitPython();
  const cdx = findCdxScript();
  if (!py || !cdx) {
    vscode.window.showWarningMessage("ChemDraw Skill shared Python runtime was not found. Run `python scripts/install.py --runtime --apply` first.");
    return;
  }
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: "Rendering 300 DPI ChemDraw PNG..." },
    () => new Promise((resolve) => {
      cp.execFile(py, [cdx, "render", targetUri.fsPath], { timeout: 45000 }, async (err, stdout, stderr) => {
        if (err) {
          vscode.window.showErrorMessage(`ChemDraw render failed: ${(stderr || err.message).slice(0, 240)}`);
          resolve();
          return;
        }
        try {
          const out = JSON.parse(stdout);
          const png = (out.outputs && (out.outputs.png_path || out.outputs.output_path)) || targetUri.fsPath.replace(/\.cdxml$/i, ".png");
          if (fs.existsSync(png)) {
            await vscode.commands.executeCommand("vscode.open", vscode.Uri.file(png), vscode.ViewColumn.Beside);
          }
        } catch (_e) {}
        resolve();
      });
    })
  );
}

/** Generate 3D payload via toolkit Python (ETKDGv3 + MMFF94) with lightweight fallback. */
function build3DPayloadFromTarget(target, context) {
  const py = findToolkitPython();
  if (py) {
    const code = [
      "import json, sys",
      "from cdxml_toolkit.mcp_runtime import ui_apps",
      "q = sys.argv[1]",
      "res = ui_apps.view_molecule_3d(q, launch_browser=False)",
      "print(json.dumps({k: res.get(k) for k in ('title','format','representation','smiles','pdb_id','formula','molecular_weight','mol_data','pdb_data','scene','is_macromolecule')}))"
    ].join("; ");
    const r = cp.spawnSync(py, ["-c", code, target], { encoding: "utf8", timeout: 20000 });
    if (r.status === 0 && r.stdout.trim()) {
      try {
        return JSON.parse(r.stdout.trim().split(/\r?\n/).pop());
      } catch (_e) {}
    }
  }
  void context;
  const clean = (target || "aspirin").trim();
  if (/^[0-9][A-Za-z0-9]{3}$/.test(clean)) {
    return {
      title: `PDB ${clean.toUpperCase()}`,
      pdb_id: clean.toUpperCase(),
      format: "mmcif",
      representation: "cartoon",
      is_macromolecule: true,
      scene: { atoms: [], bonds: [] }
    };
  }
  return {
    title: clean,
    smiles: clean,
    format: "sdf",
    representation: "ball-and-stick",
    is_macromolecule: false,
    scene: { atoms: [], bonds: [] }
  };
}

/** Attach common Webview message handlers for any 2D Studio surface. */
function wireStudioMessages(webview, context, extraHandlers = {}) {
  webview.onDidReceiveMessage(async (msg) => {
    if (!msg || typeof msg !== "object") return;
    if (extraHandlers[msg.type]) {
      await extraHandlers[msg.type](msg);
      return;
    }
    if (msg.type === "transferToAgent") {
      await dispatchStructureToAgent(msg);
    } else if (msg.type === "saveFileDialog") {
      const ext = path.extname(msg.filename || ".cdxml").slice(1) || "cdxml";
      const uri = await vscode.window.showSaveDialog({
        defaultUri: vscode.Uri.file(
          path.join(
            (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0].uri.fsPath) || os.homedir(),
            msg.filename || "structure.cdxml"
          )
        ),
        filters: { "Chemical Structure": [ext] }
      });
      if (uri) {
        await vscode.workspace.fs.writeFile(uri, Buffer.from(msg.content || "", "utf8"));
        vscode.window.setStatusBarMessage(`Saved ${path.basename(uri.fsPath)}`, 3500);
      }
    } else if (msg.type === "open3D") {
      const q = msg.smiles || "aspirin";
      await open3DMolstarPanel(context, q);
    }
  });
}

let activeStudioPanel = null;

async function open2DStudioPanel(context, viewColumn, initialGraph, initialTextToLoad) {
  if (activeStudioPanel) {
    activeStudioPanel.reveal(viewColumn || vscode.ViewColumn.Beside);
    if (initialTextToLoad) {
      activeStudioPanel.webview.postMessage({ type: "loadTextStructure", text: initialTextToLoad });
    }
    return activeStudioPanel;
  }
  const panel = vscode.window.createWebviewPanel(
    "chemdraw.studioPanel",
    "ChemDraw 2D Studio",
    viewColumn || vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true }
  );
  activeStudioPanel = panel;
  panel.onDidDispose(() => {
    if (activeStudioPanel === panel) activeStudioPanel = null;
  });
  panel.webview.html = buildStudioWebviewHtml(context, panel.webview, initialGraph, { isCustomEditor: false });
  wireStudioMessages(panel.webview, context, {
    ready: async () => {
      if (initialTextToLoad) {
        panel.webview.postMessage({ type: "loadTextStructure", text: initialTextToLoad });
      }
    }
  });
  return panel;
}

async function open3DMolstarPanel(context, queryOrPath) {
  let target = queryOrPath;
  if (!target) {
    target = await vscode.window.showInputBox({
      title: "ChemDraw 3D Mol* Viewer",
      prompt: "Enter a SMILES string, compound name (aspirin, taxol, caffeine), 4-char PDB ID (1CRN, 6LU7), or file path",
      value: "caffeine"
    });
  }
  if (!target) return;
  const payload = build3DPayloadFromTarget(target, context);
  const panel = vscode.window.createWebviewPanel(
    "chemdraw.molstar3d",
    `3D Mol*: ${payload.title || target}`,
    vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true }
  );
  panel.webview.html = build3DViewerHtml(context, payload);
}

/** Sidebar WebviewView Provider (dockable in Primary or Right Secondary Sidebar beside Agent Chat!). */
class StudioSidebarProvider {
  constructor(context) {
    this.context = context;
    this.view = null;
  }
  resolveWebviewView(webviewView) {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = buildStudioWebviewHtml(this.context, webviewView.webview, null, { isSidebar: true });
    wireStudioMessages(webviewView.webview, this.context);
  }
}

/** Native Two-Way CustomTextEditorProvider for *.cdxml, *.mol, and *.sdf files. */
class Structure2DCustomEditorProvider {
  constructor(context, format) {
    this.context = context;
    this.format = format; // "cdxml" | "mol"
  }
  async resolveCustomTextEditor(document, webviewPanel) {
    webviewPanel.webview.options = { enableScripts: true };
    const text = document.getText();
    const fileName = path.basename(document.uri.fsPath);
    const graph = this.format === "mol"
      ? parseMolfileToGraph(text, fileName)
      : parseCdxmlToGraph(text, fileName);

    let lastSavedText = text;
    webviewPanel.webview.html = buildStudioWebviewHtml(this.context, webviewPanel.webview, graph, {
      isCustomEditor: true,
      format: this.format,
      fileName
    });

    wireStudioMessages(webviewPanel.webview, this.context, {
      saveCustomDocument: async (msg) => {
        if (!msg.content) return;
        lastSavedText = msg.content;
        const edit = new vscode.WorkspaceEdit();
        edit.replace(
          document.uri,
          new vscode.Range(0, 0, document.lineCount, 0),
          msg.content
        );
        await vscode.workspace.applyEdit(edit);
        await document.save();
      },
      renderNativePng: async () => {
        await renderNativeChemDrawPng(document.uri);
      }
    });

    const sub = vscode.workspace.onDidChangeTextDocument((ev) => {
      if (ev.document.uri.toString() !== document.uri.toString()) return;
      const updated = ev.document.getText();
      if (updated === lastSavedText) return;
      // External edit (e.g. AI coding agent updated the .cdxml / .mol file on disk!) -> live reload!
      const newGraph = this.format === "mol"
        ? parseMolfileToGraph(updated, fileName)
        : parseCdxmlToGraph(updated, fileName);
      webviewPanel.webview.html = buildStudioWebviewHtml(this.context, webviewPanel.webview, newGraph, {
        isCustomEditor: true,
        format: this.format,
        fileName
      });
    });
    webviewPanel.onDidDispose(() => sub.dispose());
  }
}

/** Readonly 3D CustomEditor for *.pdb, *.cif, *.mmcif, *.xyz files. */
class Structure3DCustomViewerProvider {
  constructor(context) {
    this.context = context;
  }
  async openCustomDocument(uri) {
    return { uri, dispose: () => {} };
  }
  async resolveCustomEditor(document, webviewPanel) {
    webviewPanel.webview.options = { enableScripts: true };
    const fsPath = document.uri.fsPath;
    const ext = path.extname(fsPath).toLowerCase();
    let payload = build3DPayloadFromTarget(fsPath, this.context);
    if (!payload.mol_data && fs.existsSync(fsPath)) {
      const raw = fs.readFileSync(fsPath, "utf8");
      payload = {
        title: path.basename(fsPath),
        format: ext === ".cif" || ext === ".mmcif" ? "mmcif" : (ext === ".xyz" ? "xyz" : "pdb"),
        representation: ext === ".xyz" ? "ball-and-stick" : "cartoon",
        mol_data: raw.slice(0, 524288),
        scene: parse3DTextScene(raw, ext),
        is_macromolecule: ext !== ".xyz"
      };
    }
    webviewPanel.webview.html = build3DViewerHtml(this.context, payload);
  }
}

/** TreeView listing all chemical files in the workspace. */
class WorkspaceStructuresProvider {
  constructor() {
    this._emitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._emitter.event;
  }
  refresh() {
    this._emitter.fire(undefined);
  }
  getTreeItem(el) {
    return el;
  }
  async getChildren() {
    if (!vscode.workspace.workspaceFolders) return [];
    const uris = await vscode.workspace.findFiles(
      "**/*.{cdxml,mol,sdf,smi,smiles,pdb,cif,mmcif,xyz}",
      "**/{node_modules,.git,venv,.venv}/**",
      150
    );
    return uris
      .sort((a, b) => a.fsPath.localeCompare(b.fsPath))
      .map((u) => {
        const ext = path.extname(u.fsPath).toLowerCase();
        const is3d = [".pdb", ".cif", ".mmcif", ".xyz"].includes(ext);
        const item = new vscode.TreeItem(path.basename(u.fsPath), vscode.TreeItemCollapsibleState.None);
        item.resourceUri = u;
        item.description = vscode.workspace.asRelativePath(path.dirname(u.fsPath));
        item.iconPath = new vscode.ThemeIcon(is3d ? "globe" : "beaker");
        item.command = {
          command: "chemdraw.openTreeStructure",
          title: "Open Structure",
          arguments: [u]
        };
        return item;
      });
  }
}

/** Quick Actions TreeView in the ChemDraw Activity Bar sidebar. */
class QuickActionsProvider {
  getTreeItem(el) {
    return el;
  }
  getChildren() {
    const mk = (label, desc, icon, cmd) => {
      const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
      item.description = desc;
      item.iconPath = new vscode.ThemeIcon(icon);
      item.command = { command: cmd, title: label };
      return item;
    };
    return [
      mk("Open Full 2D Studio", "Ctrl+Alt+M · Beside Chat", "beaker", "chemdraw.openStudio"),
      mk("Open 3D Mol* Viewer", "Ctrl+Alt+3 · SMILES / PDB", "globe", "chemdraw.open3DViewer"),
      mk("Refresh Structures", "Scan workspace files", "refresh", "chemdraw.refreshWorkspace")
    ];
  }
}

/** HoverProvider turning SMILES literals in Markdown / code into 1-click 2D Studio & 3D Mol* links! */
const SMILES_TOKEN_RE = /(?<![A-Za-z0-9_/@+-])((?:[BCNOPSFIbcnops]|Cl|Br|\[[0-9A-Za-z@+\-:;!,]+\])(?:[BCNOPSFIbcnops0-9()=#@+\-/\\.%]|Cl|Br|\[[0-9A-Za-z@+\-:;!,]+\]){4,160})(?![A-Za-z0-9_])/;
const COMMON_WORDS = /^[A-Za-z]+$/;

class SmilesHoverProvider {
  provideHover(document, position) {
    if (!vscode.workspace.getConfiguration("chemdraw").get("enableSmilesHover", true)) return null;
    const range = document.getWordRangeAtPosition(position, SMILES_TOKEN_RE);
    if (!range) return null;
    const tok = document.getText(range);
    if (COMMON_WORDS.test(tok) && !/[0-9()=#[\]]/.test(tok) && !/^c1[a-z]+1$/.test(tok)) return null;

    const arg = encodeURIComponent(JSON.stringify([tok]));
    const md = new vscode.MarkdownString(
      `**ChemDraw Structure Detected** (\`${tok.slice(0, 48)}${tok.length > 48 ? "..." : ""}\`)\n\n` +
      `[$(beaker) Edit in 2D Studio](command:chemdraw.openSmilesIn2D?${arg}) &nbsp;|&nbsp; ` +
      `[$(globe) View 3D in Mol*](command:chemdraw.openSmilesIn3D?${arg})`
    );
    md.isTrusted = true;
    md.supportThemeIcons = true;
    return new vscode.Hover(md, range);
  }
}

function activate(context) {
  const sidebarProvider = new StudioSidebarProvider(context);
  const wsTree = new WorkspaceStructuresProvider();
  const quickTree = new QuickActionsProvider();

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("chemdraw.sidebarStudio", sidebarProvider, {
      webviewOptions: { retainContextWhenHidden: true }
    }),
    vscode.window.registerTreeDataProvider("chemdraw.workspaceStructures", wsTree),
    vscode.window.registerTreeDataProvider("chemdraw.quickActions", quickTree),
    vscode.window.registerCustomEditorProvider(
      "chemdraw.cdxmlEditor",
      new Structure2DCustomEditorProvider(context, "cdxml"),
      { webviewOptions: { retainContextWhenHidden: true } }
    ),
    vscode.window.registerCustomEditorProvider(
      "chemdraw.molEditor",
      new Structure2DCustomEditorProvider(context, "mol"),
      { webviewOptions: { retainContextWhenHidden: true } }
    ),
    vscode.window.registerCustomEditorProvider(
      "chemdraw.structure3dViewer",
      new Structure3DCustomViewerProvider(context),
      { webviewOptions: { retainContextWhenHidden: true } }
    ),
    vscode.languages.registerHoverProvider(
      ["markdown", "python", "json", "plaintext", "smiles", "yaml"],
      new SmilesHoverProvider()
    )
  );

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("chemdraw.openStudio", async () => {
      await open2DStudioPanel(context, vscode.ViewColumn.Beside, null, null);
    }),
    vscode.commands.registerCommand("chemdraw.openStudioHere", async () => {
      await open2DStudioPanel(context, vscode.ViewColumn.Active, null, null);
    }),
    vscode.commands.registerCommand("chemdraw.open3DViewer", async () => {
      const ed = vscode.window.activeTextEditor;
      const sel = ed && !ed.selection.isEmpty ? ed.document.getText(ed.selection).trim() : "";
      await open3DMolstarPanel(context, sel || undefined);
    }),
    vscode.commands.registerCommand("chemdraw.selectionTo2D", async () => {
      const ed = vscode.window.activeTextEditor;
      if (!ed || ed.selection.isEmpty) return;
      const sel = ed.document.getText(ed.selection).trim();
      if (sel) await open2DStudioPanel(context, vscode.ViewColumn.Beside, null, sel);
    }),
    vscode.commands.registerCommand("chemdraw.selectionTo3D", async () => {
      const ed = vscode.window.activeTextEditor;
      if (!ed || ed.selection.isEmpty) return;
      const sel = ed.document.getText(ed.selection).trim();
      if (sel) await open3DMolstarPanel(context, sel);
    }),
    vscode.commands.registerCommand("chemdraw.openSmilesIn2D", async (smi) => {
      if (smi) await open2DStudioPanel(context, vscode.ViewColumn.Beside, null, smi);
    }),
    vscode.commands.registerCommand("chemdraw.openSmilesIn3D", async (smi) => {
      if (smi) await open3DMolstarPanel(context, smi);
    }),
    vscode.commands.registerCommand("chemdraw.renderNativePng", async (uri) => {
      await renderNativeChemDrawPng(uri);
    }),
    vscode.commands.registerCommand("chemdraw.viewSource", async () => {
      const tab = vscode.window.tabGroups.activeTabGroup.activeTab;
      const uri = tab && tab.input && tab.input.uri;
      if (uri) {
        await vscode.commands.executeCommand("vscode.openWith", uri, "default", vscode.ViewColumn.Beside);
      }
    }),
    vscode.commands.registerCommand("chemdraw.refreshWorkspace", () => wsTree.refresh()),
    vscode.commands.registerCommand("chemdraw.openTreeStructure", async (uri) => {
      if (!uri) return;
      const ext = path.extname(uri.fsPath).toLowerCase();
      if (ext === ".cdxml") {
        await vscode.commands.executeCommand("vscode.openWith", uri, "chemdraw.cdxmlEditor");
      } else if (ext === ".mol" || ext === ".sdf") {
        await vscode.commands.executeCommand("vscode.openWith", uri, "chemdraw.molEditor");
      } else if ([".pdb", ".ent", ".cif", ".mmcif", ".xyz"].includes(ext)) {
        await vscode.commands.executeCommand("vscode.openWith", uri, "chemdraw.structure3dViewer");
      } else {
        const raw = fs.readFileSync(uri.fsPath, "utf8").trim().split(/\s+/)[0];
        await open2DStudioPanel(context, vscode.ViewColumn.Beside, null, raw);
      }
    }),
    vscode.commands.registerCommand("chemdraw.sendFileToAgent", async (uri) => {
      if (!uri) return;
      const rel = vscode.workspace.asRelativePath(uri.fsPath);
      await dispatchStructureToAgent({
        formula: path.basename(uri.fsPath),
        queryMode: "exact",
        cdxml: uri.fsPath.endsWith(".cdxml") ? fs.readFileSync(uri.fsPath, "utf8") : "",
        molfile: uri.fsPath.endsWith(".mol") ? fs.readFileSync(uri.fsPath, "utf8") : "",
        smiles: `file:${rel}`
      });
    })
  );

  // Watch workspace for agent-generated studio-live.cdxml / studio-live.json & chemical files
  const liveWatcher = vscode.workspace.createFileSystemWatcher("**/{studio-live.cdxml,*.cdxml,*.mol,*.pdb}");
  liveWatcher.onDidCreate((uri) => {
    wsTree.refresh();
    if (path.basename(uri.fsPath) === "studio-live.cdxml" &&
        vscode.workspace.getConfiguration("chemdraw").get("autoOpenOnAgentSync", true)) {
      const xml = fs.readFileSync(uri.fsPath, "utf8");
      const g = parseCdxmlToGraph(xml, "Agent Live Sync");
      open2DStudioPanel(context, vscode.ViewColumn.Beside, g, null);
    }
  });
  liveWatcher.onDidChange(() => wsTree.refresh());
  liveWatcher.onDidDelete(() => wsTree.refresh());
  context.subscriptions.push(liveWatcher);

  // Persistent Status Bar quick-launch button
  const sb = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 98);
  sb.text = "$(beaker) ChemDraw 2D";
  sb.tooltip = "Open Reaxys / SciFinder 2D Structure & Query Studio beside Chat (Ctrl+Alt+M)";
  sb.command = "chemdraw.openStudio";
  sb.show();
  context.subscriptions.push(sb);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
  parseCdxmlToGraph,
  parseMolfileToGraph,
  parse3DTextScene
};
