# Workflows — Stella skillset and workflow definitions
#
# Workflows are YAML files that chain skill operations into multi-step
# automations. Inspired by Grok Bot's 3 workflows:
#   1. Read social for you (read-only monitoring)
#   2. Claude Code + Codex inside Grok Bot (agent chaining)
#   3. Local newsletter (scan + write + send to destinations)
#
# Available workflows:
#   - social_monitor.yaml      — Read-only social monitoring (Workflow 1 pattern)
#   - social_scheduler.yaml    — Scheduled posting with draft review
#   - content_briefing.yaml    — Scan + write + send to destinations (Workflow 3 pattern)
#   - social_automation.yaml   — End-to-end social automation
#
# Skills:
#   - skills/writing/         — Document, email, report, letter, note, summary, rewrite, proofread
#   - skills/social/          — Schedule, queue, draft, publish, cancel, monitor, template, analytics
#
# Example usage:
#   stella execute workflow social_monitor --query "AI news" --platforms x --limit 10
#   stella execute workflow social_scheduler --content "Hello world" --platforms x,linkedin --schedule_at "tomorrow at 9 AM"
#   stella execute workflow content_briefing --topic "AI news" --area "global" --interests "technology"
