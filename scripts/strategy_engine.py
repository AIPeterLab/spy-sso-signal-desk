#!/usr/bin/env python3
"""Pure calculation engine for the volatility-adjusted SPY/SSO strategy."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable


BUY_BAND = 1.01
SELL_BAND = 0.99
LOW_VOLATILITY = 0.15
HIGH_VOLATILITY = 0.25
VOLATILITY_WINDOW = 20
STARTING_VALUE = 1000.0


@dataclass
class DailyRow:
    date: str
    spy_close: float
    sso_close: float
    sma200: float | None = None
    spread: float | None = None
    buy_threshold: float | None = None
    sell_threshold: float | None = None
    spy_20d_volatility: float | None = None
    trend_signal: str = "No Action"
    trend_state: str = "Cash"
    signal: str = "No Action"
    position: str = "Cash"
    target_spy_pct: float = 0.0
    target_sso_pct: float = 0.0
    target_cash_pct: float = 1.0
    reason: str = ""
    spy_daily_return: float = 0.0
    sso_daily_return: float = 0.0
    strategy_return: float = 0.0
    strategy_value: float = STARTING_VALUE
    spy_benchmark_value: float = STARTING_VALUE
    strategy_drawdown: float = 0.0
    spy_drawdown: float = 0.0
    spread_cycle: int | None = None
    cycle_high_floor: float | None = None
    cycle_max_spread: float | None = None
    cycle_max_date: str | None = None
    in_cycle_high_range: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def simple_moving_average(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    output: list[float | None] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= window:
            running -= values[index - window]
        output.append(running / window if index >= window - 1 else None)
    return output


def rolling_annualized_volatility(
    prices: list[float], window: int = VOLATILITY_WINDOW
) -> list[float | None]:
    """Return sample standard deviation of daily returns, annualized by sqrt(252)."""
    if window < 2:
        raise ValueError("volatility window must be at least 2")
    returns: list[float | None] = [None]
    returns.extend(prices[index] / prices[index - 1] - 1 for index in range(1, len(prices)))
    output: list[float | None] = []
    for index in range(len(prices)):
        start = index - window + 1
        sample = returns[start : index + 1] if start >= 1 else []
        if len(sample) != window or any(value is None for value in sample):
            output.append(None)
            continue
        numeric = [float(value) for value in sample if value is not None]
        mean = sum(numeric) / window
        variance = sum((value - mean) ** 2 for value in numeric) / (window - 1)
        output.append(math.sqrt(variance) * math.sqrt(252))
    return output


def allocation_for_state(trend_state: str, volatility: float | None) -> tuple[str, float, float, float]:
    if trend_state == "Cash" or volatility is None or volatility > HIGH_VOLATILITY:
        return "Cash", 0.0, 0.0, 1.0
    if volatility > LOW_VOLATILITY:
        return "50% SSO / 50% SPY", 0.5, 0.5, 0.0
    return "SSO", 0.0, 1.0, 0.0

def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * probability
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def signal_for_close(spy_close: float, sma200: float, previous_position: str) -> tuple[str, str, str]:
    upper = sma200 * BUY_BAND
    lower = sma200 * SELL_BAND
    if spy_close > upper:
        if previous_position == "Cash":
            return "Buy SSO", "SSO", "Buy SSO: SPY adjusted close is above SMA200 × 1.01."
        return "No Action", "SSO", "Hold SSO: SPY remains above the upper SMA200 band."
    if spy_close < lower:
        if previous_position == "SSO":
            return "Sell to Cash", "Cash", "Sell SSO: SPY adjusted close is below SMA200 × 0.99."
        return "No Action", "Cash", "Hold Cash: SPY remains below the lower SMA200 band."
    return (
        "No Action",
        previous_position,
        f"No action: SPY is between the bands, so the prior {previous_position} position persists.",
    )


def maximum_drawdown(values: Iterable[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1)
    return worst


def build_daily_rows(
    spy_series: dict[str, float],
    sso_series: dict[str, float],
    *,
    sma_window: int = 200,
) -> list[DailyRow]:
    spy_dates = sorted(spy_series)
    spy_sma = simple_moving_average([spy_series[day] for day in spy_dates], sma_window)
    spy_volatility = rolling_annualized_volatility([spy_series[day] for day in spy_dates])
    sma_by_date = dict(zip(spy_dates, spy_sma))
    volatility_by_date = dict(zip(spy_dates, spy_volatility))
    active_dates = sorted(day for day in sso_series if day in spy_series and sma_by_date.get(day) is not None)
    if not active_dates:
        raise ValueError("No overlapping SPY/SSO dates have a valid SMA200.")

    rows: list[DailyRow] = []
    previous_trend_state = "Cash"
    previous_position = "Cash"
    strategy_value = STARTING_VALUE
    benchmark_value = STARTING_VALUE
    strategy_peak = STARTING_VALUE
    benchmark_peak = STARTING_VALUE
    previous_spy: float | None = None
    previous_sso: float | None = None

    for index, day in enumerate(active_dates):
        spy_close = spy_series[day]
        sso_close = sso_series[day]
        sma200 = sma_by_date[day]
        assert sma200 is not None

        spy_return = 0.0 if previous_spy is None else spy_close / previous_spy - 1
        sso_return = 0.0 if previous_sso is None else sso_close / previous_sso - 1
        if index > 0 and previous_position == "SSO":
            strategy_return = sso_return
        elif index > 0 and previous_position == "50% SSO / 50% SPY":
            strategy_return = 0.5 * sso_return + 0.5 * spy_return
        else:
            strategy_return = 0.0
        if index > 0:
            strategy_value *= 1 + strategy_return
            benchmark_value *= 1 + spy_return

        trend_signal, trend_state, trend_reason = signal_for_close(
            spy_close, sma200, previous_trend_state
        )
        volatility = volatility_by_date[day]
        position, target_spy, target_sso, target_cash = allocation_for_state(trend_state, volatility)
        if position == previous_position:
            signal = "No Action"
        elif position == "Cash":
            signal = "Move to Cash"
        elif position == "SSO":
            signal = "Rebalance to SSO"
        else:
            signal = "Rebalance to 50% SSO / 50% SPY"
        if trend_state == "Cash":
            reason = trend_reason
        elif volatility is None:
            reason = "Hold Cash: 20-day annualized SPY volatility is not yet available."
        elif volatility <= LOW_VOLATILITY:
            reason = f"{trend_reason} Volatility is {volatility:.2%}, at or below 15%; target 100% SSO."
        elif volatility <= HIGH_VOLATILITY:
            reason = f"{trend_reason} Volatility is {volatility:.2%}, above 15% through 25%; target 50% SSO / 50% SPY."
        else:
            reason = f"{trend_reason} Volatility is {volatility:.2%}, above 25%; target Cash."
        strategy_peak = max(strategy_peak, strategy_value)
        benchmark_peak = max(benchmark_peak, benchmark_value)

        rows.append(
            DailyRow(
                date=day,
                spy_close=spy_close,
                sso_close=sso_close,
                sma200=sma200,
                spread=spy_close / sma200 - 1,
                buy_threshold=sma200 * BUY_BAND,
                sell_threshold=sma200 * SELL_BAND,
                spy_20d_volatility=volatility,
                trend_signal=trend_signal,
                trend_state=trend_state,
                signal=signal,
                position=position,
                target_spy_pct=target_spy,
                target_sso_pct=target_sso,
                target_cash_pct=target_cash,
                reason=reason,
                spy_daily_return=spy_return,
                sso_daily_return=sso_return,
                strategy_return=strategy_return,
                strategy_value=strategy_value,
                spy_benchmark_value=benchmark_value,
                strategy_drawdown=strategy_value / strategy_peak - 1,
                spy_drawdown=benchmark_value / benchmark_peak - 1,
            )
        )

        previous_trend_state = trend_state
        previous_position = position
        previous_spy = spy_close
        previous_sso = sso_close

    attach_spread_cycles(rows)
    return rows


def attach_spread_cycles(rows: list[DailyRow]) -> list[dict]:
    cycles: list[dict] = []
    active: list[DailyRow] = []
    cycle_number = 0

    for row in rows:
        if row.trend_signal == "Buy SSO":
            cycle_number += 1
            active = [row]
        elif active:
            active.append(row)

        if active:
            row.spread_cycle = cycle_number

        if active and row.trend_signal == "Sell to Cash":
            cycles.append(_finish_cycle(cycle_number, active, "closed"))
            active = []

    if active:
        cycles.append(_finish_cycle(cycle_number, active, "open"))

    cycle_map = {cycle["cycle"]: cycle for cycle in cycles}
    for row in rows:
        if row.spread_cycle is None:
            continue
        cycle = cycle_map[row.spread_cycle]
        row.cycle_high_floor = cycle["high_range_floor"]
        row.cycle_max_spread = cycle["max_spread"]
        row.cycle_max_date = cycle["max_spread_date"]
        row.in_cycle_high_range = bool(
            row.spread is not None and row.spread >= cycle["high_range_floor"]
        )
    return cycles


def _finish_cycle(cycle_number: int, rows: list[DailyRow], status: str) -> dict:
    spreads = [row.spread for row in rows if row.spread is not None]
    assert spreads
    floor = percentile(spreads, 0.90)
    max_row = max(rows, key=lambda row: row.spread if row.spread is not None else -math.inf)
    high_rows = [row for row in rows if row.spread is not None and row.spread >= floor]
    return {
        "cycle": cycle_number,
        "status": status,
        "buy_date": rows[0].date,
        "sell_date": rows[-1].date if status == "closed" else None,
        "duration_trading_days": len(rows),
        "min_spread": min(spreads),
        "high_range_floor": floor,
        "max_spread": max(spreads),
        "max_spread_date": max_row.date,
        "high_range_days": len(high_rows),
        "current_spread": rows[-1].spread if status == "open" else None,
        "current_in_high_range": (
            rows[-1].spread is not None and rows[-1].spread >= floor
            if status == "open"
            else None
        ),
    }


def spread_cycles(rows: list[DailyRow]) -> list[dict]:
    cycles: list[dict] = []
    current_number: int | None = None
    current_rows: list[DailyRow] = []
    for row in rows:
        if row.spread_cycle != current_number:
            if current_rows and current_number is not None:
                status = "closed" if current_rows[-1].trend_signal == "Sell to Cash" else "open"
                cycles.append(_finish_cycle(current_number, current_rows, status))
            current_number = row.spread_cycle
            current_rows = [row] if current_number is not None else []
        elif current_number is not None:
            current_rows.append(row)
    if current_rows and current_number is not None:
        status = "closed" if current_rows[-1].trend_signal == "Sell to Cash" else "open"
        cycles.append(_finish_cycle(current_number, current_rows, status))
    return cycles


def calendar_cycles(rows: list[DailyRow], lengths: tuple[int, ...] = (1, 2, 3, 5, 10)) -> list[dict]:
    if not rows:
        return []
    years = sorted({int(row.date[:4]) for row in rows})
    last_complete_year = date.fromisoformat(rows[-1].date).year - 1
    by_year: dict[int, list[DailyRow]] = {}
    for row in rows:
        by_year.setdefault(int(row.date[:4]), []).append(row)

    output: list[dict] = []
    for length in lengths:
        for start_year in years:
            end_year = start_year + length - 1
            if end_year > last_complete_year or any(year not in by_year for year in range(start_year, end_year + 1)):
                continue
            period = [row for row in rows if start_year <= int(row.date[:4]) <= end_year]
            if len(period) < 2:
                continue
            strategy_value = STARTING_VALUE
            spy_value = STARTING_VALUE
            strategy_values = [strategy_value]
            spy_values = [spy_value]
            for row in period[1:]:
                strategy_value *= 1 + row.strategy_return
                spy_value *= 1 + row.spy_daily_return
                strategy_values.append(strategy_value)
                spy_values.append(spy_value)
            output.append(
                {
                    "cycle_years": length,
                    "start_year": start_year,
                    "end_year": end_year,
                    "start_date": period[0].date,
                    "end_date": period[-1].date,
                    "strategy_final": strategy_value,
                    "spy_final": spy_value,
                    "strategy_return": strategy_value / STARTING_VALUE - 1,
                    "spy_return": spy_value / STARTING_VALUE - 1,
                    "strategy_max_drawdown": maximum_drawdown(strategy_values),
                    "spy_max_drawdown": maximum_drawdown(spy_values),
                    "strategy_beat_spy": strategy_value > spy_value,
                    "strategy_positive": strategy_value > STARTING_VALUE,
                }
            )
    return output
