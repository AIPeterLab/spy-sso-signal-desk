#!/usr/bin/env python3
"""Refresh SPY/SSO adjusted-close data and all dashboard outputs."""

from __future__ import annotations

import csv
import json
import sys
import time
from calendar import monthcalendar, SUNDAY
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from strategy_engine import build_daily_rows, calendar_cycles, spread_cycles


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1=946684800&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
)


def eastern_now() -> datetime:
    """Return current US Eastern time without requiring the optional tzdata package."""
    utc_now = datetime.now(timezone.utc)
    march = monthcalendar(utc_now.year, 3)
    november = monthcalendar(utc_now.year, 11)
    march_sundays = [week[SUNDAY] for week in march if week[SUNDAY]]
    november_sundays = [week[SUNDAY] for week in november if week[SUNDAY]]
    dst_start_utc = datetime(utc_now.year, 3, march_sundays[1], 7, tzinfo=timezone.utc)
    dst_end_utc = datetime(utc_now.year, 11, november_sundays[0], 6, tzinfo=timezone.utc)
    offset = timedelta(hours=-4 if dst_start_utc <= utc_now < dst_end_utc else -5)
    return utc_now + offset


def fetch_yahoo(symbol: str) -> dict[str, float]:
    period2 = int(time.time()) + 86400
    request = Request(
        YAHOO_URL.format(symbol=symbol, period2=period2),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch {symbol} adjusted-close data: {exc}") from exc

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    output: dict[str, float] = {}
    for stamp, close in zip(timestamps, adjusted):
        if close is None:
            continue
        output[datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%d")] = float(close)
    if not output:
        raise RuntimeError(f"Yahoo Finance returned no usable {symbol} rows.")
    now_new_york = eastern_now()
    if (now_new_york.hour, now_new_york.minute) < (16, 15):
        output.pop(now_new_york.date().isoformat(), None)
    return output


def rounded(value, digits: int = 6):
    if isinstance(value, float):
        return round(value, digits)
    return value


def serialize(row) -> dict:
    return {key: rounded(value) for key, value in row.to_dict().items()}


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    try:
        spy = fetch_yahoo("SPY")
        sso = fetch_yahoo("SSO")
        rows = build_daily_rows(spy, sso)
        daily = [serialize(row) for row in rows]
        calendar = [{key: rounded(value) for key, value in item.items()} for item in calendar_cycles(rows)]
        spreads = [{key: rounded(value) for key, value in item.items()} for item in spread_cycles(rows)]
        latest = daily[-1]
        lead_dollars = latest["strategy_value"] - latest["spy_benchmark_value"]
        lead_pct = latest["strategy_value"] / latest["spy_benchmark_value"] - 1
        current_cycle = spreads[-1] if spreads and spreads[-1]["status"] == "open" else None

        payload = {
            "project": "SSO Signal Desk",
            "dashboard_title": "SPY/SSO Signal Desk",
            "last_updated": latest["date"],
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_source": "Yahoo Finance chart API adjusted close",
            "strategy": {
                "signal_source": "SPY adjusted daily close",
                "indicator": "SPY 200-day simple moving average",
                "invested_asset": "SSO",
                "defensive_position": "Cash",
                "benchmark": "SPY Hold",
                "buy_rule": "SPY adjusted close > SMA200 × 1.01",
                "sell_rule": "SPY adjusted close < SMA200 × 0.99",
                "timing": "Signals are calculated after the close and apply to the next trading day.",
            },
            "summary": {
                **latest,
                "headline_status": f"Hold {latest['position']}",
                "current_action": latest["signal"],
                "lead_lag_dollars": rounded(lead_dollars, 2),
                "lead_lag_pct": rounded(lead_pct, 6),
                "max_strategy_drawdown": rounded(min(row["strategy_drawdown"] for row in daily)),
                "max_spy_drawdown": rounded(min(row["spy_drawdown"] for row in daily)),
                "spread_cycle_number": current_cycle["cycle"] if current_cycle else None,
                "cycle_high_floor": current_cycle["high_range_floor"] if current_cycle else None,
                "cycle_max_spread": current_cycle["max_spread"] if current_cycle else None,
                "cycle_max_date": current_cycle["max_spread_date"] if current_cycle else None,
                "in_cycle_high_range": current_cycle["current_in_high_range"] if current_cycle else None,
            },
            "daily": daily,
            "calendar_cycles": calendar,
            "spread_cycles": spreads,
        }

        DATA_DIR.mkdir(exist_ok=True)
        (DATA_DIR / "signals.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        write_csv(DATA_DIR / "signals.csv", daily)
        write_csv(DATA_DIR / "calendar_cycles.csv", calendar)
        write_csv(DATA_DIR / "spread_cycles.csv", spreads)
    except Exception as exc:
        print(f"update_signals failed: {exc}", file=sys.stderr)
        return 1

    print(f"Updated SPY/SSO signal data through {payload['last_updated']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
