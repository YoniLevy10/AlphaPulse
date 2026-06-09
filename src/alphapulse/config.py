from dataclasses import dataclass


@dataclass(frozen=True)
class ScannerConfig:
    min_price: float = 0.01
    max_price: float = 5.00
    min_relative_volume: float = 2.0
    min_price_momentum_pct: float = 8.0
    min_gap_pct: float = 5.0
    low_float_max_shares: int = 25_000_000
    min_scanner_score: int = 65


@dataclass(frozen=True)
class LiquidityConfig:
    max_spread_pct: float = 4.0
    hard_reject_spread_pct: float = 5.0
    min_daily_dollar_volume: int = 1_000_000
    min_avg_trade_size: int = 100
    max_slippage_estimate: float = 2.0
    min_volume_consistency_score: int = 55
    min_level2_depth_score: int = 60
    min_liquidity_score: int = 60


@dataclass(frozen=True)
class TechnicalConfig:
    min_setup_score: int = 65
    default_max_hold_minutes: int = 90
    minimum_reward_r_multiple: float = 1.7


@dataclass(frozen=True)
class CatalystConfig:
    positive_catalysts: tuple[str, ...] = (
        "FDA",
        "CONTRACT",
        "PARTNERSHIP",
        "EARNINGS",
        "NEWS",
    )
    high_risk_catalysts: tuple[str, ...] = (
        "OFFERING",
        "DILUTION",
        "REVERSE_SPLIT",
        "BANKRUPTCY",
    )


@dataclass(frozen=True)
class RiskConfig:
    no_overnight_holds: bool = True
    typical_hold_min_minutes: int = 5
    typical_hold_max_minutes: int = 120
    risk_per_trade_min_pct: float = 0.5
    risk_per_trade_max_pct: float = 1.0
    max_daily_loss_pct: float = 3.0
    max_open_positions: int = 3
    reject_spread_pct_above: float = 5.0
    avoid_market_orders: bool = True
    min_confidence_for_paper_trade: int = 68


@dataclass(frozen=True)
class AccountConfig:
    starting_capital: float = 1_000.0
    risk_per_trade_pct: float = 1.0
    min_risk_per_trade_pct: float = 0.5
    max_risk_per_trade_pct: float = 1.0
    max_position_value_pct: float = 25.0
    max_daily_loss_pct: float = 3.0
    max_open_positions: int = 3
    minimum_reward_r_multiple: float = 1.5
    trading_enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    scanner: ScannerConfig = ScannerConfig()
    liquidity: LiquidityConfig = LiquidityConfig()
    technical: TechnicalConfig = TechnicalConfig()
    catalyst: CatalystConfig = CatalystConfig()
    risk: RiskConfig = RiskConfig()
    account: AccountConfig = AccountConfig()
