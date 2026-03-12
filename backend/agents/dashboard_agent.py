"""
Agent 10 — Dashboard Agent
Pushes real-time state updates to all connected frontend WebSocket clients.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger("agent.dashboard")


def _serialize_state_snapshot(state: dict) -> dict:
    """Convert full pipeline state to a lightweight frontend-friendly snapshot."""
    pnl = state.get("pnl_result", {})
    forecast = state.get("forecast_result", {})
    anomaly = state.get("anomaly_result", {})
    recon = state.get("reconciliation_result", {})

    return {
        "type": "pipeline_complete",
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "completed_agents": state.get("completed_agents", []),
        "errors": state.get("errors", []),
        "metrics": {
            "revenue": pnl.get("revenue"),
            "net_profit": pnl.get("net_profit"),
            "gross_margin_pct": pnl.get("gross_margin_pct"),
            "health_score": pnl.get("health_score"),
            "anomalies_flagged": anomaly.get("total_flagged", 0),
            "critical_anomalies": anomaly.get("critical_count", 0),
            "match_rate_pct": recon.get("match_rate_pct"),
            "forecast_30d": (forecast.get("projections") or {}).get(30),
            "forecast_90d": (forecast.get("projections") or {}).get(90),
        },
        "anomalies": (anomaly.get("anomalies") or [])[:10],
        "executive_summary": (state.get("report_result") or {}).get("executive_summary", ""),
    }


async def push_update(state: dict, ws_manager: Any):
    """Broadcast final pipeline state to all WebSocket clients."""
    if ws_manager is None:
        logger.warning("[DashboardAgent] No WebSocket manager available — skipping push")
        return

    snapshot = _serialize_state_snapshot(state)
    await ws_manager.broadcast(snapshot)
    logger.info(
        "[DashboardAgent] Broadcast sent to %d clients", len(ws_manager.active)
    )


async def push_agent_event(event_type: str, agent_name: str, data: dict, ws_manager: Any):
    """
    Lightweight mid-pipeline event push (call from individual agents if needed).
    event_type: agent_started | agent_done | agent_error
    """
    if ws_manager is None:
        return

    payload = {
        "type": event_type,
        "agent": agent_name,
        "data": data,
    }
    await ws_manager.broadcast(payload)
