"""Live pass prediction check against the ISS (not a repo test)."""
import json
import math
import urllib.request
from datetime import datetime, timezone

from core.astro.passes import predict_passes, look_angles, observer_ecef
from core.astro.sgp4 import Satrec, ecef_from_eci, julian_from_datetime


def get(url, timeout=20):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "StellaAI/1.0"}), timeout=timeout
    ).read()


tle = get("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE").decode().strip().splitlines()
sat = Satrec.twoline2rv(tle[1], tle[2])

observer_lat, observer_lon = 19.2183, 72.9781  # Kalyan, India
passes = predict_passes(sat, observer_lat, observer_lon, min_elevation_deg=10.0,
                        horizon_hours=36, step_seconds=30)

print("passes in 36h from Kalyan:", len(passes))
for p in passes[:4]:
    print(" -", p.summary(), "| sunlit:", p.sunlit)

api = json.loads(get("https://api.wheretheiss.at/v1/satellites/25544", timeout=10))
jd = julian_from_datetime(datetime.fromtimestamp(api["timestamp"], tz=timezone.utc))
pos, _, _ = sat.sgp4(jd)
angles = look_angles(ecef_from_eci(pos, jd), observer_lat, observer_lon)
print("current from Kalyan: elev %.1f deg, az %.1f, range %.0f km"
      % (angles["elevation_deg"], angles["azimuth_deg"], angles["range_km"]))
