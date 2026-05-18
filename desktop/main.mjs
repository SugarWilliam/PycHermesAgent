/**
 * Minimal desktop shell: probes the local sidecar /health and renders JSON in-window.
 * Start the Python sidecar first, or set PYC_HERMES_SIDECAR_CMD to spawn it (advanced).
 */
import http from "node:http";
import { spawn } from "node:child_process";
import { app, BrowserWindow, Menu, shell } from "electron";

const sidecarUrl = process.env.PYC_HERMES_SIDECAR_URL || "http://127.0.0.1:8765";
let sidecarChild = null;

function probeHealth(urlString) {
  return new Promise((resolve, reject) => {
    const u = new URL(new URL("/health", urlString).toString());
    const port = u.port ? Number(u.port) : u.protocol === "https:" ? 443 : 80;
    const req = http.request(
      {
        hostname: u.hostname,
        port,
        path: `${u.pathname}${u.search}`,
        method: "GET",
        timeout: 3000,
      },
      (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (c) => {
          body += c;
        });
        res.on("end", () => resolve({ status: res.statusCode ?? 0, body }));
      },
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy(new Error("timeout"));
    });
    req.end();
  });
}

function probeGet(urlString, pathname) {
  return new Promise((resolve, reject) => {
    const u = new URL(new URL(pathname, urlString).toString());
    const port = u.port ? Number(u.port) : u.protocol === "https:" ? 443 : 80;
    const req = http.request(
      {
        hostname: u.hostname,
        port,
        path: `${u.pathname}${u.search}`,
        method: "GET",
        timeout: 3000,
      },
      (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (c) => {
          body += c;
        });
        res.on("end", () => resolve({ status: res.statusCode ?? 0, body }));
      },
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy(new Error("timeout"));
    });
    req.end();
  });
}

function maybeSpawnSidecar() {
  const cmd = process.env.PYC_HERMES_SIDECAR_CMD;
  if (!cmd || sidecarChild) return;
  sidecarChild = spawn(cmd, { shell: true, stdio: "ignore", detached: false });
  sidecarChild.on("error", (err) => console.error("sidecar spawn error:", err));
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildApplicationMenu(runtimePaths, win) {
  const logsDir = runtimePaths?.logs_dir;
  const localData = runtimePaths?.local_data_dir;
  const fileSubmenu = [
    {
      label: "Open logs folder",
      enabled: Boolean(logsDir),
      click: () => {
        if (logsDir) void shell.openPath(logsDir);
      },
    },
    {
      label: "Open local data folder",
      enabled: Boolean(localData),
      click: () => {
        if (localData) void shell.openPath(localData);
      },
    },
  ];
  if (process.platform !== "darwin") {
    fileSubmenu.push({ type: "separator" }, { role: "quit" });
  }

  const viewSubmenu = [
    {
      label: "Refresh sidecar status",
      accelerator: "CmdOrCtrl+R",
      click: () => void loadSidecarStatusIntoWindow(win),
    },
  ];

  const template = [
    { label: "File", submenu: fileSubmenu },
    { label: "View", submenu: viewSubmenu },
  ];
  if (process.platform === "darwin") {
    template.unshift({
      label: app.name,
      submenu: [{ role: "about" }, { type: "separator" }, { role: "quit" }],
    });
  }
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function loadSidecarStatusIntoWindow(win) {
  if (!win || win.isDestroyed()) return;

  let runtimePaths = null;
  try {
    const { status, body } = await probeHealth(sidecarUrl);
    let summary = "";
    let pathsSummary = "";
    let pre = escapeHtml(body || "");
    if (body && (body.trim().startsWith("{") || body.trim().startsWith("["))) {
      try {
        const h = JSON.parse(body);
        const parts = [
          h.status_label && `status_label: ${h.status_label}`,
          h.degraded != null && `degraded: ${h.degraded}`,
          h.sidecar_api_version && `sidecar_api_version: ${h.sidecar_api_version}`,
          h.version && `package_version: ${h.version}`,
        ].filter(Boolean);
        if (parts.length) summary = `<ul>${parts.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>`;
      } catch {
        /* keep raw body in <pre> */
      }
    }
    try {
      const rp = await probeGet(sidecarUrl, "/runtime-paths");
      if (rp.status === 200 && rp.body && rp.body.trim().startsWith("{")) {
        runtimePaths = JSON.parse(rp.body);
        const p = runtimePaths;
        const show = ["logs_dir", "mrag_dir", "artifacts_dir", "models_dir"]
          .filter((k) => p[k])
          .map((k) => `${k}: ${p[k]}`);
        if (show.length)
          pathsSummary = `<h2>Runtime paths</h2><p><em>Use the application menu (<strong>File</strong>) to open logs or local data in the file manager.</em></p><ul>${show.map((line) => `<li><code>${escapeHtml(line)}</code></li>`).join("")}</ul>`;
      }
    } catch {
      /* optional */
    }
    buildApplicationMenu(runtimePaths, win);
    const title = status === 200 ? "PycHermesAgent — sidecar health" : "PycHermesAgent — sidecar error";
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title><style>body{font-family:system-ui,sans-serif;margin:1.5rem}code{background:#f4f4f4;padding:0.1em 0.3em;word-break:break-all}</style></head><body><h1>${title}</h1><p>HTTP ${status} from <code>${escapeHtml(sidecarUrl)}</code></p>${summary}<p><em>View → Refresh sidecar status (Ctrl+R / Cmd+R)</em></p>${pathsSummary}<h2>Raw health JSON</h2><pre>${pre}</pre></body></html>`;
    await win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  } catch (e) {
    if (win.isDestroyed()) return;
    buildApplicationMenu(null, win);
    const msg = escapeHtml(String(e));
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sidecar unreachable</title></head><body><h1>Sidecar unreachable</h1><p>Start <code>pyc-hermes-sidecar</code> or set <code>PYC_HERMES_SIDECAR_URL</code>.</p><p><em>View → Refresh sidecar status (Ctrl+R / Cmd+R)</em></p><pre>${msg}</pre><p>Target: <code>${escapeHtml(sidecarUrl)}</code></p></body></html>`;
    await win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  }
}

async function createWindow() {
  maybeSpawnSidecar();
  const win = new BrowserWindow({
    width: 960,
    height: 720,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  await loadSidecarStatusIntoWindow(win);
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("before-quit", () => {
  if (sidecarChild && !sidecarChild.killed) {
    try {
      sidecarChild.kill("SIGTERM");
    } catch {
      /* ignore */
    }
  }
});
