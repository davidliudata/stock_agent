"""
Persistence layer — saves scan results to JSON and tracks stocks over time.
Lets you see how long a stock has been flagged as high-potential.
"""

import json
import os
from datetime import datetime

TRACKER_FILE = os.path.join(os.path.dirname(__file__), "tracker_data.json")


def _load() -> dict:
    if not os.path.exists(TRACKER_FILE):
        return {}
    with open(TRACKER_FILE) as f:
        return json.load(f)


def _save(data: dict):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_scan(qualified: list, watchlist: list):
    """Append today's scan results to persistent history."""
    data = _load()
    today = datetime.now().strftime("%Y-%m-%d")

    for stock in qualified + watchlist:
        ticker = stock["ticker"]
        if ticker not in data:
            data[ticker] = {"first_seen": today, "history": [], "status": ""}
        entry = {
            "date": today,
            "price": stock["price"],
            "return_10d": stock["total_return_10d"],
            "up_days": stock["up_days"],
            "vol_ratio": stock["vol_ratio"],
            "qualified": stock["qualifies"],
        }
        # Avoid duplicate entries for the same day
        if not any(h["date"] == today for h in data[ticker]["history"]):
            data[ticker]["history"].append(entry)
        data[ticker]["status"] = "hot" if stock["qualifies"] else "watch"

    _save(data)


def get_tracked() -> dict:
    return _load()


def days_tracked(ticker: str) -> int:
    data = _load()
    if ticker not in data:
        return 0
    return len(data[ticker]["history"])


def price_change_since_first(ticker: str) -> float | None:
    """Return % price change from first detection to today."""
    data = _load()
    if ticker not in data or len(data[ticker]["history"]) < 2:
        return None
    hist = data[ticker]["history"]
    first_price = hist[0]["price"]
    last_price  = hist[-1]["price"]
    if first_price == 0:
        return None
    return round((last_price / first_price - 1) * 100, 2)
