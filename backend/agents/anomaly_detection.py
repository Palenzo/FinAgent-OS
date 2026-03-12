"""
Agent 5 — Anomaly Detection Agent
Uses Z-score + IQR to flag statistical outliers, then Claude explains WHY.
"""

import json
import logging
import re
from typing import Optional

import numpy as np

from tools.claude_client import SONNET, run_agent

logger = logging.getLogger("agent.anomaly")

SYSTEM_PROMPT = """You are a forensic financial analyst AI specialising in transaction anomaly investigation.

You have been given a list of flagged transactions that exceeded statistical thresholds.
For EACH anomaly:
1. Explain WHY it is suspicious in plain English (1-2 sentences).
2. Assign a severity: low | medium | high | critical.
3. Recommend a specific action the finance team should take.

Respond with a JSON array:
[
  {
    "transaction_index": 0,
    "reason": "...",
    "severity": "high",
    "recommended_action": "..."
  },
  ...
]"""


def _zscore_anomalies(transactions: list[dict], threshold: float = 2.5) -> list[dict]:
    amounts = np.array([float(tx.get("amount", 0)) for tx in transactions])
    if len(amounts) < 4:
        return []

    mean = amounts.mean()
    std = amounts.std()
    if std == 0:
        return []

    q1, q3 = np.percentile(amounts, 25), np.percentile(amounts, 75)
    iqr = q3 - q1
    lower_iqr = q1 - 1.5 * iqr
    upper_iqr = q3 + 1.5 * iqr

    flagged = []
    for i, tx in enumerate(transactions):
        amt = float(tx.get("amount", 0))
        z = abs((amt - mean) / std)
        iqr_flag = amt < lower_iqr or amt > upper_iqr

        if z > threshold or iqr_flag:
            flagged.append(
                {
                    "index": i,
                    "transaction": tx,
                    "z_score": round(float(z), 3),
                    "anomaly_score": round(min(z / threshold, 1.0), 3),
                }
            )

    # Duplicate detection: same amount + description within 3 days
    seen: dict[str, list[str]] = {}
    for i, tx in enumerate(transactions):
        key = f"{tx.get('amount')}|{tx.get('description', '')[:30]}"
        if key in seen:
            sister_idx = seen[key][-1]
            # check date proximity
            try:
                d1 = tx["date"][:10]
                d2 = transactions[int(sister_idx)]["date"][:10]
                from datetime import datetime
                delta = abs((datetime.fromisoformat(d1) - datetime.fromisoformat(d2)).days)
                if delta <= 3 and i not in [f["index"] for f in flagged]:
                    flagged.append(
                        {
                            "index": i,
                            "transaction": tx,
                            "z_score": 0,
                            "anomaly_score": 0.8,
                            "reason_hint": "potential_duplicate",
                        }
                    )
        seen.setdefault(key, []).append(str(i))

    return flagged


async def detect(ingestion_result: dict, run_id: Optional[str] = None) -> dict:
    logger.info("[AnomalyDetection] Running for run_id=%s", run_id)

    transactions = ingestion_result.get("transactions", [])
    flagged = _zscore_anomalies(transactions)

    if not flagged:
        logger.info("[AnomalyDetection] No anomalies detected")
        return {"anomalies": [], "total_flagged": 0, "tokens_used": 0}

    # Only send top 10 to Claude to control token cost
    top_flagged = sorted(flagged, key=lambda x: x["anomaly_score"], reverse=True)[:10]

    context = {
        "run_id": run_id,
        "flagged_transactions": top_flagged,
        "total_transactions": len(transactions),
    }

    claude_result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        model=SONNET,
        max_tokens=1500,
    )

    raw = claude_result["text"]
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    explanations = []
    if match:
        try:
            explanations = json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Merge statistical scores with Claude explanations
    enriched = []
    for i, item in enumerate(top_flagged):
        expl = explanations[i] if i < len(explanations) else {}
        tx = item["transaction"]
        enriched.append(
            {
                "transaction_date": tx.get("date"),
                "description": tx.get("description"),
                "amount": tx.get("amount"),
                "z_score": item["z_score"],
                "anomaly_score": item["anomaly_score"],
                "severity": expl.get("severity", "medium"),
                "reason": expl.get("reason", item.get("reason_hint", "Statistical outlier")),
                "recommended_action": expl.get("recommended_action", "Review manually"),
            }
        )

    logger.info("[AnomalyDetection] Flagged %d anomalies", len(enriched))

    return {
        "anomalies": enriched,
        "total_flagged": len(enriched),
        "critical_count": sum(1 for a in enriched if a["severity"] == "critical"),
        "tokens_used": claude_result["tokens_used"],
    }
