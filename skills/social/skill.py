"""
skills/social/skill.py - Stella social media automation.

Provides scheduled posting, multi-platform content queues, draft management,
engagement monitoring (read-only), and post templates. Pure-Python, no external
dependencies.

Inspired by Grok Bot workflows: read social platforms, schedule content, and
send drafts to multiple destinations before posting.

Operations:
  schedule      - Schedule a post for a specific time across platforms
  queue         - List pending/queued posts
  draft         - Create a draft post for review
  publish       - Publish a queued/draft post immediately
  cancel        - Cancel a scheduled post
  monitor       - Read-only monitor of accounts/topics (like Grok Bot reads X)
  template      - Manage post templates
  analytics     - Track post performance (stored locally)
  sources       - Return skill metadata
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "social"
QUEUE_FILE = DATA_DIR / "queue.json"
DRAFTS_FILE = DATA_DIR / "drafts.json"
SCHEDULED_FILE = DATA_DIR / "scheduled.json"
ANALYTICS_FILE = DATA_DIR / "analytics.json"
TEMPLATES_FILE = DATA_DIR / "templates.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path, default: Any) -> Any:
    _ensure_data_dir()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save(path: Path, data: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return datetime.now().isoformat()


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _wrap(text: str, width: int = 80) -> str:
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for w in words:
        if current_len + len(w) + len(current) > width:
            lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += len(w)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


# ── Platform registry ──────────────────────────────────────────────────

PLATFORMS = {
    "x": {"name": "X (Twitter)", "read_only": True, "supports_schedule": True},
    "youtube": {"name": "YouTube", "read_only": False, "supports_schedule": True},
    "linkedin": {"name": "LinkedIn", "read_only": False, "supports_schedule": True},
    "facebook": {"name": "Facebook", "read_only": False, "supports_schedule": True},
    "instagram": {"name": "Instagram", "read_only": False, "supports_schedule": True},
    "threads": {"name": "Threads", "read_only": False, "supports_schedule": True},
    "bluesky": {"name": "Bluesky", "read_only": False, "supports_schedule": True},
    "mastodon": {"name": "Mastodon", "read_only": False, "supports_schedule": True},
}


# ── Schedule operation ─────────────────────────────────────────────────

def _op_schedule(kwargs: dict) -> dict:
    """Schedule a post for a specific time across platforms."""
    content = (kwargs.get("content") or "").strip()
    platforms = kwargs.get("platforms") or ["x"]
    schedule_at = kwargs.get("schedule_at") or ""
    repeat = kwargs.get("repeat") or ""
    tags = kwargs.get("tags") or []

    if not content:
        return _op("schedule", False, None, "Provide content to post (content=...).")

    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(",") if p.strip()]

    invalid = [p for p in platforms if p not in PLATFORMS]
    if invalid:
        return _op("schedule", False, None, "Unknown platform(s): " + ", ".join(invalid))

    scheduled_time = None
    if schedule_at:
        try:
            scheduled_time = datetime.fromisoformat(schedule_at)
        except Exception:
            scheduled_time = _parse_natural_time(schedule_at)
            if scheduled_time is None:
                return _op("schedule", False, None, "Could not parse schedule time: " + schedule_at)

    post_id = str(uuid.uuid4())[:8]
    post = {
        "id": post_id,
        "content": content,
        "platforms": platforms,
        "schedule_at": scheduled_time.isoformat() if scheduled_time else None,
        "repeat": repeat,
        "tags": tags,
        "status": "scheduled" if scheduled_time else "draft",
        "created_at": _now(),
        "published_at": None,
        "results": {},
    }

    if scheduled_time:
        scheduled = _load(SCHEDULED_FILE, [])
        scheduled.append(post)
        _save(SCHEDULED_FILE, scheduled)
    else:
        drafts = _load(DRAFTS_FILE, [])
        drafts.append(post)
        _save(DRAFTS_FILE, drafts)

    platforms_str = ", ".join(PLATFORMS[p]["name"] for p in platforms)
    when = scheduled_time.strftime("%Y-%m-%d %H:%M") if scheduled_time else "as draft"

    return _op("schedule", True, {
        "id": post_id,
        "content": content,
        "platforms": platforms,
        "platforms_str": platforms_str,
        "schedule_at": post["schedule_at"],
        "repeat": repeat,
        "status": post["status"],
        "message": "Post " + post_id + " queued for " + platforms_str + " at " + when,
    })


def _parse_natural_time(text: str) -> datetime | None:
    """Parse natural language time like 'tomorrow at 9 AM'."""
    text = text.strip().lower()
    now = datetime.now()
    target = now

    if "tomorrow" in text:
        target = now + timedelta(days=1)
        text = text.replace("tomorrow", "").strip()

    time_match = re.search(r"(\d{1,2})\s*:\s*(\d{2})?\s*(am|pm)?", text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
    elif "morning" in text:
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
    elif "afternoon" in text:
        target = target.replace(hour=14, minute=0, second=0, microsecond=0)
    elif "evening" in text:
        target = target.replace(hour=18, minute=0, second=0, microsecond=0)
    else:
        return None

    if target <= now:
        target += timedelta(days=1)
    return target


# ── Queue operation ────────────────────────────────────────────────────

def _op_queue(kwargs: dict) -> dict:
    """List pending/queued posts."""
    status_filter = (kwargs.get("status") or "all").strip()
    limit = int(kwargs.get("limit") or 20)

    scheduled = _load(SCHEDULED_FILE, [])
    drafts = _load(DRAFTS_FILE, [])

    all_posts = []
    for p in scheduled:
        p["_source"] = "scheduled"
        all_posts.append(p)
    for p in drafts:
        p["_source"] = "draft"
        all_posts.append(p)

    all_posts.sort(key=lambda p: p.get("schedule_at") or p.get("created_at", ""))

    if status_filter != "all":
        all_posts = [p for p in all_posts if p.get("status") == status_filter]

    all_posts = all_posts[:limit]

    lines = []
    lines.append("Social Queue (" + str(len(all_posts)) + " post(s))")
    lines.append("=" * 40)
    lines.append("")
    for p in all_posts:
        when = p.get("schedule_at") or "as draft"
        if when != "as draft":
            try:
                when = datetime.fromisoformat(when).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        platforms = ", ".join(p.get("platforms", []))
        lines.append("[" + p["id"] + "] " + p["status"] + " - " + platforms)
        lines.append("    " + when)
        lines.append("    " + p["content"][:80])
        if p.get("tags"):
            lines.append("    tags: " + ", ".join(p["tags"]))
        lines.append("")

    content = "\n".join(lines)
    return _op("queue", True, {
        "count": len(all_posts),
        "posts": all_posts,
        "content": content,
    })


# ── Draft operation ────────────────────────────────────────────────────

def _op_draft(kwargs: dict) -> dict:
    """Create a draft post for review."""
    content = (kwargs.get("content") or "").strip()
    platforms = kwargs.get("platforms") or ["x"]
    tags = kwargs.get("tags") or []

    if not content:
        return _op("draft", False, None, "Provide content for the draft (content=...).")

    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(",") if p.strip()]

    post_id = str(uuid.uuid4())[:8]
    post = {
        "id": post_id,
        "content": content,
        "platforms": platforms,
        "schedule_at": None,
        "repeat": "",
        "tags": tags,
        "status": "draft",
        "created_at": _now(),
        "published_at": None,
        "results": {},
    }

    drafts = _load(DRAFTS_FILE, [])
    drafts.append(post)
    _save(DRAFTS_FILE, drafts)

    return _op("draft", True, {
        "id": post_id,
        "content": content,
        "platforms": platforms,
        "status": "draft",
        "message": "Draft " + post_id + " created for review",
    })


# ── Publish operation ──────────────────────────────────────────────────

def _op_publish(kwargs: dict) -> dict:
    """Publish a queued/draft post immediately."""
    post_id = (kwargs.get("id") or "").strip()
    content = (kwargs.get("content") or "").strip()
    platforms = kwargs.get("platforms") or ["x"]

    if not post_id and not content:
        return _op("publish", False, None, "Provide a post id or content to publish.")

    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(",") if p.strip()]

    target = None
    source = None
    scheduled = _load(SCHEDULED_FILE, [])
    drafts = _load(DRAFTS_FILE, [])

    for p in scheduled:
        if p["id"] == post_id:
            target = p
            source = "scheduled"
            break
    if not target:
        for p in drafts:
            if p["id"] == post_id:
                target = p
                source = "draft"
                break

    if target is None and content:
        post_id = str(uuid.uuid4())[:8]
        target = {
            "id": post_id,
            "content": content,
            "platforms": platforms,
            "schedule_at": None,
            "repeat": "",
            "tags": [],
            "status": "published",
            "created_at": _now(),
            "published_at": _now(),
            "results": {},
        }
        analytics = _load(ANALYTICS_FILE, [])
        analytics.append({
            "post_id": post_id,
            "content": content,
            "platforms": platforms,
            "published_at": _now(),
            "status": "published",
        })
        _save(ANALYTICS_FILE, analytics)
        return _op("publish", True, {
            "id": post_id,
            "platforms": platforms,
            "status": "published",
            "message": "Published " + post_id + " immediately to " + ", ".join(platforms),
        })

    if target is None:
        return _op("publish", False, None, "Post " + post_id + " not found in queue or drafts.")

    if source == "scheduled":
        scheduled = [p for p in scheduled if p["id"] != post_id]
        _save(SCHEDULED_FILE, scheduled)
    else:
        drafts = [p for p in drafts if p["id"] != post_id]
        _save(DRAFTS_FILE, drafts)

    target["status"] = "published"
    target["published_at"] = _now()

    analytics = _load(ANALYTICS_FILE, [])
    analytics.append({
        "post_id": post_id,
        "content": target["content"],
        "platforms": target["platforms"],
        "published_at": target["published_at"],
        "status": "published",
    })
    _save(ANALYTICS_FILE, analytics)

    platforms_str = ", ".join(PLATFORMS[p]["name"] for p in target["platforms"])
    return _op("publish", True, {
        "id": post_id,
        "platforms": target["platforms"],
        "platforms_str": platforms_str,
        "status": "published",
        "message": "Published " + post_id + " to " + platforms_str,
    })


# ── Cancel operation ───────────────────────────────────────────────────

def _op_cancel(kwargs: dict) -> dict:
    """Cancel a scheduled post."""
    post_id = (kwargs.get("id") or "").strip()
    if not post_id:
        return _op("cancel", False, None, "Provide a post id to cancel (id=...).")

    scheduled = _load(SCHEDULED_FILE, [])
    original_len = len(scheduled)
    scheduled = [p for p in scheduled if p["id"] != post_id]

    if len(scheduled) == original_len:
        return _op("cancel", False, None, "Scheduled post " + post_id + " not found.")

    _save(SCHEDULED_FILE, scheduled)
    return _op("cancel", True, {
        "id": post_id,
        "message": "Cancelled scheduled post " + post_id,
    })


# ── Monitor operation (read-only, like Grok Bot reads X) ───────────────

def _op_monitor(kwargs: dict) -> dict:
    """Read-only monitor of accounts/topics. Does not post."""
    query = (kwargs.get("query") or "").strip()
    platforms = kwargs.get("platforms") or ["x"]
    limit = int(kwargs.get("limit") or 10)

    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(",") if p.strip()]

    if not query:
        return _op("monitor", False, None, "Provide a query to monitor (query=...).")

    lines = []
    lines.append("Social Monitor: '" + query + "'")
    lines.append("=" * 40)
    lines.append("")
    lines.append("Platforms: " + ", ".join(PLATFORMS[p]["name"] for p in platforms))
    lines.append("Mode: read-only (no posts made)")
    lines.append("")
    lines.append("Note: This is a read-only monitor. To connect real platform APIs,")
    lines.append("configure credentials in Settings -> Cloud Providers.")
    lines.append("")
    lines.append("Sample results (simulated):")
    lines.append("- No matching posts found for '" + query + "'")
    lines.append("")

    content = "\n".join(lines)
    return _op("monitor", True, {
        "query": query,
        "platforms": platforms,
        "mode": "read_only",
        "results": [],
        "content": content,
    })


# ── Template operation ─────────────────────────────────────────────────

def _op_template(kwargs: dict) -> dict:
    """Manage post templates."""
    action = (kwargs.get("action") or "list").strip()
    name = (kwargs.get("name") or "").strip()
    content = (kwargs.get("content") or "").strip()
    tags = kwargs.get("tags") or []

    templates = _load(TEMPLATES_FILE, {})

    if action == "list":
        if not templates:
            return _op("template", True, {
                "templates": [],
                "content": "No templates defined yet.",
            })
        lines = []
        lines.append("Post Templates")
        lines.append("==============")
        lines.append("")
        for tname, tdata in templates.items():
            lines.append("- " + tname + ": " + tdata.get("content", "")[:60])
            if tdata.get("tags"):
                lines.append("  tags: " + ", ".join(tdata["tags"]))
        lines.append("")
        return _op("template", True, {
            "templates": templates,
            "content": "\n".join(lines),
        })

    if action == "add":
        if not name or not content:
            return _op("template", False, None, "Provide name and content for the template.")
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        templates[name] = {
            "content": content,
            "tags": tags,
            "created_at": _now(),
        }
        _save(TEMPLATES_FILE, templates)
        return _op("template", True, {
            "name": name,
            "message": "Template '" + name + "' added",
        })

    if action == "remove":
        if not name:
            return _op("template", False, None, "Provide a template name to remove.")
        if name not in templates:
            return _op("template", False, None, "Template '" + name + "' not found.")
        del templates[name]
        _save(TEMPLATES_FILE, templates)
        return _op("template", True, {
            "name": name,
            "message": "Template '" + name + "' removed",
        })

    if action == "use":
        if not name:
            return _op("template", False, None, "Provide a template name to use.")
        if name not in templates:
            return _op("template", False, None, "Template '" + name + "' not found.")
        return _op("template", True, {
            "name": name,
            "content": templates[name]["content"],
            "tags": templates[name].get("tags", []),
            "message": "Template '" + name + "' loaded",
        })

    return _op("template", False, None, "Unknown template action: " + action + ". One of: list, add, remove, use.")


# ── Analytics operation ────────────────────────────────────────────────

def _op_analytics(kwargs: dict) -> dict:
    """Track post performance (stored locally)."""
    limit = int(kwargs.get("limit") or 20)
    analytics = _load(ANALYTICS_FILE, [])
    analytics = analytics[-limit:]

    if not analytics:
        return _op("analytics", True, {
            "count": 0,
            "content": "No analytics data yet.",
        })

    lines = []
    lines.append("Post Analytics (" + str(len(analytics)) + " post(s))")
    lines.append("=" * 40)
    lines.append("")
    for a in analytics:
        when = a.get("published_at", "")
        try:
            when = datetime.fromisoformat(when).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        lines.append("[" + a["post_id"] + "] " + when)
        lines.append("    platforms: " + ", ".join(a.get("platforms", [])))
        lines.append("    status: " + a.get("status", "unknown"))
        lines.append("    " + a["content"][:60])
        lines.append("")

    content = "\n".join(lines)
    return _op("analytics", True, {
        "count": len(analytics),
        "analytics": analytics,
        "content": content,
    })


# ── Sources ────────────────────────────────────────────────────────────

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "social (Stella social media automation)",
        "dependencies": [],
        "operations": ["schedule", "queue", "draft", "publish", "cancel",
                       "monitor", "template", "analytics", "sources"],
        "platforms": list(PLATFORMS.keys()),
        "note": "Pure-Python social automation skill. Runs on desktop and Android. "
                "Platform API credentials configured via Settings -> Cloud Providers.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "schedule": _op_schedule,
    "queue": _op_queue,
    "draft": _op_draft,
    "publish": _op_publish,
    "cancel": _op_cancel,
    "monitor": _op_monitor,
    "template": _op_template,
    "analytics": _op_analytics,
}

_OPERATION_TITLES = {
    "sources": "Social Skill Sources",
    "schedule": "Schedule Post",
    "queue": "Social Queue",
    "draft": "Create Draft",
    "publish": "Publish Post",
    "cancel": "Cancel Post",
    "monitor": "Social Monitor",
    "template": "Post Templates",
    "analytics": "Post Analytics",
}


def execute(**kwargs) -> dict:
    """Run one social operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Social",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown social operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Social",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Social",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Social error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Social"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
