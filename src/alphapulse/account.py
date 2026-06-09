from dataclasses import replace
from datetime import date

from alphapulse.config import AccountConfig
from alphapulse.models import (
    AccountState,
    CatalystResult,
    LiquidityResult,
    MarketSnapshot,
    PaperTradeDecision,
    PositionSizingResult,
    ScannerResult,
    TechnicalSetupResult,
    calculate_shares,
    float_category,
    time_of_day,
)


class PaperAccount:
    def __init__(
        self,
        config: AccountConfig,
        state: AccountState | None = None,
        trading_day: str | None = None,
    ):
        self.config = config
        active_day = trading_day or date.today().isoformat()
        if state is not None and state.trading_day != active_day:
            state = replace(
                state,
                daily_pnl=0.0,
                max_daily_loss_usd=round(state.current_equity * (config.max_daily_loss_pct / 100), 2),
                trading_enabled=config.trading_enabled,
                trading_day=active_day,
            )
        self.state = state or AccountState(
            starting_capital=config.starting_capital,
            current_equity=config.starting_capital,
            cash_available=config.starting_capital,
            open_positions=(),
            daily_pnl=0.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            max_daily_loss_usd=config.starting_capital * (config.max_daily_loss_pct / 100),
            max_open_positions=config.max_open_positions,
            trading_enabled=config.trading_enabled,
            trading_day=active_day,
        )

    def apply_trade_decision(
        self,
        base_decision: PaperTradeDecision,
        snapshot: MarketSnapshot,
        scanner: ScannerResult,
        liquidity: LiquidityResult,
        catalyst: CatalystResult,
        technical: TechnicalSetupResult,
    ) -> PaperTradeDecision:
        sizing = self.evaluate_position_size(base_decision, liquidity)
        enriched = self._enrich_decision(
            base_decision=base_decision,
            snapshot=snapshot,
            scanner=scanner,
            liquidity=liquidity,
            catalyst=catalyst,
            technical=technical,
            sizing=sizing,
        )

        if not sizing.allowed:
            return replace(
                enriched,
                decision=sizing.decision,
                reason="; ".join((*base_decision.reason.split("; "), *sizing.reasons)),
                result="NO_TRADE",
                rule_violations=sizing.reasons,
            )

        closed = self._close_same_day(enriched, snapshot)
        self._apply_closed_trade(closed)
        return closed

    def evaluate_position_size(
        self,
        decision: PaperTradeDecision,
        liquidity: LiquidityResult,
    ) -> PositionSizingResult:
        reasons: list[str] = []

        if decision.decision != "PAPER_TRADE":
            return PositionSizingResult(
                approved=False,
                shares=0,
                position_value=0.0,
                risk_amount=0.0,
                risk_per_share=0.0,
                reward_r_multiple=0.0,
                decision=decision.decision,
                reasons=("signal_not_approved_by_risk_engine",),
            )

        if not self.state.trading_enabled:
            reasons.append("trading_disabled")
        if self.state.daily_pnl <= -self.state.max_daily_loss_usd:
            reasons.append("max_daily_loss_reached")
        if len(self.state.open_positions) >= self.state.max_open_positions:
            reasons.append("max_open_positions_reached")
        if decision.ticker in self.state.open_positions:
            reasons.append("no_averaging_down_or_duplicate_position")
        if decision.theoretical_entry <= 0 or decision.stop <= 0:
            reasons.append("invalid_entry_or_stop")
        if decision.theoretical_entry <= decision.stop:
            reasons.append("stop_not_below_entry_for_long_trade")
        if liquidity.spread_pct > 5:
            reasons.append("spread_too_high_for_account")
        if not liquidity.tradable:
            reasons.append("liquidity_not_tradeable_for_account")

        shares, position_value, allowed_risk, risk_per_share = calculate_shares(
            current_equity=self.state.current_equity,
            entry_price=decision.theoretical_entry,
            stop_price=decision.stop,
            risk_per_trade_pct=self.config.risk_per_trade_pct,
            max_position_value_pct=self.config.max_position_value_pct,
        )
        reward_r = 0.0
        if risk_per_share > 0:
            reward_r = (decision.target - decision.theoretical_entry) / risk_per_share

        max_position_value = self.state.current_equity * (self.config.max_position_value_pct / 100)
        actual_risk = shares * risk_per_share

        if shares <= 0:
            reasons.append("shares_zero_after_sizing")
        if position_value > max_position_value:
            reasons.append("position_value_above_max")
        if position_value > self.state.cash_available:
            reasons.append("insufficient_cash_available")
        if actual_risk > allowed_risk + 0.01:
            reasons.append("actual_risk_above_allowed")
        if reward_r < self.config.minimum_reward_r_multiple:
            reasons.append("risk_reward_below_minimum")

        approved = not reasons
        return PositionSizingResult(
            approved=approved,
            shares=shares if approved else 0,
            position_value=round(position_value if approved else 0.0, 2),
            risk_amount=round(actual_risk if approved else 0.0, 2),
            risk_per_share=round(risk_per_share, 4),
            reward_r_multiple=round(reward_r, 2),
            decision="PAPER_TRADE" if approved else "REJECT",
            reasons=tuple(reasons),
        )

    def _enrich_decision(
        self,
        base_decision: PaperTradeDecision,
        snapshot: MarketSnapshot,
        scanner: ScannerResult,
        liquidity: LiquidityResult,
        catalyst: CatalystResult,
        technical: TechnicalSetupResult,
        sizing: PositionSizingResult,
    ) -> PaperTradeDecision:
        return replace(
            base_decision,
            shares=sizing.shares,
            position_value=sizing.position_value,
            risk_amount=sizing.risk_amount,
            scanner_score=scanner.scanner_score,
            technical_score=technical.setup_score,
            catalyst_score=catalyst.catalyst_score,
            liquidity_score=liquidity.liquidity_score,
            news_type=catalyst.catalyst_type,
            float_category=float_category(snapshot.float_shares),
            spread_pct=liquidity.spread_pct,
            relative_volume=round(snapshot.relative_volume, 2),
            time_of_day=time_of_day(snapshot.minutes_since_open),
            market_condition=snapshot.market_condition,
            slippage_estimate=liquidity.slippage_estimate,
            max_favorable_excursion=snapshot.max_favorable_excursion,
            max_adverse_excursion=snapshot.max_adverse_excursion,
        )

    def _close_same_day(
        self,
        decision: PaperTradeDecision,
        snapshot: MarketSnapshot,
    ) -> PaperTradeDecision:
        exit_price = snapshot.simulated_exit_price
        exit_reason = snapshot.simulated_exit_reason
        if exit_price is None:
            exit_price = decision.theoretical_entry
            exit_reason = "NO_EXIT_SIM_FLAT"

        pnl_usd = round((exit_price - decision.theoretical_entry) * decision.shares, 2)
        pnl_pct = round((pnl_usd / decision.position_value) * 100, 2) if decision.position_value else 0.0
        r_multiple = round(pnl_usd / decision.risk_amount, 2) if decision.risk_amount else 0.0
        win_loss = "WIN" if pnl_usd > 0 else "LOSS" if pnl_usd < 0 else "FLAT"

        return replace(
            decision,
            exit_price=round(exit_price, 4),
            exit_reason=exit_reason,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            r_multiple=r_multiple,
            win_loss=win_loss,
            hold_minutes=snapshot.simulated_hold_minutes or decision.max_hold_minutes,
            result="CLOSED_SIMULATED",
        )

    def _apply_closed_trade(self, decision: PaperTradeDecision) -> None:
        realized_pnl = round(self.state.realized_pnl + decision.pnl_usd, 2)
        daily_pnl = round(self.state.daily_pnl + decision.pnl_usd, 2)
        current_equity = round(self.state.starting_capital + realized_pnl + self.state.unrealized_pnl, 2)
        self.state = replace(
            self.state,
            current_equity=current_equity,
            cash_available=current_equity,
            realized_pnl=realized_pnl,
            daily_pnl=daily_pnl,
            trading_enabled=daily_pnl > -self.state.max_daily_loss_usd,
        )
