"""
Feature: check_current_stock_prices
Description: Retrieves the current stock price and historical data for a given stock symbol, then generates a dark-themed graph card showing price trends. Defaults to BMW.DE stock.
Uses theme tokens from themes.json (no hardcoded colours).
"""

FEATURE_METADATA = {
    "name": "check_current_stock_prices",
    "description": "Retrieves the current stock price and historical data for a given stock symbol, then generates a graph card showing price trends. Defaults to BMW.DE stock. Colours come from the active theme in themes.json.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "symbol": {
                "type": "STRING",
                "description": "The stock ticker symbol (e.g., 'AAPL' for Apple, 'BMW.DE' for BMW on XETRA, 'TSLA' for Tesla). Defaults to 'BMW.DE'.",
            },
            "period": {
                "type": "STRING",
                "description": "The historical period for the graph (e.g., '1mo' for 1 month, '3mo' for 3 months, '1y' for 1 year). Defaults to '1mo'.",
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
    """Retrieves the current stock price and generates a price-trend graph."""
    import urllib.request
    import json
    import datetime

    symbol = kwargs.get("symbol", "BMW.DE")
    period = kwargs.get("period", "1mo")

    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    if period not in valid_periods:
        return {"error": f"Invalid period '{period}'. Please choose from: {', '.join(valid_periods)}"}

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())

        if not data or "chart" not in data or not data["chart"]["result"]:
            return {"error": f"Could not retrieve data for symbol '{symbol}'. It might be invalid or unavailable."}

        chart_data = data["chart"]["result"][0]
        meta = chart_data["meta"]
        indicators = chart_data["indicators"]["quote"][0]

        current_price = meta.get("regularMarketPrice")
        currency = meta.get("currency", "USD")

        timestamps = chart_data["timestamp"]
        closes = indicators["close"]

        valid_data = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
        if not valid_data:
            return {"error": f"No valid historical closing price data found for '{symbol}' in the last {period}."}

        timestamps, closes = zip(*valid_data)
        dates = [datetime.datetime.fromtimestamp(ts) for ts in timestamps]

        plt = _matplotlib()
        image_path = None
        if plt is not None:
            try:
                plt.style.use("dark_background")
                fig, ax = plt.subplots(figsize=(10, 6))
                fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
                ax.set_facecolor(_theme_colour("surface", "#0B0F19"))

                text_colour = _theme_colour("text-primary", "#E0E0E0")
                muted_colour = _theme_colour("text-secondary", "#E0E0E0")
                border_colour = _theme_colour("border", "#1E293B")
                primary_colour = _theme_colour("primary", "#00F0FF")

                ax.tick_params(colors=text_colour)
                ax.xaxis.label.set_color(text_colour)
                ax.yaxis.label.set_color(text_colour)
                ax.title.set_color(text_colour)

                ax.plot(
                    dates, closes, color=primary_colour, linewidth=2, marker="o",
                    markersize=3, markerfacecolor=primary_colour, markeredgecolor=primary_colour,
                )
                ax.grid(True, linestyle="--", alpha=0.6, color=border_colour)
                ax.set_xlabel("Date", fontsize=12, color=text_colour)
                ax.set_ylabel(f"Price ({currency})", fontsize=12, color=text_colour)
                ax.set_title(f"{symbol} Stock Price Trend ({period})", fontsize=14, weight="bold", color=text_colour)
                fig.autofmt_xdate()

                output_dir = _deliverables_dir()
                output_dir.mkdir(parents=True, exist_ok=True)
                image_filename = f"{symbol.replace('.', '_')}_stock_price_trend_{period}.png"
                image_path = str(output_dir / image_filename)
                plt.savefig(image_path, bbox_inches="tight", dpi=100, facecolor=fig.get_facecolor())
                plt.close(fig)
            except Exception:
                try:
                    plt.close("all")
                except Exception:
                    pass

        summary_text = f"Current price for {symbol}: {current_price:.2f} {currency}. Historical trend over {period} shown in the graph."
        if current_price is None:
            summary_text = f"Could not retrieve current price for {symbol}. Historical trend over {period} shown in the graph."

        return {
            "image_path": image_path,
            "title": f"{symbol} Stock Price ({period})",
            "summary": summary_text,
        }

    except urllib.error.URLError as e:
        return {"error": f"Network error while fetching data for {symbol}: {e.reason}. Please check your internet connection."}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": f"Stock symbol '{symbol}' not found or data unavailable. Please check the symbol."}
        return {"error": f"HTTP error while fetching data for {symbol}: {e.code} - {e.reason}"}
    except json.JSONDecodeError:
        return {"error": f"Failed to decode JSON response for {symbol}. The API might have returned malformed data."}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}
