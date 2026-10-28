"""
skills/writing/skill.py - Stella writing assistant.

Provides document, email, report, letter, note, summary, rewrite, and
proofreading operations. Pure-Python, no external dependencies.

Operations:
  document   - Write a structured document (title, sections, conclusion)
  email      - Write a professional or casual email
  report     - Write a findings report with sections and recommendations
  letter     - Write a formal or personal letter
  note       - Write a short note or memo
  summary    - Summarize provided text into key points
  rewrite    - Rewrite text in a different tone/style
  proofread  - Check text for grammar, spelling, clarity issues
  sources    - Return skill metadata (dependencies, operations)
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.split())


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


# ── Document ────────────────────────────────────────────────────────────

def _op_document(kwargs: dict) -> dict:
    title = (kwargs.get("title") or "Untitled Document").strip()
    sections = kwargs.get("sections") or []
    tone = (kwargs.get("tone") or "professional").strip()
    audience = (kwargs.get("audience") or "general reader").strip()
    include_conclusion = bool(kwargs.get("include_conclusion", True))

    if isinstance(sections, str):
        import json
        try:
            sections = json.loads(sections)
        except Exception:
            sections = [{"heading": "Content", "body": sections}]
    if not isinstance(sections, list):
        sections = [{"heading": "Content", "body": str(sections)}]

    lines = []
    lines.append(_title_case(title))
    lines.append("=" * len(title))
    lines.append("")
    lines.append("Tone: " + tone + "  |  Audience: " + audience)
    lines.append("")

    for i, section in enumerate(sections, 1):
        if isinstance(section, dict):
            heading = section.get("heading", "Section " + str(i))
            body = section.get("body", "")
        else:
            heading = "Section " + str(i)
            body = str(section)
        lines.append(str(i) + ". " + heading)
        lines.append("-" * len(heading))
        lines.append("")
        lines.append(_wrap(body, 88))
        lines.append("")

    if include_conclusion:
        lines.append("Conclusion")
        lines.append("----------")
        lines.append("")
        lines.append(_wrap(
            "This document covered " + str(len(sections)) + " section(s) on '" + title +
            "' for a " + audience + " audience, written in a " + tone + " tone.",
            88,
        ))
        lines.append("")

    content = "\n".join(lines)
    return _op("document", True, {
        "title": title,
        "tone": tone,
        "audience": audience,
        "sections": len(sections),
        "content": content,
        "word_count": len(content.split()),
    })


# ── Email ───────────────────────────────────────────────────────────────

def _op_email(kwargs: dict) -> dict:
    to = (kwargs.get("to") or "").strip()
    subject = (kwargs.get("subject") or "No Subject").strip()
    body = (kwargs.get("body") or "").strip()
    tone = (kwargs.get("tone") or "professional").strip()
    purpose = (kwargs.get("purpose") or "general").strip()

    greeting_map = {
        "professional": "Dear " + to + "," if to else "Hello,",
        "casual": "Hi " + to + "," if to else "Hey there,",
        "formal": "Dear " + to + "," if to else "Dear Sir/Madam,",
        "friendly": "Hi " + to + "," if to else "Hello,",
    }
    closing_map = {
        "professional": "Best regards,",
        "casual": "Cheers,",
        "formal": "Sincerely,",
        "friendly": "Warmly,",
    }
    greeting = greeting_map.get(tone, greeting_map["professional"])
    closing = closing_map.get(tone, closing_map["professional"])

    lines = []
    lines.append("To: " + to)
    lines.append("Subject: " + subject)
    lines.append("")
    lines.append(greeting)
    lines.append("")
    lines.append(_wrap(body, 88))
    lines.append("")
    lines.append(closing)
    lines.append("")
    lines.append("Stella - Your AI Assistant")

    content = "\n".join(lines)
    return _op("email", True, {
        "to": to,
        "subject": subject,
        "tone": tone,
        "purpose": purpose,
        "content": content,
        "word_count": len(content.split()),
    })


# ── Report ──────────────────────────────────────────────────────────────

def _op_report(kwargs: dict) -> dict:
    topic = (kwargs.get("topic") or "Report").strip()
    findings = kwargs.get("findings") or []
    recommendations = kwargs.get("recommendations") or []
    audience = (kwargs.get("audience") or "stakeholders").strip()

    if isinstance(findings, str):
        findings = [f.strip() for f in findings.split("\n") if f.strip()]
    if isinstance(recommendations, str):
        recommendations = [r.strip() for r in recommendations.split("\n") if r.strip()]

    lines = []
    lines.append("Report: " + topic)
    lines.append("=" * (len(topic) + 8))
    lines.append("")
    lines.append("Audience: " + audience)
    lines.append("")

    lines.append("Executive Summary")
    lines.append("-----------------")
    lines.append("")
    lines.append(_wrap(
        "This report presents findings and recommendations on '" + topic +
        "' for " + audience + ".",
        88,
    ))
    lines.append("")

    if findings:
        lines.append("Key Findings")
        lines.append("------------")
        lines.append("")
        for i, finding in enumerate(findings, 1):
            lines.append(str(i) + ". " + finding)
        lines.append("")

    if recommendations:
        lines.append("Recommendations")
        lines.append("---------------")
        lines.append("")
        for i, rec in enumerate(recommendations, 1):
            lines.append(str(i) + ". " + rec)
        lines.append("")

    lines.append("Conclusion")
    lines.append("----------")
    lines.append("")
    lines.append(_wrap(
        "The findings above provide a basis for next steps on '" + topic + "'. " +
        "Implementing the recommendations will help " + audience + " move forward.",
        88,
    ))
    lines.append("")

    content = "\n".join(lines)
    return _op("report", True, {
        "topic": topic,
        "audience": audience,
        "findings_count": len(findings),
        "recommendations_count": len(recommendations),
        "content": content,
        "word_count": len(content.split()),
    })


# ── Letter ──────────────────────────────────────────────────────────────

def _op_letter(kwargs: dict) -> dict:
    recipient = (kwargs.get("recipient") or "").strip()
    sender = (kwargs.get("sender") or "Stella").strip()
    subject = (kwargs.get("subject") or "").strip()
    body = (kwargs.get("body") or "").strip()
    style = (kwargs.get("style") or "formal").strip()

    opening_map = {
        "formal": "Dear " + recipient + "," if recipient else "Dear Sir or Madam,",
        "personal": "Dear " + recipient + "," if recipient else "Hello,",
        "business": "Dear " + recipient + "," if recipient else "Hello,",
    }
    closing_map = {
        "formal": "Yours faithfully,",
        "personal": "Warmly,",
        "business": "Best regards,",
    }
    opening = opening_map.get(style, opening_map["formal"])
    closing = closing_map.get(style, closing_map["formal"])

    lines = []
    if subject:
        lines.append("Re: " + subject)
        lines.append("")
    lines.append(opening)
    lines.append("")
    lines.append(_wrap(body, 88))
    lines.append("")
    lines.append(closing)
    lines.append("")
    lines.append(sender)

    content = "\n".join(lines)
    return _op("letter", True, {
        "recipient": recipient,
        "sender": sender,
        "subject": subject,
        "style": style,
        "content": content,
        "word_count": len(content.split()),
    })


# ── Note ────────────────────────────────────────────────────────────────

def _op_note(kwargs: dict) -> dict:
    title = (kwargs.get("title") or "Note").strip()
    content_text = (kwargs.get("content") or "").strip()
    tags = kwargs.get("tags") or []
    priority = (kwargs.get("priority") or "normal").strip()

    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not isinstance(tags, list):
        tags = []

    lines = []
    lines.append("NOTE: " + title)
    lines.append("-" * (len(title) + 6))
    lines.append("")
    lines.append("Priority: " + priority)
    if tags:
        lines.append("Tags: " + ", ".join(tags))
    lines.append("")
    lines.append(_wrap(content_text, 88))
    lines.append("")

    content = "\n".join(lines)
    return _op("note", True, {
        "title": title,
        "priority": priority,
        "tags": tags,
        "content": content,
        "word_count": len(content.split()),
    })


# ── Summary ─────────────────────────────────────────────────────────────

def _op_summary(kwargs: dict) -> dict:
    text = (kwargs.get("text") or "").strip()
    max_points = int(kwargs.get("max_points") or 5)
    focus = (kwargs.get("focus") or "general").strip()

    if not text:
        return _op("summary", False, None, "Provide text to summarize (text=...).")

    import re
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return _op("summary", False, None, "No sentences found in text.")

    keywords = set(focus.lower().split()) if focus != "general" else set()
    scored = []
    for i, s in enumerate(sentences):
        score = 0
        if i == 0:
            score += 3
        if i == len(sentences) - 1:
            score += 2
        low = s.lower()
        for kw in keywords:
            if kw in low:
                score += 1
        scored.append((score, i, s))

    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[:max_points]
    top.sort(key=lambda x: x[1])

    points = [s for _, _, s in top]
    lines = []
    lines.append("Summary (" + str(len(points)) + " point(s), focus: " + focus + ")")
    lines.append("=" * 40)
    lines.append("")
    for i, p in enumerate(points, 1):
        lines.append(str(i) + ". " + p)
    lines.append("")

    content = "\n".join(lines)
    return _op("summary", True, {
        "original_length": len(text.split()),
        "summary_length": len(content.split()),
        "points": points,
        "content": content,
    })


# ── Rewrite ─────────────────────────────────────────────────────────────

def _op_rewrite(kwargs: dict) -> dict:
    text = (kwargs.get("text") or "").strip()
    target_tone = (kwargs.get("tone") or "professional").strip()
    audience = (kwargs.get("audience") or "general reader").strip()

    if not text:
        return _op("rewrite", False, None, "Provide text to rewrite (text=...).")

    tone_guidance = {
        "professional": "Rewrite in a professional, business-appropriate tone.",
        "casual": "Rewrite in a casual, conversational tone.",
        "formal": "Rewrite in a formal, polite tone.",
        "friendly": "Rewrite in a friendly, warm tone.",
        "persuasive": "Rewrite in a persuasive, compelling tone.",
        "concise": "Rewrite concisely, removing unnecessary words.",
    }
    guidance = tone_guidance.get(target_tone, tone_guidance["professional"])

    lines = []
    lines.append("Rewrite: " + target_tone + " tone")
    lines.append("Audience: " + audience)
    lines.append("")
    lines.append("Original:")
    lines.append(_wrap(text, 88))
    lines.append("")
    lines.append("Rewritten:")
    lines.append("-" * 40)
    lines.append("")

    rewritten = text
    if target_tone == "concise":
        fillers = ["really", "very", "quite", "just", "simply", "basically", "actually"]
        for f in fillers:
            rewritten = rewritten.replace(" " + f + " ", " ")
    elif target_tone == "professional":
        rewritten = rewritten.replace("hey", "hello").replace("hi ", "greetings ")
    elif target_tone == "casual":
        rewritten = rewritten.replace("greetings", "hey").replace("hello", "hi")

    lines.append(_wrap(rewritten, 88))
    lines.append("")

    content = "\n".join(lines)
    return _op("rewrite", True, {
        "target_tone": target_tone,
        "audience": audience,
        "original": text,
        "rewritten": rewritten,
        "content": content,
        "word_count": len(content.split()),
    })


# ── Proofread ───────────────────────────────────────────────────────────

def _op_proofread(kwargs: dict) -> dict:
    text = (kwargs.get("text") or "").strip()

    if not text:
        return _op("proofread", False, None, "Provide text to proofread (text=...).")

    import re
    issues = []

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    if "  " in text:
        issues.append("Double spaces detected - use single spaces between words.")

    for s in sentences:
        if s and s[0].islower() and s[0].isalpha():
            issues.append("Sentence starts with lowercase: '" + s[:40] + "...'")

    for s in sentences:
        if len(s.split()) > 40:
            issues.append("Long sentence (" + str(len(s.split())) + " words): '" + s[:50] + "...'")

    words = text.split()
    for i in range(len(words) - 1):
        if words[i].lower() == words[i + 1].lower():
            issues.append("Repeated word: '" + words[i] + "'")

    if text and not text.rstrip().endswith((".", "!", "?")):
        issues.append("Text does not end with sentence-ending punctuation.")

    word_count = len(text.split())
    sentence_count = len(sentences)
    avg_len = round(word_count / max(sentence_count, 1), 1)

    lines = []
    lines.append("Proofread Results")
    lines.append("=================")
    lines.append("")
    lines.append("Word count: " + str(word_count))
    lines.append("Sentence count: " + str(sentence_count))
    lines.append("Average words per sentence: " + str(avg_len))
    lines.append("")
    if issues:
        lines.append("Issues found: " + str(len(issues)))
        lines.append("")
        for i, issue in enumerate(issues, 1):
            lines.append(str(i) + ". " + issue)
    else:
        lines.append("No issues found. Text looks clean!")
    lines.append("")

    content = "\n".join(lines)
    return _op("proofread", True, {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_words_per_sentence": avg_len,
        "issues": issues,
        "issue_count": len(issues),
        "content": content,
    })


# ── Sources ─────────────────────────────────────────────────────────────

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "writing (Stella writing assistant)",
        "dependencies": [],
        "operations": ["document", "email", "report", "letter", "note",
                       "summary", "rewrite", "proofread", "sources"],
        "note": "Pure-Python writing skill. Runs on desktop and Android.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "document": _op_document,
    "email": _op_email,
    "report": _op_report,
    "letter": _op_letter,
    "note": _op_note,
    "summary": _op_summary,
    "rewrite": _op_rewrite,
    "proofread": _op_proofread,
}

_OPERATION_TITLES = {
    "sources": "Writing Skill Sources",
    "document": "Document",
    "email": "Email",
    "report": "Report",
    "letter": "Letter",
    "note": "Note",
    "summary": "Summary",
    "rewrite": "Rewrite",
    "proofread": "Proofread",
}


def execute(**kwargs) -> dict:
    """Run one writing operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Writing",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown writing operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Writing",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Writing",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Writing error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Writing"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
