import csv
from pathlib import Path

from alphapulse.storage import SQLiteLogger


LEDGER_COLUMNS = [
    "id",
    "created_at",
    "ticker",
    "decision",
    "setup",
    "entry_trigger",
    "theoretical_entry",
    "stop",
    "target",
    "exit_price",
    "exit_reason",
    "shares",
    "position_value",
    "risk_amount",
    "pnl_usd",
    "pnl_pct",
    "r_multiple",
    "win_loss",
    "confidence",
    "risk_level",
    "scanner_score",
    "technical_score",
    "momentum_score",
    "catalyst_score",
    "liquidity_score",
    "news_type",
    "float_category",
    "spread_pct",
    "relative_volume",
    "time_of_day",
    "market_condition",
    "max_hold_minutes",
    "hold_minutes",
    "max_favorable_excursion",
    "max_adverse_excursion",
    "slippage_estimate",
    "result",
    "reason",
    "rule_violations_json",
]


def export_trade_ledger_csv(db_path: str | Path, output_path: str | Path) -> Path:
    logger = SQLiteLogger(db_path)
    summary = logger.dashboard_summary()
    rows = logger.trade_ledger_rows()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    account = summary["account"] or {}
    signals = summary["signals"]
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["AlphaPulse Paper Trading Ledger"])
        writer.writerow([])
        writer.writerow(["P/L Summary"])
        writer.writerow(["Trading Day", account.get("trading_day", "")])
        writer.writerow(["Starting Capital", account.get("starting_capital", "")])
        writer.writerow(["Current Equity", account.get("current_equity", "")])
        writer.writerow(["Cash Available", account.get("cash_available", "")])
        writer.writerow(["Daily P/L USD", account.get("daily_pnl", "")])
        writer.writerow(["Realized P/L USD", account.get("realized_pnl", "")])
        writer.writerow(["Unrealized P/L USD", account.get("unrealized_pnl", "")])
        writer.writerow(["Total Paper Trade P/L USD", signals["total_pnl"]])
        writer.writerow(["Paper Trades", signals["paper_trades"]])
        writer.writerow(["Watchlist", signals["watchlist"]])
        writer.writerow(["Rejected", signals["rejected"]])
        writer.writerow(["Win Rate", signals["win_rate"]])
        writer.writerow(["Average R", signals["avg_r"]])
        writer.writerow([])
        writer.writerow(LEDGER_COLUMNS)
        for row in rows:
            writer.writerow([row[column] for column in LEDGER_COLUMNS])

    return output
