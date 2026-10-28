import importlib.util

spec = importlib.util.spec_from_file_location("world_watch", "features/world_watch/skill.py")
skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill)

tle = "\n".join([
    "ISS (ZARYA)",
    "1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995",
    "2 25544  51.6337  11.7282 0006920 310.9581  49.0806 15.49059765592065",
    "",
])

from core.astro.sgp4 import Satrec

print("direct parse:")
try:
    sat = Satrec.twoline2rv(tle.splitlines()[1], tle.splitlines()[2])
    print("  ok:", sat.satnum)
except Exception as exc:
    print("  FAIL:", type(exc).__name__, exc)

# Call the internals the way the skill does.
kwargs = {"operation": "satellites", "limit": "1"}


class FakeHttp:
    @staticmethod
    def get_text(url, **kw):
        return {"ok": True, "value": tle, "url": url}

    @staticmethod
    def get_json(url, **kw):
        return {"ok": False, "failure": "network", "reason": "offline"}


skill_http = skill._http()
skill._http = lambda: FakeHttp
result = skill._op_satellites(kwargs)
print("satellites record:", result)

result = skill._op_space_passes({"lat": "19.2", "lon": "72.9", "hours": "6"})
print("passes record:", result)
