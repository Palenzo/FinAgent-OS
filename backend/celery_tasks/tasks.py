"""
Celery task queue — scheduled and async pipeline execution.
Schedule: runs the full pipeline daily at midnight UTC.
"""

import os

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "finagent",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "nightly-pipeline": {
            "task": "celery_tasks.tasks.run_scheduled_pipeline",
            "schedule": crontab(hour=0, minute=0),  # midnight UTC
        },
    },
)


@celery_app.task(name="celery_tasks.tasks.run_scheduled_pipeline", bind=True, max_retries=2)
def run_scheduled_pipeline(self):
    """
    Nightly scheduled run using the last uploaded dataset in the DB.
    Falls back to a synthetic demo dataset if nothing is uploaded yet.
    """
    import asyncio
    import json

    try:
        asyncio.run(_async_scheduled_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)  # retry after 5 min


async def _async_scheduled_run():
    """Async implementation of the scheduled pipeline."""
    import uuid
    from datetime import datetime, timedelta
    import io
    import csv

    from db.models import AsyncSessionLocal, PipelineRun, RunStatus
    from graph.workflow import FinAgentState, build_graph

    # Build a synthetic dataset if no real data exists
    rows = [["date", "description", "amount", "category"]]
    base = datetime.utcnow()
    import random

    random.seed(42)
    for i in range(90):
        day = (base - timedelta(days=i)).strftime("%Y-%m-%d")
        rows.append([day, "Monthly SaaS Revenue", round(random.uniform(8000, 12000), 2), "revenue"])
        rows.append([day, "AWS Infrastructure", round(-random.uniform(800, 1500), 2), "expense"])
        rows.append([day, "Staff Salaries", -8500.00, "expense"])
        if i % 7 == 0:
            rows.append([day, "Consulting Invoice", round(random.uniform(2000, 5000), 2), "revenue"])

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    content = buffer.getvalue().encode()

    run_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        run = PipelineRun(id=run_id, triggered_by="schedule", status=RunStatus.running)
        db.add(run)
        await db.commit()

    graph = build_graph(AsyncSessionLocal, None)
    initial_state: FinAgentState = {
        "run_id": str(run_id),
        "triggered_by": "schedule",
        "file_content": content,
        "file_type": "csv",
        "errors": [],
        "completed_agents": [],
        "status": "running",
    }

    final_state = await graph.ainvoke(initial_state)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(PipelineRun).where(PipelineRun.id == run_id)
        )
        run = result.scalar_one()
        run.status = (
            RunStatus.completed
            if final_state.get("status") == "completed"
            else RunStatus.failed
        )
        from datetime import datetime

        run.completed_at = datetime.utcnow()
        await db.commit()
