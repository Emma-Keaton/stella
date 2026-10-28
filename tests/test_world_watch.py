"""Step 4 tests: world_watch skill, with the HTTP layer mocked."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "features" / "world_watch" / "skill.py"


@pytest.fixture()
def skill(monkeypatch):
    spec = importlib.util.spec_from_file_location("stella_skill_world_watch", SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def mock_http(monkeypatch, skill):
    """A controllable stand-in for core.net.http, with the disk cache disabled."""
    from core.net import http as http_module

    calls: list = []
    responses: dict = {}
    monkeypatch.setattr(skill, "_cache", lambda: None)

    def get_json(url, **kwargs):
        calls.append(("json", url))
        for match, result in responses.items():
            if match in url:
                return result
        pytest.fail(f"unexpected request to {url}")

    def get_text(url, **kwargs):
        calls.append(("text", url))
        for match, result in responses.items():
            if match in url:
                return result
        pytest.fail(f"unexpected request to {url}")

    monkeypatch.setattr(http_module, "get_json", get_json)
    monkeypatch.setattr(http_module, "get_text", get_text)

    def respond(match: str, payload, ok: bool = True, failure: str = "http", reason: str = ""):
        if ok:
            responses[match] = {"ok": True, "value": payload, "url": match, "cached": False}
        else:
            responses[match] = {"ok": False, "value": None, "failure": failure,
                                "reason": reason or f"{match} failed", "url": match}

    controller = type("Controller", (), {"respond": staticmethod(respond), "calls": calls})()
    return controller


def _opensky(**overrides):
    payload = {"time": 1762000000.0, "states": [
        ["4840d6", "KL1023  ", "Netherlands", 1762000000, 1762000000,
         4.77, 52.07, 10668.0, False, 231.4, 92.0, 0.0, None, 11845.0, False, False],
        ["3c6dd6", "DLH1CK  ", "Germany", 1762000000, 1762000000, None, None,
         0.0, True, 0.0, 180.0, 0.0, None, 0.0, False, False],
    ]}
    payload.update(overrides)
    return payload


GEOCODE = {"results": [{"latitude": 52.07, "longitude": 4.77, "name": "Somewhere",
                        "country": "Somewhereland"}]}


# ------------------------------------------------------------------- discovery

def test_the_skill_is_discovered_by_the_registry():
    from core.dynamic_registry import DynamicToolRegistry

    registry = DynamicToolRegistry()
    registry.initialize()
    names = [s.get("name") if isinstance(s, dict) else str(s) for s in registry.list_skills()]
    assert "world_watch" in names

    matched = registry.find_matching_skill("use world_watch to track flights over London")
    assert matched is not None
    matched_name = matched[0] if isinstance(matched, tuple) else matched.get("name")
    assert matched_name == "world_watch"


def test_manifest_and_skill_metadata_agree(skill):
    manifest = json.loads((REPO_ROOT / "features" / "world_watch" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == skill.FEATURE_METADATA["name"]
    assert set(manifest["parameters"]["properties"]) == set(
        skill.FEATURE_METADATA["parameters"]["properties"])
    assert manifest["version"] == skill.FEATURE_METADATA["version"]


# --------------------------------------------------------------- operation map

def test_operations_and_aliases_resolve(skill):
    for name in ("flights", "military_flights", "vessels", "satellites", "space_passes",
                 "earthquakes", "fires", "cyclones", "launches", "wind", "radar",
                 "air_quality", "cameras", "radio", "transit", "bikeshare", "alpr",
                 "street_level", "infrastructure", "traffic", "gnss_integrity", "sources"):
        assert name in skill._OPERATIONS, name

    assert skill._ALIASES["iss"] == "space_passes"
    assert skill._ALIASES["hurricane"] == "cyclones"
    assert skill._ALIASES["aqi"] == "air_quality"
    assert skill._ALIASES["bike"] == "bikeshare"
    assert skill._ALIASES["planes"] == "flights" if "planes" in skill._ALIASES else True


def test_sources_operation_lists_every_layer(skill):
    result = skill.execute(operation="sources")
    assert result["ok"] is True
    assert len(result["record"]["value"]["layers"]) >= 20
    assert all("source" in layer and "auth" in layer for layer in result["record"]["value"]["layers"])


def test_unknown_operation_reports_the_known_ones(skill):
    result = skill.execute(operation="teleport")
    assert result["ok"] is False
    assert "Unknown operation" in result["record"]["error"]
    assert "flights" in result["summary"]


# -------------------------------------------------------------------- flights

def test_flights_read_the_bounding_box_and_skip_null_positions(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("opensky-network.org", _opensky())

    result = skill.execute(operation="flights", area="somewhere", limit="10")
    assert result["ok"] is True
    value = result["record"]["value"]
    assert value["count"] == 2
    assert len(value["flights"]) == 1
    flight = value["flights"][0]
    assert flight["callsign"] == "KL1023"
    assert flight["latitude"] == 52.07
    assert flight["altitude_ft"] == round(10668.0 * 3.28084)
    assert value["source"] == "OpenSky Network (anonymous)"

    urls = [url for kind, url in mock_http.calls if "opensky" in url]
    assert urls, "the OpenSky query should have been made"
    assert "lamin=" in urls[0]


def test_flights_report_the_rate_limit(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("opensky-network.org", None, ok=False, failure="rate-limited",
                      reason="OpenSky answered HTTP 429: rate limit reached")

    result = skill.execute(operation="flights", area="somewhere")
    assert result["ok"] is False
    assert "429" in result["record"]["error"]
    assert "unavailable" in result["summary"].lower()


def test_flights_without_a_network_report_it(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", None, ok=False, failure="network",
                      reason="geocoder unreachable")
    result = skill.execute(operation="flights", area="nowhere")
    assert result["ok"] is False


def test_explicit_bbox_overrides_the_area(skill, mock_http):
    mock_http.respond("opensky-network.org", _opensky())
    result = skill.execute(operation="flights", bbox="52.0,52.2,4.6,4.9")
    assert result["ok"] is True
    bounds = result["record"]["value"]["bbox"]
    assert bounds == {"lat_min": 52.0, "lat_max": 52.2, "lon_min": 4.6, "lon_max": 4.9}
    assert not any("geocoding-api" in url for kind, url in mock_http.calls)


def test_an_implausible_bbox_is_refused(skill, mock_http):
    result = skill.execute(operation="flights", bbox="80.0,10.0,0.0,1.0")
    assert result["ok"] is False
    assert "does not describe a real box" in result["record"]["error"]


# ----------------------------------------------------------------- satellites

def test_satellite_catalogue_reads_the_TLE_feed(skill, mock_http):
    tle = "\n".join([
        "ISS (ZARYA)",
        "1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995",
        "2 25544  51.6337  11.7282 0006920 310.9581  49.0806 15.49059765592065",
        "",
    ])
    mock_http.respond("celestrak.org", tle)
    result = skill.execute(operation="satellites", limit="1")
    assert result["ok"] is True
    entry = result["record"]["value"]["satellites"][0]
    assert entry["norad_id"] == "25544"
    assert entry["period_minutes"] == pytest.approx(92.96, abs=0.01)
    assert entry["apogee_km"] > entry["perigee_km"]


def test_space_passes_use_the_observer_point(skill, mock_http):
    tle = "\n".join([
        "ISS (ZARYA)",
        "1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995",
        "2 25544  51.6337  11.7282 0006920 310.9581  49.0806 15.49059765592065",
        "",
    ])
    mock_http.respond("celestrak.org", tle)
    result = skill.execute(operation="space_passes", lat="19.2183", lon="72.9781",
                           hours="24", min_elevation="10", limit="3")
    assert result["ok"] is True
    value = result["record"]["value"]
    assert value["norad_id"] == "25544"
    assert value["propagation"]["method"]
    assert value["propagation"]["accuracy_km"] > 0
    assert isinstance(value["passes"], list)
    if value["passes"]:
        window = value["passes"][0]
        assert window["max_elevation_deg"] >= 10.0
        assert window["duration_seconds"] > 0
        assert "Rises" in window["summary"] if isinstance(window.get("summary"), str) else True


def test_space_passes_without_an_observer_say_why(skill, monkeypatch):
    monkeypatch.setattr(skill, "_device_location", lambda: None)
    result = skill.execute(operation="space_passes")
    assert result["ok"] is False
    assert "observer" in result["record"]["error"]


def test_southern_hemisphere_passes_are_not_reflected(skill, mock_http, monkeypatch):
    tle = "\n".join([
        "ISS (ZARYA)",
        "1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995",
        "2 25544  51.6337  11.7282 0006920 310.9581  49.0806 15.49059765592065",
        "",
    ])
    mock_http.respond("celestrak.org", tle)
    from core.astro import passes as passes_module

    seen = {}
    original = passes_module.predict_passes

    def spy(sat, latitude, longitude, **kwargs):
        seen["lat"], seen["lon"] = latitude, longitude
        return original(sat, latitude, longitude, **kwargs)

    monkeypatch.setattr(passes_module, "predict_passes", spy)
    monkeypatch.setattr(skill, "predict_passes", spy, raising=False)
    result = skill.execute(operation="space_passes", lat="-33.9", lon="151.2", hours="1")
    assert result["ok"] is True
    assert seen["lat"] == -33.9, "a southern observer must not be reflected north"
    assert seen["lon"] == 151.2


# ------------------------------------------------------------------- key-gated

def test_fires_without_a_key_name_the_key(skill, monkeypatch):
    from core.providers import keys as keys_module

    monkeypatch.setattr(keys_module, "resolve_key", lambda pid: "")
    result = skill.execute(operation="fires", area="somewhere")
    assert result["ok"] is False
    assert "NASA_FIRMS_MAP_KEY" in result["record"]["error"]


def test_vessels_without_a_key_name_the_key(skill, monkeypatch):
    from core.providers import keys as keys_module

    monkeypatch.setattr(keys_module, "resolve_key", lambda pid: "")
    result = skill.execute(operation="vessels")
    assert result["ok"] is False
    assert "AISSTREAM_API_KEY" in result["record"]["error"]


def test_fires_with_a_key_parse_the_csv(skill, mock_http, monkeypatch):
    from core.providers import keys as keys_module

    monkeypatch.setattr(keys_module, "resolve_key", lambda pid: "firms-key")
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("firms.modaps.eosdis.nasa.gov",
                      "latitude,longitude,bright_ti4,confidence,acq_date,acq_time,satellite\n"
                      "52.1,4.8,310.2,high,2026-10-27,0340,N\n"
                      "52.2,4.9,300.1,medium,2026-10-27,0330,S\n")
    result = skill.execute(operation="fires", area="somewhere")
    assert result["ok"] is True
    detections = result["record"]["value"]["detections"]
    assert len(detections) == 2
    assert detections[0]["confidence"] == "high"
    assert "evidence of heat" in result["summary"].lower() or "heat is evidence" in result["summary"].lower()


def test_traffic_without_a_key_reports_it(skill, monkeypatch):
    from core.providers import keys as keys_module

    monkeypatch.setattr(keys_module, "resolve_key", lambda pid: "")
    result = skill.execute(operation="traffic", area="somewhere")
    assert result["ok"] is False
    assert "TOMTOM_API_KEY" in result["record"]["error"]


# ------------------------------------------------------------------ keyless ops

def test_earthquakes_filter_to_the_box(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("earthquake.usgs.gov", {"features": [
        {"geometry": {"coordinates": [4.75, 52.05, 10.0]},
         "properties": {"place": "10km N of Somewhere", "mag": 3.1, "time": 1762000000000,
                        "tsunami": 0, "url": "https://example.test/event"}},
        {"geometry": {"coordinates": [-70.0, -20.0, 30.0]},
         "properties": {"place": "far away", "mag": 6.5, "time": 1762000000000,
                        "tsunami": 0, "url": ""}},
    ]})
    result = skill.execute(operation="earthquakes", area="somewhere")
    assert result["ok"] is True
    events = result["record"]["value"]["earthquakes"]
    assert len(events) == 1
    assert events[0]["place"] == "10km N of Somewhere"
    assert events[0]["magnitude"] == 3.1


def test_radio_directory_lists_stations(skill, mock_http):
    mock_http.respond("radio-browser.info", [
        {"name": "Jazz FM", "country": "United Kingdom", "votes": 1200,
         "url_resolved": "https://stream.example/jazz", "codec": "MP3", "bitrate": 128},
        {"name": "Radio Nova", "country": "Portugal", "votes": 40,
         "url_resolved": "https://stream.example/nova", "codec": "AAC", "bitrate": 64},
    ])
    result = skill.execute(operation="radio", category="jazz")
    assert result["ok"] is True
    assert result["record"]["value"]["count"] == 2


def test_wind_forecast_returns_samples(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("api.open-meteo.com", {
        "hourly": {"time": ["2026-10-27T00:00", "2026-10-27T01:00"],
                   "wind_speed_10m": [12.0, 16.1],
                   "wind_direction_10m": [200, 210]}})
    result = skill.execute(operation="wind", area="somewhere")
    assert result["ok"] is True
    assert result["record"]["value"]["max_speed_kmh"] == 16.1
    assert result["record"]["value"]["forecast_hours"][0]["speed_kmh"] == 12.0


def test_air_quality_reports_the_index(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("air-quality-api.open-meteo.com", {
        "hourly": {"time": ["2026-10-27T00:00"], "us_aqi": [74], "european_aqi": [47]}})
    result = skill.execute(operation="air_quality", area="somewhere")
    assert result["ok"] is True
    assert "74" in result["summary"]
    assert "47" in result["summary"]


def test_radar_frames_come_from_rainviewer(skill, mock_http):
    mock_http.respond("api.rainviewer.com", {
        "host": "https://tilecache.rainviewer.com",
        "generated": 1762000000,
        "satellite": {"infrared": [{"time": 1761990000, "path": "/v2/ir/1/1_1.png",
                                    "steps": []}]}})
    result = skill.execute(operation="radar")
    assert result["ok"] is True
    assert len(result["record"]["value"]["radar_frames"]) == 1


def test_cyclones_list_active_storms(skill, mock_http):
    mock_http.respond("nhc.noaa.gov", {"activeStorms": [
        {"name": "FIVE", "intensity": 45, "latitude": 25.0, "longitude": -60.0,
         "classification": "Tropical Storm", "movement": "W at 10 mph"}]})
    result = skill.execute(operation="cyclones", category="AL")
    assert result["ok"] is True
    assert result["record"]["value"]["active_storms"][0]["name"] == "FIVE"


def test_cyclones_with_no_active_storms_says_so(skill, mock_http):
    mock_http.respond("nhc.noaa.gov", {"activeStorms": []})
    result = skill.execute(operation="cyclones")
    assert result["ok"] is True
    assert "No active tropical cyclones" in result["summary"]


def test_launches_list_the_manifests(skill, mock_http):
    mock_http.respond("ll.thespacedevs.com", {"results": [
        {"name": "Falcon 9 Block 5 | Starlink Group 10-21", "net": "2026-10-28T12:00:00Z",
         "status": {"name": "Go"}, "probability": 90,
         "launch_service_provider": {"name": "SpaceX"}, "pad": {"name": "SLC-40",
                                                               "location": {"name": "Cape Canaveral"}},
         "mission": {"name": "Starlink Group 10-21", "description": "A batch of Starlink satellites."}}]})
    result = skill.execute(operation="launches")
    assert result["ok"] is True
    launch = result["record"]["value"]["launches"][0]
    assert launch["provider"] == "SpaceX"
    assert launch["pad"] == "SLC-40"


def test_cameras_read_osm(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("overpass-api.de", {"elements": [
        {"id": 1, "lat": 52.06, "lon": 4.77, "tags": {"operator": "City", "name": "Main St"}}]})
    result = skill.execute(operation="cameras", area="somewhere")
    assert result["ok"] is True
    assert result["record"]["value"]["count"] == 1
    assert "no plate data" in result["summary"]


def test_alpr_reads_osm(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("overpass-api.de", {"elements": [
        {"id": 7, "center": {"lat": 52.06, "lon": 4.77},
         "tags": {"camera": "alpr", "operator": "Highway Agency"}}]})
    result = skill.execute(operation="alpr", area="somewhere")
    assert result["ok"] is True
    assert result["record"]["value"]["count"] == 1


def test_infrastructure_lists_features(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("overpass-api.de", {"elements": [
        {"id": 9, "center": {"lat": 52.1, "lon": 4.8},
         "tags": {"name": "Some Datacenter", "operator": "Acme"}}]})
    result = skill.execute(operation="infrastructure", category="datacenter", area="somewhere")
    assert result["ok"] is True
    assert result["record"]["value"]["features"][0]["name"] == "Some Datacenter"


def test_military_flights_use_point_and_radius(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("api.adsb.lol", {"ac": [
        {"hex": "ae1234", "flight": "RCH1234 ", "t": "C17", "alt_baro": 25000,
         "gs": 400, "track": 90, "squawk": "1234", "r": "06-1234"}]})
    result = skill.execute(operation="military_flights", area="somewhere", radius_km="120")
    assert result["ok"] is True
    value = result["record"]["value"]
    assert value["radius_km"] == 120.0
    assert value["aircraft"][0]["type"] == "C17"

    urls = [url for kind, url in mock_http.calls if "adsb.lol" in url]
    assert "/lat/" in urls[0] and "/lon/" in urls[0] and "/dist/" in urls[0]


def test_military_radius_is_capped_at_250(skill, mock_http):
    mock_http.respond("api.adsb.lol", {"ac": []})
    result = skill.execute(operation="military_flights", area="somewhere", radius_km="9999")
    assert result["ok"] is True
    assert result["record"]["value"]["radius_km"] == 250.0


def test_bikeshare_needs_a_network(skill):
    result = skill.execute(operation="bikeshare")
    assert result["ok"] is False
    assert "network" in result["record"]["error"]


def test_bikeshare_lists_stations(skill, mock_http):
    mock_http.respond("gbfs.api.velib-metropole.fr", {"data": {"stations": [
        {"station_id": "16107", "num_bikes_available": 4, "num_docks_available": 12,
         "is_renting": True, "last_reported": 1762000000}]}})
    result = skill.execute(operation="bikeshare", category="velib")
    assert result["ok"] is True
    station = result["record"]["value"]["stations"][0]
    assert station["station_id"] == "16107"
    assert station["num_bikes_available"] == 4


def test_street_level_uses_kartaview(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("api.kartaview.org", {"photos": [
        {"id": 42, "location": {"lat": 52.06, "lng": 4.77},
         "shot_date": "2026-01-01", "fileurl": "https://example.test/photo.jpg"}]})
    result = skill.execute(operation="street_level", area="somewhere")
    assert result["ok"] is True
    photo = result["record"]["value"]["photos"][0]
    assert photo["latitude"] == 52.06
    assert "Mapillary" in result["record"]["value"]["note"]


def test_transit_lists_known_networks(skill):
    result = skill.execute(operation="transit")
    assert result["ok"] is True
    assert "ttc" in result["record"]["value"]["available_networks"]


def test_transit_refuses_an_unknown_network(skill):
    result = skill.execute(operation="transit", category="nowhere")
    assert result["ok"] is False
    assert "no GTFS-Realtime feed" in result["record"]["error"]


def test_gnss_integrity_states_its_interpretation(skill):
    result = skill.execute(operation="gnss_integrity")
    assert result["ok"] is True
    assert "not a measurement" in result["record"]["value"]["interpretation"] or "aggregated" in \
        result["record"]["value"]["interpretation"]


def test_every_operation_handles_a_feed_failure(skill, mock_http):
    """No operation may raise when its feed is unreachable."""
    mock_http.respond("geocoding-api.open-meteo.com", None, ok=False, failure="network",
                      reason="offline")
    mock_http.respond("api.adsb.lol", None, ok=False, failure="network", reason="offline")
    mock_http.respond("overpass-api.de", None, ok=False, failure="network", reason="offline")
    mock_http.respond("ll.thespacedevs.com", None, ok=False, failure="network", reason="offline")
    mock_http.respond("api.open-meteo.com", None, ok=False, failure="network", reason="offline")
    mock_http.respond("air-quality-api.open-meteo.com", None, ok=False, failure="network",
                      reason="offline")
    mock_http.respond("api.rainviewer.com", None, ok=False, failure="network", reason="offline")
    mock_http.respond("celestrak.org", None, ok=False, failure="network", reason="offline")
    mock_http.respond("earthquake.usgs.gov", None, ok=False, failure="network", reason="offline")
    mock_http.respond("api.kartaview.org", None, ok=False, failure="network", reason="offline")
    for name in ("flights", "military_flights", "earthquakes", "fires", "wind", "radar",
                 "air_quality", "cameras", "alpr", "street_level", "infrastructure",
                 "launches", "satellites", "space_passes"):
        result = skill.execute(operation=name, area="nowhere")
        assert result["ok"] is False, f"{name} should report unavailability"
        assert result["record"]["error"], f"{name} should say why"
        assert "summary" in result


def test_summary_is_always_a_string(skill, mock_http):
    for name in ("sources", "gnss_integrity"):
        result = skill.execute(operation=name)
        assert isinstance(result["summary"], str)
        assert result["summary"]


def test_alias_input_is_accepted(skill, mock_http):
    mock_http.respond("geocoding-api.open-meteo.com", GEOCODE)
    mock_http.respond("earthquake.usgs.gov", {"features": []})
    result = skill.execute(operation="quake", area="somewhere")
    assert result["ok"] is True
    assert result["operation"] == "earthquakes"
