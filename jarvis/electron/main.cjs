/**
 * JARVIS desktop shell for the local Open WebUI fork.
 *
 * - Starts run.bat (hidden) if the server is not already running, shows a
 *   small splash, then loads http://localhost:<PORT> unchanged.
 * - Tray icon + Ctrl+Shift+J global hotkey to show/hide JARVIS.
 * - Ctrl+Shift+H (or any link to the Barehands stage) opens the Barehands
 *   hand-tracked stage fullscreen; Esc closes it.
 * - Grants camera/microphone to the local pages only (voice + Barehands).
 * Ported from JoshTXWC/JARVIS electron/main.cjs, trimmed to wrap Open WebUI.
 */
const { app, BrowserWindow, Menu, Tray, globalShortcut, nativeImage, session, shell } = require("electron");
const { spawn, execFile } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const HOME = process.env.JARVIS_HOME ? path.resolve(process.env.JARVIS_HOME) : path.resolve(__dirname, "..", "..");
const PORT = Number(process.env.PORT || readEnvPort() || 8080);
const UI_URL = `http://localhost:${PORT}`;
const BH_PORT = Number(process.env.BAREHANDS_PORT || 8794);
const BH_URL = `http://127.0.0.1:${BH_PORT}/stage.html`;
const ICON = path.join(HOME, "static", "static", "favicon.png");
const LOCAL_ORIGINS = [`http://localhost:${PORT}`, `http://127.0.0.1:${PORT}`, `http://127.0.0.1:${BH_PORT}`, `http://localhost:${BH_PORT}`];

let mainWindow = null;
let bhWindow = null;
let tray = null;
let backend = null;
let bhProc = null;
let quitting = false;

function readEnvPort() {
  try {
    const txt = fs.readFileSync(path.join(HOME, "jarvis.env"), "utf8");
    const m = txt.match(/^\s*PORT\s*=\s*(\d+)\s*$/m);
    return m ? m[1] : null;
  } catch { return null; }
}

function isLocal(url) {
  return LOCAL_ORIGINS.some((o) => (url || "").startsWith(o));
}

function ping(url, timeout = 1500) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout }, (res) => { res.resume(); resolve(res.statusCode < 500); });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

function portOpen(port) {
  return new Promise((resolve) => {
    const s = net.connect({ host: "127.0.0.1", port }, () => { s.end(); resolve(true); });
    s.on("error", () => resolve(false));
    s.setTimeout(600, () => { s.destroy(); resolve(false); });
  });
}

async function waitFor(fn, ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await fn()) return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function startBackend() {
  const bat = path.join(HOME, "run.bat");
  if (process.platform !== "win32" || !fs.existsSync(bat)) return;
  backend = spawn("cmd.exe", ["/d", "/c", bat, "--no-browser"], {
    cwd: HOME, windowsHide: true, stdio: "ignore", env: { ...process.env, JARVIS_HOME: HOME },
  });
  backend.on("exit", (code) => {
    backend = null;
    if (!quitting) console.log(`[jarvis] backend exited (${code})`);
  });
}

function stopBackend() {
  if (backend && process.platform === "win32") {
    try { execFile("taskkill", ["/pid", String(backend.pid), "/T", "/F"]); } catch { /* noop */ }
  }
  if (bhProc) { try { bhProc.kill(); } catch { /* noop */ } }
}

const SPLASH = `data:text/html;charset=utf-8,${encodeURIComponent(`<!doctype html><html><body style="margin:0;height:100vh;display:flex;
align-items:center;justify-content:center;background:#0b0f14;color:#9fe7ff;font:16px system-ui">
<div style="text-align:center"><div style="font-size:28px;letter-spacing:6px">J.A.R.V.I.S.</div>
<div style="opacity:.7;margin-top:12px">Starting Open WebUI and local models&hellip;</div>
<div style="opacity:.45;margin-top:6px;font-size:13px">First launch can take a minute.</div></div></body></html>`)}`;

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 860, minWidth: 720, minHeight: 500,
    title: "JARVIS", backgroundColor: "#0b0f14", autoHideMenuBar: true,
    icon: fs.existsSync(ICON) ? ICON : undefined,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  mainWindow.loadURL(SPLASH);
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.includes(`:${BH_PORT}`)) { openBarehands(); return { action: "deny" }; }
    if (isLocal(url)) return { action: "allow" };
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (e, url) => {
    if (url.includes(`:${BH_PORT}`)) { e.preventDefault(); openBarehands(); }
    else if (!isLocal(url) && /^https?:/i.test(url)) { e.preventDefault(); shell.openExternal(url); }
  });
  mainWindow.on("close", (e) => {
    if (!quitting && tray) { e.preventDefault(); mainWindow.hide(); }
  });
}

async function startBarehandsServer() {
  if (await portOpen(BH_PORT)) return true;
  const dir = process.env.JARVIS_BAREHANDS_DIR || path.join(HOME, "integrations", "barehands");
  const py = [path.join(HOME, ".venv", "Scripts", "python.exe"), path.join(HOME, ".venv", "bin", "python")]
    .find((p) => fs.existsSync(p)) || "python";
  if (!fs.existsSync(path.join(dir, "server.py"))) return false;
  bhProc = spawn(py, ["server.py"], { cwd: dir, windowsHide: true, stdio: "ignore",
    env: { ...process.env, PYTHONUTF8: "1" } });
  bhProc.on("exit", () => { bhProc = null; });
  return waitFor(() => portOpen(BH_PORT), 20000);
}

async function openBarehands() {
  if (bhWindow && !bhWindow.isDestroyed()) { bhWindow.show(); bhWindow.focus(); return; }
  const ok = await startBarehandsServer();
  if (!ok) {
    if (mainWindow) mainWindow.webContents.executeJavaScript(
      "alert('Barehands is not installed. Run setup.bat again (it copies or clones it into integrations\\\\barehands).')");
    return;
  }
  bhWindow = new BrowserWindow({
    fullscreen: true, frame: false, backgroundColor: "#000000", title: "Barehands",
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  bhWindow.loadURL(BH_URL);
  bhWindow.webContents.on("before-input-event", (e, input) => {
    if (input.type === "keyDown" && input.key === "Escape") { e.preventDefault(); bhWindow.close(); }
  });
  bhWindow.on("closed", () => { bhWindow = null; });
}

function toggleMain() {
  if (!mainWindow) return;
  if (mainWindow.isVisible() && mainWindow.isFocused()) mainWindow.hide();
  else { mainWindow.show(); mainWindow.focus(); }
}

function createTray() {
  try {
    const img = fs.existsSync(ICON) ? nativeImage.createFromPath(ICON).resize({ width: 16, height: 16 }) : nativeImage.createEmpty();
    tray = new Tray(img);
    tray.setToolTip("JARVIS");
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: "Show / hide JARVIS  (Ctrl+Shift+J)", click: toggleMain },
      { label: "Barehands stage  (Ctrl+Shift+H)", click: openBarehands },
      { label: "Open in browser", click: () => shell.openExternal(UI_URL) },
      { type: "separator" },
      { label: "Quit JARVIS", click: () => { quitting = true; app.quit(); } },
    ]));
    tray.on("click", toggleMain);
  } catch (e) {
    console.warn("[jarvis] tray unavailable", e);
    tray = null;
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } });

  app.whenReady().then(async () => {
    const allow = new Set(["media", "audioCapture", "videoCapture", "microphone", "camera", "notifications",
      "clipboard-read", "clipboard-sanitized-write", "fullscreen"]);
    session.defaultSession.setPermissionRequestHandler((wc, permission, cb) => {
      cb(allow.has(permission) && isLocal(wc.getURL()));
    });
    session.defaultSession.setPermissionCheckHandler((wc, permission, origin) => allow.has(permission) && isLocal(origin || ""));

    createMainWindow();
    createTray();
    globalShortcut.register("CommandOrControl+Shift+J", toggleMain);
    globalShortcut.register("CommandOrControl+Shift+H", openBarehands);

    const health = () => ping(`${UI_URL}/health`);
    if (!(await health())) startBackend();
    if (await waitFor(health, 15 * 60 * 1000)) {
      mainWindow.webContents.once("did-finish-load", () => console.log(`[jarvis] UI loaded: ${mainWindow.webContents.getTitle()} (${UI_URL})`));
      mainWindow.loadURL(UI_URL);
    } else {
      mainWindow.loadURL(`data:text/html,${encodeURIComponent(
        "<body style='background:#0b0f14;color:#fff;font:16px system-ui;padding:40px'>JARVIS did not start. " +
        "Run run.bat in a terminal to see the error, or run setup.bat again.</body>")}`);
    }
  });

  app.on("before-quit", () => { quitting = true; stopBackend(); });
  app.on("will-quit", () => globalShortcut.unregisterAll());
  app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
}
