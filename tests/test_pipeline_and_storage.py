import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from alphapulse.config import AppConfig
from alphapulse.exporting import export_trade_ledger_csv
from alphapulse.io import load_market_snapshots
from alphapulse.learning import LearningEngine
from alphapulse.pipeline import PhaseOnePipeline
from alphapulse.storage import SQLiteLogger


class PipelineAndStorageTests(unittest.TestCase):
    def test_pipeline_approves_only_candidates_passing_scanner_and_liquidity(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")
        results = PhaseOnePipeline(AppConfig()).evaluate(snapshots)
        paper_trades = {result.ticker for result in results if result.paper_trade.decision == "PAPER_TRADE"}
        rejected = {result.ticker for result in results if result.paper_trade.decision == "REJECT"}

        self.assertIn("ABCD", paper_trades)
        self.assertIn("EDGE", paper_trades)
        self.assertIn("LOWQ", rejected)
        self.assertIn("DILU", rejected)
        self.assertNotIn("SLOW", paper_trades)

    def test_pipeline_updates_paper_account_equity(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")
        pipeline = PhaseOnePipeline(AppConfig())
        results = pipeline.evaluate(snapshots)
        paper_trades = [result.paper_trade for result in results if result.paper_trade.decision == "PAPER_TRADE"]

        self.assertEqual(len(paper_trades), 2)
        self.assertNotEqual(pipeline.account.state.current_equity, 1000)
        self.assertAlmostEqual(pipeline.account.state.realized_pnl, sum(t.pnl_usd for t in paper_trades))

    def test_sqlite_logger_persists_phase_one_results(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")
        pipeline = PhaseOnePipeline(AppConfig())
        results = pipeline.evaluate(snapshots)

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "alphapulse.db"
            logger = SQLiteLogger(db_path)
            logger.log_run(results)
            logger.log_account_state(pipeline.account.state)

            with closing(sqlite3.connect(db_path)) as conn:
                scanner_count = conn.execute("SELECT COUNT(*) FROM scanner_results").fetchone()[0]
                liquidity_count = conn.execute("SELECT COUNT(*) FROM liquidity_metrics").fetchone()[0]
                catalyst_count = conn.execute("SELECT COUNT(*) FROM catalyst_results").fetchone()[0]
                setup_count = conn.execute("SELECT COUNT(*) FROM technical_setups").fetchone()[0]
                paper_count = conn.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]
                paper_trade_count = conn.execute(
                    "SELECT COUNT(*) FROM paper_trades WHERE decision = 'PAPER_TRADE'"
                ).fetchone()[0]
                account_snapshot_count = conn.execute("SELECT COUNT(*) FROM account_snapshots").fetchone()[0]

        self.assertEqual(scanner_count, 6)
        self.assertEqual(liquidity_count, 6)
        self.assertEqual(catalyst_count, 6)
        self.assertEqual(setup_count, 6)
        self.assertEqual(paper_count, 6)
        self.assertEqual(paper_trade_count, 2)
        self.assertEqual(account_snapshot_count, 1)

    def test_learning_engine_reports_closed_paper_trades(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")
        pipeline = PhaseOnePipeline(AppConfig())
        results = pipeline.evaluate(snapshots)

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "alphapulse.db"
            SQLiteLogger(db_path).log_run(results)
            report = LearningEngine(db_path).report()

        self.assertEqual(report["total_trades"], 2)
        self.assertIn("by_setup", report)
        self.assertIn("recommendations", report)

    def test_dashboard_summary_and_trade_ledger_export(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")
        pipeline = PhaseOnePipeline(AppConfig(), trading_day="2026-06-09")
        results = pipeline.evaluate(snapshots)

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "alphapulse.db"
            output_path = Path(tmp_dir) / "ledger.csv"
            logger = SQLiteLogger(db_path)
            logger.log_run(results)
            logger.log_account_state(pipeline.account.state)

            summary = logger.dashboard_summary()
            export_trade_ledger_csv(db_path, output_path)
            exported = output_path.read_text(encoding="utf-8-sig")

        self.assertEqual(summary["signals"]["paper_trades"], 2)
        self.assertAlmostEqual(summary["account"]["current_equity"], pipeline.account.state.current_equity)
        self.assertIn("P/L Summary", exported)
        self.assertIn("AlphaPulse Paper Trading Ledger", exported)
        self.assertIn("ABCD", exported)

    def test_account_state_can_continue_across_runs(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "alphapulse.db"
            logger = SQLiteLogger(db_path)

            first_pipeline = PhaseOnePipeline(AppConfig())
            first_results = first_pipeline.evaluate(snapshots)
            logger.log_run(first_results)
            logger.log_account_state(first_pipeline.account.state)

            loaded_state = logger.load_latest_account_state()
            second_pipeline = PhaseOnePipeline(AppConfig(), account_state=loaded_state)
            second_results = second_pipeline.evaluate(snapshots)
            logger.log_run(second_results)
            logger.log_account_state(second_pipeline.account.state)

            recent = logger.recent_paper_trades(limit=3)

        self.assertIsNotNone(loaded_state)
        self.assertGreater(second_pipeline.account.state.current_equity, first_pipeline.account.state.current_equity)
        self.assertEqual(len(recent), 3)

    def test_new_trading_day_resets_daily_pnl_without_resetting_equity(self):
        snapshots = load_market_snapshots("data/sample_market_snapshot.csv")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "alphapulse.db"
            logger = SQLiteLogger(db_path)

            first_pipeline = PhaseOnePipeline(AppConfig(), trading_day="2026-06-09")
            first_results = first_pipeline.evaluate(snapshots)
            logger.log_run(first_results)
            logger.log_account_state(first_pipeline.account.state)

            loaded_state = logger.load_latest_account_state()
            second_pipeline = PhaseOnePipeline(
                AppConfig(),
                account_state=loaded_state,
                trading_day="2026-06-10",
            )
            second_results = second_pipeline.evaluate(snapshots)
            second_day_pnl = sum(
                result.paper_trade.pnl_usd
                for result in second_results
                if result.paper_trade.decision == "PAPER_TRADE"
            )

        self.assertEqual(second_pipeline.account.state.trading_day, "2026-06-10")
        self.assertAlmostEqual(second_pipeline.account.state.daily_pnl, second_day_pnl)
        self.assertGreater(second_pipeline.account.state.realized_pnl, second_pipeline.account.state.daily_pnl)


if __name__ == "__main__":
    unittest.main()
