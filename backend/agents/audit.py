"""
Agent 9 — Audit Agent
Logs every agent action, decision, and Claude API call to PostgreSQL.
Full traceability — every number traces back to source.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditLog, PipelineRun, RunStatus

logger = logging.getLogger("agent.audit")


async def log_agent_action(
    run_id: Optional[str],
    agent_name: str,
    action: str,
    input_data: Optional[dict],
    output_data: Optional[dict],
    claude_model: Optional[str],
    tokens_used: int,
    duration_ms: int,
    status: str,
    error: Optional[str],
    db: AsyncSession,
):
    """Write a single audit entry — called by individual agents."""
    import uuid

    entry = AuditLog(
        run_id=uuid.UUID(run_id) if run_id else None,
        agent_name=agent_name,
        action=action,
        input_data=input_data,
        output_data=output_data,
        claude_model=claude_model,
        tokens_used=tokens_used,
        duration_ms=duration_ms,
        status=status,
        error=error,
    )
    db.add(entry)
    await db.commit()


async def log_run(state: dict, db: AsyncSession):
    """
    Called at end of pipeline — write a summary audit entry for the whole run.
    """
    import uuid

    run_id = state.get("run_id")
    completed = state.get("completed_agents", [])
    errors = state.get("errors", [])

    total_tokens = 0
    for key in ["pnl_result", "forecast_result", "anomaly_result", "report_result"]:
        result = state.get(key, {})
        total_tokens += result.get("tokens_used", 0)

    summary_entry = AuditLog(
        run_id=uuid.UUID(run_id) if run_id else None,
        agent_name="audit",
        action="pipeline_summary",
        input_data={"triggered_by": state.get("triggered_by")},
        output_data={
            "completed_agents": completed,
            "total_agents": len(completed),
            "total_tokens_used": total_tokens,
            "errors": errors,
        },
        claude_model="mixed",
        tokens_used=total_tokens,
        duration_ms=0,
        status="success" if state.get("status") == "completed" else "partial",
        error=str(errors) if errors else None,
    )
    db.add(summary_entry)
    await db.commit()
    logger.info("[AuditAgent] Pipeline audit logged, total_tokens=%d", total_tokens)
