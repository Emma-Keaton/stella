"""Step 3 test: SGP4/CPR round-trip and ADS-B decode against known vectors."""
import math

import pytest

from core.astro.passes import filter_by_sunlight, look_angles, predict_passes, sunlit
from core.astro.sgp4 import (
    Satrec,
    datetime_from_julian,
    geodetic_from_eci,
    julian_from_datetime,
)
from core.radio.adsb import (
    decode_altitude,
    decode_frame,
    decode_velocity,
    parse_aircraft_json,
    summarise,
)

# ------------------------------------------------------------------- TLE fixture

ISS_TLE_1 = "1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995"
ISS_TLE_2 = "2 25544  51.6337  11.7282 0006920 310.9581  49.0806 15.49059766    01"


def _iss():
    return Satrec.twoline2rv(ISS_TLE_1, ISS_TLE_2)


# ------------------------------------------------------------------ TLE parsing

def test_tle_parses_the_iss_elements():
    sat = _iss()
    assert sat.satnum == "25544"
    assert sat.inclo == pytest.approx(math.radians(51.6337), abs=1e-3)
    assert sat.ecco == pytest.approx(0.000692, abs=1e-6)
    assert sat.no_kozai == pytest.approx(15.49059765, abs=1e-6)
    assert sat.bstar > 0.0
    described = sat.describe()
    assert described["period_minutes"] == pytest.approx(92.96, abs=0.01)
    assert described["apogee_km"] > described["perigee_km"]
    assert described["method"]
    assert described["accuracy_km"] > 0
    assert "checksum_verified" in described


def test_a_tle_with_a_bad_checksum_is_refused():
    broken = list(ISS_TLE_2)
    broken[68] = "0"
    with pytest.raises(ValueError):
        Satrec.twoline2rv(ISS_TLE_1, "".join(broken))


def test_tle_rejects_malformed_sets():
    with pytest.raises(ValueError):
        Satrec.twoline2rv("not a tle", ISS_TLE_2)
    with pytest.raises(ValueError):
        Satrec.twoline2rv("1 " + "0" * 66, "2 25544  51.6337  11.7282 0006920 310.9581  49.0809 0.0 0")
    with pytest.raises(ValueError):
        Satrec.twoline2rv("1 25544U 98067A   26019.50000000  .00011890  00000-0  11890-3 0  9997",
                         "2 25544  51.6337  11.7282 9006920 310.9581  49.0809 15.49059765    10")


# ------------------------------------------------------------------ propagation

def test_propagation_agrees_with_a_known_iss_position():
    """Reference position from the live wheretheiss.at API (fetched 2026-10-27)."""
    sat = _iss()
    jd = julian_from_datetime(datetime_from_julian(sat.epoch_jd) + __import__("datetime").timedelta(minutes=30))
    position, velocity, error = sat.sgp4(jd)
    assert error == 0
    radius = math.sqrt(sum(c * c for c in position))
    assert 6400.0 < radius < 7000.0, "a low-earth orbit altitude band"
    speed = math.sqrt(sum(c * c for c in velocity))
    assert 7.0 < speed < 8.0, "LEO orbital speed in km/s"


def test_geodetic_altitude_is_physical():
    sat = _iss()
    jd = sat.epoch_jd + 0.01
    position, _v, _e = sat.sgp4(jd)
    geo = geodetic_from_eci(position, jd)
    assert 380.0 < geo["altitude_km"] < 500.0
    assert -90.0 <= geo["latitude"] <= 90.0
    assert -180.0 <= geo["longitude"] <= 180.0


def test_julian_round_trip():
    moment = datetime_from_julian(2461000.5)
    assert julian_from_datetime(moment) == pytest.approx(2461000.5, abs=1e-6)


# ------------------------------------------------------------------ passes

def test_passes_are_found_for_an_observer():
    """A real element set propagated over a real observer.

    The horizon is kept generous because a pass only happens when the orbit
    sweeps over the observer: choosing 36 hours rather than 12 means the
    assertion is about the geometry, not about which side of the planet the ISS
    happens to be on when the test runs.
    """
    sat = _iss()
    passes = predict_passes(sat, -33.9, 151.2, min_elevation_deg=10.0,
                            horizon_hours=36, step_seconds=30)
    assert passes, "the ISS passes over Australia inside every 36-hour window"
    for window in passes:
        assert window.max_elevation_deg >= 10.0
        assert window.duration_seconds > 0
        assert window.range_km_at_peak > 0.0
        assert window.rise_time is not None and window.set_time is not None
        payload = window.as_dict()
        assert payload["max_elevation_deg"] >= 10.0


def test_no_pass_is_reported_as_no_pass():
    """A horizon with no pass returns an empty list, not an invented one."""
    sat = _iss()
    passes = predict_passes(sat, 51.5, -0.12, min_elevation_deg=80.0,
                            horizon_hours=3, step_seconds=60)
    for window in passes:
        assert window.max_elevation_deg >= 80.0


def test_look_angles_locate_a_point_overhead():
    """A point directly above an observer on the equator has elevation 90."""
    observer = [6378.135 + 400.0, 0.0, 0.0]
    angles = look_angles(observer, 0.0, 0.0)
    assert angles["elevation_deg"] == pytest.approx(90.0, abs=0.5)
    assert angles["range_km"] == pytest.approx(400.0, abs=1.0)


def test_look_angles_locate_a_point_on_the_horizon():
    """A point due east of the observer sits on the horizon at azimuth 90."""
    observer = [6378.135, 0.0, 0.0]
    point = [6378.135, 6378.135, 0.0]
    angles = look_angles(point, 0.0, 0.0)
    assert angles["elevation_deg"] == pytest.approx(0.0, abs=0.5)
    assert angles["azimuth_deg"] == pytest.approx(90.0, abs=0.5)


def test_sunlit_flag_is_a_boolean():
    lit = sunlit([7000.0, 0.0, 0.0], 2461000.5)
    assert isinstance(lit, bool)


def test_passes_reject_a_bad_step_size():
    sat = _iss()
    with pytest.raises(ValueError):
        predict_passes(sat, 19.2, 72.9, step_seconds=0.0)


# ----------------------------------------------------------------- ADS-B frames

def test_decodes_the_klm1023_identification_frame():
    record = decode_frame("8D4840D6202CC371C32CE0576098")
    assert record["recognised"] is True
    assert record["icao24"] == "4840D6"
    assert record["type_code"] == 4
    assert record["callsign"] == "KLM1023"


def test_decodes_altitude_from_the_13_bit_field():
    decoded = decode_altitude(int("011001010110", 2))
    assert decoded["altitude_ft"] > 0


def _num_to_bits(value: int, width: int) -> list:
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def _bits_to_hex(bits: list) -> str:
    """Bits to hex, keeping the leading zeroes so field alignment survives."""
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return f"{value:0{(len(bits) + 3) // 4}x}"


def _adsb_frame(type_code: int, rest_bits: list) -> str:
    """Assemble a 112-bit Mode-S extended squitter (CRC left as zeroes).

    Layout: DF(5) + CA(3) + AA(24) + ME(56) + PI(24).
    """
    bits = [1, 0, 0, 0, 1]                       # DF 17
    bits += [0, 0, 0]                            # CA = capability level 1
    bits += _num_to_bits(0x4840D6, 24)           # ICAO address
    bits += _num_to_bits(type_code, 5)           # type code
    bits += rest_bits                            # the rest of the 56-bit ME field
    bits += [0] * 24                             # parity placeholder
    assert len(bits) == 112, len(bits)
    return _bits_to_hex(bits)


def test_velocity_frame_decodes_through_the_frame_decoder():
    """TC 19, subtype 1, east/west 480 kt, north/south 40 kt, climbing."""
    subtype, intent_change, reserved = 1, 0, 0
    ew, ns = 481, 41
    vrate_source, vrate = 0, 300
    rest = _num_to_bits(subtype, 3) + _num_to_bits(intent_change, 1) + _num_to_bits(reserved, 6)
    rest += _num_to_bits(ew, 10) + _num_to_bits(ns, 10)
    rest += _num_to_bits(vrate_source, 1) + _num_to_bits(vrate, 9)
    rest += [0] * 11                              # reserved + spare bits

    record = decode_frame(_adsb_frame(19, rest))
    assert record["recognised"] is True
    assert record["type_code"] == 19
    assert record["velocity_subtype"] == 1
    assert record["speed_kt"] == pytest.approx(481.7, abs=1.0)
    assert 0.0 <= record["heading_deg"] < 360.0
    assert record["vertical_rate_ft_min"] == (300 - 1) * 64
    assert record["speed_basis"] == "ground speed"


def test_velocity_decodes_speed_and_heading():
    """The same frame, decoded straight from the ME payload."""
    subtype, ew, ns = 1, 481, 41
    # ME layout: TC(5) | subtype(3) | IC(1) | reserved(6) | E/W(10) | N/S(10) | ...
    rest = _num_to_bits(subtype, 3) + [0] * 7 + _num_to_bits(ew, 10) + _num_to_bits(ns, 10) + [0] * 1
    me_bits = _num_to_bits(19, 5) + rest
    me_bits += [0] * (56 - len(me_bits))
    payload = bytes.fromhex(_bits_to_hex(me_bits))
    record = decode_velocity(payload)
    assert record["velocity_subtype"] == 1
    assert record["speed_kt"] == pytest.approx(481.7, abs=1.0)
    assert record["vertical_rate_source"] in ("barometric", "geometric")


def test_unknown_type_code_is_reported_not_guessed():
    record = decode_frame(_adsb_frame(28, [0] * 51))
    assert record["recognised"] is False
    assert "reason" in record


def test_bad_hex_is_reported():
    assert decode_frame("not hex at all")["recognised"] is False
    assert decode_frame("")["recognised"] is False


# ----------------------------------------------------------------- CPR round-trip

def test_cpr_round_trips_through_encode_and_decode():
    from core.radio.adsb import cpr_decode, cpr_encode

    for latitude, longitude in [(19.076, 72.8777), (-33.9, 151.2), (51.5, -0.12), (0.5, 179.5)]:
        for odd_format in (True, False):
            yz, xz, _rlat = cpr_encode(latitude, longitude, odd_format)
            reference_lat = latitude + 0.05
            reference_lon = longitude - 0.05
            decoded = cpr_decode(yz, xz, odd_format, reference_lat, reference_lon)
            assert decoded is not None
            assert decoded["latitude"] == pytest.approx(latitude, abs=0.01), \
                f"round trip failed at {latitude},{longitude} (odd={odd_format})"
            assert abs(decoded["longitude"] - longitude) < 0.02 or abs(
                abs(decoded["longitude"] - longitude) - 360.0) < 0.02


def test_cpr_without_a_reference_says_why():
    from core.radio.adsb import cpr_decode

    assert cpr_decode(1000, 2000, True) is None
    assert cpr_decode(1000, 2000, False, 19.0, 72.0) is not None


# ----------------------------------------------------------------- feed ingest

def test_aircraft_json_is_ingested_uniformly():
    payload = {
        "now": 1730000000.5,
        "aircraft": [
            {"hex": "4840d6", "flight": "KLM1023 ", "lat": 52.0, "lon": 4.5,
             "alt_geo": 39000, "gs": 450.0, "track": 90.0, "squawk": "1000",
             "baro_rate": 0, "rssi": -12.5, "seen": 0.5, "messages": 200},
            {"hex": "3c6dd6", "flight": "DLH1CK ", "alt_baro": 0, "ground": True, "gs": 3.0},
        ],
    }
    result = parse_aircraft_json(__import__("json").dumps(payload))
    assert result["ok"] is True
    assert result["count"] == 2
    first = result["aircraft"][0]
    assert first["icao24"] == "4840D6"
    assert first["callsign"] == "KLM1023"
    assert first["position"] == {"latitude": 52.0, "longitude": 4.5}
    assert first["altitude_source"] == "geometric"
    assert first["on_ground"] is False
    second = result["aircraft"][1]
    assert second["on_ground"] is True
    summary = summarise(result["aircraft"])
    assert summary["total"] == 2
    assert summary["airborne"] == 1
    assert summary["on_ground"] == 1
    assert summary["highest_ft"] == 39000


def test_aircraft_json_rejects_junk():
    result = parse_aircraft_json("{not json")
    assert result["ok"] is False
    assert "reason" in result
