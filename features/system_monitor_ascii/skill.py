"""
Feature: system_monitor_ascii
Description: Monitors and displays current CPU and RAM utilization using ASCII progress bars.
Uses theme tokens from themes.json (no hardcoded colours). Requires `psutil`; reports unavailability if missing.
"""

FEATURE_METADATA = {
    "name": "system_monitor_ascii",
    "aliases": ["monitor system", "system status", "resource usage", "systemmonitorascii"],
    "description": "Monitors and displays current CPU and RAM utilization using ASCII progress bars. Requires the `psutil` package; if unavailable, reports that system metrics cannot be read.",
    "triggers": [
        "monitor system", "system status", "resource usage", "show cpu and ram",
        "what is my system load", "system monitor ascii",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["psutil"],
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


def create_progress_bar(percentage: float, width: int = 50) -> str:
    """Creates an ASCII progress bar using theme colours."""
    filled_width = int(width * (percentage / 100))
    filled_char = "\u2588"
    empty_char = "\u258a"
    bar = filled_char * filled_width + empty_char * (width - filled_width)
    bar_colour = _theme_colour("primary", "\033[92m")
    reset = "\033[0m"
    return f"{bar_colour}|{bar}|{reset} {percentage:.1f}%"


def execute(**kwargs) -> dict:
    """Monitors CPU and RAM load and displays an ASCII visual progress bar for both."""
    psutil = _psutil()
    if psutil is None:
        return {
            "title": "System Monitor Unavailable",
            "summary": "The `psutil` package is not installed on this machine, so CPU and RAM metrics cannot be read. Install psutil to enable this feature.",
        }

    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        mem_info = psutil.virtual_memory()
        ram_percent = mem_info.percent

        cpu_bar = create_progress_bar(cpu_percent)
        ram_bar = create_progress_bar(ram_percent)

        output = f"CPU Usage: {cpu_bar}\nRAM Usage: {ram_bar}"

        return {
            "title": "System Resource Monitor",
            "summary": output,
        }
    except Exception as e:
        error_message = f"Could not retrieve system metrics. Error: {e}"
        return {
            "title": "System Monitor Error",
            "summary": error_message,
        }
