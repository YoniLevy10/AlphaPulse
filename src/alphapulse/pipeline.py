from alphapulse.account import PaperAccount
from alphapulse.agents.catalyst import CatalystAgent
from alphapulse.agents.liquidity import LiquidityAgent
from alphapulse.agents.risk import RiskEngine
from alphapulse.agents.scanner import ScannerAgent
from alphapulse.agents.technical import TechnicalIntradaySetupAgent
from alphapulse.config import AppConfig
from alphapulse.models import AccountState, CandidateResult, MarketSnapshot, PaperTradeDecision


class PhaseOnePipeline:
    def __init__(
        self,
        config: AppConfig,
        account_state: AccountState | None = None,
        trading_day: str | None = None,
    ):
        self.account = PaperAccount(config.account, account_state, trading_day=trading_day)
        self.scanner = ScannerAgent(config.scanner)
        self.liquidity = LiquidityAgent(config.liquidity)
        self.catalyst = CatalystAgent(config.catalyst)
        self.technical = TechnicalIntradaySetupAgent(config.technical)
        self.risk = RiskEngine(config.risk)

    def evaluate(self, snapshots: list[MarketSnapshot]) -> list[CandidateResult]:
        results: list[CandidateResult] = []
        for snapshot in snapshots:
            scanner_result = self.scanner.evaluate(snapshot)
            liquidity_result = self.liquidity.evaluate(snapshot)
            catalyst_result = self.catalyst.evaluate(snapshot)
            technical_result = self.technical.evaluate(snapshot)
            risk_result = self.risk.evaluate(
                scanner=scanner_result,
                liquidity=liquidity_result,
                catalyst=catalyst_result,
                technical=technical_result,
            )
            paper_trade = PaperTradeDecision(
                ticker=snapshot.ticker,
                setup=technical_result.setup,
                entry_trigger=technical_result.entry_trigger,
                theoretical_entry=technical_result.theoretical_entry,
                stop=technical_result.stop,
                target=technical_result.target,
                max_hold_minutes=risk_result.max_hold_minutes,
                reason="; ".join(risk_result.reasons or technical_result.reasons),
                confidence=risk_result.confidence,
                risk_level=risk_result.risk_level,
                decision=risk_result.decision,
            )
            paper_trade = self.account.apply_trade_decision(
                base_decision=paper_trade,
                snapshot=snapshot,
                scanner=scanner_result,
                liquidity=liquidity_result,
                catalyst=catalyst_result,
                technical=technical_result,
            )
            results.append(
                CandidateResult(
                    ticker=snapshot.ticker,
                    scanner=scanner_result,
                    liquidity=liquidity_result,
                    catalyst=catalyst_result,
                    technical=technical_result,
                    risk=risk_result,
                    paper_trade=paper_trade,
                )
            )
        return results
