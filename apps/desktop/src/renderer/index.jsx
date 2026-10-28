// apps/desktop/src/renderer/index.jsx — SolidJS renderer entry
// Minimal starter UI that connects to the Python backend via window.stella

import { render } from "solid-js/web";
import { createSignal, onMount, onCleanup } from "solid-js";

function App() {
  const [status, setStatus] = createStatus("disconnected");
  const [config, setConfig] = createSignal(null);
  const [tools, setTools] = createSignal([]);
  const [skills, setSkills] = createSignal([]);
  const [log, setLog] = createSignal([]);

  onMount(async () => {
    addLog("Stella frontend initializing...");
    try {
      await window.stella.ping();
      setStatus("connected");
      addLog("Connected to Stella backend");

      // Load config
      const cfg = await window.stella.configRead();
      setConfig(cfg);
      addLog("Configuration loaded");

      // Load tools
      const t = await window.stella.agentTools();
      setTools(Array.isArray(t) ? t : []);
      addLog(`Loaded ${tools().length} tool declarations`);

      // Load skills
      const s = await window.stella.agentSkills();
      setSkills(Array.isArray(s) ? s : []);
      addLog(`Loaded ${skills().length} skills`);
    } catch (err) {
      setStatus("error");
      addLog(`Error: ${err.message}`);
    }
  });

  // Listen for backend events
  const unsubscribe = window.stella.onEvent((event) => {
    addLog(`[${event.endpoint}] ${JSON.stringify(event.payload).slice(0, 100)}`);
    if (event.endpoint === "event.state") {
      setStatus(event.payload?.connected ? "connected" : "disconnected");
    }
  });
  onCleanup(unsubscribe);

  async function sendMessage(text) {
    addLog(`> ${text}`);
    try {
      const result = await window.stella.agentRun({ text, context: {} });
      addLog(`< ${result.result || JSON.stringify(result)}`);
      if (result.honesty) addLog(`[honesty] ${result.honesty}`);
    } catch (err) {
      addLog(`< Error: ${err.message}`);
    }
  }

  function createStatus(initial) {
    const s = createSignal(initial);
    return s;
  }

  function addLog(msg) {
    const now = new Date().toLocaleTimeString();
    setLog((prev) => [...prev.slice(-49), `[${now}] ${msg}`]);
  }

  return (
    <div style={{ padding: "24px", height: "100%", display: "flex", flexDirection: "column", gap: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: status() === "connected" ? "#22c55e" : status() === "error" ? "#ef4444" : "#f59e0b",
          }}
        />
        <span style={{ fontWeight: "600", fontSize: "18px" }}>Stella</span>
        <span
          style={{
            fontSize: "12px",
            padding: "2px 8px",
            borderRadius: "12px",
            background: status() === "connected" ? "#166534" : status() === "error" ? "#7f1d1d" : "#92400e",
            color: "#fff",
          }}
        >
          {status()}
        </span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "16px", background: "#111114", borderRadius: "8px", border: "1px solid #222", fontFamily: "monospace", fontSize: "13px", lineHeight: "1.5" }}>
        {log().map((line, i) => (
          <div key={i} style={{ marginBottom: "6px", whiteSpace: "pre-wrap" }}>{line}</div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "8px" }}>
        <input
          type="text"
          placeholder="Type a message to Stella..."
          onKeyDown={(e) => {
            if (e.key === "Enter") sendMessage(e.currentTarget.value);
          }}
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: "6px",
            border: "1px solid #333",
            background: "#0a0a0c",
            color: "#e8e8ea",
            fontSize: "14px",
          }}
        />
        <button
          onClick={() => sendMessage("Hello Stella!")}
          disabled={status() !== "connected"}
          style={{
            padding: "10px 20px",
            borderRadius: "6px",
            border: "none",
            background: status() === "connected" ? "#3b82f6" : "#444",
            color: "#fff",
            fontWeight: "600",
            cursor: status() === "connected" ? "pointer" : "not-allowed",
          }}
        >
          Send
        </button>
      </div>

      <div style={{ fontSize: "11px", color: "#666", marginTop: "auto" }}>
        Stella v2.0.0 · Electron + SolidJS · Python backend
      </div>
    </div>
  );
}

render(() => <App />, document.getElementById("root"));
