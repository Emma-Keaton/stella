// apps/desktop/src/preload/index.js — Preload bridge
// Exposes a narrow typed API to the renderer: window.stella
// Context isolation enabled — renderer cannot access Node/Electron directly.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("stella", {
  // RPC calls to Python backend
  ping: () => ipcRenderer.invoke("stella:ping"),
  configRead: () => ipcRenderer.invoke("stella:config:read"),
  configWrite: (payload) => ipcRenderer.invoke("stella:config:write", payload),
  agentRun: (payload) => ipcRenderer.invoke("stella:agent:run", payload),
  agentTools: () => ipcRenderer.invoke("stella:agent:tools"),
  agentSkills: () => ipcRenderer.invoke("stella:agent:skills"),
  pluginList: () => ipcRenderer.invoke("stella:plugin:list"),
  pluginToggle: (payload) => ipcRenderer.invoke("stella:plugin:toggle", payload),
  evolutionSummary: () => ipcRenderer.invoke("stella:evolution:summary"),

  // Events from Python backend
  onEvent: (callback) => {
    const handler = (_, event) => callback(event);
    ipcRenderer.on("stella:event", handler);
    return () => ipcRenderer.removeListener("stella:event", handler);
  },
});
