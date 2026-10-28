"""Smoke the world_watch skill's offline paths."""
import importlib.util
import json

spec = importlib.util.spec_from_file_location("world_watch", "features/world_watch/skill.py")
skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill)

print("manifest ok:", bool(json.load(open("features/world_watch/manifest.json"))))

r = skill.execute(operation="sources")
print("sources keys:", sorted(r.keys()))
if "summary" not in r:
    print("   error:", r.get("error"))
    raise SystemExit(1)
print("sources ok:", r["ok"], "|", r["summary"][:110])

r = skill.execute(operation="bogus")
print("bad op:", r["ok"], "|", r["summary"][:130])

r = skill.execute(operation="flights", area="Kalyan")
print("flights:", r["ok"], "|", r["summary"][:260])
if not r["ok"]:
    print("   error:", r["record"]["error"][:160])

r = skill.execute(operation="space_passes", lat="19.2183", lon="72.9781", hours="6")
print("passes:", r["ok"], "|", r["summary"][:300])

r = skill.execute(operation="earthquakes", area="Kalyan")
print("quakes:", r["ok"], "|", r["summary"][:220])

r = skill.execute(operation="wind", area="Kalyan")
print("wind:", r["ok"], "|", r["summary"][:220])

r = skill.execute(operation="air_quality", area="Kalyan")
print("air:", r["ok"], "|", r["summary"][:220])

r = skill.execute(operation="fires", area="Kalyan")
print("fires (no key):", r["ok"], "|", r["summary"][:220])

r = skill.execute(operation="vessels")
print("vessels (no key):", r["ok"], "|", r["summary"][:220])

r = skill.execute(operation="radio", category="jazz", limit="3")
print("radio:", r["ok"], "|", r["summary"][:200])

r = skill.execute(operation="street_level", area="Kalyan")
print("street:", r["ok"], "|", r["summary"][:220])

r = skill.execute(operation="satellites", category="stations", limit="3")
print("satellites:", r["ok"], "|", r["summary"][:240])

r = skill.execute(operation="military_flights", area="Kalyan", radius_km="300")
print("military:", r["ok"], "|", r["summary"][:220])
