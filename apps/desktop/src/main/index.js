// apps/desktop/src/main/index.js — Electron main process
// Lifecycle, window management, IPC registration, OS adapters.
// Bridges to the Python backend via WebSocket.

const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("node:path");
const { spawn } = require("node:child_process");
const WebSocket = require("ws");

let mainWindow = null;
let pythonBackend = null;
let wsClient = null;
let wsResolve = null;
let wsReady = new Promise((resolve) => { wsResolve = resolve; });

const PYTHON_HOST = "127.0.0.1";
const PYTHON_PORT = 8765;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    startPythonBackend();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
    stopPythonBackend();
  });
}

function startPythonBackend() {
  // Spawn the Python backend (main.py)
  const python = process.env.PYTHON_EXECUTABLE || "python";
  pythonBackend = spawn(python, ["main.py", "--host", PYTHON_HOST, "--port", PYTHON_PORT.toString()], {
    cwd: path.join(__dirname, "../../../"),
    stdio: ["ignore", "pipe", "pipe"],
  });

  pythonBackend.stdout.on("data", (data) => {
    console.log(`[python] ${data.toString().trim()}`);
  });
  pythonBackend.stderr.on("data", (data) => {
    console.error(`[python err] ${data.toString().trim()}`);
  });
  pythonBackend.on("close", (code) => {
    console.log(`[python] exited with code ${code}`);
    pythonBackend = null;
  });

  // Connect WebSocket to Python backend after a short delay
  setTimeout(connectWebSocket, 2000);
}

function connectWebSocket() {
  if (wsClient) return;
  wsClient = new WebSocket(`ws://${PYTHON_HOST}:${PYTHON_PORT}`);

  wsClient.on("open", () => {
    console.log("[ws] connected to Python backend");
    wsResolve();
  });

  wsClient.on("message", (data) => {
    try {
      const msg = JSON.parse(data.toString());
      if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send("stella:event", msg);
      }
    } catch (e) {
      console.error("[ws] parse error:", e);
    }
  });

  wsClient.on("close", () => {
    console.log("[ws] disconnected");
    wsClient = null;
    // Retry connection
    setTimeout(connectWebSocket, 3000);
  });

  wsClient.on("error", (err) => {
    console.error("[ws] error:", err.message);
  });
}

function stopPythonBackend() {
  if (wsClient) {
    wsClient.close();
    wsClient = null;
  }
  if (pythonBackend) {
    pythonBackend.kill();
    pythonBackend = null;
  }
}

function sendToPython(message) {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify(message));
    return true;
  }
  return false;
}

// ── IPC handlers (renderer → Python backend) ──
ipcMain.handle("stella:ping", async () => {
  await wsReady;
  const msg = { id: Date.now(), endpoint: "backend.ping", payload: {} };
  return new Promise((resolve) => {
    const handler = (data) => {
      if (data.id === msg.id) {
        wsClient.removeListener("message", handler);
        resolve(data);
      }
    };
    wsClient.on("message", (raw) => {
      try { handler(JSON.parse(raw.toString())); } catch {}
    });
    sendToPython(msg);
  });
});

ipcMain.handle("stella:config:read", async () => {
  await wsReady;
  return rpc("config.read", {});
});

ipcMain.handle("stella:config:write", async (_, payload) => {
  await wsReady;
  return rpc("config.write", payload);
});

ipcMain.handle("stella:agent:run", async (_, payload) => {
  await wsReady;
  return rpc("agent.run", payload);
});

ipcMain.handle("stella:agent:tools", async () => {
  await wsReady;
  return rpc("agent.tool.declarations", {});
});

ipcMain.handle("stella:agent:skills", async () => {
  await wsReady;
  return rpc("agent.skill.list", {});
});

ipcMain.handle("stella:plugin:list", async () => {
  await wsReady;
  return rpc("plugin.list", {});
});

ipcMain.handle("stella:plugin:toggle", async (_, payload) => {
  await wsReady;
  return rpc("plugin.toggle", payload);
});

ipcMain.handle("stella:evolution:summary", async () => {
  await wsReady;
  return rpc("evolution.summary", {});
});

function rpc(endpoint, payload) {
  const msg = { id: Date.now(), endpoint, payload };
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      wsClient.removeListener("message", handler);
      reject(new Error("RPC timeout"));
    }, 30000);

    const handler = (raw) => {
      try {
        const data = JSON.parse(raw.toString());
        if (data.id === msg.id) {
          clearTimeout(timeout);
          wsClient.removeListener("message", handler);
          if (data.ok) resolve(data.payload);
          else reject(new Error(data.error?.message || "Unknown error"));
        }
      } catch {}
    };
    wsClient.on("message", handler);
    sendToPython(msg);
  });
}

// ── App lifecycle ──
app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopPythonBackend();
});
