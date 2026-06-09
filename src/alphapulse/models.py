from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import floor


@dataclass(frozen=True)
class MarketSnapshot:
    ticker: str
    price: float
    previous_close: float
    volume: int
    average_volume: int
    daily_dollar_volume: int
    avg_trade_size: int
    spread_pct: float
    slippage_estimate: float
    level2_depth_score: int
    news_catalyst: bool = False
    short_interest_pct: float = 0.0
    premarket_gap_pct: float = 0.0
    intraday_gap_pct: float = 0.0
    float_shares: int | None = None
    volume_consistency_score: int = 50
    catalyst_type: str = "NONE"
    dilution_risk: str = "none"
    above_vwap: bool = False
    reclaimed_vwap: bool = False
    broke_high_of_day: bool = False
    pullback_holding: bool = False
    opening_range_breakout: bool = False
    news_spike: bool = False
    vwap: float = 0.0
    high_of_day: float = 0.0
    opening_range_high: float = 0.0
    opening_range_low: float = 0.0
    atr: float = 0.0
    minutes_since_open: int = 0
    market_condition: str = "unknown"
    simulated_exit_price: float | None = None
    simulated_exit_reason: str = "EOD_FLAT"
    simulated_hold_minutes: int = 0
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0

    @property
    def pct_change(self) -> float:
        if self.previous_close <= 0:
            return 0.0
        return ((self.price - self.previous_close) / self.previous_close) * 100

    @property
    def relative_volume(self) -> float:
        if self.average_volume <= 0:
            return 0.0
        return self.volume / self.average_volume


@dataclass(frozen=True)
class ScannerResult:
    ticker: str
    scanner_score: int
    passed: bool
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class LiquidityResult:
    ticker: str
    liquidity_score: int
    tradable: bool
    spread_pct: float
    slippage_estimate: float
    daily_dollar_volume: int
    volume_consistency_score: int
    level2_depth_score: int
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class CatalystResult:
    ticker: str
    catalyst_type: str
    catalyst_score: int
    real_catalyst: bool
    dilution_risk: str
    risk_flags: tuple[str, ...]
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class TechnicalSetupResult:
    ticker: str
    setup: str
    setup_score: int
    entry_trigger: str
    theoretical_entry: float
    stop: float
    target: float
    max_hold_minutes: int
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def reward_r_multiple(self) -> float:
        risk = self.theoretical_entry - self.stop
        if risk <= 0:
            return 0.0
        return (self.target - self.theoretical_entry) / risk


@dataclass(frozen=True)
class RiskResult:
    ticker: str
    approved: bool
    risk_level: str
    confidence: int
    decision: str
    risk_per_trade_pct: float
    max_hold_minutes: int
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PaperTradeDecision:
    ticker: str
    setup: str
    entry_trigger: str
    theoretical_entry: float
    stop: float
    target: float
    max_hold_minutes: int
    reason: str
    confidence: int
    risk_level: str
    decision: str
    shares: int = 0
    position_value: float = 0.0
    risk_amount: float = 0.0
    scanner_score: int = 0
    technical_score: int = 0
    momentum_score: int = 0
    catalyst_score: int = 0
    liquidity_score: int = 0
    news_type: str = "NONE"
    float_category: str = "unknown"
    spread_pct: float = 0.0
    relative_volume: float = 0.0
    time_of_day: str = "unknown"
    market_condition: str = "unknown"
    exit_price: float | None = None
    exit_reason: str | None = None
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    r_multiple: float | None = None
    win_loss: str = "UNREALIZED"
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    hold_minutes: int = 0
    slippage_estimate: float = 0.0
    rule_violations: tuple[str, ...] = ()
    result: str = "NO_TRADE"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AccountState:
    starting_capital: float
    current_equity: float
    cash_available: float
    open_positions: tuple[str, ...]
    daily_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    max_daily_loss_usd: float
    max_open_positions: int
    trading_enabled: bool
    trading_day: str


@dataclass(frozen=True)
class PositionSizingResult:
    approved: bool
    shares: int
    position_value: float
    risk_amount: float
    risk_per_share: float
    reward_r_multiple: float
    decision: str
    reasons: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return self.approved and self.shares > 0


def float_category(float_shares: int | None) -> str:
    if float_shares is None:
        return "unknown"
    if float_shares <= 10_000_000:
        return "micro_float"
    if float_shares <= 25_000_000:
        return "low_float"
    if float_shares <= 75_000_000:
        return "medium_float"
    return "high_float"


def time_of_day(minutes_since_open: int) -> str:
    if minutes_since_open <= 30:
        return "open_0_30"
    if minutes_since_open <= 90:
        return "morning_31_90"
    if minutes_since_open <= 240:
        return "midday_91_240"
    return "power_hour"


def calculate_shares(
    current_equity: float,
    entry_price: float,
    stop_price: float,
    risk_per_trade_pct: float,
    max_position_value_pct: float,
) -> tuple[int, float, float, float]:
    risk_amount = current_equity * (risk_per_trade_pct / 100)
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0 or entry_price <= 0:
        return 0, 0.0, risk_amount, risk_per_share
    shares_by_risk = floor(risk_amount / risk_per_share)
    shares_by_capital = floor((current_equity * (max_position_value_pct / 100)) / entry_price)
    shares = max(0, min(shares_by_risk, shares_by_capital))
    return shares, shares * entry_price, risk_amount, risk_per_share


@dataclass(frozen=True)
class CandidateResult:
    ticker: str
    scanner: ScannerResult
    liquidity: LiquidityResult
    catalyst: CatalystResult
    technical: TechnicalSetupResult
    risk: RiskResult
    paper_trade: PaperTradeDecision

    @property
    def approved_for_research(self) -> bool:
        return self.paper_trade.decision == "PAPER_TRADE"
