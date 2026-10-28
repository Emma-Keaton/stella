"""core/security/tools.py - probe and run the external security toolchain.

Two rules:

1. **Probe before you promise.** `available()` reports, per tool, whether this
   machine actually has the binary - and on a phone (Termux) or a bare Linux box
   it frequently does not. A skill that says "run hashcat" without checking gets
   a `not-installed` record with the package name to install, never a traceback.

2. **Never a shell.** Every invocation goes through an argument list, so a
   filename containing a space or a semicolon cannot turn into a second command.
   Output is bounded, so a runaway tool cannot fill the log or the context.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Optional

MAX_OUTPUT_BYTES = 64_000
DEFAULT_TIMEOUT = 120

#: Tool -> the package that provides it per platform, so a missing binary
#: reports what to install rather than just "not found".
INSTALL_HINTS = {
    "aircrack-ng": {"linux": "apt install aircrack-ng",
                    "termux": "pkg install aircrack-ng",
                    "darwin": "brew install aircrack-ng",
                    "windows": "install Aircrack-ng for Windows"},
    "wifite": {"linux": "apt install wifite",
               "termux": "pkg install wifite"},
    "bettercap": {"linux": "apt install bettercap",
                  "termux": "pkg install bettercap",
                  "darwin": "brew install bettercap"},
    "hcxdumptool": {"linux": "apt install hcxdumptool"},
    "hcxpcapngtool": {"linux": "apt install hcxtools"},
    "hashcat": {"linux": "apt install hashcat",
                "termux": "pkg install hashcat",
                "darwin": "brew install hashcat",
                "windows": "download the hashcat Windows binaries"},
    "john": {"linux": "apt install john", "termux": "pkg install john",
             "darwin": "brew install john"},
    "reaver": {"linux": "apt install reaver"},
    "bully": {"linux": "apt install bully"},
    "airgeddon": {"linux": "git clone airgeddon or apt install airgeddon"},
    "iw": {"linux": "apt install iw", "termux": "pkg install iw"},
    "iwlist": {"linux": "apt install wireless-tools"},
    "tshark": {"linux": "apt install tshark", "termux": "pkg install tshark"},
}


def platform_tag() -> str:
    """The platform bucket used by the install hints: linux | termux | darwin | windows."""
    import sys

    if sys.platform.startswith("linux"):
        try:
            import os

            if os.environ.get("TERMUX_VERSION") or os.path.isdir("/data/data/com.termux"):
                return "termux"
        except Exception:
            pass
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    return "windows"


def available(tools: Optional[list] = None) -> dict:
    """Which of the named tools exist on this machine, and where."""
    names = list(tools or INSTALL_HINTS)
    found: dict = {}
    for name in names:
        path = shutil.which(name)
        if path:
            found[name] = {"present": True, "path": path}
        else:
            hint = INSTALL_HINTS.get(name, {}).get(platform_tag())
            found[name] = {"present": False, "path": None,
                           "install": hint or f"install {name} for {platform_tag()}"}
    return found


def describe_platform() -> dict:
    """What kind of surface this is, and what that means for wireless work."""
    tag = platform_tag()
    if tag == "termux":
        note = ("Termux gives you the Linux userspace tools (iw, aircrack-ng, hashcat) but the "
                "chipset still needs an external adapter in monitor mode - most Android Wi-Fi "
                "chips cannot do monitor mode at all.")
    elif tag == "linux":
        note = ("Linux can put a supported chipset into monitor mode; whether *this* adapter can "
                "is reported by the wireless_audit interfaces operation.")
    elif tag == "darwin":
        note = ("macOS has no monitor-mode support for the built-in adapter; capture needs a "
                "separate Linux box or a packet capture you already have.")
    else:
        note = ("Windows needs Npcap plus a driver that supports monitor mode (NPcap or a "
                "compatible Atheros/AW adapter); otherwise only cracking is possible.")
    return {"platform": tag, "note": note}


def run(argv: list, timeout: int = DEFAULT_TIMEOUT, max_bytes: int = MAX_OUTPUT_BYTES,
        cwd: Optional[str] = None) -> dict:
    """Run a tool with an argument list, bounded output and a hard timeout.

    Returns `{"ok": returncode == 0, ...}` plus the captured streams; never raises
    for a tool that fails, because a failed tool is a result to report.
    """
    if not argv:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "reason": "nothing to run"}
    started = time.time()
    try:
        process = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            cwd=cwd,
        )
    except FileNotFoundError:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "reason": f"{argv[0]} is not installed on this machine"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "timed_out": True,
                "reason": f"{argv[0]} did not finish within {timeout}s"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "reason": f"{argv[0]} could not be run: {type(exc).__name__}: {exc}"}

    def _cap(raw: bytes) -> tuple[str, bool]:
        data = (raw or b"")[:max_bytes]
        return data.decode("utf-8", errors="replace"), len(raw or b"") > max_bytes

    stdout, stdout_truncated = _cap(process.stdout)
    stderr, stderr_truncated = _cap(process.stderr)
    return {
        "ok": process.returncode == 0,
        "returncode": int(process.returncode),
        "stdout": stdout,
        "stderr": stderr,
        "truncated": stdout_truncated or stderr_truncated,
        "elapsed_s": round(time.time() - started, 2),
        "argv": [argv[0]] + ["***" if _is_secret(a) else a for a in argv[1:]],
    }


def _is_secret(value: str) -> bool:
    lowered = (value or "").lower()
    return lowered.startswith(("--passwords-file", "--identify")) and "=" in lowered


def run_background(argv: list, log_path: str) -> dict:
    """Start a long-running tool (a crack session) and return where it reports.

    A cracking session is `started`, never `done`: what it produces is read back
    from its outfile by the status operation.
    """
    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(log_path.rsplit("/", 1)[0]) if "/" in log_path else ".",
        )
    except FileNotFoundError:
        return {"ok": False, "outcome": "failed",
                "reason": f"{argv[0]} is not installed on this machine"}
    except Exception as exc:
        return {"ok": False, "outcome": "failed",
                "reason": f"{argv[0]} could not be started: {type(exc).__name__}: {exc}"}
    return {"ok": True, "outcome": "started", "pid": process.pid,
            "reason": f"{argv[0]} started as pid {process.pid}; check progress with the status operation."}
