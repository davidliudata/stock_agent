"""
Early-stage momentum investment strategy — based on MU/Sandisk-type breakouts.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def print_strategy():
    console.print()
    console.rule("[bold yellow]📈 Early-Stage Momentum Strategy[/bold yellow]")

    # ── Why MU & Sandisk moved ────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Why stocks like MU (Micron) make explosive moves:[/bold]\n\n"
        "1. [cyan]Macro catalyst[/cyan] — AI boom → huge demand for HBM memory chips.\n"
        "   Sandisk/WD similarly benefited from NAND storage demand cycles.\n\n"
        "2. [cyan]Analyst upgrades[/cyan] — price target raises after an earnings beat or guidance raise\n"
        "   trigger institutional FOMO buying (volume explodes 2–5×).\n\n"
        "3. [cyan]Short squeeze potential[/cyan] — heavily shorted stocks with bad news\n"
        "   priced in can rocket on any positive surprise.\n\n"
        "4. [cyan]Sector rotation[/cyan] — when semis (SMH ETF) start outperforming,\n"
        "   individual names get dragged along before the headlines arrive.",
        title="[yellow]What drives early-stage breakouts[/yellow]",
        border_style="yellow",
    ))

    # ── 5-step entry checklist ────────────────────────────────────────────────
    t = Table(title="5-Step Entry Checklist", box=box.ROUNDED, border_style="cyan")
    t.add_column("#",     style="bold cyan", width=3)
    t.add_column("Signal",               style="bold white", min_width=22)
    t.add_column("What to check",        style="white")
    t.add_column("Tool / source",        style="dim")

    t.add_row("1", "Volume surge",       "Today's volume > 1.5× 20-day avg\n→ institutions are buying",       "Yahoo Finance / screener.py")
    t.add_row("2", "Price above 50-MA",  "Closing price > 50-day moving average\n→ medium-term trend is bullish","TradingView / yfinance")
    t.add_row("3", "Sector ETF rising",  "SMH (semis) or XLK (tech) making new highs\n→ tide is rising for the sector","ETF price check")
    t.add_row("4", "Catalyst exists",    "Earnings beat, new product, upgrade,\nor macro tailwind announced",   "Earnings calendar, news")
    t.add_row("5", "RSI 50–75",          "Not overbought, but momentum confirmed\n→ sweet spot for entry",       "screener.py output")

    console.print(t)
    console.print()

    # ── Entry & exit ──────────────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Entry:[/bold]\n"
        "  • [green]Buy on the first pullback[/green] after the initial surge (wait 1–3 days after spike).\n"
        "    Chasing on day 1 of a +15% move is the fastest way to get hurt.\n"
        "  • Look for price to hold near the [green]10-day or 21-day EMA[/green] on the pullback.\n"
        "  • Enter when volume tapers off on the dip — means sellers are exhausted.\n\n"
        "[bold]Position sizing:[/bold]\n"
        "  • Risk only [bold]1–2% of portfolio[/bold] per trade (risk = entry − stop-loss × shares).\n"
        "  • Start with [bold]half position[/bold] on initial entry, add second half if it confirms.\n\n"
        "[bold]Stop-loss:[/bold]\n"
        "  • Hard stop: [red]−7 to −8% from entry[/red] (CANSLIM rule — cuts losses before they compound).\n"
        "  • Or: below the most recent swing low.\n\n"
        "[bold]Profit taking:[/bold]\n"
        "  • Sell [green]20–25%[/green] of position at +20% gain (lock in some profit).\n"
        "  • Trail remaining with a [green]10-day MA trailing stop[/green].\n"
        "  • Full exit if stock closes below 50-day MA on heavy volume.",
        title="[green]Entry / Exit Rules[/green]",
        border_style="green",
    ))

    # ── Red flags ─────────────────────────────────────────────────────────────
    console.print(Panel(
        "[red]🚩 Avoid buying when:[/red]\n\n"
        "  • Stock is already up [bold]+30%+[/bold] in 10 days with no pullback (parabolic = dangerous).\n"
        "  • RSI > 80 — extremely overbought, late buyers get trapped.\n"
        "  • Volume is fading while price is still rising — weak hands.\n"
        "  • The [bold]sector ETF is rolling over[/bold] while the stock still looks hot.\n"
        "  • You're trading on [bold]social media hype[/bold] alone (Reddit, X) — usually means\n"
        "    institutions already exited and retail is the exit liquidity.",
        title="[red]Red Flags[/red]",
        border_style="red",
    ))

    # ── MU-style early detection tips ────────────────────────────────────────
    console.print(Panel(
        "[bold yellow]How to find the next MU before it moves +50%:[/bold yellow]\n\n"
        "  1. [cyan]Watch SMH (Semiconductor ETF)[/cyan] — when it makes a new 52-week high,\n"
        "     scan for individual semis that haven't moved yet (laggards catch up).\n\n"
        "  2. [cyan]Earnings estimate revisions[/cyan] — when analysts raise EPS estimates for\n"
        "     a sector (e.g., AI memory), stocks in that sub-sector re-rate.\n"
        "     Check: Earnings Whispers, Zacks Rank changes.\n\n"
        "  3. [cyan]Insider buying[/cyan] — executives buying their own stock in size is a\n"
        "     strong early signal. Check: openinsider.com\n\n"
        "  4. [cyan]Float rotation[/cyan] — small/mid-cap stocks with high short interest\n"
        "     (>15% float short) that start seeing volume spikes can short-squeeze rapidly.\n\n"
        "  5. [cyan]Run this screener weekly[/cyan] — stocks that appear on the qualified list\n"
        "     for 2+ consecutive weeks are confirming sustained momentum, not a 1-day spike.",
        title="[yellow]Finding the next MU early[/yellow]",
        border_style="yellow",
    ))
    console.print()
