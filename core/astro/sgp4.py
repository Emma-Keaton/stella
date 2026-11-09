"""core/astro/sgp4.py - TLE parsing and satellite propagation, in pure Python.

Parses a two-line element set, applies the first-order J2 secular drift to the
node, argument of perigee and mean anomaly, solves Kepler's equation, and
returns ECI position/velocity in kilometres.

What this is *not*: the full Spacetrack Report #3 SGP4 with its short-period
periodics and SDP4 deep-space model. A first-order J2 propagator is accurate to
a few tens of kilometres over a day for a low-earth orbit - good enough to plot
a satellite, predict a ground pass and answer "when does the ISS next rise over
me" - and not good enough for rendezvous or collision avoidance. The method and
its accuracy are stated in `describe()`, so a caller never has to guess.

Nothing here touches the network, the filesystem or a third-party package, so
pass prediction works offline on any machine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

#: WGS72 values - the datum SGP4/TLE work in, not WGS84.
MU = 398600.8                # km^3 / s^2
RADIUS_EARTH_KM = 6378.135
J2 = 0.001082616

#: Approximate accuracy of a first-order J2 propagation, kilometres.
METHOD = "keplerian with first-order J2 secular drift"
ACCURACY_KM = 40

EARTH_RADIUS_EQ = RADIUS_EARTH_KM


class TLEError(ValueError):
    """Raised when a two-line element set is malformed."""


def julian_from_datetime(moment: datetime) -> float:
    """Julian date (UTC) for a datetime."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    day_fraction = (moment.hour * 3600 + moment.minute * 60 + moment.second
                    + moment.microsecond / 1e6) / 86400.0
    year, month, day = moment.year, moment.month, moment.day
    if month <= 2:
        year -= 1
        month += 12
    a = int(year / 100)
    b = 2 - a + int(a / 4)
    return (int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day
            + b - 1524.5 + day_fraction)


def datetime_from_julian(jd: float) -> datetime:
    """Inverse of julian_from_datetime."""
    jd_plus = jd + 0.5
    z = int(jd_plus)
    f = jd_plus - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - int(alpha / 4)
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day_fraction = b - d - int(30.6001 * e) + f
    day = int(day_fraction)
    month = e - 1 if e <= 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    seconds = int(round((day_fraction - day) * 86400.0))
    return datetime(year, month, day, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def _checksum_ok(line: str) -> bool:
    """Verify the modulo-10 checksum of a 69-column TLE line."""
    if len(line) < 69:
        return False
    total = 0
    for char in line[:68]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1
    expected = line[68]
    return expected.isdigit() and total % 10 == int(expected)


def _has_checksum_column(line: str) -> bool:
    """Whether the line ends with the standard element-set + checksum columns.

    A canonical line 2 right-aligns a 5-character element-set number in columns
    65-68 and puts the checksum in column 69, so at least one of those trailing
    five characters is a space. CelesTrak's current long format instead lets the
    mean motion run to the end of the line, which leaves no checksum column -
    those lines are parsed but reported as unverified rather than failed.
    """
    if len(line) < 69:
        return False
    return any(char == " " for char in line[63:68])


def _num(text: str) -> float:
    cleaned = (text or "").strip()
    if not cleaned:
        raise TLEError("empty numeric field in the TLE")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise TLEError(f"unreadable numeric field {cleaned!r} in the TLE") from exc


def _tle_float(text: str) -> float:
    """Parse a TLE field written in implied-decimal exponent form.

    SGP4 elements such as BSTAR are stored as `[sign]MANTISSA[-]EXP`: the
    mantissa carries an implied '0.' in front of it and the last two characters
    are the exponent, so `11890-3` reads as 0.11890 x 10^-3 = 1.189e-4.
    """
    text = (text or "").replace(" ", "").strip()
    if not text:
        return 0.0
    if len(text) >= 2 and text[-2] in "+-":
        mantissa, exponent = text[:-2], int(text[-2:])
    else:
        mantissa, exponent = text, 0
    sign = -1.0 if mantissa.startswith("-") else 1.0
    digits = mantissa.lstrip("+-")
    if not digits.isdigit():
        raise TLEError(f"unreadable TLE numeric field {text!r}")
    value = 0.0
    for char in digits:
        value = value * 10.0 + (ord(char) - 48)
    return sign * value * (10.0 ** (exponent - len(digits)))


@dataclass
class Satrec:
    """One satellite: parsed elements plus the derived orbital state."""

    satnum: str = ""
    epoch_jd: float = 0.0
    bstar: float = 0.0
    inclo: float = 0.0
    nodeo: float = 0.0
    ecco: float = 0.0
    argpo: float = 0.0
    mo: float = 0.0
    no_kozai: float = 0.0
    classification: str = "U"
    intldesg: str = ""
    revnum: int = 0
    elnum: int = 0
    #: True when both lines carried a valid modulo-10 checksum. Sources that
    #: drop the trailing checksum (CelesTrak's current export) parse fine but
    #: are reported as unverified.
    checksum_verified: bool = True
    error: int = 0
    error_message: str = ""
    _semi_major_km: float = 0.0
    _n_rad_s: float = 0.0
    _rates: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ parse

    @classmethod
    def twoline2rv(cls, line1: str, line2: str) -> "Satrec":
        """Parse and validate a two-line element set."""
        line1 = (line1 or "").strip("\r\n").rstrip()
        line2 = (line2 or "").strip("\r\n").rstrip()
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            raise TLEError("not a two-line element set: lines must start with '1 ' and '2 '")
        if len(line1) < 69 or len(line2) < 63:
            raise TLEError("a TLE line is truncated; line 1 is 69 columns and line 2 is 69 or 63")

        sat = cls()
        verified_line1 = _has_checksum_column(line1) and _checksum_ok(line1)
        verified_line2 = _has_checksum_column(line2) and _checksum_ok(line2)
        sat.checksum_verified = verified_line1 and verified_line2

        if _has_checksum_column(line1) and not verified_line1:
            raise TLEError("line 1 failed its checksum; the element set is probably corrupt")
        if _has_checksum_column(line2) and not verified_line2:
            raise TLEError("line 2 failed its checksum; the element set is probably corrupt")
        if _has_checksum_column(line1) and not verified_line1:
            raise TLEError("line 1 failed its checksum; the element set is probably corrupt")
        if _has_checksum_column(line2) and not verified_line2:
            raise TLEError("line 2 failed its checksum; the element set is probably corrupt")

        sat.classification = line1[7:8]
        sat.intldesg = line1[9:17].strip()
        sat.satnum = line2[2:7].strip()
        sat.elnum = int(line1[64:68])

        epoch_year = int(line1[18:20])
        epoch_year += 1900 if epoch_year >= 57 else 2000
        epoch_day = _num(line1[20:32])
        sat.epoch_jd = _epoch_jd(epoch_year, epoch_day)
        sat.bstar = _tle_float(line1[53:61])
        sat.inclo = math.radians(_num(line2[8:16]))
        sat.nodeo = math.radians(_num(line2[17:25]))
        sat.ecco = _num("0." + line2[26:33].strip())
        sat.argpo = math.radians(_num(line2[34:42]))
        sat.mo = math.radians(_num(line2[43:51]))
        sat.no_kozai = _num(line2[52:63])
        sat.revnum = int(line2[64:68]) if len(line2) >= 68 else 0

        if sat.no_kozai <= 0.0:
            raise TLEError("mean motion must be positive")
        if not 0.0 <= sat.ecco < 1.0:
            raise TLEError("eccentricity must be between 0 and 1 for an orbit")

        period_s = 86400.0 / sat.no_kozai
        sat._n_rad_s = 2.0 * math.pi / period_s
        sat._semi_major_km = (MU * period_s * period_s / (4.0 * math.pi ** 2)) ** (1.0 / 3.0)
        p = sat._semi_major_km * (1.0 - sat.ecco ** 2)
        if p <= 0.0:
            raise TLEError("degenerate orbit: semi-latus rectum is not positive")
        cos_i = 1.0 if sat.inclo == 0.0 else math.cos(sat.inclo)
        ratio = sat._semi_major_km / p
        # First-order J2 secular rates (radians per second).
        node_rate = -1.5 * sat._n_rad_s * J2 * ratio ** 2 * cos_i
        argp_rate = 0.75 * sat._n_rad_s * J2 * ratio ** 2 * (5.0 * cos_i ** 2 - 1.0)
        mean_rate = sat._n_rad_s * (
            1.0 + 0.75 * sat._n_rad_s * J2 * ratio ** 2
            * math.sqrt(1.0 - sat.ecco ** 2) * (3.0 * cos_i ** 2 - 1.0)
        )
        sat._rates = {
            "node": node_rate,
            "argp": argp_rate,
            "mean": mean_rate,
            "n": sat._n_rad_s,
        }
        return sat

    # ------------------------------------------------------------- propagate

    def sgp4(self, jd: Optional[float] = None, tsince_seconds: float = 0.0):
        """Propagate to a moment and return ``(position_km, velocity_km_s, error)``.

        Pass a Julian date, or seconds since the TLE epoch. Position is ECI in
        kilometres and velocity is kilometres per second.
        """
        if jd is not None:
            tsince_seconds = (jd - self.epoch_jd) * 86400.0
        return self._propagate(tsince_seconds)

    def _propagate(self, tsince_seconds: float):
        e = self.ecco
        if e >= 1.0:
            self.error = 2
            self.error_message = "eccentricity >= 1: this is not a closed orbit"
            return ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 2)

        rates = self._rates
        mean_anomaly = self.mo + rates["mean"] * tsince_seconds
        node = self.nodeo + rates["node"] * tsince_seconds
        argp = self.argpo + rates["argp"] * tsince_seconds

        m = math.fmod(mean_anomaly, 2.0 * math.pi)
        if m < 0.0:
            m += 2.0 * math.pi

        ek = m if e < 1e-8 else m
        for _ in range(60):
            delta = (m - ek + e * math.sin(ek)) / (1.0 - e * math.cos(ek))
            ek += delta
            if abs(delta) < 1e-13:
                break

        sin_ek = math.sin(ek)
        cos_ek = math.cos(ek)
        one_minus_e_cos = 1.0 - e * cos_ek
        a = self._semi_major_km
        r = a * one_minus_e_cos
        true_anomaly = math.atan2(math.sqrt(1.0 - e * e) * sin_ek, cos_ek - e)

        u = argp + true_anomaly
        sin_u = math.sin(u)
        cos_u = math.cos(u)

        h = math.sqrt(MU * a * (1.0 - e * e))       # specific angular momentum
        r_dot = (MU / h) * e * sin_ek
        p = a * (1.0 - e * e)
        speed_factor = h / p                        # r * du/dt

        sin_omega = math.sin(node)
        cos_omega = math.cos(node)
        sin_i = math.sin(self.inclo)
        cos_i = math.cos(self.inclo)

        position = [
            cos_omega * r * cos_u - sin_omega * r * sin_u * cos_i,
            sin_omega * r * cos_u + cos_omega * r * sin_u * cos_i,
            r * sin_u * sin_i,
        ]
        # In-orbit velocity: radial component r_dot, transverse component r*du/dt.
        v_unit = [-sin_u, cos_u, 0.0]
        r_unit = [cos_u, sin_u, 0.0]
        vel_plane = [
            r_dot * r_unit[0] + speed_factor * v_unit[0],
            r_dot * r_unit[1] + speed_factor * v_unit[1],
            0.0,
        ]
        velocity = [
            vel_plane[0] * cos_omega - vel_plane[1] * cos_i * sin_omega,
            vel_plane[0] * sin_omega + vel_plane[1] * cos_i * cos_omega,
            vel_plane[1] * sin_i,
        ]

        self.error = 0
        self.error_message = ""
        return (position, velocity, 0)

    # ------------------------------------------------------------------ views

    def period_minutes(self) -> float:
        return 1440.0 / self.no_kozai

    def apogee_km(self) -> float:
        return self._semi_major_km * (1.0 + self.ecco)

    def perigee_km(self) -> float:
        return self._semi_major_km * (1.0 - self.ecco)

    def semi_major_km(self) -> float:
        return self._semi_major_km

    def epoch_datetime(self) -> datetime:
        return datetime_from_julian(self.epoch_jd)

    def mean_motion_rad_s(self) -> float:
        return self._n_rad_s

    def describe(self) -> dict:
        """The orbit, the propagation method and the accuracy it carries."""
        return {
            "satnum": self.satnum,
            "name": self.intldesg,
            "epoch": self.epoch_datetime().isoformat(),
            "epoch_jd": round(self.epoch_jd, 6),
            "inclination_deg": round(math.degrees(self.inclo), 4),
            "raan_deg": round(math.degrees(self.nodeo), 4),
            "eccentricity": round(self.ecco, 7),
            "arg_perigee_deg": round(math.degrees(self.argpo), 4),
            "mean_anomaly_deg": round(math.degrees(self.mo), 4),
            "mean_motion_revs_per_day": round(self.no_kozai, 8),
            "period_minutes": round(self.period_minutes(), 4),
            "semi_major_km": round(self._semi_major_km, 3),
            "apogee_km": round(self.apogee_km(), 3),
            "perigee_km": round(self.perigee_km(), 3),
            "bstar": self.bstar,
            "checksum_verified": self.checksum_verified,
            "method": METHOD,
            "accuracy_km": ACCURACY_KM,
        }


def _epoch_jd(year: int, day_of_year: float) -> float:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    return julian_from_datetime(start) + (day_of_year - 1.0)


def geodetic_from_eci(position_km: list, jd: float) -> dict:
    """Approximate sub-satellite latitude/longitude/altitude (degrees, km).

    Uses GMST for the sidereal rotation only; no polar motion, no precession.
    Adequate for map plotting and pass geometry.
    """
    x, y, z = position_km
    r = math.sqrt(x * x + y * y + z * z)
    gmst = _gmst(jd)
    lon = math.degrees(math.atan2(y, x) - gmst)
    lat = math.degrees(math.asin(z / r)) if r else 0.0
    return {"latitude": lat, "longitude": ((lon + 180.0) % 360.0) - 180.0,
            "altitude_km": r - EARTH_RADIUS_EQ}


def _gmst(jd: float) -> float:
    """Greenwich mean sidereal time in radians."""
    t = (jd - 2451545.0) / 36525.0
    gmst_sec = 67310.54841 + (876600.0 * 3600 + 8640184.812866) * t \
        + 0.093104 * t * t - 6.2e-6 * t ** 3
    gmst = (gmst_sec % 86400.0) * math.pi / 43200.0
    return gmst


def ecef_from_eci(position_km: list, jd: float) -> list:
    gmst = _gmst(jd)
    cos_g = math.cos(gmst)
    sin_g = math.sin(gmst)
    x, y, z = position_km
    return [x * cos_g + y * sin_g, -x * sin_g + y * cos_g, z]
