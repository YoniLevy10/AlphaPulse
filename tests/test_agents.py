import unittest

from alphapulse.account import PaperAccount
from alphapulse.agents.liquidity import LiquidityAgent
from alphapulse.agents.catalyst import CatalystAgent
from alphapulse.agents.risk import RiskEngine
from alphapulse.agents.scanner import ScannerAgent
from alphapulse.agents.technical import TechnicalIntradaySetupAgent
from alphapulse.config import AppConfig, CatalystConfig, LiquidityConfig, ScannerConfig, TechnicalConfig
from alphapulse.models import MarketSnapshot, PaperTradeDecision


def make_snapshot(**overrides):
    data = {
        "ticker": "ABCD",
        "price": 1.24,
        "previous_close": 0.76,
        "volume": 8_300_000,
        "average_volume": 1_800_000,
        "daily_dollar_volume": 10_292_000,
        "avg_trade_size": 520,
        "spread_pct": 1.1,
        "slippage_estimate": 0.8,
        "level2_depth_score": 84,
        "news_catalyst": True,
        "short_interest_pct": 18.5,
        "premarket_gap_pct": 22.0,
        "intraday_gap_pct": 54.3,
        "float_shares": 18_000_000,
        "volume_consistency_score": 82,
        "catalyst_type": "CONTRACT",
        "dilution_risk": "none",
        "above_vwap": True,
        "reclaimed_vwap": True,
        "broke_high_of_day": False,
        "pullback_holding": False,
        "opening_range_breakout": False,
        "news_spike": True,
        "vwap": 1.37,
        "high_of_day": 1.48,
        "opening_range_high": 1.39,
        "opening_range_low": 1.21,
        "atr": 0.08,
        "minutes_since_open": 38,
        "market_condition": "strong_momentum",
        "simulated_exit_price": 1.58,
        "simulated_exit_reason": "TARGET_AREA",
        "simulated_hold_minutes": 76,
        "max_favorable_excursion": 0.18,
        "max_adverse_excursion": -0.03,
    }
    data.update(overrides)
    return MarketSnapshot(**data)


class AgentTests(unittest.TestCase):
    def test_scanner_passes_candidate_with_catalyst_volume_and_price_momentum(self):
        result = ScannerAgent(ScannerConfig()).evaluate(make_snapshot())

        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.scanner_score, 65)
        self.assertIn("news_catalyst_present", result.reasons)
        self.assertIn("tradable_gap_present", result.reasons)

    def test_liquidity_rejects_wide_spread_even_when_candidate_has_activity(self):
        snapshot = make_snapshot(spread_pct=6.4, slippage_estimate=3.1, level2_depth_score=42)
        result = LiquidityAgent(LiquidityConfig()).evaluate(snapshot)

        self.assertFalse(result.tradable)
        self.assertIn("spread_above_threshold", result.reasons)
        self.assertIn("level2_depth_below_threshold", result.reasons)

    def test_liquidity_passes_tradeable_candidate(self):
        result = LiquidityAgent(LiquidityConfig()).evaluate(make_snapshot())

        self.assertTrue(result.tradable)
        self.assertGreaterEqual(result.liquidity_score, 60)

    def test_technical_agent_detects_vwap_reclaim(self):
        result = TechnicalIntradaySetupAgent(TechnicalConfig()).evaluate(make_snapshot())

        self.assertEqual(result.setup, "VWAP_RECLAIM")
        self.assertGreaterEqual(result.setup_score, 65)
        self.assertGreater(result.target, result.theoretical_entry)

    def test_catalyst_agent_flags_critical_dilution(self):
        result = CatalystAgent(CatalystConfig()).evaluate(
            make_snapshot(catalyst_type="OFFERING", dilution_risk="critical")
        )

        self.assertFalse(result.real_catalyst)
        self.assertIn("critical_dilution_risk", result.risk_flags)

    def test_risk_engine_rejects_critical_dilution_even_with_good_setup(self):
        config = AppConfig()
        snapshot = make_snapshot(catalyst_type="OFFERING", dilution_risk="critical")
        scanner = ScannerAgent(config.scanner).evaluate(snapshot)
        liquidity = LiquidityAgent(config.liquidity).evaluate(snapshot)
        catalyst = CatalystAgent(config.catalyst).evaluate(snapshot)
        technical = TechnicalIntradaySetupAgent(config.technical).evaluate(snapshot)
        risk = RiskEngine(config.risk).evaluate(scanner, liquidity, catalyst, technical)

        self.assertFalse(risk.approved)
        self.assertEqual(risk.decision, "REJECT")
        self.assertIn("critical_dilution_risk_reject", risk.reasons)

    def test_paper_account_sizes_and_closes_trade(self):
        config = AppConfig()
        snapshot = make_snapshot()
        scanner = ScannerAgent(config.scanner).evaluate(snapshot)
        liquidity = LiquidityAgent(config.liquidity).evaluate(snapshot)
        catalyst = CatalystAgent(config.catalyst).evaluate(snapshot)
        technical = TechnicalIntradaySetupAgent(config.technical).evaluate(snapshot)
        risk = RiskEngine(config.risk).evaluate(scanner, liquidity, catalyst, technical)

        account = PaperAccount(config.account)
        decision = account.apply_trade_decision(
            base_decision=PaperTradeDecision(
                ticker=snapshot.ticker,
                setup=technical.setup,
                entry_trigger=technical.entry_trigger,
                theoretical_entry=technical.theoretical_entry,
                stop=technical.stop,
                target=technical.target,
                max_hold_minutes=risk.max_hold_minutes,
                reason="; ".join(risk.reasons),
                confidence=risk.confidence,
                risk_level=risk.risk_level,
                decision=risk.decision,
            ),
            snapshot=snapshot,
            scanner=scanner,
            liquidity=liquidity,
            catalyst=catalyst,
            technical=technical,
        )

        self.assertEqual(decision.decision, "PAPER_TRADE")
        self.assertGreater(decision.shares, 0)
        self.assertGreater(decision.pnl_usd, 0)
        self.assertGreater(account.state.current_equity, 1000)
        self.assertEqual(decision.result, "CLOSED_SIMULATED")


if __name__ == "__main__":
    unittest.main()
