#!/usr/bin/env node
/**
 * Stella Unified Launcher
 * Spawns all three components:
 * 1. Python Backend (main.py) - WebSocket on port 8765
 * 2. Python Dashboard (server.py) - HTTP on port 8000
 * 3. Next.js Frontend (npm run dev) - HTTP on port 3000
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Use absolute paths - script is at E:/Projects/stella/start-all.js
const REPO_ROOT = path.resolve('E:/Projects/stella');
const DASHBOARD_DIR = path.join(REPO_ROOT, 'dashboard');

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
  if (name === 'python-dashboard' || name === 'python-backend') {
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
    'python-dashboard': colors.cyan,
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

  processes.push({ name, proc, color });
  return proc;
}

async function checkDependencies() {
  log('launcher', 'Checking dependencies...', colors.blue);
  
  // Check Python
  const pythonCmd = process.platform === 'win32' ? 'python.exe' : 'python3';
  
  // Check if main.py exists
  if (!fs.existsSync(path.join(REPO_ROOT, 'main.py'))) {
    log('launcher', 'main.py not found in repo root', colors.red);
    process.exit(1);
  }
  
  // Check if dashboard server.py exists
  if (!fs.existsSync(path.join(DASHBOARD_DIR, 'server.py'))) {
    log('launcher', 'dashboard/server.py not found', colors.red);
    process.exit(1);
  }
  
  // Check if package.json exists
  if (!fs.existsSync(path.join(DASHBOARD_DIR, 'package.json'))) {
    log('launcher', 'dashboard/package.json not found', colors.red);
    process.exit(1);
  }
  
  // Check node_modules
  if (!fs.existsSync(path.join(DASHBOARD_DIR, 'node_modules'))) {
    log('launcher', 'node_modules not found. Run "npm install" in dashboard/ first.', colors.yellow);
    log('launcher', 'Installing dependencies...', colors.blue);
    
    await new Promise((resolve, reject) => {
      const install = spawn('npm', ['install'], {
        cwd: DASHBOARD_DIR,
        stdio: 'inherit',
        shell: process.platform === 'win32',
      });
      install.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`npm install failed with code ${code}`));
      });
    });
  }
  
  log('launcher', 'All dependencies satisfied', colors.green);
}

function shutdown() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  
  log('launcher', 'Shutting down all processes...', colors.yellow);
  
  processes.forEach(({ name, proc }) => {
    if (proc && !proc.killed) {
      log('launcher', `Stopping ${name}...`, colors.dim);
      proc.kill('SIGTERM');
    }
  });
  
  setTimeout(() => {
    processes.forEach(({ name, proc }) => {
      if (proc && !proc.killed) {
        log('launcher', `Force killing ${name}...`, colors.red);
        proc.kill('SIGKILL');
      }
    });
    process.exit(0);
  }, 5000);
}

async function main() {
  console.log(`\n${colors.bright}${colors.cyan}
╔═══════════════════════════════════════════════════════════════╗\n║                    STELLA UNIFIED LAUNCHER                     ║\n║     Backend (8765) │ Dashboard (8000) │ Frontend (3000)       ║\n╚═══════════════════════════════════════════════════════════════╝\n${colors.reset}
`);

  const isDev = process.argv.includes('--dev') || process.env.STELLA_DEV === 'true';
  
  if (isDev) {
    process.env.STELLA_DEV_MODE = 'true';
    process.env.NODE_ENV = 'development';
    log('launcher', 'Running in DEVELOPMENT mode (Next.js dev server on 3000)', colors.yellow);
  } else {
    process.env.STELLA_DEV_MODE = 'false';
    process.env.NODE_ENV = 'production';
    process.env.NEXT_STATIC_EXPORT = 'true';
    log('launcher', 'Running in PRODUCTION mode (static export served by Python)', colors.green);
    
    const outDir = path.join(DASHBOARD_DIR, 'out');
    if (!fs.existsSync(outDir)) {
      log('launcher', 'Building Next.js static export...', colors.blue);
      await new Promise((resolve, reject) => {
        const build = spawn('npm', ['run', 'build'], {
          cwd: DASHBOARD_DIR,
          stdio: 'inherit',
          shell: process.platform === 'win32',
          env: { ...process.env, NODE_ENV: 'production', NEXT_STATIC_EXPORT: 'true' },
        });
        build.on('close', (code) => {
          if (code === 0) resolve();
          else reject(new Error('Next.js build failed with code ' + code));
        });
      });
      log('launcher', 'Next.js build complete', colors.green);
    }
  }

  await checkDependencies();
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  process.on('exit', shutdown);

  const pythonCmd = process.platform === 'win32' ? 'python.exe' : 'python3';
  spawnProcess('python-backend', pythonCmd, ['main.py'], { cwd: REPO_ROOT });
  await new Promise(resolve => setTimeout(resolve, 2000));

  const dashboardEnv = { STELLA_DEV_MODE: isDev ? 'true' : 'false' };
  spawnProcess('python-dashboard', pythonCmd, ['-m', 'dashboard.server'], {
    cwd: REPO_ROOT,
    env: dashboardEnv 
  });
  await new Promise(resolve => setTimeout(resolve, 1500));

  if (isDev) {
    spawnProcess('nextjs-frontend', 'npm', ['run', 'dev'], {
      cwd: DASHBOARD_DIR,
      env: { ...process.env, NODE_ENV: 'development' }
    });
    log('launcher', 'Frontend dev server:  http://localhost:3000', colors.green);
  } else {
    log('launcher', 'Frontend served by Python dashboard at http://localhost:8000', colors.green);
  }

  log('launcher', 'All services starting...', colors.green);
  log('launcher', 'Backend WebSocket:  ws://localhost:8765', colors.magenta);
  log('launcher', 'Dashboard HTTP:     http://localhost:8000', colors.cyan);
  log('launcher', 'Press Ctrl+C to stop all services', colors.dim);
}

main().catch(err => {
  log('launcher', `Fatal error: ${err.message}`, colors.red);
  shutdown();
  process.exit(1);
});
