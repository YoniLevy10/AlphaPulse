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


if __name__ == "__main__":
    unittest.main()
