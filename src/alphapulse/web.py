import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from alphapulse.learning import LearningEngine
from alphapulse.storage import SQLiteLogger


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AlphaPulse Command Center</title>
  <style>
    :root {
      --bg: #05070a;
      --surface: #0e131a;
      --surface-2: #151b24;
      --border: #202938;
      --text: #f8fafc;
      --muted: #8b98aa;
      --faint: #5b6678;
      --cyan: #38bdf8;
      --green: #22c55e;
      --red: #ef4444;
      --amber: #f59e0b;
      --violet: #a78bfa;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(ellipse 80% 45% at 50% -15%, rgba(56,189,248,0.12), transparent 55%),
        radial-gradient(ellipse 45% 30% at 100% 0%, rgba(34,197,94,0.08), transparent 55%),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .shell { display: grid; grid-template-columns: 232px 1fr; min-height: 100vh; }
    aside {
      border-right: 1px solid var(--border);
      background: rgba(5,7,10,0.92);
      padding: 18px 14px;
      position: sticky;
      top: 0;
      height: 100vh;
    }
    .brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 18px; border-bottom: 1px solid var(--border); }
    .mark { width: 30px; height: 30px; border-radius: 9px; background: linear-gradient(135deg, var(--cyan), var(--green)); box-shadow: 0 0 22px rgba(56,189,248,0.25); }
    .brand strong { letter-spacing: .12em; font-size: 13px; }
    nav { margin-top: 18px; display: grid; gap: 6px; }
    nav a { color: var(--muted); text-decoration: none; padding: 10px 12px; border-radius: 9px; border: 1px solid transparent; font-size: 13px; }
    nav a.active, nav a:hover { color: var(--text); background: rgba(56,189,248,0.08); border-color: rgba(56,189,248,0.22); }
    main { padding: 22px; min-width: 0; }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-bottom: 18px; }
    h1 { margin: 0; font-size: 22px; letter-spacing: -0.01em; }
    .sub { color: var(--muted); font-size: 12px; margin-top: 4px; }
    .status { display: flex; align-items: center; gap: 9px; color: var(--muted); font-size: 12px; }
    .dot { width: 8px; height: 8px; border-radius: 999px; background: var(--green); box-shadow: 0 0 14px rgba(34,197,94,0.7); }
    .pl-strip {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .card {
      background: linear-gradient(180deg, rgba(21,27,36,0.92), rgba(14,19,26,0.96));
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 14px 34px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.035);
      min-width: 0;
    }
    .card.accent { border-color: rgba(56,189,248,0.35); box-shadow: 0 0 0 1px rgba(56,189,248,0.08), 0 14px 34px rgba(0,0,0,0.32); }
    .label { color: var(--muted); text-transform: uppercase; letter-spacing: .12em; font-size: 10px; margin-bottom: 8px; }
    .value { font-family: "JetBrains Mono", Consolas, monospace; font-size: 22px; font-weight: 800; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
    .value.sm { font-size: 16px; }
    .green { color: var(--green); }
    .red { color: var(--red); }
    .amber { color: var(--amber); }
    .cyan { color: var(--cyan); }
    .grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(320px, .85fr); gap: 14px; }
    .panel-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
    .panel-title h2 { margin: 0; font-size: 14px; letter-spacing: .02em; }
    .pill { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 4px 8px; font-size: 11px; border: 1px solid var(--border); color: var(--muted); }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { color: var(--muted); text-align: left; font-weight: 600; padding: 9px 8px; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: .08em; font-size: 10px; }
    td { padding: 10px 8px; border-bottom: 1px solid rgba(32,41,56,0.72); color: #dbe4f0; }
    td.num { font-family: "JetBrains Mono", Consolas, monospace; font-variant-numeric: tabular-nums; }
    tr:hover td { background: rgba(56,189,248,0.035); }
    .badge { border-radius: 999px; padding: 4px 7px; font-size: 10px; font-weight: 700; border: 1px solid; }
    .badge.PAPER_TRADE { color: var(--green); border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.08); }
    .badge.WATCHLIST { color: var(--amber); border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.08); }
    .badge.REJECT { color: var(--red); border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.08); }
    .learn-grid { display: grid; gap: 10px; }
    .mini { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 12px; border-bottom: 1px solid rgba(32,41,56,0.7); padding-bottom: 8px; }
    .mini strong { color: var(--text); font-family: "JetBrains Mono", Consolas, monospace; }
    .note { color: var(--muted); font-size: 12px; line-height: 1.45; }
    @media (max-width: 1020px) {
      .shell { grid-template-columns: 1fr; }
      aside { position: static; height: auto; }
      nav { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .pl-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div class="brand"><div class="mark"></div><strong>ALPHAPULSE</strong></div>
      <nav>
        <a class="active" href="#overview">Overview</a>
        <a href="#ledger">Trade Ledger</a>
        <a href="#learning">Learning</a>
        <a href="/api/summary">API</a>
      </nav>
    </aside>
    <main>
      <div class="topbar">
        <div>
          <h1>Paper Trading Command Center</h1>
          <div class="sub">Live account state, P/L strip, signal decisions, and learning telemetry.</div>
        </div>
        <div class="status"><span class="dot"></span><span id="refreshState">Syncing...</span></div>
      </div>

      <section id="overview" class="pl-strip">
        <div class="card accent"><div class="label">Current Equity</div><div id="equity" class="value cyan">$0.00</div></div>
        <div class="card"><div class="label">Daily P/L</div><div id="dailyPnl" class="value">$0.00</div></div>
        <div class="card"><div class="label">Realized P/L</div><div id="realizedPnl" class="value">$0.00</div></div>
        <div class="card"><div class="label">Win Rate</div><div id="winRate" class="value sm">0.0%</div></div>
        <div class="card"><div class="label">Avg R</div><div id="avgR" class="value sm">0.00</div></div>
        <div class="card"><div class="label">Status</div><div id="tradingStatus" class="value sm">offline</div></div>
      </section>

      <section class="grid">
        <div id="ledger" class="card">
          <div class="panel-title">
            <h2>Trade Documentation Ledger</h2>
            <span id="tradeCounts" class="pill">0 trades</span>
          </div>
          <div style="overflow:auto">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th><th>Decision</th><th>Setup</th><th>Shares</th><th>Entry</th><th>Exit</th><th>P/L</th><th>R</th><th>Confidence</th>
                </tr>
              </thead>
              <tbody id="tradeRows"></tbody>
            </table>
          </div>
        </div>

        <div id="learning" class="card">
          <div class="panel-title">
            <h2>Learning Snapshot</h2>
            <span id="milestone" class="pill">pre_50</span>
          </div>
          <div class="learn-grid">
            <div class="mini"><span>Total paper trades</span><strong id="learnTrades">0</strong></div>
            <div class="mini"><span>Profit factor</span><strong id="profitFactor">0.00</strong></div>
            <div class="mini"><span>Max drawdown</span><strong id="drawdown">$0.00</strong></div>
            <div class="mini"><span>Best setup</span><strong id="bestSetup">none</strong></div>
            <div class="note" id="recommendation">Collect trades to unlock recommendations.</div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const money = (value) => {
      const n = Number(value || 0);
      return `${n < 0 ? '-' : ''}$${Math.abs(n).toFixed(2)}`;
    };
    const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
    const cls = (value) => Number(value || 0) >= 0 ? 'green' : 'red';

    async function load() {
      const [summaryRes, tradesRes, learningRes] = await Promise.all([
        fetch('/api/summary'),
        fetch('/api/trades?limit=30'),
        fetch('/api/learning'),
      ]);
      const summary = await summaryRes.json();
      const trades = await tradesRes.json();
      const learning = await learningRes.json();
      renderSummary(summary);
      renderTrades(trades);
      renderLearning(learning);
      document.getElementById('refreshState').textContent = `Live - ${new Date().toLocaleTimeString()}`;
    }

    function renderSummary(summary) {
      const account = summary.account || {};
      const signals = summary.signals || {};
      const daily = Number(account.daily_pnl || 0);
      const realized = Number(account.realized_pnl || 0);
      document.getElementById('equity').textContent = money(account.current_equity);
      document.getElementById('dailyPnl').textContent = money(daily);
      document.getElementById('dailyPnl').className = `value ${cls(daily)}`;
      document.getElementById('realizedPnl').textContent = money(realized);
      document.getElementById('realizedPnl').className = `value ${cls(realized)}`;
      document.getElementById('winRate').textContent = pct(signals.win_rate);
      document.getElementById('avgR').textContent = Number(signals.avg_r || 0).toFixed(2);
      document.getElementById('tradingStatus').textContent = account.trading_enabled ? 'enabled' : 'locked';
      document.getElementById('tradingStatus').className = `value sm ${account.trading_enabled ? 'green' : 'red'}`;
      document.getElementById('tradeCounts').textContent = `${signals.paper_trades || 0} paper / ${signals.watchlist || 0} watch / ${signals.rejected || 0} rejected`;
    }

    function renderTrades(rows) {
      const body = document.getElementById('tradeRows');
      body.innerHTML = '';
      for (const row of rows) {
        const pnl = Number(row.pnl_usd || 0);
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${row.ticker}</td>
          <td><span class="badge ${row.decision}">${row.decision}</span></td>
          <td>${row.setup}</td>
          <td class="num">${row.shares}</td>
          <td class="num">${Number(row.theoretical_entry || 0).toFixed(4)}</td>
          <td class="num">${row.exit_price == null ? '' : Number(row.exit_price).toFixed(4)}</td>
          <td class="num ${cls(pnl)}">${money(pnl)}</td>
          <td class="num">${row.r_multiple == null ? '' : Number(row.r_multiple).toFixed(2)}</td>
          <td class="num">${row.confidence}</td>
        `;
        body.appendChild(tr);
      }
    }

    function renderLearning(report) {
      const overall = report.overall || {};
      const bySetup = report.by_setup || {};
      const best = Object.entries(bySetup).sort((a, b) => (b[1].avg_r || 0) - (a[1].avg_r || 0))[0];
      document.getElementById('milestone').textContent = report.milestone || 'pre_50_collect_data';
      document.getElementById('learnTrades').textContent = report.total_trades || 0;
      document.getElementById('profitFactor').textContent = Number(overall.profit_factor || 0).toFixed(2);
      document.getElementById('drawdown').textContent = money(overall.max_drawdown_usd || 0);
      document.getElementById('bestSetup').textContent = best ? best[0] : 'none';
      document.getElementById('recommendation').textContent = (report.recommendations || ['Collect more trades.'])[0];
    }

    load().catch((err) => {
      document.getElementById('refreshState').textContent = `Error: ${err}`;
    });
    setInterval(() => load().catch(console.error), 10000);
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    db_path: Path

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(HTML)
            return
        if parsed.path == "/api/summary":
            self._send_json(SQLiteLogger(self.db_path).dashboard_summary())
            return
        if parsed.path == "/api/trades":
            limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
            rows = SQLiteLogger(self.db_path).recent_paper_trades(limit=limit)
            self._send_json([dict(row) for row in rows])
            return
        if parsed.path == "/api/learning":
            self._send_json(LearningEngine(self.db_path).report())
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: object) -> None:
        data = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve_dashboard(db_path: str | Path, host: str, port: int) -> None:
    handler = type(
        "AlphaPulseDashboardHandler",
        (DashboardHandler,),
        {"db_path": Path(db_path)},
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"AlphaPulse dashboard running at http://{host}:{port}")
    server.serve_forever()
