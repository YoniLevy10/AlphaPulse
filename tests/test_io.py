import tempfile
import unittest
from pathlib import Path

from alphapulse.io import load_market_snapshots


class IOTests(unittest.TestCase):
    def test_missing_required_csv_columns_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "bad.csv"
            csv_path.write_text("ticker,price\nABCD,1.23\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required columns"):
                load_market_snapshots(csv_path)

    def test_real_data_mode_rejects_sample_csv_without_metadata(self):
        with self.assertRaisesRegex(ValueError, "Real-data mode CSV missing required columns"):
            load_market_snapshots("data/sample_market_snapshot.csv", require_real_data=True)

    def test_real_data_mode_accepts_broker_paper_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "real.csv"
            csv_path.write_text(
                "ticker,price,previous_close,volume,average_volume,daily_dollar_volume,"
                "avg_trade_size,spread_pct,slippage_estimate,level2_depth_score,"
                "data_source,feed_timestamp_utc,is_real_time,execution_mode,source_latency_ms\n"
                "ABCD,1.23,1.00,1200000,300000,1476000,200,1.2,0.7,72,"
                "alpaca_iex,2026-06-09T14:35:00Z,true,PAPER_BROKER,120\n",
                encoding="utf-8",
            )

            snapshots = load_market_snapshots(csv_path, require_real_data=True)

        self.assertEqual(len(snapshots), 1)
        self.assertTrue(snapshots[0].is_real_time)
        self.assertEqual(snapshots[0].execution_mode, "PAPER_BROKER")

    def test_real_data_mode_rejects_simulated_exit_prices(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "bad_real.csv"
            csv_path.write_text(
                "ticker,price,previous_close,volume,average_volume,daily_dollar_volume,"
                "avg_trade_size,spread_pct,slippage_estimate,level2_depth_score,"
                "data_source,feed_timestamp_utc,is_real_time,execution_mode,simulated_exit_price\n"
                "ABCD,1.23,1.00,1200000,300000,1476000,200,1.2,0.7,72,"
                "alpaca_iex,2026-06-09T14:35:00Z,true,PAPER_BROKER,1.31\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "simulated_exit_price"):
                load_market_snapshots(csv_path, require_real_data=True)


if __name__ == "__main__":
    unittest.main()
