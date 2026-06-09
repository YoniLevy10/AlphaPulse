from alphapulse.config import RiskConfig
from alphapulse.models import (
    CatalystResult,
    LiquidityResult,
    RiskResult,
    ScannerResult,
    TechnicalSetupResult,
)


class RiskEngine:
    def __init__(self, config: RiskConfig):
        self.config = config

    def evaluate(
        self,
        scanner: ScannerResult,
        liquidity: LiquidityResult,
        catalyst: CatalystResult,
        technical: TechnicalSetupResult,
    ) -> RiskResult:
        reasons: list[str] = []
        confidence = self._confidence(scanner, liquidity, catalyst, technical)
        approved = True
        risk_level = "medium"
        risk_per_trade_pct = self.config.risk_per_trade_max_pct

        if not scanner.passed:
            approved = False
            reasons.append("scanner_score_below_trade_threshold")
        if not liquidity.tradable:
            approved = False
            reasons.append("liquidity_not_tradeable")
        if technical.setup == "NO_VALID_INTRADAY_SETUP":
            approved = False
            reasons.append("no_valid_intraday_setup")
        if not catalyst.real_catalyst:
            approved = False
            reasons.append("no_trade_quality_catalyst")
        if catalyst.dilution_risk == "critical":
            approved = False
            reasons.append("critical_dilution_risk_reject")
        if liquidity.spread_pct > self.config.reject_spread_pct_above:
            approved = False
            reasons.append("spread_hard_reject")
        if confidence < self.config.min_confidence_for_paper_trade:
            approved = False
            reasons.append("confidence_below_paper_trade_threshold")

        if catalyst.dilution_risk == "high":
            risk_level = "medium-high"
            risk_per_trade_pct = self.config.risk_per_trade_min_pct
            reasons.append("high_dilution_risk_reduce_size")
        elif liquidity.spread_pct > 3 or technical.reward_r_multiple < 2:
            risk_level = "medium-high"
            risk_per_trade_pct = 0.75
            reasons.append("balanced_aggressive_size_control")
        elif confidence >= 82 and liquidity.liquidity_score >= 80:
            risk_level = "medium"

        if self.config.no_overnight_holds:
            reasons.append("same_day_exit_required")
        if self.config.avoid_market_orders:
            reasons.append("limit_orders_only")

        decision = "PAPER_TRADE" if approved else ("WATCHLIST" if scanner.passed else "REJECT")
        if not approved and (not liquidity.tradable or catalyst.dilution_risk == "critical"):
            decision = "REJECT"

        return RiskResult(
            ticker=scanner.ticker,
            approved=approved,
            risk_level=risk_level,
            confidence=confidence,
            decision=decision,
            risk_per_trade_pct=risk_per_trade_pct,
            max_hold_minutes=min(technical.max_hold_minutes, self.config.typical_hold_max_minutes),
            reasons=tuple(reasons),
        )

    def _confidence(
        self,
        scanner: ScannerResult,
        liquidity: LiquidityResult,
        catalyst: CatalystResult,
        technical: TechnicalSetupResult,
    ) -> int:
        raw = (
            scanner.scanner_score * 0.25
            + liquidity.liquidity_score * 0.25
            + catalyst.catalyst_score * 0.20
            + technical.setup_score * 0.30
        )
        if catalyst.dilution_risk == "high":
            raw -= 8
        if catalyst.dilution_risk == "critical":
            raw -= 30
        return max(0, min(100, round(raw)))
