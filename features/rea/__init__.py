"""Stella reverse-engineer-anything skill package."""

try:
    from features.theme_tokens import all_tokens, active_theme_id, list_themes, token, theme_colour
except Exception:  # features package may not be on sys.path when loaded standalone
    import sys
    from pathlib import Path
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from theme_tokens import all_tokens, active_theme_id, list_themes, token, theme_colour

__all__ = ["all_tokens", "active_theme_id", "list_themes", "token", "theme_colour"]
