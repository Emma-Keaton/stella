# src/backend/agent — Agentic runtime
# loop.py      — Think→act→observe→verify loop (bounded turns, repeat detection)
# llm.py       — Multi-backend LLM adapter (local K2 + cloud providers)
# tools.py     — Tool dataclass, Registry with permission/policy/audit
# planner.py   — Task planner: breaks goals into JSON tool steps
# executor.py  — AgentExecutor: executes planned steps via _call_tool dispatcher
# skill_loader.py — Loads skills from skills/ (SKILL.md + skill.py)
# integration.py — Bridge between UI/voice layer and agent loop
