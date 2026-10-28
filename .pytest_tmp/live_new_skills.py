"""Live smoke of the new skills, on this machine."""
import importlib.util
import json


def load(name):
    spec = importlib.util.spec_from_file_location(f"live_{name}", f"features/{name}/skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ww = load("world_watch")
wa = load("wireless_audit")
hc = load("hash_cracker")
sc = load("sound_check")

print("== world_watch ==")
for op, kwargs in (("flights", {"area": "Kalyan", "limit": "3"}),
                   ("earthquakes", {"area": "Kalyan"}),
                   ("wind", {"area": "Kalyan"}),
                   ("air_quality", {"area": "Kalyan"}),
                   ("radio", {"query": "jazz", "limit": "2"}),
                   ("satellites", {"limit": "2"}),
                   ("space_passes", {"lat": "19.2183", "lon": "72.9781", "hours": "6"})):
    r = ww.execute(operation=op, **kwargs)
    print(f"  {op}: ok={r['ok']} | {r['summary'][:150]}")

print("== wireless_audit ==")
for op in ("tools", "interfaces", "monitor", "survey", "sources"):
    r = wa.execute(operation=op)
    print(f"  {op}: ok={r['ok']} | {r['summary'][:170]}")

print("== hash_cracker ==")
for op, kwargs in (("tools", {}),
                   ("identify", {"hash": "5f4dcc3b5aa765d61d8327deb882cf99"}),
                   ("identify", {"hash": "$2y$10$abcdefghijklmnopqrstuv"}),
                   ("wordlists", {}),
                   ("crack", {"hash_file": "C:/tmp/nope.hc22000", "confirm": True})):
    r = hc.execute(operation=op, **kwargs)
    print(f"  {op}: ok={r['ok']} | {r['summary'][:160]}")

print("== sound_check ==")
for op, kwargs in (("diagnosis", {}), ("devices", {}), ("volume", {"volume": "45"})):
    r = sc.execute(operation=op, **kwargs)
    print(f"  {op}: ok={r['ok']} | {r['summary'][:170]}")

print("== handshake validator (real APK's manifest is not a pcap; use the ISS TLE data) ==")
from core.security import handshake

print("  file missing:", handshake.inspects_file("C:/tmp/not-there.cap")["reason"][:100])
