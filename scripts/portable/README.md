# scripts/portable — self-contained Stella launchers

## What this is

A portable bundle of Stella that keeps **all user data inside the bundle**
instead of under the system `%LOCALAPPDATA%`/`~/Library` location. Copy this
folder (plus the repo it came from) to a USB stick, a shared drive, or an
offline machine and Stella runs from there without touching the host outside
the bundle.

## Files

| File | Purpose |
|------|---------|
| `portable_stella.ps1` | Windows launcher (PowerShell). Use `pythonw` with `--windowed` for no console. |
| `portable_stella.sh`  | Linux/macOS launcher (bash). |
| `README.md`           | This file. |

## How it works

1. Resolves the `.venv` next to the script (created by `bootstrap.py` / `build.ps1`).
2. Sets `STELLA_USER_DATA_DIR` and `LOCALAPPDATA` to a `data/` folder inside
   the portable bundle — memories, settings, sessions, approvals, and audit logs
   all live there.
3. Sets the working directory to the repo root so relative imports resolve.
4. Runs `main.py`.

## Running

Windows (PowerShell):

```powershell
.\scripts\portable\portable_stella.ps1
.\scripts\portable\portable_stella.ps1 --windowed
```

Linux/macOS:

```bash
chmod +x scripts/portable/portable_stella.sh
./scripts/portable/portable_stella.sh
```

## Data location

All Stella user data lands under:

```
scripts/portable/data/          # or STELLA_DATA_DIR
  StellaAI/
    memories/
    config/
    sessions/
    logs/
```

Nothing is written to `%LOCALAPPDATA%\StellaAI` or `~/Library/...` unless you
point `STELLA_DATA_DIR` there.
