"""
Feature: market_analysis
Description: Analyzes the current Bitcoin price and displays a graph card with recent price data. By default, it fetches BTCUSDT 1-hour klines for the last 24 hours.
Uses theme tokens from themes.json (no hardcoded colours).
"""

FEATURE_METADATA = {
    "name": "market_analysis",
    "description": "Analyzes the current Bitcoin price and displays a graph card with recent price data. By default, it fetches BTCUSDT 1-hour klines for the last 24 hours. Colours come from the active theme in themes.json.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "symbol": {
                "type": "STRING",
                "description": "The trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT'). Defaults to 'BTCUSDT'.",
            },
            "interval": {
                "type": "STRING",
                "description": "The candlestick interval (e.g., '1m', '5m', '1h', '1d'). Defaults to '1h'.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "The number of historical data points to fetch for the graph. Defaults to 24.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["matplotlib"],
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def execute(**kwargs):
    """Analyzes the current Bitcoin price and generates a price-trend graph."""
    import urllib.request
    import json
    import datetime

    symbol = kwargs.get("symbol", "BTCUSDT").upper()
    interval = kwargs.get("interval", "1h")
    limit = kwargs.get("limit", 24)

    try:
        limit = int(limit)
    except ValueError:
        return {"error": "Invalid 'limit' parameter. Must be an integer."}

    ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    current_price = "N/A"
    price_change_percent = "N/A"
    try:
        with urllib.request.urlopen(ticker_url, timeout=8) as response:
            ticker_data = json.loads(response.read().decode())
            current_price = float(ticker_data.get("lastPrice", 0))
            price_change_percent = float(ticker_data.get("priceChangePercent", 0))
    except urllib.error.URLError as e:
        print(f"Error fetching live ticker data for {symbol}: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding live ticker JSON for {symbol}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred fetching live ticker data: {e}")

    klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    times = []
    prices = []
    try:
        with urllib.request.urlopen(klines_url, timeout=8) as response:
            klines_data = json.loads(response.read().decode())
            for kline in klines_data:
                close_time_ms = kline[6]
                close_price = float(kline[4])
                times.append(datetime.datetime.fromtimestamp(close_time_ms / 1000))
                prices.append(close_price)
    except urllib.error.URLError as e:
        return {"error": f"Failed to fetch historical data for {symbol}: {e}"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to decode historical data JSON for {symbol}: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred fetching historical data: {e}"}

    if not times or not prices:
        return {"error": f"No historical data available for {symbol} with interval {interval} and limit {limit}."}

    plt = _matplotlib()
    image_path = None
    if plt is not None:
        try:
            plt.style.use("dark_background")
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
            ax.set_facecolor(_theme_colour("surface", "#0B0F19"))

            text_colour = _theme_colour("text-primary", "white")
            muted_colour = _theme_colour("text-secondary", "white")
            border_colour = _theme_colour("border", "#1E293B")
            primary_colour = _theme_colour("primary", "#00F0FF")

            ax.plot(
                times, prices, color=primary_colour, marker="o", markersize=4,
                linestyle="-", linewidth=2,
            )
            ax.set_title(f"{symbol} Price Trend ({interval} Interval)", color=text_colour, fontsize=16)
            ax.set_xlabel("Time", color=text_colour, fontsize=12)
            ax.set_ylabel("Price (USD)", color=text_colour, fontsize=12)
            ax.grid(True, linestyle="--", alpha=0.6, color=border_colour)
            ax.tick_params(axis="x", colors=text_colour, rotation=45)
            ax.tick_params(axis="y", colors=text_colour)
            for spine in ax.spines.values():
                spine.set_edgecolor(border_colour)

            fig.tight_layout()

            output_dir = _deliverables_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            image_path = str(output_dir / f"{symbol}_price_trend_{interval}.png")
            plt.savefig(image_path)
            plt.close(fig)
        except Exception:
            try:
                plt.close("all")
            except Exception:
                pass

    summary_text = f"Current {symbol} Price: ${current_price:,.2f}. "
    if price_change_percent != "N/A":
        change_sign = "+" if price_change_percent >= 0 else ""
        summary_text += f"24hr Change: {change_sign}{price_change_percent:.2f}%. "
    summary_text += f"Displaying {len(prices)} {interval} data points."

    return {
        "image_path": image_path,
        "title": f"{symbol} Market Analysis",
        "summary": summary_text,
    }
