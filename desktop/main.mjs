/**
 * Minimal desktop shell: probes the local sidecar /health and renders JSON in-window.
 * Start the Python sidecar first, or set PYC_HERMES_SIDECAR_CMD to spawn it (advanced).
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";
import { app, BrowserWindow, Menu, shell, dialog, clipboard } from "electron";

const DEFAULT_SIDECAR_URL = "http://127.0.0.1:8765";
/** Single-line base URL; lives next to Electron caches (see README). */
const SIDECAR_URL_FILE = "sidecar_url.txt";

let sidecarChild = null;

function getSidecarResolution() {
  const envRaw = process.env.PYC_HERMES_SIDECAR_URL?.trim();
  if (envRaw) {
    try {
      const url = new URL(envRaw).toString().replace(/\/$/, "");
      return { url, source: "environment variable PYC_HERMES_SIDECAR_URL" };
    } catch {
      return {
        url: DEFAULT_SIDECAR_URL,
        source: "default (invalid PYC_HERMES_SIDECAR_URL)",
      };
    }
  }
  try {
    const fp = path.join(app.getPath("userData"), SIDECAR_URL_FILE);
    if (fs.existsSync(fp)) {
      const text = fs.readFileSync(fp, "utf8");
      const line = text
        .split(/\r?\n/)
        .map((l) => l.trim())
        .find((l) => l && !l.startsWith("#"));
      if (line) {
        const url = new URL(line).toString().replace(/\/$/, "");
        return { url, source: `${SIDECAR_URL_FILE} in app user data folder` };
      }
    }
  } catch {
    /* malformed file or URL */
  }
  return { url: DEFAULT_SIDECAR_URL, source: "default" };
}

async function probeWithRetry(probeFn, { attempts = 5, baseMs = 400 } = {}) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await probeFn();
    } catch (e) {
      lastErr = e;
      if (i < attempts - 1) {
        await new Promise((r) => setTimeout(r, baseMs * (i + 1)));
      }
    }
  }
  throw lastErr;
}

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

function createSidecarUrlTemplateIfMissing(win) {
  const userDataDir = app.getPath("userData");
  const fp = path.join(userDataDir, SIDECAR_URL_FILE);
  if (fs.existsSync(fp)) {
    void dialog.showMessageBox(win, {
      type: "info",
      title: SIDECAR_URL_FILE,
      message: `${SIDECAR_URL_FILE} already exists.`,
      detail: fp,
    });
    return;
  }
  const content = [
    "# PycHermesAgent desktop — base URL for the Python sidecar HTTP API.",
    "# First non-comment line is used as the URL (trailing slash optional).",
    "# If PYC_HERMES_SIDECAR_URL is set in the environment, it overrides this file.",
    DEFAULT_SIDECAR_URL,
    "",
  ].join("\n");
  fs.mkdirSync(userDataDir, { recursive: true });
  fs.writeFileSync(fp, content, "utf8");
  void dialog.showMessageBox(win, {
    type: "info",
    title: SIDECAR_URL_FILE,
    message: `Created ${SIDECAR_URL_FILE} with the default local URL.`,
    detail: fp,
  });
  void loadSidecarStatusIntoWindow(win);
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
  const userDataDir = app.getPath("userData");
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
    {
      label: "Open desktop config folder",
      click: () => void shell.openPath(userDataDir),
    },
    {
      label: `Create ${SIDECAR_URL_FILE} template…`,
      click: () => createSidecarUrlTemplateIfMissing(win),
    },
    {
      label: "Copy resolved sidecar URL",
      accelerator: "CmdOrCtrl+Shift+C",
      click: () => {
        const { url } = getSidecarResolution();
        clipboard.writeText(url);
      },
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

  const { url: sidecarUrl, source: urlSource } = getSidecarResolution();
  let runtimePaths = null;
  try {
    const { status, body } = await probeWithRetry(() => probeHealth(sidecarUrl), {
      attempts: 5,
      baseMs: 450,
    });
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
          h.python_version && `python_version: ${h.python_version}`,
          h.platform && `platform: ${h.platform}`,
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
    const refreshedAt = new Date().toISOString();
    const sourceNote = `<p><small>URL source: <code>${escapeHtml(urlSource)}</code> — <em>View → Open desktop config folder</em> to edit <code>${escapeHtml(SIDECAR_URL_FILE)}</code> (optional; env wins).</small></p>`;
    const footer = `<p><small>Desktop view refreshed: <code>${escapeHtml(refreshedAt)}</code></small></p>`;
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title><style>body{font-family:system-ui,sans-serif;margin:1.5rem}code{background:#f4f4f4;padding:0.1em 0.3em;word-break:break-all}</style></head><body><h1>${title}</h1><p>HTTP ${status} from <code>${escapeHtml(sidecarUrl)}</code></p>${sourceNote}${summary}<p><em>View → Refresh sidecar status (Ctrl+R / Cmd+R)</em> — up to 5 connection attempts with backoff.</p>${pathsSummary}<h2>Raw health JSON</h2><pre>${pre}</pre>${footer}</body></html>`;
    await win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  } catch (e) {
    if (win.isDestroyed()) return;
    buildApplicationMenu(null, win);
    const msg = escapeHtml(String(e));
    const ud = escapeHtml(app.getPath("userData"));
    const refreshedAt = new Date().toISOString();
    const footer = `<p><small>Desktop view refreshed: <code>${escapeHtml(refreshedAt)}</code></small></p>`;
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sidecar unreachable</title></head><body><h1>Sidecar unreachable</h1><p>Start <code>pyc-hermes-sidecar</code>, set <code>PYC_HERMES_SIDECAR_URL</code>, or create <code>${escapeHtml(SIDECAR_URL_FILE)}</code> under <code>${ud}</code>.</p><p><small>URL tried: <code>${escapeHtml(sidecarUrl)}</code> (${escapeHtml(urlSource)})</small></p><p><em>View → Refresh</em> retries with backoff; <em>View → Open desktop config folder</em> for <code>${escapeHtml(SIDECAR_URL_FILE)}</code>.</p><pre>${msg}</pre>${footer}</body></html>`;
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
