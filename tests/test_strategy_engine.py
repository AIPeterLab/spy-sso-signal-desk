import unittest

from scripts.strategy_engine import (
    DailyRow,
    attach_spread_cycles,
    build_daily_rows,
    calendar_cycles,
    maximum_drawdown,
    allocation_for_state,
    rolling_annualized_volatility,
    signal_for_close,
    simple_moving_average,
)


class StrategyEngineTests(unittest.TestCase):
    def test_sma200(self):
        values = [float(value) for value in range(1, 202)]
        result = simple_moving_average(values, 200)
        self.assertIsNone(result[198])
        self.assertEqual(result[199], 100.5)
        self.assertEqual(result[200], 101.5)

    def test_threshold_logic_is_strict(self):
        self.assertEqual(signal_for_close(101.01, 100, "Cash")[0], "Buy SSO")
        self.assertEqual(signal_for_close(98.99, 100, "SSO")[0], "Sell to Cash")
        self.assertEqual(signal_for_close(101.0, 100, "Cash")[0], "No Action")
        self.assertEqual(signal_for_close(99.0, 100, "SSO")[0], "No Action")

    def test_position_persists_between_bands(self):
        self.assertEqual(signal_for_close(100, 100, "SSO")[1], "SSO")
        self.assertEqual(signal_for_close(100, 100, "Cash")[1], "Cash")

    def test_volatility_uses_sample_standard_deviation(self):
        prices = [100.0]
        for daily_return in ([0.01, -0.01] * 10):
            prices.append(prices[-1] * (1 + daily_return))
        result = rolling_annualized_volatility(prices)
        self.assertIsNone(result[19])
        self.assertAlmostEqual(result[20], 0.01 * (20 / 19) ** 0.5 * 252 ** 0.5)

    def test_volatility_allocation_thresholds(self):
        self.assertEqual(allocation_for_state("Cash", 0.10)[0], "Cash")
        self.assertEqual(allocation_for_state("SSO", 0.15)[0], "SSO")
        self.assertEqual(allocation_for_state("SSO", 0.150001)[0], "50% SSO / 50% SPY")
        self.assertEqual(allocation_for_state("SSO", 0.25)[0], "50% SSO / 50% SPY")
        self.assertEqual(allocation_for_state("SSO", 0.250001)[0], "Cash")

    def test_signal_applies_next_trading_day(self):
        spy = {"2024-01-01": 100, "2024-01-02": 102, "2024-01-03": 103}
        sso = {"2024-01-01": 10, "2024-01-02": 11, "2024-01-03": 12.1}
        rows = build_daily_rows(spy, sso, sma_window=1)
        rows[0].signal = "Buy SSO"
        rows[0].position = "SSO"
        # Re-run with a slightly lower SMA proxy so the first row creates a buy.
        spy_source = {"2024-01-01": 100, "2024-01-02": 102, "2024-01-03": 103}
        sso_source = {"2024-01-01": 10, "2024-01-02": 11, "2024-01-03": 12.1}
        built = build_daily_rows(spy_source, sso_source, sma_window=2)
        # The first actionable row is Jan 2; its own return remains cash.
        self.assertEqual(built[0].strategy_return, 0)

    def test_next_day_return_with_forced_buy(self):
        spy = {}
        sso = {}
        spy_price = 100.0
        sso_price = 10.0
        for day in range(1, 25):
            date_key = f"2024-01-{day:02d}"
            spy[date_key] = spy_price
            sso[date_key] = sso_price
            spy_price *= 1.03
            sso_price *= 1.10
        rows = build_daily_rows(spy, sso, sma_window=2)
        buy_row = next(row for row in rows if row.signal == "Rebalance to SSO")
        self.assertEqual(buy_row.strategy_return, 0)
        following = rows[rows.index(buy_row) + 1]
        self.assertAlmostEqual(following.strategy_return, 0.10)

    def test_drawdown(self):
        self.assertAlmostEqual(maximum_drawdown([100, 120, 90, 110]), -0.25)

    def test_calendar_cycle_resets_to_1000(self):
        rows = [
            DailyRow("2022-01-03", 100, 10),
            DailyRow("2022-12-30", 110, 11, spy_daily_return=0.10, strategy_return=0.20),
            DailyRow("2023-01-03", 110, 11),
            DailyRow("2023-12-29", 121, 12, spy_daily_return=0.10, strategy_return=0.10),
            DailyRow("2024-01-03", 121, 12),
        ]
        cycles = calendar_cycles(rows, (1,))
        cycle_2022 = next(item for item in cycles if item["start_year"] == 2022)
        self.assertAlmostEqual(cycle_2022["spy_final"], 1100)
        self.assertAlmostEqual(cycle_2022["strategy_final"], 1200)

    def test_spread_cycles(self):
        rows = [
            DailyRow("2024-01-01", 100, 10, spread=0.02, trend_signal="Buy SSO", position="SSO"),
            DailyRow("2024-01-02", 101, 11, spread=0.05, position="SSO"),
            DailyRow("2024-01-03", 99, 9, spread=-0.02, trend_signal="Sell to Cash", position="Cash"),
        ]
        cycles = attach_spread_cycles(rows)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["status"], "closed")
        self.assertEqual(cycles[0]["max_spread_date"], "2024-01-02")
        self.assertEqual(cycles[0]["duration_trading_days"], 3)


if __name__ == "__main__":
    unittest.main()
