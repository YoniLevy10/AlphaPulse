import json
import sqlite3
from contextlib import closing
from pathlib import Path

from alphapulse.models import (
    CandidateResult,
    CatalystResult,
    AccountState,
    LiquidityResult,
    PaperTradeDecision,
    ScannerResult,
    TechnicalSetupResult,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS scanner_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    scanner_score INTEGER NOT NULL,
    passed INTEGER NOT NULL,
    reasons_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS liquidity_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    spread_pct REAL NOT NULL,
    slippage_estimate REAL NOT NULL,
    daily_dollar_volume INTEGER NOT NULL,
    volume_consistency_score INTEGER NOT NULL,
    level2_depth_score INTEGER NOT NULL,
    liquidity_score INTEGER NOT NULL,
    tradable INTEGER NOT NULL,
    reasons_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalyst_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    catalyst_type TEXT NOT NULL,
    catalyst_score INTEGER NOT NULL,
    real_catalyst INTEGER NOT NULL,
    dilution_risk TEXT NOT NULL,
    risk_flags_json TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS technical_setups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    setup TEXT NOT NULL,
    setup_score INTEGER NOT NULL,
    entry_trigger TEXT NOT NULL,
    theoretical_entry REAL NOT NULL,
    stop REAL NOT NULL,
    target REAL NOT NULL,
    max_hold_minutes INTEGER NOT NULL,
    reasons_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    setup TEXT NOT NULL,
    entry_trigger TEXT NOT NULL,
    theoretical_entry REAL NOT NULL,
    stop REAL NOT NULL,
    target REAL NOT NULL,
    max_hold_minutes INTEGER NOT NULL,
    reason TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    decision TEXT NOT NULL,
    shares INTEGER NOT NULL DEFAULT 0,
    position_value REAL NOT NULL DEFAULT 0,
    risk_amount REAL NOT NULL DEFAULT 0,
    scanner_score INTEGER NOT NULL DEFAULT 0,
    technical_score INTEGER NOT NULL DEFAULT 0,
    momentum_score INTEGER NOT NULL DEFAULT 0,
    catalyst_score INTEGER NOT NULL DEFAULT 0,
    liquidity_score INTEGER NOT NULL DEFAULT 0,
    news_type TEXT NOT NULL DEFAULT 'NONE',
    float_category TEXT NOT NULL DEFAULT 'unknown',
    spread_pct REAL NOT NULL DEFAULT 0,
    relative_volume REAL NOT NULL DEFAULT 0,
    time_of_day TEXT NOT NULL DEFAULT 'unknown',
    market_condition TEXT NOT NULL DEFAULT 'unknown',
    exit_price REAL,
    exit_reason TEXT,
    pnl_usd REAL NOT NULL DEFAULT 0,
    pnl_pct REAL NOT NULL DEFAULT 0,
    r_multiple REAL,
    win_loss TEXT NOT NULL DEFAULT 'UNREALIZED',
    max_favorable_excursion REAL NOT NULL DEFAULT 0,
    max_adverse_excursion REAL NOT NULL DEFAULT 0,
    hold_minutes INTEGER NOT NULL DEFAULT 0,
    slippage_estimate REAL NOT NULL DEFAULT 0,
    rule_violations_json TEXT NOT NULL DEFAULT '[]',
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    starting_capital REAL NOT NULL,
    current_equity REAL NOT NULL,
    cash_available REAL NOT NULL,
    open_positions_json TEXT NOT NULL,
    daily_pnl REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    max_daily_loss_usd REAL NOT NULL,
    max_open_positions INTEGER NOT NULL,
    trading_enabled INTEGER NOT NULL,
    trading_day TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    scanner_score INTEGER NOT NULL,
    liquidity_score INTEGER NOT NULL,
    setup TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    decision TEXT NOT NULL,
    approved_for_research INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


class SQLiteLogger:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.executescript(SCHEMA)
                self._ensure_column(conn, "liquidity_metrics", "volume_consistency_score", "INTEGER NOT NULL DEFAULT 0")
                self._ensure_column(conn, "candidate_results", "setup", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(conn, "candidate_results", "confidence", "INTEGER NOT NULL DEFAULT 0")
                self._ensure_column(conn, "candidate_results", "decision", "TEXT NOT NULL DEFAULT ''")
                self._ensure_column(conn, "account_snapshots", "trading_day", "TEXT NOT NULL DEFAULT ''")
                self._ensure_paper_trade_columns(conn)

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = {
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

    def _ensure_paper_trade_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            "shares": "INTEGER NOT NULL DEFAULT 0",
            "position_value": "REAL NOT NULL DEFAULT 0",
            "risk_amount": "REAL NOT NULL DEFAULT 0",
            "scanner_score": "INTEGER NOT NULL DEFAULT 0",
            "technical_score": "INTEGER NOT NULL DEFAULT 0",
            "momentum_score": "INTEGER NOT NULL DEFAULT 0",
            "catalyst_score": "INTEGER NOT NULL DEFAULT 0",
            "liquidity_score": "INTEGER NOT NULL DEFAULT 0",
            "news_type": "TEXT NOT NULL DEFAULT 'NONE'",
            "float_category": "TEXT NOT NULL DEFAULT 'unknown'",
            "spread_pct": "REAL NOT NULL DEFAULT 0",
            "relative_volume": "REAL NOT NULL DEFAULT 0",
            "time_of_day": "TEXT NOT NULL DEFAULT 'unknown'",
            "market_condition": "TEXT NOT NULL DEFAULT 'unknown'",
            "exit_reason": "TEXT",
            "pnl_usd": "REAL NOT NULL DEFAULT 0",
            "pnl_pct": "REAL NOT NULL DEFAULT 0",
            "win_loss": "TEXT NOT NULL DEFAULT 'UNREALIZED'",
            "max_favorable_excursion": "REAL NOT NULL DEFAULT 0",
            "max_adverse_excursion": "REAL NOT NULL DEFAULT 0",
            "hold_minutes": "INTEGER NOT NULL DEFAULT 0",
            "slippage_estimate": "REAL NOT NULL DEFAULT 0",
            "rule_violations_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column_name, column_definition in columns.items():
            self._ensure_column(conn, "paper_trades", column_name, column_definition)

    def log_scanner_result(self, result: ScannerResult) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO scanner_results
                        (ticker, scanner_score, passed, reasons_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        result.ticker,
                        result.scanner_score,
                        int(result.passed),
                        json.dumps(result.reasons),
                        result.created_at.isoformat(),
                    ),
                )

    def log_liquidity_result(self, result: LiquidityResult) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO liquidity_metrics
                    (
                        ticker,
                        spread_pct,
                        slippage_estimate,
                        daily_dollar_volume,
                        volume_consistency_score,
                        level2_depth_score,
                        liquidity_score,
                            tradable,
                            reasons_json,
                            created_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.ticker,
                        result.spread_pct,
                        result.slippage_estimate,
                        result.daily_dollar_volume,
                        result.volume_consistency_score,
                        result.level2_depth_score,
                        result.liquidity_score,
                        int(result.tradable),
                        json.dumps(result.reasons),
                        result.created_at.isoformat(),
                    ),
                )

    def log_catalyst_result(self, result: CatalystResult) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO catalyst_results
                        (
                            ticker,
                            catalyst_type,
                            catalyst_score,
                            real_catalyst,
                            dilution_risk,
                            risk_flags_json,
                            reasons_json,
                            created_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.ticker,
                        result.catalyst_type,
                        result.catalyst_score,
                        int(result.real_catalyst),
                        result.dilution_risk,
                        json.dumps(result.risk_flags),
                        json.dumps(result.reasons),
                        result.created_at.isoformat(),
                    ),
                )

    def log_technical_setup(self, result: TechnicalSetupResult) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO technical_setups
                        (
                            ticker,
                            setup,
                            setup_score,
                            entry_trigger,
                            theoretical_entry,
                            stop,
                            target,
                            max_hold_minutes,
                            reasons_json,
                            created_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.ticker,
                        result.setup,
                        result.setup_score,
                        result.entry_trigger,
                        result.theoretical_entry,
                        result.stop,
                        result.target,
                        result.max_hold_minutes,
                        json.dumps(result.reasons),
                        result.created_at.isoformat(),
                    ),
                )

    def log_paper_trade(self, result: PaperTradeDecision) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO paper_trades
                        (
                            ticker,
                            setup,
                            entry_trigger,
                            theoretical_entry,
                            stop,
                            target,
                            max_hold_minutes,
                            reason,
                            confidence,
                            risk_level,
                            decision,
                            shares,
                            position_value,
                            risk_amount,
                            scanner_score,
                            technical_score,
                            momentum_score,
                            catalyst_score,
                            liquidity_score,
                            news_type,
                            float_category,
                            spread_pct,
                            relative_volume,
                            time_of_day,
                            market_condition,
                            exit_price,
                            exit_reason,
                            pnl_usd,
                            pnl_pct,
                            r_multiple,
                            win_loss,
                            max_favorable_excursion,
                            max_adverse_excursion,
                            hold_minutes,
                            slippage_estimate,
                            rule_violations_json,
                            result,
                            created_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.ticker,
                        result.setup,
                        result.entry_trigger,
                        result.theoretical_entry,
                        result.stop,
                        result.target,
                        result.max_hold_minutes,
                        result.reason,
                        result.confidence,
                        result.risk_level,
                        result.decision,
                        result.shares,
                        result.position_value,
                        result.risk_amount,
                        result.scanner_score,
                        result.technical_score,
                        result.momentum_score,
                        result.catalyst_score,
                        result.liquidity_score,
                        result.news_type,
                        result.float_category,
                        result.spread_pct,
                        result.relative_volume,
                        result.time_of_day,
                        result.market_condition,
                        result.exit_price,
                        result.exit_reason,
                        result.pnl_usd,
                        result.pnl_pct,
                        result.r_multiple,
                        result.win_loss,
                        result.max_favorable_excursion,
                        result.max_adverse_excursion,
                        result.hold_minutes,
                        result.slippage_estimate,
                        json.dumps(result.rule_violations),
                        result.result,
                        result.created_at.isoformat(),
                    ),
                )

    def log_account_state(self, state: AccountState) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO account_snapshots
                        (
                            starting_capital,
                            current_equity,
                            cash_available,
                            open_positions_json,
                            daily_pnl,
                            realized_pnl,
                            unrealized_pnl,
                            max_daily_loss_usd,
                            max_open_positions,
                            trading_enabled,
                            trading_day,
                            created_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        state.starting_capital,
                        state.current_equity,
                        state.cash_available,
                        json.dumps(state.open_positions),
                        state.daily_pnl,
                        state.realized_pnl,
                        state.unrealized_pnl,
                        state.max_daily_loss_usd,
                        state.max_open_positions,
                        int(state.trading_enabled),
                        state.trading_day,
                    ),
                )

    def load_latest_account_state(self) -> AccountState | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT *
                FROM account_snapshots
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return AccountState(
            starting_capital=row["starting_capital"],
            current_equity=row["current_equity"],
            cash_available=row["cash_available"],
            open_positions=tuple(json.loads(row["open_positions_json"])),
            daily_pnl=row["daily_pnl"],
            realized_pnl=row["realized_pnl"],
            unrealized_pnl=row["unrealized_pnl"],
            max_daily_loss_usd=row["max_daily_loss_usd"],
            max_open_positions=row["max_open_positions"],
            trading_enabled=bool(row["trading_enabled"]),
            trading_day=row["trading_day"],
        )

    def recent_paper_trades(self, limit: int = 20) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return list(
                conn.execute(
                    """
                    SELECT
                        id,
                        ticker,
                        decision,
                        setup,
                        shares,
                        theoretical_entry,
                        exit_price,
                        pnl_usd,
                        r_multiple,
                        win_loss,
                        confidence,
                        created_at
                    FROM paper_trades
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            )

    def trade_ledger_rows(self) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return list(
                conn.execute(
                    """
                    SELECT
                        id,
                        ticker,
                        decision,
                        setup,
                        entry_trigger,
                        theoretical_entry,
                        stop,
                        target,
                        max_hold_minutes,
                        reason,
                        confidence,
                        risk_level,
                        shares,
                        position_value,
                        risk_amount,
                        scanner_score,
                        technical_score,
                        momentum_score,
                        catalyst_score,
                        liquidity_score,
                        news_type,
                        float_category,
                        spread_pct,
                        relative_volume,
                        time_of_day,
                        market_condition,
                        exit_price,
                        exit_reason,
                        pnl_usd,
                        pnl_pct,
                        r_multiple,
                        win_loss,
                        max_favorable_excursion,
                        max_adverse_excursion,
                        hold_minutes,
                        slippage_estimate,
                        rule_violations_json,
                        result,
                        created_at
                    FROM paper_trades
                    ORDER BY id
                    """
                )
            )

    def dashboard_summary(self) -> dict[str, object]:
        state = self.load_latest_account_state()
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            trade_stats = conn.execute(
                """
                SELECT
                    COUNT(CASE WHEN decision = 'PAPER_TRADE' THEN 1 END) AS paper_trades,
                    COUNT(CASE WHEN decision = 'WATCHLIST' THEN 1 END) AS watchlist,
                    COUNT(CASE WHEN decision = 'REJECT' THEN 1 END) AS rejected,
                    COALESCE(SUM(CASE WHEN decision = 'PAPER_TRADE' THEN pnl_usd ELSE 0 END), 0) AS total_pnl,
                    COALESCE(AVG(CASE WHEN decision = 'PAPER_TRADE' THEN r_multiple END), 0) AS avg_r,
                    COALESCE(SUM(CASE WHEN decision = 'PAPER_TRADE' AND pnl_usd > 0 THEN 1 ELSE 0 END), 0) AS wins,
                    COALESCE(SUM(CASE WHEN decision = 'PAPER_TRADE' AND pnl_usd < 0 THEN 1 ELSE 0 END), 0) AS losses
                FROM paper_trades
                """
            ).fetchone()
            recent = list(
                conn.execute(
                    """
                    SELECT ticker, decision, setup, confidence, pnl_usd, r_multiple, created_at
                    FROM paper_trades
                    ORDER BY id DESC
                    LIMIT 8
                    """
                )
            )

        paper_trades = trade_stats["paper_trades"] or 0
        wins = trade_stats["wins"] or 0
        win_rate = (wins / paper_trades) if paper_trades else 0.0
        return {
            "account": None if state is None else {
                "trading_day": state.trading_day,
                "starting_capital": state.starting_capital,
                "current_equity": state.current_equity,
                "cash_available": state.cash_available,
                "daily_pnl": state.daily_pnl,
                "realized_pnl": state.realized_pnl,
                "unrealized_pnl": state.unrealized_pnl,
                "max_daily_loss_usd": state.max_daily_loss_usd,
                "max_open_positions": state.max_open_positions,
                "trading_enabled": state.trading_enabled,
            },
            "signals": {
                "paper_trades": paper_trades,
                "watchlist": trade_stats["watchlist"] or 0,
                "rejected": trade_stats["rejected"] or 0,
                "wins": wins,
                "losses": trade_stats["losses"] or 0,
                "win_rate": round(win_rate, 4),
                "avg_r": round(trade_stats["avg_r"] or 0.0, 4),
                "total_pnl": round(trade_stats["total_pnl"] or 0.0, 2),
            },
            "recent": [dict(row) for row in recent],
        }

    def log_candidate_result(self, result: CandidateResult) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO candidate_results
                        (
                        ticker,
                        scanner_score,
                        liquidity_score,
                        setup,
                        confidence,
                        decision,
                        approved_for_research,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.ticker,
                        result.scanner.scanner_score,
                        result.liquidity.liquidity_score,
                        result.technical.setup,
                        result.risk.confidence,
                        result.risk.decision,
                        int(result.approved_for_research),
                        result.scanner.created_at.isoformat(),
                    ),
                )

    def log_run(self, results: list[CandidateResult]) -> None:
        for result in results:
            self.log_scanner_result(result.scanner)
            self.log_liquidity_result(result.liquidity)
            self.log_catalyst_result(result.catalyst)
            self.log_technical_setup(result.technical)
            self.log_paper_trade(result.paper_trade)
            self.log_candidate_result(result)
