"""
sample_skill/skill.py — Example skill implementation.

The execute() function is the entry point called by the skill_loader.
"""

def execute(**kwargs) -> str:
    name = kwargs.get("name", "there")
    return f"Hello, {name}! This is the sample skill speaking."
