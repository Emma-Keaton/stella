"""Live validation of the SGP4 propagator against wheretheiss.at (not a repo test)."""
import json
import math
import time
import urllib.request
from datetime import datetime, timezone

from core.astro.sgp4 import Satrec, geodetic_from_eci, julian_from_datetime


def get(url, timeout=20):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "StellaAI/1.0"}), timeout=timeout
    ).read()


tle = get("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE").decode().strip().splitlines()
print("TLE lines:", len(tle))
sat = Satrec.twoline2rv(tle[1], tle[2])
print("describe:", json.dumps(sat.describe()))

errors = []
for i in range(3):
    api = json.loads(get("https://api.wheretheiss.at/v1/satellites/25544", timeout=10))
    jd = julian_from_datetime(datetime.fromtimestamp(api["timestamp"], tz=timezone.utc))
    pos, vel, err = sat.sgp4(jd)
    geo = geodetic_from_eci(pos, jd)
    dlat = (geo["latitude"] - api["latitude"]) * 111.0
    dlon = (geo["longitude"] - api["longitude"]) * 111.0 * math.cos(math.radians(api["latitude"]))
    err_km = math.sqrt(dlat * dlat + dlon * dlon)
    errors.append(err_km)
    print(
        "sample %d: api=(%.4f,%.4f) ours=(%.4f,%.4f) error=%.1f km alt=%.1f km speed=%.3f km/s"
        % (i, api["latitude"], api["longitude"], geo["latitude"], geo["longitude"],
           err_km, geo["altitude_km"], math.sqrt(sum(v * v for v in vel)))
    )
    time.sleep(3)

print("max error: %.1f km (plan allows 40 km)" % max(errors))
