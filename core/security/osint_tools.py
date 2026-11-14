"""core/security/osint_tools.py - Security tool wrappers for Stella backend."""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Optional

MAX_OUTPUT_BYTES = 64_000
DEFAULT_TIMEOUT = 120

INSTALL_HINTS = {
    "nmap": {"linux": "apt install nmap", "termux": "pkg install nmap", "darwin": "brew install nmap"},
    "dracnmap": {"linux": "git clone https://github.com/Screetsec/Dracnmap.git", "termux": "git clone https://github.com/Screetsec/Dracnmap.git"},
    "xerosploit": {"linux": "git clone https://github.com/LionSec/xerosploit.git", "termux": "git clone https://github.com/LionSec/xerosploit.git"},
    "rhawk.php": {"linux": "git clone https://github.com/Tuhinshubhra/RED_HAWK.git", "termux": "git clone https://github.com/Tuhinshubhra/RED_HAWK.git"},
    "reconspider.py": {"linux": "git clone https://github.com/bhavsec/reconspider.git", "termux": "git clone https://github.com/bhavsec/reconspider.git"},
    "infoga.py": {"linux": "git clone https://github.com/Security-Tools-Alliance/Infoga.git", "termux": "git clone https://github.com/Security-Tools-Alliance/Infoga.git"},
    "dog": {"linux": "git clone https://github.com/s0md3v/ReconDog.git", "termux": "git clone https://github.com/s0md3v/ReconDog.git"},

def platform_tag() -> str:
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


def run(argv: list, timeout: int = DEFAULT_TIMEOUT, max_bytes: int = MAX_OUTPUT_BYTES,
        cwd: Optional[str] = None) -> dict:
    if not argv:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "reason": "nothing to run"}
    started = time.time()
    try:
        process = subprocess.run(argv, capture_output=True, timeout=timeout, cwd=cwd)
    except FileNotFoundError:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "reason": f"{argv[0]} is not installed on this machine"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "timed_out": True,
                "reason": f"{argv[0]} did not finish within {timeout}s"}
    except Exception as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "",
                "reason": f"{argv[0]} could not be run: {type(exc).__name__}: {exc}"}

    def _cap(raw: bytes) -> tuple:
        data = (raw or b"")[:max_bytes]
        return data.decode("utf-8", errors="replace"), len(raw or b"") > max_bytes

    stdout, stdout_truncated = _cap(process.stdout)
    stderr, stderr_truncated = _cap(process.stderr)
    return {
        "ok": process.returncode == 0,
        "returncode": int(process.returncode),
        "stdout": stdout,
        "stderr": stderr,

def nmap_scan(target: str, ports: Optional[str] = None,
              scan_type: str = "sS", timing: str = "T3",
              scripts: Optional[str] = None) -> dict:
    argv = ["nmap", f"-{scan_type}", f"-{timing}"]
    if ports:
        argv.extend(["-p", ports])
    if scripts:
        argv.extend(["--script", scripts])
    argv.append(target)
    return run(argv, timeout=300)


def nmap_service_scan(target: str, ports: Optional[str] = None,
                      timing: str = "T3") -> dict:
    argv = ["nmap", "-sV", f"-{timing}"]
    if ports:
        argv.extend(["-p", ports])
    argv.append(target)
    return run(argv, timeout=300)


def nmap_os_detect(target: str, timing: str = "T3") -> dict:
    return run(["nmap", "-O", f"-{timing}", target], timeout=300)


def nmap_script_scan(target: str, scripts: str = "vuln",

def dracnmap_scan(target: str, scan_type: Optional[str] = None) -> dict:
    argv = ["bash", "Dracnmap.sh"]
    if scan_type:
        argv.append(scan_type)
    argv.append(target)
    return run(argv, timeout=300, cwd="Dracnmap")


def xerosploit_run(target: str, gateway: str,
                   module: Optional[str] = None) -> dict:
    argv = ["sudo", "xerosploit"]
    return run(argv, timeout=300, cwd="xerosploit")


def red_hawk_scan(target: str, scan_type: str = "basic",
                  https: bool = False) -> dict:

def infoga_scan(domain: Optional[str] = None, email: Optional[str] = None,
                source: str = "all", breach: bool = False,
                verbose: str = "2") -> dict:
    argv = ["python3", "infoga.py"]
    if domain:
        argv.extend(["--domain", domain])
    if email:
        argv.extend(["--info", email])
    argv.extend(["--source", source])
    if breach:
        argv.append("--breach")
    argv.extend(["-v", verbose])
    return run(argv, timeout=300, cwd="infoga")


def recondog_scan(target: str, command: str = "all") -> dict:
    cmd_map = {"search": "1", "ns": "2", "port": "3", "cms": "4",
               "whois": "5", "honeypot": "6", "subdomain": "7",
               "reverse_ip": "8", "tech": "9", "all": "10"}
    opt = cmd_map.get(command, "10")
    argv = ["python3", "dog.py"]
    return run(argv, timeout=300, cwd="recondog")


def striker_scan(target: str, phase: str = "all") -> dict:
    argv = ["python3", "striker.py", target]
    return run(argv, timeout=600, cwd="striker")


def rang3r_scan(target_ip: str) -> dict:
    return run(["python2", "rang3r.py", "--ip", target_ip],
               timeout=300, cwd="rang3r")


def breacher_scan(target: str, extension: str = "none",
                  fast: bool = False, path: Optional[str] = None) -> dict:
    argv = ["python3", "breacher.py", "-u", target]
    if extension != "none":
        argv.extend(["--type", extension])
    if fast:
        argv.append("--fast")
    if path:
        argv.extend(["--path", path])
    return run(argv, timeout=300, cwd="breacher")
    argv = ["php", "rhawk.php"]
    return run(argv, timeout=300, cwd="RED_HAWK")


def reconspider_scan(target: str, module: str = "host") -> dict:
    argv = ["python3", "reconspider.py"]
    return run(argv, timeout=300, cwd="reconspider")
                     timing: str = "T3") -> dict:
    return run(["nmap", "--script", scripts, f"-{timing}", target],
               timeout=600)


def nmap_quick_scan(target: str) -> dict:
    return run(["nmap", "-T4", "-F", target], timeout=120)


def nmap_intense_scan(target: str) -> dict:
    return run(["nmap", "-T4", "-A", "-v", target], timeout=600)
        "truncated": stdout_truncated or stderr_truncated,
        "elapsed_s": round(time.time() - started, 2),
        "argv": [argv[0]] + ["***" if _is_secret(a) else a for a in argv[1:]],
    }


def _is_secret(value: str) -> bool:
    lowered = (value or "").lower()
    return lowered.startswith(("--passwords-file", "--identify")) and "=" in lowered
    "striker.py": {"linux": "git clone https://github.com/s0md3v/Striker.git", "termux": "git clone https://github.com/s0md3v/Striker.git"},
    "rang3r.py": {"linux": "git clone https://github.com/floriankunushevci/rang3r.git", "termux": "git clone https://github.com/floriankunushevci/rang3r.git"},
    "breacher.py": {"linux": "git clone https://github.com/s0md3v/breacher.git", "termux": "git clone https://github.com/s0md3v/breacher.git"},
}