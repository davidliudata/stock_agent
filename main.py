"""
Stock Agent — momentum screener + tracker.

Usage:
  python main.py                    # Scan all sectors
  python main.py --sector semis     # Scan semiconductors only
  python main.py --sector tech
  python main.py --sector biotech
  python main.py --sector energy
  python main.py --tickers MU NVDA AMD   # Scan specific tickers
  python main.py --history          # Show tracking history
  python main.py --strategy         # Print investment strategy guide
"""

import argparse
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from screener import run_scan, UNIVERSE
from tracker import record_scan, get_tracked, days_tracked, price_change_since_first
from strategy import print_strategy

console = Console()

SECTOR_ALIASES = {
    "semis": "Semiconductors",
    "semiconductors": "Semiconductors",
    "tech": "Tech / AI",
    "ai": "Tech / AI",
    "biotech": "Biotech",
    "energy": "Energy",
}


def vol_bar(ratio: float) -> str:
    filled = min(int(ratio * 2), 8)
    bar = "█" * filled + "░" * (8 - filled)
    color = "green" if ratio >= 1.5 else "yellow" if ratio >= 1.0 else "red"
    return f"[{color}]{bar}[/{color}] {ratio:.1f}×"


def rsi_color(rsi: float) -> str:
    if rsi > 80:   return f"[red]{rsi}[/red]"
    if rsi >= 50:  return f"[green]{rsi}[/green]"
    return f"[dim]{rsi}[/dim]"


def print_results(qualified: list, watchlist: list):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    console.print()

    # ── HIGH POTENTIAL ────────────────────────────────────────────────────────
    if qualified:
        t = Table(
            title=f"🔥 HIGH POTENTIAL STOCKS  [{now}]",
            box=box.ROUNDED, border_style="bright_red",
            title_style="bold bright_red",
        )
        t.add_column("Ticker",      style="bold white",   width=7)
        t.add_column("Price",       style="cyan",         width=8)
        t.add_column("10d Return",  style="bold green",   width=12)
        t.add_column("Up Days",     style="yellow",       width=10)
        t.add_column("Volume",      min_width=18)
        t.add_column("vs 52w High", style="dim",          width=12)
        t.add_column("RSI",         width=6)
        t.add_column("Tracked",     style="dim",          width=9)

        for s in qualified:
            d = days_tracked(s["ticker"])
            chg = price_change_since_first(s["ticker"])
            tracked_str = f"{d}d" if d <= 1 else f"{d}d ({chg:+.1f}%)" if chg is not None else f"{d}d"
            up_str = f"{'★' * s['up_days']}{'·' * (10 - s['up_days'])}  {s['up_days']}/10"
            t.add_row(
                s["ticker"],
                f"${s['price']:,.2f}",
                f"+{s['total_return_10d']:.1f}%",
                up_str,
                vol_bar(s["vol_ratio"]),
                f"{s['pct_from_52w_high']:+.1f}%",
                rsi_color(s["rsi"]),
                tracked_str,
            )
        console.print(t)
    else:
        console.print(Panel(
            "No stocks meet the primary criteria today.\n"
            "Primary: [bold]5+ up days out of 10[/bold] AND [bold]>10% total return[/bold].\n"
            "Check the watchlist below for stocks approaching qualification.",
            title="🔥 High Potential", border_style="dim red",
        ))

    console.print()

    # ── WATCHLIST ─────────────────────────────────────────────────────────────
    if watchlist:
        t2 = Table(
            title="👀 WATCHLIST  (approaching criteria)",
            box=box.SIMPLE_HEAD, border_style="yellow",
            title_style="bold yellow",
        )
        t2.add_column("Ticker",     style="bold",   width=7)
        t2.add_column("Price",      style="cyan",   width=8)
        t2.add_column("10d Return", style="green",  width=12)
        t2.add_column("Up Days",    style="yellow", width=10)
        t2.add_column("Volume",     min_width=18)
        t2.add_column("RSI",        width=6)

        for s in watchlist[:15]:  # show top 15
            up_str = f"{'★' * s['up_days']}{'·' * (10 - s['up_days'])}  {s['up_days']}/10"
            t2.add_row(
                s["ticker"],
                f"${s['price']:,.2f}",
                f"{s['total_return_10d']:+.1f}%",
                up_str,
                vol_bar(s["vol_ratio"]),
                rsi_color(s["rsi"]),
            )
        console.print(t2)

    console.print()
    console.print(
        "[dim]Criteria: 5+ up days/10 AND >10% 10-day return. "
        "Volume: vs prior 20-day avg. Run daily to track momentum.[/dim]"
    )
    console.print()


def print_history():
    data = get_tracked()
    if not data:
        console.print("[yellow]No tracking history yet. Run a scan first.[/yellow]")
        return

    console.print()
    t = Table(
        title="📊 Tracking History",
        box=box.ROUNDED, border_style="cyan",
    )
    t.add_column("Ticker",       style="bold white",  width=8)
    t.add_column("First Seen",   style="dim",         width=12)
    t.add_column("Days Tracked", style="cyan",        width=13)
    t.add_column("Entry Price",  style="cyan",        width=12)
    t.add_column("Latest Price", style="cyan",        width=13)
    t.add_column("Since Entry",  style="bold green",  width=13)
    t.add_column("Status",       width=10)

    rows = sorted(data.items(), key=lambda x: x[1]["first_seen"], reverse=True)
    for ticker, info in rows:
        hist = info["history"]
        if not hist:
            continue
        first_price = hist[0]["price"]
        last_price  = hist[-1]["price"]
        chg = (last_price / first_price - 1) * 100 if first_price else 0
        chg_str = f"[green]+{chg:.1f}%[/green]" if chg >= 0 else f"[red]{chg:.1f}%[/red]"
        status_str = "[red]🔥 hot[/red]" if info["status"] == "hot" else "[yellow]👀 watch[/yellow]"
        t.add_row(
            ticker,
            info["first_seen"],
            str(len(hist)),
            f"${first_price:.2f}",
            f"${last_price:.2f}",
            chg_str,
            status_str,
        )
    console.print(t)
    console.print()


def main():
    parser = argparse.ArgumentParser(description="Stock momentum screener & tracker")
    parser.add_argument("--sector",   type=str, help="Sector to scan: semis, tech, biotech, energy")
    parser.add_argument("--tickers",  nargs="+", help="Specific tickers to scan, e.g. MU NVDA AMD")
    parser.add_argument("--history",  action="store_true", help="Show tracking history")
    parser.add_argument("--strategy", action="store_true", help="Show investment strategy guide")
    parser.add_argument("--no-save",  action="store_true", help="Don't save results to tracker")
    parser.add_argument("--report",   action="store_true", help="Generate HTML report and open in browser")
    args = parser.parse_args()

    console.print()
    console.rule("[bold cyan]📈 Stock Agent[/bold cyan]")

    if args.strategy:
        print_strategy()
        return

    if args.history:
        print_history()
        return

    # Resolve sector name
    sector = None
    if args.sector:
        sector = SECTOR_ALIASES.get(args.sector.lower(), args.sector)

    # Determine tickers
    tickers = args.tickers if args.tickers else None

    if tickers:
        label = ", ".join(tickers)
    elif sector:
        label = sector
    else:
        label = "All sectors"

    console.print(f"\n[bold]Scanning:[/bold] {label}\n", style="cyan")

    qualified, watchlist = run_scan(tickers=tickers, sector=sector)

    print_results(qualified, watchlist)

    if not args.no_save and (qualified or watchlist):
        record_scan(qualified, watchlist)
        console.print("[dim]Results saved to tracker.[/dim]\n")

    if args.report:
        from report import generate_report
        import webbrowser
        n = len(tickers) if tickers else len(__import__('screener').UNIVERSE.get(sector, __import__('screener').ALL_TICKERS))
        path = generate_report(qualified, watchlist, label, n_scanned=n)
        console.print(f"\n[bold green]✅ Report:[/bold green] {path}")
        webbrowser.open(f"file://{path}")


if __name__ == "__main__":
    main()
