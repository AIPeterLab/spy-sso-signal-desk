import unittest

from scripts.update_signals import attach_series, latest_on_or_before


class UpdateSignalsTests(unittest.TestCase):
    def test_latest_on_or_before(self):
        series = {"2024-01-02": 12.5, "2024-01-05": 14.0}
        self.assertEqual(latest_on_or_before(series, "2024-01-04"), ("2024-01-02", 12.5))
        self.assertEqual(latest_on_or_before(series, "2024-01-05"), ("2024-01-05", 14.0))
        self.assertEqual(latest_on_or_before(series, "2024-01-01"), (None, None))

    def test_attach_series_keeps_missing_dates_explicit(self):
        daily = [{"date": "2024-01-02"}, {"date": "2024-01-03"}]
        attach_series(daily, {"2024-01-02": 12.5}, "vix_close")
        self.assertEqual(daily[0]["vix_close"], 12.5)
        self.assertIsNone(daily[1]["vix_close"])


if __name__ == "__main__":
    unittest.main()
