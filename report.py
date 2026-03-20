"""
Report generator — produces a self-contained HTML report with
reasoning for every stock recommendation.

Usage:
  python report.py                    # scan all sectors, open report
  python report.py --sector semis
  python report.py --tickers MU NVDA
"""

import os
import argparse
import webbrowser
from datetime import datetime

import yfinance as yf
from rich.console import Console

from screener import run_scan, UNIVERSE
from main import SECTOR_ALIASES

console = Console()

# ── Company info cache ────────────────────────────────────────────────────────

KNOWN = {
    "MU":   ("Micron Technology",           "Semiconductors",  "Memory & Storage"),
    "NVDA": ("NVIDIA Corporation",           "Semiconductors",  "GPUs / AI Compute"),
    "AMD":  ("Advanced Micro Devices",       "Semiconductors",  "CPUs / GPUs"),
    "INTC": ("Intel Corporation",            "Semiconductors",  "CPUs / Foundry"),
    "QCOM": ("Qualcomm",                     "Semiconductors",  "Mobile / RF Chips"),
    "AVGO": ("Broadcom Inc.",                "Semiconductors",  "Networking Chips"),
    "TXN":  ("Texas Instruments",            "Semiconductors",  "Analog Chips"),
    "MRVL": ("Marvell Technology",           "Semiconductors",  "Data Infrastructure"),
    "AMAT": ("Applied Materials",            "Semiconductors",  "Equipment"),
    "LRCX": ("Lam Research",                 "Semiconductors",  "Equipment"),
    "KLAC": ("KLA Corporation",              "Semiconductors",  "Equipment"),
    "ASML": ("ASML Holding",                 "Semiconductors",  "Lithography"),
    "TSM":  ("Taiwan Semiconductor",         "Semiconductors",  "Foundry"),
    "SMCI": ("Super Micro Computer",         "Technology",      "AI Servers"),
    "COHR": ("Coherent Corp.",               "Technology",      "Optical Networking"),
    "AMBA": ("Ambarella",                    "Semiconductors",  "AI Vision Chips"),
    "RMBS": ("Rambus",                       "Semiconductors",  "Memory Interface"),
    "MPWR": ("Monolithic Power Systems",     "Semiconductors",  "Power Management"),
    "ON":   ("ON Semiconductor",             "Semiconductors",  "Power / Auto Chips"),
    "WOLF": ("Wolfspeed",                    "Semiconductors",  "Silicon Carbide"),
    "CRUS": ("Cirrus Logic",                 "Semiconductors",  "Audio Chips"),
    "SWKS": ("Skyworks Solutions",           "Semiconductors",  "RF Chips"),
    "MSFT": ("Microsoft",                    "Technology",      "Cloud / AI Software"),
    "GOOGL":("Alphabet (Google)",            "Technology",      "Cloud / AI / Search"),
    "META": ("Meta Platforms",               "Technology",      "Social / AI"),
    "AAPL": ("Apple Inc.",                   "Technology",      "Consumer / Chips"),
    "AMZN": ("Amazon",                       "Technology",      "Cloud / E-Commerce"),
    "PLTR": ("Palantir Technologies",        "Technology",      "AI / Data Analytics"),
    "AI":   ("C3.ai",                        "Technology",      "Enterprise AI"),
    "SOUN": ("SoundHound AI",                "Technology",      "Voice AI"),
    "IONQ": ("IonQ",                         "Technology",      "Quantum Computing"),
    "MRNA": ("Moderna",                      "Biotech",         "mRNA Vaccines"),
    "NVAX": ("Novavax",                      "Biotech",         "Vaccines"),
    "XOM":  ("ExxonMobil",                   "Energy",          "Oil & Gas"),
    "CVX":  ("Chevron",                      "Energy",          "Oil & Gas"),
    "ENPH": ("Enphase Energy",               "Energy",          "Solar Inverters"),
    "FSLR": ("First Solar",                  "Energy",          "Solar Panels"),
}


def get_info(ticker: str) -> tuple[str, str, str]:
    """Return (company_name, sector, industry). Falls back to yfinance."""
    if ticker in KNOWN:
        return KNOWN[ticker]
    try:
        info = yf.Ticker(ticker).info
        name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector") or "—"
        industry = info.get("industry") or "—"
        return name, sector, industry
    except Exception:
        return ticker, "—", "—"


# ── Reasoning generator ───────────────────────────────────────────────────────

def generate_reasoning(s: dict, name: str, sector: str, industry: str) -> dict:
    """
    Build a structured reasoning object with headline, signals, and narrative.
    """
    r = s["total_return_10d"]
    up = s["up_days"]
    vol = s["vol_ratio"]
    rsi_val = s["rsi"]
    hi_pct = s["pct_from_52w_high"]
    qualifies = s["qualifies"]

    # ── Headline ──
    if qualifies:
        if r >= 20 and up >= 7:
            headline = f"Strong institutional breakout with exceptional momentum"
        elif r >= 15:
            headline = f"High-conviction momentum move with broad participation"
        else:
            headline = f"Meets primary momentum criteria — building trend confirmed"
    else:
        needed = []
        if up < 5:    needed.append(f"{5 - up} more up day(s)")
        if r < 10:    needed.append(f"{10 - r:.1f}% more price gain")
        headline = f"Approaching qualification — needs {' and '.join(needed)}"

    # ── Signal bullets ──
    signals = []

    # Momentum signal
    if up >= 7:
        signals.append(("✅", "price_momentum",
            f"Closed higher on <b>{up}/10</b> recent trading days — unusually consistent uptrend."))
    elif up >= 5:
        signals.append(("✅", "price_momentum",
            f"Closed higher on <b>{up}/10</b> recent trading days — meets momentum threshold."))
    else:
        signals.append(("⚠️", "price_momentum",
            f"Only <b>{up}/10</b> up days — trend not yet confirmed."))

    # Return signal
    if r >= 20:
        signals.append(("✅", "return",
            f"<b>+{r:.1f}%</b> gain in 10 trading days — exceptional near-term return."))
    elif r >= 10:
        signals.append(("✅", "return",
            f"<b>+{r:.1f}%</b> gain in 10 trading days — exceeds our 10% qualification threshold."))
    elif r >= 0:
        signals.append(("⚠️", "return",
            f"<b>+{r:.1f}%</b> gain in 10 trading days — below 10% threshold yet."))
    else:
        signals.append(("❌", "return",
            f"<b>{r:.1f}%</b> over 10 days — negative momentum."))

    # Volume signal
    if vol >= 2.0:
        signals.append(("✅", "volume",
            f"Volume running at <b>{vol:.1f}×</b> normal — strong institutional accumulation signal."))
    elif vol >= 1.5:
        signals.append(("✅", "volume",
            f"Volume at <b>{vol:.1f}×</b> average — above-normal activity, likely institutional interest."))
    elif vol >= 1.0:
        signals.append(("⚠️", "volume",
            f"Volume at <b>{vol:.1f}×</b> average — normal, no unusual activity yet."))
    else:
        signals.append(("❌", "volume",
            f"Volume at <b>{vol:.1f}×</b> average — below-normal, weak participation."))

    # RSI signal
    if 55 <= rsi_val <= 75:
        signals.append(("✅", "rsi",
            f"RSI at <b>{rsi_val}</b> — ideal momentum zone (50–75): strong trend, not yet overbought."))
    elif rsi_val > 75:
        signals.append(("⚠️", "rsi",
            f"RSI at <b>{rsi_val}</b> — approaching overbought territory; wait for a pullback entry."))
    elif rsi_val >= 45:
        signals.append(("⚠️", "rsi",
            f"RSI at <b>{rsi_val}</b> — neutral; momentum not yet confirmed."))
    else:
        signals.append(("❌", "rsi",
            f"RSI at <b>{rsi_val}</b> — weak / oversold territory."))

    # 52-week high proximity
    if hi_pct >= -5:
        signals.append(("✅", "52w",
            f"Trading <b>{abs(hi_pct):.1f}%</b> below its 52-week high — near breakout territory."))
    elif hi_pct >= -15:
        signals.append(("⚠️", "52w",
            f"Trading <b>{abs(hi_pct):.1f}%</b> below its 52-week high — recovering but not at highs."))
    else:
        signals.append(("❌", "52w",
            f"Trading <b>{abs(hi_pct):.1f}%</b> below its 52-week high — significant distance to recover."))

    # ── Narrative paragraph ──
    if qualifies:
        vol_desc = ("significantly above-average volume (suggesting institutional buying)"
                    if vol >= 1.5 else "average volume")
        rsi_desc = ("healthy momentum zone without being overbought" if 50 <= rsi_val <= 75
                    else "elevated RSI (caution on chasing)")
        hi_desc  = (f"just {abs(hi_pct):.0f}% from its 52-week high" if hi_pct >= -10
                    else f"{abs(hi_pct):.0f}% below its 52-week high")
        narrative = (
            f"{name} ({sector} — {industry}) has demonstrated strong short-term momentum: "
            f"up <b>{r:.1f}%</b> over the past 10 trading days with <b>{up} of those 10 days</b> closing higher. "
            f"This pattern, combined with {vol_desc}, indicates the move has broad market participation. "
            f"The RSI of <b>{rsi_val}</b> sits in the {rsi_desc}, and the stock is currently {hi_desc}. "
        )
        if vol >= 1.5:
            narrative += (
                f"The volume surge ({vol:.1f}× baseline) is a key signal: it often precedes "
                f"a sustained trend as institutional money flows in before retail catches on. "
            )
        narrative += (
            f"<b>Strategy:</b> Look for a 1–3 day pullback to the 10-day moving average as a lower-risk entry. "
            f"Set a hard stop at −8% from entry and take partial profit at +20%."
        )
    else:
        gaps = []
        if up < 5:   gaps.append(f"needs {5 - up} more up day(s) (currently {up}/10)")
        if r < 10:   gaps.append(f"needs {10.0 - r:.1f}% more price gain (currently +{r:.1f}%)")
        narrative = (
            f"{name} is on our watchlist for {', '.join(gaps)}. "
        )
        if vol >= 1.5:
            narrative += f"The elevated volume ({vol:.1f}×) is encouraging and suggests accumulation is underway. "
        if rsi_val >= 50:
            narrative += f"RSI of {rsi_val} shows the trend is intact. "
        narrative += (
            f"<b>Watch for:</b> continued daily gains and volume staying above average. "
            f"If momentum continues for 2–3 more sessions, this stock may graduate to the High Potential list."
        )

    return {
        "headline": headline,
        "signals": signals,
        "narrative": narrative,
    }


# ── Sparkline SVG ─────────────────────────────────────────────────────────────

def sparkline_svg(prices: list[float], width=200, height=50, positive=True) -> str:
    if len(prices) < 2:
        return ""
    mn, mx = min(prices), max(prices)
    rng = mx - mn or 1
    pad = 4
    w, h = width - pad * 2, height - pad * 2
    pts = []
    for i, p in enumerate(prices):
        x = pad + i * w / (len(prices) - 1)
        y = pad + h - (p - mn) / rng * h
        pts.append(f"{x:.1f},{y:.1f}")

    # Build fill polygon (close to bottom)
    fill_pts = pts + [f"{pad + w:.1f},{pad + h:.1f}", f"{pad:.1f},{pad + h:.1f}"]
    color  = "#3182ce" if positive else "#e53e3e"
    fill_c = "#3182ce22" if positive else "#e53e3e22"
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polygon points="{" ".join(fill_pts)}" fill="{fill_c}"/>'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
        f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" '
        f'r="3.5" fill="{color}"/>'
        f'</svg>'
    )


def day_bars_svg(daily_rets: list[float], width=200, height=36) -> str:
    """Mini bar chart of daily returns (green up, red down)."""
    n = len(daily_rets)
    if n == 0:
        return ""
    gap = 2
    bw = (width - gap * (n - 1)) / n
    mid = height / 2
    max_abs = max(abs(r) for r in daily_rets) or 1
    bars = []
    for i, r in enumerate(daily_rets):
        x = i * (bw + gap)
        bar_h = abs(r) / max_abs * (mid - 2)
        color = "#48bb78" if r >= 0 else "#fc8181"
        if r >= 0:
            bars.append(f'<rect x="{x:.1f}" y="{mid - bar_h:.1f}" width="{bw:.1f}" '
                        f'height="{bar_h:.1f}" rx="1" fill="{color}"/>')
        else:
            bars.append(f'<rect x="{x:.1f}" y="{mid:.1f}" width="{bw:.1f}" '
                        f'height="{bar_h:.1f}" rx="1" fill="{color}"/>')
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<line x1="0" y1="{mid:.1f}" x2="{width}" y2="{mid:.1f}" '
            f'stroke="#e2e8f0" stroke-width="1"/>'
            + "".join(bars) + "</svg>")


# ── HTML builder ──────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f0f4f8; color: #2d3748; padding: 32px 16px; }
.container { max-width: 920px; margin: 0 auto; }

/* Header */
.report-header { background: linear-gradient(135deg,#1a365d,#2b6cb0);
  border-radius: 16px; padding: 32px 36px; color: #fff; margin-bottom: 28px; }
.report-header h1 { font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; }
.report-meta { margin-top: 10px; opacity: .75; font-size: 0.88rem; }
.report-meta span { margin-right: 20px; }

/* Summary pills */
.summary-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 28px; }
.summary-pill { background: #fff; border-radius: 12px; padding: 16px 22px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); text-align: center; flex: 1; min-width: 130px; }
.summary-pill .val { font-size: 1.9rem; font-weight: 800; letter-spacing: -1px; }
.summary-pill .lbl { font-size: 0.7rem; font-weight: 700; color: #a0aec0;
  text-transform: uppercase; letter-spacing: .06em; margin-top: 4px; }
.pill-hot  .val { color: #e53e3e; }
.pill-watch .val { color: #d69e2e; }
.pill-scan  .val { color: #3182ce; }
.pill-top   .val { color: #38a169; }

/* Section titles */
.section-title { font-size: 1.1rem; font-weight: 800; color: #2d3748;
  margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.section-title .badge { font-size: .7rem; padding: 2px 10px; border-radius: 20px;
  font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
.badge-hot   { background: #fff5f5; color: #c53030; }
.badge-watch { background: #fffff0; color: #b7791f; }

/* Stock cards */
.stock-card { background: #fff; border-radius: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 18px; overflow: hidden; }
.card-hot   { border-left: 5px solid #e53e3e; }
.card-watch { border-left: 5px solid #d69e2e; }

.card-top { display: flex; align-items: flex-start; gap: 20px;
  padding: 22px 24px 18px; flex-wrap: wrap; }
.card-identity { flex: 1; min-width: 200px; }
.card-ticker { font-size: 1.5rem; font-weight: 900; color: #1a202c; letter-spacing: -0.5px; }
.card-name   { font-size: 0.88rem; color: #718096; margin-top: 2px; }
.card-tags   { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.tag { font-size: .68rem; font-weight: 700; padding: 2px 8px; border-radius: 10px;
  background: #edf2f7; color: #4a5568; }

.card-chart  { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.chart-label { font-size: 0.65rem; color: #a0aec0; font-weight: 600;
  text-transform: uppercase; letter-spacing: .05em; }

.card-metrics { display: flex; gap: 28px; flex-wrap: wrap;
  padding: 0 24px 16px; }
.metric { display: flex; flex-direction: column; gap: 3px; }
.metric .m-val { font-size: 1.15rem; font-weight: 800; color: #2d3748; }
.metric .m-lbl { font-size: .65rem; font-weight: 700; color: #a0aec0;
  text-transform: uppercase; letter-spacing: .06em; }
.green { color: #38a169 !important; }
.red   { color: #e53e3e !important; }
.blue  { color: #3182ce !important; }
.orange{ color: #d69e2e !important; }

/* Up-day pips */
.pips { display: flex; gap: 3px; margin-top: 4px; }
.pip { width: 10px; height: 10px; border-radius: 2px; }
.pip-up   { background: #48bb78; }
.pip-down { background: #e2e8f0; }

/* Signals */
.card-signals { padding: 14px 24px; background: #f7fafc;
  border-top: 1px solid #e2e8f0; }
.signals-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr));
  gap: 8px; }
.signal-row { display: flex; gap: 8px; align-items: flex-start;
  font-size: .84rem; color: #4a5568; line-height: 1.4; }
.signal-icon { font-size: .95rem; flex-shrink: 0; margin-top: 1px; }

/* Headline */
.card-headline { padding: 12px 24px 0;
  font-size: .88rem; font-weight: 700; color: #4a5568; }

/* Narrative */
.card-narrative { padding: 14px 24px 20px; font-size: .88rem;
  color: #4a5568; line-height: 1.65;
  border-top: 1px solid #e2e8f0; }
.card-narrative b { color: #2d3748; }

/* Strategy box */
.strategy-box { background: #fff; border-radius: 16px; padding: 28px 32px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-top: 12px; }
.strategy-box h3 { font-size: 1rem; font-weight: 800; color: #2d3748;
  margin-bottom: 14px; }
.strategy-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px,1fr));
  gap: 14px; }
.strategy-item { padding: 14px 16px; border-radius: 10px; border-left: 3px solid; }
.si-entry  { background:#f0fff4; border-color:#38a169; }
.si-stop   { background:#fff5f5; border-color:#e53e3e; }
.si-exit   { background:#ebf8ff; border-color:#3182ce; }
.si-size   { background:#fffff0; border-color:#d69e2e; }
.strategy-item h4 { font-size:.78rem; font-weight:800; text-transform:uppercase;
  letter-spacing:.05em; color:#4a5568; margin-bottom:6px; }
.strategy-item p  { font-size:.83rem; color:#4a5568; line-height:1.5; }

/* Footer */
.report-footer { text-align:center; margin-top:36px; font-size:.78rem; color:#a0aec0; }

@media (max-width:600px) {
  .card-top { flex-direction: column; }
  .card-metrics { gap: 16px; }
}
"""


def build_card(s: dict, reasoning: dict, name: str, sector: str, industry: str) -> str:
    r = s["total_return_10d"]
    up = s["up_days"]
    cls = "card-hot" if s["qualifies"] else "card-watch"
    badge = '<span class="badge badge-hot">🔥 High Potential</span>' if s["qualifies"] \
            else '<span class="badge badge-watch">👀 Watchlist</span>'

    pips = "".join(
        f'<div class="pip pip-up" title="+day"></div>' if i < up
        else f'<div class="pip pip-down"></div>'
        for i in range(10)
    )

    vol_color = "green" if s["vol_ratio"] >= 1.5 else ("orange" if s["vol_ratio"] >= 1.0 else "red")
    rsi_color = "green" if 50 <= s["rsi"] <= 75 else ("orange" if s["rsi"] < 50 else "red")
    hi_color  = "green" if s["pct_from_52w_high"] >= -10 else "orange"
    ret_color = "green" if r >= 10 else ("orange" if r >= 0 else "red")

    spark = sparkline_svg(s["prices_10d"], positive=(r >= 0))
    bars  = day_bars_svg(s["daily_rets"])

    signals_html = "".join(
        f'<div class="signal-row"><span class="signal-icon">{icon}</span>'
        f'<span>{text}</span></div>'
        for icon, _, text in reasoning["signals"]
    )

    tags = [sector, industry]
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags if t and t != "—")

    return f"""
<div class="stock-card {cls}">
  <div class="card-top">
    <div class="card-identity">
      <div class="card-ticker">{s['ticker']} {badge}</div>
      <div class="card-name">{name}</div>
      <div class="card-tags">{tags_html}</div>
    </div>
    <div class="card-chart">
      <div class="chart-label">10-day price</div>
      {spark}
      <div class="chart-label">daily returns</div>
      {bars}
    </div>
  </div>

  <div class="card-metrics">
    <div class="metric">
      <div class="m-val {ret_color}">{'+' if r >= 0 else ''}{r:.1f}%</div>
      <div class="m-lbl">10d Return</div>
    </div>
    <div class="metric">
      <div class="m-val">${s['price']:,.2f}</div>
      <div class="m-lbl">Price</div>
    </div>
    <div class="metric">
      <div class="m-val">{up}/10</div>
      <div class="m-lbl">Up Days</div>
      <div class="pips">{pips}</div>
    </div>
    <div class="metric">
      <div class="m-val {vol_color}">{s['vol_ratio']:.1f}×</div>
      <div class="m-lbl">Volume vs Avg</div>
    </div>
    <div class="metric">
      <div class="m-val {rsi_color}">{s['rsi']}</div>
      <div class="m-lbl">RSI</div>
    </div>
    <div class="metric">
      <div class="m-val {hi_color}">{s['pct_from_52w_high']:+.1f}%</div>
      <div class="m-lbl">vs 52w High</div>
    </div>
  </div>

  <div class="card-headline">💡 {reasoning['headline']}</div>

  <div class="card-signals">
    <div class="signals-grid">{signals_html}</div>
  </div>

  <div class="card-narrative">{reasoning['narrative']}</div>
</div>"""


def build_html(qualified, watchlist, sector_label, n_scanned) -> str:
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y at %H:%M")

    # Enrich + build cards
    all_stocks = [(s, True) for s in qualified] + [(s, False) for s in watchlist]
    hot_cards = ""
    watch_cards = ""

    top_mover = max(qualified + watchlist, key=lambda x: x["total_return_10d"],
                    default=None) if (qualified or watchlist) else None

    console.print("  Fetching company info and building report...", style="dim")
    for s, is_hot in all_stocks:
        name, sector, industry = get_info(s["ticker"])
        reasoning = generate_reasoning(s, name, sector, industry)
        card = build_card(s, reasoning, name, sector, industry)
        if is_hot:
            hot_cards += card
        else:
            watch_cards += card

    top_str = (f"+{top_mover['total_return_10d']:.1f}% {top_mover['ticker']}"
               if top_mover else "—")

    summary_html = f"""
<div class="summary-row">
  <div class="summary-pill pill-scan">
    <div class="val">{n_scanned}</div><div class="lbl">Stocks Scanned</div>
  </div>
  <div class="summary-pill pill-hot">
    <div class="val">{len(qualified)}</div><div class="lbl">High Potential</div>
  </div>
  <div class="summary-pill pill-watch">
    <div class="val">{len(watchlist)}</div><div class="lbl">Watchlist</div>
  </div>
  <div class="summary-pill pill-top">
    <div class="val" style="font-size:1.3rem">{top_str}</div><div class="lbl">Top Mover</div>
  </div>
</div>"""

    hot_section = f"""
<div class="section-title">🔥 High Potential Stocks
  <span class="badge badge-hot">≥5 up days & >10% return</span>
</div>
{hot_cards if hot_cards else '<p style="color:#a0aec0;padding:20px 0">No stocks qualify today.</p>'}
"""

    watch_section = f"""
<div class="section-title" style="margin-top:32px">👀 Watchlist
  <span class="badge badge-watch">approaching criteria</span>
</div>
{watch_cards if watch_cards else '<p style="color:#a0aec0;padding:20px 0">Watchlist is empty.</p>'}
"""

    strategy_section = """
<div class="section-title" style="margin-top:32px">📋 Quick Strategy Reference</div>
<div class="strategy-box">
  <div class="strategy-grid">
    <div class="strategy-item si-entry">
      <h4>✅ Entry</h4>
      <p>Buy the <b>first pullback</b> after a surge (1–3 days). Look for price holding the 10-day EMA on low volume.</p>
    </div>
    <div class="strategy-item si-stop">
      <h4>🛑 Stop-Loss</h4>
      <p>Hard stop at <b>−8% from entry</b>. Never move stop lower. Exit immediately if violated.</p>
    </div>
    <div class="strategy-item si-exit">
      <h4>💰 Profit Target</h4>
      <p>Sell <b>25% at +20%</b> gain. Trail the rest with a 10-day MA stop. Full exit below 50-day MA on volume.</p>
    </div>
    <div class="strategy-item si-size">
      <h4>⚖️ Position Size</h4>
      <p>Risk <b>max 1–2% of portfolio</b> per trade. Start with half size; add the rest when the move confirms.</p>
    </div>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Momentum Report — {now.strftime('%Y-%m-%d')}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

  <div class="report-header">
    <h1>📈 Stock Momentum Report</h1>
    <div class="report-meta">
      <span>📅 {date_str}</span>
      <span>🔭 Universe: {sector_label}</span>
      <span>⚙️ Criteria: ≥5 up days / 10 &amp; &gt;10% 10-day return</span>
    </div>
  </div>

  {summary_html}
  {hot_section}
  {watch_section}
  {strategy_section}

  <div class="report-footer">
    Generated by Stock Agent · For educational purposes only · Not financial advice
  </div>
</div>
</body>
</html>"""


# ── PDF export ────────────────────────────────────────────────────────────────

def html_to_pdf(html_path: str) -> str | None:
    import subprocess, shutil
    pdf_path = html_path.replace(".html", ".pdf")
    chrome = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    if not shutil.which(chrome) and not __import__('os').path.exists(chrome):
        console.print("  [yellow]PDF skipped: Chrome not found[/yellow]")
        return None
    try:
        result = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             "--allow-file-access-from-files", "--disable-web-security",
             f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header",
             f"file://{html_path}"],
            capture_output=True, timeout=60
        )
        if __import__('os').path.exists(pdf_path) and __import__('os').path.getsize(pdf_path) > 1000:
            return pdf_path
        console.print(f"  [yellow]PDF generation failed[/yellow]")
        return None
    except Exception as e:
        console.print(f"  [yellow]PDF generation failed: {e}[/yellow]")
        return None


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_report(qualified, watchlist, sector_label="All Sectors", n_scanned=0,
                    output_path=None, pdf=False) -> dict[str, str]:
    """Returns dict with 'html' path and optionally 'pdf' path."""
    html = build_html(qualified, watchlist, sector_label, n_scanned)
    if output_path is None:
        date = datetime.now().strftime("%Y-%m-%d")
        reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"{date}_{sector_label.replace('/', '-').replace(' ', '_')}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    # Always keep a latest.html copy
    latest_path = os.path.join(os.path.dirname(output_path), "latest.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html)

    result = {"html": output_path, "latest": latest_path}
    if pdf:
        console.print("  Converting to PDF...", style="dim")
        pdf_path = html_to_pdf(output_path)
        if pdf_path:
            result["pdf"] = pdf_path
    return result


def main():
    parser = argparse.ArgumentParser(description="Stock momentum report generator")
    parser.add_argument("--sector",     type=str)
    parser.add_argument("--tickers",    nargs="+")
    parser.add_argument("--out",        type=str, help="Output HTML file path")
    parser.add_argument("--pdf",        action="store_true", help="Also generate PDF")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser (for cron)")
    args = parser.parse_args()

    console.print()
    console.rule("[bold cyan]📈 Stock Agent — Report Generator[/bold cyan]")

    sector = None
    if args.sector:
        sector = SECTOR_ALIASES.get(args.sector.lower(), args.sector)

    tickers = args.tickers or None
    label = ", ".join(tickers) if tickers else (sector or "All Sectors")

    console.print(f"\n[bold]Scanning:[/bold] {label}\n", style="cyan")
    qualified, watchlist = run_scan(tickers=tickers, sector=sector)

    from screener import ALL_TICKERS, UNIVERSE
    n = len(tickers) if tickers else len(UNIVERSE.get(sector, ALL_TICKERS))

    paths = generate_report(qualified, watchlist, label, n_scanned=n,
                            output_path=args.out, pdf=args.pdf)

    console.print(f"\n[bold green]✅ HTML:[/bold green] {paths['html']}")
    if "pdf" in paths:
        console.print(f"[bold green]✅ PDF: [/bold green] {paths['pdf']}")

    if not args.no_browser:
        webbrowser.open(f"file://{paths['html']}")
        console.print("[dim]Opening in browser...[/dim]\n")


if __name__ == "__main__":
    main()
