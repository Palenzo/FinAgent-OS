"""
Agent 3 — P&L Analyzer
Calculates revenue, expenses, gross/net profit per period.
Claude writes the human-readable narrative.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from tools.claude_client import SONNET, run_agent

logger = logging.getLogger("agent.pnl")

SYSTEM_PROMPT = """You are a senior financial analyst AI specialising in P&L analysis.
You have been provided with structured transaction data.

Your task:
1. Validate the numerical P&L calculation below (already computed for you).
2. Write a clear, professional 3-paragraph executive narrative covering:
   - Revenue performance vs typical patterns
   - Expense efficiency analysis
   - Net profit health and key concerns
3. Flag any metric that deviates significantly from healthy benchmarks.

Respond with a JSON object:
{
  "narrative": "...",
  "key_insights": ["insight1", "insight2", ...],
  "health_score": 0-100,
  "alerts": ["alert1", ...]
}"""


def _compute_pnl(transactions: list[dict]) -> dict:
    """Pure Python P&L computation — no LLM needed for the numbers."""
    revenue = 0.0
    expenses = 0.0
    by_category: dict[str, float] = defaultdict(float)

    for tx in transactions:
        amt = float(tx.get("amount", 0))
        cat = tx.get("category", "other")
        by_category[cat] += amt
        if amt > 0:
            revenue += amt
        else:
            expenses += abs(amt)

    gross_profit = revenue - expenses
    # rough net: assume 25% tax on positive profit
    net_profit = gross_profit * 0.75 if gross_profit > 0 else gross_profit
    margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0

    return {
        "revenue": round(revenue, 2),
        "expenses": round(expenses, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "gross_margin_pct": round(margin, 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
    }


async def analyze(ingestion_result: dict, run_id: Optional[str] = None) -> dict:
    logger.info("[PnLAnalyzer] Starting analysis for run_id=%s", run_id)

    transactions = ingestion_result.get("transactions", [])
    pnl_numbers = _compute_pnl(transactions)

    context = {
        "run_id": run_id,
        "date_range": ingestion_result.get("date_range"),
        "total_transactions": ingestion_result.get("total_transactions"),
        "pnl_metrics": pnl_numbers,
        "category_breakdown": ingestion_result.get("categories"),
    }

    claude_result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        model=SONNET,
        max_tokens=1024,
    )

    import json, re
    raw = claude_result["text"]
    # Extract JSON block if embedded in prose
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed = {}
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            parsed = {"narrative": raw}

    logger.info(
        "[PnLAnalyzer] Done — revenue=$%.2f, net_profit=$%.2f",
        pnl_numbers["revenue"],
        pnl_numbers["net_profit"],
    )

    return {
        **pnl_numbers,
        "narrative": parsed.get("narrative", ""),
        "key_insights": parsed.get("key_insights", []),
        "health_score": parsed.get("health_score", 50),
        "alerts": parsed.get("alerts", []),
        "tokens_used": claude_result["tokens_used"],
    }
