from alphapulse.config import TechnicalConfig
from alphapulse.models import MarketSnapshot, TechnicalSetupResult


class TechnicalIntradaySetupAgent:
    def __init__(self, config: TechnicalConfig):
        self.config = config

    def evaluate(self, snapshot: MarketSnapshot) -> TechnicalSetupResult:
        setup, score, reasons = self._detect_setup(snapshot)
        entry = round(snapshot.price, 4)
        stop = self._calculate_stop(snapshot, setup)
        risk = max(entry - stop, 0.01)
        target = round(entry + (risk * 2), 4)

        return TechnicalSetupResult(
            ticker=snapshot.ticker,
            setup=setup,
            setup_score=score,
            entry_trigger=self._entry_trigger(snapshot, setup),
            theoretical_entry=entry,
            stop=stop,
            target=target,
            max_hold_minutes=self.config.default_max_hold_minutes,
            reasons=tuple(reasons),
        )

    def _detect_setup(self, snapshot: MarketSnapshot) -> tuple[str, int, list[str]]:
        candidates: list[tuple[str, int, list[str]]] = []

        if snapshot.opening_range_breakout:
            candidates.append(
                (
                    "OPENING_RANGE_BREAKOUT",
                    72 + self._volume_bonus(snapshot),
                    ["opening_range_breakout", "intraday_momentum"],
                )
            )

        if snapshot.reclaimed_vwap:
            candidates.append(
                (
                    "VWAP_RECLAIM",
                    70 + self._volume_bonus(snapshot),
                    ["vwap_reclaim", "buyer_control_reappearing"],
                )
            )

        if snapshot.broke_high_of_day:
            candidates.append(
                (
                    "HIGH_OF_DAY_BREAKOUT",
                    68 + self._volume_bonus(snapshot),
                    ["high_of_day_breakout", "momentum_continuation"],
                )
            )

        if snapshot.pullback_holding and snapshot.above_vwap:
            candidates.append(
                (
                    "PULLBACK_CONTINUATION",
                    64 + self._volume_bonus(snapshot),
                    ["pullback_holding", "above_vwap"],
                )
            )

        if snapshot.news_spike and snapshot.news_catalyst:
            candidates.append(
                (
                    "NEWS_CATALYST_SPIKE",
                    66 + self._volume_bonus(snapshot),
                    ["news_spike", "catalyst_driven_move"],
                )
            )

        if snapshot.minutes_since_open <= 45 and snapshot.pct_change >= 10 and snapshot.relative_volume >= 2:
            candidates.append(
                (
                    "OPENING_MOMENTUM",
                    62 + self._volume_bonus(snapshot),
                    ["opening_momentum", "early_session_volume"],
                )
            )

        if not candidates:
            return "NO_VALID_INTRADAY_SETUP", 0, ["no_supported_setup_detected"]

        setup, score, reasons = max(candidates, key=lambda item: item[1])
        return setup, min(score, 100), reasons

    def _volume_bonus(self, snapshot: MarketSnapshot) -> int:
        bonus = 0
        if snapshot.relative_volume >= 5:
            bonus += 12
        elif snapshot.relative_volume >= 3:
            bonus += 8
        elif snapshot.relative_volume >= 2:
            bonus += 4

        if snapshot.volume_consistency_score >= 75:
            bonus += 6
        return bonus

    def _calculate_stop(self, snapshot: MarketSnapshot, setup: str) -> float:
        atr_buffer = snapshot.atr * 0.5 if snapshot.atr > 0 else snapshot.price * 0.03
        anchors = []
        if setup == "VWAP_RECLAIM" and snapshot.vwap > 0:
            anchors.append(snapshot.vwap - atr_buffer)
        if setup in {"OPENING_RANGE_BREAKOUT", "PULLBACK_CONTINUATION"} and snapshot.opening_range_low > 0:
            anchors.append(snapshot.opening_range_low)
        if setup == "HIGH_OF_DAY_BREAKOUT" and snapshot.high_of_day > 0:
            anchors.append(snapshot.high_of_day - atr_buffer)
        anchors.append(snapshot.price - max(atr_buffer, snapshot.price * 0.04))
        return round(max(0.01, min(anchors)), 4)

    def _entry_trigger(self, snapshot: MarketSnapshot, setup: str) -> str:
        if setup == "VWAP_RECLAIM":
            return f"Break and hold above VWAP near {snapshot.vwap:.2f} with volume"
        if setup == "HIGH_OF_DAY_BREAKOUT":
            return f"Break above high of day near {snapshot.high_of_day:.2f} with volume"
        if setup == "OPENING_RANGE_BREAKOUT":
            return f"Break above opening range high near {snapshot.opening_range_high:.2f}"
        if setup == "PULLBACK_CONTINUATION":
            return "Hold pullback support above VWAP and curl higher"
        if setup == "NEWS_CATALYST_SPIKE":
            return "News-driven spike confirms with sustained volume"
        if setup == "OPENING_MOMENTUM":
            return "Opening momentum continues after first confirmation candle"
        return "No executable intraday trigger"
