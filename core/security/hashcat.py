"""core/security/hashcat.py - hash identification, capture conversion, cracking.

The cracking tools are all external and all optional: hashcat and John are probed
per call, and a missing tool reports what to install rather than failing. Cracking
is offline only - a hash never leaves the machine, and no server is contacted.

Hashcat mode 22000 is the modern WPA mode ("WPA-PBKDF2-PMKID+EAPOL"), which both
hashcat and John accept; the older `hccapx` (mode 2500) path is still supported
for tools and workflows that have not moved on.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

MODE_WPA = "22000"
MODE_HCCAPX = "2500"

#: argon2 variant -> hashcat mode, keyed by the tag inside the hash.
ARGON_MODES = {"argon2id": 13400, "argon2i": 1300, "argon2d": 1310}


def _argon_variant(candidate: str) -> str:
    """The argon2 variant named in the hash, defaulting to argon2id."""
    match = re.search(r"\$argon2(id|i|d)\$", candidate)
    return f"argon2{match.group(1)}" if match else "argon2id"


def tools() -> dict:
    from core.security.tools import available

    return available(["hashcat", "john", "hcxpcapngtool", "cap2hccapx", "aircrack-ng",
                      "tshark", "hcxhashtool"])


def identify(sample: str) -> dict:
    """Identify a hash from its shape, without contacting anything."""
    text = (sample or "").strip()
    if not text:
        return {"ok": False, "reason": "give the hash or its first characters (sample=...)"}
    candidate = text.split(":")[0] if ":" in text else text
    patterns = [
        (r"^\$2[aby]?\$", "bcrypt", 3200),
        (r"^\$argon2(i|d|id)\$", "argon2", {"argon2id": 13400, "argon2i": 1300, "argon2d": 1310}[
            _argon_variant(candidate)]),
        (r"^\$P\$", "phpass (WordPress)", 400),
        (r"^\$H\$", "phpBB3", 400),
        (r"^\$Drupal", "Drupal7", 7900),
        (r"^\$sha1\$", "SHA1 crypt (salt)", 12400),
        (r"^\$6\$", "sha512crypt", 1800),
        (r"^\$5\$", "sha256crypt", 7400),
        (r"^\$apr1\$", "APR1 (Apache)", 1600),
        (r"^\$md5\$", "Cisco Type 5", 500),
        (r"^\$pbkdf2-sha256\$", "PBKDF2-SHA256", 1000),
        (r"^\$pbkdf2-sha512\$", "PBKDF2-SHA512", 1210),
        (r"^\$office\$", "MS Office", 9600),
        (r"^\$pdf\$", "PDF", 10500),
        (r"^\$zip\$", "ZIP", 13600),
        (r"^\$rar5\$", "RAR5", 13000),
        (r"^\$7z\$", "7-Zip", 11600),
        (r"^\$keepass\$", "KeePass", 13400),
        (r"^\$bitcoin\$", "Bitcoin wallet", 15200),
        (r"^\$mssql", "MSSQL", 131),
        (r"^\$krb5", "Kerberos", 7500),
    ]
    for pattern, name, mode in patterns:
        if re.search(pattern, candidate):
            return {"ok": True, "hash_type": name, "hashcat_mode": mode,
                    "sample_length": len(candidate),
                    "note": "Identified by shape alone; the mode is a suggestion for hashcat."}

    length = len(candidate)
    if re.fullmatch(r"[0-9a-f]{32}", candidate):
        return {"ok": True, "hash_type": "MD5 / NTLM (32 hex)",
                "hashcat_mode": "0 (MD5) or 1000 (NTLM)",
                "sample_length": length,
                "note": "MD5 and NTLM share a shape; a hashcat run tries both."}
    if re.fullmatch(r"[0-9a-f]{40}", candidate):
        return {"ok": True, "hash_type": "SHA-1", "hashcat_mode": 100,
                "sample_length": length}
    if re.fullmatch(r"[0-9a-f]{56}", candidate) and b":" in sample.encode():
        return {"ok": True, "hash_type": "SHA-224", "hashcat_mode": 17300,
                "sample_length": length}
    if re.fullmatch(r"[0-9a-f]{64}", candidate):
        return {"ok": True, "hash_type": "SHA-256", "hashcat_mode": 1400,
                "sample_length": length}
    if re.fullmatch(r"[0-9a-f]{128}", candidate):
        return {"ok": True, "hash_type": "SHA-512", "hashcat_mode": 1700,
                "sample_length": length}
    if re.fullmatch(r"[0-9a-f]{16}", candidate):
        return {"ok": True, "hash_type": "LM (half)", "hashcat_mode": 3000,
                "sample_length": length}

    return {"ok": False,
            "reason": (f"a {length}-character hash of this shape is not one the identifier "
                       "knows. Try `hashcat --example-hashes` on this machine, or name the "
                       "format explicitly for the crack operation."),
            "sample_length": length}


def convert(capture_path: str, output_path: str = "", target_format: str = "hc22000") -> dict:
    """Convert a capture into crackable hashes.

    `hcxpcapngtool` handles pcap/pcapng; `cap2hccapx` produces the older hccapx;
    `aircrack-ng -J` writes the JtR/hashcat-compatible hccap. Availability is
    reported per call, because none of these ships by default.
    """
    from core.security.tools import available, run

    path = Path(capture_path).expanduser()
    if not path.exists():
        return {"ok": False, "reason": f"{path} does not exist on this machine"}

    probed = available(["hcxpcapngtool", "cap2hccapx", "aircrack-ng"])
    destination = output_path or str(path.with_suffix(".hc22000"))

    if probed["hcxpcapngtool"]["present"]:
        result = run(["hcxpcapngtool", "-o", destination, str(path)], timeout=120)
        return {"ok": result["ok"] and Path(destination).exists(),
                "tool": "hcxpcapngtool", "output": destination,
                "stdout": result["stdout"][-800:], "stderr": result["stderr"][-400:],
                "reason": result.get("reason") or "hcxpcapngtool ran"}
    if probed["cap2hccapx"]["present"]:
        result = run(["cap2hccapx", str(path), destination], timeout=60)
        return {"ok": result["ok"] and Path(destination).exists(),
                "tool": "cap2hccapx", "output": destination,
                "reason": result.get("reason") or "cap2hccapx ran"}
    if probed["aircrack-ng"]["present"]:
        result = run(["aircrack-ng", str(path), "-J", destination], timeout=120)
        return {"ok": result["ok"] and Path(destination).exists(),
                "tool": "aircrack-ng -J", "output": destination,
                "reason": result.get("reason") or "aircrack-ng ran"}
    return {"ok": False, "reason": (
        "no capture converter is installed (looked for hcxpcapngtool, cap2hccapx, aircrack-ng). "
        "Install hcxtools on Linux/Termux, or use tshark to extract the EAPOL frames.")}


def start_crack(
    hash_file: str,
    wordlist: str = "",
    mode: str = MODE_WPA,
    rules: Optional[list] = None,
    workload: str = "2",
    output_path: str = "",
) -> dict:
    """Start a cracking session with hashcat, reporting `started` and where it writes."""
    from core.security.tools import available, run_background

    path = Path(hash_file).expanduser()
    if not path.exists():
        return {"ok": False, "outcome": "failed", "reason": f"{path} does not exist on this machine"}

    probed = available(["hashcat"])
    if not probed["hashcat"]["present"]:
        return {"ok": False, "outcome": "failed", "reason": (
            f"hashcat is not installed on this machine ({probed['hashcat']['install']}). "
            "Nothing was run.")}

    cracked = output_path or str(path.with_suffix(".cracked.txt"))
    argv = ["hashcat", str(path), "-m", str(mode), "-w", str(workload),
            "--potfile-path", str(path.with_suffix(".potfile")),
            "-o", cracked, "--outfile-format=2"]
    if wordlist:
        argv.append(Path(wordlist).expanduser().as_posix())
        if rules:
            argv += ["-r", rules[0]]
    else:
        argv += ["--increment", "--increment-min", "8"]

    result = run_background(argv, cracked)
    if not result.get("ok"):
        return {"ok": False, "outcome": "failed", "reason": result.get("reason")}
    result.update({"hash_file": str(path), "mode": mode, "wordlist": wordlist or "incremental",
                   "cracked_file": cracked, "potfile": str(path.with_suffix(".potfile"))})
    return result


def cracked(hash_file: str) -> dict:
    """Read back what a session has already produced, without starting anything."""
    from core.security.tools import available, run

    path = Path(hash_file).expanduser()
    if not path.exists():
        return {"ok": False, "reason": f"{path} does not exist on this machine"}

    probed = available(["hashcat"])
    if not probed["hashcat"]["present"]:
        return {"ok": False, "reason": probed["hashcat"]["install"]}

    result = run(["hashcat", str(path), "-m", MODE_WPA, "--show",
                  "--potfile-path", str(path.with_suffix(".potfile"))], timeout=60)
    cracked_lines = [line for line in (result["stdout"] or "").splitlines() if line.strip()]
    return {"ok": result["ok"], "cracked": cracked_lines, "count": len(cracked_lines),
            "stdout_tail": (result["stdout"] or "")[-600:],
            "reason": result.get("reason") or "hashcat --show ran"}


def john(hash_file: str, wordlist: str = "") -> dict:
    """Run John the Ripper over a hash file, reporting `started` and where it writes."""
    from core.security.tools import available, run_background

    path = Path(hash_file).expanduser()
    if not path.exists():
        return {"ok": False, "outcome": "failed", "reason": f"{path} does not exist on this machine"}
    probed = available(["john"])
    if not probed["john"]["present"]:
        return {"ok": False, "outcome": "failed", "reason": (
            f"john is not installed on this machine ({probed['john']['install']}).")}

    argv = ["john", "--session=stella", str(path)]
    if wordlist:
        argv.append(f"--wordlist={Path(wordlist).expanduser()}")
    result = run_background(argv, str(path.with_suffix(".john.log")))
    result.update({"hash_file": str(path), "wordlist": wordlist or "default modes"})
    return result


def john_show(hash_file: str) -> dict:
    from core.security.tools import available, run

    path = Path(hash_file).expanduser()
    probed = available(["john"])
    if not probed["john"]["present"]:
        return {"ok": False, "reason": probed["john"]["install"]}
    result = run(["john", "--show", str(path)], timeout=60)
    return {"ok": result["ok"], "stdout": (result["stdout"] or "")[-800:],
            "reason": result.get("reason") or "john --show ran"}


def wordlists() -> dict:
    """The wordlists this machine already has, so a crack never invents one."""
    candidates = [
        Path("/usr/share/wordlists/rockyou.txt"),
        Path("/usr/share/wordlists"),
        Path("/usr/share/john/password.lst"),
        Path("/usr/local/share/wordlists"),
        Path.home() / "wordlists",
    ]
    found = []
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.stat().st_size > 0:
                found.append({"path": str(candidate), "bytes": candidate.stat().st_size})
            elif candidate.is_dir():
                entries = [entry for entry in candidate.glob("*.txt")
                           if entry.is_file() and entry.stat().st_size > 0]
                found.extend({"path": str(entry), "bytes": entry.stat().st_size}
                             for entry in sorted(entries)[:10])
        except OSError:
            continue
    return {"ok": True, "wordlists": found,
            "note": ("Only lists already on this machine are listed. If none are found, "
                     "SecLists or rockyou must be added by hand.")}
