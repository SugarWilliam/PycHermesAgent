/**
 * Minimal desktop shell: probes the local sidecar /health and renders JSON in-window.
 * Start the Python sidecar first, or set PYC_HERMES_SIDECAR_CMD to spawn it (advanced).
 */
import http from "node:http";
import { spawn } from "node:child_process";
import { app, BrowserWindow } from "electron";

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

async function createWindow() {
  maybeSpawnSidecar();
  const win = new BrowserWindow({
    width: 960,
    height: 720,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });

  try {
    const { status, body } = await probeHealth(sidecarUrl);
    const pre = escapeHtml(body || "");
    const title = status === 200 ? "PycHermesAgent — sidecar health" : "PycHermesAgent — sidecar error";
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title></head><body><h1>${title}</h1><p>HTTP ${status} from <code>${escapeHtml(sidecarUrl)}</code></p><pre>${pre}</pre></body></html>`;
    await win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  } catch (e) {
    const msg = escapeHtml(String(e));
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sidecar unreachable</title></head><body><h1>Sidecar unreachable</h1><p>Start <code>pyc-hermes-sidecar</code> or set <code>PYC_HERMES_SIDECAR_URL</code>.</p><pre>${msg}</pre><p>Target: <code>${escapeHtml(sidecarUrl)}</code></p></body></html>`;
    await win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  }
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
