# AlphaPulse Paper Experiment Playbook

This system is ready for a controlled paper-only experiment. It is not a live
trading bot and must not be connected to real order execution.

## Experiment Goal

Collect 100-200 simulated day-trading decisions and evaluate whether the system
has positive expectancy before any discussion of live trading.

## Daily Workflow

1. Prepare a market snapshot CSV using the schema in `data/sample_market_snapshot.csv`.
2. Run a scan with the current trading day.
3. Review account state.
4. Review recent trades.
5. Generate the learning report after the session.

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli scan --input data/sample_market_snapshot.csv --db data/alphapulse.db --trading-day 2026-06-09
python -m alphapulse.cli account --db data/alphapulse.db
python -m alphapulse.cli trades --db data/alphapulse.db --limit 20
python -m alphapulse.cli learn --db data/alphapulse.db
```

Use `--fresh-account` only for smoke tests. For the real paper experiment, let
the system continue from the latest account snapshot.

## Current Guardrails

- Starting capital: `$1,000`
- Max risk per paper trade: `1%` of current equity
- Max position value: `25%` of current equity
- Max daily loss: `3%` of equity at start of day
- Max open positions: `3`
- No overnight holds
- No averaging down
- No martingale sizing
- No forced trades
- No live order execution

## Minimum Data Needed Per Candidate

Required CSV columns:

- `ticker`
- `price`
- `previous_close`
- `volume`
- `average_volume`
- `daily_dollar_volume`
- `avg_trade_size`
- `spread_pct`
- `slippage_estimate`
- `level2_depth_score`

Useful optional columns:

- `catalyst_type`
- `dilution_risk`
- `premarket_gap_pct`
- `intraday_gap_pct`
- `float_shares`
- `volume_consistency_score`
- `above_vwap`
- `reclaimed_vwap`
- `broke_high_of_day`
- `opening_range_breakout`
- `vwap`
- `high_of_day`
- `opening_range_high`
- `opening_range_low`
- `atr`
- `minutes_since_open`
- `market_condition`
- `simulated_exit_price`
- `simulated_exit_reason`
- `simulated_hold_minutes`

## Milestones

- 50 paper trades: initial report only
- 100 paper trades: review threshold recommendations
- 200 paper trades: consider limited adaptive scoring
- 300+ paper trades: evaluate whether there is real edge

## Readiness Criteria Before Live Trading Discussion

- At least 300 paper trades
- Profit factor above `1.3`
- Average R consistently positive
- Max drawdown below `15%`
- Weak setup/news/time buckets identified and filtered
- No unresolved data-quality issues
- No risk-rule violations

