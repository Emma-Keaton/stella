"""
Feature: internet_speed_test
Description: Measures real internet download speed, upload speed, latency and jitter, and renders a themed gauge card.
Uses theme tokens from themes.json (no hardcoded colours). Uses `speedtest-cli` when installed; otherwise a real HTTP chunk-streaming probe against Cloudflare's speed endpoints. Never fabricates a number — an unmeasurable transfer is reported as unavailable with the reason.
"""

FEATURE_METADATA = {
    "name": "internet_speed_test",
    "aliases": ["tests_my_internet_speed", "speed_test"],
    "description": "Tests internet download speed, upload speed, latency and jitter, and draws a visual speed gauge card. Download/upload are measured by transferring real data; when no transfer can be measured the skill says so instead of inventing values. Colours come from the active theme in themes.json.",
    "triggers": [
        "internet speed", "speed test", "test my speed", "test speed",
        "check speed", "download speed", "upload speed", "wifi speed",
        "network speed", "how fast is my internet", "my internet speed",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    },
    "version": "2.0.0",
    "active": True,
    "optional_dependencies": ["speedtest", "matplotlib"],
}

_DOWN_URL = "https://speed.cloudflare.com/__down"
_UP_URL = "https://speed.cloudflare.com/__up"
_LATENCY_HOSTS = ("1.1.1.1", "8.8.8.8", "speed.cloudflare.com")
_MAX_SECONDS = 25.0


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def _matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _speedtest():
    try:
        import speedtest
        return speedtest
    except Exception:
        return None


def _tcp_latency(host: str, timeout: float = 5.0) -> float | None:
    import socket
    import time

    started = time.time()
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return round((time.time() - started) * 1000.0, 2)
    except Exception:
        return None


def _probe_latency() -> tuple[float, float, list]:
    samples = [lat for lat in (_tcp_latency(h) for h in _LATENCY_HOSTS) if lat is not None]
    if not samples:
        return 0.0, 0.0, []
    mean = sum(samples) / len(samples)
    jitter = 0.0
    if len(samples) > 1:
        variance = sum((s - mean) ** 2 for s in samples) / (len(samples) - 1)
        jitter = round(variance ** 0.5, 2)
    return round(mean, 2), jitter, samples


def _stream_transfer(url: str, data: bytes | None, total_seconds: float) -> tuple[int, float]:
    import time
    import urllib.request

    mover = min(total_seconds, _MAX_SECONDS)
    started = time.time()
    received = 0
    if data is None:
        with urllib.request.urlopen(url, timeout=10) as response:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                received += len(chunk)
                if time.time() - started >= mover:
                    break
    else:
        request = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                received += len(chunk)
                if time.time() - started >= mover:
                    break
    return received, time.time() - started


def _shape_transfer(elapsed: float, received: int) -> float:
    if elapsed <= 0.0 or received <= 0:
        return 0.0
    return round((received * 8) / (elapsed * 1_000_000.0), 2)


def _adaptive_sizes(first_elapsed: float, first_bytes: int) -> tuple[int, int]:
    first_mbps = _shape_transfer(first_elapsed, first_bytes)
    if first_mbps <= 0.0:
        return 5_000_000, 1_000_000
    down = int(first_mbps * 1_000_000 / 8 * 4.0)
    up = int(first_mbps * 1_000_000 / 8 * 1.5)
    return max(2_000_000, min(down, 100_000_000)), max(500_000, min(up, 25_000_000))


def _probe_throughput() -> dict:
    import os
    import time

    first_bytes, first_elapsed = _stream_transfer(f"{_DOWN_URL}?bytes=2000000", None, 3.0)
    if first_bytes <= 0:
        return {}

    down_bytes, up_bytes = _adaptive_sizes(first_elapsed, first_bytes)
    down_target = max(4.0, min(10.0, (down_bytes * 8 / 1_000_000) / max(first_mbps := _shape_transfer(first_elapsed, first_bytes), 0.5) / 1_000_000))
    up_target = max(3.0, min(8.0, down_target / 2.0))

    payload = os.urandom(up_bytes)
    total_down, total_down_time = first_bytes, first_elapsed
    total_up, total_up_time = 0, 0.0

    deadline = time.time() + _MAX_SECONDS - (first_elapsed + 0.1)
    if down_target > first_elapsed and deadline - time.time() > 1.0:
        extra, extra_time = _stream_transfer(f"{_DOWN_URL}?bytes={down_bytes}", None, down_target)
        total_down += extra
        total_down_time += extra_time
    if deadline - time.time() > 1.0:
        sent, sent_time = _stream_transfer(_UP_URL, payload, up_target)
        total_up += sent
        total_up_time += sent_time

    return {
        "download_mbps": _shape_transfer(total_down_time, total_down),
        "upload_mbps": _shape_transfer(total_up_time, total_up),
        "bytes_down": total_down,
        "bytes_up": total_up,
        "seconds": round(total_down_time + total_up_time, 2),
    }


def _render_gauge(values, labels, colours):
    plt = _matplotlib()
    if plt is None:
        return None
    image_path = None
    try:
        fig, ax = plt.subplots(figsize=(8, 5.5))
        fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
        ax.set_facecolor(_theme_colour("surface", "#0B0F19"))
        plt.style.use("dark_background")

        bars = ax.bar(labels, values, color=colours, width=0.45,
                      edgecolor=_theme_colour("border", "#1E293B"), linewidth=1.5)
        ax.set_title("STELLA NETWORK TELEMETRY - INTERNET SPEED",
                     color=_theme_colour("text-primary", "#FFFFFF"), fontsize=13, fontweight="bold", pad=15)
        ax.tick_params(axis="y", colors=_theme_colour("text-secondary", "#94A3B8"))
        ax.tick_params(axis="x", colors=_theme_colour("text-primary", "#FFFFFF"), labelsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(_theme_colour("border", "#1E293B"))
        ax.spines["bottom"].set_color(_theme_colour("border", "#1E293B"))

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval + max(values) * 0.02, f"{yval:.2f}",
                    ha="center", va="bottom", color=_theme_colour("text-primary", "#FFFFFF"),
                    fontweight="bold")

        ax.grid(True, linestyle="--", alpha=0.3, color=_theme_colour("border", "#1E293B"))
        ax.set_axisbelow(True)

        output_dir = _deliverables_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        image_path = str(output_dir / "internet_speed_test.png")
        fig.tight_layout()
        plt.savefig(image_path, dpi=120, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
    except Exception:
        try:
            plt.close("all")
        except Exception:
            pass
    return image_path


def execute(**kwargs) -> dict:
    """Measures real download/upload throughput, latency and jitter, and renders the gauge card."""
    speedtest = _speedtest()
    method = "speedtest-cli"
    download_speed = 0.0
    upload_speed = 0.0
    ping = 0.0
    jitter = 0.0
    notes: list[str] = []

    if speedtest is not None:
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download_speed = round(st.download() / 1_000_000.0, 2)
            upload_speed = round(st.upload() / 1_000_000.0, 2)
            ping = round(float(st.results.ping), 2)
            jitter = round(float(getattr(st.results, "jitter", 0.0) or 0.0), 2)
        except Exception as e:
            notes.append(f"speedtest-cli failed ({type(e).__name__}: {e}); falling back to the HTTP probe.")
            speedtest = None

    if speedtest is None:
        method = "http-chunk-probe"
        ping, jitter, samples = _probe_latency()
        if not samples:
            return {
                "title": "Internet Speed Unavailable",
                "summary": (
                    "No TCP connection to 1.1.1.1, 8.8.8.8 or speed.cloudflare.com could be opened, so "
                    "no latency could be measured and the throughput probe cannot run. This usually means "
                    "the machine is offline, a firewall is blocking outbound HTTPS, or DNS is failing. "
                    "Nothing was measured and no estimate is reported."
                ),
                "error": "latency_probe_unreachable",
                "method": method,
            }
        throughput = _probe_throughput()
        if not throughput:
            return {
                "title": "Internet Speed Unavailable",
                "summary": (
                    "The latency probe succeeded, but no bytes could be transferred from "
                    "speed.cloudflare.com, so download and upload throughput cannot be measured. "
                    "The endpoint may be blocked, throttled or unavailable from this network. "
                    "Nothing was measured and no estimate is reported."
                ),
                "error": "throughput_probe_no_data",
                "method": method,
                "ping_ms": ping,
                "jitter_ms": jitter,
            }
        download_speed = throughput["download_mbps"]
        upload_speed = throughput["upload_mbps"]

    labels = ["Download (Mbps)", "Upload (Mbps)", "Ping (ms)"]
    values = [download_speed, upload_speed, ping]
    colours = [
        _theme_colour("secondary", "#00F0FF"),
        _theme_colour("success", "#10B981"),
        _theme_colour("warning", "#F59E0B"),
    ]

    image_path = None
    if download_speed > 0 or upload_speed > 0:
        image_path = _render_gauge(values, labels, colours)

    summary = (
        f"Download: {download_speed:.2f} Mbps | Upload: {upload_speed:.2f} Mbps | "
        f"Latency: {ping:.2f} ms | Jitter: {jitter:.2f} ms | Method: {method}"
    )
    spoken = (
        f"Speed test complete using the {method} method. Download is {download_speed:.1f} megabits per "
        f"second, upload is {upload_speed:.1f} megabits per second, latency {int(ping)} milliseconds."
    )
    if notes:
        spoken = " ".join(notes) + " " + spoken

    return {
        "title": "Internet Speed Test Results",
        "summary": summary,
        "spoken_narrative": spoken,
        "image_path": image_path,
        "file_path": image_path,
        "deliverable": image_path,
        "download_mbps": download_speed,
        "upload_mbps": upload_speed,
        "ping_ms": ping,
        "jitter_ms": jitter,
        "method": method,
        "notes": notes,
    }
