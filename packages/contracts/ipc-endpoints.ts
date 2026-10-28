// Single source of truth for IPC endpoint list — enforced by type system.
// Renderer cannot import src/main or src/backend.
// Preload bridge contains no business rules — maps typed calls to IPC channels.

export const IPC_GROUP_PATHS = {
  app: ["app"],
  providers: ["providers"],
  agent: ["agent"],
  servers: ["servers"],
  browser: ["browser"],
  skills: ["skills"],
  memory: ["memory"],
  actions: ["actions"],
  plugins: ["plugins"],
} as const;

export type IpcGroup = keyof typeof IPC_GROUP_PATHS;
