from alphapulse.config import LiquidityConfig
from alphapulse.models import LiquidityResult, MarketSnapshot


class LiquidityAgent:
    def __init__(self, config: LiquidityConfig):
        self.config = config

    def evaluate(self, snapshot: MarketSnapshot) -> LiquidityResult:
        score = 100
        reasons: list[str] = []

        if snapshot.spread_pct > self.config.max_spread_pct:
            penalty = min(35, int((snapshot.spread_pct - self.config.max_spread_pct) * 8))
            score -= penalty
            reasons.append("spread_above_threshold")
        else:
            reasons.append("spread_acceptable")

        if snapshot.daily_dollar_volume < self.config.min_daily_dollar_volume:
            score -= 30
            reasons.append("daily_dollar_volume_below_threshold")
        else:
            reasons.append("daily_dollar_volume_acceptable")

        if snapshot.avg_trade_size < self.config.min_avg_trade_size:
            score -= 15
            reasons.append("avg_trade_size_below_threshold")
        else:
            reasons.append("avg_trade_size_acceptable")

        if snapshot.slippage_estimate > self.config.max_slippage_estimate:
            penalty = min(25, int((snapshot.slippage_estimate - self.config.max_slippage_estimate) * 10))
            score -= penalty
            reasons.append("slippage_above_threshold")
        else:
            reasons.append("slippage_acceptable")

        if snapshot.volume_consistency_score < self.config.min_volume_consistency_score:
            score -= min(25, self.config.min_volume_consistency_score - snapshot.volume_consistency_score)
            reasons.append("volume_consistency_below_threshold")
        else:
            reasons.append("volume_consistency_acceptable")

        if snapshot.level2_depth_score < self.config.min_level2_depth_score:
            score -= min(25, self.config.min_level2_depth_score - snapshot.level2_depth_score)
            reasons.append("level2_depth_below_threshold")
        else:
            reasons.append("level2_depth_acceptable")

        score = max(0, min(score, 100))
        hard_reject = (
            snapshot.spread_pct > self.config.hard_reject_spread_pct
            or snapshot.daily_dollar_volume < self.config.min_daily_dollar_volume
            or snapshot.volume_consistency_score < self.config.min_volume_consistency_score
            or snapshot.level2_depth_score < self.config.min_level2_depth_score
        )

        return LiquidityResult(
            ticker=snapshot.ticker,
            liquidity_score=score,
            tradable=(not hard_reject) and score >= self.config.min_liquidity_score,
            spread_pct=snapshot.spread_pct,
            slippage_estimate=snapshot.slippage_estimate,
            daily_dollar_volume=snapshot.daily_dollar_volume,
            volume_consistency_score=snapshot.volume_consistency_score,
            level2_depth_score=snapshot.level2_depth_score,
            reasons=tuple(reasons),
        )
