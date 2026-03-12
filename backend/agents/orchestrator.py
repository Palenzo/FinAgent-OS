"""
Agent 1 — Orchestrator
Decides pipeline sequencing based on the current financial context.
"""

import logging
from typing import Optional

from tools.claude_client import SONNET, run_agent

logger = logging.getLogger("agent.orchestrator")

SYSTEM_PROMPT = """You are the Orchestrator of FinAgent OS, an autonomous financial operations platform.
Your role is to review the incoming financial context and determine the optimal sequence of analysis operations.

Available agents (always run in this priority order):
1. data_ingestion — parse and normalise raw financial data
2. pnl_analyzer — calculate P&L metrics
3. forecasting — 30/60/90-day cash flow projection
4. anomaly_detection — flag suspicious transactions
5. reconciliation — cross-check against expected records
6. report_generator — compile executive report
7. notification — email stakeholders
8. audit — log everything to database
9. dashboard — push live updates to frontend

Respond with a JSON object:
{
  "recommended_sequence": ["agent1", "agent2", ...],
  "priority": "standard|urgent|partial",
  "notes": "brief reasoning"
}"""


async def decide_sequence(context: dict) -> dict:
    logger.info("[Orchestrator] Analysing context to plan pipeline")
    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        model=SONNET,
        max_tokens=512,
        use_cache=False,  # orchestrator decisions should always be fresh
    )
    logger.info("[Orchestrator] Plan generated (%d tokens)", result["tokens_used"])
    return result
