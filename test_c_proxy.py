from ui import C

print("Void theme (default):")
print(f"  C.BG = {C.BG}")
print(f"  C.TEXT = {C.TEXT}")
print(f"  C.PRI = {C.PRI}")
print(f"  C.ACC = {C.ACC}")
print(f"  C.PANEL = {C.PANEL}")
print(f"  C.BORDER = {C.BORDER}")
print(f"  C.GREEN = {C.GREEN}")
print(f"  C.RED = {C.RED}")

C.set_theme("light")
print("\nLight theme:")
print(f"  C.BG = {C.BG}")
print(f"  C.TEXT = {C.TEXT}")
print(f"  C.PRI = {C.PRI}")
print(f"  C.ACC = {C.ACC}")

C.set_theme("oled")
print("\nOLED theme:")
print(f"  C.BG = {C.BG}")
print(f"  C.TEXT = {C.TEXT}")

C.set_theme("aurora")
print("\nAurora theme:")
print(f"  C.BG = {C.BG}")
print(f"  C.PRI = {C.PRI}")
print(f"  C.ICE = {C.ICE}")