/* VS Code Webview Bridge for ChemDraw Reaxys/SciFinder 2D Studio & Custom Editors */
(() => {
  const vscode = typeof acquireVsCodeApi === "function" ? acquireVsCodeApi() : null;
  if (!vscode) return;

  const boot = window.__CHEMDRAW_VSCODE_BOOT__ || {};
  const root = document.getElementById("cdx-studio-root");

  // Responsive layout refinements for narrow sidebar WebviewViews (< 500px wide) & Custom Editor save badge
  const extraStyle = document.createElement("style");
  extraStyle.textContent = `
    html, body { margin: 0; padding: 0; background: transparent; overflow-x: hidden; }
    #cdx-studio-root { border-radius: 0; border-left: 0; border-right: 0; }
    @media (max-width: 520px) {
      #cdx-studio-root .cdx-work { grid-template-columns: 34px 1fr 38px; min-height: 296px; }
      #cdx-studio-root #cdx-svg { height: 296px; }
      #cdx-studio-root .cdx-smi-chip { max-width: 130px; }
      #cdx-studio-root .cdx-toast { font-size: 10px; max-width: 78%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    }
    #cdx-vscode-docbar {
      display: flex; align-items: center; justify-content: space-between; gap: 6px;
      padding: 4px 8px; background: var(--cdx-bar); border-bottom: 1px solid var(--cdx-border);
      font-size: 11.5px;
    }
    #cdx-vscode-docbar .cdx-doc-pill {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 11px; opacity: 0.85; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
  `;
  document.head.appendChild(extraStyle);

  // Read live editor DOM values cleanly
  function collectSnapshot() {
    const formulaEl = document.getElementById("cdx-m-formula");
    const mwEl = document.getElementById("cdx-m-mw");
    const exactEl = document.getElementById("cdx-m-exact");
    const smiEl = document.getElementById("cdx-m-smi");
    const qModeEl = document.getElementById("cdx-query-mode");
    const styleEl = document.getElementById("cdx-style-sel");
    return {
      formula: formulaEl ? formulaEl.textContent : "",
      mw: mwEl ? mwEl.textContent : "",
      exactMass: exactEl ? exactEl.textContent : "",
      smiles: smiEl && smiEl.textContent !== "Empty canvas" ? smiEl.textContent : "",
      queryMode: qModeEl ? qModeEl.value : "exact",
      style: styleEl ? styleEl.value : "acs1996",
      graph: window.__cdxLastState ? window.__cdxLastState.graph : null
    };
  }

  // Intercept Blob downloads inside sandboxed Electron Webview -> route to native VS Code Save Dialog!
  const origCreateObjectURL = URL.createObjectURL.bind(URL);
  let lastBlobRecord = null;
  URL.createObjectURL = function (blob) {
    lastBlobRecord = blob;
    return origCreateObjectURL(blob);
  };
  document.addEventListener("click", (ev) => {
    const a = ev.target && ev.target.closest ? ev.target.closest("a[download]") : null;
    if (a && lastBlobRecord) {
      ev.preventDefault();
      const filename = a.getAttribute("download") || "structure.cdxml";
      lastBlobRecord.text().then((content) => {
        vscode.postMessage({ type: "saveFileDialog", filename, content });
      });
    }
  }, true);

  // Intercept window.openai-style bridge or MCP postMessage calls emitted by ui_apps.py
  window.openai = {
    widgetState: vscode.getState() || null,
    setWidgetState: async (st) => {
      vscode.setState(st);
      window.__cdxLastState = st && st.privateContent ? st.privateContent : null;
      if (boot.isCustomEditor) {
        vscode.postMessage({
          type: "dirtyState",
          modelContent: st ? st.modelContent : null,
          graph: window.__cdxLastState ? window.__cdxLastState.graph : null
        });
      }
    },
    sendFollowUpMessage: async ({ prompt, title }) => {
      // Trigger export extraction for exact CDXML + Molfile V2000 via hidden export helper
      const snap = collectSnapshot();
      const payloads = extractFormatsFromEditor();
      vscode.postMessage({
        type: "transferToAgent",
        prompt,
        title: title || "Transfer Structure to Agent",
        ...snap,
        ...payloads
      });
    }
  };

  function extractFormatsFromEditor() {
    let cdxml = "", molfile = "", smarts = "", smiles = "";
    try {
      const expBtn = document.getElementById("cdx-act-export");
      const backdrop = document.getElementById("cdx-backdrop");
      const modal = document.getElementById("cdx-modal");
      if (expBtn && backdrop && modal) {
        const wasHidden = backdrop.hidden;
        expBtn.click();
        const readFmt = (fmt) => {
          const b = modal.querySelector(`[data-ef="${fmt}"]`);
          if (b) b.click();
          const ta = document.getElementById("cdx-exp-txt");
          return ta ? ta.value : "";
        };
        molfile = readFmt("mol");
        cdxml = readFmt("cdxml");
        smiles = readFmt("smiles");
        smarts = readFmt("smarts");
        if (wasHidden) backdrop.hidden = true;
      }
    } catch (_e) {}
    return { cdxml, molfile, smarts, smiles };
  }

  // Wire 3D Mol* button directly to VS Code 3D Viewer Panel!
  const btn3d = document.getElementById("cdx-btn-3d");
  if (btn3d) {
    btn3d.addEventListener("click", (ev) => {
      ev.stopImmediatePropagation();
      const fmts = extractFormatsFromEditor();
      const smi = fmts.smiles || collectSnapshot().smiles;
      vscode.postMessage({ type: "open3D", smiles: smi, molfile: fmts.molfile });
    }, true);
  }

  // Custom Editor top document bar (Save back to .cdxml / .mol + Render 300 DPI PNG)
  if (boot.isCustomEditor && root) {
    const bar = document.createElement("div");
    bar.id = "cdx-vscode-docbar";
    bar.innerHTML = `
      <span class="cdx-doc-pill" id="cdx-doc-label">Editing: ${boot.fileName || "Document"}</span>
      <div style="display:flex;gap:5px;align-items:center">
        ${boot.format === "cdxml" ? '<button type="button" class="cdx-ibtn" id="cdx-vs-png" style="border:1px solid var(--cdx-border);padding:0 8px">300 DPI PNG</button>' : ""}
        <button type="button" class="cdx-cta" id="cdx-vs-save" title="Write changes to file (Ctrl+S)">Save to ${boot.format === "mol" ? ".mol" : ".cdxml"}</button>
      </div>
    `;
    root.insertBefore(bar, root.firstChild);

    const saveNow = () => {
      const fmts = extractFormatsFromEditor();
      const content = boot.format === "mol" ? fmts.molfile : fmts.cdxml;
      if (content) {
        vscode.postMessage({ type: "saveCustomDocument", format: boot.format, content, smiles: fmts.smiles });
        const toast = document.getElementById("cdx-toast");
        if (toast) toast.textContent = "Saved to " + (boot.fileName || "document");
      }
    };
    document.getElementById("cdx-vs-save").addEventListener("click", saveNow);
    const pngBtn = document.getElementById("cdx-vs-png");
    if (pngBtn) {
      pngBtn.addEventListener("click", () => {
        saveNow();
        vscode.postMessage({ type: "renderNativePng" });
      });
    }
    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") {
        ev.preventDefault();
        saveNow();
      }
    });
  }

  // Listen for messages pushed from the VS Code Extension Host (e.g. external file updates, load SMILES/MOL)
  window.addEventListener("message", (ev) => {
    const msg = ev.data;
    if (!msg || typeof msg !== "object") return;
    if (msg.type === "loadTextStructure" && msg.text) {
      const impBtn = document.getElementById("cdx-act-import");
      const backdrop = document.getElementById("cdx-backdrop");
      if (impBtn && backdrop) {
        impBtn.click();
        const ta = document.getElementById("cdx-imp-txt");
        const go = document.getElementById("cdx-imp-go");
        if (ta && go) {
          ta.value = msg.text;
          go.click();
        }
        backdrop.hidden = true;
      }
    }
  });

  vscode.postMessage({ type: "ready" });
})();
