from alphapulse.config import CatalystConfig
from alphapulse.models import CatalystResult, MarketSnapshot


class CatalystAgent:
    def __init__(self, config: CatalystConfig):
        self.config = config

    def evaluate(self, snapshot: MarketSnapshot) -> CatalystResult:
        catalyst_type = snapshot.catalyst_type.strip().upper() or "NONE"
        dilution_risk = snapshot.dilution_risk.strip().lower() or "none"
        score = 0
        reasons: list[str] = []
        risk_flags: list[str] = []

        if catalyst_type in self.config.positive_catalysts:
            score += 75
            reasons.append("real_catalyst_detected")
        elif catalyst_type == "GENERIC_PR":
            score += 25
            reasons.append("generic_pr_fluff")
        elif catalyst_type in self.config.high_risk_catalysts:
            score += 10
            reasons.append("negative_or_financing_catalyst")
            risk_flags.append(catalyst_type.lower())
        else:
            reasons.append("no_clear_catalyst")

        if dilution_risk == "critical":
            score = min(score, 20)
            risk_flags.append("critical_dilution_risk")
            reasons.append("critical_dilution_risk")
        elif dilution_risk == "high":
            score = max(0, score - 25)
            risk_flags.append("high_dilution_risk")
            reasons.append("high_dilution_risk")

        if catalyst_type in {"FDA", "CONTRACT", "PARTNERSHIP"}:
            score = min(100, score + 15)
            reasons.append("high_quality_catalyst_category")

        return CatalystResult(
            ticker=snapshot.ticker,
            catalyst_type=catalyst_type,
            catalyst_score=max(0, min(score, 100)),
            real_catalyst=score >= 60 and catalyst_type not in self.config.high_risk_catalysts,
            dilution_risk=dilution_risk,
            risk_flags=tuple(risk_flags),
            reasons=tuple(reasons),
        )
