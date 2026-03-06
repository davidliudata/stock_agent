"""
Stock screener — identifies high-momentum stocks using price + volume signals.

Primary criteria (qualifies as HIGH POTENTIAL):
  • 5+ out of last 10 trading days closed higher than open day
  • Total 10-day price return > 10%

Bonus signals (used for scoring/sorting):
  • Volume surge: recent 10-day avg volume > 1.5× prior 20-day avg
  • Near 52-week high (within 15%)
  • RSI between 50–80 (momentum without being overbought)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from rich.console import Console

console = Console()

# ── Universe of stocks to scan ────────────────────────────────────────────────

# Semiconductors & AI hardware (where MU, SNDK-like plays live)
SEMIS = [
    "MU", "NVDA", "AMD", "INTC", "QCOM", "AVGO", "TXN", "MRVL", "AMAT",
    "LRCX", "KLAC", "ASML", "TSM", "SWKS", "MPWR", "ON", "WOLF", "CRUS",
    "SLAB", "QORVO", "RMBS", "AMBA", "SMCI", "COHR",
]

# Tech / AI software
TECH = [
    "MSFT", "GOOGL", "META", "AAPL", "AMZN", "CRM", "NOW", "SNOW", "DDOG",
    "PLTR", "PATH", "AI", "BBAI", "SOUN", "IONQ",
]

# Biotech / Healthcare momentum
BIOTECH = [
    "MRNA", "BNTX", "REGN", "VRTX", "GILD", "BIIB", "SGEN", "ALNY",
    "BEAM", "EDIT", "CRSP", "NTLA", "RXRX",
]

# Energy (oil, clean energy)
ENERGY = [
    "XOM", "CVX", "OXY", "DVN", "FANG", "SLB", "HAL",
    "ENPH", "SEDG", "FSLR", "BE", "PLUG", "RUN",
]

UNIVERSE = {
    "Semiconductors": SEMIS,
    "Tech / AI": TECH,
    "Biotech": BIOTECH,
    "Energy": ENERGY,
}

ALL_TICKERS = list({t for tickers in UNIVERSE.values() for t in tickers})


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_history(tickers: list[str], days: int = 60) -> dict[str, pd.DataFrame]:
    """Download OHLCV history for all tickers in one batch call (yfinance >= 1.0)."""
    end = datetime.today()
    start = end - timedelta(days=days)
    raw = yf.download(
        tickers, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
        auto_adjust=True, progress=False, threads=True,
    )
    result = {}
    fields = ["Close", "High", "Low", "Open", "Volume"]
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                # Single ticker: columns are flat (Close, High, ...)
                df = raw[fields].copy()
            else:
                # Multi ticker: columns are MultiIndex (field, ticker)
                df = pd.DataFrame({f: raw[(f, ticker)] for f in fields if (f, ticker) in raw.columns})
            df = df.dropna(how="all")
            if len(df) >= 12:
                result[ticker] = df
        except Exception:
            pass
    return result


# ── Scoring ───────────────────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return float(100 - 100 / (1 + rs.iloc[-1]))


def score_ticker(ticker: str, df: pd.DataFrame) -> dict | None:
    """
    Returns a scoring dict or None if not enough data.
    """
    try:
        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        if len(close) < 12:
            return None

        # 10-day window (most recent 10 trading days)
        c10 = close.iloc[-11:]      # 11 prices → 10 daily returns
        v10 = volume.iloc[-10:]
        v_baseline = volume.iloc[-30:-10] if len(volume) >= 30 else volume.iloc[:-10]

        daily_ret = c10.pct_change().dropna()
        up_days = int((daily_ret > 0).sum())
        total_return_10d = float((c10.iloc[-1] / c10.iloc[0] - 1) * 100)

        # Volume surge
        vol_10d_avg = float(v10.mean())
        vol_base_avg = float(v_baseline.mean()) if len(v_baseline) > 0 else vol_10d_avg
        vol_ratio = vol_10d_avg / vol_base_avg if vol_base_avg > 0 else 1.0

        # 52-week high proximity
        high_52w = float(close.iloc[-252:].max()) if len(close) >= 252 else float(close.max())
        pct_from_high = float((close.iloc[-1] / high_52w - 1) * 100)

        # RSI
        rsi_val = rsi(close) if len(close) >= 16 else 50.0

        # Primary qualification
        qualifies = up_days >= 5 and total_return_10d > 10.0

        # Bonus score (0–100, used for ranking)
        bonus = 0
        if vol_ratio >= 1.5:  bonus += 25
        if vol_ratio >= 2.0:  bonus += 15
        if pct_from_high > -15: bonus += 20
        if 50 <= rsi_val <= 75: bonus += 20
        if up_days >= 7:       bonus += 20

        # 10-day price series for sparkline in report
        prices_10d = [round(float(p), 2) for p in c10.values]
        dates_10d  = [str(d)[:10] for d in c10.index]
        daily_rets = [round(float(r) * 100, 2) for r in daily_ret.values]

        return {
            "ticker": ticker,
            "qualifies": qualifies,
            "up_days": up_days,
            "total_return_10d": round(total_return_10d, 2),
            "vol_ratio": round(vol_ratio, 2),
            "pct_from_52w_high": round(pct_from_high, 1),
            "rsi": round(rsi_val, 1),
            "bonus_score": bonus,
            "price": round(float(close.iloc[-1]), 2),
            "prices_10d": prices_10d,
            "dates_10d": dates_10d,
            "daily_rets": daily_rets,
            "high_52w": round(high_52w, 2),
            "scanned_at": datetime.now().isoformat(),
        }
    except Exception:
        return None


# ── Main scan ─────────────────────────────────────────────────────────────────

def run_scan(tickers: list[str] | None = None, sector: str | None = None) -> tuple[list, list]:
    """
    Scan tickers and return (qualified, watchlist).
    - qualified: meet primary criteria (5/10 days up, >10% return)
    - watchlist: close to qualifying (4 up days OR 7–10% return)
    """
    if tickers is None:
        if sector and sector in UNIVERSE:
            tickers = UNIVERSE[sector]
        else:
            tickers = ALL_TICKERS

    console.print(f"  Fetching data for [bold]{len(tickers)}[/bold] stocks...", style="dim")
    history = fetch_history(tickers, days=60)
    console.print(f"  Got data for [bold]{len(history)}[/bold] stocks. Scoring...", style="dim")

    qualified, watchlist = [], []

    for ticker, df in history.items():
        result = score_ticker(ticker, df)
        if result is None:
            continue
        if result["qualifies"]:
            qualified.append(result)
        elif result["up_days"] >= 4 or result["total_return_10d"] >= 7:
            watchlist.append(result)

    qualified.sort(key=lambda x: (x["up_days"], x["total_return_10d"]), reverse=True)
    watchlist.sort(key=lambda x: (x["up_days"], x["total_return_10d"]), reverse=True)

    return qualified, watchlist
