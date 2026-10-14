"""Small checks for the business definitions, not UI implementation details."""

import unittest

import pandas as pd

from delivery_metrics import analysis_orders, delivery_clues, late_rate_status, load_orders, summary, weekly_rates


class DeliveryMetricsTest(unittest.TestCase):
    def test_date_level_lateness_and_eligible_denominator(self):
        rows = pd.DataFrame(
            [
                ("a", "SP", "delivered", "2018-01-01", "2018-01-02", "2018-01-03 23:59:00", "2018-01-03"),
                ("b", "SP", "delivered", "2018-01-01", "2018-01-02", "2018-01-04 00:01:00", "2018-01-03"),
                ("c", "RJ", "shipped", "2018-01-01", "2018-01-02", None, "2018-01-03"),
                ("d", "RJ", "delivered", "2018-01-01", "2018-01-02", None, "2018-01-03"),
            ],
            columns=[
                "order_id", "customer_state", "order_status", "order_purchase_timestamp",
                "order_delivered_carrier_date", "order_delivered_customer_date",
                "order_estimated_delivery_date",
            ],
        )
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "orders.csv"
            rows.to_csv(path, index=False)
            result = analysis_orders(load_orders(path))

        self.assertEqual(summary(result)["orders"], 2)
        self.assertEqual(summary(result)["late_orders"], 1)
        self.assertEqual(summary(result)["late_rate"], 0.5)
        self.assertEqual(summary(result)["median_late_days"], 1.0)
        self.assertEqual(weekly_rates(result)["orders"].sum(), 2)

    def test_handoff_clues_are_timing_labels(self):
        rows = pd.DataFrame({
            "order_id": ["before", "after", "missing"],
            "is_late": [True, True, True],
            "order_delivered_carrier_date": pd.to_datetime(["2018-01-02", "2018-01-04", None]),
            "promise_date": pd.to_datetime(["2018-01-03"] * 3),
            "delivered_date": pd.to_datetime(["2018-01-05"] * 3),
        })
        result = delivery_clues(rows).set_index("order_id")
        self.assertEqual(result.loc["before", "handoff_clue"], "Handed off by promised date")
        self.assertEqual(result.loc["after", "handoff_clue"], "Handed off after promised date")
        self.assertEqual(result.loc["missing", "handoff_clue"], "Handoff date missing")
        self.assertEqual(result.loc["before", "handoff_to_delivery_days"], 3)

    def test_late_rate_status_boundaries(self):
        self.assertEqual(late_rate_status(0.049)[0], "Low")
        self.assertEqual(late_rate_status(0.05)[0], "Needs attention")
        self.assertEqual(late_rate_status(0.15)[0], "Needs attention")
        self.assertEqual(late_rate_status(0.151)[0], "High risk")


if __name__ == "__main__":
    unittest.main()
