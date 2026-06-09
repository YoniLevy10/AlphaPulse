import csv
from pathlib import Path

from alphapulse.models import MarketSnapshot


REQUIRED_COLUMNS = {
    "ticker",
    "price",
    "previous_close",
    "volume",
    "average_volume",
    "daily_dollar_volume",
    "avg_trade_size",
    "spread_pct",
    "slippage_estimate",
    "level2_depth_score",
}

REAL_DATA_REQUIRED_COLUMNS = {
    "data_source",
    "feed_timestamp_utc",
    "is_real_time",
    "execution_mode",
}

DISALLOWED_REAL_DATA_SOURCES = {"sample", "demo", "mock", "manual", "backtest", "simulated_csv"}
ALLOWED_REAL_EXECUTION_MODES = {"PAPER_BROKER", "BROKER_PAPER", "BANK_PAPER"}


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def validate_real_data_row(row: dict[str, str], row_number: int) -> None:
    missing = [column for column in REAL_DATA_REQUIRED_COLUMNS if not row.get(column)]
    if missing:
        raise ValueError(
            f"Real-data mode row {row_number} missing required columns: {', '.join(sorted(missing))}"
        )

    data_source = row["data_source"].strip().lower()
    execution_mode = row["execution_mode"].strip().upper()
    if data_source in DISALLOWED_REAL_DATA_SOURCES:
        raise ValueError(f"Real-data mode row {row_number} uses disallowed data_source: {row['data_source']}")
    if not parse_bool(row["is_real_time"]):
        raise ValueError(f"Real-data mode row {row_number} is not marked real-time")
    if execution_mode not in ALLOWED_REAL_EXECUTION_MODES:
        raise ValueError(
            f"Real-data mode row {row_number} has unsupported execution_mode: {row['execution_mode']}"
        )
    if row.get("simulated_exit_price"):
        raise ValueError(f"Real-data mode row {row_number} contains simulated_exit_price")


def load_market_snapshots(path: str | Path, require_real_data: bool = False) -> list[MarketSnapshot]:
    snapshots: list[MarketSnapshot] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Market snapshot CSV missing required columns: {missing_list}")
        if require_real_data:
            real_missing = REAL_DATA_REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if real_missing:
                missing_list = ", ".join(sorted(real_missing))
                raise ValueError(f"Real-data mode CSV missing required columns: {missing_list}")
        for row_number, row in enumerate(reader, start=2):
            if require_real_data:
                validate_real_data_row(row, row_number)
            snapshots.append(
                MarketSnapshot(
                    ticker=row["ticker"].strip().upper(),
                    price=float(row["price"]),
                    previous_close=float(row["previous_close"]),
                    volume=int(row["volume"]),
                    average_volume=int(row["average_volume"]),
                    daily_dollar_volume=int(row["daily_dollar_volume"]),
                    avg_trade_size=int(row["avg_trade_size"]),
                    spread_pct=float(row["spread_pct"]),
                    slippage_estimate=float(row["slippage_estimate"]),
                    level2_depth_score=int(row["level2_depth_score"]),
                    news_catalyst=parse_bool(row.get("news_catalyst", "false")),
                    short_interest_pct=float(row.get("short_interest_pct", 0) or 0),
                    premarket_gap_pct=float(row.get("premarket_gap_pct", 0) or 0),
                    intraday_gap_pct=float(row.get("intraday_gap_pct", 0) or 0),
                    float_shares=parse_optional_int(row.get("float_shares")),
                    volume_consistency_score=int(row.get("volume_consistency_score", 50) or 50),
                    catalyst_type=row.get("catalyst_type", "NONE"),
                    dilution_risk=row.get("dilution_risk", "none"),
                    above_vwap=parse_bool(row.get("above_vwap", "false")),
                    reclaimed_vwap=parse_bool(row.get("reclaimed_vwap", "false")),
                    broke_high_of_day=parse_bool(row.get("broke_high_of_day", "false")),
                    pullback_holding=parse_bool(row.get("pullback_holding", "false")),
                    opening_range_breakout=parse_bool(row.get("opening_range_breakout", "false")),
                    news_spike=parse_bool(row.get("news_spike", "false")),
                    vwap=float(row.get("vwap", 0) or 0),
                    high_of_day=float(row.get("high_of_day", 0) or 0),
                    opening_range_high=float(row.get("opening_range_high", 0) or 0),
                    opening_range_low=float(row.get("opening_range_low", 0) or 0),
                    atr=float(row.get("atr", 0) or 0),
                    minutes_since_open=int(row.get("minutes_since_open", 0) or 0),
                    market_condition=row.get("market_condition", "unknown"),
                    simulated_exit_price=(
                        float(row["simulated_exit_price"])
                        if row.get("simulated_exit_price")
                        else None
                    ),
                    simulated_exit_reason=row.get("simulated_exit_reason", "EOD_FLAT"),
                    simulated_hold_minutes=int(row.get("simulated_hold_minutes", 0) or 0),
                    max_favorable_excursion=float(row.get("max_favorable_excursion", 0) or 0),
                    max_adverse_excursion=float(row.get("max_adverse_excursion", 0) or 0),
                    data_source=row.get("data_source", "sample"),
                    feed_timestamp_utc=row.get("feed_timestamp_utc", ""),
                    is_real_time=parse_bool(row.get("is_real_time", "false")),
                    execution_mode=row.get("execution_mode", "SIMULATED_CSV"),
                    source_latency_ms=int(row.get("source_latency_ms", 0) or 0),
                )
            )
    return snapshots
