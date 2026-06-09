# AlphaPulse AI

Phase 1 MVP for the Penny Stock Day Trading Signal Lab.

This repository currently implements:

- Scanner Agent
- News / Catalyst Agent
- Liquidity Agent
- Technical / Intraday Setup Agent
- Risk Engine
- Paper Account Manager with `$1,000` starting capital
- Paper Trading Logger
- Learning Engine
- SQLite event/result logger
- CLI workflow against CSV market snapshots

The system is paper-only at this stage. It does not place live trades.

## Quick Start

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli scan --input data/sample_market_snapshot.csv --db data/alphapulse.db --trading-day 2026-06-09
```

Run tests:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

Generate a learning report:

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli learn --db data/alphapulse.db
```

Show current paper account state:

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli account --db data/alphapulse.db
```

List recent signal/trade records:

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli trades --db data/alphapulse.db --limit 20
```

Export an Excel-friendly trade documentation ledger:

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli export-ledger --db data/alphapulse.db --output exports/alphapulse_trade_ledger.csv
```

Run the local visual command center:

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli serve --db data/alphapulse.db --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765` in the browser. The dashboard includes a live P/L
summary strip, account state, trade documentation ledger, and learning snapshot.

For any real paper-trading session, use `--require-real-data`. This rejects
sample/backtest/simulated rows unless they include real-time broker-paper
metadata. See `REAL_DATA_POLICY.md`.

## Phase 1 Goal

Find and measure intraday penny-stock paper trade signals with:

- Sufficient scanner score
- A catalyst classification
- Tradeable liquidity
- A supported intraday setup
- Acceptable spread and slippage
- Same-day risk rules
- Persisted audit trail for every signal

Target daily frequency:

- `watchlist_candidates_per_day`: 10-40
- `valid_intraday_setups_per_day`: 0-8
- `approved_paper_trades_per_day`: 0-5
- `no_trade_days_allowed`: true

Risk profile: balanced aggressive. The system should reject most noisy penny
stocks while still producing paper trades when catalyst, volume, liquidity, and
setup quality line up.

## Phase 2 Account Rules

The paper account starts with:

- `starting_capital`: `$1,000`
- `risk_per_trade`: `0.5%` to `1.0%` of current equity
- `max_position_value_pct`: `25%`
- `max_daily_loss`: `3%`
- `max_open_positions`: `3`
- `no_overnight_holds`: `true`

The account layer rejects trades when:

- Position size is zero
- Cash is insufficient
- Daily loss limit is reached
- Risk/reward is below `1:1.5`
- Stop is invalid
- Liquidity/spread rules fail

The Learning Engine reports setup, news-type, time-of-day, confidence, R-multiple,
profit factor, drawdown, and milestone status. It only emits recommendations;
it does not loosen risk rules or enable live trading.

By default, `scan` continues from the latest saved account snapshot in the DB.
Use `--fresh-account` only for isolated smoke tests. Use `--trading-day` to
start a new day; equity and realized PnL continue, but daily PnL and daily loss
limits reset for that day.
