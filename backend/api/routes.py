"""
FastAPI routes — public API surface for the FinAgent OS platform.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditLog, FinancialReport, PipelineRun, RunStatus, get_db
from graph.workflow import FinAgentState, build_graph
from db.models import AsyncSessionLocal

router = APIRouter()


# ── Pipeline trigger ──────────────────────────────────────────────────────────

@router.post("/run")
async def trigger_pipeline(
    request: Request,
    file: UploadFile = File(...),
    file_type: str = Form("csv"),
    triggered_by: str = Form("manual"),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV/JSON financial file and kick off the full agent pipeline."""
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    run_id = uuid.uuid4()

    pipeline_run = PipelineRun(
        id=run_id,
        triggered_by=triggered_by,
        status=RunStatus.running,
    )
    db.add(pipeline_run)
    await db.commit()

    ws_manager = getattr(request.app.state, "ws_manager", None)
    graph = build_graph(AsyncSessionLocal, ws_manager)

    initial_state: FinAgentState = {
        "run_id": str(run_id),
        "triggered_by": triggered_by,
        "file_content": content,
        "file_type": file_type,
        "errors": [],
        "completed_agents": [],
        "status": "running",
    }

    # Run the graph (async invoke)
    final_state = await graph.ainvoke(initial_state)

    # Update pipeline run record
    pipeline_run.status = (
        RunStatus.completed if final_state.get("status") == "completed" else RunStatus.failed
    )
    pipeline_run.completed_at = datetime.utcnow()
    pipeline_run.summary = str(final_state.get("completed_agents", []))
    if final_state.get("errors"):
        pipeline_run.error_message = str(final_state["errors"])
    await db.commit()

    return {
        "run_id": str(run_id),
        "status": final_state.get("status"),
        "completed_agents": final_state.get("completed_agents"),
        "errors": final_state.get("errors"),
    }


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports")
async def list_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FinancialReport).order_by(FinancialReport.created_at.desc()).limit(20)
    )
    reports = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "run_id": str(r.run_id),
            "period_start": r.period_start,
            "period_end": r.period_end,
            "created_at": r.created_at,
        }
        for r in reports
    ]


@router.get("/reports/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FinancialReport).where(FinancialReport.id == uuid.UUID(report_id))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": str(report.id),
        "pnl_data": report.pnl_data,
        "forecast_data": report.forecast_data,
        "anomalies": report.anomalies,
        "reconciliation": report.reconciliation,
        "executive_summary": report.executive_summary,
        "markdown_report": report.markdown_report,
        "created_at": report.created_at,
    }


# ── Audit logs ────────────────────────────────────────────────────────────────

@router.get("/audit/{run_id}")
async def get_audit_trail(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.run_id == uuid.UUID(run_id))
        .order_by(AuditLog.created_at)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "agent_name": l.agent_name,
            "action": l.action,
            "tokens_used": l.tokens_used,
            "duration_ms": l.duration_ms,
            "status": l.status,
            "created_at": l.created_at,
        }
        for l in logs
    ]


# ── Pipeline runs ─────────────────────────────────────────────────────────────

@router.get("/runs")
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "triggered_by": r.triggered_by,
            "status": r.status,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
        }
        for r in runs
    ]
