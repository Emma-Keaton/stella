# Skill: theme_tokens

Lightweight theme-token reader for Stella skills. Reads the single source of truth (themes.json) so skills never ship hardcoded colours.

## Usage

```python
from skills.theme_tokens import token, active_theme_id, theme_colour

bg = token("bg")                 # active theme
mint = token("primary", "void")  # specific theme
bg_hex = theme_colour("bg")      # same as token, returns str or None
```

## Functions

- `list_themes()` - Return every theme id defined in themes.json
- `active_theme_id()` - Return the active theme id (defaults to "void")
- `token(key, theme_id?)` - Return the value of a single token key for a theme
- `theme_colour(key, theme_id?)` - Alias of token that explicitly returns a colour string or None
- `all_tokens(theme_id?)` - Return every token for a theme, or an empty dict when missing

## Returns

Token values from themes.json for the requested theme. Returns None when the theme or token is missing.