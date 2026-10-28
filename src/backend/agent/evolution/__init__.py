# src/backend/agent/evolution — Dr. Zero self-evolving search agents without training data
#
# Stella trains, learns, and evolves without training data dumps.
# A self-evolution feedback loop:
#   Proposer  → generates diverse, challenging-yet-solvable questions
#   Solver    → Stella's agent attempts to solve them using search/tools
#   Curriculum → difficulty adjusts based on solver success rate
#   HRPO       → hop-grouped relative policy optimization for efficient evaluation
#
# Zero-data init: starts with zero training data. Proposer uses domain templates
# + LLM to generate questions. Solver uses existing tools (web_search, etc.) to answer.
# As solver evolves, proposer generates harder questions (automated curriculum).
