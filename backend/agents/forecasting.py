"""
Agent 4 — Forecasting Agent
Projects 30/60/90-day cash flow using linear trend + Claude interpretation.
"""

import logging
import re
import json
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from tools.claude_client import SONNET, run_agent

logger = logging.getLogger("agent.forecasting")

SYSTEM_PROMPT = """You are a financial forecasting AI with deep expertise in cash flow modelling.

You have been given historical transaction data and a computed linear trend forecast.
Your tasks:
1. Interpret the trend and qualitatively assess forecast reliability.
2. Identify seasonal patterns or one-off events that may distort the projection.
3. Provide a confidence-adjusted narrative for 30, 60, and 90-day outlooks.

Respond with a JSON object:
{
  "summary": "2-3 sentence overall forecast summary",
  "confidence_level": "high|medium|low",
  "risk_factors": ["risk1", "risk2"],
  "30_day": {"narrative": "...", "confidence_pct": 85},
  "60_day": {"narrative": "...", "confidence_pct": 72},
  "90_day": {"narrative": "...", "confidence_pct": 60}
}"""


def _compute_trend_forecast(transactions: list[dict]) -> dict:
    """Simple linear regression on daily net cash flow."""
    if not transactions:
        return {}

    from collections import defaultdict
    daily: dict[str, float] = defaultdict(float)
    for tx in transactions:
        day = tx["date"][:10]  # YYYY-MM-DD
        daily[day] += float(tx.get("amount", 0))

    sorted_days = sorted(daily.keys())
    y = np.array([daily[d] for d in sorted_days], dtype=float)
    x = np.arange(len(y))

    if len(x) < 2:
        avg = float(y[0]) if len(y) else 0
        return {"daily_avg": avg, "trend_slope": 0, "projections": {30: avg * 30}}

    slope, intercept = np.polyfit(x, y, 1)
    n = len(x)

    projections = {}
    for horizon in [30, 60, 90]:
        future_x = np.arange(n, n + horizon)
        projected_daily = slope * future_x + intercept
        projections[horizon] = round(float(projected_daily.sum()), 2)

    return {
        "daily_avg": round(float(y.mean()), 2),
        "trend_slope": round(float(slope), 4),
        "volatility": round(float(y.std()), 2),
        "projections": projections,
        "historical_days": n,
    }


async def forecast(ingestion_result: dict, run_id: Optional[str] = None) -> dict:
    logger.info("[ForecastingAgent] Starting for run_id=%s", run_id)

    transactions = ingestion_result.get("transactions", [])
    computed = _compute_trend_forecast(transactions)

    context = {
        "run_id": run_id,
        "date_range": ingestion_result.get("date_range"),
        "computed_forecast": computed,
        "total_transactions": ingestion_result.get("total_transactions"),
    }

    claude_result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        model=SONNET,
        max_tokens=1024,
    )

    raw = claude_result["text"]
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    parsed = {}
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            parsed = {"summary": raw}

    logger.info(
        "[ForecastingAgent] Projections: 30d=$%.2f, 60d=$%.2f, 90d=$%.2f",
        computed.get("projections", {}).get(30, 0),
        computed.get("projections", {}).get(60, 0),
        computed.get("projections", {}).get(90, 0),
    )

    return {
        **computed,
        "narrative_summary": parsed.get("summary", ""),
        "confidence_level": parsed.get("confidence_level", "medium"),
        "risk_factors": parsed.get("risk_factors", []),
        "outlook": {
            "30_day": parsed.get("30_day", {}),
            "60_day": parsed.get("60_day", {}),
            "90_day": parsed.get("90_day", {}),
        },
        "tokens_used": claude_result["tokens_used"],
    }
