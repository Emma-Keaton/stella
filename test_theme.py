from core.theme_tokens import theme_manager, get_theme, get_token, list_themes

print("Themes:", list_themes())
for tid in list_themes():
    t = get_theme(tid)
    print(f"  {tid}: {len(t)} tokens, bg={t.get('bg')}, primary={t.get('primary')}")
print("Active:", theme_manager.active_theme)
theme_manager.active_theme = "light"
print("After switch:", theme_manager.active_theme)
print("Light bg:", get_token("bg"))
print("Void bg:", get_token("bg", "void"))