"""Stella feedback ping system.

Structured upgrade/update requests from a Stella instance to the creator.
Report schema: what was encountered / what the user did / how / what they
need next — plus device profile and app version. NEVER includes secrets.

Channels (user picks one in settings, default: local file):
  1. local   — writes JSON to ~/.stella/feedback/ (fully private, default)
  2. email   — SMTP via the USER's own account to the creator address
  3. github  — prefilled issue URL opened in browser (user submits; no token)
  4. webhook — JSON POST to a user-provided HTTPS endpoint
  5. off     — no pings at all
"""
from __future__ import annotations

import json
import os
import platform
import re
import smtplib
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

SCHEMA_VERSION = 1

# Patterns scrubbed before ANY send. Secrets never leave the device.
_SCRUB_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([^\s'\"]+)"), r"\1: [REDACTED]"),
    (re.compile(r"(?i)(secret|password|passwd|pwd|token|bearer)\s*[:=]\s*['\"]?([^\s'\"]+)"), r"\1: [REDACTED]"),
    (re.compile(r"\b(sk-[A-Za-z0-9_-]{8,}|gsk_[A-Za-z0-9]{8,}|sk-or-[A-Za-z0-9_-]{8,})"), "[REDACTED-KEY]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[REDACTED-EMAIL]"),
]


def scrub(text: str) -> str:
    clean = text or ""
    for pat, repl in _SCRUB_PATTERNS:
        clean = pat.sub(repl, clean)
    return clean


def _stella_home() -> Path:
    try:
        from core.user_paths import get_user_data_dir
        base = get_user_data_dir()
    except Exception:
        base = Path.home() / ".stella"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _settings() -> dict:
    for cand in (_stella_home() / "config" / "app_settings.json",
                 Path(__file__).resolve().parent.parent / "config" / "app_settings.json"):
        try:
            return json.loads(cand.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
    return {}


def _version() -> str:
    """App version, robust to version.txt being a VSVersionInfo blob.

    version.txt is a PyInstaller version-resource struct, not a bare '1.2.3',
    so regex out the first semver token. A plain '1.2.3' file still works.
    """
    try:
        txt = (Path(__file__).resolve().parent.parent / "version.txt").read_text(
            encoding="utf-8", errors="ignore")
        m = re.search(r"(\d+\.\d+\.\d+)", txt)
        return m.group(1) if m else txt.strip().splitlines()[0][:40]
    except Exception:
        return "unknown"


def channels_available(cfg: dict | None = None) -> dict:
    """Which feedback routes are actually usable right now, for the UI.

    The GitHub issue route only needs a repo (always configured). The email and
    webhook routes need the destination to be set by the creator first, so the
    settings UI can show them as 'coming soon' until then instead of letting the
    user pick one that will fail.
    """
    cfg = cfg or _settings()
    # Fall back to the built-in repo: a migrated/legacy user config predates the
    # feedback fields, and the GitHub route only needs a repo (always present in
    # the app defaults), so the "available now" claim should hold regardless.
    repo = (cfg.get("feedback_github_repo") or "").strip() or _DEFAULT_REPO
    return {
        "github": bool(repo),
        "email": bool((cfg.get("feedback_email_to") or "").strip()
                      and (cfg.get("feedback_smtp_host") or "").strip()),
        "webhook": bool((cfg.get("feedback_webhook_url") or "").strip()),
    }


def build_report(encountered: str, did: str, how: str, need: str,
                 kind: str = "upgrade-request") -> dict:
    """Build a structured, scrubbed feedback report."""
    specs: dict = {}
    try:
        specs = {"os": platform.system(), "arch": platform.machine(),
                 "cores": os.cpu_count()}
        try:
            import psutil
            specs["ram_free_gb"] = round(psutil.virtual_memory().available / 1024 ** 3, 2)
        except Exception:
            pass
    except Exception:
        pass
    return {
        "schema": SCHEMA_VERSION, "kind": kind,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "app_version": _version(),
        "encountered": scrub(encountered), "did": scrub(did),
        "how": scrub(how), "need": scrub(need),
        "device": specs,
    }


def _save_local(report: dict) -> dict:
    d = _stella_home() / "feedback"
    d.mkdir(parents=True, exist_ok=True)
    name = f"feedback-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    p = d / name
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"ok": True, "channel": "local", "path": str(p)}


def _send_email(report: dict, cfg: dict) -> dict:
    to_addr = (cfg.get("feedback_email_to") or "").strip()
    smtp_host = (cfg.get("feedback_smtp_host") or "").strip()
    smtp_user = (cfg.get("feedback_smtp_user") or "").strip()
    smtp_pass = (cfg.get("feedback_smtp_pass") or "")
    if not (to_addr and smtp_host and smtp_user and smtp_pass):
        return {"ok": False, "channel": "email",
                "error": "creator address + SMTP host/user/pass required in settings"}
    msg = EmailMessage()
    msg["Subject"] = f"[Stella] {report.get('kind')} v{report.get('app_version')}"
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg.set_content(json.dumps(report, indent=2))
    try:
        port = int(cfg.get("feedback_smtp_port", 587))
    except Exception:
        port = 587
    with smtplib.SMTP(smtp_host, port, timeout=30) as s:
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)
    return {"ok": True, "channel": "email", "to": "[REDACTED-EMAIL]"}


def _create_github_issue_api(report: dict, cfg: dict) -> dict | None:
    """Create the issue directly via GitHub API. Returns None if no token,
    letting the caller fall back to the prefilled-URL flow."""
    repo = (cfg.get("feedback_github_repo") or "").strip()
    token = (cfg.get("feedback_github_token") or "").strip()
    if not repo or not token:
        return None
    title = f"[Stella] {report.get('kind')}"
    body = ("**Encountered**\n" + report["encountered"] + "\n\n**Did**\n" +
            report["did"] + "\n\n**How**\n" + report["how"] +
            "\n\n**Need**\n" + report["need"])
    payload = json.dumps({
        "title": title, "body": body,
        "labels": ["stella-feedback", str(report.get("kind", "feedback"))],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}",
                 "User-Agent": "stella-feedback/1.0",
                 "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "channel": "github-api",
                    "issue": data.get("number"), "url": data.get("html_url")}
    except Exception as e:
        return {"ok": False, "channel": "github-api", "error": str(e)[:200]}


def close_github_issue(repo: str, number: int, token: str) -> dict:
    """Close an attended issue (called by the update/release flow)."""
    payload = json.dumps({"state": "closed"}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{number}", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}",
                 "User-Agent": "stella-feedback/1.0",
                 "Accept": "application/vnd.github+json"}, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"ok": resp.status == 200, "issue": number}
    except Exception as e:
        return {"ok": False, "issue": number, "error": str(e)[:200]}


def _github_issue_url(report: dict, cfg: dict) -> dict:
    repo = (cfg.get("feedback_github_repo") or "").strip()  # owner/repo
    if not repo:
        return {"ok": False, "channel": "github",
                "error": "feedback_github_repo (owner/repo) required in settings"}
    import urllib.parse
    title = f"[Stella] {report.get('kind')}"
    ver = report.get("app_version")
    dev = report.get("device")
    body = ("**Encountered**\n" + report["encountered"] + "\n\n**Did**\n" +
            report["did"] + "\n\n**How**\n" + report["how"] +
            "\n\n**Need**\n" + report["need"] +
            f"\n\n_app {ver} / {dev}_")
    url = (f"https://github.com/{repo}/issues/new?"
           + urllib.parse.urlencode({"title": title, "body": body}))
    return {"ok": True, "channel": "github", "open_url": url}


def _post_webhook(report: dict, cfg: dict) -> dict:
    url = (cfg.get("feedback_webhook_url") or "").strip()
    if not url or not url.startswith("https://"):
        return {"ok": False, "channel": "webhook",
                "error": "feedback_webhook_url (https) required in settings"}
    data = json.dumps(report).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "stella-feedback/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return {"ok": 200 <= resp.status < 300, "channel": "webhook",
                "status": resp.status}


def send_report(report: dict, cfg: dict | None = None) -> dict:
    """Route a report to the user's chosen channel. Default: local file."""
    cfg = cfg or _settings()
    channel = (cfg.get("feedback_channel") or "local").strip().lower()
    if channel == "off":
        return {"ok": True, "channel": "off", "note": "pings disabled by user"}
    if channel == "email":
        return _send_email(report, cfg)
    if channel == "github":
        api_res = _create_github_issue_api(report, cfg)
        if api_res is not None:
            return api_res
        return _github_issue_url(report, cfg)
    if channel == "webhook":
        return _post_webhook(report, cfg)
    return _save_local(report)


# Built-in feedback destination. The GitHub-issue route needs nothing but a
# repo, so it is the one channel that works out of the box on every install.
_DEFAULT_REPO = "Emma-Keaton/stella"

CHANNELS = ["local", "email", "github", "webhook", "off"]
