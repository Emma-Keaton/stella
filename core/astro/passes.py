"""core/astro/passes.py - ground-pass prediction over the SGP4 propagator.

Steps a satellite's orbit at a fixed cadence, converts each position into the
observer's local horizon frame (azimuth, elevation, range), and reports the
windows where the satellite is above `min_elevation_deg`.

Honesty of the geometry:

* rise/set times are the first and last samples inside the window, so a pass
  never claims a time finer than `step_seconds`
* the observer is a point on a spherical earth: no refraction, no terrain, no
  horizon obstruction
* `sunlit` is a crude cone test about the sun direction, not an illumination
  model - it is reported per pass so a caller can say "estimates", never "fact"

Pass prediction is a geometry computation on the propagated orbit, not a
forecast service: it is only as good as the TLE age and the propagator
(see `core/astro/sgp4.py` for the stated accuracy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.astro.sgp4 import (
    Satrec,
    ecef_from_eci,
    julian_from_datetime,
)

EARTH_RADIUS_KM = 6378.135


@dataclass
class PassWindow:
    """One pass, as computed from propagated samples."""

    rise_time: Optional[datetime]
    peak_time: datetime
    set_time: Optional[datetime]
    max_elevation_deg: float
    duration_seconds: int
    rise_azimuth_deg: Optional[float]
    peak_azimuth_deg: float
    set_azimuth_deg: Optional[float]
    range_km_at_peak: float
    sunlit: Optional[bool]

    def as_dict(self) -> dict:
        return {
            "rise_time": self.rise_time.isoformat() if self.rise_time else None,
            "peak_time": self.peak_time.isoformat(),
            "set_time": self.set_time.isoformat() if self.set_time else None,
            "max_elevation_deg": round(self.max_elevation_deg, 1),
            "duration_seconds": self.duration_seconds,
            "rise_azimuth_deg": None if self.rise_azimuth_deg is None else round(self.rise_azimuth_deg, 1),
            "peak_azimuth_deg": round(self.peak_azimuth_deg, 1),
            "set_azimuth_deg": None if self.set_azimuth_deg is None else round(self.set_azimuth_deg, 1),
            "range_km_at_peak": round(self.range_km_at_peak, 1),
            "sunlit": self.sunlit,
        }

    def summary(self) -> str:
        rise = self.rise_time.strftime("%H:%M UTC") if self.rise_time else "already visible"
        peak = self.peak_time.strftime("%H:%M UTC")
        set_time = self.set_time.strftime("%H:%M UTC") if self.set_time else "still up at the horizon"
        return (
            f"Rises {rise}, peaks {peak} at {self.max_elevation_deg:.0f} degrees "
            f"from azimuth {self.peak_azimuth_deg:.0f}, sets {set_time} "
            f"({self.duration_seconds // 60} minutes)."
        )


def observer_ecef(latitude_deg: float, longitude_deg: float, altitude_km: float = 0.0) -> list:
    """An observer's ECEF position on a spherical earth."""
    lat = math.radians(latitude_deg)
    lon = math.radians(longitude_deg)
    radius = EARTH_RADIUS_KM + altitude_km
    return [
        radius * math.cos(lat) * math.cos(lon),
        radius * math.cos(lat) * math.sin(lon),
        radius * math.sin(lat),
    ]


def horizon_frame(latitude_deg: float, longitude_deg: float) -> tuple:
    """East / north / up unit vectors of the observer's local frame (ECEF)."""
    lat = math.radians(latitude_deg)
    lon = math.radians(longitude_deg)
    east = [-math.sin(lon), math.cos(lon), 0.0]
    north = [-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)]
    up = [math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)]
    return east, north, up


def look_angles(position_ecef: list, latitude_deg: float, longitude_deg: float) -> dict:
    """Azimuth (degrees clockwise from true north), elevation and range (km)."""
    east, north, up = horizon_frame(latitude_deg, longitude_deg)
    observer = observer_ecef(latitude_deg, longitude_deg)
    dx, dy, dz = (position_ecef[i] - observer[i] for i in range(3))
    east_dot = dx * east[0] + dy * east[1] + dz * east[2]
    north_dot = dx * north[0] + dy * north[1] + dz * north[2]
    up_dot = dx * up[0] + dy * up[1] + dz * up[2]
    range_km = math.sqrt(dx * dx + dy * dy + dz * dz)
    if range_km <= 0.0:
        return {"azimuth_deg": 0.0, "elevation_deg": 0.0, "range_km": 0.0}
    azimuth = math.degrees(math.atan2(east_dot, north_dot)) % 360.0
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, up_dot / range_km))))
    return {"azimuth_deg": azimuth, "elevation_deg": elevation, "range_km": range_km}


def _gmst_rad(jd: float) -> float:
    return math.radians((280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0)


def _sun_ecef(jd: float) -> list:
    """A low-precision sun position in ECEF - adequate for a sunlit estimate."""
    days = jd - 2451545.0
    mean_longitude = math.radians((280.460 + 0.9856474 * days) % 360.0)
    mean_anomaly = math.radians((357.528 + 0.9856003 * days) % 360.0)
    ecliptic_longitude = mean_longitude + math.radians(
        1.915 * math.sin(mean_anomaly) + 0.020 * math.sin(2.0 * mean_anomaly))
    obliquity = math.radians(23.439 - 0.0000004 * days)
    sun = [
        math.cos(ecliptic_longitude),
        math.cos(obliquity) * math.sin(ecliptic_longitude),
        math.sin(obliquity) * math.sin(ecliptic_longitude),
    ]
    theta = _gmst_rad(jd)
    cos_g, sin_g = math.cos(theta), math.sin(theta)
    return [
        sun[0] * cos_g + sun[1] * sin_g,
        -sun[0] * sin_g + sun[1] * cos_g,
        sun[2],
    ]


def sunlit(position_ecef: list, jd: float) -> bool:
    """Whether the satellite is in sunlight - a cone test, not a shadow model."""
    sun = _sun_ecef(jd)
    norm = math.sqrt(sum(c * c for c in sun)) or 1.0
    radius = math.sqrt(sum(c * c for c in position_ecef)) or 1.0
    if radius <= 0.0:
        return False
    return (sum(sun[i] * position_ecef[i] for i in range(3)) / (norm * radius)) >= -0.15


def predict_passes(
    sat: Satrec,
    latitude_deg: float,
    longitude_deg: float,
    min_elevation_deg: float = 10.0,
    horizon_hours: float = 48.0,
    step_seconds: float = 30.0,
    start: Optional[datetime] = None,
) -> list:
    """Find the passes above `min_elevation_deg` inside the horizon window.

    Every pass is built from samples that were actually evaluated, so a pass
    cannot report a crossing finer than the step size.
    """
    if not 0.0 < step_seconds <= 600.0:
        raise ValueError("step_seconds must be greater than 0 and at most 600")
    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("latitude must be between -90 and 90 decimal degrees (south is negative)")
    start = start or datetime.now(timezone.utc)
    total_steps = int(horizon_hours * 3600.0 / step_seconds)

    passes: list = []
    samples: list = []

    for step in range(total_steps + 1):
        moment = start + timedelta(seconds=step * step_seconds)
        jd = julian_from_datetime(moment)
        position, _velocity, error = sat.sgp4(jd)
        if error:
            break
        ecef = ecef_from_eci(position, jd)
        angles = look_angles(ecef, latitude_deg, longitude_deg)
        if angles["elevation_deg"] >= min_elevation_deg:
            samples.append((moment, angles, ecef, jd))
        else:
            if len(samples) >= 2:
                passes.append(_window_from(samples))
            samples = []

    if len(samples) >= 2:
        passes.append(_window_from(samples))
    return passes


def _window_from(samples: list) -> PassWindow:
    first_moment, first_angles, _first_ecef, _first_jd = samples[0]
    peak_moment, peak_angles, peak_ecef, peak_jd = max(
        samples, key=lambda s: s[1]["elevation_deg"])
    last_moment, last_angles, _last_ecef, _last_jd = samples[-1]
    return PassWindow(
        rise_time=first_moment,
        peak_time=peak_moment,
        set_time=last_moment,
        max_elevation_deg=peak_angles["elevation_deg"],
        duration_seconds=int((last_moment - first_moment).total_seconds()),
        rise_azimuth_deg=first_angles["azimuth_deg"],
        peak_azimuth_deg=peak_angles["azimuth_deg"],
        set_azimuth_deg=last_angles["azimuth_deg"],
        range_km_at_peak=peak_angles["range_km"],
        sunlit=sunlit(peak_ecef, peak_jd),
    )


def filter_by_sunlight(passes: list, want_sunlit: Optional[bool]) -> list:
    """Keep the passes matching a requested sunlight estimate."""
    if want_sunlit is None:
        return passes
    return [p for p in passes if p.sunlit is want_sunlit]
