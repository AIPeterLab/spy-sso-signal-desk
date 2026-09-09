#!/usr/bin/env python3
"""Compare SSO Signal Desk returns with SPMO buy-and-hold cycles."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

try:
    from strategy_engine import STARTING_VALUE, maximum_drawdown
    from update_signals import fetch_yahoo
except ModuleNotFoundError:
    from scripts.strategy_engine import STARTING_VALUE, maximum_drawdown
    from scripts.update_signals import fetch_yahoo


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SIGNALS_CSV = DATA_DIR / "signals.csv"
OUTPUT_CSV = DATA_DIR / "spmo_cycle_comparison.csv"
OUTPUT_JSON = DATA_DIR / "spmo_cycle_comparison_summary.json"
OUTPUT_MD = DATA_DIR / "spmo_cycle_comparison.md"
SPMO_INCEPTION_DATE = "2015-10-09"
SPMO_START_YEAR = 2015
CYCLE_LENGTHS = (3, 5)


def read_signal_rows() -> list[dict]:
    with SIGNALS_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pct_return(value: float) -> float:
    return value / STARTING_VALUE - 1


def cagr(total_return: float, years: int) -> float:
    return (1 + total_return) ** (1 / years) - 1


def rounded(value):
    if isinstance(value, float):
        return round(value, 6)
    return value


def build_comparison(signal_rows: list[dict], spmo: dict[str, float]) -> list[dict]:
    spmo_dates = sorted(spmo)
    first_spmo_price_date = spmo_dates[0]
    spmo_daily_return = {}
    previous_spmo = None
    for day in spmo_dates:
        spmo_daily_return[day] = 0.0 if previous_spmo is None else spmo[day] / previous_spmo - 1
        previous_spmo = spmo[day]
    last_complete_year = min(
        date.fromisoformat(signal_rows[-1]["date"]).year - 1,
        date.fromisoformat(spmo_dates[-1]).year - 1,
    )
    output: list[dict] = []

    for length in CYCLE_LENGTHS:
        for start_year in range(SPMO_START_YEAR, last_complete_year - length + 2):
            end_year = start_year + length - 1
            rows = [
                row
                for row in signal_rows
                if first_spmo_price_date <= row["date"] <= f"{end_year}-12-31"
                and start_year <= int(row["date"][:4]) <= end_year
                and row["date"] in spmo
            ]
            if not rows:
                continue

            strategy_value = STARTING_VALUE
            spy_value = STARTING_VALUE
            spmo_value = STARTING_VALUE
            strategy_values = [strategy_value]
            spy_values = [spy_value]
            spmo_values = [spmo_value]

            for row in rows:
                strategy_value *= 1 + float(row["strategy_return"])
                spy_value *= 1 + float(row["spy_daily_return"])
                spmo_value *= 1 + spmo_daily_return[row["date"]]
                strategy_values.append(strategy_value)
                spy_values.append(spy_value)
                spmo_values.append(spmo_value)

            strategy_return = pct_return(strategy_value)
            spy_return = pct_return(spy_value)
            spmo_return = pct_return(spmo_value)
            output.append(
                {
                    "cycle_years": length,
                    "start_year": start_year,
                    "end_year": end_year,
                    "start_date": rows[0]["date"],
                    "end_date": rows[-1]["date"],
                    "strategy_final": strategy_value,
                    "spy_final": spy_value,
                    "spmo_final": spmo_value,
                    "strategy_return": strategy_return,
                    "spy_return": spy_return,
                    "spmo_return": spmo_return,
                    "strategy_cagr": cagr(strategy_return, length),
                    "spy_cagr": cagr(spy_return, length),
                    "spmo_cagr": cagr(spmo_return, length),
                    "strategy_max_drawdown": maximum_drawdown(strategy_values),
                    "spy_max_drawdown": maximum_drawdown(spy_values),
                    "spmo_max_drawdown": maximum_drawdown(spmo_values),
                    "strategy_beat_spmo": strategy_value > spmo_value,
                    "strategy_beat_spy": strategy_value > spy_value,
                }
            )

    return output


def write_csv(records: list[dict]) -> None:
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: rounded(value) for key, value in record.items()} for record in records)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def full_history(signal_rows: list[dict], spmo: dict[str, float]) -> dict:
    spmo_dates = sorted(spmo)
    first_spmo_price_date = spmo_dates[0]
    spmo_daily_return = {}
    previous_spmo = None
    for day in spmo_dates:
        spmo_daily_return[day] = 0.0 if previous_spmo is None else spmo[day] / previous_spmo - 1
        previous_spmo = spmo[day]

    rows = [
        row
        for row in signal_rows
        if first_spmo_price_date <= row["date"] <= spmo_dates[-1] and row["date"] in spmo
    ]
    strategy_value = STARTING_VALUE
    spy_value = STARTING_VALUE
    spmo_value = STARTING_VALUE
    strategy_values = [strategy_value]
    spy_values = [spy_value]
    spmo_values = [spmo_value]

    for row in rows:
        strategy_value *= 1 + float(row["strategy_return"])
        spy_value *= 1 + float(row["spy_daily_return"])
        spmo_value *= 1 + spmo_daily_return[row["date"]]
        strategy_values.append(strategy_value)
        spy_values.append(spy_value)
        spmo_values.append(spmo_value)

    return {
        "start_date": rows[0]["date"],
        "end_date": rows[-1]["date"],
        "strategy_final": strategy_value,
        "spy_final": spy_value,
        "spmo_final": spmo_value,
        "strategy_return": pct_return(strategy_value),
        "spy_return": pct_return(spy_value),
        "spmo_return": pct_return(spmo_value),
        "strategy_max_drawdown": maximum_drawdown(strategy_values),
        "spy_max_drawdown": maximum_drawdown(spy_values),
        "spmo_max_drawdown": maximum_drawdown(spmo_values),
    }


def write_markdown(records: list[dict], full: dict) -> None:
    lines = [
        "# SSO Signal Desk vs SPMO Cycle Comparison",
        "",
        "SPMO inception: 2015-10-09. First usable adjusted-close date: 2015-10-12.",
        "",
        "## Full Common History",
        "",
        f"Start date: {full['start_date']}. End date: {full['end_date']}.",
        "",
        "| Method | Final Value per $1,000 | Total Return | Max Drawdown |",
        "|---|---:|---:|---:|",
        f"| SSO Desk | ${full['strategy_final']:,.2f} | {pct(full['strategy_return'])} | {pct(full['strategy_max_drawdown'])} |",
        f"| SPY Hold | ${full['spy_final']:,.2f} | {pct(full['spy_return'])} | {pct(full['spy_max_drawdown'])} |",
        f"| SPMO Hold | ${full['spmo_final']:,.2f} | {pct(full['spmo_return'])} | {pct(full['spmo_max_drawdown'])} |",
        "",
        "## Rolling Cycles",
        "",
        "| Cycle | Dates | SSO Desk Return | SSO Desk Max DD | SPY Return | SPY Max DD | SPMO Return | SPMO Max DD | Winner |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in records:
        winner_values = {
            "SSO Desk": row["strategy_final"],
            "SPY": row["spy_final"],
            "SPMO": row["spmo_final"],
        }
        winner = max(winner_values, key=winner_values.get)
        lines.append(
            "| "
            f"{row['cycle_years']}Y | "
            f"{row['start_year']}-{row['end_year']} | "
            f"{pct(row['strategy_return'])} | "
            f"{pct(row['strategy_max_drawdown'])} | "
            f"{pct(row['spy_return'])} | "
            f"{pct(row['spy_max_drawdown'])} | "
            f"{pct(row['spmo_return'])} | "
            f"{pct(row['spmo_max_drawdown'])} | "
            f"{winner} |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    spmo = fetch_yahoo("SPMO")
    signal_rows = read_signal_rows()
    records = build_comparison(signal_rows, spmo)
    full = full_history(signal_rows, spmo)
    write_csv(records)
    write_markdown(records, full)

    summary = {
        "data_source": "Yahoo Finance chart API adjusted close",
        "spmo_inception_date": SPMO_INCEPTION_DATE,
        "first_spmo_adjusted_close_date": min(spmo),
        "last_spmo_adjusted_close_date": max(spmo),
        "start_year_used": SPMO_START_YEAR,
        "cycle_lengths": list(CYCLE_LENGTHS),
        "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
        "output_markdown": str(OUTPUT_MD.relative_to(ROOT)),
        "records": len(records),
        "strategy_wins": sum(1 for row in records if row["strategy_beat_spmo"]),
        "spmo_wins": sum(1 for row in records if not row["strategy_beat_spmo"]),
        "strategy_beats_spy": sum(1 for row in records if row["strategy_beat_spy"]),
        "full_history": {key: rounded(value) for key, value in full.items()},
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
