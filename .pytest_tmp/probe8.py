import importlib.util
import json
import urllib.request

spec = importlib.util.spec_from_file_location("world_watch", "features/world_watch/skill.py")
skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill)

print("geocode Kalyan:", skill._geocode("Kalyan"))
print("bounds Kalyan:", skill._bounds({"area": "Kalyan"}))

from core.net import http

fetched = http.get_text("https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=TLE",
                        timeout=15.0)
print("tle ok:", fetched.get("ok"), "bytes:", fetched.get("bytes"))
lines = [l for l in str(fetched.get("value") or "").splitlines() if l.strip()]
print("lines:", len(lines))
for i in range(0, 9):
    print(" ", i, repr(lines[i][:70]))
try:
    from core.astro.sgp4 import Satrec
    sat = Satrec.twoline2rv(lines[1], lines[2])
    print("parsed:", sat.satnum, round(sat.period_minutes(), 3))
except Exception as exc:
    print("PARSE FAIL:", type(exc).__name__, exc)

for url in (
    "https://api.adsb.lol/v2/lat/19.2/lon/72.9/dist/100",
    "https://api.adsb.lol/v2/lat/19.2/lon/72.9/dist/250",
    "https://api.adsb.lol/v2/point/19.2/72.9/100",
):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "StellaAI/1.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read())
        print("OK  ", url, "->", body.get("ac", []).__len__(), "contacts")
    except Exception as exc:
        print("FAIL", url, "->", type(exc).__name__, exc)
