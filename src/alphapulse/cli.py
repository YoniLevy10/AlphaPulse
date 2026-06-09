import argparse
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from alphapulse.config import AppConfig
from alphapulse.io import load_market_snapshots
from alphapulse.learning import LearningEngine
from alphapulse.pipeline import PhaseOnePipeline
from alphapulse.storage import SQLiteLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alphapulse")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Run Phase 1 scan against a CSV market snapshot")
    scan.add_argument("--input", required=True, help="Path to market snapshot CSV")
    scan.add_argument("--db", default="data/alphapulse.db", help="SQLite database path")
    scan.add_argument(
        "--fresh-account",
        action="store_true",
        help="Ignore saved account state and start this run from configured starting capital",
    )
    scan.add_argument(
        "--starting-capital",
        type=float,
        default=None,
        help="Override starting capital for a fresh account run",
    )
    scan.add_argument(
        "--trading-day",
        default=date.today().isoformat(),
        help="Trading day for daily PnL tracking, YYYY-MM-DD",
    )
    scan.add_argument(
        "--approved-only",
        action="store_true",
        help="Print only candidates approved for research",
    )
    learn = subparsers.add_parser("learn", help="Generate learning report from paper trades")
    learn.add_argument("--db", default="data/alphapulse.db", help="SQLite database path")

    account = subparsers.add_parser("account", help="Show latest paper account state")
    account.add_argument("--db", default="data/alphapulse.db", help="SQLite database path")

    trades = subparsers.add_parser("trades", help="List recent paper trade records")
    trades.add_argument("--db", default="data/alphapulse.db", help="SQLite database path")
    trades.add_argument("--limit", type=int, default=20, help="Number of recent rows to show")
    return parser


def run_scan(args: argparse.Namespace) -> int:
    snapshots = load_market_snapshots(args.input)
    config = AppConfig()
    if args.starting_capital is not None:
        config = replace(
            config,
            account=replace(config.account, starting_capital=args.starting_capital),
        )

    logger = SQLiteLogger(args.db)
    account_state = None if args.fresh_account else logger.load_latest_account_state()
    pipeline = PhaseOnePipeline(config, account_state=account_state, trading_day=args.trading_day)
    results = pipeline.evaluate(snapshots)

    logger.log_run(results)
    logger.log_account_state(pipeline.account.state)

    printable = [r for r in results if r.approved_for_research] if args.approved_only else results
    print(
        "ticker,decision,setup,scanner_score,liquidity_score,"
        "catalyst_score,setup_score,confidence,risk_level,shares,position_value,"
        "risk_amount,entry,stop,target,exit_price,pnl_usd,r_multiple,max_hold_minutes"
    )
    for result in sorted(
        printable,
        key=lambda r: (
            r.paper_trade.decision == "PAPER_TRADE",
            r.risk.confidence,
            r.scanner.scanner_score,
            r.liquidity.liquidity_score,
        ),
        reverse=True,
    ):
        print(
            f"{result.ticker},"
            f"{result.paper_trade.decision},"
            f"{result.paper_trade.setup},"
            f"{result.scanner.scanner_score},"
            f"{result.liquidity.liquidity_score},"
            f"{result.catalyst.catalyst_score},"
            f"{result.technical.setup_score},"
            f"{result.risk.confidence},"
            f"{result.risk.risk_level},"
            f"{result.paper_trade.shares},"
            f"{result.paper_trade.position_value:.2f},"
            f"{result.paper_trade.risk_amount:.2f},"
            f"{result.paper_trade.theoretical_entry:.4f},"
            f"{result.paper_trade.stop:.4f},"
            f"{result.paper_trade.target:.4f},"
            f"{'' if result.paper_trade.exit_price is None else f'{result.paper_trade.exit_price:.4f}'},"
            f"{result.paper_trade.pnl_usd:.2f},"
            f"{'' if result.paper_trade.r_multiple is None else f'{result.paper_trade.r_multiple:.2f}'},"
            f"{result.paper_trade.max_hold_minutes}"
        )

    paper_trades = sum(1 for result in results if result.paper_trade.decision == "PAPER_TRADE")
    watchlist = sum(1 for result in results if result.paper_trade.decision == "WATCHLIST")
    rejected = sum(1 for result in results if result.paper_trade.decision == "REJECT")
    print(
        f"\nlogged_signals={len(results)} paper_trades={paper_trades} "
        f"watchlist={watchlist} rejected={rejected} db={Path(args.db)}"
    )
    print(
        f"account_equity={pipeline.account.state.current_equity:.2f} "
        f"cash_available={pipeline.account.state.cash_available:.2f} "
        f"daily_pnl={pipeline.account.state.daily_pnl:.2f} "
        f"realized_pnl={pipeline.account.state.realized_pnl:.2f} "
        f"trading_enabled={str(pipeline.account.state.trading_enabled).lower()}"
    )
    return 0


def run_account(args: argparse.Namespace) -> int:
    state = SQLiteLogger(args.db).load_latest_account_state()
    if state is None:
        print("No account snapshot found.")
        return 0
    print(
        "trading_day,starting_capital,current_equity,cash_available,daily_pnl,"
        "realized_pnl,unrealized_pnl,max_daily_loss_usd,max_open_positions,trading_enabled"
    )
    print(
        f"{state.trading_day},"
        f"{state.starting_capital:.2f},"
        f"{state.current_equity:.2f},"
        f"{state.cash_available:.2f},"
        f"{state.daily_pnl:.2f},"
        f"{state.realized_pnl:.2f},"
        f"{state.unrealized_pnl:.2f},"
        f"{state.max_daily_loss_usd:.2f},"
        f"{state.max_open_positions},"
        f"{str(state.trading_enabled).lower()}"
    )
    return 0


def run_trades(args: argparse.Namespace) -> int:
    rows = SQLiteLogger(args.db).recent_paper_trades(limit=args.limit)
    print("id,ticker,decision,setup,shares,entry,exit,pnl_usd,r_multiple,win_loss,confidence,created_at")
    for row in rows:
        exit_price = "" if row["exit_price"] is None else f"{row['exit_price']:.4f}"
        r_multiple = "" if row["r_multiple"] is None else f"{row['r_multiple']:.2f}"
        print(
            f"{row['id']},"
            f"{row['ticker']},"
            f"{row['decision']},"
            f"{row['setup']},"
            f"{row['shares']},"
            f"{row['theoretical_entry']:.4f},"
            f"{exit_price},"
            f"{row['pnl_usd']:.2f},"
            f"{r_multiple},"
            f"{row['win_loss']},"
            f"{row['confidence']},"
            f"{row['created_at']}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return run_scan(args)
    if args.command == "learn":
        print(json.dumps(LearningEngine(args.db).report(), indent=2, sort_keys=True))
        return 0
    if args.command == "account":
        return run_account(args)
    if args.command == "trades":
        return run_trades(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
