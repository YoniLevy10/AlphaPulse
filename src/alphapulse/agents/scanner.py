from alphapulse.config import ScannerConfig
from alphapulse.models import MarketSnapshot, ScannerResult


class ScannerAgent:
    def __init__(self, config: ScannerConfig):
        self.config = config

    def evaluate(self, snapshot: MarketSnapshot) -> ScannerResult:
        score = 0
        reasons: list[str] = []

        if self.config.min_price <= snapshot.price <= self.config.max_price:
            score += 20
            reasons.append("price_in_penny_stock_range")
        else:
            reasons.append("price_out_of_range")

        if snapshot.relative_volume >= self.config.min_relative_volume:
            score += 20
            reasons.append("relative_volume_elevated")
        else:
            reasons.append("relative_volume_below_threshold")

        gap_pct = max(snapshot.premarket_gap_pct, snapshot.intraday_gap_pct)
        if gap_pct >= self.config.min_gap_pct:
            score += 15
            reasons.append("tradable_gap_present")
        else:
            reasons.append("gap_below_threshold")

        if snapshot.pct_change >= self.config.min_price_momentum_pct:
            score += 15
            reasons.append("strong_intraday_change")
        elif snapshot.pct_change > 0:
            score += 8
            reasons.append("positive_intraday_change")
        else:
            reasons.append("no_positive_price_momentum")

        if snapshot.news_catalyst:
            score += 15
            reasons.append("news_catalyst_present")
        else:
            reasons.append("no_news_catalyst")

        if snapshot.float_shares and snapshot.float_shares <= self.config.low_float_max_shares:
            score += 10
            reasons.append("low_float_available")

        if snapshot.short_interest_pct >= 15:
            score += 10
            reasons.append("short_squeeze_potential")
        elif snapshot.short_interest_pct >= 8:
            score += 5
            reasons.append("moderate_short_interest")

        score = min(score, 100)
        return ScannerResult(
            ticker=snapshot.ticker,
            scanner_score=score,
            passed=score >= self.config.min_scanner_score,
            reasons=tuple(reasons),
        )
