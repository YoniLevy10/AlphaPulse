import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from statistics import mean


def _profit_factor(pnls: list[float]) -> float:
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    if gross_loss == 0:
        return gross_profit if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return round(max_dd, 2)


def _group_metrics(rows: list[sqlite3.Row], key: str) -> dict[str, dict[str, float]]:
    groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)

    metrics = {}
    for group, group_rows in groups.items():
        pnls = [row["pnl_usd"] for row in group_rows]
        r_values = [row["r_multiple"] for row in group_rows if row["r_multiple"] is not None]
        wins = sum(1 for row in group_rows if row["pnl_usd"] > 0)
        metrics[group] = {
            "trades": len(group_rows),
            "win_rate": round(wins / len(group_rows), 3),
            "avg_r": round(mean(r_values), 3) if r_values else 0.0,
            "profit_factor": round(_profit_factor(pnls), 3),
            "drawdown_usd": _max_drawdown(pnls),
            "pnl_usd": round(sum(pnls), 2),
        }
    return metrics


class LearningEngine:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def report(self) -> dict[str, object]:
        rows = self._load_closed_paper_trades()
        total = len(rows)
        pnls = [row["pnl_usd"] for row in rows]
        r_values = [row["r_multiple"] for row in rows if row["r_multiple"] is not None]
        wins = sum(1 for row in rows if row["pnl_usd"] > 0)

        report = {
            "total_trades": total,
            "milestone": self._milestone(total),
            "overall": {
                "win_rate": round(wins / total, 3) if total else 0.0,
                "avg_r": round(mean(r_values), 3) if r_values else 0.0,
                "profit_factor": round(_profit_factor(pnls), 3) if rows else 0.0,
                "max_drawdown_usd": _max_drawdown(pnls) if rows else 0.0,
                "pnl_usd": round(sum(pnls), 2),
            },
            "by_setup": _group_metrics(rows, "setup"),
            "by_time_of_day": _group_metrics(rows, "time_of_day"),
            "by_news_type": _group_metrics(rows, "news_type"),
            "confidence_calibration": self._confidence_calibration(rows),
            "recommendations": self._recommendations(rows),
        }
        return report

    def _load_closed_paper_trades(self) -> list[sqlite3.Row]:
        if not self.db_path.exists():
            return []
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return list(
                conn.execute(
                    """
                    SELECT *
                    FROM paper_trades
                    WHERE decision = 'PAPER_TRADE'
                      AND result = 'CLOSED_SIMULATED'
                    ORDER BY id
                    """
                )
            )

    def _confidence_calibration(self, rows: list[sqlite3.Row]) -> dict[str, dict[str, float]]:
        buckets: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in rows:
            confidence = row["confidence"]
            bucket_start = int(confidence // 10) * 10
            buckets[f"{bucket_start}-{bucket_start + 9}"].append(row)
        return {
            bucket: {
                "trades": len(bucket_rows),
                "win_rate": round(
                    sum(1 for row in bucket_rows if row["pnl_usd"] > 0) / len(bucket_rows),
                    3,
                ),
                "avg_r": round(mean(row["r_multiple"] for row in bucket_rows), 3),
            }
            for bucket, bucket_rows in sorted(buckets.items())
        }

    def _recommendations(self, rows: list[sqlite3.Row]) -> list[str]:
        total = len(rows)
        recommendations: list[str] = []
        if total < 50:
            recommendations.append("Collect at least 50 paper trades before changing thresholds.")
        elif total < 100:
            recommendations.append("Initial report only; avoid aggressive rule changes.")
        elif total < 200:
            recommendations.append("Review threshold recommendations, but keep adaptive changes manual.")
        else:
            recommendations.append("Limited adaptive scoring can be considered within risk guardrails.")

        for setup, metrics in _group_metrics(rows, "setup").items():
            if metrics["trades"] >= 10 and metrics["avg_r"] < 0:
                recommendations.append(f"Lower confidence for weak setup: {setup}.")
            if metrics["trades"] >= 10 and metrics["avg_r"] > 0.7:
                recommendations.append(f"Consider modest confidence lift for strong setup: {setup}.")

        for news_type, metrics in _group_metrics(rows, "news_type").items():
            if metrics["trades"] >= 5 and metrics["profit_factor"] < 1:
                recommendations.append(f"Reduce position size or tighten filters for news type: {news_type}.")

        for time_bucket, metrics in _group_metrics(rows, "time_of_day").items():
            if metrics["trades"] >= 5 and metrics["avg_r"] < 0:
                recommendations.append(f"Mark time bucket as low priority: {time_bucket}.")

        return recommendations

    def _milestone(self, total: int) -> str:
        if total < 50:
            return "pre_50_collect_data"
        if total < 100:
            return "50_trade_initial_report"
        if total < 200:
            return "100_trade_threshold_review"
        if total < 300:
            return "200_trade_limited_adaptive_scoring"
        return "300_plus_edge_review"
