# AlphaPulse Real Data Policy

AlphaPulse must not mix sample/backtest data with a real paper-trading session.

## Required Direction

The production experiment should run only on real-time market data during real
market hours, using a broker-paper execution environment that behaves like a
real brokerage account without routing live orders.

Current safe mode:

- Paper trading only
- No live-money order routing
- No simulated CSV exits in real-data mode
- No fake/sample/backtest data in real-data mode

## CLI Guardrail

Use `--require-real-data` for any session that is intended to represent a real
paper-trading day:

```powershell
$env:PYTHONPATH = "src"
python -m alphapulse.cli scan --input live_snapshot.csv --db data/alphapulse.db --trading-day 2026-06-09 --require-real-data
```

When this flag is enabled, the CSV must include:

- `data_source`
- `feed_timestamp_utc`
- `is_real_time`
- `execution_mode`

Allowed `execution_mode` values:

- `PAPER_BROKER`
- `BROKER_PAPER`
- `BANK_PAPER`

Disallowed data sources:

- `sample`
- `demo`
- `mock`
- `manual`
- `backtest`
- `simulated_csv`

Rows with `simulated_exit_price` are rejected in real-data mode. Real exits must
come from broker-paper fills or real-time paper account events.

## Broker/Data Feed Target

For a realistic bank-like paper account, AlphaPulse should connect to one of:

- Alpaca Paper Trading + real-time market data
- Interactive Brokers paper account through IBKR API / TWS / Client Portal

The broker adapter should provide:

- real-time quotes/trades
- real-time account equity
- paper order submission
- paper fill events
- position state
- cancel/replace support
- market-hours/session awareness

## Not Allowed

- Live-money trading
- Synthetic exits in real-data mode
- Backtest data presented as live data
- Any automatic relaxation of risk rules
- Any order routing to a real exchange

