#!/usr/bin/env node
/**
 * Stella Unified Launcher
 * Starts all Stella endpoints together at once and stays alive
 * until the user shuts down (Ctrl+C).
 *
 * Endpoints:
 * 1. Python Backend (main.py) - WebSocket on port 8765
 * 2. Next.js Frontend (npm run dev) - HTTP on port 3000
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Absolute paths
const REPO_ROOT = path.resolve('E:/Projects/stella');
const FRONTEND_DIR = path.join(REPO_ROOT, 'frontend');

const processes = [];
let isShuttingDown = false;

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(component, message, color = colors.reset) {
  const timestamp = new Date().toLocaleTimeString();
  const prefix = `${colors.dim}[${timestamp}]${colors.reset} ${color}${component}${colors.reset}`;
  console.log(`${prefix} ${message}`);
}

function spawnProcess(name, command, args, options = {}) {
  const env = { ...process.env, ...options.env };

  // Set PYTHONPATH for Python processes to include repo root
  if (name === 'python-backend') {
    env.PYTHONPATH = REPO_ROOT + (env.PYTHONPATH ? path.delimiter + env.PYTHONPATH : '');
  }

  const proc = spawn(command, args, {
    cwd: options.cwd || REPO_ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: env,
    shell: process.platform === 'win32',
    windowsHide: true,
  });

  const color = {
    'python-backend': colors.magenta,
    'nextjs-frontend': colors.green,
  }[name] || colors.yellow;

  proc.stdout?.on('data', (data) => {
    const lines = data.toString().trim().split('\n');
    lines.forEach(line => {
      if (line.trim()) log(name, line, color);
    });
  });

  proc.stderr?.on('data', (data) => {
    const lines = data.toString().trim().split('\n');
    lines.forEach(line => {
      if (line.trim()) log(name, line, color);
    });
  });

  proc.on('error', (err) => {
    log(name, `Failed to start: ${err.message}`, colors.red);
  });

  proc.on('close', (code) => {
    if (!isShuttingDown) {
      log(name, `Exited with code ${code}`, colors.red);
    }
  });

  processes.push({ name, proc });
  return proc;
}

function shutdown() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  log('launcher', 'Shutting down all Stella endpoints...', colors.yellow);

  processes.forEach(({ name, proc }) => {
    if (proc && !proc.killed) {
      log('launcher', `Stopping ${name}...`, colors.dim);
      try { proc.kill('SIGTERM'); } catch (e) {}
    }
  });

  // Force kill any still-alive processes after a grace period
  setTimeout(() => {
    processes.forEach(({ name, proc }) => {
      if (proc && !proc.killed) {
        log('launcher', `Force killing ${name}...`, colors.red);
        try { proc.kill('SIGKILL'); } catch (e) {}
      }
    });
    process.exit(0);
  }, 5000);
}

async function checkDependencies() {
  log('launcher', 'Checking dependencies...', colors.blue);

  const pythonCmd = process.platform === 'win32' ? 'python.exe' : 'python3';

  if (!fs.existsSync(path.join(REPO_ROOT, 'main.py'))) {
    log('launcher', 'main.py not found in repo root', colors.red);
    process.exit(1);
  }

  if (!fs.existsSync(path.join(FRONTEND_DIR, 'package.json'))) {
    log('launcher', 'frontend/package.json not found', colors.red);
    process.exit(1);
  }
}

async function main() {
  console.log(`\n${colors.bright}${colors.cyan}
╔═══════════════════════════════════════════════════════════════╗
║                    STELLA UNIFIED LAUNCHER                     ║
║     Backend (8765) │ Frontend (3000)                           ║
╚═══════════════════════════════════════════════════════════════╝
${colors.reset}
`);

  const isDev = process.argv.includes('--dev') || process.env.STELLA_DEV === 'true';
  if (isDev) {
    process.env.STELLA_DEV_MODE = 'true';
    process.env.NODE_ENV = 'development';
    log('launcher', 'Running in DEVELOPMENT mode', colors.yellow);
  } else {
    process.env.STELLA_DEV_MODE = 'false';
    process.env.NODE_ENV = 'production';
    log('launcher', 'Running in PRODUCTION mode', colors.green);
  }

  await checkDependencies();
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  const pythonCmd = process.platform === 'win32' ? 'python.exe' : 'python3';

  // ── Start ALL endpoints together at once (no artificial delays) ──
  spawnProcess('python-backend', pythonCmd, ['main.py'], { cwd: REPO_ROOT });
  log('launcher', 'Backend WebSocket:  ws://localhost:8765', colors.magenta);

  spawnProcess('nextjs-frontend', 'npm', ['run', 'dev'], {
    cwd: FRONTEND_DIR,
    env: { ...process.env, NODE_ENV: 'development', BROWSER: 'none' },
  });
  log('launcher', 'Frontend dev server: http://localhost:3000', colors.green);

  log('launcher', 'All Stella endpoints started.', colors.green);
  log('launcher', 'Press Ctrl+C to stop all services and shut down.', colors.dim);

  // Keep the process alive indefinitely until the user shuts down.
  // Child process stdio pipes keep the Node event loop alive.
}

main().catch(err => {
  log('launcher', `Fatal error: ${err.message}`, colors.red);
  shutdown();
  process.exit(1);
});
