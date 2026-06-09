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


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def load_market_snapshots(path: str | Path) -> list[MarketSnapshot]:
    snapshots: list[MarketSnapshot] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Market snapshot CSV missing required columns: {missing_list}")
        for row in reader:
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
                )
            )
    return snapshots
