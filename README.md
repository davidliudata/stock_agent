# Stock Agent

A Python CLI that scans stocks for early-stage momentum — the kind of move seen in MU, NVDA, and similar names before big runs. Generates HTML/PDF reports and pushes them to GitHub daily via cron.

## Screening Criteria

**Qualifies as high-potential when both are true:**
- Closed higher on 5+ of the last 10 trading days
- Total 10-day price return > 10%

**Bonus signals (used for ranking):**
- Volume surge: recent 10-day avg > 1.5× prior 20-day avg
- RSI between 50–80 (momentum without being overbought)
- Within 15% of 52-week high

## Usage

```bash
# Scan all sectors
python main.py

# Scan a specific sector
python main.py --sector semis
python main.py --sector tech
python main.py --sector biotech
python main.py --sector energy

# Scan specific tickers
python main.py --tickers MU NVDA AMD

# Show tracking history (multi-day persistence)
python main.py --history

# Print investment strategy guide
python main.py --strategy

# Generate HTML + PDF report
python report.py --sector semis --pdf --no-browser
python report.py --sector tech --out ./reports/today_tech.html
```

## Reports

Reports are self-contained HTML files with:
- Per-stock sparkline and day-by-day return bars
- Signal breakdown (up-days, return %, volume ratio, RSI, 52w proximity)
- Plain-English reasoning for each recommendation
- Strategy reference section

PDF export uses Chrome headless for full-fidelity rendering.

## Sectors

| Alias | Coverage |
|-------|----------|
| `semis` | Semiconductors (MU, NVDA, AMD, ASML, TSM, ...) |
| `tech` | Tech / AI software (MSFT, GOOGL, META, PLTR, ...) |
| `biotech` | Biotech (MRNA, BNTX, REGN, GILD, ...) |
| `energy` | Energy (XOM, CVX, OXY, SLB, ...) |

## Daily Cron

Reports run automatically at **4:35 PM weekdays** (after US market close), saved to `reports/` and pushed to GitHub.

To view or modify the schedule:
```bash
crontab -l          # view
crontab -e          # edit
```

Current entry:
```
35 16 * * 1-5 /path/to/stock_agent/run_daily.sh
```

Logs are written to `logs/cron.log`.

## Setup

```bash
pip install -r requirements.txt
```

**Requirements:** Python 3.9+, yfinance >= 0.2.28, pandas, rich, Google Chrome (for PDF)

## Files

| File | Description |
|------|-------------|
| `screener.py` | Fetches data, scores tickers, runs scans |
| `main.py` | CLI entry point, rich terminal output |
| `report.py` | HTML/PDF report generator |
| `tracker.py` | Persists scan results to `tracker_data.json` |
| `strategy.py` | Formatted strategy guide for terminal |
| `run_daily.sh` | Cron script: scan → report → git push |
| `reports/` | Generated HTML and PDF reports |
