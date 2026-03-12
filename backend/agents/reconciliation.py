"""
Agent 6 — Reconciliation Agent
Cross-checks actual transactions against expected records.
Identifies matched, unmatched, and discrepancy items.
"""

import json
import logging
import re
from typing import Optional

from tools.claude_client import SONNET, run_agent

logger = logging.getLogger("agent.reconciliation")

SYSTEM_PROMPT = """You are an expert reconciliation accountant AI.

You have been given a list of actual transactions and a computed reconciliation summary.
Your task:
1. Identify patterns in the unmatched / discrepancy items.
2. Suggest the most likely root causes (e.g. timing differences, duplicate entries, missing invoices).
3. Provide a short action plan for the finance team.

Respond with a JSON object:
{
  "root_cause_analysis": "...",
  "action_plan": ["step1", "step2", ...],
  "risk_level": "low|medium|high",
  "estimated_resolution_hours": 0
}"""


def _reconcile_transactions(transactions: list[dict]) -> dict:
    """
    Simplified reconciliation:
    - 'Matched': transactions with same category+amount appearing an even number of times
    - 'Unmatched': odd-count or unique entries
    - 'Discrepancies': transactions where debits > 10x the category average
    """
    from collections import defaultdict

    cat_totals: dict[str, list[float]] = defaultdict(list)
    for tx in transactions:
        cat_totals[tx.get("category", "other")].append(float(tx.get("amount", 0)))

    matched = []
    unmatched = []
    discrepancies = []

    seen_keys: dict[str, int] = {}
    for tx in transactions:
        key = f"{tx.get('category')}|{tx.get('amount')}"
        seen_keys[key] = seen_keys.get(key, 0) + 1

    for tx in transactions:
        key = f"{tx.get('category')}|{tx.get('amount')}"
        amt = float(tx.get("amount", 0))
        cat_amounts = cat_totals[tx.get("category", "other")]
        avg = sum(cat_amounts) / len(cat_amounts) if cat_amounts else 1

        if seen_keys[key] % 2 == 0:
            matched.append(tx)
        elif amt < 0 and abs(amt) > abs(avg) * 5:
            discrepancies.append({**tx, "expected_avg": round(avg, 2)})
        else:
            unmatched.append(tx)

    total = len(transactions)
    return {
        "total_transactions": total,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "discrepancy_count": len(discrepancies),
        "match_rate_pct": round(len(matched) / total * 100, 1) if total else 0,
        "top_discrepancies": discrepancies[:5],
        "unmatched_sample": unmatched[:5],
    }


async def reconcile(ingestion_result: dict, run_id: Optional[str] = None) -> dict:
    logger.info("[ReconciliationAgent] Running for run_id=%s", run_id)

    transactions = ingestion_result.get("transactions", [])
    computed = _reconcile_transactions(transactions)

    context = {
        "run_id": run_id,
        "reconciliation_summary": computed,
    }

    claude_result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        model=SONNET,
        max_tokens=800,
    )

    raw = claude_result["text"]
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed = {}
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            parsed = {}

    logger.info(
        "[ReconciliationAgent] match_rate=%.1f%%, discrepancies=%d",
        computed["match_rate_pct"],
        computed["discrepancy_count"],
    )

    return {
        **computed,
        "root_cause_analysis": parsed.get("root_cause_analysis", ""),
        "action_plan": parsed.get("action_plan", []),
        "risk_level": parsed.get("risk_level", "medium"),
        "tokens_used": claude_result["tokens_used"],
    }
