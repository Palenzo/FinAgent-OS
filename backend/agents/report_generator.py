"""
Agent 7 — Report Generator Agent
Compiles outputs from all agents into a full financial report.
Claude (Opus) writes the executive summary and recommendations.
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from tools.claude_client import OPUS, run_agent

logger = logging.getLogger("agent.report_generator")

SYSTEM_PROMPT = """You are the CFO-level reporting AI for FinAgent OS.

You have received outputs from all 6 analysis agents. Your task is to compile a boardroom-ready financial report.

Write:
1. Executive Summary (3-4 paragraphs) — plain English, no jargon, suitable for a non-financial executive.
2. Key Metrics section — a concise list of the 5 most important numbers.
3. Top 3 Risks identified this period with severity.
4. Top 3 Opportunities for cost reduction or revenue growth.
5. Recommended Next Actions (numbered list, 5 items max).

Format your entire response as a Markdown document starting with "# FinAgent OS — Financial Report"."""


async def generate_report(state: dict) -> dict:
    run_id = state.get("run_id")
    logger.info("[ReportGenerator] Compiling report for run_id=%s", run_id)

    pnl = state.get("pnl_result", {})
    forecast = state.get("forecast_result", {})
    anomaly = state.get("anomaly_result", {})
    reconciliation = state.get("reconciliation_result", {})

    context = {
        "run_id": run_id,
        "report_date": datetime.utcnow().isoformat(),
        "pnl_summary": {
            "revenue": pnl.get("revenue"),
            "expenses": pnl.get("expenses"),
            "net_profit": pnl.get("net_profit"),
            "gross_margin_pct": pnl.get("gross_margin_pct"),
            "health_score": pnl.get("health_score"),
            "key_insights": pnl.get("key_insights", []),
        },
        "forecast_summary": {
            "30_day_projection": forecast.get("projections", {}).get(30),
            "90_day_projection": forecast.get("projections", {}).get(90),
            "confidence": forecast.get("confidence_level"),
            "risk_factors": forecast.get("risk_factors", []),
        },
        "anomaly_summary": {
            "total_flagged": anomaly.get("total_flagged", 0),
            "critical_count": anomaly.get("critical_count", 0),
            "top_anomalies": (anomaly.get("anomalies") or [])[:3],
        },
        "reconciliation_summary": {
            "match_rate_pct": reconciliation.get("match_rate_pct"),
            "unmatched_count": reconciliation.get("unmatched_count"),
            "risk_level": reconciliation.get("risk_level"),
        },
    }

    # Use Opus for final report — highest quality
    claude_result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        model=OPUS,
        max_tokens=3000,
        use_cache=False,  # reports should always be freshly generated
    )

    markdown_report = claude_result["text"]

    # Persist to DB
    try:
        from db.models import AsyncSessionLocal, FinancialReport
        import uuid

        async with AsyncSessionLocal() as db:
            report_row = FinancialReport(
                run_id=uuid.UUID(run_id) if run_id else None,
                pnl_data=pnl,
                forecast_data=forecast,
                anomalies=anomaly.get("anomalies", []),
                reconciliation=reconciliation,
                markdown_report=markdown_report,
                executive_summary=markdown_report[:2000],
            )
            db.add(report_row)
            await db.commit()
            report_id = str(report_row.id)
    except Exception as exc:
        logger.warning("[ReportGenerator] DB persist failed: %s", exc)
        report_id = None

    logger.info("[ReportGenerator] Report generated (%d chars)", len(markdown_report))

    return {
        "report_id": report_id,
        "markdown_report": markdown_report,
        "executive_summary": markdown_report[:2000],
        "tokens_used": claude_result["tokens_used"],
    }
